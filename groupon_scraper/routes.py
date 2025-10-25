"""HTTP route handlers (FastAPI APIRouter).

Defines the `/search` and `/health` endpoints and delegates scraping to
the `scraper` module while using the lifecycle helpers in
`playwright_manager`.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
from enum import Enum
import os

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .playwright_manager import get_browser, get_playwright, get_semaphore
from .scraper import run

# Environment-configurable timeouts/retries for navigation
GOTO_TIMEOUT_MS = int(os.getenv("PAGE_GOTO_TIMEOUT_MS", "60000"))
GOTO_RETRIES = int(os.getenv("PAGE_GOTO_RETRIES", "2"))

logger = logging.getLogger("app.routes")

router = APIRouter()


class SortOption(str, Enum):
    relevance = "relevance"
    price_asc = "price:asc"
    price_desc = "price:desc"
    distance = "distance"
    rating = "rating"


@router.get("/search")
async def search(
    query: str = Query(..., min_length=1),
    sort_option: Optional[SortOption] = None,
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, ge=0),
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
            # FastAPI will coerce and validate `sort_option` to one of the
            # SortOption enum values (or None). Convert to plain string for
            # the scraper.run function which expects Optional[str].
            sort_str = sort_option.value if sort_option is not None else None

            result = await run(
                page=page,
                query=query,
                sort_option=sort_str,
                price_min=price_min,
                price_max=price_max,
                goto_timeout_ms=GOTO_TIMEOUT_MS,
                goto_retries=GOTO_RETRIES,
            )

            return {
                "success": True,
                "data": result or "No results found",
            }

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
