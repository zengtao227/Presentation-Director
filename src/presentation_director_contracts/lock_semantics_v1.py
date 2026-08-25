"""Shared deck semantics for complete Director lock packets.

These checks mirror the frozen Plan V1 deck invariants that are decidable from a lock packet before
BPS governance is attached. They deliberately do not change the frozen wire models or invent a
synthetic governance binding.
"""

from __future__ import annotations

from .producer_v1 import ConfirmedDirectorLockPacketV1


def validate_confirmed_lock_packet_deck_semantics(
    packet: ConfirmedDirectorLockPacketV1,
) -> ConfirmedDirectorLockPacketV1:
    """Reject lock packets that the frozen Plan compiler must reject on deck semantics."""

    validated = ConfirmedDirectorLockPacketV1.model_validate(packet.model_dump(mode="json"))
    slides = validated.composition_lock.slides

    slide_ids = [slide.slide_id for slide in slides]
    if len(slide_ids) != len(set(slide_ids)):
        raise ValueError("slides must have unique slide_id values")

    slide_count = len(slides)
    length = validated.content_lock.length
    if length.target_slide_count is not None:
        if length.target_slide_count != slide_count:
            raise ValueError("target_slide_count must equal the persisted slide count")
    else:
        assert length.slide_count_range is not None
        if not (
            length.slide_count_range.minimum <= slide_count <= length.slide_count_range.maximum
        ):
            raise ValueError("persisted slide count must fall inside slide_count_range")

    used_content = {
        (item.content_kind, item.content_id)
        for slide in slides
        for item in (
            ([slide.primary_claim] if slide.primary_claim is not None else [])
            + slide.supporting_content
        )
    }
    omitted_content = {
        (item.content_kind, item.content_id) for item in validated.content_lock.omitted_content
    }
    conflicts = sorted(
        f"{kind.value}:{content_id}" for kind, content_id in used_content & omitted_content
    )
    if conflicts:
        raise ValueError(
            "governed content cannot be both used and omitted: " + ", ".join(conflicts)
        )

    declared_references = {
        reference.reference_id
        for reference in validated.composition_lock.reference_only_inspiration
    }
    used_references = {reference_id for slide in slides for reference_id in slide.reference_ids}
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

    return validated
