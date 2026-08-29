"""Fail-closed orchestration over the filing-readiness domain modules.

The router stores every supplied payload and result in a local content-addressed
store.  It performs no network access.  Rendering dependencies are imported
only inside the rendering and release handlers so the basic CLI remains usable
without the optional document runtime.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
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
from .source_evidence import SourceEvidenceRepository, execute_bounded_retrieval
from .storage import (
    AppendOnlyJsonlLedger,
    ContentAddressedStore,
    canonical_json_bytes,
    stable_id,
    utc_now,
)


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
            "fetch",
            "import",
            "manual-import",
            "manual_import",
            "status",
        }
    ),
    "application": frozenset({"evaluate", "status"}),
    "issues": frozenset({"generate", "status"}),
    "failures": frozenset({"search", "coverage"}),
    "render": frozenset({"build", "status"}),
    "release": frozenset({"approve", "build", "check", "validate", "status"}),
}
_SECRET_KEYS = frozenset(
    {"token", "api_key", "apikey", "secret", "password", "authorization", "cookie"}
)


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

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.matter = load_matter(self.workspace)
        self.objects = ContentAddressedStore(self.workspace, "workflow")
        self.events = AppendOnlyJsonlLedger(self.workspace / "workflow" / "events.jsonl")
        self.source_root = self.workspace / "evidence" / "official-sources"
        self.failure_root = self.workspace / "evidence" / "failure-corpus"

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

    def _latest_result(self, route: str) -> Optional[dict[str, Any]]:
        for event in reversed(self.events.records()):
            if event.get("route") != route or event.get("action") in {"status", "coverage"}:
                continue
            raw = self.objects.read_bytes(_mapping(event.get("result_object"), label="result_object"))
            value = json.loads(raw)
            if isinstance(value, dict):
                return value
        return None

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
        repository = SourceEvidenceRepository(self.source_root)
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
            verified = [item for item in evidence if item.get("filing_ready") is True]
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
        locator = _required_text(payload, "locator")
        parsed = urlparse(locator)
        bounded_scope = _mapping(payload.get("bounded_scope"), label="bounded_scope")
        identity_checks = payload.get("identity_checks") or []
        if not isinstance(identity_checks, Sequence) or isinstance(identity_checks, (str, bytes)):
            raise WorkflowInputError("identity_checks должен быть списком.")
        if not all(isinstance(item, Mapping) for item in identity_checks):
            raise WorkflowInputError("Каждая identity check должна быть JSON-объектом.")
        request = AdapterRequest(
            source_id=_required_text(payload, "source_id"),
            locator=locator,
            bounded_scope=bounded_scope,
            max_attempts=int(payload.get("max_attempts") or 1),
            timeout_seconds=float(payload.get("timeout_seconds") or 20.0),
            metadata={
                "max_bytes": int(payload.get("max_bytes") or 25 * 1024 * 1024),
                "terminal_rule_verified": payload.get("terminal_rule_verified") is True,
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
            latest = self._latest_result("application")
            return self._base_result(
                "application",
                action,
                state=(str(latest["state"]) if latest else "blocked"),
                implemented=True,
                message=(
                    "Показан последний доказательственный вывод о применении нормы."
                    if latest
                    else "Оценка применения нормы ещё не выполнялась."
                ),
                result={"latest": latest},
                found=(("Последняя оценка применения",) if latest else ()),
                missing=(() if latest else ("Оценка по полным текстам судебных актов",)),
                next_actions=(
                    "Проверьте вывод и доказательственные локаторы вручную."
                    if latest
                    else "Передайте records[] в application evaluate."
                ,),
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
            latest = self._latest_result("issues")
            return self._base_result(
                "issues",
                action,
                state=(str(latest["state"]) if latest else "blocked"),
                implemented=True,
                message=(
                    "Показан последний набор конституционно-правовых вариантов."
                    if latest
                    else "Варианты конституционно-правовой проблемы ещё не формировались."
                ),
                result={"latest": latest},
                missing=(() if latest else ("Доказательственный seed для issue-кандидата",)),
                next_actions=("Передайте seeds[] в issues generate.",),
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
        decisions = [asdict(evaluate_issue_gates(candidate)) for candidate in generated.candidates]
        release_ready = [
            candidate["issue_option_id"]
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
        corpus = FailureCorpus(self.failure_root)
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
            require_release_support(complaint)
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
            return self._operation_status("release", "Комплект для подачи ещё не собирался.")
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
            reviewer = _required_text(payload, "reviewer")
            reviewed_at = (
                str(payload["reviewed_at"]).strip()
                if payload.get("reviewed_at")
                else None
            )
            try:
                manifest = approve_release_pack(
                    manifest_path,
                    reviewer=reviewer,
                    reviewed_at=reviewed_at,
                )
                integrity_errors = verify_release_manifest(manifest)
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
            errors = verify_release_manifest(manifest)
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
            )
            integrity_errors = verify_release_manifest(manifest)
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
