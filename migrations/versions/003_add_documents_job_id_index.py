"""Add index on documents.job_id for faster job queries.

Revision ID: 003
Revises: 002
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_documents_job_id", "documents", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_job_id", table_name="documents")
