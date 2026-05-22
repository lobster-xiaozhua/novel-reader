FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci

COPY . .

RUN cd frontend && npm run build

RUN mkdir -p /app/data /app/data/logs /app/data/books /app/data/cache

RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000

CMD ["granian", "novel_reader.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--interface", "asgi", "--workers", "1"]
