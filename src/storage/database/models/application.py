import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, JSON, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index(
            "uq_active_application_per_post_user",
            "post_id",
            "applicant_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'accepted')"),
            postgresql_where=text("status IN ('pending', 'accepted')"),
        ),
        Index("ix_applications_applicant_created", "applicant_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    role_wanted: Mapped[str] = mapped_column(Text, nullable=False)
    experience: Mapped[str] = mapped_column(Text, nullable=False)
    available_time: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    withdrawn_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
