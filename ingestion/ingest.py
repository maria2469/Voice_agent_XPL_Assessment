"""
ingestion/ingest.py
Reads the Firecrawl CSV → chunks → classifies → stores in PGVector.

Run:
    python -m ingestion.ingest
    python -m ingestion.ingest --csv path/to/other.csv --chunk-size 800
"""
import csv
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from db.vector_store import get_vector_store_sync

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_CSV    = "sunmarke_accordion_scraped.csv"
CHUNK_SIZE     = 600      # characters per chunk (tune to your embedding model)
CHUNK_OVERLAP  = 80       # overlap to preserve cross-chunk context
BATCH_SIZE     = 50       # docs per .add_documents() call (avoids rate limits)

# ─────────────────────────────────────────────────────────────────────────────
# CONTENT CLASSIFIER
# Simple keyword-based tagger — replace with an LLM call if you want richer tags
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("admissions",   ["admissions", "enrol", "enrollment", "apply", "application", "fees", "tuition"]),
    ("curriculum",   ["curriculum", "gcse", "igcse", "a-level", "ib", "subject", "lesson", "learning"]),
    ("activities",   ["activity", "activities", "sport", "club", "extracurricular", "trip"]),
    ("about",        ["about", "mission", "vision", "principal", "leadership", "history", "ethos"]),
    ("parents",      ["parent", "pta", "uniform", "term dates", "calendar", "newsletter"]),
    ("news",         ["news", "event", "blog", "announcement", "update"]),
    ("contact",      ["contact", "location", "address", "phone", "email", "map"]),
    ("wellbeing",    ["wellbeing", "mental health", "counselling", "pastoral", "inclusion"]),
]

def classify(text: str) -> str:
    low = text.lower()
    for category, keywords in CATEGORY_RULES:
        if any(k in low for k in keywords):
            return category
    return "general"

# ─────────────────────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────────────────────
def parse_crawled_at(value: str) -> datetime:
    """
    Safely parse a datetime string from CSV and return a naive datetime.
    If empty or invalid, return current naive datetime.
    """
    if not value:
        return datetime.now()
    try:
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=None)  # make naive
    except Exception:
        return datetime.now()

# ─────────────────────────────────────────────────────────────────────────────
# LOAD CSV
# ─────────────────────────────────────────────────────────────────────────────
def load_csv(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Skip 404 / empty pages
            content = (row.get("content") or "").strip()
            title   = (row.get("title")   or "").lower()
            if not content or "page not found" in title:
                continue
            rows.append(row)
    print(f"📂  Loaded {len(rows)} valid pages from {path}")
    return rows

# ─────────────────────────────────────────────────────────────────────────────
# CHUNK + BUILD DOCUMENTS
# ─────────────────────────────────────────────────────────────────────────────
def build_documents(rows: list[dict], chunk_size: int, chunk_overlap: int) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = chunk_size,
        chunk_overlap = chunk_overlap,
        separators    = ["\n\n", "\n", ". ", " ", ""],
    )

    docs = []
    for row in rows:
        content     = row.get("content",     "").strip()
        url         = row.get("url",         "")
        title       = row.get("title",       "")
        description = row.get("description", "")
        language    = row.get("language",    "")
        crawled_at  = parse_crawled_at(row.get("crawled_at", ""))

        chunks = splitter.split_text(content)

        for chunk in chunks:
            category = classify(chunk)
            docs.append(Document(
                id           = str(uuid.uuid4()),
                page_content = chunk,
                metadata     = {
                    "url":      url,
                    "title":       title,
                    "description": description,
                    "category":    category,
                    "language":    language,
                    "crawled_at":  crawled_at,
                },
            ))

    print(f"✂️   Split into {len(docs)} chunks  "
          f"(avg {sum(len(d.page_content) for d in docs)//max(len(docs),1)} chars each)")
    return docs

# ─────────────────────────────────────────────────────────────────────────────
# INGEST IN BATCHES
# ─────────────────────────────────────────────────────────────────────────────
def ingest(csv_path: str = DEFAULT_CSV,
           chunk_size: int = CHUNK_SIZE,
           chunk_overlap: int = CHUNK_OVERLAP) -> None:

    print("\n🚀  Starting Firecrawl → PGVector ingestion pipeline\n")

    # 1. Load
    rows = load_csv(csv_path)
    if not rows:
        print("⚠️  No rows found. Exiting.")
        return

    # 2. Chunk + classify
    docs = build_documents(rows, chunk_size, chunk_overlap)

    # 3. Connect to vector store
    print("🔌  Connecting to PGVector store …")
    store = get_vector_store_sync()

    # 4. Batch-insert with progress
    total   = len(docs)
    batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"🧠  Embedding + storing {total} chunks in {batches} batches …\n")

    for i in range(0, total, BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        store.add_documents(batch)
        done = min(i + BATCH_SIZE, total)
        pct  = done / total * 100
        print(f"    [{pct:5.1f}%]  {done}/{total} chunks stored")

    print(f"\n✅  Ingestion complete — {total} chunks in PGVector table 'sunmarke_firecrawl_docs'\n")

# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Firecrawl CSV into PGVector")
    parser.add_argument("--csv",          default=DEFAULT_CSV,   help="Path to CSV file")
    parser.add_argument("--chunk-size",   default=CHUNK_SIZE,    type=int)
    parser.add_argument("--chunk-overlap",default=CHUNK_OVERLAP, type=int)
    args = parser.parse_args()

    ingest(
        csv_path     = args.csv,
        chunk_size   = args.chunk_size,
        chunk_overlap= args.chunk_overlap,
    )