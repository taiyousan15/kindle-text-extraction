"""
Reranking Agent - Usage Examples

This file demonstrates various use cases of the Reranking Agent
for search result optimization.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.agents.reranking import RerankingAgent, SearchResult


def example_1_basic_cross_encoder():
    """
    Example 1: Basic Cross-Encoder Reranking

    Best for: Fast, real-time applications
    """
    print("\n" + "="*80)
    print("Example 1: Basic Cross-Encoder Reranking")
    print("="*80)

    # Initialize agent
    agent = RerankingAgent(
        repository_path=".",
        top_k=5,
        confidence_threshold=0.6
    )

    # Sample search results (e.g., from vector search)
    results = [
        SearchResult(
            doc_id="doc1",
            content="Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed.",
            original_score=0.75,
            metadata={"source": "textbook", "page": 42}
        ),
        SearchResult(
            doc_id="doc2",
            content="Deep learning is a type of machine learning that uses neural networks with multiple layers to analyze various factors of data.",
            original_score=0.82,
            metadata={"source": "research_paper", "year": 2024}
        ),
        SearchResult(
            doc_id="doc3",
            content="Python is a high-level programming language that is widely used in data science and machine learning applications.",
            original_score=0.68,
            metadata={"source": "tutorial"}
        ),
        SearchResult(
            doc_id="doc4",
            content="Natural language processing (NLP) uses machine learning algorithms to understand and generate human language.",
            original_score=0.71,
            metadata={"source": "article"}
        ),
        SearchResult(
            doc_id="doc5",
            content="Supervised learning is a type of machine learning where the model is trained on labeled data.",
            original_score=0.79,
            metadata={"source": "course"}
        ),
    ]

    # Perform reranking
    query = "What is machine learning and how does it work?"
    reranked = agent.rerank(
        query=query,
        results=results,
        method="cross_encoder"
    )

    # Display results
    print(f"\nQuery: {query}")
    print(f"\nTop {len(reranked)} Results (after reranking):\n")

    for i, result in enumerate(reranked, 1):
        print(f"{i}. Document: {result.doc_id}")
        print(f"   Original Score: {result.original_score:.4f}")
        print(f"   Rerank Score:   {result.rerank_score:.4f}")
        print(f"   Confidence:     {result.confidence:.4f}")
        print(f"   Improvement:    {result.rerank_score - result.original_score:+.4f}")
        print(f"   Content:        {result.content[:100]}...")
        print()


def example_2_llm_reranking():
    """
    Example 2: LLM-based Reranking with Claude

    Best for: Complex queries requiring deep understanding
    """
    print("\n" + "="*80)
    print("Example 2: LLM-based Reranking (requires ANTHROPIC_API_KEY)")
    print("="*80)

    # Initialize agent with LLM support
    agent = RerankingAgent(
        repository_path=".",
        use_llm=True,
        llm_model="claude-3-haiku-20240307",
        top_k=3
    )

    # Sample results for a complex query
    results = [
        SearchResult(
            doc_id="doc1",
            content="Gradient descent is an optimization algorithm used to minimize the loss function in machine learning by iteratively adjusting parameters.",
            original_score=0.70,
            metadata={"difficulty": "advanced"}
        ),
        SearchResult(
            doc_id="doc2",
            content="The backpropagation algorithm is used in neural networks to calculate gradients and update weights during training.",
            original_score=0.65,
            metadata={"difficulty": "advanced"}
        ),
        SearchResult(
            doc_id="doc3",
            content="A neural network learns by adjusting connection weights between neurons based on the error in its predictions.",
            original_score=0.80,
            metadata={"difficulty": "intermediate"}
        ),
    ]

    query = "How do neural networks learn and improve their predictions?"

    print(f"\nQuery: {query}")
    print(f"\nNote: This example requires ANTHROPIC_API_KEY to be set.")
    print("If not available, the agent will fall back to original scores.\n")

    try:
        reranked = agent.rerank(
            query=query,
            results=results,
            method="llm"
        )

        print(f"\nTop {len(reranked)} Results (LLM-reranked):\n")
        for i, result in enumerate(reranked, 1):
            print(f"{i}. {result.doc_id}: Score={result.rerank_score:.4f}, Confidence={result.confidence:.4f}")
            print(f"   {result.content[:120]}...")
            print()
    except Exception as e:
        print(f"❌ LLM reranking failed: {e}")
        print("Make sure ANTHROPIC_API_KEY is set in your environment.")


def example_3_hybrid_reranking():
    """
    Example 3: Hybrid Reranking (Cross-Encoder + LLM)

    Best for: Production use, optimal quality
    """
    print("\n" + "="*80)
    print("Example 3: Hybrid Reranking (CE + LLM)")
    print("="*80)

    # Initialize agent for hybrid mode
    agent = RerankingAgent(
        repository_path=".",
        use_llm=True,
        top_k=5,
        confidence_threshold=0.7
    )

    # Larger result set
    results = [
        SearchResult(
            doc_id=f"doc{i}",
            content=f"Document {i} about machine learning and artificial intelligence with various technical details.",
            original_score=0.5 + (i % 10) / 20,
            metadata={"index": i}
        )
        for i in range(1, 11)
    ]

    query = "Explain machine learning concepts"

    print(f"\nQuery: {query}")
    print(f"Input: {len(results)} results")
    print("\nProcessing:")
    print("  1. Cross-Encoder scores all results (~100ms)")
    print("  2. LLM reranks top-20 from CE (~2s)")
    print("  3. Combines scores (70% CE + 30% LLM)\n")

    try:
        reranked = agent.rerank(
            query=query,
            results=results,
            method="hybrid"
        )

        print(f"\nTop {len(reranked)} Results (Hybrid):\n")
        for i, result in enumerate(reranked, 1):
            print(f"{i}. {result.doc_id}: "
                  f"Score={result.rerank_score:.4f}, "
                  f"Confidence={result.confidence:.4f}, "
                  f"Method={result.method}")
    except Exception as e:
        print(f"❌ Hybrid reranking failed: {e}")


def example_4_rag_integration():
    """
    Example 4: Integration with RAG Pipeline

    Shows how to integrate with a typical RAG workflow
    """
    print("\n" + "="*80)
    print("Example 4: RAG Pipeline Integration")
    print("="*80)

    print("\nTypical RAG Pipeline with Reranking:")
    print("  1. Vector Search (retrieve 50 candidates)")
    print("  2. Rerank (optimize to top-10)")
    print("  3. LLM Context (use top-3 for generation)")

    # Simulate vector search results
    vector_search_results = [
        SearchResult(
            doc_id=f"chunk_{i}",
            content=f"Text chunk {i} about the requested topic with relevant information and context.",
            original_score=0.9 - (i * 0.01),  # Decreasing scores
            metadata={"chunk_id": i, "doc": f"document_{i//5}"}
        )
        for i in range(20)
    ]

    # Initialize reranking agent
    agent = RerankingAgent(
        repository_path=".",
        top_k=10,
        confidence_threshold=0.6
    )

    # Rerank
    query = "Explain the concept in detail"
    reranked = agent.rerank(
        query=query,
        results=vector_search_results,
        method="cross_encoder"
    )

    # Take top-3 for LLM context
    top_3 = reranked[:3]

    print(f"\nVector Search returned {len(vector_search_results)} results")
    print(f"After reranking: {len(reranked)} results passed filters")
    print(f"\nTop 3 for LLM context:\n")

    for i, result in enumerate(top_3, 1):
        print(f"{i}. {result.doc_id} (confidence: {result.confidence:.4f})")

    # Simulate LLM context creation
    context = "\n\n".join([r.content for r in top_3])
    print(f"\n📄 Context created ({len(context)} characters)")
    print("✅ Ready for LLM generation!")


def example_5_performance_comparison():
    """
    Example 5: Performance Comparison

    Compare original scores vs reranked scores
    """
    print("\n" + "="*80)
    print("Example 5: Performance Comparison")
    print("="*80)

    # Create test results with varying relevance
    results = [
        SearchResult("doc1", "Highly relevant content about machine learning algorithms", 0.65, None),
        SearchResult("doc2", "Somewhat related to ML but mostly about data preprocessing", 0.80, None),
        SearchResult("doc3", "Perfect match for machine learning explanation", 0.70, None),
        SearchResult("doc4", "Unrelated content about web development", 0.75, None),
        SearchResult("doc5", "Good coverage of ML concepts and applications", 0.68, None),
    ]

    agent = RerankingAgent(repository_path=".")
    query = "Explain machine learning algorithms"

    reranked = agent.rerank(query, results, method="cross_encoder")

    print(f"\nQuery: {query}\n")
    print("Before vs After Reranking:\n")
    print(f"{'Rank':<6} {'Doc ID':<8} {'Original':<12} {'Reranked':<12} {'Change':<10}")
    print("-" * 60)

    # Sort original by score
    original_sorted = sorted(results, key=lambda x: x.original_score, reverse=True)

    for i, (orig, reranked_result) in enumerate(zip(original_sorted, reranked), 1):
        change = reranked_result.rerank_score - reranked_result.original_score
        print(f"{i:<6} {reranked_result.doc_id:<8} "
              f"{reranked_result.original_score:<12.4f} "
              f"{reranked_result.rerank_score:<12.4f} "
              f"{change:+.4f}")

    # Calculate improvement
    orig_avg = sum(r.original_score for r in results) / len(results)
    rerank_avg = sum(r.rerank_score for r in reranked) / len(reranked)
    improvement = ((rerank_avg - orig_avg) / orig_avg) * 100

    print(f"\n📊 Average Score Improvement: {improvement:+.2f}%")


def example_6_advanced_filtering():
    """
    Example 6: Advanced Filtering Strategies

    Demonstrates different filtering configurations
    """
    print("\n" + "="*80)
    print("Example 6: Advanced Filtering Strategies")
    print("="*80)

    # Sample results
    results = [
        SearchResult(f"doc{i}", f"Content {i}", 0.5 + i/20, None)
        for i in range(15)
    ]

    query = "test query"

    # Strategy 1: High quality, few results
    print("\nStrategy 1: High Quality (threshold=0.8, top_k=3)")
    agent1 = RerankingAgent(repository_path=".", confidence_threshold=0.8, top_k=3)
    results1 = agent1.rerank(query, results, "cross_encoder")
    print(f"  Results: {len(results1)} (all high confidence)")

    # Strategy 2: Broad coverage
    print("\nStrategy 2: Broad Coverage (threshold=0.5, top_k=10)")
    agent2 = RerankingAgent(repository_path=".", confidence_threshold=0.5, top_k=10)
    results2 = agent2.rerank(query, results, "cross_encoder")
    print(f"  Results: {len(results2)} (wider coverage)")

    # Strategy 3: Balanced
    print("\nStrategy 3: Balanced (threshold=0.65, top_k=5)")
    agent3 = RerankingAgent(repository_path=".", confidence_threshold=0.65, top_k=5)
    results3 = agent3.rerank(query, results, "cross_encoder")
    print(f"  Results: {len(results3)} (balanced quality/coverage)")

    print("\n💡 Tip: Adjust based on your use case:")
    print("   - Critical applications → high threshold")
    print("   - Exploratory search → low threshold, high top_k")
    print("   - Production RAG → balanced approach")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("RERANKING AGENT - USAGE EXAMPLES")
    print("="*80)
    print("\nThis script demonstrates various usage patterns of the Reranking Agent.")
    print("Each example can be run independently.\n")

    examples = [
        ("Basic Cross-Encoder", example_1_basic_cross_encoder),
        ("LLM Reranking", example_2_llm_reranking),
        ("Hybrid Reranking", example_3_hybrid_reranking),
        ("RAG Integration", example_4_rag_integration),
        ("Performance Comparison", example_5_performance_comparison),
        ("Advanced Filtering", example_6_advanced_filtering),
    ]

    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...\n")

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "-"*80)

    print("\n✅ All examples completed!")
    print("\nNext steps:")
    print("  - Review the code in this file")
    print("  - Read RERANKING_README.md for full documentation")
    print("  - Run tests: pytest tests/test_reranking_agent.py -v")
    print("  - Integrate into your RAG pipeline")


if __name__ == "__main__":
    main()
