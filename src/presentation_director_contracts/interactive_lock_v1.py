"""Interactive confirmation runtime for one complete governed Director lock candidate.

This module is deliberately separate from the legacy Presentation Director brief UI. It does not
infer Content/Form/Composition Locks from ``brief-confirmed.json``. The caller must provide every
field required by the frozen ``ConfirmedDirectorLockPacketV1`` except ``confirmation_state``; only a
real browser confirmation may add that state and publish the confirmed packet.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import os
import secrets
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Literal, NoReturn
from urllib.parse import parse_qs, urlparse

import rfc8785

from .lock_semantics_v1 import validate_confirmed_lock_packet_deck_semantics
from .plan_v1 import PresentationPlanSlideV1
from .producer_v1 import ConfirmedDirectorLockPacketV1

JsonObject = dict[str, Any]
BrowserOpener = Callable[[str], bool]
UiLocale = Literal["en", "zh-CN"]

MAX_FORM_BODY_BYTES = 64 * 1024
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_HOST = "127.0.0.1"
_CANDIDATE_KEYS = frozenset(
    {
        "identity",
        "lock_packet_id",
        "plan_id",
        "task_slug",
        "output_format",
        "content_lock",
        "form_lock",
        "composition_lock",
    }
)


class LockConfirmationError(RuntimeError):
    """Base failure for the governed interactive lock confirmation boundary."""


class LockConfirmationCancelled(LockConfirmationError):
    """The local user explicitly cancelled the lock confirmation."""


class LockConfirmationTimeout(LockConfirmationError):
    """No valid local decision arrived within the configured timeout."""


@dataclass(frozen=True, slots=True)
class _CandidateSnapshot:
    candidate: JsonObject
    canonical_sha256: str


@dataclass(slots=True)
class _DecisionState:
    decision: Literal["pending", "confirmed", "cancelled", "error"] = "pending"
    packet: ConfirmedDirectorLockPacketV1 | None = None
    error: Exception | None = None


def _fail(message: str) -> NoReturn:
    raise LockConfirmationError(message)


def _json_object_without_duplicates(pairs: list[tuple[str, Any]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_json_constant(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant: {value}")


def _require_regular_json_object(path: Path, *, label: str) -> JsonObject:
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
        raise LockConfirmationError(f"cannot read {label}: {exc}") from exc
    if not isinstance(loaded, dict):
        _fail(f"{label} must contain one JSON object")
    return loaded


def _snapshot_candidate(path: Path) -> _CandidateSnapshot:
    raw = _require_regular_json_object(path, label="Director lock candidate")
    keys = frozenset(raw)
    missing = sorted(_CANDIDATE_KEYS - keys)
    unexpected = sorted(keys - _CANDIDATE_KEYS)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected fields: {', '.join(unexpected)}")
        _fail("Director lock candidate must be exact and unconfirmed (" + "; ".join(details) + ")")

    material: JsonObject = dict(raw)
    material["confirmation_state"] = "confirmed"
    try:
        packet = ConfirmedDirectorLockPacketV1.model_validate(material)
        validate_confirmed_lock_packet_deck_semantics(packet)
    except ValueError as exc:
        raise LockConfirmationError(f"invalid Director lock candidate: {exc}") from exc

    normalized = packet.model_dump(mode="json")
    normalized.pop("confirmation_state")
    raw_typed = json.dumps(
        raw,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    normalized_typed = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if normalized_typed != raw_typed:
        _fail("Director lock candidate must already be in exact validated canonical form")
    canonical_bytes = rfc8785.dumps(raw)
    return _CandidateSnapshot(
        candidate=normalized,
        canonical_sha256=hashlib.sha256(canonical_bytes).hexdigest(),
    )


def _confirmed_packet(snapshot: _CandidateSnapshot) -> ConfirmedDirectorLockPacketV1:
    material: JsonObject = dict(snapshot.candidate)
    material["confirmation_state"] = "confirmed"
    return ConfirmedDirectorLockPacketV1.model_validate(material)


def _preflight_output_target(path: Path) -> Path:
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise LockConfirmationError(f"cannot resolve confirmed lock output parent: {exc}") from exc
    if not parent.is_dir():
        _fail(f"confirmed lock output parent must be a directory: {parent}")
    target = parent / path.name
    if os.path.lexists(target):
        _fail(f"confirmed lock packet is immutable and already exists: {target}")
    return target


def _write_packet_once(path: Path, packet: ConfirmedDirectorLockPacketV1) -> None:
    payload = (
        json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise LockConfirmationError(
            f"confirmed lock packet is immutable and already exists: {path}"
        ) from exc
    except OSError as exc:
        raise LockConfirmationError(f"cannot publish confirmed lock packet: {exc}") from exc

    try:
        persisted = ConfirmedDirectorLockPacketV1.model_validate_json(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise LockConfirmationError(
            f"cannot revalidate persisted confirmed lock packet: {exc}"
        ) from exc
    if persisted != packet:
        _fail("persisted confirmed lock packet differs from the confirmed packet")


def _validated_loopback_host(host: str) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise LockConfirmationError(
            "interactive lock confirmation host must be an IPv4 loopback address"
        ) from exc
    if address.version != 4 or not address.is_loopback:
        _fail("interactive lock confirmation host must be IPv4 loopback-only")
    return host


def _ui_locale(packet: ConfirmedDirectorLockPacketV1) -> UiLocale:
    content_language = packet.content_lock.content_language
    if content_language.startswith("zh"):
        return "zh-CN"
    if content_language.startswith("en"):
        return "en"
    _fail(f"unsupported confirmation UI locale: {content_language}")


def _label(locale: UiLocale, chinese: str, english: str) -> str:
    return chinese if locale == "zh-CN" else english


def _joined(values: list[str], locale: UiLocale) -> str:
    if not values:
        return _label(locale, "无", "(none)")
    return "\n".join(f"{index}. {value}" for index, value in enumerate(values, start=1))


def _review_rows(items: tuple[tuple[str, str], ...]) -> str:
    return "".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd>" for label, value in items
    )


def _content_binding_text(kind: str, content_id: str, locale: UiLocale) -> str:
    kind_labels = {
        "fact": _label(locale, "事实", "Fact"),
        "claim": _label(locale, "主张", "Claim"),
        "disclaimer": _label(locale, "免责声明", "Disclaimer"),
    }
    return f"{kind_labels.get(kind, kind)} · {content_id}"


def _slide_review_html(
    slide: PresentationPlanSlideV1,
    *,
    index: int,
    locale: UiLocale,
) -> str:
    primary_claim = _label(locale, "无", "(none)")
    if slide.primary_claim is not None:
        primary_claim = _content_binding_text(
            slide.primary_claim.content_kind.value,
            slide.primary_claim.content_id,
            locale,
        )
    supporting = [
        _content_binding_text(item.content_kind.value, item.content_id, locale)
        for item in slide.supporting_content
    ]
    assets = [f"{item.asset_id} · {', '.join(item.roles)}" for item in slide.assets]
    rows = _review_rows(
        (
            (_label(locale, "本页目的", "Purpose"), slide.purpose),
            (_label(locale, "主要主张", "Primary claim"), primary_claim),
            (_label(locale, "支撑内容", "Supporting content"), _joined(supporting, locale)),
            (
                _label(locale, "证据表达", "Proof object"),
                f"{slide.proof_object.kind.value} · "
                f"{_joined(slide.proof_object.source_ids, locale)}",
            ),
            (_label(locale, "版式家族", "Layout family"), slide.layout_family),
            (_label(locale, "视觉处理", "Visual treatment"), slide.visual_treatment),
            (_label(locale, "批准素材", "Approved assets"), _joined(assets, locale)),
            (
                _label(locale, "任务来源", "Task sources"),
                _joined(slide.task_source_ids, locale),
            ),
            (_label(locale, "字体", "Fonts"), _joined(slide.font_families, locale)),
            (
                _label(locale, "品牌颜色角色", "Brand token roles"),
                _joined(slide.brand_token_ids, locale),
            ),
            (
                _label(locale, "演讲者备注", "Speaker notes"),
                _joined(slide.speaker_notes, locale),
            ),
            (
                _label(locale, "生成能力约束", "Required capabilities"),
                _joined([item.value for item in slide.required_capabilities], locale),
            ),
        )
    )
    slide_kind = _label(locale, "页面类型", "Slide kind") + f" · {slide.slide_kind.value}"
    return (
        '<article class="slide-card">'
        f'<p class="slide-index">{html.escape(slide_kind)} · {index:02d}</p>'
        f"<h3>{html.escape(slide.title)}</h3>"
        f"<dl>{rows}</dl>"
        "</article>"
    )


def _candidate_page(snapshot: _CandidateSnapshot, token: str) -> str:
    packet = _confirmed_packet(snapshot)
    locale = _ui_locale(packet)
    content = packet.content_lock
    form = packet.form_lock
    composition = packet.composition_lock
    length = content.length
    if length.target_slide_count is not None:
        length_text = _label(
            locale,
            f"{length.target_slide_count} 页",
            f"{length.target_slide_count} slides",
        )
    else:
        assert length.slide_count_range is not None
        length_text = _label(
            locale,
            f"{length.slide_count_range.minimum}-{length.slide_count_range.maximum} 页",
            f"{length.slide_count_range.minimum}-{length.slide_count_range.maximum} slides",
        )
    if length.target_duration_minutes is not None:
        length_text += _label(
            locale,
            f" · 目标 {length.target_duration_minutes} 分钟",
            f" · target {length.target_duration_minutes} minutes",
        )

    omitted_content = [
        f"{_content_binding_text(item.content_kind.value, item.content_id, locale)} · "
        f"{item.omission_reason}"
        for item in content.omitted_content
    ]
    content_rows = _review_rows(
        (
            (_label(locale, "内容语言", "Content language"), content.content_language),
            (_label(locale, "目标受众", "Audience"), content.audience.audience),
            (_label(locale, "受众熟悉度", "Audience familiarity"), content.audience.familiarity),
            (_label(locale, "希望达成的结果", "Desired outcome"), content.audience.desired_outcome),
            (_label(locale, "演示目标", "Goal"), content.goal),
            (_label(locale, "核心论点", "Thesis"), content.thesis),
            (_label(locale, "叙事顺序", "Narrative arc"), _joined(content.narrative_arc, locale)),
            (_label(locale, "篇幅", "Length"), length_text),
            (
                _label(locale, "实际幻灯片数", "Actual slide count"),
                str(len(composition.slides)),
            ),
            (_label(locale, "附录说明", "Appendix notes"), _joined(content.appendix_notes, locale)),
            (
                _label(locale, "明确不包含", "Deck omissions"),
                _joined(content.deck_omissions, locale),
            ),
            (
                _label(locale, "省略的受治理内容", "Omitted governed content"),
                _joined(omitted_content, locale),
            ),
        )
    )
    direction = form.direction
    form_rows = _review_rows(
        (
            (_label(locale, "版式方案", "Treatment"), form.treatment.treatment_id),
            (_label(locale, "版式版本", "Treatment version"), form.treatment.version),
            (
                _label(locale, "版式定义 SHA-256", "Treatment definition SHA-256"),
                form.treatment.definition_sha256,
            ),
            (_label(locale, "形式方向", "Direction"), direction.name),
            (_label(locale, "语气", "Tone"), direction.tone),
            (_label(locale, "背景策略", "Background strategy"), direction.background_strategy),
            (_label(locale, "色彩角色", "Palette intent"), direction.palette_role_intent),
            (_label(locale, "字体策略", "Typography intent"), direction.typography_intent),
            (
                _label(locale, "图表与图示", "Chart and diagram grammar"),
                direction.chart_diagram_grammar,
            ),
            (_label(locale, "图片策略", "Image strategy"), direction.image_strategy),
            (_label(locale, "动效策略", "Motion policy"), direction.motion_policy),
            (
                _label(locale, "禁止样式", "Forbidden patterns"),
                _joined(direction.forbidden_patterns, locale),
            ),
        )
    )
    slides = "".join(
        _slide_review_html(slide, index=index, locale=locale)
        for index, slide in enumerate(composition.slides, start=1)
    )
    references = [
        f"{item.label} · {item.influence.value} · {item.locator}"
        for item in composition.reference_only_inspiration
    ]
    audit_rows = _review_rows(
        (
            (_label(locale, "锁定包", "Lock packet"), packet.lock_packet_id),
            (_label(locale, "计划", "Plan"), packet.plan_id),
            (_label(locale, "任务", "Task"), packet.task_slug),
            (_label(locale, "输出格式", "Output format"), packet.output_format),
            (_label(locale, "候选 SHA-256", "Candidate SHA-256"), snapshot.canonical_sha256),
        )
    )
    candidate_text = json.dumps(snapshot.candidate, ensure_ascii=False, indent=2, sort_keys=True)
    hidden_token = html.escape(token, quote=True)
    title = _label(
        locale,
        "确认 Director 内容、形式与逐页组成",
        "Confirm Director content, form, and composition",
    )
    intro = _label(
        locale,
        "请先阅读内容、形式和逐页组成, 再确认这一份精确且完整的 Director lock candidate。",
        (
            "Review the content, form, and per-slide composition before confirming this "
            "exact, complete Director lock candidate."
        ),
    )
    edit_notice = _label(
        locale,
        (
            "此页面只用于确认, 不能直接修改内容。若要调整版式或逐页组成, "
            "请取消并修改未确认的 Director 输入。若要更改输出格式或已确认的任务内容, "
            "请取消并创建新的 job 与 Task draft; 不要先确认再修改。"
        ),
        (
            "This page is for confirmation only and cannot edit the governed content. "
            "To change layout or per-slide composition, cancel and revise the unconfirmed "
            "Director input. To change output format or confirmed task content, cancel and "
            "create a new job and Task draft. Do not confirm and then edit."
        ),
    )
    exact_payload_label = _label(
        locale,
        "精确的机器可读载荷 (技术审计)",
        "Exact machine-readable payload (technical audit)",
    )
    content_heading = _label(locale, "1. 内容锁定", "1. Content lock")
    form_heading = _label(locale, "2. 形式锁定", "2. Form lock")
    composition_heading = _label(
        locale,
        "3. 逐页组成锁定",
        "3. Per-slide composition lock",
    )
    references_heading = _label(locale, "仅作参考的灵感: ", "Reference-only inspiration: ")
    audit_heading = _label(locale, "绑定与审计信息", "Binding and audit evidence")
    exact_payload_note = _label(
        locale,
        "这里保留完全精确的机器可读表示, 仅用于技术审计。",
        "This exact machine-readable representation is retained for technical audit.",
    )
    confirm_label = _label(locale, "确认这份精确锁定", "Confirm exact lock")
    cancel_label = _label(locale, "取消并返回修改", "Cancel and return to edit")
    return f"""<!doctype html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
* {{ box-sizing: border-box; }}
:root {{
  --ink: #161616;
  --ink-muted: #626262;
  --paper: #f7f4ee;
  --surface: #ffffff;
  --rule: #d8d2c7;
  --signal: #274c77;
  --signal-soft: #eef4f8;
  --warning: #a63d00;
  --warning-soft: #fff6ec;
}}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 400 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Noto Sans CJK SC", sans-serif;
}}
main {{
  width: min(100%, 1120px);
  margin: 0 auto;
  padding: 32px 20px 48px;
}}
.eyebrow {{
  margin: 0 0 8px;
  color: var(--warning);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
}}
h1 {{
  margin: 0;
  font-size: clamp(30px, 7vw, 46px);
  line-height: 1.12;
  letter-spacing: -.02em;
}}
.lede {{
  max-width: 72ch;
  margin: 16px 0 24px;
  color: var(--ink-muted);
  font-size: 18px;
}}
.notice {{
  margin: 0 0 24px;
  padding: 14px 16px;
  border-left: 4px solid var(--warning);
  border-radius: 6px;
  background: var(--warning-soft);
}}
.review-grid {{ display: grid; grid-template-columns: 1fr; gap: 16px; }}
.review-section, .composition, .audit, details {{
  overflow: hidden;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: var(--surface);
}}
.review-section h2, .composition h2, .audit h2 {{
  margin: 0;
  padding: 20px 24px;
  border-bottom: 1px solid var(--rule);
  font-size: 20px;
}}
dl {{ display: grid; grid-template-columns: 1fr; margin: 0; }}
dt, dd {{ padding: 12px 24px; }}
dt {{
  padding-bottom: 0;
  color: var(--ink-muted);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: .03em;
}}
dd {{
  margin: 0;
  border-bottom: 1px solid var(--rule);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}}
dd:last-child {{ border-bottom: 0; }}
.composition {{ margin-top: 16px; }}
.slides {{ display: grid; grid-template-columns: 1fr; gap: 16px; padding: 16px; }}
.slide-card {{
  overflow: hidden;
  border: 1px solid var(--rule);
  border-radius: 6px;
  background: #fcfcfb;
}}
.slide-card h3 {{ margin: 0; padding: 0 20px 16px; font-size: 19px; }}
.slide-index {{
  margin: 0;
  padding: 16px 20px 6px;
  color: var(--signal);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .06em;
  text-transform: uppercase;
}}
.reference-note {{
  margin: 0;
  padding: 0 24px 20px;
  color: var(--ink-muted);
  white-space: pre-wrap;
}}
.audit {{ margin-top: 16px; border-top: 4px solid var(--signal); }}
.audit code {{
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 13px;
}}
details {{ margin-top: 16px; }}
summary {{
  min-height: 48px;
  padding: 13px 24px;
  color: var(--signal);
  font-weight: 700;
  cursor: pointer;
}}
summary:focus-visible, button:focus-visible {{
  outline: 2px solid var(--signal);
  outline-offset: 2px;
}}
details p {{ margin: 0; padding: 0 24px 16px; color: var(--ink-muted); }}
pre {{
  max-height: 480px;
  margin: 0;
  padding: 24px;
  overflow: auto;
  border-top: 1px solid var(--rule);
  background: #f8fafc;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}}
form {{ display: flex; flex-direction: column; gap: 12px; margin-top: 24px; }}
button {{
  min-height: 48px;
  padding: 12px 20px;
  border: 1px solid var(--ink);
  border-radius: 4px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.2;
  cursor: pointer;
  transition: background-color 180ms ease, border-color 180ms ease, color 180ms ease;
}}
.confirm {{ border-color: var(--signal); background: var(--signal); color: #fff; }}
.confirm:hover {{ border-color: var(--ink); background: var(--ink); }}
.cancel {{ background: transparent; color: var(--ink); }}
.cancel:hover {{ border-color: var(--warning); background: var(--warning-soft); }}
@media (min-width: 768px) {{
  main {{ padding: 48px 24px 64px; }}
  .review-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .slides {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  dl {{ grid-template-columns: 190px 1fr; }}
  dt, dd {{ padding: 14px 24px; border-bottom: 1px solid var(--rule); }}
  dt {{ padding-right: 0; }}
  form {{ flex-direction: row; }}
}}
@media (prefers-reduced-motion: reduce) {{ button {{ transition: none; }} }}
</style>
</head>
<body>
<main>
  <p class="eyebrow">{html.escape(_label(locale, "最终人工锁定", "Final human lock"))}</p>
  <h1>{html.escape(title)}</h1>
  <p class="lede">{html.escape(intro)}</p>
  <p class="notice">{html.escape(edit_notice)}</p>
  <div class="review-grid">
    <section class="review-section">
      <h2>{html.escape(content_heading)}</h2><dl>{content_rows}</dl>
    </section>
    <section class="review-section">
      <h2>{html.escape(form_heading)}</h2><dl>{form_rows}</dl>
    </section>
  </div>
  <section class="composition">
    <h2>{html.escape(composition_heading)}</h2>
    <div class="slides">{slides}</div>
    <p class="reference-note">
      <strong>{html.escape(references_heading)}</strong>
      {html.escape(_joined(references, locale))}
    </p>
  </section>
  <section class="audit">
    <h2>{html.escape(audit_heading)}</h2><dl>{audit_rows}</dl>
  </section>
  <details>
    <summary>{html.escape(exact_payload_label)}</summary>
    <p>{html.escape(exact_payload_note)}</p>
    <pre><code>{html.escape(candidate_text)}</code></pre>
  </details>
  <form method="post" action="/decision">
    <input type="hidden" name="token" value="{hidden_token}">
    <button class="confirm" type="submit" name="decision" value="confirm">
      {html.escape(confirm_label)}
    </button>
    <button class="cancel" type="submit" name="decision" value="cancel">
      {html.escape(cancel_label)}
    </button>
  </form>
</main>
</body>
</html>
"""


def _message_page(title: str, message: str, *, locale: UiLocale) -> str:
    return (
        f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title></head><body><h1>{html.escape(title)}</h1>"
        f"<p>{html.escape(message)}</p></body></html>"
    )


def confirm_lock_candidate_interactively(
    candidate_path: Path,
    output_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    host: str = DEFAULT_HOST,
    port: int = 0,
    browser_opener: BrowserOpener | None = webbrowser.open,
) -> ConfirmedDirectorLockPacketV1:
    """Confirm and publish one complete Director lock candidate through a local browser.

    The candidate is untrusted input and must already contain every frozen lock-packet field except
    ``confirmation_state``. This boundary never reads or converts the legacy confirmed brief. It
    re-reads the candidate after the human decision and refuses publication if its canonical content
    changed during the confirmation window.
    """

    if timeout_seconds <= 0:
        _fail("confirmation timeout must be positive")
    if not 0 <= port <= 65535:
        _fail("confirmation port must be between 0 and 65535")
    if not os.path.lexists(candidate_path):
        _fail(f"Director lock candidate is required: {candidate_path}")
    if candidate_path.is_symlink() or not candidate_path.is_file():
        _fail("Director lock candidate must be a regular file")
    try:
        candidate = candidate_path.resolve(strict=True)
    except OSError as exc:
        raise LockConfirmationError(f"cannot resolve Director lock candidate: {exc}") from exc

    target = _preflight_output_target(output_path)
    if candidate == target:
        _fail("Director lock candidate and confirmed output must be different files")

    snapshot = _snapshot_candidate(candidate)
    locale = _ui_locale(_confirmed_packet(snapshot))
    loopback_host = _validated_loopback_host(host)
    token = secrets.token_urlsafe(32)
    state = _DecisionState()
    bound_port: int | None = None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format_text: str, *args: Any) -> None:
            del format_text, args

        def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
                "base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(payload)

        def _trusted_origin(self) -> bool:
            origin = self.headers.get("Origin", "")
            if not origin:
                return True
            parsed = urlparse(origin)
            if (
                parsed.scheme != "http"
                or parsed.hostname != loopback_host
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.params
                or parsed.query
                or parsed.fragment
            ):
                return False
            try:
                origin_port = parsed.port
            except ValueError:
                return False
            return bound_port is not None and (origin_port or 80) == bound_port

        def do_GET(self) -> None:
            if urlparse(self.path).path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_html(_candidate_page(snapshot, token))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/decision":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not self._trusted_origin():
                self.send_error(HTTPStatus.FORBIDDEN, "Untrusted request origin")
                return
            content_length_headers = self.headers.get_all("Content-Length", [])
            if len(content_length_headers) != 1:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
                return
            content_length_text = content_length_headers[0]
            if (
                not content_length_text
                or not content_length_text.isascii()
                or not content_length_text.isdigit()
            ):
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length")
                return
            content_length = int(content_length_text)
            if content_length <= 0 or content_length > MAX_FORM_BODY_BYTES:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid form body size")
                return
            body_bytes = self.rfile.read(content_length)
            if len(body_bytes) != content_length:
                self.send_error(HTTPStatus.BAD_REQUEST, "Incomplete form body")
                return
            try:
                body = body_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                self.send_error(HTTPStatus.BAD_REQUEST, "Invalid UTF-8 form body")
                return
            form = parse_qs(body, keep_blank_values=True)
            submitted_token = form.get("token", [""])[0]
            decision = form.get("decision", [""])[0]
            if not secrets.compare_digest(submitted_token, token):
                self.send_error(HTTPStatus.FORBIDDEN, "Invalid confirmation token")
                return
            if decision == "cancel":
                state.decision = "cancelled"
                self._send_html(
                    _message_page(
                        _label(locale, "已取消", "Cancelled"),
                        _label(
                            locale,
                            (
                                "没有写入已确认的 Director lock packet。"
                                "现在可以返回未确认输入进行修改。"
                            ),
                            (
                                "No confirmed Director lock packet was written. "
                                "You can now revise the unconfirmed input."
                            ),
                        ),
                        locale=locale,
                    )
                )
                return
            if decision != "confirm":
                self.send_error(HTTPStatus.BAD_REQUEST, "Unknown decision")
                return
            try:
                current = _snapshot_candidate(candidate)
                if current.canonical_sha256 != snapshot.canonical_sha256:
                    raise LockConfirmationError(
                        "Director lock candidate changed during human confirmation"
                    )
                _preflight_output_target(target)
                packet = _confirmed_packet(current)
                _write_packet_once(target, packet)
            except Exception as exc:
                state.decision = "error"
                state.error = exc
                self._send_html(
                    _message_page(
                        _label(locale, "确认失败", "Confirmation failed"),
                        str(exc),
                        locale=locale,
                    ),
                    HTTPStatus.CONFLICT,
                )
                return
            state.packet = packet
            state.decision = "confirmed"
            self._send_html(
                _message_page(
                    _label(locale, "确认完成", "Confirmed"),
                    _label(
                        locale,
                        "这份精确的受治理 Director lock packet 已写入。",
                        "The exact governed Director lock packet was written.",
                    ),
                    locale=locale,
                )
            )

    server = HTTPServer((loopback_host, port), Handler)
    server.timeout = min(0.25, timeout_seconds)
    bound_port = server.server_port
    url = f"http://{loopback_host}:{bound_port}/"
    try:
        print(f"Confirm Director lock packet at {url}", flush=True)
        if browser_opener is not None:
            try:
                opened = browser_opener(url)
            except Exception as exc:
                raise LockConfirmationError(
                    f"unable to open the local confirmation page: {exc}"
                ) from exc
            if not opened:
                raise LockConfirmationError("unable to open the local confirmation page")
        deadline = time.monotonic() + timeout_seconds
        while state.decision == "pending" and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if state.decision == "pending":
        raise LockConfirmationTimeout("Director lock confirmation timed out")
    if state.decision == "cancelled":
        raise LockConfirmationCancelled("Director lock confirmation was cancelled")
    if state.decision == "error":
        assert state.error is not None
        if isinstance(state.error, LockConfirmationError):
            raise state.error
        raise LockConfirmationError(str(state.error)) from state.error
    if state.packet is None:
        _fail("confirmed Director lock packet is missing after confirmation")
    return state.packet


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="presentation-director-confirm-lock",
        description=(
            "Confirm one complete BPS-governed Director lock candidate via loopback browser."
        ),
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    try:
        packet = confirm_lock_candidate_interactively(
            args.candidate,
            args.output,
            timeout_seconds=args.timeout,
            host=args.host,
            port=args.port,
            browser_opener=None if args.no_browser else webbrowser.open,
        )
    except LockConfirmationError as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        f"CONFIRMED_DIRECTOR_LOCK_PACKET {packet.lock_packet_id} -> {Path(args.output).resolve()}",
        flush=True,
    )


if __name__ == "__main__":
    main()
