# 要件定義書 v2→v3 変更サマリー

## 📅 変更日: 2025-10-27

---

## 🎯 変更の目的

**デプロイなし・ローカル環境専用**に簡素化し、セットアップを劇的に簡単にする。

---

## 📊 変更の全体像

| 項目 | v2.0（改善版） | v3.0（ローカル版） | 変化 |
|------|----------------|-------------------|------|
| **実行環境** | Render（5サービス） | Docker Compose（ローカル） | ✅ 簡素化 |
| **ストレージ** | S3 + PostgreSQL | PostgreSQL BLOB + ローカルFS | ✅ 簡素化 |
| **認証** | JWT + x-api-key | なし | ✅ 削除 |
| **通知** | Slack Webhook | Streamlit toast | ✅ 簡素化 |
| **レート制限** | 60rpm + QPS制御 | なし | ✅ 削除 |
| **環境変数数** | 15個 | 5個 | ✅ 削減67% |
| **依存ライブラリ** | 40個 | 35個 | ✅ 削減5個 |
| **月額コスト** | $26 | $0（LLM除く） | ✅ 削減$26 |
| **セットアップ時間** | 30分 | 5分 | ✅ 短縮83% |
| **デプロイ難易度** | 70/100 | 20/100 | ✅ 削減71% |

---

## ✅ 主要変更点（10項目）

### 1. **デプロイ記述を全削除**

**削除内容**:
- Render/Cloud Run デプロイ手順（v2: 495-528行目）
- CI/CD・GitHub Actions 設定
- 本番環境用サービス構成（5サービス）

**置き換え**:
- Docker Compose起動手順（3ステップ）
- Pythonダイレクト実行手順（Dockerなし）

---

### 2. **ストレージをPostgreSQL BLOBに統一**

**v2.0**: S3互換ストレージ（Wasabi等）+ PostgreSQL（メタDB）

**v3.0**: PostgreSQL BLOB（画像・テキスト・ファイル全て） + ローカルファイルシステム（バックアップ用）

**変更理由**:
- S3は外部サービスで設定が複雑
- ローカル環境ではPostgreSQL BLOBで十分
- バックアップは `pg_dump` 一発で完結

**テーブル変更例**:
```sql
-- v2.0
ocr_results (id, job_id, page_num, text, confidence, s3_key)

-- v3.0
ocr_results (id, job_id, page_num, text, confidence, image_blob BYTEA)
```

---

### 3. **認証システム削除**

**v2.0**: JWT + x-api-key（マルチユーザー想定）

**v3.0**: 認証なし（ローカル単一ユーザー）

**削除項目**:
- JWT Secret生成
- python-jose依存関係
- API Key管理
- レート制限（slowapi）

**影響箇所**:
- FastAPI依存性注入（`Depends(get_current_user)` 削除）
- 環境変数（`JWT_SECRET`, `API_KEY_MASTER` 削除）

---

### 4. **通知をStreamlit toastに変更**

**v2.0**: Slack Webhook（外部通知）

**v3.0**: Streamlit toast（ブラウザ通知）

**変更理由**:
- ローカル環境でSlack通知は不要
- Streamlit標準機能で十分

**実装例**:
```python
# v2.0
slack_client.send_message(f"✅ OCR完了: {book_title}")

# v3.0
st.toast(f"✅ OCR完了: {book_title}", icon="🎉")
```

---

### 5. **環境変数を大幅削減**

**削減内容**:

| 削除された環境変数 | 理由 |
|-------------------|------|
| S3_ENDPOINT | S3削除 |
| S3_BUCKET | S3削除 |
| S3_ACCESS_KEY | S3削除 |
| S3_SECRET_KEY | S3削除 |
| SLACK_WEBHOOK_URL | Slack削除 |
| JWT_SECRET | 認証削除 |
| API_KEY_MASTER | 認証削除 |
| LLM_PROVIDER_PREFERENCE | 簡素化（autoのみ） |
| MODEL_QPS_PER_PROVIDER | レート制限削除 |
| CHROME_DRIVER_PATH | webdriver-managerで自動管理 |

**残った環境変数（5個のみ）**:
```bash
DATABASE_URL           # PostgreSQL接続
REDIS_URL             # Celeryブローカー
ANTHROPIC_API_KEY     # Claude API
AMAZON_EMAIL          # Selenium用（オプション）
AMAZON_PASSWORD       # Selenium用（オプション）
```

---

### 6. **依存ライブラリ削減**

**削除されたライブラリ**:
- `boto3`（S3クライアント）
- `python-jose[jwt]`（JWT認証）
- `slowapi`（レート制限）
- `slack-sdk`（Slack通知）
- `passlib[bcrypt]`（パスワードハッシュ）

**追加されたライブラリ**:
- `pgvector`（PostgreSQLベクトル検索拡張）

---

### 7. **起動手順の大幅簡素化**

**v2.0**: 5サービスをRenderに個別デプロイ
1. PostgreSQL作成
2. Redis作成
3. FastAPI Web Service設定
4. Celery Worker設定
5. Beat Scheduler設定
6. 環境変数15個設定
7. GitHub連携
8. デプロイ実行

**v3.0**: Docker Compose一発起動
```bash
python3 setup_wizard.py  # 環境変数自動生成
docker-compose up -d     # 全サービス起動
```

---

### 8. **データバックアップ手順追加**

**v2.0**: バックアップ記述なし

**v3.0**: PostgreSQLダンプ手順明記
```bash
# バックアップ
docker-compose exec postgres pg_dump -U kindle_user kindle_ocr > backups/backup_$(date +%Y%m%d).sql

# リストア
cat backups/backup_20251027.sql | docker-compose exec -T postgres psql -U kindle_user kindle_ocr
```

---

### 9. **トラブルシューティング追加**

**v2.0**: トラブルシューティングなし

**v3.0**: よくあるエラー対処法を詳細記載
- Docker起動エラー
- PostgreSQL接続エラー
- Celery Workerが動かない
- OCR精度が低い

---

### 10. **pgvector拡張の採用**

**v2.0**: FAISS（メモリ内ベクトル検索）

**v3.0**: pgvector + FAISS（ハイブリッド）

**利点**:
- PostgreSQLに直接ベクトル保存
- SQLで検索可能
- バックアップが簡単

**セットアップ**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE INDEX ON biz_cards USING ivfflat (vector_embedding vector_cosine_ops);
```

---

## 📝 削除された機能

### 1. **外部サービス連携**
- ❌ S3互換ストレージ（Wasabi等）
- ❌ Slack通知
- ❌ Render/Cloud Run デプロイ

### 2. **認証・セキュリティ**
- ❌ JWT認証
- ❌ x-api-key認証
- ❌ レート制限（60rpm）
- ❌ bcryptパスワードハッシュ

### 3. **CI/CD**
- ❌ GitHub Actions
- ❌ 自動デプロイ
- ❌ 自動テスト実行（CI）

### 4. **マルチユーザー対応**
- ❌ ロール管理（Admin/Operator/Viewer）
- ❌ ユーザー認証
- ❌ 管理画面

---

## 🆕 追加された機能

### 1. **ローカル最適化**
- ✅ Docker Compose環境構築
- ✅ setup_wizard.py（対話型セットアップ）
- ✅ PostgreSQL BLOB保存

### 2. **バックアップ**
- ✅ pg_dump手順
- ✅ ローカルファイルシステムバックアップ

### 3. **トラブルシューティング**
- ✅ よくあるエラー対処法
- ✅ ログ確認コマンド
- ✅ 再起動手順

### 4. **pgvector統合**
- ✅ PostgreSQLベクトル検索
- ✅ IVFFlat インデックス

---

## 📂 ファイル構成の変更

### 削除されたファイル（想定）
- `app/services/storage_s3.py`（S3ストレージサービス）
- `app/api/auth.py`（JWT認証）
- `.github/workflows/ci.yml`（CI/CD設定）
- `render.yaml`（Renderデプロイ設定）

### 追加されたファイル
- `app/services/storage_local.py`（ローカルストレージサービス）
- `backups/`ディレクトリ（PostgreSQLバックアップ）
- `V3_CHANGES_SUMMARY.md`（この変更サマリー）

### 変更されたファイル
- `requirements.txt`（5ライブラリ削減、pgvector追加）
- `.env`（環境変数67%削減）
- `docker-compose.yml`（ローカル環境最適化）
- `Kindle文字起こし要件定義書_v3_ローカル版.md`（新規作成）

---

## 🔧 移行手順（v2→v3）

既にv2環境を構築済みの場合:

### 1. データ移行

```bash
# S3からローカルにダウンロード
aws s3 sync s3://kindle-knowledge-v2/data/ ./local_data/

# PostgreSQLにBLOB挿入
python scripts/migrate_s3_to_blob.py
```

### 2. 環境変数更新

```bash
# .envファイル編集
# S3関連削除、JWT関連削除
vim .env
```

### 3. Docker Compose起動

```bash
docker-compose down
docker-compose up -d
```

---

## ⚠️ 注意事項

### 1. **データ永続化**

ローカル環境のため、以下に注意:
- Docker volumeは `docker-compose down -v` で削除される
- 定期的に `pg_dump` でバックアップ推奨
- 重要データは外部HDDにも保存

### 2. **コスト管理**

LLM API使用料のみ発生:
- MONTHLY_TOKEN_CAP=10000000（1000万トークン/月）
- 80%到達でブラウザ警告
- 100%到達で全機能停止

### 3. **セキュリティ**

ローカル単一ユーザーのため:
- 認証なし（localhost:8501へ誰でもアクセス可能）
- 外部ネットワークからアクセスさせない
- .envファイルは絶対にGit管理しない

---

## 📊 コスト比較

| 項目 | v2.0（Render） | v3.0（ローカル） | 差額 |
|------|----------------|------------------|------|
| PostgreSQL | $7/月 | $0 | -$7 |
| Redis | $5/月 | $0 | -$5 |
| Web Service | $7/月 | $0 | -$7 |
| Worker | $7/月 | $0 | -$7 |
| Beat | $0（Workerに含む） | $0 | $0 |
| **インフラ合計** | **$26/月** | **$0** | **-$26** |
| LLM API | $10-30/月 | $10-30/月 | ±$0 |
| **総コスト** | **$36-56/月** | **$10-30/月** | **-$26** |

**年間削減額**: **$312**

---

## 🎯 推奨される使い方

### ローカル開発・個人利用
- ✅ v3.0（ローカル版）を使用
- Docker Composeで簡単起動
- コスト$0（LLM除く）

### 本番環境・チーム利用
- v2.0（改善版）を使用
- Renderにデプロイ
- マルチユーザー対応
- 外部アクセス可能

---

## 🚀 次のステップ

v3.0要件定義書に基づき、Phase 1 MVP実装開始:

1. **SQLAlchemyモデル実装**（8テーブル）
   - user.py
   - job.py
   - ocr_result.py（image_blob BYTEA追加）
   - summary.py
   - knowledge.py（content_blob BYTEA追加）
   - biz_file.py（file_blob BYTEA追加）
   - biz_card.py（vector_embedding VECTOR(384)追加）
   - feedback.py
   - retrain_queue.py

2. **FastAPI エンドポイント実装**
   - POST /ocr/upload
   - POST /ocr/auto-capture/pyautogui
   - POST /ocr/auto-capture/selenium
   - GET /jobs/{job_id}
   - POST /summary/generate
   - POST /knowledge/structure
   - POST /biz/upload
   - POST /biz/ingest
   - POST /biz/query
   - POST /relearn/trigger

3. **Streamlit UI実装**
   - Home.py
   - pages/1_OCR.py
   - pages/2_Text_Download.py
   - pages/3_Summary.py
   - pages/4_Knowledge.py
   - pages/5_Business_Knowledge.py

4. **Celery タスク実装**
   - pipeline.py（OCR→要約→ナレッジ）
   - biz_pipeline.py（ビジネスRAG）
   - capture_pipeline.py（自動キャプチャ）
   - schedule.py（再学習スケジュール）

---

**作成日**: 2025-10-27
**作成者**: Matsumoto Toshihiko

🤖 Generated with [Claude Code](https://claude.com/claude-code)
