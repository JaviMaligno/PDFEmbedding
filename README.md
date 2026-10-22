# PDF Embedding Service

A service that ingests PDF documents, extracts their text content, builds searchable embeddings, and supports semantic search queries over the ingested corpus.

## Features

- **PDF Ingestion**: Upload multiple PDFs for async processing
- **Smart OCR**: Uses LLM vision (Gemini/DeepSeek) for scanned documents
- **Hybrid Search**: Combines BM25 keyword search with vector similarity
- **Observability**: Prometheus metrics + Grafana dashboards

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Gemini or DeepSeek API key (for OCR)

### Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your API keys
3. Start the services:

```bash
docker-compose up -d
```

4. Run migrations:

```bash
docker-compose exec api alembic upgrade head
```

5. Access the API at http://localhost:8000

## API Endpoints

### POST /upload

Upload PDF files for processing.

```bash
curl -X POST http://localhost:8000/upload \
  -F "files=@document.pdf"
```

### GET /jobs/{job_id}/status

Check processing status.

```bash
curl http://localhost:8000/jobs/{job_id}/status
```

### POST /search

Search documents.

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your search query", "limit": 10}'
```

## Architecture

See [docs/plans/2026-01-26-pdf-embedding-service-design.md](docs/plans/2026-01-26-pdf-embedding-service-design.md) for detailed architecture documentation.

## Development

### Reproducible security environment

The committed `uv.lock` is newly resolved from this repository's manifest, rather
than copied from an existing local checkout. It is intentionally tracked now;
refresh it with uv 0.13.5 and review the dependency diff before committing.

The container uses Python 3.11.17 and uv 0.13.5 with `uv sync --frozen --no-dev`.
It copies `app/` before building the local wheel, and does not execute bundled pip.
For an isolated local setup, run `uv sync --frozen` with Python 3.11.17. Installing
dependencies does not require provider keys; starting services and migrations do.

The locked security cohort retains FastAPI 0.136.3 / Starlette 1.3.1 and the
PyMuPDF 1.x API. Resolver and wheel checks establish packaging and dependency
consistency, not database, OCR-provider or deployed-service correctness.

### Running Tests

```bash
pytest tests/ -v
```

### Running Locally

```bash
# Install dependencies
pip install -e ".[dev]"

# Start dependencies
docker-compose up -d postgres redis

# Run API
uvicorn app.main:app --reload

# Run worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

## Monitoring

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## License

MIT
