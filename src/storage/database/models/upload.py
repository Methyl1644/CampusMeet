import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from storage.database.shared.model import Base


class UploadRecord(Base):
    __tablename__ = "uploads"
    __table_args__ = (
        Index("ix_uploads_owner_status_created", "owner_id", "status", "created_at"),
        Index("ix_uploads_object_key", "object_key", unique=True),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    expected_size: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_size: Mapped[int | None] = mapped_column(Integer)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    attached_to_type: Mapped[str | None] = mapped_column(Text)
    attached_to_id: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="s3", server_default="s3")
    cloudinary_asset_id: Mapped[str | None] = mapped_column(Text)
    cloudinary_public_id: Mapped[str | None] = mapped_column(Text)
    cloudinary_resource_type: Mapped[str | None] = mapped_column(Text)
    cloudinary_delivery_type: Mapped[str | None] = mapped_column(Text)
    cloudinary_format: Mapped[str | None] = mapped_column(Text)
    cloudinary_version: Mapped[int | None] = mapped_column(Integer)
    cloudinary_secure_url: Mapped[str | None] = mapped_column(Text)
