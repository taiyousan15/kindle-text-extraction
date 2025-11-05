"""
T-Max Ultimate - Evaluator Agent

Best-of-N自動採点システム:
- 複数エージェントの成果物を自動評価
- 機械的・再現的な採点
- 勝者自動決定
- 学習データ蓄積
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import sys
import hashlib

sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


class EvaluatorAgent:
    """
    Evaluator Agent - Best-of-N自動採点

    機能:
    - pytest実行結果の評価
    - 差分の複雑度分析
    - コード品質チェック（Pylint, Bandit）
    - ドキュメント一貫性チェック
    - 総合スコア計算と勝者決定
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()

        # 評価ウェイト（カスタマイズ可能）
        self.weights = {
            "test_pass_rate": 0.5,  # テスト合格率（最重要）
            "diff_complexity": 0.2,  # 差分の複雑度（低いほど良い）
            "code_quality": 0.2,     # コード品質スコア
            "doc_consistency": 0.1   # ドキュメント一貫性
        }

        # エージェント登録
        try:
            self.blackboard.register_agent(
                AgentType.QA,  # 既存のQAタイプを使用（後でEVALUATORを追加）
                worktree="main"
            )
        except:
            pass  # 既に登録されている場合はスキップ

        self.blackboard.log(
            "🏆 Evaluator Agent initialized - Best-of-N scoring system ready",
            level="INFO",
            agent=AgentType.QA
        )

    def evaluate_candidates(self, candidates: List[Dict]) -> Dict:
        """
        複数候補を評価し、勝者を決定

        Args:
            candidates: 候補リスト
                [
                    {
                        "id": "agent-01",
                        "worktree_path": "/path/to/worktree",
                        "branch": "parallel/agent-01"
                    },
                    ...
                ]

        Returns:
            評価結果
                {
                    "evaluated_at": "2025-11-05T20:00:00Z",
                    "candidates": [
                        {
                            "id": "agent-01",
                            "metrics": {...},
                            "score": 0.85
                        },
                        ...
                    ],
                    "winner": "agent-01",
                    "decision_rule": "weighted_sum"
                }
        """
        self.blackboard.log(
            f"🔍 Evaluating {len(candidates)} candidates...",
            level="INFO",
            agent=AgentType.QA
        )

        scores = []

        for candidate in candidates:
            candidate_id = candidate["id"]
            worktree_path = Path(candidate["worktree_path"])

            self.blackboard.log(
                f"📊 Evaluating candidate: {candidate_id}",
                level="INFO",
                agent=AgentType.QA
            )

            # 1. テスト実行
            test_result = self._run_tests(worktree_path)

            # 2. 差分分析
            diff_stats = self._analyze_diff(worktree_path)

            # 3. コード品質チェック
            quality_score = self._check_code_quality(worktree_path)

            # 4. ドキュメント一貫性チェック
            doc_score = self._check_documentation(worktree_path)

            # 5. 総合スコア計算
            final_score = (
                self.weights["test_pass_rate"] * test_result["pass_rate"] +
                self.weights["diff_complexity"] * (1 - diff_stats["complexity_norm"]) +
                self.weights["code_quality"] * quality_score +
                self.weights["doc_consistency"] * doc_score
            )

            scores.append({
                "id": candidate_id,
                "metrics": {
                    "test_pass_rate": test_result["pass_rate"],
                    "test_passed": test_result["passed"],
                    "test_failed": test_result["failed"],
                    "diff_lines": diff_stats["total_lines"],
                    "complexity": diff_stats["complexity"],
                    "quality_score": quality_score,
                    "doc_score": doc_score
                },
                "score": round(final_score, 4)
            })

            self.blackboard.log(
                f"✅ {candidate_id} score: {final_score:.4f}",
                level="INFO",
                agent=AgentType.QA
            )

        # 勝者決定
        winner = max(scores, key=lambda x: x["score"])

        result = {
            "evaluated_at": datetime.now().isoformat(),
            "candidates": scores,
            "winner": winner["id"],
            "winner_score": winner["score"],
            "decision_rule": self._format_decision_rule(),
            "weights": self.weights
        }

        self.blackboard.log(
            f"🥇 Winner: {winner['id']} with score {winner['score']:.4f}",
            level="SUCCESS",
            agent=AgentType.QA
        )

        # Blackboardに記録
        self._record_evaluation(result)

        return result

    def _run_tests(self, worktree_path: Path) -> Dict:
        """
        pytestを実行してテスト結果を取得

        Returns:
            {
                "passed": 10,
                "failed": 2,
                "total": 12,
                "pass_rate": 0.833
            }
        """
        try:
            result = subprocess.run(
                ["pytest", "--tb=short", "-v", "--json-report", "--json-report-file=test_report.json"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            # JSONレポート読み込み
            report_file = worktree_path / "test_report.json"
            if report_file.exists():
                report = json.loads(report_file.read_text())

                passed = report["summary"]["passed"]
                failed = report["summary"]["failed"]
                total = report["summary"]["total"]

                return {
                    "passed": passed,
                    "failed": failed,
                    "total": total,
                    "pass_rate": passed / total if total > 0 else 0.0
                }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Test execution failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )

        # テスト失敗時のデフォルト
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "pass_rate": 0.0
        }

    def _analyze_diff(self, worktree_path: Path) -> Dict:
        """
        git diffを分析して差分の複雑度を評価

        Returns:
            {
                "total_lines": 120,
                "added": 80,
                "deleted": 40,
                "complexity": 3.5,
                "complexity_norm": 0.35
            }
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD~1..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )

            lines = result.stdout.strip().split("\n")
            if not lines:
                return self._default_diff_stats()

            # 最終行から統計情報を抽出
            summary = lines[-1]
            # 例: "10 files changed, 120 insertions(+), 40 deletions(-)"

            added = 0
            deleted = 0

            if "insertion" in summary:
                added = int(summary.split("insertion")[0].split(",")[-1].strip())
            if "deletion" in summary:
                deleted = int(summary.split("deletion")[0].split(",")[-1].strip())

            total_lines = added + deleted

            # 複雑度計算（簡易版: 変更行数の対数）
            import math
            complexity = math.log10(max(total_lines, 1) + 1)
            complexity_norm = min(complexity / 10.0, 1.0)  # 0-1に正規化

            return {
                "total_lines": total_lines,
                "added": added,
                "deleted": deleted,
                "complexity": round(complexity, 2),
                "complexity_norm": round(complexity_norm, 4)
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Diff analysis failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return self._default_diff_stats()

    def _default_diff_stats(self) -> Dict:
        """デフォルトの差分統計"""
        return {
            "total_lines": 0,
            "added": 0,
            "deleted": 0,
            "complexity": 0.0,
            "complexity_norm": 0.0
        }

    def _check_code_quality(self, worktree_path: Path) -> float:
        """
        コード品質をチェック（Pylint, Bandit）

        Returns:
            品質スコア（0-1）
        """
        scores = []

        # Pylint
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", "app/", "tmax_work3/"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Pylintスコアを解析（0-10 → 0-1）
            # 簡易版: エラーがなければ0.8、あれば0.5
            if result.returncode == 0:
                scores.append(0.8)
            else:
                scores.append(0.5)
        except:
            scores.append(0.5)

        # Bandit（セキュリティチェック）
        try:
            result = subprocess.run(
                ["bandit", "-r", "app/", "-f", "json"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Bandit結果を解析
            if result.returncode == 0:
                scores.append(0.9)
            else:
                scores.append(0.6)
        except:
            scores.append(0.6)

        # 平均スコア
        return sum(scores) / len(scores) if scores else 0.5

    def _check_documentation(self, worktree_path: Path) -> float:
        """
        ドキュメント一貫性をチェック

        - README.mdの存在
        - docstringの存在率
        - CHANGELOG.mdの更新

        Returns:
            ドキュメントスコア（0-1）
        """
        score = 0.0

        # README.md存在チェック
        readme = worktree_path / "README.md"
        if readme.exists() and readme.stat().st_size > 100:
            score += 0.4

        # CHANGELOG.md更新チェック
        changelog = worktree_path / "CHANGELOG.md"
        if changelog.exists():
            score += 0.3

        # Pythonファイルのdocstring存在率チェック（簡易版）
        python_files = list(worktree_path.glob("**/*.py"))
        if python_files:
            docstring_count = 0
            for py_file in python_files[:10]:  # 最初の10ファイルをサンプリング
                try:
                    content = py_file.read_text()
                    if '"""' in content or "'''" in content:
                        docstring_count += 1
                except:
                    pass

            docstring_rate = docstring_count / min(len(python_files), 10)
            score += 0.3 * docstring_rate

        return round(score, 4)

    def _format_decision_rule(self) -> str:
        """決定ルールを文字列化"""
        return (
            f"{self.weights['test_pass_rate']}*test_pass + "
            f"{self.weights['diff_complexity']}*(1-diff_norm) + "
            f"{self.weights['code_quality']}*quality + "
            f"{self.weights['doc_consistency']}*doc"
        )

    def _record_evaluation(self, result: Dict):
        """評価結果をBlackboardに記録"""
        # JSONファイルに保存
        eval_dir = self.repo_path / "tmax_work3" / "data" / "evaluations"
        eval_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        eval_file = eval_dir / f"evaluation_{timestamp}.json"

        eval_file.write_text(json.dumps(result, indent=2))

        self.blackboard.log(
            f"💾 Evaluation saved: {eval_file}",
            level="INFO",
            agent=AgentType.QA
        )


# テスト用コード
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="T-Max Evaluator Agent")
    parser.add_argument("--test", action="store_true", help="Run test")
    args = parser.parse_args()

    if args.test:
        print("🧪 Testing Evaluator Agent...")

        evaluator = EvaluatorAgent(".")

        # テスト候補
        candidates = [
            {
                "id": "test-agent-01",
                "worktree_path": ".",
                "branch": "main"
            }
        ]

        # 評価実行
        result = evaluator.evaluate_candidates(candidates)

        print("\n📊 Evaluation Result:")
        print(json.dumps(result, indent=2))

        print("\n✅ Test complete!")
    else:
        print("Usage: python evaluator.py --test")
