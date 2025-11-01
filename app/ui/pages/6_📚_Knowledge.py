"""
Knowledge Page - ナレッジ化

OCR結果から構造化されたナレッジ（知識）を抽出し、
YAML/JSON形式でエクスポートするページ
"""
import streamlit as st
import sys
import os
import requests
import json
import yaml
from typing import Optional, Dict, Any, List
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import list_jobs, APIError, API_BASE_URL
import logging

logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="Knowledge - Structured Knowledge Extraction",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .knowledge-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #e67e22;
        margin-bottom: 1rem;
    }
    .knowledge-box {
        background-color: #fff8e1;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #ffd54f;
        margin: 1rem 0;
    }
    .entity-badge {
        display: inline-block;
        background-color: #4caf50;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        margin: 0.2rem;
        font-size: 0.9rem;
    }
    .relationship-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ========================================
# API クライアント関数
# ========================================

def extract_knowledge(
    job_id: Optional[str] = None,
    text: Optional[str] = None,
    book_title: Optional[str] = None,
    extract_type: str = "concepts_and_insights",
    language: str = "ja"
) -> Dict[str, Any]:
    """ナレッジ抽出"""
    url = f"{API_BASE_URL}/api/v1/knowledge/extract"

    payload = {
        "extract_type": extract_type,
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
        raise APIError(message=f"ナレッジ抽出エラー: {str(e)}", detail=str(e))


def export_knowledge(
    knowledge_id: int,
    export_format: str = "yaml"
) -> Dict[str, Any]:
    """ナレッジをエクスポート"""
    url = f"{API_BASE_URL}/api/v1/knowledge/{knowledge_id}/export"

    payload = {
        "format": export_format
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
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
        raise APIError(message=f"エクスポートエラー: {str(e)}", detail=str(e))


def extract_entities(
    job_id: Optional[str] = None,
    text: Optional[str] = None,
    entity_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """エンティティ抽出"""
    url = f"{API_BASE_URL}/api/v1/knowledge/extract-entities"

    payload = {}

    if job_id:
        payload["job_id"] = job_id
    elif text:
        payload["text"] = text
    else:
        raise ValueError("Either job_id or text must be provided")

    if entity_types:
        payload["entity_types"] = entity_types

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
        raise APIError(message=f"エンティティ抽出エラー: {str(e)}", detail=str(e))


# ========================================
# メイン画面
# ========================================

def main():
    # ヘッダー
    st.markdown('<div class="knowledge-header">📚 ナレッジ化システム</div>', unsafe_allow_html=True)

    st.info(
        "🔍 **Knowledge Extraction**: OCR結果から構造化されたナレッジ（知識）を抽出し、YAML/JSON形式でエクスポートします。\n\n"
        "**抽出タイプ**:\n"
        "- **コンセプト・洞察**: 主要なコンセプトと洞察を抽出\n"
        "- **エンティティ**: 人物、組織、場所などの固有表現を抽出\n"
        "- **関係性**: エンティティ間の関係性を抽出"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("📚 Knowledge")
        st.markdown("---")

        extraction_mode = st.radio(
            "抽出モード",
            ["🔍 コンセプト・洞察", "🏷️ エンティティ抽出", "🔗 関係性抽出"],
            index=0
        )

        st.markdown("---")
        st.markdown("### 💡 機能説明")

        if "コンセプト" in extraction_mode:
            st.markdown(
                "**コンセプト・洞察抽出**\n\n"
                "1. ジョブを選択\n"
                "2. 抽出タイプを選択\n"
                "3. ナレッジ抽出実行\n"
                "4. YAML/JSON形式でエクスポート"
            )
        elif "エンティティ" in extraction_mode:
            st.markdown(
                "**エンティティ抽出**\n\n"
                "1. ジョブを選択\n"
                "2. エンティティタイプを選択\n"
                "3. 抽出実行\n"
                "4. エンティティ一覧を確認"
            )
        else:
            st.markdown(
                "**関係性抽出**\n\n"
                "1. ジョブを選択\n"
                "2. 関係性抽出実行\n"
                "3. エンティティ間の関係を確認\n"
                "4. ナレッジグラフを構築"
            )

        st.markdown("---")
        st.markdown("### 📄 エクスポート形式")
        st.markdown("📋 **YAML**: 人間が読みやすい")
        st.markdown("🔧 **JSON**: プログラムで処理しやすい")

    # ジョブ一覧を取得
    with st.spinner("📚 ジョブ一覧を読み込み中..."):
        try:
            jobs = list_jobs(limit=50)

            # 完了ジョブのみフィルタ
            completed_jobs = [job for job in jobs if job.get("status") == "completed"]

            if not completed_jobs:
                st.warning("⚠️ 完了したジョブがありません。OCR処理を実行してからナレッジ化を実行してください。")
                st.page_link("pages/1_📤_Upload.py", label="📤 手動OCRアップロード", icon="📤")
                st.page_link("pages/2_🤖_Auto_Capture.py", label="🤖 自動キャプチャ", icon="🤖")
                return

            st.success(f"✅ 完了ジョブ: {len(completed_jobs)}件")

            # ジョブ選択
            st.markdown("### 📚 ジョブ選択")

            selected_job = st.selectbox(
                "ナレッジ化対象のジョブを選択",
                options=completed_jobs,
                format_func=lambda job: f"{job.get('job_id', '')[:8]}... - {job.get('pages_captured', 0)}ページ - {job.get('created_at', '')[:10]}",
                index=0
            )

            if selected_job:
                job_id = selected_job.get("job_id", "")

                st.markdown("---")

                # モード別の表示
                if "コンセプト" in extraction_mode:
                    render_concept_extraction(job_id)
                elif "エンティティ" in extraction_mode:
                    render_entity_extraction(job_id)
                else:
                    render_relationship_extraction(job_id)

        except APIError as e:
            st.error(f"❌ APIエラー: {e.message}")
            if e.detail:
                st.error(f"詳細: {e.detail}")
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# コンセプト・洞察抽出
# ========================================

def render_concept_extraction(job_id: str):
    """コンセプト・洞察抽出UI"""
    st.markdown("### 🔍 コンセプト・洞察抽出")

    # 抽出タイプ選択
    extract_type = st.selectbox(
        "抽出タイプ",
        options=[
            "concepts_and_insights",
            "key_topics",
            "actionable_items",
            "comprehensive"
        ],
        index=0,
        format_func=lambda x: {
            "concepts_and_insights": "コンセプト・洞察",
            "key_topics": "主要トピック",
            "actionable_items": "アクションアイテム",
            "comprehensive": "包括的"
        }[x]
    )

    # 抽出ボタン
    extract_button = st.button(
        "🚀 ナレッジ抽出",
        type="primary",
        use_container_width=True
    )

    if extract_button:
        with st.spinner("🔍 AIがナレッジを抽出中... しばらくお待ちください（最大5分）"):
            try:
                result = extract_knowledge(
                    job_id=job_id,
                    extract_type=extract_type,
                    language="ja"
                )

                st.success("✅ ナレッジ抽出が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📊 抽出されたナレッジ")

                # 統計情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ナレッジID", result.get("knowledge_id", "N/A"))
                with col2:
                    tokens = result.get("tokens", {})
                    total_tokens = tokens.get("total", 0)
                    st.metric("トークン使用量", f"{total_tokens:,}")
                with col3:
                    is_mock = result.get("is_mock", False)
                    st.metric("モード", "モック" if is_mock else "本番")

                st.markdown("---")

                # ナレッジ内容表示
                knowledge_json = result.get("knowledge_json", {})

                st.markdown("#### 📋 抽出されたナレッジ")

                # JSON形式で表示
                st.json(knowledge_json)

                # エクスポート機能
                st.markdown("---")
                st.markdown("### 💾 エクスポート")

                col1, col2 = st.columns(2)

                with col1:
                    export_format = st.radio(
                        "エクスポート形式",
                        ["yaml", "json"],
                        format_func=lambda x: {"yaml": "YAML", "json": "JSON"}[x]
                    )

                with col2:
                    st.markdown("#### ")
                    export_button = st.button("📥 エクスポート", use_container_width=True)

                if export_button:
                    try:
                        export_result = export_knowledge(
                            knowledge_id=result.get("knowledge_id"),
                            export_format=export_format
                        )

                        exported_content = export_result.get("content", "")

                        st.success(f"✅ {export_format.upper()}形式でエクスポート完了！")

                        # プレビュー
                        st.code(exported_content, language=export_format)

                        # ダウンロードボタン
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        book_title = result.get("book_title", "knowledge")

                        st.download_button(
                            label=f"📥 {export_format.upper()}ファイルをダウンロード",
                            data=exported_content,
                            file_name=f"{book_title}_knowledge_{timestamp}.{export_format}",
                            mime=f"application/{export_format}",
                            use_container_width=True
                        )

                    except APIError as e:
                        st.error(f"❌ エクスポートエラー: {e.message}")

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# エンティティ抽出
# ========================================

def render_entity_extraction(job_id: str):
    """エンティティ抽出UI"""
    st.markdown("### 🏷️ エンティティ抽出")

    st.info(
        "📝 **エンティティ**: 人物、組織、場所、日付などの固有表現を抽出します"
    )

    # エンティティタイプ選択
    entity_types = st.multiselect(
        "抽出するエンティティタイプ（空の場合は全タイプ）",
        options=["PERSON", "ORG", "GPE", "DATE", "TIME", "MONEY", "PERCENT", "PRODUCT", "EVENT"],
        default=[],
        format_func=lambda x: {
            "PERSON": "人物",
            "ORG": "組織",
            "GPE": "地政学的実体（国・都市等）",
            "DATE": "日付",
            "TIME": "時間",
            "MONEY": "金額",
            "PERCENT": "パーセント",
            "PRODUCT": "製品",
            "EVENT": "イベント"
        }.get(x, x)
    )

    # 抽出ボタン
    extract_button = st.button(
        "🚀 エンティティ抽出",
        type="primary",
        use_container_width=True,
        key="entity_extract"
    )

    if extract_button:
        with st.spinner("🏷️ AIがエンティティを抽出中... しばらくお待ちください"):
            try:
                result = extract_entities(
                    job_id=job_id,
                    entity_types=entity_types if entity_types else None
                )

                st.success("✅ エンティティ抽出が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📊 抽出されたエンティティ")

                # 統計情報
                entities = result.get("entities", [])
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("総エンティティ数", len(entities))
                with col2:
                    unique_types = len(set(e.get("type", "") for e in entities))
                    st.metric("エンティティタイプ数", unique_types)
                with col3:
                    is_mock = result.get("is_mock", False)
                    st.metric("モード", "モック" if is_mock else "本番")

                # エンティティタイプ別に表示
                entity_by_type = {}
                for entity in entities:
                    entity_type = entity.get("type", "UNKNOWN")
                    if entity_type not in entity_by_type:
                        entity_by_type[entity_type] = []
                    entity_by_type[entity_type].append(entity)

                st.markdown("---")

                for entity_type, entity_list in entity_by_type.items():
                    with st.expander(f"🏷️ {entity_type} ({len(entity_list)}件)", expanded=True):
                        for entity in entity_list:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**{entity.get('text', '')}**")
                            with col2:
                                st.markdown(f"信頼度: {entity.get('confidence', 0.0):.2%}")

                # JSON形式でダウンロード
                st.markdown("---")
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                book_title = result.get("book_title", "entities")

                st.download_button(
                    label="📥 エンティティリストをダウンロード（JSON）",
                    data=json.dumps(entities, ensure_ascii=False, indent=2),
                    file_name=f"{book_title}_entities_{timestamp}.json",
                    mime="application/json",
                    use_container_width=True
                )

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# 関係性抽出
# ========================================

def render_relationship_extraction(job_id: str):
    """関係性抽出UI"""
    st.markdown("### 🔗 関係性抽出")

    st.info(
        "🔗 **関係性抽出**: エンティティ間の関係性を抽出し、ナレッジグラフを構築します"
    )

    st.warning("⚠️ この機能は現在開発中です。エンティティ抽出を先に実行してください。")

    # プレースホルダー機能
    if st.button("🚀 関係性抽出（準備中）", type="primary", use_container_width=True, disabled=True):
        pass


if __name__ == "__main__":
    main()
