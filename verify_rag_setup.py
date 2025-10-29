#!/usr/bin/env python3
"""
RAG Setup Verification Script

Quick verification that all Phase 2 components are properly installed and configured.
Run this after installing dependencies to ensure everything works.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all RAG components can be imported"""
    print("\n" + "="*60)
    print("PHASE 2 RAG SETUP VERIFICATION")
    print("="*60)

    print("\n[1/5] Testing imports...")

    try:
        from app.services.llm_service import LLMService, get_llm_service
        print("  ✓ LLM Service")
    except ImportError as e:
        print(f"  ✗ LLM Service: {e}")
        return False

    try:
        from app.services.embedding_service import EmbeddingService, get_embedding_service
        print("  ✓ Embedding Service")
    except ImportError as e:
        print(f"  ✗ Embedding Service: {e}")
        return False

    try:
        from app.services.vector_store import VectorStore
        print("  ✓ Vector Store")
    except ImportError as e:
        print(f"  ✗ Vector Store: {e}")
        return False

    try:
        from app.schemas.rag import (
            RAGQueryRequest, RAGQueryResponse,
            RAGIndexRequest, RAGIndexResponse
        )
        print("  ✓ RAG Schemas")
    except ImportError as e:
        print(f"  ✗ RAG Schemas: {e}")
        return False

    try:
        from app.api.v1.endpoints import rag
        print("  ✓ RAG Endpoints")
    except ImportError as e:
        print(f"  ✗ RAG Endpoints: {e}")
        return False

    return True


def test_llm_service():
    """Test LLM service initialization"""
    print("\n[2/5] Testing LLM Service...")

    try:
        from app.services.llm_service import get_llm_service

        llm = get_llm_service(provider="anthropic")

        if llm.is_mock:
            print("  ⚠ LLM in mock mode (API key not configured)")
        else:
            print("  ✓ LLM service initialized with API key")

        # Test generation
        result = llm.generate("Hello")
        print(f"  ✓ Generation test passed (mock={result['is_mock']})")

        return True
    except Exception as e:
        print(f"  ✗ LLM Service error: {e}")
        return False


def test_embedding_service():
    """Test embedding service initialization"""
    print("\n[3/5] Testing Embedding Service...")

    try:
        from app.services.embedding_service import get_embedding_service

        print("  → Loading embedding model (this may take a minute first time)...")
        embedding_service = get_embedding_service()

        info = embedding_service.get_model_info()
        print(f"  ✓ Model loaded: {info['model_name']}")
        print(f"  ✓ Embedding dimension: {info['embedding_dim']}")

        # Test embedding generation
        text = "This is a test."
        embedding = embedding_service.generate_embedding(text)
        print(f"  ✓ Embedding generated: {len(embedding)} dimensions")

        return True
    except Exception as e:
        print(f"  ✗ Embedding Service error: {e}")
        return False


def test_database_connection():
    """Test database connection"""
    print("\n[4/5] Testing Database Connection...")

    try:
        from app.core.database import check_connection

        if check_connection():
            print("  ✓ Database connection successful")
            return True
        else:
            print("  ✗ Database connection failed")
            print("  → Check DATABASE_URL in .env")
            return False
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return False


def test_vector_store():
    """Test vector store functionality"""
    print("\n[5/5] Testing Vector Store...")

    try:
        from app.core.database import SessionLocal
        from app.services.vector_store import VectorStore

        db = SessionLocal()
        vector_store = VectorStore(db)

        # Get statistics
        stats = vector_store.get_statistics()
        print(f"  ✓ Vector store accessible")
        print(f"  ✓ Total documents: {stats['total_documents']}")
        print(f"  ✓ Total files: {stats['total_files']}")
        print(f"  ✓ Documents with embeddings: {stats['documents_with_embeddings']}")

        db.close()
        return True
    except Exception as e:
        print(f"  ✗ Vector Store error: {e}")
        return False


def print_summary(results):
    """Print summary of verification"""
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(results.values())

    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All tests passed! RAG system is ready to use.")
        print("\nNext steps:")
        print("  1. Start server: uvicorn app.main:app --reload")
        print("  2. Access docs: http://localhost:8000/docs")
        print("  3. Run tests: pytest test_rag.py -v")
        print("  4. See QUICKSTART_RAG.md for usage examples")
        return True
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Check database: Ensure PostgreSQL is running")
        print("  - Enable pgvector: CREATE EXTENSION vector;")
        print("  - See QUICKSTART_RAG.md for detailed setup")
        return False


def main():
    """Run all verification tests"""
    results = {
        "Imports": test_imports(),
    }

    # Only run subsequent tests if imports pass
    if results["Imports"]:
        results["LLM Service"] = test_llm_service()
        results["Embedding Service"] = test_embedding_service()
        results["Database"] = test_database_connection()

        # Only test vector store if database works
        if results["Database"]:
            results["Vector Store"] = test_vector_store()
        else:
            results["Vector Store"] = False
    else:
        print("\n⚠️ Imports failed. Skipping other tests.")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        results.update({
            "LLM Service": False,
            "Embedding Service": False,
            "Database": False,
            "Vector Store": False
        })

    success = print_summary(results)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
