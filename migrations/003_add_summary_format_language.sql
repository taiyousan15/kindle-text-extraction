-- Migration 003: Add format and language columns to summaries table
-- Phase 3: Summary enhancements
-- Created: 2025-10-28

-- Add format column to store summary format type
ALTER TABLE summaries
ADD COLUMN IF NOT EXISTS format VARCHAR(50);

-- Add language column to store detected/specified language
ALTER TABLE summaries
ADD COLUMN IF NOT EXISTS language VARCHAR(10);

-- Add index on language for filtering
CREATE INDEX IF NOT EXISTS idx_summary_language ON summaries(language);

-- Add comment for documentation
COMMENT ON COLUMN summaries.format IS 'Summary format type: plain_text, bullet_points, structured';
COMMENT ON COLUMN summaries.language IS 'Summary language: ja (Japanese), en (English)';

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 003 completed: Added format and language columns to summaries table';
END
$$;
