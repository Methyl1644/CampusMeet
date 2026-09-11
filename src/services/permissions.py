import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.database.models import (
    OrganizationMember,
    Post,
    PostCollaborator,
    Topic,
    TopicCollaborator,
    User,
)


TOPIC_ROLE_CAPABILITIES = {
    "coordinator": frozenset({"moderate_posts"}),
    "editor": frozenset({"moderate_posts", "edit_topic"}),
    "manager": frozenset({"moderate_posts", "edit_topic", "manage_collaborators"}),
}
POST_ROLE_CAPABILITIES = {
    "application_manager": frozenset({"manage_applications", "update_status"}),
    "editor": frozenset({"manage_applications", "update_status", "edit_post"}),
}


def _aware(value: datetime.datetime) -> datetime.datetime:
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


def _is_active(status: str, expires_at: datetime.datetime | None) -> bool:
    if status != "active":
        return False
    return expires_at is None or _aware(expires_at) > datetime.datetime.now(datetime.timezone.utc)


def _active_organization_membership(
    session: Session,
    user_id: int,
    organization_id: int,
) -> OrganizationMember | None:
    member = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    return member if member and _is_active(member.status, member.expires_at) else None


def can_manage_topic(session: Session, user: User, topic: Topic, capability: str) -> bool:
    if capability not in {"moderate_posts", "edit_topic", "manage_collaborators"}:
        return False
    if user.site_role == "operator":
        return True
    if topic.organization_id is not None:
        member = _active_organization_membership(session, user.id, topic.organization_id)
        if member and member.role == "owner":
            return True
        if member and topic.created_by == user.id and member.role in {"owner", "publisher"}:
            return capability in {"moderate_posts", "edit_topic"}
    grant = session.execute(
        select(TopicCollaborator).where(
            TopicCollaborator.topic_id == topic.id,
            TopicCollaborator.user_id == user.id,
        )
    ).scalar_one_or_none()
    return bool(
        grant
        and _is_active(grant.status, grant.expires_at)
        and capability in TOPIC_ROLE_CAPABILITIES.get(grant.role, frozenset())
    )


def can_manage_post(session: Session, user: User, post: Post, capability: str) -> bool:
    if capability not in {"manage_applications", "update_status", "edit_post"}:
        return False
    if user.site_role == "operator" or post.author_id == user.id:
        return True
    grant = session.execute(
        select(PostCollaborator).where(
            PostCollaborator.post_id == post.id,
            PostCollaborator.user_id == user.id,
        )
    ).scalar_one_or_none()
    return bool(
        grant
        and _is_active(grant.status, grant.expires_at)
        and capability in POST_ROLE_CAPABILITIES.get(grant.role, frozenset())
    )
