import pytest

from tools.ai_tools import _valid_post_draft_result
from api.schemas.agent import PostDraftAgentRequest


def field(value, status="confirmed"):
    return {"value": value, "status": status}


def draft(activity, time, location, *, total=3, current=1, recruit=2, description=""):
    value = {
        "activity": {"value": activity, "raw_text": activity, "confidence": 0.95},
        "time": {"value": time, "raw_text": time, "normalized_time": "", "precision": "fuzzy", "confidence": 0.9},
        "location": {"value": location, "raw_text": location, "normalized_location": location, "confidence": 0.9},
        "people": {"total_people": total, "current_people": current, "recruit_people": recruit, "min_people": total, "max_people": total, "raw_text": str(total), "confidence": 0.95},
    }
    if description:
        value["description"] = description
    return value


@pytest.mark.parametrize(
    ("result", "expected_missing", "expected_next"),
    [
        (
            {"reply": "请确认城市", "draft": draft("去玄武湖边走走", "周末", "玄武湖", total=4, recruit=3), "is_complete": False,
             "field_states": {"activity": field("去玄武湖边走走"), "time": field("周末"), "location": field("玄武湖", "pending"), "people": field(4)},
             "suggested_tag_ids": [], "missing_fields": ["location"], "next_field": "location", "degraded": False},
            ["location"], "location",
        ),
        (
            {"reply": "已整理", "draft": draft("新街口火锅", "明天晚上7点", "南京新街口", description="明晚吃火锅，再找2位伙伴。"), "is_complete": True,
             "field_states": {"activity": field("新街口火锅"), "time": field("明天晚上7点"), "location": field("南京新街口"), "people": field(3)},
             "suggested_tag_ids": [], "missing_fields": [], "next_field": "", "degraded": False},
            [], "",
        ),
        (
            {"reply": "时间已改为周日下午", "draft": draft("玄武湖散步", "周日下午", "南京玄武湖"), "is_complete": True,
             "field_states": {"activity": field("玄武湖散步"), "time": field("周日下午"), "location": field("南京玄武湖"), "people": field(3)},
             "suggested_tag_ids": [], "missing_fields": [], "next_field": "", "degraded": False},
            [], "",
        ),
        (
            {"reply": "请输入组队需求", "draft": {}, "is_complete": True, "field_states": {}, "suggested_tag_ids": [],
             "missing_fields": [], "next_field": "", "degraded": True},
            [], "",
        ),
        (
            {"reply": "还希望什么时候进行？", "draft": {**draft("数学建模", "", "南京大学", total=3, recruit=2), "kind": "topic_team", "topic_id": "12"}, "is_complete": False,
             "field_states": {"activity": field("数学建模"), "time": field(None, "pending"), "location": field("南京大学"), "people": field(3)},
             "suggested_tag_ids": [], "missing_fields": ["time"], "next_field": "time", "degraded": False},
            ["time"], "time",
        ),
        (
            {"reply": "请补充活动时间", "draft": draft("红山森林动物园志愿活动", "", "红山森林动物园", total=3, recruit=2), "is_complete": False,
             "field_states": {"activity": field("红山森林动物园志愿活动"), "time": field(None, "pending"), "location": field("红山森林动物园"), "people": field(3)},
             "suggested_tag_ids": [], "missing_fields": ["time"], "next_field": "time", "degraded": False},
            ["time"], "time",
        ),
    ],
    ids=["xuanwu-lake", "hotpot-ready", "change-time-only", "blank-degraded", "topic-team", "zoo-volunteer"],
)
def test_section_nine_regression_outputs_are_accepted(result, expected_missing, expected_next):
    assert _valid_post_draft_result(result, set(), "casual_invitation")
    assert result["missing_fields"] == expected_missing
    assert result["next_field"] == expected_next


def test_blank_message_reaches_workflow_degradation_path():
    assert PostDraftAgentRequest(message="").message == ""
