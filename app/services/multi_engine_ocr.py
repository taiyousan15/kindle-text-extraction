"""
Multi-Engine OCR Service for 99% Accuracy Target

This module implements a cascading multi-engine OCR pipeline:
1. Tesseract (fast, free baseline)
2. Claude Vision API (primary high-accuracy engine)
3. OpenAI GPT-4 Vision (fallback for maximum accuracy)

Target: 99% accuracy on Japanese Kindle book pages
"""
import base64
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import io

from anthropic import Anthropic
from openai import OpenAI

# Import existing Tesseract OCR
from app.services.ocr_preprocessing import enhanced_ocr_with_preprocessing
from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiEngineOCR:
    """
    Advanced OCR service with multiple engine fallback for 99% accuracy

    Pipeline:
    1. Tesseract (confidence threshold: 85%)
    2. Claude Vision (confidence threshold: 90%)
    3. OpenAI GPT-4 Vision (final fallback)
    """

    def __init__(
        self,
        tesseract_lang: str = 'jpn+eng',
        tesseract_confidence_threshold: float = 0.85,
        claude_confidence_threshold: float = 0.90,
        enable_tesseract: bool = True,
        enable_claude: bool = True,
        enable_openai: bool = True
    ):
        """
        Initialize multi-engine OCR service

        Args:
            tesseract_lang: Language code for Tesseract
            tesseract_confidence_threshold: Min confidence to accept Tesseract result
            claude_confidence_threshold: Min confidence to accept Claude result
            enable_tesseract: Enable Tesseract engine
            enable_claude: Enable Claude Vision engine
            enable_openai: Enable OpenAI Vision engine
        """
        self.tesseract_lang = tesseract_lang
        self.tesseract_threshold = tesseract_confidence_threshold
        self.claude_threshold = claude_confidence_threshold

        self.enable_tesseract = enable_tesseract
        self.enable_claude = enable_claude
        self.enable_openai = enable_openai

        # Initialize API clients
        self.anthropic_client = None
        self.openai_client = None

        if self.enable_claude and settings.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("✅ Claude Vision API initialized")
            except Exception as e:
                logger.warning(f"⚠️ Claude API init failed: {e}")
                self.enable_claude = False

        if self.enable_openai and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("✅ OpenAI Vision API initialized")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI API init failed: {e}")
                self.enable_openai = False

        logger.info(
            f"🔍 Multi-Engine OCR initialized: "
            f"Tesseract={self.enable_tesseract}, "
            f"Claude={self.enable_claude}, "
            f"OpenAI={self.enable_openai}"
        )

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        Encode image file to base64 for API transmission

        Args:
            image_path: Path to image file

        Returns:
            str: Base64-encoded image data
        """
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')

    def _tesseract_ocr(self, image_path: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Run Tesseract OCR

        Args:
            image_path: Path to image file

        Returns:
            Tuple[str, float, Dict]: (text, confidence, metadata)
        """
        logger.info("🔍 Running Tesseract OCR (Engine 1/3)...")

        try:
            text, confidence = enhanced_ocr_with_preprocessing(
                image_path,
                lang=self.tesseract_lang
            )

            metadata = {
                'engine': 'tesseract',
                'lang': self.tesseract_lang,
                'char_count': len(text),
                'word_count': len(text.split()),
                'success': True
            }

            logger.info(
                f"✅ Tesseract: {len(text)} chars, "
                f"{confidence:.2%} confidence"
            )

            return text, confidence, metadata

        except Exception as e:
            logger.error(f"❌ Tesseract OCR failed: {e}")
            return "", 0.0, {'engine': 'tesseract', 'success': False, 'error': str(e)}

    def _claude_vision_ocr(self, image_path: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Run Claude Vision API for OCR

        Args:
            image_path: Path to image file

        Returns:
            Tuple[str, float, Dict]: (text, confidence, metadata)
        """
        logger.info("🔍 Running Claude Vision OCR (Engine 2/3)...")

        if not self.anthropic_client:
            logger.warning("⚠️ Claude API not available")
            return "", 0.0, {'engine': 'claude', 'success': False, 'error': 'API not initialized'}

        try:
            # Encode image
            base64_image = self._encode_image_to_base64(image_path)

            # Determine image type
            image_ext = Path(image_path).suffix.lower()
            media_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            media_type = media_type_map.get(image_ext, 'image/png')

            # Call Claude Vision API
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Latest model with vision
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": (
                                    "このKindle本のページ画像からテキストを正確に抽出してください。\n\n"
                                    "要件:\n"
                                    "1. ヘッダーとフッター（ページ番号など）は除外\n"
                                    "2. 本文のみを抽出\n"
                                    "3. 改行と段落構造を保持\n"
                                    "4. 日本語の文字を正確に認識\n"
                                    "5. 余計な説明は不要で、抽出したテキストのみを出力\n\n"
                                    "Please extract text from this Kindle book page image accurately.\n\n"
                                    "Requirements:\n"
                                    "1. Exclude headers and footers (page numbers, etc.)\n"
                                    "2. Extract only the main content\n"
                                    "3. Preserve line breaks and paragraph structure\n"
                                    "4. Accurately recognize Japanese characters\n"
                                    "5. Output only the extracted text without any explanation"
                                )
                            }
                        ]
                    }
                ]
            )

            # Extract text from response
            text = message.content[0].text.strip()

            # Estimate confidence based on text characteristics
            # Claude doesn't provide explicit confidence, so we estimate
            confidence = self._estimate_confidence_claude(text)

            metadata = {
                'engine': 'claude',
                'model': 'claude-3-5-sonnet-20241022',
                'char_count': len(text),
                'word_count': len(text.split()),
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens,
                'success': True
            }

            logger.info(
                f"✅ Claude: {len(text)} chars, "
                f"{confidence:.2%} confidence (estimated)"
            )

            return text, confidence, metadata

        except Exception as e:
            logger.error(f"❌ Claude Vision OCR failed: {e}")
            return "", 0.0, {'engine': 'claude', 'success': False, 'error': str(e)}

    def _openai_vision_ocr(self, image_path: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Run OpenAI GPT-4 Vision API for OCR

        Args:
            image_path: Path to image file

        Returns:
            Tuple[str, float, Dict]: (text, confidence, metadata)
        """
        logger.info("🔍 Running OpenAI Vision OCR (Engine 3/3)...")

        if not self.openai_client:
            logger.warning("⚠️ OpenAI API not available")
            return "", 0.0, {'engine': 'openai', 'success': False, 'error': 'API not initialized'}

        try:
            # Encode image
            base64_image = self._encode_image_to_base64(image_path)

            # Determine image type
            image_ext = Path(image_path).suffix.lower()
            mime_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.webp': 'image/webp',
                '.gif': 'image/gif'
            }
            mime_type = mime_type_map.get(image_ext, 'image/png')

            # Call OpenAI Vision API
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": (
                                    "このKindle本のページ画像からテキストを正確に抽出してください。\n\n"
                                    "要件:\n"
                                    "1. ヘッダーとフッター（ページ番号など）は除外\n"
                                    "2. 本文のみを抽出\n"
                                    "3. 改行と段落構造を保持\n"
                                    "4. 日本語の文字を正確に認識\n"
                                    "5. 余計な説明は不要で、抽出したテキストのみを出力\n\n"
                                    "Please extract text from this Kindle book page image accurately.\n\n"
                                    "Requirements:\n"
                                    "1. Exclude headers and footers (page numbers, etc.)\n"
                                    "2. Extract only the main content\n"
                                    "3. Preserve line breaks and paragraph structure\n"
                                    "4. Accurately recognize Japanese characters\n"
                                    "5. Output only the extracted text without any explanation"
                                )
                            }
                        ]
                    }
                ]
            )

            # Extract text from response
            text = response.choices[0].message.content.strip()

            # Estimate confidence
            confidence = self._estimate_confidence_openai(text, response)

            metadata = {
                'engine': 'openai',
                'model': 'gpt-4-vision-preview',
                'char_count': len(text),
                'word_count': len(text.split()),
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
                'finish_reason': response.choices[0].finish_reason,
                'success': True
            }

            logger.info(
                f"✅ OpenAI: {len(text)} chars, "
                f"{confidence:.2%} confidence (estimated)"
            )

            return text, confidence, metadata

        except Exception as e:
            logger.error(f"❌ OpenAI Vision OCR failed: {e}")
            return "", 0.0, {'engine': 'openai', 'success': False, 'error': str(e)}

    def _estimate_confidence_claude(self, text: str) -> float:
        """
        Estimate confidence score for Claude Vision result

        Heuristics:
        - Longer text = higher confidence
        - Presence of Japanese characters = higher confidence
        - Presence of common OCR errors = lower confidence

        Args:
            text: Extracted text

        Returns:
            float: Estimated confidence (0.0-1.0)
        """
        if not text:
            return 0.0

        confidence = 0.90  # Base confidence for Claude (high quality)

        # Adjust based on text length
        if len(text) < 50:
            confidence -= 0.05
        elif len(text) > 500:
            confidence += 0.05

        # Check for Japanese characters (expected for Kindle books)
        japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF')
        if japanese_chars > 0:
            confidence += 0.02

        # Check for OCR error indicators
        error_indicators = ['???', '□□□', '■■■', '��']
        if any(indicator in text for indicator in error_indicators):
            confidence -= 0.10

        return min(0.99, max(0.70, confidence))

    def _estimate_confidence_openai(self, text: str, response: Any) -> float:
        """
        Estimate confidence score for OpenAI Vision result

        Args:
            text: Extracted text
            response: OpenAI API response object

        Returns:
            float: Estimated confidence (0.0-1.0)
        """
        if not text:
            return 0.0

        confidence = 0.92  # Base confidence for GPT-4 Vision (high quality)

        # Check finish reason
        if response.choices[0].finish_reason != 'stop':
            confidence -= 0.10

        # Adjust based on text length
        if len(text) < 50:
            confidence -= 0.05
        elif len(text) > 500:
            confidence += 0.05

        # Check for Japanese characters
        japanese_chars = sum(1 for c in text if '\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF')
        if japanese_chars > 0:
            confidence += 0.02

        # Check for OCR error indicators
        error_indicators = ['???', '□□□', '■■■', '��']
        if any(indicator in text for indicator in error_indicators):
            confidence -= 0.10

        return min(0.99, max(0.70, confidence))

    def process_image_file(
        self,
        image_path: str,
        force_engine: Optional[str] = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Process image with cascading multi-engine OCR

        Pipeline:
        1. Try Tesseract (fast, free)
        2. If confidence < threshold, try Claude Vision
        3. If still < threshold, try OpenAI Vision

        Args:
            image_path: Path to image file
            force_engine: Force specific engine ('tesseract', 'claude', 'openai')

        Returns:
            Tuple[str, float, Dict]: (best_text, best_confidence, full_metadata)
        """
        logger.info(f"📸 Processing image: {image_path}")

        results = {
            'engines_tried': [],
            'tesseract': None,
            'claude': None,
            'openai': None,
            'selected_engine': None,
            'fallback_used': False
        }

        best_text = ""
        best_confidence = 0.0
        best_engine = "none"

        # Force specific engine if requested
        if force_engine:
            if force_engine == 'tesseract' and self.enable_tesseract:
                text, conf, meta = self._tesseract_ocr(image_path)
                results['tesseract'] = meta
                results['engines_tried'].append('tesseract')
                results['selected_engine'] = 'tesseract'
                return text, conf, results

            elif force_engine == 'claude' and self.enable_claude:
                text, conf, meta = self._claude_vision_ocr(image_path)
                results['claude'] = meta
                results['engines_tried'].append('claude')
                results['selected_engine'] = 'claude'
                return text, conf, results

            elif force_engine == 'openai' and self.enable_openai:
                text, conf, meta = self._openai_vision_ocr(image_path)
                results['openai'] = meta
                results['engines_tried'].append('openai')
                results['selected_engine'] = 'openai'
                return text, conf, results

        # Strategy 1: Try Tesseract first (fast, free)
        if self.enable_tesseract:
            text, conf, meta = self._tesseract_ocr(image_path)
            results['tesseract'] = meta
            results['engines_tried'].append('tesseract')

            if conf >= self.tesseract_threshold:
                logger.info(f"✅ Tesseract confidence {conf:.2%} meets threshold {self.tesseract_threshold:.2%}")
                results['selected_engine'] = 'tesseract'
                return text, conf, results

            logger.info(f"⚠️ Tesseract confidence {conf:.2%} below threshold {self.tesseract_threshold:.2%}, trying Claude...")
            best_text, best_confidence, best_engine = text, conf, 'tesseract'
            results['fallback_used'] = True

        # Strategy 2: Try Claude Vision (high accuracy)
        if self.enable_claude:
            text, conf, meta = self._claude_vision_ocr(image_path)
            results['claude'] = meta
            results['engines_tried'].append('claude')

            if conf >= self.claude_threshold:
                logger.info(f"✅ Claude confidence {conf:.2%} meets threshold {self.claude_threshold:.2%}")
                results['selected_engine'] = 'claude'
                return text, conf, results

            if conf > best_confidence:
                best_text, best_confidence, best_engine = text, conf, 'claude'

            logger.info(f"⚠️ Claude confidence {conf:.2%} below threshold {self.claude_threshold:.2%}, trying OpenAI...")
            results['fallback_used'] = True

        # Strategy 3: Try OpenAI Vision (final fallback)
        if self.enable_openai:
            text, conf, meta = self._openai_vision_ocr(image_path)
            results['openai'] = meta
            results['engines_tried'].append('openai')

            if conf > best_confidence:
                best_text, best_confidence, best_engine = text, conf, 'openai'

            results['selected_engine'] = best_engine
            return best_text, best_confidence, results

        # Return best result found
        logger.warning(
            f"⚠️ All engines below threshold. "
            f"Best: {best_engine} ({best_confidence:.2%})"
        )
        results['selected_engine'] = best_engine
        return best_text, best_confidence, results

    def batch_process_images(
        self,
        image_paths: list[str],
        force_engine: Optional[str] = None,
        max_workers: int = 3
    ) -> list[Dict[str, Any]]:
        """
        Process multiple images with parallelization

        Args:
            image_paths: List of image file paths
            force_engine: Force specific engine
            max_workers: Maximum parallel workers

        Returns:
            list: List of results for each image
        """
        import concurrent.futures

        logger.info(f"📸 Batch processing {len(image_paths)} images...")

        def process_single(image_path: str) -> Dict[str, Any]:
            try:
                text, confidence, metadata = self.process_image_file(
                    image_path,
                    force_engine=force_engine
                )
                return {
                    'image_path': image_path,
                    'text': text,
                    'confidence': confidence,
                    'metadata': metadata,
                    'success': True,
                    'error': None
                }
            except Exception as e:
                logger.error(f"❌ Failed to process {image_path}: {e}")
                return {
                    'image_path': image_path,
                    'text': '',
                    'confidence': 0.0,
                    'metadata': {},
                    'success': False,
                    'error': str(e)
                }

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(process_single, path): path
                for path in image_paths
            }

            for future in concurrent.futures.as_completed(future_to_path):
                results.append(future.result())

        success_count = sum(1 for r in results if r['success'])
        avg_confidence = sum(r['confidence'] for r in results if r['success']) / max(success_count, 1)

        logger.info(
            f"✅ Batch complete: {success_count}/{len(image_paths)} successful, "
            f"avg confidence: {avg_confidence:.2%}"
        )

        return results
