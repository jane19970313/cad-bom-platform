from datetime import datetime

from pydantic import BaseModel, ConfigDict
from uuid import UUID

class ProjectCreate(BaseModel):

    name: str

    description: str | None = None


class ProjectResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    name: str

    description: str | None

    owner_id: UUID

    created_at: datetime
