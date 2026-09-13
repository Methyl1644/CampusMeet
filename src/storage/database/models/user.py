import datetime
from sqlalchemy import CheckConstraint, DateTime, Integer, JSON, Text, func, literal_column
from sqlalchemy.orm import Mapped, mapped_column
from storage.database.shared.model import Base
from storage.database.shared.types import BIGINT_PRIMARY_KEY


DEFAULT_NOTIFICATION_PREFERENCES = {
    "applications": True,
    "teams": True,
    "moderation": True,
    "deadlines": True,
    "messages": True,
}
NOTIFICATION_PREFERENCES_MAX_BYTES = 512
SQLITE_NOTIFICATION_PREFERENCES_CHECK = (
    "json_valid(notification_preferences) "
    "AND json_type(notification_preferences) = 'object' "
    "AND json_type(notification_preferences, '$.applications') IS NOT NULL "
    "AND json_type(notification_preferences, '$.applications') IN ('true', 'false') "
    "AND json_type(notification_preferences, '$.teams') IS NOT NULL "
    "AND json_type(notification_preferences, '$.teams') IN ('true', 'false') "
    "AND json_type(notification_preferences, '$.moderation') IS NOT NULL "
    "AND json_type(notification_preferences, '$.moderation') IN ('true', 'false') "
    "AND json_type(notification_preferences, '$.deadlines') IS NOT NULL "
    "AND json_type(notification_preferences, '$.deadlines') IN ('true', 'false') "
    "AND json_type(notification_preferences, '$.messages') IS NOT NULL "
    "AND json_type(notification_preferences, '$.messages') IN ('true', 'false') "
    "AND json_remove(notification_preferences, '$.applications', '$.teams', "
    "'$.moderation', '$.deadlines', '$.messages') = '{}' "
    f"AND length(CAST(notification_preferences AS BLOB)) <= {NOTIFICATION_PREFERENCES_MAX_BYTES}"
)
POSTGRESQL_NOTIFICATION_PREFERENCES_CHECK = (
    "jsonb_typeof(notification_preferences::jsonb) = 'object' "
    "AND notification_preferences::jsonb ?& ARRAY['applications', 'teams', "
    "'moderation', 'deadlines', 'messages'] "
    "AND (notification_preferences::jsonb - 'applications' - 'teams' - "
    "'moderation' - 'deadlines' - 'messages') = '{}'::jsonb "
    "AND jsonb_typeof(notification_preferences::jsonb -> 'applications') = 'boolean' "
    "AND jsonb_typeof(notification_preferences::jsonb -> 'teams') = 'boolean' "
    "AND jsonb_typeof(notification_preferences::jsonb -> 'moderation') = 'boolean' "
    "AND jsonb_typeof(notification_preferences::jsonb -> 'deadlines') = 'boolean' "
    "AND jsonb_typeof(notification_preferences::jsonb -> 'messages') = 'boolean' "
    f"AND octet_length(notification_preferences::text) <= {NOTIFICATION_PREFERENCES_MAX_BYTES}"
)


def default_notification_preferences() -> dict[str, bool]:
    return dict(DEFAULT_NOTIFICATION_PREFERENCES)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            SQLITE_NOTIFICATION_PREFERENCES_CHECK,
            name="ck_users_notification_preferences_bounded",
        ).ddl_if(dialect="sqlite"),
        CheckConstraint(
            POSTGRESQL_NOTIFICATION_PREFERENCES_CHECK,
            name="ck_users_notification_preferences_bounded",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text, unique=True)
    wechat: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    avatar: Mapped[str | None] = mapped_column(Text)
    major: Mapped[str | None] = mapped_column(Text)
    grade: Mapped[str | None] = mapped_column(Text)
    onboarding_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    onboarding_completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    bio: Mapped[str | None] = mapped_column(Text)
    interests: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    looking_for: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    availability: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    profile_visibility: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notification_preferences: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=default_notification_preferences,
        server_default=literal_column(
            "'{\"applications\":true,\"teams\":true,\"moderation\":true,"
            "\"deadlines\":true,\"messages\":true}'"
        ),
    )
    skills: Mapped[list] = mapped_column(JSON, default=list)
    auth_status: Mapped[str] = mapped_column(Text, nullable=False, default="unverified")
    site_role: Mapped[str] = mapped_column(Text, nullable=False, default="student")
    account_status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    deactivated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    verified_email: Mapped[str | None] = mapped_column(Text, unique=True)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    team_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
