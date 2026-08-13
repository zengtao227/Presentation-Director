from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from presentation_director_contracts.plan_v1 import (
    PresentationDirectorPlanV1,
    presentation_director_plan_v1_sha256,
)
from presentation_director_contracts.producer_v1 import (
    GovernedPlanProductionInputV1,
    compile_presentation_director_plan_v1,
    governed_plan_production_input_v1_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_INPUT = ROOT / "fixtures" / "presentation-director-plan-production-input-v1.golden.json"
PLAN = ROOT / "fixtures" / "presentation-director-plan-v1.golden.json"


def load_production_input() -> dict[str, object]:
    return json.loads(PRODUCTION_INPUT.read_text(encoding="utf-8"))


def test_producer_reconstructs_exact_golden_plan() -> None:
    production_input = GovernedPlanProductionInputV1.model_validate(load_production_input())
    produced = compile_presentation_director_plan_v1(production_input)
    golden = PresentationDirectorPlanV1.model_validate_json(PLAN.read_bytes())
    assert produced == golden
    assert presentation_director_plan_v1_sha256(produced) == presentation_director_plan_v1_sha256(
        golden
    )


def test_producer_is_deterministic_and_derives_capability_union() -> None:
    production_input = GovernedPlanProductionInputV1.model_validate(load_production_input())
    first = compile_presentation_director_plan_v1(production_input)
    second = compile_presentation_director_plan_v1(production_input)
    assert first == second
    assert governed_plan_production_input_v1_sha256(
        production_input
    ) == governed_plan_production_input_v1_sha256(production_input)
    assert [capability.value for capability in first.required_capabilities] == sorted(
        {capability.value for slide in first.slides for capability in slide.required_capabilities}
    )


def test_legacy_brief_confirmed_shape_is_rejected() -> None:
    legacy_brief = {
        "confirmed": True,
        "output_format": "pptx",
        "confirmation_gate": {
            "method": "browser-form",
            "confirmed_by": "user-click",
            "token_verified": True,
        },
    }
    with pytest.raises(ValidationError):
        GovernedPlanProductionInputV1.model_validate(legacy_brief)


def test_missing_complete_lock_field_fails_before_plan_production() -> None:
    payload = load_production_input()
    lock_packet = payload["lock_packet"]
    assert isinstance(lock_packet, dict)
    content_lock = lock_packet["content_lock"]
    assert isinstance(content_lock, dict)
    content_lock.pop("thesis")
    with pytest.raises(ValidationError, match="Field required"):
        GovernedPlanProductionInputV1.model_validate(payload)


def test_unconfirmed_lock_packet_is_rejected() -> None:
    payload = load_production_input()
    lock_packet = payload["lock_packet"]
    assert isinstance(lock_packet, dict)
    lock_packet["confirmation_state"] = "draft"
    with pytest.raises(ValidationError):
        GovernedPlanProductionInputV1.model_validate(payload)


def test_governance_binding_changes_plan_digest() -> None:
    original_payload = load_production_input()
    changed_payload = copy.deepcopy(original_payload)
    governance = changed_payload["governance"]
    assert isinstance(governance, dict)
    governance["constraint_view_sha256"] = "f" * 64
    original = compile_presentation_director_plan_v1(
        GovernedPlanProductionInputV1.model_validate(original_payload)
    )
    changed = compile_presentation_director_plan_v1(
        GovernedPlanProductionInputV1.model_validate(changed_payload)
    )
    assert presentation_director_plan_v1_sha256(original) != presentation_director_plan_v1_sha256(
        changed
    )
