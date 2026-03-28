# db/vector_store.py
from langchain_postgres.v2 import PGVectorStore
from db.pg_engine import pg_engine
from services.embedding import get_embedding_service

TABLE_NAME = "sunmarke_firecrawl_docs"  # your existing collection

def get_vector_store_sync():
    """
    Returns a synchronous PGVectorStore connected to the already stored vectors.
    No async embeddings are called.
    """
    embeddings = get_embedding_service()  # your LoopingHybridEmbedding instance

    store = PGVectorStore(
        engine=pg_engine,              # SQLAlchemy engine
        collection_name=TABLE_NAME,    # existing collection
        embedding_service=embeddings,  # sync embeddings
        use_async=False                # ⚡ FORCE sync mode
    )

    return store