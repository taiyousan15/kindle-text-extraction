#!/usr/bin/env python3
"""
パスキーダイアログの要素を調査するテストスクリプト
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import time

def test_passkey_dialog():
    """パスキーダイアログの要素を調査"""

    # Chrome起動
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("=" * 80)
        print("パスキーダイアログ調査テスト")
        print("=" * 80)

        # 1. Amazonトップページにアクセス
        print("\n[1/6] Amazon.co.jp にアクセス中...")
        driver.get("https://www.amazon.co.jp")
        time.sleep(3)

        # 2. ログインリンククリック
        print("\n[2/6] ログインリンクをクリック中...")
        wait = WebDriverWait(driver, 10)
        login_link = wait.until(
            EC.element_to_be_clickable((By.ID, "nav-link-accountList"))
        )
        login_link.click()
        time.sleep(3)

        # 3. メールアドレス入力
        print("\n[3/6] メールアドレス入力中...")
        email_field = wait.until(
            EC.presence_of_element_located((By.NAME, "email"))
        )

        # 環境変数から読み込む（デモのため仮の値）
        import os
        email = os.getenv("AMAZON_EMAIL", "your_email@example.com")

        email_field.clear()
        email_field.send_keys(email)
        email_field.send_keys(Keys.RETURN)
        print(f"   メールアドレス入力完了: {email}")
        time.sleep(5)  # パスキーダイアログが表示されるまで待機

        # 4. 現在のURLとページタイトルを確認
        print("\n[4/6] ページ情報確認中...")
        print(f"   現在のURL: {driver.current_url}")
        print(f"   ページタイトル: {driver.title}")

        # 5. パスキーダイアログの有無をチェック
        print("\n[5/6] パスキーダイアログの調査中...")

        # URLでチェック
        if "/ax/claim" in driver.current_url:
            print("   ✅ パスキーダイアログのURLを検出しました！")

            # ページソースを保存
            with open("/Users/matsumototoshihiko/Desktop/passkey_dialog.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("   ✅ ページソースを保存: /Users/matsumototoshihiko/Desktop/passkey_dialog.html")

            # 全ボタン要素を調査
            print("\n   === ページ内の全ボタン要素 ===")
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"   見つかったbutton要素: {len(buttons)}個")

            for i, btn in enumerate(buttons):
                btn_id = btn.get_attribute("id")
                btn_class = btn.get_attribute("class")
                btn_text = btn.text
                btn_name = btn.get_attribute("name")
                btn_type = btn.get_attribute("type")

                print(f"\n   [Button {i+1}]")
                print(f"     id='{btn_id}'")
                print(f"     class='{btn_class}'")
                print(f"     text='{btn_text}'")
                print(f"     name='{btn_name}'")
                print(f"     type='{btn_type}'")

            # 全リンク要素も調査
            print("\n   === ページ内の全リンク要素 ===")
            links = driver.find_elements(By.TAG_NAME, "a")
            print(f"   見つかったa要素: {len(links)}個")

            for i, link in enumerate(links[:10]):  # 最初の10個のみ
                link_text = link.text
                link_href = link.get_attribute("href")
                link_id = link.get_attribute("id")
                link_class = link.get_attribute("class")

                if link_text or "cancel" in str(link_href).lower() or "skip" in str(link_href).lower():
                    print(f"\n   [Link {i+1}]")
                    print(f"     id='{link_id}'")
                    print(f"     class='{link_class}'")
                    print(f"     text='{link_text}'")
                    print(f"     href='{link_href}'")
        else:
            print("   ℹ️  パスキーダイアログは表示されませんでした")
            print(f"   現在のURL: {driver.current_url}")

        # 6. 30秒間ブラウザを表示
        print("\n[6/6] 30秒間ブラウザを表示します（手動で確認してください）...")
        time.sleep(30)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()
        print("\nテスト終了")

if __name__ == "__main__":
    test_passkey_dialog()
