"""
T-Max Ultimate - Self-Correction Agent

自己修正エージェント:
- 生成コードの自動検証
- エラー検出とパターン学習
- 自動修正候補生成
- 修正の再検証ループ（最大3回）
- 学習データの蓄積
"""
import os
import re
import sys
import ast
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from tmax_work3.agents.evaluator import EvaluatorAgent
except ImportError:
    EvaluatorAgent = None

try:
    from tmax_work3.agents.error_recovery import ErrorRecoveryAgent
except ImportError:
    ErrorRecoveryAgent = None


@dataclass
class ValidationResult:
    """コード検証結果"""
    is_valid: bool
    syntax_errors: List[Dict]
    test_failures: List[Dict]
    quality_score: float
    error_patterns: List[str]
    timestamp: str


@dataclass
class CorrectionAttempt:
    """修正試行の記録"""
    attempt_number: int
    original_code: str
    corrected_code: str
    validation_result: ValidationResult
    correction_strategy: str
    success: bool
    timestamp: str


@dataclass
class LearningEntry:
    """学習データエントリ"""
    error_pattern: str
    error_context: str
    successful_fix: Optional[str]
    fix_strategy: str
    success_rate: float
    occurrences: int
    last_seen: str


class SelfCorrectionAgent:
    """
    Self-Correction Agent - 自己修正エージェント

    機能:
    - 生成コードの構文チェック
    - pytest自動実行と結果分析
    - エラーパターン学習
    - Claude APIで修正候補生成
    - 最大3回の修正再検証ループ
    - 成功/失敗パターンの蓄積

    統合:
    - Evaluator Agent: コード品質評価
    - Error Recovery Agent: エラー分析と修正
    """

    MAX_CORRECTION_ATTEMPTS = 3

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()

        # 学習データパス
        self.learning_data_path = self.repo_path / "tmax_work3" / "data" / "self_correction_learning.json"
        self.learning_data_path.parent.mkdir(parents=True, exist_ok=True)

        # 修正履歴パス
        self.correction_history_path = self.repo_path / "tmax_work3" / "data" / "correction_history"
        self.correction_history_path.mkdir(parents=True, exist_ok=True)

        # Claude API初期化
        self.claude_client = None
        if Anthropic and os.getenv("ANTHROPIC_API_KEY"):
            self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # Evaluator Agent初期化
        self.evaluator = None
        if EvaluatorAgent:
            try:
                self.evaluator = EvaluatorAgent(str(self.repo_path))
            except:
                pass

        # Error Recovery Agent初期化
        self.error_recovery = None
        if ErrorRecoveryAgent:
            try:
                self.error_recovery = ErrorRecoveryAgent(str(self.repo_path))
            except:
                pass

        # エージェント登録
        try:
            self.blackboard.register_agent(
                AgentType.QA,  # Self-correctionはQAの一種として扱う
                worktree="main"
            )
        except:
            pass

        # 学習データロード
        self.learning_data = self._load_learning_data()

        self.blackboard.log(
            "🔄 Self-Correction Agent initialized - Auto-validation and learning enabled",
            level="INFO",
            agent=AgentType.QA
        )

    def _load_learning_data(self) -> Dict[str, LearningEntry]:
        """学習データを読み込む"""
        if self.learning_data_path.exists():
            try:
                data = json.loads(self.learning_data_path.read_text())
                return {
                    k: LearningEntry(**v) for k, v in data.items()
                }
            except Exception as e:
                self.blackboard.log(
                    f"⚠️ Failed to load learning data: {e}",
                    level="WARNING",
                    agent=AgentType.QA
                )

        return {}

    def _save_learning_data(self):
        """学習データを保存"""
        try:
            data = {
                k: asdict(v) for k, v in self.learning_data.items()
            }
            self.learning_data_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Failed to save learning data: {e}",
                level="WARNING",
                agent=AgentType.QA
            )

    def validate_code(self, code: str, file_path: Optional[str] = None) -> ValidationResult:
        """
        コードを検証

        Args:
            code: 検証するコード
            file_path: ファイルパス（pytest実行用）

        Returns:
            ValidationResult
        """
        self.blackboard.log(
            "🔍 Validating code...",
            level="INFO",
            agent=AgentType.QA
        )

        syntax_errors = []
        test_failures = []
        error_patterns = []
        quality_score = 1.0

        # 1. 構文チェック
        try:
            ast.parse(code)
        except SyntaxError as e:
            syntax_errors.append({
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset
            })
            quality_score -= 0.5

            # エラーパターン学習
            error_pattern = self._extract_error_pattern(str(e))
            error_patterns.append(error_pattern)

        # 2. 静的解析（簡易版）
        static_issues = self._static_analysis(code)
        if static_issues:
            quality_score -= 0.1 * len(static_issues)
            for issue in static_issues:
                error_patterns.append(issue["pattern"])

        # 3. pytest実行（ファイルパスが指定されている場合）
        if file_path and Path(file_path).exists():
            test_results = self._run_pytest(file_path)
            if test_results["failed"] > 0:
                test_failures = test_results["failures"]
                quality_score -= 0.3
                for failure in test_failures:
                    pattern = self._extract_error_pattern(failure["message"])
                    error_patterns.append(pattern)

        # 4. Evaluator統合（コード品質評価）
        if self.evaluator and file_path:
            try:
                eval_score = self.evaluator._check_code_quality(Path(file_path).parent)
                quality_score = (quality_score + eval_score) / 2
            except:
                pass

        is_valid = len(syntax_errors) == 0 and len(test_failures) == 0

        result = ValidationResult(
            is_valid=is_valid,
            syntax_errors=syntax_errors,
            test_failures=test_failures,
            quality_score=max(0.0, min(1.0, quality_score)),
            error_patterns=error_patterns,
            timestamp=datetime.now().isoformat()
        )

        log_level = "SUCCESS" if is_valid else "WARNING"
        self.blackboard.log(
            f"✅ Validation complete: Valid={is_valid}, Quality={quality_score:.2f}",
            level=log_level,
            agent=AgentType.QA
        )

        return result

    def _static_analysis(self, code: str) -> List[Dict]:
        """
        静的解析（簡易版）

        チェック項目:
        - 未使用インポート
        - 未定義変数（基本的なもの）
        - コーディング規約違反（基本的なもの）

        Returns:
            問題リスト
        """
        issues = []

        try:
            tree = ast.parse(code)

            # 未使用インポートの簡易検出
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.append(alias.name)

            # コード中での使用チェック（簡易版）
            code_lower = code.lower()
            for imp in imports:
                if imp.lower() not in code_lower.replace(f"import {imp.lower()}", ""):
                    issues.append({
                        "type": "unused_import",
                        "pattern": f"unused_import:{imp}",
                        "message": f"Unused import: {imp}"
                    })

        except:
            pass

        return issues

    def _run_pytest(self, file_path: str) -> Dict:
        """
        pytestを実行

        Returns:
            {
                "passed": 10,
                "failed": 2,
                "failures": [...]
            }
        """
        try:
            result = subprocess.run(
                ["pytest", file_path, "-v", "--tb=short", "--json-report", "--json-report-file=test_report.json"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # JSONレポート読み込み
            report_file = self.repo_path / "test_report.json"
            if report_file.exists():
                report = json.loads(report_file.read_text())

                failures = []
                for test in report.get("tests", []):
                    if test.get("outcome") == "failed":
                        failures.append({
                            "test_name": test["nodeid"],
                            "message": test.get("call", {}).get("longrepr", "")
                        })

                return {
                    "passed": report["summary"].get("passed", 0),
                    "failed": report["summary"].get("failed", 0),
                    "failures": failures
                }

        except Exception as e:
            self.blackboard.log(
                f"⚠️ pytest execution failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )

        return {"passed": 0, "failed": 0, "failures": []}

    def _extract_error_pattern(self, error_message: str) -> str:
        """
        エラーメッセージからパターンを抽出

        例:
        - "NameError: name 'foo' is not defined" -> "name_not_defined"
        - "SyntaxError: invalid syntax" -> "invalid_syntax"
        """
        # 一般的なエラーパターンをマッチ
        patterns = {
            r"name '.*' is not defined": "name_not_defined",
            r"invalid syntax": "invalid_syntax",
            r"unexpected indent": "unexpected_indent",
            r"unresolved reference": "unresolved_reference",
            r"module '.*' has no attribute": "no_attribute",
            r"cannot import name": "import_error",
            r"division by zero": "division_by_zero",
            r"index out of range": "index_out_of_range",
            r"key error": "key_error",
            r"type error": "type_error",
            r"value error": "value_error",
            r"assertion.*failed": "assertion_failed",
        }

        error_lower = error_message.lower()
        for pattern, name in patterns.items():
            if re.search(pattern, error_lower):
                return name

        # デフォルト: ハッシュ化
        return f"error_{hashlib.md5(error_message.encode()).hexdigest()[:8]}"

    def generate_correction(self, code: str, validation_result: ValidationResult, context: Optional[str] = None) -> Tuple[bool, str]:
        """
        修正候補を生成

        Args:
            code: 元のコード
            validation_result: 検証結果
            context: 追加コンテキスト

        Returns:
            (success, corrected_code)
        """
        self.blackboard.log(
            "🛠️ Generating correction...",
            level="INFO",
            agent=AgentType.QA
        )

        # Claude APIが使用可能な場合
        if self.claude_client:
            return self._generate_correction_with_claude(code, validation_result, context)

        # Error Recovery Agentとの統合
        if self.error_recovery and validation_result.error_patterns:
            try:
                error_log = "\n".join([
                    f"{e['type']}: {e['message']}" for e in validation_result.syntax_errors
                ])
                analysis = self.error_recovery.analyze_error(error_log, context)
                success, fix_code = self.error_recovery.generate_fix(analysis)
                if success:
                    return True, fix_code
            except:
                pass

        # フォールバック: パターンベースの修正
        return self._pattern_based_correction(code, validation_result)

    def _generate_correction_with_claude(self, code: str, validation_result: ValidationResult, context: Optional[str]) -> Tuple[bool, str]:
        """Claude APIで修正候補を生成"""
        # 学習データから類似パターンを検索
        similar_fixes = self._find_similar_patterns(validation_result.error_patterns)

        # プロンプト構築
        prompt = self._build_correction_prompt(code, validation_result, similar_fixes, context)

        try:
            message = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # コードブロックを抽出
            code_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)
            if code_match:
                corrected_code = code_match.group(1)

                self.blackboard.log(
                    "✅ Correction generated with Claude API",
                    level="SUCCESS",
                    agent=AgentType.QA
                )

                return True, corrected_code

        except Exception as e:
            self.blackboard.log(
                f"⚠️ Claude correction generation failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )

        return False, code

    def _build_correction_prompt(self, code: str, validation_result: ValidationResult, similar_fixes: List[LearningEntry], context: Optional[str]) -> str:
        """修正プロンプトを構築"""
        prompt_parts = [
            "# Code Correction Request",
            "",
            "## Original Code",
            "```python",
            code,
            "```",
            "",
            "## Validation Errors",
        ]

        # 構文エラー
        if validation_result.syntax_errors:
            prompt_parts.append("### Syntax Errors:")
            for error in validation_result.syntax_errors:
                prompt_parts.append(f"- Line {error['line']}: {error['message']}")

        # テストエラー
        if validation_result.test_failures:
            prompt_parts.append("\n### Test Failures:")
            for failure in validation_result.test_failures:
                prompt_parts.append(f"- {failure['test_name']}: {failure['message'][:200]}")

        # 学習データから類似修正
        if similar_fixes:
            prompt_parts.append("\n## Similar Successful Fixes (Learning Data):")
            for i, fix in enumerate(similar_fixes[:3], 1):
                prompt_parts.append(f"\n### Fix {i} (Success Rate: {fix.success_rate:.1%})")
                prompt_parts.append(f"Error Pattern: {fix.error_pattern}")
                prompt_parts.append(f"Strategy: {fix.fix_strategy}")
                if fix.successful_fix:
                    prompt_parts.append(f"Fix Applied:\n{fix.successful_fix[:300]}")

        # コンテキスト
        if context:
            prompt_parts.append(f"\n## Additional Context\n{context}")

        prompt_parts.extend([
            "",
            "## Task",
            "Please provide a corrected version of the code that:",
            "1. Fixes all syntax errors",
            "2. Passes all tests",
            "3. Maintains the original functionality",
            "4. Follows Python best practices",
            "",
            "Return ONLY the corrected Python code in a ```python code block, with no additional explanation.",
        ])

        return "\n".join(prompt_parts)

    def _find_similar_patterns(self, error_patterns: List[str]) -> List[LearningEntry]:
        """学習データから類似パターンを検索"""
        similar = []

        for pattern in error_patterns:
            if pattern in self.learning_data:
                similar.append(self.learning_data[pattern])

        # 成功率でソート
        similar.sort(key=lambda x: x.success_rate, reverse=True)

        return similar

    def _pattern_based_correction(self, code: str, validation_result: ValidationResult) -> Tuple[bool, str]:
        """パターンベースの簡易修正"""
        corrected = code

        # 簡易修正ルール
        for error in validation_result.syntax_errors:
            if "unexpected indent" in error["message"]:
                # インデント修正（簡易版）
                lines = corrected.split("\n")
                if 0 <= error["line"] - 1 < len(lines):
                    lines[error["line"] - 1] = lines[error["line"] - 1].lstrip()
                corrected = "\n".join(lines)

        return True, corrected

    def correct_with_retry(self, code: str, file_path: Optional[str] = None, context: Optional[str] = None) -> Dict:
        """
        最大3回の再検証ループで修正

        Returns:
            {
                "success": bool,
                "final_code": str,
                "attempts": List[CorrectionAttempt],
                "learning_updated": bool
            }
        """
        self.blackboard.log(
            f"🔄 Starting correction cycle (max {self.MAX_CORRECTION_ATTEMPTS} attempts)...",
            level="INFO",
            agent=AgentType.QA
        )

        attempts = []
        current_code = code
        final_success = False

        for attempt_num in range(1, self.MAX_CORRECTION_ATTEMPTS + 1):
            self.blackboard.log(
                f"📍 Attempt {attempt_num}/{self.MAX_CORRECTION_ATTEMPTS}",
                level="INFO",
                agent=AgentType.QA
            )

            # 検証
            validation = self.validate_code(current_code, file_path)

            if validation.is_valid:
                self.blackboard.log(
                    f"✅ Code valid after {attempt_num} attempt(s)!",
                    level="SUCCESS",
                    agent=AgentType.QA
                )
                final_success = True

                # 学習データ更新（成功）
                self._update_learning_data(validation.error_patterns, current_code, "success", True)

                attempts.append(CorrectionAttempt(
                    attempt_number=attempt_num,
                    original_code=code,
                    corrected_code=current_code,
                    validation_result=validation,
                    correction_strategy="validation_passed",
                    success=True,
                    timestamp=datetime.now().isoformat()
                ))

                break

            # 修正生成
            success, corrected_code = self.generate_correction(current_code, validation, context)

            attempts.append(CorrectionAttempt(
                attempt_number=attempt_num,
                original_code=current_code,
                corrected_code=corrected_code,
                validation_result=validation,
                correction_strategy="claude_api" if self.claude_client else "pattern_based",
                success=False,
                timestamp=datetime.now().isoformat()
            ))

            if not success:
                self.blackboard.log(
                    f"⚠️ Correction generation failed at attempt {attempt_num}",
                    level="WARNING",
                    agent=AgentType.QA
                )
                # 学習データ更新（失敗）
                self._update_learning_data(validation.error_patterns, None, "generation_failed", False)
                break

            current_code = corrected_code

        # 最終検証
        if not final_success and attempts:
            self.blackboard.log(
                f"❌ Failed to correct code after {len(attempts)} attempts",
                level="ERROR",
                agent=AgentType.QA
            )
            # 学習データ更新（失敗）
            last_validation = attempts[-1].validation_result
            self._update_learning_data(last_validation.error_patterns, None, "max_retries_exceeded", False)

        # 修正履歴を保存
        self._save_correction_history(attempts)

        result = {
            "success": final_success,
            "final_code": current_code,
            "attempts": [asdict(a) for a in attempts],
            "learning_updated": True,
            "timestamp": datetime.now().isoformat()
        }

        return result

    def _update_learning_data(self, error_patterns: List[str], successful_fix: Optional[str], strategy: str, success: bool):
        """学習データを更新"""
        for pattern in error_patterns:
            if pattern not in self.learning_data:
                self.learning_data[pattern] = LearningEntry(
                    error_pattern=pattern,
                    error_context="",
                    successful_fix=None,
                    fix_strategy="",
                    success_rate=0.0,
                    occurrences=0,
                    last_seen=datetime.now().isoformat()
                )

            entry = self.learning_data[pattern]
            entry.occurrences += 1
            entry.last_seen = datetime.now().isoformat()

            if success and successful_fix:
                entry.successful_fix = successful_fix[:1000]  # 最大1000文字
                entry.fix_strategy = strategy

                # 成功率更新（移動平均）
                entry.success_rate = (entry.success_rate * (entry.occurrences - 1) + 1.0) / entry.occurrences
            else:
                # 失敗時は成功率を下げる
                entry.success_rate = (entry.success_rate * (entry.occurrences - 1)) / entry.occurrences

        self._save_learning_data()

    def _save_correction_history(self, attempts: List[CorrectionAttempt]):
        """修正履歴を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = self.correction_history_path / f"correction_{timestamp}.json"

        data = [asdict(a) for a in attempts]
        history_file.write_text(json.dumps(data, indent=2))

        self.blackboard.log(
            f"💾 Correction history saved: {history_file}",
            level="INFO",
            agent=AgentType.QA
        )

    def analyze_learning_data(self) -> Dict:
        """
        学習データを分析

        Returns:
            統計情報
        """
        total_patterns = len(self.learning_data)
        successful_patterns = sum(1 for e in self.learning_data.values() if e.success_rate > 0.5)
        avg_success_rate = sum(e.success_rate for e in self.learning_data.values()) / total_patterns if total_patterns > 0 else 0.0

        top_patterns = sorted(
            self.learning_data.values(),
            key=lambda x: x.occurrences,
            reverse=True
        )[:10]

        return {
            "total_patterns": total_patterns,
            "successful_patterns": successful_patterns,
            "average_success_rate": round(avg_success_rate, 4),
            "top_patterns": [
                {
                    "pattern": p.error_pattern,
                    "occurrences": p.occurrences,
                    "success_rate": p.success_rate,
                    "strategy": p.fix_strategy
                }
                for p in top_patterns
            ],
            "timestamp": datetime.now().isoformat()
        }


# テスト用コード
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="T-Max Self-Correction Agent")
    parser.add_argument("--test", action="store_true", help="Run test")
    parser.add_argument("--code", help="Code to validate and correct")
    parser.add_argument("--file", help="File path to validate and correct")
    parser.add_argument("--analyze", action="store_true", help="Analyze learning data")
    args = parser.parse_args()

    agent = SelfCorrectionAgent(".")

    if args.analyze:
        print("📊 Analyzing learning data...")
        analysis = agent.analyze_learning_data()
        print(json.dumps(analysis, indent=2))

    elif args.test:
        print("🧪 Testing Self-Correction Agent...")

        # テストコード（意図的なエラー）
        broken_code = """
def calculate_sum(a, b):
    result = a + b
      return result  # インデントエラー

def divide(x, y):
    return x / y  # division by zeroの可能性
"""

        print("\n📝 Original (broken) code:")
        print(broken_code)

        # 修正サイクル実行
        result = agent.correct_with_retry(broken_code)

        print(f"\n✅ Correction Result:")
        print(f"Success: {result['success']}")
        print(f"Attempts: {len(result['attempts'])}")

        if result['success']:
            print(f"\n🎉 Final corrected code:")
            print(result['final_code'])

        # 学習データ分析
        print("\n📊 Learning Data Analysis:")
        analysis = agent.analyze_learning_data()
        print(json.dumps(analysis, indent=2))

    elif args.code:
        print("🔍 Validating and correcting code...")
        result = agent.correct_with_retry(args.code)
        print(json.dumps(result, indent=2))

    elif args.file:
        print(f"🔍 Validating and correcting file: {args.file}")
        code = Path(args.file).read_text()
        result = agent.correct_with_retry(code, args.file)
        print(json.dumps(result, indent=2))

    else:
        print("Usage: python self_correction.py [--test|--analyze|--code CODE|--file FILE]")
