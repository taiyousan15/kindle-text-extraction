"""
BM25 Index Module for Hybrid Search RAG System
Provides keyword-based retrieval using BM25 algorithm
"""
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)


class BM25Index:
    """
    BM25 Keyword Search Index

    Implements BM25 (Best Matching 25) algorithm for keyword-based document retrieval.
    BM25 is a probabilistic ranking function that considers:
    - Term frequency (TF)
    - Inverse document frequency (IDF)
    - Document length normalization
    """

    def __init__(
        self,
        language: str = "english",
        use_stopwords: bool = True,
        lowercase: bool = True
    ):
        """
        Initialize BM25 Index

        Args:
            language: Language for tokenization and stopwords
            use_stopwords: Whether to remove stopwords
            lowercase: Whether to lowercase text
        """
        self.language = language
        self.use_stopwords = use_stopwords
        self.lowercase = lowercase

        # Download required NLTK data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)

        if self.use_stopwords:
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            self.stop_words = set(stopwords.words(language))
        else:
            self.stop_words = set()

        # Index state
        self.bm25: Optional[BM25Okapi] = None
        self.documents: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.document_ids: List[str] = []
        self.metadata: List[Dict] = []

        logger.info(f"BM25Index initialized (language={language}, use_stopwords={use_stopwords})")

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text with preprocessing

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Lowercase
        if self.lowercase:
            text = text.lower()

        # Tokenize
        tokens = word_tokenize(text, language=self.language)

        # Remove stopwords
        if self.use_stopwords:
            tokens = [t for t in tokens if t not in self.stop_words and len(t) > 2]

        return tokens

    def add_documents(
        self,
        documents: List[str],
        document_ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict]] = None
    ):
        """
        Add documents to the index

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

        # Tokenize documents
        tokenized_docs = [self.tokenize(doc) for doc in documents]

        # Add to corpus
        self.documents.extend(documents)
        self.document_ids.extend(document_ids)
        self.tokenized_corpus.extend(tokenized_docs)
        self.metadata.extend(metadata)

        # Rebuild BM25 index
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        logger.info(f"Added {len(documents)} documents to BM25 index (total: {len(self.documents)})")

    def search(
        self,
        query: str,
        top_k: int = 10,
        return_scores: bool = True
    ) -> List[Dict]:
        """
        Search documents using BM25

        Args:
            query: Search query
            top_k: Number of results to return
            return_scores: Whether to return BM25 scores

        Returns:
            List of result dictionaries with document info and scores
        """
        if self.bm25 is None:
            logger.warning("BM25 index is empty")
            return []

        # Tokenize query
        tokenized_query = self.tokenize(query)

        if not tokenized_query:
            logger.warning(f"Query tokenization resulted in empty tokens: {query}")
            return []

        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)

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
                "method": "bm25"
            }

            if return_scores:
                result["score"] = float(scores[idx])

            results.append(result)

        logger.debug(f"BM25 search for '{query}' returned {len(results)} results")
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
        Save index to disk

        Args:
            path: File path to save
        """
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "documents": self.documents,
            "document_ids": self.document_ids,
            "tokenized_corpus": self.tokenized_corpus,
            "metadata": self.metadata,
            "language": self.language,
            "use_stopwords": self.use_stopwords,
            "lowercase": self.lowercase
        }

        with open(save_path, 'wb') as f:
            pickle.dump(state, f)

        logger.info(f"BM25 index saved to {save_path}")

    def load(self, path: str):
        """
        Load index from disk

        Args:
            path: File path to load
        """
        load_path = Path(path)

        if not load_path.exists():
            raise FileNotFoundError(f"Index file not found: {load_path}")

        with open(load_path, 'rb') as f:
            state = pickle.load(f)

        self.documents = state["documents"]
        self.document_ids = state["document_ids"]
        self.tokenized_corpus = state["tokenized_corpus"]
        self.metadata = state["metadata"]
        self.language = state["language"]
        self.use_stopwords = state["use_stopwords"]
        self.lowercase = state["lowercase"]

        # Rebuild BM25
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)

        logger.info(f"BM25 index loaded from {load_path} ({len(self.documents)} documents)")

    def clear(self):
        """Clear all documents from the index"""
        self.bm25 = None
        self.documents = []
        self.tokenized_corpus = []
        self.document_ids = []
        self.metadata = []
        logger.info("BM25 index cleared")

    def __len__(self) -> int:
        """Return number of documents in index"""
        return len(self.documents)

    def __repr__(self) -> str:
        return f"BM25Index(documents={len(self.documents)}, language={self.language})"


if __name__ == "__main__":
    # Test BM25 Index
    logging.basicConfig(level=logging.INFO)

    # Create index
    bm25_index = BM25Index()

    # Add sample documents
    documents = [
        "The quick brown fox jumps over the lazy dog",
        "Python is a powerful programming language for data science",
        "Machine learning models require large datasets for training",
        "Natural language processing enables computers to understand human language",
        "Deep learning neural networks can solve complex problems"
    ]

    bm25_index.add_documents(documents)

    # Search
    query = "machine learning training data"
    results = bm25_index.search(query, top_k=3)

    print(f"\nSearch results for: '{query}'")
    print("=" * 80)
    for result in results:
        print(f"Rank {result['rank']}: (score={result['score']:.4f})")
        print(f"  {result['text']}")
        print()
