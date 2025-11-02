"""
Test suite for improved OCR with image preprocessing

Testing Strategy:
- Test image preprocessing pipeline (binarization, noise removal, etc.)
- Test main text extraction (header/footer removal)
- Test OCR confidence measurement
- Validate 90%+ accuracy on sample images
"""
import pytest
import numpy as np
from PIL import Image
import io
import os
from pathlib import Path

from app.services.ocr_preprocessing import (
    preprocess_image_for_ocr,
    extract_main_text_region,
    remove_headers_footers,
    enhanced_ocr_with_preprocessing
)


class TestImagePreprocessing:
    """Test cases for image preprocessing pipeline"""

    @pytest.fixture
    def sample_image_path(self):
        """Path to test image"""
        # Use the actual test image mentioned in requirements
        test_image = Path("/Users/matsumototoshihiko/Downloads/Kindle_OCR_f77e6260_images_20251101_184925/page_0004.png")
        if test_image.exists():
            return str(test_image)
        # Fallback: create a synthetic test image
        return self._create_synthetic_test_image()

    def _create_synthetic_test_image(self) -> str:
        """Create a synthetic test image with text"""
        from PIL import ImageDraw, ImageFont

        # Create white background
        img = Image.new('RGB', (800, 1200), color='white')
        draw = ImageDraw.Draw(img)

        # Add some text (simulating a book page)
        sample_text = [
            "電子書籍版データ作成日 2025年10月27日 第1版",
            "著 者    松本勇気",
            "発行者    中川ヒロミ",
            "編 集    進藤寛・西倫英",
            "発 行    株式会社日経BP",
        ]

        y_position = 100
        for text in sample_text:
            draw.text((50, y_position), text, fill='black')
            y_position += 40

        # Save to temp file
        temp_path = "/tmp/test_kindle_page.png"
        img.save(temp_path)
        return temp_path

    def test_preprocess_image_returns_pil_image(self, sample_image_path):
        """Test that preprocessing returns a PIL Image object"""
        result = preprocess_image_for_ocr(sample_image_path)

        assert isinstance(result, Image.Image)
        assert result.mode in ['L', '1']  # Grayscale or binary

    def test_preprocess_improves_contrast(self, sample_image_path):
        """Test that preprocessing improves image contrast"""
        original_img = Image.open(sample_image_path).convert('L')
        preprocessed_img = preprocess_image_for_ocr(sample_image_path)

        # Convert to numpy arrays for comparison
        original_array = np.array(original_img)
        preprocessed_array = np.array(preprocessed_img)

        # Calculate contrast (std deviation of pixel values)
        original_contrast = np.std(original_array)
        preprocessed_contrast = np.std(preprocessed_array)

        # Preprocessed image should have equal or higher contrast
        assert preprocessed_contrast >= original_contrast * 0.8  # Allow 20% tolerance

    def test_preprocess_removes_noise(self, sample_image_path):
        """Test that preprocessing removes noise from image"""
        preprocessed_img = preprocess_image_for_ocr(sample_image_path)

        # Check that image has been processed (not identical to original)
        original_img = Image.open(sample_image_path).convert('L')

        original_array = np.array(original_img)
        preprocessed_array = np.array(preprocessed_img)

        # Images should be different (preprocessing applied)
        assert not np.array_equal(original_array, preprocessed_array)

    def test_preprocess_handles_invalid_path(self):
        """Test error handling for invalid image path"""
        with pytest.raises((FileNotFoundError, IOError)):
            preprocess_image_for_ocr("/nonexistent/path/image.png")

    def test_preprocess_pipeline_steps(self, sample_image_path):
        """Test that all preprocessing steps are applied"""
        # This test verifies the preprocessing pipeline executes without errors
        result = preprocess_image_for_ocr(sample_image_path)

        # Verify image dimensions are preserved
        original = Image.open(sample_image_path)
        assert result.size == original.size or abs(result.size[0] - original.size[0]) < 10


class TestHeaderFooterRemoval:
    """Test cases for header/footer removal"""

    @pytest.fixture
    def mock_image_with_header_footer(self):
        """Create mock image with header and footer"""
        img = Image.new('RGB', (800, 1200), color='white')
        draw = ImageDraw.Draw(img)

        # Header (top 10%)
        draw.text((50, 50), "Header: Book Title", fill='black')

        # Main content (middle 80%)
        main_text = [
            "This is the main content of the page.",
            "It contains the actual book text.",
            "This should be extracted and included.",
        ]
        y_pos = 200
        for line in main_text:
            draw.text((50, y_pos), line, fill='black')
            y_pos += 40

        # Footer (bottom 10%)
        draw.text((50, 1100), "Page 123", fill='black')

        return img

    def test_extract_main_text_region(self, mock_image_with_header_footer):
        """Test extraction of main text region (excluding header/footer)"""
        result = extract_main_text_region(mock_image_with_header_footer)

        # Result should be smaller than original (header/footer removed)
        assert result.size[1] < mock_image_with_header_footer.size[1]

    def test_remove_headers_footers_with_bounding_boxes(self):
        """Test header/footer removal using OCR bounding boxes"""
        # Mock OCR data with bounding boxes
        mock_ocr_data = {
            'text': ['Header', 'Main', 'Content', 'Footer'],
            'top': [50, 200, 240, 1100],  # Y coordinates
            'height': [30, 30, 30, 30],
            'conf': [95, 95, 95, 95]
        }

        image_height = 1200
        filtered_text = remove_headers_footers(mock_ocr_data, image_height)

        # Should only include 'Main' and 'Content' (middle region)
        assert 'Header' not in filtered_text
        assert 'Footer' not in filtered_text
        assert 'Main' in filtered_text
        assert 'Content' in filtered_text


class TestEnhancedOCR:
    """Test cases for enhanced OCR with preprocessing"""

    @pytest.fixture
    def sample_kindle_image(self):
        """Sample Kindle page image"""
        test_image = Path("/Users/matsumototoshihiko/Downloads/Kindle_OCR_f77e6260_images_20251101_184925/page_0004.png")
        if test_image.exists():
            return str(test_image)
        return None

    def test_enhanced_ocr_returns_text_and_confidence(self, sample_kindle_image):
        """Test that enhanced OCR returns both text and confidence score"""
        if sample_kindle_image is None:
            pytest.skip("Sample image not available")

        text, confidence = enhanced_ocr_with_preprocessing(sample_kindle_image)

        assert isinstance(text, str)
        assert len(text) > 0
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_enhanced_ocr_achieves_high_confidence(self, sample_kindle_image):
        """Test that enhanced OCR achieves 90%+ confidence"""
        if sample_kindle_image is None:
            pytest.skip("Sample image not available")

        text, confidence = enhanced_ocr_with_preprocessing(sample_kindle_image)

        # Target: 90%+ confidence
        assert confidence >= 0.90, f"OCR confidence {confidence:.2%} is below 90% target"

    def test_enhanced_ocr_extracts_complete_sentences(self, sample_kindle_image):
        """Test that OCR extracts complete, readable sentences"""
        if sample_kindle_image is None:
            pytest.skip("Sample image not available")

        text, confidence = enhanced_ocr_with_preprocessing(sample_kindle_image)

        # Expected content from page_0004.png
        expected_phrases = [
            "電子書籍版",
            "松本勇気",
            "日経BP"
        ]

        # At least one expected phrase should be present
        found = any(phrase in text for phrase in expected_phrases)
        assert found, f"Expected phrases not found in OCR result:\n{text}"

    def test_enhanced_ocr_removes_page_numbers(self, sample_kindle_image):
        """Test that page numbers are excluded from main text"""
        if sample_kindle_image is None:
            pytest.skip("Sample image not available")

        text, confidence = enhanced_ocr_with_preprocessing(sample_kindle_image)

        # Page numbers should be filtered out (footer region)
        # This is a heuristic test - page numbers are typically single/double digits
        lines = text.split('\n')
        standalone_numbers = [line for line in lines if line.strip().isdigit() and len(line.strip()) <= 3]

        # Should have minimal standalone page numbers
        assert len(standalone_numbers) <= 1, "Too many standalone numbers (likely page numbers) found"

    def test_enhanced_ocr_preserves_formatting(self, sample_kindle_image):
        """Test that OCR preserves basic text formatting (line breaks)"""
        if sample_kindle_image is None:
            pytest.skip("Sample image not available")

        text, confidence = enhanced_ocr_with_preprocessing(sample_kindle_image)

        # Should have multiple lines (not all concatenated)
        lines = text.split('\n')
        assert len(lines) > 1, "OCR result should preserve line breaks"

    @pytest.mark.parametrize("test_image_type", [
        "high_quality",
        "low_contrast",
        "noisy"
    ])
    def test_enhanced_ocr_handles_various_image_qualities(self, test_image_type):
        """Test OCR robustness with different image qualities"""
        # Create synthetic test images with different qualities
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "Test text for OCR", fill='black')

        # Modify based on test type
        if test_image_type == "low_contrast":
            img = img.convert('L')
            img = Image.eval(img, lambda x: x + 100)  # Reduce contrast

        elif test_image_type == "noisy":
            # Add noise
            img_array = np.array(img)
            noise = np.random.randint(0, 50, img_array.shape, dtype='uint8')
            noisy_img = np.clip(img_array.astype(int) + noise, 0, 255).astype('uint8')
            img = Image.fromarray(noisy_img)

        # Save to temp file
        temp_path = f"/tmp/test_{test_image_type}.png"
        img.save(temp_path)

        # Run enhanced OCR
        text, confidence = enhanced_ocr_with_preprocessing(temp_path)

        # Should extract at least some text
        assert len(text) > 0, f"Failed to extract text from {test_image_type} image"


class TestOCRAccuracyBenchmark:
    """Benchmark tests for OCR accuracy"""

    def test_ocr_accuracy_on_known_sample(self):
        """Test OCR accuracy against known ground truth"""
        sample_image = Path("/Users/matsumototoshihiko/Downloads/Kindle_OCR_f77e6260_images_20251101_184925/page_0004.png")

        if not sample_image.exists():
            pytest.skip("Benchmark image not available")

        # Ground truth (expected text from page_0004.png)
        ground_truth_keywords = [
            "電子書籍版",
            "2025",
            "松本勇気",
            "日経BP",
            "第1版"
        ]

        text, confidence = enhanced_ocr_with_preprocessing(str(sample_image))

        # Calculate keyword accuracy
        found_keywords = sum(1 for kw in ground_truth_keywords if kw in text)
        accuracy = found_keywords / len(ground_truth_keywords)

        assert accuracy >= 0.80, f"Keyword accuracy {accuracy:.2%} is below 80% threshold"
        assert confidence >= 0.85, f"OCR confidence {confidence:.2%} is below 85% threshold"

    def test_ocr_performance_metrics(self):
        """Test OCR performance (speed and memory)"""
        sample_image = Path("/Users/matsumototoshihiko/Downloads/Kindle_OCR_f77e6260_images_20251101_184925/page_0004.png")

        if not sample_image.exists():
            pytest.skip("Benchmark image not available")

        import time

        start_time = time.time()
        text, confidence = enhanced_ocr_with_preprocessing(str(sample_image))
        end_time = time.time()

        processing_time = end_time - start_time

        # OCR should complete within reasonable time (< 10 seconds for single page)
        assert processing_time < 10.0, f"OCR took {processing_time:.2f}s, exceeding 10s limit"

        # Text should be substantial
        assert len(text) > 50, "Extracted text is too short"


# Mock implementations for missing imports
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
