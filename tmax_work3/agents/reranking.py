"""
T-Max Work3 Reranking Agent

Advanced reranking system for search results using:
- Cross-Encoder models (sentence-transformers)
- LLM-based reranking (Claude API)
- Confidence scoring and result optimization
- Blackboard integration
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import dependencies with fallback
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logging.warning("sentence-transformers not available. Cross-Encoder reranking disabled.")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logging.warning("anthropic library not available. LLM reranking disabled.")

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


@dataclass
class SearchResult:
    """Search result data structure"""
    doc_id: str
    content: str
    original_score: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class RerankedResult:
    """Reranked result with confidence scores"""
    doc_id: str
    content: str
    original_score: float
    rerank_score: float
    confidence: float
    method: str  # "cross_encoder", "llm", "hybrid"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class RerankingAgent:
    """
    Reranking Agent - Search Result Optimization

    Features:
    - Cross-Encoder reranking using sentence-transformers
    - LLM-based reranking using Claude API
    - Hybrid approach combining both methods
    - Confidence scoring for result quality
    - Top-k result selection and optimization
    - Blackboard integration for state management

    Architecture:
    1. Receive search results from Hybrid Search or other retrieval systems
    2. Apply Cross-Encoder scoring for semantic relevance
    3. (Optional) Apply LLM-based reranking for complex queries
    4. Combine scores using weighted aggregation
    5. Return top-k results with confidence scores
    """

    def __init__(
        self,
        repository_path: str = ".",
        cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        anthropic_api_key: Optional[str] = None,
        use_llm: bool = False,
        llm_model: str = "claude-3-haiku-20240307",
        top_k: int = 10,
        confidence_threshold: float = 0.5
    ):
        """
        Initialize Reranking Agent

        Args:
            repository_path: Path to repository root
            cross_encoder_model: HuggingFace cross-encoder model name
            anthropic_api_key: Anthropic API key for Claude
            use_llm: Whether to use LLM-based reranking
            llm_model: Claude model to use for LLM reranking
            top_k: Number of top results to return
            confidence_threshold: Minimum confidence score for results
        """
        self.repo_path = Path(repository_path)
        self.top_k = top_k
        self.confidence_threshold = confidence_threshold
        self.use_llm = use_llm and ANTHROPIC_AVAILABLE
        self.llm_model = llm_model

        # Initialize Blackboard
        self.blackboard = get_blackboard()

        # Register agent
        try:
            self.blackboard.register_agent(
                AgentType.QA,  # Using QA type for now (can add RERANKING later)
                worktree="main"
            )
        except:
            pass  # Already registered

        # Initialize Cross-Encoder
        self.cross_encoder = None
        if CROSS_ENCODER_AVAILABLE:
            try:
                self.cross_encoder = CrossEncoder(cross_encoder_model)
                self.blackboard.log(
                    f"Cross-Encoder initialized: {cross_encoder_model}",
                    level="INFO",
                    agent=AgentType.QA
                )
            except Exception as e:
                self.blackboard.log(
                    f"Failed to initialize Cross-Encoder: {e}",
                    level="WARNING",
                    agent=AgentType.QA
                )

        # Initialize Claude client
        self.claude_client = None
        if self.use_llm:
            api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    self.claude_client = anthropic.Anthropic(api_key=api_key)
                    self.blackboard.log(
                        f"Claude client initialized: {llm_model}",
                        level="INFO",
                        agent=AgentType.QA
                    )
                except Exception as e:
                    self.blackboard.log(
                        f"Failed to initialize Claude client: {e}",
                        level="WARNING",
                        agent=AgentType.QA
                    )
            else:
                self.blackboard.log(
                    "ANTHROPIC_API_KEY not found. LLM reranking disabled.",
                    level="WARNING",
                    agent=AgentType.QA
                )
                self.use_llm = False

        self.blackboard.log(
            "Reranking Agent initialized - Ready for result optimization",
            level="SUCCESS",
            agent=AgentType.QA
        )

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        method: str = "cross_encoder"
    ) -> List[RerankedResult]:
        """
        Rerank search results

        Args:
            query: Search query
            results: List of search results to rerank
            method: Reranking method ("cross_encoder", "llm", "hybrid")

        Returns:
            List of reranked results with confidence scores
        """
        self.blackboard.log(
            f"Reranking {len(results)} results using {method} method",
            level="INFO",
            agent=AgentType.QA
        )

        if not results:
            return []

        # Select reranking method
        if method == "cross_encoder":
            reranked = self._rerank_cross_encoder(query, results)
        elif method == "llm":
            reranked = self._rerank_llm(query, results)
        elif method == "hybrid":
            reranked = self._rerank_hybrid(query, results)
        else:
            raise ValueError(f"Unknown reranking method: {method}")

        # Apply confidence threshold and top-k filtering
        filtered = [
            r for r in reranked
            if r.confidence >= self.confidence_threshold
        ][:self.top_k]

        self.blackboard.log(
            f"Reranking complete: {len(filtered)} results passed filters",
            level="SUCCESS",
            agent=AgentType.QA
        )

        # Record metrics
        self._record_metrics(query, results, reranked, filtered, method)

        return filtered

    def _rerank_cross_encoder(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[RerankedResult]:
        """
        Rerank using Cross-Encoder model

        Args:
            query: Search query
            results: Search results

        Returns:
            Reranked results
        """
        if not self.cross_encoder:
            self.blackboard.log(
                "Cross-Encoder not available, returning original results",
                level="WARNING",
                agent=AgentType.QA
            )
            return self._fallback_rerank(results, "cross_encoder")

        try:
            # Prepare query-document pairs
            pairs = [[query, r.content] for r in results]

            # Score with Cross-Encoder
            scores = self.cross_encoder.predict(pairs)

            # Create reranked results
            reranked = []
            for i, (result, score) in enumerate(zip(results, scores)):
                reranked.append(RerankedResult(
                    doc_id=result.doc_id,
                    content=result.content,
                    original_score=result.original_score,
                    rerank_score=float(score),
                    confidence=self._calculate_confidence(float(score), "cross_encoder"),
                    method="cross_encoder",
                    metadata=result.metadata
                ))

            # Sort by rerank score
            reranked.sort(key=lambda x: x.rerank_score, reverse=True)

            return reranked

        except Exception as e:
            self.blackboard.log(
                f"Cross-Encoder reranking failed: {e}",
                level="ERROR",
                agent=AgentType.QA
            )
            return self._fallback_rerank(results, "cross_encoder")

    def _rerank_llm(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[RerankedResult]:
        """
        Rerank using LLM (Claude)

        Args:
            query: Search query
            results: Search results

        Returns:
            Reranked results
        """
        if not self.claude_client:
            self.blackboard.log(
                "Claude client not available, using fallback",
                level="WARNING",
                agent=AgentType.QA
            )
            return self._fallback_rerank(results, "llm")

        try:
            # Prepare prompt
            prompt = self._create_llm_reranking_prompt(query, results)

            # Call Claude API
            response = self.claude_client.messages.create(
                model=self.llm_model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse response
            rankings = self._parse_llm_response(response.content[0].text)

            # Create reranked results
            reranked = []
            for rank_data in rankings:
                doc_id = rank_data["doc_id"]
                score = rank_data["score"]

                # Find original result
                original = next((r for r in results if r.doc_id == doc_id), None)
                if original:
                    reranked.append(RerankedResult(
                        doc_id=original.doc_id,
                        content=original.content,
                        original_score=original.original_score,
                        rerank_score=score,
                        confidence=self._calculate_confidence(score, "llm"),
                        method="llm",
                        metadata=original.metadata
                    ))

            # Add any missing results with low scores
            ranked_ids = {r.doc_id for r in reranked}
            for result in results:
                if result.doc_id not in ranked_ids:
                    reranked.append(RerankedResult(
                        doc_id=result.doc_id,
                        content=result.content,
                        original_score=result.original_score,
                        rerank_score=0.1,
                        confidence=0.1,
                        method="llm",
                        metadata=result.metadata
                    ))

            # Sort by rerank score
            reranked.sort(key=lambda x: x.rerank_score, reverse=True)

            return reranked

        except Exception as e:
            self.blackboard.log(
                f"LLM reranking failed: {e}",
                level="ERROR",
                agent=AgentType.QA
            )
            return self._fallback_rerank(results, "llm")

    def _rerank_hybrid(
        self,
        query: str,
        results: List[SearchResult]
    ) -> List[RerankedResult]:
        """
        Hybrid reranking combining Cross-Encoder and LLM

        Args:
            query: Search query
            results: Search results

        Returns:
            Reranked results
        """
        # Get Cross-Encoder rankings
        ce_results = self._rerank_cross_encoder(query, results)

        # Get LLM rankings (only for top-N from CE)
        top_n_for_llm = min(20, len(ce_results))
        llm_input = [
            SearchResult(
                doc_id=r.doc_id,
                content=r.content,
                original_score=r.original_score,
                metadata=r.metadata
            )
            for r in ce_results[:top_n_for_llm]
        ]

        llm_results = self._rerank_llm(query, llm_input)

        # Combine scores (70% CE, 30% LLM)
        ce_weight = 0.7
        llm_weight = 0.3

        # Create lookup for LLM scores
        llm_scores = {r.doc_id: r.rerank_score for r in llm_results}

        # Combine scores
        hybrid_results = []
        for ce_result in ce_results:
            llm_score = llm_scores.get(ce_result.doc_id, 0.0)

            combined_score = (
                ce_weight * ce_result.rerank_score +
                llm_weight * llm_score
            )

            hybrid_results.append(RerankedResult(
                doc_id=ce_result.doc_id,
                content=ce_result.content,
                original_score=ce_result.original_score,
                rerank_score=combined_score,
                confidence=self._calculate_confidence(combined_score, "hybrid"),
                method="hybrid",
                metadata=ce_result.metadata
            ))

        # Sort by combined score
        hybrid_results.sort(key=lambda x: x.rerank_score, reverse=True)

        return hybrid_results

    def _fallback_rerank(
        self,
        results: List[SearchResult],
        method: str
    ) -> List[RerankedResult]:
        """
        Fallback reranking using original scores

        Args:
            results: Original search results
            method: Attempted method name

        Returns:
            Results with original scores
        """
        return [
            RerankedResult(
                doc_id=r.doc_id,
                content=r.content,
                original_score=r.original_score,
                rerank_score=r.original_score,
                confidence=0.5,
                method=f"{method}_fallback",
                metadata=r.metadata
            )
            for r in results
        ]

    def _calculate_confidence(self, score: float, method: str) -> float:
        """
        Calculate confidence score based on rerank score and method

        Args:
            score: Rerank score
            method: Reranking method

        Returns:
            Confidence score (0-1)
        """
        # Normalize score to 0-1 range
        if method == "cross_encoder":
            # Cross-Encoder scores are typically in [-10, 10] range
            normalized = (score + 10) / 20
        elif method in ["llm", "hybrid"]:
            # LLM and hybrid scores are already 0-1
            normalized = score
        else:
            normalized = min(max(score, 0), 1)

        # Apply confidence curve (sigmoid-like)
        import math
        confidence = 1 / (1 + math.exp(-5 * (normalized - 0.5)))

        return round(confidence, 4)

    def _create_llm_reranking_prompt(
        self,
        query: str,
        results: List[SearchResult]
    ) -> str:
        """
        Create prompt for LLM-based reranking

        Args:
            query: Search query
            results: Search results

        Returns:
            Formatted prompt
        """
        docs_text = "\n\n".join([
            f"Document {i+1} (ID: {r.doc_id}):\n{r.content[:500]}..."
            for i, r in enumerate(results)
        ])

        prompt = f"""You are a search result reranking expert. Given a query and a list of documents,
rank the documents by their relevance to the query.

Query: {query}

Documents:
{docs_text}

Instructions:
1. Analyze each document's relevance to the query
2. Consider semantic similarity, topic alignment, and information quality
3. Assign a relevance score (0.0-1.0) to each document
4. Return results as JSON array with format: [{{"doc_id": "...", "score": 0.X}}]

Return ONLY the JSON array, no explanation."""

        return prompt

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM reranking response

        Args:
            response: LLM response text

        Returns:
            List of ranking data
        """
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                rankings = json.loads(json_match.group())
                return rankings
            else:
                raise ValueError("No JSON array found in response")
        except Exception as e:
            self.blackboard.log(
                f"Failed to parse LLM response: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return []

    def _record_metrics(
        self,
        query: str,
        original_results: List[SearchResult],
        reranked_results: List[RerankedResult],
        filtered_results: List[RerankedResult],
        method: str
    ):
        """
        Record reranking metrics to Blackboard

        Args:
            query: Search query
            original_results: Original results
            reranked_results: Reranked results
            filtered_results: Filtered final results
            method: Reranking method used
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "method": method,
            "original_count": len(original_results),
            "reranked_count": len(reranked_results),
            "filtered_count": len(filtered_results),
            "avg_confidence": sum(r.confidence for r in filtered_results) / len(filtered_results)
                if filtered_results else 0.0,
            "score_improvement": self._calculate_score_improvement(
                original_results, reranked_results
            )
        }

        self.blackboard.set_metric("reranking", query[:50], metrics)

        # Save to file
        self._save_reranking_result(query, filtered_results, metrics)

    def _calculate_score_improvement(
        self,
        original: List[SearchResult],
        reranked: List[RerankedResult]
    ) -> float:
        """
        Calculate average score improvement from reranking

        Args:
            original: Original results
            reranked: Reranked results

        Returns:
            Average score improvement
        """
        if not original or not reranked:
            return 0.0

        original_avg = sum(r.original_score for r in original) / len(original)
        reranked_avg = sum(r.rerank_score for r in reranked) / len(reranked)

        return round(reranked_avg - original_avg, 4)

    def _save_reranking_result(
        self,
        query: str,
        results: List[RerankedResult],
        metrics: Dict[str, Any]
    ):
        """
        Save reranking results to file

        Args:
            query: Search query
            results: Reranked results
            metrics: Metrics data
        """
        output_dir = self.repo_path / "tmax_work3" / "data" / "reranking"
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"reranking_{timestamp}.json"

        data = {
            "query": query,
            "metrics": metrics,
            "results": [r.to_dict() for r in results]
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.blackboard.log(
            f"Reranking results saved: {output_file}",
            level="INFO",
            agent=AgentType.QA
        )


# Helper function for easy integration
def create_reranking_agent(**kwargs) -> RerankingAgent:
    """
    Factory function to create a RerankingAgent instance

    Args:
        **kwargs: Arguments to pass to RerankingAgent constructor

    Returns:
        Configured RerankingAgent instance
    """
    return RerankingAgent(**kwargs)


# CLI interface for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="T-Max Reranking Agent")
    parser.add_argument("--test", action="store_true", help="Run test")
    parser.add_argument("--method", default="cross_encoder",
                       choices=["cross_encoder", "llm", "hybrid"],
                       help="Reranking method")
    parser.add_argument("--query", default="What is machine learning?",
                       help="Test query")

    args = parser.parse_args()

    if args.test:
        print("Testing Reranking Agent...")

        # Create agent
        agent = RerankingAgent(
            repository_path=".",
            use_llm=args.method in ["llm", "hybrid"]
        )

        # Create test results
        test_results = [
            SearchResult(
                doc_id="doc1",
                content="Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                original_score=0.7,
                metadata={"source": "test"}
            ),
            SearchResult(
                doc_id="doc2",
                content="Deep learning uses neural networks with multiple layers to process complex patterns.",
                original_score=0.6,
                metadata={"source": "test"}
            ),
            SearchResult(
                doc_id="doc3",
                content="Python is a popular programming language used in data science.",
                original_score=0.5,
                metadata={"source": "test"}
            ),
        ]

        # Rerank
        reranked = agent.rerank(
            query=args.query,
            results=test_results,
            method=args.method
        )

        # Display results
        print(f"\nReranked Results ({args.method}):")
        print("=" * 80)
        for i, result in enumerate(reranked):
            print(f"\n{i+1}. Document: {result.doc_id}")
            print(f"   Original Score: {result.original_score:.4f}")
            print(f"   Rerank Score: {result.rerank_score:.4f}")
            print(f"   Confidence: {result.confidence:.4f}")
            print(f"   Content: {result.content[:100]}...")

        print("\nTest complete!")
    else:
        print("Usage: python reranking.py --test [--method cross_encoder|llm|hybrid]")
