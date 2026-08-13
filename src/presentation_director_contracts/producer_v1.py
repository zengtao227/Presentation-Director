"""Deterministic producer boundary for the governed Plan V1 candidate."""

from __future__ import annotations

import hashlib
from typing import Literal

import rfc8785
from pydantic import Field, field_validator

from .plan_v1 import (
    PLAN_SCHEMA_ID,
    PLAN_SCHEMA_VERSION,
    PPTX_MEDIA_TYPE,
    AudienceIntent,
    CanonicalLocale,
    CapabilityVocabularyIdentity,
    ContentOmission,
    FormDirection,
    GovernanceBinding,
    LengthIntent,
    NonEmptyText,
    PlanIdentity,
    PresentationDirectorPlanV1,
    PresentationPlanSlideV1,
    ReferenceOnlyInspiration,
    StableId,
    StrictModel,
    TreatmentBinding,
)
from .vocabulary import CAPABILITY_VOCABULARY_ID, CAPABILITY_VOCABULARY_VERSION

LOCK_PACKET_SCHEMA_ID: Literal["presentation-director-lock-packet"] = (
    "presentation-director-lock-packet"
)
LOCK_PACKET_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"
PRODUCTION_INPUT_SCHEMA_ID: Literal["presentation-director-plan-production-input"] = (
    "presentation-director-plan-production-input"
)
PRODUCTION_INPUT_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"


class LockPacketIdentity(StrictModel):
    schema_id: Literal["presentation-director-lock-packet"]
    schema_version: Literal["1.0.0"]


class ProductionInputIdentity(StrictModel):
    schema_id: Literal["presentation-director-plan-production-input"]
    schema_version: Literal["1.0.0"]


class ContentLockV1(StrictModel):
    content_language: CanonicalLocale
    audience: AudienceIntent
    goal: NonEmptyText
    thesis: NonEmptyText
    narrative_arc: list[NonEmptyText] = Field(min_length=1)
    length: LengthIntent
    appendix_notes: list[NonEmptyText]
    deck_omissions: list[NonEmptyText]
    omitted_content: list[ContentOmission]

    @field_validator("deck_omissions")
    @classmethod
    def validate_deck_omissions(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)) or values != sorted(values):
            raise ValueError("deck_omissions must be sorted and unique")
        return values

    @field_validator("omitted_content")
    @classmethod
    def validate_omitted_content(cls, values: list[ContentOmission]) -> list[ContentOmission]:
        keys = [f"{item.content_kind.value}:{item.content_id}" for item in values]
        if len(keys) != len(set(keys)) or keys != sorted(keys):
            raise ValueError("omitted_content must be sorted and unique")
        return values


class FormLockV1(StrictModel):
    treatment: TreatmentBinding
    direction: FormDirection


class CompositionLockV1(StrictModel):
    slides: list[PresentationPlanSlideV1] = Field(min_length=1)
    reference_only_inspiration: list[ReferenceOnlyInspiration]

    @field_validator("reference_only_inspiration")
    @classmethod
    def validate_references(
        cls, values: list[ReferenceOnlyInspiration]
    ) -> list[ReferenceOnlyInspiration]:
        ids = [item.reference_id for item in values]
        if len(ids) != len(set(ids)) or ids != sorted(ids):
            raise ValueError("reference_only_inspiration must be sorted and unique")
        return values


class ConfirmedDirectorLockPacketV1(StrictModel):
    """Complete lock state; `confirmed` is state, not proof of actor authenticity."""

    identity: LockPacketIdentity
    lock_packet_id: StableId
    confirmation_state: Literal["confirmed"]
    plan_id: StableId
    task_slug: StableId
    output_format: Literal["pptx"]
    content_lock: ContentLockV1
    form_lock: FormLockV1
    composition_lock: CompositionLockV1


class GovernedPlanProductionInputV1(StrictModel):
    identity: ProductionInputIdentity
    lock_packet: ConfirmedDirectorLockPacketV1
    governance: GovernanceBinding


def governed_plan_production_input_v1_bytes(
    production_input: GovernedPlanProductionInputV1,
) -> bytes:
    validated = GovernedPlanProductionInputV1.model_validate(
        production_input.model_dump(mode="json")
    )
    return rfc8785.dumps(validated.model_dump(mode="json"))


def governed_plan_production_input_v1_sha256(
    production_input: GovernedPlanProductionInputV1,
) -> str:
    return hashlib.sha256(governed_plan_production_input_v1_bytes(production_input)).hexdigest()


def compile_presentation_director_plan_v1(
    production_input: GovernedPlanProductionInputV1,
) -> PresentationDirectorPlanV1:
    """Compile complete locks and BPS binding without inference or fallback."""

    validated = GovernedPlanProductionInputV1.model_validate(
        production_input.model_dump(mode="json")
    )
    packet = validated.lock_packet
    slide_capabilities = sorted(
        {
            capability
            for slide in packet.composition_lock.slides
            for capability in slide.required_capabilities
        },
        key=lambda capability: capability.value,
    )
    return PresentationDirectorPlanV1(
        identity=PlanIdentity(schema_id=PLAN_SCHEMA_ID, schema_version=PLAN_SCHEMA_VERSION),
        plan_id=packet.plan_id,
        task_slug=packet.task_slug,
        governance=validated.governance,
        output_format="pptx",
        expected_artifact_media_type=PPTX_MEDIA_TYPE,
        capability_vocabulary=CapabilityVocabularyIdentity(
            vocabulary_id=CAPABILITY_VOCABULARY_ID,
            version=CAPABILITY_VOCABULARY_VERSION,
        ),
        treatment=packet.form_lock.treatment,
        content_language=packet.content_lock.content_language,
        audience=packet.content_lock.audience,
        goal=packet.content_lock.goal,
        thesis=packet.content_lock.thesis,
        narrative_arc=packet.content_lock.narrative_arc,
        length=packet.content_lock.length,
        form=packet.form_lock.direction,
        slides=packet.composition_lock.slides,
        omitted_content=packet.content_lock.omitted_content,
        reference_only_inspiration=packet.composition_lock.reference_only_inspiration,
        required_capabilities=slide_capabilities,
        appendix_notes=packet.content_lock.appendix_notes,
        deck_omissions=packet.content_lock.deck_omissions,
    )
