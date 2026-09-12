import os
import time
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import logging
logger = logging.getLogger(__name__)

MAX_RETRY_TIME = 20  # 连接最大重试时间（秒）
# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def get_db_url() -> str:
    """Build database URL from environment."""
    url = os.getenv("DATABASE_URL") or os.getenv("PGDATABASE_URL") or ""
    if url:
        return url

    if not os.getenv("COZE_WORKLOAD_IDENTITY_CLIENT_ID"):
        database_path = Path(__file__).resolve().parents[3] / "campusmate.db"
        return f"sqlite:///{database_path.as_posix()}"

    from coze_workload_identity import Client
    try:
        client = Client()
        env_vars = client.get_project_env_vars()
        client.close()
        for env_var in env_vars:
            if env_var.key == "PGDATABASE_URL":
                url = env_var.value.replace("'", "'\\''")
                return url
    except Exception as e:
        logger.error(f"Error loading PGDATABASE_URL: {e}")
        raise e
    finally:
        if url is None or url == "":
            logger.error("PGDATABASE_URL is not set")
    return url
_engine = None
_SessionLocal = None


def _bounded_environment_int(
    environment,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(environment.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def get_postgres_pool_options(environment=None) -> dict[str, int | bool]:
    """Keep each application instance within Neon connection limits."""
    env = environment if environment is not None else os.environ
    return {
        "pool_size": _bounded_environment_int(env, "DB_POOL_SIZE", 5, 1, 20),
        "max_overflow": _bounded_environment_int(
            env, "DB_MAX_OVERFLOW", 5, 0, 20
        ),
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_timeout": 30,
    }

def _create_engine_with_retry():
    url = get_db_url()
    if url.startswith("sqlite:"):
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(url, **get_postgres_pool_options())
    # 验证连接，带重试
    start_time = time.time()
    last_error = None
    while time.time() - start_time < MAX_RETRY_TIME:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as e:
            last_error = e
            elapsed = time.time() - start_time
            logger.warning(f"Database connection failed, retrying... (elapsed: {elapsed:.1f}s)")
            time.sleep(min(1, MAX_RETRY_TIME - elapsed))
    logger.error(f"Database connection failed after {MAX_RETRY_TIME}s: {last_error}")
    raise last_error  # pyright: ignore [reportGeneralTypeIssues]

def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_with_retry()
    return _engine

def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

def get_session():
    return get_sessionmaker()()


def ensure_compatibility_columns(engine) -> None:
    """Apply the small additive migration needed by legacy local databases."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []
    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "site_role" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN site_role TEXT NOT NULL DEFAULT 'student'")
        if "failed_login_attempts" not in user_columns:
            statements.append(
                "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0"
            )
        if "locked_until" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP")
    if "posts" in table_names:
        post_columns = {column["name"] for column in inspector.get_columns("posts")}
        if "kind" not in post_columns:
            statements.append("ALTER TABLE posts ADD COLUMN kind TEXT NOT NULL DEFAULT 'casual_invitation'")
        if "topic_id" not in post_columns:
            statements.append("ALTER TABLE posts ADD COLUMN topic_id BIGINT")
    if "conversations" in table_names:
        conversation_columns = {
            column["name"] for column in inspector.get_columns("conversations")
        }
        if "author_confirmed" not in conversation_columns:
            statements.append(
                "ALTER TABLE conversations ADD COLUMN author_confirmed BOOLEAN NOT NULL DEFAULT FALSE"
            )
        if "applicant_confirmed" not in conversation_columns:
            statements.append(
                "ALTER TABLE conversations ADD COLUMN applicant_confirmed BOOLEAN NOT NULL DEFAULT FALSE"
            )
    if "verification_codes" in table_names:
        verification_columns = {
            column["name"] for column in inspector.get_columns("verification_codes")
        }
        if "attempts" not in verification_columns:
            statements.append(
                "ALTER TABLE verification_codes ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0"
            )
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

__all__ = [
    "get_db_url",
    "get_engine",
    "get_sessionmaker",
    "get_session",
    "get_postgres_pool_options",
    "ensure_compatibility_columns",
]
