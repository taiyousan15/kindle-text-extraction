# Auto-Capture Endpoint - Phase 1-4

## 概要

自動キャプチャエンドポイントは、Kindle Cloud Readerからページを自動的にキャプチャし、OCR処理を行うAPIです。

## 主要機能

1. **非同期キャプチャ**: ジョブIDを即座に返却し、バックグラウンドで処理を実行
2. **Amazon自動ログイン**: Seleniumを使用してAmazonに自動ログイン
3. **ページ自動キャプチャ**: Kindle Cloud Readerから指定ページ数を自動キャプチャ
4. **OCR処理**: キャプチャした画像をpytesseractでOCR処理
5. **進捗管理**: リアルタイムで進捗状況を追跡

## エンドポイント一覧

### 1. POST /api/v1/capture/start - キャプチャ開始

自動キャプチャを開始します。

**Request Body:**
```json
{
  "amazon_email": "user@example.com",
  "amazon_password": "your-password",
  "book_url": "https://read.amazon.com/kindle-library",
  "book_title": "プロンプトエンジニアリング入門",
  "max_pages": 50,
  "headless": true
}
```

**Parameters:**
- `amazon_email` (required): AmazonアカウントのEメールアドレス
- `amazon_password` (required): Amazonアカウントのパスワード（最低6文字）
- `book_url` (required): Kindle Cloud ReaderのブックURL
- `book_title` (optional): 書籍タイトル（デフォルト: "Untitled"）
- `max_pages` (optional): 最大キャプチャページ数（1-500、デフォルト: 100）
- `headless` (optional): ヘッドレスモード（デフォルト: true）

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "自動キャプチャジョブを開始しました。/api/v1/capture/status/{job_id} でステータスを確認してください。"
}
```

**cURLコマンド例:**
```bash
curl -X POST "http://localhost:8000/api/v1/capture/start" \
  -H "Content-Type: application/json" \
  -d '{
    "amazon_email": "user@example.com",
    "amazon_password": "your-password",
    "book_url": "https://read.amazon.com/kindle-library",
    "book_title": "テスト書籍",
    "max_pages": 10
  }'
```

---

### 2. GET /api/v1/capture/status/{job_id} - ステータス取得

キャプチャジョブのステータスを取得します。

**Path Parameters:**
- `job_id` (required): ジョブID (UUID)

**Response (200 OK):**
```json
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

**Status Values:**
- `pending`: キャプチャ待機中
- `processing`: キャプチャ実行中
- `completed`: キャプチャ完了
- `failed`: キャプチャ失敗

**cURLコマンド例:**
```bash
curl "http://localhost:8000/api/v1/capture/status/550e8400-e29b-41d4-a716-446655440000"
```

---

### 3. GET /api/v1/capture/jobs - ジョブ一覧取得

キャプチャジョブの一覧を取得します。

**Query Parameters:**
- `limit` (optional): 取得件数（デフォルト: 10）

**Response (200 OK):**
```json
[
  {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "progress": 100,
    "pages_captured": 50,
    "total_pages": null,
    "error_message": null,
    "ocr_results": [],
    "created_at": "2025-10-28T10:30:00",
    "completed_at": "2025-10-28T11:00:00"
  }
]
```

**cURLコマンド例:**
```bash
curl "http://localhost:8000/api/v1/capture/jobs?limit=5"
```

---

## アーキテクチャ

### ファイル構成

```
app/
├── api/v1/endpoints/
│   └── capture.py              # FastAPIエンドポイント
├── schemas/
│   └── capture.py              # Pydanticスキーマ
├── services/
│   ├── capture_service.py      # バックグラウンドタスク処理
│   └── capture/
│       ├── selenium_capture.py # Selenium自動化
│       └── ...
├── models/
│   ├── job.py                  # Jobモデル
│   └── ocr_result.py           # OCRResultモデル
└── core/
    └── database.py             # DB接続
```

### データフロー

```
1. クライアント → POST /api/v1/capture/start
2. API: Job作成 (status=pending)
3. API: バックグラウンドスレッド起動
4. API: job_id即座に返却 (202 Accepted)
5. バックグラウンド:
   a. Amazonログイン (Selenium)
   b. Kindle Cloud Readerで本を開く
   c. ページキャプチャ (save_screenshot)
   d. OCR処理 (pytesseract)
   e. OCRResult保存 (DB)
   f. Job更新 (progress, status)
6. クライアント → GET /api/v1/capture/status/{job_id}
7. API: 現在の進捗とOCR結果を返却
```

---

## セキュリティ

### パスワード管理

- **ログ出力しない**: パスワードはログに出力されません
- **DB保存しない**: パスワードはデータベースに保存されません
- **メモリのみ**: パスワードは処理中のメモリのみに保持されます

### 推奨事項

- 本番環境では環境変数または秘密管理サービス（AWS Secrets Manager等）を使用
- HTTPS通信を使用してパスワードを暗号化
- アクセス制限とレート制限を実装

---

## エラーハンドリング

### よくあるエラー

| エラー | 原因 | 対処法 |
|--------|------|--------|
| Amazonログイン失敗 | メールアドレス/パスワードが間違っている | 認証情報を確認 |
| 本が見つからない | book_urlが無効 | 正しいKindle Cloud ReaderのURLを使用 |
| OCR処理失敗 | pytesseractがインストールされていない | `brew install tesseract` (Mac) |
| Chrome Driver失敗 | Chromeがインストールされていない | Google Chromeをインストール |

### エラーレスポンス例

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "progress": 30,
  "error_message": "Amazonログイン失敗",
  ...
}
```

---

## テスト

### テストスクリプト実行

```bash
# サーバー起動
python -m uvicorn app.main:app --reload

# 別ターミナルでテスト実行
python test_capture_endpoint.py
```

### 手動テスト（curl）

```bash
# 1. キャプチャ開始
JOB_ID=$(curl -X POST "http://localhost:8000/api/v1/capture/start" \
  -H "Content-Type: application/json" \
  -d '{
    "amazon_email": "user@example.com",
    "amazon_password": "your-password",
    "book_url": "https://read.amazon.com/kindle-library",
    "book_title": "テスト書籍",
    "max_pages": 5
  }' | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# 2. ステータス確認（繰り返し実行）
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/capture/status/$JOB_ID" | jq -r '.status')
  PROGRESS=$(curl -s "http://localhost:8000/api/v1/capture/status/$JOB_ID" | jq -r '.progress')
  echo "Status: $STATUS, Progress: $PROGRESS%"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi

  sleep 5
done

# 3. 最終結果確認
curl "http://localhost:8000/api/v1/capture/status/$JOB_ID" | jq
```

---

## パフォーマンス

### 処理時間目安

- **Amazonログイン**: 5-10秒
- **ページキャプチャ**: 2秒/ページ
- **OCR処理**: 3-5秒/ページ

**例**: 50ページの本の場合
- キャプチャ: 50 × 2秒 = 100秒
- OCR: 50 × 4秒 = 200秒
- 合計: 約5-6分

### 最適化

- `headless=true`: ヘッドレスモードで高速化
- `max_pages`: 必要なページ数のみ指定
- 並列処理: 将来的にはCeleryなどで並列実行

---

## トラブルシューティング

### 1. Chromeが起動しない

**原因**: Chrome Driverが見つからない

**対処法**:
```bash
pip install selenium webdriver-manager
```

### 2. OCRの精度が低い

**原因**: Tesseractの言語データが不足

**対処法**:
```bash
# Mac
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

### 3. ジョブがpendingのまま

**原因**: バックグラウンドスレッドが起動していない

**対処法**:
- サーバーログを確認
- データベース接続を確認
- `captures/` ディレクトリの書き込み権限を確認

---

## Future Enhancements (Phase 2以降)

- [ ] Celeryによる非同期タスク管理
- [ ] 複数ジョブの並列実行
- [ ] キャプチャのキャンセル機能
- [ ] リトライ機能
- [ ] Webhook通知
- [ ] 認証・認可 (JWT)
- [ ] ファイルストレージ (S3等)
- [ ] ログ集約 (CloudWatch等)

---

## License

MIT License
