"""Command-line orchestration for a self-contained local research run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _digest_existing(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _pre_thesis_evidence_sha256(workspace: Path) -> str:
    return _digest_existing(
        [
            workspace / "applicant-chain.json",
            workspace / "coding-decisions.jsonl",
            workspace / "exports" / "coverage.json",
            workspace / "exports" / "sources.jsonl",
            workspace / "exports" / "case-chains.jsonl",
            workspace / "adverse-review.json",
        ]
    )


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
    frozen = freeze_plan(plan, workspace)
    print(json.dumps({"plan_sha256": frozen["plan_sha256"], "frozen": True}, ensure_ascii=False))
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


def cmd_analyze(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    records = read_jsonl(workspace / "coding-decisions.jsonl")
    plan = latest_plan(workspace)
    coverage_path = workspace / "exports" / "coverage.json"
    coverage = read_json(coverage_path) if coverage_path.exists() else {"population_status": "insufficient_coverage"}
    coverage_status = (
        coverage.get("population_status", "insufficient_coverage")
        if coverage.get("collection_complete") is True
        else "insufficient_coverage"
    )
    result = analyze_reviewed_chains(records, coverage_status=coverage_status)
    result["plan_sha256"] = plan.get("plan_sha256")
    result["practice_is_evidence_of_meaning_not_review_object"] = True
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
    if args.thesis_file:
        candidates = read_jsonl(Path(args.thesis_file).expanduser().resolve())
    adverse: dict[str, Any] = {}
    if args.adverse_file:
        adverse = read_json(Path(args.adverse_file).expanduser().resolve())
        write_json(workspace / "adverse-review.json", adverse)
    elif (workspace / "adverse-review.json").exists():
        adverse = read_json(workspace / "adverse-review.json")
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
        for candidate in candidates:
            candidate["drafting_ready"] = True
        write_jsonl(workspace / "thesis-candidates.jsonl", candidates)

    evidence_files = [
        workspace / "analysis.json",
        workspace / "coding-decisions.jsonl",
        workspace / "exports" / "coverage.json",
        workspace / "adverse-review.json",
        workspace / "thesis-candidates.jsonl",
    ]
    decision = {
        "schema_version": "1.0",
        "decision": args.decision,
        "reviewer": args.reviewer,
        "plan_sha256": plan["plan_sha256"],
        "evidence_sha256": _digest_existing(evidence_files),
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
    decision_path = workspace / "human-decision.json"
    decision = read_json(decision_path) if decision_path.exists() else {}
    analysis_path = workspace / "analysis.json"
    analysis = read_json(analysis_path) if analysis_path.exists() else {}
    candidates = read_jsonl(workspace / "thesis-candidates.jsonl")
    candidate_approved = bool(candidates) and all(
        not validate_thesis_candidate(candidate) and candidate.get("drafting_ready") is True
        for candidate in candidates
    )
    evidence_files = [
        workspace / "analysis.json",
        workspace / "coding-decisions.jsonl",
        workspace / "exports" / "coverage.json",
        workspace / "adverse-review.json",
        workspace / "thesis-candidates.jsonl",
    ]
    approval_hashes_match = bool(decision) and decision.get("plan_sha256") == plan.get(
        "plan_sha256"
    ) and decision.get("evidence_sha256") == _digest_existing(evidence_files)
    return {
        "plan_frozen": plan.get("frozen") is True,
        "collection_complete": coverage.get("collection_complete") is True,
        "coding_complete": bool(coding) and all(not validate_coding_record(record) for record in coding),
        "adverse_review_complete": decision.get("adverse_review_complete") is True,
        "coverage_review_complete": decision.get("coverage_review_complete") is True,
        "human_approved": decision.get("decision") == "approved" and approval_hashes_match,
        "candidate_approved": candidate_approved and approval_hashes_match,
        "approval_hashes_match": approval_hashes_match,
        "maximum_permitted_claim": analysis.get("status", plan.get("maximum_claim_if_incomplete")),
    }


def cmd_validate(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    plan = latest_plan(workspace)
    errors = validate_plan({key: value for key, value in plan.items() if key not in {"frozen", "plan_sha256"}})
    state = _validation_state(workspace)
    if args.require_thesis_ready:
        proposed = args.thesis or "В наблюдаемом корпусе выявлен раскрытый в отчёте судебный смысл нормы."
        errors.extend(validate_thesis_readiness(state, proposed))
    report = {"schema_version": "1.0", "valid": not errors, "errors": errors, "state": state, "validated_at": utc_now()}
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
