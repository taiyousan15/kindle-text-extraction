# OCR Endpoint Documentation

## Overview

The OCR endpoint provides image upload and text extraction capabilities for the Kindle OCR system.

## Endpoints

### POST `/api/v1/ocr/upload`

Upload an image file and extract text using OCR.

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `file` (required): Image file (.png, .jpg, .jpeg)
  - `book_title` (optional, default: "Untitled"): Title of the book
  - `page_num` (optional, default: 1): Page number

**Response:** `201 Created`
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "book_title": "サンプル書籍",
  "page_num": 1,
  "text": "抽出されたテキストの内容...",
  "confidence": 0.95
}
```

**Errors:**
- `400 Bad Request`: Invalid file format or missing filename
- `413 Request Entity Too Large`: File size exceeds 10MB
- `500 Internal Server Error`: OCR processing or database error

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/upload" \
  -F "file=@/path/to/image.png" \
  -F "book_title=My Book" \
  -F "page_num=1"
```

**Example (Python):**
```python
import requests

url = "http://localhost:8000/api/v1/ocr/upload"
files = {"file": open("image.png", "rb")}
data = {
    "book_title": "My Book",
    "page_num": 1
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### GET `/api/v1/ocr/jobs/{job_id}`

Get the status of a specific OCR job.

**Request:**
- Path Parameters:
  - `job_id` (required): UUID of the job

**Response:** `200 OK`
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

**Errors:**
- `404 Not Found`: Job not found

**Example (cURL):**
```bash
curl -X GET "http://localhost:8000/api/v1/ocr/jobs/550e8400-e29b-41d4-a716-446655440000"
```

## Features

- **Multi-language OCR**: Supports Japanese and English text extraction (jpn+eng)
- **Image Storage**: Stores uploaded images as BYTEA in PostgreSQL
- **Confidence Scoring**: Returns OCR confidence score (0.0-1.0)
- **Job Tracking**: Creates Job records for tracking processing status
- **Error Handling**: Comprehensive error handling with proper HTTP status codes

## File Format Support

- PNG (.png)
- JPEG (.jpg, .jpeg)
- Maximum file size: 10MB

## Database Models

### Job
- `id`: UUID (primary key)
- `user_id`: Integer (defaults to 1 for MVP)
- `type`: "ocr"
- `status`: "pending" | "processing" | "completed" | "failed"
- `progress`: Integer (0-100)
- `created_at`: Timestamp

### OCRResult
- `id`: Auto-increment integer
- `job_id`: Foreign key to Job
- `book_title`: String
- `page_num`: Integer
- `text`: Extracted text
- `confidence`: Float (0.0-1.0)
- `image_blob`: BYTEA (original image)
- `created_at`: Timestamp

## Requirements

- Python 3.11+
- Tesseract OCR installed on system:
  - macOS: `brew install tesseract tesseract-lang`
  - Ubuntu: `apt-get install tesseract-ocr tesseract-ocr-jpn`
- Python packages (from requirements.txt):
  - pytesseract
  - Pillow
  - FastAPI
  - SQLAlchemy
  - psycopg2-binary

## Testing

Run the FastAPI development server:
```bash
uvicorn app.main:app --reload
```

Access the interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Implementation Notes

- **MVP Simplification**: Uses default `user_id=1` (no authentication yet)
- **Synchronous Processing**: OCR is processed synchronously in the request
- **Image Storage**: Full image stored in database for Phase 1; consider external storage for production
- **OCR Engine**: Uses Tesseract LSTM OCR engine (--oem 3) with single block mode (--psm 6)
