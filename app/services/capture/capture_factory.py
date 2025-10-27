"""
キャプチャ方式ファクトリー

PyAutoGUI or Selenium を切り替えて使用
"""
from enum import Enum
from typing import Union
from pathlib import Path

from .pyautogui_capture import PyAutoGUICapture, CaptureConfig, CaptureResult
from .selenium_capture import SeleniumKindleCapture, SeleniumCaptureConfig, SeleniumCaptureResult


class CaptureMethod(str, Enum):
    """キャプチャ方式"""
    PYAUTOGUI = "pyautogui"
    SELENIUM = "selenium"


class CaptureFactory:
    """キャプチャサービスのファクトリー"""

    @staticmethod
    def create_pyautogui(
        book_title: str,
        total_pages: int,
        interval_seconds: float = 2.0,
        capture_mode: str = "fullscreen",
        page_turn_key: str = "right",
        output_dir: Path = None
    ) -> PyAutoGUICapture:
        """PyAutoGUIキャプチャサービスを作成"""
        config = CaptureConfig(
            book_title=book_title,
            total_pages=total_pages,
            interval_seconds=interval_seconds,
            capture_mode=capture_mode,
            page_turn_key=page_turn_key,
            output_dir=output_dir
        )
        return PyAutoGUICapture(config)

    @staticmethod
    def create_selenium(
        book_url: str,
        book_title: str,
        amazon_email: str,
        amazon_password: str,
        max_pages: int = 500,
        headless: bool = True,
        output_dir: Path = None
    ) -> SeleniumKindleCapture:
        """Seleniumキャプチャサービスを作成"""
        config = SeleniumCaptureConfig(
            book_url=book_url,
            book_title=book_title,
            amazon_email=amazon_email,
            amazon_password=amazon_password,
            max_pages=max_pages,
            headless=headless,
            output_dir=output_dir
        )
        return SeleniumKindleCapture(config)

    @staticmethod
    def get_method_info(method: CaptureMethod) -> dict:
        """キャプチャ方式の情報を取得"""
        info = {
            CaptureMethod.PYAUTOGUI: {
                "name": "デスクトップ版（PyAutoGUI）",
                "description": "Kindleアプリを開いた状態で自動キャプチャ",
                "pros": [
                    "追加コスト0円",
                    "実装が簡単",
                    "Kindle以外にも使える"
                ],
                "cons": [
                    "PC前で実行する必要あり",
                    "他の作業と並行不可"
                ],
                "requirements": [
                    "Kindleアプリまたはブラウザで本を開く",
                    "pyautoguiライブラリ"
                ]
            },
            CaptureMethod.SELENIUM: {
                "name": "Cloud版（Selenium + Kindle Cloud Reader）",
                "description": "完全バックグラウンドで自動キャプチャ",
                "pros": [
                    "完全自動化可能",
                    "他の作業と並行可能",
                    "精度が高い"
                ],
                "cons": [
                    "Kindle Cloud Reader対応の本のみ",
                    "Amazonアカウント認証が必要",
                    "Chrome Driverのインストール必要"
                ],
                "requirements": [
                    "Kindle Cloud Reader対応の本",
                    "Amazonアカウント",
                    "selenium, webdriver-manager"
                ]
            }
        }
        return info.get(method, {})


# 使用例
if __name__ == "__main__":
    # PyAutoGUI版
    print("=" * 50)
    print("PyAutoGUI版の情報:")
    print(CaptureFactory.get_method_info(CaptureMethod.PYAUTOGUI))

    print("\n" + "=" * 50)
    print("Selenium版の情報:")
    print(CaptureFactory.get_method_info(CaptureMethod.SELENIUM))
