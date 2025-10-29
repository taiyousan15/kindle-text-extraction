"""
Embedding Service for RAG

sentence-transformers統合、日本語対応、ベクトル生成
"""
import logging
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from functools import lru_cache
import hashlib
import json

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embeddingサービス（sentence-transformers統合）"""

    # サポートされているモデル
    SUPPORTED_MODELS = {
        "multilingual-e5-large": "intfloat/multilingual-e5-large",  # 384次元、多言語対応
        "japanese-bert": "cl-tohoku/bert-base-japanese-v3",  # 768次元、日本語特化
        "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",  # 384次元、英語
    }

    def __init__(
        self,
        model_name: str = "multilingual-e5-large",
        cache_size: int = 1000,
        device: Optional[str] = None
    ):
        """
        Embeddingサービス初期化

        Args:
            model_name: モデル名（SUPPORTED_MODELSのキー）
            cache_size: キャッシュサイズ
            device: デバイス（"cuda", "cpu", None=自動選択）
        """
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model_name}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )

        self.model_name = model_name
        self.model_path = self.SUPPORTED_MODELS[model_name]
        self.cache_size = cache_size
        self._cache: Dict[str, List[float]] = {}

        logger.info(f"Loading embedding model: {self.model_path}")

        try:
            # モデルロード
            self.model = SentenceTransformer(self.model_path, device=device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()

            logger.info(
                f"Embedding model loaded successfully. "
                f"Dimension: {self.embedding_dim}, Device: {self.model.device}"
            )

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """
        単一テキストのEmbedding生成

        Args:
            text: 入力テキスト
            use_cache: キャッシュ使用有無

        Returns:
            Embeddingベクトル（List[float]）
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.embedding_dim

        # キャッシュチェック
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return self._cache[cache_key]

        try:
            # Embedding生成
            logger.debug(f"Generating embedding for text: {text[:50]}...")
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True  # コサイン類似度用に正規化
            )

            # numpy配列 -> list変換
            embedding_list = embedding.tolist()

            # キャッシュ保存
            if use_cache:
                self._add_to_cache(cache_key, embedding_list)

            return embedding_list

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32,
        use_cache: bool = True,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        複数テキストのEmbedding一括生成

        Args:
            texts: 入力テキストリスト
            batch_size: バッチサイズ
            use_cache: キャッシュ使用有無
            show_progress: プログレスバー表示

        Returns:
            Embeddingベクトルリスト
        """
        if not texts:
            logger.warning("Empty texts list provided")
            return []

        embeddings = []
        texts_to_encode = []
        indices_to_encode = []

        # キャッシュチェック
        for i, text in enumerate(texts):
            if not text or not text.strip():
                embeddings.append([0.0] * self.embedding_dim)
                continue

            if use_cache:
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    embeddings.append(self._cache[cache_key])
                    continue

            # キャッシュミス → エンコード対象
            texts_to_encode.append(text)
            indices_to_encode.append(i)

        # バッチエンコード
        if texts_to_encode:
            try:
                logger.info(f"Batch encoding {len(texts_to_encode)} texts...")

                batch_embeddings = self.model.encode(
                    texts_to_encode,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=show_progress
                )

                # 結果を配列に格納
                for idx, embedding in zip(indices_to_encode, batch_embeddings):
                    embedding_list = embedding.tolist()
                    embeddings.insert(idx, embedding_list)

                    # キャッシュ保存
                    if use_cache:
                        cache_key = self._get_cache_key(texts[idx])
                        self._add_to_cache(cache_key, embedding_list)

                logger.info(f"Batch encoding completed. Total: {len(embeddings)}")

            except Exception as e:
                logger.error(f"Batch encoding failed: {e}")
                raise

        return embeddings

    def similarity(
        self,
        text1: str,
        text2: str,
        use_cache: bool = True
    ) -> float:
        """
        2つのテキスト間のコサイン類似度計算

        Args:
            text1: テキスト1
            text2: テキスト2
            use_cache: キャッシュ使用有無

        Returns:
            コサイン類似度（0.0-1.0）
        """
        emb1 = np.array(self.generate_embedding(text1, use_cache=use_cache))
        emb2 = np.array(self.generate_embedding(text2, use_cache=use_cache))

        # コサイン類似度（既に正規化済みなので内積で計算可能）
        similarity = np.dot(emb1, emb2)

        return float(similarity)

    def most_similar(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        クエリに最も類似するテキストをランキング

        Args:
            query: クエリテキスト
            candidates: 候補テキストリスト
            top_k: 上位K件を返す
            use_cache: キャッシュ使用有無

        Returns:
            [{"text": str, "score": float, "index": int}, ...]
        """
        if not candidates:
            return []

        # クエリEmbedding
        query_emb = np.array(self.generate_embedding(query, use_cache=use_cache))

        # 候補Embeddings
        candidate_embs = np.array(
            self.generate_embeddings(candidates, use_cache=use_cache)
        )

        # コサイン類似度計算（行列積）
        similarities = np.dot(candidate_embs, query_emb)

        # 上位K件取得
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = [
            {
                "text": candidates[idx],
                "score": float(similarities[idx]),
                "index": int(idx)
            }
            for idx in top_indices
        ]

        logger.debug(f"Most similar search: query='{query[:50]}...', top_k={top_k}")

        return results

    def _get_cache_key(self, text: str) -> str:
        """
        キャッシュキー生成（テキストのハッシュ）

        Args:
            text: テキスト

        Returns:
            ハッシュキー
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _add_to_cache(self, key: str, embedding: List[float]):
        """
        キャッシュに追加（LRU戦略）

        Args:
            key: キャッシュキー
            embedding: Embeddingベクトル
        """
        if len(self._cache) >= self.cache_size:
            # 最も古いエントリを削除（簡易LRU）
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = embedding

    def clear_cache(self):
        """キャッシュクリア"""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_size(self) -> int:
        """キャッシュサイズ取得"""
        return len(self._cache)

    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報取得

        Returns:
            {"model_name": str, "embedding_dim": int, "device": str, ...}
        """
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "embedding_dim": self.embedding_dim,
            "device": str(self.model.device),
            "cache_size": len(self._cache),
            "max_cache_size": self.cache_size
        }


# シングルトンインスタンス
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service(
    model_name: str = "multilingual-e5-large",
    force_new: bool = False
) -> EmbeddingService:
    """
    Embeddingサービスインスタンス取得（シングルトン）

    Args:
        model_name: モデル名
        force_new: 強制的に新規インスタンス作成

    Returns:
        EmbeddingServiceインスタンス
    """
    global _embedding_service_instance

    if force_new or _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService(model_name=model_name)

    return _embedding_service_instance


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # サービス初期化
    embedding_service = EmbeddingService(model_name="multilingual-e5-large")

    # 単一Embedding生成
    text = "これはテストです。"
    embedding = embedding_service.generate_embedding(text)
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 10 values: {embedding[:10]}")

    # バッチEmbedding生成
    texts = [
        "Python is a programming language.",
        "Pythonはプログラミング言語です。",
        "I love machine learning.",
    ]
    embeddings = embedding_service.generate_embeddings(texts)
    print(f"\nBatch embeddings: {len(embeddings)} x {len(embeddings[0])}")

    # 類似度計算
    similarity = embedding_service.similarity(texts[0], texts[1])
    print(f"\nSimilarity between text1 and text2: {similarity:.4f}")

    # 最も類似するテキスト検索
    query = "機械学習が好きです"
    results = embedding_service.most_similar(query, texts, top_k=2)
    print(f"\nMost similar to '{query}':")
    for result in results:
        print(f"  - {result['text'][:50]}: {result['score']:.4f}")

    # モデル情報
    info = embedding_service.get_model_info()
    print(f"\nModel info: {json.dumps(info, indent=2)}")
