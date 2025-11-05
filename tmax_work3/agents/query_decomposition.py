"""
Query Decomposition Agent - 複雑なクエリを単純なサブクエリに分解

役割:
- 複雑なクエリをLLMで分析
- 単純なサブクエリに分解
- テンプレートベースの分解パターン適用
- サブクエリ依存関係の管理
- Coordinatorから呼び出され、Hybrid Searchに複数クエリを送信
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import re

# LangChain imports
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    get_blackboard
)

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """クエリタイプ分類"""
    SIMPLE = "simple"                    # 単純クエリ（分解不要）
    COMPARATIVE = "comparative"          # 比較クエリ
    AGGREGATION = "aggregation"          # 集計クエリ
    MULTI_HOP = "multi_hop"             # 多段推論クエリ
    TEMPORAL = "temporal"                # 時系列クエリ
    CONDITIONAL = "conditional"          # 条件付きクエリ


@dataclass
class SubQuery:
    """サブクエリデータ構造"""
    query_id: str                        # サブクエリID
    text: str                            # サブクエリテキスト
    dependencies: List[str]              # 依存するサブクエリID
    query_type: QueryType                # クエリタイプ
    priority: int                        # 実行優先度
    metadata: Dict[str, Any]             # メタデータ


@dataclass
class DecompositionResult:
    """クエリ分解結果"""
    original_query: str                  # 元のクエリ
    query_type: QueryType                # 分類されたクエリタイプ
    sub_queries: List[SubQuery]          # サブクエリリスト
    dependency_graph: Dict[str, List[str]]  # 依存関係グラフ
    execution_order: List[str]           # 実行順序
    is_simple: bool                      # 単純クエリフラグ


class QueryDecompositionAgent:
    """
    Query Decomposition Agent

    複雑なクエリを単純なサブクエリに分解し、
    依存関係を管理して効率的な検索を実現する
    """

    def __init__(
        self,
        llm_provider: str = "anthropic",
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.0,
        enable_templates: bool = True,
        blackboard: Optional[Blackboard] = None
    ):
        """
        初期化

        Args:
            llm_provider: LLMプロバイダー（anthropic/openai）
            model: 使用モデル
            temperature: LLM生成温度
            enable_templates: テンプレートベース分解の有効化
            blackboard: Blackboardインスタンス
        """
        self.llm_provider = llm_provider
        self.model = model
        self.temperature = temperature
        self.enable_templates = enable_templates
        self.blackboard = blackboard or get_blackboard()

        # LLMクライアント初期化
        self._init_llm_client()

        # テンプレートパターン定義
        self.decomposition_templates = self._load_decomposition_templates()

        # Blackboardにエージェント登録
        self.blackboard.register_agent(AgentType.COORDINATOR)

        logger.info(
            f"Query Decomposition Agent initialized: "
            f"provider={llm_provider}, model={model}"
        )

    def _init_llm_client(self):
        """LLMクライアント初期化"""
        try:
            if self.llm_provider == "anthropic":
                import os
                api_key = os.getenv("ANTHROPIC_API_KEY")

                if not api_key:
                    logger.warning(
                        "ANTHROPIC_API_KEY not found. Using mock mode."
                    )
                    self.llm_client = None
                    self.is_mock = True
                else:
                    self.llm_client = ChatAnthropic(
                        model=self.model,
                        anthropic_api_key=api_key,
                        temperature=self.temperature,
                        max_tokens=2048
                    )
                    self.is_mock = False
                    logger.info(f"LLM client initialized: {self.model}")

            else:
                logger.warning(f"Unsupported LLM provider: {self.llm_provider}")
                self.llm_client = None
                self.is_mock = True

        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
            self.is_mock = True

    def _load_decomposition_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        分解テンプレートパターンをロード

        Returns:
            テンプレート辞書
        """
        templates = {
            "comparative": {
                "pattern": r"(比較|違い|差|異なる|vs|versus)",
                "decomposer": self._decompose_comparative
            },
            "aggregation": {
                "pattern": r"(合計|平均|最大|最小|集計|統計)",
                "decomposer": self._decompose_aggregation
            },
            "multi_hop": {
                "pattern": r"(そして|次に|その後|それから|について.*について)",
                "decomposer": self._decompose_multi_hop
            },
            "temporal": {
                "pattern": r"(\d{4}年|\d+月|\d+日|昨日|今日|明日|先週|来週)",
                "decomposer": self._decompose_temporal
            },
            "conditional": {
                "pattern": r"(もし|場合|条件|when|if)",
                "decomposer": self._decompose_conditional
            }
        }
        return templates

    def decompose(self, query: str) -> DecompositionResult:
        """
        クエリを分解

        Args:
            query: 元のクエリ

        Returns:
            DecompositionResult
        """
        self.blackboard.log(
            f"Starting query decomposition: '{query}'",
            level="INFO",
            agent=AgentType.COORDINATOR
        )

        # Step 1: クエリタイプ分類
        query_type = self._classify_query(query)

        # Step 2: 単純クエリチェック
        if query_type == QueryType.SIMPLE:
            return self._create_simple_result(query)

        # Step 3: テンプレートベース分解を試行
        if self.enable_templates:
            template_result = self._try_template_decomposition(query, query_type)
            if template_result:
                self.blackboard.log(
                    f"Template-based decomposition successful: {len(template_result.sub_queries)} sub-queries",
                    level="INFO",
                    agent=AgentType.COORDINATOR
                )
                return template_result

        # Step 4: LLMベース分解
        llm_result = self._llm_decompose(query, query_type)

        self.blackboard.log(
            f"Query decomposition complete: {len(llm_result.sub_queries)} sub-queries",
            level="SUCCESS",
            agent=AgentType.COORDINATOR
        )

        return llm_result

    def _classify_query(self, query: str) -> QueryType:
        """
        クエリタイプを分類

        Args:
            query: クエリテキスト

        Returns:
            QueryType
        """
        # 簡易ルールベース分類
        query_lower = query.lower()

        for template_name, template in self.decomposition_templates.items():
            if re.search(template["pattern"], query):
                type_mapping = {
                    "comparative": QueryType.COMPARATIVE,
                    "aggregation": QueryType.AGGREGATION,
                    "multi_hop": QueryType.MULTI_HOP,
                    "temporal": QueryType.TEMPORAL,
                    "conditional": QueryType.CONDITIONAL
                }
                return type_mapping.get(template_name, QueryType.SIMPLE)

        # 複雑さチェック
        if len(query.split()) <= 5 and "?" not in query and "。" not in query[:-1]:
            return QueryType.SIMPLE

        return QueryType.MULTI_HOP

    def _create_simple_result(self, query: str) -> DecompositionResult:
        """
        単純クエリ結果を生成

        Args:
            query: クエリテキスト

        Returns:
            DecompositionResult
        """
        sub_query = SubQuery(
            query_id="sq_0",
            text=query,
            dependencies=[],
            query_type=QueryType.SIMPLE,
            priority=1,
            metadata={"is_original": True}
        )

        return DecompositionResult(
            original_query=query,
            query_type=QueryType.SIMPLE,
            sub_queries=[sub_query],
            dependency_graph={"sq_0": []},
            execution_order=["sq_0"],
            is_simple=True
        )

    def _try_template_decomposition(
        self,
        query: str,
        query_type: QueryType
    ) -> Optional[DecompositionResult]:
        """
        テンプレートベース分解を試行

        Args:
            query: クエリテキスト
            query_type: クエリタイプ

        Returns:
            DecompositionResult or None
        """
        for template_name, template in self.decomposition_templates.items():
            if re.search(template["pattern"], query):
                decomposer = template["decomposer"]
                try:
                    result = decomposer(query)
                    if result:
                        return result
                except Exception as e:
                    logger.warning(
                        f"Template decomposition failed for {template_name}: {e}"
                    )
                    continue

        return None

    def _decompose_comparative(self, query: str) -> Optional[DecompositionResult]:
        """比較クエリ分解"""
        # "AとBの違い" -> ["Aについて", "Bについて", "AとBの比較"]
        match = re.search(r"(.+?)と(.+?)の(違い|差|比較)", query)
        if not match:
            return None

        entity_a = match.group(1).strip()
        entity_b = match.group(2).strip()

        sub_queries = [
            SubQuery(
                query_id="sq_0",
                text=f"{entity_a}について",
                dependencies=[],
                query_type=QueryType.SIMPLE,
                priority=3,
                metadata={"entity": entity_a}
            ),
            SubQuery(
                query_id="sq_1",
                text=f"{entity_b}について",
                dependencies=[],
                query_type=QueryType.SIMPLE,
                priority=3,
                metadata={"entity": entity_b}
            ),
            SubQuery(
                query_id="sq_2",
                text=f"{entity_a}と{entity_b}の違い",
                dependencies=["sq_0", "sq_1"],
                query_type=QueryType.COMPARATIVE,
                priority=1,
                metadata={"comparison": True}
            )
        ]

        dependency_graph = {
            "sq_0": [],
            "sq_1": [],
            "sq_2": ["sq_0", "sq_1"]
        }

        execution_order = ["sq_0", "sq_1", "sq_2"]

        return DecompositionResult(
            original_query=query,
            query_type=QueryType.COMPARATIVE,
            sub_queries=sub_queries,
            dependency_graph=dependency_graph,
            execution_order=execution_order,
            is_simple=False
        )

    def _decompose_aggregation(self, query: str) -> Optional[DecompositionResult]:
        """集計クエリ分解"""
        # 簡易実装: 集計キーワードを抽出
        return None

    def _decompose_multi_hop(self, query: str) -> Optional[DecompositionResult]:
        """多段推論クエリ分解"""
        # 簡易実装: 文を分割
        sentences = re.split(r"[。、]", query)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return None

        sub_queries = []
        for i, sentence in enumerate(sentences):
            dependencies = [f"sq_{i-1}"] if i > 0 else []
            sub_queries.append(
                SubQuery(
                    query_id=f"sq_{i}",
                    text=sentence,
                    dependencies=dependencies,
                    query_type=QueryType.SIMPLE,
                    priority=len(sentences) - i,
                    metadata={"step": i}
                )
            )

        dependency_graph = {
            sq.query_id: sq.dependencies for sq in sub_queries
        }
        execution_order = [sq.query_id for sq in sub_queries]

        return DecompositionResult(
            original_query=query,
            query_type=QueryType.MULTI_HOP,
            sub_queries=sub_queries,
            dependency_graph=dependency_graph,
            execution_order=execution_order,
            is_simple=False
        )

    def _decompose_temporal(self, query: str) -> Optional[DecompositionResult]:
        """時系列クエリ分解"""
        return None

    def _decompose_conditional(self, query: str) -> Optional[DecompositionResult]:
        """条件付きクエリ分解"""
        return None

    def _llm_decompose(
        self,
        query: str,
        query_type: QueryType
    ) -> DecompositionResult:
        """
        LLMベースのクエリ分解

        Args:
            query: クエリテキスト
            query_type: クエリタイプ

        Returns:
            DecompositionResult
        """
        if self.is_mock or not self.llm_client:
            logger.warning("LLM not available, using fallback decomposition")
            return self._fallback_decompose(query, query_type)

        # システムプロンプト
        system_prompt = """あなたは検索クエリ分解の専門家です。
複雑なクエリを単純なサブクエリに分解し、依存関係を明確にしてください。

出力フォーマット（JSON）:
{
  "sub_queries": [
    {
      "query_id": "sq_0",
      "text": "サブクエリテキスト",
      "dependencies": [],
      "priority": 3
    },
    ...
  ]
}

ルール:
1. 各サブクエリは独立して実行可能
2. dependencies には依存するquery_idを列挙
3. priority は高いほど先に実行（1-5）
4. 最大5個までのサブクエリに分解
"""

        # ユーザープロンプト
        user_prompt = f"""以下のクエリを分解してください:

クエリ: {query}
クエリタイプ: {query_type.value}

JSON形式で出力してください。"""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = self.llm_client.invoke(messages)
            response_text = response.content

            # JSON抽出
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                sub_queries = [
                    SubQuery(
                        query_id=sq["query_id"],
                        text=sq["text"],
                        dependencies=sq.get("dependencies", []),
                        query_type=QueryType.SIMPLE,
                        priority=sq.get("priority", 1),
                        metadata={}
                    )
                    for sq in data.get("sub_queries", [])
                ]

                # 依存関係グラフ構築
                dependency_graph = {
                    sq.query_id: sq.dependencies for sq in sub_queries
                }

                # 実行順序計算
                execution_order = self._compute_execution_order(dependency_graph)

                return DecompositionResult(
                    original_query=query,
                    query_type=query_type,
                    sub_queries=sub_queries,
                    dependency_graph=dependency_graph,
                    execution_order=execution_order,
                    is_simple=False
                )

        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")

        # フォールバック
        return self._fallback_decompose(query, query_type)

    def _fallback_decompose(
        self,
        query: str,
        query_type: QueryType
    ) -> DecompositionResult:
        """
        フォールバック分解（LLM失敗時）

        Args:
            query: クエリテキスト
            query_type: クエリタイプ

        Returns:
            DecompositionResult
        """
        # 単純クエリとして返す
        return self._create_simple_result(query)

    def _compute_execution_order(
        self,
        dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """
        トポロジカルソートで実行順序を計算

        Args:
            dependency_graph: 依存関係グラフ

        Returns:
            実行順序リスト
        """
        # Kahn's algorithm
        in_degree = {node: 0 for node in dependency_graph}

        for node, deps in dependency_graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        execution_order = []

        while queue:
            # 優先度でソート（仮）
            queue.sort()
            node = queue.pop(0)
            execution_order.append(node)

            # 依存を解決
            for dependent in dependency_graph:
                if node in dependency_graph[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        return execution_order

    def decompose_to_dict(self, query: str) -> Dict[str, Any]:
        """
        クエリを分解して辞書形式で返す

        Args:
            query: クエリテキスト

        Returns:
            分解結果の辞書
        """
        result = self.decompose(query)

        return {
            "original_query": result.original_query,
            "query_type": result.query_type.value,
            "is_simple": result.is_simple,
            "sub_queries": [
                {
                    "query_id": sq.query_id,
                    "text": sq.text,
                    "dependencies": sq.dependencies,
                    "query_type": sq.query_type.value,
                    "priority": sq.priority,
                    "metadata": sq.metadata
                }
                for sq in result.sub_queries
            ],
            "dependency_graph": result.dependency_graph,
            "execution_order": result.execution_order
        }

    def get_executable_subqueries(
        self,
        result: DecompositionResult,
        completed_ids: Set[str]
    ) -> List[SubQuery]:
        """
        実行可能なサブクエリを取得

        Args:
            result: 分解結果
            completed_ids: 完了済みサブクエリID集合

        Returns:
            実行可能なサブクエリリスト
        """
        executable = []

        for sq in result.sub_queries:
            if sq.query_id in completed_ids:
                continue

            # 依存関係チェック
            dependencies_met = all(dep in completed_ids for dep in sq.dependencies)

            if dependencies_met:
                executable.append(sq)

        # 優先度でソート
        return sorted(executable, key=lambda x: x.priority, reverse=True)


def main():
    """メイン実行（テスト用）"""
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    agent = QueryDecompositionAgent()

    test_queries = [
        "PythonとJavaの違いは何ですか？",
        "東京の人口",
        "2023年の売上を集計してください",
        "機械学習について調べて、その後ディープラーニングについて教えて"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")

        result = agent.decompose_to_dict(query)

        print(f"\nQuery Type: {result['query_type']}")
        print(f"Is Simple: {result['is_simple']}")
        print(f"\nSub-queries ({len(result['sub_queries'])}):")

        for sq in result['sub_queries']:
            print(f"  [{sq['query_id']}] {sq['text']}")
            print(f"    Dependencies: {sq['dependencies']}")
            print(f"    Priority: {sq['priority']}")

        print(f"\nExecution Order: {result['execution_order']}")


if __name__ == "__main__":
    main()
