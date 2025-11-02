# 🚀 クイックスタートガイド

## 📋 前提条件

- Python 3.11以上
- Docker & Docker Compose（オプション）
- Git

---

## ⚡ 最速セットアップ（3ステップ）

### 1️⃣ セットアップウィザード実行

```bash
cd /Users/matsumototoshihiko/div/Kindle文字起こしツール
python3 setup_wizard.py
```

**入力内容**:
- PostgreSQL設定（デフォルト値でOK）
- Anthropic API Key（[https://console.anthropic.com/](https://console.anthropic.com/)）
- OpenAI API Key（オプション）
- その他はEnterでスキップ可能

---

### 2️⃣ Docker Compose起動

```bash
docker-compose up -d
```

**起動するサービス**:
- PostgreSQL（データベース + pgvector拡張）
- Redis（タスクキュー）
- FastAPI（バックエンドAPI）
- Celery Worker（OCR/RAG処理）
- Celery Beat（スケジューラ：毎日03:00再学習）
- Streamlit（Web UI）

---

### 3️⃣ アクセス

```bash
# Web UI
open http://localhost:8501

# API ドキュメント
open http://localhost:8000/docs
```

---

## 🧪 動作確認

### PyAutoGUI キャプチャテスト

```bash
# 1. Kindleアプリで本を開く（1ページ目）
# 2. 以下を実行
python -m app.services.capture.pyautogui_capture
```

### Selenium キャプチャテスト

```bash
# .envファイルにAmazon認証情報を追加後
python -m app.services.capture.selenium_capture
```

---

## 📚 ドキュメント

- **要件定義書（最新）**: `Kindle文字起こし要件定義書_v3_ローカル版.md`
- **v2→v3変更サマリー**: `V3_CHANGES_SUMMARY.md`
- **デプロイレポート**: `DEPLOYMENT_READY_REPORT.md`
- **実装サマリー**: `IMPLEMENTATION_SUMMARY.md`

---

## ❓ トラブルシューティング

### Docker起動エラー

```bash
# ログ確認
docker-compose logs

# 再起動
docker-compose down
docker-compose up -d
```

### データベース接続エラー

```bash
# PostgreSQL接続確認
docker-compose exec postgres pg_isready

# 手動接続テスト
python -c "from app.core.database import check_connection; check_connection()"
```

---

## 🆘 サポート

- GitHub Issues: [https://github.com/taiyousan15/kindle-text-extraction/issues](https://github.com/taiyousan15/kindle-text-extraction/issues)
- 設定ファイル: `.env`（setup_wizardで自動生成）

---

**所要時間**: 初回セットアップ約5分
