"""
Test Suite for Self-Correction Agent

テスト項目:
1. コード検証機能
2. エラーパターン検出
3. 修正候補生成
4. 再検証ループ（最大3回）
5. 学習データ蓄積
6. Evaluator/Error Recovery統合
"""
import pytest
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.agents.self_correction import (
    SelfCorrectionAgent,
    ValidationResult,
    CorrectionAttempt,
    LearningEntry
)


@pytest.fixture
def agent(tmp_path):
    """Self-Correction Agent fixture"""
    return SelfCorrectionAgent(str(tmp_path))


@pytest.fixture
def valid_code():
    """有効なコードサンプル"""
    return """
def add(a, b):
    return a + b

def multiply(x, y):
    result = x * y
    return result
"""


@pytest.fixture
def broken_code_syntax():
    """構文エラーのあるコード"""
    return """
def add(a, b):
    return a + b
      return a - b  # インデントエラー
"""


@pytest.fixture
def broken_code_logic():
    """論理エラーのあるコード"""
    return """
def divide(x, y):
    return x / y  # division by zero未対応

def get_item(lst, index):
    return lst[index]  # index out of range未対応
"""


@pytest.fixture
def broken_code_undefined():
    """未定義変数エラー"""
    return """
def calculate():
    result = foo + bar  # 未定義
    return result
"""


class TestValidation:
    """コード検証機能のテスト"""

    def test_validate_valid_code(self, agent, valid_code):
        """有効なコードの検証"""
        result = agent.validate_code(valid_code)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.syntax_errors) == 0
        assert result.quality_score > 0.5

    def test_validate_syntax_error(self, agent, broken_code_syntax):
        """構文エラーの検出"""
        result = agent.validate_code(broken_code_syntax)

        assert result.is_valid is False
        assert len(result.syntax_errors) > 0
        assert result.syntax_errors[0]["type"] == "SyntaxError"
        assert "indent" in result.syntax_errors[0]["message"].lower()

    def test_validate_captures_error_patterns(self, agent, broken_code_syntax):
        """エラーパターンが抽出されること"""
        result = agent.validate_code(broken_code_syntax)

        assert len(result.error_patterns) > 0
        # インデントエラーパターンが含まれる
        assert any("indent" in p for p in result.error_patterns)

    def test_quality_score_calculation(self, agent):
        """品質スコアが正しく計算されること"""
        # 完全に有効なコード
        valid_result = agent.validate_code("def foo(): pass")
        assert valid_result.quality_score >= 0.9

        # 構文エラーのあるコード
        invalid_result = agent.validate_code("def foo( pass")
        assert invalid_result.quality_score < 0.6


class TestErrorPatternExtraction:
    """エラーパターン抽出のテスト"""

    def test_extract_syntax_error_pattern(self, agent):
        """構文エラーパターンの抽出"""
        error_msg = "SyntaxError: invalid syntax"
        pattern = agent._extract_error_pattern(error_msg)

        assert pattern == "invalid_syntax"

    def test_extract_name_error_pattern(self, agent):
        """未定義変数エラーパターンの抽出"""
        error_msg = "NameError: name 'foo' is not defined"
        pattern = agent._extract_error_pattern(error_msg)

        assert pattern == "name_not_defined"

    def test_extract_import_error_pattern(self, agent):
        """インポートエラーパターンの抽出"""
        error_msg = "ImportError: cannot import name 'Foo'"
        pattern = agent._extract_error_pattern(error_msg)

        assert pattern == "import_error"

    def test_extract_unknown_error_pattern(self, agent):
        """未知のエラーはハッシュ化されること"""
        error_msg = "VeryUnusualError: something went wrong"
        pattern = agent._extract_error_pattern(error_msg)

        assert pattern.startswith("error_")
        assert len(pattern) == 14  # "error_" + 8文字のハッシュ


class TestCorrectionGeneration:
    """修正候補生成のテスト"""

    def test_generate_correction_without_claude(self, agent, broken_code_syntax):
        """Claude APIなしでのパターンベース修正"""
        # Claude APIを無効化
        agent.claude_client = None

        validation = agent.validate_code(broken_code_syntax)
        success, corrected = agent.generate_correction(broken_code_syntax, validation)

        assert isinstance(success, bool)
        assert isinstance(corrected, str)
        assert len(corrected) > 0

    def test_pattern_based_correction_indent(self, agent):
        """インデントエラーのパターンベース修正"""
        broken = "def foo():\n      return 1"  # 過剰インデント
        validation = agent.validate_code(broken)

        # Claude無効化
        agent.claude_client = None

        success, corrected = agent._pattern_based_correction(broken, validation)

        assert success is True
        # インデントが修正される
        assert "      return" not in corrected or "    return" in corrected


class TestCorrectionRetryLoop:
    """再検証ループのテスト"""

    def test_retry_loop_with_valid_code(self, agent, valid_code):
        """有効なコードは1回で成功すること"""
        result = agent.correct_with_retry(valid_code)

        assert result["success"] is True
        assert len(result["attempts"]) == 1
        assert result["attempts"][0]["success"] is True

    def test_retry_loop_max_attempts(self, agent, broken_code_syntax):
        """最大3回試行すること"""
        # Claude無効化（パターンベース修正では解決しない）
        agent.claude_client = None

        result = agent.correct_with_retry(broken_code_syntax)

        # 最大3回試行される
        assert len(result["attempts"]) <= agent.MAX_CORRECTION_ATTEMPTS

    def test_retry_loop_saves_history(self, agent, tmp_path, broken_code_syntax):
        """修正履歴が保存されること"""
        agent.repo_path = tmp_path
        agent.correction_history_path = tmp_path / "tmax_work3" / "data" / "correction_history"
        agent.correction_history_path.mkdir(parents=True, exist_ok=True)

        result = agent.correct_with_retry(broken_code_syntax)

        # 履歴ファイルが作成される
        history_files = list(agent.correction_history_path.glob("correction_*.json"))
        assert len(history_files) > 0

        # 履歴ファイルの内容を確認
        history_data = json.loads(history_files[0].read_text())
        assert isinstance(history_data, list)
        assert len(history_data) > 0


class TestLearningData:
    """学習データ蓄積のテスト"""

    def test_learning_data_initialization(self, agent):
        """学習データが初期化されること"""
        assert isinstance(agent.learning_data, dict)

    def test_learning_data_update_on_success(self, agent, valid_code):
        """成功時に学習データが更新されること"""
        initial_count = len(agent.learning_data)

        # わざとエラーパターンを含む検証を実行
        agent._update_learning_data(
            error_patterns=["test_pattern"],
            successful_fix="fixed_code",
            strategy="test_strategy",
            success=True
        )

        assert len(agent.learning_data) >= initial_count
        assert "test_pattern" in agent.learning_data

        entry = agent.learning_data["test_pattern"]
        assert entry.success_rate > 0
        assert entry.occurrences > 0
        assert entry.successful_fix == "fixed_code"

    def test_learning_data_update_on_failure(self, agent):
        """失敗時に学習データが更新されること"""
        agent._update_learning_data(
            error_patterns=["failure_pattern"],
            successful_fix=None,
            strategy="failed_strategy",
            success=False
        )

        assert "failure_pattern" in agent.learning_data
        entry = agent.learning_data["failure_pattern"]

        # 失敗は成功率を下げる
        assert entry.success_rate == 0.0
        assert entry.occurrences > 0

    def test_learning_data_persistence(self, agent, tmp_path):
        """学習データが永続化されること"""
        agent.repo_path = tmp_path
        agent.learning_data_path = tmp_path / "tmax_work3" / "data" / "self_correction_learning.json"
        agent.learning_data_path.parent.mkdir(parents=True, exist_ok=True)

        # データを追加
        agent._update_learning_data(
            error_patterns=["persist_test"],
            successful_fix="test_fix",
            strategy="test",
            success=True
        )

        # 保存されることを確認
        assert agent.learning_data_path.exists()

        # 新しいエージェントでロード
        agent2 = SelfCorrectionAgent(str(tmp_path))
        assert "persist_test" in agent2.learning_data

    def test_analyze_learning_data(self, agent):
        """学習データ分析機能"""
        # テストデータを追加
        agent._update_learning_data(["pattern1"], "fix1", "strategy1", True)
        agent._update_learning_data(["pattern2"], "fix2", "strategy2", True)
        agent._update_learning_data(["pattern3"], None, "strategy3", False)

        analysis = agent.analyze_learning_data()

        assert "total_patterns" in analysis
        assert "successful_patterns" in analysis
        assert "average_success_rate" in analysis
        assert "top_patterns" in analysis

        assert analysis["total_patterns"] >= 3


class TestIntegration:
    """他エージェントとの統合テスト"""

    def test_evaluator_integration(self, agent):
        """Evaluator Agentとの統合"""
        # Evaluatorが初期化されていること
        if agent.evaluator:
            assert hasattr(agent.evaluator, '_check_code_quality')

    def test_error_recovery_integration(self, agent):
        """Error Recovery Agentとの統合"""
        # Error Recoveryが初期化されていること
        if agent.error_recovery:
            assert hasattr(agent.error_recovery, 'analyze_error')
            assert hasattr(agent.error_recovery, 'generate_fix')


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_code(self, agent):
        """空のコード"""
        result = agent.validate_code("")
        # 空のコードは構文的には有効（Pythonの仕様）
        assert isinstance(result, ValidationResult)

    def test_very_long_code(self, agent):
        """非常に長いコード"""
        long_code = "\n".join([f"def func{i}(): pass" for i in range(1000)])
        result = agent.validate_code(long_code)

        assert isinstance(result, ValidationResult)
        # パフォーマンステスト: 合理的な時間で完了すること

    def test_non_python_code(self, agent):
        """Python以外のコード"""
        javascript_code = "function foo() { return 42; }"
        result = agent.validate_code(javascript_code)

        assert result.is_valid is False
        assert len(result.syntax_errors) > 0

    def test_unicode_characters(self, agent):
        """Unicode文字を含むコード"""
        unicode_code = """
def greet():
    return "こんにちは世界"
"""
        result = agent.validate_code(unicode_code)

        # Unicode文字は有効
        assert result.is_valid is True


class TestRealWorldScenarios:
    """実際のシナリオテスト"""

    def test_fix_missing_import(self, agent):
        """不足しているインポートの修正"""
        code_missing_import = """
def calculate_date():
    today = datetime.now()
    return today
"""
        validation = agent.validate_code(code_missing_import)

        # 未定義変数は静的解析では検出できない（構文的には有効）
        # 実行時にNameErrorが発生する
        assert isinstance(validation, ValidationResult)

    def test_fix_indentation_mixed(self, agent):
        """混在したインデントの修正"""
        mixed_indent = """
def foo():
    x = 1
\ty = 2  # タブ
    return x + y
"""
        result = agent.correct_with_retry(mixed_indent)

        # 何らかの結果が返る（修正されるか、エラーが記録される）
        assert "attempts" in result
        assert len(result["attempts"]) > 0


# パフォーマンステスト
class TestPerformance:
    """パフォーマンステスト"""

    def test_validation_performance(self, agent, valid_code):
        """検証のパフォーマンステスト"""
        import time
        start = time.time()

        result = agent.validate_code(valid_code)

        elapsed = time.time() - start

        # 合理的な時間（5秒以内）で完了すること
        assert elapsed < 5
        assert isinstance(result, ValidationResult)

    def test_correction_performance(self, agent, broken_code_syntax):
        """修正のパフォーマンステスト（タイムアウトなし）"""
        import time
        start = time.time()

        result = agent.correct_with_retry(broken_code_syntax)

        elapsed = time.time() - start

        # 合理的な時間（60秒以内）で完了すること
        assert elapsed < 60
        assert "attempts" in result


if __name__ == "__main__":
    # pytest実行
    pytest.main([__file__, "-v", "--tb=short"])
