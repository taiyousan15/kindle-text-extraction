#!/usr/bin/env python3
"""
ChromeDriverManagerの動作確認テスト
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def test_chromedriver_simple():
    """ChromeDriverの基本動作テスト"""

    print("=" * 80)
    print("ChromeDriverManager 動作確認テスト")
    print("=" * 80)

    # ChromeDriverManagerを使ってインストール
    print("\nChromeDriverManagerでChromeDriverをインストール中...")
    service = Service(ChromeDriverManager().install())

    # Chromeオプション設定
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # Chrome起動
    print("Chromeを起動中...")
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Googleにアクセス
        print("Google.comにアクセス中...")
        driver.get("https://www.google.com")
        time.sleep(2)

        print("✅ ChromeDriver が正常に動作しました!")
        print(f"現在のURL: {driver.current_url}")

        # 10秒間表示
        print("\n10秒間ブラウザを表示します...")
        time.sleep(10)

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()
        print("\nテスト終了")

if __name__ == "__main__":
    test_chromedriver_simple()
