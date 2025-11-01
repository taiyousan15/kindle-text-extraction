"""
Summary Page - 要約生成

OCR結果からAIを使用して高度な要約を生成するページ
シングルレベル要約とマルチレベル要約（3段階）に対応
"""
import streamlit as st
import sys
import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import list_jobs, APIError, API_BASE_URL
import logging

logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="Summary - AI Text Summarization",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .summary-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #9b59b6;
        margin-bottom: 1rem;
    }
    .summary-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #dee2e6;
        margin: 1rem 0;
    }
    .level-1-box {
        background-color: #e8f5e9;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #4caf50;
        margin: 1rem 0;
    }
    .level-2-box {
        background-color: #fff3e0;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #ff9800;
        margin: 1rem 0;
    }
    .level-3-box {
        background-color: #e3f2fd;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ========================================
# API クライアント関数
# ========================================

def create_summary(
    job_id: Optional[str] = None,
    text: Optional[str] = None,
    book_title: Optional[str] = None,
    length: str = "medium",
    tone: str = "professional",
    granularity: str = "high_level",
    format_type: str = "plain_text",
    language: str = "ja"
) -> Dict[str, Any]:
    """要約を作成"""
    url = f"{API_BASE_URL}/api/v1/summary/create"

    payload = {
        "length": length,
        "tone": tone,
        "granularity": granularity,
        "format": format_type,
        "language": language
    }

    if job_id:
        payload["job_id"] = job_id
    elif text:
        payload["text"] = text
        payload["book_title"] = book_title or "Untitled"
    else:
        raise ValueError("Either job_id or text must be provided")

    try:
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        raise APIError(
            message=f"APIエラー: {response.status_code}",
            status_code=response.status_code,
            detail=error_detail
        )
    except Exception as e:
        raise APIError(message=f"要約作成エラー: {str(e)}", detail=str(e))


def create_multilevel_summary(
    job_id: Optional[str] = None,
    text: Optional[str] = None,
    book_title: Optional[str] = None,
    tone: str = "professional",
    format_type: str = "plain_text",
    language: str = "ja"
) -> Dict[str, Any]:
    """マルチレベル要約を作成（3段階）"""
    url = f"{API_BASE_URL}/api/v1/summary/create-multilevel"

    payload = {
        "tone": tone,
        "format": format_type,
        "language": language
    }

    if job_id:
        payload["job_id"] = job_id
    elif text:
        payload["text"] = text
        payload["book_title"] = book_title or "Untitled"
    else:
        raise ValueError("Either job_id or text must be provided")

    try:
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        raise APIError(
            message=f"APIエラー: {response.status_code}",
            status_code=response.status_code,
            detail=error_detail
        )
    except Exception as e:
        raise APIError(message=f"マルチレベル要約作成エラー: {str(e)}", detail=str(e))


# ========================================
# メイン画面
# ========================================

def main():
    # ヘッダー
    st.markdown('<div class="summary-header">🧠 AI要約生成</div>', unsafe_allow_html=True)

    st.info(
        "🤖 **AI Summary**: OCR処理済みのテキストから、AIを使用して高度な要約を生成します。\n\n"
        "**シングルレベル要約**: カスタマイズ可能な1つの要約を生成\n\n"
        "**マルチレベル要約**: エグゼクティブ・標準・詳細の3段階の要約を一度に生成"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("🧠 Summary")
        st.markdown("---")

        summary_mode = st.radio(
            "要約モード",
            ["📝 シングルレベル要約", "📚 マルチレベル要約（3段階）"],
            index=0
        )

        st.markdown("---")
        st.markdown("### 💡 機能説明")

        if "シングルレベル" in summary_mode:
            st.markdown(
                "**シングルレベル要約**\n\n"
                "1. ジョブを選択\n"
                "2. 要約パラメータを設定\n"
                "3. 要約生成実行\n"
                "4. 結果をダウンロード"
            )
        else:
            st.markdown(
                "**マルチレベル要約**\n\n"
                "1. ジョブを選択\n"
                "2. トーンと形式を設定\n"
                "3. 要約生成実行\n"
                "4. 3段階の要約を確認"
            )

        st.markdown("---")
        st.markdown("### ⚙️ 要約オプション")
        st.markdown("📏 **Length**: 要約の長さ")
        st.markdown("🎭 **Tone**: 文章のトーン")
        st.markdown("🔍 **Granularity**: 詳細度")
        st.markdown("📄 **Format**: 出力形式")

    # ジョブ一覧を取得
    with st.spinner("📚 ジョブ一覧を読み込み中..."):
        try:
            jobs = list_jobs(limit=50)

            # 完了ジョブのみフィルタ
            completed_jobs = [job for job in jobs if job.get("status") == "completed"]

            if not completed_jobs:
                st.warning("⚠️ 完了したジョブがありません。OCR処理を実行してから要約を生成してください。")
                st.page_link("pages/1_📤_Upload.py", label="📤 手動OCRアップロード", icon="📤")
                st.page_link("pages/2_🤖_Auto_Capture.py", label="🤖 自動キャプチャ", icon="🤖")
                return

            st.success(f"✅ 完了ジョブ: {len(completed_jobs)}件")

            # ジョブ選択
            st.markdown("### 📚 ジョブ選択")

            selected_job = st.selectbox(
                "要約対象のジョブを選択",
                options=completed_jobs,
                format_func=lambda job: f"{job.get('job_id', '')[:8]}... - {job.get('pages_captured', 0)}ページ - {job.get('created_at', '')[:10]}",
                index=0
            )

            if selected_job:
                job_id = selected_job.get("job_id", "")

                st.markdown("---")

                # モード別の表示
                if "シングルレベル" in summary_mode:
                    render_single_level_summary(job_id)
                else:
                    render_multilevel_summary(job_id)

        except APIError as e:
            st.error(f"❌ APIエラー: {e.message}")
            if e.detail:
                st.error(f"詳細: {e.detail}")
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# シングルレベル要約
# ========================================

def render_single_level_summary(job_id: str):
    """シングルレベル要約UI"""
    st.markdown("### 📝 シングルレベル要約")

    # パラメータ設定
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ⚙️ 基本設定")

        length = st.select_slider(
            "要約の長さ",
            options=["short", "medium", "long"],
            value="medium",
            format_func=lambda x: {"short": "短い (200-300語)", "medium": "中程度 (500-700語)", "long": "長い (1000-1500語)"}[x]
        )

        tone = st.selectbox(
            "文章のトーン",
            options=["professional", "casual", "academic", "storytelling"],
            index=0,
            format_func=lambda x: {
                "professional": "プロフェッショナル",
                "casual": "カジュアル",
                "academic": "学術的",
                "storytelling": "ストーリーテリング"
            }[x]
        )

    with col2:
        st.markdown("#### 🔍 詳細設定")

        granularity = st.selectbox(
            "詳細度",
            options=["executive", "high_level", "comprehensive"],
            index=1,
            format_func=lambda x: {
                "executive": "エグゼクティブ (超要約)",
                "high_level": "高レベル (バランス)",
                "comprehensive": "包括的 (詳細)"
            }[x]
        )

        format_type = st.selectbox(
            "出力形式",
            options=["plain_text", "bullet_points", "structured"],
            index=0,
            format_func=lambda x: {
                "plain_text": "プレーンテキスト",
                "bullet_points": "箇条書き",
                "structured": "構造化"
            }[x]
        )

    st.markdown("---")

    # 要約生成ボタン
    generate_button = st.button(
        "🚀 要約生成",
        type="primary",
        use_container_width=True
    )

    if generate_button:
        with st.spinner("🧠 AIが要約を生成中... しばらくお待ちください（最大3分）"):
            try:
                result = create_summary(
                    job_id=job_id,
                    length=length,
                    tone=tone,
                    granularity=granularity,
                    format_type=format_type,
                    language="ja"
                )

                st.success("✅ 要約生成が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📄 生成された要約")

                # 統計情報
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("要約ID", result.get("summary_id", "N/A"))
                with col2:
                    tokens = result.get("token_usage", {})
                    total_tokens = tokens.get("total", 0)
                    st.metric("トークン使用量", f"{total_tokens:,}")
                with col3:
                    st.metric("チャンク数", result.get("chunks", 0))
                with col4:
                    is_mock = result.get("is_mock", False)
                    st.metric("モード", "モック" if is_mock else "本番")

                st.markdown("---")

                # 要約テキスト表示
                summary_text = result.get("summary_text", "")

                st.markdown("#### 📝 要約内容")
                st.text_area(
                    "要約テキスト",
                    value=summary_text,
                    height=400,
                    disabled=True,
                    label_visibility="collapsed"
                )

                # ダウンロードボタン
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                book_title = result.get("book_title", "summary")

                st.download_button(
                    label="📥 要約をダウンロード",
                    data=summary_text,
                    file_name=f"{book_title}_summary_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# マルチレベル要約
# ========================================

def render_multilevel_summary(job_id: str):
    """マルチレベル要約UI（3段階）"""
    st.markdown("### 📚 マルチレベル要約（3段階）")

    st.info(
        "📊 **3段階の要約を一度に生成**\n\n"
        "- **Level 1 (エグゼクティブ)**: 超要約 - 最も重要なポイントのみ\n"
        "- **Level 2 (標準)**: バランス型 - 主要なトピックをカバー\n"
        "- **Level 3 (詳細)**: 包括的 - すべての重要な情報を含む"
    )

    # パラメータ設定
    col1, col2 = st.columns(2)

    with col1:
        tone = st.selectbox(
            "文章のトーン",
            options=["professional", "casual", "academic", "storytelling"],
            index=0,
            format_func=lambda x: {
                "professional": "プロフェッショナル",
                "casual": "カジュアル",
                "academic": "学術的",
                "storytelling": "ストーリーテリング"
            }[x],
            key="multilevel_tone"
        )

    with col2:
        format_type = st.selectbox(
            "出力形式",
            options=["plain_text", "bullet_points", "structured"],
            index=0,
            format_func=lambda x: {
                "plain_text": "プレーンテキスト",
                "bullet_points": "箇条書き",
                "structured": "構造化"
            }[x],
            key="multilevel_format"
        )

    st.markdown("---")

    # 要約生成ボタン
    generate_button = st.button(
        "🚀 マルチレベル要約生成",
        type="primary",
        use_container_width=True,
        key="multilevel_generate"
    )

    if generate_button:
        with st.spinner("🧠 AIが3段階の要約を生成中... しばらくお待ちください（最大5分）"):
            try:
                result = create_multilevel_summary(
                    job_id=job_id,
                    tone=tone,
                    format_type=format_type,
                    language="ja"
                )

                st.success("✅ マルチレベル要約生成が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📊 生成された3段階の要約")

                # 統計情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    tokens = result.get("total_tokens", {})
                    total_tokens = tokens.get("total", 0)
                    st.metric("総トークン使用量", f"{total_tokens:,}")
                with col2:
                    summary_ids = result.get("summary_ids", [])
                    st.metric("生成要約数", len(summary_ids))
                with col3:
                    is_mock = result.get("is_mock", False)
                    st.metric("モード", "モック" if is_mock else "本番")

                st.markdown("---")

                # Level 1 - エグゼクティブ
                level_1 = result.get("level_1", {})
                with st.container():
                    st.markdown("#### 🟢 Level 1: エグゼクティブ要約")
                    st.markdown(
                        f"**トークン使用量**: {level_1.get('tokens', {}).get('total', 0):,}"
                    )

                    st.text_area(
                        "Level 1",
                        value=level_1.get("summary", ""),
                        height=200,
                        disabled=True,
                        label_visibility="collapsed",
                        key="level_1_text"
                    )

                st.markdown("---")

                # Level 2 - 標準
                level_2 = result.get("level_2", {})
                with st.container():
                    st.markdown("#### 🟡 Level 2: 標準要約")
                    st.markdown(
                        f"**トークン使用量**: {level_2.get('tokens', {}).get('total', 0):,}"
                    )

                    st.text_area(
                        "Level 2",
                        value=level_2.get("summary", ""),
                        height=300,
                        disabled=True,
                        label_visibility="collapsed",
                        key="level_2_text"
                    )

                st.markdown("---")

                # Level 3 - 詳細
                level_3 = result.get("level_3", {})
                with st.container():
                    st.markdown("#### 🔵 Level 3: 詳細要約")
                    st.markdown(
                        f"**トークン使用量**: {level_3.get('tokens', {}).get('total', 0):,}"
                    )

                    st.text_area(
                        "Level 3",
                        value=level_3.get("summary", ""),
                        height=400,
                        disabled=True,
                        label_visibility="collapsed",
                        key="level_3_text"
                    )

                st.markdown("---")

                # 統合ダウンロードボタン
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                book_title = result.get("book_title", "summary")

                combined_text = f"""
書籍タイトル: {book_title}
生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

================================
Level 1: エグゼクティブ要約
================================

{level_1.get("summary", "")}

================================
Level 2: 標準要約
================================

{level_2.get("summary", "")}

================================
Level 3: 詳細要約
================================

{level_3.get("summary", "")}
"""

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.download_button(
                        label="📥 Level 1 をダウンロード",
                        data=level_1.get("summary", ""),
                        file_name=f"{book_title}_level1_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                with col2:
                    st.download_button(
                        label="📥 Level 2 をダウンロード",
                        data=level_2.get("summary", ""),
                        file_name=f"{book_title}_level2_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                with col3:
                    st.download_button(
                        label="📥 Level 3 をダウンロード",
                        data=level_3.get("summary", ""),
                        file_name=f"{book_title}_level3_{timestamp}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                st.download_button(
                    label="📥 全レベルを統合ダウンロード",
                    data=combined_text,
                    file_name=f"{book_title}_multilevel_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    type="primary"
                )

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")


if __name__ == "__main__":
    main()
