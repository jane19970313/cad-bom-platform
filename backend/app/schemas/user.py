from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID

class UserResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    email: EmailStr

    is_active: bool
