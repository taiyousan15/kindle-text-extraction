"""
Business Knowledge Page - ビジネスナレッジRAGシステム

ビジネス文書をアップロードして専門知識ベースを構築し、
高度なRAG検索と質問応答を実行するページ
"""
import streamlit as st
import sys
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import APIError, API_BASE_URL
import logging

logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(
    page_title="Business Knowledge - RAG System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .business-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .result-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #dee2e6;
        margin-top: 1rem;
    }
    .source-box {
        background-color: #e9ecef;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3498db;
        margin: 0.5rem 0;
    }
    .similarity-high {
        color: #27ae60;
        font-weight: bold;
    }
    .similarity-medium {
        color: #f39c12;
        font-weight: bold;
    }
    .similarity-low {
        color: #e74c3c;
        font-weight: bold;
    }
    .doc-card {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #ddd;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


# ========================================
# API クライアント関数
# ========================================

def upload_business_document(
    file_data: bytes,
    filename: str,
    tags: str = "",
    auto_index: bool = True
) -> Dict[str, Any]:
    """ビジネス文書をアップロード"""
    url = f"{API_BASE_URL}/api/v1/business/upload"

    files = {
        "file": (filename, file_data)
    }

    data = {
        "tags": tags,
        "auto_index": str(auto_index).lower()
    }

    try:
        response = requests.post(url, files=files, data=data, timeout=120)
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
        raise APIError(message=f"アップロードエラー: {str(e)}", detail=str(e))


def query_business_kb(
    query: str,
    top_k: int = 5,
    file_ids: Optional[List[int]] = None,
    tags: Optional[List[str]] = None,
    similarity_threshold: float = 0.0
) -> Dict[str, Any]:
    """ビジネスナレッジベースに質問"""
    url = f"{API_BASE_URL}/api/v1/business/query"

    payload = {
        "query": query,
        "top_k": top_k,
        "similarity_threshold": similarity_threshold
    }

    if file_ids:
        payload["file_ids"] = file_ids
    if tags:
        payload["tags"] = tags

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
        raise APIError(message=f"クエリエラー: {str(e)}", detail=str(e))


def list_business_documents(
    tags: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """ビジネス文書一覧を取得"""
    url = f"{API_BASE_URL}/api/v1/business/documents"

    params = {
        "limit": limit,
        "offset": offset
    }

    if tags:
        params["tags"] = tags

    try:
        response = requests.get(url, params=params, timeout=30)
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
        raise APIError(message=f"取得エラー: {str(e)}", detail=str(e))


def delete_business_document(file_id: int) -> Dict[str, Any]:
    """ビジネス文書を削除"""
    url = f"{API_BASE_URL}/api/v1/business/documents/{file_id}"

    try:
        response = requests.delete(url, timeout=30)
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
        raise APIError(message=f"削除エラー: {str(e)}", detail=str(e))


def get_document_stats(file_id: int) -> Dict[str, Any]:
    """文書統計を取得"""
    url = f"{API_BASE_URL}/api/v1/business/documents/{file_id}/stats"

    try:
        response = requests.get(url, timeout=30)
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
        raise APIError(message=f"統計取得エラー: {str(e)}", detail=str(e))


# ========================================
# ヘルパー関数
# ========================================

def get_similarity_class(similarity: float) -> str:
    """類似度に応じたCSSクラスを返す"""
    if similarity >= 0.8:
        return "similarity-high"
    elif similarity >= 0.6:
        return "similarity-medium"
    else:
        return "similarity-low"


def format_file_size(size_bytes: int) -> str:
    """ファイルサイズを読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


# ========================================
# メイン画面
# ========================================

def main():
    # ヘッダー
    st.markdown('<div class="business-header">💼 ビジネスナレッジRAGシステム</div>', unsafe_allow_html=True)

    st.info(
        "📚 **Business Knowledge**: ビジネス文書（PDF, DOCX, TXT, MD）をアップロードして専門知識ベースを構築し、\n"
        "RAG（Retrieval Augmented Generation）を使用して高度な質問応答を実行します。\n\n"
        "対応形式: PDF, DOCX, TXT, Markdown | 自動インデックス化 | セマンティック検索"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("💼 Business Knowledge")
        st.markdown("---")

        page_mode = st.radio(
            "機能を選択",
            ["📤 文書アップロード", "🔍 ナレッジ検索", "📚 文書管理"],
            index=0
        )

        st.markdown("---")
        st.markdown("### 💡 機能説明")

        if page_mode == "📤 文書アップロード":
            st.markdown(
                "**文書アップロード**\n\n"
                "1. ファイルを選択\n"
                "2. タグを追加（オプション）\n"
                "3. アップロードボタンをクリック\n"
                "4. 自動的にベクトル化・インデックス化"
            )
        elif page_mode == "🔍 ナレッジ検索":
            st.markdown(
                "**ナレッジ検索**\n\n"
                "1. 質問を入力\n"
                "2. 検索パラメータを調整\n"
                "3. 検索実行\n"
                "4. 関連文書と回答を確認"
            )
        else:
            st.markdown(
                "**文書管理**\n\n"
                "1. アップロード済み文書一覧\n"
                "2. 文書の詳細情報表示\n"
                "3. 文書の削除\n"
                "4. 統計情報の確認"
            )

        st.markdown("---")
        st.markdown("### 📊 システム情報")
        st.markdown("🌐 RAGエンジン: ベクトル検索")
        st.markdown("🤖 Embedding: OpenAI/ローカル")
        st.markdown("💾 ストレージ: PostgreSQL + pgvector")

    # ========================================
    # ページモード別の表示
    # ========================================

    if page_mode == "📤 文書アップロード":
        render_upload_page()
    elif page_mode == "🔍 ナレッジ検索":
        render_query_page()
    else:
        render_management_page()


# ========================================
# 文書アップロードページ
# ========================================

def render_upload_page():
    st.markdown("### 📤 ビジネス文書アップロード")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 📁 ファイル選択")

        uploaded_file = st.file_uploader(
            "ビジネス文書を選択してください",
            type=["pdf", "docx", "txt", "md"],
            help="PDF, Word, テキスト, Markdownファイルに対応しています"
        )

        if uploaded_file is not None:
            st.success(f"✅ ファイル選択: {uploaded_file.name}")
            st.markdown(f"**ファイルサイズ:** {format_file_size(uploaded_file.size)}")
            st.markdown(f"**ファイル形式:** {uploaded_file.type}")

    with col2:
        st.markdown("#### ⚙️ インデックス設定")

        tags_input = st.text_input(
            "タグ（カンマ区切り）",
            value="",
            placeholder="例: 契約書, 法務, 2024年度",
            help="文書を分類するためのタグを追加します"
        )

        auto_index = st.checkbox(
            "自動インデックス化",
            value=True,
            help="アップロード時に自動的にベクトル化・インデックス化します"
        )

        st.markdown("---")

        upload_button = st.button(
            "🚀 アップロード & インデックス化",
            type="primary",
            use_container_width=True,
            disabled=(uploaded_file is None)
        )

    # アップロード処理
    if upload_button and uploaded_file is not None:
        with st.spinner("🔄 文書をアップロード中... ベクトル化とインデックス化を実行しています..."):
            try:
                file_data = uploaded_file.read()

                result = upload_business_document(
                    file_data=file_data,
                    filename=uploaded_file.name,
                    tags=tags_input,
                    auto_index=auto_index
                )

                st.success("✅ アップロードとインデックス化が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📊 処理結果")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("ファイルID", result.get("file_id", "N/A"))
                with col2:
                    st.metric("作成チャンク数", result.get("chunks_created", 0))
                with col3:
                    st.metric("インデックス数", result.get("indexed_count", 0))
                with col4:
                    status = result.get("status", "unknown")
                    st.metric("ステータス", status)

                if result.get("message"):
                    st.info(f"ℹ️ {result['message']}")

                # 次のアクション
                st.markdown("---")
                st.markdown("### 🎯 次のアクション")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 ナレッジ検索を試す", use_container_width=True):
                        st.session_state["page_mode"] = "🔍 ナレッジ検索"
                        st.rerun()
                with col2:
                    if st.button("📚 文書管理を確認", use_container_width=True):
                        st.session_state["page_mode"] = "📚 文書管理"
                        st.rerun()

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# ナレッジ検索ページ
# ========================================

def render_query_page():
    st.markdown("### 🔍 ビジネスナレッジ検索")

    # 検索クエリ入力
    query = st.text_area(
        "質問を入力してください",
        value="",
        height=100,
        placeholder="例: 契約書の重要な条項について教えてください",
        help="ナレッジベースに対する質問を入力します"
    )

    # 検索パラメータ
    col1, col2, col3 = st.columns(3)

    with col1:
        top_k = st.slider(
            "検索結果数",
            min_value=1,
            max_value=20,
            value=5,
            help="返却する関連文書の数"
        )

    with col2:
        similarity_threshold = st.slider(
            "類似度閾値",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.1,
            help="この値未満の類似度の結果は除外されます"
        )

    with col3:
        filter_tags = st.text_input(
            "タグフィルタ（カンマ区切り）",
            value="",
            placeholder="例: 契約書, 法務",
            help="特定のタグでフィルタリングします"
        )

    # 検索ボタン
    search_button = st.button(
        "🔍 検索実行",
        type="primary",
        use_container_width=True,
        disabled=(not query.strip())
    )

    if not query.strip():
        st.warning("⚠️ 質問を入力してください")

    # 検索実行
    if search_button and query.strip():
        with st.spinner("🔍 ナレッジベースを検索中..."):
            try:
                # タグのパース
                tags_list = None
                if filter_tags.strip():
                    tags_list = [t.strip() for t in filter_tags.split(",") if t.strip()]

                result = query_business_kb(
                    query=query,
                    top_k=top_k,
                    tags=tags_list,
                    similarity_threshold=similarity_threshold
                )

                st.success("✅ 検索が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📊 検索結果")

                # 統計情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("マッチ文書数", result.get("results_count", 0))
                with col2:
                    st.metric("検索時間", f"{result.get('search_time_ms', 0):.0f} ms")
                with col3:
                    query_text = result.get("query", "")
                    st.metric("クエリ長", f"{len(query_text)} 文字")

                # 検索結果の詳細
                results = result.get("results", [])

                if results:
                    st.markdown("---")
                    st.markdown("### 📚 関連文書")

                    for i, doc_result in enumerate(results, 1):
                        similarity = doc_result.get("similarity", 0.0)
                        similarity_class = get_similarity_class(similarity)

                        with st.expander(
                            f"📄 結果 {i} - {doc_result.get('filename', 'Unknown')} "
                            f"(類似度: {similarity:.2%})",
                            expanded=(i == 1)
                        ):
                            # メタデータ
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**ファイルID:** {doc_result.get('file_id', 'N/A')}")
                            with col2:
                                st.markdown(f"**チャンクID:** {doc_result.get('chunk_id', 'N/A')}")
                            with col3:
                                st.markdown(
                                    f'**類似度:** <span class="{similarity_class}">{similarity:.2%}</span>',
                                    unsafe_allow_html=True
                                )

                            # 文書内容
                            st.markdown("#### 📝 関連テキスト")
                            content = doc_result.get("content", "")
                            st.text_area(
                                "内容",
                                value=content,
                                height=150,
                                disabled=True,
                                label_visibility="collapsed"
                            )

                            # タグ表示
                            tags = doc_result.get("tags", [])
                            if tags:
                                st.markdown("**🏷️ タグ:** " + ", ".join(f"`{tag}`" for tag in tags))

                    # コンテキストのダウンロード
                    st.markdown("---")
                    combined_context = result.get("combined_context", "")
                    if combined_context:
                        st.download_button(
                            label="📥 検索コンテキストをダウンロード",
                            data=combined_context,
                            file_name=f"business_knowledge_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )
                else:
                    st.warning("⚠️ 検索結果が見つかりませんでした。類似度閾値を下げるか、クエリを変更してください。")

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")


# ========================================
# 文書管理ページ
# ========================================

def render_management_page():
    st.markdown("### 📚 ビジネス文書管理")

    # フィルタ設定
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_tags = st.text_input(
            "タグフィルタ",
            value="",
            placeholder="例: 契約書, 法務",
            help="特定のタグで文書をフィルタリングします"
        )

    with col2:
        limit = st.number_input(
            "表示件数",
            min_value=10,
            max_value=500,
            value=100,
            step=10
        )

    with col3:
        if st.button("🔄 更新", use_container_width=True):
            st.rerun()

    # 文書一覧を取得
    with st.spinner("📚 文書一覧を読み込み中..."):
        try:
            result = list_business_documents(
                tags=filter_tags if filter_tags.strip() else None,
                limit=limit,
                offset=0
            )

            documents = result.get("documents", [])
            total = result.get("total", 0)
            count = result.get("count", 0)

            # 統計表示
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総文書数", total)
            with col2:
                st.metric("表示中", count)
            with col3:
                avg_chunks = result.get("average_chunks_per_document", 0)
                st.metric("平均チャンク数", f"{avg_chunks:.1f}")

            if documents:
                st.markdown("---")
                st.markdown("### 📄 文書一覧")

                for doc in documents:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                        with col1:
                            st.markdown(f"**📄 {doc.get('filename', 'Unknown')}**")
                            tags = doc.get("tags", [])
                            if tags:
                                st.markdown("🏷️ " + ", ".join(f"`{tag}`" for tag in tags))

                        with col2:
                            st.markdown(f"**ID:** {doc.get('file_id', 'N/A')}")
                            st.markdown(f"**サイズ:** {format_file_size(doc.get('file_size', 0))}")

                        with col3:
                            st.markdown(f"**チャンク数:** {doc.get('chunk_count', 0)}")
                            created_at = doc.get('created_at', '')
                            if created_at:
                                st.markdown(f"**作成日:** {created_at[:10]}")

                        with col4:
                            file_id = doc.get('file_id')

                            if st.button("📊", key=f"stats_{file_id}", help="統計表示"):
                                show_document_stats(file_id)

                            if st.button("🗑️", key=f"delete_{file_id}", help="削除", type="secondary"):
                                if st.session_state.get(f"confirm_delete_{file_id}"):
                                    try:
                                        delete_business_document(file_id)
                                        st.success(f"✅ 文書 {file_id} を削除しました")
                                        st.rerun()
                                    except APIError as e:
                                        st.error(f"❌ 削除エラー: {e.message}")
                                else:
                                    st.session_state[f"confirm_delete_{file_id}"] = True
                                    st.warning("⚠️ もう一度クリックして削除を確認してください")

                        st.markdown("---")
            else:
                st.info("📭 文書がまだアップロードされていません。「文書アップロード」から追加してください。")

        except APIError as e:
            st.error(f"❌ APIエラー: {e.message}")
            if e.detail:
                st.error(f"詳細: {e.detail}")
        except Exception as e:
            st.error(f"❌ エラーが発生しました: {str(e)}")


def show_document_stats(file_id: int):
    """文書統計を表示"""
    try:
        stats = get_document_stats(file_id)

        st.markdown("#### 📊 文書統計")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("チャンク数", stats.get("chunk_count", 0))
        with col2:
            avg_quality = stats.get("average_quality_score", 0.0)
            st.metric("平均品質スコア", f"{avg_quality:.2%}")
        with col3:
            st.metric("総文字数", stats.get("total_characters", 0))

        st.markdown("---")

    except APIError as e:
        st.error(f"❌ 統計取得エラー: {e.message}")
    except Exception as e:
        st.error(f"❌ エラー: {str(e)}")


if __name__ == "__main__":
    main()
