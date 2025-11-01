"""
Advanced OCR Image Preprocessing Service

Implements sophisticated image preprocessing pipeline to dramatically improve OCR accuracy:
- Grayscale conversion
- Noise reduction (Gaussian blur, Non-local means denoising)
- Contrast enhancement (CLAHE)
- Adaptive binarization
- Morphological operations
- Header/footer removal

Target: 90%+ OCR confidence on Kindle book pages
"""
import cv2
import numpy as np
from PIL import Image
import pytesseract
from pytesseract import Output
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OCRPreprocessor:
    """Advanced image preprocessor for OCR accuracy improvement"""

    @staticmethod
    def preprocess_image_for_ocr(image_path: str) -> Image.Image:
        """
        Complete preprocessing pipeline for OCR

        Pipeline steps:
        1. Load image with OpenCV
        2. Convert to grayscale
        3. Denoise (Non-local means)
        4. Enhance contrast (CLAHE)
        5. Adaptive binarization
        6. Morphological operations (noise removal)

        Args:
            image_path: Path to input image

        Returns:
            PIL.Image: Preprocessed image ready for OCR

        Raises:
            FileNotFoundError: If image file doesn't exist
            IOError: If image cannot be loaded
        """
        logger.info(f"🖼️ Preprocessing image: {image_path}")

        # Load image
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = cv2.imread(str(img_path))
        if img is None:
            raise IOError(f"Failed to load image: {image_path}")

        # Step 1: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        logger.debug("   Step 1: Grayscale conversion complete")

        # Step 2: Simple noise reduction (fast and effective)
        # Gaussian blur with small kernel for speed
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        logger.debug("   Step 2: Gaussian blur complete")

        # Step 3: Contrast enhancement using CLAHE
        # (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)
        logger.debug("   Step 3: Contrast enhancement complete")

        # Step 4: Adaptive binarization
        # This works better than global thresholding for varying lighting
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,  # Block size
            2    # Constant subtracted from mean
        )
        logger.debug("   Step 4: Adaptive binarization complete")

        # Step 5: Light morphological operations to remove tiny noise
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        logger.debug("   Step 5: Morphological operations complete")

        # Convert back to PIL Image
        pil_image = Image.fromarray(morph)
        logger.info("✅ Preprocessing complete")

        return pil_image

    @staticmethod
    def extract_main_text_region(image: Image.Image,
                                 top_margin: float = 0.10,
                                 bottom_margin: float = 0.10) -> Image.Image:
        """
        Extract main text region, excluding header and footer areas

        Args:
            image: Input PIL Image
            top_margin: Percentage of image height to exclude from top (header)
            bottom_margin: Percentage of image height to exclude from bottom (footer)

        Returns:
            PIL.Image: Cropped image containing only main text region
        """
        width, height = image.size

        # Calculate crop boundaries
        top_crop = int(height * top_margin)
        bottom_crop = int(height * (1 - bottom_margin))

        # Crop image
        cropped = image.crop((0, top_crop, width, bottom_crop))

        logger.debug(f"   Cropped to main region: {cropped.size}")
        return cropped

    @staticmethod
    def remove_headers_footers(ocr_data: dict, image_height: int,
                               top_threshold: float = 0.10,
                               bottom_threshold: float = 0.90,
                               line_break_threshold: int = 15) -> str:
        """
        Filter OCR results to exclude header/footer regions based on bounding boxes

        This method uses bounding box positions to intelligently reconstruct text
        while filtering out header and footer regions.

        Args:
            ocr_data: Pytesseract output dictionary with bounding boxes
            image_height: Height of original image
            top_threshold: Percentage threshold for header region (default: 0.10)
            bottom_threshold: Percentage threshold for footer region (default: 0.90)
            line_break_threshold: Y-coordinate difference to detect line breaks (default: 15px)

        Returns:
            str: Filtered text with headers/footers removed
        """
        main_text_top = int(image_height * top_threshold)
        main_text_bottom = int(image_height * bottom_threshold)

        filtered_lines = []
        current_line = []
        prev_top = -1
        prev_left = -1
        prev_width = 0

        for i, text in enumerate(ocr_data['text']):
            if not text.strip():
                continue

            top = ocr_data['top'][i]
            left = ocr_data['left'][i]
            width = ocr_data['width'][i]
            confidence = int(ocr_data['conf'][i])

            # Skip low-confidence text
            if confidence < 50:  # Higher threshold for better quality (skip noise)
                continue

            # Skip header/footer regions
            if top < main_text_top or top > main_text_bottom:
                continue

            # Detect line breaks (Y coordinate changed significantly)
            if prev_top != -1 and abs(top - prev_top) > line_break_threshold:
                if current_line:
                    # Join current line without extra spaces for Japanese text
                    line_text = ''.join(current_line)
                    filtered_lines.append(line_text)
                    current_line = []
                prev_left = -1

            # Add space if there's a significant horizontal gap (for mixed Japanese/English)
            if prev_left != -1:
                # Calculate expected next position
                expected_left = prev_left + prev_width
                actual_gap = left - expected_left

                # Add space if gap is significant (> 20px typically indicates word boundary)
                if actual_gap > 20:
                    current_line.append(' ')

            current_line.append(text)
            prev_top = top
            prev_left = left
            prev_width = width

        # Add last line
        if current_line:
            line_text = ''.join(current_line)
            filtered_lines.append(line_text)

        return '\n'.join(filtered_lines)


def preprocess_image_for_ocr(image_path: str) -> Image.Image:
    """
    Convenience function for preprocessing

    Args:
        image_path: Path to image file

    Returns:
        PIL.Image: Preprocessed image
    """
    preprocessor = OCRPreprocessor()
    return preprocessor.preprocess_image_for_ocr(image_path)


def extract_main_text_region(image: Image.Image) -> Image.Image:
    """
    Convenience function for main text extraction

    Args:
        image: PIL Image

    Returns:
        PIL.Image: Cropped image with main text only
    """
    preprocessor = OCRPreprocessor()
    return preprocessor.extract_main_text_region(image)


def remove_headers_footers(ocr_data: dict, image_height: int,
                          top_threshold: float = 0.10,
                          bottom_threshold: float = 0.90,
                          line_break_threshold: int = 15) -> str:
    """
    Convenience function for header/footer removal

    Args:
        ocr_data: Pytesseract output dictionary
        image_height: Image height in pixels
        top_threshold: Percentage threshold for header region (default: 0.10)
        bottom_threshold: Percentage threshold for footer region (default: 0.90)
        line_break_threshold: Y-coordinate difference to detect line breaks (default: 15px)

    Returns:
        str: Filtered text
    """
    preprocessor = OCRPreprocessor()
    return preprocessor.remove_headers_footers(ocr_data, image_height,
                                              top_threshold, bottom_threshold,
                                              line_break_threshold)


def enhanced_ocr_with_preprocessing(image_path: str, lang: str = 'jpn+eng',
                                   enable_header_footer_removal: bool = True,
                                   top_margin: float = 0.08,
                                   bottom_margin: float = 0.08) -> Tuple[str, float]:
    """
    Complete OCR pipeline with preprocessing

    This is the main entry point for improved OCR processing.

    Pipeline:
    1. Preprocess image (denoise, enhance, binarize)
    2. Extract main text region (remove headers/footers via bounding box filtering)
    3. Run Tesseract OCR with optimized config
    4. Calculate confidence score

    Args:
        image_path: Path to image file
        lang: Tesseract language (default: 'jpn+eng' for Japanese + English)
        enable_header_footer_removal: Enable header/footer filtering (default: True)
        top_margin: Top margin percentage to exclude (header area, default: 0.08 = 8%)
        bottom_margin: Bottom margin percentage to exclude (footer area, default: 0.08 = 8%)

    Returns:
        Tuple[str, float]: (extracted_text, confidence_score)
            - extracted_text: OCR result as string (with headers/footers removed)
            - confidence_score: Average confidence (0.0 to 1.0)

    Raises:
        FileNotFoundError: If image file doesn't exist
        IOError: If image processing fails
    """
    logger.info(f"🔍 Starting enhanced OCR: {image_path}")
    logger.info(f"   Header/Footer removal: {'ENABLED' if enable_header_footer_removal else 'DISABLED'}")
    logger.info(f"   Margins: top={top_margin:.1%}, bottom={bottom_margin:.1%}")

    try:
        # Step 1: Preprocess image
        preprocessed_img = preprocess_image_for_ocr(image_path)
        height = preprocessed_img.size[1]

        # Step 2: Run OCR with optimized configuration
        custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
        # OEM 3: Default (LSTM + Legacy)
        # PSM 6: Assume a single uniform block of text
        # preserve_interword_spaces: Preserve spaces between words

        # Get detailed OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(
            preprocessed_img,
            lang=lang,
            config=custom_config,
            output_type=Output.DICT
        )

        # Step 3: Extract text with header/footer filtering
        if enable_header_footer_removal:
            # Filter out header/footer regions based on bounding box positions
            text = remove_headers_footers(ocr_data, height,
                                         top_threshold=top_margin,
                                         bottom_threshold=1.0 - bottom_margin)
            logger.info(f"   ✂️ Headers/footers removed")
        else:
            # Simple text extraction without filtering
            text = pytesseract.image_to_string(
                preprocessed_img,
                lang=lang,
                config=custom_config
            )
            logger.info(f"   ℹ️ Using full text (no filtering)")

        # Step 4: Calculate average confidence (only for main text region if filtering enabled)
        if enable_header_footer_removal:
            main_text_top = int(height * top_margin)
            main_text_bottom = int(height * (1.0 - bottom_margin))

            confidences = [
                float(conf) for i, conf in enumerate(ocr_data['conf'])
                if conf != '-1' and int(conf) >= 0
                and main_text_top <= ocr_data['top'][i] <= main_text_bottom
            ]
        else:
            confidences = [
                float(conf) for conf in ocr_data['conf']
                if conf != '-1' and int(conf) >= 0
            ]

        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        logger.info(f"✅ OCR complete - Text length: {len(text)}, Confidence: {avg_confidence:.2%}")

        return text.strip(), avg_confidence

    except Exception as e:
        logger.error(f"❌ Enhanced OCR failed: {e}", exc_info=True)
        raise


# Example usage
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_preprocessing.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    print(f"\n{'='*60}")
    print(f"Enhanced OCR Processing: {image_path}")
    print(f"{'='*60}\n")

    text, confidence = enhanced_ocr_with_preprocessing(image_path)

    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"{'='*60}")
    print(f"Confidence: {confidence:.2%}")
    print(f"Text length: {len(text)} characters")
    print(f"\n{'-'*60}")
    print(f"Extracted Text:")
    print(f"{'-'*60}")
    print(text)
    print(f"\n{'='*60}\n")
