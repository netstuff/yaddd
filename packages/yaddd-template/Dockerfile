# syntax=docker/dockerfile:1

# Dependencies first: this layer is cached until pyproject.toml or uv.lock changes.
FROM ghcr.io/astral-sh/uv:0.9-python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies into a virtual environment the runtime stage copies.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    --mount=type=bind,source=app,target=app \
    uv sync --locked --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.13-slim-bookworm AS runtime

# Never run the application as root.
RUN useradd --create-home --uid 10001 app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    YADDD_API_HOST=0.0.0.0 \
    YADDD_API_PORT=8000 \
    YADDD_WORKER_HOST=0.0.0.0 \
    YADDD_WORKER_PORT=8001 \
    YADDD_DATABASE_URL=sqlite+aiosqlite:////data/yaddd-template.db

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

RUN mkdir -p /data && chown app:app /data
USER app
VOLUME ["/data"]

EXPOSE 8000 8001

# The API by default; override the command for the worker or the CLI:
#   docker run … broker
#   docker run … worker migrate
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live').read()"]

CMD ["api"]