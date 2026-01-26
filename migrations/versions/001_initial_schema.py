"""Initial schema with jobs, documents, chunks tables.

Revision ID: 001
Revises:
Create Date: 2026-01-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create jobs table
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "partial", "failed", name="jobstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "completed", "failed", name="documentstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])

    # Create chunks table
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create HNSW index for vector similarity search
    op.execute(
        """
        CREATE INDEX chunks_embedding_idx ON chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )

    # Create GIN index for full-text search
    op.execute(
        """
        CREATE INDEX chunks_content_fts_idx ON chunks
        USING gin (to_tsvector('english', content))
        """
    )


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("jobs")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS jobstatus")
