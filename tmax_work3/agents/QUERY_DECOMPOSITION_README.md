# Query Decomposition Agent

複雑なクエリを単純なサブクエリに分解し、依存関係を管理するエージェント

## 概要

Query Decomposition Agentは、複雑な検索クエリを解析し、実行可能な単純なサブクエリに分解します。これにより、RAGシステムやHybrid Searchでの検索精度が向上します。

## 主な機能

### 1. クエリタイプ分類
- **SIMPLE**: 単純クエリ（分解不要）
- **COMPARATIVE**: 比較クエリ（"AとBの違い"）
- **AGGREGATION**: 集計クエリ（"合計"、"平均"）
- **MULTI_HOP**: 多段推論クエリ（"Aについて調べて、その後B"）
- **TEMPORAL**: 時系列クエリ（日付・期間指定）
- **CONDITIONAL**: 条件付きクエリ（"もし"、"場合"）

### 2. テンプレートベース分解
正規表現パターンマッチングによる高速分解：
- 比較クエリ: `"PythonとJavaの違い"` → 3つのサブクエリ
- 多段推論: `"Aを調べて、その後B"` → 依存関係付き2クエリ

### 3. LLMベース分解
Claude APIを使用した高度な分解：
- 複雑なクエリの意図理解
- コンテキストに応じた適切な分解
- JSON形式での構造化出力

### 4. 依存関係管理
- サブクエリ間の依存関係をグラフで管理
- トポロジカルソートによる実行順序計算
- 並列実行可能なサブクエリの識別

## インストール

```bash
# 依存関係インストール
pip install langchain langchain-anthropic

# 環境変数設定
export ANTHROPIC_API_KEY="your-api-key"
```

## 使い方

### 基本的な使用例

```python
from tmax_work3.agents.query_decomposition import QueryDecompositionAgent

# エージェント初期化
agent = QueryDecompositionAgent()

# クエリ分解
query = "PythonとJavaの違いは何ですか？"
result = agent.decompose(query)

# 結果確認
print(f"Query Type: {result.query_type}")
print(f"Sub-queries: {len(result.sub_queries)}")

for sq in result.sub_queries:
    print(f"  [{sq.query_id}] {sq.text}")
    print(f"    Dependencies: {sq.dependencies}")
```

### 辞書形式での取得

```python
# 辞書形式で取得（JSON変換可能）
result_dict = agent.decompose_to_dict(query)

import json
print(json.dumps(result_dict, indent=2, ensure_ascii=False))
```

出力例：
```json
{
  "original_query": "PythonとJavaの違いは何ですか？",
  "query_type": "comparative",
  "is_simple": false,
  "sub_queries": [
    {
      "query_id": "sq_0",
      "text": "Pythonについて",
      "dependencies": [],
      "priority": 3
    },
    {
      "query_id": "sq_1",
      "text": "Javaについて",
      "dependencies": [],
      "priority": 3
    },
    {
      "query_id": "sq_2",
      "text": "PythonとJavaの違い",
      "dependencies": ["sq_0", "sq_1"],
      "priority": 1
    }
  ],
  "execution_order": ["sq_0", "sq_1", "sq_2"]
}
```

### 実行可能サブクエリの取得

```python
# 完了済みサブクエリIDを管理
completed_ids = set()

# 実行可能なサブクエリを取得
executable = agent.get_executable_subqueries(result, completed_ids)

for sq in executable:
    print(f"Executing: {sq.text}")
    # ... 検索実行 ...
    completed_ids.add(sq.query_id)
```

## Coordinatorとの統合

### 統合例

```python
from tmax_work3.agents.query_decomposition import QueryDecompositionAgent
from your_hybrid_search import HybridSearchAgent

class QueryDecompositionCoordinator:
    def __init__(self):
        self.decomposition_agent = QueryDecompositionAgent()
        self.hybrid_search = HybridSearchAgent()

    def process_query(self, query: str):
        # Step 1: クエリ分解
        result = self.decomposition_agent.decompose(query)

        # Step 2: サブクエリ実行
        subquery_results = {}
        completed = set()

        for query_id in result.execution_order:
            subquery = next(sq for sq in result.sub_queries if sq.query_id == query_id)

            # 依存関係チェック
            if all(dep in completed for dep in subquery.dependencies):
                # Hybrid Search実行
                search_results = self.hybrid_search.search(subquery.text)
                subquery_results[query_id] = search_results
                completed.add(query_id)

        # Step 3: 結果統合
        return self._aggregate_results(result, subquery_results)
```

詳細な統合例は `/tmax_work3/examples/query_decomposition_integration.py` を参照してください。

## テスト

### テスト実行

```bash
# 全テスト実行
pytest tmax_work3/tests/test_query_decomposition.py -v

# カバレッジ付きテスト
pytest tmax_work3/tests/test_query_decomposition.py --cov=tmax_work3.agents.query_decomposition --cov-report=html
```

### テストカバレッジ

- **クエリ分類**: 6種類のクエリタイプ
- **分解パターン**: テンプレートベース・LLMベース
- **依存関係グラフ**: 構造・一貫性・トポロジカルソート
- **エッジケース**: 空クエリ、長文、特殊文字、多言語
- **パフォーマンス**: 単純クエリ<100ms、複雑クエリ<5s
- **統合テスト**: エンドツーエンド実行

全34テストケース ✅

## 技術仕様

### データ構造

#### SubQuery
```python
@dataclass
class SubQuery:
    query_id: str              # サブクエリID
    text: str                  # サブクエリテキスト
    dependencies: List[str]    # 依存するサブクエリID
    query_type: QueryType      # クエリタイプ
    priority: int              # 実行優先度（1-5）
    metadata: Dict[str, Any]   # メタデータ
```

#### DecompositionResult
```python
@dataclass
class DecompositionResult:
    original_query: str                 # 元のクエリ
    query_type: QueryType               # 分類されたクエリタイプ
    sub_queries: List[SubQuery]         # サブクエリリスト
    dependency_graph: Dict[str, List[str]]  # 依存関係グラフ
    execution_order: List[str]          # 実行順序
    is_simple: bool                     # 単純クエリフラグ
```

### アルゴリズム

#### トポロジカルソート（Kahn's Algorithm）
依存関係グラフから実行順序を計算：
1. 入次数0のノードをキューに追加
2. キューからノードを取り出し、実行順序に追加
3. 依存ノードの入次数をデクリメント
4. 入次数0になったノードをキューに追加
5. キューが空になるまで繰り返し

## パフォーマンス

- **単純クエリ**: < 100ms
- **比較クエリ（テンプレート）**: < 50ms
- **複雑クエリ（LLM）**: < 5s（API呼び出し含む）
- **メモリ使用量**: サブクエリ数に比例（通常 < 1MB）

## 制限事項

- 最大サブクエリ数: 5個（設計上の制限）
- LLMモード: ANTHROPIC_API_KEY必須
- テンプレート対応: 日本語・英語のみ
- 循環依存: 検出しないが、発生しない設計

## ロードマップ

- [ ] 多言語対応（中国語、韓国語）
- [ ] カスタムテンプレート追加機能
- [ ] サブクエリ結果のキャッシング
- [ ] 並列実行の最適化
- [ ] クエリ書き換え機能

## ライセンス

MIT License

## 貢献

Issue・Pull Request歓迎です。

## サポート

質問・バグ報告は Issues へ。
