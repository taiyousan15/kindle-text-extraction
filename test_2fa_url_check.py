#!/usr/bin/env python3
"""
2段階認証後のURL変化を確認するテストスクリプト
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time
import os

def test_2fa_url_monitoring():
    """2段階認証後のURL変化を監視"""

    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("=" * 80)
        print("2段階認証URL監視テスト")
        print("=" * 80)

        # 1. Amazonトップページにアクセス
        print("\n[1/5] Amazon.co.jp にアクセス中...")
        driver.get("https://www.amazon.co.jp")
        time.sleep(3)

        # 2. ログインリンククリック
        print("\n[2/5] ログインリンクをクリック中...")
        wait = WebDriverWait(driver, 10)
        login_link = wait.until(
            EC.element_to_be_clickable((By.ID, "nav-link-accountList"))
        )
        login_link.click()
        time.sleep(3)

        # 3. メールアドレス入力
        print("\n[3/5] メールアドレス入力中...")
        email_field = wait.until(
            EC.presence_of_element_located((By.NAME, "email"))
        )

        email = os.getenv("AMAZON_EMAIL", "your_email@example.com")
        email_field.clear()
        email_field.send_keys(email)
        email_field.send_keys(Keys.RETURN)
        print(f"   メールアドレス入力完了: {email}")
        time.sleep(5)

        # パスキーダイアログスキップ
        current_url = driver.current_url
        if "/ax/claim" in current_url or "openid" in current_url:
            print("\n   🔐 パスキーダイアログ検出。スキップ中...")
            try:
                skip_link = wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "signin-with-another-account"))
                )
                skip_link.click()
                time.sleep(3)
                print("   ✅ パスキーダイアログをスキップしました")
            except:
                print("   ⚠️  パスキーダイアログのスキップに失敗")

        # 4. パスワード入力（環境変数から）
        print("\n[4/5] パスワード入力中...")
        password = os.getenv("AMAZON_PASSWORD", "")
        if password:
            try:
                password_field = wait.until(
                    EC.presence_of_element_located((By.NAME, "password"))
                )
                password_field.clear()
                password_field.send_keys(password)
                password_field.send_keys(Keys.RETURN)
                print("   ✅ パスワード入力完了")
                time.sleep(5)
            except Exception as e:
                print(f"   ❌ パスワード入力失敗: {e}")
        else:
            print("   ℹ️  環境変数 AMAZON_PASSWORD が設定されていません")
            print("   手動でパスワードを入力してください（30秒待機）")
            time.sleep(30)

        # 5. URL監視開始
        print("\n[5/5] 2段階認証ページのURL監視開始")
        print("=" * 80)
        print("📱 SMS/メールで届いた認証コードを入力して「次へ」をクリックしてください")
        print("🔍 URLの変化を5秒ごとに記録します（最大3分間）")
        print("=" * 80)

        start_time = time.time()
        max_duration = 180  # 3分間
        check_interval = 5  # 5秒ごと
        last_url = ""
        url_history = []

        while time.time() - start_time < max_duration:
            try:
                current_url = driver.current_url
                elapsed = int(time.time() - start_time)

                if current_url != last_url:
                    print(f"\n[{elapsed}秒経過] URL変化を検出:")
                    print(f"   旧URL: {last_url if last_url else '(初回)'}")
                    print(f"   新URL: {current_url}")

                    # URLパターンチェック
                    login_patterns = ["signin", "ap/mfa", "ap/cvf", "ap/challenge", "auth-mfa", "verify"]
                    is_login_page = any(pattern in current_url.lower() for pattern in login_patterns)
                    print(f"   ログインページ判定: {'はい' if is_login_page else 'いいえ'}")

                    url_history.append({
                        "time": elapsed,
                        "url": current_url,
                        "is_login_page": is_login_page
                    })

                    last_url = current_url

                    # ログインページでなくなったら成功
                    if not is_login_page and elapsed > 10:  # 最初の10秒は除外
                        print("\n" + "=" * 80)
                        print("✅ ログイン成功を検出しました！")
                        print("=" * 80)
                        print(f"最終URL: {current_url}")
                        break

            except Exception as e:
                print(f"\n❌ エラー発生: {e}")
                break

            time.sleep(check_interval)

        # 結果サマリー
        print("\n" + "=" * 80)
        print("URL変化履歴サマリー")
        print("=" * 80)
        for entry in url_history:
            print(f"[{entry['time']}秒] ログインページ={entry['is_login_page']}")
            print(f"  URL: {entry['url']}")

        print("\n30秒間ブラウザを表示します...")
        time.sleep(30)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()
        print("\nテスト終了")

if __name__ == "__main__":
    test_2fa_url_monitoring()
