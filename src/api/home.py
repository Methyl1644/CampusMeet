from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.common import api_ok, current_user_id
from services.home import build_home_feed
from storage.database.db import get_session
from storage.database.models import User


router = APIRouter(prefix="/home", tags=["home"])


@router.get("")
def home_feed(user_id: str = Depends(current_user_id)) -> dict[str, Any]:
    session = get_session()
    try:
        user = session.get(User, int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="登录状态已失效")
        return api_ok(build_home_feed(session, user))
    finally:
        session.close()
