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
import hashlib  # FIX: Added for screenshot hash calculation

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

        # FIX: Comprehensive extension blocking to prevent JavaScript interference
        # REASON: Extensions like MetaMask, Pocket Universe redefine window.ethereum
        #         and intercept keyboard events, causing page turn failures
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-translate')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-component-extensions-with-background-pages')

        # FIX: Use clean Chrome profile to avoid loading user extensions
        # REASON: User profile may have extensions that --disable-extensions doesn't block
        import tempfile
        temp_user_data = tempfile.mkdtemp(prefix='chrome_selenium_')
        options.add_argument(f'--user-data-dir={temp_user_data}')
        logger.info(f"🔒 一時的なChromeプロファイルを使用: {temp_user_data}")

        # Bot検出回避のための追加オプション
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        # FIX: Disable notifications and other intrusive features
        # REASON: Prevent popups that might interfere with automation
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        options.add_experimental_option('prefs', prefs)

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

    def _calculate_screenshot_hash(self) -> str:
        """
        現在表示されているページのスクリーンショットハッシュを計算

        FIX: Page duplicate detection using MD5 hash
        REASON: Detects when page turning fails and same page is captured repeatedly

        Returns:
            str: MD5ハッシュ値
        """
        screenshot_bytes = self.driver.get_screenshot_as_png()
        return hashlib.md5(screenshot_bytes).hexdigest()

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

            # 本を開く（DRM初期化のためライブラリ経由で開く）
            logger.info(f"📖 本を開いています: {self.config.book_url}")

            # FIX: Open book through library to ensure proper DRM initialization
            # REASON: Direct ASIN URLs fail DRM handshake, causing "Something Went Wrong" error
            if not self._open_book_via_library(self.config.book_url):
                return SeleniumCaptureResult(
                    success=False,
                    captured_pages=0,
                    image_paths=[],
                    error_message="本を開けませんでした。Kindleライブラリに本が存在するか確認してください。"
                )

            # FIX: Critical - Verify book opened successfully BEFORE starting capture
            # REASON: Prevent capturing error pages when book failed to open
            logger.info("🔍 本が正常に開いたか最終確認中...")
            time.sleep(3)  # Wait for any delayed error messages to appear

            if self._check_for_kindle_error_page():
                logger.error("❌ 本を開けませんでした: Kindleエラーページが検出されました")
                logger.error("   キャプチャを開始できません")
                return SeleniumCaptureResult(
                    success=False,
                    captured_pages=0,
                    image_paths=[],
                    error_message="本を開けませんでした: Kindleエラーページが表示されています。本がライブラリに存在するか確認してください。"
                )

            logger.info("✅ 本が正常に開きました。キャプチャを開始します")

            # ページ数自動検出（可能な場合）
            actual_total_pages = self._detect_total_pages()
            if actual_total_pages:
                logger.info(f"📊 総ページ数を検出: {actual_total_pages}ページ")
                max_pages = min(self.config.max_pages, actual_total_pages)
            else:
                logger.warning("⚠️ 総ページ数を自動検出できませんでした。max_pagesを使用します")
                max_pages = self.config.max_pages

            logger.info(f"🚀 キャプチャ開始（最大{max_pages}ページ）")

            # FIX: Initialize duplicate detection variables
            # REASON: Track consecutive identical pages to detect page turning failures
            page = 1
            consecutive_same_pages = 0  # 連続同一ページカウンター
            previous_hash = None

            while page <= max_pages:
                # 停止チェック
                if stop_check and stop_check():
                    logger.warning(f"⚠️ ユーザーによる中断 (ページ {page}/{max_pages})")
                    break

                # ページキャプチャ
                screenshot_path = self.output_dir / f"page_{page:04d}.png"
                self.driver.save_screenshot(str(screenshot_path))
                image_paths.append(screenshot_path)

                # FIX: Calculate page hash for duplicate detection
                # REASON: Detect if the same page is being captured repeatedly
                current_hash = self._calculate_screenshot_hash()

                # FIX: Check if current page is identical to previous page
                # REASON: Early detection of page turning failures
                if previous_hash and current_hash == previous_hash:
                    consecutive_same_pages += 1
                    logger.warning(
                        f"⚠️ 警告: ページ {page} が前ページと同一です "
                        f"(連続{consecutive_same_pages}回目)"
                    )

                    # FIX: Stop capture if 3 consecutive identical pages detected
                    # REASON: Prevent wasting resources on duplicate captures
                    if consecutive_same_pages >= 3:
                        logger.error(
                            f"❌ エラー: 3回連続で同一ページが検出されました。"
                            f"ページめくりが機能していない可能性があります。"
                        )
                        return SeleniumCaptureResult(
                            success=False,
                            captured_pages=len(image_paths),
                            image_paths=image_paths,
                            error_message="ページめくり失敗: 3回連続で同一ページ検出"
                        )
                else:
                    # FIX: Reset counter when page changes successfully
                    # REASON: Only consecutive duplicates indicate a problem
                    consecutive_same_pages = 0

                previous_hash = current_hash

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
                    # FIX: Add retry mechanism for page turning with verification
                    # REASON: Ensure page actually changes before continuing
                    turn_success = False
                    for retry in range(3):  # 最大3回リトライ
                        try:
                            logger.debug(f"🔄 ページめくり試行 {retry + 1}/3 (ページ {page} → {page + 1})")
                            self._turn_page()

                            # FIX: Increased wait time from 2s to 4s for slow page loads
                            # REASON: Kindle Cloud Reader may take time to render new page
                            #         especially with images or slow network
                            time.sleep(4)  # ページ読み込み待機（2秒→4秒に増加）

                            # FIX: Verify page changed after turning
                            # REASON: Immediate detection of failed page turn
                            new_hash = self._calculate_screenshot_hash()
                            if new_hash != current_hash:
                                turn_success = True
                                logger.debug(f"✅ ページめくり成功 (試行 {retry + 1}/3)")
                                break
                            else:
                                logger.warning(
                                    f"⚠️ ページめくり失敗 (リトライ {retry + 1}/3) - "
                                    f"ページハッシュが変化していません"
                                )
                                if retry < 2:  # 最後のリトライでない場合
                                    time.sleep(2)  # 追加待機（1秒→2秒に増加）
                        except Exception as turn_error:
                            logger.error(f"❌ ページめくり中にエラー (試行 {retry + 1}/3): {turn_error}")
                            if retry < 2:
                                time.sleep(2)
                            continue

                    if not turn_success:
                        logger.error(f"❌ ページめくりが3回失敗しました (ページ {page})")
                        logger.error(f"   デバッグ情報: 現在のURL = {self.driver.current_url}")
                        logger.error(f"   デバッグ情報: ページタイトル = {self.driver.title}")
                        # FIX: Stop capture after repeated page turn failures
                        # REASON: Continuing would only create more duplicates
                        return SeleniumCaptureResult(
                            success=False,
                            captured_pages=len(image_paths),
                            image_paths=image_paths,
                            error_message=f"ページめくり失敗: ページ {page} で3回連続失敗。ブラウザ拡張機能を無効化するか、ネットワーク接続を確認してください。"
                        )

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

    def _extract_asin_from_url(self, url: str) -> Optional[str]:
        """
        KindleブックURLからASINを抽出

        Args:
            url: Kindle本のURL

        Returns:
            Optional[str]: ASIN、抽出失敗時はNone
        """
        import re

        # URLパターン: https://read.amazon.co.jp/?asin=B0FPDT572W&...
        # または: https://read.amazon.co.jp/kindle-library/B0FPDT572W
        patterns = [
            r'[?&]asin=([A-Z0-9]{10})',  # Query parameter
            r'/([A-Z0-9]{10})(?:[/?#]|$)',  # Path segment
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                asin = match.group(1)
                logger.info(f"📚 ASIN extracted: {asin}")
                return asin

        logger.error(f"❌ ASINの抽出に失敗しました: {url}")
        return None

    def _check_for_kindle_error_page(self) -> bool:
        """
        Kindleエラーページが表示されているかチェック

        FIX: Enhanced error detection with screenshot logging
        REASON: Better debugging and immediate error detection

        Returns:
            bool: エラーページが表示されている場合True
        """
        try:
            # エラーダイアログの検出（複数パターン）
            error_indicators = [
                (By.XPATH, "//*[contains(text(), 'Something Went Wrong')]"),
                (By.XPATH, "//*[contains(text(), 'Oops')]"),
                (By.XPATH, "//*[contains(text(), 'try to open this book from the library')]"),
                (By.XPATH, "//*[contains(text(), '何か問題が発生しました')]"),  # Japanese error message
                (By.CLASS_NAME, "error-dialog"),
                (By.ID, "kindleReaderError"),
            ]

            for by, selector in error_indicators:
                try:
                    elements = self.driver.find_elements(by, selector)
                    if elements and len(elements) > 0:
                        logger.error(f"❌ Kindleエラーページを検出: {selector}")

                        # FIX: Save error screenshot for debugging
                        # REASON: Helps diagnose why book failed to open
                        try:
                            error_screenshot_path = self.output_dir / "kindle_error.png"
                            self.driver.save_screenshot(str(error_screenshot_path))
                            logger.error(f"📸 エラースクリーンショット保存: {error_screenshot_path}")
                        except Exception as screenshot_error:
                            logger.warning(f"⚠️ エラースクリーンショット保存失敗: {screenshot_error}")

                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.warning(f"⚠️ エラーページチェック中に例外: {e}")
            return False

    def _open_book_via_library(self, book_url: str) -> bool:
        """
        Kindleライブラリ経由で本を開く（DRM初期化のため）

        FIX: Proper DRM initialization through library access with retry and better error handling
        REASON: Direct ASIN URL fails with "Something Went Wrong" error

        Args:
            book_url: 本のURL（ASINを含む）

        Returns:
            bool: 成功した場合True
        """
        try:
            # Step 1: ASINを抽出
            asin = self._extract_asin_from_url(book_url)
            if not asin:
                logger.error("❌ URLからASINを抽出できませんでした")
                logger.error(f"   提供されたURL: {book_url}")
                logger.error("   正しい形式: https://read.amazon.co.jp/?asin=B0FPDT572W")
                return False

            # FIX: Validate login state before accessing library
            # REASON: Expired cookies cause immediate "Something Went Wrong" error
            logger.info("🔐 ログイン状態を確認しています...")
            self.driver.get("https://www.amazon.co.jp")
            time.sleep(2)

            # Check if we're logged in by looking for account element
            try:
                account_element = self.driver.find_element(By.ID, "nav-link-accountList")
                logger.info("✅ ログイン状態: 有効")
            except NoSuchElementException:
                logger.warning("⚠️ ログイン状態が無効です。Cookie再認証を試行します...")
                # Try to re-login
                if not self.login_amazon():
                    logger.error("❌ 再ログインに失敗しました")
                    return False

            # Step 2: Kindleライブラリにアクセス
            logger.info("📚 Kindleライブラリにアクセスしています...")
            self.driver.get("https://read.amazon.co.jp/kindle-library")
            time.sleep(8)  # FIX: Increased from 5s to 8s for full library load
            # REASON: Library page loads books dynamically, needs more time

            # FIX: Dismiss Kindle for Web terms agreement popup if present
            # REASON: First-time access shows terms agreement dialog that blocks interaction
            try:
                logger.info("🔍 規約同意ポップアップをチェックしています...")
                wait = WebDriverWait(self.driver, 5)

                # Try multiple strategies to find and click the OK button
                button_found = False

                # Strategy 1: Text-based selectors (case-insensitive)
                button_selectors = [
                    (By.XPATH, "//button[contains(translate(text(), 'OK', 'ok'), 'ok')]"),
                    (By.XPATH, "//button[contains(text(), 'OK')]"),
                    (By.XPATH, "//button[contains(text(), 'Ok')]"),
                    (By.XPATH, "//button[contains(text(), 'ok')]"),
                    (By.XPATH, "//button[contains(text(), '承諾')]"),
                    (By.CSS_SELECTOR, "button[class*='dialog'] button"),
                    (By.CSS_SELECTOR, "[role='dialog'] button"),
                    (By.CSS_SELECTOR, "button"),  # Last resort: any button
                ]

                for by, selector in button_selectors:
                    try:
                        ok_button = wait.until(EC.element_to_be_clickable((by, selector)))
                        # Verify button text contains OK-like text
                        button_text = ok_button.text.lower()
                        if 'ok' in button_text or '承諾' in button_text or button_text == '':
                            ok_button.click()
                            logger.info(f"✅ 規約同意ポップアップを閉じました (selector: {selector})")
                            button_found = True
                            time.sleep(2)  # Wait for dialog to close
                            break
                    except (TimeoutException, NoSuchElementException):
                        continue
                    except Exception as click_error:
                        logger.debug(f"   ボタンクリック試行失敗: {click_error}")
                        continue

                if not button_found:
                    logger.debug("   規約同意ポップアップは表示されていません（正常）")

            except Exception as popup_error:
                logger.debug(f"   ポップアップ処理エラー（無視可能）: {popup_error}")

            # FIX: Check if library page loaded successfully
            # REASON: Sometimes redirects to login if cookies expired
            current_url = self.driver.current_url.lower()
            if "signin" in current_url or "ap/mfa" in current_url:
                logger.error("❌ ライブラリアクセス失敗: ログインページにリダイレクトされました")
                logger.error("   Cookieが無効になっている可能性があります")
                return False

            # Step 3: ライブラリ内で本を検索してクリック
            # FIX: Enhanced book finding with debugging and multiple strategies
            # REASON: Original selectors didn't match Kindle library HTML structure
            logger.info(f"🔍 ライブラリ内で本を検索: ASIN={asin}")

            # FIX: Save library page screenshot for debugging
            # REASON: Helps identify why book isn't found
            try:
                library_screenshot_path = self.output_dir / "kindle_library_debug.png"
                self.driver.save_screenshot(str(library_screenshot_path))
                logger.info(f"📸 ライブラリページスクリーンショット保存: {library_screenshot_path}")
            except Exception as screenshot_error:
                logger.warning(f"⚠️ ライブラリスクリーンショット保存失敗: {screenshot_error}")

            # FIX: Log all book links found on the page for debugging
            # REASON: Helps understand the actual HTML structure
            try:
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                kindle_links = [link.get_attribute("href") for link in all_links if link.get_attribute("href") and "asin" in link.get_attribute("href").lower()]
                logger.info(f"📚 ライブラリ内で発見されたKindle本リンク数: {len(kindle_links)}")
                if kindle_links:
                    logger.info(f"   最初の3件の例: {kindle_links[:3]}")
                    # Check if our ASIN is in any of these links
                    matching_links = [link for link in kindle_links if asin.lower() in link.lower()]
                    if matching_links:
                        logger.info(f"✅ ASIN {asin} を含むリンクを発見: {len(matching_links)}件")
                    else:
                        logger.warning(f"⚠️ ASIN {asin} を含むリンクが見つかりません")
            except Exception as debug_error:
                logger.warning(f"⚠️ デバッグ情報取得失敗: {debug_error}")

            # Method 1: ASINを含むリンクを探す（改善版）
            # FIX: More comprehensive selectors based on actual Kindle library structure
            # REASON: Original selectors were too generic and didn't match
            book_link_selectors = [
                # Kindle Cloud Reader specific selectors
                (By.CSS_SELECTOR, f"a[href*='read.amazon'][href*='{asin}']"),
                (By.CSS_SELECTOR, f"a[href*='kindle'][href*='{asin}']"),
                (By.XPATH, f"//a[contains(@href, 'read.amazon') and contains(@href, '{asin}')]"),
                (By.XPATH, f"//a[contains(@href, '{asin}') and contains(@href, 'ref_')]"),
                # Generic fallbacks
                (By.CSS_SELECTOR, f"a[href*='{asin}']"),
                (By.XPATH, f"//a[contains(@href, '{asin}')]"),
            ]

            book_found = False
            for by, selector in book_link_selectors:
                try:
                    logger.debug(f"   試行中: {selector}")
                    wait = WebDriverWait(self.driver, 5)  # Reduced to 5s per selector
                    book_link = wait.until(EC.element_to_be_clickable((by, selector)))
                    logger.info(f"✅ 本が見つかりました: {selector}")
                    logger.info(f"   リンクURL: {book_link.get_attribute('href')}")
                    book_link.click()
                    book_found = True
                    break
                except TimeoutException:
                    logger.debug(f"   リンク検索失敗（次を試行）: {selector}")
                    continue
                except Exception as click_error:
                    logger.warning(f"   クリック失敗: {click_error}")
                    continue

            # FIX: Remove dangerous fallback to direct URL
            # REASON: Direct ASIN URLs cause "Something Went Wrong" error
            if not book_found:
                logger.error("❌ ライブラリ内で本が見つかりませんでした")
                logger.error("")
                logger.error("   考えられる原因:")
                logger.error(f"   1. ASIN {asin} の本がこのAmazonアカウントのライブラリに存在しない")
                logger.error("   2. 本が購入済みでない、またはKindle Unlimitedで現在借りていない")
                logger.error("   3. 本が別のAmazonアカウントで購入されている")
                logger.error("   4. Kindleライブラリのページ構造が変更された")
                logger.error("")
                logger.error("📋 解決方法:")
                logger.error("   1. https://www.amazon.co.jp/hz/mycd/digital-console/contentlist/booksAll にアクセス")
                logger.error("   2. 本のタイトルを検索して、Kindleライブラリに存在するか確認")
                logger.error("   3. 本を「今すぐ読む」でKindle Cloud Readerで手動で開く")
                logger.error("   4. URLバーから完全なURLをコピー（例: https://read.amazon.co.jp/?asin=...）")
                logger.error("   5. そのURLをこのツールに入力してください")
                logger.error("")
                logger.error(f"   デバッグ用スクリーンショット: {self.output_dir / 'kindle_library_debug.png'}")
                return False

            # Step 4: 本の読み込み待機
            logger.info("⏳ 本の読み込みを待機しています...")
            time.sleep(8)  # DRM初期化とレンダリングのための待機時間を増加

            # Step 5: エラーページチェック
            if self._check_for_kindle_error_page():
                logger.error("❌ 本を開けませんでした: Kindleエラーページが表示されています")
                logger.error("   考えられる原因:")
                logger.error("   1. 本がKindleライブラリに存在しない（購入していない本）")
                logger.error("   2. DRMライセンスが無効（デバイス制限に達している）")
                logger.error("   3. ネットワークエラー（Amazonサーバーに接続できない）")
                logger.error("   4. 本が別のAmazonアカウントで購入されている")
                logger.error(f"   現在のURL: {self.driver.current_url}")
                logger.error(f"   ASIN: {asin}")

                # FIX: Provide actionable solution
                # REASON: Help user understand what to do next
                logger.error("")
                logger.error("📋 解決方法:")
                logger.error("   1. https://www.amazon.co.jp/hz/mycd/digital-console/contentlist/booksAll にアクセス")
                logger.error("   2. 本のタイトルを検索して、Kindleライブラリに存在するか確認")
                logger.error("   3. 本を「今すぐ読む」でKindle Cloud Readerで開く")
                logger.error("   4. URLバーからASINを含む完全なURLをコピー")
                logger.error("   5. そのURLをこのツールに入力してください")
                logger.error("")
                return False

            # Step 6: 本が正常に読み込まれたか確認
            current_url = self.driver.current_url.lower()
            if "read.amazon" in current_url and asin.lower() in current_url:
                logger.info("✅ 本が正常に開きました")
                return True
            else:
                logger.warning(f"⚠️ 本が開いたか不明です (URL: {current_url})")
                # エラーページでなければ成功とみなす
                return not self._check_for_kindle_error_page()

        except Exception as e:
            logger.error(f"❌ ライブラリ経由での本オープンエラー: {e}", exc_info=True)
            return False

    def _detect_total_pages(self) -> Optional[int]:
        """
        総ページ数を自動検出（Kindle Cloud Reader UIから）

        検出方法（優先順位順）:
        1. ページインジケーター要素から取得 ("Page 1 of 258")
        2. JavaScript経由でKindle Readerオブジェクトから取得
        3. プログレスバーのaria-valuemaxから取得

        Returns:
            Optional[int]: 検出された総ページ数、失敗時はNone
        """
        import re

        # 方法1: ページインジケーター ("Page 1 of 258" or "1 / 258")
        try:
            wait = WebDriverWait(self.driver, 5)

            # Try multiple selectors for page indicator
            selectors = [
                (By.ID, "kr-page-indicator"),
                (By.CLASS_NAME, "page-number"),
                (By.CSS_SELECTOR, "[aria-label*='page']"),
                (By.CSS_SELECTOR, ".page-info"),
            ]

            for by, selector in selectors:
                try:
                    page_indicator = wait.until(
                        EC.presence_of_element_located((by, selector))
                    )
                    text = page_indicator.text
                    logger.info(f"📊 Page indicator found: '{text}'")

                    # Match various formats: "Page 1 of 258", "1 / 258", "1/258", "ページ 1 / 258"
                    patterns = [
                        r'of\s+(\d+)',      # "of 258"
                        r'/\s*(\d+)',       # "/ 258" or "/258"
                        r'全\s*(\d+)',      # Japanese: "全258"
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            total_pages = int(match.group(1))
                            logger.info(f"✅ Total pages detected (indicator): {total_pages}")
                            return total_pages

                except (TimeoutException, NoSuchElementException):
                    continue

        except Exception as e:
            logger.warning(f"⚠️ Page indicator detection failed: {e}")

        # 方法2: JavaScript経由でKindle Readerオブジェクトから取得
        try:
            # Try various JavaScript methods to get page count
            js_methods = [
                "return window.KindleReader?.reader?.getNumberOfPages();",
                "return window.KindleReader?.getNumberOfPages();",
                "return document.querySelector('[aria-valuemax]')?.getAttribute('aria-valuemax');",
            ]

            for js_code in js_methods:
                try:
                    result = self.driver.execute_script(js_code)
                    if result:
                        total_pages = int(result)
                        logger.info(f"✅ Total pages detected (JavaScript): {total_pages}")
                        return total_pages
                except Exception:
                    continue

        except Exception as e:
            logger.warning(f"⚠️ JavaScript detection failed: {e}")

        # 方法3: プログレスバーのaria-valuemaxから取得
        try:
            progress_selectors = [
                (By.CSS_SELECTOR, "[role='progressbar']"),
                (By.CSS_SELECTOR, "input[type='range']"),
                (By.CSS_SELECTOR, ".progress-bar"),
            ]

            for by, selector in progress_selectors:
                try:
                    progress_element = self.driver.find_element(by, selector)
                    max_value = progress_element.get_attribute("aria-valuemax")
                    if max_value:
                        total_pages = int(max_value)
                        logger.info(f"✅ Total pages detected (progress bar): {total_pages}")
                        return total_pages
                except (NoSuchElementException, ValueError):
                    continue

        except Exception as e:
            logger.warning(f"⚠️ Progress bar detection failed: {e}")

        logger.warning("⚠️ Could not detect total pages from Kindle Cloud Reader")
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
        """
        次のページへ（複数の方法を試行）

        FIX: Improved page turning with multiple fallback strategies
        REASON: Single arrow key method was unreliable due to focus/extension issues

        Strategies (in order):
        1. JavaScript click on next page button (most reliable)
        2. Arrow key to body element (original method)
        3. Arrow key with explicit focus (fallback)
        """
        try:
            # Strategy 1: Try JavaScript click on next page button (most reliable)
            # Kindle Cloud Reader uses various selectors for the next button
            js_click_selectors = [
                "document.querySelector('.navBar-button-next')?.click()",
                "document.querySelector('[aria-label=\"Next Page\"]')?.click()",
                "document.querySelector('[aria-label=\"次のページ\"]')?.click()",
                "document.querySelector('#kindleReader_pageTurnAreaRight')?.click()",
                "document.querySelector('.kr-right-pageTurn')?.click()",
            ]

            for js_code in js_click_selectors:
                try:
                    result = self.driver.execute_script(js_code)
                    if result is not False:  # Click succeeded
                        logger.debug("⏭️ ページ送り: JavaScript click")
                        return
                except Exception:
                    continue

            # Strategy 2: Original arrow key method
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.ARROW_RIGHT)
            logger.debug("⏭️ ページ送り: 右矢印キー")

        except Exception as e:
            # Strategy 3: Fallback - try to focus explicitly then send key
            logger.warning(f"⚠️ ページ送りエラー、フォールバック試行: {e}")
            try:
                # Focus on the reader container
                self.driver.execute_script("document.activeElement.blur(); document.body.focus();")
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ARROW_RIGHT)
                logger.debug("⏭️ ページ送り: フォーカス後の右矢印キー")
            except Exception as fallback_error:
                logger.error(f"❌ ページ送り完全失敗: {fallback_error}")
                raise

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
