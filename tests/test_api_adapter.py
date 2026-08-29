import json

import pytest


def test_api_ok_wraps_payload():
    from api.common import api_ok

    assert api_ok({"id": "1"}) == {"code": 0, "message": "ok", "data": {"id": "1"}}


def test_tool_result_unwraps_named_payload():
    from api.common import parse_tool_result

    raw = json.dumps({"success": True, "post": {"id": "42"}, "message": "created"}, ensure_ascii=False)

    assert parse_tool_result(raw, "post") == {"code": 0, "message": "created", "data": {"id": "42"}}


def test_tool_result_unwraps_list_payload():
    from api.common import parse_tool_result

    raw = json.dumps({"success": True, "list": [{"id": "1"}], "total": 1, "page": 1, "page_size": 10})

    assert parse_tool_result(raw, "list") == {
        "code": 0,
        "message": "ok",
        "data": {"list": [{"id": "1"}], "total": 1, "page": 1, "page_size": 10},
    }


def test_tool_result_raises_on_failure():
    from api.common import parse_tool_result

    raw = json.dumps({"success": False, "message": "bad request"})

    with pytest.raises(Exception) as exc:
        parse_tool_result(raw)

    assert "bad request" in str(exc.value)
