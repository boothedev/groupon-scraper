"""Playwright lifecycle and browser manager.

This module centralizes Playwright startup/shutdown and exposes
helpers used by request handlers.
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from playwright.async_api import Playwright, Browser, async_playwright

logger = logging.getLogger("app.playwright")

# Config
MAX_CONCURRENT_PAGES = 4

# Use a bounded semaphore to avoid accidental growth of waiting tasks
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
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
    """Gracefully stop Playwright and close the browser.

    Shutdown may fail if the driver already exited; log and continue.
    """
    global _playwright, _browser
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
