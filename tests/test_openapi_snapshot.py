from __future__ import annotations

import json
from pathlib import Path

from main import app


SNAPSHOT = Path(__file__).parents[1] / "docs" / "api" / "openapi.json"


def test_openapi_schema_matches_the_committed_frontend_contract():
    assert SNAPSHOT.exists(), "run scripts/export_openapi.py after intentional API changes"
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert app.openapi() == expected
