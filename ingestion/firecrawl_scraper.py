"""
╔══════════════════════════════════════════════════════════╗
║       Firecrawl + LangChain Scraper — sunmarke.com       ║
║  Crawls entire site → LangChain Documents → CSV output   ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import csv
import time
from datetime import datetime
from dotenv import load_dotenv

from langchain_core.documents import Document as LCDocument
from firecrawl import Firecrawl
from firecrawl.v2.types import ScrapeOptions

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
TARGET_URL  = "https://www.sunmarke.com"
MAX_PAGES   = 200
MAX_DEPTH   = 5
OUTPUT_CSV  = "sunmarke_firecrawl_1.csv"
POLL_EVERY  = 10

# Pages known to be JS-rendered — will be scraped individually with longer wait
JS_HEAVY_PATHS = [
    "/admissions/tuition-fees/",
    "/admissions/faqs/",
    "/admissions/scholarships/",
    "/for-parents/school-timings/",
    "/for-parents/academic-calendar/",
    "/for-parents/transport-services/",
    "/for-parents/dining-catering/",
]

# PDFs to extract text from directly
IMPORTANT_PDFS = [
    "https://www.sunmarke.com/wp-content/uploads/2023/05/KHDA-Tuition-Fees.pdf",
    "https://www.sunmarke.com/wp-content/uploads/2023/01/ADMISSIONS-FEE-POLICY-2022-23.pdf",
    "https://www.sunmarke.com/wp-content/uploads/2023/02/ADMISSIONS-FEE-POLICY-2022-23-2.pdf",
    "https://www.sunmarke.com/wp-content/uploads/2023/02/Admission-and-Transfer-Guidelines.pdf",
    "https://www.sunmarke.com/wp-content/uploads/2022/10/SMS_Brochure_2022.pdf",
]

load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
if not FIRECRAWL_API_KEY:
    raise EnvironmentError("FIRECRAWL_API_KEY not found in .env")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1A — MAIN CRAWL (same as before, but with fixes)
# ─────────────────────────────────────────────────────────────────────────────
def run_crawl() -> list:
    print(f"\n🔥  Starting Firecrawl crawl → {TARGET_URL}")
    print(f"    Max pages : {MAX_PAGES} | Max depth : {MAX_DEPTH}\n")

    app = Firecrawl(api_key=FIRECRAWL_API_KEY)

    crawl_response = app.start_crawl(
        TARGET_URL,
        limit                   = MAX_PAGES,
        max_discovery_depth     = MAX_DEPTH,
        sitemap                 = "include",
        ignore_query_parameters = True,
        crawl_entire_domain     = True,
        allow_subdomains        = False,
        allow_external_links    = False,
        exclude_paths           = [
            "wp-json/.*",
            "feed/.*",
            "tag/.*",
        ],
        scrape_options=ScrapeOptions(
            formats              = ["markdown"],
            only_main_content    = False,         # ← FIXED: was True, caused JS tables to be stripped
            block_ads            = True,
            proxy                = "auto",
            wait_for             = 3000,           # ← FIXED: was 1500ms, not enough for JS render
            remove_base64_images = True,
            timeout              = 45000,          # ← FIXED: was 30000, PDFs need more time
        ),
    )

    job_id = crawl_response.id
    print(f"    Crawl job ID : {job_id}")
    print(f"    Polling every {POLL_EVERY}s ...\n")

    while True:
        job = app.get_crawl_status(job_id)
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"    [{ts}]  {job.status}  —  {job.completed}/{job.total or '?'} pages done")

        if job.status == "completed":
            pages = job.data or []
            print(f"\n✅  Crawl complete — {len(pages)} pages retrieved\n")
            return pages

        if job.status in ("failed", "cancelled"):
            raise RuntimeError(f"Crawl job ended with status '{job.status}'.")

        time.sleep(POLL_EVERY)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1B — RE-SCRAPE JS-HEAVY PAGES INDIVIDUALLY WITH LONGER WAIT
# These pages render tables/fees via JavaScript and need extra time
# ─────────────────────────────────────────────────────────────────────────────
def scrape_js_pages(app: Firecrawl) -> list:
    print(f"\n🔄  Re-scraping {len(JS_HEAVY_PATHS)} JS-heavy pages with extended wait...\n")
    results = []

    for path in JS_HEAVY_PATHS:
        url = TARGET_URL + path
        print(f"    Scraping: {url}")
        try:
            result = app.scrape_url(
                url,
                formats           = ["markdown"],
                only_main_content = False,         # keep full DOM
                wait_for          = 6000,           # 6s — let JS tables fully render
                timeout           = 60000,
                actions           = [               # scroll to trigger lazy-load
                    {"type": "scroll", "direction": "down", "amount": 500},
                    {"type": "wait",   "milliseconds": 2000},
                    {"type": "scroll", "direction": "down", "amount": 500},
                ],
            )
            if result and getattr(result, "markdown", None):
                results.append(result)
                words = len(result.markdown.split())
                print(f"    ✅  {words} words captured")
            else:
                print(f"    ⚠️  Empty response")
        except Exception as e:
            print(f"    ❌  Failed: {e}")
        time.sleep(2)

    print(f"\n    JS pages scraped: {len(results)}\n")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1C — SCRAPE IMPORTANT PDFs FOR TEXT CONTENT
# Firecrawl can extract text from PDFs directly
# ─────────────────────────────────────────────────────────────────────────────
def scrape_pdfs(app: Firecrawl) -> list:
    print(f"\n📄  Extracting text from {len(IMPORTANT_PDFS)} important PDFs...\n")
    results = []

    for url in IMPORTANT_PDFS:
        print(f"    Scraping PDF: {url}")
        try:
            result = app.scrape_url(
                url,
                formats = ["markdown"],
                timeout = 60000,
            )
            if result and getattr(result, "markdown", None):
                results.append(result)
                words = len(result.markdown.split())
                print(f"    ✅  {words} words extracted from PDF")
            else:
                print(f"    ⚠️  No content extracted")
        except Exception as e:
            print(f"    ❌  Failed: {e}")
        time.sleep(2)

    print(f"\n    PDFs extracted: {len(results)}\n")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1D — INJECT MANUAL DATA (fees not available online)
# ─────────────────────────────────────────────────────────────────────────────
def get_manual_documents() -> list[LCDocument]:
    """
    Hardcode data that the crawler cannot reach
    (JS-rendered tables, gated content, etc.)
    """
    manual = [
        LCDocument(
            page_content="""
Sunmarke School Tuition Fees 2025-2026 (AED)

Year (British Curriculum) | Age Range | Annual Fee | Term 1    | Term 2    | Term 3
Foundation Stage 1 (FS1)  | 3-4 years | 53,040     | 21,216    | 15,912    | 15,912
Foundation Stage 2 (FS2)  | 4-5 years | 58,164     | 23,266    | 17,449    | 17,449

These are the official 2025-2026 tuition fees for Sunmarke School in Dubai.
FS1 is for children aged 3-4 years. FS2 is for children aged 4-5 years.
Fees are split across 3 terms. Term 1 is the highest fee each year.
""",
            metadata={
                "source":      "https://www.sunmarke.com/admissions/tuition-fees/",
                "title":       "Sunmarke Tuition Fees 2025-2026",
                "description": "Official tuition fee breakdown by year group and term",
                "status_code": 200,
                "language":    "en",
                "crawled_at":  datetime.utcnow().isoformat(),
            },
        ),
        # Add more manual entries here as needed
    ]

    print(f"📝  Injected {len(manual)} manual document(s)\n")
    return manual


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Convert all raw pages → LangChain Documents
# ─────────────────────────────────────────────────────────────────────────────
def to_langchain_documents(raw_pages: list) -> list[LCDocument]:
    docs = []

    for page in raw_pages:
        markdown = getattr(page, "markdown", None) or ""
        meta_obj = getattr(page, "metadata", None)

        if meta_obj is None:
            meta = {}
        elif hasattr(meta_obj, "model_dump"):
            meta = meta_obj.model_dump()
        elif hasattr(meta_obj, "__dict__"):
            meta = {k: v for k, v in vars(meta_obj).items() if not k.startswith("_")}
        else:
            meta = dict(meta_obj)

        if not markdown.strip():
            continue

        source = (
            meta.get("sourceURL")
            or meta.get("source_url")
            or meta.get("url")
            or ""
        )
        status = meta.get("statusCode") or meta.get("status_code") or 200

        docs.append(LCDocument(
            page_content=markdown,
            metadata={
                "source":      source,
                "title":       meta.get("title",       ""),
                "description": meta.get("description", ""),
                "status_code": status,
                "language":    meta.get("language",    ""),
                "crawled_at":  datetime.utcnow().isoformat(),
            },
        ))

    print(f"📄  Converted {len(docs)} pages → LangChain Documents\n")
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Deduplicate by URL (JS re-scrape overrides crawl version)
# ─────────────────────────────────────────────────────────────────────────────
def deduplicate(docs: list[LCDocument]) -> list[LCDocument]:
    """
    Later entries win — so JS-rescraped and manual docs
    override the original crawl for the same URL.
    """
    seen = {}
    for doc in docs:
        url = doc.metadata.get("source", "")
        seen[url] = doc  # overwrite with latest version

    deduped = list(seen.values())
    print(f"🔁  After dedup: {len(deduped)} unique documents\n")
    return deduped


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Save to CSV
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
                "content":     doc.page_content[:25000],
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
    t0  = time.time()
    app = Firecrawl(api_key=FIRECRAWL_API_KEY)

    # 1. Main crawl
    raw_pages     = run_crawl()
    crawl_docs    = to_langchain_documents(raw_pages)

    # 2. Re-scrape JS-heavy pages with extended wait
    js_raw        = scrape_js_pages(app)
    js_docs       = to_langchain_documents(js_raw)

    # 3. Extract important PDFs
    pdf_raw       = scrape_pdfs(app)
    pdf_docs      = to_langchain_documents(pdf_raw)

    # 4. Inject manual/hardcoded data
    manual_docs   = get_manual_documents()

    # 5. Merge: crawl first, then JS overrides, then PDFs, then manual
    all_docs      = crawl_docs + js_docs + pdf_docs + manual_docs
    final_docs    = deduplicate(all_docs)

    print_summary(final_docs)
    save_to_csv(final_docs)

    print(f"\n⏱  Total time : {time.time() - t0:.1f}s")
    print(f"📂  Output    : {OUTPUT_CSV}\n")