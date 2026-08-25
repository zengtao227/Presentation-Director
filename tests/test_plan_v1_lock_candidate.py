from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import rfc8785

from presentation_director_contracts.lock_candidate_v1 import (
    BpsPresentationConstraintViewV02,
    DirectorLockDecisionsV1,
    LockCandidateError,
    build_director_lock_candidate_from_files,
    build_director_lock_candidate_v1,
)
from presentation_director_contracts.producer_v1 import ConfirmedDirectorLockPacketV1


def _constraint_view_data() -> dict[str, object]:
    return {
        "schema_version": "0.2",
        "profile": {
            "profile_id": "bps-presentation-director-bridge",
            "version": "0.2.0",
        },
        "authority": {
            "job_id": "job-001",
            "resolved_job_sha256": "a" * 64,
            "brand_package_sha256": "b" * 64,
            "output_format": "pptx",
        },
        "task_context": {
            "purpose": "Explain the approved governed evidence.",
            "audience": "Executive review",
            "output_locale": "en-US",
            "title": "Governed update",
            "market": None,
            "jurisdiction": None,
            "content_request": None,
        },
        "treatment": {
            "treatment_id": "editorial-pptx",
            "version": "1.0.0",
            "definition_sha256": "c" * 64,
            "slide_size": "wide",
            "density": "medium",
            "allowed_layouts": ["editorial-left", "editorial-split"],
        },
        "content": {
            "facts": [
                {
                    "fact_id": "fact-1",
                    "fact_type": "text",
                    "locale": "en-US",
                    "value": "Revenue grew on the approved basis.",
                    "source_ids": ["brand-src"],
                }
            ],
            "claims": [
                {
                    "claim_id": "claim-1",
                    "locale": "en-US",
                    "text": "Execution remains on the approved growth path.",
                    "source_ids": ["brand-src"],
                }
            ],
            "disclaimers": [
                {
                    "disclaimer_id": "disc-1",
                    "locale": "en-US",
                    "text": "Past performance is not a guarantee of future results.",
                    "source_ids": ["brand-src"],
                    "required": True,
                }
            ],
        },
        "governed_sources": [
            {
                "source_id": "brand-src",
                "root": "brand_package",
                "relative_location": "sources/approved.json",
                "sha256": "d" * 64,
                "media_type": "application/json",
            }
        ],
        "task_sources": [
            {
                "source_id": "task-notes",
                "root": "job",
                "relative_location": "sources/notes.md",
                "sha256": "e" * 64,
                "media_type": "text/markdown",
            }
        ],
        "assets": [
            {
                "asset_id": "image-1",
                "root": "brand_package",
                "relative_location": "assets/approved.png",
                "sha256": "f" * 64,
                "media_type": "image/png",
                "roles": ["logo", "supporting_image"],
                "treatment_required": True,
            }
        ],
        "form": {
            "allowed_fonts": ["Inter"],
            "brand_tokens": {
                "accent": "#0055ff",
                "background": "#ffffff",
                "text": "#111111",
            },
        },
    }


def _decisions_data() -> dict[str, object]:
    text_capabilities = ["editable_text", "font_family_assignment"]
    content_capabilities = [
        "editable_text",
        "embedded_images",
        "font_family_assignment",
        "speaker_notes",
    ]
    tokens = ["accent", "background", "text"]
    return {
        "identity": {
            "schema_id": "presentation-director-lock-decisions",
            "schema_version": "1.0.0",
        },
        "lock_packet_id": "lock-job-001-v1",
        "plan_id": "plan-job-001-v1",
        "audience_familiarity": "mixed",
        "thesis": "Approved evidence supports the proposed direction.",
        "narrative_arc": ["Frame", "Evidence", "Close"],
        "length": {
            "target_slide_count": 3,
            "slide_count_range": None,
            "target_duration_minutes": None,
        },
        "appendix_notes": [],
        "deck_omissions": [],
        "form_direction": {
            "name": "editorial-standard",
            "tone": "precise",
            "background_strategy": "light",
            "palette_role_intent": "approved tokens only",
            "typography_intent": "editable hierarchy",
            "chart_diagram_grammar": "native objects",
            "image_strategy": "approved assets only",
            "motion_policy": "none",
            "forbidden_patterns": [],
        },
        "slides": [
            {
                "slide_id": "s-cover",
                "slide_kind": "cover",
                "title": "Governed update",
                "purpose": "Frame the approved task.",
                "primary_claim_id": None,
                "supporting_content": [],
                "proof_object": {"kind": "text", "source_ids": []},
                "layout_family": "editorial-left",
                "visual_treatment": "cover-standard",
                "assets": [],
                "task_source_ids": [],
                "font_families": ["Inter"],
                "brand_token_ids": tokens,
                "reference_ids": [],
                "speaker_notes": [],
                "required_capabilities": text_capabilities,
            },
            {
                "slide_id": "s-content",
                "slide_kind": "content",
                "title": "Governed evidence",
                "purpose": "Present all governed content and the required asset.",
                "primary_claim_id": "claim-1",
                "supporting_content": [
                    {"content_kind": "disclaimer", "content_id": "disc-1"},
                    {"content_kind": "fact", "content_id": "fact-1"},
                ],
                "proof_object": {"kind": "text", "source_ids": ["brand-src"]},
                "layout_family": "editorial-split",
                "visual_treatment": "content-standard",
                "assets": [{"asset_id": "image-1", "roles": ["supporting_image"]}],
                "task_source_ids": ["task-notes"],
                "font_families": ["Inter"],
                "brand_token_ids": tokens,
                "reference_ids": [],
                "speaker_notes": ["Do not add unapproved figures."],
                "required_capabilities": content_capabilities,
            },
            {
                "slide_id": "s-closing",
                "slide_kind": "closing",
                "title": "Close",
                "purpose": "Close without adding new claims.",
                "primary_claim_id": None,
                "supporting_content": [],
                "proof_object": {"kind": "text", "source_ids": []},
                "layout_family": "editorial-left",
                "visual_treatment": "closing-standard",
                "assets": [],
                "task_source_ids": [],
                "font_families": ["Inter"],
                "brand_token_ids": tokens,
                "reference_ids": [],
                "speaker_notes": [],
                "required_capabilities": text_capabilities,
            },
        ],
        "omitted_content": [],
        "reference_only_inspiration": [],
    }


def _models() -> tuple[BpsPresentationConstraintViewV02, DirectorLockDecisionsV1]:
    return (
        BpsPresentationConstraintViewV02.model_validate(_constraint_view_data()),
        DirectorLockDecisionsV1.model_validate(_decisions_data()),
    )


def test_builds_complete_unconfirmed_candidate_from_governed_view() -> None:
    view, decisions = _models()

    candidate = build_director_lock_candidate_v1(view, decisions)
    payload = candidate.model_dump(mode="json")

    assert "confirmation_state" not in payload
    assert candidate.task_slug == view.authority.job_id
    assert candidate.content_lock.content_language == view.task_context.output_locale
    assert candidate.content_lock.audience.audience == view.task_context.audience
    assert candidate.content_lock.audience.desired_outcome == view.task_context.purpose
    assert candidate.content_lock.goal == view.task_context.purpose
    assert candidate.form_lock.treatment.treatment_id == view.treatment.treatment_id
    assert candidate.form_lock.treatment.definition_sha256 == view.treatment.definition_sha256

    content_slide = candidate.composition_lock.slides[1]
    assert content_slide.primary_claim is not None
    expected_claim_sha = hashlib.sha256(
        rfc8785.dumps(view.content.claims[0].model_dump(mode="json"))
    ).hexdigest()
    assert content_slide.primary_claim.value_sha256 == expected_claim_sha
    assert content_slide.primary_claim.source_ids == ["brand-src"]
    assert content_slide.assets[0].sha256 == view.assets[0].sha256
    assert content_slide.assets[0].roles == ["supporting_image"]

    confirmed = ConfirmedDirectorLockPacketV1.model_validate(
        {**payload, "confirmation_state": "confirmed"}
    )
    assert confirmed.lock_packet_id == candidate.lock_packet_id


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (
            lambda data: data["slides"][0].__setitem__(
                "layout_family", "unknown-layout"
            ),
            "unapproved layout",
        ),
        (
            lambda data: data["slides"][0].__setitem__(
                "font_families", ["Unknown Sans"]
            ),
            "unapproved fonts",
        ),
        (
            lambda data: data["slides"][0].__setitem__(
                "brand_token_ids", ["unknown-token"]
            ),
            "unknown brand tokens",
        ),
        (
            lambda data: data["slides"][1].__setitem__(
                "primary_claim_id", "unknown-claim"
            ),
            "content outside Constraint View",
        ),
        (
            lambda data: data["slides"][1].__setitem__(
                "assets",
                [{"asset_id": "unknown-asset", "roles": ["supporting_image"]}],
            ),
            "asset outside Constraint View",
        ),
        (
            lambda data: data["slides"][1]["assets"][0].__setitem__(
                "roles", ["unapproved_role"]
            ),
            "unapproved roles",
        ),
    ],
)
def test_governed_selections_fail_closed(
    mutation: object,
    match: str,
) -> None:
    view = BpsPresentationConstraintViewV02.model_validate(_constraint_view_data())
    decision_data = _decisions_data()
    assert callable(mutation)
    mutation(decision_data)
    decisions = DirectorLockDecisionsV1.model_validate(decision_data)

    with pytest.raises(LockCandidateError, match=match):
        build_director_lock_candidate_v1(view, decisions)


def test_required_disclaimer_cannot_be_omitted() -> None:
    view = BpsPresentationConstraintViewV02.model_validate(_constraint_view_data())
    decision_data = _decisions_data()
    decision_data["slides"][1]["supporting_content"] = [
        {"content_kind": "fact", "content_id": "fact-1"}
    ]
    decision_data["omitted_content"] = [
        {
            "content_kind": "disclaimer",
            "content_id": "disc-1",
            "omission_reason": "Try to hide the required disclaimer.",
        }
    ]
    decisions = DirectorLockDecisionsV1.model_validate(decision_data)

    with pytest.raises(LockCandidateError, match="required disclaimer cannot be omitted"):
        build_director_lock_candidate_v1(view, decisions)


def test_all_governed_content_requires_used_or_omitted_coverage() -> None:
    view = BpsPresentationConstraintViewV02.model_validate(_constraint_view_data())
    decision_data = _decisions_data()
    decision_data["slides"][1]["supporting_content"] = [
        {"content_kind": "fact", "content_id": "fact-1"}
    ]
    decisions = DirectorLockDecisionsV1.model_validate(decision_data)

    with pytest.raises(LockCandidateError, match="do not account for governed content"):
        build_director_lock_candidate_v1(view, decisions)


def test_treatment_required_asset_must_be_used() -> None:
    view = BpsPresentationConstraintViewV02.model_validate(_constraint_view_data())
    decision_data = _decisions_data()
    decision_data["slides"][1]["assets"] = []
    decision_data["slides"][1]["required_capabilities"] = [
        "editable_text",
        "font_family_assignment",
        "speaker_notes",
    ]
    decisions = DirectorLockDecisionsV1.model_validate(decision_data)

    with pytest.raises(LockCandidateError, match="omit treatment-required assets"):
        build_director_lock_candidate_v1(view, decisions)


def test_file_handoff_writes_once_and_never_adds_confirmation_state(tmp_path: Path) -> None:
    view_path = tmp_path / "constraint-view.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "lock-candidate.json"
    view_path.write_text(
        json.dumps(_constraint_view_data(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    decisions_path.write_text(
        json.dumps(_decisions_data(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    candidate = build_director_lock_candidate_from_files(
        view_path,
        decisions_path,
        output_path,
    )
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert "confirmation_state" not in persisted
    assert persisted == candidate.model_dump(mode="json")

    with pytest.raises(LockCandidateError, match="immutable and already exists"):
        build_director_lock_candidate_from_files(view_path, decisions_path, output_path)


def test_duplicate_json_key_is_rejected_before_output(tmp_path: Path) -> None:
    view_path = tmp_path / "constraint-view.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "lock-candidate.json"
    view_text = json.dumps(_constraint_view_data(), ensure_ascii=False, indent=2)
    view_path.write_text(
        view_text.replace(
            '  "schema_version": "0.2",',
            '  "schema_version": "0.2",\n  "schema_version": "0.2",',
            1,
        ),
        encoding="utf-8",
    )
    decisions_path.write_text(json.dumps(_decisions_data(), indent=2), encoding="utf-8")

    with pytest.raises(LockCandidateError, match="duplicate JSON object key: schema_version"):
        build_director_lock_candidate_from_files(view_path, decisions_path, output_path)
    assert not output_path.exists()


def test_type_normalization_in_decisions_is_rejected_before_output(tmp_path: Path) -> None:
    view_path = tmp_path / "constraint-view.json"
    decisions_path = tmp_path / "decisions.json"
    output_path = tmp_path / "lock-candidate.json"
    view_path.write_text(json.dumps(_constraint_view_data(), indent=2), encoding="utf-8")
    decisions = copy.deepcopy(_decisions_data())
    decisions["length"]["target_slide_count"] = "3"
    decisions_path.write_text(json.dumps(decisions, indent=2), encoding="utf-8")

    with pytest.raises(LockCandidateError, match="exact validated JSON types and values"):
        build_director_lock_candidate_from_files(view_path, decisions_path, output_path)
    assert not output_path.exists()
