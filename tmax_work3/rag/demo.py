"""
Hybrid Search RAG System - Interactive Demo
Demonstrates all search methods with real examples
"""
import logging
from hybrid_search import HybridSearchRAG

logging.basicConfig(level=logging.WARNING)  # Reduce noise

print("=" * 80)
print("Hybrid Search RAG System - Interactive Demo")
print("=" * 80)

# Sample knowledge base
documents = [
    "Python is a high-level, interpreted programming language known for its simplicity and readability",
    "Machine learning is a subset of artificial intelligence that enables systems to learn from data",
    "Deep learning neural networks use multiple layers to progressively extract higher-level features",
    "Natural language processing allows computers to understand, interpret and generate human language",
    "Data science combines statistics, programming, and domain knowledge to extract insights from data",
    "TensorFlow is an open-source machine learning framework developed by Google",
    "PyTorch is a deep learning framework known for its dynamic computation graph",
    "BERT is a transformer-based model that has revolutionized NLP tasks",
    "GPT models use transformer architecture for text generation and understanding",
    "Vector embeddings represent words or documents as dense vectors in continuous space",
    "The transformer architecture uses self-attention mechanisms for sequence processing",
    "Supervised learning requires labeled training data to learn input-output mappings",
    "Unsupervised learning finds patterns in data without explicit labels",
    "Reinforcement learning trains agents through rewards and penalties",
    "Convolutional neural networks excel at processing grid-like data such as images",
    "Recurrent neural networks are designed to process sequential data",
    "Attention mechanisms allow models to focus on relevant parts of input",
    "Transfer learning reuses pre-trained models for new but related tasks",
    "Fine-tuning adapts pre-trained models to specific downstream tasks",
    "Large language models have billions of parameters trained on massive text corpora"
]

print("\nInitializing Hybrid Search RAG system...")
print("-" * 80)

# Initialize system (disable SPLADE for faster demo)
rag = HybridSearchRAG(
    use_splade=False,
    vector_backend="faiss",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)

print("✓ System initialized")
print(f"  - BM25 Index ready")
print(f"  - Vector Store (FAISS) ready")
print(f"  - RRF Fusion ready")

# Add documents
print("\nIndexing knowledge base...")
print("-" * 80)
rag.add_documents(documents)
print(f"✓ Indexed {len(documents)} documents")

# Demo queries
demo_queries = [
    {
        "query": "machine learning training data",
        "description": "Keyword-focused query"
    },
    {
        "query": "How do neural networks learn?",
        "description": "Natural language question"
    },
    {
        "query": "transformer attention mechanism",
        "description": "Technical terms"
    }
]

print("\n" + "=" * 80)
print("DEMONSTRATION: Comparing Search Methods")
print("=" * 80)

for demo in demo_queries:
    query = demo["query"]
    description = demo["description"]

    print(f"\nQuery: \"{query}\"")
    print(f"Type: {description}")
    print("-" * 80)

    # BM25 Search
    print("\n1. BM25 (Keyword Search)")
    bm25_results = rag.search(query, method="bm25", top_k=3)
    for i, result in enumerate(bm25_results, 1):
        print(f"   {i}. [{result['score']:.3f}] {result['text'][:70]}...")

    # Dense Vector Search
    print("\n2. Dense Vector (Semantic Search)")
    dense_results = rag.search(query, method="dense", top_k=3)
    for i, result in enumerate(dense_results, 1):
        print(f"   {i}. [{result['score']:.3f}] {result['text'][:70]}...")

    # Hybrid Search (Recommended)
    print("\n3. Hybrid (RRF Fusion) - RECOMMENDED")
    hybrid_results = rag.search(query, method="hybrid", top_k=3)
    for i, result in enumerate(hybrid_results, 1):
        methods_str = '+'.join(result['methods'])
        print(f"   {i}. [{result['rrf_score']:.4f}] [{methods_str}]")
        print(f"       {result['text'][:70]}...")

    # Show detected alpha
    alpha = rag._detect_optimal_alpha(query)
    print(f"\n   Auto-detected alpha: {alpha:.2f} ", end="")
    if alpha < 0.4:
        print("(favors keyword matching)")
    elif alpha > 0.6:
        print("(favors semantic similarity)")
    else:
        print("(balanced)")

    print()

# Performance metrics
print("\n" + "=" * 80)
print("PERFORMANCE METRICS")
print("=" * 80)
metrics = rag.get_metrics()
print(f"Total searches performed: {metrics['total_searches']}")
print(f"Average search time: {metrics['avg_search_time']*1000:.1f}ms")
print(f"\nMethod usage:")
for method, count in metrics['method_usage'].items():
    if count > 0:
        print(f"  - {method}: {count} searches")

# Advanced features demo
print("\n" + "=" * 80)
print("ADVANCED FEATURES")
print("=" * 80)

print("\n1. Custom Alpha Weighting")
print("-" * 80)
query = "python programming"
print(f"Query: \"{query}\"")

for alpha, description in [(0.2, "Heavy keyword"), (0.5, "Balanced"), (0.8, "Heavy semantic")]:
    results = rag.search(query, method="hybrid", alpha=alpha, top_k=1)
    print(f"  Alpha={alpha} ({description}): {results[0]['text'][:60]}...")

print("\n2. Result Diversity Analysis")
print("-" * 80)
hybrid_results = rag.search("deep learning models", method="hybrid", top_k=5)
multi_method = sum(1 for r in hybrid_results if len(r['methods']) > 1)
print(f"  Top-5 results:")
print(f"    - Found by multiple methods: {multi_method}/5")
print(f"    - Unique methods used: {len(set(m for r in hybrid_results for m in r['methods']))}")

# Interactive mode
print("\n" + "=" * 80)
print("INTERACTIVE MODE")
print("=" * 80)
print("\nTry your own queries! (type 'quit' to exit)")
print("-" * 80)

while True:
    try:
        user_query = input("\nYour query: ").strip()

        if user_query.lower() in ['quit', 'exit', 'q']:
            break

        if not user_query:
            continue

        # Perform hybrid search
        results = rag.search(user_query, method="hybrid", top_k=5)

        print(f"\nTop {len(results)} results:")
        for i, result in enumerate(results, 1):
            methods_str = '+'.join(result['methods'])
            print(f"\n{i}. [{methods_str}] (RRF: {result['rrf_score']:.4f})")
            print(f"   {result['text']}")

        # Show alpha
        alpha = rag._detect_optimal_alpha(user_query)
        print(f"\n   (Auto-detected alpha: {alpha:.2f})")

    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 80)
print("Demo completed!")
print("=" * 80)
print("\nKey Takeaways:")
print("  1. BM25 excels at keyword matching")
print("  2. Dense vectors capture semantic meaning")
print("  3. Hybrid (RRF) combines strengths of both methods")
print("  4. Dynamic alpha adjustment optimizes for query type")
print("\nFor more information, see README.md")
print("=" * 80)
