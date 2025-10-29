"""
Vector Store Service for RAG

pgvector統合、ベクトル類似度検索
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func
from pgvector.sqlalchemy import Vector
import numpy as np

from app.models.biz_card import BizCard
from app.models.biz_file import BizFile
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStore:
    """ベクトルストアサービス（pgvector統合）"""

    def __init__(self, db: Session, embedding_service=None):
        """
        ベクトルストア初期化

        Args:
            db: データベースセッション
            embedding_service: Embeddingサービス（Noneの場合は自動取得）
        """
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        logger.debug("VectorStore initialized")

    def add_document(
        self,
        content: str,
        file_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        generate_embedding: bool = True
    ) -> BizCard:
        """
        ドキュメント追加

        Args:
            content: ドキュメント内容
            file_id: ファイルID
            metadata: メタデータ（将来の拡張用）
            generate_embedding: Embedding自動生成

        Returns:
            作成されたBizCardインスタンス
        """
        try:
            # Embedding生成
            embedding = None
            if generate_embedding:
                embedding = self.embedding_service.generate_embedding(content)
                logger.debug(f"Generated embedding for document: {content[:50]}...")

            # BizCard作成
            biz_card = BizCard(
                file_id=file_id,
                content=content,
                vector_embedding=embedding,
                score=None  # 初期スコアはNone
            )

            self.db.add(biz_card)
            self.db.commit()
            self.db.refresh(biz_card)

            logger.info(f"Document added: BizCard ID={biz_card.id}")
            return biz_card

        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            self.db.rollback()
            raise

    def add_documents(
        self,
        documents: List[str],
        file_id: int,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 32
    ) -> List[BizCard]:
        """
        複数ドキュメント一括追加

        Args:
            documents: ドキュメント内容リスト
            file_id: ファイルID
            metadatas: メタデータリスト
            batch_size: バッチサイズ

        Returns:
            作成されたBizCardインスタンスリスト
        """
        if not documents:
            logger.warning("Empty documents list provided")
            return []

        try:
            # バッチEmbedding生成
            logger.info(f"Generating embeddings for {len(documents)} documents...")
            embeddings = self.embedding_service.generate_embeddings(
                documents,
                batch_size=batch_size,
                show_progress=True
            )

            # BizCard一括作成
            biz_cards = []
            for i, (doc, emb) in enumerate(zip(documents, embeddings)):
                biz_card = BizCard(
                    file_id=file_id,
                    content=doc,
                    vector_embedding=emb,
                    score=None
                )
                biz_cards.append(biz_card)

            self.db.add_all(biz_cards)
            self.db.commit()

            logger.info(f"Added {len(biz_cards)} documents to vector store")
            return biz_cards

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            self.db.rollback()
            raise

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        score_threshold: Optional[float] = None,
        file_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        類似度検索（クエリテキストから）

        Args:
            query: クエリテキスト
            k: 取得件数
            score_threshold: スコア閾値（この値以上のみ返す）
            file_ids: 検索対象ファイルIDリスト（Noneの場合は全体検索）

        Returns:
            [
                {
                    "id": int,
                    "content": str,
                    "score": float,
                    "file_id": int,
                    "filename": str,
                    "distance": float
                },
                ...
            ]
        """
        try:
            # クエリEmbedding生成
            query_embedding = self.embedding_service.generate_embedding(query)

            # ベクトル検索実行
            return self.search_by_vector(
                vector=query_embedding,
                k=k,
                score_threshold=score_threshold,
                file_ids=file_ids
            )

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise

    def search_by_vector(
        self,
        vector: List[float],
        k: int = 5,
        score_threshold: Optional[float] = None,
        file_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        ベクトル直接検索

        Args:
            vector: クエリベクトル
            k: 取得件数
            score_threshold: スコア閾値
            file_ids: 検索対象ファイルIDリスト

        Returns:
            検索結果リスト（similarity_search()と同じ形式）
        """
        try:
            # pgvectorのコサイン距離演算子 (<=>)
            # 注意: pgvectorの<=>は距離なので、類似度は 1 - distance で計算
            query_vector = str(vector)

            # SQLクエリ構築
            sql = text("""
                SELECT
                    bc.id,
                    bc.content,
                    bc.score,
                    bc.file_id,
                    bf.filename,
                    (bc.vector_embedding <=> :query_vector) AS distance,
                    (1 - (bc.vector_embedding <=> :query_vector)) AS similarity
                FROM biz_cards bc
                JOIN biz_files bf ON bc.file_id = bf.id
                WHERE bc.vector_embedding IS NOT NULL
            """)

            # ファイルIDフィルター追加
            if file_ids:
                sql = text(str(sql) + " AND bc.file_id = ANY(:file_ids)")

            # スコア閾値フィルター（類似度）
            if score_threshold is not None:
                sql = text(
                    str(sql) + f" AND (1 - (bc.vector_embedding <=> :query_vector)) >= :score_threshold"
                )

            # ORDER BY, LIMIT追加
            sql = text(str(sql) + " ORDER BY distance ASC LIMIT :k")

            # パラメータ設定
            params = {
                "query_vector": query_vector,
                "k": k
            }
            if file_ids:
                params["file_ids"] = file_ids
            if score_threshold is not None:
                params["score_threshold"] = score_threshold

            # クエリ実行
            result = self.db.execute(sql, params)
            rows = result.fetchall()

            # 結果整形
            results = []
            for row in rows:
                results.append({
                    "id": row.id,
                    "content": row.content,
                    "score": row.score,
                    "file_id": row.file_id,
                    "filename": row.filename,
                    "distance": float(row.distance),
                    "similarity": float(row.similarity)
                })

            logger.info(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    def update_embedding(
        self,
        biz_card_id: int,
        new_content: Optional[str] = None
    ) -> BizCard:
        """
        Embedding更新

        Args:
            biz_card_id: BizCard ID
            new_content: 新しいコンテンツ（Noneの場合は既存のcontentから再生成）

        Returns:
            更新されたBizCard
        """
        try:
            # BizCard取得
            biz_card = self.db.query(BizCard).filter(BizCard.id == biz_card_id).first()

            if not biz_card:
                raise ValueError(f"BizCard not found: id={biz_card_id}")

            # コンテンツ更新
            if new_content:
                biz_card.content = new_content

            # Embedding再生成
            new_embedding = self.embedding_service.generate_embedding(biz_card.content)
            biz_card.vector_embedding = new_embedding

            self.db.commit()
            self.db.refresh(biz_card)

            logger.info(f"Embedding updated for BizCard ID={biz_card_id}")
            return biz_card

        except Exception as e:
            logger.error(f"Failed to update embedding: {e}")
            self.db.rollback()
            raise

    def delete_document(self, biz_card_id: int):
        """
        ドキュメント削除

        Args:
            biz_card_id: BizCard ID
        """
        try:
            biz_card = self.db.query(BizCard).filter(BizCard.id == biz_card_id).first()

            if not biz_card:
                raise ValueError(f"BizCard not found: id={biz_card_id}")

            self.db.delete(biz_card)
            self.db.commit()

            logger.info(f"Document deleted: BizCard ID={biz_card_id}")

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            self.db.rollback()
            raise

    def delete_documents_by_file(self, file_id: int):
        """
        ファイルに紐づく全ドキュメント削除

        Args:
            file_id: ファイルID
        """
        try:
            result = self.db.query(BizCard).filter(BizCard.file_id == file_id).delete()
            self.db.commit()

            logger.info(f"Deleted {result} documents for file_id={file_id}")

        except Exception as e:
            logger.error(f"Failed to delete documents by file: {e}")
            self.db.rollback()
            raise

    def get_document_count(self, file_id: Optional[int] = None) -> int:
        """
        ドキュメント数取得

        Args:
            file_id: ファイルID（Noneの場合は全体）

        Returns:
            ドキュメント数
        """
        try:
            query = self.db.query(BizCard)
            if file_id:
                query = query.filter(BizCard.file_id == file_id)

            count = query.count()
            return count

        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """
        ベクトルストア統計情報取得

        Returns:
            {
                "total_documents": int,
                "total_files": int,
                "documents_with_embeddings": int,
                "avg_embedding_dim": float
            }
        """
        try:
            total_documents = self.db.query(BizCard).count()
            total_files = self.db.query(BizFile).count()
            documents_with_embeddings = self.db.query(BizCard).filter(
                BizCard.vector_embedding.isnot(None)
            ).count()

            # 平均Embedding次元数（最初のドキュメントから取得）
            first_card = self.db.query(BizCard).filter(
                BizCard.vector_embedding.isnot(None)
            ).first()

            avg_dim = len(first_card.vector_embedding) if first_card else 0

            return {
                "total_documents": total_documents,
                "total_files": total_files,
                "documents_with_embeddings": documents_with_embeddings,
                "avg_embedding_dim": avg_dim,
                "embedding_coverage": (
                    documents_with_embeddings / total_documents
                    if total_documents > 0 else 0.0
                )
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise


# 使用例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from app.core.database import SessionLocal

    # セッション作成
    db = SessionLocal()

    try:
        # VectorStore初期化
        vector_store = VectorStore(db)

        # ドキュメント追加（仮想的なfile_id=1を使用）
        # 注意: 実際の使用時はBizFileを先に作成する必要があります
        doc = "これはテストドキュメントです。"
        # biz_card = vector_store.add_document(content=doc, file_id=1)
        # print(f"Added document: {biz_card.id}")

        # 類似度検索
        # results = vector_store.similarity_search("テスト", k=3)
        # for result in results:
        #     print(f"  - {result['content'][:50]}: {result['similarity']:.4f}")

        # 統計情報
        stats = vector_store.get_statistics()
        print(f"Vector store statistics: {stats}")

    finally:
        db.close()
