"""
Kindle OCR - Auto Capture Page
自動キャプチャページ

Kindle Cloud Readerから自動的にページをキャプチャしてOCR処理
"""
import streamlit as st
import sys
import os
import time
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import start_auto_capture, get_job_status, APIError

# ページ設定
st.set_page_config(
    page_title="Kindle OCR - Auto Capture",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .capture-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .status-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        margin-top: 1rem;
    }
    .status-pending {
        color: #ff9800;
    }
    .status-processing {
        color: #2196f3;
    }
    .status-completed {
        color: #4caf50;
    }
    .status-failed {
        color: #f44336;
    }
</style>
""", unsafe_allow_html=True)


def get_status_color(status: str) -> str:
    """ステータスに応じた色を返す"""
    status_colors = {
        "pending": "orange",
        "processing": "blue",
        "completed": "green",
        "failed": "red"
    }
    return status_colors.get(status, "gray")


def main():
    # セッション状態の初期化
    if "capture_job_id" not in st.session_state:
        st.session_state.capture_job_id = None
    if "capture_running" not in st.session_state:
        st.session_state.capture_running = False
    if "last_progress" not in st.session_state:
        st.session_state.last_progress = 0

    # ヘッダー
    st.markdown('<div class="capture-header">🤖 自動キャプチャ</div>', unsafe_allow_html=True)

    st.info(
        "🚀 **自動キャプチャ**: Kindle Cloud Readerから自動的に複数ページをキャプチャし、OCR処理を実行します。\n\n"
        "Amazon認証情報とブックURLを入力するだけで、バックグラウンドで処理が実行されます。"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("🤖 Auto Capture")
        st.markdown("---")
        st.markdown("### キャプチャ手順")
        st.markdown(
            "1. Amazon認証情報を入力\n"
            "2. Kindle Cloud ReaderのブックURLを入力\n"
            "3. 書籍タイトルと最大ページ数を設定\n"
            "4. キャプチャ開始ボタンをクリック\n"
            "5. リアルタイムで進捗を確認"
        )
        st.markdown("---")
        st.markdown("### 注意事項")
        st.markdown(
            "⚠️ Amazon認証情報は安全に保管されます\n\n"
            "⏱️ 処理時間はページ数に応じて変動\n\n"
            "🔄 処理中はページを閉じないでください"
        )

    # メインコンテンツ
    # キャプチャ実行中の場合はステータス表示
    if st.session_state.capture_running and st.session_state.capture_job_id:
        display_capture_status()
    else:
        display_capture_form()


def display_capture_form():
    """キャプチャ開始フォームを表示"""

    st.markdown("### ⚙️ キャプチャ設定")

    # 2カラムレイアウト
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 🔐 Amazon認証情報")

        amazon_email = st.text_input(
            "Amazonアカウント (Email)",
            placeholder="example@email.com",
            type="default",
            help="AmazonアカウントのEメールアドレスを入力してください"
        )

        amazon_password = st.text_input(
            "Amazonパスワード",
            type="password",
            placeholder="パスワードを入力",
            help="Amazonアカウントのパスワードを入力してください"
        )

        st.markdown("---")
        st.markdown("#### 📚 書籍情報")

        book_url = st.text_input(
            "Kindle Cloud Reader URL",
            placeholder="https://read.amazon.com/...",
            help="Kindle Cloud Readerでブックを開いたときのURLを入力してください"
        )

    with col2:
        st.markdown("#### 📖 キャプチャ設定")

        book_title = st.text_input(
            "書籍タイトル",
            placeholder="例: プロンプトエンジニアリング入門",
            help="書籍のタイトルを入力してください（OCR結果の管理に使用）"
        )

        max_pages = st.slider(
            "最大キャプチャページ数",
            min_value=1,
            max_value=100,
            value=50,
            step=1,
            help="キャプチャする最大ページ数を設定してください"
        )

        headless = st.checkbox(
            "ヘッドレスモード",
            value=True,
            help="チェックを入れるとブラウザを表示せずにバックグラウンドで実行します"
        )

        st.markdown("---")

        # 入力値のバリデーション
        all_fields_filled = all([
            amazon_email.strip(),
            amazon_password.strip(),
            book_url.strip(),
            book_title.strip()
        ])

        # キャプチャ開始ボタン
        start_button = st.button(
            "🚀 キャプチャ開始",
            type="primary",
            use_container_width=True,
            disabled=not all_fields_filled
        )

        if not all_fields_filled:
            st.warning("⚠️ すべての必須項目を入力してください")

    # キャプチャ開始処理
    if start_button:
        with st.spinner("🔄 キャプチャジョブを開始しています..."):
            try:
                # APIコール
                result = start_auto_capture(
                    email=amazon_email.strip(),
                    password=amazon_password.strip(),
                    book_url=book_url.strip(),
                    book_title=book_title.strip(),
                    max_pages=max_pages,
                    headless=headless
                )

                # セッション状態を更新
                st.session_state.capture_job_id = result.get("job_id")
                st.session_state.capture_running = True
                st.session_state.last_progress = 0

                st.success(f"✅ キャプチャジョブを開始しました！\n\nジョブID: {result.get('job_id')}")
                st.info("🔄 自動的にステータス画面に切り替わります...")

                # 少し待ってからリロード
                time.sleep(2)
                st.rerun()

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
                st.info("💡 FastAPIサーバーが起動しているか確認してください")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")

    # ヒント
    st.markdown("---")
    st.markdown("### 💡 使い方のヒント")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "**🔗 ブックURLの取得方法**\n\n"
            "1. [Kindle Cloud Reader](https://read.amazon.com)を開く\n"
            "2. 読みたい本を選択\n"
            "3. ブラウザのアドレスバーからURLをコピー"
        )
    with col2:
        st.markdown(
            "**⚙️ ヘッドレスモード**\n\n"
            "- ON: ブラウザを表示せず高速処理\n"
            "- OFF: ブラウザの動作を確認できる\n"
            "- デバッグ時はOFFを推奨"
        )
    with col3:
        st.markdown(
            "**📊 処理時間の目安**\n\n"
            "- 1ページあたり約5-10秒\n"
            "- 50ページで約5-8分\n"
            "- ネットワーク速度に依存"
        )


def display_capture_status():
    """キャプチャステータスを表示"""

    st.markdown("### 📊 キャプチャ進捗状況")

    job_id = st.session_state.capture_job_id

    # ステータス取得
    try:
        status_data = get_job_status(job_id)

        status = status_data.get("status")
        progress = status_data.get("progress", 0)
        pages_captured = status_data.get("pages_captured", 0)
        error_message = status_data.get("error_message")

        # ステータス表示
        col1, col2, col3 = st.columns(3)
        with col1:
            status_color = get_status_color(status)
            st.markdown(f"**ステータス:** :{status_color}[{status.upper()}]")
        with col2:
            st.metric("進捗率", f"{progress}%")
        with col3:
            st.metric("キャプチャ済みページ", pages_captured)

        # 進捗バー
        st.progress(progress / 100.0)

        # エラーメッセージ
        if error_message:
            st.error(f"❌ エラー: {error_message}")

        # OCR結果の表示
        if pages_captured > 0:
            st.markdown("---")
            st.markdown("### 📄 OCR結果")

            ocr_results = status_data.get("ocr_results", [])

            if ocr_results:
                # タブで各ページを表示
                tabs = st.tabs([f"ページ {r.get('page_num')}" for r in ocr_results])

                for i, result in enumerate(ocr_results):
                    with tabs[i]:
                        page_num = result.get("page_num")
                        text = result.get("text", "")
                        confidence = result.get("confidence", 0.0)

                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"**ページ番号:** {page_num}")
                        with col2:
                            st.markdown(f"**信頼度:** {confidence:.2%}")

                        st.text_area(
                            f"抽出テキスト (ページ {page_num})",
                            value=text,
                            height=200,
                            disabled=True,
                            label_visibility="collapsed"
                        )

        # ボタン
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 ステータス更新", use_container_width=True):
                st.rerun()

        with col2:
            # 完了またはエラーの場合のみ表示
            if status in ["completed", "failed"]:
                if st.button("🔚 完了・終了", use_container_width=True):
                    st.session_state.capture_running = False
                    st.session_state.capture_job_id = None
                    st.rerun()

        with col3:
            st.page_link("pages/3_📊_Jobs.py", label="📊 ジョブ一覧", use_container_width=True)

        # 自動更新（processing中のみ）
        if status == "processing":
            st.info("🔄 処理中... 5秒後に自動更新されます")
            time.sleep(5)
            st.rerun()
        elif status == "completed":
            st.success("✅ キャプチャが完了しました！")
        elif status == "failed":
            st.error("❌ キャプチャが失敗しました。")

    except APIError as e:
        st.error(f"❌ ステータス取得エラー: {e.message}")
        if e.detail:
            st.error(f"詳細: {e.detail}")

        # エラー時は終了ボタンを表示
        if st.button("🔚 終了", use_container_width=True):
            st.session_state.capture_running = False
            st.session_state.capture_job_id = None
            st.rerun()

    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")

        # エラー時は終了ボタンを表示
        if st.button("🔚 終了", use_container_width=True):
            st.session_state.capture_running = False
            st.session_state.capture_job_id = None
            st.rerun()


if __name__ == "__main__":
    main()
