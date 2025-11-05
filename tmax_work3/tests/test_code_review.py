"""
Test suite for Code Review Agent

Tests:
- Static code analysis (Pylint, Bandit)
- Style checking (Black, isort)
- Complexity analysis (Radon, McCabe)
- Security scanning
- Report generation
- Blackboard integration
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from tmax_work3.agents.code_review import (
    CodeReviewAgent,
    ReviewResult,
    SecurityIssue,
    StyleIssue,
    ComplexityMetric
)
from tmax_work3.blackboard.state_manager import AgentType


@pytest.fixture
def temp_repo():
    """Create a temporary repository for testing"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create sample Python files
    (repo_path / "app").mkdir(parents=True, exist_ok=True)

    # Good code sample
    good_code = '''"""
Sample module with good code quality
"""

def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


class Calculator:
    """Simple calculator class"""

    def add(self, x: int, y: int) -> int:
        """Add two numbers"""
        return x + y
'''

    # Bad code sample (for testing)
    bad_code = '''
import os
import subprocess

def bad_function(user_input):
    # Security issue: command injection
    os.system(f"echo {user_input}")

    # Complexity issue
    if True:
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            print("Too complex")

    # Style issue: unused variable
    unused_var = 123

    return None
'''

    (repo_path / "app" / "good_module.py").write_text(good_code)
    (repo_path / "app" / "bad_module.py").write_text(bad_code)

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def code_review_agent(temp_repo):
    """Create CodeReviewAgent instance"""
    return CodeReviewAgent(str(temp_repo))


class TestCodeReviewAgentInitialization:
    """Test agent initialization"""

    def test_agent_initialization(self, code_review_agent):
        """Test that agent initializes correctly"""
        assert code_review_agent is not None
        assert code_review_agent.repo_path.exists()
        assert code_review_agent.blackboard is not None

    def test_report_directory_creation(self, code_review_agent):
        """Test that report directory is created"""
        report_dir = code_review_agent.repo_path / "tmax_work3" / "data" / "code_reviews"
        assert report_dir.exists()


class TestStaticAnalysis:
    """Test static code analysis functionality"""

    def test_pylint_analysis(self, code_review_agent, temp_repo):
        """Test Pylint static analysis"""
        file_path = temp_repo / "app" / "good_module.py"
        result = code_review_agent.run_pylint(str(file_path))

        assert result is not None
        assert "score" in result
        assert "issues" in result
        assert result["score"] >= 0
        assert result["score"] <= 10

    def test_pylint_with_bad_code(self, code_review_agent, temp_repo):
        """Test Pylint detects issues in bad code"""
        file_path = temp_repo / "app" / "bad_module.py"
        result = code_review_agent.run_pylint(str(file_path))

        assert result is not None
        assert len(result["issues"]) > 0
        assert result["score"] < 10

    def test_analyze_directory(self, code_review_agent):
        """Test analyzing entire directory"""
        results = code_review_agent.analyze_directory("app")

        assert len(results) > 0
        assert all("score" in r for r in results)


class TestSecurityScanning:
    """Test security vulnerability scanning"""

    def test_bandit_security_scan(self, code_review_agent, temp_repo):
        """Test Bandit security scanning"""
        file_path = temp_repo / "app" / "bad_module.py"
        result = code_review_agent.run_bandit(str(file_path))

        assert result is not None
        assert "issues" in result
        assert "severity_counts" in result

    def test_detect_security_issues(self, code_review_agent, temp_repo):
        """Test that security issues are detected"""
        file_path = temp_repo / "app" / "bad_module.py"
        result = code_review_agent.run_bandit(str(file_path))

        # Should detect os.system usage as security issue
        assert len(result["issues"]) > 0

    def test_safety_check(self, code_review_agent):
        """Test Safety dependency vulnerability check"""
        result = code_review_agent.run_safety_check()

        assert result is not None
        assert "vulnerabilities" in result


class TestStyleChecking:
    """Test code style checking"""

    def test_black_format_check(self, code_review_agent, temp_repo):
        """Test Black formatting check"""
        file_path = temp_repo / "app" / "good_module.py"
        result = code_review_agent.check_black_formatting(str(file_path))

        assert result is not None
        assert "is_formatted" in result

    def test_isort_import_check(self, code_review_agent, temp_repo):
        """Test isort import ordering check"""
        file_path = temp_repo / "app" / "bad_module.py"
        result = code_review_agent.check_isort(str(file_path))

        assert result is not None
        assert "is_sorted" in result


class TestComplexityAnalysis:
    """Test code complexity analysis"""

    def test_radon_complexity(self, code_review_agent, temp_repo):
        """Test Radon cyclomatic complexity"""
        file_path = temp_repo / "app" / "bad_module.py"
        result = code_review_agent.analyze_complexity(str(file_path))

        assert result is not None
        assert "average_complexity" in result
        assert "max_complexity" in result
        assert "functions" in result

    def test_detect_high_complexity(self, code_review_agent, temp_repo):
        """Test detection of high complexity code"""
        file_path = temp_repo / "app" / "bad_module.py"
        result = code_review_agent.analyze_complexity(str(file_path))

        # Bad code should have higher complexity
        assert result["max_complexity"] > 1

    def test_maintainability_index(self, code_review_agent, temp_repo):
        """Test maintainability index calculation"""
        file_path = temp_repo / "app" / "good_module.py"
        result = code_review_agent.calculate_maintainability(str(file_path))

        assert result is not None
        assert "maintainability_index" in result
        assert 0 <= result["maintainability_index"] <= 100


class TestReportGeneration:
    """Test review report generation"""

    def test_generate_markdown_report(self, code_review_agent, temp_repo):
        """Test Markdown report generation"""
        review_data = {
            "reviewed_at": "2025-11-05T12:00:00",
            "files_reviewed": 2,
            "total_score": 75,
            "issues": [],
            "security_issues": [],
            "complexity_metrics": {}
        }

        report = code_review_agent.generate_markdown_report(review_data)

        assert report is not None
        assert isinstance(report, str)
        assert "# Code Review Report" in report
        assert "Total Score" in report

    def test_save_report_to_file(self, code_review_agent):
        """Test saving report to file"""
        review_data = {
            "reviewed_at": "2025-11-05T12:00:00",
            "total_score": 85
        }

        report_path = code_review_agent.save_review_report(review_data)

        assert report_path is not None
        assert Path(report_path).exists()

    def test_report_contains_github_style_formatting(self, code_review_agent):
        """Test that report uses GitHub-style Markdown"""
        review_data = {
            "reviewed_at": "2025-11-05T12:00:00",
            "files_reviewed": 1,
            "total_score": 90,
            "issues": [{
                "file": "test.py",
                "line": 10,
                "severity": "error",
                "message": "Test issue"
            }]
        }

        report = code_review_agent.generate_markdown_report(review_data)

        # Check for GitHub-style elements
        assert "```" in report  # Code blocks
        assert "- " in report or "* " in report  # List items (markdown lists)
        assert "##" in report  # Headers
        assert "|" in report  # Tables


class TestScoringSystem:
    """Test scoring system (0-100 points)"""

    def test_calculate_quality_score(self, code_review_agent):
        """Test quality score calculation"""
        metrics = {
            "pylint_score": 8.5,
            "security_issues": 2,
            "complexity_avg": 3.5,
            "style_violations": 5
        }

        score = code_review_agent.calculate_quality_score(metrics)

        assert 0 <= score <= 100
        assert isinstance(score, (int, float))

    def test_perfect_score(self, code_review_agent):
        """Test perfect score calculation"""
        metrics = {
            "pylint_score": 10.0,
            "security_issues": 0,
            "complexity_avg": 1.0,
            "style_violations": 0
        }

        score = code_review_agent.calculate_quality_score(metrics)

        assert score >= 95  # Should be near perfect

    def test_low_score_for_bad_code(self, code_review_agent):
        """Test low score for problematic code"""
        metrics = {
            "pylint_score": 3.0,
            "security_issues": 10,
            "complexity_avg": 15.0,
            "style_violations": 20
        }

        score = code_review_agent.calculate_quality_score(metrics)

        assert score < 50  # Should be low score


class TestBlackboardIntegration:
    """Test integration with Blackboard system"""

    def test_log_to_blackboard(self, code_review_agent):
        """Test logging to Blackboard"""
        initial_log_count = len(code_review_agent.blackboard.logs)

        code_review_agent.blackboard.log(
            "Test log message",
            level="INFO",
            agent=AgentType.QA
        )

        assert len(code_review_agent.blackboard.logs) > initial_log_count

    def test_record_metrics(self, code_review_agent):
        """Test recording metrics to Blackboard"""
        code_review_agent.blackboard.set_metric(
            "code_review",
            "test_score",
            85.5
        )

        metrics = code_review_agent.blackboard.get_metrics()
        assert "code_review" in metrics
        assert metrics["code_review"]["test_score"] == 85.5


class TestFullReviewCycle:
    """Test complete code review cycle"""

    def test_full_review_workflow(self, code_review_agent):
        """Test complete review workflow"""
        result = code_review_agent.review_codebase(
            target_dirs=["app"],
            generate_report=True
        )

        assert result is not None
        assert "total_score" in result
        assert "files_reviewed" in result
        assert "report_path" in result

    def test_review_with_thresholds(self, code_review_agent):
        """Test review with quality thresholds"""
        result = code_review_agent.review_codebase(
            target_dirs=["app"],
            min_score_threshold=70
        )

        assert "passed_threshold" in result
        assert isinstance(result["passed_threshold"], bool)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_review_nonexistent_directory(self, code_review_agent):
        """Test handling of non-existent directory"""
        result = code_review_agent.review_codebase(
            target_dirs=["nonexistent_dir"]
        )

        assert result is not None
        # Should handle gracefully, not crash

    def test_review_empty_directory(self, code_review_agent, temp_repo):
        """Test reviewing empty directory"""
        empty_dir = temp_repo / "empty"
        empty_dir.mkdir(exist_ok=True)

        result = code_review_agent.review_codebase(
            target_dirs=["empty"]
        )

        assert result["files_reviewed"] == 0

    def test_invalid_python_file(self, code_review_agent, temp_repo):
        """Test handling of invalid Python syntax"""
        invalid_file = temp_repo / "app" / "invalid.py"
        invalid_file.write_text("def invalid syntax here")

        result = code_review_agent.analyze_directory("app")

        # Should not crash, should report error
        assert result is not None


class TestEvaluatorIntegration:
    """Test integration with Evaluator Agent"""

    def test_provide_metrics_to_evaluator(self, code_review_agent):
        """Test providing review metrics to Evaluator"""
        review_result = code_review_agent.review_codebase(
            target_dirs=["app"]
        )

        # Metrics should be in format expected by Evaluator
        assert "total_score" in review_result
        assert isinstance(review_result["total_score"], (int, float))

    def test_quality_score_format(self, code_review_agent):
        """Test quality score is in 0-100 range for Evaluator"""
        metrics = {
            "pylint_score": 7.5,
            "security_issues": 1,
            "complexity_avg": 2.0,
            "style_violations": 3
        }

        score = code_review_agent.calculate_quality_score(metrics)

        assert 0 <= score <= 100
        assert isinstance(score, (int, float))
