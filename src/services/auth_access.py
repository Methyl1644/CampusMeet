from __future__ import annotations

import os
from collections.abc import Mapping


AUTH_ACCESS_MODES = {"public", "allowlist"}
ACCESS_DENIED_MESSAGE = "当前为内部测试阶段，该账号暂未获得访问权限"


def auth_access_mode(environment: Mapping[str, str] | None = None) -> str:
    env = environment if environment is not None else os.environ
    return env.get("AUTH_ACCESS_MODE", "public").strip().lower() or "public"


def allowed_auth_emails(
    environment: Mapping[str, str] | None = None,
) -> frozenset[str]:
    env = environment if environment is not None else os.environ
    return frozenset(
        item.strip().casefold()
        for item in env.get("AUTH_ALLOWED_EMAILS", "").split(",")
        if item.strip()
    )


def auth_email_is_allowed(
    email: str,
    environment: Mapping[str, str] | None = None,
) -> bool:
    mode = auth_access_mode(environment)
    if mode == "public":
        return True
    if mode != "allowlist":
        return False
    return email.strip().casefold() in allowed_auth_emails(environment)
