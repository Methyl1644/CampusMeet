import os
import secrets
from collections.abc import Mapping


DEFAULT_LOCAL_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
UNSAFE_JWT_SECRETS = {
    "",
    "your_jwt_secret_here",
    "campusmate_default_secret_2026",
}


def _configured_pair(environment: Mapping[str, str], first: str, second: str) -> bool:
    return bool(environment.get(first, "").strip() and environment.get(second, "").strip())


def production_config_errors(
    environment: Mapping[str, str] | None = None,
) -> list[str]:
    """Return safe, variable-only diagnostics for an unsafe production setup."""
    env = environment if environment is not None else os.environ
    if env.get("APP_ENV", "").strip().lower() != "production":
        return []

    errors: list[str] = []
    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url.startswith(("postgresql://", "postgresql+")):
        errors.append("DATABASE_URL: production requires PostgreSQL")

    jwt_secret = env.get("JWT_SECRET", "").strip()
    if jwt_secret in UNSAFE_JWT_SECRETS or len(jwt_secret) < 32:
        errors.append("JWT_SECRET: configure a random value of at least 32 characters")

    if env.get("AUTH_TEST_MODE", "").strip().lower() not in {"0", "false", "no", "off"}:
        errors.append("AUTH_TEST_MODE: must be false in production")

    if not env.get("CAMPUS_EMAIL_DOMAINS", "").strip():
        errors.append("CAMPUS_EMAIL_DOMAINS: configure at least one campus domain")

    origins = get_allowed_origins(env)
    if not origins or "*" in origins or any(not origin.startswith("https://") for origin in origins):
        errors.append("FRONTEND_ORIGINS: configure explicit HTTPS origins")

    email_ready = (
        _configured_pair(env, "BREVO_API_KEY", "BREVO_FROM_EMAIL")
        or _configured_pair(env, "RESEND_API_KEY", "RESEND_FROM_EMAIL")
        or all(
            env.get(name, "").strip()
            for name in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_SENDER")
        )
    )
    if not email_ready:
        errors.append("EMAIL_DELIVERY: configure Brevo, Resend, or SMTP")
    return errors


def assert_production_config(
    environment: Mapping[str, str] | None = None,
) -> None:
    errors = production_config_errors(environment)
    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))


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
