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

            for image_path in result.image_paths:
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

                    logger.info(f"📝 OCR完了: ページ {page_num} (信頼度: {confidence:.2f})")

                except Exception as e:
                    logger.error(f"❌ OCR処理エラー (ページ {image_path}): {e}")
                    continue

            # コミット
            db.commit()
            logger.info(f"✅ OCR処理完了: {ocr_count}ページ保存")

            # Jobステータス更新: completed
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            db.commit()

            logger.info(f"🎉 キャプチャタスク完了: job_id={job_id}")

        except Exception as e:
            logger.error(f"❌ キャプチャタスクエラー: {e}", exc_info=True)

            # Jobステータス更新: failed
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception as update_error:
                logger.error(f"❌ ジョブステータス更新エラー: {update_error}")

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
        画像ファイルからテキストを抽出 (pytesseract)

        Args:
            image_path: 画像ファイルパス

        Returns:
            tuple[str, float]: (抽出されたテキスト, 信頼度スコア)

        Raises:
            Exception: OCR処理失敗時
        """
        try:
            # PIL Imageに変換
            image = Image.open(image_path)

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

            return text.strip(), avg_confidence

        except Exception as e:
            logger.error(f"❌ OCR処理エラー: {e}", exc_info=True)
            raise Exception(f"OCR処理に失敗しました: {str(e)}")


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
