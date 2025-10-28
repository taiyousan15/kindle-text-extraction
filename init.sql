-- Kindle OCR Database Initialization Script
-- Automatically executed when PostgreSQL container starts for the first time

-- Install pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial user (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kindle_user') THEN
        CREATE ROLE kindle_user WITH LOGIN PASSWORD 'kindle_password';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE kindle_ocr TO kindle_user;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE '✅ pgvector extension installed successfully';
    RAISE NOTICE '✅ User kindle_user created/verified';
    RAISE NOTICE '✅ Database kindle_ocr initialized';
END
$$;
