# Quick Start Guide - Auto-Capture API

Phase 1-4の自動キャプチャAPIを5分でセットアップして実行する手順です。

---

## Prerequisites

以下がインストールされていることを確認してください:

```bash
# Python 3.11+
python3 --version

# Tesseract OCR
tesseract --version

# Google Chrome
google-chrome --version  # Linux
# または
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version  # Mac
```

### 必要なソフトウェアのインストール

**Mac:**
```bash
# Homebrew でインストール
brew install tesseract tesseract-lang
brew install --cask google-chrome
```

**Ubuntu:**
```bash
# apt でインストール
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn
sudo apt-get install -y google-chrome-stable
```

---

## Step 1: 依存関係のインストール

```bash
# プロジェクトディレクトリに移動
cd /Users/matsumototoshihiko/div/Kindle文字起こしツール

# 仮想環境がない場合は作成
python3 -m venv venv

# 仮想環境をアクティベート
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 依存関係をインストール
pip install -r requirements.txt

# 追加のライブラリ (まだない場合)
pip install selenium webdriver-manager pytesseract pillow
```

---

## Step 2: データベース起動

```bash
# PostgreSQL起動 (Dockerの場合)
docker-compose up -d postgres

# または、ローカルPostgreSQLを起動
brew services start postgresql  # Mac
sudo service postgresql start   # Ubuntu

# データベース作成 (初回のみ)
psql -U postgres -c "CREATE DATABASE kindle_ocr;"
psql -U postgres -c "CREATE USER kindle_user WITH PASSWORD 'kindle_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE kindle_ocr TO kindle_user;"

# テーブル作成
python -c "from app.core.database import create_tables; create_tables()"
```

---

## Step 3: サーバー起動

```bash
# FastAPIサーバー起動
python -m uvicorn app.main:app --reload

# 起動確認
curl http://localhost:8000/health
```

**期待される出力:**
```json
{
  "status": "healthy",
  "database": "postgresql",
  "pool_size": 10,
  ...
}
```

---

## Step 4: APIドキュメント確認

ブラウザで以下のURLを開く:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Step 5: テスト実行

### 方法1: テストスクリプト (推奨)

```bash
# 別ターミナルを開く
cd /Users/matsumototoshihiko/div/Kindle文字起こしツール
source venv/bin/activate

# テストスクリプト実行
python test_capture_endpoint.py
```

### 方法2: cURL

```bash
# 1. キャプチャ開始
curl -X POST "http://localhost:8000/api/v1/capture/start" \
  -H "Content-Type: application/json" \
  -d '{
    "amazon_email": "your-email@example.com",
    "amazon_password": "your-password",
    "book_url": "https://read.amazon.com/kindle-library",
    "book_title": "テスト書籍",
    "max_pages": 5,
    "headless": true
  }'

# レスポンスからjob_idをコピー
# 例: "550e8400-e29b-41d4-a716-446655440000"

# 2. ステータス確認 (繰り返し実行)
curl "http://localhost:8000/api/v1/capture/status/550e8400-e29b-41d4-a716-446655440000"

# 3. ジョブ一覧確認
curl "http://localhost:8000/api/v1/capture/jobs?limit=5"
```

### 方法3: Pythonスクリプト

```python
import requests
import time
import json

# 1. キャプチャ開始
response = requests.post(
    "http://localhost:8000/api/v1/capture/start",
    json={
        "amazon_email": "your-email@example.com",
        "amazon_password": "your-password",
        "book_url": "https://read.amazon.com/kindle-library",
        "book_title": "テスト書籍",
        "max_pages": 5
    }
)

job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# 2. 進捗監視
while True:
    status_response = requests.get(
        f"http://localhost:8000/api/v1/capture/status/{job_id}"
    )
    data = status_response.json()

    print(f"Status: {data['status']}, Progress: {data['progress']}%")

    if data["status"] in ["completed", "failed"]:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        break

    time.sleep(5)
```

---

## Step 6: 結果確認

### キャプチャ画像の確認

```bash
# キャプチャされた画像を確認
ls -lh captures/{job_id}/

# 例:
# page_0001.png
# page_0002.png
# page_0003.png
# ...
```

### データベース確認

```bash
# psqlで接続
psql -U kindle_user -d kindle_ocr

# ジョブ確認
SELECT id, type, status, progress, created_at FROM jobs ORDER BY created_at DESC LIMIT 5;

# OCR結果確認
SELECT job_id, page_num, LEFT(text, 50) as text_preview, confidence
FROM ocr_results
ORDER BY job_id, page_num
LIMIT 10;
```

---

## トラブルシューティング

### 問題1: Amazonログイン失敗

**エラー:**
```json
{
  "status": "failed",
  "error_message": "Amazonログイン失敗"
}
```

**対処法:**
1. メールアドレス・パスワードを確認
2. 2段階認証が有効な場合は無効化
3. ヘッドレスモードを無効にしてデバッグ: `"headless": false`

---

### 問題2: Chrome Driverエラー

**エラー:**
```
WebDriverException: Message: 'chromedriver' executable needs to be in PATH
```

**対処法:**
```bash
# webdriver-manager を再インストール
pip install --upgrade webdriver-manager

# 手動でChrome Driverをダウンロード
# https://chromedriver.chromium.org/
```

---

### 問題3: OCRエラー

**エラー:**
```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```

**対処法:**
```bash
# Mac
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

# 確認
tesseract --version
```

---

### 問題4: データベース接続エラー

**エラー:**
```json
{
  "status": "unhealthy",
  "error": "could not connect to server"
}
```

**対処法:**
```bash
# PostgreSQL起動確認
docker ps | grep postgres
# または
brew services list | grep postgresql

# 接続テスト
psql -U kindle_user -d kindle_ocr -c "SELECT 1;"
```

---

## 次のステップ

1. **APIドキュメントを読む**: `/docs` でインタラクティブなAPI仕様を確認
2. **詳細なREADMEを読む**: `app/api/v1/endpoints/CAPTURE_README.md`
3. **実装サマリーを読む**: `PHASE_1-4_IMPLEMENTATION_SUMMARY.md`
4. **本番環境への適用**: HTTPS、認証、環境変数の設定

---

## クイックリファレンス

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/capture/start | キャプチャ開始 |
| GET | /api/v1/capture/status/{job_id} | ステータス取得 |
| GET | /api/v1/capture/jobs | ジョブ一覧 |
| POST | /api/v1/ocr/upload | 単一画像OCR |
| GET | /api/v1/ocr/jobs/{job_id} | OCRジョブ取得 |
| GET | /health | ヘルスチェック |

### Job Status

| Status | Description |
|--------|-------------|
| pending | キャプチャ待機中 |
| processing | キャプチャ実行中 |
| completed | キャプチャ完了 |
| failed | キャプチャ失敗 |

---

## サポート

問題が発生した場合:

1. サーバーログを確認: `uvicorn` の出力
2. データベースログを確認: `docker logs kindle_postgres`
3. テストスクリプトを実行: `python test_capture_endpoint.py`
4. 詳細なREADMEを参照: `app/api/v1/endpoints/CAPTURE_README.md`

---

## まとめ

これでKindle文字起こしツールの自動キャプチャAPIが使えるようになりました！

**次の手順:**
1. 実際のKindle書籍でテスト
2. OCR精度の確認
3. パフォーマンスの測定
4. Phase 2の機能追加を検討

Happy Coding! 🚀
