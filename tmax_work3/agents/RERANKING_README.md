# Reranking Agent - Complete Documentation

## Overview

The **Reranking Agent** is an advanced search result optimization system that improves the quality and relevance of search results using state-of-the-art reranking techniques.

### Key Features

- **Cross-Encoder Reranking**: Uses sentence-transformers cross-encoder models for semantic relevance scoring
- **LLM-based Reranking**: Leverages Claude API for intelligent result reordering
- **Hybrid Approach**: Combines Cross-Encoder and LLM methods for optimal performance
- **Confidence Scoring**: Assigns confidence scores to indicate result quality
- **Top-k Selection**: Filters and returns only the most relevant results
- **Blackboard Integration**: Full integration with T-Max Work3 state management system
- **Performance Metrics**: Tracks and logs reranking performance and improvements

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Reranking Agent                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Input: Search Results (from Hybrid Search/RAG)    │
│         ↓                                           │
│  ┌─────────────────────────────────────┐           │
│  │  Cross-Encoder Reranking            │           │
│  │  - Semantic similarity scoring      │           │
│  │  - Fast batch processing            │           │
│  └─────────────────────────────────────┘           │
│         ↓                                           │
│  ┌─────────────────────────────────────┐           │
│  │  LLM-based Reranking (Optional)     │           │
│  │  - Deep semantic understanding      │           │
│  │  - Context-aware ranking            │           │
│  └─────────────────────────────────────┘           │
│         ↓                                           │
│  ┌─────────────────────────────────────┐           │
│  │  Score Aggregation                  │           │
│  │  - Weighted combination             │           │
│  │  - Confidence calculation           │           │
│  └─────────────────────────────────────┘           │
│         ↓                                           │
│  ┌─────────────────────────────────────┐           │
│  │  Filtering & Selection              │           │
│  │  - Top-k selection                  │           │
│  │  - Confidence threshold             │           │
│  └─────────────────────────────────────┘           │
│         ↓                                           │
│  Output: Optimized Results + Confidence Scores     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Installation

### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Specifically for reranking:
pip install sentence-transformers==2.2.2
pip install transformers==4.35.2
pip install torch==2.1.1
pip install anthropic==0.7.4
```

### 2. Environment Setup

Set up your Anthropic API key for LLM-based reranking:

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```

Or create a `.env` file:

```bash
ANTHROPIC_API_KEY=your_api_key_here
```

---

## Usage

### Basic Usage

```python
from tmax_work3.agents.reranking import RerankingAgent, SearchResult

# Initialize agent
agent = RerankingAgent(
    repository_path=".",
    top_k=10,
    confidence_threshold=0.5
)

# Prepare search results
results = [
    SearchResult(
        doc_id="doc1",
        content="Machine learning is a subset of AI...",
        original_score=0.85,
        metadata={"source": "textbook"}
    ),
    SearchResult(
        doc_id="doc2",
        content="Deep learning uses neural networks...",
        original_score=0.78,
        metadata={"source": "research"}
    ),
    # ... more results
]

# Rerank using Cross-Encoder
reranked = agent.rerank(
    query="What is machine learning?",
    results=results,
    method="cross_encoder"
)

# Access results
for result in reranked:
    print(f"Doc: {result.doc_id}")
    print(f"Score: {result.rerank_score:.4f}")
    print(f"Confidence: {result.confidence:.4f}")
    print(f"Method: {result.method}")
```

### Advanced Usage - LLM Reranking

```python
# Initialize with LLM support
agent = RerankingAgent(
    repository_path=".",
    use_llm=True,
    llm_model="claude-3-haiku-20240307",
    anthropic_api_key="your_key"
)

# Rerank using Claude
reranked = agent.rerank(
    query="Explain deep learning architecture",
    results=results,
    method="llm"
)
```

### Hybrid Reranking (Recommended for Best Quality)

```python
# Hybrid approach combines CE and LLM
agent = RerankingAgent(
    repository_path=".",
    use_llm=True,
    top_k=10,
    confidence_threshold=0.7
)

# Best of both worlds
reranked = agent.rerank(
    query="What is the difference between ML and DL?",
    results=results,
    method="hybrid"
)
```

---

## Configuration Options

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repository_path` | str | "." | Path to repository root |
| `cross_encoder_model` | str | "cross-encoder/ms-marco-MiniLM-L-6-v2" | HuggingFace cross-encoder model |
| `anthropic_api_key` | str | None | Anthropic API key (optional) |
| `use_llm` | bool | False | Enable LLM-based reranking |
| `llm_model` | str | "claude-3-haiku-20240307" | Claude model for LLM reranking |
| `top_k` | int | 10 | Number of top results to return |
| `confidence_threshold` | float | 0.5 | Minimum confidence score for results |

### Reranking Methods

1. **cross_encoder** (Fast, Good Quality)
   - Uses cross-encoder transformer models
   - Best for: Real-time applications, large result sets
   - Speed: ~100ms for 50 results
   - Quality: High semantic relevance

2. **llm** (Slower, Highest Quality)
   - Uses Claude API for deep understanding
   - Best for: Complex queries, small result sets
   - Speed: ~1-2s per API call
   - Quality: Highest contextual understanding

3. **hybrid** (Balanced, Recommended)
   - Combines CE (70%) + LLM (30%)
   - Best for: Production use, critical queries
   - Speed: ~1-2s (CE + LLM for top-20)
   - Quality: Optimal balance

---

## API Reference

### RerankingAgent Class

#### Methods

##### `rerank(query, results, method)`

Rerank search results.

**Parameters:**
- `query` (str): Search query
- `results` (List[SearchResult]): Results to rerank
- `method` (str): Reranking method ("cross_encoder", "llm", "hybrid")

**Returns:**
- `List[RerankedResult]`: Reranked results with confidence scores

**Example:**
```python
reranked = agent.rerank(
    query="machine learning",
    results=search_results,
    method="cross_encoder"
)
```

---

### Data Structures

#### SearchResult

Input data structure for search results.

```python
@dataclass
class SearchResult:
    doc_id: str                      # Unique document ID
    content: str                     # Document content/text
    original_score: float            # Original search score
    metadata: Optional[Dict] = None  # Additional metadata
```

#### RerankedResult

Output data structure with reranking scores.

```python
@dataclass
class RerankedResult:
    doc_id: str                      # Document ID
    content: str                     # Document content
    original_score: float            # Original score
    rerank_score: float              # New reranked score
    confidence: float                # Confidence score (0-1)
    method: str                      # Reranking method used
    metadata: Optional[Dict] = None  # Metadata
```

---

## Performance Benchmarks

### Cross-Encoder Performance

| Result Count | Processing Time | Throughput |
|--------------|-----------------|------------|
| 10 results   | ~50ms          | 200 QPS    |
| 50 results   | ~100ms         | 100 QPS    |
| 100 results  | ~200ms         | 50 QPS     |

### LLM Performance

| Result Count | Processing Time | Cost/Query |
|--------------|-----------------|------------|
| 10 results   | ~1.5s          | $0.001     |
| 20 results   | ~2.0s          | $0.002     |
| 50 results   | ~3.0s          | $0.005     |

### Hybrid Performance

Hybrid mode processes:
- All results with Cross-Encoder (~100ms)
- Top-20 with LLM (~2s)
- Total: ~2.1s for optimal quality

---

## Integration Examples

### With Hybrid Search

```python
from hybrid_search import HybridSearchAgent
from tmax_work3.agents.reranking import RerankingAgent

# Step 1: Perform hybrid search
search_agent = HybridSearchAgent()
search_results = search_agent.search(
    query="What is quantum computing?",
    top_k=50
)

# Step 2: Rerank results
rerank_agent = RerankingAgent(top_k=10)
final_results = rerank_agent.rerank(
    query="What is quantum computing?",
    results=search_results,
    method="hybrid"
)

# Step 3: Use top results
for result in final_results[:5]:
    print(f"Score: {result.rerank_score:.4f} - {result.content[:100]}")
```

### With RAG Pipeline

```python
from langchain.vectorstores import FAISS
from tmax_work3.agents.reranking import RerankingAgent, SearchResult

# Step 1: Vector search
vectorstore = FAISS.load_local("./vectorstore")
docs = vectorstore.similarity_search_with_score(
    query="Explain transformers",
    k=50
)

# Step 2: Convert to SearchResult format
search_results = [
    SearchResult(
        doc_id=f"doc_{i}",
        content=doc.page_content,
        original_score=score,
        metadata=doc.metadata
    )
    for i, (doc, score) in enumerate(docs)
]

# Step 3: Rerank
agent = RerankingAgent(use_llm=True)
reranked = agent.rerank(
    query="Explain transformers",
    results=search_results,
    method="hybrid"
)

# Step 4: Use for LLM context
context = "\n\n".join([r.content for r in reranked[:3]])
```

---

## Metrics and Monitoring

### Automatic Metrics

The agent automatically tracks:

- **Query metrics**: Query text, timestamp
- **Performance**: Processing time, result counts
- **Quality**: Average confidence, score improvements
- **Method usage**: Which reranking method was used

### Accessing Metrics

```python
# Get all metrics
metrics = agent.blackboard.get_metrics()
reranking_metrics = metrics.get("reranking", {})

# Example metric structure:
{
    "timestamp": "2025-11-05T20:00:00",
    "query": "machine learning",
    "method": "hybrid",
    "original_count": 50,
    "reranked_count": 50,
    "filtered_count": 10,
    "avg_confidence": 0.85,
    "score_improvement": 0.12
}
```

### Saved Results

Results are automatically saved to:
```
tmax_work3/data/reranking/reranking_YYYYMMDD_HHMMSS.json
```

---

## Testing

### Run Full Test Suite

```bash
# Run all tests
pytest tests/test_reranking_agent.py -v

# Run specific test class
pytest tests/test_reranking_agent.py::TestCrossEncoderReranking -v

# Run with coverage
pytest tests/test_reranking_agent.py --cov=tmax_work3.agents.reranking
```

### Test Coverage

Current test coverage: **27 test cases** covering:

- ✅ Agent initialization
- ✅ Cross-Encoder reranking
- ✅ LLM-based reranking
- ✅ Hybrid reranking
- ✅ Confidence scoring
- ✅ Top-k filtering
- ✅ Confidence threshold filtering
- ✅ Metrics recording
- ✅ Error handling
- ✅ Edge cases
- ✅ Performance with large datasets
- ✅ Blackboard integration

---

## Best Practices

### 1. Choose the Right Method

- **Cross-Encoder**: For real-time applications, large result sets
- **LLM**: For complex queries, when quality > speed
- **Hybrid**: For production use, balanced approach

### 2. Optimize Top-K and Threshold

```python
# For high-quality applications
agent = RerankingAgent(
    top_k=10,
    confidence_threshold=0.8  # Only high-confidence results
)

# For broad coverage
agent = RerankingAgent(
    top_k=20,
    confidence_threshold=0.5  # More results, lower bar
)
```

### 3. Use Caching for Repeated Queries

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_rerank(query, method="cross_encoder"):
    return agent.rerank(query, results, method)
```

### 4. Monitor Performance

```python
import time

start = time.time()
results = agent.rerank(query, search_results, method="hybrid")
elapsed = time.time() - start

print(f"Reranking took {elapsed:.2f}s")
if elapsed > 3.0:
    print("⚠️ Consider using cross_encoder for faster results")
```

---

## Troubleshooting

### Common Issues

#### 1. Cross-Encoder Model Download

**Problem**: First run downloads model (~80MB)

**Solution**: Pre-download the model:
```python
from sentence_transformers import CrossEncoder
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
```

#### 2. LLM API Errors

**Problem**: `ANTHROPIC_API_KEY not found`

**Solution**:
```bash
export ANTHROPIC_API_KEY="your_key_here"
```

#### 3. Memory Issues with Large Result Sets

**Problem**: Out of memory with 1000+ results

**Solution**: Use batch processing:
```python
# Process in batches of 100
batch_size = 100
for i in range(0, len(results), batch_size):
    batch = results[i:i+batch_size]
    reranked_batch = agent.rerank(query, batch, method="cross_encoder")
```

#### 4. Low Confidence Scores

**Problem**: All results have low confidence

**Solution**: Check query-document relevance or lower threshold:
```python
agent = RerankingAgent(confidence_threshold=0.3)
```

---

## Advanced Topics

### Custom Cross-Encoder Models

```python
# Use a different cross-encoder model
agent = RerankingAgent(
    cross_encoder_model="cross-encoder/ms-marco-TinyBERT-L-2-v2"  # Faster
    # or
    cross_encoder_model="cross-encoder/ms-marco-electra-base"      # More accurate
)
```

### Custom Confidence Calculation

```python
class CustomRerankingAgent(RerankingAgent):
    def _calculate_confidence(self, score: float, method: str) -> float:
        # Custom confidence logic
        if method == "cross_encoder":
            # Custom normalization
            return min(max(score / 10.0, 0), 1)
        return super()._calculate_confidence(score, method)
```

### Batch Reranking

```python
def batch_rerank(queries, results_per_query):
    agent = RerankingAgent()

    all_reranked = {}
    for query, results in zip(queries, results_per_query):
        reranked = agent.rerank(query, results, method="cross_encoder")
        all_reranked[query] = reranked

    return all_reranked
```

---

## Contributing

To contribute improvements to the Reranking Agent:

1. Add tests in `tests/test_reranking_agent.py`
2. Update this documentation
3. Run test suite: `pytest tests/test_reranking_agent.py -v`
4. Submit PR with detailed description

---

## License

Part of T-Max Work3 autonomous agent system.

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review test cases for examples
- Check Blackboard logs for debugging

## Changelog

### v1.0.0 (2025-11-05)
- Initial release
- Cross-Encoder reranking
- LLM-based reranking (Claude)
- Hybrid approach
- Confidence scoring
- Blackboard integration
- Comprehensive test suite (27 tests)
