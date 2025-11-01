#!/usr/bin/env python3
"""
Test script to verify all system services and dependencies
"""
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_postgres():
    """Test PostgreSQL connection"""
    print("\n🔍 Testing PostgreSQL connection...")
    try:
        import psycopg2
        from dotenv import load_dotenv

        load_dotenv()

        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'kindle_ocr'),
            user=os.getenv('DB_USER', 'kindle_user'),
            password=os.getenv('DB_PASSWORD', 'kindle_password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )

        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        print(f"✅ PostgreSQL connected: {version[0][:50]}...")

        # Check for pgvector extension
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        has_vector = cursor.fetchone()
        if has_vector:
            print("✅ pgvector extension is installed")
        else:
            print("⚠️  pgvector extension is NOT installed")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def test_redis():
    """Test Redis connection"""
    print("\n🔍 Testing Redis connection...")
    try:
        import redis
        from dotenv import load_dotenv

        load_dotenv()

        r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        print(f"✅ Redis connected: {r.info()['redis_version']}")
        return True

    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_tesseract():
    """Test Tesseract OCR"""
    print("\n🔍 Testing Tesseract OCR...")
    try:
        import pytesseract
        from PIL import Image
        import numpy as np

        # Get version
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract version: {version}")

        # Check languages
        langs = pytesseract.get_languages()
        print(f"✅ Available languages: {', '.join(langs)}")

        if 'jpn' in langs and 'eng' in langs:
            print("✅ Japanese and English support confirmed")
            return True
        else:
            print("⚠️  Missing language support (need jpn+eng)")
            return False

    except Exception as e:
        print(f"❌ Tesseract test failed: {e}")
        return False

def test_selenium():
    """Test Selenium WebDriver"""
    print("\n🔍 Testing Selenium WebDriver...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get('https://www.google.com')
        title = driver.title
        driver.quit()

        print(f"✅ Selenium WebDriver working (tested with Google)")
        return True

    except Exception as e:
        print(f"❌ Selenium test failed: {e}")
        return False

def test_anthropic_api():
    """Test Anthropic Claude API"""
    print("\n🔍 Testing Anthropic Claude API...")
    try:
        from anthropic import Anthropic
        from dotenv import load_dotenv

        load_dotenv()

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == '':
            print("⚠️  ANTHROPIC_API_KEY not set in .env")
            return False

        client = Anthropic(api_key=api_key)

        # Simple test message - using available model for this API key
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'API test successful' in Japanese"}
            ]
        )

        response_text = message.content[0].text
        print(f"✅ Claude API working: {response_text[:50]}...")
        return True

    except Exception as e:
        print(f"❌ Anthropic API test failed: {e}")
        return False

def test_file_structure():
    """Test required file structure"""
    print("\n🔍 Testing file structure...")

    required_dirs = [
        'app',
        'app/api',
        'app/core',
        'app/models',
        'app/schemas',
        'app/services',
        'app/ui',
        'captures',
    ]

    all_exist = True
    for dir_path in required_dirs:
        full_path = Path(__file__).parent / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ Missing: {dir_path}")
            all_exist = False

    return all_exist

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Kindle OCR System - Service Verification")
    print("=" * 60)

    results = {
        "File Structure": test_file_structure(),
        "PostgreSQL": test_postgres(),
        "Redis": test_redis(),
        "Tesseract OCR": test_tesseract(),
        "Selenium WebDriver": test_selenium(),
        "Anthropic API": test_anthropic_api(),
    }

    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All services are operational!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} service(s) need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
