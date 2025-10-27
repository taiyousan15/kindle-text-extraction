"""
Selenium + Kindle Cloud Reader 自動キャプチャサービス

完全バックグラウンドでKindle Cloud Readerから全ページを自動キャプチャ
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass
import logging
import base64

logger = logging.getLogger(__name__)


@dataclass
class SeleniumCaptureConfig:
    """Seleniumキャプチャ設定"""
    book_url: str
    book_title: str
    amazon_email: str
    amazon_password: str
    max_pages: int = 500
    headless: bool = True
    output_dir: Optional[Path] = None


@dataclass
class SeleniumCaptureResult:
    """Seleniumキャプチャ結果"""
    success: bool
    captured_pages: int
    image_paths: List[Path]
    actual_total_pages: Optional[int] = None  # 実際の総ページ数（自動検出）
    error_message: Optional[str] = None


class SeleniumKindleCapture:
    """Selenium + Kindle Cloud Readerでの自動キャプチャ"""

    def __init__(self, config: SeleniumCaptureConfig):
        self.config = config

        # 出力ディレクトリ設定
        if config.output_dir is None:
            self.output_dir = Path(f"captures/{config.book_title}")
        else:
            self.output_dir = config.output_dir

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Selenium WebDriver初期化
        self.driver = self._init_driver()

    def _init_driver(self) -> webdriver.Chrome:
        """Chrome WebDriver初期化"""
        options = webdriver.ChromeOptions()

        if self.config.headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')

        # ウィンドウサイズ（Kindleページ全体が見えるサイズ）
        options.add_argument('--window-size=1920,1080')

        # その他の推奨オプション
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')

        # User-Agent（Kindleが正常に動作するため）
        options.add_argument(
            'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )

        # WebDriver起動
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        logger.info(f"✅ Chrome WebDriver起動 (ヘッドレス: {self.config.headless})")
        return driver

    def login_amazon(self) -> bool:
        """Amazon自動ログイン"""
        try:
            logger.info("🔐 Amazonログイン開始...")

            self.driver.get("https://www.amazon.co.jp/ap/signin")

            # メールアドレス入力
            wait = WebDriverWait(self.driver, 10)
            email_field = wait.until(
                EC.presence_of_element_located((By.ID, "ap_email"))
            )
            email_field.clear()
            email_field.send_keys(self.config.amazon_email)
            email_field.send_keys(Keys.RETURN)

            logger.info("   📧 メールアドレス入力完了")
            time.sleep(2)

            # パスワード入力
            password_field = wait.until(
                EC.presence_of_element_located((By.ID, "ap_password"))
            )
            password_field.clear()
            password_field.send_keys(self.config.amazon_password)
            password_field.send_keys(Keys.RETURN)

            logger.info("   🔑 パスワード入力完了")
            time.sleep(3)

            # ログイン成功確認
            if "signin" not in self.driver.current_url.lower():
                logger.info("✅ Amazonログイン成功")
                return True
            else:
                logger.error("❌ Amazonログイン失敗（認証エラーの可能性）")
                return False

        except TimeoutException:
            logger.error("❌ Amazonログインタイムアウト")
            return False
        except Exception as e:
            logger.error(f"❌ Amazonログインエラー: {e}", exc_info=True)
            return False

    def capture_all_pages(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> SeleniumCaptureResult:
        """
        Kindle Cloud Readerで全ページキャプチャ

        Args:
            progress_callback: 進捗コールバック (current_page, total_pages)
            stop_check: 停止チェック関数 (True返却で中断)

        Returns:
            SeleniumCaptureResult
        """
        image_paths: List[Path] = []

        try:
            # Amazonログイン
            if not self.login_amazon():
                return SeleniumCaptureResult(
                    success=False,
                    captured_pages=0,
                    image_paths=[],
                    error_message="Amazonログイン失敗"
                )

            # 本を開く
            logger.info(f"📖 本を開いています: {self.config.book_url}")
            self.driver.get(self.config.book_url)
            time.sleep(5)  # 本の読み込み待機

            # ページ数自動検出（可能な場合）
            actual_total_pages = self._detect_total_pages()
            if actual_total_pages:
                logger.info(f"📊 総ページ数を検出: {actual_total_pages}ページ")
                max_pages = min(self.config.max_pages, actual_total_pages)
            else:
                logger.warning("⚠️ 総ページ数を自動検出できませんでした。max_pagesを使用します")
                max_pages = self.config.max_pages

            logger.info(f"🚀 キャプチャ開始（最大{max_pages}ページ）")

            page = 1
            while page <= max_pages:
                # 停止チェック
                if stop_check and stop_check():
                    logger.warning(f"⚠️ ユーザーによる中断 (ページ {page}/{max_pages})")
                    break

                # ページキャプチャ
                screenshot_path = self.output_dir / f"page_{page:04d}.png"
                self.driver.save_screenshot(str(screenshot_path))
                image_paths.append(screenshot_path)

                logger.info(f"📸 ページ {page}/{max_pages} キャプチャ完了")

                # 進捗コールバック
                if progress_callback:
                    progress_callback(page, max_pages)

                # 最終ページチェック
                if self._is_last_page():
                    logger.info(f"📚 最終ページに到達しました (ページ {page})")
                    break

                # 次のページへ
                if page < max_pages:
                    self._turn_page()
                    time.sleep(2)  # ページ読み込み待機

                page += 1

            logger.info(f"🎉 完了！{len(image_paths)}ページを保存しました: {self.output_dir}")

            return SeleniumCaptureResult(
                success=True,
                captured_pages=len(image_paths),
                image_paths=image_paths,
                actual_total_pages=actual_total_pages
            )

        except Exception as e:
            error_msg = f"予期しないエラー: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return SeleniumCaptureResult(
                success=False,
                captured_pages=len(image_paths),
                image_paths=image_paths,
                error_message=error_msg
            )

        finally:
            self.close()

    def _detect_total_pages(self) -> Optional[int]:
        """総ページ数を自動検出（Kindle Cloud Reader UI から）"""
        try:
            # Kindle Cloud Readerのページ表示要素を検索
            # 例: "123 / 456" のような表示
            wait = WebDriverWait(self.driver, 5)

            # セレクタは実際のKindle Cloud Reader UIに合わせて調整が必要
            page_indicator = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "page-number"))
            )

            text = page_indicator.text  # 例: "1 / 456"
            if "/" in text:
                total = int(text.split("/")[1].strip())
                return total

        except (TimeoutException, NoSuchElementException, ValueError):
            pass

        return None

    def _is_last_page(self) -> bool:
        """最終ページかどうかチェック"""
        try:
            # Kindle Cloud Readerの「本の終わり」要素を検出
            end_of_book = self.driver.find_elements(By.CLASS_NAME, "end-of-book")
            return len(end_of_book) > 0
        except:
            return False

    def _turn_page(self):
        """次のページへ"""
        body = self.driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ARROW_RIGHT)
        logger.debug("⏭️ ページ送り: 右矢印キー")

    def close(self):
        """WebDriver終了"""
        if self.driver:
            self.driver.quit()
            logger.info("🔚 Chrome WebDriver終了")


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = SeleniumCaptureConfig(
        book_url="https://read.amazon.com/kindle-library",  # 実際の本のURL
        book_title="プロンプトエンジニアリング入門",
        amazon_email="your-email@example.com",
        amazon_password="your-password",
        max_pages=50,
        headless=False  # デバッグ時はFalse推奨
    )

    capturer = SeleniumKindleCapture(config)

    result = capturer.capture_all_pages()

    if result.success:
        print(f"✅ 成功: {result.captured_pages}ページキャプチャ")
        if result.actual_total_pages:
            print(f"📚 実際の総ページ数: {result.actual_total_pages}")
    else:
        print(f"❌ 失敗: {result.error_message}")
