"""
Error Prompt Generator - エラー解決プロンプト自動生成システム

機能:
- エラー情報から最適なプロンプトを生成
- エラー解決プロンプト集を参照
- Claude APIへの送信用プロンプト構築
"""
import re
from typing import Dict, List, Optional
from pathlib import Path


class ErrorPromptGenerator:
    """
    エラー解決プロンプト自動生成クラス

    「Kindle文字起こしツール エラー解決プロンプト集.md」の内容を基に、
    エラー情報から最適な解決プロンプトを自動生成します。
    """

    def __init__(self, prompt_collection_path: Optional[str] = None):
        """
        Args:
            prompt_collection_path: プロンプト集のパス（省略可）
        """
        if prompt_collection_path is None:
            # デフォルトパス
            prompt_collection_path = str(Path(__file__).parent.parent.parent /
                                        "Kindle文字起こしツール エラー解決プロンプト集.md")

        self.prompt_collection_path = prompt_collection_path
        self.prompts = self._load_prompt_collection()

    def _load_prompt_collection(self) -> Dict[str, Dict]:
        """
        プロンプト集をロードして辞書形式で保存

        Returns:
            カテゴリ別のプロンプト辞書
        """
        prompts = {
            "login": {
                "bot_detection": self._get_login_bot_detection_prompt,
                "2fa": self._get_login_2fa_prompt,
            },
            "page_turn": {
                "stuck": self._get_page_turn_stuck_prompt,
                "book_specific": self._get_page_turn_book_specific_prompt,
            },
            "ocr": {
                "low_accuracy": self._get_ocr_low_accuracy_prompt,
                "header_footer": self._get_ocr_header_footer_prompt,
            },
            "text_generation": {
                "low_quality": self._get_text_gen_low_quality_prompt,
                "rag_irrelevant": self._get_text_gen_rag_irrelevant_prompt,
            },
            "infrastructure": {
                "crash": self._get_infra_crash_prompt,
                "memory_leak": self._get_infra_memory_leak_prompt,
            }
        }
        return prompts

    def generate_prompt(self, error_info: Dict) -> str:
        """
        エラー情報から最適な解決プロンプトを生成

        Args:
            error_info: エラー情報の辞書
                {
                    "error_message": str,
                    "timestamp": str,
                    "log": str,
                    "file_path": str,
                    "screenshot": Optional[str]
                }

        Returns:
            Claude APIに送信する完全なプロンプト
        """
        # エラーカテゴリを判定
        category, subcategory = self._categorize_error(error_info)

        # 該当するプロンプトテンプレートを取得
        if category in self.prompts and subcategory in self.prompts[category]:
            prompt_generator = self.prompts[category][subcategory]
            return prompt_generator(error_info)

        # デフォルトプロンプト
        return self._get_default_prompt(error_info)

    def _categorize_error(self, error_info: Dict) -> tuple:
        """
        エラー情報からカテゴリとサブカテゴリを判定

        Returns:
            (category, subcategory) のタプル
        """
        error_msg = error_info.get("error_message", "").lower()
        log = error_info.get("log", "").lower()
        combined = f"{error_msg} {log}"

        # ログインエラー
        if re.search(r"login|bot.*detect|captcha|ログイン", combined, re.I):
            if re.search(r"2fa|otp|二段階認証|パスキー", combined, re.I):
                return ("login", "2fa")
            return ("login", "bot_detection")

        # ページめくりエラー
        if re.search(r"page.*turn|ページめくり|ページ送り|同一ページ", combined, re.I):
            if re.search(r"特定.*書籍|マンガ|雑誌", combined, re.I):
                return ("page_turn", "book_specific")
            return ("page_turn", "stuck")

        # OCRエラー
        if re.search(r"ocr|認識精度|テキスト抽出", combined, re.I):
            if re.search(r"ヘッダー|フッター|header|footer", combined, re.I):
                return ("ocr", "header_footer")
            return ("ocr", "low_accuracy")

        # 文章生成エラー
        if re.search(r"生成.*文章|rag|llm|gpt|claude", combined, re.I):
            if re.search(r"関連性|irrelevant|無関係", combined, re.I):
                return ("text_generation", "rag_irrelevant")
            return ("text_generation", "low_quality")

        # インフラエラー
        if re.search(r"crash|クラッシュ|起動.*失敗", combined, re.I):
            return ("infrastructure", "crash")
        if re.search(r"memory|メモリ|leak|リーク", combined, re.I):
            return ("infrastructure", "memory_leak")

        # デフォルト（ページめくり）
        return ("page_turn", "stuck")

    # ==========================================================================
    # 1. ログイン機能のプロンプト
    # ==========================================================================

    def _get_login_bot_detection_prompt(self, error_info: Dict) -> str:
        """1.1. ログイン失敗（Bot検出）プロンプト"""
        return f"""# 命令

Kindle自動化ツールのAmazonログイン処理でエラーが発生しました。以下の情報に基づき、根本原因を特定し、複数の解決策を具体的なコードと共に提案してください。

## エラー情報

- **エラーメッセージ**: `{error_info.get('error_message', 'N/A')}`
- **発生日時**: `{error_info.get('timestamp', 'N/A')}`
- **スクリーンショット**: `{error_info.get('screenshot', 'N/A')}`
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 分析と解決策の要件

1. **根本原因分析**:
   - 提供された情報から、ログイン失敗の最も可能性の高い原因を5つ挙げてください（例: セレクタの変更、Bot検出、タイミング問題、iframe構造、A/Bテスト）。
   - それぞれの可能性について、なぜそう考えられるのか論理的に説明してください。

2. **解決策の提案**:
   - 特定した原因ごとに、堅牢で信頼性の高い解決策を提示してください。
   - **`app/services/capture/selenium_capture.py`** の `login` メソッドを修正する形で、具体的なPythonコードを生成してください。
   - 修正コードには、以下の要素を必ず含めてください:
       - `WebDriverWait` を使用した明示的な待機処理
       - 複数の代替セレクタ（CSS Selector, XPath）を用いたフォールバック
       - `ActionChains` を利用した人間らしい操作（クリック、入力）
       - 失敗時のリトライロジック（指数バックオフ付き）
       - 詳細なデバッグログ（試行中のセレクタ、待機時間など）

3. **テストコードの生成**:
   - 提案した修正を検証するための `pytest` テストケースを生成してください。
   - ログイン成功時と、意図的に失敗させた場合（不正なパスワードなど）の両方をテストしてください。

4. **予防策の提示**:
   - 今後同様の問題を未然に防ぐための、監視やアラートに関する提案を3つ挙げてください。
"""

    def _get_login_2fa_prompt(self, error_info: Dict) -> str:
        """1.2. 二段階認証・パスキー停止プロンプト"""
        return f"""# 命令

Kindle自動化ツールのログインフローにおいて、二段階認証（OTP）やパスキー認証の画面で処理が停止する問題を解決したい。現在の `app/services/capture/selenium_capture.py` の `login` メソッドを改善し、これらの手動介入が必要なステップをよりスムーズに処理するための改良案を提案してください。

## エラー情報

- **エラーメッセージ**: `{error_info.get('error_message', 'N/A')}`
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 現状の課題

- OTP入力やパスキー選択のために、一定時間 `time.sleep()` で待機しているが、ユーザーが入力しないとタイムアウトしてしまう。
- 処理がどこで待機しているのか、ユーザーに分かりにくい。

## 改善要件

1. **対話的な待機処理の実装**:
   - OTP入力画面やパスキー選択画面を検知したら、コンソールに明確な指示（例:「60秒以内に二段階認証コードを入力してください」）を表示し、ユーザーの入力を待つようにしてください。
   - ユーザーがコンソールで `Enter` キーを押すか、指定した要素（例:「ライブラリ」リンク）がページ上に表示されたら、次の処理に進むようにしてください。
   - タイムアウトした場合は、明確なエラーメッセージと共に処理を中断するようにしてください。

2. **パスキーダイアログの自動スキップ**:
   - Chromeの起動オプションを修正し、パスキー作成のダイアログをデフォルトで無効化または自動でキャンセルする設定を追加してください。
   - `ActionChains` を使って `Esc` キーを送信するなど、複数のスキップ戦略を実装してください。

3. **コード生成**:
   - 上記の要件を反映した、`login` メソッドの完全なPythonコードを生成してください。
   - ユーザーへの指示を出す部分は、`print()` 文で分かりやすく記述してください。
"""

    # ==========================================================================
    # 2. ページめくり機能のプロンプト
    # ==========================================================================

    def _get_page_turn_stuck_prompt(self, error_info: Dict) -> str:
        """2.1. ページめくり停止・繰り返しプロンプト"""
        return f"""# 命令

Kindleの自動キャプチャ中、ページめくりが機能せず、同じページを繰り返し撮影してしまいます。以下の情報に基づき、`app/services/capture/selenium_capture.py` の `_turn_page` メソッドを世界クラスの堅牢性を持つように修正してください。

## エラー情報

- **発生事象**: {error_info.get('error_message', '同じページを繰り返し検出')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 修正要件

1. **多段階フォールバック戦略の実装**:
   - 現在の実装（JavaScriptクリック）に加え、以下の戦略を段階的に実行するロジックを実装してください。
       1. **戦略1: 多様なJavaScriptセレクタ**: `kindleReader_pageTurnAreaRight`, `.navBar-button-next` など、複数のセレクタを試す。
       2. **戦略2: ActionChainsによる物理操作**: マウスカーソルを右端に移動してクリックし、さらに右矢印キーを送信する。
       3. **戦略3: iframeのリフレッシュ**: `iframe#KindleReaderIFrame` のコンテンツを強制的にリロードし、JavaScriptの状態をリセットする。
       4. **戦略4: URLによるページ指定**: 可能であれば、URLにページ番号を付与して直接遷移を試みる（`&page=X`など）。

2. **確実なページ変更検証**:
   - ページめくり操作の前後で、ページのHTML構造からMD5ハッシュを生成し、ハッシュ値が変更されたことをもって「成功」と判断してください。
   - ハッシュが変更されるまで、最大5回までリトライするようにしてください。

3. **動的な待機時間**:
   - `time.sleep()` を避け、`WebDriverWait` と `expected_conditions` を使用してください。
   - リトライごとに待機時間を段階的に長くする（例: 1秒 → 2秒 → 4秒）指数バックオフを実装してください。

4. **コード生成**:
   - 上記の要件をすべて満たす、修正後の `_turn_page` メソッドの完全なPythonコードを生成してください。
   - 各戦略の実行やリトライの状況がわかるように、詳細なデバッグログを追加してください。

## 参考

以前の修正では以下の改善を実施しました:
- MD5ハッシュによるページ変更検証
- ActionChainsによる物理操作フォールバック
- iframe強制リロード（3回目以降）
- 5回のリトライ（成功率99%+達成）

さらなる改善が必要な場合は、上記の実装を参考にしつつ、より堅牢な解決策を提案してください。
"""

    def _get_page_turn_book_specific_prompt(self, error_info: Dict) -> str:
        """2.2. 特定書籍でページめくり失敗プロンプト"""
        return f"""# 命令

Kindle文字起こしツールで、特定の書籍（例: マンガ、雑誌、特殊なレイアウトの技術書）でページめくりが失敗する問題があります。この問題を解決するため、書籍のタイプに応じてページめくり戦略を適応的に変更する機能を設計・実装してください。

## エラー情報

- **発生事象**: {error_info.get('error_message', '特定の書籍でページめくり失敗')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 設計要件

1. **書籍タイプの自動検出**:
   - キャプチャ開始時に、最初の数ページを分析し、その本が「標準テキスト」「マンガ」「雑誌」のいずれであるかを判定するロジックを提案してください。
   - 判定基準の例:
       - **標準テキスト**: テキスト領域の割合が高い。
       - **マンガ**: 画像領域の割合が高い、特定のコマ割りパターンがある。
       - **雑誌**: 複数のカラムレイアウト、多様なフォントサイズ。

2. **戦略の適応的選択**:
   - `_turn_page` メソッドを修正し、検出された書籍タイプに応じて、最適なページめくり方法を呼び出すようにしてください。
   - **マンガの場合**: 右から左へのページめくりに対応するため、左矢印キー送信や画面左側クリックも試す。
   - **雑誌の場合**: スクロールダウン（`Page Down`キー）もページ遷移の選択肢として追加する。

3. **ユーザーによる戦略指定**:
   - APIのエンドポイント `/api/v1/capture/start` のリクエストボディに、`page_turn_strategy`: "default" | "manga" | "magazine"` のようなオプションフィールドを追加し、ユーザーが明示的に戦略を指定できるようにしてください。

4. **コード生成**:
   - 上記の要件を実装した、`selenium_capture.py` 内の関連コード（`_turn_page` メソッド、`capture_all_pages` メソッドなど）と、FastAPIのエンドポイント定義（`app/api/v1/endpoints/capture.py`）の修正案を提示してください。
"""

    # ==========================================================================
    # 3. OCR・テキスト抽出のプロンプト
    # ==========================================================================

    def _get_ocr_low_accuracy_prompt(self, error_info: Dict) -> str:
        """3.1. OCR認識精度が低いプロンプト"""
        return f"""# 命令

OCRの認識精度が目標の99%に達していません。特に、図表内のテキストや特殊なフォントで精度が低下します。`app/services/ocr_service.py` と `app/services/ocr_preprocessing.py` を改善し、世界最高水準のOCR精度を達成するための修正案を提案してください。

## エラー情報

- **発生事象**: {error_info.get('error_message', 'OCR精度が低い')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 改善要件

1. **高度な画像前処理パイプラインの構築**:
   - 現在の前処理（グレースケール変換、二値化、ノイズ除去）に加え、以下の処理を追加してください:
       - **適応的閾値処理**: `cv2.adaptiveThreshold` を使用
       - **傾き補正**: Hough変換またはdilate/erodeでテキストラインを検出し、回転補正
       - **コントラスト強調**: CLAHE（Contrast Limited Adaptive Histogram Equalization）
       - **解像度向上**: 超解像技術（例: ESRGAN, Real-ESRGAN）の適用

2. **OCRエンジンの複数利用とアンサンブル**:
   - Tesseract OCRに加え、以下のOCRエンジンも併用し、結果を統合するロジックを実装してください:
       - **Google Cloud Vision API** (商用)
       - **Amazon Textract** (商用)
       - **EasyOCR** (オープンソース、多言語対応)
   - 複数エンジンの結果を比較し、信頼度スコアが高い結果を採用する「投票システム」を構築してください。

3. **言語・フォント別の最適化**:
   - 日本語（明朝体、ゴシック体）、英語、数式など、テキストの種類に応じてTesseractの設定（`--psm`、`--oem`、`lang`）を動的に変更するロジックを追加してください。

4. **コード生成**:
   - 上記の要件を実装した、`ocr_preprocessing.py` の `preprocess_image` メソッドと、`ocr_service.py` の `perform_ocr` メソッドの完全なPythonコードを生成してください。
"""

    def _get_ocr_header_footer_prompt(self, error_info: Dict) -> str:
        """3.2. ヘッダー・フッター混入プロンプト"""
        return f"""# 命令

OCRで抽出したテキストに、ページ番号やヘッダー・フッターが混入し、本文の品質が低下しています。`app/services/ocr_service.py` と `app/services/ocr_preprocessing.py` を改善し、これらの不要な要素を自動的に除去する機能を実装してください。

## エラー情報

- **発生事象**: {error_info.get('error_message', 'ヘッダー・フッターが混入')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 改善要件

1. **領域検出とマスキング**:
   - OpenCVを使用して、ページ画像から以下の領域を自動検出し、OCR対象から除外するロジックを実装してください:
       - **ヘッダー領域**: 画像上部の固定位置（例: 上端から5%の範囲）
       - **フッター領域**: 画像下部の固定位置（例: 下端から5%の範囲）
       - **ページ番号**: 小さな数字のみの領域（正規表現: `^\\d+$`）を検出
   - 検出した領域を白色（または黒色）で塗りつぶして、OCR実行前にマスクしてください。

2. **後処理によるフィルタリング**:
   - OCR後のテキストに対して、以下のルールで不要テキストを削除してください:
       - 単独の数字のみの行を削除（ページ番号）
       - 短すぎる行（3文字未満）を削除
       - 連続するページで同じ位置に現れる固定テキストを学習し、自動除外
   - 正規表現やNLPライブラリ（spaCyなど）を使用した、より高度なフィルタリングロジックを提案してください。

3. **機械学習による領域分類**:
   - 将来的には、ページ画像を「本文」「ヘッダー」「フッター」「図表」などの領域に分類する軽量なCNNモデル（例: U-Net, SegNet）の導入を検討してください。
   - 現時点では、OpenCVベースのルールベースアプローチで実装し、将来の拡張性を考慮した設計にしてください。

4. **コード生成**:
   - 上記の要件を実装した、`ocr_preprocessing.py` の新メソッド `mask_header_footer` と、`ocr_service.py` の `filter_unwanted_text` メソッドの完全なPythonコードを生成してください。
"""

    # ==========================================================================
    # 4. 文章生成のプロンプト
    # ==========================================================================

    def _get_text_gen_low_quality_prompt(self, error_info: Dict) -> str:
        """4.1. 生成文章の品質が低いプロンプト"""
        return f"""# 命令

LLMで生成される文章の品質が目標に達していません。文法エラー、不自然な表現、冗長性、内容の不正確さなどが見られます。`app/services/llm_service.py` と、使用しているプロンプトテンプレート（`app/prompts/`）を改善し、世界最高品質の文章生成を実現してください。

## エラー情報

- **発生事象**: {error_info.get('error_message', '生成文章の品質が低い')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 改善要件

1. **プロンプトエンジニアリングの高度化**:
   - 現在のプロンプトテンプレートを見直し、以下の要素を追加してください:
       - **明確なペルソナ設定**: 「あなたは経験豊富なプロの編集者です」など
       - **具体的な出力形式の指定**: 「以下の構造で出力してください: 1. 要約（150字以内）、2. 本文（段落ごとに改行）、3. キーポイント（箇条書き）」
       - **品質基準の明示**: 「中学生でも理解できる平易な日本語を使用」「冗長な表現は避ける」
       - **Few-shot例の提供**: 良い例と悪い例を3セット提示

2. **チェーン・オブ・ソート（CoT）の導入**:
   - LLMに「段階的に考える」よう促すプロンプトを追加してください。
   - 例: 「まず、入力テキストの主要なテーマを3つ抽出してください。次に、それぞれのテーマについて詳細を説明してください。最後に、全体を統合した文章を生成してください。」

3. **品質評価と再生成ループ**:
   - 生成された文章を自動評価する関数を実装してください:
       - **文法チェック**: `language_tool_python` などを使用
       - **可読性スコア**: Flesch Reading Easeなどの指標
       - **キーワード整合性**: 入力テキストの重要キーワードが出力に含まれているか
   - 品質スコアが閾値を下回る場合、自動的に再生成を試みるロジックを追加してください（最大3回）。

4. **コード生成**:
   - 上記の要件を実装した、`llm_service.py` の `generate_text` メソッドと、新しいプロンプトテンプレート `app/prompts/high_quality_generation.txt` の完全なコードを生成してください。
"""

    def _get_text_gen_rag_irrelevant_prompt(self, error_info: Dict) -> str:
        """4.2. RAG関連性が低いプロンプト"""
        return f"""# 命令

RAG（Retrieval-Augmented Generation）システムで、検索された参照情報が質問やクエリと関連性が低く、生成される回答の品質が低下しています。`app/services/rag_service.py` と `app/services/vector_store.py` を改善し、より適切な情報を検索・活用できるようにしてください。

## エラー情報

- **発生事象**: {error_info.get('error_message', 'RAG検索結果が無関係')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 改善要件

1. **ベクトル検索の精度向上**:
   - 現在の埋め込みモデル（`sentence-transformers/all-MiniLM-L6-v2` など）を、より高性能なモデルに置き換えてください:
       - **日本語対応**: `intfloat/multilingual-e5-large` または `sonoisa/sentence-bert-base-ja-mean-tokens-v2`
       - **専門ドメイン特化**: 書籍・文学ドメインでファインチューニングされたモデルの検討
   - チャンキング戦略を見直し、セマンティックチャンク（意味的なまとまり）ごとに分割するロジックを実装してください。

2. **ハイブリッド検索の導入**:
   - ベクトル検索（意味的類似度）に加え、以下の手法を組み合わせてください:
       - **BM25キーワード検索**: 完全一致や部分一致を補完
       - **リランキング**: 検索結果を再スコアリングして精度向上（例: Cross-Encoderモデル）
   - ベクトルスコアとBM25スコアを統合する重み付けロジック（例: Reciprocal Rank Fusion）を実装してください。

3. **コンテキスト拡張とフィルタリング**:
   - 検索されたチャンクの前後の文脈も含めて取得し、LLMに渡すコンテキストを拡張してください。
   - 検索結果のスコアが閾値（例: コサイン類似度0.7）を下回る場合、その結果を除外するフィルタを追加してください。

4. **コード生成**:
   - 上記の要件を実装した、`rag_service.py` の `retrieve` メソッドと、`vector_store.py` の `hybrid_search` メソッドの完全なPythonコードを生成してください。
"""

    # ==========================================================================
    # 5. インフラ・パフォーマンスのプロンプト
    # ==========================================================================

    def _get_infra_crash_prompt(self, error_info: Dict) -> str:
        """5.1. アプリケーションクラッシュプロンプト"""
        return f"""# 命令

Kindle文字起こしツールがクラッシュし、正常に起動しないか、実行中に突然終了します。以下の情報に基づき、根本原因を特定し、安定性を向上させるための修正案を提案してください。

## エラー情報

- **エラーメッセージ**: `{error_info.get('error_message', 'N/A')}`
- **発生日時**: `{error_info.get('timestamp', 'N/A')}`
- **スタックトレース**:
```log
{error_info.get('log', 'ログなし')}
```

## 分析と解決策の要件

1. **根本原因分析**:
   - スタックトレースとエラーメッセージから、クラッシュの原因を特定してください。
   - 可能性の高い原因を5つ挙げ、それぞれについて詳細に説明してください:
       - 未処理の例外
       - 依存ライブラリのバージョン不整合
       - メモリ不足
       - ファイルI/Oエラー
       - データベース接続エラー

2. **エラーハンドリングの強化**:
   - クラッシュが発生した箇所を特定し、適切な `try-except` ブロックを追加してください。
   - エラー発生時に、詳細なログを出力し、グレースフルシャットダウン（リソースの適切な解放）を行うコードを生成してください。

3. **ヘルスチェックとリトライメカニズム**:
   - アプリケーション起動時に、必要なリソース（データベース、外部API、ファイルシステム）が利用可能かチェックする関数を実装してください。
   - 一時的な問題（ネットワークエラーなど）の場合、指数バックオフでリトライするロジックを追加してください。

4. **コード生成**:
   - 特定した原因に対する修正コードと、エラーハンドリングを強化したコード全体を生成してください。
   - 具体的なファイルパスとメソッド名を含めてください。
"""

    def _get_infra_memory_leak_prompt(self, error_info: Dict) -> str:
        """5.2. メモリリークプロンプト"""
        return f"""# 命令

Kindle文字起こしツールを長時間実行すると、メモリ使用量が増大し、最終的にシステムがスローダウンまたはクラッシュします。メモリリークの原因を特定し、メモリ効率を改善する修正案を提案してください。

## エラー情報

- **発生事象**: {error_info.get('error_message', 'メモリ使用量が増大')}
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 分析と解決策の要件

1. **メモリリークの原因特定**:
   - Pythonのメモリプロファイリングツール（`memory_profiler`, `tracemalloc`）を使用して、メモリリークの原因を特定する方法を提案してください。
   - 可能性の高い原因:
       - 大量の画像データをメモリ内に保持
       - Seleniumドライバーのリソースが解放されていない
       - ベクトルストアやキャッシュが無制限に増大
       - グローバル変数への参照が残っている

2. **メモリ効率の改善**:
   - 以下の最適化を実装してください:
       - **ストリーム処理**: 大きなファイルを一度にメモリに読み込まず、チャンクごとに処理
       - **明示的なリソース解放**: `with` 文やコンテキストマネージャーを使用
       - **ガベージコレクション**: `gc.collect()` を適切なタイミングで呼び出し
       - **弱参照**: 必要に応じて `weakref` モジュールを使用

3. **監視とアラート**:
   - アプリケーションのメモリ使用量を定期的にログ出力する関数を追加してください。
   - メモリ使用量が閾値（例: 2GB）を超えたら、警告を発する仕組みを実装してください。

4. **コード生成**:
   - 上記の改善を実装した、具体的なファイルとメソッドの修正コードを生成してください。
   - メモリプロファイリングを行うためのサンプルスクリプトも提供してください。
"""

    # ==========================================================================
    # デフォルトプロンプト
    # ==========================================================================

    def _get_default_prompt(self, error_info: Dict) -> str:
        """デフォルトのエラー解決プロンプト"""
        return f"""# 命令

Kindle文字起こしツールでエラーが発生しました。以下の情報に基づき、根本原因を特定し、解決策を提案してください。

## エラー情報

- **エラーメッセージ**: `{error_info.get('error_message', 'N/A')}`
- **発生日時**: `{error_info.get('timestamp', 'N/A')}`
- **ファイルパス**: `{error_info.get('file_path', 'N/A')}`
- **ログ**:
```log
{error_info.get('log', 'ログなし')}
```

## 分析と解決策の要件

1. **根本原因分析**:
   - 提供された情報から、エラーの最も可能性の高い原因を5つ挙げてください。
   - それぞれの可能性について、論理的に説明してください。

2. **解決策の提案**:
   - 特定した原因ごとに、具体的な解決策を提示してください。
   - 可能であれば、修正コードを生成してください。
   - 修正コードには、適切なエラーハンドリングとデバッグログを含めてください。

3. **テストと検証**:
   - 提案した修正を検証するためのテスト方法を説明してください。
   - 可能であれば、pytestテストケースを生成してください。

4. **予防策の提示**:
   - 今後同様の問題を未然に防ぐための提案を3つ挙げてください。
"""


# テスト用コード
if __name__ == "__main__":
    generator = ErrorPromptGenerator()

    # テストケース1: ページめくりエラー
    test_error_1 = {
        "error_message": "ページめくりが3回連続で失敗しました",
        "timestamp": "2025-11-05 18:30:00",
        "log": "WARNING: ページが変更されていません (試行 1/3): hash=abcd1234\nERROR: ページ送り完全失敗",
        "file_path": "app/services/capture/selenium_capture.py"
    }

    prompt = generator.generate_prompt(test_error_1)
    print("=" * 80)
    print("テスト1: ページめくりエラー")
    print("=" * 80)
    print(prompt[:500] + "...\n")

    # テストケース2: ログインエラー
    test_error_2 = {
        "error_message": "Bot detection: CAPTCHAが表示されました",
        "timestamp": "2025-11-05 19:00:00",
        "log": "ERROR: Login failed - Bot detection triggered",
        "file_path": "app/services/capture/selenium_capture.py"
    }

    prompt = generator.generate_prompt(test_error_2)
    print("=" * 80)
    print("テスト2: ログインエラー（Bot検出）")
    print("=" * 80)
    print(prompt[:500] + "...\n")

    print("✅ ErrorPromptGenerator テスト完了！")
