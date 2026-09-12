import datetime
import json

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, JSON, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, validates
from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


TEAM_TASK_LIMIT = 12
TEAM_TASK_JSON_MAX_BYTES = 12_288
TEAM_TASK_FIELD_LIMITS = {
    "id": (64, 256),
    "title": (120, 480),
    "assignee_id": (64, 256),
    "assignee_name": (80, 320),
    "due_at": (40, 160),
    "deadline": (40, 160),
}

SQLITE_TEAM_TASK_CHECK = (
    "json_valid(task_list) "
    "AND json_type(task_list) = 'array' "
    f"AND json_array_length(task_list) <= {TEAM_TASK_LIMIT} "
    f"AND length(CAST(task_list AS BLOB)) <= {TEAM_TASK_JSON_MAX_BYTES}"
)
POSTGRESQL_TEAM_TASK_CHECK = (
    "jsonb_typeof(task_list::jsonb) = 'array' "
    f"AND jsonb_array_length(task_list::jsonb) <= {TEAM_TASK_LIMIT} "
    f"AND octet_length(task_list::text) <= {TEAM_TASK_JSON_MAX_BYTES}"
)


def _trim_task_string(value: object, *, max_chars: int, max_bytes: int) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()[:max_chars]
    if not trimmed:
        return None
    if len(trimmed.encode("utf-8")) > max_bytes:
        trimmed = trimmed.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
    return trimmed or None


def _serialized_task_bytes(value: list[dict[str, object]]) -> int:
    return len(json.dumps(value, ensure_ascii=True).encode("utf-8"))


def normalize_team_task_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, object]] = []
    for item in value:
        if len(normalized) >= TEAM_TASK_LIMIT:
            break
        if not isinstance(item, dict):
            continue

        task: dict[str, object] = {}
        for field, (max_chars, max_bytes) in TEAM_TASK_FIELD_LIMITS.items():
            trimmed = _trim_task_string(
                item.get(field),
                max_chars=max_chars,
                max_bytes=max_bytes,
            )
            if trimmed is not None:
                task[field] = trimmed
        if "id" not in task or "title" not in task:
            continue
        done = item.get("done", False)
        task["done"] = done if isinstance(done, bool) else False

        candidate = [*normalized, task]
        if _serialized_task_bytes(candidate) > TEAM_TASK_JSON_MAX_BYTES:
            break
        normalized = candidate
    return normalized


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        CheckConstraint(
            SQLITE_TEAM_TASK_CHECK,
            name="ck_teams_task_list_bounded",
        ).ddl_if(dialect="sqlite"),
        CheckConstraint(
            POSTGRESQL_TEAM_TASK_CHECK,
            name="ck_teams_task_list_bounded",
        ).ddl_if(dialect="postgresql"),
    )

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

    @validates("task_list")
    def _bound_task_list(self, _key: str, value: object) -> list[dict[str, object]]:
        return normalize_team_task_list(value)


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
