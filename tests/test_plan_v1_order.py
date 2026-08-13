from __future__ import annotations

import copy
import json
from pathlib import Path

from presentation_director_contracts.plan_v1 import (
    PresentationDirectorPlanV1,
    presentation_director_plan_v1_sha256,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "presentation-director-plan-v1.golden.json"


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_slide_order_is_semantic_and_not_sorted_by_id() -> None:
    original_payload = load_fixture()
    original = PresentationDirectorPlanV1.model_validate(original_payload)
    changed_payload = copy.deepcopy(original_payload)
    slides = changed_payload["slides"]
    assert isinstance(slides, list)
    slides[0], slides[1] = slides[1], slides[0]
    changed = PresentationDirectorPlanV1.model_validate(changed_payload)
    assert [slide.slide_id for slide in changed.slides[:2]] == ["s02", "s01"]
    assert presentation_director_plan_v1_sha256(original) != presentation_director_plan_v1_sha256(changed)


def test_narrative_arc_order_is_semantic() -> None:
    original_payload = load_fixture()
    original = PresentationDirectorPlanV1.model_validate(original_payload)
    changed_payload = copy.deepcopy(original_payload)
    arc = changed_payload["narrative_arc"]
    assert isinstance(arc, list)
    arc[0], arc[1] = arc[1], arc[0]
    changed = PresentationDirectorPlanV1.model_validate(changed_payload)
    assert presentation_director_plan_v1_sha256(original) != presentation_director_plan_v1_sha256(changed)
