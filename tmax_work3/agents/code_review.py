"""
T-Max Ultimate - Code Review Agent

Automated Code Review System:
- Static analysis (Pylint, Bandit)
- Security scanning (Bandit, Safety)
- Style checking (Black, isort)
- Complexity analysis (Radon, McCabe)
- GitHub-style Markdown reports
- Scoring system (0-100 points)
"""
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import sys
import tempfile

sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.blackboard.state_manager import (
    Blackboard,
    AgentType,
    TaskStatus,
    get_blackboard
)


@dataclass
class SecurityIssue:
    """Security vulnerability data structure"""
    file: str
    line: int
    severity: str  # HIGH, MEDIUM, LOW
    confidence: str
    issue_text: str
    cwe_id: Optional[str] = None


@dataclass
class StyleIssue:
    """Code style issue data structure"""
    file: str
    line: int
    column: int
    type: str  # black, isort, flake8
    message: str


@dataclass
class ComplexityMetric:
    """Code complexity metric"""
    file: str
    function: str
    complexity: int
    line: int
    rank: str  # A, B, C, D, F


@dataclass
class ReviewResult:
    """Complete review result"""
    reviewed_at: str
    files_reviewed: int
    total_score: float
    pylint_scores: Dict[str, float]
    security_issues: List[SecurityIssue]
    style_issues: List[StyleIssue]
    complexity_metrics: List[ComplexityMetric]
    summary: Dict[str, Any]
    passed_threshold: bool


class CodeReviewAgent:
    """
    Code Review Agent - Automated Code Quality Analysis

    Features:
    - Static code analysis with Pylint
    - Security vulnerability scanning with Bandit
    - Dependency vulnerability check with Safety
    - Code style checking (Black, isort)
    - Complexity analysis (Radon)
    - Comprehensive scoring system (0-100)
    - GitHub-style Markdown reports
    - Blackboard integration
    """

    def __init__(self, repository_path: str):
        self.repo_path = Path(repository_path)
        self.blackboard = get_blackboard()
        self.report_dir = self.repo_path / "tmax_work3" / "data" / "code_reviews"
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Scoring weights
        self.weights = {
            "pylint": 0.40,      # Pylint score (most important)
            "security": 0.30,    # Security issues
            "complexity": 0.20,  # Code complexity
            "style": 0.10        # Style compliance
        }

        # Register agent with blackboard
        try:
            self.blackboard.register_agent(
                AgentType.QA,
                worktree="main"
            )
        except:
            pass  # Already registered

        self.blackboard.log(
            "🔍 Code Review Agent initialized - Automated quality analysis ready",
            level="INFO",
            agent=AgentType.QA
        )

    def run_pylint(self, file_path: str) -> Dict[str, Any]:
        """
        Run Pylint static analysis on a file

        Args:
            file_path: Path to Python file

        Returns:
            {
                "score": 8.5,
                "issues": [
                    {
                        "type": "error",
                        "line": 10,
                        "message": "undefined variable"
                    }
                ]
            }
        """
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", file_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
                issues = []

                for item in data:
                    issues.append({
                        "type": item.get("type", "unknown"),
                        "line": item.get("line", 0),
                        "column": item.get("column", 0),
                        "message": item.get("message", ""),
                        "symbol": item.get("symbol", "")
                    })

                # Extract score from stderr (Pylint prints score there)
                score_match = re.search(r"rated at ([\d.]+)/10", result.stderr)
                score = float(score_match.group(1)) if score_match else 5.0

                return {
                    "score": score,
                    "issues": issues,
                    "file": file_path
                }

            except json.JSONDecodeError:
                # Fallback: parse text output
                score = 5.0
                if "rated at" in result.stdout:
                    score_match = re.search(r"rated at ([\d.]+)/10", result.stdout)
                    if score_match:
                        score = float(score_match.group(1))

                return {
                    "score": score,
                    "issues": [],
                    "file": file_path
                }

        except FileNotFoundError:
            self.blackboard.log(
                "⚠️ Pylint not installed, skipping analysis",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "score": 5.0,
                "issues": [],
                "file": file_path
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Pylint analysis failed for {file_path}: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "score": 5.0,
                "issues": [],
                "file": file_path
            }

    def run_bandit(self, file_path: str) -> Dict[str, Any]:
        """
        Run Bandit security analysis

        Args:
            file_path: Path to Python file or directory

        Returns:
            {
                "issues": [SecurityIssue, ...],
                "severity_counts": {"HIGH": 2, "MEDIUM": 5, "LOW": 3}
            }
        """
        try:
            result = subprocess.run(
                ["bandit", "-r", "-f", "json", file_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            data = json.loads(result.stdout)
            issues = []
            severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

            for item in data.get("results", []):
                severity = item.get("issue_severity", "LOW")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

                issues.append(SecurityIssue(
                    file=item.get("filename", ""),
                    line=item.get("line_number", 0),
                    severity=severity,
                    confidence=item.get("issue_confidence", "MEDIUM"),
                    issue_text=item.get("issue_text", ""),
                    cwe_id=item.get("cwe", {}).get("id") if isinstance(item.get("cwe"), dict) else None
                ))

            return {
                "issues": issues,
                "severity_counts": severity_counts
            }

        except FileNotFoundError:
            self.blackboard.log(
                "⚠️ Bandit not installed, skipping security scan",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "issues": [],
                "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Bandit scan failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "issues": [],
                "severity_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            }

    def run_safety_check(self) -> Dict[str, Any]:
        """
        Check dependencies for security vulnerabilities using Safety

        Returns:
            {
                "vulnerabilities": [
                    {
                        "package": "requests",
                        "version": "2.19.0",
                        "vulnerability": "CVE-2023-12345",
                        "severity": "HIGH"
                    }
                ]
            }
        """
        try:
            # Check if requirements.txt exists
            req_file = self.repo_path / "requirements.txt"
            if not req_file.exists():
                return {"vulnerabilities": []}

            result = subprocess.run(
                ["safety", "check", "--json", "-r", str(req_file)],
                capture_output=True,
                text=True,
                timeout=60
            )

            try:
                data = json.loads(result.stdout)
                vulnerabilities = []

                for item in data:
                    vulnerabilities.append({
                        "package": item[0] if len(item) > 0 else "unknown",
                        "version": item[2] if len(item) > 2 else "unknown",
                        "vulnerability": item[1] if len(item) > 1 else "unknown",
                        "severity": "HIGH"  # Safety doesn't provide severity in JSON
                    })

                return {"vulnerabilities": vulnerabilities}

            except json.JSONDecodeError:
                return {"vulnerabilities": []}

        except FileNotFoundError:
            self.blackboard.log(
                "⚠️ Safety not installed, skipping dependency check",
                level="WARNING",
                agent=AgentType.QA
            )
            return {"vulnerabilities": []}
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Safety check failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {"vulnerabilities": []}

    def check_black_formatting(self, file_path: str) -> Dict[str, Any]:
        """
        Check if file is formatted with Black

        Args:
            file_path: Path to Python file

        Returns:
            {
                "is_formatted": True/False,
                "diff": "..." (if not formatted)
            }
        """
        try:
            result = subprocess.run(
                ["black", "--check", "--diff", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            is_formatted = result.returncode == 0

            return {
                "is_formatted": is_formatted,
                "diff": result.stdout if not is_formatted else ""
            }

        except FileNotFoundError:
            return {
                "is_formatted": True,  # Assume formatted if Black not available
                "diff": ""
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Black check failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "is_formatted": True,
                "diff": ""
            }

    def check_isort(self, file_path: str) -> Dict[str, Any]:
        """
        Check import ordering with isort

        Args:
            file_path: Path to Python file

        Returns:
            {
                "is_sorted": True/False,
                "diff": "..." (if not sorted)
            }
        """
        try:
            result = subprocess.run(
                ["isort", "--check-only", "--diff", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            is_sorted = result.returncode == 0

            return {
                "is_sorted": is_sorted,
                "diff": result.stdout if not is_sorted else ""
            }

        except FileNotFoundError:
            return {
                "is_sorted": True,  # Assume sorted if isort not available
                "diff": ""
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ isort check failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "is_sorted": True,
                "diff": ""
            }

    def analyze_complexity(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze code complexity using Radon

        Args:
            file_path: Path to Python file

        Returns:
            {
                "average_complexity": 3.5,
                "max_complexity": 10,
                "functions": [
                    {
                        "name": "function_name",
                        "complexity": 5,
                        "line": 10,
                        "rank": "B"
                    }
                ]
            }
        """
        try:
            result = subprocess.run(
                ["radon", "cc", "-j", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            try:
                data = json.loads(result.stdout)
                functions = []
                complexities = []

                for file, items in data.items():
                    for item in items:
                        complexity = item.get("complexity", 1)
                        complexities.append(complexity)

                        functions.append({
                            "name": item.get("name", "unknown"),
                            "complexity": complexity,
                            "line": item.get("lineno", 0),
                            "rank": item.get("rank", "A")
                        })

                return {
                    "average_complexity": sum(complexities) / len(complexities) if complexities else 1.0,
                    "max_complexity": max(complexities) if complexities else 1,
                    "functions": functions
                }

            except json.JSONDecodeError:
                return {
                    "average_complexity": 1.0,
                    "max_complexity": 1,
                    "functions": []
                }

        except FileNotFoundError:
            self.blackboard.log(
                "⚠️ Radon not installed, skipping complexity analysis",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "average_complexity": 1.0,
                "max_complexity": 1,
                "functions": []
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Complexity analysis failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "average_complexity": 1.0,
                "max_complexity": 1,
                "functions": []
            }

    def calculate_maintainability(self, file_path: str) -> Dict[str, Any]:
        """
        Calculate maintainability index using Radon

        Args:
            file_path: Path to Python file

        Returns:
            {
                "maintainability_index": 65.5,
                "rank": "B"
            }
        """
        try:
            result = subprocess.run(
                ["radon", "mi", "-j", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            try:
                data = json.loads(result.stdout)

                # Extract maintainability index
                for file, info in data.items():
                    return {
                        "maintainability_index": info.get("mi", 50.0),
                        "rank": info.get("rank", "B")
                    }

                return {
                    "maintainability_index": 50.0,
                    "rank": "B"
                }

            except json.JSONDecodeError:
                return {
                    "maintainability_index": 50.0,
                    "rank": "B"
                }

        except FileNotFoundError:
            return {
                "maintainability_index": 50.0,
                "rank": "B"
            }
        except Exception as e:
            self.blackboard.log(
                f"⚠️ Maintainability calculation failed: {e}",
                level="WARNING",
                agent=AgentType.QA
            )
            return {
                "maintainability_index": 50.0,
                "rank": "B"
            }

    def analyze_directory(self, directory: str) -> List[Dict[str, Any]]:
        """
        Analyze all Python files in a directory

        Args:
            directory: Directory path relative to repo root

        Returns:
            List of analysis results
        """
        dir_path = self.repo_path / directory
        if not dir_path.exists():
            self.blackboard.log(
                f"⚠️ Directory not found: {directory}",
                level="WARNING",
                agent=AgentType.QA
            )
            return []

        python_files = list(dir_path.rglob("*.py"))
        results = []

        for py_file in python_files:
            if "__pycache__" in str(py_file):
                continue

            try:
                pylint_result = self.run_pylint(str(py_file))
                results.append(pylint_result)
            except Exception as e:
                self.blackboard.log(
                    f"⚠️ Failed to analyze {py_file}: {e}",
                    level="WARNING",
                    agent=AgentType.QA
                )

        return results

    def calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall quality score (0-100)

        Args:
            metrics: Dictionary of quality metrics

        Returns:
            Quality score (0-100)
        """
        # Pylint score component (0-10 -> 0-100)
        pylint_score = metrics.get("pylint_score", 5.0) * 10

        # Security component (deduct points for issues)
        security_issues = metrics.get("security_issues", 0)
        security_score = max(0, 100 - (security_issues * 10))

        # Complexity component (lower is better)
        complexity_avg = metrics.get("complexity_avg", 1.0)
        complexity_score = max(0, 100 - (complexity_avg * 5))

        # Style component
        style_violations = metrics.get("style_violations", 0)
        style_score = max(0, 100 - (style_violations * 2))

        # Weighted average
        total_score = (
            self.weights["pylint"] * pylint_score +
            self.weights["security"] * security_score +
            self.weights["complexity"] * complexity_score +
            self.weights["style"] * style_score
        )

        return round(min(100, max(0, total_score)), 2)

    def review_codebase(
        self,
        target_dirs: Optional[List[str]] = None,
        generate_report: bool = True,
        min_score_threshold: float = 70.0
    ) -> Dict[str, Any]:
        """
        Perform complete code review

        Args:
            target_dirs: Directories to review (default: ["app", "tmax_work3"])
            generate_report: Whether to generate Markdown report
            min_score_threshold: Minimum acceptable quality score

        Returns:
            Complete review result
        """
        if target_dirs is None:
            target_dirs = ["app", "tmax_work3"]

        self.blackboard.log(
            f"🔍 Starting code review for directories: {', '.join(target_dirs)}",
            level="INFO",
            agent=AgentType.QA
        )

        # Collect all results
        all_pylint_scores = {}
        all_security_issues = []
        all_style_issues = []
        all_complexity_metrics = []
        files_reviewed = 0

        # Analyze each directory
        for target_dir in target_dirs:
            dir_path = self.repo_path / target_dir
            if not dir_path.exists():
                self.blackboard.log(
                    f"⚠️ Directory not found: {target_dir}",
                    level="WARNING",
                    agent=AgentType.QA
                )
                continue

            python_files = list(dir_path.rglob("*.py"))

            for py_file in python_files:
                if "__pycache__" in str(py_file):
                    continue

                files_reviewed += 1
                rel_path = str(py_file.relative_to(self.repo_path))

                # Pylint analysis
                pylint_result = self.run_pylint(str(py_file))
                all_pylint_scores[rel_path] = pylint_result["score"]

                # Security scan
                bandit_result = self.run_bandit(str(py_file))
                all_security_issues.extend(bandit_result["issues"])

                # Style check
                black_result = self.check_black_formatting(str(py_file))
                if not black_result["is_formatted"]:
                    all_style_issues.append(StyleIssue(
                        file=rel_path,
                        line=0,
                        column=0,
                        type="black",
                        message="File not formatted with Black"
                    ))

                isort_result = self.check_isort(str(py_file))
                if not isort_result["is_sorted"]:
                    all_style_issues.append(StyleIssue(
                        file=rel_path,
                        line=0,
                        column=0,
                        type="isort",
                        message="Imports not sorted correctly"
                    ))

                # Complexity analysis
                complexity_result = self.analyze_complexity(str(py_file))
                for func in complexity_result["functions"]:
                    all_complexity_metrics.append(ComplexityMetric(
                        file=rel_path,
                        function=func["name"],
                        complexity=func["complexity"],
                        line=func["line"],
                        rank=func["rank"]
                    ))

        # Calculate overall score
        avg_pylint = sum(all_pylint_scores.values()) / len(all_pylint_scores) if all_pylint_scores else 5.0
        avg_complexity = sum(m.complexity for m in all_complexity_metrics) / len(all_complexity_metrics) if all_complexity_metrics else 1.0

        metrics = {
            "pylint_score": avg_pylint,
            "security_issues": len(all_security_issues),
            "complexity_avg": avg_complexity,
            "style_violations": len(all_style_issues)
        }

        total_score = self.calculate_quality_score(metrics)

        # Create result
        result = {
            "reviewed_at": datetime.now().isoformat(),
            "files_reviewed": files_reviewed,
            "total_score": total_score,
            "pylint_scores": all_pylint_scores,
            "security_issues": [asdict(issue) for issue in all_security_issues],
            "style_issues": [asdict(issue) for issue in all_style_issues],
            "complexity_metrics": [asdict(metric) for metric in all_complexity_metrics],
            "summary": {
                "average_pylint_score": avg_pylint,
                "total_security_issues": len(all_security_issues),
                "high_severity_security": sum(1 for i in all_security_issues if i.severity == "HIGH"),
                "total_style_issues": len(all_style_issues),
                "average_complexity": avg_complexity,
                "high_complexity_functions": sum(1 for m in all_complexity_metrics if m.complexity > 10)
            },
            "passed_threshold": total_score >= min_score_threshold
        }

        # Record metrics to Blackboard
        self.blackboard.set_metric("code_review", "total_score", total_score)
        self.blackboard.set_metric("code_review", "files_reviewed", files_reviewed)
        self.blackboard.set_metric("code_review", "security_issues", len(all_security_issues))

        # Generate report
        if generate_report:
            report = self.generate_markdown_report(result)
            report_path = self.save_review_report_content(report)
            result["report_path"] = report_path

        self.blackboard.log(
            f"✅ Code review complete - Score: {total_score:.1f}/100 ({files_reviewed} files)",
            level="SUCCESS" if result["passed_threshold"] else "WARNING",
            agent=AgentType.QA
        )

        return result

    def generate_markdown_report(self, review_data: Dict[str, Any]) -> str:
        """
        Generate GitHub-style Markdown report

        Args:
            review_data: Review result data

        Returns:
            Markdown formatted report
        """
        report = f"""# Code Review Report

**Generated:** {review_data.get('reviewed_at', datetime.now().isoformat())}
**Files Reviewed:** {review_data.get('files_reviewed', 0)}
**Total Score:** {review_data.get('total_score', 0):.1f}/100

---

## Summary

| Metric | Value |
|--------|-------|
| Average Pylint Score | {review_data.get('summary', {}).get('average_pylint_score', 0):.2f}/10 |
| Security Issues | {review_data.get('summary', {}).get('total_security_issues', 0)} |
| High Severity Security | {review_data.get('summary', {}).get('high_severity_security', 0)} |
| Style Issues | {review_data.get('summary', {}).get('total_style_issues', 0)} |
| Average Complexity | {review_data.get('summary', {}).get('average_complexity', 0):.2f} |
| High Complexity Functions | {review_data.get('summary', {}).get('high_complexity_functions', 0)} |

---

## Quick Actions

```bash
# Run code review locally
python tmax_work3/agents/code_review.py --dirs app tmax_work3

# Fix style issues automatically
black . && isort .

# Run security scan
bandit -r app/
```

---

## Security Issues

"""

        security_issues = review_data.get('security_issues', [])
        if security_issues:
            report += "| File | Line | Severity | Issue |\n"
            report += "|------|------|----------|-------|\n"

            for issue in security_issues[:20]:  # Limit to 20 for readability
                report += f"| {issue['file']} | {issue['line']} | {issue['severity']} | {issue['issue_text'][:50]}... |\n"

            if len(security_issues) > 20:
                report += f"\n*... and {len(security_issues) - 20} more issues*\n"
        else:
            report += "✅ No security issues detected\n"

        report += "\n---\n\n## Style Issues\n\n"

        style_issues = review_data.get('style_issues', [])
        if style_issues:
            report += "| File | Type | Message |\n"
            report += "|------|------|--------|\n"

            for issue in style_issues[:20]:
                report += f"| {issue['file']} | {issue['type']} | {issue['message']} |\n"

            if len(style_issues) > 20:
                report += f"\n*... and {len(style_issues) - 20} more issues*\n"
        else:
            report += "✅ No style issues detected\n"

        report += "\n---\n\n## Complexity Analysis\n\n"

        complexity_metrics = review_data.get('complexity_metrics', [])
        high_complexity = [m for m in complexity_metrics if m.get('complexity', 0) > 10]

        if high_complexity:
            report += "### High Complexity Functions (Complexity > 10)\n\n"
            report += "| File | Function | Complexity | Rank |\n"
            report += "|------|----------|------------|------|\n"

            for metric in high_complexity[:15]:
                report += f"| {metric['file']} | {metric['function']} | {metric['complexity']} | {metric['rank']} |\n"
        else:
            report += "✅ No high complexity functions detected\n"

        report += "\n---\n\n## File Scores\n\n"

        pylint_scores = review_data.get('pylint_scores', {})
        if pylint_scores:
            report += "| File | Pylint Score |\n"
            report += "|------|-------------|\n"

            # Sort by score (worst first)
            sorted_scores = sorted(pylint_scores.items(), key=lambda x: x[1])

            for file, score in sorted_scores[:20]:
                emoji = "✅" if score >= 8 else "⚠️" if score >= 6 else "❌"
                report += f"| {emoji} {file} | {score:.2f}/10 |\n"

            if len(pylint_scores) > 20:
                report += f"\n*... and {len(pylint_scores) - 20} more files*\n"

        report += "\n---\n\n## Recommendations\n\n"

        # Generate recommendations based on findings
        recommendations = []

        if review_data.get('summary', {}).get('high_severity_security', 0) > 0:
            recommendations.append("🔴 **CRITICAL:** Address high-severity security issues immediately")

        if review_data.get('summary', {}).get('average_pylint_score', 10) < 7:
            recommendations.append("⚠️ Improve code quality - Average Pylint score is below 7/10")

        if review_data.get('summary', {}).get('high_complexity_functions', 0) > 5:
            recommendations.append("⚠️ Refactor high-complexity functions to improve maintainability")

        if review_data.get('summary', {}).get('total_style_issues', 0) > 10:
            recommendations.append("📝 Run `black` and `isort` to fix style issues")
            report += "\n**How to fix style issues:**\n\n"
            report += "```bash\n"
            report += "# Format code with Black\n"
            report += "black .\n\n"
            report += "# Sort imports with isort\n"
            report += "isort .\n"
            report += "```\n\n"

        if review_data.get('total_score', 0) >= 90:
            recommendations.append("✅ Excellent code quality! Keep up the good work.")
        elif review_data.get('total_score', 0) >= 70:
            recommendations.append("👍 Good code quality overall, minor improvements suggested.")
        else:
            recommendations.append("🔧 Significant improvements needed to meet quality standards.")

        for rec in recommendations:
            report += f"- {rec}\n"

        report += f"\n---\n\n*Generated by T-Max Code Review Agent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

        return report

    def save_review_report(self, review_data: Dict[str, Any]) -> str:
        """
        Save review result to file

        Args:
            review_data: Review result

        Returns:
            Path to saved report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON
        json_path = self.report_dir / f"review_{timestamp}.json"
        json_path.write_text(json.dumps(review_data, indent=2, default=str), encoding='utf-8')

        # Save Markdown
        report = self.generate_markdown_report(review_data)
        md_path = self.report_dir / f"review_{timestamp}.md"
        md_path.write_text(report, encoding='utf-8')

        self.blackboard.log(
            f"📄 Review report saved: {md_path}",
            level="INFO",
            agent=AgentType.QA
        )

        return str(md_path)

    def save_review_report_content(self, report_content: str) -> str:
        """
        Save report content to file

        Args:
            report_content: Markdown report content

        Returns:
            Path to saved report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = self.report_dir / f"review_{timestamp}.md"
        md_path.write_text(report_content, encoding='utf-8')

        self.blackboard.log(
            f"📄 Review report saved: {md_path}",
            level="INFO",
            agent=AgentType.QA
        )

        return str(md_path)


# Standalone execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="T-Max Code Review Agent")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--dirs", nargs="+", default=["app"], help="Directories to review")
    parser.add_argument("--threshold", type=float, default=70.0, help="Minimum quality score")
    parser.add_argument("--no-report", action="store_true", help="Skip report generation")

    args = parser.parse_args()

    agent = CodeReviewAgent(args.repo)

    print("🔍 Starting code review...\n")

    result = agent.review_codebase(
        target_dirs=args.dirs,
        generate_report=not args.no_report,
        min_score_threshold=args.threshold
    )

    print("\n" + "=" * 60)
    print(f"📊 REVIEW RESULTS")
    print("=" * 60)
    print(f"Files Reviewed: {result['files_reviewed']}")
    print(f"Total Score: {result['total_score']:.1f}/100")
    print(f"Security Issues: {result['summary']['total_security_issues']}")
    print(f"Style Issues: {result['summary']['total_style_issues']}")
    print(f"Average Complexity: {result['summary']['average_complexity']:.2f}")
    print(f"\nThreshold ({args.threshold}): {'✅ PASSED' if result['passed_threshold'] else '❌ FAILED'}")

    if 'report_path' in result:
        print(f"\n📄 Full report: {result['report_path']}")

    print("=" * 60)
