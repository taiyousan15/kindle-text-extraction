"""
RAG Integration Tests

Embedding生成、ベクトル検索、RAGクエリのテスト
"""
import pytest
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.vector_store import VectorStore
from app.models.biz_file import BizFile
from app.models.biz_card import BizCard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Fixtures ====================

@pytest.fixture(scope="module")
def db_session():
    """テスト用DBセッション"""
    # テーブル作成
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def embedding_service():
    """Embeddingサービス"""
    return get_embedding_service(model_name="multilingual-e5-large")


@pytest.fixture(scope="module")
def llm_service():
    """LLMサービス"""
    return get_llm_service(provider="anthropic")


@pytest.fixture(scope="module")
def sample_biz_file(db_session):
    """サンプルBizFile作成"""
    # 既存のファイルをクリーンアップ
    db_session.query(BizCard).delete()
    db_session.query(BizFile).delete()
    db_session.commit()

    biz_file = BizFile(
        filename="test_document.txt",
        tags=["test", "rag"],
        file_blob=b"This is a test document",
        file_size=23,
        mime_type="text/plain"
    )
    db_session.add(biz_file)
    db_session.commit()
    db_session.refresh(biz_file)

    yield biz_file

    # クリーンアップ
    db_session.query(BizCard).filter(BizCard.file_id == biz_file.id).delete()
    db_session.delete(biz_file)
    db_session.commit()


# ==================== Embedding Tests ====================

def test_embedding_service_initialization(embedding_service):
    """Embeddingサービス初期化テスト"""
    assert embedding_service is not None
    assert embedding_service.embedding_dim == 384
    logger.info(f"Embedding service initialized: {embedding_service.get_model_info()}")


def test_generate_single_embedding(embedding_service):
    """単一Embedding生成テスト"""
    text = "これはテストです。"
    embedding = embedding_service.generate_embedding(text)

    assert isinstance(embedding, list)
    assert len(embedding) == 384
    assert all(isinstance(x, float) for x in embedding)

    logger.info(f"Generated embedding: dim={len(embedding)}, first 5 values: {embedding[:5]}")


def test_generate_batch_embeddings(embedding_service):
    """バッチEmbedding生成テスト"""
    texts = [
        "Python is a programming language.",
        "Pythonはプログラミング言語です。",
        "I love machine learning.",
        "機械学習が好きです。"
    ]

    embeddings = embedding_service.generate_embeddings(texts)

    assert len(embeddings) == len(texts)
    assert all(len(emb) == 384 for emb in embeddings)

    logger.info(f"Generated {len(embeddings)} embeddings")


def test_embedding_similarity(embedding_service):
    """Embedding類似度計算テスト"""
    text1 = "Python is a programming language."
    text2 = "Pythonはプログラミング言語です。"
    text3 = "I like cats."

    sim_12 = embedding_service.similarity(text1, text2)
    sim_13 = embedding_service.similarity(text1, text3)

    # 類似したテキストの方が高いスコア
    assert sim_12 > sim_13
    assert 0.0 <= sim_12 <= 1.0
    assert 0.0 <= sim_13 <= 1.0

    logger.info(f"Similarity(text1, text2): {sim_12:.4f}")
    logger.info(f"Similarity(text1, text3): {sim_13:.4f}")


def test_embedding_most_similar(embedding_service):
    """最も類似するテキスト検索テスト"""
    query = "機械学習について"
    candidates = [
        "Python is a programming language.",
        "機械学習はAIの一分野です。",
        "I like cats.",
        "ディープラーニングは機械学習の手法です。"
    ]

    results = embedding_service.most_similar(query, candidates, top_k=2)

    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]  # スコアの降順
    assert "機械学習" in results[0]["text"] or "ディープラーニング" in results[0]["text"]

    logger.info("Most similar results:")
    for result in results:
        logger.info(f"  - {result['text'][:50]}: {result['score']:.4f}")


def test_embedding_cache(embedding_service):
    """Embeddingキャッシュテスト"""
    text = "キャッシュテスト"

    # 初回生成
    embedding_service.clear_cache()
    assert embedding_service.get_cache_size() == 0

    emb1 = embedding_service.generate_embedding(text, use_cache=True)
    assert embedding_service.get_cache_size() == 1

    # キャッシュヒット
    emb2 = embedding_service.generate_embedding(text, use_cache=True)
    assert embedding_service.get_cache_size() == 1
    assert emb1 == emb2  # 同じ結果

    logger.info(f"Cache hit successful: size={embedding_service.get_cache_size()}")


# ==================== Vector Store Tests ====================

def test_vector_store_add_document(db_session, sample_biz_file, embedding_service):
    """ドキュメント追加テスト"""
    vector_store = VectorStore(db_session, embedding_service)

    doc_content = "これはベクトルストアのテストドキュメントです。"
    biz_card = vector_store.add_document(
        content=doc_content,
        file_id=sample_biz_file.id
    )

    assert biz_card.id is not None
    assert biz_card.content == doc_content
    assert biz_card.vector_embedding is not None
    assert len(biz_card.vector_embedding) == 384

    logger.info(f"Document added: BizCard ID={biz_card.id}")


def test_vector_store_add_documents_batch(db_session, sample_biz_file, embedding_service):
    """バッチドキュメント追加テスト"""
    vector_store = VectorStore(db_session, embedding_service)

    documents = [
        "Pythonは高水準プログラミング言語です。",
        "Pythonは読みやすく書きやすいです。",
        "Pythonは機械学習でよく使われます。"
    ]

    biz_cards = vector_store.add_documents(
        documents=documents,
        file_id=sample_biz_file.id
    )

    assert len(biz_cards) == len(documents)
    assert all(card.vector_embedding is not None for card in biz_cards)

    logger.info(f"Added {len(biz_cards)} documents in batch")


def test_vector_store_similarity_search(db_session, sample_biz_file, embedding_service):
    """ベクトル類似度検索テスト"""
    vector_store = VectorStore(db_session, embedding_service)

    # テストデータ追加
    documents = [
        "Pythonは機械学習に最適です。",
        "JavaScriptはWeb開発に使われます。",
        "Pythonはデータサイエンスで人気です。"
    ]
    vector_store.add_documents(documents, file_id=sample_biz_file.id)

    # 検索
    query = "機械学習に使える言語は？"
    results = vector_store.similarity_search(query, k=2)

    assert len(results) <= 2
    if results:
        assert "similarity" in results[0]
        assert "content" in results[0]
        assert results[0]["similarity"] <= 1.0

        logger.info(f"Search results for '{query}':")
        for result in results:
            logger.info(f"  - {result['content'][:50]}: {result['similarity']:.4f}")


def test_vector_store_statistics(db_session, embedding_service):
    """ベクトルストア統計テスト"""
    vector_store = VectorStore(db_session, embedding_service)

    stats = vector_store.get_statistics()

    assert "total_documents" in stats
    assert "total_files" in stats
    assert "documents_with_embeddings" in stats
    assert "embedding_coverage" in stats

    logger.info(f"Vector store statistics: {stats}")


# ==================== LLM Tests ====================

def test_llm_service_initialization(llm_service):
    """LLMサービス初期化テスト"""
    assert llm_service is not None
    logger.info(f"LLM service initialized: provider={llm_service.provider}, mock={llm_service.is_mock}")


def test_llm_generate(llm_service):
    """LLM生成テスト"""
    prompt = "Hello, how are you?"

    result = llm_service.generate(prompt)

    assert "content" in result
    assert "tokens" in result
    assert "model" in result
    assert "is_mock" in result
    assert isinstance(result["content"], str)

    logger.info(f"LLM response: {result['content'][:100]}...")
    logger.info(f"Tokens: {result['tokens']}, Mock: {result['is_mock']}")


def test_llm_generate_with_context(llm_service):
    """コンテキスト付きLLM生成テスト（RAG）"""
    query = "Pythonの特徴は？"
    context_documents = [
        "Pythonは高水準プログラミング言語です。",
        "Pythonは読みやすく書きやすい構文が特徴です。",
        "Pythonは機械学習やデータサイエンスで広く使われています。"
    ]

    result = llm_service.generate_with_context(
        query=query,
        context_documents=context_documents
    )

    assert "content" in result
    assert isinstance(result["content"], str)

    logger.info(f"RAG response: {result['content'][:200]}...")


# ==================== Integration Tests ====================

def test_rag_full_pipeline(db_session, sample_biz_file, embedding_service, llm_service):
    """RAGフルパイプライン統合テスト"""
    # 1. ドキュメント追加
    vector_store = VectorStore(db_session, embedding_service)

    documents = [
        "Pythonは1991年にGuido van Rossumによって作成されました。",
        "Pythonはインデントでブロックを表現します。",
        "Pythonは動的型付け言語です。",
        "Pythonは機械学習ライブラリが豊富です。"
    ]

    vector_store.add_documents(documents, file_id=sample_biz_file.id)

    # 2. 類似度検索
    query = "Pythonの作者は誰ですか？"
    search_results = vector_store.similarity_search(query, k=2)

    assert len(search_results) > 0
    logger.info(f"Found {len(search_results)} relevant documents")

    # 3. RAG生成
    context_docs = [result["content"] for result in search_results]
    rag_result = llm_service.generate_with_context(
        query=query,
        context_documents=context_docs
    )

    assert rag_result["content"]
    logger.info(f"RAG answer: {rag_result['content'][:200]}...")

    # 4. 統計確認
    stats = vector_store.get_statistics()
    assert stats["total_documents"] >= len(documents)


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
