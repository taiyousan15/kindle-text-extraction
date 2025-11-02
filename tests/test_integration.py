"""
統合テストスクリプト - Phase 1-7
Kindle OCR MVP 全機能テスト

全てのコンポーネントが正常に動作することを確認
"""
import sys
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# テスト設定
API_BASE_URL = "http://localhost:8000"
VERBOSE = True


def print_test(test_name):
    """テスト名を表示"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)


def print_result(success, message):
    """テスト結果を表示"""
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")
    return success


def test_1_database_connection():
    """Test 1: データベース接続確認"""
    print_test("1. Database Connection")

    try:
        from app.core.database import check_connection
        result = check_connection()
        return print_result(result, "データベース接続成功" if result else "データベース接続失敗")
    except Exception as e:
        return print_result(False, f"データベース接続テスト失敗: {e}")


def test_2_health_endpoint():
    """Test 2: ヘルスチェックエンドポイント"""
    print_test("2. Health Check Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)

        if response.status_code == 200:
            data = response.json()
            if VERBOSE:
                print(f"  Status: {data.get('status')}")
                print(f"  Database: {data.get('database')}")
                print(f"  Pool Size: {data.get('pool_size')}")

            success = data.get('status') == 'healthy'
            return print_result(success, "ヘルスチェック正常" if success else "ヘルスチェック異常")
        else:
            return print_result(False, f"ヘルスチェック失敗 (status={response.status_code})")
    except Exception as e:
        return print_result(False, f"ヘルスチェックエンドポイントエラー: {e}")


def test_3_root_endpoint():
    """Test 3: ルートエンドポイント"""
    print_test("3. Root Endpoint")

    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)

        if response.status_code == 200:
            data = response.json()
            if VERBOSE:
                print(f"  Message: {data.get('message')}")
                print(f"  Version: {data.get('version')}")

            success = 'message' in data and 'version' in data
            return print_result(success, "ルートエンドポイント正常")
        else:
            return print_result(False, f"ルートエンドポイント失敗 (status={response.status_code})")
    except Exception as e:
        return print_result(False, f"ルートエンドポイントエラー: {e}")


def test_4_models_import():
    """Test 4: モデルインポート確認"""
    print_test("4. Database Models Import")

    try:
        from app.models import (
            User, Job, OCRResult, Summary, Knowledge,
            BizFile, BizCard, Feedback, RetrainQueue
        )

        models = [User, Job, OCRResult, Summary, Knowledge, BizFile, BizCard, Feedback, RetrainQueue]
        if VERBOSE:
            print(f"  Imported models: {len(models)}")
            for model in models:
                print(f"    - {model.__name__}")

        return print_result(True, "全9モデルインポート成功")
    except Exception as e:
        return print_result(False, f"モデルインポート失敗: {e}")


def test_5_ocr_endpoint():
    """Test 5: OCRエンドポイント"""
    print_test("5. OCR Upload Endpoint")

    try:
        # テスト画像作成
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((50, 80), "Test OCR Text", fill='black')

        # 画像をバイトに変換
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # アップロード
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'book_title': 'Test Book', 'page_num': 1}

        response = requests.post(
            f"{API_BASE_URL}/api/v1/ocr/upload",
            files=files,
            data=data,
            timeout=30
        )

        if response.status_code == 201:
            result = response.json()
            if VERBOSE:
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Text: {result.get('text', '')[:50]}...")
                print(f"  Confidence: {result.get('confidence')}")

            success = 'job_id' in result and 'text' in result
            return print_result(success, "OCRアップロード成功")
        else:
            return print_result(False, f"OCRアップロード失敗 (status={response.status_code})")
    except Exception as e:
        return print_result(False, f"OCRエンドポイントエラー: {e}")


def test_6_job_status_endpoint():
    """Test 6: ジョブステータスエンドポイント"""
    print_test("6. Job Status Endpoint")

    try:
        # まずジョブを作成
        from app.core.database import SessionLocal
        from app.models import Job
        import uuid

        db = SessionLocal()
        try:
            test_job = Job(
                id=str(uuid.uuid4()),
                user_id=1,
                type="ocr",
                status="completed",
                progress=100
            )
            db.add(test_job)
            db.commit()
            db.refresh(test_job)

            job_id = test_job.id

            # ジョブステータス取得
            response = requests.get(
                f"{API_BASE_URL}/api/v1/ocr/jobs/{job_id}",
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                if VERBOSE:
                    print(f"  Job ID: {result.get('id')}")
                    print(f"  Status: {result.get('status')}")
                    print(f"  Progress: {result.get('progress')}%")

                success = result.get('id') == job_id
                return print_result(success, "ジョブステータス取得成功")
            else:
                return print_result(False, f"ジョブステータス取得失敗 (status={response.status_code})")
        finally:
            db.close()
    except Exception as e:
        return print_result(False, f"ジョブステータスエンドポイントエラー: {e}")


def test_7_celery_tasks_import():
    """Test 7: Celeryタスクインポート確認"""
    print_test("7. Celery Tasks Import")

    try:
        from app.tasks import celery_app, process_ocr_job, process_retraining_queue

        if VERBOSE:
            print(f"  Celery App: {celery_app}")
            print(f"  OCR Task: {process_ocr_job.name}")
            print(f"  Retraining Task: {process_retraining_queue.name}")

        success = celery_app is not None and process_ocr_job is not None
        return print_result(success, "Celeryタスクインポート成功")
    except Exception as e:
        return print_result(False, f"Celeryタスクインポート失敗: {e}")


def test_8_schemas_import():
    """Test 8: スキーマインポート確認"""
    print_test("8. Pydantic Schemas Import")

    try:
        from app.schemas.ocr import OCRUploadResponse, JobResponse
        from app.schemas.capture import CaptureStartRequest, CaptureStartResponse

        if VERBOSE:
            print(f"  OCR Schemas: OCRUploadResponse, JobResponse")
            print(f"  Capture Schemas: CaptureStartRequest, CaptureStartResponse")

        return print_result(True, "全スキーマインポート成功")
    except Exception as e:
        return print_result(False, f"スキーマインポート失敗: {e}")


def test_9_api_client_import():
    """Test 9: APIクライアントインポート確認"""
    print_test("9. Streamlit API Client Import")

    try:
        from app.ui.utils.api_client import (
            upload_image, start_auto_capture, get_job_status,
            list_jobs, get_health
        )

        if VERBOSE:
            print(f"  Functions: upload_image, start_auto_capture, get_job_status")
            print(f"            list_jobs, get_health")

        return print_result(True, "APIクライアントインポート成功")
    except Exception as e:
        return print_result(False, f"APIクライアントインポート失敗: {e}")


def test_10_database_tables():
    """Test 10: データベーステーブル確認"""
    print_test("10. Database Tables Verification")

    try:
        from app.core.database import engine
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            'users', 'jobs', 'ocr_results', 'summaries', 'knowledge',
            'biz_files', 'biz_cards', 'feedbacks', 'retrain_queue'
        ]

        if VERBOSE:
            print(f"  Expected tables: {len(expected_tables)}")
            print(f"  Found tables: {len(tables)}")
            for table in expected_tables:
                status = "✓" if table in tables else "✗"
                print(f"    {status} {table}")

        success = all(table in tables for table in expected_tables)
        return print_result(success, f"全{len(expected_tables)}テーブル確認完了")
    except Exception as e:
        return print_result(False, f"データベーステーブル確認失敗: {e}")


def main():
    """メイン実行"""
    print("\n")
    print("🧪 " + "="*56)
    print("🧪 Kindle OCR MVP - 統合テストスイート")
    print("🧪 Phase 1-7: Integration Testing")
    print("🧪 " + "="*56)
    print()

    # 全テスト実行
    tests = [
        test_1_database_connection,
        test_2_health_endpoint,
        test_3_root_endpoint,
        test_4_models_import,
        test_5_ocr_endpoint,
        test_6_job_status_endpoint,
        test_7_celery_tasks_import,
        test_8_schemas_import,
        test_9_api_client_import,
        test_10_database_tables,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ テスト実行エラー: {e}")
            results.append(False)

    # 結果サマリー
    print("\n")
    print("="*60)
    print("テスト結果サマリー")
    print("="*60)

    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"✅ 成功: {passed}/{total} ({success_rate:.1f}%)")
    print(f"❌ 失敗: {total - passed}/{total}")

    if passed == total:
        print("\n🎉 全てのテストが成功しました！")
        print("="*60)
        print("✅ Phase 1 MVP 完成！")
        print("="*60)
        print()
        print("次のステップ:")
        print("  1. FastAPI起動: uvicorn app.main:app --reload")
        print("  2. Celery起動: celery -A app.tasks.celery_app worker -l info")
        print("  3. Streamlit起動: streamlit run app/ui/Home.py")
        print()
        sys.exit(0)
    else:
        print("\n⚠️  一部のテストが失敗しました。上記のエラーを確認してください。")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
