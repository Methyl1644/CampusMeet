from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.common import api_ok, current_user_id
from services.collaboration_lifecycle import PUBLIC_POST_STATUSES
from storage.database.db import get_session
from storage.database.models import Post, PostBookmark, Topic, TopicFollow, User


router = APIRouter(prefix="/favorites", tags=["favorites"])


def _session_and_user(user_id: str) -> tuple[Session, User]:
    session = get_session()
    user = session.get(User, int(user_id))
    if user is None:
        session.close()
        raise HTTPException(status_code=401, detail="登录状态已失效")
    return session, user


def _visible_topic(session: Session, topic_id: int) -> Topic:
    topic = session.scalar(
        select(Topic).where(Topic.id == topic_id, Topic.status == "active")
    )
    if topic is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return topic


def _visible_post(session: Session, post_id: int) -> Post:
    post = session.scalar(
        select(Post).where(
            Post.id == post_id,
            Post.status.in_(PUBLIC_POST_STATUSES),
        )
    )
    if post is None:
        raise HTTPException(status_code=404, detail="组队不存在")
    return post


def _insert_once(session: Session, model, values: dict[str, int]) -> None:
    dialect_name = session.get_bind().dialect.name
    conflict_columns = list(values)
    if dialect_name == "sqlite":
        statement = sqlite_insert(model).values(**values).on_conflict_do_nothing(
            index_elements=conflict_columns
        )
        session.execute(statement)
        return
    if dialect_name == "postgresql":
        statement = postgresql_insert(model).values(**values).on_conflict_do_nothing(
            index_elements=conflict_columns
        )
        session.execute(statement)
        return

    if session.get(model, values) is not None:
        return
    try:
        with session.begin_nested():
            session.add(model(**values))
            session.flush()
    except IntegrityError:
        if session.get(model, values) is None:
            raise


def _topic_favorite_state(session: Session, topic_id: int, user_id: int) -> dict[str, Any]:
    follower_count = int(
        session.scalar(
            select(func.count()).select_from(TopicFollow).where(
                TopicFollow.topic_id == topic_id
            )
        )
        or 0
    )
    favorite = session.get(
        TopicFollow,
        {"topic_id": topic_id, "user_id": user_id},
    ) is not None
    return {
        "topic_id": str(topic_id),
        "favorite": favorite,
        "followed": favorite,
        "follower_count": follower_count,
    }


@router.put("/topics/{topic_id}")
def favorite_topic(
    topic_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        _visible_topic(session, topic_id)
        _insert_once(
            session,
            TopicFollow,
            {"topic_id": topic_id, "user_id": user.id},
        )
        session.commit()
        return api_ok(_topic_favorite_state(session, topic_id, user.id))
    finally:
        session.close()


@router.delete("/topics/{topic_id}")
def unfavorite_topic(
    topic_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        _visible_topic(session, topic_id)
        session.execute(
            delete(TopicFollow).where(
                TopicFollow.topic_id == topic_id,
                TopicFollow.user_id == user.id,
            )
        )
        session.commit()
        return api_ok(_topic_favorite_state(session, topic_id, user.id))
    finally:
        session.close()


@router.put("/posts/{post_id}")
def favorite_post(
    post_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        _visible_post(session, post_id)
        _insert_once(
            session,
            PostBookmark,
            {"post_id": post_id, "user_id": user.id},
        )
        session.commit()
        return api_ok({"post_id": str(post_id), "bookmark": True})
    finally:
        session.close()


@router.delete("/posts/{post_id}")
def unfavorite_post(
    post_id: int,
    user_id: str = Depends(current_user_id),
) -> dict[str, Any]:
    session, user = _session_and_user(user_id)
    try:
        _visible_post(session, post_id)
        session.execute(
            delete(PostBookmark).where(
                PostBookmark.post_id == post_id,
                PostBookmark.user_id == user.id,
            )
        )
        session.commit()
        return api_ok({"post_id": str(post_id), "bookmark": False})
    finally:
        session.close()
