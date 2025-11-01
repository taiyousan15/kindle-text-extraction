"""
Kindle OCR - Streamlit Home Page
書籍自動文字起こしシステム - メインページ

システムの概要、ステータス、最近のジョブを表示
Amazon認証ログインシステム統合
"""
import streamlit as st
import sys
import os
from datetime import datetime
import time
from pathlib import Path
import subprocess
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.ui.utils.api_client import get_health, list_jobs, APIError
from app.services.capture.selenium_capture import SeleniumKindleCapture, SeleniumCaptureConfig

logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="Kindle OCR - ホーム",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #e0e0e0;
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .stat-label {
        font-size: 1rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .health-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .health-healthy {
        background-color: #4caf50;
    }
    .health-unhealthy {
        background-color: #f44336;
    }
    .login-container {
        max-width: 500px;
        margin: 3rem auto;
        padding: 2.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .login-header {
        font-size: 2rem;
        font-weight: bold;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-success {
        background-color: #4caf50;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin-top: 1rem;
    }
    .login-info {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def format_datetime(dt_str):
    """日時文字列をフォーマット"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


def get_status_emoji(status: str) -> str:
    """ステータスに応じた絵文字を返す"""
    status_map = {
        "pending": "⏳",
        "processing": "⚙️",
        "completed": "✅",
        "failed": "❌"
    }
    return status_map.get(status, "❓")


def check_amazon_cookie_exists(email: str) -> bool:
    """Amazon Cookieが保存されているかチェック"""
    cookies_dir = Path(".amazon_cookies")
    cookie_file = cookies_dir / f"amazon_{email.replace('@', '_at_')}.pkl"
    return cookie_file.exists()


def test_amazon_login(email: str, password: str) -> tuple[bool, str]:
    """
    Amazonログインテスト（2FA対応）

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Kindle Cloud Readerの実際のURL（ログインテスト用）
        config = SeleniumCaptureConfig(
            book_url="https://read.amazon.co.jp/kindle-library",
            book_title="login_test",
            amazon_email=email,
            amazon_password=password,
            max_pages=1,
            headless=False  # 2FA入力のためブラウザ表示
        )

        capturer = SeleniumKindleCapture(config)

        # ログインのみ実行
        login_success = capturer.login_amazon()

        # ブラウザクローズ
        capturer.close()

        if login_success:
            return True, "Amazon認証が成功しました。Cookieを保存しました。"
        else:
            return False, "Amazonログインに失敗しました。メールアドレス・パスワードを確認してください。"

    except Exception as e:
        logger.error(f"ログインテストエラー: {e}", exc_info=True)
        return False, f"エラーが発生しました: {str(e)}"


def render_login_screen():
    """Amazonログイン画面を表示"""
    st.markdown('<div class="login-header">🔐 Amazon認証</div>', unsafe_allow_html=True)

    st.info(
        "**Kindle OCRシステムへようこそ**\n\n"
        "このシステムを使用するには、Amazon Kindleアカウントでの認証が必要です。\n\n"
        "初回ログイン時は、2段階認証（SMS/メールコード）の入力が必要です。\n"
        "認証情報は安全に保存され、次回以降は自動的にログインされます。"
    )

    st.markdown("---")

    # ログインフォーム
    with st.form("amazon_login_form"):
        st.markdown("### 認証情報を入力")

        amazon_email = st.text_input(
            "Amazonメールアドレス",
            placeholder="example@amazon.co.jp",
            help="Kindleアカウントのメールアドレス"
        )

        amazon_password = st.text_input(
            "Amazonパスワード",
            type="password",
            help="Kindleアカウントのパスワード"
        )

        st.markdown("---")

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(
                '<div class="login-info">'
                '⚠️ <strong>重要:</strong> ログイン時にブラウザが開きます。'
                'SMS/メールで届いた認証コードを入力してください（最大3分）。'
                '</div>',
                unsafe_allow_html=True
            )

        with col2:
            submit_button = st.form_submit_button(
                "🔐 ログイン",
                use_container_width=True,
                type="primary"
            )

    # ログイン処理
    if submit_button:
        if not amazon_email or not amazon_password:
            st.error("❌ メールアドレスとパスワードを入力してください")
            return

        # Cookie存在チェック
        has_cookie = check_amazon_cookie_exists(amazon_email)

        if has_cookie:
            st.info("🍪 保存されたCookieが見つかりました。自動ログインを試行します...")
        else:
            st.warning("📂 初回ログインです。ブラウザが開きます。2段階認証コードを入力してください。")

        # ログイン実行
        with st.spinner("🔄 Amazonログイン中..."):
            success, message = test_amazon_login(amazon_email, amazon_password)

        if success:
            # セッションに保存
            st.session_state["amazon_logged_in"] = True
            st.session_state["amazon_email"] = amazon_email
            st.session_state["amazon_password"] = amazon_password

            st.markdown(
                f'<div class="login-success">✅ {message}</div>',
                unsafe_allow_html=True
            )
            st.success("🎉 ログイン成功！ページが自動的にリロードされます...")
            time.sleep(2)
            st.rerun()
        else:
            st.error(f"❌ {message}")
            st.info("💡 2段階認証コードの入力時間が足りない場合は、再度お試しください。")


def render_main_dashboard():
    """メインダッシュボード（ログイン後）"""
    # ヘッダー
    st.markdown('<div class="main-header">📚 Kindle OCR - 書籍自動文字起こしシステム</div>', unsafe_allow_html=True)

    # ログイン中のユーザー情報を表示
    amazon_email = st.session_state.get("amazon_email", "未認証")
    st.success(f"✅ Amazon認証済み: {amazon_email}")

    # サイドバー
    with st.sidebar:
        st.title("📚 Kindle OCR")
        st.markdown("---")

        # ログインユーザー情報
        st.markdown(f"👤 **ログイン中**")
        st.markdown(f"📧 {amazon_email}")

        st.markdown("---")
        st.markdown("### ナビゲーション")
        st.markdown("📤 **Upload** - 手動OCR")
        st.markdown("🤖 **Auto Capture** - 自動キャプチャ")
        st.markdown("📊 **Jobs** - ジョブ管理")
        st.markdown("---")
        st.markdown("### システム情報")

        # ヘルスチェック
        try:
            health = get_health()
            is_healthy = health.get("status") == "healthy"
            health_class = "health-healthy" if is_healthy else "health-unhealthy"
            health_text = "正常" if is_healthy else "異常"

            st.markdown(
                f'<div><span class="health-indicator {health_class}"></span><strong>API:</strong> {health_text}</div>',
                unsafe_allow_html=True
            )
            st.markdown(f"**データベース:** {health.get('database', 'N/A')}")
            st.markdown(f"**接続プール:** {health.get('pool_size', 'N/A')}")

        except APIError as e:
            st.error(f"❌ API接続エラー: {e.message}")
        except Exception as e:
            st.error(f"❌ エラー: {str(e)}")

        st.markdown("---")
        col_refresh, col_logout = st.columns(2)

        with col_refresh:
            if st.button("🔄", use_container_width=True, help="リフレッシュ"):
                st.rerun()

        with col_logout:
            if st.button("🚪", use_container_width=True, help="ログアウト", type="primary"):
                # セッションクリア
                st.session_state.clear()
                st.success("ログアウトしました")
                time.sleep(1)
                st.rerun()

    # メインコンテンツ
    st.markdown("### システム概要")
    st.info(
        "📖 **Kindle OCR** は、Kindle書籍のスクリーンショットから自動的にテキストを抽出し、\n"
        "検索可能な知識ベースを構築するシステムです。\n\n"
        "**主な機能:**\n"
        "- 📤 **手動OCR**: 個別の画像ファイルをアップロードしてテキスト抽出\n"
        "- 🤖 **自動キャプチャ**: Kindle Cloud Readerから自動的にページをキャプチャしてOCR処理\n"
        "- 📊 **ジョブ管理**: すべてのOCRジョブを一覧表示・管理"
    )

    st.markdown("---")

    # クイック統計
    st.markdown("### 📊 クイック統計")

    try:
        jobs = list_jobs(limit=100)

        # 統計計算
        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j.get("status") == "completed"])
        failed_jobs = len([j for j in jobs if j.get("status") == "failed"])
        total_pages = sum([j.get("pages_captured", 0) for j in jobs])
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

        # 3カラムでステータス表示
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f'''
                <div class="stat-box">
                    <div class="stat-number">{total_jobs}</div>
                    <div class="stat-label">総ジョブ数</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f'''
                <div class="stat-box">
                    <div class="stat-number">{total_pages}</div>
                    <div class="stat-label">OCR処理ページ数</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f'''
                <div class="stat-box">
                    <div class="stat-number">{completed_jobs}</div>
                    <div class="stat-label">完了ジョブ数</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                f'''
                <div class="stat-box">
                    <div class="stat-number">{success_rate:.1f}%</div>
                    <div class="stat-label">成功率</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

    except APIError as e:
        st.error(f"❌ データ取得エラー: {e.message}")
    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")

    st.markdown("---")

    # 最近のジョブ
    st.markdown("### 📋 最近のジョブ")

    try:
        jobs = list_jobs(limit=10)

        if jobs:
            # テーブル用データ準備
            job_data = []
            for job in jobs:
                job_data.append({
                    "ステータス": f"{get_status_emoji(job.get('status'))} {job.get('status')}",
                    "ジョブID": job.get("job_id", "N/A")[:8] + "...",
                    "進捗": f"{job.get('progress', 0)}%",
                    "ページ数": job.get("pages_captured", 0),
                    "作成日時": format_datetime(job.get("created_at", "")),
                })

            # データフレーム表示
            st.dataframe(
                job_data,
                use_container_width=True,
                hide_index=True
            )

            st.info("💡 **詳細を確認**: 左サイドバーから「📊 Jobs」ページでジョブの詳細を確認できます。")

        else:
            st.info("📭 まだジョブがありません。左サイドバーから「📤 Upload」または「🤖 Auto Capture」でOCR処理を開始してください。")

    except APIError as e:
        st.error(f"❌ ジョブ取得エラー: {e.message}")
        st.info("💡 FastAPIサーバーが起動しているか確認してください: `uvicorn app.main:app --reload`")
    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")

    st.markdown("---")

    # クイックスタート
    st.markdown("### 🚀 クイックスタート")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📤 手動OCR")
        st.markdown(
            "1. 左サイドバーから「📤 Upload」ページに移動\n"
            "2. 画像ファイル (.png, .jpg, .jpeg) をアップロード\n"
            "3. 書籍タイトルとページ番号を入力\n"
            "4. 「アップロード」ボタンをクリック\n"
            "5. OCR結果を確認"
        )

    with col2:
        st.markdown("#### 🤖 自動キャプチャ")
        st.markdown(
            "1. 左サイドバーから「🤖 Auto Capture」ページに移動\n"
            "2. Amazon認証情報を入力\n"
            "3. Kindle Cloud ReaderのブックURLを入力\n"
            "4. 「キャプチャ開始」ボタンをクリック\n"
            "5. リアルタイムで進捗を確認"
        )

    st.markdown("---")

    # フッター
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 2rem 0;">
            <p>📚 Kindle OCR v1.0.0 (Phase 1-6 MVP)</p>
            <p>Powered by FastAPI, Streamlit, Tesseract OCR</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def main():
    """メインエントリーポイント - ログイン状態で画面を切り替え"""
    # セッション状態の初期化
    if "amazon_logged_in" not in st.session_state:
        st.session_state["amazon_logged_in"] = False

    # ログイン状態で画面を切り替え
    if st.session_state.get("amazon_logged_in", False):
        # ログイン済み -> メインダッシュボード表示
        render_main_dashboard()
    else:
        # 未ログイン -> ログイン画面表示
        render_login_screen()


if __name__ == "__main__":
    main()
