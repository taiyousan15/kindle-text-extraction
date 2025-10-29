# Auto-Capture System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT APPLICATION                          │
│  (Web Browser, Mobile App, CLI, Postman, curl, etc.)               │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ HTTP/HTTPS
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                           │
│                         (app/main.py)                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     API Endpoints                            │  │
│  │  ┌─────────────────────┐  ┌─────────────────────────────┐   │  │
│  │  │  OCR Endpoint       │  │  Capture Endpoint           │   │  │
│  │  │  /api/v1/ocr/       │  │  /api/v1/capture/           │   │  │
│  │  │  - upload           │  │  - start (POST)             │   │  │
│  │  │  - jobs/{id}        │  │  - status/{id} (GET)        │   │  │
│  │  └─────────────────────┘  │  - jobs (GET)               │   │  │
│  │                            └─────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ Depends(get_db)
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                       SERVICES LAYER                                 │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  CaptureService (app/services/capture_service.py)          │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  start_capture_task()                                │  │    │
│  │  │  - Launch background thread                          │  │    │
│  │  │  - Return immediately                                │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  _run_capture_task() [Background Thread]            │  │    │
│  │  │  1. Update Job (status=processing)                  │  │    │
│  │  │  2. Initialize SeleniumKindleCapture                │  │    │
│  │  │  3. Login to Amazon                                 │  │    │
│  │  │  4. Navigate to book                                │  │    │
│  │  │  5. Capture pages (loop)                            │  │    │
│  │  │  6. OCR processing (pytesseract)                    │  │    │
│  │  │  7. Save OCRResults to DB                           │  │    │
│  │  │  8. Update Job (status=completed, progress=100)     │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  SeleniumKindleCapture (app/services/capture/)             │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  _init_driver()                                      │  │    │
│  │  │  - Initialize Chrome WebDriver                       │  │    │
│  │  │  - Setup headless mode                               │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  login_amazon()                                      │  │    │
│  │  │  - Navigate to Amazon login page                    │  │    │
│  │  │  - Input email and password                          │  │    │
│  │  │  - Submit and verify login                           │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  capture_all_pages()                                 │  │    │
│  │  │  - Open book in Kindle Cloud Reader                 │  │    │
│  │  │  - Loop: capture screenshot + turn page              │  │    │
│  │  │  - Progress callback                                 │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         │ SQLAlchemy ORM
                         │
┌────────────────────────▼────────────────────────────────────────────┐
│                       DATABASE LAYER                                 │
│                    (PostgreSQL Database)                             │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  jobs                                                      │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  id (UUID, PK)                                       │  │    │
│  │  │  user_id (INT, FK)                                   │  │    │
│  │  │  type (VARCHAR) - "ocr" or "auto_capture"           │  │    │
│  │  │  status (VARCHAR) - pending/processing/completed    │  │    │
│  │  │  progress (INT) - 0-100                              │  │    │
│  │  │  error_message (TEXT)                                │  │    │
│  │  │  created_at (TIMESTAMP)                              │  │    │
│  │  │  completed_at (TIMESTAMP)                            │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ocr_results                                               │    │
│  │  ┌──────────────────────────────────────────────────────┐  │    │
│  │  │  id (SERIAL, PK)                                     │  │    │
│  │  │  job_id (UUID, FK → jobs.id)                        │  │    │
│  │  │  book_title (VARCHAR)                                │  │    │
│  │  │  page_num (INT)                                      │  │    │
│  │  │  text (TEXT)                                         │  │    │
│  │  │  confidence (FLOAT)                                  │  │    │
│  │  │  image_blob (BYTEA) - PNG image data                │  │    │
│  │  │  created_at (TIMESTAMP)                              │  │    │
│  │  └──────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow - Auto-Capture

### 1. Start Capture Request

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     │ POST /api/v1/capture/start
     │ {
     │   "amazon_email": "user@example.com",
     │   "amazon_password": "password",
     │   "book_url": "https://read.amazon.com/...",
     │   "book_title": "My Book",
     │   "max_pages": 50
     │ }
     ▼
┌─────────────────┐
│ capture.py      │ 1. Create Job (status=pending)
│ start_auto_     │ 2. Save to DB
│ capture()       │ 3. Start background thread
└────┬────────────┘ 4. Return 202 Accepted with job_id
     │
     │ Response (immediate):
     │ {
     │   "job_id": "550e8400-...",
     │   "status": "pending",
     │   "message": "Job started..."
     │ }
     ▼
┌─────────┐
│ Client  │
└─────────┘
```

### 2. Background Task Execution

```
┌──────────────────────────────────────────────────────────────────┐
│                   Background Thread                              │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. Update Job (status=processing, progress=0)             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 2. Initialize Selenium Chrome Driver                      │ │
│  │    - Headless mode                                        │ │
│  │    - Window size: 1920x1080                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 3. Login to Amazon                                        │ │
│  │    - Navigate to https://amazon.co.jp/ap/signin          │ │
│  │    - Input email                                          │ │
│  │    - Input password                                       │ │
│  │    - Submit and verify                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 4. Navigate to Book                                       │ │
│  │    - Open book_url in Kindle Cloud Reader                │ │
│  │    - Wait for page load                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 5. Capture Loop (for each page)                          │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ a. Screenshot: driver.save_screenshot()            │ │ │
│  │    │    → captures/{job_id}/page_0001.png               │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  │                           ▼                                │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ b. Update Progress: (page / total) * 100           │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  │                           ▼                                │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ c. Turn Page: send Keys.ARROW_RIGHT                │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  │                           ▼                                │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ d. Wait 2 seconds                                  │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 6. OCR Processing (for each captured image)              │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ a. Load image: Image.open(page_0001.png)           │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  │                           ▼                                │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ b. OCR: pytesseract.image_to_string()              │ │ │
│  │    │    - lang='jpn+eng'                                │ │ │
│  │    │    - Extract text + confidence                     │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  │                           ▼                                │ │
│  │    ┌────────────────────────────────────────────────────┐ │ │
│  │    │ c. Save OCRResult to DB                            │ │ │
│  │    │    - job_id, book_title, page_num                  │ │ │
│  │    │    - text, confidence, image_blob                  │ │ │
│  │    └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 7. Finalize                                               │ │
│  │    - Update Job (status=completed, progress=100)         │ │
│  │    - Set completed_at timestamp                          │ │
│  │    - Close Chrome Driver                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 3. Status Check Request

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     │ GET /api/v1/capture/status/{job_id}
     │
     ▼
┌─────────────────┐
│ capture.py      │ 1. Query Job by job_id
│ get_capture_    │ 2. Query OCRResults by job_id
│ status()        │ 3. Build response
└────┬────────────┘
     │
     │ Response:
     │ {
     │   "job_id": "550e8400-...",
     │   "status": "processing",
     │   "progress": 50,
     │   "pages_captured": 25,
     │   "ocr_results": [
     │     {"page_num": 1, "text": "...", "confidence": 0.95},
     │     ...
     │   ],
     │   "created_at": "2025-10-28T10:30:00",
     │   "completed_at": null
     │ }
     ▼
┌─────────┐
│ Client  │
└─────────┘
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        Technology Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Web Framework:         FastAPI 0.109+                          │
│  Validation:            Pydantic 2.0+                           │
│  Database ORM:          SQLAlchemy 2.0+                         │
│  Database:              PostgreSQL 16+                          │
│  Browser Automation:    Selenium 4.0+                           │
│  Chrome Driver:         webdriver-manager                       │
│  OCR Engine:            pytesseract + Tesseract 5.0+            │
│  Image Processing:      Pillow (PIL)                            │
│  Async Processing:      threading (Python stdlib)               │
│  HTTP Client:           requests (for testing)                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

```
┌─────────────────────────────────────────────────────────────────┐
│                     Security Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Password Management:                                        │
│     ✓ Passwords NOT logged                                     │
│     ✓ Passwords NOT stored in database                         │
│     ✓ Passwords only in memory during processing               │
│     ✓ Memory cleared after use                                 │
│                                                                 │
│  2. Database Security:                                          │
│     ✓ Connection pooling with SSL                              │
│     ✓ Prepared statements (SQLAlchemy)                         │
│     ✓ Input validation (Pydantic)                              │
│                                                                 │
│  3. API Security (Future):                                      │
│     ☐ JWT authentication                                       │
│     ☐ Rate limiting                                            │
│     ☐ HTTPS only                                               │
│     ☐ CORS configuration                                       │
│                                                                 │
│  4. File Storage:                                               │
│     ✓ Local filesystem (./captures/)                           │
│     ☐ S3/GCS integration (future)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture (Future)

```
┌──────────────────────────────────────────────────────────────────┐
│                      Production Deployment                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐                                             │
│  │  Load Balancer │                                             │
│  │  (ALB/Nginx)   │                                             │
│  └────────┬───────┘                                             │
│           │                                                      │
│           ├────────────────┬────────────────┐                   │
│           ▼                ▼                ▼                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │  FastAPI     │ │  FastAPI     │ │  FastAPI     │            │
│  │  Instance 1  │ │  Instance 2  │ │  Instance 3  │            │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘            │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
│                          │                                      │
│                          ▼                                      │
│                 ┌────────────────┐                              │
│                 │  Task Queue    │                              │
│                 │  (Celery/RQ)   │                              │
│                 └────────┬───────┘                              │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │  Worker  │    │  Worker  │    │  Worker  │                 │
│  │  (Celery)│    │  (Celery)│    │  (Celery)│                 │
│  └──────┬───┘    └──────┬───┘    └──────┬───┘                 │
│         │               │               │                      │
│         └───────────────┴───────────────┘                      │
│                         │                                      │
│                         ▼                                      │
│                ┌─────────────────┐                             │
│                │  PostgreSQL     │                             │
│                │  (Primary)      │                             │
│                └────────┬────────┘                             │
│                         │                                      │
│                         ▼                                      │
│                ┌─────────────────┐                             │
│                │  PostgreSQL     │                             │
│                │  (Replica)      │                             │
│                └─────────────────┘                             │
│                                                                │
│  Storage:                                                      │
│    ┌────────────────┐                                          │
│    │  S3 / GCS      │  ← Screenshot storage                   │
│    └────────────────┘                                          │
│                                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Monitoring & Observability (Future)

```
┌──────────────────────────────────────────────────────────────────┐
│                    Monitoring Architecture                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Metrics:              Prometheus + Grafana                      │
│  Logging:              CloudWatch / ELK Stack                    │
│  Tracing:              OpenTelemetry / Jaeger                    │
│  Alerting:             PagerDuty / Slack                         │
│  Health Checks:        /health endpoint                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
Kindle文字起こしツール/
├── app/
│   ├── main.py                          # FastAPI app entry point
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── ocr.py               # OCR endpoints
│   │           └── capture.py           # Auto-capture endpoints ★
│   ├── schemas/
│   │   ├── ocr.py                       # OCR schemas
│   │   └── capture.py                   # Capture schemas ★
│   ├── services/
│   │   ├── capture_service.py           # Background task service ★
│   │   └── capture/
│   │       ├── selenium_capture.py      # Selenium automation
│   │       └── capture_factory.py       # Factory pattern
│   ├── models/
│   │   ├── job.py                       # Job model
│   │   └── ocr_result.py                # OCRResult model
│   └── core/
│       ├── database.py                  # DB connection
│       └── config.py                    # Configuration
├── captures/                            # Screenshot storage
│   └── {job_id}/
│       ├── page_0001.png
│       ├── page_0002.png
│       └── ...
├── test_capture_endpoint.py             # Test script ★
├── QUICKSTART_CAPTURE.md                # Quick start guide ★
├── PHASE_1-4_IMPLEMENTATION_SUMMARY.md  # Implementation summary ★
└── ARCHITECTURE_DIAGRAM.md              # This file ★

★ = New files for Phase 1-4
```

---

This architecture enables scalable, maintainable, and secure auto-capture functionality for Kindle books.
