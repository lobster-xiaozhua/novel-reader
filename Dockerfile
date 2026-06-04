FROM node:22-slim AS frontend
WORKDIR /build
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci --registry https://registry.npmmirror.com
COPY frontend/ frontend/
RUN cd frontend && npm run build

FROM python:3.12-slim AS backend
WORKDIR /app
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY . .
COPY --from=frontend /build/frontend/dist /app/frontend/dist
RUN mkdir -p /app/data /app/data/logs /app/data/books /app/data/cache
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000
CMD ["granian", "novel_reader.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--interface", "asginl", "--workers", "2"]
