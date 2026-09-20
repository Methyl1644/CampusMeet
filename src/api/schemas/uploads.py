from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UploadCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    purpose: Literal["avatar", "topic_cover", "post_cover", "organization_evidence"]
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=100)
    size: int = Field(gt=0, le=15 * 1024 * 1024)


class UploadCompleteRequest(BaseModel):
    """Whitelisted Cloudinary upload result.

    Only fields the server needs to cross-check are accepted; `secure_url` is
    deliberately absent because delivery URLs are rebuilt from server-side
    metadata instead of being trusted from the browser.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    public_id: str | None = Field(default=None, min_length=1, max_length=255)
    version: int | None = Field(default=None, ge=0, le=2_147_483_647)
    signature: str | None = Field(default=None, min_length=1, max_length=128)
    asset_id: str | None = Field(default=None, min_length=1, max_length=128)
    resource_type: str | None = Field(default=None, max_length=32)
    type: str | None = Field(default=None, max_length=32)
    format: str | None = Field(default=None, max_length=32)
    bytes: int | None = Field(default=None, ge=0, le=15 * 1024 * 1024)


class UploadAttachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: int | None = Field(default=None, gt=0)
