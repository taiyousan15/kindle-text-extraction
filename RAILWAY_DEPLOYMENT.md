# Railway.app Deployment Guide

Complete guide for deploying Kindle OCR Tool to Railway.app

Estimated time: 30-45 minutes
Cost: $5/month (Railway Hobby Plan)

---

## Why Railway Instead of Vercel?

Vercel **CANNOT** run this application because:

1. Selenium requires persistent browser sessions (not supported in serverless)
2. Auto-capture tasks run 5-10+ minutes (Vercel timeout: 10s free, 60s Pro)
3. Celery workers need long-running processes (Vercel is stateless)
4. Streamlit requires WebSocket connections (not ideal for Vercel)

Railway solves all of these problems with persistent compute environments.

---

## Prerequisites

- GitHub account
- Railway account (https://railway.app)
- Credit card for Railway Hobby Plan ($5/month)
- Git installed locally

---

## Step 1: Prepare Your Repository

### 1.1 Commit Railway Configuration Files

```bash
cd /Users/matsumototoshihiko/div/Kindle文字起こしツール

# Check that these files exist:
ls -la railway.json nixpacks.toml Procfile

# Add and commit
git add railway.json nixpacks.toml Procfile .env.railway.template
git commit -m "Add Railway deployment configuration"
git push origin main
```

### 1.2 Verify Files Are Present

Ensure these files exist in your repository:
- `railway.json` - Railway service configuration
- `nixpacks.toml` - Build configuration with Chromium/Tesseract
- `Procfile` - Process definitions (web, worker, beat)
- `.env.railway.template` - Environment variable template

---

## Step 2: Create Railway Account

1. Go to https://railway.app
2. Click "Start a New Project"
3. Sign in with GitHub
4. Authorize Railway to access your repositories
5. Add payment method (required for Hobby Plan)

---

## Step 3: Deploy PostgreSQL Database

### 3.1 Create PostgreSQL Service

1. In Railway dashboard, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway provisions the database automatically (takes ~30 seconds)
4. Click on the PostgreSQL service tile

### 3.2 Enable pgvector Extension

1. Click on PostgreSQL service
2. Go to "Data" tab
3. Click "Query" button
4. Run this SQL command:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

5. Verify installation:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

Expected output: `vector | 1 | ...`

### 3.3 Note the DATABASE_URL

1. Go to "Variables" tab
2. Copy the `DATABASE_URL` value
3. Format: `postgresql://postgres:password@host:port/railway`

---

## Step 4: Deploy Redis

### 4.1 Create Redis Service

1. Click "New" in Railway dashboard
2. Select "Database" → "Redis"
3. Railway provisions Redis automatically
4. Click on the Redis service tile

### 4.2 Note the REDIS_URL

1. Go to "Variables" tab
2. Copy the `REDIS_URL` value
3. Format: `redis://default:password@host:port`

---

## Step 5: Deploy FastAPI Backend

### 5.1 Deploy from GitHub

1. Click "New" in Railway dashboard
2. Select "GitHub Repo"
3. Choose your `Kindle文字起こしツール` repository
4. Railway will detect Python and start building
5. Wait for build to complete (~3-5 minutes)

### 5.2 Configure Service Name

1. Click on the new service
2. Go to "Settings" tab
3. Change name to "api" (optional but recommended)

### 5.3 Set Environment Variables

1. Go to "Variables" tab
2. Click "Raw Editor"
3. Paste the following (update YOUR_* placeholders):

```bash
# Database (reference from PostgreSQL service)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (reference from Redis service)
REDIS_URL=${{Redis.REDIS_URL}}
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URL=${{Redis.REDIS_URL}}

# Application
ENVIRONMENT=production
AUTH_ENABLED=false

# Security (GENERATE NEW KEYS!)
SECRET_KEY=YOUR_RANDOM_32_CHAR_SECRET_KEY_HERE
JWT_SECRET_KEY=YOUR_RANDOM_32_CHAR_JWT_SECRET_HERE
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501

# AI APIs
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY_HERE
OPENAI_API_KEY=
LLM_PROVIDER=anthropic
CLAUDE_MODEL=claude-3-haiku-20240307

# Amazon Credentials
AMAZON_EMAIL=YOUR_AMAZON_EMAIL
AMAZON_PASSWORD=YOUR_AMAZON_PASSWORD

# Token Management
MONTHLY_TOKEN_CAP=10000000
RELEARN_CRON=0 3 * * *
TIMEZONE=Asia/Tokyo

# OCR Configuration
TESSERACT_LANG=jpn+eng

# File Storage (temporary paths)
UPLOAD_DIR=/tmp/uploads
CAPTURE_DIR=/tmp/captures
LOG_DIR=/tmp/logs
MAX_UPLOAD_SIZE=10

# Device Identifier
DEVICE_IDENTIFIER=Railway Production Server

# Port (Railway auto-assigns)
PORT=${{PORT}}
```

4. Click "Save"
5. Railway will automatically redeploy

### 5.4 Generate Strong Secret Keys

Use this command locally to generate secure keys:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy these values into your Railway environment variables.

---

## Step 6: Run Database Migrations

### 6.1 Install Railway CLI

```bash
npm install -g @railway/cli
```

### 6.2 Login and Link Project

```bash
# Login to Railway
railway login

# Link to your project
cd /Users/matsumototoshihiko/div/Kindle文字起こしツール
railway link
```

Select your project from the list.

### 6.3 Run Migrations

```bash
# Run Alembic migrations
railway run alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> d53621f402b5, initial schema
INFO  [alembic.runtime.migration] Running upgrade d53621f402b5 -> 5aa636e83b69, add authentication fields
INFO  [alembic.runtime.migration] Running upgrade 5aa636e83b69 -> 173e95521004, add performance indexes
```

---

## Step 7: Deploy Celery Worker

### 7.1 Create New Service from Same Repo

1. Click "New" in Railway dashboard
2. Select "GitHub Repo"
3. Choose the SAME repository
4. Railway creates a second service

### 7.2 Configure Celery Worker

1. Click on the new service
2. Go to "Settings" tab
3. Change name to "celery-worker"
4. Under "Deploy" section, find "Start Command"
5. Replace with:

```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

### 7.3 Copy Environment Variables

1. Go to "Variables" tab
2. Click "Raw Editor"
3. Paste the SAME environment variables from FastAPI service
4. Save

---

## Step 8: Deploy Celery Beat (Scheduler)

### 8.1 Create Third Service

1. Click "New" → "GitHub Repo"
2. Choose the SAME repository again
3. Railway creates a third service

### 8.2 Configure Celery Beat

1. Click on the new service
2. Go to "Settings" tab
3. Change name to "celery-beat"
4. Change "Start Command" to:

```bash
celery -A app.tasks.schedule beat --loglevel=info
```

### 8.3 Copy Environment Variables

1. Go to "Variables" tab
2. Copy the SAME environment variables from FastAPI service
3. Save

---

## Step 9: Verify Deployment

### 9.1 Check All Services Are Running

In Railway dashboard, you should see 5 services:
- PostgreSQL (green, running)
- Redis (green, running)
- api (green, running)
- celery-worker (green, running)
- celery-beat (green, running)

### 9.2 Get API URL

1. Click on "api" service
2. Go to "Settings" tab
3. Under "Networking", find "Public Networking"
4. Click "Generate Domain"
5. Railway generates a URL like: `your-app-production.up.railway.app`

### 9.3 Test Health Endpoint

```bash
curl https://your-app-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "postgresql",
  "pool_size": 5,
  "checked_out": 0
}
```

If you see this, congratulations! Your backend is live.

### 9.4 Test API Root

```bash
curl https://your-app-production.up.railway.app/
```

Expected response:
```json
{
  "message": "Kindle OCR API",
  "version": "1.0.0 (Phase 1-8 MVP)",
  "docs": "/docs",
  "health": "/health",
  "rate_limiting": "enabled"
}
```

---

## Step 10: Deploy Streamlit Frontend (Optional)

### Option A: Deploy Streamlit on Railway

1. Create NEW service from same repo
2. Name it "streamlit"
3. Change "Start Command" to:

```bash
streamlit run app/ui/Home.py --server.port $PORT --server.address 0.0.0.0
```

4. Add environment variables:

```bash
API_BASE_URL=${{api.RAILWAY_PUBLIC_DOMAIN}}
STREAMLIT_SERVER_HEADLESS=true
```

5. Generate domain for Streamlit service
6. Visit: `https://your-streamlit.up.railway.app`

### Option B: Use Vercel for Frontend (Recommended)

See `DEPLOYMENT_ARCHITECTURE.md` for Next.js conversion guide.

---

## Step 11: Post-Deployment Verification

### 11.1 Check Logs

```bash
# API logs
railway logs --service api

# Celery worker logs
railway logs --service celery-worker

# Celery beat logs
railway logs --service celery-beat
```

### 11.2 Test OCR Upload

```bash
curl -X POST https://your-app.railway.app/api/v1/ocr/upload \
  -F "file=@test_image.png" \
  -F "book_title=Test Book"
```

### 11.3 Test Auto-Capture (if Amazon credentials set)

```bash
curl -X POST https://your-app.railway.app/api/v1/capture/start \
  -H "Content-Type: application/json" \
  -d '{
    "amazon_email": "your-email@example.com",
    "amazon_password": "your-password",
    "book_url": "https://read.amazon.com/...",
    "max_pages": 5,
    "headless": true
  }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "自動キャプチャジョブを開始しました..."
}
```

### 11.4 Check Job Status

```bash
curl https://your-app.railway.app/api/v1/capture/status/{job_id}
```

---

## Step 12: Custom Domain (Optional)

### 12.1 Add Custom Domain

1. Click on "api" service
2. Go to "Settings" → "Networking"
3. Under "Custom Domain", click "Add Domain"
4. Enter your domain: `api.yourdomain.com`

### 12.2 Configure DNS

Add a CNAME record in your DNS provider:

```
Type: CNAME
Name: api
Value: your-app-production.up.railway.app
TTL: 3600
```

### 12.3 Wait for SSL Certificate

Railway automatically provisions SSL certificate (takes 1-5 minutes).

---

## Monitoring & Maintenance

### View Resource Usage

1. Go to Railway dashboard
2. Click on any service
3. Go to "Metrics" tab
4. View:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

### View Logs in Real-Time

```bash
# Follow API logs
railway logs --service api --follow

# Follow Celery worker logs
railway logs --service celery-worker --follow
```

### Restart Services

```bash
# Restart API
railway up --service api

# Restart all services
railway up
```

### Check Database Size

1. Click on PostgreSQL service
2. Go to "Metrics" tab
3. View disk usage

### Backup Database

```bash
# Export database via Railway CLI
railway connect postgres

# Inside psql
\dt  # List tables
\q   # Exit

# Backup from command line
railway run pg_dump -Fc > backup.dump
```

---

## Troubleshooting

### Problem: "Tesseract not found"

Check logs for Tesseract installation:

```bash
railway logs --service api | grep tesseract
```

Fix: Verify `nixpacks.toml` includes tesseract:

```toml
[phases.setup]
nixPkgs = ["python310", "chromium", "chromedriver", "tesseract", "tessdata"]
```

### Problem: "Database connection failed"

Check:
1. PostgreSQL service is running
2. `DATABASE_URL` environment variable is set
3. pgvector extension is installed

Fix:
```bash
railway connect postgres
CREATE EXTENSION IF NOT EXISTS vector;
```

### Problem: "Celery worker not processing jobs"

Check:
1. Redis is running
2. `REDIS_URL` is set correctly
3. Celery worker service is running

View logs:
```bash
railway logs --service celery-worker
```

### Problem: "Selenium Chrome not working"

Chromium may not be installing correctly. Check logs:

```bash
railway logs --service api | grep -i chrome
```

Fix: Update `nixpacks.toml`:

```toml
[phases.setup]
nixPkgs = ["python310", "chromium", "chromedriver"]

[phases.install]
cmds = [
  "pip install --upgrade pip",
  "pip install -r requirements.txt"
]

[variables]
CHROME_BIN = "/nix/store/*/bin/chromium"
CHROMEDRIVER_PATH = "/nix/store/*/bin/chromedriver"
```

### Problem: "Rate limit errors"

Redis may not be connected. Check:

```bash
railway logs --service api | grep -i redis
```

Fix: Verify `REDIS_URL` and `RATE_LIMIT_STORAGE_URL` are set.

---

## Cost Management

### Monitor Usage

1. Go to Railway dashboard
2. Click "Usage" in sidebar
3. View current month's usage:
   - Execution hours
   - Network egress
   - Estimated cost

### Railway Hobby Plan Limits

- **Cost**: $5/month
- **Execution Time**: 500 hours/month (~16.7 hours/day)
- **Services**: Unlimited
- **Databases**: Included

### Optimization Tips

1. **Reduce Celery Worker Concurrency**:
   ```bash
   celery -A app.tasks.celery_app worker --concurrency=1
   ```

2. **Use Headless Chrome**:
   ```python
   options.add_argument('--headless')
   ```

3. **Limit Capture Pages**:
   ```python
   max_pages=50  # Instead of 100+
   ```

4. **Cache OCR Results**:
   Store processed results in PostgreSQL to avoid reprocessing.

---

## Scaling Up

### Upgrade to Railway Pro Plan

If you hit limits, upgrade:
- **Cost**: $20/month
- **Execution Time**: Unlimited
- **Priority Support**: Yes

### Horizontal Scaling

Add more Celery workers:

1. Duplicate "celery-worker" service
2. Name it "celery-worker-2"
3. Railway runs multiple workers in parallel

---

## Security Checklist

Before going live:

- [ ] `SECRET_KEY` is strong random value (32+ chars)
- [ ] `JWT_SECRET_KEY` is strong random value (32+ chars)
- [ ] `ANTHROPIC_API_KEY` is valid
- [ ] `AMAZON_EMAIL`/`PASSWORD` are secure
- [ ] `ALLOWED_ORIGINS` is set to production domains only
- [ ] `AUTH_ENABLED=true` for production
- [ ] PostgreSQL uses strong password
- [ ] Redis is not publicly accessible
- [ ] SSL is enabled (Railway does this automatically)
- [ ] Logs don't contain sensitive data
- [ ] Database backups are configured

---

## Next Steps

1. **Frontend Deployment**: Deploy Streamlit or create Next.js UI
2. **Custom Domain**: Add your own domain
3. **Monitoring**: Set up error tracking (Sentry)
4. **Analytics**: Add usage analytics
5. **CI/CD**: Set up GitHub Actions for auto-deploy
6. **Documentation**: Update API docs

---

## Getting Help

If you encounter issues:

1. Check Railway logs: `railway logs`
2. Review this troubleshooting section
3. Ask in Railway Discord: https://discord.gg/railway
4. Check Railway docs: https://docs.railway.app
5. Ask me for help!

---

## Summary

You now have:
- FastAPI backend running on Railway
- PostgreSQL with pgvector extension
- Redis for caching and task queue
- Celery workers processing OCR jobs
- Celery beat scheduling relearning tasks
- HTTPS enabled automatically
- Logs and monitoring available

Total cost: **$5/month**

Congratulations on your deployment!
