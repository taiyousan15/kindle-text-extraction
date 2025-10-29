# CI/CD Pipeline Guide

## Overview

This project uses GitHub Actions for continuous integration and continuous deployment. The pipeline ensures code quality, security, and reliability through automated testing and deployment.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions Workflows                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │    CI    │  │  Docker  │  │   Code   │  │ Security │   │
│  │ Pipeline │  │  Build   │  │ Quality  │  │   Scan   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↓             ↓             ↓             ↓          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Test   │  │   Push   │  │   Lint   │  │ CodeQL   │   │
│  │  Suite   │  │  Image   │  │  Check   │  │ Analysis │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Workflows

### 1. CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`

**What it does:**
1. Spins up PostgreSQL (with pgvector) and Redis
2. Installs system dependencies (Tesseract OCR, etc.)
3. Installs Python dependencies
4. Runs database migrations
5. Executes comprehensive test suite
6. Uploads test results as artifacts

**Status Badge:**
```markdown
[![CI Pipeline](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/ci.yml)
```

### 2. Docker Build & Push (`docker.yml`)

**Triggers:**
- Push to `main` branch
- Git tags matching `v*.*.*`
- Manual workflow dispatch

**What it does:**
1. Builds multi-stage Docker image
2. Pushes to GitHub Container Registry (ghcr.io)
3. Tags with version, branch, and SHA
4. Uses layer caching for faster builds

**Status Badge:**
```markdown
[![Docker Build](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/docker.yml)
```

### 3. Code Quality (`lint.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main`

**What it does:**
1. Black - Code formatting check
2. isort - Import sorting check
3. Flake8 - PEP 8 linting
4. MyPy - Type checking
5. Bandit - Security vulnerability scanning

**Status Badge:**
```markdown
[![Code Quality](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/lint.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/lint.yml)
```

### 4. Security Scan (`security.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main`
- Weekly schedule (Sunday 00:00 UTC)
- Manual dispatch

**What it does:**
1. Safety - Python dependency vulnerability check
2. CodeQL - Static code analysis
3. TruffleHog - Secret scanning

**Status Badge:**
```markdown
[![Security Scan](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/security.yml/badge.svg)](https://github.com/taiyousan15/kindle-text-extraction/actions/workflows/security.yml)
```

### 5. Performance Tests (`performance.yml`)

**Triggers:**
- Push to `main`
- Pull requests to `main`
- Weekly schedule (Monday 02:00 UTC)
- Manual dispatch

**What it does:**
1. Runs performance benchmarks
2. Verifies database indexes
3. Tests query performance

### 6. Release (`release.yml`)

**Triggers:**
- Git tags matching `v*.*.*`

**What it does:**
1. Generates changelog from commits
2. Creates GitHub Release
3. Attaches release notes
4. Links to Docker images

## Required Secrets

Configure these secrets in your GitHub repository settings:
**Settings → Secrets and variables → Actions → New repository secret**

### Required Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key for LLM tests | `sk-ant-...` |
| `OPENAI_API_KEY` | OpenAI API key (optional, for tests) | `sk-...` |

### Optional Secrets

| Secret Name | Description | When Needed |
|------------|-------------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub username | If pushing to Docker Hub |
| `DOCKERHUB_TOKEN` | Docker Hub access token | If pushing to Docker Hub |

**Note:** By default, Docker images are pushed to GitHub Container Registry (ghcr.io), which uses `GITHUB_TOKEN` (automatically provided).

## Local Testing

### Run Tests Locally

```bash
# Start services
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 10

# Install dependencies
pip install -r requirements.txt

# Run migrations
export DATABASE_URL="postgresql://kindle_user:kindle_password@localhost:5432/kindle_ocr"
export REDIS_URL="redis://localhost:6379/0"
alembic upgrade head

# Run tests
pytest test_comprehensive.py -v
pytest test_auth.py -v
pytest test_rate_limiting.py -v
```

### Test Workflows Locally with Act

Install `act`: https://github.com/nektos/act

```bash
# Install act (macOS)
brew install act

# Run CI workflow
act push -W .github/workflows/ci.yml

# Run with secrets
act push -W .github/workflows/ci.yml --secret-file .env.secrets

# Test specific job
act push -j test
```

### Lint Locally

```bash
# Install linting tools
pip install black flake8 mypy isort bandit

# Format code
black app/
isort app/

# Check formatting
black --check app/
isort --check-only app/

# Lint
flake8 app/ --max-line-length=120 --exclude=__pycache__

# Type check
mypy app/ --ignore-missing-imports

# Security check
bandit -r app/ -ll
```

## Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test Locally**
   ```bash
   # Format code
   black app/
   isort app/

   # Run tests
   pytest test_comprehensive.py -v
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Wait for CI Checks**
   - All workflows must pass
   - Code quality checks must pass
   - Security scans must pass

6. **Review and Merge**
   - Get approval from maintainers
   - Merge to main

## Release Process

### Creating a Release

1. **Update Version**
   ```bash
   # Create version tag
   git tag -a v1.0.0 -m "Release v1.0.0"
   ```

2. **Push Tag**
   ```bash
   git push origin v1.0.0
   ```

3. **Automated Process**
   - `release.yml` workflow triggers
   - GitHub Release is created
   - Docker image is built and tagged
   - Changelog is generated

4. **Verify Release**
   - Check GitHub Releases page
   - Verify Docker image: `docker pull ghcr.io/taiyousan15/kindle-text-extraction:v1.0.0`

## Deployment

### Pull Latest Docker Image

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/taiyousan15/kindle-text-extraction:latest

# Or specific version
docker pull ghcr.io/taiyousan15/kindle-text-extraction:v1.0.0
```

### Deploy with Docker Compose

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

## Troubleshooting

### CI Pipeline Failures

#### Test Failures
```bash
# Check test logs in GitHub Actions
# Download test artifacts for detailed analysis

# Run tests locally to debug
pytest test_comprehensive.py -v --tb=long
```

#### Database Connection Issues
```bash
# Ensure PostgreSQL service is healthy
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

#### Redis Connection Issues
```bash
# Ensure Redis service is healthy
docker-compose ps redis

# Check logs
docker-compose logs redis
```

### Docker Build Failures

#### Build Context Too Large
```bash
# Check .dockerignore
cat .dockerignore

# Add to .dockerignore:
# .git
# __pycache__
# *.pyc
# .pytest_cache
# node_modules
```

#### Dependency Installation Failures
```bash
# Test locally
docker build -t kindle-ocr:test .

# Check requirements.txt
cat requirements.txt
```

### Secret Configuration Issues

#### Missing Secrets
1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add required secrets

#### Secret Not Available in Fork
- Forks don't have access to repository secrets
- Add secrets to your fork for testing

### Performance Test Failures

```bash
# Run locally with profiling
pytest test_query_performance.py -v --profile

# Check database indexes
python verify_indexes.py

# Analyze slow queries
docker-compose exec postgres psql -U kindle_user -d kindle_ocr -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

## Monitoring

### GitHub Actions Dashboard

View all workflow runs:
https://github.com/taiyousan15/kindle-text-extraction/actions

### Workflow Run History

- Click on any workflow to see run history
- View logs for each step
- Download artifacts (test results, reports)

### Email Notifications

GitHub sends email notifications for:
- Workflow failures
- First workflow success after failures
- Configure in Settings → Notifications

## Best Practices

### Commit Messages

Follow conventional commits:
```
feat: add new feature
fix: bug fix
docs: documentation update
style: formatting changes
refactor: code refactoring
test: add tests
chore: maintenance tasks
```

### Branch Strategy

```
main (production)
  ↑
develop (staging)
  ↑
feature/your-feature (development)
```

### Testing Strategy

1. **Unit Tests** - Test individual functions
2. **Integration Tests** - Test API endpoints
3. **Performance Tests** - Benchmark queries
4. **Security Tests** - Scan vulnerabilities

### Security

- Never commit secrets or API keys
- Use `.env` files (gitignored)
- Use GitHub Secrets for CI/CD
- Run security scans regularly
- Keep dependencies updated

## Rollback Procedures

### Rollback Docker Image

```bash
# List available tags
docker images ghcr.io/taiyousan15/kindle-text-extraction

# Deploy previous version
docker-compose down
docker pull ghcr.io/taiyousan15/kindle-text-extraction:v0.9.0
docker-compose up -d
```

### Rollback Database Migration

```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# View migration history
alembic history
```

### Rollback Git Commit

```bash
# Soft reset (keep changes)
git reset --soft HEAD~1

# Hard reset (discard changes)
git reset --hard HEAD~1

# Revert commit (create new commit)
git revert HEAD
```

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [Project Deployment Guide](DEPLOYMENT.md)
- [Architecture Documentation](ARCHITECTURE_DIAGRAM.md)

## Support

For issues or questions:
1. Check existing GitHub Issues
2. Create new issue with detailed description
3. Include logs and error messages
4. Tag with appropriate labels (bug, enhancement, question)
