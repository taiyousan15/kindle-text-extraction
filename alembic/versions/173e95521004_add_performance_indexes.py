"""add_performance_indexes

Revision ID: 173e95521004
Revises: 5aa636e83b69
Create Date: 2025-10-29 14:48:25.161172

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '173e95521004'
down_revision = '5aa636e83b69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance-critical indexes for frequently queried columns"""

    # ========================================
    # 1. USERS TABLE INDEXES
    # ========================================
    # Index for filtering active users (e.g., WHERE is_active=true)
    op.create_index('idx_users_is_active', 'users', ['is_active'])

    # ========================================
    # 2. JOBS TABLE INDEXES
    # ========================================
    # Composite index for filtering jobs by user and status
    # Supports queries: WHERE user_id=X AND status='pending'
    op.create_index('idx_jobs_user_status', 'jobs', ['user_id', 'status'])

    # Index for sorting jobs by creation time (DESC for recent-first)
    # Supports queries: ORDER BY created_at DESC
    op.create_index('idx_jobs_created_at', 'jobs', ['created_at'],
                    postgresql_ops={'created_at': 'DESC'})

    # ========================================
    # 3. OCR_RESULTS TABLE INDEXES
    # ========================================
    # Index for sorting OCR results by creation time
    # Supports queries: ORDER BY created_at DESC
    op.create_index('idx_ocr_created_at', 'ocr_results', ['created_at'],
                    postgresql_ops={'created_at': 'DESC'})

    # ========================================
    # 4. SUMMARIES TABLE INDEXES
    # ========================================
    # Index for sorting summaries by creation time
    op.create_index('idx_summaries_created_at', 'summaries', ['created_at'],
                    postgresql_ops={'created_at': 'DESC'})

    # Index for filtering summaries by format (e.g., markdown, pdf)
    op.create_index('idx_summaries_format', 'summaries', ['format'])

    # Index for filtering summaries by granularity (e.g., detailed, brief)
    op.create_index('idx_summaries_granularity', 'summaries', ['granularity'])

    # ========================================
    # 5. KNOWLEDGE TABLE INDEXES
    # ========================================
    # Index for sorting knowledge entries by creation time
    op.create_index('idx_knowledge_created_at', 'knowledge', ['created_at'],
                    postgresql_ops={'created_at': 'DESC'})


def downgrade() -> None:
    """Remove performance indexes"""

    # Drop indexes in reverse order
    op.drop_index('idx_knowledge_created_at', table_name='knowledge')
    op.drop_index('idx_summaries_granularity', table_name='summaries')
    op.drop_index('idx_summaries_format', table_name='summaries')
    op.drop_index('idx_summaries_created_at', table_name='summaries')
    op.drop_index('idx_ocr_created_at', table_name='ocr_results')
    op.drop_index('idx_jobs_created_at', table_name='jobs')
    op.drop_index('idx_jobs_user_status', table_name='jobs')
    op.drop_index('idx_users_is_active', table_name='users')
