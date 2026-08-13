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
from presentation_director_contracts.producer_v1 import GovernedPlanProductionInputV1

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "presentation-director-plan-v1.golden.json"
GOLDEN_SHA = ROOT / "fixtures" / "presentation-director-plan-v1.golden.sha256"
SCHEMA = ROOT / "schemas" / "presentation-director-plan-v1.schema.json"
PRODUCTION_INPUT_SCHEMA = (
    ROOT / "schemas" / "presentation-director-plan-production-input-v1.schema.json"
)


def load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_golden_fixture_validates_and_digest_is_stable() -> None:
    plan = PresentationDirectorPlanV1.model_validate(load_fixture())
    assert presentation_director_plan_v1_sha256(plan) == GOLDEN_SHA.read_text().strip()
    assert presentation_director_plan_v1_bytes(plan) == presentation_director_plan_v1_bytes(
        PresentationDirectorPlanV1.model_validate(plan.model_dump(mode="json"))
    )


def test_checked_in_schema_matches_model_export() -> None:
    assert (
        json.loads(SCHEMA.read_text(encoding="utf-8"))
        == PresentationDirectorPlanV1.model_json_schema()
    )
    assert (
        json.loads(PRODUCTION_INPUT_SCHEMA.read_text(encoding="utf-8"))
        == GovernedPlanProductionInputV1.model_json_schema()
    )


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


@pytest.mark.parametrize(
    "field",
    [
        "task_source_ids",
        "font_families",
        "brand_token_ids",
        "reference_ids",
    ],
)
def test_governance_visible_slide_fields_are_required(field: str) -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    first = slides[0]
    assert isinstance(first, dict)
    first.pop(field)
    with pytest.raises(ValidationError, match="Field required"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_cover_slide_can_omit_primary_claim() -> None:
    plan = PresentationDirectorPlanV1.model_validate(load_fixture())
    assert plan.slides[0].slide_kind.value == "cover"
    assert plan.slides[0].primary_claim is None


def test_content_slide_cannot_omit_primary_claim() -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    second = slides[1]
    assert isinstance(second, dict)
    second["primary_claim"] = None
    with pytest.raises(ValidationError, match="content slides require"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_reference_only_flags_fail_closed() -> None:
    payload = load_fixture()
    references = payload["reference_only_inspiration"]
    assert isinstance(references, list)
    first = references[0]
    assert isinstance(first, dict)
    first["not_artifact_input"] = False
    with pytest.raises(ValidationError):
        PresentationDirectorPlanV1.model_validate(payload)


def test_unknown_slide_reference_fails_closed() -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    first = slides[0]
    assert isinstance(first, dict)
    first["reference_ids"] = ["unknown-reference"]
    with pytest.raises(ValidationError, match="exactly cover"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_governed_content_cannot_be_used_and_omitted() -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    second = slides[1]
    assert isinstance(second, dict)
    supporting = second["supporting_content"]
    assert isinstance(supporting, list)
    payload["omitted_content"] = [supporting[0] | {"omission_reason": "Duplicate omission"}]
    with pytest.raises(ValidationError, match="both used and omitted"):
        PresentationDirectorPlanV1.model_validate(payload)


def test_content_omission_requires_exact_reason() -> None:
    payload = load_fixture()
    omitted_content = payload["omitted_content"]
    assert isinstance(omitted_content, list)
    omission = omitted_content[0]
    assert isinstance(omission, dict)
    omission.pop("omission_reason")
    with pytest.raises(ValidationError, match="Field required"):
        PresentationDirectorPlanV1.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    ["task_source_ids", "font_families", "brand_token_ids"],
)
def test_governance_visible_sets_require_canonical_order(field: str) -> None:
    payload = load_fixture()
    slides = payload["slides"]
    assert isinstance(slides, list)
    first = slides[0]
    assert isinstance(first, dict)
    first[field] = ["z-value", "a-value"]
    with pytest.raises(ValidationError, match="canonical sorted order"):
        PresentationDirectorPlanV1.model_validate(payload)
