"""
db/pg_engine.py
Shared PGEngine instance — import this everywhere instead of re-creating it.
"""
from langchain_postgres import PGEngine
from core.config import settings

# Sync engine (used by init_table.py and any sync code)
pg_engine = PGEngine.from_connection_string(url=settings.DATABASE_URL)