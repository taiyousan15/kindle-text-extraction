"""
Test suite for Kindle Cloud Reader page detection

Testing Strategy:
- Mock Selenium WebDriver interactions
- Test multiple detection methods (fallback mechanism)
- Verify error handling when detection fails
- Test integration with capture flow
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from app.services.capture.selenium_capture import (
    SeleniumKindleCapture,
    SeleniumCaptureConfig
)


class TestPageDetection:
    """Test cases for total page detection feature"""

    @pytest.fixture
    def mock_driver(self):
        """Mock Selenium WebDriver"""
        driver = MagicMock()
        driver.current_url = "https://read.amazon.co.jp/kindle-library"
        return driver

    @pytest.fixture
    def capture_config(self):
        """Create test capture configuration"""
        return SeleniumCaptureConfig(
            book_url="https://read.amazon.co.jp/...",
            book_title="Test Book",
            amazon_email="test@example.com",
            amazon_password="password123",
            max_pages=100,
            headless=True
        )

    def test_detect_total_pages_from_page_indicator(self, mock_driver, capture_config):
        """Test page detection from page indicator element (e.g., 'Page 1 of 258')"""
        # Setup mock page indicator element
        mock_element = Mock(spec=WebElement)
        mock_element.text = "Page 1 of 258"
        mock_driver.find_element.return_value = mock_element

        # Create capturer with mocked driver
        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            capturer = SeleniumKindleCapture(capture_config)
            capturer.driver = mock_driver

            # Execute detection
            total_pages = capturer._detect_total_pages()

            # Assertions
            assert total_pages == 258
            assert isinstance(total_pages, int)

    def test_detect_total_pages_from_javascript(self, mock_driver, capture_config):
        """Test page detection from JavaScript (Kindle Reader API)"""
        # Setup: Page indicator method fails, JavaScript succeeds
        mock_driver.find_element.side_effect = NoSuchElementException()
        mock_driver.execute_script.return_value = 456

        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            capturer = SeleniumKindleCapture(capture_config)
            capturer.driver = mock_driver

            total_pages = capturer._detect_total_pages()

            assert total_pages == 456
            # Verify JavaScript was called
            mock_driver.execute_script.assert_called_once()

    def test_detect_total_pages_from_progress_bar(self, mock_driver, capture_config):
        """Test page detection from progress bar aria-valuemax attribute"""
        # Setup: First two methods fail, progress bar succeeds
        mock_driver.find_element.side_effect = [
            NoSuchElementException(),  # Page indicator fails
            NoSuchElementException()   # But find progress bar
        ]
        mock_driver.execute_script.return_value = None  # JavaScript fails

        # Create mock progress bar element
        mock_progress = Mock(spec=WebElement)
        mock_progress.get_attribute.return_value = "350"
        mock_driver.find_element.return_value = mock_progress

        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            capturer = SeleniumKindleCapture(capture_config)
            capturer.driver = mock_driver

            # Override find_element to return progress bar when CSS selector is used
            def mock_find_element(by, value):
                if "progressbar" in str(value).lower():
                    return mock_progress
                raise NoSuchElementException()

            mock_driver.find_element.side_effect = mock_find_element

            total_pages = capturer._detect_total_pages()

            assert total_pages == 350

    def test_detect_total_pages_returns_none_on_failure(self, mock_driver, capture_config):
        """Test that detection returns None when all methods fail"""
        # Setup: All detection methods fail
        mock_driver.find_element.side_effect = NoSuchElementException()
        mock_driver.execute_script.return_value = None

        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            capturer = SeleniumKindleCapture(capture_config)
            capturer.driver = mock_driver

            total_pages = capturer._detect_total_pages()

            # Should return None instead of raising exception
            assert total_pages is None

    def test_capture_uses_detected_pages(self, mock_driver, capture_config):
        """Test that capture_all_pages uses detected total pages"""
        # Setup: Mock successful login and page detection
        mock_element = Mock(spec=WebElement)
        mock_element.text = "Page 1 of 50"

        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            with patch('app.services.capture.selenium_capture.SeleniumKindleCapture.login_amazon', return_value=True):
                with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._detect_total_pages', return_value=50):
                    with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._is_last_page', return_value=False):
                        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._turn_page'):
                            capturer = SeleniumKindleCapture(capture_config)
                            capturer.driver = mock_driver

                            # Mock screenshot saving
                            mock_driver.save_screenshot = Mock()

                            result = capturer.capture_all_pages()

                            # Assertions
                            assert result.success is True
                            assert result.actual_total_pages == 50
                            # Should capture 50 pages (detected) instead of 100 (config.max_pages)
                            assert result.captured_pages == 50

    def test_capture_falls_back_to_max_pages(self, mock_driver, capture_config):
        """Test that capture falls back to config.max_pages when detection fails"""
        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            with patch('app.services.capture.selenium_capture.SeleniumKindleCapture.login_amazon', return_value=True):
                with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._detect_total_pages', return_value=None):
                    with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._is_last_page', return_value=False):
                        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._turn_page'):
                            capturer = SeleniumKindleCapture(capture_config)
                            capturer.driver = mock_driver

                            mock_driver.save_screenshot = Mock()

                            result = capturer.capture_all_pages()

                            # Should use config.max_pages (100) when detection fails
                            assert result.actual_total_pages is None
                            assert result.captured_pages == 100

    def test_page_indicator_regex_variations(self, mock_driver, capture_config):
        """Test page indicator parsing with various text formats"""
        test_cases = [
            ("Page 1 of 258", 258),
            ("ページ 1 / 300", 300),
            ("1 of 150", 150),
            ("1/200", 200),
        ]

        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            capturer = SeleniumKindleCapture(capture_config)
            capturer.driver = mock_driver

            for text, expected_pages in test_cases:
                mock_element = Mock(spec=WebElement)
                mock_element.text = text
                mock_driver.find_element.return_value = mock_element

                total_pages = capturer._detect_total_pages()
                assert total_pages == expected_pages, f"Failed to parse '{text}'"


class TestPageDetectionIntegration:
    """Integration tests for page detection with real scenarios"""

    @pytest.fixture
    def capture_config(self):
        return SeleniumCaptureConfig(
            book_url="https://read.amazon.co.jp/test-book",
            book_title="Integration Test Book",
            amazon_email="test@example.com",
            amazon_password="password",
            max_pages=500,
            headless=True
        )

    def test_detection_timeout_handling(self, capture_config):
        """Test proper handling of WebDriver timeout during detection"""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = TimeoutException()

        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            capturer = SeleniumKindleCapture(capture_config)
            capturer.driver = mock_driver

            # Should not raise exception, should return None
            total_pages = capturer._detect_total_pages()
            assert total_pages is None

    def test_detection_uses_minimum_of_detected_and_max(self, capture_config):
        """Test that capture uses min(detected_pages, max_pages)"""
        mock_driver = MagicMock()

        # Detected pages (1000) > max_pages (500)
        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._init_driver', return_value=mock_driver):
            with patch('app.services.capture.selenium_capture.SeleniumKindleCapture.login_amazon', return_value=True):
                with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._detect_total_pages', return_value=1000):
                    with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._is_last_page', return_value=False):
                        with patch('app.services.capture.selenium_capture.SeleniumKindleCapture._turn_page'):
                            capturer = SeleniumKindleCapture(capture_config)
                            capturer.driver = mock_driver
                            mock_driver.save_screenshot = Mock()

                            result = capturer.capture_all_pages()

                            # Should limit to max_pages (500)
                            assert result.captured_pages == 500
                            assert result.actual_total_pages == 1000
