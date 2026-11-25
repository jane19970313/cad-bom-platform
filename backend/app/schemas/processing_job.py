from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProcessingJobResponse(BaseModel):
    id: UUID
    drawing_id: UUID
    status: str
    task_id: str | None
    attempt_count: int
    error_message: str | None
    result_summary: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProcessingJobListResponse(BaseModel):
    items: list[ProcessingJobResponse]
    total: int
