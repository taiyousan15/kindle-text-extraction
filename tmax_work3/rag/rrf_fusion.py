"""
Reciprocal Rank Fusion (RRF) Module for Hybrid Search RAG System
Combines multiple ranked result lists into a unified ranking
"""
import logging
from typing import List, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) Algorithm

    RRF is a method to combine multiple ranked result lists.
    It's particularly effective for hybrid search because:
    1. It's unsupervised (no training required)
    2. It handles different score scales across retrieval methods
    3. It's robust to outliers
    4. It gives higher weight to documents that appear in multiple result lists

    Formula:
    RRF_score(d) = Σ (1 / (k + rank_i(d)))

    Where:
    - d is a document
    - k is a constant (typically 60)
    - rank_i(d) is the rank of document d in result list i
    """

    def __init__(self, k: int = 60):
        """
        Initialize RRF

        Args:
            k: Constant for RRF formula (default: 60, as per literature)
               Lower k gives more weight to top-ranked items
               Higher k makes the fusion more uniform
        """
        self.k = k
        logger.info(f"ReciprocalRankFusion initialized (k={k})")

    def fuse(
        self,
        result_lists: List[List[Dict]],
        weights: Optional[List[float]] = None
    ) -> List[Dict]:
        """
        Fuse multiple ranked result lists using RRF

        Args:
            result_lists: List of result lists from different retrieval methods
                         Each result should have 'document_id', 'rank', and other fields
            weights: Optional weights for each result list (default: equal weights)

        Returns:
            Fused result list sorted by RRF score
        """
        if not result_lists:
            logger.warning("No result lists to fuse")
            return []

        # Validate weights
        if weights is None:
            weights = [1.0] * len(result_lists)
        elif len(weights) != len(result_lists):
            raise ValueError(f"Number of weights ({len(weights)}) must match number of result lists ({len(result_lists)})")

        # Normalize weights to sum to 1
        total_weight = sum(weights)
        if total_weight == 0:
            raise ValueError("Sum of weights cannot be zero")
        weights = [w / total_weight for w in weights]

        # Calculate RRF scores
        rrf_scores = defaultdict(float)
        document_info = {}  # Store full document info

        for result_list, weight in zip(result_lists, weights):
            for result in result_list:
                doc_id = result["document_id"]
                rank = result["rank"]

                # RRF formula: 1 / (k + rank)
                rrf_score = weight * (1.0 / (self.k + rank))
                rrf_scores[doc_id] += rrf_score

                # Store document info (prefer first occurrence)
                if doc_id not in document_info:
                    document_info[doc_id] = {
                        "document_id": doc_id,
                        "text": result.get("text", ""),
                        "metadata": result.get("metadata", {}),
                        "methods": []
                    }

                # Track which methods retrieved this document
                method = result.get("method", "unknown")
                if method not in document_info[doc_id]["methods"]:
                    document_info[doc_id]["methods"].append(method)

        # Sort by RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Build final result list
        fused_results = []
        for rank, (doc_id, rrf_score) in enumerate(sorted_docs, 1):
            result = document_info[doc_id].copy()
            result["rank"] = rank
            result["rrf_score"] = float(rrf_score)
            fused_results.append(result)

        logger.debug(f"Fused {len(result_lists)} result lists into {len(fused_results)} documents")
        return fused_results

    def fuse_weighted(
        self,
        result_lists: List[List[Dict]],
        alpha: float = 0.5
    ) -> List[Dict]:
        """
        Fuse result lists with dynamic alpha weighting

        Commonly used for combining sparse (BM25) and dense (vector) results.

        Args:
            result_lists: List of exactly 2 result lists [sparse_results, dense_results]
            alpha: Weight for dense results (0-1)
                  0.0 = only sparse (BM25)
                  1.0 = only dense (vector)
                  0.5 = equal weight

        Returns:
            Fused result list sorted by RRF score
        """
        if len(result_lists) != 2:
            raise ValueError("fuse_weighted expects exactly 2 result lists (sparse and dense)")

        sparse_weight = 1.0 - alpha
        dense_weight = alpha

        weights = [sparse_weight, dense_weight]

        logger.debug(f"Fusing with alpha={alpha:.2f} (sparse={sparse_weight:.2f}, dense={dense_weight:.2f})")
        return self.fuse(result_lists, weights=weights)

    def evaluate_fusion_quality(
        self,
        fused_results: List[Dict],
        ground_truth_ids: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Evaluate the quality of fusion results

        Args:
            fused_results: Fused result list
            ground_truth_ids: Optional list of relevant document IDs for evaluation

        Returns:
            Dictionary of evaluation metrics
        """
        metrics = {}

        # Diversity: How many different methods contributed
        all_methods = set()
        for result in fused_results:
            all_methods.update(result.get("methods", []))
        metrics["diversity"] = len(all_methods)

        # Coverage: Percentage of documents retrieved by multiple methods
        multi_method_count = sum(1 for r in fused_results if len(r.get("methods", [])) > 1)
        metrics["multi_method_coverage"] = (
            multi_method_count / len(fused_results) if fused_results else 0.0
        )

        # If ground truth provided, calculate precision
        if ground_truth_ids:
            retrieved_ids = [r["document_id"] for r in fused_results]
            relevant_retrieved = len(set(retrieved_ids) & set(ground_truth_ids))
            metrics["precision"] = relevant_retrieved / len(retrieved_ids) if retrieved_ids else 0.0
            metrics["recall"] = relevant_retrieved / len(ground_truth_ids) if ground_truth_ids else 0.0

        return metrics


def weighted_sum_fusion(
    result_lists: List[List[Dict]],
    weights: Optional[List[float]] = None,
    normalize_scores: bool = True
) -> List[Dict]:
    """
    Alternative fusion method: Weighted sum of normalized scores

    Args:
        result_lists: List of result lists with 'score' field
        weights: Optional weights for each result list
        normalize_scores: Whether to normalize scores to [0, 1] range

    Returns:
        Fused result list sorted by weighted sum
    """
    if not result_lists:
        return []

    if weights is None:
        weights = [1.0] * len(result_lists)

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Calculate weighted scores
    weighted_scores = defaultdict(float)
    document_info = {}

    for result_list, weight in zip(result_lists, weights):
        if not result_list:
            continue

        # Normalize scores if requested
        if normalize_scores:
            scores = [r.get("score", 0.0) for r in result_list]
            min_score = min(scores) if scores else 0.0
            max_score = max(scores) if scores else 1.0
            score_range = max_score - min_score if max_score != min_score else 1.0
        else:
            min_score = 0.0
            score_range = 1.0

        for result in result_list:
            doc_id = result["document_id"]
            raw_score = result.get("score", 0.0)

            # Normalize score
            norm_score = (raw_score - min_score) / score_range if score_range > 0 else 0.0

            # Add weighted score
            weighted_scores[doc_id] += weight * norm_score

            # Store document info
            if doc_id not in document_info:
                document_info[doc_id] = {
                    "document_id": doc_id,
                    "text": result.get("text", ""),
                    "metadata": result.get("metadata", {}),
                    "methods": []
                }

            method = result.get("method", "unknown")
            if method not in document_info[doc_id]["methods"]:
                document_info[doc_id]["methods"].append(method)

    # Sort by weighted score
    sorted_docs = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)

    # Build final result list
    fused_results = []
    for rank, (doc_id, score) in enumerate(sorted_docs, 1):
        result = document_info[doc_id].copy()
        result["rank"] = rank
        result["fusion_score"] = float(score)
        fused_results.append(result)

    return fused_results


if __name__ == "__main__":
    # Test RRF
    logging.basicConfig(level=logging.INFO)

    # Create sample result lists from different retrieval methods
    bm25_results = [
        {"document_id": "doc1", "rank": 1, "score": 5.2, "text": "Machine learning models", "method": "bm25"},
        {"document_id": "doc2", "rank": 2, "score": 4.8, "text": "Training datasets", "method": "bm25"},
        {"document_id": "doc3", "rank": 3, "score": 3.5, "text": "Neural networks", "method": "bm25"},
    ]

    vector_results = [
        {"document_id": "doc2", "rank": 1, "score": 0.92, "text": "Training datasets", "method": "dense_vector"},
        {"document_id": "doc4", "rank": 2, "score": 0.88, "text": "Deep learning", "method": "dense_vector"},
        {"document_id": "doc1", "rank": 3, "score": 0.85, "text": "Machine learning models", "method": "dense_vector"},
    ]

    splade_results = [
        {"document_id": "doc1", "rank": 1, "score": 12.5, "text": "Machine learning models", "method": "splade"},
        {"document_id": "doc4", "rank": 2, "score": 11.2, "text": "Deep learning", "method": "splade"},
        {"document_id": "doc5", "rank": 3, "score": 9.8, "text": "AI systems", "method": "splade"},
    ]

    # Test RRF fusion
    rrf = ReciprocalRankFusion(k=60)
    fused_results = rrf.fuse([bm25_results, vector_results, splade_results])

    print("\nRRF Fusion Results:")
    print("=" * 80)
    for result in fused_results:
        print(f"Rank {result['rank']}: {result['document_id']} (RRF score={result['rrf_score']:.4f})")
        print(f"  Methods: {', '.join(result['methods'])}")
        print(f"  Text: {result['text']}")
        print()

    # Test weighted fusion
    print("\nWeighted Fusion (alpha=0.7):")
    print("=" * 80)
    weighted_results = rrf.fuse_weighted([bm25_results, vector_results], alpha=0.7)
    for result in weighted_results[:3]:
        print(f"Rank {result['rank']}: {result['document_id']} (RRF score={result['rrf_score']:.4f})")
        print()
