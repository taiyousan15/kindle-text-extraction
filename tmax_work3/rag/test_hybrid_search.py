"""
Comprehensive Test Suite for Hybrid Search RAG System
"""
import pytest
import tempfile
import shutil
from pathlib import Path

from bm25_index import BM25Index
from vector_store import VectorStore
from splade_model import SPLADEModel
from rrf_fusion import ReciprocalRankFusion, weighted_sum_fusion
from hybrid_search import HybridSearchRAG


# Sample test documents
SAMPLE_DOCUMENTS = [
    "The quick brown fox jumps over the lazy dog",
    "Python is a powerful programming language for data science and machine learning",
    "Machine learning models require large datasets for training and validation",
    "Natural language processing enables computers to understand and generate human language",
    "Deep learning neural networks can solve complex problems in computer vision",
    "Transformers have revolutionized natural language processing tasks",
    "BERT and GPT are popular transformer-based language models",
    "Vector embeddings capture semantic meaning of text",
    "Information retrieval systems help users find relevant documents",
    "Hybrid search combines keyword matching with semantic search for better results"
]

SAMPLE_QUERIES = [
    "machine learning training",
    "natural language understanding",
    "vector embeddings semantic",
    "How do transformers work?",
    "python programming"
]


class TestBM25Index:
    """Test BM25 keyword search index"""

    def test_initialization(self):
        """Test BM25 index initialization"""
        index = BM25Index()
        assert len(index) == 0
        assert index.language == "english"
        assert index.use_stopwords is True

    def test_add_documents(self):
        """Test adding documents to BM25 index"""
        index = BM25Index()
        index.add_documents(SAMPLE_DOCUMENTS[:5])
        assert len(index) == 5

    def test_search_basic(self):
        """Test basic BM25 search"""
        index = BM25Index()
        index.add_documents(SAMPLE_DOCUMENTS)

        results = index.search("machine learning", top_k=3)
        assert len(results) <= 3
        assert all("document_id" in r for r in results)
        assert all("rank" in r for r in results)
        assert all("score" in r for r in results)

    def test_search_ranking(self):
        """Test that BM25 ranks relevant documents higher"""
        index = BM25Index()
        index.add_documents(SAMPLE_DOCUMENTS)

        results = index.search("machine learning models training", top_k=5)
        assert len(results) > 0

        # Document about machine learning should be in top results
        top_doc_ids = [r["document_id"] for r in results[:2]]
        assert any("doc_2" in doc_id or "doc_1" in doc_id for doc_id in top_doc_ids)

    def test_tokenization(self):
        """Test tokenization"""
        index = BM25Index()
        tokens = index.tokenize("The quick brown fox")
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_save_load(self):
        """Test saving and loading BM25 index"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "bm25_test.pkl"

            # Create and save
            index1 = BM25Index()
            index1.add_documents(SAMPLE_DOCUMENTS[:3])
            index1.save(str(save_path))

            # Load
            index2 = BM25Index()
            index2.load(str(save_path))

            assert len(index2) == 3
            assert index2.documents == index1.documents

    def test_clear(self):
        """Test clearing index"""
        index = BM25Index()
        index.add_documents(SAMPLE_DOCUMENTS)
        assert len(index) > 0

        index.clear()
        assert len(index) == 0


class TestVectorStore:
    """Test dense vector store"""

    def test_initialization_faiss(self):
        """Test FAISS backend initialization"""
        store = VectorStore(backend="faiss")
        assert store.backend == "faiss"
        assert len(store) == 0

    def test_add_documents(self):
        """Test adding documents to vector store"""
        store = VectorStore(backend="faiss")
        store.add_documents(SAMPLE_DOCUMENTS[:5])
        assert len(store) == 5

    def test_search_semantic(self):
        """Test semantic search"""
        store = VectorStore(backend="faiss")
        store.add_documents(SAMPLE_DOCUMENTS)

        # Semantic query
        results = store.search("understanding human language", top_k=3)
        assert len(results) <= 3

        # Should find NLP-related documents
        top_texts = [r["text"] for r in results]
        assert any("natural language" in text.lower() for text in top_texts)

    def test_encode(self):
        """Test encoding text to embeddings"""
        store = VectorStore(backend="faiss")
        embeddings = store.encode(["test text"])
        assert embeddings.shape[0] == 1
        assert embeddings.shape[1] == store.embedding_dim

    def test_save_load_faiss(self):
        """Test saving and loading FAISS index"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "vector_test"

            # Create and save
            store1 = VectorStore(backend="faiss")
            store1.add_documents(SAMPLE_DOCUMENTS[:3])
            store1.save(str(save_path))

            # Load
            store2 = VectorStore(backend="faiss")
            store2.load(str(save_path))

            assert len(store2) == 3
            assert store2.documents == store1.documents


class TestSPLADEModel:
    """Test SPLADE sparse-dense hybrid model"""

    def test_initialization(self):
        """Test SPLADE model initialization"""
        model = SPLADEModel()
        assert len(model) == 0

    def test_add_documents(self):
        """Test adding documents to SPLADE index"""
        model = SPLADEModel()
        model.add_documents(SAMPLE_DOCUMENTS[:5])
        assert len(model) == 5

    def test_encode(self):
        """Test encoding text to sparse vectors"""
        model = SPLADEModel()
        sparse_vecs = model.encode(["test text"])
        assert len(sparse_vecs) == 1
        assert isinstance(sparse_vecs[0], dict)

    def test_search(self):
        """Test SPLADE search"""
        model = SPLADEModel()
        model.add_documents(SAMPLE_DOCUMENTS)

        results = model.search("machine learning", top_k=3)
        assert len(results) <= 3
        assert all("document_id" in r for r in results)

    def test_save_load(self):
        """Test saving and loading SPLADE index"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "splade_test.pkl"

            # Create and save
            model1 = SPLADEModel()
            model1.add_documents(SAMPLE_DOCUMENTS[:3])
            model1.save(str(save_path))

            # Load
            model2 = SPLADEModel()
            model2.load(str(save_path))

            assert len(model2) == 3
            assert model2.documents == model1.documents


class TestRRFFusion:
    """Test Reciprocal Rank Fusion algorithm"""

    def test_initialization(self):
        """Test RRF initialization"""
        rrf = ReciprocalRankFusion(k=60)
        assert rrf.k == 60

    def test_basic_fusion(self):
        """Test basic RRF fusion"""
        rrf = ReciprocalRankFusion(k=60)

        result_list1 = [
            {"document_id": "doc1", "rank": 1, "text": "text1", "method": "bm25"},
            {"document_id": "doc2", "rank": 2, "text": "text2", "method": "bm25"},
        ]

        result_list2 = [
            {"document_id": "doc2", "rank": 1, "text": "text2", "method": "dense"},
            {"document_id": "doc3", "rank": 2, "text": "text3", "method": "dense"},
        ]

        fused = rrf.fuse([result_list1, result_list2])

        assert len(fused) == 3
        assert all("rrf_score" in r for r in fused)
        assert all("methods" in r for r in fused)

        # doc2 appears in both lists, should rank high
        top_doc = fused[0]
        assert top_doc["document_id"] == "doc2"
        assert len(top_doc["methods"]) == 2

    def test_weighted_fusion(self):
        """Test weighted RRF fusion"""
        rrf = ReciprocalRankFusion(k=60)

        result_list1 = [
            {"document_id": "doc1", "rank": 1, "text": "text1", "method": "sparse"},
        ]

        result_list2 = [
            {"document_id": "doc2", "rank": 1, "text": "text2", "method": "dense"},
        ]

        # Heavily favor dense (alpha=0.9)
        fused = rrf.fuse_weighted([result_list1, result_list2], alpha=0.9)

        assert len(fused) == 2
        # Dense result should rank higher with alpha=0.9
        assert fused[0]["document_id"] == "doc2"

    def test_empty_results(self):
        """Test fusion with empty result lists"""
        rrf = ReciprocalRankFusion(k=60)
        fused = rrf.fuse([])
        assert len(fused) == 0


class TestWeightedSumFusion:
    """Test weighted sum fusion"""

    def test_basic_weighted_sum(self):
        """Test basic weighted sum fusion"""
        result_list1 = [
            {"document_id": "doc1", "rank": 1, "score": 5.0, "text": "text1", "method": "bm25"},
        ]

        result_list2 = [
            {"document_id": "doc2", "rank": 1, "score": 0.9, "text": "text2", "method": "dense"},
        ]

        fused = weighted_sum_fusion([result_list1, result_list2])
        assert len(fused) == 2
        assert all("fusion_score" in r for r in fused)


class TestHybridSearchRAG:
    """Test complete Hybrid Search RAG system"""

    def test_initialization(self):
        """Test system initialization"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        assert rag.bm25_index is not None
        assert rag.vector_store is not None
        assert rag.rrf is not None

    def test_add_documents(self):
        """Test adding documents to system"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS[:5])

        assert len(rag.bm25_index) == 5
        assert len(rag.vector_store) == 5

    def test_search_bm25(self):
        """Test BM25-only search"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        results = rag.search("machine learning", method="bm25", top_k=3)
        assert len(results) <= 3
        assert all(r["method"] == "bm25" for r in results)

    def test_search_dense(self):
        """Test dense vector search"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        results = rag.search("understanding human language", method="dense", top_k=3)
        assert len(results) <= 3
        assert all(r["method"] == "dense_vector" for r in results)

    def test_search_hybrid(self):
        """Test hybrid search with RRF fusion"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        results = rag.search("machine learning models", method="hybrid", top_k=3)
        assert len(results) <= 3
        assert all("rrf_score" in r for r in results)
        assert all("methods" in r for r in results)

    def test_alpha_adjustment(self):
        """Test dynamic alpha adjustment"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        # Short query should favor BM25 (lower alpha)
        alpha_short = rag._detect_optimal_alpha("ML")
        assert alpha_short < 0.5

        # Long semantic query should favor dense (higher alpha)
        alpha_long = rag._detect_optimal_alpha("How does natural language processing work?")
        assert alpha_long > 0.5

    def test_metrics(self):
        """Test performance metrics tracking"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        # Perform searches
        rag.search("test query 1", method="bm25", top_k=3)
        rag.search("test query 2", method="dense", top_k=3)
        rag.search("test query 3", method="hybrid", top_k=3)

        metrics = rag.get_metrics()
        assert metrics["total_searches"] == 3
        assert metrics["avg_search_time"] > 0
        assert metrics["method_usage"]["bm25"] == 1
        assert metrics["method_usage"]["dense"] == 1
        assert metrics["method_usage"]["hybrid"] == 1

    def test_save_load(self):
        """Test saving and loading entire system"""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = Path(tmpdir) / "rag_system"

            # Create and save
            rag1 = HybridSearchRAG(use_splade=False, vector_backend="faiss")
            rag1.add_documents(SAMPLE_DOCUMENTS[:5])
            rag1.save(str(save_dir))

            # Load
            rag2 = HybridSearchRAG(use_splade=False, vector_backend="faiss")
            rag2.load(str(save_dir))

            assert len(rag2.bm25_index) == 5
            assert len(rag2.vector_store) == 5

    def test_clear(self):
        """Test clearing all indexes"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        assert len(rag.bm25_index) > 0
        assert len(rag.vector_store) > 0

        rag.clear()

        assert len(rag.bm25_index) == 0
        assert len(rag.vector_store) == 0


class TestIntegration:
    """Integration tests for complete workflow"""

    def test_end_to_end_workflow(self):
        """Test complete end-to-end RAG workflow"""
        # Initialize system
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")

        # Add documents
        rag.add_documents(SAMPLE_DOCUMENTS)

        # Perform various searches
        for query in SAMPLE_QUERIES:
            # BM25 search
            bm25_results = rag.search(query, method="bm25", top_k=3)
            assert len(bm25_results) <= 3

            # Dense search
            dense_results = rag.search(query, method="dense", top_k=3)
            assert len(dense_results) <= 3

            # Hybrid search
            hybrid_results = rag.search(query, method="hybrid", top_k=3)
            assert len(hybrid_results) <= 3

        # Check metrics
        metrics = rag.get_metrics()
        assert metrics["total_searches"] == len(SAMPLE_QUERIES) * 3

    def test_retrieval_quality(self):
        """Test retrieval quality with known relevant documents"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")
        rag.add_documents(SAMPLE_DOCUMENTS)

        # Query about machine learning
        query = "machine learning models training datasets"
        results = rag.search(query, method="hybrid", top_k=5)

        # Check that relevant documents are retrieved
        texts = [r["text"].lower() for r in results]
        assert any("machine learning" in text for text in texts)
        assert any("training" in text or "datasets" in text for text in texts)

    def test_batch_processing(self):
        """Test batch document processing"""
        rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")

        # Add large batch
        large_batch = SAMPLE_DOCUMENTS * 10  # 100 documents
        rag.add_documents(large_batch, batch_size=20)

        assert len(rag.bm25_index) == 100
        assert len(rag.vector_store) == 100

        # Search should still work
        results = rag.search("test query", method="hybrid", top_k=10)
        assert len(results) <= 10


def test_blackboard_integration():
    """Test integration with Blackboard system"""
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))

    from blackboard.state_manager import AgentType

    # Verify RAG agent type exists
    assert hasattr(AgentType, "RAG")
    assert AgentType.RAG.value == "rag"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
