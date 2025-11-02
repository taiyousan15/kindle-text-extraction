#!/usr/bin/env python3
"""
Final System Check - Complete End-to-End Verification
最終システムチェック - 完全なエンドツーエンド検証
"""
import sys
import os
from pathlib import Path
import subprocess

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def run_test_script(script_name, description):
    """Run a test script and return success status"""
    print(f"\n🔍 {description}...")
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error output:\n{result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def check_docker_services():
    """Check if Docker services are running"""
    print("\n🔍 Checking Docker services...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=kindle", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                print("✅ Docker services running:")
                for line in lines:
                    print(f"   {line}")
                return True
            else:
                print("⚠️  No Kindle Docker containers found")
                return False
        else:
            print("❌ Failed to check Docker services")
            return False
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False

def check_env_config():
    """Check critical environment variables"""
    print("\n🔍 Checking environment configuration...")

    from dotenv import load_dotenv
    load_dotenv()

    critical_vars = {
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "REDIS_URL": os.getenv("REDIS_URL"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL"),
        "LLM_PROVIDER": os.getenv("LLM_PROVIDER"),
    }

    optional_vars = {
        "AMAZON_EMAIL": os.getenv("AMAZON_EMAIL"),
        "AMAZON_PASSWORD": os.getenv("AMAZON_PASSWORD"),
    }

    all_good = True

    print("\nCritical variables:")
    for var, value in critical_vars.items():
        if value:
            # Mask sensitive values
            display_value = value[:20] + "..." if len(value) > 20 else value
            if "KEY" in var or "PASSWORD" in var:
                display_value = "***" + value[-4:] if len(value) > 4 else "***"
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NOT SET")
            all_good = False

    print("\nOptional variables:")
    for var, value in optional_vars.items():
        if value:
            print(f"   ✅ {var}: ***")
        else:
            print(f"   ⚠️  {var}: NOT SET (login automation disabled)")

    return all_good

def check_file_permissions():
    """Check critical file and directory permissions"""
    print("\n🔍 Checking file permissions...")

    critical_paths = [
        Path("app"),
        Path("captures"),
        Path("logs"),
        Path("uploads"),
        Path(".env"),
    ]

    all_good = True
    for path in critical_paths:
        if path.exists():
            if path.is_dir():
                if os.access(path, os.R_OK | os.W_OK | os.X_OK):
                    print(f"   ✅ {path}/ (rwx)")
                else:
                    print(f"   ❌ {path}/ (insufficient permissions)")
                    all_good = False
            else:
                if os.access(path, os.R_OK):
                    print(f"   ✅ {path} (readable)")
                else:
                    print(f"   ❌ {path} (not readable)")
                    all_good = False
        else:
            if path.name in ['logs', 'uploads']:  # These can be created on demand
                print(f"   ⚠️  {path} (will be created on first use)")
            else:
                print(f"   ❌ {path} (missing)")
                all_good = False

    return all_good

def generate_health_report():
    """Generate system health report"""
    print_section("📊 SYSTEM HEALTH REPORT")

    health_checks = {
        "Environment Configuration": check_env_config(),
        "File Permissions": check_file_permissions(),
        "Docker Services": check_docker_services(),
        "Service Tests": run_test_script("test_services.py", "Core Services"),
        "Functionality Tests": run_test_script("test_core_functionality.py", "Core Functionality"),
    }

    print_section("📋 FINAL RESULTS")

    passed = sum(1 for v in health_checks.values() if v)
    total = len(health_checks)

    for check_name, result in health_checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")

    print(f"\n{'='*80}")
    print(f"Total: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    print(f"{'='*80}\n")

    if passed == total:
        print("🎉 SYSTEM STATUS: FULLY OPERATIONAL")
        print("\nNext steps:")
        print("1. Start the application:")
        print("   docker-compose up -d")
        print("\n2. Access the UI:")
        print("   http://localhost:8501")
        print("\n3. Check API docs:")
        print("   http://localhost:8000/docs")
        return 0
    else:
        print("⚠️  SYSTEM STATUS: NEEDS ATTENTION")
        print(f"\n{total - passed} check(s) failed. Please review the errors above.")
        print("\nRecommended actions:")
        print("1. Review DEBUGGING_REPORT.md for detailed fixes")
        print("2. Ensure Docker services are running: colima start && docker-compose up -d postgres redis")
        print("3. Verify .env configuration")
        return 1

def main():
    """Main execution"""
    print("=" * 80)
    print("🚀 Kindle OCR System - Final System Check")
    print("   Kindle OCRシステム - 最終システムチェック")
    print("=" * 80)
    print(f"\nPython: {sys.version.split()[0]}")
    print(f"Working Directory: {Path.cwd()}")

    return generate_health_report()

if __name__ == "__main__":
    sys.exit(main())
