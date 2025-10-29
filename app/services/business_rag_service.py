"""
Business RAG Service

Handles business document upload, processing, and querying with pgvector
Supports PDF, DOCX, TXT files with automatic text extraction and chunking
"""
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import io

from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.models.biz_file import BizFile
from app.models.biz_card import BizCard
from app.services.embedding_service import get_embedding_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class BusinessRAGService:
    """Business RAG Service for document management and querying"""

    # Supported file types
    SUPPORTED_MIMETYPES = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/plain": ".txt",
    }

    # Chunking configuration
    DEFAULT_CHUNK_SIZE = 500  # characters
    DEFAULT_CHUNK_OVERLAP = 100  # characters

    def __init__(
        self,
        db: Session,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        mock_mode: bool = False
    ):
        """
        Initialize Business RAG Service

        Args:
            db: Database session
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            mock_mode: Use mock mode for testing
        """
        self.db = db
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.mock_mode = mock_mode

        # Initialize embedding service
        if not mock_mode:
            self.embedding_service = get_embedding_service()
        else:
            self.embedding_service = None
            logger.info("Business RAG Service initialized in MOCK mode")

    def upload_document(
        self,
        filename: str,
        file_content: bytes,
        mime_type: str,
        tags: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        auto_index: bool = True
    ) -> Dict[str, Any]:
        """
        Upload and process business document

        Args:
            filename: Original filename
            file_content: File binary content
            mime_type: MIME type
            tags: Optional tags for categorization
            user_id: Optional user ID for access control
            auto_index: Automatically create vector index

        Returns:
            dict: {"file_id": int, "filename": str, "chunks_created": int, "status": str}
        """
        try:
            # Validate file type
            if mime_type not in self.SUPPORTED_MIMETYPES:
                raise ValueError(
                    f"Unsupported file type: {mime_type}. "
                    f"Supported: {list(self.SUPPORTED_MIMETYPES.keys())}"
                )

            # Create BizFile record
            biz_file = BizFile(
                filename=filename,
                file_blob=file_content,
                file_size=len(file_content),
                mime_type=mime_type,
                tags=tags or []
            )

            self.db.add(biz_file)
            self.db.flush()  # Get file ID

            logger.info(
                f"Uploaded file {filename} (ID: {biz_file.id}, size: {len(file_content)} bytes)"
            )

            chunks_created = 0

            # Auto-index if requested
            if auto_index:
                chunks_created = self._index_document(biz_file)

            self.db.commit()

            return {
                "file_id": biz_file.id,
                "filename": filename,
                "file_size": len(file_content),
                "mime_type": mime_type,
                "chunks_created": chunks_created,
                "status": "indexed" if auto_index else "uploaded",
                "uploaded_at": biz_file.uploaded_at.isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upload document {filename}: {e}", exc_info=True)
            raise

    def _index_document(self, biz_file: BizFile) -> int:
        """
        Index document by extracting text, chunking, and creating embeddings

        Args:
            biz_file: BizFile object

        Returns:
            int: Number of chunks created
        """
        try:
            # Extract text from file
            text = self._extract_text(biz_file.file_blob, biz_file.mime_type)

            if not text or not text.strip():
                logger.warning(f"No text extracted from file {biz_file.id}")
                return 0

            # Chunk text
            chunks = self._chunk_text(text)
            logger.info(f"Created {len(chunks)} chunks for file {biz_file.id}")

            # Create embeddings and store
            chunks_created = 0
            for idx, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue

                # Generate embedding
                if not self.mock_mode:
                    embedding = self.embedding_service.generate_embedding(chunk)
                else:
                    # Mock embedding
                    embedding = [0.0] * 384

                # Create BizCard record
                biz_card = BizCard(
                    file_id=biz_file.id,
                    content=chunk,
                    vector_embedding=embedding,
                    score=0.0  # Initial score
                )

                self.db.add(biz_card)
                chunks_created += 1

                if (idx + 1) % 10 == 0:
                    self.db.flush()  # Periodic flush for large documents
                    logger.debug(f"Indexed {idx + 1}/{len(chunks)} chunks")

            self.db.flush()
            logger.info(f"Successfully indexed {chunks_created} chunks for file {biz_file.id}")

            return chunks_created

        except Exception as e:
            logger.error(f"Failed to index file {biz_file.id}: {e}", exc_info=True)
            raise

    def _extract_text(self, file_content: bytes, mime_type: str) -> str:
        """
        Extract text from file based on MIME type

        Args:
            file_content: File binary content
            mime_type: MIME type

        Returns:
            str: Extracted text
        """
        try:
            if mime_type == "text/plain":
                # Plain text
                return file_content.decode("utf-8")

            elif mime_type == "application/pdf":
                # PDF extraction
                return self._extract_pdf_text(file_content)

            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                # DOCX extraction
                return self._extract_docx_text(file_content)

            else:
                raise ValueError(f"Unsupported MIME type for extraction: {mime_type}")

        except Exception as e:
            logger.error(f"Text extraction failed: {e}", exc_info=True)
            raise

    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            import PyPDF2

            pdf_file = io.BytesIO(file_content)
            reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text())

            return "\n\n".join(text_parts)

        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            raise
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}", exc_info=True)
            raise

    def _extract_docx_text(self, file_content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            import docx

            docx_file = io.BytesIO(file_content)
            doc = docx.Document(docx_file)

            text_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            return "\n\n".join(text_parts)

        except ImportError:
            logger.error("python-docx not installed. Install with: pip install python-docx")
            raise
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}", exc_info=True)
            raise

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Input text

        Returns:
            List[str]: Text chunks
        """
        if not text or len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for delim in ["。", ".", "！", "!", "？", "?", "\n\n"]:
                    last_delim = text.rfind(delim, start, end)
                    if last_delim > start:
                        end = last_delim + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move to next chunk with overlap
            start = end - self.chunk_overlap if end < len(text) else end

        return chunks

    def query_documents(
        self,
        query: str,
        top_k: int = 5,
        file_ids: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        similarity_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Query business knowledge base

        Args:
            query: Search query
            top_k: Number of results to return
            file_ids: Optional filter by file IDs
            tags: Optional filter by tags
            user_id: Optional user ID for access control
            similarity_threshold: Minimum similarity score

        Returns:
            dict: Query results with context and metadata
        """
        try:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")

            # Generate query embedding
            if not self.mock_mode:
                query_embedding = self.embedding_service.generate_embedding(query)
            else:
                # Mock mode
                query_embedding = [0.0] * 384

            # Build query
            query_obj = self.db.query(
                BizCard.id,
                BizCard.content,
                BizCard.file_id,
                BizCard.indexed_at,
                BizFile.filename,
                BizFile.tags,
                # Calculate similarity using pgvector
                text(
                    f"1 - (biz_cards.vector_embedding <=> "
                    f"CAST(ARRAY{query_embedding} AS vector(384))) AS similarity"
                )
            ).join(BizFile, BizCard.file_id == BizFile.id)

            # Apply filters
            if file_ids:
                query_obj = query_obj.filter(BizCard.file_id.in_(file_ids))

            if tags:
                query_obj = query_obj.filter(BizFile.tags.overlap(tags))

            # Order by similarity and limit
            if not self.mock_mode:
                query_obj = query_obj.order_by(text("similarity DESC"))
            else:
                # Mock mode: use random ordering
                query_obj = query_obj.order_by(BizCard.id.desc())

            query_obj = query_obj.limit(top_k * 2)  # Get more for filtering

            results = query_obj.all()

            # Filter by similarity threshold
            filtered_results = []
            for result in results:
                similarity = result.similarity if hasattr(result, 'similarity') else 0.0

                if similarity >= similarity_threshold or self.mock_mode:
                    filtered_results.append({
                        "card_id": result.id,
                        "content": result.content,
                        "file_id": result.file_id,
                        "filename": result.filename,
                        "tags": result.tags or [],
                        "similarity": similarity,
                        "indexed_at": result.indexed_at.isoformat()
                    })

                if len(filtered_results) >= top_k:
                    break

            logger.info(
                f"Query '{query[:50]}...' returned {len(filtered_results)} results"
            )

            # Build context for LLM
            context_parts = []
            for idx, result in enumerate(filtered_results, 1):
                context_parts.append(
                    f"[{idx}] ({result['filename']}, similarity: {result['similarity']:.2f})\n"
                    f"{result['content']}\n"
                )

            context = "\n---\n".join(context_parts)

            return {
                "query": query,
                "results_count": len(filtered_results),
                "results": filtered_results,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            raise

    def list_documents(
        self,
        user_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List user's documents

        Args:
            user_id: Optional user ID filter
            tags: Optional tags filter
            limit: Max results
            offset: Pagination offset

        Returns:
            dict: Document list with metadata
        """
        try:
            query = self.db.query(BizFile)

            # Apply filters
            if tags:
                query = query.filter(BizFile.tags.overlap(tags))

            # Count total
            total = query.count()

            # Paginate
            files = query.order_by(BizFile.uploaded_at.desc()).limit(limit).offset(offset).all()

            # Build response
            documents = []
            for file in files:
                # Count chunks
                chunk_count = self.db.query(func.count(BizCard.id)).filter(
                    BizCard.file_id == file.id
                ).scalar()

                documents.append({
                    "file_id": file.id,
                    "filename": file.filename,
                    "file_size": file.file_size,
                    "mime_type": file.mime_type,
                    "tags": file.tags or [],
                    "chunk_count": chunk_count,
                    "uploaded_at": file.uploaded_at.isoformat()
                })

            return {
                "total": total,
                "count": len(documents),
                "limit": limit,
                "offset": offset,
                "documents": documents
            }

        except Exception as e:
            logger.error(f"Failed to list documents: {e}", exc_info=True)
            raise

    def delete_document(self, file_id: int, user_id: Optional[int] = None) -> bool:
        """
        Delete document and associated chunks

        Args:
            file_id: File ID to delete
            user_id: Optional user ID for access control

        Returns:
            bool: True if deleted
        """
        try:
            file = self.db.query(BizFile).filter(BizFile.id == file_id).first()

            if not file:
                logger.warning(f"File {file_id} not found")
                return False

            # Delete file (cascade will delete BizCards)
            self.db.delete(file)
            self.db.commit()

            logger.info(f"Deleted file {file_id} ({file.filename})")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete file {file_id}: {e}", exc_info=True)
            raise

    def reindex_document(self, file_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Reindex document (delete old chunks and create new ones)

        Args:
            file_id: File ID to reindex
            user_id: Optional user ID for access control

        Returns:
            dict: Reindex results
        """
        try:
            file = self.db.query(BizFile).filter(BizFile.id == file_id).first()

            if not file:
                raise ValueError(f"File {file_id} not found")

            # Delete existing chunks
            deleted_count = self.db.query(BizCard).filter(
                BizCard.file_id == file_id
            ).delete(synchronize_session=False)

            self.db.flush()

            logger.info(f"Deleted {deleted_count} old chunks for file {file_id}")

            # Reindex
            chunks_created = self._index_document(file)

            self.db.commit()

            return {
                "file_id": file_id,
                "filename": file.filename,
                "deleted_chunks": deleted_count,
                "created_chunks": chunks_created,
                "status": "reindexed",
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reindex file {file_id}: {e}", exc_info=True)
            raise

    def get_document_stats(self, file_id: int) -> Dict[str, Any]:
        """Get document statistics"""
        try:
            file = self.db.query(BizFile).filter(BizFile.id == file_id).first()

            if not file:
                raise ValueError(f"File {file_id} not found")

            chunk_count = self.db.query(func.count(BizCard.id)).filter(
                BizCard.file_id == file_id
            ).scalar()

            avg_score = self.db.query(func.avg(BizCard.score)).filter(
                BizCard.file_id == file_id
            ).scalar()

            return {
                "file_id": file_id,
                "filename": file.filename,
                "file_size": file.file_size,
                "mime_type": file.mime_type,
                "tags": file.tags or [],
                "chunk_count": chunk_count,
                "average_score": float(avg_score) if avg_score else 0.0,
                "uploaded_at": file.uploaded_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get stats for file {file_id}: {e}", exc_info=True)
            raise


def get_business_rag_service(db: Session, mock_mode: bool = False) -> BusinessRAGService:
    """
    Factory function for BusinessRAGService

    Args:
        db: Database session
        mock_mode: Use mock mode

    Returns:
        BusinessRAGService instance
    """
    return BusinessRAGService(db=db, mock_mode=mock_mode)
