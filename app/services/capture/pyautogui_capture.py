"""
PyAutoGUI自動キャプチャサービス

Kindleアプリを開いた状態で、画面キャプチャ → ページ送り を自動繰り返し
"""
import pyautogui
import time
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CaptureConfig:
    """キャプチャ設定"""
    book_title: str
    total_pages: int
    interval_seconds: float = 2.0
    capture_mode: str = "fullscreen"  # "fullscreen" or "window"
    page_turn_key: str = "right"  # "right", "space", "pagedown"
    output_dir: Optional[Path] = None


@dataclass
class CaptureResult:
    """キャプチャ結果"""
    success: bool
    captured_pages: int
    image_paths: List[Path]
    error_message: Optional[str] = None


class PyAutoGUICapture:
    """PyAutoGUIを使用した自動キャプチャ"""

    def __init__(self, config: CaptureConfig):
        self.config = config

        # 出力ディレクトリ設定
        if config.output_dir is None:
            self.output_dir = Path(f"captures/{config.book_title}")
        else:
            self.output_dir = config.output_dir

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # PyAutoGUIの安全設定
        pyautogui.FAILSAFE = True  # マウスを画面左上に移動で緊急停止
        pyautogui.PAUSE = 0.5  # 各操作間の待機時間

    def capture_all_pages(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> CaptureResult:
        """
        全ページを自動キャプチャ

        Args:
            progress_callback: 進捗コールバック (current_page, total_pages)
            stop_check: 停止チェック関数 (True返却で中断)

        Returns:
            CaptureResult
        """
        logger.info(f"🚀 自動キャプチャ開始: {self.config.book_title}")
        logger.info(f"📚 総ページ数: {self.config.total_pages}")
        logger.info(f"⏱️ ページ送り間隔: {self.config.interval_seconds}秒")
        logger.info(f"🚨 緊急停止: マウスを画面左上端に移動")

        image_paths: List[Path] = []

        try:
            # カウントダウン（Kindleウィンドウをアクティブにする時間）
            logger.info("⏳ 5秒後に開始します。Kindleウィンドウをアクティブにしてください...")
            for i in range(5, 0, -1):
                logger.info(f"   {i}...")
                time.sleep(1)

            logger.info("✅ キャプチャ開始！")

            for page in range(1, self.config.total_pages + 1):
                # 停止チェック
                if stop_check and stop_check():
                    logger.warning(f"⚠️ ユーザーによる中断 (ページ {page}/{self.config.total_pages})")
                    break

                # 画面キャプチャ
                screenshot = self._capture_screen()

                # 保存
                image_path = self.output_dir / f"page_{page:04d}.png"
                screenshot.save(image_path)
                image_paths.append(image_path)

                logger.info(f"📸 ページ {page}/{self.config.total_pages} キャプチャ完了")

                # 進捗コールバック
                if progress_callback:
                    progress_callback(page, self.config.total_pages)

                # 最後のページでない場合、次ページへ
                if page < self.config.total_pages:
                    self._turn_page()
                    time.sleep(self.config.interval_seconds)

            logger.info(f"🎉 完了！{len(image_paths)}ページを保存しました: {self.output_dir}")

            return CaptureResult(
                success=True,
                captured_pages=len(image_paths),
                image_paths=image_paths
            )

        except pyautogui.FailSafeException:
            error_msg = "緊急停止が発動されました（マウスが画面左上端に移動）"
            logger.error(f"🛑 {error_msg}")
            return CaptureResult(
                success=False,
                captured_pages=len(image_paths),
                image_paths=image_paths,
                error_message=error_msg
            )

        except Exception as e:
            error_msg = f"予期しないエラー: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return CaptureResult(
                success=False,
                captured_pages=len(image_paths),
                image_paths=image_paths,
                error_message=error_msg
            )

    def _capture_screen(self):
        """画面キャプチャ実行"""
        if self.config.capture_mode == "fullscreen":
            return pyautogui.screenshot()
        elif self.config.capture_mode == "window":
            # 特定ウィンドウのキャプチャ（座標指定が必要）
            # TODO: Kindleウィンドウの位置・サイズを検出して範囲指定
            return pyautogui.screenshot()
        else:
            raise ValueError(f"不正なcapture_mode: {self.config.capture_mode}")

    def _turn_page(self):
        """ページ送り"""
        pyautogui.press(self.config.page_turn_key)
        logger.debug(f"⏭️ ページ送り: {self.config.page_turn_key}キー")

    def test_capture(self) -> bool:
        """
        テストキャプチャ（1ページのみ）

        Returns:
            成功したらTrue
        """
        try:
            logger.info("🧪 テストキャプチャ実行...")
            screenshot = self._capture_screen()
            test_path = self.output_dir / "test_capture.png"
            screenshot.save(test_path)
            logger.info(f"✅ テストキャプチャ成功: {test_path}")
            return True
        except Exception as e:
            logger.error(f"❌ テストキャプチャ失敗: {e}")
            return False


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    config = CaptureConfig(
        book_title="プロンプトエンジニアリング入門",
        total_pages=10,
        interval_seconds=2.0,
        page_turn_key="right"
    )

    capturer = PyAutoGUICapture(config)

    # テストキャプチャ
    if capturer.test_capture():
        # 本番実行
        result = capturer.capture_all_pages()

        if result.success:
            print(f"✅ 成功: {result.captured_pages}ページキャプチャ")
        else:
            print(f"❌ 失敗: {result.error_message}")
