FROM python:3.14-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project


FROM python:3.14-slim-trixie

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /usr/local /usr/local

COPY alembic.ini ./
COPY migrations ./migrations
COPY templates ./templates
COPY backend ./backend

EXPOSE 8010

CMD ["python", "-m", "backend.main"]
