import time
import csv
import json
import random
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BASE_URL    = "https://www.sunmarke.com/"
MAX_PAGES   = 200
MAX_DEPTH   = 5
OUTPUT_CSV  = "sunmarke_scraped.csv"
PAGE_DELAY  = (1.5, 3.0)   # random sleep range between pages (seconds)

PRIORITY_KEYWORDS = ["about", "learning", "admissions", "parents", "activities"]

SKIP_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".mp4", ".mp3", ".zip", ".doc", ".docx", ".xls",
)

# ─────────────────────────────────────────────
# ANTI-DETECTION USER AGENTS
# ─────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
]


class SunmarkeCrawler:

    # ─────────────────────────────────────────
    # INIT – build a human-like Chrome session
    # ─────────────────────────────────────────
    def __init__(self):
        self.visited: set  = set()
        self.data:    list = []
        self.driver        = self._build_driver()

    def _build_driver(self) -> webdriver.Chrome:
        opts = Options()
        ua   = random.choice(USER_AGENTS)

        # ── Make headless look like a real browser ──────────────────────
        opts.add_argument("--headless=new")           # new headless (less detectable)
        opts.add_argument(f"--user-agent={ua}")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        # ── Stability ───────────────────────────────────────────────────
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--ignore-certificate-errors")

        # ── Enable JavaScript + Cookies (critical!) ─────────────────────
        opts.add_argument("--enable-javascript")
        opts.add_argument("--enable-cookies")

        # ── Don't block images/fonts (helps JS challenges pass) ─────────
        prefs = {
            "profile.default_content_setting_values": {
                "cookies": 1,       # 1 = allow
                "javascript": 1,
            }
        }
        opts.add_experimental_option("prefs", prefs)

        # page_load_strategy = normal so full JS executes
        opts.page_load_strategy = "normal"

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opts,
        )
        driver.set_page_load_timeout(45)

        # ── Patch navigator.webdriver flag via CDP ───────────────────────
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins',   {get: () => [1,2,3]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                    window.chrome = { runtime: {} };
                """
            },
        )

        return driver

    # ─────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        p = urlparse(url)
        return (
            bool(p.netloc)
            and p.netloc.endswith("sunmarke.com")
            and not any(url.lower().endswith(ext) for ext in SKIP_EXTENSIONS)
            and p.scheme in ("http", "https")
        )

    @staticmethod
    def _is_404(text: str) -> bool:
        low = text.lower()
        return "404" in low and "not found" in low

    @staticmethod
    def _clean(text: str) -> str:
        """Strip excess blank lines."""
        lines = [ln.strip() for ln in text.splitlines()]
        return "\n".join(ln for ln in lines if ln)

    def _random_sleep(self):
        time.sleep(random.uniform(*PAGE_DELAY))

    # ─────────────────────────────────────────
    # WAIT FOR PAGE READY (handles JS challenges)
    # ─────────────────────────────────────────
    def _wait_for_page(self, timeout: int = 20):
        """
        Wait until document.readyState == 'complete' AND the body
        has some visible text (catches cookie/JS challenge pages).
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            # Extra wait for dynamic content / challenge resolution
            time.sleep(2.5)
        except TimeoutException:
            pass

    # ─────────────────────────────────────────
    # COOKIE CHALLENGE BYPASS
    # ─────────────────────────────────────────
    def _bypass_challenge(self):
        """
        Detect and click through common cookie-consent / bot-challenge buttons.
        Also handles Cloudflare "Verify you are human" style challenges.
        """
        keywords = [
            "accept", "agree", "allow", "continue", "verify",
            "i am human", "confirm", "i'm not a robot", "proceed",
            "got it", "ok", "understood",
        ]
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button | //a[@role='button']")
            for btn in buttons:
                try:
                    txt = (btn.text or "").lower().strip()
                    if any(k in txt for k in keywords) and btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
                except Exception:
                    continue
        except Exception:
            pass

        # Handle iframe-based challenges (e.g. Cloudflare turnstile)
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    btns = self.driver.find_elements(By.XPATH, "//input[@type='checkbox'] | //button")
                    for b in btns:
                        try:
                            if b.is_displayed():
                                self.driver.execute_script("arguments[0].click();", b)
                                time.sleep(1)
                        except Exception:
                            pass
                    self.driver.switch_to.default_content()
                except Exception:
                    self.driver.switch_to.default_content()
        except Exception:
            pass

    # ─────────────────────────────────────────
    # SCROLL (lazy-load content)
    # ─────────────────────────────────────────
    def _scroll(self):
        try:
            height = self.driver.execute_script("return document.body.scrollHeight")
            step   = max(400, height // 6)
            pos    = 0
            while pos < height:
                pos = min(pos + step, height)
                self.driver.execute_script(f"window.scrollTo(0, {pos});")
                time.sleep(0.3)
        except Exception:
            pass

    # ─────────────────────────────────────────
    # EXPAND ACCORDIONS / TABS
    # ─────────────────────────────────────────
    def _expand_accordions(self):
        selectors = [
            "//button[contains(@class,'accordion')]",
            "//button[contains(@class,'toggle')]",
            "//button[contains(@class,'tab')]",
            "//div[@role='tab']",
            "//summary",                         # <details> elements
            "//*[@aria-expanded='false']",
        ]
        for sel in selectors:
            try:
                els = self.driver.find_elements(By.XPATH, sel)
                for el in els:
                    try:
                        if el.is_displayed():
                            self.driver.execute_script("arguments[0].click();", el)
                            time.sleep(0.15)
                    except Exception:
                        pass
            except Exception:
                pass

    # ─────────────────────────────────────────
    # EXTRACT FULL PAGE TEXT
    # ─────────────────────────────────────────
    def _extract_text(self) -> str:
        try:
            raw = self.driver.execute_script("return document.body.innerText;") or ""
            return self._clean(raw)
        except Exception:
            return ""

    # ─────────────────────────────────────────
    # EXTRACT STRUCTURED TABLES
    # ─────────────────────────────────────────
    def _extract_tables(self) -> list:
        results = []
        seen    = set()

        # 1. Real <table> elements
        try:
            for table in self.driver.find_elements(By.XPATH, "//table"):
                rows = []
                try:
                    for tr in table.find_elements(By.XPATH, ".//tr"):
                        try:
                            cells = [
                                c.text.strip()
                                for c in tr.find_elements(By.XPATH, ".//th | .//td")
                                if c.text.strip()
                            ]
                            if cells:
                                key = tuple(cells)
                                if key not in seen:
                                    seen.add(key)
                                    rows.append(cells)
                        except StaleElementReferenceException:
                            continue
                except StaleElementReferenceException:
                    continue

                if rows:
                    results.append({"type": "html_table", "data": rows})
        except Exception:
            pass

        # 2. Div-based grids / accordions
        div_xpath = (
            "//div["
            "contains(@class,'table') or contains(@class,'grid') or "
            "contains(@class,'accordion') or contains(@class,'faq') or "
            "contains(@class,'fees') or contains(@class,'curriculum') or "
            "contains(@class,'schedule')"
            "]"
        )
        try:
            for div in self.driver.find_elements(By.XPATH, div_xpath):
                try:
                    txt = div.text.strip()
                    if txt and len(txt) > 40:
                        key = txt[:300]
                        if key not in seen:
                            seen.add(key)
                            results.append({"type": "div_block", "data": txt})
                except StaleElementReferenceException:
                    continue
        except Exception:
            pass

        return results

    # ─────────────────────────────────────────
    # EXTRACT LINKS
    # ─────────────────────────────────────────
    def _extract_links(self) -> list[str]:
        links = set()
        try:
            for el in self.driver.find_elements(By.TAG_NAME, "a"):
                try:
                    href = el.get_attribute("href")
                    if href:
                        full = urljoin(self.driver.current_url, href).split("#")[0].rstrip("/")
                        if self._is_valid_url(full):
                            links.add(full)
                except StaleElementReferenceException:
                    continue
        except Exception:
            pass
        return list(links)

    @staticmethod
    def _prioritize(links: list[str]) -> list[str]:
        hi, lo = [], []
        for lnk in links:
            (hi if any(k in lnk.lower() for k in PRIORITY_KEYWORDS) else lo).append(lnk)
        return hi + lo

    # ─────────────────────────────────────────
    # MAIN CRAWL
    # ─────────────────────────────────────────
    def crawl(self) -> list:
        queue = [(BASE_URL.rstrip("/"), 0)]

        while queue and len(self.visited) < MAX_PAGES:
            url, depth = queue.pop(0)

            if url in self.visited or depth > MAX_DEPTH:
                continue

            print(f"[{len(self.visited)+1}/{MAX_PAGES}] depth={depth}  {url}")
            self.visited.add(url)

            try:
                # ── Load page ──────────────────────────────────────────
                try:
                    self.driver.get(url)
                except TimeoutException:
                    print(f"  ⚠ Timeout — skipping")
                    continue

                self._wait_for_page()
                self._bypass_challenge()

                # ── Re-wait if challenge page detected ─────────────────
                body_text = self._extract_text()
                if (
                    "cookies" in body_text.lower()
                    and len(body_text) < 300
                ):
                    print("  ⚠ Cookie/challenge wall detected — retrying after 5s …")
                    time.sleep(5)
                    self._bypass_challenge()
                    self._wait_for_page(timeout=15)
                    body_text = self._extract_text()

                # ── Skip empty / 404 ───────────────────────────────────
                if not body_text or self._is_404(body_text):
                    print("  ⊘ Empty or 404 — skipping")
                    continue

                # ── Enrich page ────────────────────────────────────────
                self._scroll()
                self._expand_accordions()

                # re-extract after expansion
                text   = self._extract_text()
                tables = self._extract_tables()
                links  = self._extract_links()

                self.data.append({
                    "url":     url,
                    "content": text[:20000],    # cap at 20k chars
                    "tables":  json.dumps(tables, ensure_ascii=False),
                })

                # ── Queue new links ────────────────────────────────────
                new = [lnk for lnk in self._prioritize(links) if lnk not in self.visited]
                # Prepend priority links, append the rest — all as (url, depth) tuples
                hi = [(lnk, depth + 1) for lnk in new if any(k in lnk.lower() for k in PRIORITY_KEYWORDS)]
                lo = [(lnk, depth + 1) for lnk in new if not any(k in lnk.lower() for k in PRIORITY_KEYWORDS)]
                queue = hi + lo + queue

                self._random_sleep()

            except WebDriverException as e:
                print(f"  ✗ WebDriver error: {e}")
            except Exception as e:
                print(f"  ✗ Unexpected error: {e}")

        self.driver.quit()
        print(f"\n✅ Done — {len(self.data)} pages scraped.")
        return self.data

    # ─────────────────────────────────────────
    # SAVE
    # ─────────────────────────────────────────
    def save(self):
        if not self.data:
            print("No data — nothing saved.")
            return

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "content", "tables"])
            writer.writeheader()
            writer.writerows(self.data)

        print(f"💾 Saved → {OUTPUT_CSV}  ({len(self.data)} rows)")


# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    crawler = SunmarkeCrawler()
    crawler.crawl()
    crawler.save()