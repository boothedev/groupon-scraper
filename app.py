"""Playwright-backed web scraper API.

This service exposes a small FastAPI endpoint that uses Playwright to
search Groupon for deals and return a brief JSON summary of the first
matching item.

Notes:
 - Playwright browsers must be installed on the host (`playwright install`)
 - The service uses an async lifespan to start/stop Playwright and a
   bounded semaphore to limit concurrent pages.
"""

import json
from fastapi import FastAPI, HTTPException
import asyncio
import logging
from typing import Optional
from playwright.async_api import (
    Browser,
    Playwright,
    async_playwright,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)
from contextlib import asynccontextmanager

SORT_OPTIONS = ["relevance", "price:asc", "price:desc", "distance", "rating"]

# Config
MAX_CONCURRENT_PAGES = 4
# Use a bounded semaphore to avoid accidental growth of waiting tasks
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_semaphore = asyncio.BoundedSemaphore(MAX_CONCURRENT_PAGES)


async def _ensure_startup() -> None:
    global _playwright, _browser
    if _playwright is None:
        try:
            _playwright = await async_playwright().start()
            # Launch a single browser instance shared across requests
            # headless=True for production; override with env or code for debugging
            _browser = await _playwright.chromium.launch(
                channel="chrome", headless=True
            )
            logger.info("Playwright started and browser launched")
        except Exception as e:
            logger.exception("Failed to start Playwright: %s", e)
            # Ensure globals are reset on failure
            _playwright = None
            _browser = None
            raise


async def _shutdown() -> None:
    global _playwright, _browser
    # Close things but do not let exceptions during shutdown crash the
    # application shutdown sequence. Playwright/browser shutdown can
    # fail if the driver process already exited; log and continue.
    if _browser:
        try:
            await _browser.close()
        except Exception as e:
            logger.warning("Exception while closing browser during shutdown: %s", e)

    if _playwright:
        try:
            await _playwright.stop()
        except Exception as e:
            logger.warning("Exception while stopping Playwright during shutdown: %s", e)

    _browser = None
    _playwright = None
    logger.info("Playwright stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _ensure_startup()
    yield
    await _shutdown()


app = FastAPI(lifespan=lifespan, redirect_slashes=False)
logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)


async def run(
    page: Page,
    query: str,
    sort_option: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> dict | None:
    #
    overlay_offer_loc = page.locator('[data-bhw="ExitBannerModal"]')
    search_box_loc = page.get_by_test_id("search-input")
    sort_filter_box_loc = page.locator('[data-bhw="sort-filter-box"]').first
    select_sort_filter_loc = page.locator(f'[data-bhc="sort:{sort_option}"]')
    price_range_loc = page.get_by_test_id("filter-section-price").get_by_role("textbox")
    item_list_loc = page.get_by_test_id("deal-grid").first

    await page.add_locator_handler(
        overlay_offer_loc, lambda offer: offer.get_by_role("button").click()
    )

    #
    await page.goto("https://www.groupon.com/")
    await search_box_loc.wait_for()
    await search_box_loc.fill(query)
    await search_box_loc.press("Enter")
    await sort_filter_box_loc.wait_for()

    # Set sort filter
    sort_option = (sort_option or "").lower()
    if sort_option in SORT_OPTIONS:
        await sort_filter_box_loc.click()
        await select_sort_filter_loc.click()

    # Set price range
    if price_min:
        await price_range_loc.first.fill(str(price_min))
        await price_range_loc.first.press("Tab")

    if price_max:
        await price_range_loc.last.fill(str(price_max))
        await price_range_loc.last.press("Tab")

    # Grab the first item
    await item_list_loc.wait_for()
    notfound = await page.locator('[data-bhw="EmptyDealList"]').count() != 0
    if notfound:
        return

    first_item_info = (
        await page.get_by_test_id("deal-grid")
        .locator("a")
        .first.get_attribute("data-bhd")
    ) or ""
    #
    info_dict = json.loads(first_item_info)
    section1 = info_dict["body"]["section1"]["content"]
    section2 = info_dict["body"]["section2"]["content"]
    section3 = info_dict["body"]["section3"]["content"]
    brief_info_dict = {
        "name": section1,
        "prices": {
            "list_price": section2["list_price"],
            "sell_price": section2["sell_price"],
            "discount": section2["discount"],
            "isocode_currency": section2["isocode_currency"],
            "currency_exponent": section2["currency_exponent"],
        },
        "supplier": section3,
    }

    return brief_info_dict


@app.get("/search")
async def search(
    query: str,
    sort_option: str = "",
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
):
    await _ensure_startup()
    if _browser is None or _playwright is None:
        raise HTTPException(status_code=503, detail="Browser not available")

    # Limit concurrent page usage
    async with _semaphore:
        context = await _browser.new_context(
            **_playwright.devices.get("Desktop Chrome", {})
        )
        page = await context.new_page()
        try:
            result = await run(
                page=page,
                query=query,
                sort_option=sort_option,
                price_min=price_min,
                price_max=price_max,
            )
            return {"success": True, "data": result}
        except PlaywrightTimeoutError as e:
            logger.error("Timeout: %s", e)
            raise HTTPException(status_code=504, detail="Timeout while scraping")
        except Exception as e:
            logger.exception("Scrape failed: %s", e)
            raise HTTPException(status_code=500, detail="Scrape error")
        finally:
            # always close context to free resources
            try:
                await context.close()
            except Exception:
                logger.debug("Failed to close context cleanly")


@app.get("/health")
async def health():
    """Lightweight health endpoint that does not start Playwright.

    This is useful for load balancers and tests that want a quick
    liveness check without exercising the browser.
    """
    return {"status": "ok"}
