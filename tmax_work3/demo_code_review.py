"""
Demo script for Code Review Agent
Generates a sample review report
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from tmax_work3.agents.code_review import CodeReviewAgent


def main():
    print("🔍 T-Max Code Review Agent Demo")
    print("=" * 60)
    print()

    # Initialize agent
    agent = CodeReviewAgent(".")

    # Review a small subset
    print("📊 Reviewing code...")
    print()

    result = agent.review_codebase(
        target_dirs=["tmax_work3/agents"],
        generate_report=True,
        min_score_threshold=70.0
    )

    print()
    print("=" * 60)
    print("📊 REVIEW RESULTS")
    print("=" * 60)
    print(f"Files Reviewed: {result['files_reviewed']}")
    print(f"Total Score: {result['total_score']:.1f}/100")
    print(f"Security Issues: {result['summary']['total_security_issues']}")
    print(f"Style Issues: {result['summary']['total_style_issues']}")
    print(f"Average Complexity: {result['summary']['average_complexity']:.2f}")
    print()

    if result['passed_threshold']:
        print("✅ Quality threshold PASSED")
    else:
        print("⚠️ Quality threshold NOT MET")

    if 'report_path' in result:
        print()
        print(f"📄 Full report saved to:")
        print(f"   {result['report_path']}")
        print()

        # Display excerpt from report
        print("📖 Report Preview:")
        print("-" * 60)
        with open(result['report_path'], 'r') as f:
            lines = f.readlines()
            for line in lines[:30]:  # First 30 lines
                print(line.rstrip())
        print("-" * 60)

    print()
    print("✅ Demo complete!")


if __name__ == "__main__":
    main()
