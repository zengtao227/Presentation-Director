"""Director-owned lock candidate producer for the BPS Presentation Constraint View handoff.

The BPS bridge owns the governed constraint view. Presentation Director owns narrative and
composition decisions inside that view. This module combines those two inputs into one complete,
unconfirmed lock candidate that can then cross the separate interactive confirmation boundary.

It deliberately does not import Brand Production Studio, does not infer authority from the legacy
``brief-confirmed.json``, and does not add ``confirmation_state``. The BPS-side conformance check
remains authoritative after the confirmed packet is compiled into a Plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Annotated, Any, Literal, NoReturn

import rfc8785
from pydantic import Field, field_validator, model_validator

from .plan_v1 import (
    AudienceIntent,
    CanonicalLocale,
    ContentBinding,
    ContentKind,
    ContentOmission,
    FormDirection,
    LengthIntent,
    NonEmptyText,
    PresentationPlanSlideV1,
    ProofObject,
    ReferenceOnlyInspiration,
    Sha256,
    StableId,
    StrictModel,
    TreatmentBinding,
)
from .producer_v1 import (
    LOCK_PACKET_SCHEMA_ID,
    LOCK_PACKET_SCHEMA_VERSION,
    CompositionLockV1,
    ConfirmedDirectorLockPacketV1,
    ContentLockV1,
    FormLockV1,
    LockPacketIdentity,
)
from .vocabulary import PresentationCapability

BPS_BRIDGE_PROFILE_ID: Literal["bps-presentation-director-bridge"] = (
    "bps-presentation-director-bridge"
)
BPS_BRIDGE_PROFILE_VERSION: Literal["0.2.0"] = "0.2.0"
BPS_CONSTRAINT_VIEW_SCHEMA_VERSION: Literal["0.2"] = "0.2"
LOCK_DECISIONS_SCHEMA_ID: Literal["presentation-director-lock-decisions"] = (
    "presentation-director-lock-decisions"
)
LOCK_DECISIONS_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"


class LockCandidateError(ValueError):
    """The governed handoff cannot produce a safe complete lock candidate."""


def _fail(message: str) -> NoReturn:
    raise LockCandidateError(message)


def _sorted_unique(values: list[str], *, label: str) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")
    if values != sorted(values):
        raise ValueError(f"{label} must use canonical sorted order")
    return values


def _sorted_unique_by_id(values: list[Any], *, attribute: str, label: str) -> list[Any]:
    ids = [str(getattr(value, attribute)) for value in values]
    _sorted_unique(ids, label=label)
    return values


class BpsBridgeProfileIdentity(StrictModel):
    profile_id: Literal["bps-presentation-director-bridge"]
    version: Literal["0.2.0"]


class BpsAuthorityBinding(StrictModel):
    job_id: StableId
    resolved_job_sha256: Sha256
    brand_package_sha256: Sha256
    output_format: Literal["pptx"]


class BpsTaskContext(StrictModel):
    purpose: NonEmptyText
    audience: NonEmptyText
    output_locale: CanonicalLocale
    title: str | None
    market: str | None
    jurisdiction: str | None
    content_request: str | None


class BpsTreatmentConstraint(StrictModel):
    treatment_id: StableId
    version: NonEmptyText
    definition_sha256: Sha256
    slide_size: NonEmptyText
    density: NonEmptyText
    allowed_layouts: list[StableId] = Field(min_length=1)

    @field_validator("allowed_layouts")
    @classmethod
    def validate_layouts(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="allowed_layouts")


class BpsTextFact(StrictModel):
    fact_id: StableId
    fact_type: Literal["text"]
    locale: CanonicalLocale
    value: NonEmptyText
    source_ids: list[StableId] = Field(min_length=1)

    @field_validator("source_ids")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="text fact source_ids")


class BpsNumberFact(StrictModel):
    fact_id: StableId
    source_ids: list[StableId] = Field(min_length=1)
    fact_type: Literal["number"]
    value: Annotated[str, Field(pattern=r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")]
    unit: str | None
    scale: int = Field(ge=1, strict=True)

    @field_validator("source_ids")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="number fact source_ids")


class BpsMonetaryFact(StrictModel):
    fact_id: StableId
    source_ids: list[StableId] = Field(min_length=1)
    fact_type: Literal["monetary"]
    amount: Annotated[str, Field(pattern=r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    scale: int = Field(ge=1, strict=True)

    @field_validator("source_ids")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="monetary fact source_ids")


BpsFact = Annotated[
    BpsTextFact | BpsNumberFact | BpsMonetaryFact,
    Field(discriminator="fact_type"),
]


class BpsResolvedClaim(StrictModel):
    claim_id: StableId
    locale: CanonicalLocale
    text: NonEmptyText
    source_ids: list[StableId] = Field(min_length=1)

    @field_validator("source_ids")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="claim source_ids")


class BpsResolvedDisclaimer(StrictModel):
    disclaimer_id: StableId
    locale: CanonicalLocale
    text: NonEmptyText
    source_ids: list[StableId] = Field(min_length=1)
    required: bool

    @field_validator("source_ids")
    @classmethod
    def validate_sources(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="disclaimer source_ids")


class BpsPresentationContent(StrictModel):
    facts: list[BpsFact]
    claims: list[BpsResolvedClaim]
    disclaimers: list[BpsResolvedDisclaimer]

    @field_validator("facts")
    @classmethod
    def validate_facts(cls, values: list[BpsFact]) -> list[BpsFact]:
        return _sorted_unique_by_id(values, attribute="fact_id", label="facts")

    @field_validator("claims")
    @classmethod
    def validate_claims(cls, values: list[BpsResolvedClaim]) -> list[BpsResolvedClaim]:
        return _sorted_unique_by_id(values, attribute="claim_id", label="claims")

    @field_validator("disclaimers")
    @classmethod
    def validate_disclaimers(
        cls, values: list[BpsResolvedDisclaimer]
    ) -> list[BpsResolvedDisclaimer]:
        return _sorted_unique_by_id(values, attribute="disclaimer_id", label="disclaimers")


class BpsSourceConstraint(StrictModel):
    source_id: StableId
    root: Literal["brand_package", "job"]
    relative_location: NonEmptyText
    sha256: Sha256
    media_type: str | None


class BpsAssetConstraint(StrictModel):
    asset_id: StableId
    root: Literal["brand_package"]
    relative_location: NonEmptyText
    sha256: Sha256
    media_type: str | None
    roles: list[StableId] = Field(min_length=1)
    treatment_required: bool

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="asset roles")


class BpsFormConstraints(StrictModel):
    allowed_fonts: list[NonEmptyText] = Field(min_length=1)
    brand_tokens: dict[StableId, NonEmptyText] = Field(min_length=1)

    @field_validator("allowed_fonts")
    @classmethod
    def validate_fonts(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="allowed_fonts")


class BpsPresentationConstraintViewV02(StrictModel):
    """Exact file-level handoff surface for BPS bridge profile 0.2.0.

    This local model is a compatibility parser, not a replacement BPS contract. Director remains
    decoupled from the BPS package while still refusing malformed or out-of-profile handoff bytes.
    """

    schema_version: Literal["0.2"]
    profile: BpsBridgeProfileIdentity
    authority: BpsAuthorityBinding
    task_context: BpsTaskContext
    treatment: BpsTreatmentConstraint
    content: BpsPresentationContent
    governed_sources: list[BpsSourceConstraint]
    task_sources: list[BpsSourceConstraint]
    assets: list[BpsAssetConstraint]
    form: BpsFormConstraints

    @field_validator("governed_sources", "task_sources")
    @classmethod
    def validate_sources(cls, values: list[BpsSourceConstraint]) -> list[BpsSourceConstraint]:
        return _sorted_unique_by_id(values, attribute="source_id", label="presentation sources")

    @field_validator("assets")
    @classmethod
    def validate_assets(cls, values: list[BpsAssetConstraint]) -> list[BpsAssetConstraint]:
        return _sorted_unique_by_id(values, attribute="asset_id", label="presentation assets")

    @model_validator(mode="after")
    def validate_handoff_closure(self) -> BpsPresentationConstraintViewV02:
        governed_ids = {source.source_id for source in self.governed_sources}
        task_ids = {source.source_id for source in self.task_sources}
        if governed_ids & task_ids:
            raise ValueError("governed and task source namespaces must be disjoint")
        if any(source.root != "brand_package" for source in self.governed_sources):
            raise ValueError("governed sources must be rooted at brand_package")
        if any(source.root != "job" for source in self.task_sources):
            raise ValueError("task sources must be rooted at job")

        for fact in self.content.facts:
            if not set(fact.source_ids) <= governed_ids:
                raise ValueError("fact references a source outside governed_sources")
            if isinstance(fact, BpsTextFact) and fact.locale != self.task_context.output_locale:
                raise ValueError("text fact locale differs from output_locale")
        for claim in self.content.claims:
            if not set(claim.source_ids) <= governed_ids:
                raise ValueError("claim references a source outside governed_sources")
            if claim.locale != self.task_context.output_locale:
                raise ValueError("claim locale differs from output_locale")
        for disclaimer in self.content.disclaimers:
            if not set(disclaimer.source_ids) <= governed_ids:
                raise ValueError("disclaimer references a source outside governed_sources")
            if disclaimer.locale != self.task_context.output_locale:
                raise ValueError("disclaimer locale differs from output_locale")
        return self


class LockDecisionsIdentity(StrictModel):
    schema_id: Literal["presentation-director-lock-decisions"]
    schema_version: Literal["1.0.0"]


class ContentReferenceDecision(StrictModel):
    content_kind: ContentKind
    content_id: StableId


class ContentOmissionDecision(ContentReferenceDecision):
    omission_reason: NonEmptyText


class AssetUseDecision(StrictModel):
    asset_id: StableId
    roles: list[StableId] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="asset usage roles")


class PresentationSlideDecisionV1(StrictModel):
    slide_id: StableId
    slide_kind: Literal["cover", "section_divider", "content", "closing"]
    title: NonEmptyText
    purpose: NonEmptyText
    primary_claim_id: StableId | None
    supporting_content: list[ContentReferenceDecision]
    proof_object: ProofObject
    layout_family: StableId
    visual_treatment: NonEmptyText
    assets: list[AssetUseDecision]
    task_source_ids: list[StableId]
    font_families: list[NonEmptyText] = Field(min_length=1)
    brand_token_ids: list[StableId] = Field(min_length=1)
    reference_ids: list[StableId]
    speaker_notes: list[NonEmptyText]
    required_capabilities: list[PresentationCapability] = Field(min_length=1)

    @field_validator("supporting_content")
    @classmethod
    def validate_supporting_content(
        cls, values: list[ContentReferenceDecision]
    ) -> list[ContentReferenceDecision]:
        keys = [f"{item.content_kind.value}:{item.content_id}" for item in values]
        _sorted_unique(keys, label="supporting_content")
        return values

    @field_validator("assets")
    @classmethod
    def validate_assets(cls, values: list[AssetUseDecision]) -> list[AssetUseDecision]:
        return _sorted_unique_by_id(values, attribute="asset_id", label="slide assets")

    @field_validator("task_source_ids", "font_families", "brand_token_ids", "reference_ids")
    @classmethod
    def validate_sorted_strings(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="slide governed selections")

    @field_validator("required_capabilities")
    @classmethod
    def validate_capabilities(
        cls, values: list[PresentationCapability]
    ) -> list[PresentationCapability]:
        _sorted_unique([value.value for value in values], label="required_capabilities")
        return values


class DirectorLockDecisionsV1(StrictModel):
    identity: LockDecisionsIdentity
    lock_packet_id: StableId
    plan_id: StableId
    audience_familiarity: NonEmptyText
    thesis: NonEmptyText
    narrative_arc: list[NonEmptyText] = Field(min_length=1)
    length: LengthIntent
    appendix_notes: list[NonEmptyText]
    deck_omissions: list[NonEmptyText]
    form_direction: FormDirection
    slides: list[PresentationSlideDecisionV1] = Field(min_length=1)
    omitted_content: list[ContentOmissionDecision]
    reference_only_inspiration: list[ReferenceOnlyInspiration]

    @field_validator("deck_omissions")
    @classmethod
    def validate_deck_omissions(cls, values: list[str]) -> list[str]:
        return _sorted_unique(values, label="deck_omissions")

    @field_validator("omitted_content")
    @classmethod
    def validate_omissions(
        cls, values: list[ContentOmissionDecision]
    ) -> list[ContentOmissionDecision]:
        keys = [f"{item.content_kind.value}:{item.content_id}" for item in values]
        _sorted_unique(keys, label="omitted_content")
        return values

    @field_validator("reference_only_inspiration")
    @classmethod
    def validate_references(
        cls, values: list[ReferenceOnlyInspiration]
    ) -> list[ReferenceOnlyInspiration]:
        return _sorted_unique_by_id(
            values,
            attribute="reference_id",
            label="reference_only_inspiration",
        )

    @model_validator(mode="after")
    def validate_slide_ids(self) -> DirectorLockDecisionsV1:
        slide_ids = [slide.slide_id for slide in self.slides]
        if len(slide_ids) != len(set(slide_ids)):
            raise ValueError("slides must have unique slide_id values")
        return self


class DirectorLockCandidateV1(StrictModel):
    """Complete lock packet material before the separate human confirmation state is added."""

    identity: LockPacketIdentity
    lock_packet_id: StableId
    plan_id: StableId
    task_slug: StableId
    output_format: Literal["pptx"]
    content_lock: ContentLockV1
    form_lock: FormLockV1
    composition_lock: CompositionLockV1


def _canonical_sha256(value: StrictModel) -> str:
    return hashlib.sha256(rfc8785.dumps(value.model_dump(mode="json"))).hexdigest()


def _content_lookup(
    view: BpsPresentationConstraintViewV02,
) -> dict[tuple[ContentKind, str], StrictModel]:
    result: dict[tuple[ContentKind, str], StrictModel] = {}
    for fact in view.content.facts:
        result[(ContentKind.FACT, fact.fact_id)] = fact
    for claim in view.content.claims:
        result[(ContentKind.CLAIM, claim.claim_id)] = claim
    for disclaimer in view.content.disclaimers:
        result[(ContentKind.DISCLAIMER, disclaimer.disclaimer_id)] = disclaimer
    return result


def _source_ids(value: StrictModel) -> list[str]:
    source_ids = getattr(value, "source_ids", None)
    if not isinstance(source_ids, list) or not all(isinstance(item, str) for item in source_ids):
        _fail("governed content is missing a valid source_ids list")
    return source_ids


def _bind_content(
    lookup: dict[tuple[ContentKind, str], StrictModel],
    kind: ContentKind,
    content_id: str,
) -> ContentBinding:
    value = lookup.get((kind, content_id))
    if value is None:
        _fail(
            "Director decision references content outside Constraint View: "
            f"{kind.value}:{content_id}"
        )
    return ContentBinding(
        content_kind=kind,
        content_id=content_id,
        value_sha256=_canonical_sha256(value),
        source_ids=_source_ids(value),
    )


def build_director_lock_candidate_v1(
    view: BpsPresentationConstraintViewV02,
    decisions: DirectorLockDecisionsV1,
) -> DirectorLockCandidateV1:
    """Bind Director decisions to exact BPS-governed values without adding confirmation state."""

    constraint_view = BpsPresentationConstraintViewV02.model_validate(view.model_dump(mode="json"))
    planning = DirectorLockDecisionsV1.model_validate(decisions.model_dump(mode="json"))
    content = _content_lookup(constraint_view)
    assets = {asset.asset_id: asset for asset in constraint_view.assets}
    allowed_layouts = set(constraint_view.treatment.allowed_layouts)
    allowed_fonts = set(constraint_view.form.allowed_fonts)
    allowed_tokens = set(constraint_view.form.brand_tokens)
    known_task_sources = {source.source_id for source in constraint_view.task_sources}
    known_sources = known_task_sources | {
        source.source_id for source in constraint_view.governed_sources
    }

    slides: list[PresentationPlanSlideV1] = []
    used_content: set[tuple[ContentKind, str]] = set()
    used_assets: set[str] = set()
    for decision in planning.slides:
        if decision.layout_family not in allowed_layouts:
            _fail(f"slide {decision.slide_id} selects unapproved layout: {decision.layout_family}")
        unknown_fonts = sorted(set(decision.font_families) - allowed_fonts)
        if unknown_fonts:
            _fail(f"slide {decision.slide_id} selects unapproved fonts: {', '.join(unknown_fonts)}")
        unknown_tokens = sorted(set(decision.brand_token_ids) - allowed_tokens)
        if unknown_tokens:
            _fail(
                f"slide {decision.slide_id} selects unknown brand tokens: "
                + ", ".join(unknown_tokens)
            )
        unknown_task_sources = sorted(set(decision.task_source_ids) - known_task_sources)
        if unknown_task_sources:
            _fail(
                f"slide {decision.slide_id} references unknown task sources: "
                + ", ".join(unknown_task_sources)
            )
        unknown_proof_sources = sorted(set(decision.proof_object.source_ids) - known_sources)
        if unknown_proof_sources:
            _fail(
                f"slide {decision.slide_id} proof references unknown sources: "
                + ", ".join(unknown_proof_sources)
            )

        primary_claim = None
        if decision.primary_claim_id is not None:
            primary_claim = _bind_content(content, ContentKind.CLAIM, decision.primary_claim_id)
            used_content.add((ContentKind.CLAIM, decision.primary_claim_id))

        supporting_content: list[ContentBinding] = []
        for reference in decision.supporting_content:
            supporting_content.append(
                _bind_content(content, reference.content_kind, reference.content_id)
            )
            used_content.add((reference.content_kind, reference.content_id))

        slide_assets = []
        for usage in decision.assets:
            constraint = assets.get(usage.asset_id)
            if constraint is None:
                _fail(
                    f"slide {decision.slide_id} references asset outside Constraint View: "
                    f"{usage.asset_id}"
                )
            if not set(usage.roles) <= set(constraint.roles):
                _fail(
                    f"slide {decision.slide_id} uses unapproved roles for asset {usage.asset_id}"
                )
            from .plan_v1 import AssetBinding

            slide_assets.append(
                AssetBinding(
                    asset_id=usage.asset_id,
                    sha256=constraint.sha256,
                    roles=usage.roles,
                )
            )
            used_assets.add(usage.asset_id)

        slides.append(
            PresentationPlanSlideV1(
                slide_id=decision.slide_id,
                slide_kind=decision.slide_kind,
                title=decision.title,
                purpose=decision.purpose,
                primary_claim=primary_claim,
                supporting_content=supporting_content,
                proof_object=decision.proof_object,
                layout_family=decision.layout_family,
                visual_treatment=decision.visual_treatment,
                assets=slide_assets,
                task_source_ids=decision.task_source_ids,
                font_families=decision.font_families,
                brand_token_ids=decision.brand_token_ids,
                reference_ids=decision.reference_ids,
                speaker_notes=decision.speaker_notes,
                required_capabilities=decision.required_capabilities,
            )
        )

    omitted_content: list[ContentOmission] = []
    omitted_keys: set[tuple[ContentKind, str]] = set()
    required_disclaimers = {
        (ContentKind.DISCLAIMER, item.disclaimer_id)
        for item in constraint_view.content.disclaimers
        if item.required
    }
    for omission in planning.omitted_content:
        key = (omission.content_kind, omission.content_id)
        if key in required_disclaimers:
            _fail(f"required disclaimer cannot be omitted: {omission.content_id}")
        binding = _bind_content(content, omission.content_kind, omission.content_id)
        omitted_content.append(
            ContentOmission(
                **binding.model_dump(mode="json"),
                omission_reason=omission.omission_reason,
            )
        )
        omitted_keys.add(key)

    conflicts = sorted(
        f"{kind.value}:{content_id}" for kind, content_id in used_content & omitted_keys
    )
    if conflicts:
        _fail("governed content cannot be both used and omitted: " + ", ".join(conflicts))
    missing = sorted(
        f"{kind.value}:{content_id}"
        for kind, content_id in set(content) - used_content - omitted_keys
    )
    if missing:
        _fail("Director decisions do not account for governed content: " + ", ".join(missing))

    required_assets = {
        asset.asset_id for asset in constraint_view.assets if asset.treatment_required
    }
    missing_assets = sorted(required_assets - used_assets)
    if missing_assets:
        _fail("Director decisions omit treatment-required assets: " + ", ".join(missing_assets))

    candidate = DirectorLockCandidateV1(
        identity=LockPacketIdentity(
            schema_id=LOCK_PACKET_SCHEMA_ID,
            schema_version=LOCK_PACKET_SCHEMA_VERSION,
        ),
        lock_packet_id=planning.lock_packet_id,
        plan_id=planning.plan_id,
        task_slug=constraint_view.authority.job_id,
        output_format="pptx",
        content_lock=ContentLockV1(
            content_language=constraint_view.task_context.output_locale,
            audience=AudienceIntent(
                audience=constraint_view.task_context.audience,
                familiarity=planning.audience_familiarity,
                desired_outcome=constraint_view.task_context.purpose,
            ),
            goal=constraint_view.task_context.purpose,
            thesis=planning.thesis,
            narrative_arc=planning.narrative_arc,
            length=planning.length,
            appendix_notes=planning.appendix_notes,
            deck_omissions=planning.deck_omissions,
            omitted_content=omitted_content,
        ),
        form_lock=FormLockV1(
            treatment=TreatmentBinding(
                treatment_id=constraint_view.treatment.treatment_id,
                version=constraint_view.treatment.version,
                definition_sha256=constraint_view.treatment.definition_sha256,
            ),
            direction=planning.form_direction,
        ),
        composition_lock=CompositionLockV1(
            slides=slides,
            reference_only_inspiration=planning.reference_only_inspiration,
        ),
    )

    # Reuse the frozen confirmed-packet validator for every lock semantic except the human state.
    ConfirmedDirectorLockPacketV1.model_validate(
        {**candidate.model_dump(mode="json"), "confirmation_state": "confirmed"}
    )
    return candidate


def _json_object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant: {value}")


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not os.path.lexists(path):
        _fail(f"{label} is required: {path}")
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} must be a regular file: {path}")
    try:
        loaded: Any = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_json_object_without_duplicates,
            parse_constant=_reject_nonstandard_json_constant,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise LockCandidateError(f"cannot read {label}: {exc}") from exc
    if not isinstance(loaded, dict):
        _fail(f"{label} must contain one JSON object")
    return loaded


def _load_model(path: Path, model: type[StrictModel], *, label: str) -> StrictModel:
    raw = _read_json_object(path, label=label)
    try:
        validated = model.model_validate(raw)
    except ValueError as exc:
        raise LockCandidateError(f"invalid {label}: {exc}") from exc

    raw_typed = json.dumps(
        raw,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    normalized_typed = json.dumps(
        validated.model_dump(mode="json", exclude_unset=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if raw_typed != normalized_typed:
        _fail(f"{label} must already use exact validated JSON types and values")
    return validated


def write_director_lock_candidate_once(path: Path, candidate: DirectorLockCandidateV1) -> None:
    validated = DirectorLockCandidateV1.model_validate(candidate.model_dump(mode="json"))
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise LockCandidateError(f"cannot resolve lock candidate output parent: {exc}") from exc
    if not parent.is_dir():
        _fail(f"lock candidate output parent must be a directory: {parent}")
    target = parent / path.name
    if os.path.lexists(target):
        _fail(f"lock candidate output is immutable and already exists: {target}")

    payload = (
        json.dumps(validated.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    try:
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise LockCandidateError(
            f"lock candidate output is immutable and already exists: {target}"
        ) from exc
    except OSError as exc:
        raise LockCandidateError(f"cannot publish lock candidate: {exc}") from exc

    try:
        persisted = DirectorLockCandidateV1.model_validate_json(target.read_bytes())
    except (OSError, ValueError) as exc:
        raise LockCandidateError(f"cannot revalidate persisted lock candidate: {exc}") from exc
    if persisted != validated:
        _fail("persisted lock candidate differs from produced candidate")


def build_director_lock_candidate_from_files(
    constraint_view_path: Path,
    decisions_path: Path,
    output_path: Path,
) -> DirectorLockCandidateV1:
    view = _load_model(
        constraint_view_path,
        BpsPresentationConstraintViewV02,
        label="BPS Presentation Constraint View",
    )
    decisions = _load_model(
        decisions_path,
        DirectorLockDecisionsV1,
        label="Director lock decisions",
    )
    assert isinstance(view, BpsPresentationConstraintViewV02)
    assert isinstance(decisions, DirectorLockDecisionsV1)
    candidate = build_director_lock_candidate_v1(view, decisions)
    write_director_lock_candidate_once(output_path, candidate)
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="presentation-director-build-lock-candidate",
        description=(
            "Build one complete unconfirmed Director lock candidate from a BPS Constraint View "
            "and Director-owned planning decisions."
        ),
    )
    parser.add_argument("--constraint-view", required=True, type=Path)
    parser.add_argument("--decisions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        candidate = build_director_lock_candidate_from_files(
            args.constraint_view,
            args.decisions,
            args.output,
        )
    except LockCandidateError as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        f"DIRECTOR_LOCK_CANDIDATE {candidate.lock_packet_id} -> {args.output.resolve()}",
        flush=True,
    )


if __name__ == "__main__":
    main()
