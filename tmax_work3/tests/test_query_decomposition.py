"""
Query Decomposition Agent テストスイート
"""

import pytest
import json
from pathlib import Path
from typing import List, Dict

from tmax_work3.agents.query_decomposition import (
    QueryDecompositionAgent,
    QueryType,
    SubQuery,
    DecompositionResult
)


@pytest.fixture
def agent():
    """テスト用Query Decomposition Agentインスタンス"""
    return QueryDecompositionAgent(
        llm_provider="anthropic",
        enable_templates=True
    )


@pytest.fixture
def agent_no_templates():
    """テンプレート無効のAgentインスタンス"""
    return QueryDecompositionAgent(
        llm_provider="anthropic",
        enable_templates=False
    )


class TestQueryClassification:
    """クエリタイプ分類テスト"""

    def test_simple_query_classification(self, agent):
        """単純クエリの分類"""
        query = "東京の人口"
        query_type = agent._classify_query(query)
        assert query_type == QueryType.SIMPLE

    def test_comparative_query_classification(self, agent):
        """比較クエリの分類"""
        query = "PythonとJavaの違い"
        query_type = agent._classify_query(query)
        assert query_type == QueryType.COMPARATIVE

    def test_aggregation_query_classification(self, agent):
        """集計クエリの分類"""
        query = "2023年の売上合計"
        query_type = agent._classify_query(query)
        assert query_type == QueryType.AGGREGATION

    def test_multi_hop_query_classification(self, agent):
        """多段推論クエリの分類"""
        query = "機械学習について調べて、その後ディープラーニングについて教えて"
        query_type = agent._classify_query(query)
        assert query_type == QueryType.MULTI_HOP

    def test_temporal_query_classification(self, agent):
        """時系列クエリの分類"""
        query = "2023年10月の売上データ"
        query_type = agent._classify_query(query)
        assert query_type == QueryType.TEMPORAL

    def test_conditional_query_classification(self, agent):
        """条件付きクエリの分類"""
        query = "もし在庫があれば購入したい"
        query_type = agent._classify_query(query)
        assert query_type == QueryType.CONDITIONAL


class TestSimpleQueryDecomposition:
    """単純クエリ分解テスト"""

    def test_simple_query_no_decomposition(self, agent):
        """単純クエリは分解されない"""
        query = "東京の人口"
        result = agent.decompose(query)

        assert result.is_simple is True
        assert len(result.sub_queries) == 1
        assert result.sub_queries[0].text == query
        assert result.sub_queries[0].dependencies == []

    def test_simple_query_execution_order(self, agent):
        """単純クエリの実行順序"""
        query = "パリの観光地"
        result = agent.decompose(query)

        assert result.execution_order == ["sq_0"]
        assert len(result.dependency_graph) == 1


class TestComparativeQueryDecomposition:
    """比較クエリ分解テスト"""

    def test_comparative_query_decomposition(self, agent):
        """比較クエリの分解"""
        query = "PythonとJavaの違い"
        result = agent.decompose(query)

        # 3つのサブクエリに分解されることを確認
        assert len(result.sub_queries) == 3
        assert result.is_simple is False

        # サブクエリ内容確認
        sq_texts = [sq.text for sq in result.sub_queries]
        assert "Pythonについて" in sq_texts
        assert "Javaについて" in sq_texts
        assert "PythonとJavaの違い" in sq_texts

    def test_comparative_query_dependencies(self, agent):
        """比較クエリの依存関係"""
        query = "犬と猫の比較"
        result = agent.decompose(query)

        # 最後のサブクエリが前の2つに依存
        comparison_sq = next(
            sq for sq in result.sub_queries if "比較" in sq.text or "違い" in sq.text
        )
        assert len(comparison_sq.dependencies) == 2

    def test_comparative_execution_order(self, agent):
        """比較クエリの実行順序"""
        query = "RedisとMemcachedの違い"
        result = agent.decompose(query)

        # 実行順序: 2つのエンティティ調査 → 比較
        assert len(result.execution_order) == 3
        assert result.execution_order[2] == "sq_2"  # 比較クエリが最後


class TestMultiHopQueryDecomposition:
    """多段推論クエリ分解テスト"""

    def test_multi_hop_query_decomposition(self, agent):
        """多段推論クエリの分解"""
        query = "機械学習について調べて、その後ディープラーニングについて教えて"
        result = agent.decompose(query)

        # 複数のサブクエリに分解
        assert len(result.sub_queries) >= 2
        assert result.is_simple is False

    def test_multi_hop_dependencies(self, agent):
        """多段推論クエリの依存関係"""
        query = "Aを調べて、次にBを調べて"
        result = agent.decompose(query)

        # 後続クエリが前のクエリに依存
        if len(result.sub_queries) > 1:
            assert len(result.sub_queries[1].dependencies) > 0

    def test_multi_hop_execution_order(self, agent):
        """多段推論クエリの実行順序"""
        query = "まず基礎を学び、次に応用を学ぶ"
        result = agent.decompose(query)

        # 実行順序が依存関係を尊重
        assert len(result.execution_order) == len(result.sub_queries)


class TestDependencyGraph:
    """依存関係グラフテスト"""

    def test_dependency_graph_structure(self, agent):
        """依存関係グラフの構造"""
        query = "AとBの違い"
        result = agent.decompose(query)

        # グラフが全サブクエリを含む
        assert len(result.dependency_graph) == len(result.sub_queries)

        # 各サブクエリIDがキーに存在
        for sq in result.sub_queries:
            assert sq.query_id in result.dependency_graph

    def test_dependency_graph_consistency(self, agent):
        """依存関係グラフの一貫性"""
        query = "CとDの比較"
        result = agent.decompose(query)

        # 依存関係が循環しない
        for sq in result.sub_queries:
            assert sq.query_id not in sq.dependencies

        # 依存先が実在する
        for sq in result.sub_queries:
            for dep in sq.dependencies:
                assert dep in result.dependency_graph


class TestExecutionOrder:
    """実行順序計算テスト"""

    def test_execution_order_topological_sort(self, agent):
        """トポロジカルソート実行順序"""
        query = "XとYの違い"
        result = agent.decompose(query)

        # 実行順序が依存関係を満たす
        completed = set()
        for query_id in result.execution_order:
            sq = next(sq for sq in result.sub_queries if sq.query_id == query_id)
            # 全依存が完了済み
            for dep in sq.dependencies:
                assert dep in completed
            completed.add(query_id)

    def test_execution_order_completeness(self, agent):
        """実行順序の完全性"""
        query = "Eについて調べて、その後Fについて調べて"
        result = agent.decompose(query)

        # 全サブクエリが実行順序に含まれる
        assert set(result.execution_order) == set(sq.query_id for sq in result.sub_queries)


class TestGetExecutableSubqueries:
    """実行可能サブクエリ取得テスト"""

    def test_get_executable_initial(self, agent):
        """初期実行可能サブクエリ"""
        query = "AとBの違い"
        result = agent.decompose(query)

        completed = set()
        executable = agent.get_executable_subqueries(result, completed)

        # 依存なしのサブクエリのみ実行可能
        for sq in executable:
            assert len(sq.dependencies) == 0

    def test_get_executable_after_completion(self, agent):
        """一部完了後の実行可能サブクエリ"""
        query = "GとHの比較"
        result = agent.decompose(query)

        completed = {"sq_0"}
        executable = agent.get_executable_subqueries(result, completed)

        # sq_0に依存するサブクエリは含まれない（sq_1も必要）
        for sq in executable:
            assert "sq_0" not in sq.dependencies or len(sq.dependencies) > 1

    def test_get_executable_priority_ordering(self, agent):
        """実行可能サブクエリの優先度順序"""
        query = "IとJの違い"
        result = agent.decompose(query)

        completed = set()
        executable = agent.get_executable_subqueries(result, completed)

        # 優先度でソート済み
        if len(executable) > 1:
            for i in range(len(executable) - 1):
                assert executable[i].priority >= executable[i + 1].priority


class TestDecomposeToDict:
    """辞書変換テスト"""

    def test_decompose_to_dict_structure(self, agent):
        """辞書変換の構造"""
        query = "KとLの違い"
        result_dict = agent.decompose_to_dict(query)

        # 必須キー存在確認
        assert "original_query" in result_dict
        assert "query_type" in result_dict
        assert "is_simple" in result_dict
        assert "sub_queries" in result_dict
        assert "dependency_graph" in result_dict
        assert "execution_order" in result_dict

    def test_decompose_to_dict_json_serializable(self, agent):
        """辞書がJSON変換可能"""
        query = "MとNの比較"
        result_dict = agent.decompose_to_dict(query)

        # JSON変換可能
        json_str = json.dumps(result_dict, ensure_ascii=False)
        assert len(json_str) > 0

        # JSON読み込み可能
        loaded = json.loads(json_str)
        assert loaded["original_query"] == query


class TestEdgeCases:
    """エッジケーステスト"""

    def test_empty_query(self, agent):
        """空クエリ"""
        query = ""
        result = agent.decompose(query)
        assert result.is_simple is True

    def test_very_long_query(self, agent):
        """非常に長いクエリ"""
        query = "これは非常に長いクエリです。" * 50
        result = agent.decompose(query)
        assert result is not None

    def test_special_characters_query(self, agent):
        """特殊文字を含むクエリ"""
        query = "C++とC#の違い？！"
        result = agent.decompose(query)
        assert result.query_type == QueryType.COMPARATIVE

    def test_mixed_language_query(self, agent):
        """多言語混在クエリ"""
        query = "PythonとRubyのperformance比較"
        result = agent.decompose(query)
        assert result is not None


class TestTemplateDecomposition:
    """テンプレート分解テスト"""

    def test_template_enabled(self, agent):
        """テンプレート有効時"""
        query = "OとPの違い"
        result = agent.decompose(query)

        # テンプレートベース分解が適用
        assert len(result.sub_queries) == 3

    def test_template_disabled(self, agent_no_templates):
        """テンプレート無効時"""
        query = "QとRの違い"
        result = agent_no_templates.decompose(query)

        # LLMまたはフォールバック分解
        assert result is not None


class TestBlackboardIntegration:
    """Blackboard統合テスト"""

    def test_blackboard_logging(self, agent):
        """Blackboardログ記録"""
        query = "SとTの比較"
        result = agent.decompose(query)

        # ログが記録されている（Blackboardが初期化されている）
        assert agent.blackboard is not None

    def test_blackboard_agent_registration(self, agent):
        """Blackboardエージェント登録"""
        # エージェントが登録されている
        from tmax_work3.blackboard.state_manager import AgentType
        assert AgentType.COORDINATOR in agent.blackboard.agents


# パフォーマンステスト
class TestPerformance:
    """パフォーマンステスト"""

    def test_decomposition_speed_simple(self, agent):
        """単純クエリの分解速度"""
        import time

        query = "東京"
        start = time.time()
        result = agent.decompose(query)
        elapsed = time.time() - start

        # 単純クエリは100ms以内
        assert elapsed < 0.1

    def test_decomposition_speed_complex(self, agent):
        """複雑クエリの分解速度"""
        import time

        query = "UとVの違いを調べて、その後Wについて教えて"
        start = time.time()
        result = agent.decompose(query)
        elapsed = time.time() - start

        # 複雑クエリでも5秒以内（LLM呼び出し含む）
        assert elapsed < 5.0


# 統合テスト
class TestIntegration:
    """統合テスト"""

    def test_full_decomposition_workflow(self, agent):
        """完全な分解ワークフロー"""
        query = "XとYの違い"

        # Step 1: 分解
        result = agent.decompose(query)
        assert len(result.sub_queries) > 0

        # Step 2: 実行順序取得
        execution_order = result.execution_order
        assert len(execution_order) == len(result.sub_queries)

        # Step 3: 順次実行シミュレーション
        completed = set()
        for query_id in execution_order:
            executable = agent.get_executable_subqueries(result, completed)

            # 実行可能なサブクエリが存在
            assert len(executable) > 0

            # 実行（シミュレーション）
            executed_sq = next(sq for sq in result.sub_queries if sq.query_id == query_id)
            completed.add(query_id)

        # 全サブクエリ完了
        assert len(completed) == len(result.sub_queries)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
