"""
Verify Database Indexes

Script to check all indexes created in the database
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

def verify_indexes():
    """Query and display all indexes in the database"""

    engine = create_engine(settings.DATABASE_URL)

    query = text("""
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """)

    with engine.connect() as conn:
        result = conn.execute(query)

        print("\n" + "="*100)
        print("DATABASE INDEXES")
        print("="*100 + "\n")

        current_table = None
        for row in result:
            if current_table != row.tablename:
                current_table = row.tablename
                print(f"\n{'='*100}")
                print(f"TABLE: {current_table}")
                print(f"{'='*100}")

            print(f"\nIndex: {row.indexname}")
            print(f"Definition: {row.indexdef}")

        print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    verify_indexes()
