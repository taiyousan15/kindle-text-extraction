"""
API Client Utilities for Streamlit UI

FastAPI バックエンドとの通信を行うクライアントユーティリティ
"""
import os
import requests
from typing import Optional, Dict, Any, List
import logging

# ロガー設定
logger = logging.getLogger(__name__)

# API Base URL (環境変数から取得、デフォルトはlocalhost)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIError(Exception):
    """API エラー基底クラス"""
    def __init__(self, message: str, status_code: Optional[int] = None, detail: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


def _handle_response(response: requests.Response) -> Dict[str, Any]:
    """
    レスポンスのエラーハンドリング

    Args:
        response: requests.Response オブジェクト

    Returns:
        Dict[str, Any]: レスポンスのJSON

    Raises:
        APIError: API呼び出しエラー時
    """
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = response.json().get("detail", str(e))
        except:
            error_detail = str(e)

        logger.error(f"API Error: {response.status_code} - {error_detail}")
        raise APIError(
            message=f"APIエラー: {response.status_code}",
            status_code=response.status_code,
            detail=error_detail
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Request Error: {e}")
        raise APIError(
            message=f"接続エラー: {str(e)}",
            detail=str(e)
        )


def upload_image(
    file_data: bytes,
    filename: str,
    book_title: str,
    page_num: int
) -> Dict[str, Any]:
    """
    画像ファイルをアップロードしてOCR処理を実行

    Args:
        file_data: 画像ファイルのバイトデータ
        filename: ファイル名
        book_title: 書籍タイトル
        page_num: ページ番号

    Returns:
        Dict[str, Any]: OCR結果
            - job_id: str
            - book_title: str
            - page_num: int
            - text: str
            - confidence: float

    Raises:
        APIError: API呼び出しエラー時
    """
    url = f"{API_BASE_URL}/api/v1/ocr/upload"

    files = {
        "file": (filename, file_data, "image/png")
    }

    data = {
        "book_title": book_title,
        "page_num": page_num
    }

    logger.info(f"Uploading image: {filename} for book '{book_title}', page {page_num}")

    try:
        response = requests.post(url, files=files, data=data, timeout=60)
        result = _handle_response(response)
        logger.info(f"Upload successful: job_id={result.get('job_id')}")
        return result
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise


def start_auto_capture(
    email: str,
    password: str,
    book_url: str,
    book_title: str = "Untitled",
    max_pages: int = 50,
    headless: bool = True
) -> Dict[str, Any]:
    """
    自動キャプチャを開始

    Args:
        email: AmazonアカウントのEメールアドレス
        password: Amazonアカウントのパスワード
        book_url: Kindle Cloud ReaderのブックURL
        book_title: 書籍タイトル (デフォルト: "Untitled")
        max_pages: 最大キャプチャページ数 (デフォルト: 50)
        headless: ヘッドレスモード (デフォルト: True)

    Returns:
        Dict[str, Any]: 開始レスポンス
            - job_id: str
            - status: str
            - message: str

    Raises:
        APIError: API呼び出しエラー時
    """
    url = f"{API_BASE_URL}/api/v1/capture/start"

    payload = {
        "amazon_email": email,
        "amazon_password": password,
        "book_url": book_url,
        "book_title": book_title,
        "max_pages": max_pages,
        "headless": headless
    }

    logger.info(f"Starting auto-capture for book '{book_title}', max_pages={max_pages}")

    try:
        response = requests.post(url, json=payload, timeout=10)
        result = _handle_response(response)
        logger.info(f"Auto-capture started: job_id={result.get('job_id')}")
        return result
    except Exception as e:
        logger.error(f"Auto-capture start failed: {e}")
        raise


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    ジョブのステータスを取得

    Args:
        job_id: ジョブID (UUID)

    Returns:
        Dict[str, Any]: ジョブステータス
            - job_id: str
            - status: str (pending, processing, completed, failed)
            - progress: int (0-100)
            - pages_captured: int
            - total_pages: Optional[int]
            - error_message: Optional[str]
            - ocr_results: List[Dict]
            - created_at: str
            - completed_at: Optional[str]

    Raises:
        APIError: API呼び出しエラー時
    """
    url = f"{API_BASE_URL}/api/v1/capture/status/{job_id}"

    logger.info(f"Getting job status: job_id={job_id}")

    try:
        response = requests.get(url, timeout=10)
        result = _handle_response(response)
        return result
    except Exception as e:
        logger.error(f"Get job status failed: {e}")
        raise


def list_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    ジョブの一覧を取得

    Args:
        limit: 取得件数 (デフォルト: 10)

    Returns:
        List[Dict[str, Any]]: ジョブのリスト

    Raises:
        APIError: API呼び出しエラー時
    """
    url = f"{API_BASE_URL}/api/v1/capture/jobs"
    params = {"limit": limit}

    logger.info(f"Getting job list: limit={limit}")

    try:
        response = requests.get(url, params=params, timeout=10)
        result = _handle_response(response)
        return result
    except Exception as e:
        logger.error(f"Get job list failed: {e}")
        raise


def get_health() -> Dict[str, Any]:
    """
    ヘルスチェック - システムの状態を確認

    Returns:
        Dict[str, Any]: ヘルスチェック結果
            - status: str (healthy, unhealthy)
            - database: str
            - pool_size: int
            - checked_out: int

    Raises:
        APIError: API呼び出しエラー時
    """
    url = f"{API_BASE_URL}/health"

    try:
        response = requests.get(url, timeout=5)
        result = _handle_response(response)
        return result
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise


def delete_job(job_id: str) -> Dict[str, Any]:
    """
    ジョブを削除（実装は今後の機能拡張）

    Args:
        job_id: ジョブID (UUID)

    Returns:
        Dict[str, Any]: 削除結果

    Note:
        現在のAPIには削除エンドポイントがないため、将来の実装用
    """
    # 将来の実装用 - 現在は未実装
    raise NotImplementedError("ジョブ削除機能は今後実装予定です")
