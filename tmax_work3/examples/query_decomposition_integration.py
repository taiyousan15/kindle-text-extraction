"""
Query Decomposition Agent - Coordinator統合サンプル

Coordinatorから呼び出し、Hybrid Searchに複数クエリを送信する例
"""

import logging
from typing import List, Dict, Any, Set
from pathlib import Path
import sys

# パス設定
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.agents.query_decomposition import (
    QueryDecompositionAgent,
    DecompositionResult
)
from tmax_work3.blackboard.state_manager import (
    Blackboard,
    get_blackboard
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class HybridSearchSimulator:
    """
    Hybrid Search シミュレーター（実装例）

    実際のHybrid Searchエージェントへの統合を想定
    """

    def __init__(self):
        self.search_results_cache: Dict[str, List[str]] = {}

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        検索実行（シミュレーション）

        Args:
            query: 検索クエリ
            top_k: 上位K件

        Returns:
            検索結果リスト
        """
        logger.info(f"Hybrid Search: '{query}' (top_k={top_k})")

        # シミュレーション: ダミー結果を返す
        results = [
            f"Document {i+1} for '{query}'"
            for i in range(top_k)
        ]

        # キャッシュに保存
        self.search_results_cache[query] = results

        return results


class QueryDecompositionCoordinator:
    """
    Query Decomposition Coordinator

    Query Decomposition AgentとHybrid Searchを統合
    """

    def __init__(self):
        self.decomposition_agent = QueryDecompositionAgent()
        self.hybrid_search = HybridSearchSimulator()
        self.blackboard = get_blackboard()

        logger.info("Query Decomposition Coordinator initialized")

    def process_query(
        self,
        query: str,
        top_k_per_subquery: int = 5
    ) -> Dict[str, Any]:
        """
        クエリ処理パイプライン

        Args:
            query: ユーザークエリ
            top_k_per_subquery: サブクエリごとの検索件数

        Returns:
            統合結果
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing query: '{query}'")
        logger.info(f"{'='*60}\n")

        # Step 1: クエリ分解
        decomposition_result = self.decomposition_agent.decompose(query)

        logger.info(f"\nQuery Type: {decomposition_result.query_type.value}")
        logger.info(f"Sub-queries: {len(decomposition_result.sub_queries)}")
        logger.info(f"Is Simple: {decomposition_result.is_simple}\n")

        # Step 2: サブクエリ実行
        subquery_results = self._execute_subqueries(
            decomposition_result,
            top_k_per_subquery
        )

        # Step 3: 結果統合
        final_result = self._aggregate_results(
            decomposition_result,
            subquery_results
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"Query processing complete")
        logger.info(f"{'='*60}\n")

        return final_result

    def _execute_subqueries(
        self,
        decomposition_result: DecompositionResult,
        top_k: int
    ) -> Dict[str, List[str]]:
        """
        サブクエリを実行順序に従って実行

        Args:
            decomposition_result: 分解結果
            top_k: 検索件数

        Returns:
            サブクエリIDごとの検索結果
        """
        logger.info("Executing sub-queries in dependency order...")

        subquery_results = {}
        completed_ids: Set[str] = set()

        # 実行順序に従って実行
        for query_id in decomposition_result.execution_order:
            subquery = next(
                sq for sq in decomposition_result.sub_queries
                if sq.query_id == query_id
            )

            logger.info(
                f"\n[{subquery.query_id}] Executing: '{subquery.text}'"
            )
            logger.info(f"  Dependencies: {subquery.dependencies}")

            # 依存関係チェック
            dependencies_met = all(
                dep in completed_ids for dep in subquery.dependencies
            )

            if not dependencies_met:
                logger.warning(
                    f"  Dependencies not met for {subquery.query_id}. Skipping."
                )
                continue

            # Hybrid Search実行
            search_results = self.hybrid_search.search(
                subquery.text,
                top_k=top_k
            )

            subquery_results[query_id] = search_results
            completed_ids.add(query_id)

            logger.info(f"  Results: {len(search_results)} documents")

        logger.info(
            f"\nCompleted {len(completed_ids)}/{len(decomposition_result.sub_queries)} sub-queries"
        )

        return subquery_results

    def _aggregate_results(
        self,
        decomposition_result: DecompositionResult,
        subquery_results: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        サブクエリ結果を統合

        Args:
            decomposition_result: 分解結果
            subquery_results: サブクエリ結果

        Returns:
            統合結果
        """
        logger.info("\nAggregating results...")

        # 単純クエリの場合
        if decomposition_result.is_simple:
            query_id = decomposition_result.sub_queries[0].query_id
            return {
                "original_query": decomposition_result.original_query,
                "query_type": decomposition_result.query_type.value,
                "results": subquery_results.get(query_id, []),
                "sub_queries": []
            }

        # 複雑クエリの場合: 全サブクエリ結果を含める
        aggregated = {
            "original_query": decomposition_result.original_query,
            "query_type": decomposition_result.query_type.value,
            "sub_queries": [
                {
                    "query_id": sq.query_id,
                    "text": sq.text,
                    "results": subquery_results.get(sq.query_id, [])
                }
                for sq in decomposition_result.sub_queries
            ],
            "total_documents": sum(
                len(results) for results in subquery_results.values()
            )
        }

        logger.info(f"Total documents retrieved: {aggregated['total_documents']}")

        return aggregated


def main():
    """メイン実行"""
    coordinator = QueryDecompositionCoordinator()

    # テストクエリ
    test_queries = [
        "PythonとJavaの違いは何ですか？",
        "東京の観光スポット",
        "機械学習について調べて、その後ディープラーニングの応用事例を教えて",
        "2023年と2024年の売上比較"
    ]

    for query in test_queries:
        result = coordinator.process_query(query, top_k_per_subquery=3)

        print(f"\n{'='*60}")
        print(f"Final Result for: '{query}'")
        print(f"{'='*60}")
        print(f"Query Type: {result['query_type']}")
        print(f"Total Documents: {result.get('total_documents', len(result.get('results', [])))}")

        if result.get('sub_queries'):
            print(f"\nSub-query Results:")
            for sq in result['sub_queries']:
                print(f"\n  [{sq['query_id']}] {sq['text']}")
                print(f"    Documents: {len(sq['results'])}")
                for i, doc in enumerate(sq['results'][:2], 1):
                    print(f"      {i}. {doc}")
        else:
            print(f"\nDirect Results:")
            for i, doc in enumerate(result.get('results', [])[:3], 1):
                print(f"  {i}. {doc}")

        print()


if __name__ == "__main__":
    main()
