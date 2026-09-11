import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    display_color: Mapped[str] = mapped_column(Text, nullable=False, default="gray")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TagAlias(Base):
    __tablename__ = "tag_aliases"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="curated")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TagProposal(Base):
    __tablename__ = "tag_proposals"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    proposed_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_tag_id: Mapped[str | None] = mapped_column(ForeignKey("tags.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    submitted_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    review_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    org_type: Mapped[str] = mapped_column(Text, nullable=False)
    school_scope: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    verified_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),)

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="member")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    invited_by: Mapped[int | None] = mapped_column(BigInteger)
    effective_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationApplication(Base):
    __tablename__ = "organization_applications"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    organization_name: Mapped[str] = mapped_column(Text, nullable=False)
    org_type: Mapped[str] = mapped_column(Text, nullable=False)
    official_email: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger)
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("organizer_key", "canonical_event_key", "edition", name="uq_topic_event_edition"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    short_title: Mapped[str] = mapped_column(Text, nullable=False)
    organizer: Mapped[str] = mapped_column(Text, nullable=False)
    organizer_key: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_event_key: Mapped[str] = mapped_column(Text, nullable=False)
    edition: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_status: Mapped[str] = mapped_column(Text, nullable=False, default="verified")
    cover_url: Mapped[str | None] = mapped_column(Text)
    registration_deadline: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    activity_start_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    activity_end_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    organization_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("organizations.id"))
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TopicTag(Base):
    __tablename__ = "topic_tags"

    topic_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("topics.id"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(Text, ForeignKey("tags.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="operator")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class PostTag(Base):
    __tablename__ = "post_tags"

    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id"), primary_key=True)
    tag_id: Mapped[str] = mapped_column(Text, ForeignKey("tags.id"), primary_key=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="user")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class TopicFollow(Base):
    __tablename__ = "topic_follows"

    topic_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("topics.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
