"""
Run once to create the PGVector table for Firecrawl.

Gemini text-embedding-004 outputs 768-dim vectors.
"""
from langchain_postgres import PGEngine, Column
from core.config import settings

TABLE_NAME = "sunmarke_firecrawl_1_docs"
VECTOR_SIZE = 1024

def main():
    engine = PGEngine.from_connection_string(url=settings.DATABASE_URL)

    engine.init_vectorstore_table(
        table_name = TABLE_NAME,
        vector_size = VECTOR_SIZE,
        metadata_columns = [
            Column("url",         "TEXT"),
            Column("title",       "TEXT"),
            Column("description", "TEXT"),
            Column("category",    "TEXT"),
            Column("language",    "TEXT"),
            Column("crawled_at",  "TIMESTAMP"),
        ],
        overwrite_existing = True,  # set True to reset table
    )
    print(f"✅  Table '{TABLE_NAME}' ready.")

if __name__ == "__main__":
    main()