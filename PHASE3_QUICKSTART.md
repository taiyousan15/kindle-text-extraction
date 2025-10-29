# Phase 3 Summary - Quick Start Guide

## Prerequisites

1. **Database running** (PostgreSQL with existing tables)
2. **FastAPI server** (from Phase 1-2)
3. **API Key** (optional, works in mock mode without it)

## Setup

### 1. Apply Database Migration

```bash
# Connect to database
psql -U kindle_user -d kindle_ocr

# Run migration
\i migrations/003_add_summary_format_language.sql

# Verify columns added
\d summaries
# Should show 'format' and 'language' columns
```

### 2. Configure API Key (Optional)

Edit `.env` file:
```bash
# Use Anthropic (Claude) - Recommended
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Or OpenAI (GPT-4)
OPENAI_API_KEY=sk-your-key-here
```

**Note**: Works without API keys in mock mode for testing.

### 3. Start Server

```bash
# From project root
uvicorn app.main:app --reload

# Server should start on http://localhost:8000
# Check logs for: "Phase 3: 要約エンドポイント" router registered
```

### 4. Verify Installation

Open browser: http://localhost:8000/docs

You should see new "Summary" section with endpoints:
- POST `/api/v1/summary/create`
- POST `/api/v1/summary/create-multilevel`
- GET `/api/v1/summary/{summary_id}`
- GET `/api/v1/summary/job/{job_id}`
- PUT `/api/v1/summary/{summary_id}/regenerate`
- DELETE `/api/v1/summary/{summary_id}`

## Quick Test

### Test 1: Create Simple Summary

```bash
curl -X POST "http://localhost:8000/api/v1/summary/create" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "人工知能（AI）は、近年急速に発展しており、私たちの生活に大きな影響を与えています。特に機械学習と深層学習の進歩により、画像認識、自然言語処理、音声認識などの分野で著しい成果が得られています。",
    "book_title": "AI入門",
    "length": "short",
    "tone": "professional"
  }'
```

**Expected Response**:
```json
{
  "summary_id": 1,
  "job_id": "...",
  "book_title": "AI入門",
  "summary_text": "人工知能は急速に発展し、機械学習と深層学習により様々な分野で成果を上げている。",
  "language": "ja",
  "token_usage": {"total": 150, "prompt": 100, "completion": 50},
  ...
}
```

### Test 2: Multi-level Summary

```bash
curl -X POST "http://localhost:8000/api/v1/summary/create-multilevel" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "人工知能（AI）は、近年急速に発展しており...",
    "book_title": "AI入門",
    "tone": "professional"
  }'
```

**Expected Response**: 3 summary levels (executive, standard, detailed)

### Test 3: Run Full Test Suite

```bash
# Make executable
chmod +x test_summary.py

# Run tests
./test_summary.py
```

**Expected Output**:
```
====================================================================
SUMMARY SERVICE & API TEST SUITE - Phase 3
====================================================================

✅ PASS: Basic Summarization
✅ PASS: Multi-level Summarization
...

Results: 10/10 tests passed (100.0%)
```

## Common Issues

### Issue: "Module 'summary' not found"

**Fix**: Restart server
```bash
# Stop (Ctrl+C) and restart
uvicorn app.main:app --reload
```

### Issue: Mock responses in production

**Check**: API key configuration
```bash
# Verify .env
cat .env | grep API_KEY

# Should show your API key
# If empty, add:
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

### Issue: Column 'format' does not exist

**Fix**: Run migration
```bash
psql -U kindle_user -d kindle_ocr -f migrations/003_add_summary_format_language.sql
```

## Usage Examples

### Example 1: Summary from OCR Job

First, create OCR job (Phase 1):
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/upload" \
  -F "file=@image.png" \
  -F "book_title=My Book" \
  -F "page_num=1"

# Response: {"job_id": "550e8400-..."}
```

Then, create summary:
```bash
curl -X POST "http://localhost:8000/api/v1/summary/create" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "length": "medium",
    "tone": "professional"
  }'
```

### Example 2: Bullet Points Format

```bash
curl -X POST "http://localhost:8000/api/v1/summary/create" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your long text...",
    "book_title": "Book",
    "format": "bullet_points",
    "length": "medium"
  }'
```

### Example 3: Get All Summaries for Job

```bash
curl "http://localhost:8000/api/v1/summary/job/550e8400-e29b-41d4-a716-446655440000"
```

## API Parameters Reference

### Length Options:
- `short`: 100-200 chars
- `medium`: 200-500 chars (default)
- `long`: 500-1000 chars

### Tone Options:
- `professional`: Business style (default)
- `casual`: Friendly style
- `academic`: Scholarly style
- `executive`: Executive summary style

### Granularity Options:
- `high_level`: Main points only (default)
- `detailed`: Include examples
- `comprehensive`: Full coverage

### Format Options:
- `plain_text`: Paragraph format (default)
- `bullet_points`: Bulleted list
- `structured`: Sections with headers

## Next Steps

1. **Integrate with UI** (Streamlit/React)
2. **Add to RAG system** for searchable summaries
3. **Batch processing** for multiple books
4. **Export features** (PDF, Word, etc.)

## Documentation

- **Full Documentation**: `PHASE3_SUMMARY.md`
- **API Docs**: http://localhost:8000/docs
- **Test Suite**: `test_summary.py`

## Support

For issues or questions:
1. Check `PHASE3_SUMMARY.md` for detailed documentation
2. Run test suite to verify setup
3. Check server logs for errors
4. Verify database migration applied

## Success Criteria

Phase 3 is working correctly if:
- ✅ Server starts without errors
- ✅ `/docs` shows Summary endpoints
- ✅ Test suite passes (10/10 tests)
- ✅ Can create summaries via API
- ✅ Summaries stored in database
- ✅ Japanese text detected and summarized correctly

You're now ready to use the Phase 3 Summary system!
