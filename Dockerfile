FROM ghcr.io/astral-sh/uv:0.13.5 AS uv
FROM python:3.11.17-slim

COPY --from=uv /uv /uvx /usr/local/bin/
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system dependencies for PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install the committed dependency graph before building the local application.
# No bundled pip is executed during dependency installation.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Hatch needs app/ in the build context, not just pyproject.toml.
COPY app/ app/
COPY README.md ./
RUN uv sync --frozen --no-dev

# Copy migrations
COPY alembic.ini .
COPY migrations/ migrations/

# Create storage directory
RUN mkdir -p /data/pdfs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
