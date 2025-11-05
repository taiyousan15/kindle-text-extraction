# Self-Correction Agent - 自己修正エージェント

## 概要

Self-Correction Agentは、生成されたコードを自動的に検証し、エラーを検出・修正する自己改善型エージェントです。最大3回の再検証ループで修正を試み、成功/失敗のパターンを学習データとして蓄積します。

## 主要機能

### 1. コード自動検証
- **構文チェック**: `ast.parse()`による構文エラー検出
- **静的解析**: 未使用インポート、コーディング規約違反の検出
- **pytest自動実行**: テストファイルがある場合、自動でテスト実行
- **品質スコア計算**: 総合的なコード品質を0-1のスコアで評価

### 2. エラーパターン学習
- エラーメッセージから再利用可能なパターンを抽出
- 類似エラーの検出と対応策の提案
- 出現頻度と成功率の追跡

### 3. 自動修正候補生成
- **Claude API統合**: 高度な修正候補を生成（オプション）
- **Error Recovery Agent統合**: 既知のエラーパターンから修正を生成
- **パターンベース修正**: 簡易的な自動修正（フォールバック）

### 4. 再検証ループ（最大3回）
1. コードを検証
2. エラーがあれば修正候補を生成
3. 修正を適用して再検証
4. 成功するまで繰り返し（最大3回）

### 5. 学習データ蓄積
- 各エラーパターンの成功率を記録
- 成功した修正方法を保存
- 修正履歴をJSON形式で永続化

### 6. Evaluator/Error Recovery統合
- **Evaluator Agent**: コード品質評価を統合
- **Error Recovery Agent**: エラー分析と修正戦略を統合

## アーキテクチャ

```
Self-Correction Agent
│
├── validate_code()          # コード検証
│   ├── 構文チェック (ast.parse)
│   ├── 静的解析
│   ├── pytest実行（オプション）
│   └── 品質スコア計算
│
├── generate_correction()    # 修正候補生成
│   ├── Claude API（優先）
│   ├── Error Recovery Agent
│   └── パターンベース修正
│
├── correct_with_retry()     # 再検証ループ
│   ├── 最大3回試行
│   ├── 学習データ更新
│   └── 修正履歴保存
│
└── analyze_learning_data()  # 学習データ分析
    ├── 総パターン数
    ├── 成功率統計
    └── 頻出パターン
```

## データ構造

### ValidationResult
```python
@dataclass
class ValidationResult:
    is_valid: bool                  # コードが有効か
    syntax_errors: List[Dict]       # 構文エラーリスト
    test_failures: List[Dict]       # テスト失敗リスト
    quality_score: float            # 品質スコア (0-1)
    error_patterns: List[str]       # 検出されたエラーパターン
    timestamp: str                  # 検証時刻
```

### CorrectionAttempt
```python
@dataclass
class CorrectionAttempt:
    attempt_number: int             # 試行回数
    original_code: str              # 元のコード
    corrected_code: str             # 修正後のコード
    validation_result: ValidationResult  # 検証結果
    correction_strategy: str        # 修正戦略
    success: bool                   # 成功したか
    timestamp: str                  # 試行時刻
```

### LearningEntry
```python
@dataclass
class LearningEntry:
    error_pattern: str              # エラーパターン名
    error_context: str              # エラーコンテキスト
    successful_fix: Optional[str]   # 成功した修正コード
    fix_strategy: str               # 修正戦略
    success_rate: float             # 成功率 (0-1)
    occurrences: int                # 出現回数
    last_seen: str                  # 最終出現日時
```

## 使用方法

### 1. 基本的な使い方

```python
from tmax_work3.agents.self_correction import SelfCorrectionAgent

# エージェント初期化
agent = SelfCorrectionAgent(repository_path=".")

# コード検証のみ
code = """
def add(a, b):
    return a + b
"""
result = agent.validate_code(code)
print(f"Valid: {result.is_valid}")
print(f"Quality Score: {result.quality_score}")

# 修正ループ実行
broken_code = """
def add(a, b):
      return a + b  # インデントエラー
"""
result = agent.correct_with_retry(broken_code)
print(f"Success: {result['success']}")
print(f"Final Code:\n{result['final_code']}")
```

### 2. ファイルを指定して検証

```python
# ファイルパスを指定するとpytestも実行される
result = agent.correct_with_retry(
    code=code,
    file_path="app/utils/calculator.py",
    context="Main calculator module"
)
```

### 3. 学習データ分析

```python
analysis = agent.analyze_learning_data()
print(f"Total patterns: {analysis['total_patterns']}")
print(f"Average success rate: {analysis['average_success_rate']:.2%}")

# 頻出パターンを確認
for pattern in analysis['top_patterns']:
    print(f"{pattern['pattern']}: {pattern['success_rate']:.2%}")
```

### 4. コマンドライン使用

```bash
# テスト実行
python tmax_work3/agents/self_correction.py --test

# コード検証と修正
python tmax_work3/agents/self_correction.py --code "def foo(): pass"

# ファイル検証と修正
python tmax_work3/agents/self_correction.py --file app/utils/helper.py

# 学習データ分析
python tmax_work3/agents/self_correction.py --analyze
```

## 環境変数

```bash
# Claude API Key（オプション: 高度な修正に使用）
export ANTHROPIC_API_KEY="your-api-key"
```

APIキーがない場合、パターンベース修正とError Recovery Agentの統合のみ使用されます。

## テスト

### テスト実行

```bash
# 全テスト実行
pytest tmax_work3/tests/test_self_correction.py -v

# 特定のテストクラス実行
pytest tmax_work3/tests/test_self_correction.py::TestValidation -v

# カバレッジ付き実行
pytest tmax_work3/tests/test_self_correction.py --cov=tmax_work3.agents.self_correction
```

### テストカバレッジ

- **28個のテストケース** (100%合格)
- コード検証機能
- エラーパターン抽出
- 修正候補生成
- 再検証ループ
- 学習データ蓄積
- Evaluator/Error Recovery統合
- エッジケース
- 実際のシナリオ
- パフォーマンステスト

## ディレクトリ構造

```
tmax_work3/
├── agents/
│   ├── self_correction.py              # メインエージェント
│   ├── evaluator.py                    # Evaluator Agent（統合）
│   └── error_recovery.py               # Error Recovery Agent（統合）
│
├── data/
│   ├── self_correction_learning.json   # 学習データ
│   └── correction_history/             # 修正履歴
│       └── correction_YYYYMMDD_HHMMSS.json
│
└── tests/
    └── test_self_correction.py         # テストスイート
```

## パフォーマンス

- **検証速度**: 通常のコード（<100行）で < 0.1秒
- **修正ループ**: 最大3回試行、通常1-2回で成功
- **メモリ使用**: 学習データは自動で最適化（最大1000文字/エントリ）

## ベストプラクティス

### 1. 段階的な修正
```python
# 大きなコードは分割して検証
for module in large_codebase:
    result = agent.correct_with_retry(module)
    if result['success']:
        apply_fix(result['final_code'])
```

### 2. 学習データの定期分析
```python
# 週次レポート
analysis = agent.analyze_learning_data()
send_report(analysis)
```

### 3. Error Recovery Agentとの連携
```python
# エラー検出 → 分析 → 修正 → 検証のフルサイクル
error_log = detect_error()
error_analysis = error_recovery.analyze_error(error_log)
fix = error_recovery.generate_fix(error_analysis, file_path)

# Self-Correctionで検証
validation = agent.validate_code(fix)
if not validation.is_valid:
    final_result = agent.correct_with_retry(fix)
```

## 制限事項

1. **静的解析の限界**: 実行時エラー（未定義変数など）は検出できない
2. **最大試行回数**: 3回の試行で修正できない場合は失敗を記録
3. **Claude API依存**: 高度な修正にはAPIキーが必要（フォールバックあり）

## トラブルシューティング

### Q: 修正が成功しない
A: 以下を確認してください：
- Claude API Keyが設定されているか
- Error Recovery Agentが初期化されているか
- エラーパターンが学習データに存在するか

### Q: pytestが実行されない
A: `file_path`パラメータを指定してください：
```python
result = agent.correct_with_retry(code, file_path="path/to/file.py")
```

### Q: 学習データが保存されない
A: `tmax_work3/data/`ディレクトリへの書き込み権限を確認してください。

## 今後の拡張予定

- [ ] AST変換による高度な修正
- [ ] 複数修正候補のランキング
- [ ] LLMファインチューニング用データセット生成
- [ ] リアルタイム修正提案（IDE統合）
- [ ] 修正の影響範囲分析

## 参考資料

- [Evaluator Agent Documentation](./EVALUATOR_README.md)
- [Error Recovery Agent Documentation](./ERROR_RECOVERY_README.md)
- [T-Max Work3 Architecture](../README.md)

## ライセンス

MIT License

## 作成者

T-Max Ultimate Project Team
2025-11-05
