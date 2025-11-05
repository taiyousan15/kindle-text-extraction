# Hybrid Search RAG System

A state-of-the-art Retrieval-Augmented Generation (RAG) system combining multiple search methods for optimal document retrieval.

## Features

### Multi-Method Retrieval

1. **BM25 Keyword Search**
   - Traditional probabilistic ranking
   - Excellent for exact keyword matching
   - Fast and efficient

2. **Dense Vector Search**
   - Semantic similarity using embeddings
   - Captures meaning beyond keywords
   - Powered by sentence-transformers

3. **SPLADE Hybrid Search** (Optional)
   - Combines sparse and dense representations
   - Term expansion for better coverage
   - Requires GPU for optimal performance

4. **Reciprocal Rank Fusion (RRF)**
   - Intelligently combines multiple result lists
   - Handles different score scales
   - Robust to outliers

### Advanced Features

- **Dynamic Alpha Adjustment**: Automatically balances sparse/dense search based on query characteristics
- **Performance Metrics**: Track search performance and method usage
- **Persistence**: Save and load indexes for production use
- **Batch Processing**: Efficient handling of large document collections

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Download NLTK data (first time only)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

## Quick Start

```python
from hybrid_search import HybridSearchRAG

# Initialize system (FAISS backend, no SPLADE)
rag = HybridSearchRAG(
    use_splade=False,
    vector_backend="faiss"
)

# Add documents
documents = [
    "Python is a powerful programming language",
    "Machine learning requires large datasets",
    "Natural language processing enables understanding"
]
rag.add_documents(documents)

# Search with different methods
results_bm25 = rag.search("machine learning", method="bm25", top_k=3)
results_dense = rag.search("machine learning", method="dense", top_k=3)
results_hybrid = rag.search("machine learning", method="hybrid", top_k=3)

# Print results
for result in results_hybrid:
    print(f"Rank {result['rank']}: {result['text']}")
    print(f"  Methods: {result['methods']}")
    print(f"  RRF Score: {result['rrf_score']:.4f}")
```

## Usage Examples

### Basic Search

```python
# BM25 (keyword search)
results = rag.search("machine learning", method="bm25", top_k=5)

# Dense vector (semantic search)
results = rag.search("understanding human language", method="dense", top_k=5)

# SPLADE (if enabled)
results = rag.search("neural networks", method="splade", top_k=5)

# Hybrid (recommended)
results = rag.search("how to train models", method="hybrid", top_k=5)
```

### Custom Alpha Weighting

```python
# More sparse (favor BM25 keyword matching)
results = rag.search("exact keyword match", method="hybrid", alpha=0.3, top_k=5)

# More dense (favor semantic similarity)
results = rag.search("What is the meaning?", method="hybrid", alpha=0.7, top_k=5)

# Balanced (default)
results = rag.search("general query", method="hybrid", alpha=0.5, top_k=5)
```

### Persistence

```python
# Save indexes
rag.save("/path/to/save/directory")

# Load indexes
rag.load("/path/to/save/directory")
```

### Performance Metrics

```python
# Get metrics
metrics = rag.get_metrics()
print(f"Total searches: {metrics['total_searches']}")
print(f"Average search time: {metrics['avg_search_time']:.3f}s")
print(f"Method usage: {metrics['method_usage']}")
```

## Architecture

```
HybridSearchRAG
├── BM25Index (keyword search)
│   ├── Tokenization (NLTK)
│   ├── BM25 scoring (rank-bm25)
│   └── Inverted index
├── VectorStore (semantic search)
│   ├── Embeddings (sentence-transformers)
│   ├── Vector storage (FAISS/ChromaDB)
│   └── Similarity search
├── SPLADEModel (hybrid search)
│   ├── Sparse vectors (transformers)
│   ├── Term expansion
│   └── Hybrid scoring
└── RRF Fusion
    ├── Reciprocal rank fusion
    ├── Weighted combination
    └── Dynamic alpha adjustment
```

## Component Details

### BM25Index

Traditional information retrieval using BM25 algorithm.

```python
from bm25_index import BM25Index

index = BM25Index(language="english", use_stopwords=True)
index.add_documents(documents)
results = index.search("query", top_k=10)
```

### VectorStore

Dense vector search with multiple backends.

```python
from vector_store import VectorStore

# FAISS backend (fast, in-memory)
store = VectorStore(backend="faiss")

# ChromaDB backend (persistent, feature-rich)
store = VectorStore(
    backend="chromadb",
    persist_directory="/path/to/persist"
)

store.add_documents(documents)
results = store.search("query", top_k=10)
```

### SPLADEModel

Hybrid sparse-dense retrieval.

```python
from splade_model import SPLADEModel

model = SPLADEModel(use_gpu=False)
model.add_documents(documents)
results = model.search("query", top_k=10)
```

### RRF Fusion

Combine results from multiple methods.

```python
from rrf_fusion import ReciprocalRankFusion

rrf = ReciprocalRankFusion(k=60)

# Fuse multiple result lists
fused = rrf.fuse([bm25_results, dense_results, splade_results])

# Weighted fusion for sparse/dense
fused = rrf.fuse_weighted([sparse_results, dense_results], alpha=0.5)
```

## Testing

Run comprehensive test suite:

```bash
# Run all tests
pytest test_hybrid_search.py -v

# Run with coverage
pytest test_hybrid_search.py --cov=. --cov-report=html

# Run specific test class
pytest test_hybrid_search.py::TestHybridSearchRAG -v
```

## Integration with Blackboard

The RAG system is registered as an agent in the T-Max Work3 Blackboard:

```python
from blackboard.state_manager import AgentType, get_blackboard

# Register RAG agent
blackboard = get_blackboard()
blackboard.register_agent(AgentType.RAG)

# Create RAG task
blackboard.add_task(
    task_id="rag-001",
    name="Index documents and enable search",
    agent=AgentType.RAG,
    priority=5
)
```

## Performance Considerations

### Memory Usage

- **BM25**: Low memory (tokenized documents only)
- **Vector Store**: Medium-High (embeddings stored)
- **SPLADE**: Medium (sparse vectors)

### Speed

- **BM25**: Very fast (< 10ms for 10k documents)
- **FAISS**: Fast (< 50ms for 10k documents)
- **ChromaDB**: Medium (< 100ms for 10k documents)
- **SPLADE**: Slower (GPU recommended)

### Recommendations

- Use FAISS for speed, ChromaDB for persistence
- Disable SPLADE if no GPU available
- Use batch_size=100-1000 for large collections
- Consider alpha=0.3-0.4 for keyword-heavy domains
- Consider alpha=0.6-0.7 for semantic-heavy domains

## Advanced Configuration

### Custom Embedding Model

```python
rag = HybridSearchRAG(
    embedding_model="sentence-transformers/all-mpnet-base-v2",  # Better quality
    vector_backend="faiss"
)
```

### GPU Acceleration

```python
rag = HybridSearchRAG(
    use_splade=True,
    use_gpu=True,  # Requires CUDA
    splade_model="naver/splade-cocondenser-ensembledistil"
)
```

### Custom RRF Parameter

```python
rag = HybridSearchRAG(
    rrf_k=30  # Lower k = more weight to top results
)
```

## Troubleshooting

### Issue: Slow first search

**Solution**: First search loads models into memory. Subsequent searches are faster.

### Issue: Out of memory

**Solution**: Use FAISS backend, reduce batch_size, or disable SPLADE.

### Issue: Poor semantic search quality

**Solution**: Try a larger embedding model like `all-mpnet-base-v2`.

### Issue: SPLADE not working

**Solution**: Ensure transformers and torch are installed. Consider GPU.

## References

- BM25: Robertson & Zaragoza (2009)
- Sentence-Transformers: Reimers & Gurevych (2019)
- SPLADE: Formal et al. (2021)
- RRF: Cormack et al. (2009)

## License

Part of T-Max Work3 project.

## Support

For issues or questions, please refer to the main T-Max Work3 documentation.
