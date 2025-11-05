# 🚀 今すぐデプロイする手順 (40分)

## ステップ1: GitHubにプッシュ (5分)

```bash
# 1. 全ての変更をコミット
git add .
git commit -m "feat: Add multi-engine OCR system and Railway deployment config"

# 2. GitHubにプッシュ
git push origin main
```

## ステップ2: Railway プロジェクト作成 (10分)

1. **Railwayアカウント作成**:
   - https://railway.app/ にアクセス
   - "Start a New Project" をクリック
   - GitHubアカウントでサインアップ

2. **リポジトリ接続**:
   - "Deploy from GitHub repo" を選択
   - このリポジトリを選択

3. **サービス追加**:
   - "New" → "Database" → "PostgreSQL" を追加
   - "New" → "Database" → "Redis" を追加

## ステップ3: 環境変数設定 (15分)

Railway ダッシュボード → Variables タブで以下を設定:

### 必須設定 (これがないと動作しません)

```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxx  # ← あなたのClaude API Key
OPENAI_API_KEY=sk-xxxxx          # ← あなたのOpenAI API Key

# Amazon認証情報
AMAZON_EMAIL=your-email@example.com
AMAZON_PASSWORD=your-password

# セキュリティキー (以下のコマンドで生成)
# openssl rand -hex 32
SECRET_KEY=<生成した値を貼り付け>
JWT_SECRET_KEY=<生成した値を貼り付け>

# データベース (Railwayが自動設定)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# 本番環境設定
ENVIRONMENT=production
DEBUG=false

# OCR設定
USE_MULTI_ENGINE_OCR=true
```

### シークレットキー生成コマンド

```bash
# ターミナルで実行
openssl rand -hex 32  # SECRET_KEY用
openssl rand -hex 32  # JWT_SECRET_KEY用
```

## ステップ4: デプロイ実行 (10分)

Railwayが自動的に:
1. ✅ コードをビルド
2. ✅ Chrome & Tesseract インストール
3. ✅ Python依存関係インストール
4. ✅ サービス起動

進行状況: Railway ダッシュボード → "Deployments" タブで確認

## ステップ5: デプロイ完了後のアクセス

デプロイが完了すると、Railwayが以下のURLを提供:

```
https://your-app-name.railway.app
```

### アクセス方法

1. **Streamlit UI**:
   ```
   https://your-app-name.railway.app:8501
   ```

2. **FastAPI Backend**:
   ```
   https://your-app-name.railway.app/health
   ```

3. **API ドキュメント**:
   ```
   https://your-app-name.railway.app/docs
   ```

## ⚠️ 重要な注意事項

### 1. API Keyの取得

**Claude API Key**:
- https://console.anthropic.com/ にアクセス
- API Keysセクションで新規作成
- `sk-ant-` で始まるキーをコピー

**OpenAI API Key**:
- https://platform.openai.com/api-keys にアクセス
- "Create new secret key" をクリック
- `sk-` で始まるキーをコピー

### 2. コスト見積もり

**Railway**:
- 基本: $5/月
- リソース追加: 従量課金

**API使用料**:
- Claude: $3/1000画像 (入力)
- OpenAI: $0.01/画像
- 月間予想 (10冊処理): $4-10

**合計**: 月額 $9-15 程度

### 3. 初回デプロイの確認

デプロイ完了後、必ず確認:

```bash
# ヘルスチェック
curl https://your-app-name.railway.app/health

# 期待される出力:
# {"status":"healthy","database":"postgresql",...}
```

## 🆘 トラブルシューティング

### エラー1: ビルド失敗

**原因**: 依存関係エラー
**解決**: Railway ログを確認
```
Railway Dashboard → Deployments → Build Logs
```

### エラー2: データベース接続エラー

**原因**: 環境変数未設定
**解決**: Variables タブで `DATABASE_URL=${{Postgres.DATABASE_URL}}` を確認

### エラー3: API Key エラー

**原因**: API Keyが無効または未設定
**解決**: 
1. Claude/OpenAI ダッシュボードでKeyの有効性確認
2. Railway Variables で正しく設定されているか確認

---

## 📞 サポート

デプロイでエラーが発生した場合:

1. **ログ確認**: Railway Dashboard → "Deployments" → "Logs"
2. **ドキュメント参照**: `RAILWAY_DEPLOYMENT.md`
3. **ヘルスチェック**: `curl https://your-app.railway.app/health`

---

**準備完了！上記の手順に従ってデプロイしてください** 🚀
