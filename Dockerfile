# syntax=docker/dockerfile:1.7
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /build/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    RECALLNEXT_STATIC_DIR=/app/frontend/dist

RUN addgroup --system recallnext && adduser --system --ingroup recallnext recallnext
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY backend/ backend/
COPY data/ data/
COPY planner/ planner/
COPY sql/ sql/
COPY --from=frontend-builder /build/frontend/dist/ frontend/dist/
RUN python -m pip install --no-cache-dir .

USER recallnext
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3).read()"]

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
