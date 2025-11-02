#!/usr/bin/env python3
"""
Amazon ログインページテスト
正しいログインURLを見つける
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def test_amazon_login_url():
    """Amazonログインページへのアクセステスト"""

    # Chrome起動
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # コメントアウトしてブラウザを表示
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("=" * 80)
        print("Amazon ログインページテスト開始")
        print("=" * 80)

        # 方法1: Amazonトップページ → ログインリンククリック
        print("\n【方法1】Amazonトップページからログインリンクをクリック")
        driver.get("https://www.amazon.co.jp")
        print(f"アクセス後のURL: {driver.current_url}")
        time.sleep(3)

        try:
            wait = WebDriverWait(driver, 10)
            login_link = wait.until(
                EC.element_to_be_clickable((By.ID, "nav-link-accountList"))
            )
            print("ログインリンク発見!")
            login_link.click()
            time.sleep(3)
            print(f"クリック後のURL: {driver.current_url}")

            # ログインフォームがあるか確認
            print("ページの読み込みを待機中...")
            time.sleep(5)  # ページの完全読み込みを待つ

            # 複数のIDを試す
            possible_ids = ["ap_email", "email", "ap-credential-autofill-hint"]
            email_field = None

            for email_id in possible_ids:
                try:
                    email_field = driver.find_element(By.ID, email_id)
                    print(f"✅ ログインフォーム発見! (ID={email_id})")
                    print(f"最終URL: {driver.current_url}")
                    break
                except:
                    print(f"  ID '{email_id}' は見つかりませんでした")

            if not email_field:
                # NAMEで探してみる
                try:
                    email_field = driver.find_element(By.NAME, "email")
                    print(f"✅ ログインフォーム発見! (NAME=email)")
                    print(f"最終URL: {driver.current_url}")
                except:
                    print("❌ ログインフォームが見つかりません")
                    print("ページソースを確認します...")
                    # ページ全体を保存して確認
                    page_source = driver.page_source

                    # HTMLファイルとして保存
                    with open("/Users/matsumototoshihiko/Desktop/amazon_login_page.html", "w", encoding="utf-8") as f:
                        f.write(page_source)
                    print("✅ ページソースを /Users/matsumototoshihiko/Desktop/amazon_login_page.html に保存しました")

                    # inputタグを探す
                    print("\n=== ページ内の全input要素を検索 ===")
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    print(f"見つかったinput要素: {len(inputs)}個")
                    for i, inp in enumerate(inputs[:10]):  # 最初の10個だけ表示
                        inp_id = inp.get_attribute("id")
                        inp_name = inp.get_attribute("name")
                        inp_type = inp.get_attribute("type")
                        inp_placeholder = inp.get_attribute("placeholder")
                        print(f"  [{i+1}] id='{inp_id}', name='{inp_name}', type='{inp_type}', placeholder='{inp_placeholder}'")

        except Exception as e:
            print(f"❌ エラー: {e}")

        # 10秒待機してブラウザを確認
        print("\n10秒待機します。ブラウザを確認してください...")
        time.sleep(10)

    finally:
        driver.quit()
        print("\nテスト終了")

if __name__ == "__main__":
    test_amazon_login_url()
