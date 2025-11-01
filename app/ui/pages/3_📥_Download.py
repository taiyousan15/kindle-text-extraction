"""
Text Download Page - テキストダウンロード

OCR結果をさまざまな形式（TXT, CSV, Excel）でダウンロードできるページ
画像ファイル（全ページのスクリーンショット）をZIPでダウンロードできる機能も提供
"""
import streamlit as st
import sys
import os
import pandas as pd
import io
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import list_jobs, get_job_status, APIError
import logging

logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="Text Download - OCR Export",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .download-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #16a085;
        margin-bottom: 1rem;
    }
    .job-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-completed {
        color: #27ae60;
        font-weight: bold;
    }
    .status-processing {
        color: #f39c12;
        font-weight: bold;
    }
    .status-failed {
        color: #e74c3c;
        font-weight: bold;
    }
    .format-option {
        padding: 1rem;
        background-color: #ecf0f1;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ========================================
# ヘルパー関数
# ========================================

def format_timestamp(timestamp: str) -> str:
    """タイムスタンプを読みやすい形式に変換"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y年%m月%d日 %H:%M:%S')
    except:
        return timestamp


def get_status_class(status: str) -> str:
    """ステータスに応じたCSSクラスを返す"""
    status_map = {
        "completed": "status-completed",
        "processing": "status-processing",
        "failed": "status-failed"
    }
    return status_map.get(status, "")


def convert_to_text(ocr_results: List[Dict[str, Any]], book_title: str) -> str:
    """OCR結果をプレーンテキストに変換"""
    lines = [
        f"書籍タイトル: {book_title}",
        f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
        f"総ページ数: {len(ocr_results)}",
        "=" * 80,
        ""
    ]

    for result in ocr_results:
        page_num = result.get("page_num", 0)
        text = result.get("text", "")
        confidence = result.get("confidence", 0.0)

        lines.append(f"--- ページ {page_num} (信頼度: {confidence:.2%}) ---")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def convert_to_csv(ocr_results: List[Dict[str, Any]]) -> str:
    """OCR結果をCSVに変換"""
    df = pd.DataFrame([
        {
            "ページ番号": result.get("page_num", 0),
            "テキスト": result.get("text", ""),
            "信頼度": result.get("confidence", 0.0)
        }
        for result in ocr_results
    ])
    return df.to_csv(index=False, encoding='utf-8-sig')


def convert_to_excel(ocr_results: List[Dict[str, Any]], book_title: str) -> bytes:
    """
    OCR結果をExcelに変換

    Requires: openpyxl package (pip install openpyxl)
    """
    try:
        df = pd.DataFrame([
            {
                "ページ番号": result.get("page_num", 0),
                "テキスト": result.get("text", ""),
                "信頼度": result.get("confidence", 0.0)
            }
            for result in ocr_results
        ])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='OCR結果')

            # メタデータシート
            metadata_df = pd.DataFrame({
                "項目": ["書籍タイトル", "生成日時", "総ページ数", "平均信頼度"],
                "値": [
                    book_title,
                    datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
                    len(ocr_results),
                    f"{sum(r.get('confidence', 0.0) for r in ocr_results) / len(ocr_results):.2%}" if ocr_results else "N/A"
                ]
            })
            metadata_df.to_excel(writer, index=False, sheet_name='メタデータ')

        return output.getvalue()
    except ImportError as e:
        logger.error(f"Excel変換エラー - openpyxlが見つかりません: {e}")
        raise RuntimeError(
            "Excelファイル生成に必要なopenpyxlパッケージがインストールされていません。\n"
            "pip install openpyxl を実行してください。"
        )
    except Exception as e:
        logger.error(f"Excel変換エラー: {e}", exc_info=True)
        raise


def convert_to_markdown(ocr_results: List[Dict[str, Any]], book_title: str) -> str:
    """OCR結果をMarkdownに変換"""
    lines = [
        f"# {book_title}",
        "",
        f"**生成日時:** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
        f"**総ページ数:** {len(ocr_results)}",
        "",
        "---",
        ""
    ]

    for result in ocr_results:
        page_num = result.get("page_num", 0)
        text = result.get("text", "")
        confidence = result.get("confidence", 0.0)

        lines.append(f"## ページ {page_num}")
        lines.append("")
        lines.append(f"**信頼度:** {confidence:.2%}")
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def create_image_zip(job_id: str, captures_base_dir: str = "./captures") -> Optional[bytes]:
    """
    指定されたジョブIDの画像ファイルをZIPに圧縮

    Args:
        job_id: ジョブID
        captures_base_dir: capturesディレクトリのベースパス

    Returns:
        Optional[bytes]: ZIP圧縮されたバイトデータ、失敗時はNone
    """
    try:
        # ジョブディレクトリのパス
        job_dir = Path(captures_base_dir) / job_id

        if not job_dir.exists():
            logger.warning(f"ジョブディレクトリが存在しません: {job_dir}")
            return None

        # page_NNNN.png パターンの画像ファイルを取得
        image_files = sorted(job_dir.glob("page_*.png"))

        if not image_files:
            logger.warning(f"画像ファイルが見つかりません: {job_dir}")
            return None

        # メモリ内でZIPファイルを作成
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for image_path in image_files:
                # ZIPファイル内でのファイル名（ディレクトリ構造を保持しない）
                arcname = image_path.name
                zip_file.write(image_path, arcname=arcname)
                logger.debug(f"ZIPに追加: {arcname}")

        # バイトデータを取得
        zip_bytes = zip_buffer.getvalue()
        logger.info(f"ZIPファイル作成完了: {len(image_files)}ファイル, {len(zip_bytes) / 1024 / 1024:.2f} MB")

        return zip_bytes

    except Exception as e:
        logger.error(f"ZIPファイル作成エラー: {e}", exc_info=True)
        return None


def get_zip_size_mb(zip_bytes: Optional[bytes]) -> float:
    """
    ZIPファイルのサイズをMB単位で取得

    Args:
        zip_bytes: ZIPファイルのバイトデータ

    Returns:
        float: ファイルサイズ（MB）
    """
    if not zip_bytes:
        return 0.0
    return len(zip_bytes) / 1024 / 1024


def format_file_size(size_bytes: int) -> str:
    """
    ファイルサイズを読みやすい形式にフォーマット

    Args:
        size_bytes: ファイルサイズ（バイト）

    Returns:
        str: フォーマットされたファイルサイズ（例: "45.2 MB"）
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.2f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


# ========================================
# メイン画面
# ========================================

def main():
    # ヘッダー
    st.markdown('<div class="download-header">📥 ダウンロード</div>', unsafe_allow_html=True)

    st.info(
        "📄 **Download Options**: OCR処理が完了したジョブから、画像またはテキストをダウンロードできます。\n\n"
        "**画像ダウンロード**: 全ページのスクリーンショットをZIPファイルで取得\n\n"
        "**テキストダウンロード**: OCR抽出テキストを各種形式（TXT/CSV/Excel/Markdown）で取得"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("📥 Download")
        st.markdown("---")

        st.markdown("### ダウンロード手順")
        st.markdown(
            "1. ジョブを選択\n"
            "2. ダウンロード種別を選択\n"
            "3. 形式を選択（テキストの場合）\n"
            "4. ダウンロードボタンをクリック"
        )

        st.markdown("---")
        st.markdown("### ダウンロード種別")
        st.markdown("🖼️ **画像**: スクリーンショット（ZIP）")
        st.markdown("📄 **テキスト**: OCR抽出結果")

        st.markdown("---")
        st.markdown("### テキスト対応形式")
        st.markdown("📄 **TXT**: プレーンテキスト")
        st.markdown("📊 **CSV**: カンマ区切り")
        st.markdown("📈 **XLSX**: Excel形式")
        st.markdown("📝 **MD**: Markdown形式")

        st.markdown("---")

        if st.button("🔄 ジョブ一覧を更新", use_container_width=True):
            st.rerun()

    # ジョブ一覧を取得
    with st.spinner("📚 ジョブ一覧を読み込み中..."):
        try:
            jobs = list_jobs(limit=50)

            # 完了ジョブのみフィルタ
            completed_jobs = [job for job in jobs if job.get("status") == "completed"]

            if not completed_jobs:
                st.warning("⚠️ 完了したジョブがありません。OCR処理を実行してからダウンロードしてください。")
                st.page_link("pages/1_📤_Upload.py", label="📤 手動OCRアップロード", icon="📤")
                st.page_link("pages/2_🤖_Auto_Capture.py", label="🤖 自動キャプチャ", icon="🤖")
                return

            st.success(f"✅ 完了ジョブ: {len(completed_jobs)}件")

            # ジョブ選択
            st.markdown("### 📚 ジョブ選択")

            # ジョブ一覧を表示
            selected_job_id = None

            for job in completed_jobs:
                job_id = job.get("job_id", "")
                created_at = job.get("created_at", "")
                pages_captured = job.get("pages_captured", 0)

                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                    with col1:
                        st.markdown(f"**🆔 {job_id[:8]}...**")

                    with col2:
                        st.markdown(f"**作成日時**")
                        st.markdown(format_timestamp(created_at))

                    with col3:
                        st.markdown(f"**ページ数**")
                        st.markdown(f"{pages_captured} ページ")

                    with col4:
                        if st.button("📥 選択", key=f"select_{job_id}", use_container_width=True, type="primary"):
                            selected_job_id = job_id

                    st.markdown("---")

            # 選択されたジョブの処理
            if selected_job_id or st.session_state.get("selected_job_id"):
                if selected_job_id:
                    st.session_state["selected_job_id"] = selected_job_id
                else:
                    selected_job_id = st.session_state["selected_job_id"]

                render_download_options(selected_job_id)

        except APIError as e:
            st.error(f"❌ APIエラー: {e.message}")
            if e.detail:
                st.error(f"詳細: {e.detail}")
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# ダウンロードオプション表示
# ========================================

def render_download_options(job_id: str):
    """ダウンロードオプションを表示"""
    st.markdown("---")
    st.markdown("### 📥 ダウンロード設定")

    # ジョブの詳細を取得
    with st.spinner("🔍 ジョブ詳細を取得中..."):
        try:
            job_detail = get_job_status(job_id)

            ocr_results = job_detail.get("ocr_results", [])
            pages_captured = job_detail.get("pages_captured", 0)

            if not ocr_results:
                st.warning("⚠️ OCR結果がありません。")
                return

            # ジョブ情報表示
            st.info(
                f"**ジョブID:** {job_id}\n\n"
                f"**ページ数:** {pages_captured}\n\n"
                f"**作成日時:** {format_timestamp(job_detail.get('created_at', ''))}"
            )

            # ダウンロード種別選択（画像 or テキスト）
            st.markdown("#### 📋 ダウンロード種別")

            download_type = st.radio(
                "ダウンロードする内容を選択してください",
                ["🖼️ 画像ファイル（全ページのスクリーンショット）", "📄 文字起こしテキスト（OCR抽出結果）"],
                help="画像ファイル: キャプチャした画像をZIPでダウンロード\n文字起こし: OCR抽出テキストを各種形式でダウンロード"
            )

            st.markdown("---")

            # 書籍タイトル入力
            book_title = st.text_input(
                "📚 書籍タイトル",
                value=f"Kindle_OCR_{job_id[:8]}",
                help="ダウンロードファイルに使用されるタイトル"
            )

            st.markdown("---")

            # ========================================
            # 画像ファイルダウンロード
            # ========================================
            if "🖼️ 画像ファイル" in download_type:
                st.markdown("#### 🖼️ 画像ファイルダウンロード")

                st.info(
                    "📦 **ZIP形式でダウンロード**\n\n"
                    f"• 全 {pages_captured} ページのスクリーンショット画像を含みます\n"
                    "• ファイル形式: PNG\n"
                    "• ファイル名: page_0001.png, page_0002.png, ..."
                )

                # ZIP作成
                with st.spinner("📦 ZIPファイルを作成中..."):
                    # capturesディレクトリの絶対パス
                    captures_dir = os.path.abspath("./captures")
                    zip_bytes = create_image_zip(job_id, captures_dir)

                if zip_bytes is None:
                    st.error("❌ 画像ファイルが見つかりませんでした。キャプチャが正常に完了しているか確認してください。")
                    st.warning(f"💡 確認場所: `captures/{job_id}/`")
                else:
                    zip_size_mb = get_zip_size_mb(zip_bytes)

                    # ダウンロードボタン
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{book_title}_images_{timestamp}.zip"

                    st.download_button(
                        label=f"📥 画像ファイルをダウンロード ({zip_size_mb:.2f} MB)",
                        data=zip_bytes,
                        file_name=filename,
                        mime="application/zip",
                        use_container_width=True,
                        type="primary"
                    )

                    st.success(f"✅ ZIPファイル準備完了: {len(ocr_results)}ファイル、約 {zip_size_mb:.2f} MB")

                    # 画像リスト表示
                    with st.expander("📁 含まれる画像ファイル一覧", expanded=False):
                        for i in range(1, pages_captured + 1):
                            st.markdown(f"• `page_{i:04d}.png`")

            # ========================================
            # 文字起こしテキストダウンロード
            # ========================================
            elif "📄 文字起こしテキスト" in download_type:
                st.markdown("#### 📄 文字起こしテキストダウンロード")

                # テキスト形式選択
                format_option = st.radio(
                    "📋 ファイル形式を選択",
                    ["📄 プレーンテキスト (TXT)", "📊 CSV", "📈 Excel (XLSX)", "📝 Markdown (MD)"],
                    index=0
                )

                st.markdown("---")

                # プレビュー表示
                st.markdown("#### 👀 プレビュー")

                with st.expander("最初の3ページをプレビュー", expanded=False):
                    preview_results = ocr_results[:3]

                    for result in preview_results:
                        page_num = result.get("page_num", 0)
                        text = result.get("text", "")
                        confidence = result.get("confidence", 0.0)

                        st.markdown(f"**ページ {page_num}** (信頼度: {confidence:.2%})")
                        st.text_area(
                            f"page_{page_num}",
                            value=text,
                            height=150,
                            disabled=True,
                            label_visibility="collapsed"
                        )
                        st.markdown("---")

                # ダウンロードボタン
                st.markdown("#### 💾 ダウンロード")

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                if "📄 プレーンテキスト" in format_option:
                    try:
                        text_content = convert_to_text(ocr_results, book_title)
                        st.download_button(
                            label="📥 TXTファイルをダウンロード",
                            data=text_content,
                            file_name=f"{book_title}_{timestamp}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            type="primary"
                        )

                        st.markdown(f"**ファイルサイズ:** 約 {len(text_content.encode('utf-8')) / 1024:.2f} KB")
                    except Exception as e:
                        st.error(f"❌ TXTファイル生成エラー: {str(e)}")
                        logger.error(f"Text download error: {e}", exc_info=True)

                elif "📊 CSV" in format_option:
                    try:
                        csv_content = convert_to_csv(ocr_results)
                        st.download_button(
                            label="📥 CSVファイルをダウンロード",
                            data=csv_content,
                            file_name=f"{book_title}_{timestamp}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            type="primary"
                        )

                        st.markdown(f"**ファイルサイズ:** 約 {len(csv_content.encode('utf-8')) / 1024:.2f} KB")
                        st.markdown("**形式:** UTF-8 with BOM (Excelで文字化けしません)")
                    except Exception as e:
                        st.error(f"❌ CSVファイル生成エラー: {str(e)}")
                        logger.error(f"CSV download error: {e}", exc_info=True)

                elif "📈 Excel" in format_option:
                    try:
                        excel_content = convert_to_excel(ocr_results, book_title)
                        st.download_button(
                            label="📥 Excelファイルをダウンロード",
                            data=excel_content,
                            file_name=f"{book_title}_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )

                        st.markdown(f"**ファイルサイズ:** 約 {len(excel_content) / 1024:.2f} KB")
                        st.markdown("**シート:** OCR結果 + メタデータ")
                    except RuntimeError as e:
                        st.error(f"❌ Excelファイル生成エラー")
                        st.error(str(e))
                        st.info("💡 **解決方法**: `pip install openpyxl` を実行してください")
                    except Exception as e:
                        st.error(f"❌ 予期しないエラーが発生しました: {str(e)}")
                        logger.error(f"Excel download error: {e}", exc_info=True)

                elif "📝 Markdown" in format_option:
                    try:
                        markdown_content = convert_to_markdown(ocr_results, book_title)
                        st.download_button(
                            label="📥 Markdownファイルをダウンロード",
                            data=markdown_content,
                            file_name=f"{book_title}_{timestamp}.md",
                            mime="text/markdown",
                            use_container_width=True,
                            type="primary"
                        )

                        st.markdown(f"**ファイルサイズ:** 約 {len(markdown_content.encode('utf-8')) / 1024:.2f} KB")
                        st.markdown("**用途:** GitHub, Notion, Obsidian等に最適")
                    except Exception as e:
                        st.error(f"❌ Markdownファイル生成エラー: {str(e)}")
                        logger.error(f"Markdown download error: {e}", exc_info=True)

            # ========================================
            # 統計情報（共通）
            # ========================================
            st.markdown("---")
            st.markdown("#### 📊 統計情報")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("総ページ数", pages_captured)

            with col2:
                avg_confidence = sum(r.get("confidence", 0.0) for r in ocr_results) / len(ocr_results) if ocr_results else 0.0
                st.metric("平均信頼度", f"{avg_confidence:.2%}")

            with col3:
                total_chars = sum(len(r.get("text", "")) for r in ocr_results)
                st.metric("総文字数", f"{total_chars:,}")

        except APIError as e:
            st.error(f"❌ APIエラー: {e.message}")
            if e.detail:
                st.error(f"詳細: {e.detail}")
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")


if __name__ == "__main__":
    main()
