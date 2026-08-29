import datetime
from sqlalchemy import BigInteger, DateTime, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text, unique=True)
    wechat: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    avatar: Mapped[str | None] = mapped_column(Text)
    major: Mapped[str | None] = mapped_column(Text)
    grade: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    auth_status: Mapped[str] = mapped_column(Text, nullable=False, default="unverified")
    verified_email: Mapped[str | None] = mapped_column(Text)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    team_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
