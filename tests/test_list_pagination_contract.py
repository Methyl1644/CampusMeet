from __future__ import annotations

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


def test_notification_read_all_static_route_precedes_dynamic_read_route():
    paths = [
        route.path
        for route in app.routes
        if "POST" in getattr(route, "methods", set())
        and route.path.startswith("/api/notifications/")
    ]

    assert paths.index("/api/notifications/read-all") < paths.index(
        "/api/notifications/{notification_id}/read"
    )
