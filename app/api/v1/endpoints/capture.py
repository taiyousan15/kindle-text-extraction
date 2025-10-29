"""
Capture Endpoint

自動キャプチャのエンドポイント
Phase 1-4 Implementation
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import Job, OCRResult
from app.models.user import User
from app.schemas.capture import (
    CaptureStartRequest,
    CaptureStartResponse,
    CaptureStatusResponse,
    OCRResultSummary
)
from app.services.capture_service import CaptureService

# ロガー設定
logger = logging.getLogger(__name__)

# ルーター設定
router = APIRouter()


@router.post("/start", response_model=CaptureStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_auto_capture(
    request: CaptureStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CaptureStartResponse:
    """
    自動キャプチャを開始（非同期）

    Kindle Cloud Readerから自動的にスクリーンショットをキャプチャし、
    OCR処理を実行します。処理は即座に返却され、バックグラウンドで実行されます。

    Args:
        request: キャプチャ開始リクエスト
            - amazon_email: AmazonアカウントのEメールアドレス
            - amazon_password: Amazonアカウントのパスワード
            - book_url: Kindle Cloud ReaderのブックURL
            - book_title: 書籍タイトル (オプション)
            - max_pages: 最大キャプチャページ数 (オプション、デフォルト: 100)
            - headless: ヘッドレスモード (オプション、デフォルト: True)
        db: データベースセッション

    Returns:
        CaptureStartResponse: ジョブID、ステータス、メッセージ

    Raises:
        HTTPException: データベースエラー時

    Example:
        ```
        POST /api/v1/capture/start
        {
            "amazon_email": "user@example.com",
            "amazon_password": "your-password",
            "book_url": "https://read.amazon.com/kindle-library",
            "book_title": "プロンプトエンジニアリング入門",
            "max_pages": 50,
            "headless": true
        }
        ```

        Response:
        ```
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "pending",
            "message": "自動キャプチャジョブを開始しました。..."
        }
        ```
    """
    logger.info(f"🚀 自動キャプチャ開始リクエスト: book_title={request.book_title}, max_pages={request.max_pages}")

    try:
        # Job作成
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            user_id=current_user.id,
            type="auto_capture",
            status="pending",
            progress=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"✅ Job作成完了: job_id={job_id}")

        # バックグラウンドタスク開始
        CaptureService.start_capture_task(
            job_id=job_id,
            amazon_email=request.amazon_email,
            amazon_password=request.amazon_password,
            book_url=request.book_url,
            book_title=request.book_title,
            max_pages=request.max_pages,
            headless=request.headless
        )

        return CaptureStartResponse(
            job_id=job_id,
            status="pending",
            message=f"自動キャプチャジョブを開始しました。/api/v1/capture/status/{job_id} でステータスを確認してください。"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 自動キャプチャ開始エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"自動キャプチャの開始に失敗しました: {str(e)}"
        )


@router.get("/status/{job_id}", response_model=CaptureStatusResponse)
async def get_capture_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> CaptureStatusResponse:
    """
    キャプチャジョブのステータスを取得

    Args:
        job_id: ジョブID (UUID)
        db: データベースセッション

    Returns:
        CaptureStatusResponse: ジョブステータス、進捗、OCR結果

    Raises:
        HTTPException: ジョブが見つからない場合

    Example:
        ```
        GET /api/v1/capture/status/550e8400-e29b-41d4-a716-446655440000
        ```

        Response:
        ```
        {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "progress": 50,
            "pages_captured": 25,
            "total_pages": 50,
            "error_message": null,
            "ocr_results": [
                {
                    "page_num": 1,
                    "text": "第1章 はじめに...",
                    "confidence": 0.95
                }
            ],
            "created_at": "2025-10-28T10:30:00",
            "completed_at": null
        }
        ```
    """
    logger.info(f"📊 ステータス取得: job_id={job_id}")

    # Jobを取得 (ユーザーフィルタリング)
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        logger.warning(f"⚠️ ジョブが見つかりません: job_id={job_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ジョブが見つかりません: {job_id}"
        )

    # auto_capture タイプのみ対応
    if job.type != "auto_capture":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"このエンドポイントはauto_captureジョブのみ対応しています（現在: {job.type}）"
        )

    # OCR結果を取得
    ocr_results = db.query(OCRResult).filter(
        OCRResult.job_id == job_id
    ).order_by(OCRResult.page_num).all()

    # OCRResultSummaryに変換
    ocr_summaries = [
        OCRResultSummary(
            page_num=result.page_num,
            text=result.text[:200] + "..." if len(result.text) > 200 else result.text,  # 最初の200文字のみ
            confidence=result.confidence
        )
        for result in ocr_results
    ]

    return CaptureStatusResponse(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        pages_captured=len(ocr_results),
        total_pages=None,  # SeleniumCaptureResultから取得する場合は実装が必要
        error_message=job.error_message,
        ocr_results=ocr_summaries,
        created_at=job.created_at,
        completed_at=job.completed_at
    )


@router.get("/jobs", response_model=List[CaptureStatusResponse])
async def list_capture_jobs(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[CaptureStatusResponse]:
    """
    キャプチャジョブの一覧を取得

    Args:
        limit: 取得件数 (デフォルト: 10)
        db: データベースセッション

    Returns:
        List[CaptureStatusResponse]: キャプチャジョブのリスト

    Example:
        ```
        GET /api/v1/capture/jobs?limit=10
        ```

        Response:
        ```
        [
            {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "progress": 100,
                "pages_captured": 50,
                ...
            }
        ]
        ```
    """
    logger.info(f"📋 ジョブ一覧取得: limit={limit}")

    # auto_captureタイプのジョブを取得 (ユーザーフィルタリング)
    jobs = db.query(Job).filter(
        Job.type == "auto_capture",
        Job.user_id == current_user.id
    ).order_by(Job.created_at.desc()).limit(limit).all()

    results = []
    for job in jobs:
        # OCR結果数を取得
        ocr_count = db.query(OCRResult).filter(
            OCRResult.job_id == job.id
        ).count()

        results.append(CaptureStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            pages_captured=ocr_count,
            total_pages=None,
            error_message=job.error_message,
            ocr_results=[],  # 一覧では空リスト
            created_at=job.created_at,
            completed_at=job.completed_at
        ))

    return results
