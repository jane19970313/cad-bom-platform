from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DrawingResponse(BaseModel):
    id: UUID
    project_id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    checksum_sha256: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DrawingListResponse(BaseModel):
    items: list[DrawingResponse]
    total: int