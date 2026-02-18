# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY src ./src
COPY fuel-prices-for-be-assessment.csv ./fuel-prices-for-be-assessment.csv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM base AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/
RUN groupadd --system app && useradd --system --gid app --create-home app

COPY --from=builder --chown=app:app /app /app
COPY --chown=app:app docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /app/data /app/staticfiles && chown -R app:app /app/data /app/staticfiles

USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--access-logfile", "-"]
