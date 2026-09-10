import os
import secrets
from collections.abc import Mapping


DEFAULT_LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_allowed_origins(
    environment: Mapping[str, str] | None = None,
) -> list[str]:
    """Return normalized browser origins allowed to call the API."""
    env = environment if environment is not None else os.environ
    configured = env.get("FRONTEND_ORIGINS", "").strip()
    if not configured:
        configured = env.get("FRONTEND_ORIGIN", "").strip()
    raw_origins = configured.split(",") if configured else DEFAULT_LOCAL_ORIGINS

    origins: list[str] = []
    for raw_origin in raw_origins:
        origin = raw_origin.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def should_start_agent_runtime(environment: Mapping[str, str] | None = None) -> bool:
    env = environment if environment is not None else os.environ
    configured = env.get("ENABLE_AGENT_RUNTIME", "").strip().lower()
    if configured:
        return configured in {"1", "true", "yes", "on"}
    return bool(env.get("COZE_WORKLOAD_IDENTITY_API_KEY"))


def agent_runtime_access_allowed(
    environment: Mapping[str, str] | None,
    provided_token: str | None,
) -> bool:
    """Keep legacy graph execution routes private when the REST API is public."""
    env = environment if environment is not None else os.environ
    if not should_start_agent_runtime(env):
        return False
    expected = env.get("AGENT_RUNTIME_TOKEN", "").strip()
    return bool(expected and provided_token and secrets.compare_digest(expected, provided_token))
