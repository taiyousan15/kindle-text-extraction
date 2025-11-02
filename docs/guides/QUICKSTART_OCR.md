# OCR Endpoint Quick Start Guide

## Prerequisites

1. **Tesseract OCR** must be installed:
   ```bash
   # macOS
   brew install tesseract tesseract-lang

   # Verify installation
   tesseract --version
   ```

2. **PostgreSQL** running with database created:
   ```bash
   psql -U kindle_user -d kindle_ocr
   ```

3. **Python dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```

## Start the Server

```bash
# From project root
uvicorn app.main:app --reload
```

Server will start at: http://localhost:8000

## Test the API

### 1. Check Health
```bash
curl http://localhost:8000/health
```

### 2. View API Documentation
Open in browser: http://localhost:8000/docs

### 3. Upload an Image

**Using cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/ocr/upload" \
  -F "file=@/path/to/your/image.png" \
  -F "book_title=My Kindle Book" \
  -F "page_num=1"
```

**Using Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/ocr/upload",
    files={"file": open("image.png", "rb")},
    data={
        "book_title": "My Kindle Book",
        "page_num": 1
    }
)

print(response.json())
```

**Using the Test Script:**
```bash
python3 test_ocr_endpoint.py
```

### 4. Check Job Status
```bash
# Replace {job_id} with the actual job_id from upload response
curl http://localhost:8000/api/v1/ocr/jobs/{job_id}
```

## Example Response

**Upload Response (201 Created):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "book_title": "My Kindle Book",
  "page_num": 1,
  "text": "This is the extracted text from the image...",
  "confidence": 0.92
}
```

**Job Status Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "type": "ocr",
  "status": "completed",
  "progress": 100,
  "created_at": "2025-10-28T14:30:00"
}
```

## Supported File Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- Max file size: 10MB

## Common Issues

### 1. Tesseract Not Found
```
Error: pytesseract.pytesseract.TesseractNotFoundError
```
**Solution:** Install Tesseract OCR system package

### 2. Database Connection Failed
```
Error: Database connection failed
```
**Solution:** Ensure PostgreSQL is running and DATABASE_URL is correct

### 3. Module Not Found: pytesseract
```
Error: ModuleNotFoundError: No module named 'pytesseract'
```
**Solution:** Run `pip install -r requirements.txt`

### 4. Japanese Text Not Recognized
```
Error: Tesseract couldn't load any languages!
```
**Solution:** Install Japanese language pack:
```bash
# macOS
brew install tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr-jpn
```

## Database Schema

The endpoint creates records in two tables:

**jobs:**
```sql
SELECT * FROM jobs WHERE type = 'ocr';
```

**ocr_results:**
```sql
SELECT
  id, job_id, book_title, page_num,
  length(text) as text_length,
  confidence,
  created_at
FROM ocr_results;
```

## Development Tips

1. **Enable Debug Logging:**
   Edit `app/main.py` and change:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **View SQL Queries:**
   Edit `app/core/database.py` and set:
   ```python
   engine = create_engine(DATABASE_URL, echo=True)
   ```

3. **Test with Sample Images:**
   Create a test directory and add sample Kindle screenshots

4. **Interactive Testing:**
   Use Swagger UI at http://localhost:8000/docs to upload files directly in browser

## Next Steps

- Try uploading multiple pages from the same book
- Check the extracted text quality
- Experiment with different image formats
- Review confidence scores for different image types

## Support

- API Documentation: http://localhost:8000/docs
- Implementation Details: See `PHASE1-3_IMPLEMENTATION.md`
- Endpoint Documentation: See `app/api/v1/endpoints/README.md`
