"""Playwright lifecycle and browser manager.

This module centralizes Playwright startup/shutdown and exposes
helpers used by request handlers.
"""

import asyncio
import logging
import os
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import Playwright, Browser, async_playwright

logger = logging.getLogger("app.playwright")

# Config (environment-configurable)
MAX_CONCURRENT_PAGES = int(os.getenv("MAX_CONCURRENT_PAGES", "4"))

# Headless mode can be toggled via env var (0 means headed)
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "1") != "0"

# Use a bounded semaphore to avoid accidental growth of waiting tasks
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
# Bounded semaphore to limit concurrent pages
_semaphore = asyncio.BoundedSemaphore(MAX_CONCURRENT_PAGES)


async def _ensure_startup() -> None:
    """Start Playwright and launch a shared browser instance.

    Should be safe to call multiple times (no-op if already started).
    """
    global _playwright, _browser
    if _playwright is None:
        try:
            _playwright = await async_playwright().start()
            # Launch a single browser instance shared across requests
            # headless controlled by environment variable for easier debugging
            _browser = await _playwright.chromium.launch(
                channel="chromium", headless=PLAYWRIGHT_HEADLESS
            )
            logger.info("Playwright started and browser launched")
        except Exception as e:
            logger.exception("Failed to start Playwright: %s", e)
            # Ensure globals are reset on failure
            _playwright = None
            _browser = None
            raise


async def _shutdown() -> None:
    """Gracefully stop Playwright and close the browser.

    Shutdown may fail if the driver already exited; log and continue.
    """
    global _playwright, _browser
    # Try to wait briefly for in-flight page tasks to finish by acquiring
    # all semaphore permits. This reduces TargetClosedError noise when
    # the browser is closed while pages are still being used.
    if _browser:
        try:
            # Attempt to acquire all permits with a small total timeout.
            total_permits = max(1, MAX_CONCURRENT_PAGES)
            per_attempt = 5.0 / total_permits
            for _ in range(total_permits):
                try:
                    await asyncio.wait_for(_semaphore.acquire(), timeout=per_attempt)
                except asyncio.TimeoutError:
                    logger.warning(
                        "Timed out waiting for active pages to finish before shutdown"
                    )
                    break

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
async def lifespan(app):
    await _ensure_startup()
    try:
        yield
    finally:
        await _shutdown()


def get_browser() -> Optional[Browser]:
    return _browser


def get_playwright() -> Optional[Playwright]:
    return _playwright


def get_semaphore() -> asyncio.BoundedSemaphore:
    return _semaphore
