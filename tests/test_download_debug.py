"""
Test Download Functionality - デバッグテスト

ダウンロードページの機能をテストして問題を特定する
"""
import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_download_flow():
    """ダウンロードフローをテスト"""

    print("=" * 80)
    print("Testing Download Flow")
    print("=" * 80)

    # 1. ジョブ一覧取得
    print("\n1. Fetching job list...")
    response = requests.get(f"{API_BASE_URL}/api/v1/capture/jobs?limit=5")
    jobs = response.json()

    print(f"Found {len(jobs)} jobs")

    # 完了ジョブをフィルタ
    completed_jobs = [job for job in jobs if job.get("status") == "completed"]
    print(f"Completed jobs: {len(completed_jobs)}")

    if not completed_jobs:
        print("ERROR: No completed jobs found!")
        return

    # 最初の完了ジョブを選択
    job = completed_jobs[0]
    job_id = job["job_id"]

    print(f"\nSelected job: {job_id}")
    print(f"  Status: {job['status']}")
    print(f"  Pages: {job['pages_captured']}")
    print(f"  OCR results in list: {len(job.get('ocr_results', []))}")

    # 2. ジョブ詳細取得
    print(f"\n2. Fetching job details for {job_id}...")
    response = requests.get(f"{API_BASE_URL}/api/v1/capture/status/{job_id}")
    job_detail = response.json()

    print(f"Job detail fetched:")
    print(f"  Status: {job_detail['status']}")
    print(f"  Pages: {job_detail['pages_captured']}")
    print(f"  OCR results count: {len(job_detail.get('ocr_results', []))}")

    ocr_results = job_detail.get("ocr_results", [])

    if not ocr_results:
        print("\nERROR: OCR results are empty!")
        print("This is the root cause - no OCR data to download")
        return

    print(f"\n3. Testing data conversion...")

    # TXTファイル生成テスト
    try:
        from datetime import datetime

        book_title = f"Test_Book_{job_id[:8]}"

        # プレーンテキスト
        lines = [
            f"書籍タイトル: {book_title}",
            f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"総ページ数: {len(ocr_results)}",
            "=" * 80,
            ""
        ]

        for result in ocr_results[:3]:  # 最初の3ページだけ
            page_num = result.get("page_num", 0)
            text = result.get("text", "")
            confidence = result.get("confidence", 0.0)

            lines.append(f"--- ページ {page_num} (信頼度: {confidence:.2%}) ---")
            lines.append(text[:100] + "...")  # 最初の100文字だけ
            lines.append("")

        text_content = "\n".join(lines)
        print(f"✅ Text conversion successful")
        print(f"   Size: {len(text_content.encode('utf-8'))} bytes")
        print(f"   Preview:\n{text_content[:300]}...")

    except Exception as e:
        print(f"❌ Text conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # CSVファイル生成テスト
    try:
        import pandas as pd

        df = pd.DataFrame([
            {
                "ページ番号": result.get("page_num", 0),
                "テキスト": result.get("text", ""),
                "信頼度": result.get("confidence", 0.0)
            }
            for result in ocr_results[:3]  # 最初の3ページだけ
        ])

        csv_content = df.to_csv(index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV conversion successful")
        print(f"   Size: {len(csv_content.encode('utf-8'))} bytes")
        print(f"   Rows: {len(df)}")

    except Exception as e:
        print(f"❌ CSV conversion failed: {e}")
        import traceback
        traceback.print_exc()

    # Excelファイル生成テスト
    try:
        import pandas as pd
        import io

        df = pd.DataFrame([
            {
                "ページ番号": result.get("page_num", 0),
                "テキスト": result.get("text", ""),
                "信頼度": result.get("confidence", 0.0)
            }
            for result in ocr_results[:3]  # 最初の3ページだけ
        ])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='OCR結果')

        excel_content = output.getvalue()
        print(f"\n✅ Excel conversion successful")
        print(f"   Size: {len(excel_content)} bytes")

    except Exception as e:
        print(f"❌ Excel conversion failed: {e}")
        import traceback
        traceback.print_exc()

    # Markdownファイル生成テスト
    try:
        lines = [
            f"# {book_title}",
            "",
            f"**生成日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            f"**総ページ数:** {len(ocr_results)}",
            "",
            "---",
            ""
        ]

        for result in ocr_results[:3]:  # 最初の3ページだけ
            page_num = result.get("page_num", 0)
            text = result.get("text", "")
            confidence = result.get("confidence", 0.0)

            lines.append(f"## ページ {page_num}")
            lines.append("")
            lines.append(f"**信頼度:** {confidence:.2%}")
            lines.append("")
            lines.append(text[:100] + "...")
            lines.append("")
            lines.append("---")
            lines.append("")

        markdown_content = "\n".join(lines)
        print(f"\n✅ Markdown conversion successful")
        print(f"   Size: {len(markdown_content.encode('utf-8'))} bytes")

    except Exception as e:
        print(f"❌ Markdown conversion failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ All download conversions successful!")
    print("=" * 80)

    # 画像ファイルZIP作成テスト
    print("\n4. Testing image ZIP creation...")

    try:
        from pathlib import Path
        import zipfile
        import io

        captures_dir = Path("./captures")
        job_dir = captures_dir / job_id

        if not job_dir.exists():
            print(f"⚠️  Job directory not found: {job_dir}")
            print(f"   This may be expected if images were not captured")
        else:
            image_files = sorted(job_dir.glob("page_*.png"))
            print(f"   Found {len(image_files)} image files")

            if image_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for image_path in image_files[:3]:  # 最初の3ファイルだけ
                        arcname = image_path.name
                        zip_file.write(image_path, arcname=arcname)

                zip_bytes = zip_buffer.getvalue()
                print(f"✅ ZIP creation successful")
                print(f"   Size: {len(zip_bytes) / 1024 / 1024:.2f} MB (3 images)")
            else:
                print(f"⚠️  No image files found in {job_dir}")

    except Exception as e:
        print(f"❌ ZIP creation failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Download Flow Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_download_flow()
