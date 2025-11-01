"""
OCR Endpoint

Kindle画像のアップロードとOCR処理を行うエンドポイント
Phase 1-3 MVP Implementation + Rate Limiting (Phase 1-8)
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
import pytesseract
from PIL import Image
import io
import logging
import uuid

from app.core.database import get_db
from app.core.security import get_current_user_or_default
from app.models import Job, OCRResult, User
from app.schemas.ocr import OCRUploadResponse, JobResponse
from app.services.rate_limiter import limiter, RateLimitConfig

# ロガー設定
logger = logging.getLogger(__name__)

# ルーター設定
router = APIRouter()

# 許可する画像ファイル形式
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image_file(file: UploadFile) -> None:
    """
    画像ファイルのバリデーション

    Args:
        file: アップロードされたファイル

    Raises:
        HTTPException: ファイルが無効な場合
    """
    # ファイル名チェック
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ファイル名が指定されていません"
        )

    # 拡張子チェック
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"許可されていないファイル形式です。対応形式: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def extract_text_from_image(image_data: bytes) -> tuple[str, float]:
    """
    高精度OCR処理（画像前処理パイプライン適用 + ヘッダー/フッター除去）

    処理フロー:
    1. 画像前処理（ノイズ除去、コントラスト強調、二値化）
    2. ヘッダー/フッター領域の除去（上下10%）
    3. Tesseract OCR実行（日本語+英語、最適化設定）
    4. テキストクリーニング（ページ番号などの除去）
    5. 信頼度スコア計算

    Args:
        image_data: 画像データ (bytes)

    Returns:
        tuple[str, float]: (抽出されたテキスト, 信頼度スコア 0.0-1.0)

    Raises:
        HTTPException: OCR処理に失敗した場合
    """
    try:
        # 新しい高精度OCRサービスを使用（ヘッダー/フッター除去付き）
        from app.services.ocr_service import extract_text_from_image_bytes

        text, confidence = extract_text_from_image_bytes(image_data)

        # テキストクリーニング（ページ番号などの除去）
        text = _clean_ocr_text(text)

        logger.info(f"✅ Enhanced OCR complete: {len(text)} chars, {confidence:.2%} confidence")

        return text, confidence

    except Exception as e:
        logger.error(f"❌ Enhanced OCR処理エラー: {e}", exc_info=True)

        # フォールバック: 従来のOCR処理
        logger.warning("⚠️ Falling back to legacy OCR processing")
        try:
            # PIL Imageに変換
            image = Image.open(io.BytesIO(image_data))

            # Tesseract OCR実行（日本語+英語）
            custom_config = r'--oem 3 --psm 6'  # LSTM OCRエンジン + 単一ブロック
            text = pytesseract.image_to_string(
                image,
                lang='jpn+eng',
                config=custom_config
            )

            # 信頼度スコアを取得
            data = pytesseract.image_to_data(
                image,
                lang='jpn+eng',
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )

            # 信頼度の平均を計算（-1は無効な値なので除外）
            confidences = [float(conf) for conf in data['conf'] if conf != '-1' and int(conf) >= 0]
            avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

            # フォールバックでもクリーニング適用
            text = _clean_ocr_text(text)

            return text.strip(), avg_confidence

        except Exception as fallback_error:
            logger.error(f"❌ Fallback OCR also failed: {fallback_error}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR処理に失敗しました: {str(e)}"
            )


def _clean_ocr_text(text: str) -> str:
    """
    OCR抽出テキストのクリーニング（ページ番号などの除去）

    除去対象:
    - 「Page X」形式のページ番号
    - 「ページ X」形式のページ番号
    - 数字のみの短い行（ページ番号の可能性）
    - 過度な空白行

    Args:
        text: OCR抽出されたテキスト

    Returns:
        str: クリーニングされたテキスト
    """
    import re

    if not text:
        return ""

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # 「Page X」形式のページ番号を除去
        if re.match(r'^Page\s+\d+$', line, re.IGNORECASE):
            continue

        # 「ページ X」形式のページ番号を除去
        if re.match(r'^ページ\s*\d+$', line):
            continue

        # 数字のみの短い行を除去（ページ番号の可能性）
        if re.match(r'^\d+$', line) and len(line) <= 4:
            continue

        # 短すぎる行（ノイズ）をスキップ（日本語文字は例外）
        if len(line) < 2 and not any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in line):
            continue

        cleaned_lines.append(line)

    cleaned_text = '\n'.join(cleaned_lines)

    # 3行以上の連続改行を2行に圧縮
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

    return cleaned_text.strip()


@router.post("/upload", response_model=OCRUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimitConfig.OCR_UPLOAD)
async def upload_and_ocr(
    request: Request,
    file: UploadFile = File(..., description="OCR処理する画像ファイル"),
    book_title: str = "Untitled",
    page_num: int = 1,
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
) -> OCRUploadResponse:
    """
    画像ファイルをアップロードしてOCR処理を実行

    Args:
        file: アップロードされた画像ファイル (.png, .jpg, .jpeg)
        book_title: 書籍タイトル (デフォルト: "Untitled")
        page_num: ページ番号 (デフォルト: 1)
        db: データベースセッション

    Returns:
        OCRUploadResponse: OCR結果（job_id, book_title, page_num, text, confidence）

    Raises:
        HTTPException: ファイルが無効、OCR処理失敗、DB保存失敗時
    """
    logger.info(f"📤 OCRアップロード開始: {file.filename}, 書籍={book_title}, ページ={page_num}")

    # ファイルバリデーション
    validate_image_file(file)

    try:
        # ファイルデータを読み込み
        image_data = await file.read()

        # ファイルサイズチェック
        if len(image_data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"ファイルサイズが大きすぎます（上限: {MAX_FILE_SIZE / 1024 / 1024}MB）"
            )

        # Job作成
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            user_id=current_user.id,  # 認証されたユーザーID
            type="ocr",
            status="processing",
            progress=0
        )
        db.add(job)
        db.flush()  # IDを取得するためにflush

        logger.info(f"✅ Job作成完了: job_id={job_id}")

        # OCR処理実行
        logger.info("🔍 OCR処理開始...")
        extracted_text, confidence = extract_text_from_image(image_data)
        logger.info(f"✅ OCR処理完了: テキスト長={len(extracted_text)}, 信頼度={confidence:.2f}")

        # OCRResult保存
        ocr_result = OCRResult(
            job_id=job_id,
            book_title=book_title,
            page_num=page_num,
            text=extracted_text,
            confidence=confidence,
            image_blob=image_data  # 画像をBYTEAとして保存
        )
        db.add(ocr_result)

        # Jobステータス更新
        job.status = "completed"
        job.progress = 100

        # コミット
        db.commit()
        db.refresh(ocr_result)

        logger.info(f"✅ OCR結果保存完了: ocr_result_id={ocr_result.id}")

        return OCRUploadResponse(
            job_id=job_id,
            book_title=book_title,
            page_num=page_num,
            text=extracted_text,
            confidence=confidence
        )

    except HTTPException:
        # HTTPExceptionはそのまま再送出
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"❌ OCR処理エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR処理中にエラーが発生しました: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
@limiter.limit(RateLimitConfig.STANDARD_API)
async def get_job_status(
    request: Request,
    job_id: str,
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
) -> JobResponse:
    """
    ジョブのステータスを取得

    Args:
        job_id: ジョブID (UUID)
        db: データベースセッション

    Returns:
        JobResponse: ジョブ情報

    Raises:
        HTTPException: ジョブが見つからない場合
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ジョブが見つかりません: {job_id}"
        )

    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at
    )
