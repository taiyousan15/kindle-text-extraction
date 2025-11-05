#!/usr/bin/env python3
"""
OCR Accuracy Testing System - 99% Target Validation
====================================================

Comprehensive OCR accuracy measurement system that validates OCR results
against ground truth with multiple accuracy metrics.

Target: 99% accuracy over 10+ test cycles

Author: Error Hunter Agent
Date: 2025-11-05
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import statistics

# Text comparison libraries
from difflib import SequenceMatcher
import Levenshtein  # For edit distance calculation

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.ocr_service import OCRService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AccuracyMetrics:
    """
    Comprehensive accuracy metrics for OCR evaluation

    英語 / English:
    Multiple accuracy measures to evaluate OCR quality comprehensively

    日本語 / Japanese:
    OCRの品質を総合的に評価するための複数の精度指標
    """
    # Character-level accuracy
    character_accuracy: float  # Percentage of correct characters (0-100)

    # Word-level accuracy
    word_accuracy: float  # Percentage of correct words (0-100)

    # Line-level accuracy
    line_accuracy: float  # Percentage of correct lines (0-100)

    # Edit distance metrics
    levenshtein_distance: int  # Number of edits needed to match ground truth
    normalized_levenshtein: float  # Levenshtein distance normalized by length (0-1)

    # Sequence similarity
    sequence_similarity: float  # SequenceMatcher ratio (0-100)

    # Statistical metrics
    total_characters: int  # Total characters in ground truth
    total_words: int  # Total words in ground truth
    total_lines: int  # Total lines in ground truth

    # OCR confidence (if available)
    ocr_confidence: Optional[float] = None  # OCR engine confidence score

    # Overall accuracy score (weighted average)
    overall_accuracy: Optional[float] = None


@dataclass
class TestResult:
    """
    Single OCR test result

    英語 / English:
    Result from one OCR test cycle including all metrics

    日本語 / Japanese:
    1回のOCRテストサイクルの結果（全指標含む）
    """
    cycle_number: int
    image_path: str
    ground_truth_path: str
    ocr_text: str
    ground_truth_text: str
    metrics: AccuracyMetrics
    timestamp: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class TestReport:
    """
    Complete test report for multiple cycles

    英語 / English:
    Aggregated results from multiple test cycles

    日本語 / Japanese:
    複数のテストサイクルから集約された結果
    """
    test_date: str
    num_cycles: int
    target_accuracy: float
    test_results: List[TestResult]

    # Aggregate statistics
    average_accuracy: float
    min_accuracy: float
    max_accuracy: float
    std_deviation: float

    # Pass/Fail status
    passed: bool
    status_message: str

    # Recommendations
    recommendations: List[str]


class OCRAccuracyTester:
    """
    OCR Accuracy Testing System

    英語 / English:
    Comprehensive system to test OCR accuracy against ground truth

    日本語 / Japanese:
    正解データに対してOCRの精度をテストする包括的システム
    """

    def __init__(self, target_accuracy: float = 99.0):
        """
        Initialize OCR accuracy tester

        Args:
            target_accuracy: Target accuracy percentage (default: 99.0)
        """
        self.target_accuracy = target_accuracy
        self.ocr_service = OCRService(lang='jpn+eng')

        logger.info(f"🎯 OCR Accuracy Tester initialized")
        logger.info(f"   Target accuracy: {target_accuracy}%")

    def calculate_character_accuracy(self, ocr_text: str, ground_truth: str) -> float:
        """
        Calculate character-level accuracy using Levenshtein distance

        英語 / English:
        Accuracy = (1 - (edit_distance / max_length)) * 100

        日本語 / Japanese:
        精度 = (1 - (編集距離 / 最大長)) * 100

        Args:
            ocr_text: OCR result text
            ground_truth: Ground truth text

        Returns:
            float: Character accuracy percentage (0-100)
        """
        if not ground_truth:
            return 0.0

        # Calculate edit distance
        distance = Levenshtein.distance(ocr_text, ground_truth)
        max_length = max(len(ocr_text), len(ground_truth))

        # Calculate accuracy
        if max_length == 0:
            return 100.0

        accuracy = (1 - (distance / max_length)) * 100
        return max(0.0, accuracy)  # Ensure non-negative

    def calculate_word_accuracy(self, ocr_text: str, ground_truth: str) -> float:
        """
        Calculate word-level accuracy

        英語 / English:
        Compare words one by one and calculate match percentage

        日本語 / Japanese:
        単語を1つずつ比較し、一致率を計算

        Args:
            ocr_text: OCR result text
            ground_truth: Ground truth text

        Returns:
            float: Word accuracy percentage (0-100)
        """
        ocr_words = ocr_text.split()
        truth_words = ground_truth.split()

        if not truth_words:
            return 0.0

        # Count matching words
        matches = sum(
            1 for ocr_word, truth_word in zip(ocr_words, truth_words)
            if ocr_word == truth_word
        )

        accuracy = (matches / len(truth_words)) * 100
        return accuracy

    def calculate_line_accuracy(self, ocr_text: str, ground_truth: str) -> float:
        """
        Calculate line-level accuracy

        英語 / English:
        Compare lines one by one and calculate match percentage

        日本語 / Japanese:
        行を1つずつ比較し、一致率を計算

        Args:
            ocr_text: OCR result text
            ground_truth: Ground truth text

        Returns:
            float: Line accuracy percentage (0-100)
        """
        ocr_lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        truth_lines = [line.strip() for line in ground_truth.split('\n') if line.strip()]

        if not truth_lines:
            return 0.0

        # Count matching lines
        matches = sum(
            1 for ocr_line, truth_line in zip(ocr_lines, truth_lines)
            if ocr_line == truth_line
        )

        accuracy = (matches / len(truth_lines)) * 100
        return accuracy

    def calculate_detailed_metrics(self, ocr_text: str, ground_truth: str,
                                   ocr_confidence: Optional[float] = None) -> AccuracyMetrics:
        """
        Calculate comprehensive accuracy metrics

        英語 / English:
        Compute all accuracy metrics including character, word, line, and edit distance

        日本語 / Japanese:
        文字・単語・行・編集距離を含む全精度指標を計算

        Args:
            ocr_text: OCR result text
            ground_truth: Ground truth text
            ocr_confidence: OCR engine confidence score (optional)

        Returns:
            AccuracyMetrics: Comprehensive accuracy metrics
        """
        # Character-level accuracy
        char_accuracy = self.calculate_character_accuracy(ocr_text, ground_truth)

        # Word-level accuracy
        word_accuracy = self.calculate_word_accuracy(ocr_text, ground_truth)

        # Line-level accuracy
        line_accuracy = self.calculate_line_accuracy(ocr_text, ground_truth)

        # Edit distance metrics
        lev_distance = Levenshtein.distance(ocr_text, ground_truth)
        max_length = max(len(ocr_text), len(ground_truth))
        normalized_lev = lev_distance / max_length if max_length > 0 else 0.0

        # Sequence similarity (SequenceMatcher)
        seq_similarity = SequenceMatcher(None, ocr_text, ground_truth).ratio() * 100

        # Statistical counts
        total_chars = len(ground_truth)
        total_words = len(ground_truth.split())
        total_lines = len([line for line in ground_truth.split('\n') if line.strip()])

        # Overall accuracy (weighted average)
        # Weight: Character 50%, Word 30%, Line 20%
        overall = (
            char_accuracy * 0.5 +
            word_accuracy * 0.3 +
            line_accuracy * 0.2
        )

        return AccuracyMetrics(
            character_accuracy=char_accuracy,
            word_accuracy=word_accuracy,
            line_accuracy=line_accuracy,
            levenshtein_distance=lev_distance,
            normalized_levenshtein=normalized_lev,
            sequence_similarity=seq_similarity,
            total_characters=total_chars,
            total_words=total_words,
            total_lines=total_lines,
            ocr_confidence=ocr_confidence,
            overall_accuracy=overall
        )

    def run_single_test(self, image_path: str, ground_truth_path: str,
                       cycle_number: int) -> TestResult:
        """
        Run single OCR test cycle

        英語 / English:
        Process one image through OCR and compare with ground truth

        日本語 / Japanese:
        1枚の画像をOCR処理し、正解データと比較

        Args:
            image_path: Path to test image
            ground_truth_path: Path to ground truth text file
            cycle_number: Test cycle number

        Returns:
            TestResult: Complete test result with metrics
        """
        logger.info(f"📸 Running test cycle #{cycle_number}: {image_path}")

        try:
            # Load ground truth
            with open(ground_truth_path, 'r', encoding='utf-8') as f:
                ground_truth = f.read().strip()

            logger.info(f"   Ground truth loaded: {len(ground_truth)} characters")

            # Run OCR
            ocr_text, ocr_confidence = self.ocr_service.process_image_file(image_path)
            logger.info(f"   OCR complete: {len(ocr_text)} characters, {ocr_confidence:.2%} confidence")

            # Calculate metrics
            metrics = self.calculate_detailed_metrics(
                ocr_text,
                ground_truth,
                ocr_confidence
            )

            logger.info(f"   ✅ Overall accuracy: {metrics.overall_accuracy:.2f}%")

            return TestResult(
                cycle_number=cycle_number,
                image_path=image_path,
                ground_truth_path=ground_truth_path,
                ocr_text=ocr_text,
                ground_truth_text=ground_truth,
                metrics=metrics,
                timestamp=datetime.now().isoformat(),
                success=True,
                error_message=None
            )

        except Exception as e:
            logger.error(f"   ❌ Test failed: {e}", exc_info=True)

            return TestResult(
                cycle_number=cycle_number,
                image_path=image_path,
                ground_truth_path=ground_truth_path,
                ocr_text="",
                ground_truth_text="",
                metrics=AccuracyMetrics(
                    character_accuracy=0.0,
                    word_accuracy=0.0,
                    line_accuracy=0.0,
                    levenshtein_distance=0,
                    normalized_levenshtein=0.0,
                    sequence_similarity=0.0,
                    total_characters=0,
                    total_words=0,
                    total_lines=0
                ),
                timestamp=datetime.now().isoformat(),
                success=False,
                error_message=str(e)
            )

    def run_multiple_cycles(self, test_cases: List[Tuple[str, str]],
                           num_cycles: int = 10) -> TestReport:
        """
        Run multiple test cycles

        英語 / English:
        Execute OCR tests for multiple cycles and aggregate results

        日本語 / Japanese:
        複数サイクルのOCRテストを実行し、結果を集約

        Args:
            test_cases: List of (image_path, ground_truth_path) tuples
            num_cycles: Number of test cycles (default: 10)

        Returns:
            TestReport: Complete test report with all results
        """
        logger.info(f"🚀 Starting {num_cycles} test cycles with {len(test_cases)} test cases")

        all_results = []
        cycle_counter = 1

        # Run tests for each cycle
        for cycle in range(num_cycles):
            logger.info(f"\n{'='*80}")
            logger.info(f"Test Cycle {cycle + 1}/{num_cycles}")
            logger.info(f"{'='*80}")

            for image_path, ground_truth_path in test_cases:
                result = self.run_single_test(
                    image_path,
                    ground_truth_path,
                    cycle_counter
                )
                all_results.append(result)
                cycle_counter += 1

        # Calculate aggregate statistics
        successful_results = [r for r in all_results if r.success]

        if not successful_results:
            logger.error("❌ All tests failed!")
            return TestReport(
                test_date=datetime.now().isoformat(),
                num_cycles=num_cycles,
                target_accuracy=self.target_accuracy,
                test_results=all_results,
                average_accuracy=0.0,
                min_accuracy=0.0,
                max_accuracy=0.0,
                std_deviation=0.0,
                passed=False,
                status_message="All tests failed",
                recommendations=["Fix OCR system - all tests failed"]
            )

        accuracies = [r.metrics.overall_accuracy for r in successful_results]

        avg_accuracy = statistics.mean(accuracies)
        min_accuracy = min(accuracies)
        max_accuracy = max(accuracies)
        std_dev = statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0

        # Determine pass/fail
        passed = avg_accuracy >= self.target_accuracy

        if passed:
            status_msg = f"✅ PASSED - Average accuracy {avg_accuracy:.2f}% meets target {self.target_accuracy}%"
        else:
            status_msg = f"⚠️ BELOW TARGET - Average accuracy {avg_accuracy:.2f}% < target {self.target_accuracy}%"

        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_accuracy,
            min_accuracy,
            std_dev,
            successful_results
        )

        logger.info(f"\n{'='*80}")
        logger.info(f"Test Complete: {status_msg}")
        logger.info(f"{'='*80}")

        return TestReport(
            test_date=datetime.now().isoformat(),
            num_cycles=num_cycles,
            target_accuracy=self.target_accuracy,
            test_results=all_results,
            average_accuracy=avg_accuracy,
            min_accuracy=min_accuracy,
            max_accuracy=max_accuracy,
            std_deviation=std_dev,
            passed=passed,
            status_message=status_msg,
            recommendations=recommendations
        )

    def _generate_recommendations(self, avg_accuracy: float, min_accuracy: float,
                                 std_dev: float, results: List[TestResult]) -> List[str]:
        """
        Generate actionable recommendations based on test results

        英語 / English:
        Analyze results and suggest improvements

        日本語 / Japanese:
        結果を分析し、改善案を提案

        Args:
            avg_accuracy: Average accuracy
            min_accuracy: Minimum accuracy
            std_dev: Standard deviation
            results: List of test results

        Returns:
            List[str]: List of recommendations
        """
        recommendations = []

        # Check average accuracy
        if avg_accuracy < self.target_accuracy:
            gap = self.target_accuracy - avg_accuracy
            recommendations.append(
                f"Average accuracy is {gap:.2f}% below target. "
                "Consider improving image preprocessing or OCR configuration."
            )

        # Check minimum accuracy
        if min_accuracy < self.target_accuracy - 1.0:
            recommendations.append(
                f"Minimum accuracy ({min_accuracy:.2f}%) is significantly below target. "
                "Investigate failing test cases for specific issues."
            )

        # Check consistency (standard deviation)
        if std_dev > 1.0:
            recommendations.append(
                f"High variability in results (std dev: {std_dev:.2f}%). "
                "OCR results are inconsistent - improve preprocessing or test image quality."
            )

        # Check OCR confidence
        avg_confidence = statistics.mean([
            r.metrics.ocr_confidence for r in results
            if r.metrics.ocr_confidence is not None
        ])

        if avg_confidence < 0.85:
            recommendations.append(
                f"Average OCR confidence is low ({avg_confidence:.2%}). "
                "Consider adjusting header/footer detection or image quality."
            )

        # Specific recommendations based on metric patterns
        char_accuracies = [r.metrics.character_accuracy for r in results]
        word_accuracies = [r.metrics.word_accuracy for r in results]

        avg_char = statistics.mean(char_accuracies)
        avg_word = statistics.mean(word_accuracies)

        if avg_char > avg_word + 10:
            recommendations.append(
                "Word accuracy is significantly lower than character accuracy. "
                "OCR may be splitting words incorrectly - adjust space detection."
            )

        if not recommendations:
            recommendations.append(
                "✅ Excellent OCR performance! All metrics meet or exceed target."
            )

        return recommendations

    def save_report(self, report: TestReport, output_path: str) -> None:
        """
        Save test report to JSON file

        Args:
            report: Test report to save
            output_path: Output file path
        """
        report_dict = asdict(report)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"📄 Report saved to: {output_path}")

    def print_report(self, report: TestReport) -> None:
        """
        Print formatted test report to console

        英語 / English:
        Display comprehensive test results in readable format

        日本語 / Japanese:
        包括的なテスト結果を読みやすい形式で表示

        Args:
            report: Test report to print
        """
        print("\n" + "="*80)
        print("OCR ACCURACY TEST REPORT / OCR精度テストレポート")
        print("="*80)
        print(f"Test Date / テスト日時: {report.test_date}")
        print(f"Number of Cycles / サイクル数: {report.num_cycles}")
        print(f"Target Accuracy / 目標精度: {report.target_accuracy}%")
        print(f"\n{'-'*80}")
        print("TEST RESULTS / テスト結果:")
        print("-"*80)

        for result in report.test_results:
            if result.success:
                status_icon = "✅" if result.metrics.overall_accuracy >= report.target_accuracy else "✓"
                print(f"├─ Cycle {result.cycle_number}: {result.metrics.overall_accuracy:.2f}% {status_icon}")
            else:
                print(f"├─ Cycle {result.cycle_number}: FAILED ❌ ({result.error_message})")

        print(f"\n{'-'*80}")
        print("AGGREGATE STATISTICS / 集計統計:")
        print("-"*80)
        print(f"Average Accuracy / 平均精度: {report.average_accuracy:.2f}%")
        print(f"Min Accuracy / 最小精度: {report.min_accuracy:.2f}%")
        print(f"Max Accuracy / 最大精度: {report.max_accuracy:.2f}%")
        print(f"Std Deviation / 標準偏差: {report.std_deviation:.2f}%")

        print(f"\n{'-'*80}")
        print(f"STATUS / ステータス: {report.status_message}")
        print("-"*80)

        print(f"\n{'-'*80}")
        print("RECOMMENDATIONS / 推奨事項:")
        print("-"*80)
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")

        print("\n" + "="*80 + "\n")


def main():
    """
    Main entry point for OCR accuracy testing

    英語 / English:
    Run OCR accuracy validation with ground truth dataset

    日本語 / Japanese:
    正解データセットを使用してOCR精度検証を実行
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="OCR Accuracy Testing System - 99% Target Validation"
    )
    parser.add_argument(
        '--test-data-dir',
        default='test_data/ground_truth',
        help='Directory containing test images and ground truth files'
    )
    parser.add_argument(
        '--cycles',
        type=int,
        default=10,
        help='Number of test cycles to run (default: 10)'
    )
    parser.add_argument(
        '--target',
        type=float,
        default=99.0,
        help='Target accuracy percentage (default: 99.0)'
    )
    parser.add_argument(
        '--output',
        default='test_data/results/ocr_accuracy_report.json',
        help='Output path for JSON report'
    )

    args = parser.parse_args()

    # Find test cases
    test_data_dir = Path(args.test_data_dir)
    images_dir = test_data_dir / 'images'
    transcriptions_dir = test_data_dir / 'transcriptions'

    if not images_dir.exists() or not transcriptions_dir.exists():
        logger.error(f"❌ Test data directory not found: {test_data_dir}")
        logger.error(f"   Expected structure:")
        logger.error(f"   {test_data_dir}/images/")
        logger.error(f"   {test_data_dir}/transcriptions/")
        sys.exit(1)

    # Collect test cases
    test_cases = []
    for image_file in sorted(images_dir.glob('*.png')):
        # Find corresponding ground truth file
        base_name = image_file.stem
        ground_truth_file = transcriptions_dir / f"{base_name}.txt"

        if ground_truth_file.exists():
            test_cases.append((str(image_file), str(ground_truth_file)))
            logger.info(f"✓ Found test case: {image_file.name}")
        else:
            logger.warning(f"⚠️ No ground truth for: {image_file.name}")

    if not test_cases:
        logger.error("❌ No test cases found!")
        logger.error("   Please add test images to: " + str(images_dir))
        logger.error("   And ground truth files to: " + str(transcriptions_dir))
        sys.exit(1)

    logger.info(f"\n📊 Found {len(test_cases)} test case(s)")

    # Initialize tester
    tester = OCRAccuracyTester(target_accuracy=args.target)

    # Run tests
    report = tester.run_multiple_cycles(test_cases, num_cycles=args.cycles)

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tester.save_report(report, str(output_path))

    # Print report
    tester.print_report(report)

    # Exit with appropriate code
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
