"""
Standalone test script for enhanced OCR

This script tests the new OCR preprocessing pipeline on sample Kindle images.
"""
import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ocr_preprocessing import enhanced_ocr_with_preprocessing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_ocr_on_sample_image(image_path: str):
    """Test enhanced OCR on a single image"""
    print(f"\n{'='*80}")
    print(f"Enhanced OCR Test")
    print(f"{'='*80}")
    print(f"Image: {image_path}")
    print(f"{'='*80}\n")

    try:
        # Run enhanced OCR
        text, confidence = enhanced_ocr_with_preprocessing(image_path)

        # Display results
        print(f"\n{'='*80}")
        print(f"RESULTS")
        print(f"{'='*80}")
        print(f"Confidence Score: {confidence:.2%}")
        print(f"Text Length: {len(text)} characters")
        print(f"Number of Lines: {len(text.split(chr(10)))}")

        # Quality assessment
        quality = "EXCELLENT" if confidence >= 0.90 else "GOOD" if confidence >= 0.80 else "FAIR" if confidence >= 0.70 else "POOR"
        print(f"Quality Assessment: {quality}")

        print(f"\n{'-'*80}")
        print(f"EXTRACTED TEXT:")
        print(f"{'-'*80}")
        print(text)
        print(f"\n{'='*80}\n")

        # Validate against expected content
        expected_keywords = [
            "電子書籍版",
            "松本勇気",
            "日経BP",
            "2025"
        ]

        found_keywords = [kw for kw in expected_keywords if kw in text]
        keyword_accuracy = len(found_keywords) / len(expected_keywords)

        print(f"Keyword Validation:")
        print(f"  Expected keywords: {len(expected_keywords)}")
        print(f"  Found keywords: {len(found_keywords)}")
        print(f"  Keyword accuracy: {keyword_accuracy:.2%}")
        print(f"  Found: {found_keywords}")
        print(f"  Missing: {[kw for kw in expected_keywords if kw not in text]}")

        # Overall assessment
        print(f"\n{'='*80}")
        print(f"OVERALL ASSESSMENT")
        print(f"{'='*80}")

        if confidence >= 0.90 and keyword_accuracy >= 0.75:
            print("✅ PASS: High confidence (90%+) and good keyword accuracy")
            return True
        elif confidence >= 0.85:
            print("⚠️  ACCEPTABLE: Good confidence (85%+)")
            return True
        else:
            print("❌ FAIL: Confidence below target threshold")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}\n")
        return False


def test_multiple_images(image_dir: str):
    """Test enhanced OCR on multiple images"""
    image_dir_path = Path(image_dir)

    if not image_dir_path.exists():
        print(f"❌ Directory not found: {image_dir}")
        return

    # Get all PNG files
    image_files = sorted(image_dir_path.glob("*.png"))[:5]  # Test first 5 images

    print(f"\n{'='*80}")
    print(f"BATCH OCR TEST")
    print(f"{'='*80}")
    print(f"Directory: {image_dir}")
    print(f"Images to test: {len(image_files)}")
    print(f"{'='*80}\n")

    results = []

    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] Testing: {image_path.name}")
        print("-" * 80)

        try:
            text, confidence = enhanced_ocr_with_preprocessing(str(image_path))

            results.append({
                'file': image_path.name,
                'confidence': confidence,
                'text_length': len(text),
                'success': True
            })

            print(f"✅ Success: {confidence:.2%} confidence, {len(text)} chars")

        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            results.append({
                'file': image_path.name,
                'confidence': 0.0,
                'text_length': 0,
                'success': False,
                'error': str(e)
            })

    # Summary
    print(f"\n{'='*80}")
    print(f"BATCH TEST SUMMARY")
    print(f"{'='*80}")

    successful = sum(1 for r in results if r['success'])
    avg_confidence = sum(r['confidence'] for r in results if r['success']) / successful if successful > 0 else 0

    print(f"Total images: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Average confidence: {avg_confidence:.2%}")

    # Individual results
    print(f"\nIndividual Results:")
    print(f"{'-'*80}")
    for r in results:
        status = "✅" if r['success'] else "❌"
        conf_str = f"{r['confidence']:.2%}" if r['success'] else "N/A"
        print(f"{status} {r['file']:30s} | Confidence: {conf_str:>6s} | Chars: {r['text_length']:>5d}")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single image: python test_enhanced_ocr.py <image_path>")
        print("  Multiple images: python test_enhanced_ocr.py <image_directory>")
        print("\nExample:")
        print("  python test_enhanced_ocr.py /path/to/page_0004.png")
        print("  python test_enhanced_ocr.py /path/to/images/")
        sys.exit(1)

    target = sys.argv[1]
    target_path = Path(target)

    if target_path.is_file():
        # Test single image
        success = test_ocr_on_sample_image(str(target_path))
        sys.exit(0 if success else 1)
    elif target_path.is_dir():
        # Test multiple images
        test_multiple_images(str(target_path))
        sys.exit(0)
    else:
        print(f"❌ Invalid path: {target}")
        sys.exit(1)
