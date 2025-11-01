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
import json
import pickle
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
    headless: bool = False  # デフォルトをFalseに変更（初回は手動2FA認証）
    output_dir: Optional[Path] = None
    cookies_file: Optional[Path] = None  # Cookie保存ファイルパス


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

    # Cookieファイル保存ディレクトリ（クラス変数）
    COOKIES_DIR = Path(".amazon_cookies")

    def __init__(self, config: SeleniumCaptureConfig):
        self.config = config

        # 出力ディレクトリ設定
        if config.output_dir is None:
            self.output_dir = Path(f"captures/{config.book_title}")
        else:
            self.output_dir = config.output_dir

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cookie保存ファイルパス設定
        if config.cookies_file is None:
            self.COOKIES_DIR.mkdir(exist_ok=True)
            self.cookies_file = self.COOKIES_DIR / f"amazon_{config.amazon_email.replace('@', '_at_')}.pkl"
        else:
            self.cookies_file = config.cookies_file

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

        # Bot検出回避のための追加オプション
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # User-Agent（Kindleが正常に動作するため）
        options.add_argument(
            'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )

        # WebDriver起動
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Bot検出対策: webdriver プロパティを隠す
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        logger.info(f"✅ Chrome WebDriver起動 (ヘッドレス: {self.config.headless})")
        return driver

    def _save_cookies(self) -> None:
        """現在のCookieをファイルに保存"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"💾 Cookieを保存しました: {self.cookies_file}")
        except Exception as e:
            logger.error(f"❌ Cookie保存エラー: {e}")

    def _load_cookies(self) -> bool:
        """保存されたCookieをロード"""
        try:
            if not self.cookies_file.exists():
                logger.info("📂 保存されたCookieが見つかりません")
                return False

            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)

            # Amazonのドメインにアクセスしてからcookieを設定
            self.driver.get("https://www.amazon.co.jp")
            time.sleep(2)

            for cookie in cookies:
                try:
                    # expiryが存在しない、または文字列の場合は削除
                    if 'expiry' in cookie:
                        if isinstance(cookie['expiry'], str) or cookie['expiry'] < 0:
                            del cookie['expiry']
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"⚠️ Cookie追加スキップ: {e}")
                    continue

            logger.info("🍪 保存されたCookieをロードしました")
            return True
        except Exception as e:
            logger.error(f"❌ Cookie読み込みエラー: {e}")
            return False

    def _wait_for_manual_2fa(self, timeout: int = 180) -> bool:
        """
        2段階認証の手動入力を待機（最大3分）

        Args:
            timeout: タイムアウト時間（秒）

        Returns:
            bool: ログイン成功したかどうか
        """
        logger.info("=" * 60)
        logger.info("🔐 2段階認証コードの入力を待機しています")
        logger.info("=" * 60)
        logger.info("📱 SMS/メールで届いた6桁のコードをブラウザに入力してください")
        logger.info(f"⏱️  タイムアウト: {timeout}秒 (約{timeout//60}分)")
        logger.info("=" * 60)

        start_time = time.time()
        check_interval = 2  # 2秒ごとにチェック
        last_log_time = start_time

        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url.lower()
            except Exception as e:
                logger.error(f"   ❌ URLの取得に失敗: {e}")
                return False

            elapsed = int(time.time() - start_time)

            # 10秒ごとに経過時間とURLをログ出力（デバッグ用）
            if time.time() - last_log_time >= 10:
                remaining = timeout - elapsed
                logger.info(f"⏳ 待機中... 経過時間: {elapsed}秒 / 残り: {remaining}秒")
                logger.info(f"   現在のURL: {current_url}")
                last_log_time = time.time()

            # ログイン成功を示すURLパターン（ポジティブチェック）
            success_patterns = [
                "amazon.co.jp/?",           # トップページ
                "amazon.co.jp/ref=",        # トップページ（リファラー付き）
                "kindle-dbs.amazon.co.jp",  # Kindleライブラリ
                "/gp/your-account",         # アカウントページ
            ]

            # これらのパターンに一致したらログイン成功
            is_success = any(pattern in current_url for pattern in success_patterns)

            # amazon.co.jp/? で始まるURLも成功とみなす（クエリパラメータ付き）
            if "amazon.co.jp" in current_url and "?" in current_url:
                # amazon.co.jp の直後に ? がある場合（トップページ）
                if current_url.find("amazon.co.jp") + len("amazon.co.jp") < current_url.find("?"):
                    # パス部分が / だけの場合はトップページ
                    start_idx = current_url.find("amazon.co.jp") + len("amazon.co.jp")
                    end_idx = current_url.find("?")
                    path = current_url[start_idx:end_idx]
                    if path == "" or path == "/":
                        is_success = True

            # さらに安全策：ログイン関連URLでない かつ amazon.co.jp ドメイン内
            # URLパスで判定（クエリパラメータは除外）
            url_path = current_url.split('?')[0]
            login_patterns = ["/ap/signin", "/ap/mfa", "/ap/cvf", "/ap/challenge", "/auth-mfa", "/ap/"]
            is_still_login_page = any(pattern in url_path for pattern in login_patterns)

            # ログイン成功判定：成功パターンに一致 または ログインページでなくなった
            if is_success or (not is_still_login_page and "amazon.co.jp" in current_url and elapsed > 10):
                logger.info("=" * 60)
                logger.info("✅ 2段階認証完了！ログインに成功しました")
                logger.info(f"   最終URL: {current_url}")
                logger.info("=" * 60)
                return True

            time.sleep(check_interval)

        logger.error("=" * 60)
        logger.error(f"❌ 2段階認証タイムアウト（{timeout}秒経過）")
        logger.error("   時間内にコードを入力できませんでした")
        logger.error("=" * 60)
        return False

    def login_amazon(self) -> bool:
        """
        Amazon自動ログイン（Cookie再利用 + 2段階認証対応）

        Returns:
            bool: ログイン成功したかどうか
        """
        try:
            logger.info("🔐 Amazonログイン開始...")

            # 1. 保存されたCookieでログイン試行
            if self._load_cookies():
                self.driver.get("https://www.amazon.co.jp")
                time.sleep(3)

                # ログイン状態確認（URLパスで判定）
                current_url = self.driver.current_url.lower()
                url_path = current_url.split('?')[0]
                if "/ap/signin" not in url_path and "/ap/mfa" not in url_path:
                    logger.info("✅ Cookie認証成功（ログイン不要）")
                    return True
                else:
                    logger.info("⚠️ Cookieが無効です。通常ログインを実行します")

            # 2. 通常のログインフロー
            # Amazonトップページにアクセスして、ログインリンクをクリック
            self.driver.get("https://www.amazon.co.jp")
            time.sleep(5)  # Bot検出回避のため、ページ読み込みを十分に待機

            # WebDriverWaitを最初に定義（Bot検出回避のため待機時間を延長）
            wait = WebDriverWait(self.driver, 15)

            try:
                # ログインリンクを探してクリック
                login_link = wait.until(
                    EC.element_to_be_clickable((By.ID, "nav-link-accountList"))
                )
                login_link.click()
                logger.info("   ログインリンクをクリックしました")
                time.sleep(3)
            except Exception as e:
                logger.warning(f"   ログインリンククリックに失敗: {e}")
                # 直接ログインページにアクセス
                self.driver.get("https://www.amazon.co.jp/ap/signin")
                time.sleep(3)

            logger.info(f"   現在のURL: {self.driver.current_url}")

            # メールアドレス入力 - NAMEを優先的にチェック
            email_field = None

            # 1. NAME="email"を試す（最も一般的）
            try:
                email_field = wait.until(
                    EC.presence_of_element_located((By.NAME, "email"))
                )
                logger.info("   📧 メール入力欄検出: NAME=email")
            except TimeoutException:
                # 2. ID="ap_email"や"email"を試す
                for selector in ["ap_email", "email"]:
                    try:
                        email_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, selector))
                        )
                        logger.info(f"   📧 メール入力欄検出: ID={selector}")
                        break
                    except TimeoutException:
                        continue

            if not email_field:
                logger.error("❌ メールアドレス入力欄が見つかりません")
                return False

            email_field.clear()
            email_field.send_keys(self.config.amazon_email)
            email_field.send_keys(Keys.RETURN)
            logger.info("   📧 メールアドレス入力完了")
            time.sleep(5)  # ページ遷移を待機

            # パスキーダイアログ（/ax/claim）をスキップする
            try:
                # ウィンドウが開いているか確認
                try:
                    current_url = self.driver.current_url
                    logger.info(f"   🔍 メール送信後のURL確認: {current_url}")
                except Exception as window_error:
                    logger.error(f"   ❌ ブラウザウィンドウが閉じています: {window_error}")
                    return False

                # パスキーダイアログのURLを検出（/ax/claimパスで判定）
                if "/ax/claim" in current_url:
                    logger.info("   🔐 パスキーダイアログページを検出しました")
                    logger.info("   🔄 パスキーダイアログを自動的にスキップしています...")

                    # 「別のEメールアドレスまたは携帯電話でサインインする」リンクをクリック
                    skip_successful = False
                    try:
                        # クラス名で検索
                        skip_link = wait.until(
                            EC.element_to_be_clickable((By.CLASS_NAME, "signin-with-another-account"))
                        )
                        skip_link.click()
                        logger.info("   ✅ パスキーダイアログをスキップしました")
                        skip_successful = True
                        time.sleep(3)  # ページ遷移を待機
                    except Exception as e:
                        logger.warning(f"   ⚠️  クラス名でのスキップに失敗: {e}")

                        # フォールバック: リンクテキストで検索
                        try:
                            skip_link = wait.until(
                                EC.element_to_be_clickable((By.LINK_TEXT, "別のEメールアドレスまたは携帯電話でサインインする"))
                            )
                            skip_link.click()
                            logger.info("   ✅ パスキーダイアログをスキップしました (リンクテキスト)")
                            skip_successful = True
                            time.sleep(3)
                        except Exception as e2:
                            logger.error(f"   ❌ リンクテキストでのスキップも失敗: {e2}")

                    if skip_successful:
                        # ページ遷移を確認
                        try:
                            final_url = self.driver.current_url
                            logger.info(f"   🔍 スキップ後のURL: {final_url}")
                            # パスキーページから抜けたか確認（/ax/claimパスがなくなったか）
                            if "/ax/claim" not in final_url:
                                logger.info("   ✅ パスキーページから正常に移動しました")
                            else:
                                logger.warning("   ⚠️  まだパスキーページにいます")
                        except Exception:
                            logger.error("   ❌ ブラウザウィンドウが閉じられました")
                            return False
                else:
                    logger.info("   ℹ️  パスキーダイアログは表示されませんでした")

            except Exception as e:
                logger.warning(f"   ⚠️  パスキーダイアログ処理でエラー: {e}")
                # エラーが出てもログインは継続

            # パスワード入力
            password_field = None

            # 1. NAME="password"を試す
            try:
                password_field = wait.until(
                    EC.presence_of_element_located((By.NAME, "password"))
                )
                logger.info("   🔑 パスワード入力欄検出: NAME=password")
            except TimeoutException:
                # 2. ID="ap_password"や"password"を試す
                for selector in ["ap_password", "password"]:
                    try:
                        password_field = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, selector))
                        )
                        logger.info(f"   🔑 パスワード入力欄検出: ID={selector}")
                        break
                    except TimeoutException:
                        continue

            if not password_field:
                logger.error("❌ パスワード入力欄が見つかりません")
                return False

            password_field.clear()
            password_field.send_keys(self.config.amazon_password)
            password_field.send_keys(Keys.RETURN)
            logger.info("   🔑 パスワード入力完了")

            # パスワード送信後、ページ遷移を待機（最大15秒）
            logger.info("   ⏳ ログイン処理中... ページ遷移を待機しています")
            time.sleep(3)  # 初期待機

            # 3. ログイン状態確認と2FA処理
            # 2FAページへの遷移を確実に検出するため、複数回チェック
            max_checks = 6  # 最大12秒待機（2秒 × 6回）
            is_2fa_page = False

            for check_count in range(max_checks):
                current_url = self.driver.current_url.lower()
                logger.info(f"   [{check_count + 1}/{max_checks}] 現在のURL: {current_url}")

                # 2段階認証ページに遷移した場合
                # Amazon.co.jpでは様々なURLパターンがある
                is_2fa_page = any(pattern in current_url for pattern in [
                    "ap/mfa",
                    "ap/cvf",
                    "ap/challenge",
                    "auth-mfa",
                    "verify"
                ])

                logger.info(f"   2FA判定: {is_2fa_page}")

                if is_2fa_page:
                    # 2FAページを検出した
                    break

                # ログイン成功（2FAなし）
                # URLパスに含まれるパターンで判定（クエリパラメータを除外）
                url_path = current_url.split('?')[0]  # クエリパラメータを除去
                login_patterns = ["/ap/signin", "/ap/mfa", "/ap/cvf", "/ap/challenge", "/auth-mfa", "/verify"]
                is_still_login_page = any(pattern in url_path for pattern in login_patterns)

                if not is_still_login_page:
                    # ログイン成功（2FA不要だった）
                    logger.info("   ✅ 2FA不要 - ログイン完了")
                    break

                # まだ遷移中の可能性があるので待機
                time.sleep(2)

            if is_2fa_page:
                logger.info("🔐 2段階認証が必要です")
                if not self.config.headless:
                    # ヘッドレス無効時は手動入力を待機
                    if not self._wait_for_manual_2fa():
                        return False
                else:
                    logger.error("❌ ヘッドレスモードでは2段階認証に対応できません")
                    logger.error("   headless=Falseに設定して再実行してください")
                    return False

            # ログイン成功確認
            current_url = self.driver.current_url.lower()

            # ログイン関連のURLパターン（URLパスのみで判定、クエリパラメータは除外）
            url_path = current_url.split('?')[0]  # クエリパラメータを除去
            login_patterns = ["/ap/signin", "/ap/mfa", "/ap/cvf", "/ap/challenge", "/auth-mfa", "/verify"]
            is_still_login_page = any(pattern in url_path for pattern in login_patterns)

            logger.info(f"   ログイン完了判定 - URL: {current_url}")
            logger.info(f"   URLパス: {url_path}")
            logger.info(f"   ログインページ判定: {is_still_login_page}")

            if not is_still_login_page:
                logger.info("✅ Amazonログイン成功")

                # 4. Cookie保存
                self._save_cookies()
                return True
            else:
                logger.error("❌ Amazonログイン失敗")
                logger.error(f"   最終URL: {current_url}")
                return False

        except TimeoutException as e:
            logger.error(f"❌ Amazonログインタイムアウト: {e}")
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
