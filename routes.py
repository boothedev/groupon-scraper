"""HTTP route handlers (FastAPI APIRouter).

Defines the `/search` and `/health` endpoints and delegates scraping to
the `scraper` module while using the lifecycle helpers in
`playwright_manager`.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from playwright_manager import get_browser, get_playwright, get_semaphore
from scraper import run

logger = logging.getLogger("app.routes")

router = APIRouter()


@router.get("/search")
async def search(
    query: str,
    sort_option: str = "",
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
):
    browser = get_browser()
    playwright = get_playwright()
    if browser is None or playwright is None:
        raise HTTPException(status_code=503, detail="Browser not available")

    # Limit concurrent page usage
    async with get_semaphore():
        context = await browser.new_context(
            **playwright.devices.get("Desktop Chrome", {})
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


@router.get("/health")
async def health():
    """Lightweight health endpoint that does not start Playwright.

    This is useful for load balancers and tests that want a quick
    liveness check without exercising the browser.
    """
    return {"status": "ok"}
