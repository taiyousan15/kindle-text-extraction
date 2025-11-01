"""
OCR Service with Advanced Preprocessing

High-level OCR service that integrates:
- Advanced image preprocessing (denoising, contrast enhancement, binarization)
- Main text extraction (header/footer filtering)
- Multi-language OCR (Japanese + English)
- Confidence scoring

Target: 90%+ OCR accuracy on Kindle book pages
"""
from typing import Tuple, Optional
from pathlib import Path
import logging
from PIL import Image
import io

from app.services.ocr_preprocessing import (
    enhanced_ocr_with_preprocessing,
    preprocess_image_for_ocr
)

logger = logging.getLogger(__name__)


class OCRService:
    """
    Production OCR service with advanced preprocessing

    This service provides high-accuracy OCR for Kindle book pages
    using state-of-the-art image preprocessing techniques.
    """

    def __init__(self, lang: str = 'jpn+eng'):
        """
        Initialize OCR service

        Args:
            lang: Tesseract language code (default: 'jpn+eng')
        """
        self.lang = lang
        logger.info(f"🔍 OCR Service initialized (lang={lang})")

    def process_image_file(self, image_path: str) -> Tuple[str, float]:
        """
        Process image file with enhanced OCR

        Args:
            image_path: Path to image file

        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)

        Raises:
            FileNotFoundError: If image file doesn't exist
            IOError: If OCR processing fails
        """
        logger.info(f"📸 Processing image file: {image_path}")

        try:
            text, confidence = enhanced_ocr_with_preprocessing(
                image_path,
                lang=self.lang
            )

            logger.info(
                f"✅ OCR complete - {len(text)} chars, "
                f"{confidence:.2%} confidence"
            )

            return text, confidence

        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}", exc_info=True)
            raise

    def process_image_bytes(self, image_data: bytes) -> Tuple[str, float]:
        """
        Process image from bytes (e.g., uploaded file)

        Args:
            image_data: Image data as bytes

        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)

        Raises:
            IOError: If image processing fails
        """
        logger.info("📸 Processing image from bytes")

        try:
            # Save bytes to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                tmp_file.write(image_data)
                tmp_path = tmp_file.name

            # Process the temporary file
            text, confidence = self.process_image_file(tmp_path)

            # Clean up temporary file
            import os
            os.unlink(tmp_path)

            return text, confidence

        except Exception as e:
            logger.error(f"❌ OCR from bytes failed: {e}", exc_info=True)
            raise

    def process_pil_image(self, image: Image.Image) -> Tuple[str, float]:
        """
        Process PIL Image object

        Args:
            image: PIL Image object

        Returns:
            Tuple[str, float]: (extracted_text, confidence_score)

        Raises:
            IOError: If OCR processing fails
        """
        logger.info("📸 Processing PIL Image")

        try:
            # Save PIL Image to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                image.save(tmp_file, format='PNG')
                tmp_path = tmp_file.name

            # Process the temporary file
            text, confidence = self.process_image_file(tmp_path)

            # Clean up
            import os
            os.unlink(tmp_path)

            return text, confidence

        except Exception as e:
            logger.error(f"❌ OCR from PIL Image failed: {e}", exc_info=True)
            raise

    def batch_process_images(self, image_paths: list[str]) -> list[dict]:
        """
        Process multiple images in batch

        Args:
            image_paths: List of image file paths

        Returns:
            list[dict]: List of results with format:
                {
                    'image_path': str,
                    'text': str,
                    'confidence': float,
                    'success': bool,
                    'error': Optional[str]
                }
        """
        logger.info(f"📚 Batch processing {len(image_paths)} images")

        results = []

        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"Processing image {i}/{len(image_paths)}: {image_path}")

            try:
                text, confidence = self.process_image_file(image_path)

                results.append({
                    'image_path': image_path,
                    'text': text,
                    'confidence': confidence,
                    'success': True,
                    'error': None
                })

            except Exception as e:
                logger.error(f"❌ Failed to process {image_path}: {e}")

                results.append({
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'success': False,
                    'error': str(e)
                })

        successful = sum(1 for r in results if r['success'])
        logger.info(
            f"✅ Batch processing complete: "
            f"{successful}/{len(image_paths)} successful"
        )

        return results

    def validate_ocr_quality(self, text: str, confidence: float,
                            min_confidence: float = 0.70,
                            min_text_length: int = 10) -> Tuple[bool, str]:
        """
        Validate OCR result quality

        Args:
            text: Extracted text
            confidence: OCR confidence score
            min_confidence: Minimum acceptable confidence (default: 0.70)
            min_text_length: Minimum text length (default: 10)

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Check confidence
        if confidence < min_confidence:
            return False, f"Low confidence: {confidence:.2%} < {min_confidence:.2%}"

        # Check text length
        if len(text.strip()) < min_text_length:
            return False, f"Text too short: {len(text)} chars < {min_text_length}"

        # Check if text is not just whitespace
        if not text.strip():
            return False, "Empty text extracted"

        return True, "OCR quality validated"


# Global OCR service instance (singleton pattern)
_ocr_service_instance: Optional[OCRService] = None


def get_ocr_service(lang: str = 'jpn+eng') -> OCRService:
    """
    Get global OCR service instance (singleton)

    Args:
        lang: Tesseract language code

    Returns:
        OCRService: Global OCR service instance
    """
    global _ocr_service_instance

    if _ocr_service_instance is None:
        _ocr_service_instance = OCRService(lang=lang)

    return _ocr_service_instance


# Convenience functions for backward compatibility
def extract_text_from_image_file(image_path: str) -> Tuple[str, float]:
    """
    Extract text from image file (backward compatible)

    Args:
        image_path: Path to image file

    Returns:
        Tuple[str, float]: (text, confidence)
    """
    service = get_ocr_service()
    return service.process_image_file(image_path)


def extract_text_from_image_bytes(image_data: bytes) -> Tuple[str, float]:
    """
    Extract text from image bytes (backward compatible)

    Args:
        image_data: Image data as bytes

    Returns:
        Tuple[str, float]: (text, confidence)
    """
    service = get_ocr_service()
    return service.process_image_bytes(image_data)


# Example usage and testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python ocr_service.py <image_path>")
        print("\nExample:")
        print("  python ocr_service.py /path/to/kindle/page.png")
        sys.exit(1)

    image_path = sys.argv[1]

    # Create OCR service
    ocr_service = OCRService(lang='jpn+eng')

    print(f"\n{'='*80}")
    print(f"OCR Service - Processing: {image_path}")
    print(f"{'='*80}\n")

    # Process image
    text, confidence = ocr_service.process_image_file(image_path)

    # Validate quality
    is_valid, validation_msg = ocr_service.validate_ocr_quality(text, confidence)

    print(f"\n{'='*80}")
    print(f"Results:")
    print(f"{'='*80}")
    print(f"✅ Confidence: {confidence:.2%}")
    print(f"✅ Text length: {len(text)} characters")
    print(f"✅ Quality: {validation_msg}")
    print(f"✅ Valid: {is_valid}")
    print(f"\n{'-'*80}")
    print(f"Extracted Text:")
    print(f"{'-'*80}")
    print(text)
    print(f"\n{'='*80}\n")
