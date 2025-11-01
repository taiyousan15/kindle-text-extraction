#!/usr/bin/env python3
"""
最終ログイン自動化テスト
修正後のselenium_capture.pyを使用して実際のログインフローをテスト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()  # .envファイルから環境変数を読み込む

from app.services.capture.selenium_capture import SeleniumKindleCapture, SeleniumCaptureConfig
import time

def test_login_flow():
    """ログインフローの最終テスト"""

    print("=" * 80)
    print("最終ログイン自動化テスト")
    print("=" * 80)

    # 環境変数確認
    email = os.getenv("AMAZON_EMAIL")
    password = os.getenv("AMAZON_PASSWORD")

    if not email or not password:
        print("❌ 環境変数 AMAZON_EMAIL と AMAZON_PASSWORD を設定してください")
        print("   .env ファイルに以下の形式で設定してください:")
        print("   AMAZON_EMAIL=your_email@example.com")
        print("   AMAZON_PASSWORD=your_password")
        return

    print(f"\n使用するメールアドレス: {email}")

    # 設定作成（ログインテストのためダミー値を使用）
    config = SeleniumCaptureConfig(
        book_url="https://read.amazon.co.jp/kindle-library",  # ダミーURL
        book_title="Login Test",
        amazon_email=email,
        amazon_password=password,
        headless=False  # テスト時は画面を表示
    )

    # SeleniumKindleCaptureを初期化
    print("\n[1/5] Selenium Kindle Capture を初期化中...")
    capture = SeleniumKindleCapture(config)

    try:
        # ログイン実行
        print("\n[2/5] Amazonログインを実行中...")
        print("   ⏳ ログイン処理には時間がかかる場合があります...")
        print("   ⏳ パスキーダイアログは自動的にスキップされます...")
        print("   ⏳ 二段階認証は手動で入力してください（3分間待機）...")
        print("=" * 80)
        success = capture.login()
        print("=" * 80)

        if success:
            print("\n✅ ログイン成功！")

            # 現在のURLを確認
            current_url = capture.driver.current_url
            print(f"\n[3/5] ログイン後のURL: {current_url}")

            # Kindleページにアクセステスト
            print("\n[4/5] Kindleライブラリへのアクセステスト中...")
            capture.driver.get("https://read.amazon.co.jp/kindle-library")
            time.sleep(5)

            final_url = capture.driver.current_url
            print(f"   最終URL: {final_url}")

            if "kindle-library" in final_url:
                print("   ✅ Kindleライブラリに正常にアクセスできました")
                print("\n🎉 すべてのテスト成功！")
                print("   - ログインリンククリック: ✅")
                print("   - メールアドレス入力: ✅")
                print("   - パスキー自動スキップ: ✅")
                print("   - パスワード入力: ✅")
                print("   - 二段階認証: ✅")
                print("   - Kindleライブラリアクセス: ✅")
            else:
                print("   ⚠️  まだログインページにいる可能性があります")

            print("\n[5/5] 30秒間ブラウザを表示します（状態確認用）...")
            time.sleep(30)

        else:
            print("\n❌ ログイン失敗")
            print("\n詳細:")
            print("  - ログインリンクが見つからなかった可能性があります")
            print("  - メールアドレス入力欄が見つからなかった可能性があります")
            print("  - Bot検出された可能性があります")

            # 現在のURLを確認
            current_url = capture.driver.current_url
            print(f"\n失敗時のURL: {current_url}")

            # スクリーンショット保存
            screenshot_path = "/tmp/login_failure.png"
            capture.driver.save_screenshot(screenshot_path)
            print(f"スクリーンショット保存: {screenshot_path}")

            print("\n30秒間ブラウザを表示します（デバッグ用）...")
            time.sleep(30)

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # クリーンアップ
        print("\n\nクリーンアップ中...")
        capture.close()
        print("テスト終了")

if __name__ == "__main__":
    test_login_flow()
