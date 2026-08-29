import datetime
from sqlalchemy import BigInteger, DateTime, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    main_category: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    activity_name: Mapped[str] = mapped_column(Text, nullable=False)
    current_members: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_members: Mapped[int] = mapped_column(Integer, nullable=False)
    needed_roles: Mapped[list] = mapped_column(JSON, default=list)
    weekly_hours: Mapped[str | None] = mapped_column(Text)
    school_scope: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="low")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="recruiting")
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
