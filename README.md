# Kindle OCR & RAG System

[![CI Pipeline](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml)
[![Docker Build](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml)
[![Code Quality](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/lint.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/lint.yml)
[![Security Scan](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/security.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/security.yml)
[![Performance Tests](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/performance.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/performance.yml)

A production-ready system for extracting text from Kindle screenshots using OCR and enabling intelligent question-answering through Retrieval-Augmented Generation (RAG).

## Features

### Core Capabilities
- **Automated Kindle Page Capture** - PyAutoGUI and Selenium-based screenshot automation
- **High-Accuracy OCR** - Japanese/English text extraction with Tesseract
- **Vector Search** - pgvector-powered semantic search over extracted text
- **RAG-Based Q&A** - Context-aware answers using Claude/GPT-4
- **Knowledge Extraction** - Automatic extraction of key insights from books
- **Business Card OCR** - Extract and structure business card information
- **RESTful API** - FastAPI-based backend with comprehensive endpoints
- **Web UI** - Streamlit-based user interface

### Enterprise Features
- **Authentication & Authorization** - JWT-based user authentication
- **Rate Limiting** - Per-user API rate limits with Redis
- **Performance Optimization** - Database indexing for sub-second queries
- **Async Task Processing** - Celery-based background job processing
- **Scheduled Retraining** - Automatic model retraining with user feedback
- **Comprehensive Monitoring** - Health checks, metrics, and logging
- **Docker Support** - Full containerization with docker-compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 15+ with pgvector
- Redis 7+

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/taiyousan15/kindle-text-extraction.git
   cd kindle-text-extraction
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Initialize Database**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

5. **Access Applications**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Streamlit UI: http://localhost:8501

## Documentation

- [CI/CD Guide](CI_CD_GUIDE.md) - Comprehensive CI/CD pipeline documentation
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [User Guide](USER_GUIDE_COMPLETE.md) - Complete user documentation
- [Architecture Diagram](ARCHITECTURE_DIAGRAM.md) - System architecture overview
- [Performance Guide](PERFORMANCE_INDEXES_REPORT.md) - Performance optimization details

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout

### OCR
- `POST /api/v1/ocr/upload` - Upload and process image
- `GET /api/v1/ocr/job/{job_id}` - Get job status
- `GET /api/v1/ocr/jobs` - List all jobs

### Capture
- `POST /api/v1/capture/start` - Start auto capture
- `POST /api/v1/capture/stop` - Stop capture

### RAG & Knowledge
- `POST /api/v1/rag/ask` - Ask questions about extracted text
- `POST /api/v1/knowledge/extract` - Extract key insights
- `GET /api/v1/knowledge/list` - List extracted knowledge

### Summary
- `POST /api/v1/summary/create` - Create summary
- `GET /api/v1/summary/{summary_id}` - Get summary

### Business
- `POST /api/v1/business/card/extract` - Extract business card info
- `POST /api/v1/business/ask` - Ask business-related questions

### Feedback
- `POST /api/v1/feedback/submit` - Submit user feedback
- `GET /api/v1/feedback/stats` - Get feedback statistics

See [API Documentation](http://localhost:8000/docs) for complete endpoint details.

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migration tool
- **Celery** - Distributed task queue
- **Redis** - Caching and message broker

### Database
- **PostgreSQL 15** - Primary database
- **pgvector** - Vector similarity search extension

### AI/ML
- **Tesseract OCR** - Text extraction
- **Anthropic Claude** - LLM for RAG and summarization
- **OpenAI GPT-4** - Alternative LLM
- **sentence-transformers** - Text embeddings
- **LangChain** - RAG framework

### Frontend
- **Streamlit** - Web UI framework

### DevOps
- **Docker** - Containerization
- **GitHub Actions** - CI/CD
- **pytest** - Testing framework

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│ PostgreSQL  │
│     UI      │     │     API     │     │  +pgvector  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Celery    │────▶│    Redis    │
                    │   Worker    │     │             │
                    └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Tesseract  │
                    │     OCR     │
                    └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Claude AI  │
                    │  RAG/LLM    │
                    └─────────────┘
```

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install tesseract tesseract-lang

# Install system dependencies (Ubuntu)
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

# Run database locally
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start Streamlit UI (separate terminal)
streamlit run app/ui/Home.py
```

### Testing

```bash
# Run all tests
pytest test_comprehensive.py -v

# Run specific test suite
pytest test_auth.py -v
pytest test_rate_limiting.py -v
pytest test_query_performance.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
black app/
isort app/

# Lint
flake8 app/ --max-line-length=120

# Type check
mypy app/ --ignore-missing-imports

# Security scan
bandit -r app/ -ll
```

## CI/CD Pipeline

This project uses GitHub Actions for automated testing and deployment:

- **Continuous Integration** - Runs tests on every push/PR
- **Docker Build** - Builds and pushes Docker images
- **Code Quality** - Linting and formatting checks
- **Security Scanning** - Dependency and code vulnerability scans
- **Performance Tests** - Database query performance benchmarks
- **Automated Releases** - Creates GitHub releases on version tags

See [CI/CD Guide](CI_CD_GUIDE.md) for detailed information.

## Deployment

### Docker Deployment

```bash
# Pull latest image
docker pull ghcr.io/taiyousan15/kindle-text-extraction:latest

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

### Manual Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production deployment instructions.

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kindle_ocr

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Services
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Amazon Credentials (for auto capture)
AMAZON_EMAIL=your-email@example.com
AMAZON_PASSWORD=your-password

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Rate Limiting
MONTHLY_TOKEN_CAP=10000000

# Scheduling
RELEARN_CRON=0 3 * * *  # Daily at 3 AM
TIMEZONE=Asia/Tokyo
```

See [.env.example](.env.example) for complete configuration options.

## Performance

- **OCR Processing**: ~2-3 seconds per image
- **Vector Search**: <100ms for similarity queries
- **RAG Queries**: ~1-2 seconds (depending on LLM)
- **Database Queries**: <50ms with proper indexing

See [PERFORMANCE_INDEXES_REPORT.md](PERFORMANCE_INDEXES_REPORT.md) for optimization details.

## Security

- JWT-based authentication
- Rate limiting (100 req/min per user)
- SQL injection prevention (parameterized queries)
- XSS protection (input sanitization)
- CORS configuration
- Secrets management via environment variables
- Regular dependency updates via Dependabot

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Format code (`black app/ && isort app/`)
4. Run tests (`pytest test_comprehensive.py -v`)
5. Commit changes (`git commit -m 'feat: add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

## Versioning

We use [SemVer](https://semver.org/) for versioning:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Current version: **1.0.0**

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Text extraction engine
- [Anthropic Claude](https://www.anthropic.com/) - LLM for RAG
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [LangChain](https://www.langchain.com/) - RAG framework

## Support

- **Documentation**: See [docs](https://github.com/taiyousan15/kindle-text-extraction/tree/main)
- **Issues**: [GitHub Issues](https://github.com/taiyousan15/kindle-text-extraction/issues)
- **Discussions**: [GitHub Discussions](https://github.com/taiyousan15/kindle-text-extraction/discussions)

## Roadmap

- [ ] Multi-language support (Chinese, Korean)
- [ ] PDF direct processing
- [ ] Mobile app
- [ ] Cloud deployment templates (AWS, GCP, Azure)
- [ ] Advanced analytics dashboard
- [ ] Custom model training interface

---

**Built with Claude Code** | **Production-Ready Since 2024**
