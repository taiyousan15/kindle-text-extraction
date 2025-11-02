"""
Test Enhanced OCR on Real Kindle Pages

This script tests the enhanced OCR system on actual captured Kindle pages
to verify that headers, footers, and page numbers are properly removed.
"""
import logging
from pathlib import Path
from app.services.ocr_preprocessing import enhanced_ocr_with_preprocessing
from app.services.capture_service import CaptureService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_enhanced_ocr_on_real_pages():
    """Test enhanced OCR on real Kindle page captures"""

    # Find recent capture directory
    captures_dir = Path("./captures")

    if not captures_dir.exists():
        logger.error("❌ Captures directory not found")
        return

    # Get most recent job directory
    job_dirs = sorted(captures_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)

    if not job_dirs:
        logger.error("❌ No capture directories found")
        return

    most_recent_job = job_dirs[0]
    logger.info(f"📁 Testing on job: {most_recent_job.name}")

    # Get first 3 pages for testing
    page_files = sorted([f for f in most_recent_job.iterdir() if f.name.startswith('page_') and f.suffix == '.png'])[:3]

    if not page_files:
        logger.error("❌ No page files found")
        return

    logger.info(f"📄 Found {len(page_files)} pages to test\n")

    for page_file in page_files:
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {page_file.name}")
        logger.info(f"{'='*80}\n")

        try:
            # Test 1: Enhanced OCR with header/footer removal
            logger.info("🔍 Test 1: Enhanced OCR with preprocessing + header/footer removal")
            text_enhanced, confidence_enhanced = enhanced_ocr_with_preprocessing(
                str(page_file),
                lang='jpn+eng',
                enable_header_footer_removal=True,
                top_margin=0.10,
                bottom_margin=0.10
            )

            # Apply text cleaning
            text_cleaned = CaptureService._clean_extracted_text(text_enhanced)

            logger.info(f"✅ Confidence: {confidence_enhanced:.2%}")
            logger.info(f"✅ Text length (before cleaning): {len(text_enhanced)} chars")
            logger.info(f"✅ Text length (after cleaning): {len(text_cleaned)} chars")

            # Check for common header/footer patterns that should be removed
            has_book_title = '生成AI' in text_cleaned or '戦力化' in text_cleaned
            has_page_number = 'Page' in text_cleaned or 'ページ' in text_cleaned

            logger.info(f"\n📊 Quality Check:")
            logger.info(f"  - Contains book title: {has_book_title} {'❌ SHOULD BE REMOVED' if has_book_title else '✅'}")
            logger.info(f"  - Contains page number: {has_page_number} {'❌ SHOULD BE REMOVED' if has_page_number else '✅'}")

            # Show first 300 characters of cleaned text
            logger.info(f"\n📝 Cleaned Text (first 300 chars):")
            logger.info(f"{'-'*80}")
            logger.info(text_cleaned[:300] if text_cleaned else "(empty)")
            logger.info(f"{'-'*80}\n")

            # Test 2: Compare with legacy OCR (without preprocessing)
            logger.info("🔍 Test 2: Legacy OCR (without preprocessing)")
            import pytesseract
            from PIL import Image

            image = Image.open(page_file)
            custom_config = r'--oem 3 --psm 6'
            text_legacy = pytesseract.image_to_string(
                image,
                lang='jpn+eng',
                config=custom_config
            )

            logger.info(f"✅ Legacy text length: {len(text_legacy)} chars")

            # Compare
            improvement = len(text_cleaned) / len(text_legacy) * 100 if len(text_legacy) > 0 else 0
            logger.info(f"\n📈 Improvement Analysis:")
            logger.info(f"  - Enhanced OCR: {len(text_cleaned)} chars")
            logger.info(f"  - Legacy OCR: {len(text_legacy)} chars")
            logger.info(f"  - Reduction: {improvement:.1f}% (should be less due to header/footer removal)")

        except Exception as e:
            logger.error(f"❌ Test failed: {e}", exc_info=True)

    logger.info(f"\n{'='*80}")
    logger.info("✅ Testing complete!")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    test_enhanced_ocr_on_real_pages()
