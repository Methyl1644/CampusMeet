import datetime
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_author_created", "author_id", "created_at"),
        Index("uq_posts_author_request", "author_id", "client_request_id", unique=True),
        Index("ix_posts_topic_status", "topic_id", "status"),
        Index(
            "uq_posts_effective_official_signup_topic",
            "topic_id",
            unique=True,
            sqlite_where=text(
                "topic_id IS NOT NULL AND purpose = 'official_signup' "
                "AND status IN ('recruiting', 'full')"
            ),
            postgresql_where=text(
                "topic_id IS NOT NULL AND purpose = 'official_signup' "
                "AND status IN ('recruiting', 'full')"
            ),
        ),
        CheckConstraint(
            "purpose IN ('team_recruitment', 'official_signup', 'discussion')",
            name="ck_posts_purpose",
        ),
        CheckConstraint(
            "join_mode IN ('application', 'direct', 'none')",
            name="ck_posts_join_mode",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cover_url: Mapped[str | None] = mapped_column(Text)
    client_request_id: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    kind: Mapped[str] = mapped_column(Text, nullable=False, default="casual_invitation")
    purpose: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="team_recruitment",
        server_default="team_recruitment",
    )
    join_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="application",
        server_default="application",
    )
    topic_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("topics.id", ondelete="SET NULL"))
    main_category: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    activity_name: Mapped[str] = mapped_column(Text, nullable=False)
    current_members: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_members: Mapped[int] = mapped_column(Integer, nullable=False)
    needed_roles: Mapped[list] = mapped_column(JSON, default=list)
    weekly_hours: Mapped[str | None] = mapped_column(Text)
    school_scope: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[str | None] = mapped_column(Text)
    deadline_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="low")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="recruiting")
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    closed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PostBookmark(Base):
    __tablename__ = "post_bookmarks"
    __table_args__ = (
        Index("ix_post_bookmarks_user_created", "user_id", "created_at", "post_id"),
    )

    post_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
