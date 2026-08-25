from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from presentation_director_contracts.interactive_lock_v1 import (
    LockConfirmationError,
    confirm_lock_candidate_interactively,
)
from presentation_director_contracts.lock_candidate_v1 import (
    BpsPresentationConstraintViewV02,
    DirectorLockDecisionsV1,
    LockCandidateError,
    build_director_lock_candidate_v1,
)
from presentation_director_contracts.producer_v1 import (
    ConfirmedDirectorLockPacketV1,
    GovernedPlanProductionInputV1,
    compile_presentation_director_plan_v1,
)
from tests.test_plan_v1_lock_candidate import _constraint_view_data, _decisions_data

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_INPUT = ROOT / "fixtures" / "presentation-director-plan-production-input-v1.golden.json"


def _golden_candidate_data() -> dict[str, object]:
    payload = json.loads(PRODUCTION_INPUT.read_text(encoding="utf-8"))
    packet = copy.deepcopy(payload["lock_packet"])
    assert isinstance(packet, dict)
    packet.pop("confirmation_state")
    return packet


def _write_candidate(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _producer_models() -> tuple[BpsPresentationConstraintViewV02, DirectorLockDecisionsV1]:
    return (
        BpsPresentationConstraintViewV02.model_validate(_constraint_view_data()),
        DirectorLockDecisionsV1.model_validate(_decisions_data()),
    )


def test_valid_producer_candidate_enters_frozen_compiler() -> None:
    view, decisions = _producer_models()
    candidate = build_director_lock_candidate_v1(view, decisions)
    confirmed = ConfirmedDirectorLockPacketV1.model_validate(
        {**candidate.model_dump(mode="json"), "confirmation_state": "confirmed"}
    )
    production_input = GovernedPlanProductionInputV1.model_validate(
        {
            "identity": {
                "schema_id": "presentation-director-plan-production-input",
                "schema_version": "1.0.0",
            },
            "lock_packet": confirmed.model_dump(mode="json"),
            "governance": {
                "resolved_job_id": view.authority.job_id,
                "resolved_job_sha256": view.authority.resolved_job_sha256,
                "constraint_view_sha256": "9" * 64,
            },
        }
    )

    plan = compile_presentation_director_plan_v1(production_input)

    assert plan.plan_id == candidate.plan_id
    assert len(plan.slides) == len(candidate.composition_lock.slides)


def test_producer_rejects_slide_count_mismatch() -> None:
    view = BpsPresentationConstraintViewV02.model_validate(_constraint_view_data())
    decision_data = _decisions_data()
    length = decision_data["length"]
    assert isinstance(length, dict)
    length["target_slide_count"] = 4
    decisions = DirectorLockDecisionsV1.model_validate(decision_data)

    with pytest.raises(LockCandidateError, match="target_slide_count must equal"):
        build_director_lock_candidate_v1(view, decisions)


def test_producer_rejects_reference_closure_mismatch() -> None:
    view = BpsPresentationConstraintViewV02.model_validate(_constraint_view_data())
    decision_data = _decisions_data()
    slides = decision_data["slides"]
    assert isinstance(slides, list)
    first_slide = slides[0]
    assert isinstance(first_slide, dict)
    first_slide["reference_ids"] = ["undeclared-reference"]
    decisions = DirectorLockDecisionsV1.model_validate(decision_data)

    with pytest.raises(LockCandidateError, match="reference_only_inspiration must exactly cover"):
        build_director_lock_candidate_v1(view, decisions)


def _mismatched_length(candidate: dict[str, object]) -> None:
    content_lock = candidate["content_lock"]
    assert isinstance(content_lock, dict)
    length = content_lock["length"]
    assert isinstance(length, dict)
    length["target_slide_count"] = 7


def _unknown_reference(candidate: dict[str, object]) -> None:
    composition_lock = candidate["composition_lock"]
    assert isinstance(composition_lock, dict)
    slides = composition_lock["slides"]
    assert isinstance(slides, list)
    first_slide = slides[0]
    assert isinstance(first_slide, dict)
    first_slide["reference_ids"] = ["editorial-rhythm", "unknown-reference"]


def _duplicate_slide_id(candidate: dict[str, object]) -> None:
    composition_lock = candidate["composition_lock"]
    assert isinstance(composition_lock, dict)
    slides = composition_lock["slides"]
    assert isinstance(slides, list)
    first_slide = slides[0]
    second_slide = slides[1]
    assert isinstance(first_slide, dict)
    assert isinstance(second_slide, dict)
    second_slide["slide_id"] = first_slide["slide_id"]


def _used_and_omitted_content(candidate: dict[str, object]) -> None:
    content_lock = candidate["content_lock"]
    assert isinstance(content_lock, dict)
    omitted_content = content_lock["omitted_content"]
    assert isinstance(omitted_content, list)
    omission = omitted_content[0]
    assert isinstance(omission, dict)
    omission["content_id"] = "fact-1"


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (_mismatched_length, "target_slide_count must equal"),
        (_unknown_reference, "reference_only_inspiration must exactly cover"),
        (_duplicate_slide_id, "slides must have unique slide_id values"),
        (_used_and_omitted_content, "governed content cannot be both used and omitted"),
    ],
)
def test_confirmation_rejects_compiler_invalid_candidate_before_browser(
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None],
    match: str,
) -> None:
    candidate_data = _golden_candidate_data()
    mutate(candidate_data)
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    browser_called = False

    def opener(url: str) -> bool:
        nonlocal browser_called
        del url
        browser_called = True
        return True

    with pytest.raises(LockConfirmationError, match=match):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            browser_opener=opener,
        )

    assert browser_called is False
    assert not output_path.exists()
