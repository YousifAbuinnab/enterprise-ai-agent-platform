from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerCreate(BaseModel):
    """Payload for creating a new customer."""

    name: str
    email: EmailStr
    company: str | None = None


class CustomerRead(BaseModel):
    """Customer representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    company: str | None
    created_at: datetime
