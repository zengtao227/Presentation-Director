"""Frozen-candidate Presentation Director Plan V1 machine contract."""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Annotated, Literal

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .vocabulary import PresentationCapability

PLAN_SCHEMA_ID: Literal["presentation-director-plan"] = "presentation-director-plan"
PLAN_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"
PPTX_MEDIA_TYPE: Literal[
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
] = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

NonEmptyText = Annotated[str, Field(min_length=1)]
PositiveInt = Annotated[int, Field(gt=0)]
StableId = Annotated[str, Field(pattern=_STABLE_ID_RE.pattern)]
Sha256 = Annotated[str, Field(pattern=_SHA256_RE.pattern)]
CanonicalLocale = Annotated[str, Field(pattern=_LOCALE_RE.pattern)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


def _sorted_unique(values: list[str], *, label: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")
    if values != sorted(values):
        raise ValueError(f"{label} must use canonical sorted order")
    return values


class ContentKind(str, Enum):
    FACT = "fact"
    CLAIM = "claim"
    DISCLAIMER = "disclaimer"


class ProofObjectKind(str, Enum):
    TEXT = "text"
    CHART = "chart"
    TABLE = "table"
    QUOTE = "quote"
    SCREENSHOT = "screenshot"
    ARCHITECTURE_MAP = "architecture_map"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    CHECKLIST = "checklist"
    CASE = "case"
    DIAGRAM = "diagram"
    IMAGE = "image"


class ReferenceInfluence(str, Enum):
    COMPOSITION_PATTERN = "composition_pattern"
    LAYOUT_RHYTHM = "layout_rhythm"
    SPACING = "spacing"


class SlideKind(str, Enum):
    COVER = "cover"
    SECTION_DIVIDER = "section_divider"
    CONTENT = "content"
    CLOSING = "closing"


class PlanIdentity(StrictModel):
    schema_id: Literal["presentation-director-plan"]
    schema_version: Literal["1.0.0"]


class CapabilityVocabularyIdentity(StrictModel):
    vocabulary_id: Literal["presentation-artifact-capabilities"]
    version: Literal["1.0.0"]


class GovernanceBinding(StrictModel):
    resolved_job_id: StableId
    resolved_job_sha256: Sha256
    constraint_view_sha256: Sha256


class TreatmentBinding(StrictModel):
    treatment_id: StableId
    version: NonEmptyText
    definition_sha256: Sha256


class AudienceIntent(StrictModel):
    audience: NonEmptyText
    familiarity: NonEmptyText
    desired_outcome: NonEmptyText


class SlideCountRange(StrictModel):
    minimum: PositiveInt
    maximum: PositiveInt

    @model_validator(mode="after")
    def validate_order(self) -> SlideCountRange:
        if self.minimum > self.maximum:
            raise ValueError("slide_count_range.minimum must not exceed maximum")
        return self


class LengthIntent(StrictModel):
    target_slide_count: PositiveInt | None = None
    slide_count_range: SlideCountRange | None = None
    target_duration_minutes: PositiveInt | None = None

    @model_validator(mode="after")
    def validate_primary_length(self) -> LengthIntent:
        if (self.target_slide_count is None) == (self.slide_count_range is None):
            raise ValueError("exactly one of target_slide_count or slide_count_range is required")
        return self


class FormDirection(StrictModel):
    name: NonEmptyText
    tone: NonEmptyText
    background_strategy: NonEmptyText
    palette_role_intent: NonEmptyText
    typography_intent: NonEmptyText
    chart_diagram_grammar: NonEmptyText
    image_strategy: NonEmptyText
    motion_policy: NonEmptyText
    forbidden_patterns: list[NonEmptyText]

    @field_validator("forbidden_patterns")
    @classmethod
    def validate_forbidden_patterns(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="forbidden_patterns")


class ContentBinding(StrictModel):
    content_kind: ContentKind
    content_id: StableId
    value_sha256: Sha256
    source_ids: list[StableId] = Field(min_length=1)

    @field_validator("source_ids")
    @classmethod
    def validate_source_ids(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="content source_ids")


class ContentOmission(ContentBinding):
    omission_reason: NonEmptyText


class AssetBinding(StrictModel):
    asset_id: StableId
    sha256: Sha256
    roles: list[StableId] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="asset roles")


class ProofObject(StrictModel):
    kind: ProofObjectKind
    source_ids: list[StableId]
    dataset_ids: list[StableId]

    @field_validator("source_ids", "dataset_ids")
    @classmethod
    def validate_ids(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="proof object ids")


class ReferenceOnlyInspiration(StrictModel):
    reference_id: StableId
    label: NonEmptyText
    locator: NonEmptyText
    influence: ReferenceInfluence
    reference_only: Literal[True]
    non_governing: Literal[True]
    not_artifact_input: Literal[True]


class PresentationPlanSlideV1(StrictModel):
    """One slide in semantic deck order; list position is part of Plan meaning."""

    slide_id: StableId
    slide_kind: SlideKind
    title: NonEmptyText
    purpose: NonEmptyText
    primary_claim: ContentBinding | None = None
    supporting_content: list[ContentBinding]
    proof_object: ProofObject
    layout_family: StableId
    visual_treatment: NonEmptyText
    assets: list[AssetBinding]
    task_source_ids: list[StableId]
    font_families: list[NonEmptyText] = Field(min_length=1)
    brand_token_ids: list[StableId] = Field(min_length=1)
    reference_ids: list[StableId]
    speaker_notes: list[NonEmptyText]
    required_capabilities: list[PresentationCapability] = Field(min_length=1)

    @field_validator(
        "task_source_ids",
        "font_families",
        "brand_token_ids",
        "reference_ids",
    )
    @classmethod
    def validate_governed_expression_ids(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="governed expression ids")

    @field_validator("supporting_content")
    @classmethod
    def validate_supporting_content(cls, values: list[ContentBinding]) -> list[ContentBinding]:
        keys = [f"{item.content_kind.value}:{item.content_id}" for item in values]
        if len(keys) != len(set(keys)):
            raise ValueError("supporting_content must not contain duplicates")
        if keys != sorted(keys):
            raise ValueError("supporting_content must use canonical sorted order")
        return values

    @field_validator("assets")
    @classmethod
    def validate_assets(cls, values: list[AssetBinding]) -> list[AssetBinding]:
        ids = [item.asset_id for item in values]
        if len(ids) != len(set(ids)):
            raise ValueError("assets must not contain duplicates")
        if ids != sorted(ids):
            raise ValueError("assets must use canonical sorted order")
        return values

    @field_validator("required_capabilities")
    @classmethod
    def validate_capabilities(
        cls, values: list[PresentationCapability]
    ) -> list[PresentationCapability]:
        _sorted_unique([item.value for item in values], label="slide required_capabilities")
        return values

    @model_validator(mode="after")
    def validate_semantics(self) -> PresentationPlanSlideV1:
        if self.slide_kind is SlideKind.CONTENT and self.primary_claim is None:
            raise ValueError("content slides require a governed primary_claim")
        if (
            self.primary_claim is not None
            and self.primary_claim.content_kind is not ContentKind.CLAIM
        ):
            raise ValueError("primary_claim.content_kind must be claim")
        if self.primary_claim is not None:
            primary_key = (self.primary_claim.content_kind.value, self.primary_claim.content_id)
            if any(
                (item.content_kind.value, item.content_id) == primary_key
                for item in self.supporting_content
            ):
                raise ValueError("primary_claim must not be duplicated in supporting_content")

        capabilities = set(self.required_capabilities)
        if PresentationCapability.EDITABLE_TEXT not in capabilities:
            raise ValueError("every slide requires editable_text capability")
        if PresentationCapability.THEME_FONTS not in capabilities:
            raise ValueError("non-empty font_families require theme_fonts capability")
        if self.speaker_notes and PresentationCapability.SPEAKER_NOTES not in capabilities:
            raise ValueError("non-empty speaker_notes require speaker_notes capability")
        if self.assets and PresentationCapability.EMBEDDED_IMAGES not in capabilities:
            raise ValueError("non-empty assets require embedded_images capability")
        if (
            PresentationCapability.EDITABLE_CHART_DATA in capabilities
            and PresentationCapability.NATIVE_CHART not in capabilities
        ):
            raise ValueError("editable_chart_data capability requires native_chart")
        if (
            PresentationCapability.ATTACHED_CONNECTORS in capabilities
            and PresentationCapability.NATIVE_SHAPES not in capabilities
        ):
            raise ValueError("attached_connectors capability requires native_shapes")

        proof_capability = {
            ProofObjectKind.TABLE: PresentationCapability.NATIVE_TABLE,
            ProofObjectKind.CHART: PresentationCapability.NATIVE_CHART,
            ProofObjectKind.ARCHITECTURE_MAP: PresentationCapability.NATIVE_SHAPES,
            ProofObjectKind.DIAGRAM: PresentationCapability.NATIVE_SHAPES,
            ProofObjectKind.IMAGE: PresentationCapability.EMBEDDED_IMAGES,
            ProofObjectKind.SCREENSHOT: PresentationCapability.EMBEDDED_IMAGES,
        }.get(self.proof_object.kind)
        if proof_capability is not None and proof_capability not in capabilities:
            raise ValueError(
                f"{self.proof_object.kind.value} proof object requires "
                f"{proof_capability.value} capability"
            )
        return self


class PresentationDirectorPlanV1(StrictModel):
    identity: PlanIdentity
    plan_id: StableId
    task_slug: StableId
    governance: GovernanceBinding
    output_format: Literal["pptx"]
    expected_artifact_media_type: Literal[
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ]
    capability_vocabulary: CapabilityVocabularyIdentity
    treatment: TreatmentBinding
    content_language: CanonicalLocale
    audience: AudienceIntent
    goal: NonEmptyText
    thesis: NonEmptyText
    narrative_arc: list[NonEmptyText] = Field(min_length=1)
    length: LengthIntent
    form: FormDirection
    slides: list[PresentationPlanSlideV1] = Field(min_length=1)
    omitted_content: list[ContentOmission]
    reference_only_inspiration: list[ReferenceOnlyInspiration]
    required_capabilities: list[PresentationCapability] = Field(min_length=1)
    appendix_notes: list[NonEmptyText]
    deck_omissions: list[NonEmptyText]

    @field_validator("required_capabilities")
    @classmethod
    def validate_required_capabilities(
        cls, values: list[PresentationCapability]
    ) -> list[PresentationCapability]:
        _sorted_unique([item.value for item in values], label="required_capabilities")
        return values

    @field_validator("deck_omissions")
    @classmethod
    def validate_deck_omissions(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="deck_omissions")

    @field_validator("omitted_content")
    @classmethod
    def validate_omitted_content(cls, values: list[ContentOmission]) -> list[ContentOmission]:
        keys = [f"{item.content_kind.value}:{item.content_id}" for item in values]
        _sorted_unique(keys, label="omitted_content")
        return values

    @field_validator("reference_only_inspiration")
    @classmethod
    def validate_references(
        cls, values: list[ReferenceOnlyInspiration]
    ) -> list[ReferenceOnlyInspiration]:
        ids = [item.reference_id for item in values]
        _sorted_unique(ids, label="reference_only_inspiration")
        return values

    @model_validator(mode="after")
    def validate_deck(self) -> PresentationDirectorPlanV1:
        slide_ids = [slide.slide_id for slide in self.slides]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("slides must have unique slide_id values")

        slide_count = len(self.slides)
        if self.length.target_slide_count is not None:
            if self.length.target_slide_count != slide_count:
                raise ValueError("target_slide_count must equal the persisted slide count")
        else:
            assert self.length.slide_count_range is not None
            if not (
                self.length.slide_count_range.minimum
                <= slide_count
                <= self.length.slide_count_range.maximum
            ):
                raise ValueError("persisted slide count must fall inside slide_count_range")

        required = {item.value for item in self.required_capabilities}
        slide_required = {
            item.value for slide in self.slides for item in slide.required_capabilities
        }
        if required != slide_required:
            raise ValueError(
                "required_capabilities must equal the union of slide required_capabilities"
            )

        used_content = {
            (item.content_kind, item.content_id)
            for slide in self.slides
            for item in (
                ([slide.primary_claim] if slide.primary_claim is not None else [])
                + slide.supporting_content
            )
        }
        omitted_content = {(item.content_kind, item.content_id) for item in self.omitted_content}
        conflicts = sorted(
            f"{kind.value}:{content_id}" for kind, content_id in used_content & omitted_content
        )
        if conflicts:
            raise ValueError(
                "governed content cannot be both used and omitted: " + ", ".join(conflicts)
            )

        declared_references = {
            reference.reference_id for reference in self.reference_only_inspiration
        }
        used_references = {
            reference_id for slide in self.slides for reference_id in slide.reference_ids
        }
        if used_references != declared_references:
            unknown = sorted(used_references - declared_references)
            unused = sorted(declared_references - used_references)
            details: list[str] = []
            if unknown:
                details.append("unknown=" + ",".join(unknown))
            if unused:
                details.append("unused=" + ",".join(unused))
            raise ValueError(
                "reference_only_inspiration must exactly cover slide reference_ids: "
                + "; ".join(details)
            )
        return self


def presentation_director_plan_v1_bytes(plan: PresentationDirectorPlanV1) -> bytes:
    """Return RFC 8785 canonical bytes for a fully validated Plan V1."""

    validated = PresentationDirectorPlanV1.model_validate(plan.model_dump(mode="json"))
    return rfc8785.dumps(validated.model_dump(mode="json"))


def presentation_director_plan_v1_sha256(plan: PresentationDirectorPlanV1) -> str:
    return hashlib.sha256(presentation_director_plan_v1_bytes(plan)).hexdigest()
