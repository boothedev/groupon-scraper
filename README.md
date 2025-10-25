# Groupon Scraper (Playwright + FastAPI)

Lightweight Playwright-backed scraper exposing a small HTTP API to search Groupon and return a brief summary of the first matching deal.

This repository focuses on:

- Core Python async design using FastAPI
- Playwright automation for scraping
- Reliability: bounded concurrency, graceful startup/shutdown, clear logging
- Deployment readiness notes and reproducible environment entry points

## Quick overview

## Design notes

- Single browser instance: the app starts Playwright and launches one shared browser at startup and stops it on shutdown.
- Bounded concurrency: an `asyncio.BoundedSemaphore` prevents resource exhaustion when many clients call the API concurrently.
- Robustness: startup/shutdown code logs and resets globals on errors. Endpoint captures Playwright timeouts and general exceptions and maps them to appropriate HTTP statuses.

### Search endpoint usage

Endpoint: GET /search?query=...&sort_option=...&price_min=...&price_max=...

Parameters

- query (string, required)
  - Free-text search term. Non-empty.
- sort_option (string, optional)
  - Allowed values:
    - `relevance`
    - `price:asc`
    - `price:desc`
    - `distance`
    - `rating`
- price_min (number, optional)
  - Minimum price filter (currency units, e.g., USD). Must be >= 0.
- price_max (number, optional)
  - Maximum price filter (currency units). If provided, must be >= price_min.

Validation and errors

- Missing or empty `query` → HTTP 400 Bad Request (validation error).
- Invalid `sort_option` → HTTP 400 Bad Request (list of allowed values returned).
- Non-numeric or negative prices, or `price_max < price_min` → HTTP 400 Bad Request.
- Playwright/navigation timeouts → appropriate 5xx or timeout-specific status (logged).

Response format

- Success (HTTP 200):

```
{
  "success": <bool>,
  "data": {
    "name": <string>,
    "prices": {
      "list_price": <int>,
      "sell_price": <int>,
      "discount": <int>,
      "isocode_currency": <int>,
      "currency_exponent": <int>
    },
    "supplier": <string>
  }
}
```

- Error: standard JSON error body with `success: false`, `error` message and HTTP error code.

Notes

- The handler uses a single shared Playwright browser and enforces concurrency limits (MAX_CONCURRENT_PAGES / asyncio.BoundedSemaphore) to prevent resource exhaustion.
- OpenAPI/Swagger will show the allowed `sort_option` values and parameter types when the app runs.

Example request
GET /search?query=laptop&price_max=100&sort_option=rating

Example success response

```
{
  "success":true,
  "data": {
    "name":"Lenovo 100E 2ND Gen - 11.6\" - 4GB Ram 16GB Storage - Scratch and Dent",
    "prices": {
        "list_price":31463,
        "sell_price":6499,
        "discount":79,
        "isocode_currency":"USD",
        "currency_exponent":2
    },
    "supplier":"Certified Pros"
  }
}
```

## Requirements

- Python 3.10+
- Playwright (Python) and browsers installed

Recommended packages are listed in `requirements.txt`.

## Setup (local)

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Install Playwright browsers (required once per machine):

```bash
python -m playwright install chromium
# or to install with system dependencies on Linux:
python -m playwright install chromium --with-deps
```

3. Run the app with Uvicorn (example):

```bash
uvicorn groupon_scraper:app --host 0.0.0.0 --port 8000 --log-level info
```

4. Example request:

```
GET http://127.0.0.1:8000/search?query=laptop&price_max=500&sort_option=rating
```

## Deployment readiness

- Use a process manager (systemd, supervisor) or containerize. When containerizing, ensure Playwright dependencies and browsers are installed in the image.
- Example: use the official Python base image and run `playwright install --with-deps` as part of your Dockerfile.

### Environment variables

- `MAX_CONCURRENT_PAGES` (default: `4`) - maximum concurrent pages the app will open.
- `PLAYWRIGHT_HEADLESS` (default: `1`) - `1` runs Chromium headless, `0` runs headed for debugging.
- `PAGE_GOTO_TIMEOUT_MS` (default: `60000`) - timeout (ms) for `page.goto` navigation.
- `PAGE_GOTO_RETRIES` (default: `2`) - number of attempts for `page.goto` before failing.
- `LOG_LEVEL` (default: `info`) - application log level.

An example `.env` with sensible defaults is included in the repository as `.env.example`.

### Docker (example)

This repository includes a minimal `Dockerfile` that installs dependencies and Playwright's Chromium browser. Build and run:

```bash
# build
docker build -t groupon-scraper:latest .

# run (bind to port 8000)
docker run --rm -p 8000:8000 --name groupon-scraper groupon-scraper:latest
```

## Healthchecks and container readiness

The provided `Dockerfile` exposes port `8000` and includes a `HEALTHCHECK` that queries `/health`. This helps platforms like Fly to detect readiness.
