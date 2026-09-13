from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UploadCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    purpose: Literal["avatar", "topic_cover", "post_cover", "organization_evidence"]
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    size: int = Field(gt=0, le=15 * 1024 * 1024)


class UploadAttachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: int | None = Field(default=None, gt=0)
