from __future__ import annotations

import copy
import json
import re
import socket
import threading
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import pytest

from presentation_director_contracts.interactive_lock_v1 import (
    LockConfirmationCancelled,
    LockConfirmationError,
    LockConfirmationTimeout,
    confirm_lock_candidate_interactively,
)
from presentation_director_contracts.producer_v1 import ConfirmedDirectorLockPacketV1

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_INPUT = ROOT / "fixtures" / "presentation-director-plan-production-input-v1.golden.json"
_TOKEN_RE = re.compile(r'name="token" value="([^"]+)"')


def _candidate_data() -> dict[str, object]:
    payload = json.loads(PRODUCTION_INPUT.read_text(encoding="utf-8"))
    packet = copy.deepcopy(payload["lock_packet"])
    assert isinstance(packet, dict)
    packet.pop("confirmation_state")
    return packet


def _write_candidate(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _browser_opener(
    *,
    decision: str,
    before_post: Callable[[], None] | None = None,
    first_origin: str | None = None,
    expected_first_status: int | None = None,
    captured_pages: list[str] | None = None,
) -> tuple[Callable[[str], bool], list[threading.Thread], list[BaseException]]:
    threads: list[threading.Thread] = []
    failures: list[BaseException] = []

    def opener(url: str) -> bool:
        def worker() -> None:
            try:
                with urlopen(url, timeout=5) as response:
                    page = response.read().decode("utf-8")
                if captured_pages is not None:
                    captured_pages.append(page)
                match = _TOKEN_RE.search(page)
                assert match is not None
                token = match.group(1)
                if before_post is not None:
                    before_post()

                body = urlencode({"token": token, "decision": decision}).encode("utf-8")
                decision_url = url.rstrip("/") + "/decision"
                if first_origin is not None:
                    request = Request(
                        decision_url,
                        data=body,
                        method="POST",
                        headers={"Origin": first_origin.format(port=urlparse(url).port)},
                    )
                    try:
                        urlopen(request, timeout=5)
                    except HTTPError as exc:
                        if expected_first_status is None or exc.code != expected_first_status:
                            raise
                    else:
                        raise AssertionError("untrusted-origin request unexpectedly succeeded")
                    body = urlencode({"token": token, "decision": "cancel"}).encode("utf-8")

                request = Request(decision_url, data=body, method="POST")
                try:
                    with urlopen(request, timeout=5) as response:
                        response.read()
                except HTTPError as exc:
                    if decision != "confirm" or exc.code != 409:
                        raise
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=worker, daemon=True)
        threads.append(thread)
        thread.start()
        return True

    return opener, threads, failures


def _join_workers(threads: list[threading.Thread], failures: list[BaseException]) -> None:
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    if failures:
        raise failures[0]


def test_real_loopback_confirmation_writes_exact_strict_packet(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    candidate_path = tmp_path / "director-lock-candidate.json"
    output_path = tmp_path / "director-lock-packet.confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    opener, threads, failures = _browser_opener(decision="confirm")

    packet = confirm_lock_candidate_interactively(
        candidate_path,
        output_path,
        timeout_seconds=5,
        browser_opener=opener,
    )
    _join_workers(threads, failures)

    expected_data = copy.deepcopy(candidate_data)
    expected_data["confirmation_state"] = "confirmed"
    expected = ConfirmedDirectorLockPacketV1.model_validate(expected_data)
    assert packet == expected
    assert ConfirmedDirectorLockPacketV1.model_validate_json(output_path.read_bytes()) == expected
    assert "confirmation_state" not in json.loads(candidate_path.read_text(encoding="utf-8"))


def test_missing_complete_lock_field_fails_before_browser(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    content_lock = candidate_data["content_lock"]
    assert isinstance(content_lock, dict)
    content_lock.pop("thesis")
    candidate_path = tmp_path / "candidate.json"
    _write_candidate(candidate_path, candidate_data)
    browser_called = False

    def opener(url: str) -> bool:
        nonlocal browser_called
        del url
        browser_called = True
        return True

    with pytest.raises(LockConfirmationError, match="invalid Director lock candidate"):
        confirm_lock_candidate_interactively(
            candidate_path,
            tmp_path / "confirmed.json",
            browser_opener=opener,
        )
    assert browser_called is False


def test_candidate_cannot_claim_confirmation_state_before_browser(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    candidate_data["confirmation_state"] = "confirmed"
    candidate_path = tmp_path / "candidate.json"
    _write_candidate(candidate_path, candidate_data)

    with pytest.raises(LockConfirmationError, match="unexpected fields: confirmation_state"):
        confirm_lock_candidate_interactively(candidate_path, tmp_path / "confirmed.json")


def test_candidate_change_during_human_window_fails_closed(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)

    def mutate_candidate() -> None:
        changed = copy.deepcopy(candidate_data)
        content_lock = changed["content_lock"]
        assert isinstance(content_lock, dict)
        content_lock["goal"] = "Changed after the confirmation page was shown."
        _write_candidate(candidate_path, changed)

    opener, threads, failures = _browser_opener(
        decision="confirm",
        before_post=mutate_candidate,
    )
    with pytest.raises(LockConfirmationError, match="changed during human confirmation"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_cancel_writes_no_confirmed_packet(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    opener, threads, failures = _browser_opener(decision="cancel")

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_chinese_confirmation_page_is_human_readable_and_exact_payload_is_collapsed(
    tmp_path: Path,
) -> None:
    candidate_data = _candidate_data()
    content_lock = candidate_data["content_lock"]
    assert isinstance(content_lock, dict)
    content_lock["content_language"] = "zh-CN"
    audience = content_lock["audience"]
    assert isinstance(audience, dict)
    audience["audience"] = "准备留学的学生家长"
    audience["familiarity"] = "首次了解服务"
    audience["desired_outcome"] = "理解服务范围并预约咨询"
    content_lock["goal"] = "介绍留学咨询服务的价值与边界。"
    content_lock["thesis"] = "清晰流程与透明边界帮助家庭作出审慎决定。"
    content_lock["narrative_arc"] = ["家庭关切", "服务流程", "风险边界"]

    form_lock = candidate_data["form_lock"]
    assert isinstance(form_lock, dict)
    direction = form_lock["direction"]
    assert isinstance(direction, dict)
    direction["name"] = "克制、可信的编辑风格"
    direction["tone"] = "清晰、温和、专业"

    composition_lock = candidate_data["composition_lock"]
    assert isinstance(composition_lock, dict)
    slides = composition_lock["slides"]
    assert isinstance(slides, list)
    first_slide = slides[0]
    assert isinstance(first_slide, dict)
    first_slide["title"] = "为家庭建立清晰的留学决策路径"
    first_slide["purpose"] = "说明本次介绍希望帮助家长解决什么问题。"
    first_slide["visual_treatment"] = "留白充分的编辑式封面"

    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    captured_pages: list[str] = []
    opener, threads, failures = _browser_opener(
        decision="cancel",
        captured_pages=captured_pages,
    )

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)

    assert not output_path.exists()
    assert len(captured_pages) == 1
    page = captured_pages[0]
    assert '<html lang="zh-CN">' in page
    assert "确认 Director 内容、形式与逐页组成" in page
    assert "1. 内容锁定" in page
    assert "2. 形式锁定" in page
    assert "3. 逐页组成锁定" in page
    assert "准备留学的学生家长" in page
    assert "介绍留学咨询服务的价值与边界。" in page
    assert "清晰流程与透明边界帮助家庭作出审慎决定。" in page
    assert "为家庭建立清晰的留学决策路径" in page
    assert "此页面只用于确认, 不能直接修改内容" in page
    assert "调整版式或逐页组成" in page
    assert "创建新的 job 与 Task draft" in page
    assert "取消并返回修改" in page
    assert "确认这份精确锁定" in page
    assert "精确的机器可读载荷 (技术审计)" in page
    assert "<details>" in page
    assert "<details open" not in page
    assert page.index("<details>") < page.index("<pre><code>")


def test_english_confirmation_page_remains_human_readable(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    content_lock = candidate_data["content_lock"]
    assert isinstance(content_lock, dict)
    content_lock["content_language"] = "en-US"
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    captured_pages: list[str] = []
    opener, threads, failures = _browser_opener(
        decision="cancel",
        captured_pages=captured_pages,
    )

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)

    assert not output_path.exists()
    page = captured_pages[0]
    assert '<html lang="en">' in page
    assert "1. Content lock" in page
    assert "2. Form lock" in page
    assert "3. Per-slide composition lock" in page
    assert "Confirm exact lock" in page
    assert "Cancel and return to edit" in page


def test_confirmation_page_escapes_untrusted_candidate_text(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    content_lock = candidate_data["content_lock"]
    assert isinstance(content_lock, dict)
    content_lock["goal"] = '</section><script>alert("candidate")</script>'
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    captured_pages: list[str] = []
    opener, threads, failures = _browser_opener(
        decision="cancel",
        captured_pages=captured_pages,
    )

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)

    assert not output_path.exists()
    page = captured_pages[0]
    assert '<script>alert("candidate")</script>' not in page
    assert "&lt;/section&gt;&lt;script&gt;alert(&quot;candidate&quot;)&lt;/script&gt;" in page


def test_concurrent_confirm_cancel_accepts_one_terminal_decision(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    accepted: list[str] = []
    coordinator_failures: list[BaseException] = []
    coordinator_threads: list[threading.Thread] = []

    def opener(url: str) -> bool:
        def coordinator() -> None:
            try:
                with urlopen(url, timeout=5) as response:
                    page = response.read().decode("utf-8")
                match = _TOKEN_RE.search(page)
                assert match is not None
                token = match.group(1)
                barrier = threading.Barrier(3)
                decision_threads: list[threading.Thread] = []

                def submit(decision: str) -> None:
                    body = urlencode({"token": token, "decision": decision}).encode("utf-8")
                    request = Request(
                        url.rstrip("/") + "/decision",
                        data=body,
                        method="POST",
                    )
                    barrier.wait(timeout=2)
                    try:
                        with urlopen(request, timeout=0.75) as response:
                            response.read()
                            if response.status == 200:
                                accepted.append(decision)
                    except Exception:
                        return

                for decision in ("confirm", "cancel"):
                    thread = threading.Thread(target=submit, args=(decision,), daemon=True)
                    decision_threads.append(thread)
                    thread.start()
                barrier.wait(timeout=2)
                for thread in decision_threads:
                    thread.join(timeout=2)
                    assert not thread.is_alive()
            except BaseException as exc:
                coordinator_failures.append(exc)

        thread = threading.Thread(target=coordinator, daemon=True)
        coordinator_threads.append(thread)
        thread.start()
        return True

    packet: ConfirmedDirectorLockPacketV1 | None = None
    cancelled = False
    try:
        packet = confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    except LockConfirmationCancelled:
        cancelled = True

    _join_workers(coordinator_threads, coordinator_failures)
    assert len(accepted) == 1
    if cancelled:
        assert accepted == ["cancel"]
        assert not output_path.exists()
    else:
        assert accepted == ["confirm"]
        assert packet is not None
        assert output_path.exists()
        assert ConfirmedDirectorLockPacketV1.model_validate_json(output_path.read_bytes()) == packet


def test_timeout_writes_no_confirmed_packet(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())

    with pytest.raises(LockConfirmationTimeout):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=0.05,
            browser_opener=None,
        )
    assert not output_path.exists()


@pytest.mark.parametrize("failure_mode", ["returns-false", "raises"])
def test_browser_open_failure_closes_server_and_writes_nothing(
    tmp_path: Path,
    failure_mode: str,
) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    opened_urls: list[str] = []

    def opener(url: str) -> bool:
        opened_urls.append(url)
        if failure_mode == "raises":
            raise RuntimeError("browser unavailable")
        return False

    with pytest.raises(LockConfirmationError, match="unable to open the local confirmation page"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )

    assert not output_path.exists()
    assert len(opened_urls) == 1
    parsed = urlparse(opened_urls[0])
    assert parsed.hostname == "127.0.0.1"
    assert parsed.port is not None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((parsed.hostname, parsed.port))


def test_preexisting_output_refuses_before_browser_and_preserves_bytes(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    output_path.write_bytes(b"existing-authority")
    browser_called = False

    def opener(url: str) -> bool:
        nonlocal browser_called
        del url
        browser_called = True
        return True

    with pytest.raises(LockConfirmationError, match="immutable and already exists"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            browser_opener=opener,
        )
    assert browser_called is False
    assert output_path.read_bytes() == b"existing-authority"


def test_symlink_candidate_is_rejected_before_browser(tmp_path: Path) -> None:
    real_candidate = tmp_path / "real-candidate.json"
    candidate_link = tmp_path / "candidate.json"
    _write_candidate(real_candidate, _candidate_data())
    candidate_link.symlink_to(real_candidate.name)

    with pytest.raises(LockConfirmationError, match="regular file"):
        confirm_lock_candidate_interactively(candidate_link, tmp_path / "confirmed.json")


def test_non_loopback_host_is_rejected(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    _write_candidate(candidate_path, _candidate_data())

    with pytest.raises(LockConfirmationError, match="loopback-only"):
        confirm_lock_candidate_interactively(
            candidate_path,
            tmp_path / "confirmed.json",
            host="0.0.0.0",
        )


def test_untrusted_origin_cannot_confirm(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    opener, threads, failures = _browser_opener(
        decision="confirm",
        first_origin="http://evil.example",
        expected_first_status=403,
    )

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_noncanonical_boolean_candidate_fails_before_browser(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    composition_lock = candidate_data["composition_lock"]
    assert isinstance(composition_lock, dict)
    references = composition_lock["reference_only_inspiration"]
    assert isinstance(references, list)
    reference = references[0]
    assert isinstance(reference, dict)
    reference["reference_only"] = 1
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    browser_called = False

    def opener(url: str) -> bool:
        nonlocal browser_called
        del url
        browser_called = True
        return True

    with pytest.raises(LockConfirmationError, match="exact validated canonical form"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            browser_opener=opener,
        )
    assert browser_called is False
    assert not output_path.exists()


def test_boolean_type_change_during_human_window_fails_closed(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)

    def mutate_candidate() -> None:
        changed = copy.deepcopy(candidate_data)
        composition_lock = changed["composition_lock"]
        assert isinstance(composition_lock, dict)
        references = composition_lock["reference_only_inspiration"]
        assert isinstance(references, list)
        reference = references[0]
        assert isinstance(reference, dict)
        reference["reference_only"] = 1
        _write_candidate(candidate_path, changed)

    opener, threads, failures = _browser_opener(
        decision="confirm",
        before_post=mutate_candidate,
    )
    with pytest.raises(LockConfirmationError, match="exact validated canonical form"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_duplicate_json_object_key_fails_before_browser(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    candidate_text = json.dumps(candidate_data, ensure_ascii=False, indent=2)
    needle = '  "task_slug": "bilingual-review",'
    assert candidate_text.count(needle) == 1
    candidate_path.write_text(
        candidate_text.replace(
            needle,
            needle + '\n  "task_slug": "duplicate-shadow",',
            1,
        ),
        encoding="utf-8",
    )
    browser_called = False

    def opener(url: str) -> bool:
        nonlocal browser_called
        del url
        browser_called = True
        return True

    with pytest.raises(LockConfirmationError, match="duplicate JSON object key: task_slug"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            browser_opener=opener,
        )
    assert browser_called is False
    assert not output_path.exists()


def test_other_loopback_origin_cannot_confirm(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    opener, threads, failures = _browser_opener(
        decision="confirm",
        first_origin="http://127.0.0.2:{port}",
        expected_first_status=403,
    )

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_malformed_content_length_cannot_confirm(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    threads: list[threading.Thread] = []
    failures: list[BaseException] = []

    def opener(url: str) -> bool:
        def worker() -> None:
            try:
                with urlopen(url, timeout=5) as response:
                    page = response.read().decode("utf-8")
                match = _TOKEN_RE.search(page)
                assert match is not None
                token = match.group(1)
                parsed = urlparse(url)
                assert parsed.hostname is not None
                assert parsed.port is not None
                body = urlencode({"token": token, "decision": "confirm"}).encode("utf-8")
                request_bytes = (
                    f"POST /decision HTTP/1.1\r\n"
                    f"Host: {parsed.hostname}:{parsed.port}\r\n"
                    f"Origin: http://{parsed.hostname}:{parsed.port}\r\n"
                    "Content-Type: application/x-www-form-urlencoded\r\n"
                    f"Content-Length: +{len(body)}\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii") + body
                with socket.create_connection((parsed.hostname, parsed.port), timeout=5) as client:
                    client.sendall(request_bytes)
                    response_bytes = client.recv(4096)
                assert b" 400 " in response_bytes

                cancel_body = urlencode({"token": token, "decision": "cancel"}).encode("utf-8")
                cancel_request = Request(
                    url.rstrip("/") + "/decision",
                    data=cancel_body,
                    method="POST",
                )
                with urlopen(cancel_request, timeout=5) as response:
                    response.read()
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=worker, daemon=True)
        threads.append(thread)
        thread.start()
        return True

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_truncated_content_length_cannot_confirm(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, _candidate_data())
    threads: list[threading.Thread] = []
    failures: list[BaseException] = []

    def opener(url: str) -> bool:
        def worker() -> None:
            try:
                with urlopen(url, timeout=5) as response:
                    page = response.read().decode("utf-8")
                match = _TOKEN_RE.search(page)
                assert match is not None
                token = match.group(1)
                parsed = urlparse(url)
                assert parsed.hostname is not None
                assert parsed.port is not None
                body = urlencode({"token": token, "decision": "confirm"}).encode("utf-8")
                request_bytes = (
                    f"POST /decision HTTP/1.1\r\n"
                    f"Host: {parsed.hostname}:{parsed.port}\r\n"
                    f"Origin: http://{parsed.hostname}:{parsed.port}\r\n"
                    "Content-Type: application/x-www-form-urlencoded\r\n"
                    f"Content-Length: {len(body) + 17}\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii") + body
                with socket.create_connection((parsed.hostname, parsed.port), timeout=5) as client:
                    client.sendall(request_bytes)
                    client.shutdown(socket.SHUT_WR)
                    response_bytes = client.recv(4096)
                assert b" 400 " in response_bytes

                cancel_body = urlencode({"token": token, "decision": "cancel"}).encode("utf-8")
                cancel_request = Request(
                    url.rstrip("/") + "/decision",
                    data=cancel_body,
                    method="POST",
                )
                with urlopen(cancel_request, timeout=5) as response:
                    response.read()
            except BaseException as exc:
                failures.append(exc)

        thread = threading.Thread(target=worker, daemon=True)
        threads.append(thread)
        thread.start()
        return True

    with pytest.raises(LockConfirmationCancelled):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            timeout_seconds=5,
            browser_opener=opener,
        )
    _join_workers(threads, failures)
    assert not output_path.exists()


def test_noncanonical_integer_float_candidate_fails_before_browser(tmp_path: Path) -> None:
    candidate_data = _candidate_data()
    content_lock = candidate_data["content_lock"]
    assert isinstance(content_lock, dict)
    length = content_lock["length"]
    assert isinstance(length, dict)
    length["target_duration_minutes"] = 12.0
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "confirmed.json"
    _write_candidate(candidate_path, candidate_data)
    browser_called = False

    def opener(url: str) -> bool:
        nonlocal browser_called
        del url
        browser_called = True
        return True

    with pytest.raises(LockConfirmationError, match="exact validated canonical form"):
        confirm_lock_candidate_interactively(
            candidate_path,
            output_path,
            browser_opener=opener,
        )
    assert browser_called is False
    assert not output_path.exists()
