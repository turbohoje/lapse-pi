FROM python:3.12-slim

WORKDIR /app

# Install deps first (cached layer unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrape.py .

# Run as non-root
RUN useradd -r -u 1001 scraper
USER scraper

CMD ["python", "-u", "scrape.py"]