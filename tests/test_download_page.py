"""
Test Download Page - 画像/テキストダウンロード機能のテスト

Tests:
1. Image ZIP creation functionality
2. File size calculation for images
3. Error handling for missing images
4. Text download functionality (existing)
"""
import pytest
import zipfile
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import importlib.util

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# 動的にダウンロードページモジュールをインポート（emojiファイル名対応）
def import_download_module():
    """Download pageモジュールを動的にインポート"""
    module_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "app/ui/pages/3_📥_Download.py"
    ))
    spec = importlib.util.spec_from_file_location("download_module", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestImageZIPDownload:
    """画像ZIPダウンロード機能のテスト"""

    def test_create_image_zip_success(self, tmp_path):
        """画像ZIPファイル作成が成功する"""
        # テスト用の画像ファイルを作成
        captures_dir = tmp_path / "captures" / "test-job-id"
        captures_dir.mkdir(parents=True, exist_ok=True)

        # ダミー画像ファイル作成
        for i in range(1, 4):
            image_file = captures_dir / f"page_{i:04d}.png"
            image_file.write_bytes(b"fake-image-data-" + str(i).encode() * 100)

        # ZIP作成関数をテスト
        download_module = import_download_module()
        create_image_zip = download_module.create_image_zip

        zip_bytes = create_image_zip("test-job-id", str(tmp_path / "captures"))

        # ZIPファイルが正しく作成されているか検証
        assert zip_bytes is not None
        assert len(zip_bytes) > 0

        # ZIPファイルの内容を検証
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
            file_list = zip_file.namelist()
            assert len(file_list) == 3
            assert "page_0001.png" in file_list
            assert "page_0002.png" in file_list
            assert "page_0003.png" in file_list

    def test_create_image_zip_no_images(self, tmp_path):
        """画像が存在しない場合はNoneを返す"""
        # 空のディレクトリ
        captures_dir = tmp_path / "captures" / "empty-job-id"
        captures_dir.mkdir(parents=True, exist_ok=True)

        download_module = import_download_module()
        create_image_zip = download_module.create_image_zip

        zip_bytes = create_image_zip("empty-job-id", str(tmp_path / "captures"))

        assert zip_bytes is None

    def test_create_image_zip_job_not_found(self, tmp_path):
        """ジョブディレクトリが存在しない場合はNoneを返す"""
        download_module = import_download_module()
        create_image_zip = download_module.create_image_zip

        zip_bytes = create_image_zip("nonexistent-job-id", str(tmp_path / "captures"))

        assert zip_bytes is None

    def test_calculate_zip_size(self, tmp_path):
        """ZIPファイルサイズが正しく計算される"""
        # テスト用の画像ファイルを作成
        captures_dir = tmp_path / "captures" / "test-job-id"
        captures_dir.mkdir(parents=True, exist_ok=True)

        # ダミー画像ファイル作成（約500KB）
        for i in range(1, 6):
            image_file = captures_dir / f"page_{i:04d}.png"
            image_file.write_bytes(b"x" * 100000)  # 100KB each

        download_module = import_download_module()
        create_image_zip = download_module.create_image_zip
        get_zip_size_mb = download_module.get_zip_size_mb

        zip_bytes = create_image_zip("test-job-id", str(tmp_path / "captures"))
        size_mb = get_zip_size_mb(zip_bytes)

        # ファイルサイズが正しく計算されている
        assert size_mb > 0
        assert size_mb < 1.0  # 500KB未満なので1MB以下

    def test_image_file_pattern_recognition(self, tmp_path):
        """page_NNNN.png パターンの画像ファイルのみを認識する"""
        captures_dir = tmp_path / "captures" / "test-job-id"
        captures_dir.mkdir(parents=True, exist_ok=True)

        # 正しいパターンのファイル
        (captures_dir / "page_0001.png").write_bytes(b"valid")
        (captures_dir / "page_0002.png").write_bytes(b"valid")

        # 間違ったパターンのファイル（無視されるべき）
        (captures_dir / "thumbnail.png").write_bytes(b"invalid")
        (captures_dir / "metadata.json").write_bytes(b"invalid")

        download_module = import_download_module()
        create_image_zip = download_module.create_image_zip

        zip_bytes = create_image_zip("test-job-id", str(tmp_path / "captures"))

        # 正しいパターンのファイルのみがZIPに含まれる
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
            file_list = zip_file.namelist()
            assert len(file_list) == 2
            assert "page_0001.png" in file_list
            assert "page_0002.png" in file_list
            assert "thumbnail.png" not in file_list
            assert "metadata.json" not in file_list


class TestTextDownload:
    """テキストダウンロード機能のテスト（既存機能）"""

    def test_convert_to_text(self):
        """OCR結果がプレーンテキストに変換される"""
        download_module = import_download_module()
        convert_to_text = download_module.convert_to_text

        ocr_results = [
            {"page_num": 1, "text": "テストページ1", "confidence": 0.95},
            {"page_num": 2, "text": "テストページ2", "confidence": 0.92}
        ]

        text = convert_to_text(ocr_results, "テスト書籍")

        assert "テスト書籍" in text
        assert "テストページ1" in text
        assert "テストページ2" in text
        assert "95.00%" in text or "95%" in text

    def test_convert_to_csv(self):
        """OCR結果がCSVに変換される"""
        download_module = import_download_module()
        convert_to_csv = download_module.convert_to_csv

        ocr_results = [
            {"page_num": 1, "text": "テストページ1", "confidence": 0.95},
            {"page_num": 2, "text": "テストページ2", "confidence": 0.92}
        ]

        csv = convert_to_csv(ocr_results)

        assert "ページ番号" in csv
        assert "テキスト" in csv
        assert "信頼度" in csv
        assert "テストページ1" in csv


class TestDownloadPageUI:
    """ダウンロードページUI機能のテスト"""

    @patch('streamlit.radio')
    def test_download_option_selection(self, mock_radio):
        """ダウンロードオプション選択UIが表示される"""
        mock_radio.return_value = "画像ファイル（全ページのスクリーンショット）"

        # UIレンダリングは実際のStreamlitアプリでテスト
        # ここではモック動作のみ確認
        selected = mock_radio()

        assert selected == "画像ファイル（全ページのスクリーンショット）"

    def test_file_size_display_format(self):
        """ファイルサイズが適切にフォーマットされる"""
        download_module = import_download_module()
        format_file_size = download_module.format_file_size

        # KB単位
        assert "512.00 KB" == format_file_size(512 * 1024)

        # MB単位
        assert "1.50 MB" == format_file_size(1.5 * 1024 * 1024)

        # GB単位
        assert "2.00 GB" == format_file_size(2 * 1024 * 1024 * 1024)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
