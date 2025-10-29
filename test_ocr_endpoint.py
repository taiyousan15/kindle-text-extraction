#!/usr/bin/env python3
"""
OCR Endpoint Test Script

Quick test to verify the OCR endpoint is working correctly.
Requires:
  - Running database
  - Tesseract installed
  - App running on localhost:8000
"""
import requests
import io
from PIL import Image, ImageDraw, ImageFont

def create_test_image() -> bytes:
    """Create a simple test image with Japanese text"""
    # Create a white image
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)

    # Add some text
    text = "テストテキスト\nTest Text\nPage 1"
    draw.text((50, 50), text, fill='black')

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    return img_bytes.getvalue()

def test_ocr_upload():
    """Test the OCR upload endpoint"""
    print("🧪 Testing OCR Upload Endpoint...")

    url = "http://localhost:8000/api/v1/ocr/upload"

    # Create test image
    image_data = create_test_image()

    # Prepare request
    files = {
        'file': ('test.png', image_data, 'image/png')
    }
    data = {
        'book_title': 'Test Book',
        'page_num': 1
    }

    # Send request
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()

        result = response.json()
        print("✅ OCR Upload Success!")
        print(f"📊 Result:")
        print(f"  - Job ID: {result['job_id']}")
        print(f"  - Book Title: {result['book_title']}")
        print(f"  - Page Number: {result['page_num']}")
        print(f"  - Extracted Text: {result['text'][:100]}...")
        print(f"  - Confidence: {result['confidence']:.2f}")

        return result['job_id']

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def test_job_status(job_id: str):
    """Test the job status endpoint"""
    print(f"\n🧪 Testing Job Status Endpoint...")

    url = f"http://localhost:8000/api/v1/ocr/jobs/{job_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print("✅ Job Status Success!")
        print(f"📊 Job Info:")
        print(f"  - Job ID: {result['id']}")
        print(f"  - Type: {result['type']}")
        print(f"  - Status: {result['status']}")
        print(f"  - Progress: {result['progress']}%")
        print(f"  - Created At: {result['created_at']}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")

def main():
    """Run all tests"""
    print("=" * 50)
    print("OCR Endpoint Test Suite")
    print("=" * 50)

    # Test upload
    job_id = test_ocr_upload()

    # Test job status if upload succeeded
    if job_id:
        test_job_status(job_id)

    print("\n" + "=" * 50)
    print("Tests completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()
