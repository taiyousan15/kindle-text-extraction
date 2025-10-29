"""
LLM Service for RAG

LangChain統合、Claude/GPT-4クライアント設定、APIキー管理
"""
import logging
from typing import Optional, List, Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.callbacks.base import BaseCallbackHandler
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenCounterCallback(BaseCallbackHandler):
    """トークン数カウント用コールバック"""

    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def on_llm_end(self, response, **kwargs):
        """LLM完了時にトークン数を集計"""
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            self.total_tokens += token_usage.get('total_tokens', 0)
            self.prompt_tokens += token_usage.get('prompt_tokens', 0)
            self.completion_tokens += token_usage.get('completion_tokens', 0)


class LLMService:
    """LLMサービス（Claude/GPT-4統合）"""

    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60
    ):
        """
        LLMサービス初期化

        Args:
            provider: "anthropic" or "openai"
            model: モデル名（Noneの場合はデフォルト）
            temperature: 生成の多様性（0.0-1.0）
            max_tokens: 最大トークン数
            timeout: タイムアウト秒数
        """
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.token_callback = TokenCounterCallback()

        # APIキーチェック
        if provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                logger.warning("ANTHROPIC_API_KEY not configured. LLM will use mock responses.")
                self.client = None
                self.is_mock = True
            else:
                self.model = model or "claude-3-sonnet-20240229"
                self.client = self._create_anthropic_client()
                self.is_mock = False
                logger.info(f"Initialized Anthropic client with model: {self.model}")

        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not configured. LLM will use mock responses.")
                self.client = None
                self.is_mock = True
            else:
                self.model = model or "gpt-4-turbo-preview"
                self.client = self._create_openai_client()
                self.is_mock = False
                logger.info(f"Initialized OpenAI client with model: {self.model}")

        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'anthropic' or 'openai'.")

    def _create_anthropic_client(self) -> ChatAnthropic:
        """Anthropic (Claude) クライアント作成"""
        return ChatAnthropic(
            model=self.model,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
            callbacks=[self.token_callback]
        )

    def _create_openai_client(self) -> ChatOpenAI:
        """OpenAI (GPT-4) クライアント作成"""
        return ChatOpenAI(
            model=self.model,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            request_timeout=self.timeout,
            callbacks=[self.token_callback]
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ) -> Dict[str, Any]:
        """
        テキスト生成（リトライロジック付き）

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト
            retry_count: リトライ回数
            retry_delay: リトライ間隔（秒）

        Returns:
            {
                "content": "生成されたテキスト",
                "tokens": {"total": 100, "prompt": 50, "completion": 50},
                "model": "claude-3-sonnet-20240229",
                "is_mock": False
            }
        """
        # モックモード
        if self.is_mock:
            logger.warning("Using mock LLM response (API key not configured)")
            return {
                "content": self._generate_mock_response(prompt, system_prompt),
                "tokens": {"total": 0, "prompt": 0, "completion": 0},
                "model": "mock",
                "is_mock": True
            }

        # メッセージ構築
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # リトライロジック
        last_error = None
        for attempt in range(retry_count):
            try:
                logger.debug(f"LLM generation attempt {attempt + 1}/{retry_count}")

                # リセットトークンカウンター
                self.token_callback.total_tokens = 0
                self.token_callback.prompt_tokens = 0
                self.token_callback.completion_tokens = 0

                # 生成実行
                response = self.client.invoke(messages)

                result = {
                    "content": response.content,
                    "tokens": {
                        "total": self.token_callback.total_tokens,
                        "prompt": self.token_callback.prompt_tokens,
                        "completion": self.token_callback.completion_tokens
                    },
                    "model": self.model,
                    "is_mock": False
                }

                logger.info(
                    f"LLM generation successful. Tokens: {self.token_callback.total_tokens}"
                )
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM generation failed (attempt {attempt + 1}/{retry_count}): {e}"
                )

                if attempt < retry_count - 1:
                    time.sleep(retry_delay * (attempt + 1))  # 指数バックオフ
                    continue

        # 全リトライ失敗
        logger.error(f"LLM generation failed after {retry_count} attempts: {last_error}")
        raise Exception(f"LLM generation failed: {last_error}")

    def generate_with_context(
        self,
        query: str,
        context_documents: List[str],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        コンテキスト付き生成（RAG用）

        Args:
            query: ユーザークエリ
            context_documents: 取得したドキュメントのリスト
            system_prompt: システムプロンプト

        Returns:
            生成結果（generate()と同じ形式）
        """
        # デフォルトシステムプロンプト
        if system_prompt is None:
            system_prompt = (
                "あなたは親切で正確なアシスタントです。"
                "提供されたコンテキスト情報を基に、ユーザーの質問に答えてください。"
                "コンテキストに情報がない場合は、正直にそう伝えてください。"
            )

        # コンテキストドキュメントを整形
        context_text = "\n\n---\n\n".join([
            f"Document {i+1}:\n{doc}"
            for i, doc in enumerate(context_documents)
        ])

        # プロンプト構築
        full_prompt = f"""以下のコンテキスト情報を参考にして、質問に答えてください。

【コンテキスト】
{context_text}

【質問】
{query}

【回答】
"""

        logger.debug(f"RAG prompt length: {len(full_prompt)} chars")

        return self.generate(
            prompt=full_prompt,
            system_prompt=system_prompt
        )

    def _generate_mock_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        モックレスポンス生成（APIキー未設定時）

        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト

        Returns:
            モック回答文字列
        """
        return (
            f"[MOCK RESPONSE]\n\n"
            f"これはモックレスポンスです。実際のLLM APIキーが設定されていません。\n\n"
            f"受信したプロンプト（最初の100文字）:\n"
            f"{prompt[:100]}...\n\n"
            f"本番環境では、ANTHROPIC_API_KEYまたはOPENAI_API_KEYを設定してください。"
        )

    def get_token_usage(self) -> Dict[str, int]:
        """
        トークン使用量取得

        Returns:
            {"total": 100, "prompt": 50, "completion": 50}
        """
        return {
            "total": self.token_callback.total_tokens,
            "prompt": self.token_callback.prompt_tokens,
            "completion": self.token_callback.completion_tokens
        }

    def reset_token_counter(self):
        """トークンカウンターリセット"""
        self.token_callback.total_tokens = 0
        self.token_callback.prompt_tokens = 0
        self.token_callback.completion_tokens = 0


# シングルトンインスタンス（オプション）
_llm_service_instance: Optional[LLMService] = None


def get_llm_service(
    provider: str = "anthropic",
    force_new: bool = False
) -> LLMService:
    """
    LLMサービスインスタンス取得（シングルトン）

    Args:
        provider: "anthropic" or "openai"
        force_new: 強制的に新規インスタンス作成

    Returns:
        LLMServiceインスタンス
    """
    global _llm_service_instance

    if force_new or _llm_service_instance is None:
        _llm_service_instance = LLMService(provider=provider)

    return _llm_service_instance


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Anthropic (Claude) テスト
    try:
        llm = LLMService(provider="anthropic")
        result = llm.generate("Hello, how are you?")
        print(f"Response: {result['content']}")
        print(f"Tokens: {result['tokens']}")
    except Exception as e:
        print(f"Error: {e}")

    # RAGテスト
    try:
        llm = LLMService(provider="anthropic")
        result = llm.generate_with_context(
            query="What is Python?",
            context_documents=[
                "Python is a high-level programming language.",
                "Python was created by Guido van Rossum in 1991."
            ]
        )
        print(f"\nRAG Response: {result['content']}")
    except Exception as e:
        print(f"RAG Error: {e}")
