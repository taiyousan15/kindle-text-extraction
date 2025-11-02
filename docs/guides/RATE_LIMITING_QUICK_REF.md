# Rate Limiting Quick Reference

## Quick Start

### Enable Rate Limiting
```bash
# .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1
```

### Test Rate Limiting
```bash
# Test with 5/minute endpoint
for i in {1..10}; do
  curl http://localhost:8000/test/rate-limit
  sleep 0.1
done
```

## Rate Limits by Endpoint

| Endpoint | Limit | Path |
|----------|-------|------|
| OCR Upload | 10/min | POST /api/v1/ocr/upload |
| RAG Query | 20/min | POST /api/v1/rag/query |
| Summary | 5/min | POST /api/v1/summary/create |
| Auth | 5/min | POST /api/v1/auth/login, /register |
| Health | 60/min | GET /health |
| Test | 5/min | GET /test/rate-limit |

## Common Operations

### Add IP to Whitelist
```python
from app.services.rate_limiter import get_ip_manager
ip_manager = get_ip_manager()
ip_manager.add_to_whitelist("192.168.1.100")
```

### Blacklist IP
```python
from app.services.rate_limiter import get_ip_manager
ip_manager = get_ip_manager()
ip_manager.add_to_blacklist("1.2.3.4", duration_seconds=86400)
```

### Check Whitelist/Blacklist
```python
from app.services.rate_limiter import get_ip_manager
ip_manager = get_ip_manager()
whitelist = ip_manager.get_whitelist()
blacklist = ip_manager.get_blacklist()
```

## 429 Response Format

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests to {endpoint}. Please try again in {retry_after} seconds.",
  "retry_after": 60,
  "endpoint": "/api/v1/ocr/upload",
  "limit": "429: 10 per 1 minute",
  "documentation": "See API documentation for rate limits: /docs"
}
```

## Monitoring

### View Logs
```bash
tail -f logs/app.log | grep "Rate limit exceeded"
```

### Redis Keys
```bash
# View rate limit keys
redis-cli -n 1 KEYS "ratelimit:*"

# View whitelist
redis-cli -n 1 SMEMBERS "ratelimit:whitelist"

# View blacklist
redis-cli -n 1 SMEMBERS "ratelimit:blacklist"
```

## Troubleshooting

### Rate limiting not working
1. Check RATE_LIMIT_ENABLED=true in .env
2. Verify Redis is running: `redis-cli ping`
3. Check logs for initialization: `grep "Rate limiter" logs/app.log`

### Getting 429 too quickly
1. Clear Redis: `redis-cli -n 1 FLUSHDB`
2. Check if IP is blacklisted
3. Verify endpoint limit is correct

### Rate limits not resetting
1. Wait full minute + 5 seconds
2. Check Redis TTL: `redis-cli -n 1 TTL ratelimit:{endpoint}:{ip}`
3. Restart Redis if needed
