import json
from pathlib import Path

from storage.database.db import get_postgres_pool_options
from utils.email_sender import send_verification_email
from utils.runtime import agent_runtime_access_allowed, get_allowed_origins


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_allowed_origins_normalizes_and_deduplicates_configured_urls():
    origins = get_allowed_origins(
        {
            "FRONTEND_ORIGINS": (
                "https://campusmate-web.onrender.com/, "
                "https://preview.example.com,"
                "https://campusmate-web.onrender.com"
            )
        }
    )

    assert origins == [
        "https://campusmate-web.onrender.com",
        "https://preview.example.com",
    ]


def test_allowed_origins_supports_singular_name_and_local_defaults():
    assert get_allowed_origins(
        {"FRONTEND_ORIGIN": "https://campusmate.example.edu.cn/"}
    ) == ["https://campusmate.example.edu.cn"]
    assert get_allowed_origins({}) == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_postgres_pool_defaults_are_small_and_can_be_overridden():
    defaults = get_postgres_pool_options({})

    assert defaults == {
        "pool_size": 5,
        "max_overflow": 5,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_timeout": 30,
    }

    overridden = get_postgres_pool_options(
        {"DB_POOL_SIZE": "8", "DB_MAX_OVERFLOW": "2"}
    )
    assert overridden["pool_size"] == 8
    assert overridden["max_overflow"] == 2


def test_postgres_pool_ignores_invalid_or_unsafe_values():
    options = get_postgres_pool_options(
        {"DB_POOL_SIZE": "not-a-number", "DB_MAX_OVERFLOW": "500"}
    )

    assert options["pool_size"] == 5
    assert options["max_overflow"] == 20


def test_agent_runtime_http_routes_are_closed_without_a_service_token():
    assert agent_runtime_access_allowed({}, None) is False
    assert agent_runtime_access_allowed({"ENABLE_AGENT_RUNTIME": "false"}, "anything") is False
    assert agent_runtime_access_allowed({"ENABLE_AGENT_RUNTIME": "true"}, None) is False
    assert agent_runtime_access_allowed({"ENABLE_AGENT_RUNTIME": "true"}, "wrong") is False
    assert agent_runtime_access_allowed(
        {"ENABLE_AGENT_RUNTIME": "true", "AGENT_RUNTIME_TOKEN": "secret"},
        "secret",
    ) is True


class _FakeHttpResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return b'{"id":"email_123"}'


def test_brevo_transport_posts_verification_email_without_leaking_code(
    monkeypatch, caplog
):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _FakeHttpResponse()

    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")
    monkeypatch.setenv("BREVO_FROM_EMAIL", "verified-sender@example.com")
    monkeypatch.setenv("BREVO_FROM_NAME", "CampusMate")
    monkeypatch.setenv("BREVO_API_BASE_URL", "https://mail.example.test/v3/")
    monkeypatch.setenv("RESEND_API_KEY", "unused-resend-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "unused@example.com")
    monkeypatch.setattr("utils.email_sender.urlopen", fake_urlopen)

    result = send_verification_email(
        "student@smail.nju.edu.cn", "654321", "注册"
    )

    request = captured["request"]
    body = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://mail.example.test/v3/smtp/email"
    assert request.get_header("Api-key") == "test-brevo-key"
    assert request.get_header("Accept") == "application/json"
    assert captured["timeout"] == 15
    assert body["sender"] == {
        "email": "verified-sender@example.com",
        "name": "CampusMate",
    }
    assert body["to"] == [{"email": "student@smail.nju.edu.cn"}]
    assert "654321" in body["textContent"]
    assert result == {
        "sent": True,
        "message": "验证码已发送至 student@smail.nju.edu.cn",
    }
    assert "654321" not in caplog.text


def test_brevo_failure_does_not_fall_back_or_return_the_code(monkeypatch):
    def failing_urlopen(*_args, **_kwargs):
        raise OSError("provider unavailable")

    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")
    monkeypatch.setenv("BREVO_FROM_EMAIL", "verified-sender@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "unused-resend-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "unused@example.com")
    monkeypatch.setattr("utils.email_sender.urlopen", failing_urlopen)

    result = send_verification_email(
        "student@smail.nju.edu.cn", "654321", "注册"
    )

    assert result["sent"] is False
    assert "654321" not in json.dumps(result, ensure_ascii=False)


def test_resend_transport_posts_verification_email_without_leaking_code(
    monkeypatch, caplog
):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return _FakeHttpResponse()

    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "CampusMate <verify@example.com>")
    monkeypatch.setenv("RESEND_API_BASE_URL", "https://mail.example.test/")
    monkeypatch.setattr("utils.email_sender.urlopen", fake_urlopen)

    result = send_verification_email(
        "student@example.edu.cn", "654321", "注册"
    )

    request = captured["request"]
    body = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://mail.example.test/emails"
    assert request.get_header("Authorization") == "Bearer test-resend-key"
    assert captured["timeout"] == 15
    assert body["from"] == "CampusMate <verify@example.com>"
    assert body["to"] == ["student@example.edu.cn"]
    assert "654321" in body["text"]
    assert result == {
        "sent": True,
        "message": "验证码已发送至 student@example.edu.cn",
    }
    assert "654321" not in caplog.text


def test_resend_failure_does_not_fall_back_to_returning_the_code(monkeypatch):
    def failing_urlopen(*_args, **_kwargs):
        raise OSError("provider unavailable")

    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "verify@example.com")
    monkeypatch.setattr("utils.email_sender.urlopen", failing_urlopen)

    result = send_verification_email(
        "student@example.edu.cn", "654321", "注册"
    )

    assert result["sent"] is False
    assert "654321" not in json.dumps(result, ensure_ascii=False)


def test_render_blueprint_defines_public_api_and_static_frontend():
    blueprint = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "name: campusmate-api" in blueprint
    assert "runtime: python" in blueprint
    assert "plan: free" in blueprint
    assert "region: singapore" in blueprint
    assert "buildCommand: uv sync --frozen --no-dev" in blueprint
    assert "startCommand: uv run --no-sync alembic upgrade head && uv run --no-sync python src/main.py -m http -p $PORT" in blueprint
    assert "healthCheckPath: /health" in blueprint

    assert "name: campusmate-web" in blueprint
    assert "runtime: static" in blueprint
    assert "rootDir: apps/web" not in blueprint
    assert "buildCommand: npm --prefix apps/web ci && npm --prefix apps/web run build" in blueprint
    assert "staticPublishPath: apps/web/dist" in blueprint
    assert "source: /*" in blueprint
    assert "destination: /index.html" in blueprint


def test_render_blueprint_keeps_external_credentials_out_of_git():
    blueprint = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")

    assert "key: DATABASE_URL\n        sync: false" in blueprint
    assert "key: BREVO_API_KEY\n        sync: false" in blueprint
    assert "key: BREVO_FROM_EMAIL\n        sync: false" in blueprint
    assert "key: BREVO_FROM_NAME\n        value: CampusMate" in blueprint
    assert "key: RESEND_API_KEY\n        sync: false" in blueprint
    assert "key: RESEND_FROM_EMAIL\n        sync: false" in blueprint
    assert "key: FRONTEND_ORIGINS\n        sync: false" in blueprint
    assert "key: BOOTSTRAP_OPERATOR_EMAIL\n        sync: false" in blueprint
    assert "key: VITE_API_BASE_URL\n        sync: false" in blueprint
    assert "key: JWT_SECRET\n        generateValue: true" in blueprint
    assert "key: APP_ENV\n        value: production" in blueprint
    assert "AUTH_TEST_MODE" in blueprint
    assert 'value: "false"' in blueprint
    assert "key: CAMPUS_EMAIL_DOMAINS\n        value: nju.edu.cn" in blueprint
    assert "postgresql://" not in blueprint
    assert "ghp_" not in blueprint
    assert "xkeysib-" not in blueprint
    assert "re_test" not in blueprint


def test_render_runtime_and_deployment_guide_are_present():
    python_version = (REPOSITORY_ROOT / ".python-version").read_text(
        encoding="utf-8"
    )
    guide = (REPOSITORY_ROOT / "docs/deployment/render-neon.md").read_text(
        encoding="utf-8"
    )

    assert python_version.strip() == "3.12"
    assert "DATABASE_URL" in guide
    assert "VITE_API_BASE_URL" in guide
    assert "FRONTEND_ORIGINS" in guide
    assert "Neon" in guide
    assert "Brevo" in guide


def test_runtime_lock_excludes_removed_desktop_only_packages():
    lockfile = (REPOSITORY_ROOT / "uv.lock").read_text(encoding="utf-8").lower()

    assert 'name = "pygobject"' not in lockfile
    assert 'name = "dbus-python"' not in lockfile
    assert 'name = "pycairo"' not in lockfile
