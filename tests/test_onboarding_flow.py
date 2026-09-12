from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from storage.database.models import User
from storage.database.shared.model import Base
from utils.auth import hash_password


@pytest.fixture
def factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(
            User(
                id=1,
                email="student@smail.nju.edu.cn",
                password_hash=hash_password("Password2026"),
                nickname="student",
            )
        )
        session.commit()
    return session_factory


def test_user_model_exposes_onboarding_defaults():
    user = User(email="new@smail.nju.edu.cn", password_hash="hash", nickname="new")

    assert {
        "onboarding_step",
        "onboarding_completed_at",
        "bio",
        "interests",
        "looking_for",
        "availability",
        "profile_visibility",
    } <= set(User.__table__.columns.keys())
    assert user.onboarding_step is None or user.onboarding_step == 1
    assert user.onboarding_completed_at is None


def test_user_model_persists_onboarding_collection_defaults(factory):
    with factory() as session:
        user = session.get(User, 1)

        assert user.onboarding_step == 1
        assert user.interests == []
        assert user.looking_for == []
        assert user.availability == {}
        assert user.profile_visibility == {}
