# Kindle文字起こしツール Phase 1 開発計画

## 📅 作成日: 2025-10-28

---

## 🎯 目標

v3.0要件定義書（ローカル版）に基づき、**Phase 1: MVP（7-10日）** を完成させる。

**Miyabi Agentフル稼働** + **エラー予防重視** + **ステップバイステップ実装**

---

## 📊 開発アプローチ

### 原則
1. **1機能ずつ実装・テスト・確認**（並行作業なし）
2. **各ステップで動作確認**（次に進む前に必ず確認）
3. **Miyabi Agent活用**（CodeGen, Review, Test生成）
4. **エラー予防優先**（型ヒント、バリデーション、ログ完備）

### 開発順序の理由
```
データベース（土台）
    ↓
FastAPI基本構造（API層）
    ↓
OCRエンドポイント（コア機能）
    ↓
Celeryタスク（非同期処理）
    ↓
Streamlit UI（ユーザーインターフェース）
    ↓
統合テスト（全体動作確認）
```

---

## 📋 Phase 1 詳細計画

### **Phase 1-1: データベーススキーマ設計とSQLAlchemyモデル実装**

**期間**: 1日（8時間）

**目標**: PostgreSQL 8テーブルのSQLAlchemyモデル完成

#### タスク詳細

##### 1-1-1: モデルファイル構造作成（30分）
```bash
app/models/
├── __init__.py
├── base.py           # Base設定、共通Mixin
├── user.py           # Userモデル
├── job.py            # Jobモデル
├── ocr_result.py     # OCRResultモデル
├── summary.py        # Summaryモデル
├── knowledge.py      # Knowledgeモデル
├── biz_file.py       # BizFileモデル
├── biz_card.py       # BizCardモデル（pgvector）
├── feedback.py       # Feedbackモデル
└── retrain_queue.py  # RetrainQueueモデル
```

##### 1-1-2: base.py実装（1時間）
- SQLAlchemy Base設定
- TimestampMixin（created_at, updated_at）
- UUIDMixin（UUID主キー用）
- ユーティリティメソッド（to_dict, from_dict）

##### 1-1-3: 各モデル実装（5時間）
**順序**:
1. `user.py`（依存なし）
2. `job.py`（user依存）
3. `ocr_result.py`（job依存、BYTEA使用）
4. `summary.py`（job依存）
5. `knowledge.py`（BYTEA使用）
6. `biz_file.py`（BYTEA使用）
7. `biz_card.py`（biz_file依存、**pgvector VECTOR(384)**）
8. `feedback.py`（user依存）
9. `retrain_queue.py`（biz_card依存）

**各モデル実装内容**:
- SQLAlchemyモデル定義
- 型ヒント完備
- リレーション設定
- インデックス設定
- バリデーション（Pydantic schema）

##### 1-1-4: Alembicマイグレーション生成（1時間）
```bash
# マイグレーション生成
alembic revision --autogenerate -m "Initial schema: 9 tables"

# マイグレーション確認
alembic upgrade head --sql

# 実行
alembic upgrade head
```

##### 1-1-5: 動作確認（30分）
```python
# テストスクリプト
from app.models import User, Job, OCRResult
from app.core.database import SessionLocal

db = SessionLocal()

# User作成
user = User(email="test@example.com", name="Test User")
db.add(user)
db.commit()

# Job作成
job = Job(user_id=user.id, type="ocr", status="pending")
db.add(job)
db.commit()

print("✅ Database models working!")
```

**成果物**:
- ✅ 9つのSQLAlchemyモデル
- ✅ Alembicマイグレーション
- ✅ PostgreSQL 9テーブル作成済み
- ✅ 動作確認完了

---

### **Phase 1-2: FastAPI基本構造とヘルスチェックエンドポイント**

**期間**: 0.5日（4時間）

**目標**: FastAPI起動 + ヘルスチェック実装

#### タスク詳細

##### 1-2-1: FastAPI基本構造作成（1時間）
```bash
app/api/
├── __init__.py
├── main.py           # FastAPIアプリ本体
├── deps.py           # 依存性注入（DB session等）
└── routers/
    ├── __init__.py
    ├── health.py     # ヘルスチェック
    ├── ocr.py        # OCRエンドポイント（後で実装）
    ├── summary.py    # 要約エンドポイント（後で実装）
    ├── knowledge.py  # ナレッジエンドポイント（後で実装）
    └── biz.py        # ビジネスRAGエンドポイント（後で実装）
```

##### 1-2-2: main.py実装（1時間）
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import health

app = FastAPI(
    title="Kindle OCR API",
    version="3.0.0",
    description="ローカル環境専用 Kindle文字起こしAPI"
)

# CORS設定（Streamlit用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(health.router, prefix="/api/v1", tags=["health"])

@app.get("/")
def root():
    return {"message": "Kindle OCR API v3.0 - Local"}
```

##### 1-2-3: health.py実装（1時間）
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, health_check

router = APIRouter()

@router.get("/health")
async def health():
    """ヘルスチェック"""
    db_health = await health_check()
    return {
        "status": "healthy",
        "version": "3.0.0",
        "environment": "local",
        "database": db_health
    }

@router.get("/healthz")
async def healthz():
    """Kubernetes形式ヘルスチェック"""
    return {"status": "ok"}
```

##### 1-2-4: 動作確認（1時間）
```bash
# FastAPI起動
uvicorn app.api.main:app --reload --port 8000

# テスト
curl http://localhost:8000/
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/docs  # Swagger UI確認
```

**成果物**:
- ✅ FastAPI起動成功
- ✅ ヘルスチェックエンドポイント動作
- ✅ Swagger UI表示
- ✅ CORS設定完了

---

### **Phase 1-3: OCRエンドポイント実装（手動アップロード）**

**期間**: 1日（8時間）

**目標**: 手動画像アップロード → OCR → DB保存

#### タスク詳細

##### 1-3-1: Pydantic schema作成（1時間）
```python
# app/schemas/ocr.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class OCRUploadRequest(BaseModel):
    image_b64: str = Field(..., description="Base64エンコード画像")
    book_title: str = Field(..., min_length=1, max_length=255)
    options: Optional[OCROptions] = None

class OCROptions(BaseModel):
    lang: str = "ja+en"
    dpi: int = Field(default=300, ge=100, le=600)
    layout: str = "paragraph"

class OCRResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
```

##### 1-3-2: OCRサービス実装（3時間）
```python
# app/services/ocr_service.py
import pytesseract
from PIL import Image
import io
import base64

class OCRService:
    def extract_text(self, image_b64: str, options: OCROptions) -> dict:
        # Base64デコード
        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data))

        # Tesseract OCR
        text = pytesseract.image_to_string(
            image,
            lang=options.lang,
            config=f"--dpi {options.dpi}"
        )

        # 信頼度取得
        data = pytesseract.image_to_data(image, output_type='dict')
        confidence = sum(data['conf']) / len(data['conf'])

        return {
            "text": text,
            "confidence": confidence,
            "image_blob": image_data
        }
```

##### 1-3-3: OCRエンドポイント実装（2時間）
```python
# app/api/routers/ocr.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.ocr import OCRUploadRequest, OCRResponse
from app.models import Job, OCRResult, User
from app.services.ocr_service import OCRService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=OCRResponse)
async def upload_ocr(
    request: OCRUploadRequest,
    db: Session = Depends(get_db)
):
    try:
        # デフォルトユーザー取得
        user = db.query(User).first()
        if not user:
            user = User(email="local@user.com", name="Local User")
            db.add(user)
            db.commit()

        # Job作成
        job = Job(user_id=user.id, type="ocr", status="running")
        db.add(job)
        db.commit()

        # OCR実行
        ocr_service = OCRService()
        result = ocr_service.extract_text(
            request.image_b64,
            request.options or OCROptions()
        )

        # OCRResult保存
        ocr_result = OCRResult(
            job_id=job.id,
            book_title=request.book_title,
            page_num=1,
            text=result["text"],
            confidence=result["confidence"],
            image_blob=result["image_blob"]
        )
        db.add(ocr_result)

        # Job完了
        job.status = "completed"
        job.progress = 100
        db.commit()

        logger.info(f"✅ OCR completed: job_id={job.id}")

        return OCRResponse(
            job_id=job.id,
            status="completed",
            message=f"OCR成功: {len(result['text'])}文字"
        )

    except Exception as e:
        logger.error(f"❌ OCR failed: {e}", exc_info=True)
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

##### 1-3-4: 動作確認（2時間）
```bash
# テスト画像準備
python -c "
import base64
with open('test.png', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
    print(b64[:100])
"

# APIテスト
curl -X POST http://localhost:8000/api/v1/ocr/upload \
  -H 'Content-Type: application/json' \
  -d '{
    "image_b64": "iVBORw0KG...",
    "book_title": "Test Book"
  }'
```

**成果物**:
- ✅ OCRエンドポイント実装
- ✅ 画像→テキスト変換成功
- ✅ PostgreSQLにBLOB保存
- ✅ Job管理動作確認

---

### **Phase 1-4: 自動キャプチャエンドポイント実装**

**期間**: 1日（8時間）

**目標**: PyAutoGUI/Selenium自動キャプチャAPIエンドポイント

#### タスク詳細

##### 1-4-1: 自動キャプチャschema作成（1時間）
```python
# app/schemas/capture.py
class PyAutoGUICaptureRequest(BaseModel):
    book_title: str
    total_pages: int = Field(ge=1, le=1000)
    interval_seconds: float = Field(default=2.0, ge=0.5, le=10.0)
    capture_mode: str = "fullscreen"

class SeleniumCaptureRequest(BaseModel):
    book_url: str = Field(..., regex="^https://read.amazon.com/")
    book_title: str
    max_pages: int = Field(default=500, ge=1, le=1000)
```

##### 1-4-2: エンドポイント実装（3時間）
```python
# app/api/routers/ocr.py（追加）
@router.post("/auto-capture/pyautogui")
async def auto_capture_pyautogui(
    request: PyAutoGUICaptureRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Job作成
    job = Job(user_id=1, type="ocr", status="pending")
    db.add(job)
    db.commit()

    # バックグラウンドタスク登録
    background_tasks.add_task(
        run_pyautogui_capture,
        job.id,
        request
    )

    return {
        "job_id": job.id,
        "status": "pending",
        "message": "PyAutoGUIキャプチャを開始しました"
    }
```

##### 1-4-3: ジョブ状態取得エンドポイント（2時間）
```python
@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "error_message": job.error_message
    }
```

##### 1-4-4: 動作確認（2時間）
```bash
# PyAutoGUIテスト
curl -X POST http://localhost:8000/api/v1/ocr/auto-capture/pyautogui \
  -H 'Content-Type: application/json' \
  -d '{
    "book_title": "Test Book",
    "total_pages": 5
  }'

# ジョブ状態確認
curl http://localhost:8000/api/v1/ocr/jobs/{job_id}
```

**成果物**:
- ✅ 自動キャプチャエンドポイント
- ✅ バックグラウンドタスク動作
- ✅ ジョブ状態取得API

---

### **Phase 1-5: Celeryタスク実装（OCR処理）**

**期間**: 1日（8時間）

**目標**: CeleryでOCR処理をバックグラウンド実行

#### タスク詳細

##### 1-5-1: Celery設定（2時間）
```python
# app/tasks/celery_app.py
from celery import Celery
import os

celery_app = Celery(
    "kindle_ocr",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tokyo",
    enable_utc=True,
)
```

##### 1-5-2: OCRタスク実装（4時間）
```python
# app/tasks/ocr_tasks.py
from app.tasks.celery_app import celery_app
from app.services.capture import PyAutoGUICapture
from app.core.database import SessionLocal
from app.models import Job, OCRResult
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_pyautogui_capture(self, job_id: str, config: dict):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "running"
        db.commit()

        # PyAutoGUIキャプチャ実行
        capturer = PyAutoGUICapture(CaptureConfig(**config))
        result = capturer.capture_all_pages(
            progress_callback=lambda current, total: update_progress(job_id, current, total)
        )

        # OCR処理
        for i, image_path in enumerate(result.image_paths):
            ocr_result = OCRService().extract_text_from_file(image_path)

            db_result = OCRResult(
                job_id=job_id,
                book_title=config["book_title"],
                page_num=i+1,
                text=ocr_result["text"],
                confidence=ocr_result["confidence"],
                image_blob=open(image_path, "rb").read()
            )
            db.add(db_result)

        job.status = "completed"
        job.progress = 100
        db.commit()

        logger.info(f"✅ PyAutoGUI capture completed: {result.captured_pages} pages")

    except Exception as e:
        logger.error(f"❌ Task failed: {e}", exc_info=True)
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()
```

##### 1-5-3: 動作確認（2時間）
```bash
# Celery Worker起動
celery -A app.tasks.celery_app worker --loglevel=info

# タスク実行テスト
python -c "
from app.tasks.ocr_tasks import run_pyautogui_capture
result = run_pyautogui_capture.delay('job_id', {'book_title': 'Test'})
print(result.id)
"
```

**成果物**:
- ✅ Celery設定完了
- ✅ OCRタスク実装
- ✅ バックグラウンド処理動作確認

---

### **Phase 1-6: Streamlit UI実装（OCRページ）**

**期間**: 1.5日（12時間）

**目標**: Streamlit UIでOCR機能を使える

#### タスク詳細

##### 1-6-1: Streamlit基本構造（2時間）
```python
# app/ui/Home.py
import streamlit as st

st.set_page_config(
    page_title="Kindle OCR",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Kindle文字起こしツール")
st.markdown("ローカル環境専用 - v3.0")

st.sidebar.success("ページを選択してください")
```

##### 1-6-2: OCRページ実装（8時間）
```python
# app/ui/pages/1_OCR.py
import streamlit as st
import requests
import base64
from PIL import Image
import io

st.title("📸 OCR - 画像から文字起こし")

# タブ作成
tab1, tab2, tab3 = st.tabs(["手動アップロード", "デスクトップ版", "Cloud版"])

# 手動アップロード
with tab1:
    uploaded_file = st.file_uploader("画像をアップロード", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="アップロード画像", use_column_width=True)

        book_title = st.text_input("本のタイトル", value="Untitled")

        if st.button("OCR実行"):
            # Base64エンコード
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_b64 = base64.b64encode(buffer.getvalue()).decode()

            # API呼び出し
            response = requests.post(
                "http://localhost:8000/api/v1/ocr/upload",
                json={
                    "image_b64": image_b64,
                    "book_title": book_title
                }
            )

            if response.status_code == 200:
                result = response.json()
                st.success(f"✅ {result['message']}")
                st.json(result)
            else:
                st.error(f"❌ エラー: {response.text}")
```

##### 1-6-3: 動作確認（2時間）
```bash
# Streamlit起動
streamlit run app/ui/Home.py

# ブラウザでテスト
open http://localhost:8501
```

**成果物**:
- ✅ Streamlit UI起動
- ✅ OCRページ実装
- ✅ 手動アップロード動作確認

---

### **Phase 1-7: 統合テストと動作確認**

**期間**: 0.5日（4時間）

**目標**: 全体が正しく動作することを確認

#### タスク詳細

##### 1-7-1: エンドツーエンドテスト（2時間）
```bash
# 1. Docker Compose起動
docker-compose up -d

# 2. FastAPI確認
curl http://localhost:8000/api/v1/health

# 3. Streamlit確認
open http://localhost:8501

# 4. 画像アップロード→OCR実行
# （Streamlit UIで手動テスト）

# 5. データベース確認
docker-compose exec postgres psql -U kindle_user kindle_ocr
SELECT * FROM jobs;
SELECT * FROM ocr_results;
```

##### 1-7-2: ドキュメント更新（2時間）
- README.md更新
- Phase 1完了レポート作成
- 次ステップ（Phase 2）計画策定

**成果物**:
- ✅ 全サービス連携動作確認
- ✅ ドキュメント最新化
- ✅ Phase 1完了

---

## 📊 Phase 1 タイムライン

| Phase | 期間 | 累計 | 主要マイルストーン |
|-------|------|------|------------------|
| 1-1 | 1日 | 1日 | ✅ データベースモデル完成 |
| 1-2 | 0.5日 | 1.5日 | ✅ FastAPI基本動作 |
| 1-3 | 1日 | 2.5日 | ✅ OCR手動アップロード動作 |
| 1-4 | 1日 | 3.5日 | ✅ 自動キャプチャAPI動作 |
| 1-5 | 1日 | 4.5日 | ✅ Celeryバックグラウンド処理 |
| 1-6 | 1.5日 | 6日 | ✅ Streamlit UI動作 |
| 1-7 | 0.5日 | **6.5日** | ✅ Phase 1完了 |

**目標**: 7日以内完了（余裕0.5日）

---

## 🔧 Miyabi Agent活用計画

### CodeGenAgent
- SQLAlchemyモデル生成
- FastAPIエンドポイント生成
- Celeryタスク生成
- Streamlit UI生成

### ReviewAgent
- コードレビュー（各Phase完了時）
- セキュリティチェック
- パフォーマンスチェック

### TestAgent（Phase 2）
- 単体テスト生成
- 統合テスト生成

---

## ⚠️ リスク管理

### 高リスク項目
1. **pgvector動作確認**
   - 対策: Phase 1-1でテスト実施

2. **PyAutoGUI macOS権限**
   - 対策: システム環境設定で権限付与

3. **Celery設定ミス**
   - 対策: Phase 1-5で詳細確認

### エラー予防策
- 各Phaseで必ず動作確認
- ログ出力完備
- 型ヒント徹底
- エラーハンドリング完備

---

## 🎯 Phase 1 完了条件

- [ ] PostgreSQL 9テーブル作成済み
- [ ] FastAPI `/api/v1/health` 動作
- [ ] FastAPI `/api/v1/ocr/upload` 動作
- [ ] FastAPI `/api/v1/ocr/auto-capture/pyautogui` 動作
- [ ] FastAPI `/api/v1/ocr/jobs/{job_id}` 動作
- [ ] Celery Workerバックグラウンド処理動作
- [ ] Streamlit UI起動・OCRページ動作
- [ ] Docker Compose全サービス起動
- [ ] エンドツーエンドテスト成功

---

**計画作成日**: 2025-10-28
**作成者**: Matsumoto Toshihiko
**協力**: Claude Code + Miyabi Autonomous System

🤖 Generated with [Claude Code](https://claude.com/claude-code)
