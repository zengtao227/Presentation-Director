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


def test_exact_slide_count_must_match_persisted_slides() -> None:
    payload = load_fixture()
    length = payload["length"]
    assert isinstance(length, dict)
    length["target_slide_count"] = 7
    with pytest.raises(ValidationError, match="target_slide_count"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_slide_count_range_can_be_primary_length_control() -> None:
    payload = load_fixture()
    payload["length"] = {
        "target_slide_count": None,
        "slide_count_range": {"minimum": 5, "maximum": 7},
        "target_duration_minutes": None,
    }
    plan = PresentationDirectorPlanV1.model_validate(payload)
    assert plan.length.slide_count_range is not None


def test_top_level_capabilities_equal_slide_union() -> None:
    payload = load_fixture()
    capabilities = payload["required_capabilities"]
    assert isinstance(capabilities, list)
    capabilities.remove("speaker_notes")
    with pytest.raises(ValidationError, match="union of slide required_capabilities"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_top_level_capabilities_require_canonical_order() -> None:
    payload = load_fixture()
    capabilities = payload["required_capabilities"]
    assert isinstance(capabilities, list)
    capabilities[0], capabilities[1] = capabilities[1], capabilities[0]
    with pytest.raises(ValidationError, match="canonical sorted order"):
        PresentationDirectorPlanV1.model_validate(payload)
