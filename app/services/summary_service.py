"""
Summary Service for Text Summarization

LLM-based text summarization with multiple strategies:
- Extractive summarization (select key sentences)
- Abstractive summarization (generate new text with LLM)
- Map-reduce for long documents (chunk → summarize → combine)
- Multi-level summarization (executive, standard, detailed)
"""
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class SummaryLength(str, Enum):
    """要約の長さ"""
    SHORT = "short"  # 100-200 chars
    MEDIUM = "medium"  # 200-500 chars
    LONG = "long"  # 500-1000 chars


class SummaryTone(str, Enum):
    """要約のトーン"""
    PROFESSIONAL = "professional"  # ビジネス向け
    CASUAL = "casual"  # カジュアル
    ACADEMIC = "academic"  # 学術的
    EXECUTIVE = "executive"  # 経営層向け


class SummaryGranularity(str, Enum):
    """要約の粒度"""
    HIGH_LEVEL = "high_level"  # 主要ポイントのみ
    DETAILED = "detailed"  # 例を含む詳細
    COMPREHENSIVE = "comprehensive"  # 完全カバレッジ


class SummaryFormat(str, Enum):
    """要約のフォーマット"""
    PLAIN_TEXT = "plain_text"  # プレーンテキスト
    BULLET_POINTS = "bullet_points"  # 箇条書き
    STRUCTURED = "structured"  # セクション見出し付き


class SummaryLevel(int, Enum):
    """マルチレベル要約のレベル"""
    EXECUTIVE = 1  # 1-2文、50-100文字
    STANDARD = 2  # 1段落、200-300文字
    DETAILED = 3  # 複数段落、500-1000文字


class SummaryService:
    """要約サービス"""

    # トークン制限
    MAX_TOKENS_PER_CHUNK = 3000  # チャンクあたりの最大トークン数
    MAX_TOTAL_TOKENS = 100000  # 1回の要約処理での最大トークン数

    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        temperature: float = 0.3,  # 要約は低めのtemperatureが推奨
    ):
        """
        要約サービス初期化

        Args:
            provider: "anthropic" or "openai"
            model: モデル名（Noneの場合はデフォルト）
            temperature: 生成の多様性（0.0-1.0、要約は低めが推奨）
        """
        self.llm_service = LLMService(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=2048
        )
        self.provider = provider
        logger.info(f"SummaryService initialized with provider: {provider}")

    def detect_language(self, text: str) -> str:
        """
        テキストの言語を検出

        Args:
            text: 入力テキスト

        Returns:
            "ja" (日本語) or "en" (英語)
        """
        # 簡易的な日本語検出（ひらがな、カタカナ、漢字の存在）
        japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text)
        if len(japanese_chars) > len(text) * 0.3:  # 30%以上が日本語文字
            return "ja"
        return "en"

    def estimate_tokens(self, text: str) -> int:
        """
        テキストのトークン数を概算

        Args:
            text: 入力テキスト

        Returns:
            概算トークン数
        """
        # 簡易的な推定：英語は単語数 × 1.3、日本語は文字数 × 0.5
        language = self.detect_language(text)
        if language == "ja":
            return int(len(text) * 0.5)
        else:
            return int(len(text.split()) * 1.3)

    def chunk_text(
        self,
        text: str,
        max_tokens: int = MAX_TOKENS_PER_CHUNK
    ) -> List[str]:
        """
        長いテキストをチャンクに分割

        Args:
            text: 入力テキスト
            max_tokens: チャンクあたりの最大トークン数

        Returns:
            チャンクのリスト
        """
        # 段落で分割
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_tokens = self.estimate_tokens(paragraph)

            # 単一段落が最大トークン数を超える場合は文で分割
            if paragraph_tokens > max_tokens:
                sentences = re.split(r'[。.!?]\s*', paragraph)
                for sentence in sentences:
                    if not sentence:
                        continue
                    sentence_tokens = self.estimate_tokens(sentence)

                    if current_tokens + sentence_tokens > max_tokens:
                        if current_chunk:
                            chunks.append('\n\n'.join(current_chunk))
                            current_chunk = []
                            current_tokens = 0

                    current_chunk.append(sentence)
                    current_tokens += sentence_tokens
            else:
                # 段落全体を追加できるか確認
                if current_tokens + paragraph_tokens > max_tokens:
                    if current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        current_chunk = []
                        current_tokens = 0

                current_chunk.append(paragraph)
                current_tokens += paragraph_tokens

        # 最後のチャンクを追加
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        logger.info(f"Text split into {len(chunks)} chunks")
        return chunks

    def _build_summary_prompt(
        self,
        text: str,
        length: SummaryLength,
        tone: SummaryTone,
        granularity: SummaryGranularity,
        format_type: SummaryFormat,
        language: str,
        level: Optional[SummaryLevel] = None
    ) -> Tuple[str, str]:
        """
        要約プロンプトを構築

        Args:
            text: 要約対象テキスト
            length: 要約の長さ
            tone: トーン
            granularity: 粒度
            format_type: フォーマット
            language: 言語 ("ja" or "en")
            level: マルチレベル要約のレベル（オプション）

        Returns:
            (system_prompt, user_prompt)のタプル
        """
        # 言語別のプロンプト
        if language == "ja":
            system_prompt = self._build_japanese_system_prompt(tone, granularity)
            user_prompt = self._build_japanese_user_prompt(
                text, length, format_type, level
            )
        else:
            system_prompt = self._build_english_system_prompt(tone, granularity)
            user_prompt = self._build_english_user_prompt(
                text, length, format_type, level
            )

        return system_prompt, user_prompt

    def _build_japanese_system_prompt(
        self,
        tone: SummaryTone,
        granularity: SummaryGranularity
    ) -> str:
        """日本語用システムプロンプト"""
        tone_instructions = {
            SummaryTone.PROFESSIONAL: "ビジネス文書として、丁寧で正確な表現を使用してください。",
            SummaryTone.CASUAL: "読みやすく親しみやすい表現を使用してください。",
            SummaryTone.ACADEMIC: "学術的で正確な表現を使用し、専門用語を適切に使ってください。",
            SummaryTone.EXECUTIVE: "経営層向けに、要点を明確に、簡潔にまとめてください。",
        }

        granularity_instructions = {
            SummaryGranularity.HIGH_LEVEL: "最も重要なポイントのみを抽出してください。",
            SummaryGranularity.DETAILED: "重要なポイントに加え、具体例や詳細も含めてください。",
            SummaryGranularity.COMPREHENSIVE: "全体を網羅的にカバーし、重要な詳細を漏らさないでください。",
        }

        return f"""あなたは優秀な要約アシスタントです。
以下の指示に従ってテキストを要約してください：

【トーン】
{tone_instructions[tone]}

【粒度】
{granularity_instructions[granularity]}

【重要な注意点】
- 元のテキストの意味を正確に保ってください
- 重要な情報を省略しないでください
- 簡潔で読みやすい文章にしてください
- 日本語として自然な表現を使ってください
"""

    def _build_english_system_prompt(
        self,
        tone: SummaryTone,
        granularity: SummaryGranularity
    ) -> str:
        """英語用システムプロンプト"""
        tone_instructions = {
            SummaryTone.PROFESSIONAL: "Use professional and formal language.",
            SummaryTone.CASUAL: "Use casual and friendly language.",
            SummaryTone.ACADEMIC: "Use academic and precise language with appropriate terminology.",
            SummaryTone.EXECUTIVE: "Focus on key points concisely for executive audience.",
        }

        granularity_instructions = {
            SummaryGranularity.HIGH_LEVEL: "Extract only the most important points.",
            SummaryGranularity.DETAILED: "Include important points with examples and details.",
            SummaryGranularity.COMPREHENSIVE: "Provide comprehensive coverage without missing key details.",
        }

        return f"""You are an expert summarization assistant.
Please summarize the text according to these instructions:

【Tone】
{tone_instructions[tone]}

【Granularity】
{granularity_instructions[granularity]}

【Important Notes】
- Preserve the original meaning accurately
- Do not omit important information
- Write concisely and clearly
- Use natural language
"""

    def _build_japanese_user_prompt(
        self,
        text: str,
        length: SummaryLength,
        format_type: SummaryFormat,
        level: Optional[SummaryLevel] = None
    ) -> str:
        """日本語用ユーザープロンプト"""
        length_chars = {
            SummaryLength.SHORT: "100-200文字",
            SummaryLength.MEDIUM: "200-500文字",
            SummaryLength.LONG: "500-1000文字",
        }

        # マルチレベル要約の場合
        if level is not None:
            if level == SummaryLevel.EXECUTIVE:
                length_instruction = "1-2文（50-100文字）"
                detail_instruction = "最も重要なポイントのみ"
            elif level == SummaryLevel.STANDARD:
                length_instruction = "1段落（200-300文字）"
                detail_instruction = "主要なポイントを含める"
            else:  # DETAILED
                length_instruction = "複数段落（500-1000文字）"
                detail_instruction = "詳細な情報も含める"
        else:
            length_instruction = length_chars[length]
            detail_instruction = ""

        format_instructions = {
            SummaryFormat.PLAIN_TEXT: "通常の文章形式で要約してください。",
            SummaryFormat.BULLET_POINTS: "箇条書き形式（•で開始）で要約してください。",
            SummaryFormat.STRUCTURED: "見出しとセクションを使った構造化された形式で要約してください。",
        }

        prompt = f"""以下のテキストを要約してください。

【要約の長さ】
{length_instruction}

【フォーマット】
{format_instructions[format_type]}
"""

        if detail_instruction:
            prompt += f"\n【詳細レベル】\n{detail_instruction}\n"

        prompt += f"\n【元のテキスト】\n{text}\n\n【要約】\n"

        return prompt

    def _build_english_user_prompt(
        self,
        text: str,
        length: SummaryLength,
        format_type: SummaryFormat,
        level: Optional[SummaryLevel] = None
    ) -> str:
        """英語用ユーザープロンプト"""
        length_chars = {
            SummaryLength.SHORT: "100-200 characters",
            SummaryLength.MEDIUM: "200-500 characters",
            SummaryLength.LONG: "500-1000 characters",
        }

        # マルチレベル要約の場合
        if level is not None:
            if level == SummaryLevel.EXECUTIVE:
                length_instruction = "1-2 sentences (50-100 chars)"
                detail_instruction = "Only the most critical points"
            elif level == SummaryLevel.STANDARD:
                length_instruction = "1 paragraph (200-300 chars)"
                detail_instruction = "Include main points"
            else:  # DETAILED
                length_instruction = "Multiple paragraphs (500-1000 chars)"
                detail_instruction = "Include detailed information"
        else:
            length_instruction = length_chars[length]
            detail_instruction = ""

        format_instructions = {
            SummaryFormat.PLAIN_TEXT: "Summarize in plain text format.",
            SummaryFormat.BULLET_POINTS: "Summarize in bullet point format (• prefix).",
            SummaryFormat.STRUCTURED: "Summarize in structured format with sections and headers.",
        }

        prompt = f"""Please summarize the following text.

【Length】
{length_instruction}

【Format】
{format_instructions[format_type]}
"""

        if detail_instruction:
            prompt += f"\n【Detail Level】\n{detail_instruction}\n"

        prompt += f"\n【Original Text】\n{text}\n\n【Summary】\n"

        return prompt

    def summarize(
        self,
        text: str,
        length: SummaryLength = SummaryLength.MEDIUM,
        tone: SummaryTone = SummaryTone.PROFESSIONAL,
        granularity: SummaryGranularity = SummaryGranularity.HIGH_LEVEL,
        format_type: SummaryFormat = SummaryFormat.PLAIN_TEXT,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        テキストを要約（シングルレベル）

        Args:
            text: 要約対象テキスト
            length: 要約の長さ
            tone: トーン
            granularity: 粒度
            format_type: フォーマット
            language: 言語（Noneの場合は自動検出）
            progress_callback: 進捗コールバック関数

        Returns:
            {
                "summary": "要約テキスト",
                "language": "ja" or "en",
                "tokens": {"total": 100, "prompt": 50, "completion": 50},
                "chunks": 1,  # 処理したチャンク数
                "is_mock": False
            }
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # 言語検出
        if language is None:
            language = self.detect_language(text)
        logger.info(f"Detected language: {language}")

        # トークン数推定
        total_tokens = self.estimate_tokens(text)
        logger.info(f"Estimated tokens: {total_tokens}")

        # 短いテキスト：直接要約
        if total_tokens <= self.MAX_TOKENS_PER_CHUNK:
            return self._summarize_single_chunk(
                text, length, tone, granularity, format_type, language
            )

        # 長いテキスト：Map-Reduce戦略
        return self._summarize_long_text(
            text, length, tone, granularity, format_type, language, progress_callback
        )

    def _summarize_single_chunk(
        self,
        text: str,
        length: SummaryLength,
        tone: SummaryTone,
        granularity: SummaryGranularity,
        format_type: SummaryFormat,
        language: str
    ) -> Dict[str, Any]:
        """単一チャンクの要約"""
        system_prompt, user_prompt = self._build_summary_prompt(
            text, length, tone, granularity, format_type, language
        )

        result = self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )

        return {
            "summary": result["content"].strip(),
            "language": language,
            "tokens": result["tokens"],
            "chunks": 1,
            "is_mock": result["is_mock"]
        }

    def _summarize_long_text(
        self,
        text: str,
        length: SummaryLength,
        tone: SummaryTone,
        granularity: SummaryGranularity,
        format_type: SummaryFormat,
        language: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        長いテキストのMap-Reduce要約

        Map: 各チャンクを要約
        Reduce: 要約を統合して最終要約を生成
        """
        logger.info("Using Map-Reduce strategy for long text")

        # チャンク分割
        chunks = self.chunk_text(text)
        logger.info(f"Split into {len(chunks)} chunks")

        # Map: 各チャンクを要約
        chunk_summaries = []
        total_tokens = {"total": 0, "prompt": 0, "completion": 0}

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress = int((i / len(chunks)) * 80)  # 80%までをMap処理
                progress_callback(progress)

            logger.info(f"Summarizing chunk {i+1}/{len(chunks)}")

            # 中間要約は簡潔に（MEDIUMまたはSHORT）
            chunk_length = SummaryLength.MEDIUM if len(chunks) > 5 else length

            result = self._summarize_single_chunk(
                chunk, chunk_length, tone, granularity, format_type, language
            )

            chunk_summaries.append(result["summary"])

            # トークン数を累積
            total_tokens["total"] += result["tokens"]["total"]
            total_tokens["prompt"] += result["tokens"]["prompt"]
            total_tokens["completion"] += result["tokens"]["completion"]

        # Reduce: チャンク要約を統合
        if progress_callback:
            progress_callback(80)

        logger.info("Combining chunk summaries")
        combined_text = "\n\n".join(chunk_summaries)

        # 最終要約
        final_result = self._summarize_single_chunk(
            combined_text, length, tone, granularity, format_type, language
        )

        # トークン数を累積
        total_tokens["total"] += final_result["tokens"]["total"]
        total_tokens["prompt"] += final_result["tokens"]["prompt"]
        total_tokens["completion"] += final_result["tokens"]["completion"]

        if progress_callback:
            progress_callback(100)

        return {
            "summary": final_result["summary"],
            "language": language,
            "tokens": total_tokens,
            "chunks": len(chunks),
            "is_mock": final_result["is_mock"]
        }

    def summarize_multilevel(
        self,
        text: str,
        tone: SummaryTone = SummaryTone.PROFESSIONAL,
        format_type: SummaryFormat = SummaryFormat.PLAIN_TEXT,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        マルチレベル要約（3レベル）

        Args:
            text: 要約対象テキスト
            tone: トーン
            format_type: フォーマット
            language: 言語（Noneの場合は自動検出）
            progress_callback: 進捗コールバック関数

        Returns:
            {
                "level_1": {
                    "summary": "エグゼクティブサマリー",
                    "tokens": {...}
                },
                "level_2": {
                    "summary": "標準要約",
                    "tokens": {...}
                },
                "level_3": {
                    "summary": "詳細要約",
                    "tokens": {...}
                },
                "language": "ja",
                "total_tokens": {...}
            }
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # 言語検出
        if language is None:
            language = self.detect_language(text)
        logger.info(f"Multi-level summary - detected language: {language}")

        levels_result = {}
        total_tokens = {"total": 0, "prompt": 0, "completion": 0}

        # Level 3 (詳細) → Level 2 (標準) → Level 1 (エグゼクティブ)の順で生成
        # これにより、詳細→要点への自然な流れを作る

        # Level 3: Detailed (500-1000 chars)
        if progress_callback:
            progress_callback(10)

        logger.info("Generating Level 3 (Detailed) summary")
        level_3_result = self.summarize(
            text=text,
            length=SummaryLength.LONG,
            tone=tone,
            granularity=SummaryGranularity.COMPREHENSIVE,
            format_type=format_type,
            language=language
        )

        levels_result["level_3"] = {
            "summary": level_3_result["summary"],
            "tokens": level_3_result["tokens"],
            "level": SummaryLevel.DETAILED.value
        }
        self._accumulate_tokens(total_tokens, level_3_result["tokens"])

        if progress_callback:
            progress_callback(40)

        # Level 2: Standard (200-300 chars)
        logger.info("Generating Level 2 (Standard) summary")
        level_2_result = self.summarize(
            text=level_3_result["summary"],  # Level 3の要約をベースに
            length=SummaryLength.MEDIUM,
            tone=tone,
            granularity=SummaryGranularity.HIGH_LEVEL,
            format_type=format_type,
            language=language
        )

        levels_result["level_2"] = {
            "summary": level_2_result["summary"],
            "tokens": level_2_result["tokens"],
            "level": SummaryLevel.STANDARD.value
        }
        self._accumulate_tokens(total_tokens, level_2_result["tokens"])

        if progress_callback:
            progress_callback(70)

        # Level 1: Executive (50-100 chars)
        logger.info("Generating Level 1 (Executive) summary")
        system_prompt, user_prompt = self._build_summary_prompt(
            level_2_result["summary"],  # Level 2の要約をベースに
            SummaryLength.SHORT,
            tone,
            SummaryGranularity.HIGH_LEVEL,
            SummaryFormat.PLAIN_TEXT,  # Executive は常にプレーンテキスト
            language,
            level=SummaryLevel.EXECUTIVE
        )

        level_1_llm_result = self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt
        )

        levels_result["level_1"] = {
            "summary": level_1_llm_result["content"].strip(),
            "tokens": level_1_llm_result["tokens"],
            "level": SummaryLevel.EXECUTIVE.value
        }
        self._accumulate_tokens(total_tokens, level_1_llm_result["tokens"])

        if progress_callback:
            progress_callback(100)

        return {
            "level_1": levels_result["level_1"],
            "level_2": levels_result["level_2"],
            "level_3": levels_result["level_3"],
            "language": language,
            "total_tokens": total_tokens,
            "is_mock": level_1_llm_result["is_mock"]
        }

    def _accumulate_tokens(
        self,
        total: Dict[str, int],
        new: Dict[str, int]
    ):
        """トークン数を累積"""
        total["total"] += new["total"]
        total["prompt"] += new["prompt"]
        total["completion"] += new["completion"]

    def get_token_usage(self) -> Dict[str, int]:
        """
        累積トークン使用量を取得

        Returns:
            {"total": 100, "prompt": 50, "completion": 50}
        """
        return self.llm_service.get_token_usage()

    def reset_token_counter(self):
        """トークンカウンターをリセット"""
        self.llm_service.reset_token_counter()


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # サンプルテキスト（日本語）
    japanese_text = """
    人工知能（AI）は、近年急速に発展しており、私たちの生活に大きな影響を与えています。
    特に機械学習と深層学習の進歩により、画像認識、自然言語処理、音声認識などの分野で
    著しい成果が得られています。

    AIの応用範囲は広く、医療診断、自動運転、金融取引、製造業など、様々な産業で活用されています。
    しかし、AIの発展に伴い、倫理的な問題やプライバシーの懸念も生じています。
    今後は、技術の進歩と社会的責任のバランスを取ることが重要です。

    また、AI技術の発展により、多くの仕事が自動化される可能性があります。
    これは経済や雇用に大きな影響を与える可能性があり、教育システムの見直しや
    新しいスキルの習得が必要になるでしょう。
    """

    # 要約サービス作成
    summary_service = SummaryService(provider="anthropic")

    # シングルレベル要約
    print("=== Single-level Summary ===")
    result = summary_service.summarize(
        text=japanese_text,
        length=SummaryLength.MEDIUM,
        tone=SummaryTone.PROFESSIONAL,
        format_type=SummaryFormat.BULLET_POINTS
    )
    print(f"Summary: {result['summary']}")
    print(f"Tokens: {result['tokens']}")
    print(f"Language: {result['language']}")
    print()

    # マルチレベル要約
    print("=== Multi-level Summary ===")
    multilevel_result = summary_service.summarize_multilevel(
        text=japanese_text,
        tone=SummaryTone.PROFESSIONAL
    )
    print(f"Level 1 (Executive): {multilevel_result['level_1']['summary']}")
    print(f"Level 2 (Standard): {multilevel_result['level_2']['summary']}")
    print(f"Level 3 (Detailed): {multilevel_result['level_3']['summary']}")
    print(f"Total Tokens: {multilevel_result['total_tokens']}")
