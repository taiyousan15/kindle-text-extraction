# Kindle文字起こしツール 要件定義書 v3.0（ローカル環境専用版）

> **改訂日**: 2025-10-27
> **改訂理由**: ローカル環境専用に簡素化、認証・デプロイ・S3削除、セットアップ簡易化
> **対象環境**: macOS（Docker Compose）

---

## **5W1Hサマリ**

* **Why（なぜ）**
   本や資料を読むほど**専門性が上がる**知識基盤を作り、あなたの質問に**実務的・根拠付き**で即回答するため。
   ※用語ミニ解説：**OCR=画像から文字を抽出**、**RAG=検索拡張生成（手元知識を検索してから回答）**、**トークン=AIが扱う文字数の単位**。

* **What（何を）**
   Kindle画面の**自動/手動OCR**→テキストの**ダウンロード**→必要に応じて**要約**→**ナレッジ化（YAML/JSON）**→**ビジネスナレッジ（専門学習RAG）**→**品質検証と再学習**まで。

* **Who（誰が）**
   オーナー：Matsumoto Toshihiko（ローカル単一ユーザー、認証なし）。

* **When（いつ）**
   常時稼働、**自動再学習は毎日03:00（JST）**。

* **Where（どこで）**
   **ローカルMac環境**: FastAPI（localhost:8000）、非同期: Celery+Redis（Docker）、UI: Streamlit（localhost:8501）、ストレージ: PostgreSQL（画像・テキスト含む）+ ローカルファイルシステム、実行環境: Docker Compose。

* **How（どうやって）**
   - **Phase 1（MVP）**: 手動画像アップロード or PyAutoGUI自動キャプチャ
   - **Phase 2（本格）**: Selenium + Kindle Cloud Reader完全自動化
   - **🧠 要約**／**📚 ナレッジ化**／**💼 ビジネスナレッジ**を必要に応じて実行
   - **⚡ 一括・全自動**で一気通貫も可能

---

## **📋 v2からの主要変更点**

### ✅ **ローカル環境最適化**
1. **デプロイ記述を全削除**
   - Render/Cloud Run等の記述削除
   - ローカル起動手順（Docker Compose）に統一

2. **認証削除**
   - JWT + x-api-key削除（単一ユーザーのため不要）
   - レート制限削除（ローカル環境のため不要）

3. **ストレージ簡素化**
   - S3互換ストレージ削除
   - PostgreSQL BYTEA + ローカルファイルシステムに統一

4. **通知簡素化**
   - Slack通知削除
   - Streamlit toast（ブラウザ通知）に統一

5. **環境変数削減**
   - 本番環境用変数削除
   - ローカル開発用のみ（10個→5個）

### ❌ **削除項目**
- S3互換ストレージ（boto3）
- Slack通知（slack-sdk）
- JWT認証（python-jose）
- レート制限（slowapi）
- CI/CD・GitHub Actions
- Render/Cloud Runデプロイ手順
- マルチユーザー対応

---

## **システム設計（具体イメージと操作方法つき）**

### **0. システムの具体像（言語で描くUIイメージ）**

* ブラウザで開くと左サイドバー：
   モデル選択（Auto/Claude/GPT/Gemini）／温度（0.0–2.0）／実行モード（手動/自動）

* 画面中央に大きなボタンが縦に並ぶ：
   **📸 画像をアップロード**（手動・最上段）
   **📚 まとめOCR（自動キャプチャ）**
   　├ 🖥️ デスクトップ版（PyAutoGUI）
   　└ ☁️ Cloud版（Selenium）
   **⬇️ ダウンロード（CSV/Excel/TXT/Googleスプレッドシート）**
   **🧠 要約する**／**📚 ナレッジ化**
   **💼 ビジネスナレッジ**（入力欄＋\[質問する\]）
   **⚡ 一括・全自動**

* 下部に「結果タブ」：**テキスト｜要約｜ナレッジ（YAML）｜ビジネス回答｜ログ｜履歴**

---

### **1. 操作方法（最初から最後まで）**

#### **A. 手動アップロード（最も簡単）**

1. **画像を準備**（Kindleスクリーンショット: Cmd+Shift+4）

2. **📸 画像をアップロード** → ドラッグ&ドロップ or ファイル選択

3. **OCR実行** → 数秒後に「テキスト」タブへ反映

4. **⬇️ ダウンロード**でCSV/Excel/TXT/スプレッドシートへ出力

5. 必要に応じて **🧠 要約する**（章/全体、長さ/トーンを指定）

6. さらに **📚 ナレッジ化**（YAML/JSON、構文100%検証）

7. **💼 ビジネスナレッジ**：質問を入力（例「AIのプロンプトの書き方を教えて」）→\[質問する\]

---

#### **B. 自動キャプチャ（Phase 1: PyAutoGUI）**

1. **Kindleアプリで本を開く**（1ページ目を表示）

2. **📚 まとめOCR** → **🖥️ デスクトップ版**を選択

3. 設定ダイアログ：
   - 本のタイトル: `プロンプトエンジニアリング入門`
   - 総ページ数: `200`
   - ページ送り間隔: `2.0秒`（スライダー）
   - キャプチャ範囲: `全画面` or `Kindleウィンドウのみ`

4. **🚀 開始**ボタン → 5秒カウントダウン

5. **自動実行**:
   - ページキャプチャ
   - 右矢印キー送信（次ページ）
   - 指定ページ数まで繰り返し

6. **進行状況**をリアルタイム表示（プログレスバー）

7. 完了後、全ページを自動OCR → テキストタブへ反映

---

#### **C. 自動キャプチャ（Phase 2: Selenium + Cloud Reader）**

1. **📚 まとめOCR** → **☁️ Cloud版**を選択

2. 設定ダイアログ：
   - Kindle Cloud ReaderのURL: `https://read.amazon.com/...`
   - 本のタイトル: `プロンプトエンジニアリング入門`
   - Amazonアカウント（初回のみ）:
     - メールアドレス
     - パスワード（暗号化保存）
   - 最大ページ数: `500`（自動検出も試行）

3. **🚀 開始**ボタン → バックグラウンドで実行

4. **Celery Worker**がバックグラウンドで処理:
   - ヘッドレスブラウザ起動
   - Amazon自動ログイン
   - 本を開く
   - ページキャプチャ → 次ページ → 繰り返し
   - 最終ページ検出で自動停止

5. **進行状況**をポーリングでリアルタイム表示

6. 完了後、全ページを自動OCR → **ブラウザ通知**（Streamlit toast）

---

#### **D. ⚡ 一括・全自動（慣れたら）**

* ダイアログで「要約の長さ・ナレッジ形式・出力先（CSV/Sheets）・通知」を指定→
   **OCR→要約→ナレッジ/ビジネスナレッジ→保存/通知**を自動で完走。

---

### **2. 画面仕様（5ページ+共通）**

* **P1: OCR**：
  - 手動アップロード
  - 自動キャプチャ（デスクトップ版/Cloud版）
  - 進行状況・精度表示
  - しきい値/再試行設定

* **P2: テキスト&ダウンロード**：章/ページ切替、CSV/Excel/TXT/Sheetsへ出力

* **P3: 要約**：粒度/長さ/トーン、プレビュー→保存

* **P4: ナレッジ化**：YAML/JSON（`root: {meta, items[]}`）、構文100%検証、スコア表示

* **P5: ビジネスナレッジ**：**\[外部ファイルを取り込む\]**／入力欄＋**\[質問する\]**／出典・信頼度表示

---

### **3. API設計（/api/v1、認証なし（ローカル単一ユーザー））**

#### **OCR**

* **POST** `/ocr/upload`：手動画像アップロード
  ```json
  {
    "image_b64": "<base64>",
    "book_title": "Book A",
    "options": {
      "lang": "ja+en",
      "dpi": 300,
      "layout": "paragraph"
    }
  }
  ```

* **POST** `/ocr/auto-capture/pyautogui`：PyAutoGUI自動キャプチャ
  ```json
  {
    "book_title": "Book A",
    "total_pages": 200,
    "interval_seconds": 2.0,
    "capture_mode": "fullscreen"
  }
  ```
  → 返却: `{ "job_id": "abc-123", "status": "running" }`

* **POST** `/ocr/auto-capture/selenium`：Selenium自動キャプチャ
  ```json
  {
    "book_url": "https://read.amazon.com/...",
    "book_title": "Book A",
    "max_pages": 500,
    "credentials": {
      "email": "user@example.com",
      "password": "plain_text_password"
    }
  }
  ```

* **GET** `/jobs/{job_id}`：ジョブ状態・進捗・ログURL

#### **要約/ナレッジ**

* **POST** `/summary/generate`（粒度/長さ/トーン）

* **POST** `/knowledge/structure`（format: yaml|json、スキーマ検証）

#### **ビジネスナレッジ**

* **POST** `/biz/upload`（multipart）

* **POST** `/biz/ingest`（粒度・重複除去）

* **POST** `/biz/query`（{question, domain, depth, format}→answer_md+sources+confidence）

#### **再学習**

* **POST** `/relearn/trigger`（threshold=0.65、next_run=03:00）

---

### **共通エラー**

`400 VALIDATION_ERROR`／`500 INTERNAL`（trace_id付与）

---

### **4. データ/DB**

#### **PostgreSQL（すべてのデータを保存）**

テーブル:
```sql
-- ユーザー（単一ユーザーだが将来拡張用）
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ジョブ（OCR・要約・ナレッジ化のタスク管理）
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(50) NOT NULL,  -- 'ocr', 'summary', 'knowledge', 'biz_ingest'
    status VARCHAR(50) NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
    progress INTEGER DEFAULT 0,  -- 0-100
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- OCR結果（画像BLOBも保存）
CREATE TABLE ocr_results (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    book_title VARCHAR(255) NOT NULL,
    page_num INTEGER NOT NULL,
    text TEXT NOT NULL,
    confidence FLOAT,
    image_blob BYTEA,  -- 画像をBLOBで保存
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(job_id, page_num)
);

-- 要約結果
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    book_title VARCHAR(255) NOT NULL,
    summary_text TEXT NOT NULL,
    granularity VARCHAR(50),  -- 'chapter', 'full'
    length VARCHAR(50),  -- 'short', 'medium', 'long'
    tone VARCHAR(50),  -- 'formal', 'casual'
    created_at TIMESTAMP DEFAULT NOW()
);

-- ナレッジ（YAML/JSON構造化データ）
CREATE TABLE knowledge (
    id SERIAL PRIMARY KEY,
    book_title VARCHAR(255) NOT NULL,
    format VARCHAR(10) NOT NULL,  -- 'yaml', 'json'
    score FLOAT,
    yaml_text TEXT NOT NULL,  -- YAML/JSONテキスト
    content_blob BYTEA,  -- バイナリ形式でも保存（オプション）
    created_at TIMESTAMP DEFAULT NOW()
);

-- ビジネスナレッジファイル
CREATE TABLE biz_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    tags TEXT[],
    file_blob BYTEA NOT NULL,  -- ファイル本体をBLOBで保存
    file_size INTEGER,
    mime_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- ビジネスナレッジカード（RAG用）
CREATE TABLE biz_cards (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES biz_files(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    vector_embedding VECTOR(384),  -- pgvector拡張使用
    score FLOAT,
    indexed_at TIMESTAMP DEFAULT NOW()
);

-- フィードバック（学習データ）
CREATE TABLE feedbacks (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 再学習キュー
CREATE TABLE retrain_queue (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES biz_cards(id) ON DELETE CASCADE,
    score FLOAT,
    queued_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

**pgvector拡張のインストール**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### **ローカルファイルシステム**（バックアップ・デバッグ用）

```
captures/<book>/<page>.png      # PyAutoGUI/Seleniumキャプチャ保存先
uploads/<uuid>.<ext>             # 一時アップロード
logs/app.log                     # アプリケーションログ
exports/<book>.csv|excel|txt     # ダウンロードファイル
backups/kindle_ocr_YYYYMMDD.sql  # PostgreSQLバックアップ
```

※メインデータはPostgreSQLに保存、ファイルシステムはバックアップ・デバッグ用

---

### **5. エージェント**

* **OCRMaster**（画像OCR/補正/DPI自動調整）
* **KnowledgeSynth**（要約/構造化）
* **QualityRefiner**（自己評価・再生成）
* **VerifierAI**（軽ファクトチェック）
* **BizIngestor**（TXT/MD/PDF→カード化・重複除去）
* **Indexer**（ベクトル索引 - FAISS）
* **RagQuery**（統合回答）
* **RelearnManager**（0.65未満を夜間処理）
* **MetaSupervisor**（モデル最適化・プロバイダーフォールバック）

共通：`max_tokens`・`monthly_token_cap`・`retry=exp-backoff(3)`

---

### **6. セキュリティ/コスト/品質**

* **DRMは扱わない（画面OCRのみ）**、鍵は**環境変数**。

* **認証なし**（ローカル単一ユーザー）。

* **YAML/JSON構文100%検証、回答には出典・confidence**必須。

* **コスト管理段階的アラート**:
  - 80%: ブラウザ警告通知（Streamlit toast）
  - 90%: 要約・ナレッジ化機能制限 + 緊急通知
  - 100%: 全機能停止 + 管理者通知

---

### **7. 監視/メトリクス**

* `/healthz`（FastAPIヘルスチェック）
* ログファイル: `logs/app.log`（ローテーション: 7日間保持）

主要メトリクス（ログ出力）:
- `ocr_jobs_total`
- `ocr_auto_capture_success_rate`
- `biz_cards_total`
- `query_latency_ms`
- `token_usage_total`
- `relearn_runs_total`

---

## **フォルダ構成**

```
/Kindle文字起こしツール
├── .claude/                     # Miyabi Agent設定
├── .env                         # 環境変数（setup_wizardで生成）
├── .gitignore                   # Git除外設定
├── Dockerfile                   # Dockerイメージ定義
├── docker-compose.yml           # 複数サービス管理
├── alembic.ini                  # DBマイグレーション設定
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   ├── README
│   └── versions/                # マイグレーションファイル
├── setup_wizard.py              # セットアップウィザード
├── requirements.txt             # Python依存関係
├── app/
│   ├── core/
│   │   └── database.py          # PostgreSQL接続プール
│   ├── api/
│   │   ├── main.py
│   │   ├── deps.py
│   │   └── routers/
│   │       ├── ocr.py
│   │       ├── summary.py
│   │       ├── knowledge.py
│   │       ├── biz.py
│   │       └── relearn.py
│   ├── models/                  # SQLAlchemyモデル
│   │   ├── user.py
│   │   ├── job.py
│   │   ├── ocr_result.py
│   │   ├── summary.py
│   │   ├── knowledge.py
│   │   ├── biz_file.py
│   │   ├── biz_card.py
│   │   ├── feedback.py
│   │   └── retrain_queue.py
│   ├── agents/
│   │   ├── ocr_master.py
│   │   ├── knowledge_synth.py
│   │   ├── quality_refiner.py
│   │   ├── verifier_ai.py
│   │   ├── biz_ingestor.py
│   │   ├── indexer.py
│   │   ├── rag_query.py
│   │   └── meta_supervisor.py
│   ├── services/
│   │   ├── storage_local.py     # ローカルファイルストレージ
│   │   ├── pdf_service.py
│   │   ├── text_extractor.py
│   │   ├── vector_store.py
│   │   ├── token_monitor.py
│   │   └── capture/
│   │       ├── pyautogui_capture.py
│   │       ├── selenium_capture.py
│   │       └── capture_factory.py
│   ├── tasks/
│   │   ├── pipeline.py
│   │   ├── biz_pipeline.py
│   │   ├── capture_pipeline.py
│   │   └── schedule.py
│   ├── ui/
│   │   ├── Home.py
│   │   └── pages/
│   │       ├── 1_OCR.py
│   │       ├── 2_Text_Download.py
│   │       ├── 3_Summary.py
│   │       ├── 4_Knowledge.py
│   │       └── 5_Business_Knowledge.py
│   └── tests/
│       ├── test_api/
│       │   ├── test_ocr.py
│       │   ├── test_ocr_auto_capture.py
│       │   ├── test_biz_ingest.py
│       │   └── test_biz_query.py
│       ├── test_services/
│       │   ├── test_pyautogui_capture.py
│       │   └── test_selenium_capture.py
│       ├── test_yaml_schema.py
│       └── test_models.py
├── captures/                    # キャプチャ画像保存先
├── uploads/                     # アップロード一時保存
├── logs/                        # ログファイル
├── exports/                     # ダウンロードファイル
├── backups/                     # PostgreSQLバックアップ
├── IMPLEMENTATION_SUMMARY.md    # 実装サマリー
├── DEPLOYMENT_READY_REPORT.md   # デプロイレポート
├── QUICK_START.md               # クイックスタート
└── README.md
```

---

## **依存関係（requirements.txt）**

```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pgvector==0.2.4  # ベクトル検索拡張

# 非同期処理
celery==5.3.4
redis==5.0.1
tenacity==8.2.3

# OCR
pytesseract==0.3.10
pillow==10.1.0
opencv-python==4.8.1.78

# PDF処理
pymupdf==1.23.7
pdfplumber==0.10.3
pypdf==3.17.1

# 自動キャプチャ
pyautogui==0.9.54
selenium==4.15.2
webdriver-manager==4.0.1

# データ処理
pyyaml==6.0.1
jsonschema==4.20.0

# ベクトル検索
sentence-transformers==2.2.2
faiss-cpu==1.7.4
rapidfuzz==3.5.2

# LLM
anthropic==0.7.4
openai==1.3.7
langchain==0.0.340
langchain-community==0.0.6
langchain-anthropic==0.0.2
langchain-openai==0.0.2

# UI
streamlit==1.28.2

# ユーティリティ
python-dotenv==1.0.0
python-dateutil==2.8.2
python-multipart==0.0.6

# 開発・テスト
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.11.0
ruff==0.1.6
mypy==1.7.0
```

---

## **環境変数（.env）**

```bash
# ==================== アプリケーション設定 ====================
APP_ENV=local
LOG_LEVEL=INFO
TIMEZONE=Asia/Tokyo

# ==================== Database ====================
DATABASE_URL=postgresql://kindle_user:kindle_password@localhost:5432/kindle_ocr
DB_USER=kindle_user
DB_PASSWORD=kindle_password
DB_NAME=kindle_ocr
DB_HOST=localhost
DB_PORT=5432

# ==================== Redis ====================
REDIS_URL=redis://localhost:6379/0

# ==================== LLM API ====================
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...  # オプション

# ==================== コスト管理 ====================
MONTHLY_TOKEN_CAP=10000000  # 1000万トークン/月（約$30相当）
TOKEN_WARNING_THRESHOLD_PCT=80
TOKEN_CRITICAL_THRESHOLD_PCT=90

# ==================== Amazon認証（Selenium用） ====================
AMAZON_EMAIL=your-email@example.com
AMAZON_PASSWORD=your-password

# ==================== Agent設定 ====================
RELEARN_CRON=0 3 * * *  # 毎日03:00に再学習実行

# ==================== Tesseract ====================
TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
```

---

## **ローカル起動手順（3ステップ）**

### **方法1: Docker Compose起動（推奨）**

```bash
# ステップ1: セットアップウィザード実行
cd /Users/matsumototoshihiko/div/Kindle文字起こしツール
python3 setup_wizard.py

# ステップ2: Docker起動
docker-compose up -d

# ステップ3: ブラウザでアクセス
open http://localhost:8501  # Streamlit UI
open http://localhost:8000/docs  # FastAPI Swagger UI
```

**起動するサービス**:
- PostgreSQL（データベース + pgvector拡張）
- Redis（タスクキュー）
- FastAPI（バックエンドAPI）
- Celery Worker（OCR/RAG処理）
- Streamlit（Web UI）

---

### **方法2: Python直接実行（Dockerなし）**

```bash
# 前提: PostgreSQL, Redis がローカルにインストール済み
# PostgreSQLにpgvector拡張をインストール:
# psql -U postgres -c "CREATE EXTENSION vector;"

# ステップ1: 依存関係インストール
pip install -r requirements.txt

# ステップ2: データベースマイグレーション
alembic upgrade head

# ステップ3: 各サービスを別ターミナルで起動
# Terminal 1: FastAPI
uvicorn app.api.main:app --reload --port 8000

# Terminal 2: Celery Worker
celery -A app.tasks.pipeline worker -l info

# Terminal 3: Streamlit UI
streamlit run app/ui/Home.py
```

---

### **停止・再起動**

```bash
# 停止
docker-compose down

# 再起動
docker-compose restart

# ログ確認
docker-compose logs -f api
docker-compose logs -f celery_worker

# 特定サービスのみ再起動
docker-compose restart api
```

---

### **データバックアップ**

```bash
# PostgreSQLダンプ（全データバックアップ）
docker-compose exec postgres pg_dump -U kindle_user kindle_ocr > backups/backup_$(date +%Y%m%d).sql

# リストア
cat backups/backup_20251027.sql | docker-compose exec -T postgres psql -U kindle_user kindle_ocr

# 画像ファイルバックアップ
tar -czf backups/captures_$(date +%Y%m%d).tar.gz captures/
```

---

### **トラブルシューティング**

#### **Docker起動エラー**

```bash
# ログ確認
docker-compose logs

# コンテナ状態確認
docker-compose ps

# 完全リセット（データ削除注意）
docker-compose down -v
docker-compose up -d
```

#### **PostgreSQL接続エラー**

```bash
# PostgreSQL接続確認
docker-compose exec postgres pg_isready

# 手動接続テスト
docker-compose exec postgres psql -U kindle_user kindle_ocr

# Python接続テスト
python -c "from app.core.database import check_connection; check_connection()"
```

#### **Celery Workerが動かない**

```bash
# Redisリソース確認
docker-compose exec redis redis-cli ping

# Celeryログ確認
docker-compose logs celery_worker

# 手動タスク実行テスト
python -c "from app.tasks.pipeline import test_task; test_task.delay()"
```

#### **OCR精度が低い**

- DPI設定を300→600に変更
- 画像前処理を有効化（opencv-python）
- Tesseract設定の最適化

---

## **受け入れ基準**

### **UI**
- ✅ **📸 画像をアップロード**が正常動作
- ✅ **📚 まとめOCR（デスクトップ版）**でPyAutoGUI自動キャプチャ成功
- ✅ **📚 まとめOCR（Cloud版）**でSelenium自動キャプチャ成功
- ✅ **⬇️ダウンロード**でCSV/Excel/TXT/Sheets出力
- ✅ **🧠要約／📚ナレッジ化**が粒度/形式/構文検証に準拠
- ✅ **💼ビジネスナレッジ**：外部ファイル取込み→質問が一連で成功
- ✅ **⚡一括・全自動**がOCR→要約→（ビジネス）ナレッジ→保存/通知を完走

### **機能**
- ✅ OCRジョブがPostgreSQL記録・精度表示・BLOB保存
- ✅ 自動キャプチャがバックグラウンドで実行可能
- ✅ 要約・ナレッジがPostgreSQL保存、score算出
- ✅ Biz ingestがカード数・低スコア数を返す
- ✅ `/biz/query`がsources/confidenceを返却
- ✅ `/relearn/trigger`後、03:00にQueue消化

### **コスト管理**
- ✅ コスト段階的アラート（80%/90%/100%） → ブラウザ通知
- ✅ 出典とconfidenceが全回答に付与

### **テスト**
- ✅ バックエンドAPI: coverage ≥ 80%
- ✅ 自動キャプチャ: モックテスト
- ✅ UI: 手動テスト手順書

---

## **ロードマップ**

### **Phase 1: MVP（7-10日）**
- ✅ 手動画像アップロード
- ✅ PyAutoGUI自動キャプチャ
- 🔄 基本OCR→要約→ナレッジ化
- 🔄 PostgreSQL + ローカルファイルシステム
- 🔄 Streamlit UI
- 🔄 Docker Compose環境構築

### **Phase 2: 本格運用（+5-7日）**
- Selenium + Kindle Cloud Reader
- Celeryバックグラウンド処理最適化
- ビジネスRAG完全実装（pgvector + FAISS）
- 画像前処理（DPI調整・ノイズ除去）
- エラーハンドリング強化

### **Phase 3: 高度化（+3-5日）**
- ポーリングからWebSocketリアルタイム進捗へ移行
- ホットキー対応（Electron化検討）
- データエクスポート強化（Google Sheets API連携）
- バックアップ自動化（cron）
- テストカバレッジ90%達成

---

## **コスト試算（ローカル環境）**

| 項目 | コスト | 備考 |
|------|--------|------|
| **ローカル開発環境** | $0/月 | Docker Desktop無料版 |
| **LLM API使用料** | $10-30/月 | 1000万トークン想定 |
| **ストレージ** | $0 | ローカルSSD使用 |
| **合計** | **$10-30/月** | LLM使用量次第 |

**削減額**: デプロイ環境から $26/月 → **ローカル専用で$26削減**

---

## **補足資料**

### **pgvector拡張のセットアップ**

```sql
-- PostgreSQLにログイン
psql -U kindle_user kindle_ocr

-- pgvector拡張インストール
CREATE EXTENSION IF NOT EXISTS vector;

-- ベクトルインデックス作成（高速検索用）
CREATE INDEX ON biz_cards USING ivfflat (vector_embedding vector_cosine_ops);
```

### **Tesseract日本語データインストール**

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian（Dockerfile内で自動実行）
apt-get install tesseract-ocr tesseract-ocr-jpn

# 確認
tesseract --list-langs
```

---

**🎉 ローカル環境専用v3.0 要件定義書 完成**

**次のステップ**: Phase 1 MVP実装開始（Miyabi Agent フル活用）

- SQLAlchemyモデル実装（8テーブル）
- FastAPI エンドポイント実装
- Streamlit UI実装
- Celery タスク実装

---

**作成日**: 2025-10-27
**作成者**: Matsumoto Toshihiko
**協力**: Claude Code + Miyabi Autonomous System

🤖 Generated with [Claude Code](https://claude.com/claude-code)
