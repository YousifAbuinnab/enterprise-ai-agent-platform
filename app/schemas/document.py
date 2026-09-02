from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Document metadata returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    file_path: str
    created_at: datetime
