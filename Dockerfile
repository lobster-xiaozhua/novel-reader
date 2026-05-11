FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY backend/requirements-pure-python.txt ./requirements.txt

RUN pip install --no-cache-dir --target=/app/data/cache/python-packages -r requirements.txt || \
    pip install --no-cache-dir --target=/app/data/cache/python-packages -r backend/requirements.txt

COPY backend/ ./backend/
COPY data/ ./data/
COPY .env.example ./.env

RUN mkdir -p data/{books,index,static,logs,cache,backups,versions}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPYCACHEPREFIX=/app/data/cache/__pycache__
ENV PYTHONPATH=/app/data/cache/python-packages:/app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
