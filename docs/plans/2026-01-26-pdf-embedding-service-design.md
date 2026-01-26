# PDF Embedding Service Design

## Overview

A service that ingests PDF documents, extracts their text content, builds searchable embeddings, and supports semantic search queries over the ingested corpus.

**Goals:**
- Learn production-grade architecture patterns for document search systems
- Design for scale (millions of documents) while implementing affordably
- Deploy using Docker and affordable cloud services (Render/Railway)

## Architecture

### High-Level View

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌─────────────┐     ┌──────────────────────┐  │
│  │   FastAPI    │────▶│    Redis    │────▶│   Celery Workers     │  │
│  │   (API)      │     │   (Queue)   │     │   (PDF Processing)   │  │
│  └──────────────┘     └─────────────┘     └──────────────────────┘  │
│         │                                           │                │
│         │              ┌────────────────────────────┘                │
│         ▼              ▼                                             │
│  ┌─────────────────────────────────────┐                            │
│  │         PostgreSQL                   │                            │
│  │  ┌─────────┐ ┌─────────┐ ┌────────┐ │                            │
│  │  │pgvector │ │pg_search│ │ tables │ │                            │
│  │  └─────────┘ └─────────┘ └────────┘ │                            │
│  └─────────────────────────────────────┘                            │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────┐     ┌─────────────┐                               │
│  │  Prometheus  │────▶│   Grafana   │                               │
│  └──────────────┘     └─────────────┘                               │
│                                                                      │
│  ┌──────────────────────────────────────┐                           │
│  │      Local Volume (PDF Storage)       │                           │
│  └──────────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘

External APIs: OpenAI (embeddings), Gemini/DeepSeek (OCR)
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| API | FastAPI | HTTP endpoints (upload, status, search) |
| Queue | Redis | Message broker for Celery |
| Workers | Celery | Async PDF processing |
| Database | PostgreSQL + pgvector + pg_search | Documents, embeddings, full-text search |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Storage | Local volume / Docker volume | PDF file storage |

## API Endpoints

### POST /upload

Accepts one or more PDF files, stores them, and enqueues processing jobs.

**Request:** `multipart/form-data` with PDF files

**Response:**
```json
{
  "job_id": "uuid",
  "file_count": 3,
  "status": "pending"
}
```

### GET /jobs/{job_id}/status

Returns ingestion status, progress, and error details.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "partial",
  "progress": { "total": 5, "completed": 3, "failed": 2 },
  "files": [
    { "filename": "doc1.pdf", "status": "completed" },
    { "filename": "doc2.pdf", "status": "failed", "error": "Encrypted PDF" }
  ]
}
```

### POST /search

Executes hybrid semantic search over the document corpus.

**Request:**
```json
{
  "query": "contracts mentioning force majeure",
  "limit": 10,
  "threshold": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "uuid",
      "score": 0.89,
      "snippet": "...force majeure clauses shall apply...",
      "metadata": { "filename": "contract.pdf", "page": 12 }
    }
  ]
}
```

## Ingestion Pipeline

```
PDF File
    │
    ▼
Step 1: PDF → Images (pdf2image)
    │
    ▼
Step 2: Text Extraction
    ├── Try PyMuPDF direct extraction
    └── If <50 chars/page → LLM OCR (Gemini/DeepSeek)
    │
    ▼
Step 3: Chunking
    Split into ~512 token chunks with ~50 token overlap
    │
    ▼
Step 4: Embedding Generation
    OpenAI text-embedding-3-small (batch up to 2048)
    │
    ▼
Step 5: Store in PostgreSQL
    ├── Document metadata
    ├── Chunks + embeddings (pgvector)
    └── Full-text index (pg_search)
```

### Key Decisions

- **Smart OCR fallback:** Direct text extraction first (fast, free), LLM OCR only when needed
- **Chunking strategy:** 512 tokens balances context vs. granularity; overlap prevents losing context at boundaries
- **Batch embeddings:** OpenAI allows batching to reduce API calls
- **Pipeline as Celery chain:** Each step is a subtask; allows retrying individual steps

## Search System

### Hybrid Search (BM25 + Vector)

```
Query: "contracts mentioning force majeure"
    │
    ▼
Generate Query Embedding (OpenAI)
    │
    ▼
┌─────────────────────────────────────────┐
│       Parallel Search Execution          │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │ Vector      │    │ BM25 Search     │ │
│  │ Search      │    │ (pg_search)     │ │
│  │ (pgvector)  │    │                 │ │
│  │ Top 50      │    │ Top 50          │ │
│  └──────┬──────┘    └────────┬────────┘ │
│         └──────────┬─────────┘          │
│                    ▼                     │
│         Reciprocal Rank Fusion           │
│         score = Σ 1/(k + rank)          │
└─────────────────────────────────────────┘
    │
    ▼
Top N Results + Snippet Extraction
```

### Why Hybrid?

- **Vector search:** Captures semantic meaning ("legal protection" matches "force majeure")
- **BM25 search:** Exact keyword matching (critical for proper nouns, codes, acronyms)
- **RRF fusion:** Simple, effective way to combine rankings without tuning weights

### Performance Target (<500ms)

| Step | Expected Latency |
|------|------------------|
| Embedding generation | ~100-150ms |
| Parallel DB queries | ~50-100ms |
| RRF + response | ~10ms |
| **Total** | **~200-300ms** |

## Data Model

```sql
-- Jobs (batch uploads)
CREATE TABLE jobs (
    id              UUID PRIMARY KEY,
    status          VARCHAR(20),  -- pending, processing, completed, partial, failed
    total_files     INT,
    processed_files INT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Documents (individual PDFs)
CREATE TABLE documents (
    id              UUID PRIMARY KEY,
    job_id          UUID REFERENCES jobs(id),
    filename        VARCHAR(255),
    file_path       VARCHAR(500),
    file_hash       VARCHAR(64) UNIQUE,  -- SHA-256 for deduplication
    page_count      INT,
    status          VARCHAR(20),
    error_message   TEXT,
    metadata        JSONB,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Chunks (searchable text segments)
CREATE TABLE chunks (
    id              UUID PRIMARY KEY,
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT,
    page_number     INT,
    content         TEXT,
    token_count     INT,
    embedding       VECTOR(1536),  -- OpenAI text-embedding-3-small
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX chunks_embedding_idx ON chunks
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_content_idx ON chunks
    USING gin (to_tsvector('english', content));
CREATE INDEX documents_hash_idx ON documents (file_hash);
```

## Job Queue & Worker Design

### Queues

| Queue | Purpose | Rate Limit |
|-------|---------|------------|
| pdf_processing | Main pipeline | None |
| ocr_extraction | LLM API calls | 10/min |
| embedding_gen | OpenAI API calls | 60/min |

### Task Chain

```python
process_document.s(doc_id)
    │
    ├── extract_text.s(doc_id)           # retry: 3x, exponential backoff
    ├── run_ocr_if_needed.s(doc_id)      # retry: 3x, rate_limit: 10/min
    ├── chunk_text.s(doc_id)             # no retry (deterministic)
    ├── generate_embeddings.s(doc_id)    # retry: 3x, rate_limit: 60/min
    └── finalize_document.s(doc_id)      # cleanup temp files
```

### Worker Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Concurrency | 2-4 | Memory constrained |
| Prefetch | 1 | Long-running tasks |
| Acks late | true | Retry on worker crash |
| Task timeout | 10 min | Per document |

## Error Handling

### Error Categories

**Transient (retry):**
- API rate limits (429) → backoff + retry
- API timeouts → retry up to 3x
- Network failures → retry with backoff
- DB connection lost → retry after reconnect

**Permanent (fail document):**
- Corrupt/encrypted PDF → mark failed, log reason
- Unsupported format → mark failed, log reason
- Empty document (0 pages) → mark failed, log reason
- Max retries exceeded → mark failed, preserve error

### Job Status Logic

```
job.status = 'completed'  if ALL documents succeeded
job.status = 'partial'    if SOME documents failed
job.status = 'failed'     if ALL documents failed
```

## Observability

### Prometheus Metrics

**API Metrics:**
- `http_requests_total{endpoint, method, status}`
- `http_request_duration_seconds{endpoint}` [histogram]
- `search_latency_seconds` [histogram]

**Ingestion Metrics:**
- `jobs_total{status}`
- `documents_processed_total{status}`
- `document_processing_duration_seconds` [histogram]
- `pages_processed_total`
- `ocr_calls_total{provider, status}`

**Queue Metrics:**
- `celery_queue_length{queue_name}`
- `celery_active_tasks{queue_name}`
- `celery_task_duration_seconds{task_name}` [histogram]

**External API Metrics:**
- `openai_requests_total{endpoint, status}`
- `openai_latency_seconds` [histogram]
- `llm_ocr_requests_total{provider, status}`
- `llm_ocr_latency_seconds` [histogram]

### Grafana Dashboards

| Dashboard | Purpose |
|-----------|---------|
| Overview | Request rates, error rates, queue depth |
| Ingestion | Processing throughput, failure breakdown |
| Search | Latency percentiles (p50, p95, p99) |
| External APIs | Rate limit headroom, cost tracking |

## Deployment

### Local Development (Docker Compose)

```yaml
services:
  api:          # FastAPI (port 8000)
  worker:       # Celery workers (2 replicas)
  redis:        # Message broker (port 6379)
  postgres:     # DB + pgvector + pg_search (port 5432)
  prometheus:   # Metrics (port 9090)
  grafana:      # Dashboards (port 3000)

volumes:
  postgres_data:
  pdf_storage:
  grafana_data:
```

### Production (Render/Railway)

**Render:**
- Web Service → FastAPI
- Background Worker → Celery
- Redis → Render Redis (managed)
- PostgreSQL → Render Postgres (managed, pgvector support)
- Disk → Render Disk for PDFs

**Railway:**
- Service → FastAPI + Workers
- Redis → Railway Redis plugin
- PostgreSQL → Railway Postgres plugin
- Volume → Railway volume for PDFs

### Environment Variables

```
DATABASE_URL       # PostgreSQL connection string
REDIS_URL          # Redis connection string
OPENAI_API_KEY     # Embeddings
GEMINI_API_KEY     # OCR fallback
DEEPSEEK_API_KEY   # OCR alternative
PDF_STORAGE_PATH   # /data/pdfs
```

### Estimated Costs (Hobby Tier)

| Platform | Monthly Cost |
|----------|--------------|
| Render | ~$20-30 |
| Railway | ~$15-25 |

## Project Structure

```
pdf-embedding/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
│
├── app/
│   ├── main.py                  # FastAPI application
│   ├── config.py                # Settings (pydantic-settings)
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py        # POST /upload
│   │   │   ├── jobs.py          # GET /jobs/{id}/status
│   │   │   └── search.py        # POST /search
│   │   └── deps.py              # Dependencies
│   ├── models/                  # SQLAlchemy models
│   ├── schemas/                 # Pydantic schemas
│   ├── services/
│   │   ├── pdf_processor.py     # PDF → images, text extraction
│   │   ├── ocr_service.py       # Gemini/DeepSeek OCR
│   │   ├── embedding_service.py # OpenAI embeddings
│   │   ├── search_service.py    # Hybrid search logic
│   │   └── chunker.py           # Text chunking
│   └── workers/
│       ├── celery_app.py        # Celery configuration
│       └── tasks.py             # Task definitions
│
├── migrations/                  # Alembic migrations
├── tests/                       # Pytest tests
└── monitoring/
    ├── prometheus.yml
    └── grafana/                 # Dashboard JSONs
```

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ / FastAPI |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + pgvector + pg_search |
| PDF Processing | PyMuPDF + pdf2image |
| OCR | Gemini API / DeepSeek Vision API |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| Observability | Prometheus + Grafana |
| Deployment | Docker Compose (local) / Render or Railway (prod) |

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | Modular monolith | Simple, learnable, deployable on limited resources |
| Search | Hybrid (BM25 + vector) | Best of both worlds, single database |
| Queue | Celery + Redis | Industry standard, great for learning |
| OCR | LLM-based (Gemini/DeepSeek) | Modern approach, context-aware, cheap |
| Observability | Prometheus + Grafana | Industry standard, self-hosted |
