# Phase 1-3 Implementation: OCR Endpoint

## Overview

This implementation adds the OCR upload endpoint to the Kindle OCR MVP system, allowing users to upload images and extract text using Tesseract OCR with Japanese/English support.

## Files Created

### 1. **app/schemas/ocr.py**
Pydantic schemas for request/response validation:
- `OCRUploadResponse`: Response schema for OCR upload containing job_id, book_title, page_num, text, and confidence
- `JobResponse`: Response schema for job status queries

### 2. **app/schemas/__init__.py**
Package initialization for schemas module

### 3. **app/api/v1/endpoints/ocr.py**
FastAPI router with OCR endpoints:
- `POST /api/v1/ocr/upload`: Upload image and extract text
- `GET /api/v1/ocr/jobs/{job_id}`: Get job status

### 4. **app/api/v1/endpoints/__init__.py**
Updated to export the OCR router

### 5. **app/main.py** (Updated)
Registered the OCR router with FastAPI application

## Features Implemented

### OCR Upload Endpoint
- **File Upload**: Accepts multipart/form-data with image files
- **Validation**:
  - File type validation (.png, .jpg, .jpeg)
  - File size limit (10MB max)
  - Filename validation
- **OCR Processing**:
  - Uses pytesseract with Japanese + English support
  - LSTM OCR engine (--oem 3)
  - Single block mode (--psm 6)
  - Returns confidence score (0.0-1.0)
- **Database Storage**:
  - Creates Job record with UUID
  - Saves OCRResult with extracted text
  - Stores original image as BYTEA in PostgreSQL
- **Response**: Returns job_id, book_title, page_num, extracted text, and confidence score

### Job Status Endpoint
- Query job status by UUID
- Returns job information including status, progress, and timestamps
- Proper 404 handling for non-existent jobs

## API Endpoints

### POST `/api/v1/ocr/upload`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/upload" \
  -F "file=@image.png" \
  -F "book_title=My Book" \
  -F "page_num=1"
```

**Response (201 Created):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "book_title": "My Book",
  "page_num": 1,
  "text": "Extracted text content...",
  "confidence": 0.95
}
```

### GET `/api/v1/ocr/jobs/{job_id}`

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/ocr/jobs/{job_id}"
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "type": "ocr",
  "status": "completed",
  "progress": 100,
  "created_at": "2025-10-28T10:30:00"
}
```

## Database Schema Integration

### Job Model (Existing)
```python
id: str (UUID)
user_id: int (default=1 for MVP)
type: str ("ocr")
status: str ("pending" | "processing" | "completed" | "failed")
progress: int (0-100)
created_at: datetime
```

### OCRResult Model (Existing)
```python
id: int (auto-increment)
job_id: str (FK to jobs.id)
book_title: str
page_num: int
text: str (extracted text)
confidence: float (0.0-1.0)
image_blob: bytes (original image)
created_at: datetime
```

## Error Handling

The endpoint handles various error scenarios:

1. **400 Bad Request**:
   - Missing filename
   - Invalid file extension
   - Non-image file types

2. **413 Request Entity Too Large**:
   - File size exceeds 10MB limit

3. **500 Internal Server Error**:
   - OCR processing failures
   - Database errors
   - Unexpected exceptions

All errors include descriptive messages and proper HTTP status codes.

## Testing

### Test Script
A test script is provided at `/test_ocr_endpoint.py`:

```bash
# Run the test (requires running server)
python3 test_ocr_endpoint.py
```

### Interactive API Documentation
Access Swagger UI at: http://localhost:8000/docs

### Manual Testing with cURL
```bash
# Create a test image
# Then upload it
curl -X POST "http://localhost:8000/api/v1/ocr/upload" \
  -F "file=@test.png" \
  -F "book_title=Test Book" \
  -F "page_num=1"
```

## Dependencies

All required packages are already in `requirements.txt`:
- `pytesseract==0.3.10`
- `Pillow==10.1.0`
- `python-multipart==0.0.6`

### System Requirements
Tesseract OCR must be installed:
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

## MVP Simplifications

1. **Authentication**: Uses hardcoded `user_id=1` (auth will be added later)
2. **Synchronous Processing**: OCR runs in the request handler (async queue to be added later)
3. **Image Storage**: Stores in PostgreSQL BYTEA (consider external storage for production)
4. **No Rate Limiting**: Add in production
5. **No Batch Processing**: One image at a time

## Next Steps (Phase 1-4)

1. Add auto-capture endpoints for Kindle screenshots
2. Implement batch processing
3. Add job queue for async OCR processing
4. Add authentication and user management
5. Implement file size optimization
6. Add external image storage (S3/MinIO)

## Configuration

The endpoint uses existing configuration from:
- `app/core/database.py`: Database connection and session management
- `app/core/config.py`: Application settings (if exists)

## Performance Considerations

- **Image Size**: 10MB limit prevents memory issues
- **Database**: Images stored as BYTEA (consider limits for production)
- **OCR Speed**: ~1-3 seconds per image (depends on image size and complexity)
- **Connection Pool**: Uses existing SQLAlchemy pool (10 connections + 20 overflow)

## Security Notes

1. File type validation prevents malicious uploads
2. File size limits prevent DoS attacks
3. Input sanitization on book_title and page_num
4. Proper error handling prevents information leakage
5. Database transactions ensure data integrity

## Monitoring & Logging

All endpoints include comprehensive logging:
- Upload start/completion
- OCR processing status
- Database operations
- Error details with stack traces

Example logs:
```
INFO: 📤 OCRアップロード開始: test.png, 書籍=Test Book, ページ=1
INFO: ✅ Job作成完了: job_id=550e8400-e29b-41d4-a716-446655440000
INFO: 🔍 OCR処理開始...
INFO: ✅ OCR処理完了: テキスト長=245, 信頼度=0.95
INFO: ✅ OCR結果保存完了: ocr_result_id=1
```

## Documentation

- API Documentation: `/app/api/v1/endpoints/README.md`
- Interactive Docs: http://localhost:8000/docs (Swagger UI)
- Alternative Docs: http://localhost:8000/redoc (ReDoc)

## Conclusion

Phase 1-3 implementation is complete with:
- ✅ OCR upload endpoint with file validation
- ✅ Tesseract integration with Japanese/English support
- ✅ Database integration (Job + OCRResult models)
- ✅ Image storage in PostgreSQL
- ✅ Confidence scoring
- ✅ Job status tracking
- ✅ Comprehensive error handling
- ✅ API documentation
- ✅ Test script

The system is ready for Phase 1-4: Auto-capture functionality.
