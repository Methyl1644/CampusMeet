import json
from pathlib import Path


COZE = Path("coze")


def _schema(name: str) -> dict:
    return json.loads((COZE / "schemas" / name).read_text(encoding="utf-8"))


def _jsonl(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (COZE / "evals" / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_post_draft_delivery_contract_matches_backend_parameters():
    input_schema = _schema("post_draft.input.json")
    output_schema = _schema("post_draft.output.json")

    assert set(input_schema["required"]) == {"message", "kind", "field_states", "candidate_tags"}
    assert set(input_schema["properties"]) == {
        "message",
        "draft",
        "user_skills",
        "kind",
        "field_states",
        "candidate_tags",
        "topic_id",
    }
    assert output_schema["properties"]["suggested_tag_ids"]["maxItems"] == 4
    statuses = output_schema["properties"]["field_states"]["additionalProperties"]["properties"]["status"]["enum"]
    assert set(statuses) == {"confirmed", "none", "unknown", "skipped", "pending"}


def test_classify_review_delivery_contract_matches_backend_parameters():
    input_schema = _schema("classify_review.input.json")
    output_schema = _schema("classify_review.output.json")

    assert set(input_schema["required"]) == {"title", "description", "candidate_tags"}
    assert set(input_schema["properties"]) == {"title", "description", "candidate_tags"}
    assert set(output_schema["required"]) == {
        "main_category",
        "tag_ids",
        "unknown_concepts",
        "risk_level",
        "suggestions",
    }
    assert set(output_schema["properties"]["unknown_concepts"]["items"]["properties"]["category"]["enum"]) == {
        "activity",
        "skill",
        "role",
        "level",
        "audience",
    }


def test_delivery_examples_use_only_declared_inputs_and_controlled_tag_ids():
    for filename, schema_name in (
        ("post_draft_cases.jsonl", "post_draft.input.json"),
        ("classify_review_cases.jsonl", "classify_review.input.json"),
    ):
        schema = _schema(schema_name)
        declared = set(schema["properties"])
        required = set(schema["required"])
        cases = _jsonl(filename)
        assert len(cases) >= 5
        for case in cases:
            payload = case["input"]
            assert required.issubset(payload)
            assert set(payload).issubset(declared)
            candidates = {item["tag_id"] for item in payload["candidate_tags"]}
            expected_ids = set(case["expected_output"].get("suggested_tag_ids", []))
            expected_ids.update(case["expected_output"].get("tag_ids", []))
            assert expected_ids.issubset(candidates)


def test_delivery_checklist_names_both_workflows_and_required_render_variables():
    checklist = (COZE / "DELIVERY_CHECKLIST.md").read_text(encoding="utf-8")

    assert "campusmate_post_draft" in checklist
    assert "campusmate_classify_review" in checklist
    assert "COZE_WORKFLOW_POST_DRAFT" in checklist
    assert "COZE_WORKFLOW_CLASSIFY_REVIEW" in checklist
    assert "COZE_API_TOKEN" in checklist
