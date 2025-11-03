# 🚀 本番環境デプロイメントガイド

**Kindle文字起こしツール - Production Deployment Guide**

このガイドでは、Kindle文字起こしツールを本番環境に安全にデプロイする手順を説明します。

---

## 📋 前提条件

### 必要な環境

- **サーバー**: Linux (Ubuntu 20.04+ 推奨)
- **メモリ**: 最小4GB、推奨8GB以上
- **ストレージ**: 最小20GB、推奨50GB以上
- **ネットワーク**: 固定IPアドレスまたはドメイン名

### 必要なソフトウェア

- Docker & Docker Compose (v20.10+)
- PostgreSQL 14+
- Redis 7+
- Nginx (リバースプロキシ用)
- Certbot (SSL証明書用)

---

## 🔐 セキュリティ設定（最重要）

### 1. シークレットキーの生成

**⚠️ 絶対にデフォルト値を使用しないこと！**

```bash
# シークレットキー生成
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"

# データベースパスワード生成
python3 -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(16))"
```

生成された値を`.env`ファイルに設定してください。

### 2. .env ファイルの作成

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集
nano .env
```

**必須設定項目**:

```env
# 本番環境フラグ
ENVIRONMENT=production

# データベース（強力なパスワードに変更）
DATABASE_URL=postgresql://kindle_user:YOUR_STRONG_PASSWORD@localhost:5432/kindle_ocr

# シークレットキー（生成した値を使用）
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE
JWT_SECRET_KEY=YOUR_GENERATED_JWT_SECRET_KEY_HERE

# 認証を有効化
AUTH_ENABLED=true

# 本番ドメインを設定
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# APIキー（実際の値に変更）
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
OPENAI_API_KEY=sk-your-actual-key-here

# Amazon認証情報（専用アカウント推奨）
AMAZON_EMAIL=dedicated-account@example.com
AMAZON_PASSWORD=your-secure-password
```

### 3. ファイルパーミッション設定

```bash
# .envファイルの権限を制限
chmod 600 .env

# 所有者のみ読み書き可能
chown root:root .env
```

---

## 🗄️ データベースセットアップ

### PostgreSQL インストール

```bash
# PostgreSQL 14 インストール
sudo apt update
sudo apt install postgresql-14 postgresql-contrib

# PostgreSQL 起動
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### データベース作成

```bash
# PostgreSQLにログイン
sudo -u postgres psql

# データベースとユーザー作成
CREATE DATABASE kindle_ocr;
CREATE USER kindle_user WITH ENCRYPTED PASSWORD 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE kindle_ocr TO kindle_user;
\q
```

### データベースマイグレーション

```bash
# Alembic マイグレーション実行
alembic upgrade head
```

---

## 🌐 Nginx + SSL設定

### Nginx インストール

```bash
sudo apt install nginx
```

### SSL証明書取得（Let's Encrypt）

```bash
# Certbot インストール
sudo apt install certbot python3-certbot-nginx

# SSL証明書取得
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### Nginx 設定

`/etc/nginx/sites-available/kindle-ocr` を作成:

```nginx
# HTTP → HTTPS リダイレクト
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$host$request_uri;
}

# HTTPS 設定
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL証明書（Certbotが自動設定）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'HIGH:!aNULL:!MD5';
    ssl_prefer_server_ciphers on;

    # HSTS ヘッダー
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # セキュリティヘッダー
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # バックエンドAPI（FastAPI）
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # フロントエンド（Streamlit）
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # 最大アップロードサイズ
    client_max_body_size 10M;
}
```

設定を有効化:

```bash
# シンボリックリンク作成
sudo ln -s /etc/nginx/sites-available/kindle-ocr /etc/nginx/sites-enabled/

# Nginx設定テスト
sudo nginx -t

# Nginx 再起動
sudo systemctl restart nginx
```

---

## 🐳 Docker Deploymentオプション）

### Docker Composeでデプロイ

```bash
# Docker Compose起動
docker-compose up -d

# ログ確認
docker-compose logs -f
```

### コンテナヘルスチェック

```bash
# コンテナステータス確認
docker-compose ps

# ヘルスチェック
curl https://your-domain.com/health
```

---

## 🔍 動作確認

### 1. ヘルスチェック

```bash
# API ヘルスチェック
curl https://your-domain.com/api/health

# 期待されるレスポンス
{"status":"healthy","database":"connected","redis":"connected"}
```

### 2. 認証テスト

```bash
# ユーザー登録
curl -X POST https://your-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!","name":"Test User"}'

# ログイン
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}'
```

### 3. OCR機能テスト

ブラウザで `https://your-domain.com` にアクセスし:
1. ログイン
2. OCRアップロードページで画像をアップロード
3. 文字認識結果を確認

---

## 📊 監視・ロギング

### システムログ

```bash
# FastAPI ログ
journalctl -u kindle-ocr-api -f

# Streamlit ログ
journalctl -u kindle-ocr-ui -f

# Nginx エラーログ
tail -f /var/log/nginx/error.log
```

### エラー監視（Sentry導入推奨）

```bash
# Sentry設定
pip install sentry-sdk

# .env に追加
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

---

## 🔄 バックアップ

### データベースバックアップ

```bash
# バックアップスクリプト作成
cat > /opt/kindle-ocr/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/kindle-ocr/backups
mkdir -p $BACKUP_DIR

# PostgreSQL バックアップ
pg_dump kindle_ocr -U kindle_user > $BACKUP_DIR/kindle_ocr_$DATE.sql

# 古いバックアップ削除（30日以上）
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
EOF

chmod +x /opt/kindle-ocr/backup.sh

# Cron登録（毎日3時に実行）
echo "0 3 * * * /opt/kindle-ocr/backup.sh" | crontab -
```

### アップロードファイルのバックアップ

```bash
# rclone でS3/GCSにバックアップ
rclone sync /opt/kindle-ocr/uploads s3:your-bucket/kindle-ocr-uploads
```

---

## 🚨 トラブルシューティング

### 問題1: データベース接続エラー

```bash
# PostgreSQL起動確認
sudo systemctl status postgresql

# 接続テスト
psql -U kindle_user -d kindle_ocr -h localhost
```

### 問題2: API が応答しない

```bash
# FastAPI プロセス確認
ps aux | grep uvicorn

# ポート確認
netstat -tuln | grep 8000

# ログ確認
journalctl -u kindle-ocr-api -n 50
```

### 問題3: SSL証明書エラー

```bash
# 証明書更新
sudo certbot renew

# Nginx再起動
sudo systemctl restart nginx
```

---

## 📝 セキュリティチェックリスト

本番デプロイ前に以下を確認:

- [  ] SECRET_KEY と JWT_SECRET_KEY が強力なランダム値
- [ ] DATABASE_URLパスワードが強力
- [ ] AUTH_ENABLED=true に設定
- [  ] ALLOWED_ORIGINS が本番ドメインのみ
- [  ] SSL/TLS証明書が正しく設定
- [  ] HTTPS強制が有効
- [  ] セキュリティヘッダーが設定
- [  ] ファイアウォールで不要なポートを閉鎖
- [  ] Redisにパスワード設定
- [  ] .env ファイルのパーミッションが600
- [  ] Amazonアカウントが専用で最小権限
- [  ] バックアップが自動化

---

## 🔄 ロールバック手順

デプロイに問題が発生した場合:

```bash
# 1. 前バージョンのDockerイメージに戻す
docker-compose down
docker-compose up -d --force-recreate

# 2. データベースを復元
psql -U kindle_user -d kindle_ocr < /opt/kindle-ocr/backups/kindle_ocr_YYYYMMDD_HHMMSS.sql

# 3. Nginx再起動
sudo systemctl restart nginx
```

---

## 📞 サポート

問題が発生した場合:

1. ログを確認
2. セキュリティ監査レポートを参照
3. GitHub Issuesで報告

---

**デプロイ成功を祈ります！ 🎉**

**最終更新**: 2025-11-03
