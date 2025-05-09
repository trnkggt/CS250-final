FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTE=1
ENV UV_LINK_MODE=copy
ENV UV_VENV=disabled
ENV UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY ./pyproject.toml ./uv.lock /app/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM base AS final

COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh

RUN chmod +x /app/scripts/entrypoint.sh

RUN adduser --disabled-password --gecos "" --home /home/appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["/app/scripts/entrypoint.sh"]


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
