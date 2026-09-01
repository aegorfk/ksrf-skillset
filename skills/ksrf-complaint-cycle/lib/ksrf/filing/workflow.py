"""Fail-closed orchestration over the filing-readiness domain modules.

The router stores every supplied payload and result in a local content-addressed
store.  It performs no network access.  Rendering dependencies are imported
only inside the rendering and release handlers so the basic CLI remains usable
without the optional document runtime.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Optional, Sequence
from urllib.parse import urlparse

from .adapters import AdapterRequest, ManualImportAdapter
from .application_evidence import (
    application_record_from_dict,
    assess_application_chain,
    classify_application,
    evaluate_application_admissibility,
)
from .contracts import SCHEMA_VERSION
from .failure_corpus import FailureCorpus
from .issue_options import (
    HumanIssueSelection,
    IssueGate,
    IssueSeed,
    PracticeClaimGate,
    evaluate_issue_gates,
    generate_issue_candidates,
)
from .matter import load_matter
from .source_evidence import (
    SourceEvidenceRepository,
    SourceIdentityVerifier,
    execute_bounded_retrieval,
)
from .storage import (
    AppendOnlyJsonlLedger,
    ContentAddressedStore,
    canonical_json_bytes,
    stable_id,
    utc_now,
)
from .trusted_approvals import TrustedApprovalLedger


MAX_PAYLOAD_BYTES = 10 * 1024 * 1024
HUMAN_ONLY_ACTIONS = (
    "signature",
    "fee_or_exemption_confirmation",
    "filing",
)
ROUTE_TITLES = {
    "sources": "Проверка официальных источников и редакций норм",
    "application": "Доказательство применения нормы",
    "issues": "Варианты конституционно-правовой проблемы",
    "failures": "Корпус неудачных обращений",
    "evaluate": "Outcome-blind оценка качества",
    "render": "Сборка и проверка DOCX/PDF",
    "release": "Комплект для передачи человеку",
}
SUPPORTED_ACTIONS = {
    "sources": frozenset(
        {
            "browser",
            "browser-handoff",
            "claim-coverage",
            "approve-identity",
            "fetch",
            "import",
            "manual-import",
            "manual_import",
            "pre-filing-freshness",
            "status",
        }
    ),
    "application": frozenset({"evaluate", "status"}),
    "issues": frozenset({"generate", "status"}),
    "failures": frozenset({"ingest", "search", "coverage"}),
    "evaluate": frozenset({"run", "status"}),
    "render": frozenset({"build", "status"}),
    "release": frozenset({"approve", "build", "check", "validate", "status"}),
}
_SECRET_KEYS = frozenset(
    {"token", "api_key", "apikey", "secret", "password", "authorization", "cookie"}
)
_POST_FILING_OUTCOME_KEYS = frozenset(
    {
        "actual_outcome",
        "court_outcome",
        "ksrf_disposition",
        "post_filing_outcome",
        "published_outcome",
    }
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class WorkflowError(ValueError):
    """Base error for a malformed or unsupported local workflow request."""


class WorkflowInputError(WorkflowError):
    """The versioned payload cannot be safely interpreted."""


def _reject_secret_fields(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SECRET_KEYS:
                raise WorkflowInputError(
                    f"Поле {path}.{key} похоже на секрет и не принимается в CLI payload."
                )
            _reject_secret_fields(item, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_secret_fields(item, path=f"{path}[{index}]")


def _reject_post_filing_outcome_fields(value: Any, *, path: str = "payload") -> None:
    """Keep drafting/evaluation packets blind to later KSRF dispositions."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _POST_FILING_OUTCOME_KEYS:
                raise WorkflowInputError(
                    f"Поле {path}.{key} раскрывает последующий исход и запрещено в outcome-blind оценке."
                )
            _reject_post_filing_outcome_fields(item, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _reject_post_filing_outcome_fields(item, path=f"{path}[{index}]")


def validate_versioned_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise WorkflowInputError("Payload должен быть JSON-объектом.")
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        if version is None:
            raise WorkflowInputError(
                "В payload отсутствует обязательная версия schema_version."
            )
        raise WorkflowInputError(
            f"Версия payload {version!r} не поддерживается; требуется {SCHEMA_VERSION}."
        )
    normalized = dict(payload)
    _reject_secret_fields(normalized)
    return normalized


def load_versioned_payload(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser()
    if not source.is_file():
        raise WorkflowInputError(f"Файл payload не найден: {source}")
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise WorkflowInputError(f"Не удалось прочитать payload: {exc}") from exc
    if size <= 0 or size > MAX_PAYLOAD_BYTES:
        raise WorkflowInputError(
            f"Размер payload должен быть от 1 до {MAX_PAYLOAD_BYTES} байт; получено {size}."
        )
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowInputError(f"Payload не является корректным UTF-8 JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise WorkflowInputError("Payload должен быть JSON-объектом.")
    return validate_versioned_payload(value)


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise WorkflowInputError("Ожидался список строк.")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkflowInputError(f"{label} должен быть JSON-объектом.")
    return value


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise WorkflowInputError(f"В payload отсутствует обязательное поле {key}.")
    return value


def _issue_gate(payload: Any) -> IssueGate:
    raw = _mapping(payload or {}, label="issue gate")
    return IssueGate(
        state=str(raw.get("state") or "unknown"),
        rationale=str(raw.get("rationale") or ""),
        evidence_ids=_tuple_strings(raw.get("evidence_ids")),
        reviewer=(str(raw["reviewer"]).strip() if raw.get("reviewer") else None),
        reviewed_at=(str(raw["reviewed_at"]).strip() if raw.get("reviewed_at") else None),
        requires_human_review=raw.get("requires_human_review") is True,
    )


def _practice_claim(payload: Any) -> PracticeClaimGate:
    raw = _mapping(payload, label="practice claim")
    return PracticeClaimGate(
        claim_id=_required_text(raw, "claim_id"),
        statement=str(raw.get("statement") or ""),
        state=str(raw.get("state") or "unknown"),
        evidence_ids=_tuple_strings(raw.get("evidence_ids")),
        authority_scope=str(raw.get("authority_scope") or ""),
        authority_class=str(raw.get("authority_class") or "unknown"),
        freshness_status=str(raw.get("freshness_status") or "unknown"),
        counterexample_ids=_tuple_strings(raw.get("counterexample_ids")),
        counterexample_review_status=str(
            raw.get("counterexample_review_status") or "unknown"
        ),
        human_decision=str(raw.get("human_decision") or "pending"),
        reviewer=(str(raw["reviewer"]).strip() if raw.get("reviewer") else None),
        reviewed_at=(str(raw["reviewed_at"]).strip() if raw.get("reviewed_at") else None),
    )


def _issue_seed(payload: Any) -> IssueSeed:
    raw = _mapping(payload, label="issue seed")
    selection_raw = _mapping(raw.get("human_selection") or {}, label="human_selection")
    selection = HumanIssueSelection(
        state=str(selection_raw.get("state") or "pending"),
        reviewer=(
            str(selection_raw["reviewer"]).strip()
            if selection_raw.get("reviewer")
            else None
        ),
        reviewed_at=(
            str(selection_raw["reviewed_at"]).strip()
            if selection_raw.get("reviewed_at")
            else None
        ),
        note=str(selection_raw.get("note") or ""),
    )
    practice_raw = raw.get("practice_claims") or []
    if not isinstance(practice_raw, Sequence) or isinstance(practice_raw, (str, bytes)):
        raise WorkflowInputError("practice_claims должен быть списком.")
    try:
        rank = int(raw.get("model_rank") or 0)
    except (TypeError, ValueError) as exc:
        raise WorkflowInputError("model_rank должен быть целым числом.") from exc
    return IssueSeed(
        seed_id=_required_text(raw, "seed_id"),
        claim_id=_required_text(raw, "claim_id"),
        norm_id=_required_text(raw, "norm_id"),
        norm_version_id=_required_text(raw, "norm_version_id"),
        theory_code=_required_text(raw, "theory_code"),
        normative_meaning=str(raw.get("normative_meaning") or ""),
        application_evidence_ids=_tuple_strings(raw.get("application_evidence_ids")),
        application_gate_passed=raw.get("application_gate_passed") is True,
        constitutional_benchmarks=_tuple_strings(raw.get("constitutional_benchmarks")),
        rights_impairment=str(raw.get("rights_impairment") or ""),
        anti_fourth_instance_boundary=str(raw.get("anti_fourth_instance_boundary") or ""),
        ksrf_authority_ids=_tuple_strings(raw.get("ksrf_authority_ids")),
        adverse_authority_ids=_tuple_strings(raw.get("adverse_authority_ids")),
        adverse_authority_summary=str(raw.get("adverse_authority_summary") or ""),
        adverse_authority_delta=str(raw.get("adverse_authority_delta") or ""),
        requested_remedy=str(raw.get("requested_remedy") or ""),
        strengths=_tuple_strings(raw.get("strengths")),
        weaknesses=_tuple_strings(raw.get("weaknesses")),
        source_gaps=_tuple_strings(raw.get("source_gaps")),
        model_rank=rank,
        anti_fourth_instance_gate=_issue_gate(raw.get("anti_fourth_instance_gate")),
        practice_claims=tuple(_practice_claim(item) for item in practice_raw),
        adverse_authority_gate=_issue_gate(raw.get("adverse_authority_gate")),
        remedy_gate=_issue_gate(raw.get("remedy_gate")),
        human_selection=selection,
    )


class WorkflowRouter:
    """One local router over already implemented filing-readiness modules."""

    def __init__(
        self,
        workspace: str | Path,
        *,
        approval_ledger: TrustedApprovalLedger | None = None,
        source_identity_verifier: SourceIdentityVerifier | None = None,
        relief_binding_authority: Any | None = None,
        holding_binding_authority: Any | None = None,
        failure_private_root: str | Path | None = None,
        failure_redaction_verifier: Any | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.matter = load_matter(self.workspace)
        self.objects = ContentAddressedStore(self.workspace, "workflow")
        self.events = AppendOnlyJsonlLedger(self.workspace / "workflow" / "events.jsonl")
        self.source_root = self.workspace / "evidence" / "official-sources"
        self.failure_root = self.workspace / "evidence" / "failure-corpus"
        configured_private_root = failure_private_root or os.environ.get(
            "KSRF_PRIVATE_CORPUS_ROOT"
        )
        self.failure_private_root = (
            Path(configured_private_root).expanduser().resolve()
            if configured_private_root
            else (self.workspace / "private" / "failure-corpus").resolve()
        )
        public_failure_root = self.failure_root.resolve()
        if (
            self.failure_private_root == public_failure_root
            or self.failure_private_root in public_failure_root.parents
            or public_failure_root in self.failure_private_root.parents
        ):
            raise WorkflowInputError(
                "Приватный corpus root должен быть физически отделён от публичного failure-corpus root."
            )
        self.evaluation_runs = AppendOnlyJsonlLedger(
            self.workspace / "evaluation" / "runs.jsonl"
        )
        self.approvals = approval_ledger or TrustedApprovalLedger(
            self.workspace / "trusted-approvals"
        )
        self.source_identity_verifier = source_identity_verifier
        self.relief_binding_authority = relief_binding_authority
        self.holding_binding_authority = holding_binding_authority
        self.failure_redaction_verifier = failure_redaction_verifier

    def _source_repository(self) -> SourceEvidenceRepository:
        return SourceEvidenceRepository(
            self.source_root,
            approval_ledger=self.approvals,
            identity_verifier=self.source_identity_verifier,
        )

    def _resolve_current_source_authority(
        self,
        evidence_id: str,
    ) -> Optional[dict[str, Any]]:
        repository = self._source_repository()
        matches = [
            item
            for item in repository.evidence.records()
            if str(item.get("evidence_id") or "") == str(evidence_id)
        ]
        if len(matches) != 1:
            return None
        evidence = matches[0]
        return {
            "evidence": evidence,
            "authority": repository.current_filing_authority(evidence),
        }

    def _failure_corpus(self) -> FailureCorpus:
        return FailureCorpus(
            self.failure_root,
            private_root=self.failure_private_root,
            approval_ledger=self.approvals,
            source_authority_resolver=self._resolve_current_source_authority,
            redaction_verifier=self.failure_redaction_verifier,
        )

    def _base_result(
        self,
        route: str,
        action: str,
        *,
        state: str,
        implemented: bool,
        message: str,
        result: Mapping[str, Any],
        found: Sequence[str] = (),
        missing: Sequence[str] = (),
        next_actions: Sequence[str] = (),
    ) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "route": route,
            "action": action,
            "title": ROUTE_TITLES.get(route, route),
            "state": state,
            "implemented": implemented,
            "message": message,
            "found": list(found),
            "missing": list(missing),
            "next_actions": list(next_actions),
            "result": dict(result),
            "external_transmission_performed": False,
            "human_only_actions": list(HUMAN_ONLY_ACTIONS),
            "filing_performed": False,
        }

    def _persist(
        self,
        output: Mapping[str, Any],
        input_object: Optional[Mapping[str, Any]],
    ) -> dict[str, Any]:
        result_object = self.objects.put_bytes(canonical_json_bytes(output))
        observed_at = utc_now()
        event_body = {
            "schema_version": SCHEMA_VERSION,
            "route": output["route"],
            "action": output["action"],
            "state": output["state"],
            "message": output["message"],
            "input_object": dict(input_object) if input_object else None,
            "result_object": result_object,
            "observed_at": observed_at,
        }
        event = dict(event_body)
        event["event_id"] = stable_id("workflow-event", event_body)
        self.events.append(event)
        complete = dict(output)
        complete["input_object"] = dict(input_object) if input_object else None
        complete["result_object"] = result_object
        complete["event_id"] = event["event_id"]
        return complete

    def _latest_operation(
        self, route: str
    ) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
        for event in reversed(self.events.records()):
            if event.get("route") != route or event.get("action") in {"status", "coverage"}:
                continue
            raw = self.objects.read_bytes(_mapping(event.get("result_object"), label="result_object"))
            value = json.loads(raw)
            if not isinstance(value, dict):
                continue
            payload: Optional[dict[str, Any]] = None
            input_object = event.get("input_object")
            if isinstance(input_object, Mapping):
                input_raw = self.objects.read_bytes(
                    _mapping(input_object, label="input_object")
                )
                input_value = json.loads(input_raw)
                if isinstance(input_value, dict):
                    payload = input_value
            return value, payload
        return None, None

    def _latest_result(self, route: str) -> Optional[dict[str, Any]]:
        result, _payload = self._latest_operation(route)
        return result

    def dispatch(
        self,
        route: str,
        action: str,
        payload: Optional[Mapping[str, Any]] = None,
        *,
        allow_network: bool = False,
    ) -> dict[str, Any]:
        route_key = str(route).strip().lower()
        action_key = str(action).strip().lower()
        normalized_payload = validate_versioned_payload(payload) if payload is not None else None
        input_object = (
            self.objects.put_bytes(canonical_json_bytes(normalized_payload))
            if normalized_payload is not None
            else None
        )
        if action_key not in SUPPORTED_ACTIONS.get(route_key, frozenset()):
            output = self._base_result(
                route_key,
                action_key,
                state="blocked",
                implemented=False,
                message="Для этого маршрута ещё нет проверенного локального обработчика.",
                result={"reason_code": "unsupported_route_action"},
                missing=("Проверенный обработчик этапа",),
                next_actions=("Используйте одну из документированных команд этапа.",),
            )
            return self._persist(output, input_object)
        try:
            output = self._dispatch_supported(
                route_key,
                action_key,
                normalized_payload,
                input_object,
                allow_network=allow_network,
            )
        except WorkflowInputError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkflowInputError(f"Payload этапа {route_key}/{action_key} некорректен: {exc}") from exc
        return self._persist(output, input_object)

    def _dispatch_supported(
        self,
        route: str,
        action: str,
        payload: Optional[Mapping[str, Any]],
        input_object: Optional[Mapping[str, Any]],
        *,
        allow_network: bool,
    ) -> dict[str, Any]:
        if route == "sources":
            return self._sources(action, payload, allow_network=allow_network)
        if route == "application":
            return self._application(action, payload)
        if route == "issues":
            return self._issues(action, payload)
        if route == "failures":
            return self._failures(action, payload)
        if route == "evaluate":
            return self._evaluate(action, payload)
        if route == "render":
            return self._render(action, payload, input_object)
        if route == "release":
            return self._release(action, payload, input_object)
        raise WorkflowInputError(f"Неизвестный маршрут: {route}")

    def _sources(
        self,
        action: str,
        payload: Optional[Mapping[str, Any]],
        *,
        allow_network: bool,
    ) -> dict[str, Any]:
        repository = self._source_repository()
        if action == "status":
            coverage = dict(repository.coverage_report())
            observations = repository.observations.records()
            if any(
                item.get("acquisition_transport") == "manual_import"
                for item in observations
            ):
                # A missing local file says nothing about the official bank.
                coverage["absence_claim_permitted"] = False
                coverage["limits"] = [
                    *coverage.get("limits", []),
                    "manual_import_cannot_prove_official_absence",
                ]
            evidence = repository.evidence.records()
            verified = repository.current_verified_official_evidence()
            state = "ready_for_expert_review" if verified else "blocked"
            message = (
                "Есть официальные источники с проверенной идентичностью."
                if verified
                else "Официальные доказательства пока не подтверждены."
            )
            return self._base_result(
                "sources",
                action,
                state=state,
                implemented=True,
                message=message,
                result={
                    "coverage": coverage,
                    "evidence_count": len(evidence),
                    "verified_official_evidence_count": len(verified),
                },
                found=((f"Проверенных официальных файлов: {len(verified)}",) if verified else ()),
                missing=(() if verified else ("Официальный файл с проверенной идентичностью",)),
                next_actions=(
                    "Перед подачей обновите временно чувствительные источники."
                    if verified
                    else "Импортируйте официальный файл и зафиксируйте проверки номера, даты и издателя."
                ,),
            )
        if payload is None:
            raise WorkflowInputError(f"Для sources {action} нужен версионированный --payload.")
        if action == "approve-identity":
            return self._base_result(
                "sources",
                action,
                state="blocked",
                implemented=True,
                message=(
                    "JSON-вход и неинтерактивный CLI не могут создать одобрение от имени человека."
                ),
                result={
                    "reason_code": "trusted_approval_channel_required",
                    "approval_created": False,
                },
                missing=("Интерактивный TTY или аутентифицированный серверный контекст",),
                next_actions=(
                    "Создайте approval через trusted approval API после реальной аутентификации человека."
                ,),
            )
        if action in {"claim-coverage", "pre-filing-freshness"}:
            claims = payload.get("claims")
            if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
                raise WorkflowInputError("claims должен быть списком тезисов с evidence_ids.")
            if not all(isinstance(item, Mapping) for item in claims):
                raise WorkflowInputError("Каждый тезис должен быть JSON-объектом.")
            try:
                if action == "claim-coverage":
                    report = repository.claim_source_coverage_report(claims)
                    ready = report["filing_ready"] is True
                    message = (
                        "Каждый тезис связан с достаточным проверенным источником."
                        if ready
                        else "Не все тезисы имеют достаточную подтверждённую опору."
                    )
                else:
                    report = repository.pre_filing_freshness_report(
                        claims,
                        as_of=(str(payload.get("as_of")) if payload.get("as_of") else None),
                    )
                    ready = report["pre_filing_ready"] is True
                    message = (
                        "Зависимые источники тезисов актуальны на момент проверки."
                        if ready
                        else "Перед подачей нужно обновить или повторно проверить зависимые источники."
                    )
            except ValueError as exc:
                raise WorkflowInputError(str(exc)) from exc
            blocked_claims = [
                item["claim_id"]
                for item in report["claims"]
                if (
                    item.get("support_gate_passed") is False
                    or item.get("freshness_state") != "current"
                )
            ]
            return self._base_result(
                "sources",
                action,
                state="ready_for_expert_review" if ready else "blocked",
                implemented=True,
                message=message,
                result=report,
                found=((f"Проверено тезисов: {len(report['claims'])}",) if report["claims"] else ()),
                missing=tuple(f"Источник или актуальность тезиса {claim_id}" for claim_id in blocked_claims),
                next_actions=(
                    "Разрешите все blockers по тезисам и повторите проверку непосредственно перед подачей."
                ,),
            )
        locator = _required_text(payload, "locator")
        parsed = urlparse(locator)
        bounded_scope = _mapping(payload.get("bounded_scope"), label="bounded_scope")
        identity_checks = payload.get("identity_checks") or []
        if not isinstance(identity_checks, Sequence) or isinstance(identity_checks, (str, bytes)):
            raise WorkflowInputError("identity_checks должен быть списком.")
        if not all(isinstance(item, Mapping) for item in identity_checks):
            raise WorkflowInputError("Каждая identity check должна быть JSON-объектом.")
        approval_ids = payload.get("approval_ids") or []
        if not isinstance(approval_ids, Sequence) or isinstance(approval_ids, (str, bytes)):
            raise WorkflowInputError("approval_ids должен быть списком immutable approval_id.")
        request_source_id = _required_text(payload, "source_id")
        source_config = repository.registry.get(request_source_id)
        request = AdapterRequest(
            source_id=request_source_id,
            locator=locator,
            bounded_scope=bounded_scope,
            max_attempts=int(payload.get("max_attempts") or 1),
            timeout_seconds=float(payload.get("timeout_seconds") or 20.0),
            metadata={
                "max_bytes": int(payload.get("max_bytes") or 25 * 1024 * 1024),
                "terminal_rule_verified": payload.get("terminal_rule_verified") is True,
                "allowed_domains": list(source_config.get("domains") or []),
            },
        )
        is_url = parsed.scheme in {"http", "https"}
        if is_url:
            resolved = repository.registry.resolve_url(locator)
            if not resolved or resolved.get("source_id") != request.source_id:
                return self._base_result(
                    "sources",
                    action,
                    state="blocked",
                    implemented=True,
                    message="Адрес не соответствует выбранной записи официального реестра; запрос не выполнялся.",
                    result={
                        "status": "conflict",
                        "reason_code": "source_url_registry_mismatch",
                        "network_access_authorized": allow_network,
                    },
                    missing=("Совпадение source_id и официального домена",),
                    next_actions=("Исправьте source_id или используйте адрес из официального реестра.",),
                )
        from .adapters import BrowserHandoffAdapter, DirectHttpAdapter

        if action in {"import", "manual-import", "manual_import"}:
            adapter = BrowserHandoffAdapter() if is_url else ManualImportAdapter()
        elif action in {"browser", "browser-handoff"}:
            if not is_url:
                raise WorkflowInputError("Browser handoff требует официальный http(s)-адрес.")
            adapter = BrowserHandoffAdapter()
        elif action == "fetch":
            if not is_url:
                raise WorkflowInputError("Direct fetch требует официальный http(s)-адрес.")
            adapter = DirectHttpAdapter() if allow_network else BrowserHandoffAdapter()
        else:
            raise WorkflowInputError(f"Неизвестное действие источника: {action}")

        acquired = execute_bounded_retrieval(adapter, request)
        observation, evidence = repository.record_result(
            request,
            acquired,
            identity_checks=[dict(item) for item in identity_checks],
            approval_ids=[str(item) for item in approval_ids],
        )
        ready = bool(evidence and evidence.get("filing_ready") is True)
        if acquired.status == "interactive_required":
            return self._base_result(
                "sources",
                action,
                state="blocked",
                implemented=True,
                message=(
                    "Сетевой адрес не загружался. Откройте официальный источник вручную; "
                    "при CAPTCHA продолжите в браузере и затем импортируйте сохранённый файл."
                ),
                result={
                    "status": "interactive_required",
                    "reason_code": acquired.error_code or "manual_browser_handoff_required",
                    "observation": observation,
                    "evidence": None,
                    "network_access_authorized": allow_network,
                },
                missing=("Локально сохранённый официальный файл",),
                next_actions=("Сохраните файл без обхода CAPTCHA и повторите manual-import.",),
            )
        return self._base_result(
            "sources",
            action,
            state="ready_for_expert_review" if ready else "blocked",
            implemented=True,
            message=(
                "Официальный файл сохранён неизменяемо и прошёл проверки идентичности."
                if ready
                else "Наблюдение сохранено, но официальный статус для подачи не подтверждён."
            ),
            result={
                "status": acquired.status,
                "observation": observation,
                "evidence": evidence,
                "network_access_authorized": allow_network,
            },
            found=(("Контент-адресованный оригинал",) if evidence else ()),
            missing=(() if ready else ("Проверка идентичности официального источника",)),
            next_actions=(
                "Проверьте номер, дату, издателя и устойчивый локатор перед использованием."
            ,),
        )

    def _application(
        self, action: str, payload: Optional[Mapping[str, Any]]
    ) -> dict[str, Any]:
        if action == "status":
            latest, latest_payload = self._latest_operation("application")
            current = (
                self._application("evaluate", latest_payload)
                if latest is not None and latest_payload is not None
                else None
            )
            return self._base_result(
                "application",
                action,
                state=(str(current["state"]) if current else "blocked"),
                implemented=True,
                message=(
                    "Последний вывод о применении нормы повторно проверен по текущим доказательствам и одобрениям."
                    if current
                    else "Оценка применения нормы ещё не выполнялась."
                ),
                result={
                    "latest": current,
                    "cached_result_reused_without_revalidation": False,
                },
                found=(tuple(current.get("found") or ()) if current else ()),
                missing=(
                    tuple(current.get("missing") or ())
                    if current
                    else ("Оценка по полным текстам судебных актов",)
                ),
                next_actions=(
                    tuple(current.get("next_actions") or ())
                    if current
                    else ("Передайте records[] в application evaluate.",)
                ),
            )
        if payload is None:
            raise WorkflowInputError("Для application evaluate нужен версионированный --payload.")
        raw_records = payload.get("records")
        if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)) or not raw_records:
            raise WorkflowInputError("records должен быть непустым списком.")
        records = tuple(application_record_from_dict(_mapping(item, label="application record")) for item in raw_records)
        chain = assess_application_chain(records)
        target_id = str(payload.get("target_record_id") or records[-1].record_id)
        target = next((item for item in records if item.record_id == target_id), None)
        if target is None:
            raise WorkflowInputError(f"target_record_id не найден в records: {target_id}")
        norm_version_passport = (
            dict(_mapping(payload.get("norm_version_passport"), label="norm_version_passport"))
            if payload.get("norm_version_passport") is not None
            else None
        )
        preservation_rule_evidence = (
            dict(
                _mapping(
                    payload.get("preservation_rule_evidence"),
                    label="preservation_rule_evidence",
                )
            )
            if payload.get("preservation_rule_evidence") is not None
            else None
        )
        official_evidence_repository = self._source_repository()
        decision = evaluate_application_admissibility(
            target,
            chain,
            norm_version_status=str(payload.get("norm_version_status") or "unknown"),
            version_evidence_ids=_tuple_strings(payload.get("version_evidence_ids")),
            preservation_rule_status=str(payload.get("preservation_rule_status") or "unknown"),
            discovery_score=(
                float(payload["discovery_score"])
                if payload.get("discovery_score") is not None
                else None
            ),
            approval_ledger=self.approvals,
            approval_id=(
                str(payload.get("approval_id")) if payload.get("approval_id") else None
            ),
            approval_as_of=(
                str(payload.get("approval_as_of"))
                if payload.get("approval_as_of")
                else None
            ),
            norm_version_passport=norm_version_passport,
            norm_version_official_evidence_verifier=official_evidence_repository,
            norm_version_approval_id=(
                str(payload.get("norm_version_approval_id"))
                if payload.get("norm_version_approval_id")
                else None
            ),
            preservation_rule_evidence=preservation_rule_evidence,
            preservation_rule_evidence_verifier=official_evidence_repository,
            preservation_rule_approval_id=(
                str(payload.get("preservation_rule_approval_id"))
                if payload.get("preservation_rule_approval_id")
                else None
            ),
        )
        classifications = {
            record.record_id: asdict(classify_application(record)) for record in records
        }
        state = "ready_for_expert_review" if decision.passed else "blocked"
        return self._base_result(
            "application",
            action,
            state=state,
            implemented=True,
            message=(
                "Применение нормы доказано по независимым осям; вывод требует сохранения в экспертном контуре."
                if decision.passed
                else "Критерий применения нормы не пройден: неизвестные и недоказанные элементы не повышены до фактов."
            ),
            result={
                "classifications": classifications,
                "chain": asdict(chain),
                "admissibility": asdict(decision),
                "target_record_id": target_id,
            },
            found=(("Доказательственная классификация по каждой инстанции",) if records else ()),
            missing=tuple(decision.blockers),
            next_actions=(
                "Именованный юрист должен сверить полные акты, причинность и исчерпание."
            ,),
        )

    def _issues(
        self, action: str, payload: Optional[Mapping[str, Any]]
    ) -> dict[str, Any]:
        if action == "status":
            latest, latest_payload = self._latest_operation("issues")
            current = (
                self._issues("generate", latest_payload)
                if latest is not None and latest_payload is not None
                else None
            )
            return self._base_result(
                "issues",
                action,
                state=(str(current["state"]) if current else "blocked"),
                implemented=True,
                message=(
                    "Последний набор вариантов повторно проверен по текущим одобрениям и binding."
                    if current
                    else "Варианты конституционно-правовой проблемы ещё не формировались."
                ),
                result={
                    "latest": current,
                    "cached_result_reused_without_revalidation": False,
                },
                found=(tuple(current.get("found") or ()) if current else ()),
                missing=(
                    tuple(current.get("missing") or ())
                    if current
                    else ("Доказательственный seed для issue-кандидата",)
                ),
                next_actions=(
                    tuple(current.get("next_actions") or ())
                    if current
                    else ("Передайте seeds[] в issues generate.",)
                ),
            )
        if payload is None:
            raise WorkflowInputError("Для issues generate нужен версионированный --payload.")
        raw_seeds = payload.get("seeds")
        if not isinstance(raw_seeds, Sequence) or isinstance(raw_seeds, (str, bytes)):
            raise WorkflowInputError("seeds должен быть списком.")
        seeds = tuple(_issue_seed(item) for item in raw_seeds)
        maximum = int(payload.get("max_candidates") or 4)
        generated = generate_issue_candidates(seeds, max_candidates=maximum)
        candidates = [candidate.to_dict() for candidate in generated.candidates]
        raw_approval_ids = _mapping(payload.get("approval_ids") or {}, label="approval_ids")
        decisions = [
            asdict(
                evaluate_issue_gates(
                    candidate,
                    approval_ledger=self.approvals,
                    approval_ids=_mapping(
                        raw_approval_ids.get(candidate.issue_id) or {},
                        label=f"approval_ids.{candidate.issue_id}",
                    ),
                    approval_as_of=(
                        str(payload.get("approval_as_of"))
                        if payload.get("approval_as_of")
                        else None
                    ),
                )
            )
            for candidate in generated.candidates
        ]
        release_ready = [
            candidate["issue_id"]
            for candidate, decision in zip(candidates, decisions)
            if decision["passed"] is True
        ]
        state = "ready_for_expert_review" if candidates else "blocked"
        blockers = sorted(
            {
                blocker
                for decision in decisions
                for blocker in decision.get("blockers", ())
            }
        )
        return self._base_result(
            "issues",
            action,
            state=state,
            implemented=True,
            message=generated.generation_note,
            result={
                "candidates": candidates,
                "omitted": [asdict(item) for item in generated.omitted],
                "candidate_gates": decisions,
                "release_ready_candidate_ids": release_ready,
                "generic_default_used": generated.generic_default_used,
            },
            found=((f"Самостоятельных вариантов: {len(candidates)}",) if candidates else ()),
            missing=tuple(blockers),
            next_actions=("Именованный юрист выбирает или редактирует ведущий вариант.",),
        )

    def _failures(
        self, action: str, payload: Optional[Mapping[str, Any]]
    ) -> dict[str, Any]:
        corpus = self._failure_corpus()
        if action == "ingest":
            if payload is None:
                raise WorkflowInputError("Для corpus ingest нужен версионированный --payload.")
            item_type = str(payload.get("corpus_item_type") or "public_refusal").strip()
            if item_type == "public_refusal":
                refusal = payload.get("public_refusal") or payload.get("record") or payload
                result = corpus.ingest_public_refusal(
                    _mapping(refusal, label="public_refusal")
                )
                result["eligible_for_adverse_gate"] = False
                result["coverage"] = corpus.coverage_report()
                return self._base_result(
                    "failures",
                    action,
                    state="ready_for_expert_review",
                    implemented=True,
                    message=(
                        "Публичный официальный отказ зарегистрирован локально; его petition units "
                        "не допускаются в adverse gate до локальной проверки и центрального "
                        "host-attested approval полного текущего binding."
                    ),
                    result=result,
                    found=(f"Зарегистрировано petition units: {result['inserted_count']}",),
                    missing=("Именованная проверка извлечённых единиц корпуса",),
                    next_actions=(
                        "Проверьте локаторы, роли причин отказа и каждую единицу перед одобрением.",
                    ),
                )
            if item_type == "private_document":
                source_value = _required_text(payload, "document_path")
                parsed = urlparse(source_value)
                if parsed.scheme and parsed.scheme != "file":
                    raise WorkflowInputError(
                        "Частный документ принимается только из локального файла; сеть не используется."
                    )
                source = Path(parsed.path if parsed.scheme == "file" else source_value).expanduser()
                if not source.is_file():
                    raise WorkflowInputError(f"Локальный частный документ не найден: {source}")
                size = source.stat().st_size
                if size <= 0 or size > MAX_PAYLOAD_BYTES:
                    raise WorkflowInputError(
                        f"Размер частного документа должен быть от 1 до {MAX_PAYLOAD_BYTES} байт."
                    )
                record = corpus.register_private_document(
                    matter_id=str(self.matter["matter_id"]),
                    document_role=_required_text(payload, "document_role"),
                    content=source.read_bytes(),
                    consent_id=(str(payload.get("consent_id")) if payload.get("consent_id") else None),
                )
                return self._base_result(
                    "failures",
                    action,
                    state="completed_with_limits",
                    implemented=True,
                    message=(
                        "Частный документ зарегистрирован только для этого дела и не включён "
                        "в межделовой поиск."
                    ),
                    result={
                        "record": record,
                        "eligible_for_cross_matter_retrieval": False,
                        "coverage": corpus.coverage_report(),
                    },
                    found=("Локальный частный документ зарегистрирован",),
                    next_actions=(
                        "Для общего корпуса отдельно оформите согласие, обезличивание и "
                        "host-attested approval точного производного материала.",
                    ),
                )
            raise WorkflowInputError(
                "corpus_item_type должен быть public_refusal или private_document."
            )
        if action == "coverage":
            coverage = corpus.coverage_report()
            state = "completed_with_limits" if coverage["coverage_state"] != "unknown" else "blocked"
            return self._base_result(
                "failures",
                action,
                state=state,
                implemented=True,
                message="Покрытие корпуса показано без заявления о полноте.",
                result=coverage,
                found=(f"Публичных petition units: {coverage['public_petition_unit_count']}",),
                missing=(("Наблюдаемое покрытие корпуса",) if coverage["coverage_state"] == "unknown" else ()),
                next_actions=("Учитывайте источники, даты, таксономию и ошибки доступа.",),
            )
        if payload is None:
            raise WorkflowInputError("Для failures search нужен версионированный --payload.")
        query = _mapping(payload.get("query"), label="query")
        if not query:
            raise WorkflowInputError("query не может быть пустым.")
        limit = int(payload.get("limit") or 20)
        if not 1 <= limit <= 100:
            raise WorkflowInputError("limit должен быть от 1 до 100.")
        result = corpus.search_adverse(query, limit=limit)
        return self._base_result(
            "failures",
            action,
            state="completed_with_limits",
            implemented=True,
            message=(
                "Поиск выполнен; результат ограничен фактически просмотренным покрытием и не заменяет экспертное сопоставление."
            ),
            result=result,
            found=(f"Найдено кандидатов: {len(result['hits'])}",),
            missing=(
                ("Подтверждённый материально сходный аналог",)
                if not any(item.get("eligible_for_adverse_gate") for item in result["hits"])
                else ()
            ),
            next_actions=("Сопоставьте каждый материальный аналог и сформулируйте отличие дела.",),
        )

    def _evaluate(
        self, action: str, payload: Optional[Mapping[str, Any]]
    ) -> dict[str, Any]:
        if action == "status":
            records = self.evaluation_runs.records()
            if not records:
                return self._base_result(
                    "evaluate",
                    action,
                    state="blocked",
                    implemented=True,
                    message="Outcome-blind прогоны ещё не зарегистрированы.",
                    result={"run_count": 0, "human_review": {"status": "pending"}},
                    missing=("Сопоставимые baseline и candidate прогоны",),
                    next_actions=("Передайте локальный eval bundle в evaluate run.",),
                )
            case_ids = sorted({str(item["case_id"]) for item in records})
            return self._base_result(
                "evaluate",
                action,
                state="ready_for_expert_review",
                implemented=True,
                message="Локальные outcome-blind прогоны зарегистрированы; человеческая оценка не подменена.",
                result={
                    "run_count": len(records),
                    "case_ids": case_ids,
                    "human_review": {"status": "pending"},
                },
                found=(f"Зарегистрировано прогонов: {len(records)}",),
                missing=("Именованная человеческая оценка",),
                next_actions=("Откройте review artifact и зафиксируйте человеческую оценку отдельно.",),
            )

        if payload is None:
            raise WorkflowInputError("Для evaluate run нужен версионированный --payload.")
        if payload.get("outcome_blind") is not True:
            raise WorkflowInputError("outcome_blind должен быть явно равен true.")
        _reject_post_filing_outcome_fields(payload)
        experiment_version = _required_text(payload, "experiment_version")
        dataset_version = _required_text(payload, "dataset_version")
        rubric_version = _required_text(payload, "rubric_version")
        runs_value = payload.get("runs")
        if not isinstance(runs_value, list) or not runs_value:
            raise WorkflowInputError("runs должен быть непустым массивом baseline/candidate прогонов.")

        required_run_fields = (
            "target_skill_snapshot",
            "model",
            "provider",
            "reasoning_effort",
            "prompt",
            "grader_model",
            "run_timestamp",
        )
        by_case: dict[str, dict[str, dict[str, Any]]] = {}
        normalized_runs: list[dict[str, Any]] = []
        for index, raw_run in enumerate(runs_value):
            run = dict(_mapping(raw_run, label=f"runs[{index}]"))
            case_id = _required_text(run, "case_id")
            variant = _required_text(run, "variant")
            if variant not in {"baseline", "candidate"}:
                raise WorkflowInputError(
                    f"runs[{index}].variant должен быть baseline или candidate."
                )
            evidence_hash = _required_text(run, "evidence_packet_sha256")
            if not _SHA256_RE.fullmatch(evidence_hash):
                raise WorkflowInputError(
                    f"runs[{index}].evidence_packet_sha256 должен быть SHA-256."
                )
            for field in required_run_fields:
                _required_text(run, field)
            if "output" not in run:
                raise WorkflowInputError(f"runs[{index}].output обязателен.")
            if not isinstance(run.get("tool_calls"), list):
                raise WorkflowInputError(f"runs[{index}].tool_calls должен быть массивом.")
            _mapping(run.get("usage"), label=f"runs[{index}].usage")
            _mapping(run.get("scores"), label=f"runs[{index}].scores")
            variants = by_case.setdefault(case_id, {})
            if variant in variants:
                raise WorkflowInputError(
                    f"Для case_id={case_id} повторяется вариант {variant}."
                )
            variants[variant] = run
            normalized_runs.append(run)

        for case_id, variants in by_case.items():
            if set(variants) != {"baseline", "candidate"}:
                raise WorkflowInputError(
                    f"Для case_id={case_id} нужны оба варианта baseline и candidate."
                )
            hashes = {
                str(run["evidence_packet_sha256"])
                for run in variants.values()
            }
            if len(hashes) != 1:
                raise WorkflowInputError(
                    f"Для case_id={case_id} baseline и candidate получили разные evidence packet."
                )
            prompts = {str(run["prompt"]) for run in variants.values()}
            if len(prompts) != 1:
                raise WorkflowInputError(
                    f"Для case_id={case_id} baseline и candidate получили разные prompt."
                )

        stored_runs: list[dict[str, Any]] = []
        for run in normalized_runs:
            output_value = run["output"]
            output_bytes = (
                output_value.encode("utf-8")
                if isinstance(output_value, str)
                else canonical_json_bytes(output_value)
            )
            output_object = self.objects.put_bytes(output_bytes)
            record_body = {
                "schema_version": SCHEMA_VERSION,
                "experiment_version": experiment_version,
                "dataset_version": dataset_version,
                "rubric_version": rubric_version,
                "outcome_blind": True,
                "case_id": run["case_id"],
                "variant": run["variant"],
                "evidence_packet_sha256": run["evidence_packet_sha256"],
                "target_skill_snapshot": run["target_skill_snapshot"],
                "model": run["model"],
                "provider": run["provider"],
                "reasoning_effort": run["reasoning_effort"],
                "prompt": run["prompt"],
                "inputs": run.get("inputs"),
                "tool_calls": run["tool_calls"],
                "latency_ms": run.get("latency_ms"),
                "usage": run["usage"],
                "grader_model": run["grader_model"],
                "scores": run["scores"],
                "run_timestamp": run["run_timestamp"],
                "output_object": output_object,
            }
            record = dict(record_body)
            record["run_id"] = stable_id("outcome-blind-eval-run", record_body)
            existing = self.evaluation_runs.latest_by("run_id", record["run_id"])
            if existing is None:
                self.evaluation_runs.append(record)
                stored_runs.append(record)
            else:
                stored_runs.append(existing)

        bundle_id = stable_id(
            "outcome-blind-eval-bundle",
            {
                "experiment_version": experiment_version,
                "dataset_version": dataset_version,
                "rubric_version": rubric_version,
                "run_ids": sorted(item["run_id"] for item in stored_runs),
            },
        )
        result = {
            "bundle_id": bundle_id,
            "outcome_blind": True,
            "equal_input_verified": True,
            "run_count": len(stored_runs),
            "case_count": len(by_case),
            "runs": stored_runs,
            "human_review": {
                "status": "pending",
                "required": True,
                "authority_not_inferred_from_model_scores": True,
            },
            "production_promotion_authorized": False,
        }
        return self._base_result(
            "evaluate",
            action,
            state="ready_for_expert_review",
            implemented=True,
            message=(
                "Outcome-blind baseline/candidate прогоны зарегистрированы на одинаковых входах; "
                "оценки модели не заменяют человеческое решение о продвижении."
            ),
            result=result,
            found=(
                f"Сопоставимых сценариев: {len(by_case)}",
                f"Зарегистрировано прогонов: {len(stored_runs)}",
            ),
            missing=("Именованная человеческая оценка review artifact",),
            next_actions=(
                "Проведите слепое человеческое сравнение и зафиксируйте reviewer, время и материальные ошибки.",
            ),
        )

    def _render(
        self,
        action: str,
        payload: Optional[Mapping[str, Any]],
        input_object: Optional[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if action == "status":
            return self._operation_status("render", "Рендеринг ещё не выполнялся.")
        if payload is None or input_object is None:
            raise WorkflowInputError("Для render build нужен версионированный --payload.")
        complaint_payload = _mapping(payload.get("complaint"), label="complaint")
        try:
            from .composer import build_structured_complaint, require_release_support
            from .renderer import convert_docx_to_pdf, render_docx, validate_rendered_pair
        except ImportError as exc:
            return self._optional_runtime_block("render", action, exc)
        output_dir = self.workspace / "release" / "renders" / str(input_object["sha256"])
        artifacts_dir = output_dir / "artifacts"
        preview_dir = output_dir / "previews"
        try:
            complaint = build_structured_complaint(complaint_payload)
            require_release_support(
                complaint,
                relief_binding_authority=self.relief_binding_authority,
                holding_binding_authority=self.holding_binding_authority,
                require_holding_index=True,
            )
            docx = render_docx(complaint, artifacts_dir / "constitutional-complaint.docx")
            pdf = convert_docx_to_pdf(
                docx.path,
                artifacts_dir / "constitutional-complaint.pdf",
                soffice_path=payload.get("soffice_path"),
            )
            qa = validate_rendered_pair(
                complaint,
                docx.path,
                pdf.path,
                preview_dir=preview_dir,
                pdftoppm_path=payload.get("pdftoppm_path"),
            )
        except Exception as exc:
            return self._base_result(
                "render",
                action,
                state="blocked",
                implemented=True,
                message="DOCX/PDF не прошли обязательную сборку и проверку.",
                result={
                    "error": str(exc),
                    "reason_code": "artifact_generation_or_qa_failed",
                    "output_dir": str(output_dir),
                },
                missing=("Исправный локальный renderer и успешная QA",),
                next_actions=("Установите или укажите локальный LibreOffice и pdftoppm, затем повторите проверку.",),
            )
        passed = qa.get("passed") is True
        return self._base_result(
            "render",
            action,
            state="ready_for_expert_review" if passed else "blocked",
            implemented=True,
            message=(
                "Реальные DOCX и PDF собраны; автоматическая QA пройдена."
                if passed
                else "Артефакты собраны, но QA выявила блокирующие расхождения."
            ),
            result={
                "output_dir": str(output_dir),
                "docx": docx.to_dict(),
                "pdf": pdf.to_dict(),
                "qa": qa,
                "preview_paths": [str(path) for path in sorted(preview_dir.glob("page-*.png"))],
            },
            found=("Реальный DOCX", "Реальный PDF", "Постраничные preview"),
            missing=(() if passed else ("Успешная семантическая и визуальная QA",)),
            next_actions=("Эксперт вручную просматривает PDF; подпись и подача остаются действиями человека.",),
        )

    def _release(
        self,
        action: str,
        payload: Optional[Mapping[str, Any]],
        input_object: Optional[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if action == "status":
            latest, _latest_payload = self._latest_operation("release")
            if latest is None:
                return self._operation_status(
                    "release", "Комплект для подачи ещё не собирался."
                )
            try:
                from .release import verify_release_manifest
            except ImportError as exc:
                return self._optional_runtime_block("release", action, exc)
            manifest_value = (latest.get("result") or {}).get("manifest")
            if not isinstance(manifest_value, Mapping):
                errors = ["release_manifest_missing"]
                manifest = None
            else:
                manifest_path_value = str(manifest_value.get("manifest_path") or "").strip()
                release_root = (self.workspace / "release").resolve()
                try:
                    manifest_path = Path(manifest_path_value).expanduser().resolve(strict=True)
                except (OSError, RuntimeError):
                    errors = ["release_manifest_file_missing"]
                    manifest = dict(manifest_value)
                else:
                    if release_root not in manifest_path.parents:
                        errors = ["release_manifest_path_outside_workspace"]
                        manifest = dict(manifest_value)
                    elif not manifest_path.is_file() or manifest_path.stat().st_size > MAX_PAYLOAD_BYTES:
                        errors = ["release_manifest_file_invalid"]
                        manifest = dict(manifest_value)
                    else:
                        try:
                            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError, json.JSONDecodeError):
                            errors = ["release_manifest_json_invalid"]
                            manifest = dict(manifest_value)
                        else:
                            if not isinstance(loaded, Mapping):
                                errors = ["release_manifest_not_object"]
                                manifest = dict(manifest_value)
                            else:
                                manifest = dict(loaded)
                                errors = verify_release_manifest(
                                    manifest,
                                    approval_ledger=self.approvals,
                                    relief_binding_authority=self.relief_binding_authority,
                                    holding_binding_authority=self.holding_binding_authority,
                                )
            manifest_status = str((manifest or {}).get("status") or "blocked")
            state = (
                manifest_status
                if not errors
                and manifest_status
                in {"ready_for_expert_review", "ready_for_human_signing_filing"}
                else "blocked"
            )
            current = dict(latest)
            current["state"] = state
            current_result = dict(current.get("result") or {})
            current_result["manifest"] = manifest
            current_result["integrity_errors"] = list(errors)
            current["result"] = current_result
            current["message"] = (
                "Комплект повторно проверен по текущим файлам, описи и одобрениям."
                if state != "blocked"
                else "Текущий комплект больше не проходит проверку файлов, описи или одобрений."
            )
            current["missing"] = list(errors)
            return self._base_result(
                "release",
                action,
                state=state,
                implemented=True,
                message=current["message"],
                result={
                    "latest": current,
                    "cached_result_reused_without_revalidation": False,
                },
                found=(
                    ("Текущий release manifest и его файлы повторно проверены",)
                    if state != "blocked"
                    else ()
                ),
                missing=tuple(errors),
                next_actions=(
                    "Исправьте указанные расхождения, пересоберите комплект и получите новые точные одобрения.",
                ),
            )
        if payload is None or input_object is None:
            raise WorkflowInputError(f"Для release {action} нужен версионированный --payload.")
        try:
            from .release import (
                approve_release_pack,
                build_release_pack,
                verify_release_manifest,
            )
        except ImportError as exc:
            return self._optional_runtime_block("release", action, exc)
        if action == "approve":
            manifest_path = Path(_required_text(payload, "manifest_path")).expanduser().resolve()
            release_root = (self.workspace / "release").resolve()
            if manifest_path != release_root and release_root not in manifest_path.parents:
                raise WorkflowInputError(
                    "Одобрять можно только manifest из release-каталога текущего дела."
                )
            approval_id = _required_text(payload, "approval_id")
            reviewer = (
                str(payload["reviewer"]).strip() if payload.get("reviewer") else None
            )
            reviewed_at = (
                str(payload["reviewed_at"]).strip()
                if payload.get("reviewed_at")
                else None
            )
            try:
                manifest = approve_release_pack(
                    manifest_path,
                    approval_ledger=self.approvals,
                    approval_id=approval_id,
                    approval_as_of=(
                        str(payload.get("approval_as_of"))
                        if payload.get("approval_as_of")
                        else None
                    ),
                    reviewer=reviewer,
                    reviewed_at=reviewed_at,
                    relief_binding_authority=self.relief_binding_authority,
                    holding_binding_authority=self.holding_binding_authority,
                )
                integrity_errors = verify_release_manifest(
                    manifest,
                    approval_ledger=self.approvals,
                    relief_binding_authority=self.relief_binding_authority,
                    holding_binding_authority=self.holding_binding_authority,
                )
            except Exception as exc:
                return self._base_result(
                    "release",
                    action,
                    state="blocked",
                    implemented=True,
                    message="Именованное одобрение не принято: пакет или его основание не готовы.",
                    result={
                        "error": str(exc),
                        "reason_code": "release_approval_rejected",
                        "manifest_path": str(manifest_path),
                    },
                    missing=("Неизменившийся пакет и завершённые юридические проверки",),
                    next_actions=("Устраните дефект, пересоберите пакет и повторите визуальную проверку.",),
                )
            state = (
                "ready_for_human_signing_filing"
                if not integrity_errors
                and manifest.get("status") == "ready_for_human_signing_filing"
                else "blocked"
            )
            return self._base_result(
                "release",
                action,
                state=state,
                implemented=True,
                message=(
                    "Именованное одобрение связано с fingerprint неизменившегося пакета; подача не выполнялась."
                    if state == "ready_for_human_signing_filing"
                    else "Одобрение не прошло проверку целостности."
                ),
                result={"manifest": manifest, "integrity_errors": integrity_errors},
                missing=tuple(integrity_errors),
                next_actions=("Человек проверяет подпись, пошлину/льготу и способ подачи.",),
            )
        if action in {"check", "validate"}:
            manifest_value = payload.get("manifest")
            if manifest_value is None:
                manifest_path = Path(_required_text(payload, "manifest_path")).expanduser()
                if not manifest_path.is_file() or manifest_path.stat().st_size > MAX_PAYLOAD_BYTES:
                    raise WorkflowInputError("manifest_path не указывает на допустимый локальный JSON-файл.")
                try:
                    manifest_value = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise WorkflowInputError(f"Не удалось прочитать release manifest: {exc}") from exc
            manifest = dict(_mapping(manifest_value, label="manifest"))
            errors = verify_release_manifest(
                manifest,
                approval_ledger=self.approvals,
                relief_binding_authority=self.relief_binding_authority,
                holding_binding_authority=self.holding_binding_authority,
            )
            state = str(manifest.get("status") or "blocked") if not errors else "blocked"
            if state not in {"ready_for_expert_review", "ready_for_human_signing_filing"}:
                state = "blocked"
            return self._base_result(
                "release",
                action,
                state=state,
                implemented=True,
                message=(
                    "Целостность локального комплекта подтверждена; фактическая подача не выполнялась."
                    if not errors and state != "blocked"
                    else "Комплект не прошёл проверку целостности или готовности."
                ),
                result={"manifest": manifest, "integrity_errors": errors},
                missing=tuple(errors),
                next_actions=("Человек проверяет подпись, пошлину/льготу и способ подачи.",),
            )
        complaint_payload = _mapping(payload.get("complaint"), label="complaint")
        enclosure_sources = payload.get("enclosure_sources") or []
        if not isinstance(enclosure_sources, Sequence) or isinstance(enclosure_sources, (str, bytes)):
            raise WorkflowInputError("enclosure_sources должен быть списком локальных путей.")
        output_dir = self.workspace / "release" / "filing-packs" / str(input_object["sha256"])
        try:
            from .composer import build_structured_complaint

            complaint = build_structured_complaint(complaint_payload)
            manifest = build_release_pack(
                complaint,
                output_dir,
                enclosure_sources=[str(item) for item in enclosure_sources],
                soffice_path=payload.get("soffice_path"),
                pdftoppm_path=payload.get("pdftoppm_path"),
                relief_binding_authority=self.relief_binding_authority,
                holding_binding_authority=self.holding_binding_authority,
            )
            integrity_errors = verify_release_manifest(
                manifest,
                approval_ledger=self.approvals,
                relief_binding_authority=self.relief_binding_authority,
                holding_binding_authority=self.holding_binding_authority,
            )
        except ImportError as exc:
            return self._optional_runtime_block("release", action, exc)
        except Exception as exc:
            return self._base_result(
                "release",
                action,
                state="blocked",
                implemented=True,
                message="Комплект не собран из-за ошибки входных данных или локального runtime.",
                result={"error": str(exc), "output_dir": str(output_dir)},
                missing=("Полный и проверяемый filing pack",),
                next_actions=("Исправьте указанный дефект и повторите локальную сборку.",),
            )
        state = str(manifest.get("status") or "blocked")
        if integrity_errors:
            state = "blocked"
        return self._base_result(
            "release",
            action,
            state=state,
            implemented=True,
            message=(
                "Комплект собран и готов только к контролируемой человеком подписи и подаче."
                if state == "ready_for_human_signing_filing"
                else "Комплект собран, но остаётся заблокированным до устранения пробелов."
            ),
            result={"manifest": manifest, "integrity_errors": integrity_errors},
            found=("DOCX/PDF, опись, хэши и release manifest",),
            missing=tuple(manifest.get("blockers") or ()) + tuple(integrity_errors),
            next_actions=("Человек проверяет комплект, подписывает, подтверждает пошлину/льготу и подаёт жалобу.",),
        )

    def _operation_status(self, route: str, absent_message: str) -> dict[str, Any]:
        latest = self._latest_result(route)
        return self._base_result(
            route,
            "status",
            state=(str(latest["state"]) if latest else "blocked"),
            implemented=True,
            message=("Показан последний локальный результат этапа." if latest else absent_message),
            result={"latest": latest},
            found=(("Последний локальный результат",) if latest else ()),
            missing=(() if latest else ("Выполненный этап",)),
            next_actions=("Выполните этап с версионированным payload.",),
        )

    def _optional_runtime_block(
        self, route: str, action: str, error: ImportError
    ) -> dict[str, Any]:
        missing_name = getattr(error, "name", None) or str(error)
        return self._base_result(
            route,
            action,
            state="blocked",
            implemented=True,
            message="Необязательный локальный runtime документов недоступен; базовые команды продолжают работать.",
            result={
                "reason_code": "optional_document_dependency_missing",
                "missing_dependency": str(missing_name),
            },
            missing=(f"Локальная зависимость: {missing_name}",),
            next_actions=(
                "Установите зависимость вручную в выбранное окружение или используйте профиль без рендеринга; автоматическая установка не выполняется.",
            ),
        )


def render_workflow_result(payload: Mapping[str, Any]) -> str:
    state_labels = {
        "blocked": "заблокировано",
        "ready_for_expert_review": "готово к экспертной проверке",
        "completed_with_limits": "выполнено с ограничениями покрытия",
        "ready_for_human_signing_filing": "готово к подписи и подаче человеком",
    }
    lines = [
        f"Этап: {payload.get('title', payload.get('route', ''))}",
        f"Состояние: {state_labels.get(str(payload.get('state')), payload.get('state'))}",
        str(payload.get("message") or ""),
    ]
    found = payload.get("found") or []
    missing = payload.get("missing") or []
    next_actions = payload.get("next_actions") or []
    if found:
        lines.extend(["", "Что найдено:", *(f"- {item}" for item in found)])
    if missing:
        lines.extend(["", "Чего не хватает:", *(f"- {item}" for item in missing)])
    if next_actions:
        lines.extend(["", "Следующие действия:", *(f"- {item}" for item in next_actions)])
    lines.extend(
        [
            "",
            "Подпись, подтверждение пошлины или льготы и фактическая подача выполняются только человеком.",
        ]
    )
    return "\n".join(lines) + "\n"


def workflow_exit_code(payload: Mapping[str, Any]) -> int:
    return 3 if payload.get("state") in {"blocked", "unknown", "failed", "unavailable", "interactive_required"} else 0


__all__ = [
    "HUMAN_ONLY_ACTIONS",
    "SUPPORTED_ACTIONS",
    "WorkflowError",
    "WorkflowInputError",
    "WorkflowRouter",
    "load_versioned_payload",
    "render_workflow_result",
    "validate_versioned_payload",
    "workflow_exit_code",
]
