**5W1Hサマリ**

* Why（なぜ）  
   本や資料を読むほど**専門性が上がる**知識基盤を作り、あなたの質問に**実務的・根拠付き**で即回答するため。  
   ※用語ミニ解説：**OCR=画像から文字を抽出**、**RAG=検索拡張生成（手元知識を検索してから回答）**、**トークン=AIが扱う文字数の単位**。

* What（何を）  
   Kindle画面の**即時OCR**→テキストの**ダウンロード**→必要に応じて**要約**→**ナレッジ化（YAML/JSON）**→**ビジネスナレッジ（専門学習RAG）**→**品質検証と再学習**まで。

* Who（誰が）  
   オーナー：Matsumoto Toshihiko。ロール：Admin/Operator/Viewer（権限分離）。

* When（いつ）  
   常時稼働、Notion同期30分毎、**自動再学習は毎日03:00（JST）**、CI/CDはPush/Tag時。

* Where（どこで）  
   Backend: FastAPI、非同期: Celery+Redis、UI: Streamlit、ストレージ: S3互換＋Google Sheets（メタDB）、デプロイ: Render/Cloud Run。

* How（どうやって）  
   「**📖 いま表示中を文字起こし**」ボタン/ホットキーで画面OCR→保存。  
   **🧠 要約**／**📚 ナレッジ化**／**💼 ビジネスナレッジ**を必要に応じて実行。  
   **⚡ 一括・全自動**で一気通貫も可能。TXT/MD/PDFも学習に取り込み、質問には**出典・信頼度**付きで回答。

≪ここまで≫

---

≪設計図MD：コピーここから≫  
 貼り先: 参考（アーキテクチャ共有）

# **システム設計（具体イメージと操作方法つき）**

## **0\. システムの具体像（言語で描くUIイメージ）**

* ブラウザで開くと左サイドバー：  
   モデル選択（Auto/Claude/GPT/Gemini）／温度（0.0–2.0）／煽り度（1–10）／実行モード（手動/一括全自動）

* 画面中央に大きなボタンが縦に並ぶ：  
   **📖 いま表示中を文字起こし**（最上段・強調）  
   **📚 まとめOCR（自動ページ送り）**  
   **⬇️ ダウンロード（CSV/Excel/TXT/Googleスプレッドシート）**  
   **🧠 要約する**／**📚 ナレッジ化**  
   **💼 ビジネスナレッジ**（入力欄＋\[質問する\]）  
   **⚡ 一括・全自動**

* 下部に「結果タブ」：**テキスト｜要約｜ナレッジ（YAML）｜ビジネス回答｜ログ｜履歴**

* 右上に通知ベル（Slack/メール）、ヘルプ（90秒クイック動画）

## **1\. 操作方法（最初から最後まで）**

### **A. 手動ステップ（初回おすすめ）**

1. **Kindleで本を開く**（表示中ページがOCR対象）

2. **📖 いま表示中を文字起こし** → 数秒後に「テキスト」タブへ反映

   * 次ページへ進み、同ボタン（またはホットキー）で繰り返し

   * まとまって処理したいときは **📚 まとめOCR**（自動ページ送り・上限/間隔を設定）

3. **⬇️ ダウンロード**でCSV/Excel/TXT/スプレッドシートへ出力

4. 必要に応じて **🧠 要約する**（章/全体、長さ/トーンを指定）

5. さらに **📚 ナレッジ化**（YAML/JSON、構文100%検証）

6. **💼 ビジネスナレッジ**：入力欄に質問（例「AIのプロンプトの書き方を教えて」）→\[質問する\]

   * 回答は **原則→フレーム→テンプレ→注意点→チェックリスト**＋**出典/信頼度**

   * **👍/👎・学習に追加・修正して保存**で好みを学習（夜間に自動強化）

### **B. ⚡ 一括・全自動（慣れたら）**

* ダイアログで「要約の長さ・ナレッジ形式・出力先（CSV/Sheets）・通知」を指定→  
   **OCR→要約→ナレッジ/ビジネスナレッジ→保存/通知**を自動で完走。

* まとめ画面に精度/構文検証/リンクが集約表示。

### **C. 外部ファイル（TXT/MD/PDF）の学習**

1. **💼 ビジネスナレッジ**タブ→**\[外部ファイルを取り込む\]**（複数OK）

2. テーマタグ（`copywriting`, `prompt`, `marketing`など）・粒度（章/節/見出し）・重複除去ONを指定

3. 取込み→カード化→索引→採点（0.0–1.0）。低スコアは**03:00**に再学習。

4. 以後の質問で**Kindle由来＋外部ファイル由来**の知識が横断的に使われる。

## **2\. 画面仕様（5ページ+共通）**

* **P1: OCR**：単頁/まとめ、進行状況・精度、しきい値/再試行

* **P2: テキスト&ダウンロード**：章/ページ切替、CSV/Excel/TXT/Sheetsへ出力

* **P3: 要約**：粒度/長さ/トーン、プレビュー→保存

* **P4: ナレッジ化**：YAML/JSON（`root: {meta, items[]}`）、構文100%検証、スコア表示

* **P5: ビジネスナレッジ**：**\[外部ファイルを取り込む\]**／入力欄＋**\[質問する\]**／出典・信頼度表示

## **3\. API設計（/api/v1、認証：JWT \+ x-api-key、レート：60rpm）**

* OCR

  * **POST** `/ocr/current`：単頁OCR（image\_b64/オプション）

  * **POST** `/ocr/batch`：連続OCR

  * **GET** `/jobs/{job_id}`：状態・精度・ログURL

* 要約/ナレッジ

  * **POST** `/summary/generate`（粒度/長さ/トーン）

  * **POST** `/knowledge/structure`（format: yaml|json、スキーマ検証）

* ビジネスナレッジ

  * **POST** `/biz/upload`（multipart/presigned）

  * **POST** `/biz/ingest`（粒度・重複除去）

  * **POST** `/biz/query`（{question, domain, depth, format}→answer\_md+sources+confidence）

* 同期・再学習

  * **POST** `/notion/sync`、**POST** `/relearn/trigger`（threshold=0.65、next\_run=03:00）

### **共通エラー**

`400 VALIDATION_ERROR`／`401/403 UNAUTHORIZED`／`429 RATE_LIMIT`／`500 INTERNAL`（trace\_id付与）

## **4\. データ/DB**

* **S3**：  
   `data/ocr/<book>/<page>.txt|png`／`data/summary/<book>.md`／`data/knowledge/<book>.yaml`／`data/biz/<id>.yaml`／`uploads/<uuid>.<ext>`

* **Google Sheets（メタDB）**：Users / Jobs / Knowledge / BizFiles / BizCards / Feedbacks / RetrainQueue

* 制約：ID一意、score∈\[0,1\]、role固定、APIキーは**ハッシュのみ**保存

## **5\. エージェント**

* **OCRMaster**（画面OCR/補正）、**KnowledgeSynth**（要約/構造化）、**QualityRefiner**（自己評価・再生成）、**VerifierAI**（軽ファクトチェック）、**BizIngestor**（TXT/MD/PDF→カード化・重複除去）、**Indexer**（ベクトル索引）、**RagQuery**（統合回答）、**RelearnManager**（0.65未満を夜間処理）、**MetaSupervisor**（モデル最適化）。

* 共通：`max_tokens`・`monthly_token_cap`・`retry=exp-backoff(3)`・`provider_qps=2rps`

## **6\. セキュリティ/コスト/品質**

* **DRMは扱わない（画面OCRのみ）**、鍵は**環境変数**、パスワードは**bcrypt**。

* レート制限：API 60rpm、LLM呼出は内部QPS制御。

* **YAML/JSON構文100%検証、回答には出典・confidence**必須。

* 月間トークン上限超過で**自動停止＋Slack通知**。

## **7\. 監視/メトリクス**

* `/healthz` `/metrics`（Prometheus互換）。主要メトリクス：`ocr_jobs_total`、`biz_cards_total`、`query_latency_ms`、`token_usage_total`、`relearn_runs_total`。

≪ここまで≫

---

≪Claudecode実装タスク指示書：コピーここから≫  
 貼り先: Claudecode 新規チャット冒頭

# **目的**

Kindle画面OCR→DL→要約/ナレッジ→**ビジネスナレッジ（RAG）**→根拠付き回答までを、FastAPI+Celery+Redis+S3+Sheets+Streamlitで実装。

# **完成定義（DoD）**

* 主要API（OCR/summary/knowledge/biz-upload|ingest|query/relearn/notion）が**JWT+x-api-key必須**で動作。

* **📖 いま表示中を文字起こし**がホットキーで即時OCR。

* **/biz/query** が **原則→フレーム→テンプレ→注意→チェック**＋**sources/confidence**を返す。

* YAML/JSONは**構文100%**、score\<0.65はRetrainQueueへ。Coverage≥95%。

# **フォルダ構成**

`/app`  
  `/api`  
    `main.py  deps.py`  
    `routers/ ocr.py  summary.py  knowledge.py  biz.py  relearn.py  notion.py`  
  `/agents`  
    `ocr_master.py  knowledge_synth.py  quality_refiner.py  verifier_ai.py`  
    `biz_ingestor.py  indexer.py  rag_query.py  meta_supervisor.py`  
    `schemas/ schema_knowledge.json  schema_biz_knowledge.json`  
  `/services`  
    `storage_s3.py  sheets_db.py  pdf_service.py  text_extractor.py  vector_store.py  rate_limit.py`  
  `/tasks`  
    `pipeline.py  biz_pipeline.py  schedule.py`  
  `/ui`  
    `Home.py`  
    `Pages/ 1_OCR.py  2_Text_Download.py  3_Summary.py  4_Knowledge.py  5_Business_Knowledge.py`  
  `/tests`  
    `test_api_ocr.py  test_api_biz_ingest.py  test_api_biz_query.py`  
    `test_yaml_schema.py  test_rate_limits.py`  
  `/configs`  
    `logging.yaml`  
`README.md  .env.sample`

# **依存**

fastapi, uvicorn, pydantic, python-jose\[jwt\], slowapi, celery, redis, tenacity,  
 boto3, gspread, google-auth, slack\_sdk, notion-client,  
 pytesseract, pillow, pymupdf|pdfplumber, pypdf,  
 pyyaml, jsonschema, sentence-transformers, faiss-cpu|chromadb, rapidfuzz,  
 pytest, coverage, ruff, mypy

# **環境変数（.env.sample）**

`APP_ENV=dev`  
`JWT_SECRET=change_me`  
`API_KEY_MASTER=change_me`  
`REDIS_URL=redis://...`  
`S3_ENDPOINT=https://...`  
`S3_BUCKET=ai-knowledge-v4`  
`S3_ACCESS_KEY=...`  
`S3_SECRET_KEY=...`  
`SHEETS_CREDENTIALS_JSON_BASE64=...`  
`NOTION_TOKEN=...`  
`SLACK_WEBHOOK_URL=...`  
`CLAUDE_API_KEY=...`  
`OPENAI_API_KEY=...`  
`GEMINI_API_KEY=...`  
`LLM_PROVIDER_PREFERENCE=auto`  
`MONTHLY_TOKEN_CAP=50000000`  
`MODEL_QPS_PER_PROVIDER=2`  
`RELEARN_CRON=0 3 * * *`  
`TIMEZONE=Asia/Tokyo`

# **最初に出力するファイル**

1. `README.md`（起動・Tesseract導入・ホットキー・法的注意）

2. `.env.sample`

3. `app/api/main.py`（/healthz, /metrics, 認証/レート制限の骨組み）

4. `app/agents/schemas/schema_knowledge.json`・`schema_biz_knowledge.json`

5. `app/ui/Pages/5_Business_Knowledge.py`（取り込み＋質問UI雛形）

# **エンドポイント & curl例**

* **OCR（単頁）**

`curl -X POST https://<host>/api/v1/ocr/current \`  
 `-H "Authorization: Bearer $JWT" -H "x-api-key: $KEY" -H "Content-Type: application/json" \`  
 `-d '{ "image_b64":"<...>", "book_title":"Book A",`  
       `"options":{"lang":"ja+en","dpi":300,"layout":"paragraph"} }'`

* **要約**

`curl -X POST https://<host>/api/v1/summary/generate \`  
 `-H "Authorization: Bearer $JWT" -H "x-api-key: $KEY" \`  
 `-d '{ "s3_keys":["data/ocr/BookA/1.txt"], "granularity":"chapter",`  
       `"tone":"neutral", "length":"medium" }'`

* **ナレッジ化**

`curl -X POST https://<host>/api/v1/knowledge/structure \`  
 `-H "Authorization: Bearer $JWT" -H "x-api-key: $KEY" \`  
 `-d '{ "text_keys":["data/ocr/BookA/*.txt"], "format":"yaml", "schema":"BOOK_RICH" }'`

* **ビジネス：アップロード→取込み→質問**

`curl -X POST https://<host>/api/v1/biz/upload \`  
 `-H "Authorization: Bearer $JWT" -H "x-api-key: $KEY" \`  
 `-F "file=@notes.md" -F "tags=copywriting"`

`curl -X POST https://<host>/api/v1/biz/ingest \`  
 `-H "Authorization: Bearer $JWT" -H "x-api-key: $KEY" \`  
 `-d '{ "file_keys":["uploads/notes.md"], "granularity":"section", "dedupe":true }'`

`curl -X POST https://<host>/api/v1/biz/query \`  
 `-H "Authorization: Bearer $JWT" -H "x-api-key: $KEY" -H "Content-Type: application/json" \`  
 `-d '{ "question":"AIのプロンプトの書き方を教えて",`  
       `"domain":"prompting", "depth":"pro", "format":"mixed" }'`

# **失敗時の想定レスポンス**

* 400: `{"error":"VALIDATION_ERROR","detail":"..."}`

* 401/403: `{"error":"UNAUTHORIZED"}`

* 429: `{"error":"RATE_LIMIT"}`

* 500: `{"error":"INTERNAL","trace_id":"..."}`

# **ログ/例外方針・テスト観点**

* 構造化JSONログ＋trace\_id、PIIマスク、tenacityで最大3回再試行。

* 単体テスト：JWT/レート、OCR精度閾値、YAML/JSON検証、RAG再現性、/biz/queryのsources/confidence必須、RetrainQueue挙動。

# **受け入れ基準（主要API）**

* `/ocr/current`：テキスト生成＆Jobs登録

* `/summary/generate`：指定粒度/長さ/トーンで要約

* `/knowledge/structure`：構文100%、score付与

* `/biz/upload→ingest`：ファイル格納→カード化→索引作成

* `/biz/query`：**原則→フレーム→テンプレ→注意→チェック**＋**出典/信頼度**

* `/relearn/trigger`：Queue登録、03:00消化

≪ここまで≫

---

≪受け入れチェックリスト：コピーここから≫  
 貼り先: レビュー手順

## **UI**

* **📖いま表示中を文字起こし**が最上段、ホットキー動作

* **⬇️ダウンロード**でCSV/Excel/TXT/Sheets出力

* **🧠要約／📚ナレッジ化**が粒度/形式/構文検証に準拠

* **💼ビジネスナレッジ**：外部ファイル取込み→質問が一連で成功

* **⚡一括・全自動**がOCR→要約→（ビジネス）ナレッジ→保存/通知を完走

## **機能**

* OCRジョブがS3保存・Jobs記録・精度表示

* 要約・ナレッジがS3保存、score算出

* Biz ingestがカード数・低スコア数を返す

* `/biz/query`がsources/confidenceを返却し、フォーマット別整形

* `/relearn/trigger`後、03:00にQueue消化

## **セキュリティ/コスト**

* JWT+x-api-key、role判定、APIキーは.envのみ、bcrypt

* レート60rpm/QPS2rps、MONTHLY\_TOKEN\_CAP越えで自動停止+Slack通知

* 出典とconfidenceが全回答に付与

## **可用性/監視**

* uptime≥99.5%、平均lat≤1.5s

* `/metrics`で主要メトリクス取得

* ログはS3へ日次ローテート、重大時Slack通知

≪ここまで≫

---

≪デプロイ手順MD：コピーここから≫  
 貼り先: 運用手順

# **デプロイ（Render / Cloud Run）**

## **前提**

* GitHub連携/Actions有効、Secretsに環境変数登録。

* コンテナにTesseract日本語モデル・PDF依存（poppler等）を導入。

## **Render（簡便）**

* Web Service（FastAPI）

  * Build: `pip install -r requirements.txt`

  * Start: `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`

* Worker（Celery）

  * Start: `celery -A app.tasks.pipeline worker -l info`

* Biz Worker（Ingest/Index専用）

  * Start: `celery -A app.tasks.biz_pipeline worker -l info`

* Beat（03:00再学習/同期）

  * Start: `celery -A app.tasks.schedule beat -l info`

* 外部：Redis Cloud、S3互換（Wasabi/MinIO可）

## **Cloud Run（スケール）**

* サービス分割：API / Worker / Beat（最小インスタンス1）

* Cloud Scheduler→HTTP or Pub/Subで再学習トリガ

* 同時実行・CPU常時割当でコールドスタート緩和

## **GitHub Actions（CI/CD）**

* Lint(ruff/mypy)→Test(pytest, coverage≥95%)→Build→Deploy

* 成否をSlack通知、Notionにログ追記

## **監視・アラート**

* `/healthz` `/metrics` 公開、5xx率/latency/429/token\_capを監視→Slack通知

## **セキュリティ**

* 鍵は環境変数、最小権限（S3は署名付きURLのみ書込許可）

* DRM対象は扱わない（画面OCRのみ）

* 回答は**出典・confidence必須**、PIIマスク

## **ロールバック**

* 直前リビジョンへ即時切替、データ移行不要（S3/Sheets運用）

