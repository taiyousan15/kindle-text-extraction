"""
Vector Store Module for Hybrid Search RAG System
Provides dense vector-based semantic retrieval using ChromaDB or FAISS
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
import numpy as np

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Dense Vector Store for Semantic Search

    Supports multiple backends:
    - ChromaDB (default): Persistent, feature-rich vector database
    - FAISS: Fast approximate nearest neighbor search

    Uses sentence-transformers for embedding generation.
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        backend: str = "chromadb",
        persist_directory: Optional[str] = None,
        collection_name: str = "hybrid_rag"
    ):
        """
        Initialize Vector Store

        Args:
            embedding_model: HuggingFace model name for embeddings
            backend: Vector store backend ('chromadb' or 'faiss')
            persist_directory: Directory for persistence
            collection_name: Collection/index name
        """
        self.embedding_model_name = embedding_model
        self.backend = backend
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.encoder.get_sentence_embedding_dimension()

        # Initialize backend
        if backend == "chromadb":
            self._init_chromadb()
        elif backend == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"Unsupported backend: {backend}")

        logger.info(f"VectorStore initialized (backend={backend}, dim={self.embedding_dim})")

    def _init_chromadb(self):
        """Initialize ChromaDB backend"""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError("ChromaDB not installed. Install with: pip install chromadb")

        if self.persist_directory:
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
        else:
            self.client = chromadb.Client()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

        logger.info(f"ChromaDB collection '{self.collection_name}' ready")

    def _init_faiss(self):
        """Initialize FAISS backend"""
        try:
            import faiss
        except ImportError:
            raise ImportError("FAISS not installed. Install with: pip install faiss-cpu")

        self.faiss = faiss
        self.index = None
        self.document_ids: List[str] = []
        self.documents: List[str] = []
        self.metadata: List[Dict] = []

        logger.info("FAISS backend initialized")

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Encode texts to embeddings

        Args:
            texts: Single text or list of texts

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.encoder.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        return embeddings

    def add_documents(
        self,
        documents: List[str],
        document_ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict]] = None
    ):
        """
        Add documents to vector store

        Args:
            documents: List of document texts
            document_ids: Optional list of document IDs
            metadata: Optional list of metadata dicts
        """
        # Generate IDs if not provided
        if document_ids is None:
            if self.backend == "chromadb":
                start_id = self.collection.count()
            else:
                start_id = len(self.documents)
            document_ids = [f"doc_{i}" for i in range(start_id, start_id + len(documents))]

        if metadata is None:
            metadata = [{} for _ in documents]

        # Validate input lengths
        if not (len(documents) == len(document_ids) == len(metadata)):
            raise ValueError("documents, document_ids, and metadata must have the same length")

        # Generate embeddings
        logger.info(f"Encoding {len(documents)} documents...")
        embeddings = self.encode(documents)

        # Add to backend
        if self.backend == "chromadb":
            self._add_to_chromadb(documents, document_ids, embeddings, metadata)
        elif self.backend == "faiss":
            self._add_to_faiss(documents, document_ids, embeddings, metadata)

        logger.info(f"Added {len(documents)} documents to vector store")

    def _add_to_chromadb(
        self,
        documents: List[str],
        document_ids: List[str],
        embeddings: np.ndarray,
        metadata: List[Dict]
    ):
        """Add documents to ChromaDB"""
        self.collection.add(
            documents=documents,
            ids=document_ids,
            embeddings=embeddings.tolist(),
            metadatas=metadata
        )

    def _add_to_faiss(
        self,
        documents: List[str],
        document_ids: List[str],
        embeddings: np.ndarray,
        metadata: List[Dict]
    ):
        """Add documents to FAISS"""
        # Initialize index if needed
        if self.index is None:
            self.index = self.faiss.IndexFlatIP(self.embedding_dim)  # Inner Product (cosine with normalized vectors)

        # Normalize embeddings for cosine similarity
        self.faiss.normalize_L2(embeddings)

        # Add to index
        self.index.add(embeddings)

        # Store metadata
        self.documents.extend(documents)
        self.document_ids.extend(document_ids)
        self.metadata.extend(metadata)

    def search(
        self,
        query: str,
        top_k: int = 10,
        return_scores: bool = True
    ) -> List[Dict]:
        """
        Search documents using semantic similarity

        Args:
            query: Search query
            top_k: Number of results to return
            return_scores: Whether to return similarity scores

        Returns:
            List of result dictionaries with document info and scores
        """
        # Encode query
        query_embedding = self.encode(query)

        # Search based on backend
        if self.backend == "chromadb":
            return self._search_chromadb(query_embedding, top_k, return_scores)
        elif self.backend == "faiss":
            return self._search_faiss(query_embedding, top_k, return_scores)

    def _search_chromadb(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        return_scores: bool
    ) -> List[Dict]:
        """Search using ChromaDB"""
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []
        for rank, (doc_id, document, metadata, distance) in enumerate(zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            result = {
                "rank": rank + 1,
                "document_id": doc_id,
                "text": document,
                "metadata": metadata,
                "method": "dense_vector"
            }

            if return_scores:
                # ChromaDB returns distance, convert to similarity
                result["score"] = 1.0 - distance

            formatted_results.append(result)

        return formatted_results

    def _search_faiss(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        return_scores: bool
    ) -> List[Dict]:
        """Search using FAISS"""
        if self.index is None or self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []

        # Normalize query for cosine similarity
        query_embedding = query_embedding.reshape(1, -1)
        self.faiss.normalize_L2(query_embedding)

        # Search
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, k)

        # Format results
        results = []
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
            result = {
                "rank": rank + 1,
                "document_id": self.document_ids[idx],
                "text": self.documents[idx],
                "metadata": self.metadata[idx],
                "method": "dense_vector"
            }

            if return_scores:
                result["score"] = float(score)

            results.append(result)

        return results

    def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """
        Get document by ID

        Args:
            document_id: Document ID

        Returns:
            Document dict or None if not found
        """
        if self.backend == "chromadb":
            results = self.collection.get(ids=[document_id], include=["documents", "metadatas"])
            if results["ids"]:
                return {
                    "document_id": document_id,
                    "text": results["documents"][0],
                    "metadata": results["metadatas"][0]
                }
        elif self.backend == "faiss":
            try:
                idx = self.document_ids.index(document_id)
                return {
                    "document_id": document_id,
                    "text": self.documents[idx],
                    "metadata": self.metadata[idx]
                }
            except ValueError:
                pass

        return None

    def save(self, path: str):
        """
        Save vector store to disk

        Args:
            path: File path to save
        """
        if self.backend == "chromadb":
            # ChromaDB auto-persists if persist_directory is set
            logger.info(f"ChromaDB collection persisted at {self.persist_directory}")
        elif self.backend == "faiss":
            save_path = Path(path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            if self.index is not None:
                self.faiss.write_index(self.index, str(save_path.with_suffix('.faiss')))

            # Save metadata
            import pickle
            metadata_path = save_path.with_suffix('.metadata')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    "document_ids": self.document_ids,
                    "documents": self.documents,
                    "metadata": self.metadata
                }, f)

            logger.info(f"FAISS index saved to {save_path}")

    def load(self, path: str):
        """
        Load vector store from disk

        Args:
            path: File path to load
        """
        if self.backend == "faiss":
            load_path = Path(path)

            # Load FAISS index
            index_path = load_path.with_suffix('.faiss')
            if not index_path.exists():
                raise FileNotFoundError(f"FAISS index not found: {index_path}")

            self.index = self.faiss.read_index(str(index_path))

            # Load metadata
            import pickle
            metadata_path = load_path.with_suffix('.metadata')
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.document_ids = data["document_ids"]
                self.documents = data["documents"]
                self.metadata = data["metadata"]

            logger.info(f"FAISS index loaded from {load_path} ({len(self.documents)} documents)")

    def clear(self):
        """Clear all documents from the vector store"""
        if self.backend == "chromadb":
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        elif self.backend == "faiss":
            self.index = None
            self.document_ids = []
            self.documents = []
            self.metadata = []

        logger.info("Vector store cleared")

    def __len__(self) -> int:
        """Return number of documents in vector store"""
        if self.backend == "chromadb":
            return self.collection.count()
        elif self.backend == "faiss":
            return len(self.documents)

    def __repr__(self) -> str:
        return f"VectorStore(backend={self.backend}, documents={len(self)}, dim={self.embedding_dim})"


if __name__ == "__main__":
    # Test Vector Store
    logging.basicConfig(level=logging.INFO)

    # Create vector store
    vector_store = VectorStore(backend="faiss")

    # Add sample documents
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Python is a powerful programming language for data science",
        "Machine learning models require large datasets for training",
        "Natural language processing enables computers to understand human language",
        "Deep learning neural networks can solve complex problems"
    ]

    vector_store.add_documents(documents)

    # Search
    query = "machine learning training data"
    results = vector_store.search(query, top_k=3)

    print(f"\nSemantic search results for: '{query}'")
    print("=" * 80)
    for result in results:
        print(f"Rank {result['rank']}: (score={result['score']:.4f})")
        print(f"  {result['text']}")
        print()
