# Playwright Scraper (FastAPI)

Lightweight Playwright-backed scraper exposing a small HTTP API to search Groupon and return a brief summary of the first matching deal.

This repository focuses on:

- Core Python async design using FastAPI
- Playwright automation for scraping
- Reliability: bounded concurrency, graceful startup/shutdown, clear logging
- Deployment readiness notes and reproducible environment entry points

## Quick overview

- Endpoint: `GET /search?query=...&sort_option=...&price_min=...&price_max=...`
- Returns JSON: `{ "success": true, "data": <brief item info> }` or a proper HTTP error code
- Uses a single browser instance and limits concurrent page usage with a bounded semaphore

## Requirements

- Python 3.10+
- Playwright (Python) and browsers installed

Recommended packages are listed in `requirements.txt`.

## Setup (local)

1. Create and activate a virtual environment (example using fish shell):

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
uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info
```

4. Example request:

```
GET http://localhost:8000/search?query=coffee
```

## Design notes

- Single browser instance: the app starts Playwright and launches one shared browser at startup and stops it on shutdown.
- Bounded concurrency: an `asyncio.BoundedSemaphore` prevents resource exhaustion when many clients call the API concurrently.
- Robustness: startup/shutdown code logs and resets globals on errors. Endpoint captures Playwright timeouts and general exceptions and maps them to appropriate HTTP statuses.

## Deployment readiness

- Use a process manager (systemd, supervisor) or containerize. When containerizing, ensure Playwright dependencies and browsers are installed in the image.
- Example: use the official Python base image and run `playwright install --with-deps` as part of your Dockerfile.

### Docker (example)

This repository includes a minimal `Dockerfile` that installs dependencies and Playwright's Chromium browser. Build and run:

```bash
# build
docker build -t playwright-scraper:latest .

# run (bind to port 8000)
docker run --rm -p 8000:8000 --name playwright-scraper playwright-scraper:latest
```

Notes:

- The Dockerfile installs system dependencies required by browsers; see the `Dockerfile` for details.
- For smaller images or production, consider using multi-stage builds and trimming unnecessary packages.

Security & operational notes

- Avoid running browsers as root in production. Use a minimal privileged user.
- Monitor memory and CPU usage: headless browsers can be resource heavy.

## Testing

- Lightweight unit/integration tests can be added under `tests/`. Be aware that integration tests exercising the real Playwright browser require browsers to be installed and are slower.

## Git & development

- Branch & commit small changes; keep PRs focused.
- Use the provided `.gitignore` to avoid committing virtualenvs and caches.

## Next steps / improvements

- Add structured logging (JSON) and request tracing
- Add rate limiting and authentication for public deployment
- Add lightweight integration test harness that can optionally stub Playwright for CI

---

If you'd like, I can also add a Dockerfile and a minimal test that mocks Playwright to keep CI fast — tell me which you'd prefer next.
