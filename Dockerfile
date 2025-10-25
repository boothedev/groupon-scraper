# Minimal Dockerfile for the Playwright FastAPI scraper
# Uses a Python base image and installs Playwright browsers with system deps

FROM python:3.14-slim

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

# Install Playwright browsers (with dependencies)
RUN python -m playwright install --with-deps chromium

# Copy app code
COPY . /home/appuser
RUN chown -R appuser:appuser /home/appuser
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
