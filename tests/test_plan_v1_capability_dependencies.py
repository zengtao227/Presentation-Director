from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from presentation_director_contracts.plan_v1 import PresentationDirectorPlanV1

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "presentation-director-plan-v1.golden.json"


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def get_slide(payload: dict[str, object], index: int) -> dict[str, object]:
    slides = payload["slides"]
    assert isinstance(slides, list)
    item = slides[index]
    assert isinstance(item, dict)
    return item


def test_speaker_notes_require_capability() -> None:
    payload = load_fixture()
    get_slide(payload, 0)["speaker_notes"] = ["Keep this note."]
    with pytest.raises(ValidationError, match="speaker_notes capability"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_editable_chart_data_requires_native_chart() -> None:
    payload = load_fixture()
    get_slide(payload, 3)["required_capabilities"] = ["editable_chart_data", "editable_text"]
    with pytest.raises(ValidationError, match="requires native_chart"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_attached_connectors_require_native_shapes() -> None:
    payload = load_fixture()
    get_slide(payload, 4)["required_capabilities"] = ["attached_connectors", "editable_text"]
    with pytest.raises(ValidationError, match="requires native_shapes"):
        PresentationDirectorPlanV1.model_validate(payload)
