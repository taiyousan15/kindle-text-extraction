"""
Kindle自動キャプチャサービス

PyAutoGUI（デスクトップ版）とSelenium（Cloud版）の2方式を提供
"""
from .pyautogui_capture import PyAutoGUICapture, CaptureConfig, CaptureResult
from .selenium_capture import SeleniumKindleCapture, SeleniumCaptureConfig, SeleniumCaptureResult
from .capture_factory import CaptureFactory, CaptureMethod

__all__ = [
    "PyAutoGUICapture",
    "CaptureConfig",
    "CaptureResult",
    "SeleniumKindleCapture",
    "SeleniumCaptureConfig",
    "SeleniumCaptureResult",
    "CaptureFactory",
    "CaptureMethod",
]
