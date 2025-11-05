#!/bin/bash
################################################################################
# OCR Accuracy Testing - Automated Test Runner
################################################################################
#
# 英語 / English:
# Automated script to run 10+ OCR accuracy test cycles and validate 99% target
#
# 日本語 / Japanese:
# 10回以上のOCR精度テストサイクルを実行し、99%目標を検証する自動スクリプト
#
# Usage:
#   ./run_accuracy_tests.sh [--cycles N] [--target PERCENT]
#
# Examples:
#   ./run_accuracy_tests.sh                  # Run 10 cycles, 99% target
#   ./run_accuracy_tests.sh --cycles 15      # Run 15 cycles
#   ./run_accuracy_tests.sh --target 98.5    # Set 98.5% target
#
################################################################################

set -e  # Exit on error

# Default parameters
CYCLES=10
TARGET_ACCURACY=99.0
TEST_DATA_DIR="test_data/ground_truth"
OUTPUT_DIR="test_data/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${OUTPUT_DIR}/ocr_accuracy_report_${TIMESTAMP}.json"
MARKDOWN_REPORT="${OUTPUT_DIR}/OCR_ACCURACY_REPORT_${TIMESTAMP}.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cycles)
            CYCLES="$2"
            shift 2
            ;;
        --target)
            TARGET_ACCURACY="$2"
            shift 2
            ;;
        --test-data)
            TEST_DATA_DIR="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "OCR Accuracy Testing - Automated Test Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cycles N        Number of test cycles (default: 10)"
            echo "  --target PERCENT  Target accuracy percentage (default: 99.0)"
            echo "  --test-data DIR   Test data directory (default: test_data/ground_truth)"
            echo "  --output DIR      Output directory (default: test_data/results)"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

################################################################################
# Print header
################################################################################
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}OCR Accuracy Testing System${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Test Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "Number of Cycles: ${CYCLES}"
echo -e "Target Accuracy: ${TARGET_ACCURACY}%"
echo -e "Test Data: ${TEST_DATA_DIR}"
echo -e "Output: ${OUTPUT_DIR}"
echo -e "${BLUE}============================================${NC}"
echo ""

################################################################################
# Pre-flight checks
################################################################################
echo -e "${YELLOW}Running pre-flight checks...${NC}"

# Check if test_ocr_accuracy.py exists
if [ ! -f "test_ocr_accuracy.py" ]; then
    echo -e "${RED}❌ Error: test_ocr_accuracy.py not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} test_ocr_accuracy.py found"

# Check if test data directory exists
if [ ! -d "${TEST_DATA_DIR}" ]; then
    echo -e "${RED}❌ Error: Test data directory not found: ${TEST_DATA_DIR}${NC}"
    echo -e "${YELLOW}Please create the directory and add test images + ground truth files${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Test data directory found"

# Check if images directory exists
if [ ! -d "${TEST_DATA_DIR}/images" ]; then
    echo -e "${RED}❌ Error: Images directory not found: ${TEST_DATA_DIR}/images${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Images directory found"

# Check if transcriptions directory exists
if [ ! -d "${TEST_DATA_DIR}/transcriptions" ]; then
    echo -e "${RED}❌ Error: Transcriptions directory not found: ${TEST_DATA_DIR}/transcriptions${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Transcriptions directory found"

# Count test cases
IMAGE_COUNT=$(find "${TEST_DATA_DIR}/images" -name "*.png" -o -name "*.jpg" | wc -l | tr -d ' ')
if [ "$IMAGE_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ Error: No test images found in ${TEST_DATA_DIR}/images${NC}"
    echo -e "${YELLOW}Please add test images (.png or .jpg) to this directory${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found ${IMAGE_COUNT} test image(s)"

# Check Python dependencies
echo -e "${YELLOW}Checking Python dependencies...${NC}"
python3 -c "import Levenshtein" 2>/dev/null || {
    echo -e "${RED}❌ python-Levenshtein not installed${NC}"
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install python-Levenshtein rapidfuzz
}
echo -e "${GREEN}✓${NC} All dependencies installed"

echo ""

################################################################################
# Run OCR accuracy tests
################################################################################
echo -e "${YELLOW}Starting OCR accuracy tests...${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Run the test
python3 test_ocr_accuracy.py \
    --test-data-dir "${TEST_DATA_DIR}" \
    --cycles "${CYCLES}" \
    --target "${TARGET_ACCURACY}" \
    --output "${REPORT_FILE}"

TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}============================================${NC}"

################################################################################
# Generate Markdown report
################################################################################
echo -e "${YELLOW}Generating Markdown report...${NC}"

python3 << 'EOF'
import json
import sys
from pathlib import Path

# Read JSON report
report_file = sys.argv[1]
markdown_file = sys.argv[2]

with open(report_file, 'r', encoding='utf-8') as f:
    report = json.load(f)

# Generate Markdown
md_content = f"""# OCR Accuracy Test Report / OCR精度テストレポート

**Generated:** {report['test_date']}
**Test Cycles:** {report['num_cycles']}
**Target Accuracy:** {report['target_accuracy']}%

---

## Summary / 要約

| Metric / 指標 | Value / 値 |
|---|---|
| **Average Accuracy / 平均精度** | **{report['average_accuracy']:.2f}%** |
| **Min Accuracy / 最小精度** | {report['min_accuracy']:.2f}% |
| **Max Accuracy / 最大精度** | {report['max_accuracy']:.2f}% |
| **Standard Deviation / 標準偏差** | {report['std_deviation']:.2f}% |

### Status / ステータス

{report['status_message']}

---

## Detailed Results / 詳細結果

| Cycle # | Image | Overall Accuracy | Char Accuracy | Word Accuracy | Line Accuracy | Status |
|---------|-------|------------------|---------------|---------------|---------------|--------|
"""

for result in report['test_results']:
    if result['success']:
        metrics = result['metrics']
        status = "✅" if metrics['overall_accuracy'] >= report['target_accuracy'] else "✓"
        md_content += f"| {result['cycle_number']} | {Path(result['image_path']).name} | "
        md_content += f"{metrics['overall_accuracy']:.2f}% | "
        md_content += f"{metrics['character_accuracy']:.2f}% | "
        md_content += f"{metrics['word_accuracy']:.2f}% | "
        md_content += f"{metrics['line_accuracy']:.2f}% | "
        md_content += f"{status} |\n"
    else:
        md_content += f"| {result['cycle_number']} | {Path(result['image_path']).name} | "
        md_content += f"FAILED | - | - | - | ❌ |\n"

md_content += f"""
---

## Recommendations / 推奨事項

"""

for i, rec in enumerate(report['recommendations'], 1):
    md_content += f"{i}. {rec}\n"

md_content += f"""
---

## Metric Definitions / 指標の定義

### Character Accuracy / 文字精度
Percentage of correctly recognized characters using Levenshtein distance.
レーベンシュタイン距離を使用した正しく認識された文字の割合。

**Formula:** `(1 - (edit_distance / max_length)) × 100`

### Word Accuracy / 単語精度
Percentage of correctly recognized words (exact match).
正しく認識された単語の割合（完全一致）。

### Line Accuracy / 行精度
Percentage of correctly recognized lines (exact match).
正しく認識された行の割合（完全一致）。

### Overall Accuracy / 総合精度
Weighted average: Character (50%) + Word (30%) + Line (20%)
加重平均：文字（50%）+ 単語（30%）+ 行（20%）

---

## Test Configuration / テスト設定

- **OCR Engine:** Tesseract (jpn+eng)
- **Preprocessing:** CLAHE, Adaptive Binarization, Morphological Operations
- **Header/Footer Removal:** Enabled (8% top/bottom margins)
- **Test Cycles:** {report['num_cycles']}
- **Target Accuracy:** {report['target_accuracy']}%

---

## Next Steps / 次のステップ

{'### ✅ Deployment Ready / デプロイ準備完了' if report['passed'] else '### ⚠️ Improvements Needed / 改善が必要'}

"""

if report['passed']:
    md_content += """
The OCR system has achieved the target accuracy of 99% and is ready for deployment.

OCRシステムは99%の目標精度を達成し、デプロイの準備が整いました。

**Deployment Checklist:**
- [x] OCR accuracy validated (99%+)
- [ ] Performance testing
- [ ] Security review
- [ ] Documentation complete
- [ ] Production deployment
"""
else:
    md_content += f"""
The OCR system needs improvement to reach the target accuracy.

OCRシステムは目標精度に到達するために改善が必要です。

**Current Gap:** {report['target_accuracy'] - report['average_accuracy']:.2f}% below target

**Priority Actions:**
1. Review and implement recommendations above
2. Analyze failing test cases
3. Adjust OCR preprocessing parameters
4. Re-run accuracy tests
5. Validate 99% target achievement
"""

md_content += """
---

*Report generated by OCR Accuracy Testing System*
*OCR精度テストシステムにより生成されたレポート*
"""

# Write Markdown file
with open(markdown_file, 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"✓ Markdown report generated: {markdown_file}")

EOF

python3 - "${REPORT_FILE}" "${MARKDOWN_REPORT}"

################################################################################
# Final status
################################################################################
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}Test Complete${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "JSON Report: ${REPORT_FILE}"
echo -e "Markdown Report: ${MARKDOWN_REPORT}"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED - OCR accuracy meets target!${NC}"
    echo -e "${GREEN}   System is ready for deployment${NC}"
else
    echo -e "${RED}⚠️ BELOW TARGET - OCR accuracy needs improvement${NC}"
    echo -e "${YELLOW}   Please review recommendations in the report${NC}"
fi

echo -e "${BLUE}============================================${NC}"
echo ""

exit $TEST_EXIT_CODE
