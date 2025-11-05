"""
SPLADE Model Module for Hybrid Search RAG System
Provides sparse + dense hybrid retrieval using SPLADE (SParse Lexical AnD Expansion)
"""
import logging
from typing import List, Dict, Optional, Union
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class SPLADEModel:
    """
    SPLADE (SParse Lexical AnD Expansion) Model

    SPLADE combines:
    - Sparse representations (like BM25) for exact keyword matching
    - Dense representations (like BERT) for semantic understanding
    - Term expansion for query understanding

    This implementation uses a simplified approach that combines:
    1. Transformer-based term importance scoring
    2. Sparse vector representation
    3. Efficient retrieval using inverted index
    """

    def __init__(
        self,
        model_name: str = "naver/splade-cocondenser-ensembledistil",
        use_gpu: bool = False
    ):
        """
        Initialize SPLADE Model

        Args:
            model_name: HuggingFace model name for SPLADE
            use_gpu: Whether to use GPU for inference
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.model = None
        self.tokenizer = None

        # Try to load the model
        self._load_model()

        # Document storage
        self.document_ids: List[str] = []
        self.documents: List[str] = []
        self.sparse_vectors: List[Dict[int, float]] = []
        self.metadata: List[Dict] = []

        logger.info(f"SPLADEModel initialized (model={model_name}, gpu={use_gpu})")

    def _load_model(self):
        """Load SPLADE model and tokenizer"""
        try:
            from transformers import AutoModelForMaskedLM, AutoTokenizer
            import torch

            logger.info(f"Loading SPLADE model: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForMaskedLM.from_pretrained(self.model_name)

            # Move to GPU if available and requested
            if self.use_gpu and torch.cuda.is_available():
                self.model = self.model.cuda()
                logger.info("SPLADE model loaded on GPU")
            else:
                self.model = self.model.cpu()
                logger.info("SPLADE model loaded on CPU")

            self.model.eval()

        except ImportError:
            logger.warning("Transformers not installed. SPLADE will use fallback mode.")
            self.model = None
        except Exception as e:
            logger.warning(f"Failed to load SPLADE model: {e}. Using fallback mode.")
            self.model = None

    def encode(self, texts: Union[str, List[str]]) -> List[Dict[int, float]]:
        """
        Encode texts to sparse vectors

        Args:
            texts: Single text or list of texts

        Returns:
            List of sparse vectors (dict of token_id -> weight)
        """
        if isinstance(texts, str):
            texts = [texts]

        if self.model is None:
            # Fallback: Use simple term frequency
            return self._fallback_encode(texts)

        try:
            import torch

            sparse_vectors = []

            with torch.no_grad():
                for text in texts:
                    # Tokenize
                    inputs = self.tokenizer(
                        text,
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=512
                    )

                    if self.use_gpu and torch.cuda.is_available():
                        inputs = {k: v.cuda() for k, v in inputs.items()}

                    # Forward pass
                    outputs = self.model(**inputs)
                    logits = outputs.logits

                    # Apply log(1 + ReLU) activation (SPLADE scoring)
                    scores = torch.log(1 + torch.relu(logits))

                    # Max pooling over sequence dimension
                    sparse_vec = torch.max(scores, dim=1).values.squeeze()

                    # Convert to sparse representation (keep only non-zero values)
                    sparse_dict = {}
                    for idx, value in enumerate(sparse_vec.cpu().numpy()):
                        if value > 0.01:  # Threshold for sparsity
                            sparse_dict[int(idx)] = float(value)

                    sparse_vectors.append(sparse_dict)

            return sparse_vectors

        except Exception as e:
            logger.warning(f"SPLADE encoding failed: {e}. Using fallback.")
            return self._fallback_encode(texts)

    def _fallback_encode(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        Fallback encoding using simple term frequency

        Args:
            texts: List of texts

        Returns:
            List of sparse vectors
        """
        from collections import Counter

        sparse_vectors = []

        for text in texts:
            # Simple tokenization
            tokens = text.lower().split()

            # Term frequency
            tf = Counter(tokens)

            # Create sparse vector (use hash of token as pseudo token_id)
            sparse_dict = {hash(token) % 30000: float(count) for token, count in tf.items()}

            sparse_vectors.append(sparse_dict)

        return sparse_vectors

    def add_documents(
        self,
        documents: List[str],
        document_ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict]] = None
    ):
        """
        Add documents to SPLADE index

        Args:
            documents: List of document texts
            document_ids: Optional list of document IDs
            metadata: Optional list of metadata dicts
        """
        # Generate IDs if not provided
        if document_ids is None:
            start_id = len(self.documents)
            document_ids = [f"doc_{i}" for i in range(start_id, start_id + len(documents))]

        if metadata is None:
            metadata = [{} for _ in documents]

        # Validate input lengths
        if not (len(documents) == len(document_ids) == len(metadata)):
            raise ValueError("documents, document_ids, and metadata must have the same length")

        # Encode documents
        logger.info(f"Encoding {len(documents)} documents with SPLADE...")
        sparse_vectors = self.encode(documents)

        # Store
        self.documents.extend(documents)
        self.document_ids.extend(document_ids)
        self.sparse_vectors.extend(sparse_vectors)
        self.metadata.extend(metadata)

        logger.info(f"Added {len(documents)} documents to SPLADE index (total: {len(self.documents)})")

    def search(
        self,
        query: str,
        top_k: int = 10,
        return_scores: bool = True
    ) -> List[Dict]:
        """
        Search documents using SPLADE

        Args:
            query: Search query
            top_k: Number of results to return
            return_scores: Whether to return SPLADE scores

        Returns:
            List of result dictionaries with document info and scores
        """
        if not self.documents:
            logger.warning("SPLADE index is empty")
            return []

        # Encode query
        query_vector = self.encode(query)[0]

        if not query_vector:
            logger.warning(f"Query encoding resulted in empty vector: {query}")
            return []

        # Compute scores
        scores = []
        for doc_sparse_vec in self.sparse_vectors:
            # Dot product between query and document sparse vectors
            score = sum(
                query_vector.get(token_id, 0) * doc_sparse_vec.get(token_id, 0)
                for token_id in set(query_vector.keys()) | set(doc_sparse_vec.keys())
            )
            scores.append(score)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        # Build results
        results = []
        for rank, idx in enumerate(top_indices):
            result = {
                "rank": rank + 1,
                "document_id": self.document_ids[idx],
                "text": self.documents[idx],
                "metadata": self.metadata[idx],
                "method": "splade"
            }

            if return_scores:
                result["score"] = float(scores[idx])

            results.append(result)

        logger.debug(f"SPLADE search for '{query}' returned {len(results)} results")
        return results

    def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """
        Get document by ID

        Args:
            document_id: Document ID

        Returns:
            Document dict or None if not found
        """
        try:
            idx = self.document_ids.index(document_id)
            return {
                "document_id": document_id,
                "text": self.documents[idx],
                "metadata": self.metadata[idx]
            }
        except ValueError:
            return None

    def save(self, path: str):
        """
        Save SPLADE index to disk

        Args:
            path: File path to save
        """
        import pickle

        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "documents": self.documents,
            "document_ids": self.document_ids,
            "sparse_vectors": self.sparse_vectors,
            "metadata": self.metadata,
            "model_name": self.model_name
        }

        with open(save_path, 'wb') as f:
            pickle.dump(state, f)

        logger.info(f"SPLADE index saved to {save_path}")

    def load(self, path: str):
        """
        Load SPLADE index from disk

        Args:
            path: File path to load
        """
        import pickle

        load_path = Path(path)

        if not load_path.exists():
            raise FileNotFoundError(f"SPLADE index not found: {load_path}")

        with open(load_path, 'rb') as f:
            state = pickle.load(f)

        self.documents = state["documents"]
        self.document_ids = state["document_ids"]
        self.sparse_vectors = state["sparse_vectors"]
        self.metadata = state["metadata"]

        logger.info(f"SPLADE index loaded from {load_path} ({len(self.documents)} documents)")

    def clear(self):
        """Clear all documents from the index"""
        self.documents = []
        self.document_ids = []
        self.sparse_vectors = []
        self.metadata = []
        logger.info("SPLADE index cleared")

    def __len__(self) -> int:
        """Return number of documents in index"""
        return len(self.documents)

    def __repr__(self) -> str:
        return f"SPLADEModel(documents={len(self.documents)}, model={self.model_name})"


if __name__ == "__main__":
    # Test SPLADE Model
    logging.basicConfig(level=logging.INFO)

    # Create SPLADE model
    splade = SPLADEModel()

    # Add sample documents
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Python is a powerful programming language for data science",
        "Machine learning models require large datasets for training",
        "Natural language processing enables computers to understand human language",
        "Deep learning neural networks can solve complex problems"
    ]

    splade.add_documents(documents)

    # Search
    query = "machine learning training data"
    results = splade.search(query, top_k=3)

    print(f"\nSPLADE search results for: '{query}'")
    print("=" * 80)
    for result in results:
        print(f"Rank {result['rank']}: (score={result['score']:.4f})")
        print(f"  {result['text']}")
        print()
