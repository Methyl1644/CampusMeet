import datetime
from sqlalchemy import BigInteger, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    activity_name: Mapped[str] = mapped_column(Text, nullable=False)
    division_of_labor: Mapped[list] = mapped_column(JSON, default=list)
    meeting_agenda: Mapped[list] = mapped_column(JSON, default=list)
    task_list: Mapped[list] = mapped_column(JSON, default=list)
    risk_reminders: Mapped[list] = mapped_column(JSON, default=list)
    contact_info: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    suggested_role: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
