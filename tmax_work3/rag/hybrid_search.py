"""
Hybrid Search RAG System - Main Module
Combines BM25, Dense Vector, and SPLADE for optimal retrieval
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time

try:
    from .bm25_index import BM25Index
    from .vector_store import VectorStore
    from .splade_model import SPLADEModel
    from .rrf_fusion import ReciprocalRankFusion
except ImportError:
    from bm25_index import BM25Index
    from vector_store import VectorStore
    from splade_model import SPLADEModel
    from rrf_fusion import ReciprocalRankFusion

logger = logging.getLogger(__name__)


class HybridSearchRAG:
    """
    Hybrid Search RAG System

    Implements a state-of-the-art hybrid retrieval system that combines:
    1. BM25: Keyword-based sparse retrieval
    2. Dense Vector Search: Semantic similarity using embeddings
    3. SPLADE: Hybrid sparse-dense retrieval
    4. RRF: Reciprocal Rank Fusion for result combination

    Features:
    - Dynamic alpha adjustment for sparse/dense balance
    - Multi-method retrieval with intelligent fusion
    - Configurable search strategies
    - Performance metrics and analysis
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        splade_model: str = "naver/splade-cocondenser-ensembledistil",
        vector_backend: str = "faiss",
        persist_directory: Optional[str] = None,
        use_splade: bool = True,
        use_gpu: bool = False,
        rrf_k: int = 60
    ):
        """
        Initialize Hybrid Search RAG

        Args:
            embedding_model: Model for dense vector embeddings
            splade_model: Model for SPLADE
            vector_backend: Vector store backend ('chromadb' or 'faiss')
            persist_directory: Directory for persistence
            use_splade: Whether to use SPLADE (requires GPU for best performance)
            use_gpu: Whether to use GPU for SPLADE
            rrf_k: RRF constant (default: 60)
        """
        logger.info("Initializing Hybrid Search RAG System...")

        # Initialize retrieval components
        self.bm25_index = BM25Index()
        self.vector_store = VectorStore(
            embedding_model=embedding_model,
            backend=vector_backend,
            persist_directory=persist_directory,
            collection_name="hybrid_rag_vectors"
        )

        self.use_splade = use_splade
        if use_splade:
            self.splade_model = SPLADEModel(model_name=splade_model, use_gpu=use_gpu)
        else:
            self.splade_model = None

        # Initialize fusion
        self.rrf = ReciprocalRankFusion(k=rrf_k)

        # Configuration
        self.default_alpha = 0.5  # Default balance between sparse and dense
        self.enable_query_analysis = True

        # Metrics
        self.search_metrics = {
            "total_searches": 0,
            "avg_search_time": 0.0,
            "method_usage": {"bm25": 0, "dense": 0, "splade": 0, "hybrid": 0}
        }

        logger.info("Hybrid Search RAG System initialized successfully")

    def add_documents(
        self,
        documents: List[str],
        document_ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict]] = None,
        batch_size: int = 100
    ):
        """
        Add documents to all retrieval indexes

        Args:
            documents: List of document texts
            document_ids: Optional document IDs
            metadata: Optional metadata
            batch_size: Batch size for processing
        """
        if not documents:
            logger.warning("No documents to add")
            return

        logger.info(f"Adding {len(documents)} documents to hybrid search system...")

        # Generate IDs if not provided
        if document_ids is None:
            start_id = len(self.bm25_index)
            document_ids = [f"doc_{i}" for i in range(start_id, start_id + len(documents))]

        if metadata is None:
            metadata = [{} for _ in documents]

        # Process in batches
        total_batches = (len(documents) + batch_size - 1) // batch_size

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = document_ids[i:i + batch_size]
            batch_meta = metadata[i:i + batch_size]

            batch_num = i // batch_size + 1
            logger.info(f"Processing batch {batch_num}/{total_batches}...")

            # Add to BM25
            self.bm25_index.add_documents(batch_docs, batch_ids, batch_meta)

            # Add to vector store
            self.vector_store.add_documents(batch_docs, batch_ids, batch_meta)

            # Add to SPLADE if enabled
            if self.use_splade and self.splade_model:
                self.splade_model.add_documents(batch_docs, batch_ids, batch_meta)

        logger.info(f"Successfully added {len(documents)} documents")

    def search(
        self,
        query: str,
        top_k: int = 10,
        method: str = "hybrid",
        alpha: Optional[float] = None,
        return_scores: bool = True
    ) -> List[Dict]:
        """
        Search documents using specified method

        Args:
            query: Search query
            top_k: Number of results to return
            method: Search method ('bm25', 'dense', 'splade', 'hybrid')
            alpha: Weight for dense results (0-1), None = auto-detect
            return_scores: Whether to return scores

        Returns:
            List of search results
        """
        start_time = time.time()
        self.search_metrics["total_searches"] += 1
        self.search_metrics["method_usage"][method] = self.search_metrics["method_usage"].get(method, 0) + 1

        # Auto-detect alpha if not provided
        if alpha is None and method == "hybrid":
            alpha = self._detect_optimal_alpha(query)
            logger.debug(f"Auto-detected alpha: {alpha:.2f}")
        elif alpha is None:
            alpha = self.default_alpha

        # Perform search based on method
        if method == "bm25":
            results = self._search_bm25(query, top_k, return_scores)
        elif method == "dense":
            results = self._search_dense(query, top_k, return_scores)
        elif method == "splade":
            results = self._search_splade(query, top_k, return_scores)
        elif method == "hybrid":
            results = self._search_hybrid(query, top_k, alpha, return_scores)
        else:
            raise ValueError(f"Unknown search method: {method}")

        # Update metrics
        search_time = time.time() - start_time
        self._update_search_metrics(search_time)

        logger.info(f"Search completed in {search_time:.3f}s, returned {len(results)} results")
        return results

    def _search_bm25(self, query: str, top_k: int, return_scores: bool) -> List[Dict]:
        """Search using BM25 only"""
        return self.bm25_index.search(query, top_k=top_k, return_scores=return_scores)

    def _search_dense(self, query: str, top_k: int, return_scores: bool) -> List[Dict]:
        """Search using dense vectors only"""
        return self.vector_store.search(query, top_k=top_k, return_scores=return_scores)

    def _search_splade(self, query: str, top_k: int, return_scores: bool) -> List[Dict]:
        """Search using SPLADE only"""
        if not self.use_splade or not self.splade_model:
            logger.warning("SPLADE not enabled, falling back to BM25")
            return self._search_bm25(query, top_k, return_scores)
        return self.splade_model.search(query, top_k=top_k, return_scores=return_scores)

    def _search_hybrid(
        self,
        query: str,
        top_k: int,
        alpha: float,
        return_scores: bool
    ) -> List[Dict]:
        """
        Hybrid search using RRF fusion

        Args:
            query: Search query
            top_k: Number of results
            alpha: Weight for dense (0=sparse only, 1=dense only)
            return_scores: Return scores

        Returns:
            Fused search results
        """
        # Retrieve from multiple methods (get more results for better fusion)
        retrieval_k = min(top_k * 3, 100)

        # Get results from each method
        result_lists = []
        weights = []

        # BM25 results
        bm25_results = self.bm25_index.search(query, top_k=retrieval_k, return_scores=True)
        if bm25_results:
            result_lists.append(bm25_results)
            weights.append(1.0 - alpha)  # Sparse weight

        # Dense vector results
        dense_results = self.vector_store.search(query, top_k=retrieval_k, return_scores=True)
        if dense_results:
            result_lists.append(dense_results)
            weights.append(alpha)  # Dense weight

        # SPLADE results (if enabled)
        if self.use_splade and self.splade_model:
            splade_results = self.splade_model.search(query, top_k=retrieval_k, return_scores=True)
            if splade_results:
                result_lists.append(splade_results)
                weights.append(0.5)  # SPLADE gets moderate weight

        # Fuse results using RRF
        if not result_lists:
            logger.warning("No results from any retrieval method")
            return []

        fused_results = self.rrf.fuse(result_lists, weights=weights)

        # Trim to top_k
        return fused_results[:top_k]

    def _detect_optimal_alpha(self, query: str) -> float:
        """
        Detect optimal alpha based on query characteristics

        Args:
            query: Search query

        Returns:
            Optimal alpha value (0-1)
        """
        if not self.enable_query_analysis:
            return self.default_alpha

        # Simple heuristics for alpha adjustment:
        # - Short queries with specific terms -> favor BM25 (lower alpha)
        # - Longer semantic queries -> favor dense vectors (higher alpha)
        # - Queries with rare/technical terms -> favor BM25
        # - Natural language questions -> favor dense vectors

        query_length = len(query.split())

        # Base alpha on query length
        if query_length <= 3:
            # Short queries: favor keyword matching
            alpha = 0.3
        elif query_length <= 7:
            # Medium queries: balanced
            alpha = 0.5
        else:
            # Long queries: favor semantic matching
            alpha = 0.7

        # Adjust for question words (favor semantic)
        question_words = ["what", "why", "how", "when", "where", "who", "which"]
        if any(word in query.lower() for word in question_words):
            alpha = min(alpha + 0.2, 1.0)

        return alpha

    def _update_search_metrics(self, search_time: float):
        """Update search performance metrics"""
        total = self.search_metrics["total_searches"]
        prev_avg = self.search_metrics["avg_search_time"]

        # Update running average
        new_avg = (prev_avg * (total - 1) + search_time) / total
        self.search_metrics["avg_search_time"] = new_avg

    def get_metrics(self) -> Dict:
        """Get search performance metrics"""
        return self.search_metrics.copy()

    def save(self, directory: str):
        """
        Save all indexes

        Args:
            directory: Directory to save indexes
        """
        save_dir = Path(directory)
        save_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Saving indexes to {save_dir}...")

        # Save BM25
        self.bm25_index.save(str(save_dir / "bm25_index.pkl"))

        # Save vector store
        self.vector_store.save(str(save_dir / "vector_store"))

        # Save SPLADE
        if self.use_splade and self.splade_model:
            self.splade_model.save(str(save_dir / "splade_index.pkl"))

        logger.info("All indexes saved successfully")

    def load(self, directory: str):
        """
        Load all indexes

        Args:
            directory: Directory to load indexes from
        """
        load_dir = Path(directory)

        if not load_dir.exists():
            raise FileNotFoundError(f"Directory not found: {load_dir}")

        logger.info(f"Loading indexes from {load_dir}...")

        # Load BM25
        self.bm25_index.load(str(load_dir / "bm25_index.pkl"))

        # Load vector store
        if (load_dir / "vector_store.faiss").exists() or (load_dir / "vector_store").exists():
            self.vector_store.load(str(load_dir / "vector_store"))

        # Load SPLADE
        if self.use_splade and self.splade_model:
            splade_path = load_dir / "splade_index.pkl"
            if splade_path.exists():
                self.splade_model.load(str(splade_path))

        logger.info("All indexes loaded successfully")

    def clear(self):
        """Clear all indexes"""
        self.bm25_index.clear()
        self.vector_store.clear()
        if self.use_splade and self.splade_model:
            self.splade_model.clear()
        logger.info("All indexes cleared")

    def __repr__(self) -> str:
        return (
            f"HybridSearchRAG("
            f"bm25_docs={len(self.bm25_index)}, "
            f"vector_docs={len(self.vector_store)}, "
            f"splade_enabled={self.use_splade})"
        )


if __name__ == "__main__":
    # Test Hybrid Search RAG
    logging.basicConfig(level=logging.INFO)

    # Create system
    rag = HybridSearchRAG(use_splade=False, vector_backend="faiss")

    # Add documents
    documents = [
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

    rag.add_documents(documents)

    # Test different search methods
    query = "How do machine learning models learn from data?"

    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")

    # BM25 search
    print("BM25 Results:")
    print("-" * 80)
    results = rag.search(query, top_k=3, method="bm25")
    for r in results:
        print(f"{r['rank']}. [Score: {r.get('score', 0):.3f}] {r['text'][:80]}...")
    print()

    # Dense search
    print("Dense Vector Results:")
    print("-" * 80)
    results = rag.search(query, top_k=3, method="dense")
    for r in results:
        print(f"{r['rank']}. [Score: {r.get('score', 0):.3f}] {r['text'][:80]}...")
    print()

    # Hybrid search
    print("Hybrid Search Results (RRF):")
    print("-" * 80)
    results = rag.search(query, top_k=3, method="hybrid")
    for r in results:
        methods = ', '.join(r.get('methods', []))
        print(f"{r['rank']}. [RRF: {r.get('rrf_score', 0):.4f}] [{methods}]")
        print(f"    {r['text'][:80]}...")
    print()

    # Show metrics
    print("Performance Metrics:")
    print("-" * 80)
    metrics = rag.get_metrics()
    print(f"Total searches: {metrics['total_searches']}")
    print(f"Average search time: {metrics['avg_search_time']:.3f}s")
    print(f"Method usage: {metrics['method_usage']}")
