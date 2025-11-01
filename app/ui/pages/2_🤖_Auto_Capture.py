"""
Kindle OCR - Auto Capture Page
自動キャプチャページ

Kindle Cloud Readerから自動的にページをキャプチャしてOCR処理
シングルモード: 1冊ずつ処理
バッチモード: 複数冊（最大50冊）を一括処理
"""
import streamlit as st
import sys
import os
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

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
    .batch-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        margin: 0.5rem 0;
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
    if "batch_jobs" not in st.session_state:
        st.session_state.batch_jobs = []
    if "batch_running" not in st.session_state:
        st.session_state.batch_running = False

    # ヘッダー
    st.markdown('<div class="capture-header">🤖 自動キャプチャ</div>', unsafe_allow_html=True)

    st.info(
        "🚀 **自動キャプチャ**: Kindle Cloud Readerから自動的に複数ページをキャプチャし、OCR処理を実行します。\n\n"
        "**シングルモード**: 1冊ずつ処理 | **バッチモード**: 複数冊（最大50冊）を一括処理\n\n"
        "✨ **新機能**: 総ページ数の自動検出 | 高精度OCR（90%+ 信頼度目標）"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("🤖 Auto Capture")
        st.markdown("---")

        capture_mode = st.radio(
            "キャプチャモード",
            ["📖 シングルモード", "📚 バッチモード"],
            index=0
        )

        st.markdown("---")
        st.markdown("### キャプチャ手順")

        if "シングル" in capture_mode:
            st.markdown(
                "1. Amazon認証情報を入力\n"
                "2. Kindle Cloud ReaderのブックURLを入力\n"
                "3. 書籍タイトルと最大ページ数を設定\n"
                "4. キャプチャ開始ボタンをクリック\n"
                "5. リアルタイムで進捗を確認"
            )
        else:
            st.markdown(
                "1. Amazon認証情報を入力\n"
                "2. 書籍リストをCSVまたは手動で追加\n"
                "3. 各書籍の設定を確認\n"
                "4. バッチ開始ボタンをクリック\n"
                "5. 全書籍の進捗を監視"
            )

        st.markdown("---")
        st.markdown("### 注意事項")
        st.markdown(
            "⚠️ Amazon認証情報は安全に保管されます\n\n"
            "⏱️ 処理時間はページ数に応じて変動\n\n"
            "🔄 処理中はページを閉じないでください"
        )

        if "バッチ" in capture_mode:
            st.markdown("---")
            st.markdown("### バッチモード情報")
            st.markdown(
                "📚 最大処理冊数: 50冊\n\n"
                "🔄 順次処理: 1冊ずつ実行\n\n"
                "⏱️ 推定時間: 冊数×5-10分"
            )

    # メインコンテンツ
    if "シングル" in capture_mode:
        # シングルモード
        if st.session_state.capture_running and st.session_state.capture_job_id:
            display_capture_status()
        else:
            display_capture_form()
    else:
        # バッチモード
        if st.session_state.batch_running:
            display_batch_status()
        else:
            display_batch_form()


# ========================================
# シングルモード
# ========================================

def display_capture_form():
    """キャプチャ開始フォームを表示（シングルモード）"""

    st.markdown("### ⚙️ シングルキャプチャ設定")

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

        # ページ数は自動検出されるため、フォールバック値のみ設定
        st.info("📊 **ページ数は自動検出されます**\n\n"
                "Kindle Cloud Readerから総ページ数を自動的に検出してキャプチャします。\n"
                "検出できない場合のみ、以下のフォールバック値を使用します。")

        max_pages = st.number_input(
            "フォールバック最大ページ数（自動検出失敗時のみ使用）",
            min_value=1,
            max_value=1000,
            value=500,
            help="自動検出に失敗した場合に使用する最大ページ数"
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
    """キャプチャステータスを表示（シングルモード）"""

    st.markdown("### 📊 キャプチャ進捗状況")

    job_id = st.session_state.capture_job_id

    # ステータス取得
    try:
        status_data = get_job_status(job_id)

        status = status_data.get("status")
        progress = status_data.get("progress", 0)
        pages_captured = status_data.get("pages_captured", 0)
        error_message = status_data.get("error_message")
        actual_total_pages = status_data.get("actual_total_pages")  # 自動検出された総ページ数

        # ステータス表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            status_color = get_status_color(status)
            st.markdown(f"**ステータス:** :{status_color}[{status.upper()}]")
        with col2:
            st.metric("進捗率", f"{progress}%")
        with col3:
            st.metric("キャプチャ済みページ", pages_captured)
        with col4:
            if actual_total_pages:
                st.metric("検出総ページ数", f"{actual_total_pages}ページ", delta="自動検出")
            else:
                st.metric("総ページ数", "未検出", delta="手動設定")

        # 進捗バー
        st.progress(progress / 100.0)

        # エラーメッセージ
        if error_message:
            st.error(f"❌ エラー: {error_message}")

        # スタック検出: 100%だがOCR結果が0件の場合
        if progress == 100 and status == "processing" and pages_captured == 0:
            st.warning(
                "⚠️ **ジョブがスタックしている可能性があります**\n\n"
                "進捗率は100%ですが、OCR結果が保存されていません。\n\n"
                "これは大量の画像処理中にバックグラウンドプロセスがクラッシュした可能性があります。\n\n"
                "**対処方法**: サポートに連絡するか、`fix_stuck_job.py`スクリプトを実行してください。"
            )

        # OCR結果の表示
        if pages_captured > 0:
            st.markdown("---")
            st.markdown("### 📄 OCR結果")

            ocr_results = status_data.get("ocr_results", [])

            if ocr_results:
                # 最新5件のみ表示
                display_results = ocr_results[-5:]

                for result in display_results:
                    page_num = result.get("page_num")
                    text = result.get("text", "")
                    confidence = result.get("confidence", 0.0)

                    with st.expander(f"ページ {page_num} (信頼度: {confidence:.2%})"):
                        st.text_area(
                            f"page_{page_num}",
                            value=text[:500] + ("..." if len(text) > 500 else ""),
                            height=150,
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

        if st.button("🔚 終了", use_container_width=True):
            st.session_state.capture_running = False
            st.session_state.capture_job_id = None
            st.rerun()

    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")

        if st.button("🔚 終了", use_container_width=True):
            st.session_state.capture_running = False
            st.session_state.capture_job_id = None
            st.rerun()


# ========================================
# バッチモード
# ========================================

def display_batch_form():
    """バッチキャプチャフォームを表示"""

    st.markdown("### 📚 バッチキャプチャ設定")

    # Amazon認証情報（全書籍共通）
    st.markdown("#### 🔐 Amazon認証情報（全書籍共通）")

    col1, col2 = st.columns(2)
    with col1:
        amazon_email = st.text_input(
            "Amazonアカウント (Email)",
            placeholder="example@email.com",
            key="batch_email"
        )
    with col2:
        amazon_password = st.text_input(
            "Amazonパスワード",
            type="password",
            placeholder="パスワードを入力",
            key="batch_password"
        )

    st.markdown("---")

    # 書籍リスト入力
    st.markdown("#### 📚 書籍リスト")

    input_method = st.radio(
        "入力方法",
        ["手動入力", "CSVファイルアップロード"],
        horizontal=True
    )

    # セッション状態に書籍リストを保存
    if "book_list" not in st.session_state:
        st.session_state.book_list = []

    if input_method == "CSVファイルアップロード":
        st.markdown("##### 📄 CSVファイル形式")
        st.code(
            "book_title,book_url,max_pages\n"
            "プロンプトエンジニアリング入門,https://read.amazon.com/...,50\n"
            "AI活用ガイド,https://read.amazon.com/...,100",
            language="csv"
        )

        uploaded_file = st.file_uploader(
            "CSVファイルを選択",
            type=["csv"],
            help="書籍タイトル、URL、最大ページ数を含むCSVファイル"
        )

        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)

                # 必須カラムの確認
                required_columns = ["book_title", "book_url", "max_pages"]
                if all(col in df.columns for col in required_columns):
                    st.session_state.book_list = df.to_dict('records')
                    st.success(f"✅ {len(st.session_state.book_list)}冊の書籍を読み込みました")
                else:
                    st.error(f"❌ CSVファイルに必須カラムが含まれていません: {required_columns}")
            except Exception as e:
                st.error(f"❌ CSVファイルの読み込みエラー: {str(e)}")

    else:
        # 手動入力
        st.markdown("##### ✍️ 書籍情報を手動で追加")

        with st.form("add_book_form"):
            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                new_title = st.text_input("書籍タイトル", key="new_title")
            with col2:
                new_url = st.text_input("Kindle URL", key="new_url")
            with col3:
                new_max_pages = st.number_input("最大ページ", min_value=1, max_value=1000, value=50, key="new_max_pages")

            add_button = st.form_submit_button("➕ 追加", use_container_width=True)

            if add_button:
                if new_title.strip() and new_url.strip():
                    st.session_state.book_list.append({
                        "book_title": new_title.strip(),
                        "book_url": new_url.strip(),
                        "max_pages": new_max_pages
                    })
                    st.success(f"✅ 「{new_title}」を追加しました")
                    st.rerun()
                else:
                    st.error("❌ 書籍タイトルとURLを入力してください")

    # 書籍リスト表示
    if st.session_state.book_list:
        st.markdown("---")
        st.markdown(f"##### 📋 登録済み書籍一覧 ({len(st.session_state.book_list)}冊)")

        if len(st.session_state.book_list) > 50:
            st.warning("⚠️ 書籍数が50冊を超えています。最初の50冊のみ処理されます。")

        for i, book in enumerate(st.session_state.book_list[:50]):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 4, 2, 1])

                with col1:
                    st.markdown(f"**{i+1}. {book['book_title']}**")
                with col2:
                    st.markdown(f"`{book['book_url'][:40]}...`")
                with col3:
                    st.markdown(f"最大ページ: {book['max_pages']}")
                with col4:
                    if st.button("🗑️", key=f"delete_{i}", help="削除"):
                        st.session_state.book_list.pop(i)
                        st.rerun()

        st.markdown("---")

        # バッチ開始設定
        col1, col2 = st.columns([1, 1])

        with col1:
            headless = st.checkbox(
                "ヘッドレスモード",
                value=True,
                help="ブラウザを表示せずにバックグラウンドで実行",
                key="batch_headless"
            )

        with col2:
            st.markdown(f"**推定処理時間:** 約 {len(st.session_state.book_list) * 7} 分")

        # バッチ開始ボタン
        all_filled = amazon_email.strip() and amazon_password.strip() and len(st.session_state.book_list) > 0

        start_batch_button = st.button(
            f"🚀 バッチ開始（{len(st.session_state.book_list)}冊）",
            type="primary",
            use_container_width=True,
            disabled=not all_filled
        )

        if not all_filled:
            st.warning("⚠️ Amazon認証情報を入力し、少なくとも1冊の書籍を登録してください")

        # バッチ開始処理
        if start_batch_button:
            with st.spinner("🔄 バッチキャプチャを開始しています..."):
                try:
                    # 各書籍のジョブを開始
                    batch_jobs = []

                    for book in st.session_state.book_list[:50]:
                        result = start_auto_capture(
                            email=amazon_email.strip(),
                            password=amazon_password.strip(),
                            book_url=book["book_url"],
                            book_title=book["book_title"],
                            max_pages=book["max_pages"],
                            headless=headless
                        )

                        batch_jobs.append({
                            "job_id": result.get("job_id"),
                            "book_title": book["book_title"],
                            "max_pages": book["max_pages"],
                            "status": "pending",
                            "progress": 0,
                            "pages_captured": 0
                        })

                        # 少し待機（サーバー負荷軽減）
                        time.sleep(1)

                    # セッション状態を更新
                    st.session_state.batch_jobs = batch_jobs
                    st.session_state.batch_running = True

                    st.success(f"✅ {len(batch_jobs)}冊のバッチキャプチャを開始しました！")
                    st.info("🔄 自動的にステータス画面に切り替わります...")

                    time.sleep(2)
                    st.rerun()

                except APIError as e:
                    st.error(f"❌ APIエラー: {e.message}")
                    if e.detail:
                        st.error(f"詳細: {e.detail}")
                except Exception as e:
                    st.error(f"❌ エラーが発生しました: {str(e)}")

    else:
        st.info("📚 書籍を追加してください")

    # リセットボタン
    if st.session_state.book_list:
        if st.button("🗑️ リスト全削除", use_container_width=True):
            st.session_state.book_list = []
            st.rerun()


def display_batch_status():
    """バッチキャプチャステータスを表示"""

    st.markdown("### 📊 バッチキャプチャ進捗状況")

    batch_jobs = st.session_state.batch_jobs

    # 各ジョブのステータスを更新
    try:
        updated_jobs = []

        for job in batch_jobs:
            try:
                status_data = get_job_status(job["job_id"])

                updated_jobs.append({
                    "job_id": job["job_id"],
                    "book_title": job["book_title"],
                    "max_pages": job["max_pages"],
                    "status": status_data.get("status", "pending"),
                    "progress": status_data.get("progress", 0),
                    "pages_captured": status_data.get("pages_captured", 0),
                    "error_message": status_data.get("error_message")
                })
            except:
                # エラー時は既存情報を保持
                updated_jobs.append(job)

        st.session_state.batch_jobs = updated_jobs

        # 全体統計
        total_jobs = len(updated_jobs)
        completed_jobs = sum(1 for j in updated_jobs if j["status"] == "completed")
        failed_jobs = sum(1 for j in updated_jobs if j["status"] == "failed")
        processing_jobs = sum(1 for j in updated_jobs if j["status"] == "processing")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総冊数", total_jobs)
        with col2:
            st.metric("完了", completed_jobs, delta=f"{completed_jobs/total_jobs*100:.0f}%")
        with col3:
            st.metric("処理中", processing_jobs)
        with col4:
            st.metric("失敗", failed_jobs)

        # 全体進捗バー
        overall_progress = (completed_jobs + failed_jobs) / total_jobs if total_jobs > 0 else 0
        st.progress(overall_progress)

        st.markdown("---")

        # 各書籍のステータス
        st.markdown("### 📚 各書籍の詳細")

        for i, job in enumerate(updated_jobs):
            status_color = get_status_color(job["status"])

            with st.expander(
                f"{i+1}. {job['book_title']} - :{status_color}[{job['status'].upper()}] ({job['progress']}%)",
                expanded=(job["status"] == "processing")
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**ジョブID:** {job['job_id'][:8]}...")
                with col2:
                    st.markdown(f"**進捗:** {job['progress']}%")
                with col3:
                    st.markdown(f"**キャプチャ済み:** {job['pages_captured']}/{job['max_pages']}")

                if job.get("error_message"):
                    st.error(f"❌ エラー: {job['error_message']}")

                # 進捗バー
                st.progress(job['progress'] / 100.0)

        # ボタン
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 ステータス更新", use_container_width=True):
                st.rerun()

        with col2:
            if completed_jobs + failed_jobs == total_jobs:
                if st.button("🔚 完了・終了", use_container_width=True):
                    st.session_state.batch_running = False
                    st.session_state.batch_jobs = []
                    st.session_state.book_list = []
                    st.rerun()

        with col3:
            st.page_link("pages/3_📊_Jobs.py", label="📊 ジョブ一覧", use_container_width=True)

        # 自動更新
        if processing_jobs > 0:
            st.info("🔄 処理中... 10秒後に自動更新されます")
            time.sleep(10)
            st.rerun()
        elif completed_jobs + failed_jobs == total_jobs:
            st.success(f"✅ バッチキャプチャが完了しました！ (完了: {completed_jobs}, 失敗: {failed_jobs})")

    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")

        if st.button("🔚 終了", use_container_width=True):
            st.session_state.batch_running = False
            st.session_state.batch_jobs = []
            st.rerun()


if __name__ == "__main__":
    main()
