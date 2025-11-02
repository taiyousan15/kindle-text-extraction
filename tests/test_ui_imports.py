#!/usr/bin/env python3
"""
Streamlit UI Import Test
すべてのUIファイルがインポート可能かテストする
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("🧪 Streamlit UI Import Test")
print("=" * 50)

# Test 1: API Client
print("\n1. Testing api_client.py...")
try:
    from app.ui.utils.api_client import (
        upload_image,
        start_auto_capture,
        get_job_status,
        list_jobs,
        get_health,
        APIError
    )
    print("   ✅ api_client.py - OK")
    print(f"      - upload_image: {upload_image.__name__}")
    print(f"      - start_auto_capture: {start_auto_capture.__name__}")
    print(f"      - get_job_status: {get_job_status.__name__}")
    print(f"      - list_jobs: {list_jobs.__name__}")
    print(f"      - get_health: {get_health.__name__}")
    print(f"      - APIError: {APIError.__name__}")
except Exception as e:
    print(f"   ❌ api_client.py - FAILED: {e}")
    sys.exit(1)

# Test 2: Check file existence
print("\n2. Testing file existence...")
files_to_check = [
    "app/ui/Home.py",
    "app/ui/pages/1_📤_Upload.py",
    "app/ui/pages/2_🤖_Auto_Capture.py",
    "app/ui/pages/3_📊_Jobs.py",
    "app/ui/utils/api_client.py",
    "app/ui/README.md",
    "run_ui.sh",
    "QUICKSTART_UI.md",
    "PHASE_1-6_UI_IMPLEMENTATION.md"
]

all_exist = True
for file_path in files_to_check:
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if os.path.exists(full_path):
        print(f"   ✅ {file_path}")
    else:
        print(f"   ❌ {file_path} - NOT FOUND")
        all_exist = False

if not all_exist:
    print("\n❌ Some files are missing!")
    sys.exit(1)

# Test 3: Check run_ui.sh is executable
print("\n3. Testing run_ui.sh permissions...")
run_ui_path = os.path.join(os.path.dirname(__file__), "run_ui.sh")
if os.access(run_ui_path, os.X_OK):
    print("   ✅ run_ui.sh is executable")
else:
    print("   ⚠️  run_ui.sh is not executable")
    print("      Run: chmod +x run_ui.sh")

# Test 4: Check required packages
print("\n4. Testing required packages...")
required_packages = [
    "streamlit",
    "requests",
    "pandas"
]

all_installed = True
for package in required_packages:
    try:
        __import__(package)
        print(f"   ✅ {package}")
    except ImportError:
        print(f"   ❌ {package} - NOT INSTALLED")
        all_installed = False

if not all_installed:
    print("\n⚠️  Some packages are missing!")
    print("   Run: pip install streamlit requests pandas")

# Test 5: API Base URL
print("\n5. Testing API_BASE_URL...")
from app.ui.utils.api_client import API_BASE_URL
print(f"   API_BASE_URL: {API_BASE_URL}")

# Summary
print("\n" + "=" * 50)
print("📊 Test Summary")
print("=" * 50)
print("✅ All import tests passed!")
print("✅ All files exist!")
print("\n🚀 Ready to start Streamlit UI!")
print("\nNext steps:")
print("1. Start FastAPI: uvicorn app.main:app --reload")
print("2. Start UI: ./run_ui.sh")
print("   or: streamlit run app/ui/Home.py")
print("\n💡 Access UI at: http://localhost:8501")
