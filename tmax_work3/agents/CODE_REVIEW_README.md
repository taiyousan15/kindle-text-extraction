# Code Review Agent - Complete Implementation

## Overview

The Code Review Agent is a comprehensive automated code quality analysis system that performs static analysis, security scanning, style checking, and complexity analysis on Python codebases.

## Features

### 1. Static Code Analysis (Pylint)
- Analyzes code quality with Pylint
- Scores files on a 0-10 scale
- Detects common coding issues and anti-patterns
- Provides detailed issue reports

### 2. Security Scanning
- **Bandit**: Scans for security vulnerabilities
  - Command injection risks
  - SQL injection vulnerabilities
  - Insecure cryptography usage
  - Hardcoded credentials
- **Safety**: Checks dependencies for known CVEs
- Categorizes issues by severity (HIGH, MEDIUM, LOW)

### 3. Style Checking
- **Black**: Python code formatter compliance
- **isort**: Import statement ordering
- Enforces PEP 8 style guidelines
- Detects style violations automatically

### 4. Complexity Analysis
- **Radon**: Cyclomatic complexity measurement
- **McCabe**: Function complexity scoring
- Maintainability index calculation
- Identifies high-complexity functions (>10)

### 5. Scoring System
- 0-100 point scoring system
- Weighted metrics:
  - Pylint: 40%
  - Security: 30%
  - Complexity: 20%
  - Style: 10%

### 6. Report Generation
- GitHub-style Markdown reports
- Detailed issue tables
- Visual indicators (emojis)
- Quick action commands
- Recommendations based on findings

### 7. Blackboard Integration
- Logs all activities to central Blackboard
- Records metrics for tracking
- Integrates with Evaluator Agent
- Supports distributed review workflows

## Installation

```bash
# Install required tools
pip install pylint bandit radon safety black isort

# Verify installation
pylint --version
bandit --version
radon --version
```

## Usage

### Command Line

```bash
# Basic usage
python tmax_work3/agents/code_review.py --dirs app

# Custom threshold
python tmax_work3/agents/code_review.py --dirs app tests --threshold 80

# Skip report generation
python tmax_work3/agents/code_review.py --dirs app --no-report
```

### Programmatic Usage

```python
from tmax_work3.agents.code_review import CodeReviewAgent

# Initialize agent
agent = CodeReviewAgent(".")

# Review codebase
result = agent.review_codebase(
    target_dirs=["app", "tmax_work3"],
    generate_report=True,
    min_score_threshold=70.0
)

# Access results
print(f"Total Score: {result['total_score']:.1f}/100")
print(f"Files Reviewed: {result['files_reviewed']}")
print(f"Security Issues: {result['summary']['total_security_issues']}")
```

### Integration with Evaluator

```python
from tmax_work3.agents.code_review import CodeReviewAgent
from tmax_work3.agents.evaluator import EvaluatorAgent

# Run code review
review_agent = CodeReviewAgent(".")
review_result = review_agent.review_codebase(target_dirs=["app"])

# Use in evaluation
evaluator = EvaluatorAgent(".")
candidates = [
    {
        "id": "candidate-1",
        "worktree_path": "./worktree1",
        "branch": "feature/new-code"
    }
]

# Evaluator will use code quality metrics
evaluation = evaluator.evaluate_candidates(candidates)
```

## API Reference

### CodeReviewAgent Class

#### `__init__(repository_path: str)`
Initialize the Code Review Agent.

**Parameters:**
- `repository_path`: Path to the repository root

#### `review_codebase(target_dirs, generate_report, min_score_threshold)`
Perform complete code review.

**Parameters:**
- `target_dirs`: List of directories to review
- `generate_report`: Whether to generate Markdown report (default: True)
- `min_score_threshold`: Minimum acceptable score (default: 70.0)

**Returns:**
```python
{
    "reviewed_at": "2025-11-05T20:00:00",
    "files_reviewed": 25,
    "total_score": 85.5,
    "pylint_scores": {...},
    "security_issues": [...],
    "style_issues": [...],
    "complexity_metrics": [...],
    "summary": {...},
    "passed_threshold": True,
    "report_path": "path/to/report.md"
}
```

#### `run_pylint(file_path: str)`
Run Pylint analysis on a single file.

**Returns:**
```python
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
```

#### `run_bandit(file_path: str)`
Run security analysis with Bandit.

**Returns:**
```python
{
    "issues": [SecurityIssue, ...],
    "severity_counts": {"HIGH": 2, "MEDIUM": 5, "LOW": 3}
}
```

#### `calculate_quality_score(metrics: Dict)`
Calculate overall quality score (0-100).

**Parameters:**
```python
{
    "pylint_score": 8.5,
    "security_issues": 2,
    "complexity_avg": 3.5,
    "style_violations": 5
}
```

**Returns:** `float` (0-100)

## Report Format

### Example Report Structure

```markdown
# Code Review Report

**Generated:** 2025-11-05T20:00:00
**Files Reviewed:** 17
**Total Score:** 85.5/100

---

## Summary

| Metric | Value |
|--------|-------|
| Average Pylint Score | 8.50/10 |
| Security Issues | 5 |
| High Severity Security | 1 |
| Style Issues | 3 |
| Average Complexity | 2.75 |
| High Complexity Functions | 0 |

---

## Quick Actions

```bash
# Run code review locally
python tmax_work3/agents/code_review.py --dirs app

# Fix style issues automatically
black . && isort .

# Run security scan
bandit -r app/
```

---

## Security Issues

| File | Line | Severity | Issue |
|------|------|----------|-------|
| app/main.py | 45 | HIGH | SQL injection risk |
| app/utils.py | 23 | MEDIUM | Weak cryptography |

---

## Recommendations

- 🔴 **CRITICAL:** Address high-severity security issues immediately
- ⚠️ Improve code quality - Average Pylint score is below 7/10
- 📝 Run `black` and `isort` to fix style issues
```

## Testing

### Run All Tests

```bash
python3 -m pytest tmax_work3/tests/test_code_review.py -v
```

### Test Coverage

The test suite includes:
- **28 comprehensive tests**
- Agent initialization tests
- Static analysis tests
- Security scanning tests
- Style checking tests
- Complexity analysis tests
- Report generation tests
- Scoring system tests
- Blackboard integration tests
- Full review workflow tests
- Edge case handling tests
- Evaluator integration tests

### Test Results

```
============================== 28 passed ==============================
```

All tests pass successfully!

## Demo

Run the demo script to see the agent in action:

```bash
python3 tmax_work3/demo_code_review.py
```

**Output:**
```
🔍 T-Max Code Review Agent Demo
============================================================

📊 Reviewing code...

============================================================
📊 REVIEW RESULTS
============================================================
Files Reviewed: 17
Total Score: 85.5/100
Security Issues: 5
Style Issues: 3
Average Complexity: 2.75

✅ Quality threshold PASSED

📄 Full report saved to:
   tmax_work3/data/code_reviews/review_20251105_205219.md
```

## Configuration

### Custom Weights

You can customize the scoring weights:

```python
agent = CodeReviewAgent(".")

# Modify weights
agent.weights = {
    "pylint": 0.30,      # Reduced from 0.40
    "security": 0.50,    # Increased from 0.30 (security-focused)
    "complexity": 0.15,  # Reduced from 0.20
    "style": 0.05        # Reduced from 0.10
}

result = agent.review_codebase(target_dirs=["app"])
```

### Custom Thresholds

```python
# Strict quality requirements
result = agent.review_codebase(
    target_dirs=["app"],
    min_score_threshold=90.0
)

# Lenient requirements for legacy code
result = agent.review_codebase(
    target_dirs=["legacy"],
    min_score_threshold=50.0
)
```

## Performance

### Benchmarks

- **Small codebase** (< 10 files): ~5 seconds
- **Medium codebase** (10-50 files): ~15-30 seconds
- **Large codebase** (50+ files): ~1-2 minutes

### Optimization Tips

1. **Target specific directories** instead of entire repo
2. **Skip report generation** for faster feedback
3. **Use parallel execution** for multiple branches
4. **Cache results** for unchanged files

## Integration Examples

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Code Review

on: [push, pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install dependencies
        run: pip install pylint bandit radon safety

      - name: Run code review
        run: |
          python tmax_work3/agents/code_review.py --dirs app

      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: code-review-report
          path: tmax_work3/data/code_reviews/*.md
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

python3 tmax_work3/agents/code_review.py --dirs app --threshold 70 --no-report

if [ $? -ne 0 ]; then
    echo "❌ Code review failed - quality threshold not met"
    exit 1
fi

echo "✅ Code review passed"
```

## Troubleshooting

### Tool Not Found

If you get "command not found" errors:

```bash
# Install missing tools
pip install pylint bandit radon safety black isort

# Verify PATH
which pylint
```

### JSON Decode Errors

If Pylint/Bandit output parsing fails:

```bash
# Update tools to latest versions
pip install --upgrade pylint bandit radon
```

### Slow Performance

For large codebases:

```python
# Review specific directories only
agent.review_codebase(target_dirs=["app/core"])

# Or exclude test files
agent.review_codebase(target_dirs=["app"], exclude_patterns=["**/test_*.py"])
```

## Future Enhancements

- [ ] Support for other languages (JavaScript, Go, Rust)
- [ ] Machine learning for issue prioritization
- [ ] Historical trend analysis
- [ ] Integration with GitHub Code Scanning
- [ ] Real-time review in IDE extensions
- [ ] Custom rule definitions
- [ ] Team-specific quality standards

## Contributing

To add new analysis tools:

1. Create a new method in `CodeReviewAgent`
2. Add integration in `review_codebase()`
3. Update scoring calculation
4. Add tests in `test_code_review.py`
5. Update documentation

## License

Part of the T-Max Work3 project.

## Support

For issues or questions:
- Create an issue in the repository
- Check existing documentation
- Run demo script for examples

---

**Generated by T-Max Code Review Agent**
*Production-Ready Automated Code Quality Analysis*
