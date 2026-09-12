import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, JSON, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, unique=True)
    owner_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    activity_name: Mapped[str] = mapped_column(Text, nullable=False)
    division_of_labor: Mapped[list] = mapped_column(JSON, default=list)
    meeting_agenda: Mapped[list] = mapped_column(JSON, default=list)
    task_list: Mapped[list] = mapped_column(JSON, default=list)
    risk_reminders: Mapped[list] = mapped_column(JSON, default=list)
    contact_info: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
        Index("ix_team_members_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    suggested_role: Mapped[str | None] = mapped_column(Text)
    member_role: Mapped[str] = mapped_column(Text, nullable=False, default="member")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
