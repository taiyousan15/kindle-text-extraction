"""
Capture Service

自動キャプチャのバックグラウンドタスク処理サービス
Phase 1-4 Implementation
"""
import logging
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import pytesseract
from PIL import Image
import io

from app.core.database import SessionLocal
from app.models import Job, OCRResult
from app.services.capture import SeleniumKindleCapture, SeleniumCaptureConfig

logger = logging.getLogger(__name__)


class CaptureService:
    """自動キャプチャサービス"""

    @staticmethod
    def start_capture_task(
        job_id: str,
        amazon_email: str,
        amazon_password: str,
        book_url: str,
        book_title: str = "Untitled",
        max_pages: int = 100,
        headless: bool = True
    ) -> None:
        """
        自動キャプチャタスクをバックグラウンドで開始

        Args:
            job_id: ジョブID
            amazon_email: AmazonアカウントのEメールアドレス
            amazon_password: Amazonアカウントのパスワード
            book_url: Kindle Cloud ReaderのブックURL
            book_title: 書籍タイトル
            max_pages: 最大キャプチャページ数
            headless: ヘッドレスモード
        """
        # バックグラウンドスレッドでキャプチャタスクを実行
        thread = threading.Thread(
            target=CaptureService._run_capture_task,
            args=(job_id, amazon_email, amazon_password, book_url, book_title, max_pages, headless),
            daemon=True
        )
        thread.start()
        logger.info(f"✅ キャプチャタスクをバックグラウンドで開始: job_id={job_id}")

    @staticmethod
    def _run_capture_task(
        job_id: str,
        amazon_email: str,
        amazon_password: str,
        book_url: str,
        book_title: str,
        max_pages: int,
        headless: bool
    ) -> None:
        """
        キャプチャタスクの実行（バックグラウンドスレッド内）

        Args:
            job_id: ジョブID
            amazon_email: AmazonアカウントのEメールアドレス
            amazon_password: Amazonアカウントのパスワード (ログには出力しない)
            book_url: Kindle Cloud ReaderのブックURL
            book_title: 書籍タイトル
            max_pages: 最大キャプチャページ数
            headless: ヘッドレスモード
        """
        db = SessionLocal()
        capturer = None

        try:
            logger.info(f"🚀 キャプチャタスク開始: job_id={job_id}, book_title={book_title}")

            # Jobステータス更新: processing
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error(f"❌ ジョブが見つかりません: job_id={job_id}")
                return

            job.status = "processing"
            job.progress = 0
            db.commit()

            # 出力ディレクトリ設定
            output_dir = Path(f"./captures/{job_id}")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Seleniumキャプチャ設定
            config = SeleniumCaptureConfig(
                book_url=book_url,
                book_title=book_title,
                amazon_email=amazon_email,
                amazon_password=amazon_password,  # セキュリティ: ログには出力しない
                max_pages=max_pages,
                headless=headless,
                output_dir=output_dir
            )

            # Seleniumキャプチャ開始
            capturer = SeleniumKindleCapture(config)

            # 進捗コールバック
            def progress_callback(current_page: int, total_pages: int):
                """進捗更新コールバック"""
                try:
                    progress = int((current_page / total_pages) * 100)
                    job.progress = progress
                    db.commit()
                    logger.info(f"📊 進捗更新: {progress}% ({current_page}/{total_pages})")
                except Exception as e:
                    logger.error(f"❌ 進捗更新エラー: {e}")

            # キャプチャ実行
            result = capturer.capture_all_pages(progress_callback=progress_callback)

            if not result.success:
                raise Exception(result.error_message or "キャプチャ失敗")

            logger.info(f"✅ キャプチャ完了: {result.captured_pages}ページ")

            # OCR処理
            logger.info("🔍 OCR処理開始...")
            ocr_count = 0
            batch_size = 50  # バッチサイズ（メモリとトランザクションの最適化）
            total_images = len(result.image_paths)

            for idx, image_path in enumerate(result.image_paths, 1):
                try:
                    # ページ番号を抽出 (page_0001.png → 1)
                    page_num = int(image_path.stem.split("_")[1])

                    # OCR処理
                    extracted_text, confidence = CaptureService._extract_text_from_image_file(image_path)

                    # 画像データを読み込み
                    with open(image_path, "rb") as f:
                        image_data = f.read()

                    # OCRResult保存
                    ocr_result = OCRResult(
                        job_id=job_id,
                        book_title=book_title,
                        page_num=page_num,
                        text=extracted_text,
                        confidence=confidence,
                        image_blob=image_data
                    )
                    db.add(ocr_result)
                    ocr_count += 1

                    # バッチコミット（メモリとトランザクション管理）
                    if idx % batch_size == 0:
                        db.commit()
                        logger.info(f"📝 OCRバッチ保存: {idx}/{total_images} ({idx/total_images*100:.1f}%) - {ocr_count}件保存")

                except Exception as e:
                    logger.error(f"❌ OCR処理エラー (ページ {image_path}): {e}", exc_info=True)
                    # エラー時もコミットを試行（処理済みデータを保存）
                    try:
                        db.commit()
                    except:
                        db.rollback()
                    continue

            # 最終コミット（残りのデータ）
            try:
                db.commit()
                logger.info(f"✅ OCR処理完了: {ocr_count}/{total_images}ページ保存")
            except Exception as e:
                logger.error(f"❌ 最終コミットエラー: {e}", exc_info=True)
                # ロールバックしても一部はバッチ保存されている
                db.rollback()

            # Jobステータス更新: completed
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"🎉 キャプチャタスク完了: job_id={job_id}")

        except Exception as e:
            logger.error(f"❌ キャプチャタスクエラー: {e}", exc_info=True)

            # エラーの詳細をログに記録
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ エラー詳細:\n{error_details}")

            # Jobステータス更新: failed
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    # エラーメッセージを短縮（データベースフィールドサイズ制限対応）
                    error_msg = str(e)[:500] if len(str(e)) > 500 else str(e)
                    job.error_message = error_msg
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"📝 ジョブステータスを'failed'に更新: {error_msg}")
            except Exception as update_error:
                logger.error(f"❌ ジョブステータス更新エラー: {update_error}", exc_info=True)

        finally:
            # クリーンアップ
            if capturer:
                try:
                    capturer.close()
                except Exception as e:
                    logger.error(f"❌ キャプチャクローズエラー: {e}")

            db.close()

    @staticmethod
    def _extract_text_from_image_file(image_path: Path) -> tuple[str, float]:
        """
        画像ファイルからテキストを抽出 (高精度OCR with 前処理 + ヘッダー/フッター除去)

        Args:
            image_path: 画像ファイルパス

        Returns:
            tuple[str, float]: (抽出されたテキスト, 信頼度スコア)

        Raises:
            Exception: OCR処理失敗時
        """
        try:
            # ✅ 拡張OCRサービスを使用（前処理 + ヘッダー/フッター除去）
            from app.services.ocr_preprocessing import enhanced_ocr_with_preprocessing

            text, confidence = enhanced_ocr_with_preprocessing(
                str(image_path),
                lang='jpn+eng',
                enable_header_footer_removal=True,
                top_margin=0.10,      # 上部10%を除去（タイトル、ページ番号など）
                bottom_margin=0.10    # 下部10%を除去（ページ番号、フッターなど）
            )

            # さらにテキストクリーニング（本文以外の不要文字列を除去）
            text = CaptureService._clean_extracted_text(text)

            logger.debug(f"✅ Enhanced OCR: {len(text)} chars, {confidence:.2%} confidence")

            return text, confidence

        except Exception as e:
            logger.error(f"❌ Enhanced OCR処理エラー: {e}", exc_info=True)
            logger.warning("⚠️ Falling back to legacy OCR...")

            # フォールバック: 従来のOCR（拡張OCRが失敗した場合）
            try:
                image = Image.open(image_path)
                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(
                    image,
                    lang='jpn+eng',
                    config=custom_config
                )

                data = pytesseract.image_to_data(
                    image,
                    lang='jpn+eng',
                    config=custom_config,
                    output_type=pytesseract.Output.DICT
                )

                confidences = [float(conf) for conf in data['conf'] if conf != '-1' and int(conf) >= 0]
                avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

                # フォールバックでもクリーニングを適用
                text = CaptureService._clean_extracted_text(text)

                return text.strip(), avg_confidence

            except Exception as fallback_error:
                logger.error(f"❌ Fallback OCR also failed: {fallback_error}", exc_info=True)
                raise Exception(f"OCR処理に失敗しました: {str(e)}")

    @staticmethod
    def _clean_extracted_text(text: str) -> str:
        """
        抽出されたテキストをクリーニング（不要な文字列を除去）

        除去対象:
        - 「Page X」形式のページ番号
        - 「ページ X」形式のページ番号
        - 過度な空白行
        - 制御文字

        Args:
            text: OCR抽出されたテキスト

        Returns:
            str: クリーニングされたテキスト
        """
        import re

        if not text:
            return ""

        # 行単位で処理
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # 空行はスキップ
            if not line:
                continue

            # 「Page X」形式のページ番号を除去
            if re.match(r'^Page\s+\d+$', line, re.IGNORECASE):
                continue

            # 「ページ X」形式のページ番号を除去
            if re.match(r'^ページ\s*\d+$', line):
                continue

            # 数字のみの行を除去（ページ番号の可能性）
            if re.match(r'^\d+$', line) and len(line) <= 4:
                continue

            # 短すぎる行（ノイズの可能性）をスキップ
            # ただし、日本語1文字でも意味がある場合があるので慎重に
            if len(line) < 2 and not any('\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in line):
                continue

            cleaned_lines.append(line)

        # 改行で結合
        cleaned_text = '\n'.join(cleaned_lines)

        # 3行以上の連続改行を2行に圧縮
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

        return cleaned_text.strip()


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # テスト用（実際のAPIエンドポイントから呼び出される）
    CaptureService.start_capture_task(
        job_id="test-job-id",
        amazon_email="test@example.com",
        amazon_password="test-password",
        book_url="https://read.amazon.com/kindle-library",
        book_title="テスト書籍",
        max_pages=10,
        headless=True
    )
