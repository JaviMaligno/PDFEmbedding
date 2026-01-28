# PostgreSQL Optimization Notes

Observaciones basadas en el artículo de OpenAI sobre escalado de PostgreSQL.

**Fuente:** [Scaling PostgreSQL at OpenAI](https://openai.com/index/scaling-postgresql/)

**Estado:** Completamente implementado

---

## Contexto

OpenAI escala PostgreSQL a 1M+ queries/segundo para ChatGPT usando:
- PgBouncer para connection pooling (redujo latencia de 50ms a 5ms)
- 50 read replicas para distribuir carga
- Lazy writes para reducir presión en escrituras
- Query optimization agresiva

Este documento identifica qué técnicas aplican a nuestro sistema actual.

---

## 1. Query Optimization

### 1.1 Índices actuales (correctos)

```sql
-- Vector search (HNSW)
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);

-- Full-text search (GIN)
CREATE INDEX chunks_content_fts_idx ON chunks USING gin (to_tsvector('english', content));

-- Deduplicación
CREATE INDEX ix_documents_file_hash ON documents(file_hash);
```

### 1.2 Índices adicionales

```sql
-- Acelera JOIN en búsquedas híbridas (vector + BM25)
CREATE INDEX ix_chunks_document_id ON chunks(document_id);  -- ✅ IMPLEMENTADO (migración 002)

-- Acelera consultas de estado de job
CREATE INDEX ix_documents_job_id ON documents(job_id);  -- ✅ IMPLEMENTADO (migración 003)
```

**Impacto esperado:** Medio. Evita sequential scans en tablas chunks/documents cuando crecen.

### 1.3 Cómo verificar uso de índices

```sql
EXPLAIN ANALYZE
SELECT c.id, c.content, d.filename
FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE c.embedding IS NOT NULL
ORDER BY c.embedding <=> '[...]'::vector
LIMIT 10;
```

Buscar en el output:
- `Index Scan` = bueno
- `Seq Scan` = potencial problema si la tabla es grande

---

## 2. Lazy Writes

### 2.1 Bulk insert ✅ IMPLEMENTADO

**Ubicación:** `app/workers/tasks.py:finalize_document()`

```python
# Implementado - 1 query de INSERT con db.add_all()
chunks = [
    Chunk(
        document_id=doc.id,
        chunk_index=chunk_data["chunk_index"],
        page_number=None,
        content=chunk_data["content"],
        token_count=chunk_data["token_count"],
        embedding=embedding,
    )
    for chunk_data, embedding in zip(chunks_data, embeddings)
]
db.add_all(chunks)
```

**Impacto:** Alto para documentos con muchos chunks. Reduce N round-trips a 1.

**Commit:** `8521b7d`

### 2.2 COUNT en base de datos ✅ IMPLEMENTADO

**Ubicación:** `app/workers/tasks.py:finalize_document()`

```python
# Implementado - COUNT en DB en lugar de traer filas
from sqlalchemy import func

completed = db.execute(
    select(func.count())
    .select_from(Document)
    .where(Document.job_id == job.id, Document.status == DocumentStatus.COMPLETED)
).scalar()

failed = db.execute(
    select(func.count())
    .select_from(Document)
    .where(Document.job_id == job.id, Document.status == DocumentStatus.FAILED)
).scalar()
```

**Impacto:** Bajo-medio. Relevante cuando un job tiene muchos documentos.

**Commit:** `35f5e5c`

### 2.3 Consolidar commits ✅ IMPLEMENTADO

**Ubicación:** `app/workers/tasks.py:finalize_document()`

```python
# Implementado - 1 solo commit al final
doc.status = DocumentStatus.COMPLETED
job.processed_files += 1
# ... actualizar job.status ...
db.commit()  # Solo 1 commit
```

**Impacto:** Bajo. Reduce latencia de red pero no crítico.

---

## 3. Técnicas de OpenAI NO aplicables (aún)

| Técnica | Por qué no aplica |
|---------|-------------------|
| PgBouncer | asyncpg ya tiene pooling interno; útil cuando hay muchos workers Celery |
| Read replicas | Requiere escala que justifique el costo operacional |
| Priority routing | Solo necesario con múltiples réplicas |
| Sharding | OpenAI tampoco lo usa; escalan verticalmente |

---

## 4. Estado de implementación

| Optimización | Estado | Commit/Migración |
|--------------|--------|------------------|
| Bulk insert | ✅ Implementado | `8521b7d` |
| COUNT en DB | ✅ Implementado | `35f5e5c` |
| Índice `chunks.document_id` | ✅ Implementado | migración `002` |
| Índice `documents.job_id` | ✅ Implementado | migración `003` |
| Consolidar commits | ✅ Implementado | `11d9eb6` |

---

## Referencias

- [OpenAI: Scaling PostgreSQL](https://openai.com/index/scaling-postgresql/)
- [PgBouncer for PostgreSQL](https://www.percona.com/blog/pgbouncer-for-postgresql-how-connection-pooling-solves-enterprise-slowdowns/)
- [POSETTE 2025: Scaling Postgres at OpenAI](https://posetteconf.com/2025/talks/scaling-postgres-to-the-next-level-at-openai/)
