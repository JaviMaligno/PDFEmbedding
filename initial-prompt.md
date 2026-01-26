Design a service that ingests PDF documents, extracts their text content, builds searchable embeddings, and supports semantic search queries over the ingested corpus.

Endpoints

POST /upload — client submits one or more PDF files; returns a job_id.

GET /jobs/{job_id}/status — returns ingestion status, progress, and any error details.

POST /search — client submits a natural language query; returns a ranked list of document IDs and matching text snippets.

Key Constraints

Scale: corpus may grow to millions of documents (multiple terabytes of text).

Ingestion pipeline: involves OCR and AI-based text extraction/classification; processing is slow and must be handled asynchronously with a job queue.

Search latency: typical queries should return results under 500 ms at peak load.

Error handling: pipeline steps (OCR, model calls) can fail or time out; system must retry and surface failures gracefully.

Observability: track job queue length, per-job latency, extraction success rates, and search request metrics.
