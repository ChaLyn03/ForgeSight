from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    inspection_id: str
    storage_key: str
    original_filename: str | None = None
    content_type: str | None = None
    file_size: int | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    created_at: datetime | None = None
