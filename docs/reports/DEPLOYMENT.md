# Kindle OCR System - Production Deployment Guide

Complete guide for deploying the Kindle OCR System to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Initial Deployment](#initial-deployment)
4. [Configuration](#configuration)
5. [Security Best Practices](#security-best-practices)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup & Restore](#backup--restore)
8. [Scaling](#scaling)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU**: 4+ cores recommended (8+ for production)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Disk**: 50GB+ SSD (100GB+ recommended)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### Required Software

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

### API Keys Required

- **Anthropic API Key** (required): For Claude AI
- **OpenAI API Key** (optional): For GPT models
- **Amazon Credentials** (optional): For Kindle automation

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd Kindle文字起こしツール
```

### 2. Create Environment File

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Database Configuration
POSTGRES_DB=kindle_ocr
POSTGRES_USER=kindle_user
POSTGRES_PASSWORD=<STRONG_PASSWORD_HERE>
POSTGRES_PORT=5432

# Redis Configuration
REDIS_PASSWORD=<STRONG_PASSWORD_HERE>
REDIS_PORT=6379

# API Keys
ANTHROPIC_API_KEY=<YOUR_ANTHROPIC_API_KEY>
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>

# Amazon Credentials (optional)
AMAZON_EMAIL=<YOUR_AMAZON_EMAIL>
AMAZON_PASSWORD=<YOUR_AMAZON_PASSWORD>

# Application Configuration
MONTHLY_TOKEN_CAP=10000000
RELEARN_CRON="0 3 * * *"  # Daily at 3 AM
TIMEZONE=Asia/Tokyo
LOG_LEVEL=INFO

# Ports
API_PORT=8000
STREAMLIT_PORT=8501
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=<STRONG_PASSWORD_HERE>
```

### 3. Create SSL Certificates

For production with HTTPS:

```bash
# Create SSL directory
mkdir -p deployment/nginx/ssl

# Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/nginx/ssl/key.pem \
  -out deployment/nginx/ssl/cert.pem

# OR use Let's Encrypt (recommended for production)
# See: https://letsencrypt.org/getting-started/
```

---

## Initial Deployment

### Quick Start (Recommended)

Use the Makefile for simplified deployment:

```bash
# Complete deployment with one command
make quickstart
```

This will:
1. Build Docker images
2. Start all services
3. Run database migrations
4. Display access URLs

### Manual Deployment

If you prefer manual control:

```bash
# 1. Build images
docker-compose -f docker-compose.prod.yml build

# 2. Start services
docker-compose -f docker-compose.prod.yml up -d

# 3. Wait for services to be ready
sleep 10

# 4. Run database migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# 5. Verify deployment
docker-compose -f docker-compose.prod.yml ps
```

### Verify Deployment

```bash
# Check service health
make health-check

# Or manually:
curl http://localhost:8000/health
curl http://localhost:8501/_stcore/health
```

---

## Configuration

### Application Services

The system consists of 8 main services:

1. **postgres**: PostgreSQL database with pgvector
2. **redis**: Redis cache and message broker
3. **api**: FastAPI application (REST API)
4. **worker**: Celery worker (background tasks)
5. **beat**: Celery beat (scheduler)
6. **streamlit**: Streamlit UI
7. **prometheus**: Metrics collection
8. **grafana**: Metrics visualization
9. **nginx**: Reverse proxy (optional)

### Resource Limits

Default resource limits are set in `docker-compose.prod.yml`:

```yaml
# API Service
resources:
  limits:
    cpus: '4'
    memory: 4G
  reservations:
    cpus: '2'
    memory: 2G
```

Adjust based on your hardware:

```bash
# Edit docker-compose.prod.yml
vim docker-compose.prod.yml
```

### Scaling Workers

To handle more concurrent tasks:

```bash
# Scale to 5 workers
make scale-workers COUNT=5

# Or manually:
docker-compose -f docker-compose.prod.yml up -d --scale worker=5
```

---

## Security Best Practices

### 1. Secure Passwords

Generate strong passwords:

```bash
# Generate random password
openssl rand -base64 32
```

### 2. API Key Management

Store API keys securely:

```bash
# Never commit .env to version control
echo ".env" >> .gitignore

# Use environment variables in production
export ANTHROPIC_API_KEY="your-key-here"
```

### 3. Network Security

Configure firewall:

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 4. SSL/TLS Configuration

Use valid SSL certificates:

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com
```

### 5. Regular Updates

Keep system updated:

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

---

## Monitoring & Logging

### Access Monitoring Dashboards

```bash
# Open all monitoring dashboards
make monitor
```

- **Grafana**: http://localhost:3000 (admin/password from .env)
- **Prometheus**: http://localhost:9090

### View Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-worker
make logs-beat

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f api
```

### Log Aggregation

Logs are stored in:
- `/app/logs/` (inside containers)
- `./logs/` (host mount)

Configure log rotation:

```bash
# Create logrotate config
sudo cat > /etc/logrotate.d/kindle-ocr << EOF
/path/to/Kindle文字起こしツール/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### Monitoring Metrics

Key metrics to monitor:

1. **API Response Time**: < 500ms
2. **Worker Queue Length**: < 100
3. **Database Connections**: < 80% of max
4. **Memory Usage**: < 80% of limit
5. **CPU Usage**: < 80% average

---

## Backup & Restore

### Automated Backups

Schedule daily backups:

```bash
# Add to crontab
crontab -e

# Add this line (daily at 2 AM)
0 2 * * * /path/to/deployment/scripts/backup.sh
```

### Manual Backup

```bash
# Create backup
make backup

# Or use script
./deployment/scripts/backup.sh
```

Backups are stored in `./backups/` with format: `backup_YYYYMMDD_HHMMSS.sql.gz`

### Restore Database

```bash
# List available backups
make backup-list

# Restore from backup
make restore BACKUP=backups/backup_20240101_120000.sql.gz

# Or use script
./deployment/scripts/restore.sh backups/backup_20240101_120000.sql.gz
```

### Backup to Remote Storage

```bash
# Upload to S3 (example)
aws s3 cp backups/ s3://your-bucket/kindle-ocr-backups/ --recursive

# Or use rsync
rsync -avz backups/ user@backup-server:/backups/kindle-ocr/
```

---

## Scaling

### Vertical Scaling

Increase resources for existing services:

```yaml
# In docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 8G
```

### Horizontal Scaling

Scale workers:

```bash
# Scale workers to 10
make scale-workers COUNT=10
```

Scale API instances (requires load balancer):

```bash
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_biz_card_vector ON biz_cards USING ivfflat (vector_embedding vector_cosine_ops);

-- Analyze tables
ANALYZE biz_cards;
ANALYZE feedbacks;
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# View database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Restart database
docker-compose -f docker-compose.prod.yml restart postgres
```

#### 2. Worker Not Processing Tasks

```bash
# Check worker status
make celery-status

# View worker logs
make logs-worker

# Restart worker
docker-compose -f docker-compose.prod.yml restart worker
```

#### 3. API Returning 500 Errors

```bash
# Check API logs
make logs-api

# Check database connection
docker-compose -f docker-compose.prod.yml exec api python -c "from app.core.database import check_connection; print(check_connection())"

# Restart API
docker-compose -f docker-compose.prod.yml restart api
```

#### 4. Out of Memory

```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.prod.yml
# Or reduce worker concurrency
```

#### 5. Disk Space Full

```bash
# Check disk usage
df -h

# Clean old logs
find logs/ -name "*.log" -mtime +7 -delete

# Clean old backups
find backups/ -name "backup_*.sql.gz" -mtime +30 -delete

# Docker cleanup
make prune
```

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart services
make restart
```

---

## Maintenance

### Regular Tasks

#### Daily
- Monitor service health: `make health-check`
- Check logs for errors: `make logs`
- Verify backups: `make backup-list`

#### Weekly
- Review metrics in Grafana
- Check disk space: `df -h`
- Review and rotate logs

#### Monthly
- Update dependencies
- Security audit
- Performance review
- Backup verification (test restore)

### Update Procedure

```bash
# 1. Backup current state
make backup

# 2. Pull latest changes
git pull origin main

# 3. Rebuild images
make build

# 4. Run migrations
make migrate

# 5. Restart services with zero-downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api
docker-compose -f docker-compose.prod.yml up -d --no-deps --build worker
```

### Database Migrations

```bash
# Create new migration
make migrate-create MESSAGE="add_new_column"

# Apply migrations
make migrate

# Rollback if needed
make migrate-down

# View migration history
make migrate-history
```

---

## Performance Tuning

### Database Tuning

```bash
# Edit PostgreSQL configuration
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U kindle_user -d kindle_ocr

# Increase shared_buffers
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET work_mem = '50MB';

# Restart database
docker-compose -f docker-compose.prod.yml restart postgres
```

### Redis Tuning

```bash
# Increase max memory
# In docker-compose.prod.yml, add to redis command:
--maxmemory 1gb --maxmemory-policy allkeys-lru
```

### Celery Tuning

```bash
# Adjust worker concurrency
# In docker-compose.prod.yml:
command: celery -A app.tasks.celery_app worker --concurrency=8
```

---

## Support & Resources

### Documentation
- API Documentation: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Logs
- Application logs: `./logs/`
- Docker logs: `docker-compose logs`

### Monitoring
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

### Commands Reference
```bash
make help  # Show all available commands
```

---

## Quick Reference

```bash
# Start system
make up

# Stop system
make down

# View logs
make logs

# Backup database
make backup

# Restore database
make restore BACKUP=path/to/backup.sql.gz

# Health check
make health-check

# Scale workers
make scale-workers COUNT=5

# Clean up
make clean
```

---

**Last Updated**: 2024-10-28
**Version**: 1.0.0
