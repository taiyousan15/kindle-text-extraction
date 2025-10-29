"""
Kindle OCR - Upload Page
手動OCRアップロードページ

画像ファイルをアップロードしてOCR処理を実行
"""
import streamlit as st
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from app.ui.utils.api_client import upload_image, APIError

# ページ設定
st.set_page_config(
    page_title="Kindle OCR - Upload",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .upload-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        margin-top: 1rem;
    }
    .confidence-high {
        color: #4caf50;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ff9800;
        font-weight: bold;
    }
    .confidence-low {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def get_confidence_class(confidence: float) -> str:
    """信頼度に応じたCSSクラスを返す"""
    if confidence >= 0.8:
        return "confidence-high"
    elif confidence >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"


def validate_file(uploaded_file):
    """ファイルのバリデーション"""
    if uploaded_file is None:
        return False, "ファイルが選択されていません"

    # ファイルサイズチェック (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    if uploaded_file.size > MAX_FILE_SIZE:
        return False, f"ファイルサイズが大きすぎます (上限: {MAX_FILE_SIZE / 1024 / 1024}MB)"

    # 拡張子チェック
    allowed_extensions = [".png", ".jpg", ".jpeg"]
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return False, f"許可されていないファイル形式です。対応形式: {', '.join(allowed_extensions)}"

    return True, None


def main():
    # ヘッダー
    st.markdown('<div class="upload-header">📤 手動OCRアップロード</div>', unsafe_allow_html=True)

    st.info(
        "📸 **手動OCR**: Kindle書籍のスクリーンショット画像をアップロードして、テキストを抽出します。\n\n"
        "対応形式: PNG, JPG, JPEG | 最大ファイルサイズ: 10MB"
    )

    st.markdown("---")

    # サイドバー
    with st.sidebar:
        st.title("📤 Upload")
        st.markdown("---")
        st.markdown("### アップロード手順")
        st.markdown(
            "1. 画像ファイルを選択\n"
            "2. 書籍タイトルを入力\n"
            "3. ページ番号を入力\n"
            "4. アップロードボタンをクリック"
        )
        st.markdown("---")
        st.markdown("### サポート")
        st.markdown("📄 対応形式: PNG, JPG, JPEG")
        st.markdown("📏 最大サイズ: 10MB")
        st.markdown("🌐 言語: 日本語 + 英語")

    # メインコンテンツ - 2カラムレイアウト
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📁 ファイルアップロード")

        # ファイルアップローダー
        uploaded_file = st.file_uploader(
            "画像ファイルを選択してください",
            type=["png", "jpg", "jpeg"],
            help="Kindleのスクリーンショット画像をアップロードしてください"
        )

        # プレビュー表示
        if uploaded_file is not None:
            st.image(uploaded_file, caption="アップロードされた画像", use_container_width=True)

            # ファイル情報
            st.markdown(f"**ファイル名:** {uploaded_file.name}")
            st.markdown(f"**ファイルサイズ:** {uploaded_file.size / 1024:.2f} KB")

    with col2:
        st.markdown("### ⚙️ OCR設定")

        # 書籍タイトル入力
        book_title = st.text_input(
            "書籍タイトル",
            value="",
            placeholder="例: プロンプトエンジニアリング入門",
            help="OCR処理する書籍のタイトルを入力してください"
        )

        # ページ番号入力
        page_num = st.number_input(
            "ページ番号",
            min_value=1,
            max_value=10000,
            value=1,
            step=1,
            help="スクリーンショットのページ番号を入力してください"
        )

        st.markdown("---")

        # アップロードボタン
        upload_button = st.button(
            "🚀 アップロード & OCR実行",
            type="primary",
            use_container_width=True,
            disabled=(uploaded_file is None or not book_title.strip())
        )

        if uploaded_file is None:
            st.warning("⚠️ 画像ファイルを選択してください")
        elif not book_title.strip():
            st.warning("⚠️ 書籍タイトルを入力してください")

    # アップロード処理
    if upload_button:
        # ファイルバリデーション
        is_valid, error_message = validate_file(uploaded_file)
        if not is_valid:
            st.error(f"❌ {error_message}")
            return

        # 進捗表示
        with st.spinner("🔄 OCR処理中... しばらくお待ちください"):
            try:
                # APIコール
                file_data = uploaded_file.read()
                result = upload_image(
                    file_data=file_data,
                    filename=uploaded_file.name,
                    book_title=book_title.strip(),
                    page_num=page_num
                )

                # 成功メッセージ
                st.success("✅ OCR処理が完了しました！")

                # 結果表示
                st.markdown("---")
                st.markdown("### 📄 OCR結果")

                # 結果ボックス
                job_id = result.get("job_id", "N/A")
                confidence = result.get("confidence", 0.0)
                extracted_text = result.get("text", "")

                # 基本情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ジョブID", job_id[:8] + "...")
                with col2:
                    confidence_class = get_confidence_class(confidence)
                    st.markdown(
                        f'<div>信頼度スコア<br><span class="{confidence_class}" style="font-size: 1.5rem;">{confidence:.2%}</span></div>',
                        unsafe_allow_html=True
                    )
                with col3:
                    st.metric("テキスト長", f"{len(extracted_text)} 文字")

                st.markdown("---")

                # 抽出テキスト表示
                st.markdown("#### 📝 抽出されたテキスト")

                if extracted_text:
                    with st.expander("テキストを表示", expanded=True):
                        st.text_area(
                            "OCR結果",
                            value=extracted_text,
                            height=300,
                            disabled=True,
                            label_visibility="collapsed"
                        )

                        # コピーボタン用（クリップボードにコピー）
                        st.download_button(
                            label="📥 テキストをダウンロード",
                            data=extracted_text,
                            file_name=f"{book_title}_page{page_num}.txt",
                            mime="text/plain"
                        )
                else:
                    st.warning("⚠️ テキストが抽出できませんでした。画像の品質を確認してください。")

                # 信頼度に応じたアドバイス
                if confidence < 0.6:
                    st.warning(
                        "⚠️ **信頼度が低いです。** 以下を確認してください:\n"
                        "- 画像が鮮明であるか\n"
                        "- 文字が読みやすいか\n"
                        "- 画像が傾いていないか"
                    )
                elif confidence < 0.8:
                    st.info("💡 信頼度は中程度です。必要に応じてテキストを手動で修正してください。")

                # 次のアクション
                st.markdown("---")
                st.markdown("### 🎯 次のアクション")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📤 別の画像をアップロード", use_container_width=True):
                        st.rerun()
                with col2:
                    st.page_link("pages/3_📊_Jobs.py", label="📊 ジョブ一覧を確認", use_container_width=True)

            except APIError as e:
                st.error(f"❌ APIエラー: {e.message}")
                if e.detail:
                    st.error(f"詳細: {e.detail}")
                st.info("💡 FastAPIサーバーが起動しているか確認してください")
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {str(e)}")

    # 使い方のヒント
    st.markdown("---")
    st.markdown("### 💡 ヒント")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            "**📸 高品質な画像**\n\n"
            "- 鮮明で読みやすい画像を使用\n"
            "- 十分な解像度を確保\n"
            "- 影や反射を避ける"
        )
    with col2:
        st.markdown(
            "**📝 正確な情報**\n\n"
            "- 正しい書籍タイトルを入力\n"
            "- ページ番号を確認\n"
            "- 一貫した命名規則を使用"
        )
    with col3:
        st.markdown(
            "**🤖 自動キャプチャ**\n\n"
            "- 複数ページを一括処理したい場合\n"
            "- 「Auto Capture」機能を使用\n"
            "- 時間を大幅に節約"
        )


if __name__ == "__main__":
    main()
