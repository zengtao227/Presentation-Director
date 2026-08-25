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
from .producer_v1 import ConfirmedDirectorLockPacketV1

JsonObject = dict[str, Any]
BrowserOpener = Callable[[str], bool]

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


def _candidate_page(snapshot: _CandidateSnapshot, token: str) -> str:
    candidate_text = json.dumps(snapshot.candidate, ensure_ascii=False, indent=2, sort_keys=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Confirm Director Lock Packet</title>
<style>
body {{
  font-family: system-ui, sans-serif;
  max-width: 980px;
  margin: 32px auto;
  padding: 0 20px;
}}
pre {{
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #f5f5f5;
  padding: 16px;
}}
.actions {{ display: flex; gap: 12px; margin-top: 20px; }}
button {{ padding: 10px 16px; }}
</style>
</head>
<body>
<h1>Confirm governed Director lock packet</h1>
<p>This confirms the exact complete Content, Form, and Composition Locks shown below.</p>
<p><strong>Candidate SHA-256:</strong> <code>{snapshot.canonical_sha256}</code></p>
<pre>{html.escape(candidate_text)}</pre>
<form method="post" action="/decision">
<input type="hidden" name="token" value="{html.escape(token, quote=True)}">
<div class="actions">
<button type="submit" name="decision" value="confirm">Confirm exact lock packet</button>
<button type="submit" name="decision" value="cancel">Cancel</button>
</div>
</form>
</body>
</html>
"""


def _message_page(title: str, message: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
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
                self._send_html(_message_page("Cancelled", "No confirmed lock packet was written."))
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
                    _message_page("Confirmation failed", str(exc)),
                    HTTPStatus.CONFLICT,
                )
                return
            state.packet = packet
            state.decision = "confirmed"
            self._send_html(
                _message_page(
                    "Confirmed",
                    "The exact governed Director lock packet was written.",
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
