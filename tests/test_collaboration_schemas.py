from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas.collaboration import (
    ApplicationCreateRequest,
    MessageSendRequest,
    PostCreateRequest,
    PostUpdateRequest,
)


def test_message_rejects_empty_and_oversized_content():
    with pytest.raises(ValidationError):
        MessageSendRequest(content="   ")
    with pytest.raises(ValidationError):
        MessageSendRequest(content="x" * 2001)


def test_application_rejects_invalid_post_and_oversized_question_list():
    with pytest.raises(ValidationError):
        ApplicationCreateRequest(
            post_id=0,
            role_wanted="member",
            experience="none",
            available_time="weekend",
            reason="interested",
        )
    with pytest.raises(ValidationError):
        ApplicationCreateRequest(
            post_id=1,
            role_wanted="member",
            experience="none",
            available_time="weekend",
            reason="interested",
            questions=[str(index) for index in range(11)],
        )


def test_post_create_enforces_counts_and_list_item_limits():
    with pytest.raises(ValidationError):
        PostCreateRequest(activity_name="bad", target_members=0)
    with pytest.raises(ValidationError):
        PostCreateRequest(activity_name="bad", tag_ids=[str(index) for index in range(9)])
    with pytest.raises(ValidationError):
        PostCreateRequest(activity_name="bad", needed_roles=["x" * 41])


def test_post_update_rejects_unknown_status_and_empty_request():
    with pytest.raises(ValidationError):
        PostUpdateRequest(status="deleted")
    with pytest.raises(ValidationError):
        PostUpdateRequest(status="recruiting")
    with pytest.raises(ValidationError):
        PostUpdateRequest()
