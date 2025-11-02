# RAG Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or install RAG-specific packages only:
pip install langchain==0.0.340 \
            langchain-anthropic==0.0.2 \
            langchain-openai==0.0.2 \
            sentence-transformers==2.2.2 \
            anthropic==0.7.4 \
            openai==1.3.7
```

### Step 2: Configure API Keys (Optional)

Create or edit `.env` file:

```bash
# Optional - System works without these (uses mock mode)
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...

# Required
DATABASE_URL=postgresql://kindle_user:kindle_password@localhost:5432/kindle_ocr
```

### Step 3: Verify Installation

```bash
# Test imports
python3 -c "
from app.services.llm_service import get_llm_service
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import VectorStore
print('✓ All RAG components loaded successfully!')
"
```

### Step 4: Run Tests

```bash
# Run all RAG tests
pytest test_rag.py -v

# Run specific test
pytest test_rag.py::test_embedding_service_initialization -v
```

### Step 5: Start API Server

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API docs available at: http://localhost:8000/docs
```

## 📋 API Quick Reference

### 1. Index Documents (Upload File)

```bash
curl -X POST "http://localhost:8000/api/v1/rag/index/upload" \
  -F "file=@document.txt" \
  -F "tags=python,tutorial" \
  -F "chunk_size=500"
```

**Response:**
```json
{
  "file_id": 1,
  "filename": "document.txt",
  "indexed_count": 10,
  "status": "success"
}
```

### 2. RAG Query (Search + LLM Answer)

```bash
curl -X POST "http://localhost:8000/api/v1/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Pythonの特徴は？",
    "top_k": 5,
    "provider": "anthropic"
  }'
```

**Response:**
```json
{
  "answer": "Pythonは高水準プログラミング言語で...",
  "sources": [
    {
      "id": 123,
      "content": "Python is...",
      "similarity": 0.92,
      "filename": "python_intro.pdf"
    }
  ],
  "model": "claude-3-sonnet-20240229",
  "processing_time": 2.5
}
```

### 3. Search Only (No LLM)

```bash
curl -X POST "http://localhost:8000/api/v1/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "top_k": 5
  }'
```

### 4. Get Statistics

```bash
curl http://localhost:8000/api/v1/rag/stats
```

**Response:**
```json
{
  "total_documents": 100,
  "total_files": 10,
  "documents_with_embeddings": 95,
  "embedding_coverage": 0.95
}
```

## 💡 Python Usage Examples

### Example 1: Basic RAG Query

```python
from app.core.database import SessionLocal
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStore

# Initialize
db = SessionLocal()
llm = get_llm_service(provider="anthropic")
vector_store = VectorStore(db)

# Search similar documents
results = vector_store.similarity_search("What is Python?", k=3)

# Generate answer with context
context_docs = [r["content"] for r in results]
answer = llm.generate_with_context(
    query="What is Python?",
    context_documents=context_docs
)

print(f"Answer: {answer['content']}")
print(f"Sources: {len(results)} documents")
```

### Example 2: Index New Documents

```python
from app.core.database import SessionLocal
from app.services.vector_store import VectorStore
from app.models.biz_file import BizFile

db = SessionLocal()
vector_store = VectorStore(db)

# Create file
biz_file = BizFile(
    filename="python_guide.txt",
    file_blob=b"Python is a programming language...",
    file_size=1000,
    mime_type="text/plain"
)
db.add(biz_file)
db.commit()

# Index documents
documents = [
    "Python is a high-level programming language.",
    "Python is easy to read and write.",
    "Python is used for machine learning."
]

biz_cards = vector_store.add_documents(
    documents=documents,
    file_id=biz_file.id
)

print(f"Indexed {len(biz_cards)} documents")
```

### Example 3: Custom Embedding Search

```python
from app.services.embedding_service import get_embedding_service

embedding_service = get_embedding_service()

# Find most similar texts
query = "機械学習について"
candidates = [
    "Python is a programming language.",
    "機械学習はAIの一分野です。",
    "I like cats.",
    "ディープラーニングは機械学習の手法です。"
]

results = embedding_service.most_similar(query, candidates, top_k=2)

for result in results:
    print(f"{result['text']}: {result['score']:.4f}")
```

## 🔧 Configuration Options

### LLM Provider

```python
# Use Claude (default)
llm = LLMService(provider="anthropic", temperature=0.7)

# Use GPT-4
llm = LLMService(provider="openai", model="gpt-4-turbo-preview")
```

### Embedding Model

```python
# Multilingual (default) - 384 dimensions
embedding_service = EmbeddingService(model_name="multilingual-e5-large")

# Japanese-specific - 768 dimensions
embedding_service = EmbeddingService(model_name="japanese-bert")
```

### Search Parameters

```python
# Adjust similarity threshold
results = vector_store.similarity_search(
    query="Python",
    k=10,                    # Top 10 results
    score_threshold=0.7,     # Minimum similarity: 0.7
    file_ids=[1, 2, 3]      # Search specific files only
)
```

## 📊 API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/rag/query` | RAG query with LLM generation |
| POST | `/api/v1/rag/index` | Index existing file |
| POST | `/api/v1/rag/index/upload` | Upload & index file |
| POST | `/api/v1/rag/search` | Vector search only (no LLM) |
| GET | `/api/v1/rag/stats` | Vector store statistics |

## 🐛 Troubleshooting

### Problem: "No module named 'langchain_anthropic'"

**Solution:**
```bash
pip install langchain-anthropic langchain-openai
```

### Problem: "No module named 'sentence_transformers'"

**Solution:**
```bash
pip install sentence-transformers
```

### Problem: LLM returns "[MOCK RESPONSE]"

**Reason:** API keys not configured (this is expected behavior)

**Solution (optional):**
1. Get API key from https://console.anthropic.com/
2. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
3. Restart server

**Note:** Mock mode allows testing without API costs!

### Problem: Search returns empty results

**Solution:**
```bash
# 1. Check if documents are indexed
curl http://localhost:8000/api/v1/rag/stats

# 2. Index some documents first
curl -X POST "http://localhost:8000/api/v1/rag/index/upload" \
  -F "file=@test.txt"

# 3. Try search again
```

### Problem: pgvector operator not found

**Solution:**
```sql
-- Connect to PostgreSQL
psql -U kindle_user -d kindle_ocr

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
```

## 🎯 Common Use Cases

### Use Case 1: Document Q&A System

```python
# 1. Upload documents
for file in ["doc1.txt", "doc2.txt"]:
    upload_and_index(file)

# 2. Query
answer = rag_query("What are the key points?")
print(answer)
```

### Use Case 2: Semantic Search

```python
# Search without LLM (faster, cheaper)
results = vector_store.similarity_search(
    query="Python tutorial",
    k=5
)

for result in results:
    print(f"{result['filename']}: {result['content'][:100]}")
```

### Use Case 3: Multi-language Support

```python
# Works with Japanese, English, Chinese, etc.
query_ja = "Pythonの特徴は？"
query_en = "What are Python's features?"

# Same embedding model handles both
results_ja = vector_store.similarity_search(query_ja)
results_en = vector_store.similarity_search(query_en)
```

## 📝 Notes

- **Mock Mode**: System works without API keys (uses mock responses)
- **First Run**: Embedding model auto-downloads (~500MB)
- **Cost**: Vector search is free, LLM generation costs tokens
- **Performance**: Embedding caching speeds up repeated queries
- **Scalability**: Handles 100K+ documents efficiently with pgvector

## 🚀 Next Steps

1. **Test with your data**: Upload your documents and try queries
2. **Configure API keys**: For production LLM responses
3. **Tune parameters**: Adjust chunk_size, top_k, temperature
4. **Monitor usage**: Check `/rag/stats` for system health
5. **Explore docs**: Read full docs at `http://localhost:8000/docs`

## 📚 More Information

- Full documentation: See `RAG_IMPLEMENTATION.md`
- Test suite: Run `pytest test_rag.py -v`
- API docs: http://localhost:8000/docs
- Models: https://huggingface.co/sentence-transformers

---

**Quick Test:**
```bash
# Start server
uvicorn app.main:app --reload

# In another terminal, test endpoint
curl http://localhost:8000/api/v1/rag/stats
```

If you see statistics (even if zeros), RAG is working! 🎉
