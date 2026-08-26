"""Official-source collection with local checkpoints and no project services."""

from __future__ import annotations

import gzip
import json
import os
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from .ksoyu import (
    KSOYU_ADAPTER_ID,
    KSOYU_PARSER_VERSION,
    build_listing_url,
    classify_listing,
    decode_response,
    parse_listing,
    parse_source_page,
)
from .store import RunStore


@dataclass(frozen=True)
class HttpResponse:
    status: int
    final_url: str
    headers: Mapping[str, str]
    body: bytes


class Transport(Protocol):
    def get(self, url: str) -> HttpResponse: ...


class HttpTransport:
    """Polite stdlib HTTP transport; it never bypasses protection pages."""

    def __init__(self, *, timeout: float = 30.0, min_host_interval: float = 1.5) -> None:
        self.timeout = timeout
        self.min_host_interval = min_host_interval
        self._last_request: dict[str, float] = {}

    def _throttle(self, host: str) -> None:
        previous = self._last_request.get(host)
        if previous is not None:
            remaining = self.min_host_interval - (time.monotonic() - previous)
            if remaining > 0:
                time.sleep(remaining)

    def get(self, url: str) -> HttpResponse:
        host = urlparse(url).netloc.casefold()
        self._throttle(host)
        request = Request(
            url,
            headers={
                "User-Agent": "KSRF-Judicial-Meaning/1.0 (local legal research; respectful rate limit)",
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.5",
                "Accept-Encoding": "gzip",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
                status = int(response.status)
                final_url = response.geturl()
        except HTTPError as exc:
            body = exc.read()
            headers = {str(key).lower(): str(value) for key, value in exc.headers.items()}
            status = int(exc.code)
            final_url = exc.geturl()
        except (URLError, TimeoutError, socket.timeout) as exc:
            reason = getattr(exc, "reason", exc)
            certificate_error = isinstance(reason, ssl.SSLCertVerificationError) or (
                "CERTIFICATE_VERIFY_FAILED" in str(exc)
            )
            if certificate_error and shutil.which("curl"):
                return CurlTransport(timeout=self.timeout).get(url)
            raise TimeoutError(str(exc)) from exc
        finally:
            self._last_request[host] = time.monotonic()
        if headers.get("content-encoding", "").casefold() == "gzip":
            try:
                body = gzip.decompress(body)
            except OSError:
                pass
        return HttpResponse(status=status, final_url=final_url, headers=headers, body=body)


class CurlTransport:
    """Optional system-trust fallback; TLS verification remains enabled."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        executable = shutil.which("curl")
        if not executable:
            raise ValueError("Optional curl transport не найден.")
        self.executable = executable
        self.timeout = timeout
        try:
            version = subprocess.run(
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout.splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError):
            version = "curl version_unavailable"
        self.version = version[:200]

    def get(self, url: str) -> HttpResponse:
        profile = (
            "curl --location --silent --show-error --compressed --retry 0 "
            "--max-redirs 5 --proto =https,http --max-time TIMEOUT"
        )
        with tempfile.TemporaryDirectory(prefix="judicial-meaning-curl-") as temporary:
            root = Path(temporary)
            header_path = root / "headers.txt"
            body_path = root / "body.bin"
            command = [
                self.executable,
                "--location",
                "--silent",
                "--show-error",
                "--compressed",
                "--retry",
                "0",
                "--max-redirs",
                "5",
                "--proto",
                "=https,http",
                "--max-time",
                str(self.timeout),
                "--user-agent",
                "KSRF-Judicial-Meaning/1.0 (local legal research; respectful rate limit)",
                "--dump-header",
                str(header_path),
                "--output",
                str(body_path),
                "--write-out",
                "%{http_code}\n%{url_effective}",
                url,
            ]
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 5,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise TimeoutError(f"curl transport failed: {exc.__class__.__name__}") from exc
            if result.returncode != 0:
                raise TimeoutError(f"curl transport exit {result.returncode}: {result.stderr[:300]}")
            output_lines = result.stdout.splitlines()
            if len(output_lines) < 2 or not output_lines[-2].isdigit():
                raise TimeoutError("curl transport did not return HTTP status metadata")
            status = int(output_lines[-2])
            final_url = output_lines[-1]
            body = body_path.read_bytes() if body_path.exists() else b""
            raw_headers = header_path.read_text(encoding="latin-1", errors="replace") if header_path.exists() else ""
        blocks = [block for block in raw_headers.replace("\r\n", "\n").split("\n\n") if block.startswith("HTTP/")]
        headers: dict[str, str] = {}
        if blocks:
            for line in blocks[-1].splitlines()[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
        headers["x-judicial-meaning-transport"] = "curl"
        headers["x-judicial-meaning-helper-version"] = self.version
        headers["x-judicial-meaning-command-profile"] = profile
        return HttpResponse(status=status, final_url=final_url, headers=headers, body=body)


class FixtureTransport:
    """Deterministic packaged-fixture transport for clean-install smoke tests."""

    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir

    def get(self, url: str) -> HttpResponse:
        query = parse_qs(urlparse(url).query)
        operation = (query.get("name_op") or [""])[0]
        if operation == "case":
            name = "card.html"
        elif operation == "doc":
            name = "doc.html"
        else:
            name = "listing_nonempty.html"
        path = self.fixture_dir / name
        if not path.exists():
            raise TimeoutError(f"fixture not found: {path}")
        return HttpResponse(200, url, {"content-type": "text/html; charset=utf-8"}, path.read_bytes())


class RunLock:
    def __init__(self, workspace: Path) -> None:
        self.path = workspace / ".collection.lock"
        self.owned = False

    def __enter__(self) -> "RunLock":
        payload = json.dumps({"pid": os.getpid(), "created_at": time.time()}, sort_keys=True).encode("ascii")
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            owner = self.path.read_text(encoding="utf-8", errors="replace")[:500]
            raise ValueError(f"Workspace уже собирается другим процессом. Lock: {owner}") from exc
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        self.owned = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.owned:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


def load_source_registry(path: Path | None = None) -> dict[str, Any]:
    registry_path = path or (Path(__file__).resolve().parents[2] / "source_registry" / "sources.v1.json")
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Не удалось прочитать bundled source registry: {registry_path}") from exc
    if registry.get("schema_version") != "1.0" or not isinstance(registry.get("sources"), list):
        raise ValueError("Bundled source registry имеет несовместимую структуру.")
    identifiers = [source.get("id") for source in registry["sources"] if isinstance(source, dict)]
    if len(identifiers) != len(set(identifiers)) or any(not identifier for identifier in identifiers):
        raise ValueError("Source registry содержит пустые или повторяющиеся id.")
    return registry


def _court_hosts(source: dict[str, Any]) -> dict[str, str]:
    return {
        str(court["code"]): str(court["host"])
        for court in source.get("courts", [])
        if isinstance(court, dict) and court.get("code") and court.get("host")
    }


def _source_key(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    operation = (query.get("name_op") or [""])[0]
    if operation == "case":
        identity = (query.get("case_uid") or [""])[0]
        if not identity:
            identity = ":".join(
                (query.get(name) or [""])[0] for name in ("case_id", "delo_id", "new")
            )
    elif operation == "doc":
        identity = ":".join(
            (query.get(name) or [""])[0] for name in ("number", "delo_id", "text_number")
        )
    else:
        identity = parsed.query
    return f"{parsed.netloc.casefold()}:{operation}:{identity}"


def _case_uid(url: str) -> str | None:
    return (parse_qs(urlparse(url).query).get("case_uid") or [None])[0]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _capture_source(
    store: RunStore,
    run_id: str,
    court_code: str,
    url: str,
    kind: str,
    response: HttpResponse,
    text: str,
    status: str,
    chain_key: str | None = None,
    classification_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "adapter_id": KSOYU_ADAPTER_ID,
        "adapter_version": KSOYU_ADAPTER_ID,
        "parser_version": KSOYU_PARSER_VERSION,
        "extraction_status": status,
        "requested_url": url,
        "transport": response.headers.get("x-judicial-meaning-transport", "urllib"),
        "transport_helper_version": response.headers.get(
            "x-judicial-meaning-helper-version"
        ),
        "transport_command_profile": response.headers.get(
            "x-judicial-meaning-command-profile"
        ),
    }
    metadata.update(classification_evidence or {})
    return store.add_source(
        run_id,
        court_code=court_code,
        kind=kind,
        canonical_url=response.final_url or url,
        raw=response.body,
        text=text,
        case_uid=_case_uid(url),
        chain_key=chain_key,
        http_status=response.status,
        content_type=response.headers.get("content-type"),
        metadata=metadata,
    )


def _discover_sources(
    store: RunStore,
    *,
    run_id: str,
    court_code: str,
    urls: list[tuple[str, str, str | None]],
    discovered_from_task_id: int | None,
) -> None:
    for url, kind, chain_key in urls:
        store.discover_source_task(
            run_id,
            court_code=court_code,
            kind=kind,
            canonical_url=url,
            source_key=_source_key(url),
            chain_key=chain_key,
            discovered_from_task_id=discovered_from_task_id,
        )


def _process_source_tasks(
    *,
    store: RunStore,
    run_id: str,
    transport: Transport,
    max_attempts: int,
    retry_now: bool,
    max_tasks: int | None,
) -> int:
    processed = 0
    while max_tasks is None or processed < max_tasks:
        source_task = store.claim_next_source(
            run_id, now="9999-01-01T00:00:00Z" if retry_now else None
        )
        if source_task is None:
            break
        source_task_id = int(source_task["source_task_id"])
        url = str(source_task["canonical_url"])
        kind = str(source_task["kind"])
        try:
            response = transport.get(url)
        except TimeoutError as exc:
            if int(source_task["attempts"]) >= max_attempts:
                store.finish_source_task(
                    source_task_id, "terminal_error", None, error_message=str(exc)
                )
            else:
                store.fail_source_task(source_task_id, "retryable_error", str(exc))
            processed += 1
            continue

        decoded = decode_response(response.body, response.headers)
        parsed = parse_source_page(decoded.text, response.final_url or url, kind)
        if response.status in {401, 403, 407, 429, 451} or parsed.protective:
            status = "blocked"
            text = ""
        elif response.status == 404:
            status = "missing"
            text = ""
        elif response.status == 408 or response.status >= 500:
            status = "retryable_error"
            text = ""
        elif response.status < 200 or response.status >= 300:
            status = "terminal_error"
            text = ""
        elif kind == "doc" and parsed.status == "full_text":
            status = "full_text"
            text = parsed.text
        elif kind == "doc":
            status = "official_page_no_text"
            text = parsed.text
        elif parsed.doc_urls:
            status = "card_indexed"
            text = parsed.text
        else:
            status = "card_only"
            text = parsed.text

        _capture_source(
            store,
            run_id,
            str(source_task["court_code"]),
            url,
            kind,
            response,
            text,
            status,
            chain_key=source_task.get("chain_key"),
        )
        if kind == "card" and parsed.doc_urls and status == "card_indexed":
            _discover_sources(
                store,
                run_id=run_id,
                court_code=str(source_task["court_code"]),
                urls=[(doc_url, "doc", source_task.get("chain_key")) for doc_url in parsed.doc_urls],
                discovered_from_task_id=source_task.get("discovered_from_task_id"),
            )
        if status in {"retryable_error", "blocked"}:
            if status != "blocked" and int(source_task["attempts"]) >= max_attempts:
                store.finish_source_task(
                    source_task_id,
                    "terminal_error",
                    response.status,
                    error_message=f"HTTP {response.status}",
                )
            else:
                store.fail_source_task(source_task_id, status, f"HTTP {response.status}")
        else:
            store.finish_source_task(
                source_task_id,
                status,
                response.status,
                error_message=None if status in {"full_text", "card_indexed"} else status,
            )
        processed += 1
    return processed


def _add_pagination_tasks(
    store: RunStore,
    *,
    run_id: str,
    parent: dict[str, Any],
    urls: list[str],
) -> int:
    inserted = 0
    created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with store.conn:
        for url in urls:
            segment_key = f"{parent['court_code']}:{parent['listing_date']}:page:{_source_key(url)}"
            cursor = store.conn.execute(
                """
                INSERT OR IGNORE INTO listing_tasks(
                    run_id, court_code, listing_date, segment_key, page_url, parent_task_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    parent["court_code"],
                    parent["listing_date"],
                    segment_key,
                    url,
                    parent["task_id"],
                    created_at,
                ),
            )
            if cursor.rowcount and cursor.lastrowid is not None:
                inserted += 1
                store._event(
                    run_id=run_id,
                    task_id=int(cursor.lastrowid),
                    event_type="listing",
                    reason_code="pagination_discovered",
                    payload={"parent_task_id": parent["task_id"], "url": url},
                )
    return inserted


def run_collection(
    workspace: Path,
    *,
    plan: dict[str, Any] | None = None,
    transport: Transport | None = None,
    resume: bool = True,
    max_tasks: int | None = None,
    max_attempts: int = 3,
    max_source_tasks: int | None = None,
    fixture_dir: Path | None = None,
    retry_now: bool = False,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    """Collect a frozen KSOYU stratum and return an honest coverage summary."""

    workspace = Path(workspace)
    if plan is None:
        plan_files = sorted((workspace / "plans").glob("plan-v*.json"))
        if not plan_files:
            raise ValueError("Нет замороженного плана для collection.")
        plan = json.loads(plan_files[-1].read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise ValueError("Frozen plan должен быть JSON-объектом.")
    if plan.get("frozen") is not True or not plan.get("plan_sha256"):
        raise ValueError("Collection разрешён только по frozen plan с plan_sha256.")
    population = plan.get("population") or {}
    registry = load_source_registry(registry_path)
    registry_sources = {source["id"]: source for source in registry["sources"]}
    requested_regimes = list(population.get("regimes", []))
    unsupported = [
        regime
        for regime in requested_regimes
        if regime not in registry_sources or not registry_sources[regime].get("adapter")
    ]
    regime_gaps = []
    for regime in unsupported:
        known = registry_sources.get(regime)
        regime_gaps.append(
            {
                "regime": regime,
                "status": "not_configured" if known else "registry_entry_missing",
                "reason": "Нет проверенного официального closed-enumerator; отсутствие адаптера не означает отсутствие практики.",
            }
        )
    ksoyu_source = registry_sources.get("ksoyu_post_2019", {})
    adapter_ids = {
        regime: registry_sources.get(regime, {}).get("adapter")
        for regime in requested_regimes
    }
    collector_manifest = {
        "registry_version": registry.get("registry_version"),
        "regimes": {
            regime: {
                "adapter_id": registry_sources.get(regime, {}).get("adapter"),
                "parser_version": registry_sources.get(regime, {}).get("parser_version"),
                "enumeration": registry_sources.get(regime, {}).get("enumeration"),
            }
            for regime in requested_regimes
        },
    }
    ksoyu_requested = (
        "ksoyu_post_2019" in requested_regimes
        and ksoyu_source.get("adapter") == KSOYU_ADAPTER_ID
        and ksoyu_source.get("parser_version") == KSOYU_PARSER_VERSION
    )
    adapter_start = str(ksoyu_source.get("applicable_from") or "2019-10-01")
    if ksoyu_requested and population.get("date_from", adapter_start) < adapter_start and not unsupported:
        regime_gaps.append(
            {
                "regime": "ksoyu_post_2019",
                "status": "not_applicable_before_2019_10_01",
                "date_from": population.get("date_from"),
                "date_to": "2019-09-30",
                "reason": "КСОЮ ещё не действовали; нужен отдельный дореформенный адаптер.",
            }
        )
    hosts = _court_hosts(ksoyu_source)
    unknown_courts = [
        court for court in population.get("courts", []) if ksoyu_requested and court not in hosts
    ]
    if unknown_courts:
        raise ValueError("Неизвестные суды в ksoyu_post_2019: " + ", ".join(unknown_courts))
    transport = transport or (FixtureTransport(fixture_dir) if fixture_dir else HttpTransport())

    run_metadata_path = workspace / "run.json"
    stored_run_metadata: dict[str, Any] | None = None
    if resume and run_metadata_path.exists():
        loaded_run_metadata = json.loads(run_metadata_path.read_text(encoding="utf-8"))
        if not isinstance(loaded_run_metadata, dict):
            raise ValueError("Нельзя resume: run.json должен быть JSON-объектом.")
        stored_run_metadata = loaded_run_metadata
        if stored_run_metadata.get("adapter_ids") != adapter_ids:
            raise ValueError(
                "Нельзя resume: adapter IDs не совпадают с сохранённым run; "
                "создайте новый run или выполните явную переклассификацию raw snapshots."
            )
        if stored_run_metadata.get("collector_manifest") != collector_manifest:
            raise ValueError(
                "Нельзя resume: collector manifest не совпадает с сохранённым run; "
                "создайте новый run или выполните явную переклассификацию raw snapshots."
            )

    with RunLock(workspace), RunStore(workspace) as store:
        existing_run = store.latest_run_id()
        if resume and existing_run:
            if stored_run_metadata is None:
                raise ValueError(
                    "Нельзя resume: в run.json отсутствует provenance adapter IDs."
                )
            run_id = existing_run
            if stored_run_metadata.get("run_id") != run_id:
                raise ValueError("Нельзя resume: run_id в run.json не совпадает с corpus.sqlite3.")
            if stored_run_metadata.get("plan_sha256") != plan["plan_sha256"]:
                raise ValueError("Нельзя resume: plan_sha256 в run.json не совпадает с frozen plan.")
            row = store.conn.execute("SELECT plan_sha256 FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None or row["plan_sha256"] != plan["plan_sha256"]:
                raise ValueError("Нельзя resume: хеш frozen plan не совпадает с run.")
        else:
            run_id = store.create_run(plan)
            supported_start = max(str(population["date_from"]), adapter_start)
            if ksoyu_requested and supported_start <= str(population["date_to"]):
                store.seed_calendar(
                    run_id,
                    population["courts"],
                    supported_start,
                    population["date_to"],
                )
        store.recover_stale_claims("9999-01-01T00:00:00Z")
        store.recover_stale_source_claims("9999-01-01T00:00:00Z")

        _write_json(
            run_metadata_path,
            {
                "schema_version": "1.0",
                "run_id": run_id,
                "plan_sha256": plan["plan_sha256"],
                "adapter_ids": adapter_ids,
                "collector_manifest": collector_manifest,
            },
        )
        applicant_chain_path = workspace / "applicant-chain.json"
        if applicant_chain_path.exists():
            applicant_chain = json.loads(applicant_chain_path.read_text(encoding="utf-8"))
            if not isinstance(applicant_chain, dict):
                raise ValueError("applicant-chain.json должен быть JSON-объектом.")
            applicant_chain["run_id"] = run_id
            applicant_chain["plan_sha256"] = plan["plan_sha256"]
            _write_json(applicant_chain_path, applicant_chain)

        processed = 0
        while max_tasks is None or processed < max_tasks:
            task = store.claim_next_listing(
                run_id, now="9999-01-01T00:00:00Z" if retry_now else None
            )
            if task is None:
                break
            url = task.get("page_url") or build_listing_url(hosts[task["court_code"]], task["listing_date"])
            try:
                response = transport.get(url)
            except TimeoutError as exc:
                store.fail_listing(task["task_id"], "retryable_error", str(exc))
                processed += 1
                continue
            decoded = decode_response(response.body, response.headers)
            parsed = parse_listing(decoded.text, response.final_url or url, task["listing_date"])
            status = classify_listing(response.status, parsed)
            if status == "ambiguous_empty" and parsed.pagination_urls:
                status = "success_nonempty"
            _capture_source(
                store,
                run_id,
                task["court_code"],
                url,
                "listing",
                response,
                parsed.page_text,
                status,
                classification_evidence={
                    "listing_date": task["listing_date"],
                    "listing_shell_seen": parsed.listing_shell_seen,
                    "listing_table_seen": parsed.listing_table_seen,
                    "control_date_confirmed": parsed.control_date_confirmed,
                    "content_date_confirmed": parsed.content_date_confirmed,
                    "date_confirmed": parsed.date_confirmed,
                    "empty_evidence_code": parsed.empty_evidence_code,
                    "case_row_count": parsed.case_row_count,
                    "navigation_state": parsed.navigation_state,
                },
            )
            if status in {"success_empty", "success_nonempty"}:
                _add_pagination_tasks(store, run_id=run_id, parent=task, urls=parsed.pagination_urls)
                discovered_by_key: dict[str, tuple[str, str, str | None]] = {}
                for row in parsed.rows:
                    row_chain_key = None
                    if row.case_urls:
                        row_chain_key = _case_uid(row.case_urls[0]) or _source_key(row.case_urls[0])
                    for item in row.case_urls:
                        chain_key = _case_uid(item) or row_chain_key
                        discovered_by_key[_source_key(item)] = (item, "card", chain_key)
                    for item in row.doc_urls:
                        discovered_by_key[_source_key(item)] = (item, "doc", row_chain_key)
                for item in parsed.case_urls:
                    discovered_by_key.setdefault(
                        _source_key(item), (item, "card", _case_uid(item) or _source_key(item))
                    )
                for item in parsed.doc_urls:
                    discovered_by_key.setdefault(_source_key(item), (item, "doc", None))
                discovered = list(discovered_by_key.values())
                _discover_sources(
                    store=store,
                    run_id=run_id,
                    court_code=task["court_code"],
                    urls=discovered,
                    discovered_from_task_id=task["task_id"],
                )
                store.finish_listing(
                    task["task_id"],
                    status,
                    response.status,
                    row_count=parsed.case_row_count,
                    evidence={
                        "adapter_id": KSOYU_ADAPTER_ID,
                        "listing_shell_seen": parsed.listing_shell_seen,
                        "listing_table_seen": parsed.listing_table_seen,
                        "control_date_confirmed": parsed.control_date_confirmed,
                        "content_date_confirmed": parsed.content_date_confirmed,
                        "date_confirmed": parsed.date_confirmed,
                        "empty_evidence_code": parsed.empty_evidence_code,
                        "case_row_count": parsed.case_row_count,
                    },
                )
            else:
                reason = f"HTTP {response.status}; {parsed.navigation_state}"
                if status != "blocked" and int(task["attempts"]) >= max_attempts:
                    store.terminate_listing(task["task_id"], "terminal_error", reason)
                else:
                    store.fail_listing(task["task_id"], status, reason)
            processed += 1

        processed_sources = _process_source_tasks(
            store=store,
            run_id=run_id,
            transport=transport,
            max_attempts=max_attempts,
            retry_now=retry_now,
            max_tasks=max_source_tasks,
        )
        coverage = store.coverage_report(run_id)
        source_acquisition = store.source_task_report(run_id)
        coverage["supported_segments_closed"] = coverage["closed_official_population_observed"]
        coverage["regime_gaps"] = regime_gaps
        if regime_gaps:
            coverage["closed_official_population_observed"] = False
            coverage["population_status"] = "observed_corpus_only"
        coverage["collection_complete"] = bool(
            coverage["closed_official_population_observed"]
            and source_acquisition["unresolved"] == 0
        )
        coverage["denominator_scope"] = (
            "official_daily_scheduled_listing_route_not_all_decided_or_published_acts"
        )
        coverage["denominator_limit"] = (
            "Закрытие H_date подтверждает только наблюдаемую выдачу назначенных дел; "
            "оно не доказывает публикацию каждого рассмотренного или изготовленного акта."
        )
        independence = store.independence_counts(run_id)
        for table in ("listing_tasks", "source_tasks", "sources", "snapshots", "events"):
            store.export_jsonl(table)
        store.export_case_chains(run_id)
        _write_json(workspace / "exports" / "coverage.json", coverage)
        return {
            "run_id": run_id,
            "processed_listing_tasks": processed,
            "processed_source_tasks": processed_sources,
            "coverage": coverage,
            "source_acquisition": source_acquisition,
            "independence": independence,
            "fatal": False,
        }
