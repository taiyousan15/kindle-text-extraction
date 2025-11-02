#!/usr/bin/env python3
"""
要素検出失敗の詳細デバッグテスト
Amazon ログイン自動化でどこが失敗しているかを特定する
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

def save_debug_info(driver, step_name, output_dir="/tmp/selenium_debug"):
    """デバッグ情報を保存（スクリーンショット、ページソース、URL）"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time())

    # スクリーンショット保存
    screenshot_path = f"{output_dir}/{timestamp}_{step_name}.png"
    driver.save_screenshot(screenshot_path)
    print(f"   📸 スクリーンショット保存: {screenshot_path}")

    # ページソース保存
    source_path = f"{output_dir}/{timestamp}_{step_name}_source.html"
    with open(source_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"   📄 ページソース保存: {source_path}")

    # URL記録
    print(f"   🔗 現在のURL: {driver.current_url}")

def test_element_detection_debug():
    """要素検出のデバッグテスト"""

    print("=" * 80)
    print("要素検出失敗の詳細デバッグテスト")
    print("=" * 80)

    # Chrome オプション設定
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Bot検出を回避するための追加オプション
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # User-Agent を通常のブラウザに設定
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

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

    try:
        # ステップ1: Amazonトップページにアクセス
        print("\n[1/6] Amazon.co.jp にアクセス中...")
        driver.get("https://www.amazon.co.jp")
        time.sleep(5)  # 通常より長く待機

        save_debug_info(driver, "01_amazon_top")

        # ページタイトル確認
        print(f"   ページタイトル: {driver.title}")

        # Bot検出チェック（CAPTCHAページかどうか）
        if "Robot Check" in driver.title or "captcha" in driver.current_url.lower():
            print("   ⚠️  Bot検出されました（CAPTCHA表示）")
            save_debug_info(driver, "01_bot_detected")

        # ステップ2: ログインリンクを探す
        print("\n[2/6] ログインリンクの検出を試行中...")
        wait = WebDriverWait(driver, 15)

        login_link = None

        # 試行1: ID="nav-link-accountList"
        print("   試行1: ID='nav-link-accountList' を検索...")
        try:
            login_link = wait.until(
                EC.element_to_be_clickable((By.ID, "nav-link-accountList"))
            )
            print("   ✅ ログインリンク発見（ID='nav-link-accountList'）")
        except TimeoutException:
            print("   ❌ ID='nav-link-accountList' が見つかりません")

            # 試行2: 他の可能性のあるセレクタ
            alternative_selectors = [
                ("ID", "nav-link-accountList-nav-line-1"),
                ("CLASS_NAME", "nav-line-1-container"),
                ("XPATH", "//a[contains(@class, 'nav-a') and contains(., 'ログイン')]"),
                ("XPATH", "//span[contains(text(), 'ログイン')]"),
            ]

            for selector_type, selector in alternative_selectors:
                print(f"   試行: {selector_type}='{selector}' を検索...")
                try:
                    if selector_type == "ID":
                        login_link = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.ID, selector))
                        )
                    elif selector_type == "CLASS_NAME":
                        login_link = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CLASS_NAME, selector))
                        )
                    elif selector_type == "XPATH":
                        login_link = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )

                    if login_link:
                        print(f"   ✅ ログインリンク発見（{selector_type}='{selector}'）")
                        break
                except TimeoutException:
                    print(f"   ❌ {selector_type}='{selector}' が見つかりません")
                    continue

        if not login_link:
            print("\n   ❌ どの方法でもログインリンクが見つかりませんでした")
            save_debug_info(driver, "02_login_link_not_found")

            # フォールバック: 直接ログインページにアクセス
            print("\n   🔄 直接ログインページにアクセスします...")
            driver.get("https://www.amazon.co.jp/ap/signin")
            time.sleep(5)
            save_debug_info(driver, "02_direct_login_page")
        else:
            # ログインリンクをクリック
            print("\n[3/6] ログインリンクをクリック中...")
            login_link.click()
            time.sleep(5)
            save_debug_info(driver, "03_after_login_click")

        # ステップ3: メールアドレス入力欄を探す
        print("\n[4/6] メールアドレス入力欄の検出を試行中...")

        email_field = None

        # 試行1: NAME="email"
        print("   試行1: NAME='email' を検索...")
        try:
            email_field = wait.until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            print("   ✅ メール入力欄発見（NAME='email'）")
        except TimeoutException:
            print("   ❌ NAME='email' が見つかりません")

            # 試行2: 他のセレクタ
            alternative_email_selectors = [
                ("ID", "ap_email"),
                ("ID", "email"),
                ("NAME", "email"),
                ("XPATH", "//input[@type='email']"),
                ("XPATH", "//input[@id='ap_email']"),
            ]

            for selector_type, selector in alternative_email_selectors:
                print(f"   試行: {selector_type}='{selector}' を検索...")
                try:
                    if selector_type == "ID":
                        email_field = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.ID, selector))
                        )
                    elif selector_type == "NAME":
                        email_field = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.NAME, selector))
                        )
                    elif selector_type == "XPATH":
                        email_field = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )

                    if email_field:
                        print(f"   ✅ メール入力欄発見（{selector_type}='{selector}'）")
                        break
                except TimeoutException:
                    print(f"   ❌ {selector_type}='{selector}' が見つかりません")
                    continue

        if not email_field:
            print("\n   ❌ どの方法でもメール入力欄が見つかりませんでした")
            save_debug_info(driver, "04_email_field_not_found")

            # ページ内のすべてのinput要素を表示
            print("\n   🔍 ページ内のすべてのinput要素を確認:")
            try:
                all_inputs = driver.find_elements(By.TAG_NAME, "input")
                for idx, inp in enumerate(all_inputs):
                    input_type = inp.get_attribute("type") or "unknown"
                    input_id = inp.get_attribute("id") or "no-id"
                    input_name = inp.get_attribute("name") or "no-name"
                    print(f"      Input #{idx+1}: type={input_type}, id={input_id}, name={input_name}")
            except Exception as e:
                print(f"      ❌ input要素の取得失敗: {e}")
        else:
            print("\n   ✅ メール入力欄を正常に検出しました")
            print(f"   要素タグ: {email_field.tag_name}")
            print(f"   要素ID: {email_field.get_attribute('id')}")
            print(f"   要素NAME: {email_field.get_attribute('name')}")

        # ステップ4: 最終サマリー
        print("\n[5/6] テスト結果サマリー")
        print("=" * 80)
        print(f"ログインリンク検出: {'✅ 成功' if login_link else '❌ 失敗'}")
        print(f"メール入力欄検出: {'✅ 成功' if email_field else '❌ 失敗'}")
        print("=" * 80)

        # 30秒間表示
        print("\n[6/6] 30秒間ブラウザを表示します...")
        time.sleep(30)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        save_debug_info(driver, "error")

    finally:
        driver.quit()
        print("\nテスト終了")

if __name__ == "__main__":
    test_element_detection_debug()
