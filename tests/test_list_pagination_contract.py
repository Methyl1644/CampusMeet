from __future__ import annotations

from fastapi.testclient import TestClient

from api import notifications as notifications_api
from api.common import current_user_id
from main import app


PAGINATED_PATHS = (
    "/api/organizations/invitations/my",
    "/api/organizations/{organization_id}/members",
    "/api/organizations/ownership-transfers/my",
    "/api/topics/{topic_id}/collaborators",
    "/api/posts/{post_id}/collaborators",
    "/api/moderation/blocks/my",
    "/api/posts/my",
    "/api/teams/my",
)


def test_backend_management_lists_expose_page_and_page_size_query_parameters():
    schema = app.openapi()

    for path in PAGINATED_PATHS:
        parameters = schema["paths"][path]["get"]["parameters"]
        query_names = {
            item["name"]
            for item in parameters
            if item.get("in") == "query"
        }
        assert {"page", "page_size"} <= query_names, path


def test_notification_read_all_static_route_precedes_dynamic_read_route(monkeypatch):
    paths = list(app.openapi()["paths"])

    assert paths.index("/api/notifications/read-all") < paths.index(
        "/api/notifications/{notification_id}/read"
    )

    class SessionStub:
        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(notifications_api, "get_session", SessionStub)
    monkeypatch.setattr(
        notifications_api,
        "mark_all_read",
        lambda session, user_id: 0,
    )
    app.dependency_overrides[current_user_id] = lambda: "1"
    try:
        with TestClient(app) as client:
            response = client.post("/api/notifications/read-all")
    finally:
        app.dependency_overrides.pop(current_user_id, None)

    assert response.status_code == 200
    assert response.json()["data"] == {"updated": 0}
