"""Document-related Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentBase(BaseModel):
    """Base document schema."""

    filename: str


class DocumentResponse(BaseModel):
    """Response schema for document."""

    id: uuid.UUID
    filename: str
    status: DocumentStatus
    page_count: int | None
    error_message: str | None
    metadata: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
