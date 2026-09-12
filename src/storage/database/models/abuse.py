import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


class AbuseEvent(Base):
    __tablename__ = "abuse_events"
    __table_args__ = (
        Index("ix_abuse_events_user_type_created", "user_id", "event_type", "created_at"),
        Index("ix_abuse_events_network_type_created", "network_hash", "event_type", "created_at"),
        Index("ix_abuse_events_fingerprint_created", "content_fingerprint", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[str | None] = mapped_column(Text)
    content_fingerprint: Mapped[str | None] = mapped_column(Text)
    network_hash: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, nullable=False, default="allow")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
