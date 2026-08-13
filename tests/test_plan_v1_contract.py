from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from presentation_director_contracts.plan_v1 import (
    PresentationDirectorPlanV1,
    presentation_director_plan_v1_bytes,
    presentation_director_plan_v1_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "presentation-director-plan-v1.golden.json"
GOLDEN_SHA = ROOT / "fixtures" / "presentation-director-plan-v1.golden.sha256"
SCHEMA = ROOT / "schemas" / "presentation-director-plan-v1.schema.json"


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_golden_fixture_validates_and_digest_is_stable() -> None:
    plan = PresentationDirectorPlanV1.model_validate(load_fixture())
    assert presentation_director_plan_v1_sha256(plan) == GOLDEN_SHA.read_text().strip()
    assert presentation_director_plan_v1_bytes(plan) == presentation_director_plan_v1_bytes(
        PresentationDirectorPlanV1.model_validate(plan.model_dump(mode="json"))
    )


def test_checked_in_schema_matches_model_export() -> None:
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == PresentationDirectorPlanV1.model_json_schema()


def test_identity_and_protocol_fields_are_explicit() -> None:
    for field in (
        "identity",
        "output_format",
        "expected_artifact_media_type",
        "capability_vocabulary",
    ):
        payload = load_fixture()
        payload.pop(field)
        with pytest.raises(ValidationError, match="Field required"):
            PresentationDirectorPlanV1.model_validate(payload)


def test_unknown_fields_fail_closed() -> None:
    payload = load_fixture()
    payload["provider_id"] = "example-provider"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_unknown_capability_is_rejected() -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    first = slides[0]
    assert isinstance(first, dict)
    first["required_capabilities"] = ["implementation_helper"]
    with pytest.raises(ValidationError):
        PresentationDirectorPlanV1.model_validate(payload)
