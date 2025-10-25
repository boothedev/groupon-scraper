"""Application entrypoint.

This file is intentionally small: lifecycle, scraping, and HTTP
handlers live in their own modules for readability and testability.
"""

import logging
from fastapi import FastAPI

from . import routes
from .playwright_manager import lifespan


app = FastAPI(lifespan=lifespan, redirect_slashes=False)
app.include_router(routes.router)

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)
