# Imagen de producción para InsuMeal API (FastAPI + Uvicorn)
# Build:  docker build -t insumeal-backend:latest .
# Run:    docker run --rm -p 8000:8000 --env-file .env insumeal-backend:latest
#
# Contexto de build: directorio backend/ (este archivo va junto a requirements.txt).

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime mínimo: cliente PostgreSQL (psycopg2) e imágenes (Pillow)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Raíz HTTP para comprobar que el proceso responde (útil con docker run)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)" || exit 1

CMD ["uvicorn", "__init__:app", "--host", "0.0.0.0", "--port", "8000"]
