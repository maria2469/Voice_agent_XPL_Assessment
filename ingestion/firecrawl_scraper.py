"""
╔══════════════════════════════════════════════════════════╗
║       Firecrawl + LangChain Scraper — sunmarke.com       ║
║  Crawls entire site → LangChain Documents → CSV output   ║
╚══════════════════════════════════════════════════════════╝

Setup:
    pip install firecrawl-py langchain-core python-dotenv

Get free API key (500 pages free, no card needed):
    https://www.firecrawl.dev → Sign Up → Dashboard → API Keys

Create a .env file in the same folder as this script:
    FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
"""

import os
import csv
import time
from datetime import datetime
from dotenv import load_dotenv

# ── LangChain ─────────────────────────────────────────────────────────────────
from langchain_core.documents import Document as LCDocument

# ── Firecrawl SDK v4 — verified imports ───────────────────────────────────────
# Firecrawl == FirecrawlApp (same class, two aliases)
# ScrapeOptions lives in firecrawl.v2.types (snake_case fields)
# start_crawl()      → kicks off async job, returns CrawlResponse with .id
# get_crawl_status() → polls job, returns CrawlJob with .status / .data
from firecrawl import Firecrawl
from firecrawl.v2.types import ScrapeOptions

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
TARGET_URL = "https://www.sunmarke.com"
MAX_PAGES  = 200        # free tier = 500 credits total
MAX_DEPTH  = 5
OUTPUT_CSV = "sunmarke_firecrawl.csv"
POLL_EVERY = 10         # seconds between status-check polls

# ─────────────────────────────────────────────────────────────────────────────
# LOAD ENV
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise EnvironmentError(
        "\n❌  FIRECRAWL_API_KEY not found!\n"
        "    1. Get a free key → https://www.firecrawl.dev\n"
        "    2. Add to .env :   FIRECRAWL_API_KEY=fc-...\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — CRAWL
# Verified method: start_crawl(url, *, keyword_args...)  → CrawlResponse(.id)
# Verified method: get_crawl_status(job_id)              → CrawlJob(.status/.data)
# ScrapeOptions fields are snake_case (only_main_content, block_ads, etc.)
# ─────────────────────────────────────────────────────────────────────────────
def run_crawl() -> list:
    print(f"\n🔥  Starting Firecrawl crawl → {TARGET_URL}")
    print(f"    Max pages : {MAX_PAGES}")
    print(f"    Max depth : {MAX_DEPTH}\n")

    app = Firecrawl(api_key=FIRECRAWL_API_KEY)

    # ── start_crawl() uses snake_case keyword args (verified from source) ─────
    crawl_response = app.start_crawl(
        TARGET_URL,
        limit                  = MAX_PAGES,
        max_discovery_depth    = MAX_DEPTH,
        sitemap                = "include",       # use sitemap + HTML links
        ignore_query_parameters= True,            # don't re-scrape same path
        crawl_entire_domain    = True,            # follow sibling/parent links
        allow_subdomains       = False,
        allow_external_links   = False,
        exclude_paths          = [
            "wp-json/.*",
            "feed/.*",
            "tag/.*",
        ],
        scrape_options = ScrapeOptions(
            formats            = ["markdown"],    # clean markdown output
            only_main_content  = True,            # strip nav/footer/ads
            block_ads          = True,
            proxy              = "auto",          # stealth proxy auto-select
            wait_for           = 1500,            # ms — let JS pages settle
            remove_base64_images = True,          # keep output lean
            timeout            = 30000,
        ),
    )

    job_id = crawl_response.id
    print(f"    Crawl job ID : {job_id}")
    print(f"    Polling every {POLL_EVERY}s ...\n")

    # ── Poll until done ───────────────────────────────────────────────────────
    # get_crawl_status() returns CrawlJob with fields:
    #   .status    → 'scraping' | 'completed' | 'failed' | 'cancelled'
    #   .completed → int  (pages done so far)
    #   .total     → int  (total pages found)
    #   .data      → List[Document]
    while True:
        job = app.get_crawl_status(job_id)

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"    [{ts}]  {job.status}  —  {job.completed}/{job.total or '?'} pages done")

        if job.status == "completed":
            pages = job.data or []
            print(f"\n✅  Crawl complete — {len(pages)} pages retrieved\n")
            return pages

        if job.status in ("failed", "cancelled"):
            raise RuntimeError(
                f"Crawl job ended with status '{job.status}'.\n"
                "Check your API key and remaining credits at firecrawl.dev/dashboard"
            )

        time.sleep(POLL_EVERY)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Convert Firecrawl Documents → LangChain Documents
# ─────────────────────────────────────────────────────────────────────────────
def to_langchain_documents(raw_pages: list) -> list[LCDocument]:
    """
    Firecrawl v2 Document fields (verified):
        .markdown    — clean page text
        .metadata    — pydantic model with .source_url, .title, .description, etc.
    """
    docs = []

    for page in raw_pages:
        markdown = getattr(page, "markdown", None) or ""
        meta_obj = getattr(page, "metadata", None)

        # Normalise metadata → plain dict
        if meta_obj is None:
            meta = {}
        elif hasattr(meta_obj, "model_dump"):
            meta = meta_obj.model_dump()
        elif hasattr(meta_obj, "__dict__"):
            meta = {k: v for k, v in vars(meta_obj).items() if not k.startswith("_")}
        else:
            meta = dict(meta_obj)

        if not markdown.strip():
            continue  # skip blank / error pages

        # metadata keys can be camelCase or snake_case depending on version
        source = (
            meta.get("sourceURL")
            or meta.get("source_url")
            or meta.get("url")
            or ""
        )
        status = (
            meta.get("statusCode")
            or meta.get("status_code")
            or 200
        )

        doc = LCDocument(
            page_content=markdown,
            metadata={
                "source":      source,
                "title":       meta.get("title",       ""),
                "description": meta.get("description", ""),
                "status_code": status,
                "language":    meta.get("language",    ""),
                "crawled_at":  datetime.utcnow().isoformat(),
            },
        )
        docs.append(doc)

    print(f"📄  Converted {len(docs)} pages → LangChain Documents\n")
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Save to CSV
# ─────────────────────────────────────────────────────────────────────────────
def save_to_csv(docs: list[LCDocument], path: str = OUTPUT_CSV) -> None:
    if not docs:
        print("⚠️  No documents to save.")
        return

    fieldnames = ["url", "title", "description", "status_code",
                  "language", "content", "crawled_at"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for doc in docs:
            m = doc.metadata
            writer.writerow({
                "url":         m.get("source",      ""),
                "title":       m.get("title",        ""),
                "description": m.get("description",  ""),
                "status_code": m.get("status_code",  ""),
                "language":    m.get("language",     ""),
                "content":     doc.page_content[:25000],  # cap per cell
                "crawled_at":  m.get("crawled_at",   ""),
            })

    print(f"💾  Saved → {path}  ({len(docs)} rows)")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
def print_summary(docs: list[LCDocument]) -> None:
    print("\n" + "-" * 65)
    print(f"  SCRAPE SUMMARY — {len(docs)} pages")
    print("-" * 65)
    for i, doc in enumerate(docs[:15], 1):
        title = (doc.metadata.get("title") or "(no title)")[:50]
        url   = doc.metadata.get("source", "")[:65]
        words = len(doc.page_content.split())
        print(f"  {i:>3}. [{words:>5}w]  {title}")
        print(f"        {url}")
    if len(docs) > 15:
        print(f"\n  ... and {len(docs) - 15} more pages.")
    print("-" * 65 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t0 = time.time()

    raw_pages = run_crawl()                         # Step 1
    documents = to_langchain_documents(raw_pages)   # Step 2
    print_summary(documents)
    save_to_csv(documents)                          # Step 3

    print(f"\n⏱  Total time : {time.time() - t0:.1f}s")
    print(f"📂  Output    : {OUTPUT_CSV}\n")