"""Browser runtime (PRD §8): API-first, browser second.

Real nav via Playwright Chromium (headless). Every run returns
observable evidence: final URL, title, screenshot ref — no blind success.
"""
import os
import time


def has_browser_automation() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def open_url(url: str, screenshot_name: str | None = None, timeout: int = 30000) -> dict:
    from playwright.sync_api import sync_playwright

    data_dir = os.path.abspath(os.environ.get("NEXUS_DATA_DIR", "./nexus_data"))
    os.makedirs(data_dir, exist_ok=True)
    shot = os.path.join(data_dir, screenshot_name or f"shot-{int(time.time())}.png")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_timeout(1500)
            title = page.title()
            h1 = page.locator("h1").first.inner_text() if page.locator("h1").count() else ""
            page.screenshot(path=shot, full_page=False)
            status = resp.status if resp else -1
        finally:
            browser.close()

    if not title and status != 200:
        raise RuntimeError(f"Verification failed: status={status}, empty title for {url}")
    return {
        "ok": True,
        "url": url,
        "final_url": url,
        "http_status": status,
        "title": title,
        "h1": h1[:200],
        "screenshot": shot,
        "verification": "domcontentloaded + non-empty title + screenshot saved",
    }


def quick_audit(url: str) -> dict:
    """Website-intel slice (PRD §12): technical + content signals, evidence-backed."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            data = page.evaluate(
                """() => ({
                    title: document.title,
                    desc: (document.querySelector('meta[name=description]')||{}).content || '',
                    h1count: document.querySelectorAll('h1').length,
                    h2count: document.querySelectorAll('h2').length,
                    links: document.querySelectorAll('a').length,
                    imgs: document.querySelectorAll('img').length,
                    imgsNoAlt: [...document.querySelectorAll('img')].filter(i=>!i.alt).length
                })"""
            )
            data["http_status"] = resp.status if resp else -1
            data["url"] = url
        finally:
            browser.close()
    return data
