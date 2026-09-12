from __future__ import annotations

import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api import operations
from services.observability import install_observability, redact_sensitive
from storage.database.models import AuditLog, User
from storage.database.shared.model import Base


def test_request_id_and_stable_error_envelope_do_not_expose_exception_details():
    app = FastAPI()
    install_observability(app)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/denied")
    def denied():
        raise HTTPException(status_code=403, detail="无权访问")

    @app.get("/broken")
    def broken():
        raise RuntimeError("DATABASE_URL=postgresql://user:private-password@example/db")

    client = TestClient(app, raise_server_exceptions=False)
    request_id = "client-request-123"
    ok_response = client.get("/ok", headers={"X-Request-ID": request_id})
    denied_response = client.get("/denied")
    broken_response = client.get("/broken")

    assert ok_response.headers["X-Request-ID"] == request_id
    assert denied_response.json()["message"] == "无权访问"
    assert denied_response.json()["request_id"]
    assert broken_response.status_code == 500
    assert "private-password" not in broken_response.text
    assert broken_response.json()["message"] == "服务器暂时无法处理该请求"


def test_sensitive_redaction_handles_nested_values_and_contact_patterns():
    value = {
        "authorization": "Bearer secret-token",
        "password": "Secret123",
        "body": {
            "email": "student@smail.nju.edu.cn",
            "message": "联系 13800138000 或微信 campusmate_123",
        },
        "safe": "post-19",
    }

    redacted = json.dumps(redact_sensitive(value), ensure_ascii=False)

    assert "secret-token" not in redacted
    assert "Secret123" not in redacted
    assert "student@smail.nju.edu.cn" not in redacted
    assert "13800138000" not in redacted
    assert "campusmate_123" not in redacted
    assert "post-19" in redacted


def test_operator_audit_search_is_paginated_and_rejects_students(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                User(id=1, email="student@nju.edu.cn", password_hash="x", nickname="student"),
                User(
                    id=2,
                    email="operator@nju.edu.cn",
                    password_hash="x",
                    nickname="operator",
                    site_role="operator",
                ),
                AuditLog(
                    user_id=1,
                    action="post.create",
                    target_type="post",
                    target_id="10",
                    detail='{"password":"must-not-leak","status":"recruiting"}',
                ),
                AuditLog(
                    user_id=2,
                    action="post.archive",
                    target_type="post",
                    target_id="11",
                    detail='{"status":"archived"}',
                ),
            ]
        )
        session.commit()
    monkeypatch.setattr(operations, "get_session", factory)

    with pytest.raises(HTTPException) as denied:
        operations.search_audit_logs(page=1, page_size=20, action="", target_type="", actor_id=None, user_id="1")
    assert denied.value.status_code == 403

    result = operations.search_audit_logs(
        page=1,
        page_size=1,
        action="post.",
        target_type="post",
        actor_id=None,
        user_id="2",
    )
    assert result["data"]["total"] == 2
    assert result["data"]["pages"] == 2
    assert len(result["data"]["list"]) == 1
    assert "must-not-leak" not in json.dumps(result, ensure_ascii=False)
