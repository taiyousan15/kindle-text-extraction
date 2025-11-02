# Kindle文字起こしツール 要件定義書 v2.0（改善版）

> **改善日**: 2025-10-27
> **変更理由**: 技術的実現性の向上、Miyabi Agent完全対応、エラー処理強化

---

## **5W1Hサマリ**

* **Why（なぜ）**
   本や資料を読むほど**専門性が上がる**知識基盤を作り、あなたの質問に**実務的・根拠付き**で即回答するため。
   ※用語ミニ解説：**OCR=画像から文字を抽出**、**RAG=検索拡張生成（手元知識を検索してから回答）**、**トークン=AIが扱う文字数の単位**。

* **What（何を）**
   Kindle画面の**自動/手動OCR**→テキストの**ダウンロード**→必要に応じて**要約**→**ナレッジ化（YAML/JSON）**→**ビジネスナレッジ（専門学習RAG）**→**品質検証と再学習**まで。

* **Who（誰が）**
   オーナー：Matsumoto Toshihiko。ロール：Admin/Operator/Viewer（権限分離）。

* **When（いつ）**
   常時稼働、**自動再学習は毎日03:00（JST）**、CI/CDはPush/Tag時。

* **Where（どこで）**
   Backend: FastAPI、非同期: Celery+Redis、UI: Streamlit、ストレージ: S3互換＋**PostgreSQL（メタDB）**、デプロイ: Render/Cloud Run。

* **How（どうやって）**
   - **Phase 1（MVP）**: 手動画像アップロード or PyAutoGUI自動キャプチャ
   - **Phase 2（本格）**: Selenium + Kindle Cloud Reader完全自動化
   - **🧠 要約**／**📚 ナレッジ化**／**💼 ビジネスナレッジ**を必要に応じて実行
   - **⚡ 一括・全自動**で一気通貫も可能

---

## **📋 v1からの主要変更点**

### ✅ **追加・改善**
1. **自動キャプチャ2方式実装**
   - **PyAutoGUI方式**（Phase 1: MVP）
   - **Selenium + Kindle Cloud Reader方式**（Phase 2: 本格運用）

2. **データベース変更**
   - Google Sheets → **PostgreSQL**（スケーラビリティ向上）
   - Google Sheetsは「エクスポート機能」のみ残す

3. **エラー処理強化**
   - OCR失敗時のDPI自動調整＋再試行
   - LLMプロバイダー自動フォールバック
   - コスト管理の段階的アラート（80%/90%/100%）

4. **テストカバレッジの現実化**
   - バックエンドAPI: 90%
   - UI: 手動テスト手順書

### ❌ **削除**
- Notion同期機能（必要性不明のため削除）
- ホットキー機能（Phase 2に延期）

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

5. **進行状況**をWebSocketでリアルタイム表示

6. 完了後、全ページを自動OCR → 結果通知（Slack）

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

### **3. API設計（/api/v1、認証：JWT + x-api-key、レート：60rpm）**

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
      "password_encrypted": "..."
    }
  }
  ```

* **GET** `/jobs/{job_id}`：ジョブ状態・進捗・ログURL

#### **要約/ナレッジ**

* **POST** `/summary/generate`（粒度/長さ/トーン）

* **POST** `/knowledge/structure`（format: yaml|json、スキーマ検証）

#### **ビジネスナレッジ**

* **POST** `/biz/upload`（multipart/presigned）

* **POST** `/biz/ingest`（粒度・重複除去）

* **POST** `/biz/query`（{question, domain, depth, format}→answer_md+sources+confidence）

#### **再学習**

* **POST** `/relearn/trigger`（threshold=0.65、next_run=03:00）

---

### **共通エラー**

`400 VALIDATION_ERROR`／`401/403 UNAUTHORIZED`／`429 RATE_LIMIT`／`500 INTERNAL`（trace_id付与）

---

### **4. データ/DB**

#### **PostgreSQL（メタDB）**

テーブル:
- `users` (id, email, role, created_at)
- `jobs` (id, user_id, type, status, progress, created_at)
- `ocr_results` (id, job_id, page_num, text, confidence, s3_key)
- `knowledge` (id, book_title, format, score, s3_key, created_at)
- `biz_files` (id, filename, tags, s3_key, uploaded_at)
- `biz_cards` (id, file_id, content, vector_embedding, score, indexed_at)
- `feedbacks` (id, query, answer, rating, user_id, created_at)
- `retrain_queue` (id, card_id, score, queued_at, processed_at)

#### **S3互換ストレージ**

- `data/ocr/<book>/<page>.txt|png`
- `data/summary/<book>.md`
- `data/knowledge/<book>.yaml`
- `data/biz/<id>.yaml`
- `uploads/<uuid>.<ext>`

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

共通：`max_tokens`・`monthly_token_cap`・`retry=exp-backoff(3)`・`provider_qps=2rps`

---

### **6. セキュリティ/コスト/品質**

* **DRMは扱わない（画面OCRのみ）**、鍵は**環境変数**、パスワードは**bcrypt**。

* レート制限：API 60rpm、LLM呼出は内部QPS制御。

* **YAML/JSON構文100%検証、回答には出典・confidence**必須。

* **コスト管理段階的アラート**:
  - 80%: Slack警告通知
  - 90%: 要約・ナレッジ化機能制限 + 緊急通知
  - 100%: 全機能停止 + 管理者通知

---

### **7. 監視/メトリクス**

* `/healthz` `/metrics`（Prometheus互換）
* 主要メトリクス：
  - `ocr_jobs_total`
  - `ocr_auto_capture_success_rate`
  - `biz_cards_total`
  - `query_latency_ms`
  - `token_usage_total`
  - `relearn_runs_total`

---

## **フォルダ構成**

```
/app
  /api
    main.py
    deps.py
    /routers
      ocr.py
      summary.py
      knowledge.py
      biz.py
      relearn.py
  /agents
    ocr_master.py
    knowledge_synth.py
    quality_refiner.py
    verifier_ai.py
    biz_ingestor.py
    indexer.py
    rag_query.py
    meta_supervisor.py
    /schemas
      schema_knowledge.json
      schema_biz_knowledge.json
  /services
    storage_s3.py
    db_postgres.py
    pdf_service.py
    text_extractor.py
    vector_store.py
    rate_limit.py
    token_monitor.py
    /capture
      pyautogui_capture.py      # PyAutoGUI自動キャプチャ
      selenium_capture.py        # Selenium自動キャプチャ
      capture_factory.py         # キャプチャ方式の切替
  /tasks
    pipeline.py
    biz_pipeline.py
    capture_pipeline.py          # 自動キャプチャ用
    schedule.py
  /ui
    Home.py
    /pages
      1_OCR.py
      2_Text_Download.py
      3_Summary.py
      4_Knowledge.py
      5_Business_Knowledge.py
  /tests
    /test_api
      test_ocr.py
      test_ocr_auto_capture.py   # 自動キャプチャテスト
      test_biz_ingest.py
      test_biz_query.py
    /test_services
      test_pyautogui_capture.py
      test_selenium_capture.py
    test_yaml_schema.py
    test_rate_limits.py
  /configs
    logging.yaml
README.md
.env.sample
requirements.txt
Dockerfile
docker-compose.yml
```

---

## **依存関係（requirements.txt）**

```txt
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-jose[jwt]==3.3.0
python-multipart==0.0.6
slowapi==0.1.9

# 非同期処理
celery==5.3.4
redis==5.0.1
tenacity==8.2.3

# ストレージ
boto3==1.29.7
psycopg2-binary==2.9.9
sqlalchemy==2.0.23

# 通知
slack-sdk==3.23.0

# OCR
pytesseract==0.3.10
pillow==10.1.0

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

# UI
streamlit==1.28.2

# 開発・テスト
pytest==7.4.3
coverage==7.3.2
ruff==0.1.6
mypy==1.7.0
```

---

## **環境変数（.env.sample）**

```bash
APP_ENV=dev
JWT_SECRET=change_me_random_secret_key
API_KEY_MASTER=change_me_api_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/kindle_ocr

# Redis
REDIS_URL=redis://localhost:6379/0

# S3互換
S3_ENDPOINT=https://s3.wasabisys.com
S3_BUCKET=kindle-knowledge-v2
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# 通知
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# LLM API
CLAUDE_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
LLM_PROVIDER_PREFERENCE=auto

# コスト管理
MONTHLY_TOKEN_CAP=50000000
TOKEN_WARNING_THRESHOLD_PCT=80
TOKEN_CRITICAL_THRESHOLD_PCT=90

# Agent設定
MODEL_QPS_PER_PROVIDER=2
RELEARN_CRON=0 3 * * *
TIMEZONE=Asia/Tokyo

# Selenium（Cloud版キャプチャ用）
CHROME_DRIVER_PATH=/usr/local/bin/chromedriver
HEADLESS_MODE=true

# Amazon認証（暗号化保存推奨）
AMAZON_EMAIL_ENCRYPTED=base64_encrypted_email
AMAZON_PASSWORD_ENCRYPTED=base64_encrypted_password
```

---

## **デプロイ手順（Render推奨）**

### **前提**

* GitHub連携/Actions有効、Secretsに環境変数登録
* PostgreSQL（Render提供の無料プラン）
* Redis Cloud（無料プラン）
* Tesseract + Chrome Driver導入済みDockerfile

### **Renderサービス構成**

#### **1. Web Service（FastAPI）**
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`

#### **2. Worker（Celery - OCR/要約/ナレッジ）**
- Start: `celery -A app.tasks.pipeline worker -l info`

#### **3. Capture Worker（自動キャプチャ専用）**
- Start: `celery -A app.tasks.capture_pipeline worker -l info -Q capture`

#### **4. Biz Worker（Ingest/Index専用）**
- Start: `celery -A app.tasks.biz_pipeline worker -l info -Q biz`

#### **5. Beat（スケジューラ）**
- Start: `celery -A app.tasks.schedule beat -l info`

#### **6. PostgreSQL**
- Render提供の無料プラン（1GB）

#### **7. Redis**
- Redis Cloud無料プラン（30MB）

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
- ✅ OCRジョブがPostgreSQL記録・精度表示・S3保存
- ✅ 自動キャプチャがバックグラウンドで実行可能
- ✅ 要約・ナレッジがS3保存、score算出
- ✅ Biz ingestがカード数・低スコア数を返す
- ✅ `/biz/query`がsources/confidenceを返却
- ✅ `/relearn/trigger`後、03:00にQueue消化

### **セキュリティ/コスト**
- ✅ JWT+x-api-key、role判定、bcrypt
- ✅ レート60rpm/QPS2rps
- ✅ コスト段階的アラート（80%/90%/100%）
- ✅ 出典とconfidenceが全回答に付与

### **テスト**
- ✅ バックエンドAPI: coverage ≥ 90%
- ✅ 自動キャプチャ: モックテスト
- ✅ UI: 手動テスト手順書

---

## **ロードマップ**

### **Phase 1: MVP（7-10日）**
- 手動画像アップロード
- PyAutoGUI自動キャプチャ
- 基本OCR→要約→ナレッジ化
- PostgreSQL + S3
- Streamlit UI

### **Phase 2: 本格運用（+5-7日）**
- Selenium + Kindle Cloud Reader
- Celeryバックグラウンド処理
- ビジネスRAG完全実装
- CI/CD自動化
- 監視・アラート

### **Phase 3: 高度化（+3-5日）**
- WebSocketリアルタイム進捗
- ホットキー対応（Electron化検討）
- マルチユーザー対応
- 管理画面

---

**🎉 改善版要件定義書 完成**

次のステップ: 実装開始（Miyabi Agent フル活用）
