import json
from types import SimpleNamespace

from api import posts as posts_api
from services.cover_generation import generate_content_cover


def test_generate_content_cover_calls_deployed_workflow_and_unwraps_image(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": json.dumps({"output": {"image_url": "https://cdn.example.test/cover.png"}})}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setenv("COZE_COVER_API_URL", "https://sbs68xhstz.coze.site/run")
    monkeypatch.setenv("COZE_DEPLOY_API_TOKEN", "secret-token")
    monkeypatch.setattr("requests.post", fake_post)

    result = generate_content_cover(
        content_type="post",
        title="羽毛球搭子",
        description="周末一起打球",
        category="体育与健身",
        location="仙林校区",
        roles=["双打队友"],
    )

    assert result == "https://cdn.example.test/cover.png"
    assert captured["url"] == "https://sbs68xhstz.coze.site/run"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["json"] == {
        "content_type": "post",
        "title": "羽毛球搭子",
        "description": "周末一起打球",
        "category": "体育与健身",
        "location": "仙林校区",
        "roles": "双打队友",
    }


def test_create_post_generates_cover_only_when_upload_is_missing(monkeypatch):
    captured = {}
    monkeypatch.setattr(posts_api, "_moderate_post", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        posts_api,
        "screen_post_content",
        lambda *_args: SimpleNamespace(has_violations=False, risk_level="low"),
    )
    monkeypatch.setattr(posts_api, "_classification_review", lambda *_args, **_kwargs: {})
    def fake_generate(**kwargs):
        captured["cover_request"] = kwargs
        return "https://cdn.example.test/generated.png"

    monkeypatch.setattr(posts_api, "generate_content_cover", fake_generate)

    def fake_invoke(_tool, payload):
        captured["create_payload"] = payload
        return json.dumps({"success": True, "post": {"id": "9"}})

    monkeypatch.setattr(posts_api, "invoke_tool", fake_invoke)

    posts_api.create(
        {
            "title": "寻找建模队友",
            "description": "需要 Python 和论文写作",
            "main_category": "竞赛与项目",
            "activity_name": "数学建模",
            "target_members": 3,
            "needed_roles": ["Python", "论文写作"],
            "school_scope": "仙林校区",
        },
        user_id="7",
    )

    assert captured["cover_request"]["content_type"] == "post"
    assert captured["create_payload"]["generated_cover_url"] == "https://cdn.example.test/generated.png"
