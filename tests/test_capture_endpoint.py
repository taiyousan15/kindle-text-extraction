"""
Test Auto-Capture Endpoint

Phase 1-4の自動キャプチャエンドポイントをテスト
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_capture_start():
    """自動キャプチャ開始のテスト"""
    print("=" * 60)
    print("🧪 Test 1: POST /api/v1/capture/start")
    print("=" * 60)

    # リクエストボディ
    payload = {
        "amazon_email": "test@example.com",
        "amazon_password": "test-password",
        "book_url": "https://read.amazon.com/kindle-library",
        "book_title": "テスト書籍",
        "max_pages": 5,
        "headless": True
    }

    print(f"\n📤 リクエスト:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    response = requests.post(
        f"{BASE_URL}/api/v1/capture/start",
        json=payload
    )

    print(f"\n📥 レスポンス: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 202:
        print("\n✅ Test 1 PASSED")
        return response.json()["job_id"]
    else:
        print("\n❌ Test 1 FAILED")
        return None


def test_capture_status(job_id: str):
    """キャプチャステータス取得のテスト"""
    print("\n" + "=" * 60)
    print(f"🧪 Test 2: GET /api/v1/capture/status/{job_id}")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/v1/capture/status/{job_id}")

    print(f"\n📥 レスポンス: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        print("\n✅ Test 2 PASSED")
        return response.json()
    else:
        print("\n❌ Test 2 FAILED")
        return None


def test_capture_jobs_list():
    """キャプチャジョブ一覧取得のテスト"""
    print("\n" + "=" * 60)
    print("🧪 Test 3: GET /api/v1/capture/jobs")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/api/v1/capture/jobs?limit=5")

    print(f"\n📥 レスポンス: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    if response.status_code == 200:
        print("\n✅ Test 3 PASSED")
        return response.json()
    else:
        print("\n❌ Test 3 FAILED")
        return None


def monitor_job_progress(job_id: str, max_wait: int = 60):
    """ジョブの進捗を監視"""
    print("\n" + "=" * 60)
    print(f"🧪 Test 4: Monitor job progress (job_id={job_id})")
    print("=" * 60)

    start_time = time.time()
    last_status = None

    while True:
        elapsed = int(time.time() - start_time)

        if elapsed > max_wait:
            print(f"\n⏱️ タイムアウト: {max_wait}秒経過")
            break

        status_data = test_capture_status(job_id)

        if status_data:
            status = status_data["status"]
            progress = status_data["progress"]
            pages_captured = status_data["pages_captured"]

            if status != last_status:
                print(f"\n📊 ステータス変更: {last_status} → {status}")
                last_status = status

            print(f"   進捗: {progress}% ({pages_captured}ページ)")

            if status in ["completed", "failed"]:
                print(f"\n🎉 ジョブ終了: {status}")
                if status == "failed":
                    print(f"   エラー: {status_data.get('error_message', 'N/A')}")
                break

        time.sleep(5)


def main():
    """メインテスト実行"""
    print("\n" + "=" * 60)
    print("🚀 Auto-Capture Endpoint Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)

    # Test 1: キャプチャ開始
    job_id = test_capture_start()

    if not job_id:
        print("\n❌ Test Suite FAILED: キャプチャ開始に失敗しました")
        return

    # 少し待機
    time.sleep(2)

    # Test 2: ステータス取得
    test_capture_status(job_id)

    # Test 3: ジョブ一覧取得
    test_capture_jobs_list()

    # Test 4: 進捗監視（オプション）
    print("\n" + "=" * 60)
    monitor_input = input("🤔 ジョブの進捗を監視しますか？ (y/n): ")
    if monitor_input.lower() == "y":
        monitor_job_progress(job_id, max_wait=120)

    print("\n" + "=" * 60)
    print("🎉 Test Suite Complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ テストを中断しました")
    except Exception as e:
        print(f"\n\n❌ エラー: {e}")
