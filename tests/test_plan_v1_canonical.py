from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from presentation_director_contracts.plan_v1 import PresentationDirectorPlanV1

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "presentation-director-plan-v1.golden.json"
)


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_set_like_source_ids_require_canonical_order() -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    second = slides[1]
    assert isinstance(second, dict)
    primary = second["primary_claim"]
    assert isinstance(primary, dict)
    primary["source_ids"] = ["z-source", "a-source"]
    with pytest.raises(ValidationError, match="canonical sorted order"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_slide_ids_are_unique_but_need_not_be_sorted() -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    second = slides[1]
    assert isinstance(second, dict)
    second["slide_id"] = "s01"
    with pytest.raises(ValidationError, match="unique slide_id"):
        PresentationDirectorPlanV1.model_validate(payload)
