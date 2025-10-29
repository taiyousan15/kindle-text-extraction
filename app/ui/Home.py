"""
Kindle OCR - Streamlit Home Page
書籍自動文字起こしシステム - メインページ

システムの概要、ステータス、最近のジョブを表示
"""
import streamlit as st
import sys
import os
from datetime import datetime
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.ui.utils.api_client import get_health, list_jobs, APIError

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


def main():
    # ヘッダー
    st.markdown('<div class="main-header">📚 Kindle OCR - 書籍自動文字起こしシステム</div>', unsafe_allow_html=True)

    # サイドバー
    with st.sidebar:
        st.title("📚 Kindle OCR")
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
        if st.button("🔄 リフレッシュ", use_container_width=True):
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


if __name__ == "__main__":
    main()
