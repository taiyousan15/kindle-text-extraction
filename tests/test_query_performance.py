"""
Test Query Performance with EXPLAIN ANALYZE

This script tests common query patterns to verify that indexes are being used
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def explain_query(engine, query_name, query):
    """Execute EXPLAIN ANALYZE and display results"""

    with engine.connect() as conn:
        result = conn.execute(text(f"EXPLAIN ANALYZE {query}"))

        print(f"\n{'='*100}")
        print(f"QUERY: {query_name}")
        print(f"{'='*100}")
        print(f"\nSQL: {query}\n")
        print("Execution Plan:")
        print("-" * 100)

        for row in result:
            print(row[0])

        print("-" * 100)


def test_performance():
    """Test various query patterns"""

    engine = create_engine(settings.DATABASE_URL)

    # Test queries that should use new indexes
    test_queries = {
        "1. Filter active users": """
            SELECT * FROM users WHERE is_active = true LIMIT 10;
        """,

        "2. Get user's jobs filtered by status": """
            SELECT * FROM jobs WHERE user_id = 1 AND status = 'pending';
        """,

        "3. Get recent jobs sorted by creation": """
            SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;
        """,

        "4. Get recent OCR results": """
            SELECT * FROM ocr_results ORDER BY created_at DESC LIMIT 10;
        """,

        "5. Get recent summaries by format": """
            SELECT * FROM summaries WHERE format = 'markdown' ORDER BY created_at DESC LIMIT 10;
        """,

        "6. Get summaries by granularity": """
            SELECT * FROM summaries WHERE granularity = 'detailed' LIMIT 10;
        """,

        "7. Get recent knowledge entries": """
            SELECT * FROM knowledge ORDER BY created_at DESC LIMIT 10;
        """,

        "8. Complex job query (composite index)": """
            SELECT j.*, COUNT(o.id) as ocr_count
            FROM jobs j
            LEFT JOIN ocr_results o ON j.id = o.job_id
            WHERE j.user_id = 1 AND j.status IN ('pending', 'processing')
            GROUP BY j.id
            ORDER BY j.created_at DESC
            LIMIT 10;
        """,
    }

    print("\n" + "="*100)
    print("QUERY PERFORMANCE ANALYSIS")
    print("="*100)
    print("\nLook for 'Index Scan' or 'Index Only Scan' - these indicate indexes are being used")
    print("'Seq Scan' (Sequential Scan) indicates a full table scan without indexes")
    print("="*100)

    for query_name, query in test_queries.items():
        try:
            explain_query(engine, query_name, query.strip())
        except Exception as e:
            print(f"\nError executing query '{query_name}': {e}")

    print("\n" + "="*100)
    print("PERFORMANCE TEST COMPLETE")
    print("="*100 + "\n")


def get_index_sizes():
    """Get the size of each index"""

    engine = create_engine(settings.DATABASE_URL)

    query = text("""
        SELECT
            schemaname,
            relname as tablename,
            indexrelname as indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY pg_relation_size(indexrelid) DESC;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)

        print("\n" + "="*100)
        print("INDEX SIZES")
        print("="*100 + "\n")

        print(f"{'Table':<20} {'Index Name':<40} {'Size':<15}")
        print("-" * 100)

        for row in result:
            print(f"{row.tablename:<20} {row.indexname:<40} {row.index_size:<15}")

        print("\n" + "="*100 + "\n")


def get_database_stats():
    """Get overall database and table statistics"""

    engine = create_engine(settings.DATABASE_URL)

    query = text("""
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)

        print("\n" + "="*100)
        print("TABLE AND INDEX STORAGE BREAKDOWN")
        print("="*100 + "\n")

        print(f"{'Table':<20} {'Total Size':<15} {'Table Size':<15} {'Indexes Size':<15}")
        print("-" * 100)

        for row in result:
            print(f"{row.tablename:<20} {row.total_size:<15} {row.table_size:<15} {row.indexes_size:<15}")

        print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    # Test query performance
    test_performance()

    # Show index sizes
    get_index_sizes()

    # Show database statistics
    get_database_stats()
