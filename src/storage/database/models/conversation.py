import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_conversation_application"),
        Index("ix_conversations_author_last", "post_author_id", "last_message_at"),
        Index("ix_conversations_applicant_last", "applicant_id", "last_message_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    post_author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    application_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("applications.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    contact_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    author_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applicant_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_message: Mapped[str | None] = mapped_column(Text)
    last_message_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
