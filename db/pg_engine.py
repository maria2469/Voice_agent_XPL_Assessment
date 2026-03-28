# db/pg_engine.py

from langchain_postgres import PGEngine
from core.config import settings

pg_engine = PGEngine.from_connection_string(
    settings.DATABASE_URL
)