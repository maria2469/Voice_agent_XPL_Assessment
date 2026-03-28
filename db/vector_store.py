from datetime import datetime, timezone
from langchain_postgres import PGVectorStore
from db.pg_engine import pg_engine
from services.embedding import get_embedding_service

TABLE_NAME = "sunmarke_firecrawl_docs"

METADATA_COLUMNS = [
    "url",
    "title",
    "description",
    "category",
    "language",
    "crawled_at",
]

def _ensure_datetime(metadata: dict) -> dict:
    """
    Ensure 'crawled_at' is always a datetime object.
    Accepts ISO strings or datetime objects.
    """
    crawled_at = metadata.get("crawled_at")
    if crawled_at:
        if isinstance(crawled_at, str):
            try:
                metadata["crawled_at"] = datetime.fromisoformat(crawled_at)
            except ValueError:
                # fallback if string is malformed
                metadata["crawled_at"] = datetime.now(timezone.utc)
        elif not isinstance(crawled_at, datetime):
            # fallback if unknown type
            metadata["crawled_at"] = datetime.now(timezone.utc)
    else:
        metadata["crawled_at"] = datetime.now(timezone.utc)
    return metadata

class SafePGVectorStore(PGVectorStore):
    """
    Overrides add_documents to ensure all datetime metadata is correct
    """
    def add_documents(self, documents, **kwargs):
        for doc in documents:
            doc.metadata = _ensure_datetime(doc.metadata)
        super().add_documents(documents, **kwargs)

def get_vector_store_sync() -> PGVectorStore:
    print("🔌  Creating PGVectorStore (sync)...")
    store = SafePGVectorStore.create_sync(
        engine=pg_engine,
        table_name=TABLE_NAME,
        embedding_service=get_embedding_service(),
        metadata_columns=METADATA_COLUMNS,
    )
    return store

async def get_vector_store() -> PGVectorStore:
    store = await SafePGVectorStore.create(
        engine=pg_engine,
        table_name=TABLE_NAME,
        embedding_service=get_embedding_service(),
        metadata_columns=METADATA_COLUMNS,
    )
    return store