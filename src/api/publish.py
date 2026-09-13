from typing import Literal
from fastapi import APIRouter, Depends, Query
from api.common import api_ok, current_user_id
from services.publish_context import publish_context
from storage.database.db import get_session
from storage.database.models import User

router = APIRouter(prefix="/publish", tags=["publish"])


@router.get("/context")
def context(kind: Literal["casual_invitation", "topic_team"] = "casual_invitation", topic_id: str = Query(default="", max_length=40), user_id: str = Depends(current_user_id)):
    with get_session() as session:
        return api_ok(publish_context(session, session.get(User, int(user_id)), kind, topic_id))
