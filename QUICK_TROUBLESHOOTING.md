# ⚡ Quick Troubleshooting Guide
# クイックトラブルシューティングガイド

## 🚨 Common Issues and Solutions / よくある問題と解決策

### 1. "Connection Refused" Errors / "接続拒否"エラー

#### PostgreSQL Connection Refused
```bash
# Error:
connection to server at "localhost" (127.0.0.1), port 5432 failed: Connection refused

# Fix:
colima start
docker-compose up -d postgres redis

# Verify:
docker ps | grep kindle
```

#### Redis Connection Refused
```bash
# Error:
Error 61 connecting to localhost:6379. Connection refused.

# Fix:
docker-compose up -d redis

# Verify:
docker exec -it kindle_redis redis-cli ping
# Should return: PONG
```

---

### 2. Tesseract Language Errors / Tesseract言語エラー

#### Japanese Language Not Found
```bash
# Error:
TesseractError: (1, 'Error opening data file...')

# Fix:
brew install tesseract-lang

# Verify:
tesseract --list-langs | grep jpn
# Should show: jpn, jpn_vert
```

---

### 3. Claude API Errors / Claude APIエラー

#### Model Not Found (404)
```bash
# Error:
Error code: 404 - {'type': 'not_found_error', 'message': 'model: claude-3-5-sonnet-20241022'}

# Fix:
# Update .env with available model:
CLAUDE_MODEL=claude-3-haiku-20240307

# Verify:
python3 test_claude_models.py
```

#### API Key Invalid
```bash
# Error:
Error code: 401 - Authentication error

# Fix:
# Check your .env file:
ANTHROPIC_API_KEY=sk-ant-api03-...

# Ensure no spaces or quotes around the key
```

---

### 4. Import Errors / インポートエラー

#### "No module named 'app.models.capture'"
```bash
# Error:
ModuleNotFoundError: No module named 'app.models.capture'

# Fix:
# This model doesn't exist in the codebase
# Use these instead:
from app.models.ocr_result import OCRResult
from app.models.summary import Summary
from app.models.knowledge import Knowledge
```

#### "No module named 'app.services.rag'"
```bash
# Error:
ModuleNotFoundError: No module named 'app.services.rag'

# Fix:
# RAG services are in the root services directory:
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
```

---

### 5. Docker Issues / Docker問題

#### Colima Not Running
```bash
# Error:
Cannot connect to the Docker daemon at unix:///.../docker.sock

# Fix:
colima start

# Verify:
colima status
docker ps
```

#### Container Won't Start
```bash
# Error:
Container kindle_postgres exited with code 1

# Fix:
# Check logs:
docker logs kindle_postgres

# Remove and recreate:
docker-compose down
docker-compose up -d postgres redis
```

---

## 🔧 Quick Commands / クイックコマンド

### System Health Check / システム健全性チェック
```bash
# Run comprehensive test:
python3 test_final_system_check.py

# Test services only:
python3 test_services.py

# Test functionality only:
python3 test_core_functionality.py
```

### Start/Stop System / システムの起動/停止
```bash
# Start all services:
docker-compose up -d

# Start only databases:
docker-compose up -d postgres redis

# Stop all:
docker-compose down

# View logs:
docker-compose logs -f
```

### Database Operations / データベース操作
```bash
# Connect to PostgreSQL:
docker exec -it kindle_postgres psql -U kindle_user -d kindle_ocr

# Check tables:
\dt

# Exit:
\q
```

### Redis Operations / Redis操作
```bash
# Connect to Redis:
docker exec -it kindle_redis redis-cli

# Test connection:
PING

# Check keys:
KEYS *

# Exit:
exit
```

---

## 🧪 Test Login Automation / ログイン自動化テスト

### Prerequisites / 前提条件
```bash
# Set credentials in .env:
AMAZON_EMAIL=your_email@example.com
AMAZON_PASSWORD=your_password
```

### Run Test / テスト実行
```bash
# Test login (visible browser):
python3 test_login_final.py

# Note:
# - Browser will open visibly (headless=False)
# - Manually enter 2FA code when prompted
# - Wait for test to complete (up to 3 minutes)
```

---

## 📊 View System Status / システム状態確認

### Check All Components / 全コンポーネント確認
```bash
# One command to check everything:
python3 test_final_system_check.py
```

### Expected Output / 期待される出力
```
✅ PASS: Environment Configuration
✅ PASS: File Permissions
✅ PASS: Docker Services
✅ PASS: Service Tests
✅ PASS: Functionality Tests

Total: 5/5 checks passed (100.0%)
🎉 SYSTEM STATUS: FULLY OPERATIONAL
```

---

## 🚀 Start Application / アプリケーション起動

### Full Stack (Docker) / フルスタック (Docker)
```bash
# Start everything:
docker-compose up -d

# Access UI:
open http://localhost:8501

# Access API docs:
open http://localhost:8000/docs
```

### Local Development / ローカル開発
```bash
# Terminal 1: Databases
docker-compose up -d postgres redis

# Terminal 2: FastAPI
uvicorn app.main:app --reload --port 8000

# Terminal 3: Streamlit
streamlit run app/ui/Home.py --server.port 8501

# Terminal 4: Celery (optional)
celery -A app.tasks.celery_app worker --loglevel=info
```

---

## 📝 Environment Variables Checklist / 環境変数チェックリスト

### Critical (Required) / 必須
- [x] `DATABASE_URL` - PostgreSQL connection string
- [x] `REDIS_URL` - Redis connection string
- [x] `ANTHROPIC_API_KEY` - Claude API key
- [x] `CLAUDE_MODEL` - Must be `claude-3-haiku-20240307`
- [x] `LLM_PROVIDER` - Set to `anthropic`

### Optional / オプション
- [ ] `AMAZON_EMAIL` - For login automation
- [ ] `AMAZON_PASSWORD` - For login automation
- [ ] `OPENAI_API_KEY` - If using GPT models

---

## 🆘 Emergency Reset / 緊急リセット

### Complete System Reset / 完全システムリセット
```bash
# Stop everything:
docker-compose down -v

# Remove all containers and volumes:
docker system prune -a --volumes

# Restart from scratch:
colima start
docker-compose up -d postgres redis

# Run tests:
python3 test_final_system_check.py
```

---

## 📞 Where to Find Help / ヘルプの場所

### Documentation Files / ドキュメントファイル
1. `DEBUGGING_REPORT.md` - Complete debugging report
2. `README.md` - Project overview and setup
3. `DEPLOYMENT.md` - Deployment instructions
4. `USER_GUIDE_COMPLETE.md` - End-user guide

### Test Scripts / テストスクリプト
1. `test_final_system_check.py` - Comprehensive health check
2. `test_services.py` - Core services verification
3. `test_core_functionality.py` - Functional module tests
4. `test_login_final.py` - Login automation test

---

**Last Updated / 最終更新**: 2025-11-01
**System Version / システムバージョン**: v1.0 (Post-Debug)
**Status / 状態**: ✅ FULLY OPERATIONAL
