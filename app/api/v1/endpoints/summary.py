"""
Summary Endpoint

テキスト要約機能のエンドポイント
Phase 3 Complete Implementation + Rate Limiting (Phase 1-8)
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Job, OCRResult, Summary
from app.models.user import User
from app.schemas.summary import (
    SummaryCreateRequest,
    SummaryCreateResponse,
    SummaryMultiLevelRequest,
    SummaryMultiLevelResponse,
    SummaryDetail,
    SummaryListResponse,
    SummaryRegenerateRequest,
    TokenUsage,
    SummaryLevelDetail,
    ErrorResponse
)
from app.services.summary_service import (
    SummaryService,
    SummaryLength,
    SummaryTone,
    SummaryGranularity,
    SummaryFormat,
    SummaryLevel
)
from app.services.rate_limiter import limiter, RateLimitConfig

# ロガー設定
logger = logging.getLogger(__name__)

# ルーター設定
router = APIRouter()


def get_text_from_job(db: Session, job_id: str, user_id: int) -> tuple[str, str]:
    """
    ジョブIDからOCR結果のテキストを取得

    Args:
        db: データベースセッション
        job_id: ジョブID
        user_id: ユーザーID

    Returns:
        (combined_text, book_title)のタプル

    Raises:
        HTTPException: ジョブが見つからない、またはOCR結果が空の場合
    """
    # ジョブ取得 (ユーザーフィルタリング)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    # OCR結果を取得（ページ順にソート）
    ocr_results = (
        db.query(OCRResult)
        .filter(OCRResult.job_id == job_id)
        .order_by(OCRResult.page_num)
        .all()
    )

    if not ocr_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OCR results found for job: {job_id}"
        )

    # テキストを結合
    combined_text = "\n\n".join([r.extracted_text for r in ocr_results if r.extracted_text])
    if not combined_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OCR results contain no text"
        )

    # 書籍タイトル取得（最初のOCR結果から）
    book_title = ocr_results[0].book_title

    return combined_text, book_title


@router.post(
    "/create",
    response_model=SummaryCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="要約作成",
    description="テキストまたはOCRジョブから要約を作成します"
)
@limiter.limit(RateLimitConfig.SUMMARY)
async def create_summary(
    http_request: Request,
    request: SummaryCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    要約作成エンドポイント

    Args:
        request: 要約作成リクエスト
        db: データベースセッション

    Returns:
        SummaryCreateResponse: 作成された要約情報
    """
    try:
        # テキストまたはjob_idのいずれかが必須
        if not request.text and not request.job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'text' or 'job_id' must be provided"
            )

        # テキストと書籍タイトルを取得
        if request.job_id:
            text, book_title = get_text_from_job(db, request.job_id, current_user.id)
            job_id = request.job_id
        else:
            text = request.text
            book_title = request.book_title or "Untitled"

            # テキスト直接指定の場合は、新しいジョブを作成
            job = Job(
                user_id=current_user.id,
                type="summary",
                status="completed",
                progress=100
            )
            db.add(job)
            db.flush()
            job_id = job.id

        logger.info(f"Creating summary for job: {job_id}, book: {book_title}")

        # 要約サービス初期化
        summary_service = SummaryService(provider="anthropic")

        # 要約実行
        result = summary_service.summarize(
            text=text,
            length=request.length,
            tone=request.tone,
            granularity=request.granularity,
            format_type=request.format,
            language=request.language
        )

        # データベースに保存
        summary = Summary(
            job_id=job_id,
            book_title=book_title,
            summary_text=result["summary"],
            granularity=request.granularity.value,
            length=request.length.value,
            tone=request.tone.value,
            format=request.format.value,
            language=result["language"]
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)

        logger.info(
            f"Summary created successfully: id={summary.id}, "
            f"tokens={result['tokens']['total']}, chunks={result['chunks']}"
        )

        # レスポンス作成
        return SummaryCreateResponse(
            summary_id=summary.id,
            job_id=job_id,
            book_title=book_title,
            summary_text=result["summary"],
            language=result["language"],
            granularity=request.granularity.value,
            length=request.length.value,
            tone=request.tone.value,
            format=request.format.value,
            token_usage=TokenUsage(**result["tokens"]),
            chunks=result["chunks"],
            is_mock=result["is_mock"],
            created_at=summary.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create summary: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create summary: {str(e)}"
        )


@router.post(
    "/create-multilevel",
    response_model=SummaryMultiLevelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="マルチレベル要約作成",
    description="3レベル（エグゼクティブ、標準、詳細）の要約を一度に作成します"
)
async def create_multilevel_summary(
    request: SummaryMultiLevelRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    マルチレベル要約作成エンドポイント

    Args:
        request: マルチレベル要約作成リクエスト
        db: データベースセッション

    Returns:
        SummaryMultiLevelResponse: 作成された3レベルの要約情報
    """
    try:
        # テキストまたはjob_idのいずれかが必須
        if not request.text and not request.job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'text' or 'job_id' must be provided"
            )

        # テキストと書籍タイトルを取得
        if request.job_id:
            text, book_title = get_text_from_job(db, request.job_id, current_user.id)
            job_id = request.job_id
        else:
            text = request.text
            book_title = request.book_title or "Untitled"

            # テキスト直接指定の場合は、新しいジョブを作成
            job = Job(
                user_id=current_user.id,
                type="summary_multilevel",
                status="completed",
                progress=100
            )
            db.add(job)
            db.flush()
            job_id = job.id

        logger.info(f"Creating multi-level summary for job: {job_id}, book: {book_title}")

        # 要約サービス初期化
        summary_service = SummaryService(provider="anthropic")

        # マルチレベル要約実行
        result = summary_service.summarize_multilevel(
            text=text,
            tone=request.tone,
            format_type=request.format,
            language=request.language
        )

        # 3つの要約をデータベースに保存
        summary_ids = []

        # Level 1: Executive
        summary_1 = Summary(
            job_id=job_id,
            book_title=book_title,
            summary_text=result["level_1"]["summary"],
            granularity="executive",
            length="short",
            tone=request.tone.value,
            format=request.format.value,
            language=result["language"]
        )
        db.add(summary_1)
        db.flush()
        summary_ids.append(summary_1.id)

        # Level 2: Standard
        summary_2 = Summary(
            job_id=job_id,
            book_title=book_title,
            summary_text=result["level_2"]["summary"],
            granularity="high_level",
            length="medium",
            tone=request.tone.value,
            format=request.format.value,
            language=result["language"]
        )
        db.add(summary_2)
        db.flush()
        summary_ids.append(summary_2.id)

        # Level 3: Detailed
        summary_3 = Summary(
            job_id=job_id,
            book_title=book_title,
            summary_text=result["level_3"]["summary"],
            granularity="comprehensive",
            length="long",
            tone=request.tone.value,
            format=request.format.value,
            language=result["language"]
        )
        db.add(summary_3)
        db.flush()
        summary_ids.append(summary_3.id)

        db.commit()

        logger.info(
            f"Multi-level summary created successfully: ids={summary_ids}, "
            f"total_tokens={result['total_tokens']['total']}"
        )

        # レスポンス作成
        return SummaryMultiLevelResponse(
            job_id=job_id,
            book_title=book_title,
            language=result["language"],
            level_1=SummaryLevelDetail(
                summary=result["level_1"]["summary"],
                level=result["level_1"]["level"],
                tokens=TokenUsage(**result["level_1"]["tokens"])
            ),
            level_2=SummaryLevelDetail(
                summary=result["level_2"]["summary"],
                level=result["level_2"]["level"],
                tokens=TokenUsage(**result["level_2"]["tokens"])
            ),
            level_3=SummaryLevelDetail(
                summary=result["level_3"]["summary"],
                level=result["level_3"]["level"],
                tokens=TokenUsage(**result["level_3"]["tokens"])
            ),
            total_tokens=TokenUsage(**result["total_tokens"]),
            summary_ids=summary_ids,
            is_mock=result["is_mock"],
            created_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create multi-level summary: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create multi-level summary: {str(e)}"
        )


@router.get(
    "/{summary_id}",
    response_model=SummaryDetail,
    summary="要約取得",
    description="IDを指定して要約を取得します"
)
async def get_summary(
    summary_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    要約取得エンドポイント

    Args:
        summary_id: 要約ID
        current_user: 認証されたユーザー
        db: データベースセッション

    Returns:
        SummaryDetail: 要約詳細情報
    """
    # ユーザーのジョブに紐づく要約のみ取得
    summary = db.query(Summary).join(Job).filter(
        Summary.id == summary_id,
        Job.user_id == current_user.id
    ).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary not found: {summary_id}"
        )

    return SummaryDetail.model_validate(summary)


@router.get(
    "/job/{job_id}",
    response_model=SummaryListResponse,
    summary="ジョブの要約リスト取得",
    description="ジョブIDに紐づく全ての要約を取得します"
)
async def get_summaries_by_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ジョブの要約リスト取得エンドポイント

    Args:
        job_id: ジョブID
        current_user: 認証されたユーザー
        db: データベースセッション

    Returns:
        SummaryListResponse: 要約リスト
    """
    # ジョブの存在確認 (ユーザーフィルタリング)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )

    # 要約を取得（新しい順）
    summaries = (
        db.query(Summary)
        .filter(Summary.job_id == job_id)
        .order_by(desc(Summary.created_at))
        .all()
    )

    return SummaryListResponse(
        summaries=[SummaryDetail.model_validate(s) for s in summaries],
        total=len(summaries)
    )


@router.put(
    "/{summary_id}/regenerate",
    response_model=SummaryCreateResponse,
    summary="要約再生成",
    description="異なるパラメータで要約を再生成します（元の要約は更新されます）"
)
async def regenerate_summary(
    summary_id: int,
    request: SummaryRegenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    要約再生成エンドポイント

    Args:
        summary_id: 要約ID
        request: 再生成パラメータ
        current_user: 認証されたユーザー
        db: データベースセッション

    Returns:
        SummaryCreateResponse: 再生成された要約情報
    """
    try:
        # 既存の要約を取得 (ユーザーフィルタリング)
        summary = db.query(Summary).join(Job).filter(
            Summary.id == summary_id,
            Job.user_id == current_user.id
        ).first()
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Summary not found: {summary_id}"
            )

        # ジョブからテキストを取得
        text, book_title = get_text_from_job(db, summary.job_id, current_user.id)

        logger.info(f"Regenerating summary: id={summary_id}")

        # 要約サービス初期化
        summary_service = SummaryService(provider="anthropic")

        # パラメータの決定（指定されていない場合は既存の値を使用）
        length = request.length or SummaryLength(summary.length or "medium")
        tone = request.tone or SummaryTone(summary.tone or "professional")
        granularity = request.granularity or SummaryGranularity(summary.granularity or "high_level")
        format_type = request.format or SummaryFormat.PLAIN_TEXT
        language = request.language

        # 要約実行
        result = summary_service.summarize(
            text=text,
            length=length,
            tone=tone,
            granularity=granularity,
            format_type=format_type,
            language=language
        )

        # 既存の要約を更新
        summary.summary_text = result["summary"]
        summary.granularity = granularity.value
        summary.length = length.value
        summary.tone = tone.value
        summary.format = format_type.value
        summary.language = result["language"]

        db.commit()
        db.refresh(summary)

        logger.info(
            f"Summary regenerated successfully: id={summary.id}, "
            f"tokens={result['tokens']['total']}"
        )

        # レスポンス作成
        return SummaryCreateResponse(
            summary_id=summary.id,
            job_id=summary.job_id,
            book_title=book_title,
            summary_text=result["summary"],
            language=result["language"],
            granularity=granularity.value,
            length=length.value,
            tone=tone.value,
            format=format_type.value,
            token_usage=TokenUsage(**result["tokens"]),
            chunks=result["chunks"],
            is_mock=result["is_mock"],
            created_at=summary.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate summary: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate summary: {str(e)}"
        )


@router.delete(
    "/{summary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="要約削除",
    description="要約を削除します"
)
async def delete_summary(
    summary_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    要約削除エンドポイント

    Args:
        summary_id: 要約ID
        current_user: 認証されたユーザー
        db: データベースセッション
    """
    # ユーザーのジョブに紐づく要約のみ削除
    summary = db.query(Summary).join(Job).filter(
        Summary.id == summary_id,
        Job.user_id == current_user.id
    ).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary not found: {summary_id}"
        )

    db.delete(summary)
    db.commit()

    logger.info(f"Summary deleted: id={summary_id}")
