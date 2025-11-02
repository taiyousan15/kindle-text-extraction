# Phase 3: Summary Implementation - Complete Documentation

## Overview

Phase 3 implements comprehensive text summarization functionality with LLM-based abstractive and extractive summarization strategies. The implementation supports multiple summarization levels, customizable parameters, and handles both Japanese and English text.

## Architecture

### Components

```
Phase 3 Summary System
├── app/services/summary_service.py      # Core summarization logic
├── app/schemas/summary.py               # Pydantic request/response schemas
├── app/api/v1/endpoints/summary.py      # REST API endpoints
├── app/models/summary.py                # Database model (updated)
├── test_summary.py                      # Comprehensive test suite
└── migrations/003_add_summary_format_language.sql  # Database migration
```

## Features

### 3-1: Summary Service (LLM-based)

**File**: `app/services/summary_service.py`

#### Key Features:
- **Multiple Summarization Strategies**:
  - Extractive: Select key sentences from original text
  - Abstractive: Generate new summary text using LLM
  - Map-Reduce: Handle long documents by chunking → summarize → combine

- **LLM Providers**:
  - Anthropic (Claude): Primary provider
  - OpenAI (GPT-4): Alternative provider
  - Mock mode: Works without API keys for testing

- **Token Management**:
  - Automatic token estimation
  - Per-chunk token limits (3000 tokens/chunk)
  - Total token tracking
  - Cost monitoring

- **Progress Tracking**:
  - Real-time progress updates for long documents
  - Chunk-by-chunk processing feedback

#### Class: `SummaryService`

```python
from app.services.summary_service import (
    SummaryService,
    SummaryLength,
    SummaryTone,
    SummaryGranularity,
    SummaryFormat
)

# Initialize service
service = SummaryService(provider="anthropic")

# Single-level summary
result = service.summarize(
    text="Your text here...",
    length=SummaryLength.MEDIUM,
    tone=SummaryTone.PROFESSIONAL,
    granularity=SummaryGranularity.HIGH_LEVEL,
    format_type=SummaryFormat.PLAIN_TEXT
)

# Multi-level summary (3 levels)
result = service.summarize_multilevel(
    text="Your text here...",
    tone=SummaryTone.PROFESSIONAL
)
```

### 3-2: Customization Options

#### Summary Length
- `SHORT`: 100-200 characters
- `MEDIUM`: 200-500 characters
- `LONG`: 500-1000 characters

#### Tone
- `PROFESSIONAL`: Business-appropriate, formal language
- `CASUAL`: Friendly, conversational style
- `ACADEMIC`: Scholarly, precise terminology
- `EXECUTIVE`: Concise, executive summary style

#### Granularity
- `HIGH_LEVEL`: Main points only
- `DETAILED`: Include examples and details
- `COMPREHENSIVE`: Full coverage without omissions

#### Format
- `PLAIN_TEXT`: Standard paragraph format
- `BULLET_POINTS`: Bulleted list format (• prefix)
- `STRUCTURED`: Sections with headers

#### Language
- Auto-detection: Automatically detects Japanese vs English
- Manual override: Specify `ja` or `en` explicitly
- Preserves source language in summary

### 3-3: Multi-Level Summarization

Generates 3 hierarchical summary levels:

#### Level 1: Executive Summary
- **Length**: 50-100 characters (1-2 sentences)
- **Purpose**: Quick overview for executives/busy readers
- **Granularity**: Highest-level points only

#### Level 2: Standard Summary
- **Length**: 200-300 characters (1 paragraph)
- **Purpose**: Standard summary for general audience
- **Granularity**: Main points with context

#### Level 3: Detailed Summary
- **Length**: 500-1000 characters (multiple paragraphs)
- **Purpose**: Comprehensive summary with details
- **Granularity**: Full coverage with examples

**Progressive Disclosure**: User can start with Level 1, expand to Level 2, then to Level 3 as needed.

### 3-4: API Endpoints

**Base URL**: `/api/v1/summary`

#### POST `/create` - Create Summary

Create a single-level summary from text or OCR job.

**Request**:
```json
{
  "text": "Your text here...",  // or "job_id": "uuid"
  "book_title": "Book Title",
  "length": "medium",
  "tone": "professional",
  "granularity": "high_level",
  "format": "plain_text",
  "language": "ja"  // optional, auto-detected if omitted
}
```

**Response**:
```json
{
  "summary_id": 1,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "book_title": "Book Title",
  "summary_text": "Generated summary text...",
  "language": "ja",
  "granularity": "high_level",
  "length": "medium",
  "tone": "professional",
  "format": "plain_text",
  "token_usage": {
    "total": 250,
    "prompt": 180,
    "completion": 70
  },
  "chunks": 1,
  "is_mock": false,
  "created_at": "2025-10-28T10:30:00"
}
```

#### POST `/create-multilevel` - Create Multi-Level Summary

Create all 3 summary levels in one request.

**Request**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tone": "professional",
  "format": "plain_text"
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "book_title": "Book Title",
  "language": "ja",
  "level_1": {
    "summary": "Executive summary text...",
    "level": 1,
    "tokens": {"total": 100, "prompt": 80, "completion": 20}
  },
  "level_2": {
    "summary": "Standard summary text...",
    "level": 2,
    "tokens": {"total": 200, "prompt": 150, "completion": 50}
  },
  "level_3": {
    "summary": "Detailed summary text...",
    "level": 3,
    "tokens": {"total": 400, "prompt": 300, "completion": 100}
  },
  "total_tokens": {"total": 700, "prompt": 530, "completion": 170},
  "summary_ids": [1, 2, 3],
  "is_mock": false,
  "created_at": "2025-10-28T10:30:00"
}
```

#### GET `/{summary_id}` - Get Summary

Retrieve a specific summary by ID.

**Response**:
```json
{
  "id": 1,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "book_title": "Book Title",
  "summary_text": "Summary text...",
  "granularity": "high_level",
  "length": "medium",
  "tone": "professional",
  "format": "plain_text",
  "language": "ja",
  "created_at": "2025-10-28T10:30:00"
}
```

#### GET `/job/{job_id}` - Get Summaries by Job

Retrieve all summaries associated with a job.

**Response**:
```json
{
  "summaries": [
    {
      "id": 1,
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "book_title": "Book Title",
      "summary_text": "Summary text...",
      "granularity": "high_level",
      "length": "medium",
      "tone": "professional",
      "format": "plain_text",
      "language": "ja",
      "created_at": "2025-10-28T10:30:00"
    }
  ],
  "total": 1
}
```

#### PUT `/{summary_id}/regenerate` - Regenerate Summary

Regenerate summary with different parameters.

**Request**:
```json
{
  "length": "long",
  "tone": "casual",
  "granularity": "detailed",
  "format": "bullet_points"
}
```

**Response**: Same as `/create` response

#### DELETE `/{summary_id}` - Delete Summary

Delete a summary by ID.

**Response**: 204 No Content

## Database Schema

### Summary Table Updates

**File**: `migrations/003_add_summary_format_language.sql`

New columns added:
- `format` VARCHAR(50): Summary format type
- `language` VARCHAR(10): Detected/specified language

```sql
ALTER TABLE summaries
ADD COLUMN IF NOT EXISTS format VARCHAR(50),
ADD COLUMN IF NOT EXISTS language VARCHAR(10);

CREATE INDEX idx_summary_language ON summaries(language);
```

## Japanese Language Support

### Features:
1. **Automatic Language Detection**
   - Detects Japanese characters (ひらがな、カタカナ、漢字)
   - Threshold: 30% Japanese characters → classified as Japanese

2. **Japanese-Optimized Prompts**
   - Native Japanese system prompts
   - Natural Japanese phrasing
   - Preserves nuances and context

3. **Mixed Content Handling**
   - Supports Japanese text with embedded English
   - Maintains proper context for technical terms

### Example:
```python
# Japanese text automatically detected
result = service.summarize(
    text="人工知能は近年急速に発展しており...",
    length=SummaryLength.MEDIUM
)
# result["language"] == "ja"
# result["summary"] will be in Japanese
```

## Long Document Handling

### Map-Reduce Strategy

For documents exceeding 3000 tokens:

1. **Map Phase**: Split into chunks
   - Chunk by paragraphs (preserve context)
   - Fall back to sentence splitting if needed
   - Each chunk ≤ 3000 tokens

2. **Map Phase**: Summarize each chunk
   - Generate intermediate summaries
   - Use MEDIUM or SHORT length for chunks

3. **Reduce Phase**: Combine summaries
   - Merge intermediate summaries
   - Generate final summary with target parameters

### Progress Tracking:
```python
def progress_callback(percent):
    print(f"Progress: {percent}%")

result = service.summarize(
    text=very_long_text,
    length=SummaryLength.MEDIUM,
    progress_callback=progress_callback
)
# Output:
# Progress: 20%
# Progress: 40%
# ...
# Progress: 100%
```

## Testing

### Test Suite: `test_summary.py`

Comprehensive tests covering:

#### Unit Tests (SummaryService):
1. **Basic Summarization**: Single-level Japanese summary
2. **Multi-level Summarization**: 3-level hierarchical summary
3. **Parameter Combinations**: Different length/tone/granularity/format
4. **Long Document Handling**: Map-reduce strategy
5. **Language Detection**: Japanese vs English detection

#### Integration Tests (API + Database):
6. **Create Summary**: POST `/api/v1/summary/create`
7. **Create Multi-level Summary**: POST `/api/v1/summary/create-multilevel`
8. **Get Summary**: GET `/api/v1/summary/{summary_id}`
9. **Get Summaries by Job**: GET `/api/v1/summary/job/{job_id}`
10. **Regenerate Summary**: PUT `/api/v1/summary/{summary_id}/regenerate`

### Running Tests:

```bash
# Make test executable
chmod +x test_summary.py

# Run all tests
./test_summary.py

# Or with python
python test_summary.py
```

**Note**: API tests require FastAPI server running on `localhost:8000`

### Expected Output:
```
====================================================================
SUMMARY SERVICE & API TEST SUITE - Phase 3
====================================================================

====================================================================
UNIT TESTS (SummaryService)
====================================================================

====================================================================
TEST 1: Basic SummaryService - Single-level Japanese Summary
====================================================================
✅ Summary created successfully!
   Language: ja
   Summary: 人工知能（AI）は近年急速に発展し...
   Tokens: {'total': 250, 'prompt': 180, 'completion': 70}
   ...

====================================================================
TEST SUMMARY
====================================================================
✅ PASS: Basic Summarization
✅ PASS: Multi-level Summarization
✅ PASS: Parameter Combinations
...

====================================================================
Results: 10/10 tests passed (100.0%)
====================================================================
```

## Usage Examples

### Example 1: Simple Summary from Text

```python
from app.services.summary_service import SummaryService, SummaryLength, SummaryTone

service = SummaryService(provider="anthropic")

result = service.summarize(
    text="Your long text here...",
    length=SummaryLength.SHORT,
    tone=SummaryTone.CASUAL
)

print(result["summary"])
# Output: Short, casual summary
```

### Example 2: Multi-level Summary via API

```bash
curl -X POST "http://localhost:8000/api/v1/summary/create-multilevel" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "tone": "professional"
  }'
```

### Example 3: Regenerate with Different Format

```bash
curl -X PUT "http://localhost:8000/api/v1/summary/1/regenerate" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "bullet_points",
    "length": "long"
  }'
```

### Example 4: Get All Summaries for a Job

```bash
curl "http://localhost:8000/api/v1/summary/job/550e8400-e29b-41d4-a716-446655440000"
```

## Error Handling

### Common Errors:

1. **Empty Text**:
   ```json
   {"error": "Text cannot be empty"}
   ```

2. **Invalid Job ID**:
   ```json
   {"error": "Job not found: invalid-uuid"}
   ```

3. **No OCR Results**:
   ```json
   {"error": "No OCR results found for job: uuid"}
   ```

4. **LLM Timeout**:
   - Automatic retry (3 attempts)
   - Exponential backoff
   - Final error if all retries fail

5. **Token Limit Exceeded**:
   - Automatic chunking for long documents
   - Map-reduce strategy applied

## Mock Mode

For testing without API keys:

```python
# Service will automatically use mock mode if API keys not set
service = SummaryService(provider="anthropic")
# If ANTHROPIC_API_KEY not set:
# - service.llm_service.is_mock == True
# - Returns placeholder summaries
# - Useful for testing API structure
```

Mock response format:
```
[MOCK RESPONSE]

これはモックレスポンスです。実際のLLM APIキーが設定されていません。

受信したプロンプト（最初の100文字）:
Your prompt here...

本番環境では、ANTHROPIC_API_KEYまたはOPENAI_API_KEYを設定してください。
```

## Performance Considerations

### Token Limits:
- **Per-chunk**: 3000 tokens max
- **Total request**: 100,000 tokens max (safety limit)

### Optimization:
- Chunk by paragraphs (preserves context better than sentences)
- Intermediate summaries use shorter length
- Final summary uses target length
- Parallel processing not implemented (sequential for token tracking)

### Estimated Processing Time:
- Short text (< 3000 tokens): 5-10 seconds
- Medium text (3000-10000 tokens): 15-30 seconds
- Long text (10000+ tokens): 30-60 seconds

## API Key Configuration

### Setup:

1. Create `.env` file:
```bash
# Choose one or both
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...
```

2. Restart server:
```bash
uvicorn app.main:app --reload
```

### Cost Tracking:

Monitor token usage in responses:
```json
{
  "token_usage": {
    "total": 250,
    "prompt": 180,
    "completion": 70
  }
}
```

## Database Migration

### Apply Migration:

```bash
# Connect to PostgreSQL
psql -U kindle_user -d kindle_ocr

# Run migration
\i migrations/003_add_summary_format_language.sql
```

### Verify:
```sql
\d summaries

-- Should show:
-- format   | character varying(50) |
-- language | character varying(10) |
```

## Integration with Existing System

### OCR → Summary Flow:

1. Upload image → OCR processing → `job_id` created
2. OCR results stored in `ocr_results` table
3. Create summary from OCR job:
   ```json
   POST /api/v1/summary/create
   {
     "job_id": "uuid-from-step-1",
     "length": "medium",
     "tone": "professional"
   }
   ```
4. Summary stored in `summaries` table
5. Retrieve summary anytime via `summary_id` or `job_id`

### RAG Integration (Future):

Summaries can be indexed in vector database for RAG:
- Level 1 summaries: Quick search results
- Level 2 summaries: Context for follow-up questions
- Level 3 summaries: Detailed reference material

## Troubleshooting

### Issue: "Module 'summary' has no attribute 'router'"

**Solution**: Restart server after adding new endpoints
```bash
# Stop server (Ctrl+C)
# Restart
uvicorn app.main:app --reload
```

### Issue: Mock responses in production

**Solution**: Check API key configuration
```bash
# Verify .env file
cat .env | grep API_KEY

# Check server logs
# Should see: "Initialized Anthropic client with model: claude-3-sonnet-20240229"
# Not: "ANTHROPIC_API_KEY not configured. LLM will use mock responses."
```

### Issue: Database column errors

**Solution**: Run migration
```bash
psql -U kindle_user -d kindle_ocr -f migrations/003_add_summary_format_language.sql
```

## Next Steps (Phase 4+)

Potential enhancements:
1. **Streaming**: Stream summary generation in real-time
2. **Custom prompts**: Allow user-defined summary prompts
3. **Comparison**: Compare multiple summaries side-by-side
4. **Export**: Export summaries to PDF, Word, etc.
5. **Batch processing**: Summarize multiple jobs at once
6. **Quality scoring**: Rate summary quality automatically
7. **A/B testing**: Compare different LLM providers

## API Documentation

Once server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All endpoints are documented with:
- Request/response schemas
- Example payloads
- Error codes
- Try-it-out functionality

## Conclusion

Phase 3 provides a complete, production-ready text summarization system with:
- Multiple summarization strategies
- Flexible customization options
- Multi-level hierarchical summaries
- Japanese language support
- Long document handling
- Comprehensive API
- Full test coverage
- Database integration

The system is ready for integration with OCR results and can be extended for RAG-based question answering in future phases.
