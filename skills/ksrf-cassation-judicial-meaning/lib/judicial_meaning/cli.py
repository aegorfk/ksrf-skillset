"""Command-line orchestration for a self-contained local research run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .analysis import (
    analyze_reviewed_chains,
    build_thesis_candidates,
    screen_text,
    validate_coding_against_text,
    validate_coding_record,
    validate_thesis_candidate,
    validate_thesis_readiness,
)
from .intake import intake_document, ocr_pdf_to_text, public_intake_record
from .plan import freeze_plan, validate_plan
from .casework import (
    ADVERSE_BUCKETS,
    analyze_case_relative_dynamics,
    build_adverse_review,
    build_explainable_queue,
    classify_applicant_relation,
    compare_case_features,
    prepare_casework,
    validate_normative_bridge,
    validate_position_card,
)
from .handoff_workbench import check_handoff, create_handoff, import_handoff
from .public_corpus import PublicCorpus
from .reporting import derive_research_status, write_offline_report
from .source_reconciliation import (
    promote_enumerator,
    reconcile_sources,
    validate_enumerator_manifest,
)


_QUERY_PLAN_LANE = {
    "exact_norm": "exact_norm",
    "court_language": "synonyms",
    "legal_mechanism": "mechanisms",
    "controlled_synonym": "synonyms",
    "opposite_reading": "opposite_readings",
    "narrower_reading": "opposite_readings",
    "alternative_ground": "other_grounds",
    "later_legislation": "later_authority",
    "higher_authority": "later_authority",
    "case_feature": "synonyms",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_iso_timestamp(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field} должен быть непустой датой-временем ISO.")
    try:
        datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} должен быть датой-временем ISO.") from exc
    return cleaned


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            stream.write("\n")
    temporary.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: строка {number} должна быть JSON-объектом")
        records.append(value)
    return records


def _read_records(path: Path) -> list[dict[str, Any]]:
    """Read a JSON array/object or JSONL without guessing from its contents."""

    if path.suffix.casefold() == ".jsonl":
        return read_jsonl(path)
    value = read_json(path)
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ValueError(f"{path}: JSON-массив должен содержать только объекты.")
        return list(value)
    if isinstance(value, dict):
        items = value.get("items")
        if isinstance(items, list) and all(isinstance(item, dict) for item in items):
            return list(items)
        return [value]
    raise ValueError(f"{path}: ожидался JSON-объект, массив объектов или JSONL.")


_PRE_THESIS_CASE_RELATIVE_FILES = (
    "case-fingerprint.json",
    "query-suggestions.jsonl",
    "query-decisions.jsonl",
    "supplemental-queries.jsonl",
    "queries.jsonl",
    "casework-dependencies.json",
    "case-temporal-analysis.json",
    "position-cards.jsonl",
    "case-comparison.json",
    "comparability-matrix.jsonl",
    "applicant-position.json",
    "applicant-relations.jsonl",
    "review-queue.json",
    "case-adverse-review.json",
    "source-reconciliation.json",
)

_POST_REVIEW_CASE_RELATIVE_FILES = (
    "normative-bridge.json",
)


def _case_relative_evidence_paths(
    workspace: Path, *, include_post_review: bool
) -> list[Path]:
    names = list(_PRE_THESIS_CASE_RELATIVE_FILES)
    if include_post_review:
        names.extend(_POST_REVIEW_CASE_RELATIVE_FILES)
    return [workspace / name for name in names]


def _approval_evidence_paths(workspace: Path) -> list[Path]:
    return [
        workspace / "analysis.json",
        workspace / "screening-candidates.jsonl",
        workspace / "coding-decisions.jsonl",
        workspace / "exports" / "coverage.json",
        workspace / "adverse-review.json",
        workspace / "thesis-candidates.jsonl",
        *_case_relative_evidence_paths(workspace, include_post_review=True),
    ]


def _digest_existing(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _artifact_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _pre_thesis_evidence_sha256(workspace: Path) -> str:
    return _digest_existing(
        [
            workspace / "applicant-chain.json",
            workspace / "screening-candidates.jsonl",
            workspace / "coding-decisions.jsonl",
            workspace / "exports" / "coverage.json",
            workspace / "exports" / "sources.jsonl",
            workspace / "exports" / "case-chains.jsonl",
            workspace / "adverse-review.json",
            *_case_relative_evidence_paths(workspace, include_post_review=False),
        ]
    )


def _approval_evidence_sha256(workspace: Path) -> str:
    """Hash every material artifact on which a final human approval depends."""

    return _digest_existing(_approval_evidence_paths(workspace))


def latest_plan(workspace: Path) -> dict[str, Any]:
    versions: list[tuple[int, Path]] = []
    for path in (workspace / "plans").glob("plan-v*.json"):
        try:
            versions.append((int(path.stem.split("-v", 1)[1]), path))
        except (IndexError, ValueError):
            continue
    if not versions:
        raise ValueError("Нет замороженного плана. Выполните `plan freeze`.")
    return read_json(max(versions)[1])


def iter_input_files(inputs: list[str]) -> list[Path]:
    result: list[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser()
        if path.is_dir():
            result.extend(sorted(item for item in path.rglob("*") if item.is_file()))
        else:
            result.append(path)
    deduplicated: dict[str, Path] = {}
    for path in result:
        deduplicated[str(path.resolve())] = path
    return list(deduplicated.values())


def plan_template() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Исследование судебного смысла нормы",
        "research_questions": [
            {
                "id": "rq-1",
                "status": "research_question",
                "question": "При каких сопоставимых обстоятельствах кассационные суды принимают каждый возможный исходозначимый смысл спорной нормы?",
                "norm_refs": ["УКАЖИТЕ ТОЧНУЮ НОРМУ"],
                "supported": False,
            }
        ],
        "norm_editions": [
            {
                "id": "edition-1",
                "norm_ref": "УКАЖИТЕ ТОЧНУЮ НОРМУ",
                "valid_from": "2019-10-01",
                "valid_to": None,
                "official_source_url": "УКАЖИТЕ ОФИЦИАЛЬНУЮ ССЫЛКУ",
                "edition_status": "unresolved",
            }
        ],
        "population": {
            "unit": "independent_case_chain",
            "date_from": "2019-10-01",
            "date_to": datetime.now(timezone.utc).date().isoformat(),
            "courts": ["1kas", "2kas", "3kas", "4kas", "5kas", "6kas", "7kas", "8kas", "9kas"],
            "regimes": ["ksoyu_post_2019"],
            "official_population_rule": "Все официально обнаружимые опубликованные материалы в замкнутом дневном обходе; не все рассмотренные дела.",
        },
        "temporal_strata": [],
        "interpretive_events": [],
        "query_lanes": {
            "exact_norm": [],
            "synonyms": [],
            "mechanisms": [],
            "opposite_readings": [],
            "other_grounds": [],
            "later_authority": [],
        },
        "inclusion_rules": ["УКАЖИТЕ ПРАВИЛО ВКЛЮЧЕНИЯ"],
        "exclusion_rules": ["УКАЖИТЕ ПРАВИЛО ИСКЛЮЧЕНИЯ"],
        "materiality_rule": "Смысл нормы принят судом и связан с мотивом и итогом дела.",
        "adverse_review": {
            "required": True,
            "queries": ["УКАЖИТЕ ПРОТИВОПОЛОЖНУЮ ИЛИ БОЛЕЕ УЗКУЮ ФОРМУЛИРОВКУ"],
            "no_hit_wording": "В раскрытом наблюдаемом корпусе противоположные акты не обнаружены; отсутствие в практике не доказано.",
        },
        "contradiction_rule": "Различающиеся материальные факты и самостоятельные процессуальные основания кодируются отдельно.",
        "coverage_expectation": "closed_official_population_observed",
        "maximum_claim_if_incomplete": "corroborated_observed_corpus",
        "approved_by": "УКАЖИТЕ ПРОВЕРЯЮЩЕГО",
    }


def cmd_intake(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    files = iter_input_files(args.inputs)
    if not files:
        raise ValueError("Не найдено ни одного входного файла.")
    private_records: list[dict[str, Any]] = []
    public_records: list[dict[str, Any]] = []
    objects = workspace / "objects" / "applicant"
    objects.mkdir(parents=True, exist_ok=True)
    for path in files:
        record = intake_document(path)
        record["document_id"] = "applicant-document-sha256:" + str(record["sha256"])
        record["role"] = args.role
        record["intake_at"] = utc_now()
        if record.get("sha256") and path.exists():
            destination = objects / str(record["sha256"])
            if not destination.exists():
                shutil.copyfile(path, destination)
            record["object_relpath"] = str(destination.relative_to(workspace))
        private_records.append(record)
        public_records.append(public_intake_record(record))
    write_jsonl(workspace / "intake" / "applicant-private.jsonl", private_records)
    write_jsonl(workspace / "intake" / "applicant-manifest.jsonl", public_records)
    chain = {
        "schema_version": "1.0",
        "run_id": None,
        "documents": [record.get("sha256") for record in public_records],
        "stages": [],
        "facts": [],
        "norms": [],
        "propositions": [],
        "outcomes": [],
        "unresolved": [
            "Заполните speaker и связь каждого предполагаемого смысла нормы с исходом по полному тексту актов."
        ],
    }
    write_json(workspace / "applicant-chain.json", chain)
    print(json.dumps({"workspace": str(workspace), "documents": len(files), "extracted": sum(r.get("extraction_status") == "extracted" for r in private_records), "unextractable": sum(r.get("extraction_status") != "extracted" for r in private_records)}, ensure_ascii=False))
    return 0


def cmd_ocr(args: argparse.Namespace) -> int:
    provenance = ocr_pdf_to_text(
        args.input,
        args.output,
        language=args.language,
        dpi=args.dpi,
    )
    print(json.dumps(provenance, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_plan_template(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    destination = workspace / "research-plan.json"
    if destination.exists() and not args.force:
        raise ValueError(f"{destination} уже существует; используйте --force только для осознанной замены черновика.")
    write_json(destination, plan_template())
    print(destination)
    return 0


def cmd_plan_freeze(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    plan = read_json(Path(args.plan).expanduser().resolve())
    decisions = read_jsonl(workspace / "query-decisions.jsonl")
    if decisions:
        fingerprint_path = workspace / "case-fingerprint.json"
        if not fingerprint_path.exists():
            raise ValueError("Подтверждённые запросы требуют текущего case-fingerprint.json.")
        fingerprint_sha256 = read_json(fingerprint_path).get("fingerprint_sha256")
        accepted: list[dict[str, Any]] = []
        plan = json.loads(json.dumps(plan, ensure_ascii=False))
        lanes = plan.get("query_lanes")
        if not isinstance(lanes, dict):
            raise ValueError("План не содержит query_lanes.")
        for decision in decisions:
            if decision.get("decision") != "accepted":
                continue
            suggestion = decision.get("suggestion")
            if not isinstance(suggestion, dict):
                raise ValueError("Решение по запросу не содержит исходное предложение.")
            provenance = suggestion.get("provenance")
            if not isinstance(provenance, dict) or provenance.get(
                "fingerprint_sha256"
            ) != fingerprint_sha256:
                raise ValueError(
                    "Подтверждённый запрос относится к устаревшему fingerprint; "
                    "подтвердите предложения заново."
                )
            lane = suggestion.get("lane")
            plan_lane = _QUERY_PLAN_LANE.get(str(lane))
            query = suggestion.get("query")
            if plan_lane is None or not isinstance(query, str) or not query.strip():
                raise ValueError("Подтверждённый запрос имеет неизвестную дорожку или пустой текст.")
            lane_queries = lanes.setdefault(plan_lane, [])
            if query not in lane_queries:
                lane_queries.append(query)
            accepted.append(decision)
        plan["accepted_query_suggestions"] = sorted(
            accepted, key=lambda item: str(item.get("query_id"))
        )
    frozen = freeze_plan(plan, workspace)
    print(json.dumps({"plan_sha256": frozen["plan_sha256"], "frozen": True}, ensure_ascii=False))
    return 0


def cmd_query_accept(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if not args.reviewer.strip() or not args.confirmed_at.strip():
        raise ValueError("Подтверждение запроса требует reviewer и confirmed-at.")
    _require_iso_timestamp(args.confirmed_at, "confirmed-at")
    if any((workspace / "plans").glob("plan-v*.json")):
        raise ValueError(
            "План уже заморожен; новый запрос добавляется только через query supplement."
        )
    fingerprint_path = workspace / "case-fingerprint.json"
    if not fingerprint_path.exists():
        raise ValueError("Сначала подготовьте case-fingerprint.json.")
    fingerprint_sha256 = read_json(fingerprint_path).get("fingerprint_sha256")
    suggestions = {
        str(item.get("query_id")): item
        for item in read_jsonl(workspace / "query-suggestions.jsonl")
        if item.get("query_id")
    }
    requested = list(dict.fromkeys(args.query_id))
    unknown = sorted(set(requested) - set(suggestions))
    if unknown:
        raise ValueError("Не найдены query_id: " + ", ".join(unknown) + ".")
    existing = {
        str(item.get("query_id")): item
        for item in read_jsonl(workspace / "query-decisions.jsonl")
        if item.get("query_id")
    }
    accepted: list[str] = []
    for query_id in requested:
        suggestion = suggestions[query_id]
        provenance = suggestion.get("provenance")
        if not isinstance(provenance, dict) or provenance.get(
            "fingerprint_sha256"
        ) != fingerprint_sha256:
            raise ValueError(f"Предложение {query_id} относится к устаревшему fingerprint.")
        record = {
            "schema_version": "1.0",
            "query_id": query_id,
            "decision": "accepted",
            "confirmation_state": "human_confirmed",
            "plan_relationship": "accepted_pre_freeze",
            "reviewer": args.reviewer.strip(),
            "confirmed_at": args.confirmed_at.strip(),
            "suggestion": suggestion,
        }
        existing[query_id] = record
        accepted.append(query_id)
    write_jsonl(
        workspace / "query-decisions.jsonl",
        [existing[key] for key in sorted(existing)],
    )
    _print_json(
        {
            "schema_version": "1.0",
            "accepted_query_ids": accepted,
            "next_action": "Заморозьте план; точный текст и provenance войдут в plan hash.",
        }
    )
    return 0


def cmd_query_supplement(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if not args.reviewer.strip() or not args.confirmed_at.strip():
        raise ValueError("Supplemental-запрос требует reviewer и confirmed-at.")
    _require_iso_timestamp(args.confirmed_at, "confirmed-at")
    plan = latest_plan(workspace)
    lane = args.lane.strip()
    if lane not in _QUERY_PLAN_LANE:
        raise ValueError("Неизвестная дорожка supplemental-запроса.")
    query = " ".join(args.query.split())
    reason = " ".join(args.reason.split())
    if not query or not reason:
        raise ValueError("Supplemental-запрос требует непустые query и reason.")
    fingerprint_path = workspace / "case-fingerprint.json"
    if not fingerprint_path.exists():
        raise ValueError("Supplemental-запрос требует текущий case-fingerprint.json.")
    fingerprint_sha256 = read_json(fingerprint_path).get("fingerprint_sha256")
    seed = {
        "plan_sha256": plan.get("plan_sha256"),
        "fingerprint_sha256": fingerprint_sha256,
        "lane": lane,
        "query": query,
        "reason": reason,
    }
    query_id = "supplemental-" + _artifact_sha256(seed)[:16]
    record = {
        "schema_version": "1.0",
        "query_id": query_id,
        **seed,
        "plan_lane": _QUERY_PLAN_LANE[lane],
        "confirmation_state": "human_confirmed",
        "plan_relationship": "post_freeze_supplemental",
        "changes_original_denominator": False,
        "reviewer": args.reviewer.strip(),
        "confirmed_at": args.confirmed_at.strip(),
    }
    existing = {
        str(item.get("query_id")): item
        for item in read_jsonl(workspace / "supplemental-queries.jsonl")
        if item.get("query_id")
    }
    if query_id in existing and existing[query_id] != record:
        raise ValueError("Коллизия supplemental query_id.")
    existing[query_id] = record
    write_jsonl(
        workspace / "supplemental-queries.jsonl",
        [existing[key] for key in sorted(existing)],
    )
    execution_records = {
        str(item.get("query_id")): item
        for item in read_jsonl(workspace / "queries.jsonl")
        if item.get("query_id")
    }
    execution_records[query_id] = record
    write_jsonl(
        workspace / "queries.jsonl",
        [execution_records[key] for key in sorted(execution_records)],
    )
    _print_json(record)
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    from .collection import run_collection

    result = run_collection(
        Path(args.workspace).expanduser().resolve(),
        resume=args.resume,
        max_tasks=args.max_tasks,
        max_attempts=args.max_attempts,
        max_source_tasks=args.max_source_tasks,
        fixture_dir=Path(args.fixture_dir).resolve() if args.fixture_dir else None,
        retry_now=args.retry_now,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not result.get("fatal") else 2


def _candidate_texts(workspace: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    exports = workspace / "exports" / "sources.jsonl"
    for record in read_jsonl(exports):
        if record.get("kind") != "doc":
            continue
        inline_text = record.get("text")
        if isinstance(inline_text, str) and inline_text.strip():
            candidates.append({**record, "text": inline_text})
            continue
        relpath = record.get("text_relpath")
        if not relpath:
            continue
        path = workspace / relpath
        if path.exists():
            candidates.append({**record, "text": path.read_text(encoding="utf-8", errors="replace")})
    return candidates


def cmd_screen(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    plan = latest_plan(workspace)
    records: list[dict[str, Any]] = []
    for source in _candidate_texts(workspace):
        matches = screen_text(source["text"], plan["query_lanes"])
        if matches:
            records.append(
                {
                    "source_id": source.get("source_id"),
                    "document_id": source.get("document_id"),
                    "chain_id": source.get("chain_id"),
                    "matches": matches,
                    "status": "candidate_needs_full_text_review",
                }
            )
    write_jsonl(workspace / "screening-candidates.jsonl", records)
    print(json.dumps({"candidates": len(records)}, ensure_ascii=False))
    return 0


def cmd_code(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    destination = workspace / "coding-decisions.jsonl"
    if not args.input:
        templates = []
        for candidate in read_jsonl(workspace / "screening-candidates.jsonl"):
            templates.append(
                {
                    "chain_id": candidate.get("chain_id"),
                    "document_id": candidate.get("document_id"),
                    "court_code": candidate.get("court_code"),
                    "decision_date": None,
                    "label": "unclear",
                    "speaker": None,
                    "proposition": None,
                    "quote": None,
                    "quote_locator": None,
                    "quote_verified": False,
                    "full_text_reviewed": False,
                    "norm_edition_id": None,
                    "material_facts": [],
                    "material_facts_group": None,
                    "comparability_approved": False,
                    "reasoning_to_outcome": None,
                    "alternative_grounds": [],
                    "remedy": None,
                    "reading_family": None,
                    "relation": None,
                    "coder": None,
                    "human_review": "pending",
                    "codebook_version": "1.0",
                }
            )
        write_jsonl(destination, templates)
        print(destination)
        return 0
    records = read_jsonl(Path(args.input).resolve())
    full_text_by_document = {
        source.get("document_id"): source["text"] for source in _candidate_texts(workspace)
    }
    invalid = []
    for index, record in enumerate(records, 1):
        errors = validate_coding_against_text(
            record, full_text_by_document.get(record.get("document_id"), "")
        )
        if errors:
            invalid.append({"index": index, "errors": errors})
    if invalid:
        write_json(workspace / "validation" / "coding-errors.json", invalid)
        raise ValueError(f"Не прошли проверку {len(invalid)} карточек кодирования.")
    write_jsonl(destination, records)
    print(json.dumps({"approved_records": len(records)}, ensure_ascii=False))
    return 0


def screening_resolution_complete(
    screening_candidates: list[dict[str, Any]],
    coding_records: list[dict[str, Any]],
) -> bool:
    """Require one valid reviewed resolution for every screened chain/document pair."""

    if not screening_candidates or not coding_records:
        return False
    required: set[tuple[str, str]] = set()
    for candidate in screening_candidates:
        chain_id = candidate.get("chain_id")
        document_id = candidate.get("document_id")
        if not isinstance(chain_id, str) or not chain_id.strip():
            return False
        if not isinstance(document_id, str) or not document_id.strip():
            return False
        required.add((chain_id.strip(), document_id.strip()))
    if any(validate_coding_record(record) for record in coding_records):
        return False
    resolved = {
        (str(record["chain_id"]).strip(), str(record["document_id"]).strip())
        for record in coding_records
    }
    return required.issubset(resolved)


def cmd_analyze(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    records = read_jsonl(workspace / "coding-decisions.jsonl")
    screening_candidates = read_jsonl(workspace / "screening-candidates.jsonl")
    coding_resolution_complete = screening_resolution_complete(screening_candidates, records)
    plan = latest_plan(workspace)
    coverage_path = workspace / "exports" / "coverage.json"
    coverage = read_json(coverage_path) if coverage_path.exists() else {"population_status": "insufficient_coverage"}
    coverage_status = (
        coverage.get("population_status", "insufficient_coverage")
        if coverage.get("collection_complete") is True
        else "insufficient_coverage"
    )
    result = analyze_reviewed_chains(
        records,
        coverage_status=coverage_status,
        temporal_strata=plan.get("temporal_strata"),
        interpretive_events=plan.get("interpretive_events"),
    )
    result["plan_sha256"] = plan.get("plan_sha256")
    result["practice_is_evidence_of_meaning_not_review_object"] = True
    result["screening_resolution_complete"] = coding_resolution_complete
    applicant_chain_path = workspace / "applicant-chain.json"
    applicant_chain = read_json(applicant_chain_path) if applicant_chain_path.exists() else {"propositions": []}
    run_metadata_path = workspace / "run.json"
    run_metadata = read_json(run_metadata_path) if run_metadata_path.exists() else {}
    run_id = run_metadata.get("run_id") or applicant_chain.get("run_id")
    adverse_path = workspace / "adverse-review.json"
    if not adverse_path.exists():
        write_json(
            adverse_path,
            {
                "schema_version": "1.0",
                "run_id": run_id,
                "lanes": ["adverse", "opposite_readings", "other_grounds", "later_authority"],
                "queries": plan.get("adverse_review", {}).get("queries", []),
                "completed": False,
                "reviewer": None,
                "results": [],
                "limitations": [
                    plan.get("adverse_review", {}).get(
                        "no_hit_wording",
                        "Ноль находок относится только к раскрытому наблюдаемому корпусу.",
                    )
                ],
            },
        )
    adverse = read_json(adverse_path)
    evidence_decision_path = workspace / "human-decision.json"
    evidence_decision = read_json(evidence_decision_path) if evidence_decision_path.exists() else {}
    evidence_review_complete = bool(
        evidence_decision.get("decision") in {"evidence_reviewed", "approved"}
        and evidence_decision.get("plan_sha256") == plan.get("plan_sha256")
        and evidence_decision.get("pre_thesis_evidence_sha256")
        == _pre_thesis_evidence_sha256(workspace)
        and evidence_decision.get("adverse_review_complete") is True
        and evidence_decision.get("coverage_review_complete") is True
        and adverse.get("completed") is True
        and adverse.get("queries")
        and coding_resolution_complete
    )
    candidates = (
        build_thesis_candidates(plan, applicant_chain, records, result)
        if evidence_review_complete
        else []
    )
    write_jsonl(workspace / "thesis-candidates.jsonl", candidates)
    result["thesis_candidate_count"] = len(candidates)
    result["evidence_review_complete"] = evidence_review_complete
    result["thesis_gate"] = (
        "post_evidence_review_candidates_created"
        if evidence_review_complete
        else "blocked_pending_adverse_and_coverage_review"
    )
    write_json(workspace / "analysis.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    plan = latest_plan(workspace)
    candidates: list[dict[str, Any]] = []
    fingerprint_exists = (workspace / "case-fingerprint.json").exists()
    case_adverse_path = workspace / "case-adverse-review.json"
    case_adverse = read_json(case_adverse_path) if case_adverse_path.exists() else {}
    if args.thesis_file:
        candidates = read_jsonl(Path(args.thesis_file).expanduser().resolve())
    adverse: dict[str, Any] = {}
    if args.adverse_file:
        adverse = read_json(Path(args.adverse_file).expanduser().resolve())
        write_json(workspace / "adverse-review.json", adverse)
    elif (workspace / "adverse-review.json").exists():
        adverse = read_json(workspace / "adverse-review.json")
    elif fingerprint_exists and case_adverse.get("completed") is True:
        executed_query_ids = sorted(
            {
                query_id
                for bucket in case_adverse.get("bucket_reviews", {}).values()
                if isinstance(bucket, dict)
                for query_id in bucket.get("executed_query_ids", [])
                if isinstance(query_id, str) and query_id.strip()
            }
        )
        adverse = {
            "schema_version": "1.0",
            "completed": True,
            "queries": executed_query_ids,
            "reviewer": args.reviewer,
            "source_artifact": "case-adverse-review.json",
            "limitations": [case_adverse.get("no_hit_wording")],
        }
        write_json(workspace / "adverse-review.json", adverse)
    if args.adverse_complete:
        if not adverse or adverse.get("completed") is not True or not adverse.get("queries"):
            raise ValueError("Завершённый adverse review требует completed=true и раскрытых queries.")
        if not adverse.get("reviewer"):
            raise ValueError("В завершённом adverse review укажите reviewer.")
    if args.decision == "evidence_reviewed":
        if not args.adverse_complete or not args.coverage_complete:
            raise ValueError("Evidence review требует завершённых adverse и coverage review.")
        if args.thesis_file:
            raise ValueError("На стадии evidence_reviewed тезис ещё не передаётся.")
    if args.decision == "approved":
        if not args.adverse_complete or not args.coverage_complete:
            raise ValueError("Одобрение требует завершённых adverse и coverage review.")
        if not candidates:
            raise ValueError("Для одобрения нужен --thesis-file с post-corpus кандидатом.")
        prior_decision_path = workspace / "human-decision.json"
        prior_decision = read_json(prior_decision_path) if prior_decision_path.exists() else {}
        if not (
            prior_decision.get("decision") == "evidence_reviewed"
            and prior_decision.get("plan_sha256") == plan.get("plan_sha256")
            and prior_decision.get("pre_thesis_evidence_sha256")
            == _pre_thesis_evidence_sha256(workspace)
        ):
            raise ValueError(
                "Сначала нужен актуальный review --decision evidence_reviewed, затем повторный analyze."
            )
        candidate_errors = [
            {"candidate_id": candidate.get("candidate_id"), "errors": validate_thesis_candidate(candidate)}
            for candidate in candidates
            if validate_thesis_candidate(candidate)
        ]
        if candidate_errors:
            write_json(workspace / "validation" / "thesis-errors.json", candidate_errors)
            raise ValueError(f"Не прошли проверку {len(candidate_errors)} кандидатов тезиса.")
        if fingerprint_exists:
            pre_state = _validation_state(workspace)
            required_case_gates = {
                "case_fingerprint_ready": "отпечаток дела",
                "collection_complete": "сбор корпуса",
                "coding_complete": "полнотекстовое кодирование",
                "comparison_review_complete": "сопоставимость дел",
                "applicant_relation_complete": "отношение позиций к делу заявителя",
                "adverse_review_complete": "неблагоприятная практика",
                "coverage_review_complete": "охват корпуса",
                "normative_bridge_complete": "нормативный мост",
                "analysis_complete": "корпусный анализ",
                "temporal_analysis_complete": "анализ динамики по временным стратам",
            }
            blocked = [
                label
                for field, label in required_case_gates.items()
                if pre_state.get(field) is not True
            ]
            if blocked:
                raise ValueError(
                    "Одобрение заблокировано до завершения: " + ", ".join(blocked) + "."
                )
        for candidate in candidates:
            candidate["drafting_ready"] = True
        write_jsonl(workspace / "thesis-candidates.jsonl", candidates)

    decision = {
        "schema_version": "1.0",
        "decision": args.decision,
        "reviewer": args.reviewer,
        "plan_sha256": plan["plan_sha256"],
        "evidence_sha256": _approval_evidence_sha256(workspace),
        "pre_thesis_evidence_sha256": _pre_thesis_evidence_sha256(workspace),
        "adverse_review_complete": args.adverse_complete,
        "coverage_review_complete": args.coverage_complete,
        "decided_at": utc_now(),
        "notes": args.notes,
        "candidate_ids": [candidate.get("candidate_id") for candidate in candidates],
    }
    write_json(workspace / "human-decision.json", decision)
    print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    return 0


def _validation_state(workspace: Path) -> dict[str, Any]:
    plan = latest_plan(workspace)
    coverage_path = workspace / "exports" / "coverage.json"
    coverage = read_json(coverage_path) if coverage_path.exists() else {}
    coding = read_jsonl(workspace / "coding-decisions.jsonl")
    screening = read_jsonl(workspace / "screening-candidates.jsonl")
    decision_path = workspace / "human-decision.json"
    decision = read_json(decision_path) if decision_path.exists() else {}
    analysis_path = workspace / "analysis.json"
    analysis = read_json(analysis_path) if analysis_path.exists() else {}
    case_temporal_path = workspace / "case-temporal-analysis.json"
    case_temporal = read_json(case_temporal_path) if case_temporal_path.exists() else {}
    fingerprint_path = workspace / "case-fingerprint.json"
    fingerprint = read_json(fingerprint_path) if fingerprint_path.exists() else {}
    fingerprint_sha256 = fingerprint.get("fingerprint_sha256")
    case_temporal_path = workspace / "case-temporal-analysis.json"
    case_temporal = read_json(case_temporal_path) if case_temporal_path.exists() else {}
    case_temporal_current = bool(case_temporal) and (
        case_temporal.get("fingerprint_sha256") == fingerprint_sha256
        and case_temporal.get("temporal_analysis_complete") is True
    )
    case_dependencies_path = workspace / "casework-dependencies.json"
    case_dependencies = (
        read_json(case_dependencies_path) if case_dependencies_path.exists() else {}
    )
    missing_tasks = case_dependencies.get("missing_tasks", [])
    if not isinstance(missing_tasks, list):
        missing_tasks = []
    blocking_case_tasks = [
        task
        for task in missing_tasks
        if isinstance(task, dict) and task.get("blocks_comparability") is True
    ]
    features = fingerprint.get("features", [])
    fingerprint_payload_features = []
    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, dict):
                fingerprint_payload_features.append(
                    {key: value for key, value in feature.items() if key != "revision"}
                )
    expected_fingerprint_sha256 = _artifact_sha256(
        {
            "schema_version": fingerprint.get("schema_version"),
            "issue": fingerprint.get("issue"),
            "norm_refs": fingerprint.get("norm_refs"),
            "features": fingerprint_payload_features,
        }
    )
    feature_ids = {
        str(feature.get("feature_id"))
        for feature in features
        if isinstance(feature, dict) and feature.get("feature_id")
    } if isinstance(features, list) else set()
    required_case_fields = {
        "norm_edition",
        "applicant_case_meaning",
        "procedural_posture",
    }
    intake_manifest = read_jsonl(workspace / "intake" / "applicant-manifest.jsonl")
    applicant_document_ids = {
        str(identifier)
        for record in intake_manifest
        for identifier in (
            record.get("document_id"),
            record.get("sha256"),
            (
                "applicant-document-sha256:" + str(record.get("sha256"))
                if record.get("sha256")
                else None
            ),
        )
        if isinstance(identifier, str) and identifier
    }
    document_sources_bound = all(
        isinstance(feature, dict)
        and (
            feature.get("status") != "verified"
            or (
                isinstance(feature.get("source"), dict)
                and (
                    (
                        feature["source"].get("source_type") == "user_decision"
                        and isinstance(feature["source"].get("decision_id"), str)
                        and bool(feature["source"]["decision_id"].strip())
                    )
                    or (
                        feature["source"].get("source_type") != "user_decision"
                        and feature["source"].get("document_id")
                        in applicant_document_ids
                        and isinstance(feature["source"].get("quote_locator"), str)
                        and bool(feature["source"]["quote_locator"].strip())
                    )
                )
            )
        )
        for feature in features
    ) if isinstance(features, list) else False
    case_fingerprint_ready = (
        bool(fingerprint_sha256)
        and fingerprint_sha256 == expected_fingerprint_sha256
        and isinstance(fingerprint.get("issue"), str)
        and bool(fingerprint["issue"].strip())
        and isinstance(fingerprint.get("norm_refs"), list)
        and bool(fingerprint["norm_refs"])
        and all(
            isinstance(item, str) and bool(item.strip())
            for item in fingerprint["norm_refs"]
        )
        and case_dependencies_path.exists()
        and case_dependencies.get("dependency_state", {}).get(
            "current_fingerprint_sha256"
        )
        == fingerprint_sha256
        and isinstance(features, list)
        and bool(features)
        and required_case_fields.issubset(feature_ids)
        and bool(applicant_document_ids)
        and document_sources_bound
        and not blocking_case_tasks
        and all(
        isinstance(feature, dict)
        and (
            feature.get("material") is not True
            or feature.get("status") == "verified"
        )
        for feature in features
        )
    )
    position_cards = read_jsonl(workspace / "position-cards.jsonl")
    cards_by_id = {
        str(card.get("position_card_id")): card
        for card in position_cards
        if card.get("position_card_id")
    }
    direct_card_ids = {
        card_id
        for card_id, card in cards_by_id.items()
        if not validate_position_card(card)
    }
    position_cards_valid = (
        bool(position_cards)
        and len(cards_by_id) == len(position_cards)
        and len(direct_card_ids) == len(cards_by_id)
    )
    fingerprint_features = fingerprint.get("features", [])
    applicant_features_sha256 = (
        _artifact_sha256(_comparison_feature_payload(fingerprint_features))
        if isinstance(fingerprint_features, list) and fingerprint_features
        else None
    )
    comparisons = read_jsonl(workspace / "comparability-matrix.jsonl")
    comparisons_by_id = {
        str(item.get("position_card_id")): item
        for item in comparisons
        if item.get("position_card_id")
    }
    current_comparison_ids = {
        card_id
        for card_id, comparison in comparisons_by_id.items()
        if card_id in cards_by_id
        if comparison.get("status") in {"matched", "distinguishable"}
        and comparison.get("fingerprint_sha256") == fingerprint_sha256
        and comparison.get("applicant_features_sha256")
        == applicant_features_sha256
        and comparison.get("candidate_features_sha256")
        == _artifact_sha256(
            _comparison_feature_payload(
                cards_by_id[card_id].get("comparison_features", [])
            )
        )
        and comparison.get("position_card_sha256")
        == _artifact_sha256(cards_by_id[card_id])
        and isinstance(comparison.get("review_provenance"), dict)
        and comparison["review_provenance"].get("status") == "approved"
    }
    comparison_binding_diagnostics = {
        card_id: {
            "fingerprint": comparison.get("fingerprint_sha256")
            == fingerprint_sha256,
            "applicant_features": comparison.get("applicant_features_sha256")
            == applicant_features_sha256,
            "candidate_features": comparison.get("candidate_features_sha256")
            == _artifact_sha256(
                _comparison_feature_payload(
                    cards_by_id.get(card_id, {}).get("comparison_features", [])
                )
            ),
            "position_card": comparison.get("position_card_sha256")
            == _artifact_sha256(cards_by_id.get(card_id, {})),
            "human_review": isinstance(comparison.get("review_provenance"), dict)
            and comparison["review_provenance"].get("status") == "approved",
        }
        for card_id, comparison in comparisons_by_id.items()
    }
    comparison_review_complete = position_cards_valid and direct_card_ids.issubset(
        current_comparison_ids
    )
    relations = read_jsonl(workspace / "applicant-relations.jsonl")
    relations_by_id = {
        str(item.get("position_card_id")): item
        for item in relations
        if item.get("position_card_id")
    }
    applicant_position_path = workspace / "applicant-position.json"
    applicant_position = (
        read_json(applicant_position_path) if applicant_position_path.exists() else {}
    )
    applicant_position_sha256 = (
        _artifact_sha256(applicant_position) if applicant_position else None
    )
    current_relation_ids = {
        card_id
        for card_id, relation in relations_by_id.items()
        if card_id in cards_by_id and card_id in comparisons_by_id
        if relation.get("relation")
        in {"supports", "adverse", "distinguishes", "neutral"}
        and relation.get("stale") is not True
        and relation.get("fingerprint_sha256") == fingerprint_sha256
        and relation.get("position_card_sha256")
        == _artifact_sha256(cards_by_id[card_id])
        and relation.get("comparison_id")
        == comparisons_by_id[card_id].get("comparison_id")
        and relation.get("comparison_sha256")
        == _artifact_sha256(comparisons_by_id[card_id])
        and relation.get("applicant_position_sha256")
        == applicant_position_sha256
        and relation.get("human_review") == "approved"
    }
    applicant_relation_complete = position_cards_valid and direct_card_ids.issubset(
        current_relation_ids
    )
    case_adverse_path = workspace / "case-adverse-review.json"
    case_adverse = read_json(case_adverse_path) if case_adverse_path.exists() else {}
    case_adverse_complete = case_adverse.get("completed") is True
    maximum_claim = analysis.get(
        "status", plan.get("maximum_claim_if_incomplete", "unproven_research_question")
    )
    bridge_path = workspace / "normative-bridge.json"
    bridge = read_json(bridge_path) if bridge_path.exists() else {}
    bridge_errors = validate_normative_bridge(
        bridge,
        current_fingerprint_sha256=(
            fingerprint_sha256 if isinstance(fingerprint_sha256, str) else None
        ),
        maximum_permitted_claim=(
            maximum_claim if isinstance(maximum_claim, str) else None
        ),
        position_cards=cards_by_id,
        comparisons=comparisons_by_id,
        applicant_relations=relations_by_id,
        adverse_review=case_adverse,
    )
    normative_bridge_complete = bridge_path.exists() and not bridge_errors
    queue_path = workspace / "review-queue.json"
    queue = read_json(queue_path) if queue_path.exists() else {}
    unresolved_queue = queue.get("unresolved_candidate_ids", [])
    if not isinstance(unresolved_queue, list):
        unresolved_queue = []
    stale_artifacts: list[str] = []
    if case_dependencies.get("dependency_state", {}).get(
        "applicant_relative_evidence_stale"
    ) is True:
        stale_artifacts.extend(
            [
                "comparability-matrix.jsonl",
                "applicant-relations.jsonl",
                "normative-bridge.json",
                "human-decision.json",
                "report/manifest.json",
                "handoffs",
            ]
        )
    if any(
        comparison.get("fingerprint_sha256") != fingerprint_sha256
        for comparison in comparisons_by_id.values()
    ):
        stale_artifacts.append("comparability-matrix.jsonl")
    if any(
        relation.get("fingerprint_sha256") != fingerprint_sha256
        or relation.get("stale") is True
        for relation in relations_by_id.values()
    ):
        stale_artifacts.append("applicant-relations.jsonl")
    if bridge_path.exists() and bridge.get("fingerprint_sha256") != fingerprint_sha256:
        stale_artifacts.append("normative-bridge.json")
    if case_temporal_path.exists() and not case_temporal_current:
        stale_artifacts.append("case-temporal-analysis.json")
    if position_cards and not position_cards_valid:
        stale_artifacts.append("position-cards.jsonl")
    candidates = read_jsonl(workspace / "thesis-candidates.jsonl")
    candidate_approved = bool(candidates) and all(
        not validate_thesis_candidate(candidate) and candidate.get("drafting_ready") is True
        for candidate in candidates
    )
    current_evidence_sha256 = _approval_evidence_sha256(workspace)
    approval_hashes_match = bool(decision) and decision.get("plan_sha256") == plan.get(
        "plan_sha256"
    ) and decision.get("evidence_sha256") == current_evidence_sha256
    validation_path = workspace / "validation-report.json"
    validation = read_json(validation_path) if validation_path.exists() else {}
    validation_current = bool(validation) and validation.get("valid") is True and (
        validation.get("plan_sha256") == plan.get("plan_sha256")
        and validation.get("evidence_sha256") == current_evidence_sha256
        and validation.get("fingerprint_sha256") == fingerprint_sha256
    )
    if validation_path.exists() and not validation_current:
        stale_artifacts.append("validation-report.json")
    pending_task_counts = {
        "case_facts": len(blocking_case_tasks),
        "screening": max(len(screening) - len(coding), 0),
        "review_queue": len(unresolved_queue),
        "comparisons": len(direct_card_ids - current_comparison_ids)
        + max(len(position_cards) - len(direct_card_ids), 0),
        "applicant_relations": len(direct_card_ids - current_relation_ids)
        + max(len(position_cards) - len(direct_card_ids), 0),
        "adverse_buckets": len(case_adverse.get("missing_buckets", ADVERSE_BUCKETS)),
    }
    return {
        "case_fingerprint_ready": case_fingerprint_ready,
        "plan_frozen": plan.get("frozen") is True,
        "collection_complete": coverage.get("collection_complete") is True,
        "coding_complete": screening_resolution_complete(screening, coding),
        "comparison_review_complete": comparison_review_complete,
        "applicant_relation_complete": applicant_relation_complete,
        "adverse_review_complete": case_adverse_complete
        and decision.get("adverse_review_complete") is True,
        "coverage_review_complete": decision.get("coverage_review_complete") is True,
        "normative_bridge_complete": normative_bridge_complete,
        "normative_bridge_errors": bridge_errors,
        "analysis_complete": bool(analysis) or case_temporal_current,
        "human_approved": decision.get("decision") == "approved" and approval_hashes_match,
        "candidate_approved": candidate_approved and approval_hashes_match,
        "approval_hashes_match": approval_hashes_match,
        "maximum_permitted_claim": maximum_claim,
        "temporal_analysis_complete": case_temporal_current
        or analysis.get("temporal_analysis_complete") is True,
        "validation_current": validation_current,
        "pending_task_counts": pending_task_counts,
        "stale_artifacts": sorted(set(stale_artifacts)),
        "binding_diagnostics": {
            "comparisons": comparison_binding_diagnostics,
        },
    }


def cmd_validate(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    plan = latest_plan(workspace)
    errors = validate_plan({key: value for key, value in plan.items() if key not in {"frozen", "plan_sha256"}})
    state = _validation_state(workspace)
    case_relative = (workspace / "case-fingerprint.json").exists()
    if case_relative:
        required = {
            "case_fingerprint_ready": "Не готов отпечаток дела заявителя.",
            "collection_complete": "Не завершён сбор корпуса.",
            "coding_complete": "Не завершено полнотекстовое кодирование.",
            "comparison_review_complete": "Не завершена проверка сопоставимости.",
            "applicant_relation_complete": "Не завершена applicant-relative классификация.",
            "adverse_review_complete": "Не завершён adverse workbench.",
            "coverage_review_complete": "Не завершена проверка охвата.",
            "normative_bridge_complete": "Не прошёл проверку нормативный мост.",
            "analysis_complete": "Не выполнен корпусный анализ.",
            "temporal_analysis_complete": "Не выполнен анализ динамики по временным стратам.",
            "human_approved": "Нет текущего человеческого одобрения.",
            "candidate_approved": "Нет текущего одобренного кандидата тезиса.",
            "approval_hashes_match": "Хеши одобрения устарели.",
        }
        errors.extend(message for field, message in required.items() if state.get(field) is not True)
        errors.extend(state.get("normative_bridge_errors", []))
    if args.require_thesis_ready or case_relative:
        bridge_path = workspace / "normative-bridge.json"
        bridge = read_json(bridge_path) if bridge_path.exists() else {}
        proposed = (
            args.thesis
            or bridge.get("claim_wording")
            or "В наблюдаемом корпусе выявлен раскрытый в отчёте судебный смысл нормы."
        )
        errors.extend(validate_thesis_readiness(state, proposed))
    fingerprint_path = workspace / "case-fingerprint.json"
    fingerprint = read_json(fingerprint_path) if fingerprint_path.exists() else {}
    report = {
        "schema_version": "1.0",
        "valid": not errors,
        "errors": errors,
        "state": state,
        "plan_sha256": plan.get("plan_sha256"),
        "fingerprint_sha256": fingerprint.get("fingerprint_sha256"),
        "evidence_sha256": _approval_evidence_sha256(workspace),
        "validated_at": utc_now(),
    }
    write_json(workspace / "validation-report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 2


def cmd_export(args: argparse.Namespace) -> int:
    from .store import RunStore

    workspace = Path(args.workspace).expanduser().resolve()
    store = RunStore(workspace)
    try:
        paths = [
            str(store.export_jsonl(table))
            for table in ("listing_tasks", "source_tasks", "sources", "snapshots", "events")
        ]
        run_id = args.run_id or store.latest_run_id()
        if not run_id:
            raise ValueError("Нет исследовательского запуска для экспорта.")
        paths.append(str(store.export_case_chains(run_id)))
        coverage = store.coverage_report(run_id)
        source_acquisition = store.source_task_report(run_id)
        coverage["collection_complete"] = bool(
            coverage["closed_official_population_observed"]
            and source_acquisition["unresolved"] == 0
        )
        coverage["source_acquisition"] = source_acquisition
        write_json(workspace / "exports" / "coverage.json", coverage)
    finally:
        store.close()
    print(json.dumps({"exports": paths}, ensure_ascii=False))
    return 0


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _case_answers(args: argparse.Namespace) -> dict[str, Any]:
    if args.answers:
        value = read_json(Path(args.answers).expanduser().resolve())
        if not isinstance(value, dict):
            raise ValueError("--answers должен содержать JSON-объект.")
        return value
    if not sys.stdin.isatty():
        raise ValueError(
            "В неинтерактивном режиме укажите --answers с JSON-ответами по делу."
        )
    issue = input("Юридический вопрос: ").strip()
    norm_refs = [item.strip() for item in input("Спорные нормы через запятую: ").split(",")]
    features = json.loads(input("Материальные признаки как JSON-массив: "))
    return {"issue": issue, "norm_refs": norm_refs, "features": features}


def cmd_case_prepare(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    answers = _case_answers(args)
    manifest_path = workspace / "intake" / "applicant-manifest.jsonl"
    private_path = workspace / "intake" / "applicant-private.jsonl"
    manifest = read_jsonl(manifest_path)
    private_records = read_jsonl(private_path)
    if not manifest:
        raise ValueError(
            "Сначала выполните intake актов заявителя: fingerprint нельзя "
            "подтвердить по произвольному JSON без инвентаризированного документа."
        )
    allowed_document_ids: set[str] = set()
    text_by_id: dict[str, str] = {}
    for record in manifest:
        identifiers = {
            record.get("document_id"),
            record.get("sha256"),
            (
                "applicant-document-sha256:" + str(record.get("sha256"))
                if record.get("sha256")
                else None
            ),
        }
        allowed_document_ids.update(
            str(item) for item in identifiers if isinstance(item, str) and item
        )
    for record in private_records:
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        identifiers = {
            record.get("document_id"),
            record.get("sha256"),
            (
                "applicant-document-sha256:" + str(record.get("sha256"))
                if record.get("sha256")
                else None
            ),
        }
        for identifier in identifiers:
            if isinstance(identifier, str) and identifier:
                text_by_id[identifier] = text
    previous_path = workspace / "case-fingerprint.json"
    previous = read_json(previous_path) if previous_path.exists() else None
    result = prepare_casework(
        issue=answers.get("issue", ""),
        norm_refs=answers.get("norm_refs", []),
        features=answers.get("features", []),
        previous_fingerprint=previous,
        query_axes=answers.get("query_axes"),
        allowed_document_ids=allowed_document_ids,
        document_text_by_id=text_by_id,
        required_feature_ids=(
            "norm_edition",
            "applicant_case_meaning",
            "procedural_posture",
        ),
    )
    revision = int(result["fingerprint"]["revision"])
    revision_path = (
        workspace
        / "casework"
        / "fingerprints"
        / f"fingerprint-v{revision}.json"
    )
    if revision_path.exists():
        if read_json(revision_path) != result["fingerprint"]:
            raise ValueError(
                "Коллизия версии отпечатка дела: существующий файл отличается."
            )
    else:
        write_json(revision_path, result["fingerprint"])
    write_json(previous_path, result["fingerprint"])
    write_jsonl(workspace / "query-suggestions.jsonl", result["query_suggestions"])
    write_json(
        workspace / "casework-dependencies.json",
        {
            "schema_version": result.get("schema_version", "1.0"),
            "missing_tasks": result.get("missing_tasks", []),
            "dependency_state": result.get("dependency_state", {}),
        },
    )
    dependency = result.get("dependency_state", {})
    _print_json(
        {
            "workspace": str(workspace),
            "fingerprint_sha256": result["fingerprint"]["fingerprint_sha256"],
            "fingerprint_revision": result["fingerprint"]["revision"],
            "query_count": len(result["query_suggestions"]),
            "missing_task_count": len(result.get("missing_tasks", [])),
            "applicant_relative_evidence_stale": dependency.get(
                "applicant_relative_evidence_stale", False
            ),
            "next_action": (
                "Уточните missing tasks до проверки сопоставимости."
                if result.get("missing_tasks")
                else "Просмотрите suggested_unconfirmed запросы и перенесите только одобренные в замораживаемый план."
            ),
        }
    )
    return 0


def cmd_case_dynamics(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    fingerprint_path = workspace / "case-fingerprint.json"
    if not fingerprint_path.exists():
        raise ValueError("Сначала подготовьте case-fingerprint.json.")
    fingerprint = read_json(fingerprint_path)
    fingerprint_sha256 = fingerprint.get("fingerprint_sha256")
    if not isinstance(fingerprint_sha256, str):
        raise ValueError("Fingerprint не содержит fingerprint_sha256.")
    cards = read_jsonl(workspace / "position-cards.jsonl")
    comparisons = {
        str(item.get("position_card_id")): item
        for item in read_jsonl(workspace / "comparability-matrix.jsonl")
        if item.get("position_card_id")
    }
    relations = {
        str(item.get("position_card_id")): item
        for item in read_jsonl(workspace / "applicant-relations.jsonl")
        if item.get("position_card_id")
    }
    try:
        plan = latest_plan(workspace)
    except ValueError:
        plan = {}
    strata = plan.get("temporal_strata", [])
    if not isinstance(strata, list):
        raise ValueError("temporal_strata замороженного плана должны быть массивом.")
    result = analyze_case_relative_dynamics(
        cards,
        comparisons,
        relations,
        fingerprint_sha256=fingerprint_sha256,
        temporal_strata=strata,
    )
    write_json(workspace / "case-temporal-analysis.json", result)
    _print_json(result)
    return 0 if result.get("temporal_analysis_complete") else 2


def _upsert_position_card(workspace: Path, card: Mapping[str, Any]) -> None:
    destination = workspace / "position-cards.jsonl"
    cards = read_jsonl(destination)
    by_id = {
        str(item.get("position_card_id")): item
        for item in cards
        if item.get("position_card_id")
    }
    by_id[str(card["position_card_id"])] = dict(card)
    write_jsonl(
        destination,
        [by_id[identifier] for identifier in sorted(by_id)],
    )


def cmd_position_check(args: argparse.Namespace) -> int:
    card = read_json(Path(args.input).expanduser().resolve())
    if not isinstance(card, dict):
        raise ValueError("Карточка позиции должна быть JSON-объектом.")
    errors = validate_position_card(card)
    result = {
        "schema_version": "1.0",
        "position_card_id": card.get("position_card_id"),
        "valid": not errors,
        "errors": errors,
    }
    if not errors and args.workspace:
        _upsert_position_card(Path(args.workspace).expanduser().resolve(), card)
    _print_json(result)
    return 0 if not errors else 2


def _feature_list(path: Path) -> list[dict[str, Any]]:
    value = read_json(path)
    if isinstance(value, dict) and isinstance(value.get("fingerprint"), dict):
        value = value["fingerprint"]
    if isinstance(value, dict):
        value = value.get("features")
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{path}: ожидался массив признаков или объект с полем features.")
    return list(value)


def _comparison_feature_payload(features: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, Mapping) or not isinstance(
            feature.get("feature_id"), str
        ):
            raise ValueError("Каждый признак сопоставимости должен иметь feature_id.")
        payload.append(
            {
                "feature_id": feature.get("feature_id"),
                "value": feature.get("value"),
                "status": feature.get("status"),
                "material": feature.get("material") is True,
                "source": feature.get("source"),
            }
        )
    return sorted(payload, key=lambda item: str(item["feature_id"]))


def cmd_compare(args: argparse.Namespace) -> int:
    fingerprint_sha256 = None
    position_card: dict[str, Any] | None = None
    applicant_features = _feature_list(Path(args.applicant).expanduser().resolve())
    candidate_features = _feature_list(Path(args.candidate).expanduser().resolve())
    if args.reviewed_at:
        _require_iso_timestamp(args.reviewed_at, "reviewed-at")
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        fingerprint_path = workspace / "case-fingerprint.json"
        if not fingerprint_path.exists():
            raise ValueError("Сначала подготовьте case-fingerprint.json.")
        fingerprint = read_json(fingerprint_path)
        fingerprint_sha256 = fingerprint.get("fingerprint_sha256")
        current_applicant_features = fingerprint.get("features")
        if not isinstance(current_applicant_features, list):
            raise ValueError("Текущий fingerprint не содержит массива features.")
        if _comparison_feature_payload(applicant_features) != _comparison_feature_payload(
            current_applicant_features
        ):
            raise ValueError(
                "--applicant не совпадает с текущим case-fingerprint.json; "
                "сопоставление по подменённым признакам запрещено."
            )
        cards = read_jsonl(workspace / "position-cards.jsonl")
        if args.position_card_id:
            position_card = next(
                (card for card in cards if card.get("position_card_id") == args.position_card_id),
                None,
            )
            if position_card is None:
                raise ValueError("--position-card-id не найден в position-cards.jsonl.")
        elif len(cards) == 1:
            position_card = cards[0]
        elif cards:
            raise ValueError(
                "Для матрицы с несколькими карточками явно укажите --position-card-id."
            )
        if position_card is None:
            raise ValueError("Сначала сохраните проверенную карточку позиции.")
        saved_candidate_features = position_card.get("comparison_features")
        if not isinstance(saved_candidate_features, list):
            raise ValueError("Карточка позиции не содержит comparison_features.")
        if _comparison_feature_payload(candidate_features) != _comparison_feature_payload(
            saved_candidate_features
        ):
            raise ValueError(
                "--candidate не совпадает с признаками сохранённой карточки позиции."
            )
        applicant_features = list(current_applicant_features)
        candidate_features = list(saved_candidate_features)
    result = compare_case_features(
        applicant_features,
        candidate_features,
        reviewer=args.reviewer,
        reviewed_at=args.reviewed_at,
        fingerprint_sha256=fingerprint_sha256,
    )
    if position_card is not None:
        result["position_card_id"] = position_card.get("position_card_id")
        result["chain_id"] = position_card.get("chain_id")
        result["applicant_features_sha256"] = _artifact_sha256(
            _comparison_feature_payload(applicant_features)
        )
        result["candidate_features_sha256"] = _artifact_sha256(
            _comparison_feature_payload(candidate_features)
        )
        result["position_card_sha256"] = _artifact_sha256(position_card)
        result["comparison_id"] = "comparison-" + hashlib.sha256(
            json.dumps(
                {
                    "position_card_id": result["position_card_id"],
                    "fingerprint_sha256": fingerprint_sha256,
                    "comparisons": result["comparisons"],
                    "review_provenance": result["review_provenance"],
                    "applicant_features_sha256": result[
                        "applicant_features_sha256"
                    ],
                    "candidate_features_sha256": result[
                        "candidate_features_sha256"
                    ],
                    "position_card_sha256": result["position_card_sha256"],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:16]
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        write_json(workspace / "case-comparison.json", result)
        if position_card is not None:
            existing = read_jsonl(workspace / "comparability-matrix.jsonl")
            by_card = {
                str(item.get("position_card_id")): item
                for item in existing
                if item.get("position_card_id")
            }
            by_card[str(result["position_card_id"])] = result
            write_jsonl(
                workspace / "comparability-matrix.jsonl",
                [by_card[key] for key in sorted(by_card)],
            )
    _print_json(result)
    return 0


def cmd_relation_classify(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    fingerprint_path = workspace / "case-fingerprint.json"
    if not fingerprint_path.exists():
        raise ValueError("Сначала подготовьте case-fingerprint.json.")
    fingerprint_sha256 = read_json(fingerprint_path).get("fingerprint_sha256")
    position_card_input = read_json(Path(args.position_card).expanduser().resolve())
    comparison_input = read_json(Path(args.comparison).expanduser().resolve())
    applicant_position = read_json(Path(args.applicant_position).expanduser().resolve())
    if not all(
        isinstance(value, dict)
        for value in (position_card_input, comparison_input, applicant_position)
    ):
        raise ValueError("Карточка, сравнение и позиция заявителя должны быть JSON-объектами.")
    if not args.reviewer.strip() or not args.reviewed_at.strip():
        raise ValueError("Applicant-relative классификация требует reviewer и reviewed_at.")
    _require_iso_timestamp(args.reviewed_at, "reviewed-at")
    cards = read_jsonl(workspace / "position-cards.jsonl")
    saved_cards = {
        str(item.get("position_card_id")): item
        for item in cards
        if item.get("position_card_id")
    }
    position_card_id = str(position_card_input.get("position_card_id", ""))
    position_card = saved_cards.get(position_card_id)
    if position_card is None or position_card != position_card_input:
        raise ValueError(
            "Карточка --position-card не совпадает с текущей проверенной карточкой workspace."
        )
    comparisons = read_jsonl(workspace / "comparability-matrix.jsonl")
    saved_comparisons = {
        str(item.get("comparison_id")): item
        for item in comparisons
        if item.get("comparison_id")
    }
    comparison_id = str(comparison_input.get("comparison_id", ""))
    comparison = saved_comparisons.get(comparison_id)
    if comparison is None or comparison != comparison_input:
        raise ValueError(
            "Матрица --comparison не совпадает с текущей проверенной матрицей workspace."
        )
    if comparison.get("position_card_id") != position_card_id:
        raise ValueError("Матрица сопоставимости относится к другой карточке позиции.")
    result = classify_applicant_relation(
        position_card,
        comparison,
        applicant_position,
        current_fingerprint_sha256=fingerprint_sha256,
    )
    result.update(
        {
            "schema_version": "1.0",
            "position_card_id": position_card.get("position_card_id"),
            "comparison_id": comparison.get("comparison_id"),
            "fingerprint_sha256": fingerprint_sha256,
            "position_card_sha256": _artifact_sha256(position_card),
            "comparison_sha256": _artifact_sha256(comparison),
            "applicant_position_sha256": _artifact_sha256(applicant_position),
            "reviewer": args.reviewer.strip(),
            "reviewed_at": args.reviewed_at.strip(),
            "human_review": (
                "approved" if result.get("relation") != "unresolved" else "blocked"
            ),
        }
    )
    write_json(workspace / "applicant-position.json", applicant_position)
    existing = read_jsonl(workspace / "applicant-relations.jsonl")
    by_card = {
        str(item.get("position_card_id")): item
        for item in existing
        if item.get("position_card_id")
    }
    by_card[str(result["position_card_id"])] = result
    write_jsonl(
        workspace / "applicant-relations.jsonl",
        [by_card[key] for key in sorted(by_card)],
    )
    _print_json(result)
    return 0 if result.get("relation") != "unresolved" else 2


def _resolution_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    value = read_json(path)
    if isinstance(value, list):
        mapped: dict[str, dict[str, Any]] = {}
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("candidate_id"), str):
                raise ValueError("Каждое решение должно иметь candidate_id.")
            mapped[item["candidate_id"]] = item
        return mapped
    if isinstance(value, dict) and all(isinstance(item, dict) for item in value.values()):
        return dict(value)
    raise ValueError("--resolutions должен содержать объект или массив решений.")


def cmd_queue_build(args: argparse.Namespace) -> int:
    quotas = read_json(Path(args.quotas).expanduser().resolve()) if args.quotas else None
    if quotas is not None and not isinstance(quotas, dict):
        raise ValueError("Квоты очереди должны быть JSON-объектом.")
    result = build_explainable_queue(
        _read_records(Path(args.candidates).expanduser().resolve()),
        _resolution_map(
            Path(args.resolutions).expanduser().resolve() if args.resolutions else None
        ),
        quotas=quotas,
    )
    if args.workspace:
        write_json(Path(args.workspace).expanduser().resolve() / "review-queue.json", result)
    _print_json(result)
    return 0


def cmd_adverse_build(args: argparse.Namespace) -> int:
    searched = set(args.searched_buckets)
    completed = set(args.completed_buckets)
    unknown = sorted((searched | completed) - set(ADVERSE_BUCKETS))
    if unknown:
        raise ValueError("Неизвестные adverse buckets: " + ", ".join(unknown) + ".")
    if not completed.issubset(searched):
        raise ValueError("Завершённый adverse bucket должен быть указан среди searched buckets.")
    input_cards = _read_records(Path(args.cards).expanduser().resolve())
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        saved_cards = {
            str(item.get("position_card_id")): item
            for item in read_jsonl(workspace / "position-cards.jsonl")
            if item.get("position_card_id")
        }
        for card in input_cards:
            card_id = str(card.get("position_card_id", ""))
            if card_id not in saved_cards or saved_cards[card_id] != card:
                raise ValueError(
                    f"Adverse-карточка {card_id or '[без id]'} не совпадает с "
                    "проверенной карточкой workspace."
                )
        state = _safe_validation_state(workspace)
        if not state.get("comparison_review_complete") or not state.get(
            "applicant_relation_complete"
        ):
            missing_gates = [
                name
                for name in (
                    "comparison_review_complete",
                    "applicant_relation_complete",
                )
                if not state.get(name)
            ]
            raise ValueError(
                "До adverse review нужно завершить привязанные к fingerprint "
                "сопоставления и applicant-relative отношения всех карточек: "
                + ", ".join(missing_gates)
                + ". Привязки: "
                + json.dumps(
                    state.get("binding_diagnostics", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
    result = build_adverse_review(
        input_cards,
        completed_buckets=completed,
        executed_query_ids_by_bucket=read_json(
            Path(args.executed_query_ids).expanduser().resolve()
        ),
        unresolved_segments_by_bucket=read_json(
            Path(args.unresolved_segments).expanduser().resolve()
        ),
        maximum_claim_effect_by_bucket=read_json(
            Path(args.maximum_claim_effects).expanduser().resolve()
        ),
    )
    missing_searched = [bucket for bucket in ADVERSE_BUCKETS if bucket not in searched]
    result["searched_buckets"] = [bucket for bucket in ADVERSE_BUCKETS if bucket in searched]
    result["missing_searched_buckets"] = missing_searched
    result["completed"] = result.get("completed") is True and not missing_searched
    if args.workspace:
        write_json(
            Path(args.workspace).expanduser().resolve() / "case-adverse-review.json",
            result,
        )
    _print_json(result)
    return 0


def cmd_bridge_check(args: argparse.Namespace) -> int:
    bridge = read_json(Path(args.input).expanduser().resolve())
    if not isinstance(bridge, dict):
        raise ValueError("Нормативный мост должен быть JSON-объектом.")
    validation_kwargs: dict[str, Any] = {}
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        fingerprint_path = workspace / "case-fingerprint.json"
        if not fingerprint_path.exists():
            raise ValueError("Нормативный мост требует case-fingerprint.json.")
        fingerprint_sha256 = read_json(fingerprint_path).get("fingerprint_sha256")
        cards = read_jsonl(workspace / "position-cards.jsonl")
        comparisons = read_jsonl(workspace / "comparability-matrix.jsonl")
        relations = read_jsonl(workspace / "applicant-relations.jsonl")
        adverse_path = workspace / "case-adverse-review.json"
        validation_kwargs = {
            "current_fingerprint_sha256": fingerprint_sha256,
            "maximum_permitted_claim": (
                args.maximum_permitted_claim
                or _safe_validation_state(workspace).get("maximum_permitted_claim")
            ),
            "position_cards": {
                str(item.get("position_card_id")): item
                for item in cards
                if item.get("position_card_id")
            },
            "comparisons": {
                str(item.get("position_card_id")): item
                for item in comparisons
                if item.get("position_card_id")
            },
            "applicant_relations": {
                str(item.get("position_card_id")): item
                for item in relations
                if item.get("position_card_id")
            },
            "adverse_review": read_json(adverse_path) if adverse_path.exists() else {},
        }
    errors = validate_normative_bridge(bridge, **validation_kwargs)
    result = {"schema_version": "1.0", "valid": not errors, "errors": errors}
    if not errors and args.workspace:
        write_json(
            Path(args.workspace).expanduser().resolve() / "normative-bridge.json",
            bridge,
        )
    _print_json(result)
    return 0 if not errors else 2


def _safe_validation_state(workspace: Path) -> dict[str, Any]:
    try:
        return _validation_state(workspace)
    except ValueError as exc:
        return {
            "case_fingerprint_ready": False,
            "plan_frozen": False,
            "collection_complete": False,
            "coding_complete": False,
            "comparison_review_complete": False,
            "applicant_relation_complete": False,
            "adverse_review_complete": False,
            "coverage_review_complete": False,
            "normative_bridge_complete": False,
            "analysis_complete": False,
            "human_approved": False,
            "candidate_approved": False,
            "approval_hashes_match": False,
            "maximum_permitted_claim": "unproven_research_question",
            "temporal_analysis_complete": False,
            "validation_current": False,
            "pending_task_counts": {},
            "stale_artifacts": [],
            "workspace_error": str(exc),
        }


def _status_derivation_state(workspace: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    """Expose a recorded-but-invalidated approval to the reporting status machine."""

    derived = dict(state)
    decision_path = workspace / "human-decision.json"
    if not decision_path.exists() or state.get("approval_hashes_match") is True:
        return derived
    decision = read_json(decision_path)
    if isinstance(decision, dict) and decision.get("decision") == "approved":
        derived["human_approved"] = True
        derived["recorded_approval_effective"] = False
    return derived


def cmd_status(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    state = _safe_validation_state(workspace)
    _print_json(
        {
            "schema_version": "1.0",
            "workspace": str(workspace),
            "state": state,
            "status": derive_research_status(_status_derivation_state(workspace, state)),
            "evidence_sha256": _approval_evidence_sha256(workspace),
        }
    )
    return 0


def _default_report_model(workspace: Path) -> dict[str, Any]:
    state = _safe_validation_state(workspace)
    report_state = _status_derivation_state(workspace, state)
    try:
        plan = latest_plan(workspace)
    except ValueError:
        plan = {}
    analysis_path = workspace / "analysis.json"
    analysis = read_json(analysis_path) if analysis_path.exists() else {}
    case_temporal_path = workspace / "case-temporal-analysis.json"
    case_temporal = read_json(case_temporal_path) if case_temporal_path.exists() else {}
    reconciliation_path = workspace / "source-reconciliation.json"
    reconciliation = read_json(reconciliation_path) if reconciliation_path.exists() else {}
    run_path = workspace / "run.json"
    run = read_json(run_path) if run_path.exists() else {}
    fingerprint_path = workspace / "case-fingerprint.json"
    fingerprint = read_json(fingerprint_path) if fingerprint_path.exists() else {}
    coverage_gaps: list[dict[str, Any]] = []

    def add_gap(identifier: str, label: str, reason: str) -> None:
        coverage_gaps.append({"id": identifier, "label": label, "reason": reason})

    if not reconciliation:
        add_gap(
            "source-reconciliation-missing",
            "Сверка официальных маршрутов не выполнена",
            "source_reconciliation_not_run",
        )
    for index, gap in enumerate(reconciliation.get("gaps", []), start=1):
        if not isinstance(gap, dict):
            continue
        add_gap(
            f"source-{index}",
            f"Цепочка {gap.get('chain_id', 'не указана')}",
            f"Нет в маршруте {gap.get('missing_from', 'не указан')}: {gap.get('reason', 'причина не указана')}",
        )
    for index, gap in enumerate(reconciliation.get("historical_gaps", []), start=1):
        if not isinstance(gap, dict):
            continue
        add_gap(
            f"historical-{index}",
            "Исторический режим не настроен: "
            + str(gap.get("institutional_regime", gap.get("enumerator_id", "не указан"))),
            "Период "
            + str(gap.get("applicable_from", "?"))
            + " — "
            + str(gap.get("applicable_to", "?"))
            + "; статус "
            + str(gap.get("status", "not_configured")),
        )
    route_coverage = reconciliation.get("route_coverage", {})
    if isinstance(route_coverage, dict):
        for route_id, route in sorted(route_coverage.items()):
            if not isinstance(route, dict) or route.get("status") in {
                "closed_declared_enumeration",
                "not_applicable",
            }:
                continue
            blockers = route.get("closure_blockers", [])
            blocker_text = ", ".join(str(item) for item in blockers) if isinstance(
                blockers, list
            ) else str(blockers)
            add_gap(
                "route-" + str(route_id),
                "Маршрут не закрывает заявленный знаменатель: " + str(route_id),
                str(route.get("status", "observed_only"))
                + (": " + blocker_text if blocker_text else ""),
            )
    unresolved_identities = reconciliation.get("unresolved_identity_observations", [])
    if isinstance(unresolved_identities, list) and unresolved_identities:
        add_gap(
            "unresolved-identities",
            "Есть неразрешённые идентичности актов и цепочек",
            f"unresolved_identity_observations={len(unresolved_identities)}",
        )
    if reconciliation and reconciliation.get("overall_status") != "closed_declared_enumerations":
        add_gap(
            "overall-observed-only",
            "Корпус остаётся наблюдаемым, а не полным",
            str(
                reconciliation.get(
                    "denominator_limit",
                    "Не все маршруты и исторические режимы закрыты.",
                )
            ),
        )

    cards = read_jsonl(workspace / "position-cards.jsonl")
    comparisons = {
        str(item.get("position_card_id")): item
        for item in read_jsonl(workspace / "comparability-matrix.jsonl")
        if item.get("position_card_id")
    }
    relations = {
        str(item.get("position_card_id")): item
        for item in read_jsonl(workspace / "applicant-relations.jsonl")
        if item.get("position_card_id")
    }
    adverse_path = workspace / "case-adverse-review.json"
    adverse = read_json(adverse_path) if adverse_path.exists() else {}
    adverse_ids = {
        str(card_id)
        for values in adverse.get("buckets", {}).values()
        if isinstance(values, list)
        for card_id in values
    } if isinstance(adverse.get("buckets"), dict) else set()
    current_fingerprint_sha256 = fingerprint.get("fingerprint_sha256")
    grouped_findings: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for card in cards:
        card_id = str(card.get("position_card_id", ""))
        comparison = comparisons.get(card_id, {})
        relation = relations.get(card_id, {})
        if (
            not card_id
            or comparison.get("fingerprint_sha256") != current_fingerprint_sha256
            or relation.get("fingerprint_sha256") != current_fingerprint_sha256
            or relation.get("human_review") != "approved"
        ):
            continue
        relation_name = str(relation.get("relation", "unresolved"))
        reading_family = str(card.get("reading_family", "не классифицировано"))
        grouped_findings.setdefault((relation_name, reading_family), []).append(
            {
                "chain_id": card.get("chain_id"),
                "court": card.get("court_id"),
                "decision_date": card.get("decision_date"),
                "case_number": card.get("case_number"),
                "official_url": card.get("official_url"),
                "document_id": card.get("document_id"),
                "document_sha256": card.get("document_sha256"),
                "speaker": card.get("speaker"),
                "quote": card.get("quote"),
                "quote_locator": card.get("quote_locator"),
                "relation": relation_name,
                "position_card_id": card_id,
                "materiality": card.get("outcome_materiality"),
                "comparability": comparison.get("status"),
                "adverse_status": (
                    "reviewed_adverse_bucket" if card_id in adverse_ids else "not_in_adverse_bucket"
                ),
                "outcome": card.get("outcome"),
                "remedy": card.get("remedy"),
            }
        )
    position_findings: list[dict[str, Any]] = []
    denominator = len(cards)
    for (relation_name, reading_family), chains in sorted(grouped_findings.items()):
        position_findings.append(
            {
                "id": "position-" + _artifact_sha256(
                    {"relation": relation_name, "reading_family": reading_family}
                )[:12],
                "title": f"{reading_family}: {relation_name}",
                "count": len(chains),
                "denominator": denominator,
                "denominator_scope": "все полнотекстовые карточки; только текущие проверенные связи раскрыты как вывод",
                "chains": chains,
            }
        )
    analysis_findings = analysis.get("findings", [])
    if not isinstance(analysis_findings, list):
        analysis_findings = []
    status = derive_research_status(report_state)
    bridge_path = workspace / "normative-bridge.json"
    bridge = read_json(bridge_path) if bridge_path.exists() else {}
    return {
        "title": "Исследование кассационной практики по делу заявителя",
        "run_id": run.get("run_id") or workspace.name,
        "plan_sha256": plan.get("plan_sha256", ""),
        "evidence_sha256": _approval_evidence_sha256(workspace),
        "fingerprint_sha256": current_fingerprint_sha256,
        "state": report_state,
        "coverage_gaps": coverage_gaps,
        "findings": [*analysis_findings, *position_findings],
        "temporal_analysis": case_temporal or analysis,
        "safe_wording": {
            "allowed": (
                str(bridge.get("claim_wording"))
                if status["drafting_ready"]
                else "Вывод для жалобы пока не готов; сохраняется исследовательский вопрос."
            ),
            "forbidden": [
                "Нельзя объявлять расхождение решений самостоятельным доказательством неконституционности."
            ],
            "next_steps": [status["next_action"]],
        },
    }


def cmd_report(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    model = (
        read_json(Path(args.model).expanduser().resolve())
        if args.model
        else _default_report_model(workspace)
    )
    if not isinstance(model, dict):
        raise ValueError("Модель отчёта должна быть JSON-объектом.")
    html_path = (
        Path(args.html).expanduser().resolve()
        if args.html
        else workspace / "report" / "index.html"
    )
    manifest_path = (
        Path(args.manifest).expanduser().resolve()
        if args.manifest
        else workspace / "report" / "manifest.json"
    )
    manifest = write_offline_report(model, html_path, manifest_path)
    _print_json(
        {
            **manifest,
            "html_path": str(html_path),
            "manifest_path": str(manifest_path),
        }
    )
    return 0


def _handoff_hashes(workspace: Path) -> tuple[str, str]:
    plan = latest_plan(workspace)
    plan_sha256 = plan.get("plan_sha256")
    if not isinstance(plan_sha256, str):
        raise ValueError("Замороженный план не содержит plan_sha256.")
    material_paths = _approval_evidence_paths(workspace)
    if not any(path.exists() for path in material_paths):
        raise ValueError("Нет материальных доказательственных артефактов для handoff.")
    return plan_sha256, _approval_evidence_sha256(workspace)


def _handoff_limitations(args: argparse.Namespace) -> list[str]:
    limitations = list(args.limitation or [])
    if args.limitations:
        value = read_json(Path(args.limitations).expanduser().resolve())
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("--limitations должен содержать JSON-массив строк.")
        limitations.extend(value)
    return limitations


def cmd_handoff_create(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    plan_sha256, evidence_sha256 = _handoff_hashes(workspace)
    payload = read_json(Path(args.payload).expanduser().resolve())
    if not isinstance(payload, dict):
        raise ValueError("Payload handoff должен быть JSON-объектом.")
    if args.payload_type != "unproven_research_questions":
        state = _validation_state(workspace)
        status = derive_research_status(_status_derivation_state(workspace, state))
        if status.get("drafting_ready") is not True:
            raise ValueError(
                "Проверенный handoff заблокирован: нет текущего одобрения всех доказательственных ворот. "
                + str(status.get("label", "Состояние не готово"))
                + "."
            )
        validation_path = workspace / "validation-report.json"
        if not validation_path.exists():
            raise ValueError("Проверенный handoff требует текущий validation-report.json.")
        validation = read_json(validation_path)
        if (
            not isinstance(validation, dict)
            or validation.get("valid") is not True
            or validation.get("plan_sha256") != latest_plan(workspace).get("plan_sha256")
            or validation.get("evidence_sha256") != _approval_evidence_sha256(workspace)
        ):
            raise ValueError("Проверенный handoff требует успешную проверку текущих доказательств.")
        if payload.get("maximum_permitted_claim") != state.get("maximum_permitted_claim"):
            raise ValueError(
                "maximum_permitted_claim payload не совпадает с текущим пределом вывода."
            )
    run_path = workspace / "run.json"
    run = read_json(run_path) if run_path.exists() else {}
    run_id = args.run_id or run.get("run_id") or f"run-{evidence_sha256[:12]}"
    envelope = create_handoff(
        source_skill="ksrf-cassation-judicial-meaning",
        target_skill=args.target_skill,
        run_id=run_id,
        plan_sha256=plan_sha256,
        evidence_sha256=evidence_sha256,
        payload_type=args.payload_type,
        payload=payload,
        limitations=_handoff_limitations(args),
        created_at=args.created_at or utc_now(),
        fingerprint_sha256=(
            read_json(workspace / "case-fingerprint.json").get("fingerprint_sha256")
            if (workspace / "case-fingerprint.json").exists()
            else None
        ),
    )
    destination = (
        Path(args.output).expanduser().resolve()
        if args.output
        else workspace / "handoffs" / "outbox" / f"{envelope['handoff_id']}.json"
    )
    write_json(destination, envelope)
    _print_json({**envelope, "output": str(destination)})
    return 0


def _optional_current_context(
    workspace_value: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not workspace_value:
        return None, None, None, None
    workspace = Path(workspace_value).expanduser().resolve()
    plan_sha256, evidence_sha256 = _handoff_hashes(workspace)
    fingerprint_path = workspace / "case-fingerprint.json"
    fingerprint_sha256 = (
        read_json(fingerprint_path).get("fingerprint_sha256")
        if fingerprint_path.exists()
        else None
    )
    return (
        plan_sha256,
        evidence_sha256,
        fingerprint_sha256,
        _safe_validation_state(workspace).get("maximum_permitted_claim"),
    )


def cmd_handoff_check(args: argparse.Namespace) -> int:
    envelope = read_json(Path(args.input).expanduser().resolve())
    plan_sha256, evidence_sha256, fingerprint_sha256, maximum_claim = _optional_current_context(args.workspace)
    result = check_handoff(
        envelope,
        expected_target=args.expected_target,
        current_plan_sha256=plan_sha256,
        current_evidence_sha256=evidence_sha256,
        current_fingerprint_sha256=fingerprint_sha256,
        current_maximum_permitted_claim=maximum_claim,
    )
    _print_json(result)
    return 0 if result.get("valid") else 2


def cmd_handoff_import(args: argparse.Namespace) -> int:
    envelope = read_json(Path(args.input).expanduser().resolve())
    plan_sha256, evidence_sha256, fingerprint_sha256, maximum_claim = _optional_current_context(args.workspace)
    result = import_handoff(
        envelope,
        Path(args.ledger).expanduser().resolve(),
        expected_target=args.expected_target,
        current_plan_sha256=plan_sha256,
        current_evidence_sha256=evidence_sha256,
        current_fingerprint_sha256=fingerprint_sha256,
        current_maximum_permitted_claim=maximum_claim,
    )
    _print_json(result)
    return 0 if result.get("valid") else 2


def cmd_cache_init(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    with PublicCorpus(root) as corpus:
        result = {
            "schema_version": "1.0",
            "root": str(root),
            "search_backend": corpus.search_backend,
            "evidence_digest": corpus.evidence_digest(),
        }
    _print_json(result)
    return 0


def cmd_cache_register_seed(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.register_seed(url=args.url, role=args.role, public=True)
    _print_json(result)
    return 0


def cmd_cache_ingest(args: argparse.Namespace) -> int:
    raw_path = Path(args.raw).expanduser().resolve()
    parser_manifest = read_json(Path(args.parser_manifest).expanduser().resolve())
    if not isinstance(parser_manifest, dict) or not parser_manifest:
        raise ValueError("Parser manifest должен быть непустым JSON-объектом.")
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.store_snapshot(
            seed_id=args.seed_id,
            raw=raw_path.read_bytes(),
            content_type=args.content_type,
            fetched_at=args.fetched_at,
            parser_manifest=parser_manifest,
        )
        if args.text:
            indexed = corpus.index_text(
                result["snapshot_id"],
                Path(args.text).expanduser().resolve().read_text(encoding="utf-8"),
            )
            result["text_hash"] = indexed["text_hash"]
        result["evidence_digest"] = corpus.evidence_digest()
    _print_json(result)
    return 0


def cmd_cache_pin_run(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.create_run(args.run_id, args.snapshot)
    _print_json(result)
    return 0


def cmd_cache_export_run(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        manifest = corpus.export_run(args.run_id, output)
    _print_json(
        {
            "schema_version": manifest["schema_version"],
            "run_id": manifest["run"]["run_id"],
            "manifest_sha256": manifest["manifest_sha256"],
            "output": str(output),
        }
    )
    return 0


def cmd_cache_import_run(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.import_run(Path(args.input).expanduser().resolve())
    _print_json(result)
    return 0


def cmd_cache_search(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        hits = corpus.search(args.query, limit=args.limit)
        result = {
            "schema_version": "1.0",
            "query": args.query,
            "count": len(hits),
            "hits": hits,
            "search_backend": corpus.search_backend,
        }
    _print_json(result)
    return 0


def cmd_cache_refresh_plan(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.plan_refresh(
            as_of=args.as_of,
            max_age_seconds=args.max_age_seconds,
        )
    _print_json(result)
    return 0


def cmd_cache_funnel_record(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.record_funnel(
            args.chain_id,
            args.status,
            snapshot_id=args.snapshot_id,
            reason=args.reason,
            source_role=args.source_role,
            court_id=args.court_id,
            period_id=args.period_id,
            enumerator_id=args.enumerator_id,
        )
    _print_json(result)
    return 0


def cmd_cache_funnel_report(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.funnel_report()
    _print_json(result)
    return 0


def cmd_cache_treatment_discover(args: argparse.Namespace) -> int:
    target_identity = read_json(Path(args.target_identity).expanduser().resolve())
    if not isinstance(target_identity, dict) or not target_identity:
        raise ValueError("--target-identity должен содержать непустой JSON-объект.")
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.propose_treatment(
            source_chain_id=args.source_chain_id,
            source_court_id=args.source_court_id,
            target_authority_id=args.target_authority_id,
            target_kind=args.target_kind,
            target_identity=target_identity,
            treatment_type=args.treatment_type,
            snapshot_id=args.snapshot_id,
            supersedes_treatment_id=args.supersedes_treatment_id,
        )
    _print_json(result)
    return 0


def cmd_cache_treatment_review(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.review_treatment(
            args.treatment_id,
            decision=args.decision,
            reviewer=args.reviewer,
            quote=args.quote,
            locator=args.locator,
            speaker=args.speaker,
            confirmed_target_authority_id=args.confirmed_target_authority_id,
            target_identity_confirmed=args.target_identity_confirmed,
            reviewed_at=args.reviewed_at,
        )
    _print_json(result)
    return 0


def cmd_cache_treatment_list(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        records = corpus.list_treatments(verified_only=args.verified_only)
    _print_json({"schema_version": "1.0", "count": len(records), "items": records})
    return 0


def cmd_cache_treatment_history(args: argparse.Namespace) -> int:
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        records = corpus.treatment_history(args.treatment_id)
    _print_json({"schema_version": "1.0", "count": len(records), "items": records})
    return 0


def cmd_source_reconcile(args: argparse.Namespace) -> int:
    result = reconcile_sources(
        manifests=_read_records(Path(args.manifests).expanduser().resolve()),
        observations=_read_records(Path(args.observations).expanduser().resolve()),
        route_coverage=_read_records(Path(args.route_coverage).expanduser().resolve()),
        requested_from=args.requested_from,
        requested_to=args.requested_to,
    )
    destination: Path | None = None
    if args.output:
        destination = Path(args.output).expanduser().resolve()
    elif args.workspace:
        destination = Path(args.workspace).expanduser().resolve() / "source-reconciliation.json"
    if destination is not None:
        write_json(destination, result)
    _print_json(result)
    return 0


def cmd_source_verify_manifest(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.input).expanduser().resolve())
    if not isinstance(manifest, dict):
        raise ValueError("Manifest перечислителя должен быть JSON-объектом.")
    result = validate_enumerator_manifest(manifest)
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), result)
    _print_json(
        {
            "schema_version": "1.0",
            "valid": True,
            "configured": result.get("configured"),
            "enumerator_id": result.get("enumerator_id"),
            "manifest": result,
        }
    )
    return 0


def cmd_source_promote_enumerator(args: argparse.Namespace) -> int:
    manifest = read_json(Path(args.manifest).expanduser().resolve())
    verification = read_json(Path(args.verification).expanduser().resolve())
    if not isinstance(manifest, dict) or not isinstance(verification, dict):
        raise ValueError("Manifest и verification должны быть JSON-объектами.")
    result = promote_enumerator(
        manifest,
        verification=verification,
        reviewer=args.reviewer,
        reviewed_at=args.reviewed_at,
    )
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), result)
    _print_json(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="judicial_meaning.py",
        description="Локальное исследование кассационной практики до выбора тезиса жалобы в КС РФ.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("intake", help="Инвентаризировать акты заявителя")
    intake.add_argument("--workspace", required=True)
    intake.add_argument("--inputs", nargs="+", required=True)
    intake.add_argument("--role", default="applicant_judicial_act")
    intake.set_defaults(func=cmd_intake)

    ocr = sub.add_parser("ocr", help="Явно распознать скан PDF локальными OCR-инструментами")
    ocr.add_argument("--input", required=True)
    ocr.add_argument("--output", required=True)
    ocr.add_argument("--language", default="rus")
    ocr.add_argument("--dpi", type=int, default=300)
    ocr.set_defaults(func=cmd_ocr)

    plan = sub.add_parser("plan", help="Создать или заморозить нейтральный план")
    plan_sub = plan.add_subparsers(dest="plan_command", required=True)
    template = plan_sub.add_parser("template", help="Создать заполняемый шаблон")
    template.add_argument("--workspace", required=True)
    template.add_argument("--force", action="store_true")
    template.set_defaults(func=cmd_plan_template)
    freeze = plan_sub.add_parser("freeze", help="Проверить и неизменяемо зафиксировать план")
    freeze.add_argument("--workspace", required=True)
    freeze.add_argument("--plan", required=True)
    freeze.set_defaults(func=cmd_plan_freeze)

    query = sub.add_parser("query", help="Подтвердить предложенный или добавить supplemental-запрос")
    query_sub = query.add_subparsers(dest="query_command", required=True)
    query_accept = query_sub.add_parser(
        "accept", help="Подтвердить предложения до заморозки плана"
    )
    query_accept.add_argument("--workspace", required=True)
    query_accept.add_argument("--query-id", action="append", required=True)
    query_accept.add_argument("--reviewer", required=True)
    query_accept.add_argument("--confirmed-at", required=True)
    query_accept.set_defaults(func=cmd_query_accept)
    query_supplement = query_sub.add_parser(
        "supplement", help="Добавить раскрытый запрос после заморозки без изменения знаменателя"
    )
    query_supplement.add_argument("--workspace", required=True)
    query_supplement.add_argument(
        "--lane", choices=tuple(sorted(_QUERY_PLAN_LANE)), required=True
    )
    query_supplement.add_argument("--query", required=True)
    query_supplement.add_argument("--reason", required=True)
    query_supplement.add_argument("--reviewer", required=True)
    query_supplement.add_argument("--confirmed-at", required=True)
    query_supplement.set_defaults(func=cmd_query_supplement)

    collect = sub.add_parser("collect", help="Собрать официально наблюдаемый корпус")
    collect.add_argument("--workspace", required=True)
    collect.add_argument("--resume", action="store_true")
    collect.add_argument("--max-tasks", type=int)
    collect.add_argument("--max-attempts", type=int, default=3)
    collect.add_argument("--max-source-tasks", type=int)
    collect.add_argument("--retry-now", action="store_true", help="Повторить уже наступившие и явно разрешённые пользователем retry-задачи сейчас")
    collect.add_argument("--fixture-dir", help=argparse.SUPPRESS)
    collect.set_defaults(func=cmd_collect)

    screen = sub.add_parser("screen", help="Отобрать кандидатов по дорожкам frozen plan")
    screen.add_argument("--workspace", required=True)
    screen.set_defaults(func=cmd_screen)

    code = sub.add_parser("code", help="Создать или проверить полнотекстовое кодирование")
    code.add_argument("--workspace", required=True)
    code.add_argument("--input")
    code.set_defaults(func=cmd_code)

    analyze = sub.add_parser("analyze", help="Посчитать независимые цепочки и bounded status")
    analyze.add_argument("--workspace", required=True)
    analyze.set_defaults(func=cmd_analyze)

    review = sub.add_parser("review", help="Записать adverse/coverage/human review")
    review.add_argument("--workspace", required=True)
    review.add_argument(
        "--decision",
        choices=("evidence_reviewed", "approved", "rejected", "revise"),
        required=True,
    )
    review.add_argument("--reviewer", required=True)
    review.add_argument("--adverse-complete", action="store_true")
    review.add_argument("--coverage-complete", action="store_true")
    review.add_argument("--notes", default="")
    review.add_argument("--adverse-file")
    review.add_argument("--thesis-file")
    review.set_defaults(func=cmd_review)

    validate = sub.add_parser("validate", help="Проверить артефакты и допуск тезиса")
    validate.add_argument("--workspace", required=True)
    validate.add_argument("--require-thesis-ready", action="store_true")
    validate.add_argument("--thesis")
    validate.set_defaults(func=cmd_validate)

    export = sub.add_parser("export", help="Сформировать детерминированные JSON/JSONL отчёты")
    export.add_argument("--workspace", required=True)
    export.add_argument("--run-id")
    export.set_defaults(func=cmd_export)

    case = sub.add_parser("case", help="Подготовить fingerprint дела заявителя")
    case_sub = case.add_subparsers(dest="case_command", required=True)
    case_prepare = case_sub.add_parser(
        "prepare", help="Создать или обновить fingerprint и запросы"
    )
    case_prepare.add_argument("--workspace", required=True)
    case_prepare.add_argument(
        "--answers",
        help="JSON с issue, norm_refs и features; без него разрешён только интерактивный TTY",
    )
    case_prepare.set_defaults(func=cmd_case_prepare)
    case_dynamics = case_sub.add_parser(
        "dynamics", help="Описать проверенную динамику по годам и замороженным стратам"
    )
    case_dynamics.add_argument("--workspace", required=True)
    case_dynamics.set_defaults(func=cmd_case_dynamics)

    position = sub.add_parser("position", help="Проверить карточку позиции суда")
    position_sub = position.add_subparsers(dest="position_command", required=True)
    position_check = position_sub.add_parser(
        "check", help="Проверить атрибуцию, цитату и исходозначимость"
    )
    position_check.add_argument("--input", required=True)
    position_check.add_argument("--workspace")
    position_check.set_defaults(func=cmd_position_check)

    compare = sub.add_parser("compare", help="Сопоставить материальные признаки двух дел")
    compare.add_argument("--applicant", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--workspace")
    compare.add_argument("--reviewer")
    compare.add_argument("--reviewed-at")
    compare.add_argument("--position-card-id")
    compare.set_defaults(func=cmd_compare)

    relation = sub.add_parser("relation", help="Связать позицию кассации с делом заявителя")
    relation_sub = relation.add_subparsers(dest="relation_command", required=True)
    relation_classify = relation_sub.add_parser(
        "classify", help="Классифицировать проверенную позицию на текущем fingerprint"
    )
    relation_classify.add_argument("--position-card", required=True)
    relation_classify.add_argument("--comparison", required=True)
    relation_classify.add_argument("--applicant-position", required=True)
    relation_classify.add_argument("--workspace", required=True)
    relation_classify.add_argument("--reviewer", required=True)
    relation_classify.add_argument("--reviewed-at", required=True)
    relation_classify.set_defaults(func=cmd_relation_classify)

    queue = sub.add_parser("queue", help="Собрать объяснимую очередь проверки")
    queue_sub = queue.add_subparsers(dest="queue_command", required=True)
    queue_build = queue_sub.add_parser(
        "build", help="Сохранить каждого кандидата и объяснить его статус"
    )
    queue_build.add_argument("--candidates", required=True)
    queue_build.add_argument("--resolutions")
    queue_build.add_argument("--quotas", help="JSON-квоты по court_id, stratum_id и lane")
    queue_build.add_argument("--workspace")
    queue_build.set_defaults(func=cmd_queue_build)

    adverse = sub.add_parser("adverse", help="Проверить неблагоприятные дорожки")
    adverse_sub = adverse.add_subparsers(dest="adverse_command", required=True)
    adverse_build = adverse_sub.add_parser(
        "build", help="Собрать четыре раскрытых adverse bucket"
    )
    adverse_build.add_argument("--cards", required=True)
    adverse_build.add_argument(
        "--completed-buckets", nargs="+", choices=ADVERSE_BUCKETS, required=True
    )
    adverse_build.add_argument(
        "--searched-buckets", nargs="+", choices=ADVERSE_BUCKETS, required=True
    )
    adverse_build.add_argument("--workspace")
    adverse_build.add_argument("--executed-query-ids", required=True)
    adverse_build.add_argument("--unresolved-segments", required=True)
    adverse_build.add_argument("--maximum-claim-effects", required=True)
    adverse_build.set_defaults(func=cmd_adverse_build)

    bridge = sub.add_parser("bridge", help="Проверить нормативный мост к жалобе")
    bridge_sub = bridge.add_subparsers(dest="bridge_command", required=True)
    bridge_check = bridge_sub.add_parser(
        "check", help="Проверить три звена и обычные средства защиты"
    )
    bridge_check.add_argument("--input", required=True)
    bridge_check.add_argument("--workspace")
    bridge_check.add_argument("--maximum-permitted-claim")
    bridge_check.set_defaults(func=cmd_bridge_check)

    status = sub.add_parser("status", help="Показать один fail-closed статус исследования")
    status.add_argument("--workspace", required=True)
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="Сформировать автономный HTML-отчёт")
    report.add_argument("--workspace", required=True)
    report.add_argument("--model", help="Готовая JSON-модель; иначе собирается из workspace")
    report.add_argument("--html")
    report.add_argument("--manifest")
    report.set_defaults(func=cmd_report)

    handoff = sub.add_parser("handoff", help="Передать типизированный проверяемый результат")
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_create = handoff_sub.add_parser("create", help="Создать content-bound handoff")
    handoff_create.add_argument("--workspace", required=True)
    handoff_create.add_argument("--target-skill", required=True)
    handoff_create.add_argument(
        "--payload-type",
        choices=(
            "unproven_research_questions",
            "approved_bounded_findings",
            "authority_cards",
            "selected_authorities",
        ),
        required=True,
    )
    handoff_create.add_argument("--payload", required=True)
    handoff_create.add_argument("--limitations")
    handoff_create.add_argument("--limitation", action="append", default=[])
    handoff_create.add_argument("--run-id")
    handoff_create.add_argument("--created-at")
    handoff_create.add_argument("--output")
    handoff_create.set_defaults(func=cmd_handoff_create)
    handoff_check = handoff_sub.add_parser("check", help="Проверить handoff и его хеши")
    handoff_check.add_argument("--input", required=True)
    handoff_check.add_argument("--workspace")
    handoff_check.add_argument("--expected-target")
    handoff_check.set_defaults(func=cmd_handoff_check)
    handoff_import = handoff_sub.add_parser("import", help="Идемпотентно добавить handoff в inbox")
    handoff_import.add_argument("--input", required=True)
    handoff_import.add_argument("--ledger", required=True)
    handoff_import.add_argument("--workspace")
    handoff_import.add_argument("--expected-target")
    handoff_import.set_defaults(func=cmd_handoff_import)

    cache = sub.add_parser("cache", help="Управлять локальным публичным корпусом")
    cache_sub = cache.add_subparsers(dest="cache_command", required=True)
    cache_init = cache_sub.add_parser("init", help="Создать SQLite-кэш и object store")
    cache_init.add_argument("--root", required=True)
    cache_init.set_defaults(func=cmd_cache_init)
    cache_seed = cache_sub.add_parser("register-seed", help="Добавить публичный URL seed")
    cache_seed.add_argument("--root", required=True)
    cache_seed.add_argument("--url", required=True)
    cache_seed.add_argument("--role", default="official_user_seed")
    cache_seed.set_defaults(func=cmd_cache_register_seed)
    cache_ingest = cache_sub.add_parser(
        "ingest", help="Добавить проверенный публичный snapshot и его текст"
    )
    cache_ingest.add_argument("--root", required=True)
    cache_ingest.add_argument("--seed-id", required=True)
    cache_ingest.add_argument("--raw", required=True)
    cache_ingest.add_argument("--content-type")
    cache_ingest.add_argument("--fetched-at", required=True)
    cache_ingest.add_argument("--parser-manifest", required=True)
    cache_ingest.add_argument("--text")
    cache_ingest.set_defaults(func=cmd_cache_ingest)
    cache_pin = cache_sub.add_parser(
        "pin-run", help="Неизменяемо закрепить snapshots за публичным запуском"
    )
    cache_pin.add_argument("--root", required=True)
    cache_pin.add_argument("--run-id", required=True)
    cache_pin.add_argument("--snapshot", action="append", required=True)
    cache_pin.set_defaults(func=cmd_cache_pin_run)
    cache_export = cache_sub.add_parser(
        "export-run", help="Экспортировать переносимый public-only пакет"
    )
    cache_export.add_argument("--root", required=True)
    cache_export.add_argument("--run-id", required=True)
    cache_export.add_argument("--output", required=True)
    cache_export.set_defaults(func=cmd_cache_export_run)
    cache_import = cache_sub.add_parser(
        "import-run", help="Проверить и импортировать переносимый public-only пакет"
    )
    cache_import.add_argument("--root", required=True)
    cache_import.add_argument("--input", required=True)
    cache_import.set_defaults(func=cmd_cache_import_run)
    cache_search = cache_sub.add_parser("search", help="Искать только в локально индексированном тексте")
    cache_search.add_argument("--root", required=True)
    cache_search.add_argument("--query", required=True)
    cache_search.add_argument("--limit", type=int, default=100)
    cache_search.set_defaults(func=cmd_cache_search)
    cache_refresh = cache_sub.add_parser("refresh-plan", help="Составить план обновления публичных seed")
    cache_refresh.add_argument("--root", required=True)
    cache_refresh.add_argument("--as-of", required=True)
    cache_refresh.add_argument("--max-age-seconds", type=int, required=True)
    cache_refresh.set_defaults(func=cmd_cache_refresh_plan)

    cache_funnel = cache_sub.add_parser(
        "funnel", help="Записать или показать этапы получения полного текста"
    )
    cache_funnel_sub = cache_funnel.add_subparsers(
        dest="cache_funnel_command", required=True
    )
    cache_funnel_record = cache_funnel_sub.add_parser(
        "record", help="Записать проверяемый переход одной цепочки"
    )
    cache_funnel_record.add_argument("--root", required=True)
    cache_funnel_record.add_argument("--chain-id", required=True)
    cache_funnel_record.add_argument(
        "--status",
        choices=(
            "enumerated", "card", "document_link", "payload_validated",
            "full_text_extracted", "indexed", "screened", "coded",
            "approved_independent_chain", "blocked", "retryable_error",
            "official_page_no_text", "unextractable", "ocr_pending",
            "human_verification_pending",
        ),
        required=True,
    )
    cache_funnel_record.add_argument("--snapshot-id")
    cache_funnel_record.add_argument("--reason")
    cache_funnel_record.add_argument("--source-role")
    cache_funnel_record.add_argument("--court-id")
    cache_funnel_record.add_argument("--period-id")
    cache_funnel_record.add_argument("--enumerator-id")
    cache_funnel_record.set_defaults(func=cmd_cache_funnel_record)
    cache_funnel_report = cache_funnel_sub.add_parser(
        "report", help="Показать воронку и разрезы источника, суда и периода"
    )
    cache_funnel_report.add_argument("--root", required=True)
    cache_funnel_report.set_defaults(func=cmd_cache_funnel_report)

    cache_treatment = cache_sub.add_parser(
        "treatment", help="Проверить последующее обращение суда с позицией"
    )
    cache_treatment_sub = cache_treatment.add_subparsers(
        dest="cache_treatment_command", required=True
    )
    cache_treatment_discover = cache_treatment_sub.add_parser(
        "discover", help="Создать кандидата связи без придания доказательственной силы"
    )
    cache_treatment_discover.add_argument("--root", required=True)
    cache_treatment_discover.add_argument("--source-chain-id", required=True)
    cache_treatment_discover.add_argument("--source-court-id", required=True)
    cache_treatment_discover.add_argument("--target-authority-id", required=True)
    cache_treatment_discover.add_argument("--target-kind", required=True)
    cache_treatment_discover.add_argument("--target-identity", required=True)
    cache_treatment_discover.add_argument(
        "--treatment-type",
        choices=(
            "applies", "follows", "distinguishes", "limits", "rejects",
            "supersedes", "unclear", "does_not_reach",
        ),
        required=True,
    )
    cache_treatment_discover.add_argument("--snapshot-id", required=True)
    cache_treatment_discover.add_argument("--supersedes-treatment-id")
    cache_treatment_discover.set_defaults(func=cmd_cache_treatment_discover)
    cache_treatment_review = cache_treatment_sub.add_parser(
        "review", help="Неизменяемо подтвердить или отклонить кандидата"
    )
    cache_treatment_review.add_argument("--root", required=True)
    cache_treatment_review.add_argument("--treatment-id", required=True)
    cache_treatment_review.add_argument(
        "--decision", choices=("verified", "rejected"), required=True
    )
    cache_treatment_review.add_argument("--reviewer", required=True)
    cache_treatment_review.add_argument("--quote")
    cache_treatment_review.add_argument("--locator")
    cache_treatment_review.add_argument("--speaker", choices=("court", "party", "unknown"))
    cache_treatment_review.add_argument("--confirmed-target-authority-id")
    cache_treatment_review.add_argument("--target-identity-confirmed", action="store_true")
    cache_treatment_review.add_argument("--reviewed-at")
    cache_treatment_review.set_defaults(func=cmd_cache_treatment_review)
    cache_treatment_list = cache_treatment_sub.add_parser("list", help="Показать связи")
    cache_treatment_list.add_argument("--root", required=True)
    cache_treatment_list.add_argument("--verified-only", action="store_true")
    cache_treatment_list.set_defaults(func=cmd_cache_treatment_list)
    cache_treatment_history = cache_treatment_sub.add_parser(
        "history", help="Показать неизменяемую историю проверки связи"
    )
    cache_treatment_history.add_argument("--root", required=True)
    cache_treatment_history.add_argument("--treatment-id", required=True)
    cache_treatment_history.set_defaults(func=cmd_cache_treatment_history)

    source = sub.add_parser("source", help="Сверить независимые маршруты официальных источников")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_reconcile = source_sub.add_parser(
        "reconcile", help="Сверить наблюдения без расширения заявленной полноты"
    )
    source_reconcile.add_argument("--manifests", required=True)
    source_reconcile.add_argument("--observations", required=True)
    source_reconcile.add_argument("--route-coverage", required=True)
    source_reconcile.add_argument("--requested-from", required=True)
    source_reconcile.add_argument("--requested-to", required=True)
    source_reconcile.add_argument("--workspace")
    source_reconcile.add_argument("--output")
    source_reconcile.set_defaults(func=cmd_source_reconcile)
    source_verify = source_sub.add_parser(
        "verify-manifest", help="Fail-closed проверить contract перечислителя"
    )
    source_verify.add_argument("--input", required=True)
    source_verify.add_argument("--output")
    source_verify.set_defaults(func=cmd_source_verify_manifest)
    source_promote = source_sub.add_parser(
        "promote-enumerator", help="Повысить маршрут только после всех verification gates"
    )
    source_promote.add_argument("--manifest", required=True)
    source_promote.add_argument("--verification", required=True)
    source_promote.add_argument("--reviewer", required=True)
    source_promote.add_argument("--reviewed-at")
    source_promote.add_argument("--output")
    source_promote.set_defaults(func=cmd_source_promote_enumerator)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
