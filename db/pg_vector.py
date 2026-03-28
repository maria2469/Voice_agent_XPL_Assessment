from langchain_core.vectorstores import PGVector
from langchain.embeddings import GoogleEmbeddingService  # or replace with GeminiEmbeddingService if you have Gemini API
from core.config import settings

TABLE_NAME = "sunmarke_docs"

def get_vector_store():
    """
    Returns a PGVector store instance aligned with LangChain docs.

    Features:
    - Add/delete documents
    - Similarity search
    - Metadata filtering
    """
    # Embedding model
    embedding_function = GoogleEmbeddingService(model="gemini-embedding-001", dimension=768)  # Replace with GeminiEmbeddingService() if using Gemini

    # PGVector initialization
    store = PGVector(
        connection_string=settings.DATABASE_URL,  # e.g., "postgresql+psycopg2://user:pass@host:port/db"
        embedding_function=embedding_function,
        collection_name=TABLE_NAME
    )
    return store