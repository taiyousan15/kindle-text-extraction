"""
OCR Service with Multi-Engine Support for 99% Accuracy

High-level OCR service that integrates:
- Multi-engine OCR pipeline (Tesseract → Claude → OpenAI)
- Advanced image preprocessing (denoising, contrast enhancement, binarization)
- Main text extraction (header/footer filtering)
- Multi-language OCR (Japanese + English)
- Confidence scoring with automatic fallback

Target: 99% OCR accuracy on Kindle book pages
"""
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import logging
from PIL import Image
import io
import os

from app.services.ocr_preprocessing import (
    enhanced_ocr_with_preprocessing,
    preprocess_image_for_ocr
)

# Import multi-engine OCR
try:
    from app.services.multi_engine_ocr import MultiEngineOCR
    MULTI_ENGINE_AVAILABLE = True
except ImportError:
    MULTI_ENGINE_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("⚠️ Multi-engine OCR not available, using Tesseract only")

logger = logging.getLogger(__name__)


class OCRService:
    """
    Production OCR service with multi-engine support for 99% accuracy

    This service provides industry-leading OCR accuracy through:
    1. Tesseract (fast baseline, 70-85% Japanese accuracy)
    2. Claude Vision API (primary, 90-95% accuracy)
    3. OpenAI GPT-4 Vision (fallback, 95-99% accuracy)
    """

    def __init__(
        self,
        lang: str = 'jpn+eng',
        use_multi_engine: bool = True,
        tesseract_threshold: float = 0.85,
        claude_threshold: float = 0.90
    ):
        """
        Initialize OCR service

        Args:
            lang: Tesseract language code (default: 'jpn+eng')
            use_multi_engine: Enable multi-engine OCR for 99% accuracy target
            tesseract_threshold: Minimum confidence to accept Tesseract result
            claude_threshold: Minimum confidence to accept Claude result
        """
        self.lang = lang
        self.use_multi_engine = use_multi_engine and MULTI_ENGINE_AVAILABLE

        # Initialize multi-engine OCR if enabled
        self.multi_engine = None
        if self.use_multi_engine:
            try:
                self.multi_engine = MultiEngineOCR(
                    tesseract_lang=lang,
                    tesseract_confidence_threshold=tesseract_threshold,
                    claude_confidence_threshold=claude_threshold
                )
                logger.info(f"✅ OCR Service initialized with multi-engine support (target: 99% accuracy)")
            except Exception as e:
                logger.warning(f"⚠️ Multi-engine OCR initialization failed: {e}")
                logger.warning("⚠️ Falling back to Tesseract-only mode")
                self.use_multi_engine = False
                self.multi_engine = None

        if not self.use_multi_engine:
            logger.info(f"🔍 OCR Service initialized with Tesseract only (lang={lang}, target: 90% accuracy)")

    def process_image_file(self, image_path: str) -> Tuple[str, float]:
        """
        Process image file with multi-engine OCR for 99% accuracy

        Pipeline:
        1. If multi-engine enabled: Try Tesseract → Claude → OpenAI
        2. If multi-engine disabled: Use Tesseract only

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
            if self.use_multi_engine and self.multi_engine:
                # Use multi-engine OCR for 99% accuracy
                text, confidence, metadata = self.multi_engine.process_image_file(image_path)

                logger.info(
                    f"✅ Multi-engine OCR complete - {len(text)} chars, "
                    f"{confidence:.2%} confidence, "
                    f"engine: {metadata.get('selected_engine', 'unknown')}"
                )

                return text, confidence

            else:
                # Fallback to Tesseract-only mode
                text, confidence = enhanced_ocr_with_preprocessing(
                    image_path,
                    lang=self.lang
                )

                logger.info(
                    f"✅ Tesseract OCR complete - {len(text)} chars, "
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
