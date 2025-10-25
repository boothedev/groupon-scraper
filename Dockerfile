# Minimal Dockerfile for the Playwright FastAPI scraper
# Uses a Python base image and installs Playwright browsers with system deps

FROM python:3.10-slim

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser

# Install system deps for Playwright
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 \
       libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libcups2 libxss1 libgtk-3-0 \
       ca-certificates curl gnupg --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Use a shared, system-wide Playwright browsers location so browsers
# installed at build time are visible to the non-root runtime user.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Playwright browsers (with dependencies) into $PLAYWRIGHT_BROWSERS_PATH
RUN python -m playwright install --with-deps chromium \
    && chown -R appuser:appuser $PLAYWRIGHT_BROWSERS_PATH

# Copy app code
COPY . /home/appuser
RUN chown -R appuser:appuser /home/appuser
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Healthcheck: ensure the app responds on /health. Uses curl (installed above).
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["uvicorn", "groupon_scraper:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
