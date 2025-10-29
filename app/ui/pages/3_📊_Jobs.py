"""
Kindle OCR - Jobs Management Page
ジョブ管理ページ

すべてのOCRジョブを一覧表示・管理
"""
import streamlit as st
import sys
import os
from datetime import datetime
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import list_jobs, get_job_status, APIError

# ページ設定
st.set_page_config(
    page_title="Kindle OCR - Jobs",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .jobs-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .job-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
    }
    .status-processing {
        background-color: #cfe2ff;
        color: #084298;
    }
    .status-completed {
        background-color: #d1e7dd;
        color: #0f5132;
    }
    .status-failed {
        background-color: #f8d7da;
        color: #842029;
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


def get_status_badge_class(status: str) -> str:
    """ステータスに応じたバッジクラスを返す"""
    return f"status-badge status-{status}"


def main():
    # セッション状態の初期化
    if "selected_job_id" not in st.session_state:
        st.session_state.selected_job_id = None
    if "jobs_limit" not in st.session_state:
        st.session_state.jobs_limit = 20
    if "filter_status" not in st.session_state:
        st.session_state.filter_status = "すべて"

    # ヘッダー
    st.markdown('<div class="jobs-header">📊 ジョブ管理</div>', unsafe_allow_html=True)

    st.info(
        "📋 **ジョブ管理**: すべてのOCRジョブを一覧表示し、詳細を確認できます。\n\n"
        "ジョブをクリックすると詳細情報が表示されます。"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("📊 Jobs")
        st.markdown("---")

        st.markdown("### フィルター")

        # ステータスフィルター
        status_options = ["すべて", "pending", "processing", "completed", "failed"]
        filter_status = st.selectbox(
            "ステータス",
            options=status_options,
            index=status_options.index(st.session_state.filter_status),
            help="表示するジョブのステータスを選択"
        )
        st.session_state.filter_status = filter_status

        # 表示件数
        jobs_limit = st.slider(
            "表示件数",
            min_value=5,
            max_value=100,
            value=st.session_state.jobs_limit,
            step=5,
            help="一度に表示するジョブの数"
        )
        st.session_state.jobs_limit = jobs_limit

        st.markdown("---")

        # リフレッシュボタン
        if st.button("🔄 リフレッシュ", use_container_width=True):
            st.rerun()

        st.markdown("---")
        st.markdown("### アクション")

        # CSV エクスポート用
        st.markdown("📥 CSVエクスポート機能は下部にあります")

    # ジョブ一覧取得
    try:
        with st.spinner("🔄 ジョブ一覧を取得中..."):
            jobs = list_jobs(limit=jobs_limit)

        # フィルタリング
        if filter_status != "すべて":
            jobs = [j for j in jobs if j.get("status") == filter_status]

        if not jobs:
            st.info("📭 該当するジョブがありません。")
            st.markdown("左サイドバーから「📤 Upload」または「🤖 Auto Capture」でOCR処理を開始してください。")
            return

        # 統計情報
        st.markdown("### 📈 統計情報")
        col1, col2, col3, col4 = st.columns(4)

        total_jobs = len(jobs)
        completed_jobs = len([j for j in jobs if j.get("status") == "completed"])
        processing_jobs = len([j for j in jobs if j.get("status") == "processing"])
        failed_jobs = len([j for j in jobs if j.get("status") == "failed"])

        with col1:
            st.metric("総ジョブ数", total_jobs)
        with col2:
            st.metric("完了", completed_jobs)
        with col3:
            st.metric("処理中", processing_jobs)
        with col4:
            st.metric("失敗", failed_jobs)

        st.markdown("---")

        # ジョブ一覧テーブル
        st.markdown("### 📋 ジョブ一覧")

        # DataFrame用データ準備
        job_data = []
        for job in jobs:
            job_data.append({
                "選択": False,
                "ジョブID": job.get("job_id", "N/A")[:8] + "...",
                "ステータス": f"{get_status_emoji(job.get('status'))} {job.get('status')}",
                "進捗": f"{job.get('progress', 0)}%",
                "ページ数": job.get("pages_captured", 0),
                "作成日時": format_datetime(job.get("created_at", "")),
                "完了日時": format_datetime(job.get("completed_at", "")) if job.get("completed_at") else "-",
                "_job_id": job.get("job_id")  # 内部用
            })

        # データフレーム表示
        df = pd.DataFrame(job_data)

        # 詳細表示のための選択
        st.markdown("**ジョブをクリックして詳細を表示**")

        # ジョブカード表示
        for idx, job in enumerate(jobs):
            job_id = job.get("job_id")
            status = job.get("status")
            progress = job.get("progress", 0)
            pages_captured = job.get("pages_captured", 0)
            created_at = job.get("created_at", "")
            completed_at = job.get("completed_at")
            error_message = job.get("error_message")

            # ジョブカード
            with st.expander(
                f"{get_status_emoji(status)} **ジョブ {idx + 1}** - {status.upper()} ({progress}%)",
                expanded=(st.session_state.selected_job_id == job_id)
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**ジョブID:** `{job_id}`")
                    st.markdown(f"**ステータス:** {get_status_emoji(status)} {status}")
                    st.markdown(f"**進捗:** {progress}%")
                    st.markdown(f"**キャプチャ済みページ:** {pages_captured}")
                    st.markdown(f"**作成日時:** {format_datetime(created_at)}")
                    if completed_at:
                        st.markdown(f"**完了日時:** {format_datetime(completed_at)}")
                    if error_message:
                        st.error(f"**エラー:** {error_message}")

                with col2:
                    # プログレスバー
                    st.progress(progress / 100.0)

                    # アクションボタン
                    if st.button(f"🔍 詳細を表示", key=f"detail_{job_id}", use_container_width=True):
                        st.session_state.selected_job_id = job_id
                        st.rerun()

                # OCR結果を表示
                if pages_captured > 0:
                    st.markdown("---")
                    st.markdown("#### 📄 OCR結果")

                    if st.button(f"📥 OCR結果を取得", key=f"ocr_{job_id}"):
                        with st.spinner("🔄 OCR結果を取得中..."):
                            try:
                                status_data = get_job_status(job_id)
                                ocr_results = status_data.get("ocr_results", [])

                                if ocr_results:
                                    for result in ocr_results:
                                        page_num = result.get("page_num")
                                        text = result.get("text", "")
                                        confidence = result.get("confidence", 0.0)

                                        st.markdown(f"**ページ {page_num}** (信頼度: {confidence:.2%})")
                                        st.text_area(
                                            f"テキスト (ページ {page_num})",
                                            value=text,
                                            height=150,
                                            disabled=True,
                                            label_visibility="collapsed",
                                            key=f"text_{job_id}_{page_num}"
                                        )
                                else:
                                    st.info("OCR結果はまだありません。")

                            except APIError as e:
                                st.error(f"❌ OCR結果取得エラー: {e.message}")

        st.markdown("---")

        # CSV エクスポート
        st.markdown("### 📥 データエクスポート")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("ジョブデータをCSV形式でダウンロードできます。")

        with col2:
            # エクスポート用データ準備
            export_data = []
            for job in jobs:
                export_data.append({
                    "ジョブID": job.get("job_id"),
                    "ステータス": job.get("status"),
                    "進捗": job.get("progress", 0),
                    "ページ数": job.get("pages_captured", 0),
                    "作成日時": format_datetime(job.get("created_at", "")),
                    "完了日時": format_datetime(job.get("completed_at", "")) if job.get("completed_at") else "",
                    "エラーメッセージ": job.get("error_message", "")
                })

            export_df = pd.DataFrame(export_data)
            csv = export_df.to_csv(index=False).encode('utf-8')

            st.download_button(
                label="📥 CSV ダウンロード",
                data=csv,
                file_name=f"kindle_ocr_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

    except APIError as e:
        st.error(f"❌ ジョブ取得エラー: {e.message}")
        if e.detail:
            st.error(f"詳細: {e.detail}")
        st.info("💡 FastAPIサーバーが起動しているか確認してください")
    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")

    # ヒント
    st.markdown("---")
    st.markdown("### 💡 ヒント")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "**🔍 ジョブ詳細**\n\n"
            "- ジョブカードを展開して詳細を確認\n"
            "- OCR結果ボタンでテキストを表示\n"
            "- ページごとの信頼度を確認"
        )
    with col2:
        st.markdown(
            "**📊 フィルター**\n\n"
            "- ステータスで絞り込み\n"
            "- 表示件数を調整\n"
            "- 定期的にリフレッシュ"
        )
    with col3:
        st.markdown(
            "**📥 エクスポート**\n\n"
            "- CSVでデータを保存\n"
            "- Excelで分析可能\n"
            "- バックアップとして利用"
        )


if __name__ == "__main__":
    main()
