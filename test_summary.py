#!/usr/bin/env python3
"""
Summary Service and Endpoint Test Script

Comprehensive tests for Phase 3 Summary implementation:
- Single-level summarization
- Multi-level summarization
- Different parameters (length, tone, granularity)
- Long document handling (map-reduce)
- Japanese and English text
- Integration test with database

Requirements:
  - Running database
  - App running on localhost:8000 (for API tests)
  - ANTHROPIC_API_KEY or OPENAI_API_KEY (optional, will use mock if not set)
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test samples
JAPANESE_SHORT_TEXT = """
人工知能（AI）は、近年急速に発展しており、私たちの生活に大きな影響を与えています。
特に機械学習と深層学習の進歩により、画像認識、自然言語処理、音声認識などの分野で
著しい成果が得られています。
"""

JAPANESE_LONG_TEXT = """
人工知能（AI）は、近年急速に発展しており、私たちの生活に大きな影響を与えています。
特に機械学習と深層学習の進歩により、画像認識、自然言語処理、音声認識などの分野で
著しい成果が得られています。

AIの応用範囲は広く、医療診断、自動運転、金融取引、製造業など、様々な産業で活用されています。
医療分野では、AIが画像診断の精度向上に貢献し、早期発見・早期治療につながっています。
自動運転技術では、センサーデータの解析と意思決定にAIが不可欠な役割を果たしています。

しかし、AIの発展に伴い、倫理的な問題やプライバシーの懸念も生じています。
アルゴリズムのバイアス、データの透明性、説明可能性など、解決すべき課題は多くあります。
今後は、技術の進歩と社会的責任のバランスを取ることが重要です。

また、AI技術の発展により、多くの仕事が自動化される可能性があります。
これは経済や雇用に大きな影響を与える可能性があり、教育システムの見直しや
新しいスキルの習得が必要になるでしょう。一方で、AIは人間の能力を補完し、
より創造的な仕事に集中できる機会も提供します。

最後に、AI研究の今後の方向性として、AGI（汎用人工知能）の実現や、
人間とAIの協調的な関係の構築が注目されています。技術的な進歩とともに、
人間中心のAI開発が求められています。
"""

ENGLISH_TEXT = """
Artificial Intelligence (AI) has been rapidly developing in recent years and is having
a significant impact on our lives. In particular, advances in machine learning and deep
learning have led to remarkable achievements in fields such as image recognition, natural
language processing, and speech recognition.

The scope of AI applications is broad, and it is being utilized in various industries
such as medical diagnosis, autonomous driving, financial transactions, and manufacturing.
However, with the development of AI, ethical issues and privacy concerns have also arisen.
It will be important to balance technological progress with social responsibility in the future.
"""

# =============================================================================
# Unit Tests (SummaryService)
# =============================================================================

def test_summary_service_basic():
    """Test basic SummaryService functionality"""
    print("\n" + "="*70)
    print("TEST 1: Basic SummaryService - Single-level Japanese Summary")
    print("="*70)

    from app.services.summary_service import (
        SummaryService,
        SummaryLength,
        SummaryTone,
        SummaryGranularity,
        SummaryFormat
    )

    try:
        # Initialize service
        service = SummaryService(provider="anthropic")
        logger.info("SummaryService initialized")

        # Test summarization
        result = service.summarize(
            text=JAPANESE_SHORT_TEXT,
            length=SummaryLength.MEDIUM,
            tone=SummaryTone.PROFESSIONAL,
            granularity=SummaryGranularity.HIGH_LEVEL,
            format_type=SummaryFormat.PLAIN_TEXT
        )

        # Validate result
        assert "summary" in result
        assert "language" in result
        assert "tokens" in result
        assert result["language"] == "ja"

        print(f"✅ Summary created successfully!")
        print(f"   Language: {result['language']}")
        print(f"   Summary: {result['summary'][:100]}...")
        print(f"   Tokens: {result['tokens']}")
        print(f"   Chunks: {result['chunks']}")
        print(f"   Is Mock: {result['is_mock']}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")
        return False


def test_summary_service_multilevel():
    """Test multi-level summarization"""
    print("\n" + "="*70)
    print("TEST 2: Multi-level Summarization (3 levels)")
    print("="*70)

    from app.services.summary_service import (
        SummaryService,
        SummaryTone,
        SummaryFormat
    )

    try:
        service = SummaryService(provider="anthropic")

        result = service.summarize_multilevel(
            text=JAPANESE_LONG_TEXT,
            tone=SummaryTone.PROFESSIONAL,
            format_type=SummaryFormat.PLAIN_TEXT
        )

        # Validate result
        assert "level_1" in result
        assert "level_2" in result
        assert "level_3" in result
        assert "total_tokens" in result

        print(f"✅ Multi-level summary created successfully!")
        print(f"\n📊 Level 1 (Executive):")
        print(f"   {result['level_1']['summary']}")
        print(f"   Tokens: {result['level_1']['tokens']}")

        print(f"\n📊 Level 2 (Standard):")
        print(f"   {result['level_2']['summary'][:100]}...")
        print(f"   Tokens: {result['level_2']['tokens']}")

        print(f"\n📊 Level 3 (Detailed):")
        print(f"   {result['level_3']['summary'][:100]}...")
        print(f"   Tokens: {result['level_3']['tokens']}")

        print(f"\n📈 Total Tokens: {result['total_tokens']}")
        print(f"   Is Mock: {result['is_mock']}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")
        return False


def test_summary_service_parameters():
    """Test different parameter combinations"""
    print("\n" + "="*70)
    print("TEST 3: Different Parameter Combinations")
    print("="*70)

    from app.services.summary_service import (
        SummaryService,
        SummaryLength,
        SummaryTone,
        SummaryGranularity,
        SummaryFormat
    )

    test_cases = [
        {
            "name": "Short + Casual + Bullet Points",
            "params": {
                "length": SummaryLength.SHORT,
                "tone": SummaryTone.CASUAL,
                "granularity": SummaryGranularity.HIGH_LEVEL,
                "format_type": SummaryFormat.BULLET_POINTS
            }
        },
        {
            "name": "Long + Academic + Structured",
            "params": {
                "length": SummaryLength.LONG,
                "tone": SummaryTone.ACADEMIC,
                "granularity": SummaryGranularity.COMPREHENSIVE,
                "format_type": SummaryFormat.STRUCTURED
            }
        },
        {
            "name": "Medium + Executive + Plain Text",
            "params": {
                "length": SummaryLength.MEDIUM,
                "tone": SummaryTone.EXECUTIVE,
                "granularity": SummaryGranularity.DETAILED,
                "format_type": SummaryFormat.PLAIN_TEXT
            }
        }
    ]

    service = SummaryService(provider="anthropic")
    passed = 0

    for case in test_cases:
        try:
            print(f"\n  Testing: {case['name']}")
            result = service.summarize(
                text=JAPANESE_SHORT_TEXT,
                **case['params']
            )

            assert "summary" in result
            print(f"  ✅ {case['name']}: Success")
            print(f"     Summary length: {len(result['summary'])} chars")
            print(f"     First 80 chars: {result['summary'][:80]}...")
            passed += 1

        except Exception as e:
            print(f"  ❌ {case['name']}: Failed - {e}")

    print(f"\n📊 Results: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_summary_service_long_document():
    """Test map-reduce for long documents"""
    print("\n" + "="*70)
    print("TEST 4: Long Document Handling (Map-Reduce)")
    print("="*70)

    from app.services.summary_service import (
        SummaryService,
        SummaryLength,
        SummaryTone,
        SummaryGranularity,
        SummaryFormat
    )

    try:
        # Create very long text (repeat to exceed token limit)
        very_long_text = (JAPANESE_LONG_TEXT + "\n\n") * 5

        service = SummaryService(provider="anthropic")

        # Check if chunking is needed
        estimated_tokens = service.estimate_tokens(very_long_text)
        print(f"  Text length: {len(very_long_text)} chars")
        print(f"  Estimated tokens: {estimated_tokens}")

        result = service.summarize(
            text=very_long_text,
            length=SummaryLength.MEDIUM,
            tone=SummaryTone.PROFESSIONAL,
            granularity=SummaryGranularity.HIGH_LEVEL,
            format_type=SummaryFormat.PLAIN_TEXT
        )

        print(f"✅ Long document summarized successfully!")
        print(f"   Chunks processed: {result['chunks']}")
        print(f"   Summary: {result['summary'][:150]}...")
        print(f"   Total tokens: {result['tokens']['total']}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")
        return False


def test_summary_service_language_detection():
    """Test language detection (Japanese vs English)"""
    print("\n" + "="*70)
    print("TEST 5: Language Detection (Japanese vs English)")
    print("="*70)

    from app.services.summary_service import (
        SummaryService,
        SummaryLength,
        SummaryTone,
        SummaryGranularity,
        SummaryFormat
    )

    service = SummaryService(provider="anthropic")

    # Test Japanese
    try:
        print("\n  Testing Japanese text...")
        result_ja = service.summarize(
            text=JAPANESE_SHORT_TEXT,
            length=SummaryLength.SHORT,
            tone=SummaryTone.PROFESSIONAL,
            granularity=SummaryGranularity.HIGH_LEVEL,
            format_type=SummaryFormat.PLAIN_TEXT
        )
        assert result_ja["language"] == "ja"
        print(f"  ✅ Japanese detected: {result_ja['language']}")
        print(f"     Summary: {result_ja['summary'][:80]}...")

    except Exception as e:
        print(f"  ❌ Japanese test failed: {e}")
        return False

    # Test English
    try:
        print("\n  Testing English text...")
        result_en = service.summarize(
            text=ENGLISH_TEXT,
            length=SummaryLength.SHORT,
            tone=SummaryTone.PROFESSIONAL,
            granularity=SummaryGranularity.HIGH_LEVEL,
            format_type=SummaryFormat.PLAIN_TEXT
        )
        assert result_en["language"] == "en"
        print(f"  ✅ English detected: {result_en['language']}")
        print(f"     Summary: {result_en['summary'][:80]}...")

    except Exception as e:
        print(f"  ❌ English test failed: {e}")
        return False

    print(f"\n✅ Language detection test passed!")
    return True


# =============================================================================
# Integration Tests (API + Database)
# =============================================================================

def test_api_create_summary():
    """Test summary creation API endpoint"""
    print("\n" + "="*70)
    print("TEST 6: API - Create Summary (POST /api/v1/summary/create)")
    print("="*70)

    import requests

    url = "http://localhost:8000/api/v1/summary/create"
    payload = {
        "text": JAPANESE_SHORT_TEXT,
        "book_title": "Test Book - API",
        "length": "medium",
        "tone": "professional",
        "granularity": "high_level",
        "format": "plain_text"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Summary created successfully!")
        print(f"   Summary ID: {result['summary_id']}")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Book Title: {result['book_title']}")
        print(f"   Language: {result['language']}")
        print(f"   Summary: {result['summary_text'][:100]}...")
        print(f"   Token Usage: {result['token_usage']}")

        return result['summary_id'], result['job_id']

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None, None


def test_api_create_multilevel_summary():
    """Test multi-level summary creation API endpoint"""
    print("\n" + "="*70)
    print("TEST 7: API - Create Multi-level Summary (POST /api/v1/summary/create-multilevel)")
    print("="*70)

    import requests

    url = "http://localhost:8000/api/v1/summary/create-multilevel"
    payload = {
        "text": JAPANESE_LONG_TEXT,
        "book_title": "Test Book - Multi-level",
        "tone": "professional",
        "format": "plain_text"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Multi-level summary created successfully!")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Book Title: {result['book_title']}")
        print(f"   Language: {result['language']}")
        print(f"   Summary IDs: {result['summary_ids']}")

        print(f"\n   Level 1 (Executive):")
        print(f"      {result['level_1']['summary']}")

        print(f"\n   Level 2 (Standard):")
        print(f"      {result['level_2']['summary'][:100]}...")

        print(f"\n   Level 3 (Detailed):")
        print(f"      {result['level_3']['summary'][:100]}...")

        print(f"\n   Total Tokens: {result['total_tokens']}")

        return result['summary_ids'][0], result['job_id']

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None, None


def test_api_get_summary(summary_id: int):
    """Test get summary by ID"""
    print("\n" + "="*70)
    print(f"TEST 8: API - Get Summary (GET /api/v1/summary/{summary_id})")
    print("="*70)

    import requests

    url = f"http://localhost:8000/api/v1/summary/{summary_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Summary retrieved successfully!")
        print(f"   ID: {result['id']}")
        print(f"   Job ID: {result['job_id']}")
        print(f"   Book Title: {result['book_title']}")
        print(f"   Summary: {result['summary_text'][:100]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def test_api_get_summaries_by_job(job_id: str):
    """Test get summaries by job ID"""
    print("\n" + "="*70)
    print(f"TEST 9: API - Get Summaries by Job (GET /api/v1/summary/job/{job_id})")
    print("="*70)

    import requests

    url = f"http://localhost:8000/api/v1/summary/job/{job_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Summaries retrieved successfully!")
        print(f"   Total: {result['total']}")
        print(f"   Summaries: {len(result['summaries'])}")

        for i, summary in enumerate(result['summaries'][:3], 1):
            print(f"\n   Summary {i}:")
            print(f"      ID: {summary['id']}")
            print(f"      Text: {summary['summary_text'][:80]}...")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def test_api_regenerate_summary(summary_id: int):
    """Test regenerate summary with different parameters"""
    print("\n" + "="*70)
    print(f"TEST 10: API - Regenerate Summary (PUT /api/v1/summary/{summary_id}/regenerate)")
    print("="*70)

    import requests

    url = f"http://localhost:8000/api/v1/summary/{summary_id}/regenerate"
    payload = {
        "length": "long",
        "tone": "casual",
        "granularity": "detailed",
        "format": "bullet_points"
    }

    try:
        response = requests.put(url, json=payload)
        response.raise_for_status()

        result = response.json()
        print(f"✅ Summary regenerated successfully!")
        print(f"   Summary ID: {result['summary_id']}")
        print(f"   New Length: {result['length']}")
        print(f"   New Tone: {result['tone']}")
        print(f"   New Granularity: {result['granularity']}")
        print(f"   New Summary: {result['summary_text'][:150]}...")
        print(f"   Token Usage: {result['token_usage']}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ API test failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("SUMMARY SERVICE & API TEST SUITE - Phase 3")
    print("="*70)

    results = []

    # Unit Tests
    print("\n" + "="*70)
    print("UNIT TESTS (SummaryService)")
    print("="*70)

    results.append(("Basic Summarization", test_summary_service_basic()))
    results.append(("Multi-level Summarization", test_summary_service_multilevel()))
    results.append(("Parameter Combinations", test_summary_service_parameters()))
    results.append(("Long Document (Map-Reduce)", test_summary_service_long_document()))
    results.append(("Language Detection", test_summary_service_language_detection()))

    # API Tests
    print("\n" + "="*70)
    print("INTEGRATION TESTS (API + Database)")
    print("="*70)
    print("Note: These tests require the FastAPI server running on localhost:8000")

    try:
        import requests
        # Check if server is running
        requests.get("http://localhost:8000/docs", timeout=2)
        server_running = True
    except:
        server_running = False
        print("⚠️  Server not running on localhost:8000. Skipping API tests.")

    if server_running:
        summary_id, job_id = test_api_create_summary()
        if summary_id:
            results.append(("API: Create Summary", True))
            results.append(("API: Get Summary", test_api_get_summary(summary_id)))
            results.append(("API: Get Summaries by Job", test_api_get_summaries_by_job(job_id)))
            results.append(("API: Regenerate Summary", test_api_regenerate_summary(summary_id)))
        else:
            results.append(("API: Create Summary", False))

        multilevel_summary_id, multilevel_job_id = test_api_create_multilevel_summary()
        if multilevel_summary_id:
            results.append(("API: Create Multi-level Summary", True))
        else:
            results.append(("API: Create Multi-level Summary", False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*70)

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
