"""Command-line orchestration for a self-contained local research run."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import stat
import struct
import sys
import tempfile
import textwrap
import unicodedata
import zipfile
from datetime import date, datetime, timezone
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
from .handoff_workbench import (
    artifact_sha256,
    bind_request_payload,
    build_approved_finding,
    build_artifact_manifest,
    build_selected_position_set_sha256,
    build_trusted_source_receipt,
    check_handoff,
    create_handoff,
    import_handoff,
)
from .public_corpus import PublicCorpus
from .practice_quality import (
    AUDIT_CODING_RECORD_FIELDS,
    AUDITED_CODING_FIELDS,
    CODING_AUDIT_REVIEW_IMPORT_RECEIPT_FIELDS,
    CODING_AUDIT_PLAN_FIELDS,
    NATIVE_AUDIT_QUEUE_FIELDS,
    NATIVE_AUDIT_SCREENING_FIELDS,
    NATIVE_AUDIT_CODEBOOK_VERSIONS,
    NATIVE_AUDIT_REVIEW_MATERIAL_FIELDS,
    analyze_chain_stage_propagation,
    assess_coding_reliability,
    assess_prefiling_refresh,
    build_coding_audit_plan,
    build_native_coding_audit_inputs,
    build_native_coding_audit_finalization,
    build_native_coding_review_import,
    build_uncertainty_profile,
    canonical_digest,
    NON_AUDITED_CODING_CONTENT_FIELDS,
)
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


_RUSSIAN_METAVARS = {
    "adjudications": "ФАЙЛ_РЕШЕНИЙ_ПО_РАСХОЖДЕНИЯМ",
    "adverse_file": "ФАЙЛ_НЕБЛАГОПРИЯТНЫХ_МАТЕРИАЛОВ",
    "answers": "ФАЙЛ_ОТВЕТОВ",
    "applicant": "ФАЙЛ_ДЕЛА_ЗАЯВИТЕЛЯ",
    "applicant_position": "ФАЙЛ_ПОЗИЦИИ_ЗАЯВИТЕЛЯ",
    "applicant_relations": "ФАЙЛ_СВЯЗЕЙ_С_ДЕЛОМ_ЗАЯВИТЕЛЯ",
    "as_of": "ДАТА_И_ВРЕМЯ_ISO",
    "audit_decisions": "ФАЙЛ_РЕШЕНИЙ_АУДИТА",
    "audit_import": "ПАПКА_ШТАТНОГО_ИМПОРТА",
    "audit_plan": "ФАЙЛ_ПЛАНА_АУДИТА",
    "baseline_corpus_digest": "ИСХОДНЫЙ_ХЕШ_КОРПУСА",
    "bundle": "ПАПКА_ПАКЕТА",
    "candidate": "ФАЙЛ_ДЕЛА_КАНДИДАТА",
    "candidates": "ФАЙЛ_КАНДИДАТОВ",
    "candidate_id": "ИДЕНТИФИКАТОР_КАНДИДАТА",
    "cards": "ФАЙЛ_КАРТОЧЕК",
    "chain_id": "ИДЕНТИФИКАТОР_ЦЕПОЧКИ",
    "checked_through": "ДАТА_И_ВРЕМЯ_ISO",
    "claim_id": "ИДЕНТИФИКАТОР_ТРЕБОВАНИЯ",
    "codebook_version": "ВЕРСИЯ_СПРАВОЧНИКА_КОДИРОВАНИЯ",
    "coding_reliability": "ФАЙЛ_НАДЁЖНОСТИ_КОДИРОВАНИЯ",
    "coding_audit_finalization_receipt": "ФАЙЛ_КВИТАНЦИИ_ФИНАЛИЗАЦИИ",
    "comparison": "ФАЙЛ_СОПОСТАВЛЕНИЯ",
    "comparisons": "ФАЙЛ_СОПОСТАВЛЕНИЙ",
    "confirmed_at": "ДАТА_И_ВРЕМЯ_ISO",
    "confirmed_target_authority_id": "ПОДТВЕРЖДЁННЫЙ_ИДЕНТИФИКАТОР_ИСТОЧНИКА",
    "content_type": "ТИП_СОДЕРЖИМОГО",
    "court_id": "ИДЕНТИФИКАТОР_СУДА",
    "created_at": "ДАТА_И_ВРЕМЯ_ISO",
    "current_corpus_digest": "ТЕКУЩИЙ_ХЕШ_КОРПУСА",
    "dpi": "РАЗРЕШЕНИЕ",
    "enumerator_id": "ИДЕНТИФИКАТОР_ПЕРЕЧИСЛИТЕЛЯ",
    "exclusion_sample_size": "РАЗМЕР_ВЫБОРКИ_ИСКЛЮЧЕНИЙ",
    "executed_query_ids": "ФАЙЛ_ИДЕНТИФИКАТОРОВ_ЗАПРОСОВ",
    "expected_target": "ОЖИДАЕМЫЙ_ПОЛУЧАТЕЛЬ",
    "expected_import_receipt_sha256": "СОХРАНЁННЫЙ_SHA256_КВИТАНЦИИ_ИМПОРТА",
    "expected_finalization_receipt_sha256": "СОХРАНЁННЫЙ_SHA256_ФИНАЛИЗАЦИИ",
    "expected_manifest_sha256": "СОХРАНЁННЫЙ_SHA256_МАНИФЕСТА",
    "expected_secondary_coder": "ОЖИДАЕМАЯ_МЕТКА_КОДИРОВЩИКА",
    "fetched_at": "ДАТА_И_ВРЕМЯ_ISO",
    "filing_cutoff": "ДАТА_И_ВРЕМЯ_ISO",
    "fingerprint_sha256": "ХЕШ_ОТПЕЧАТКА_ДЕЛА",
    "higher_authority_treatments": "ФАЙЛ_СВЯЗЕЙ_С_ВЫСШИМИ_ИНСТАНЦИЯМИ",
    "html": "ФАЙЛ_ОТЧЁТА",
    "input": "ВХОДНОЙ_ФАЙЛ",
    "inputs": "ВХОДНЫЕ_ФАЙЛЫ",
    "language": "ЯЗЫК",
    "ledger": "ФАЙЛ_РЕЕСТРА",
    "limit": "ПРЕДЕЛ",
    "limitation": "ОГРАНИЧЕНИЕ",
    "limitations": "ФАЙЛ_ОГРАНИЧЕНИЙ",
    "locator": "УКАЗАТЕЛЬ_МЕСТА",
    "manifest": "ФАЙЛ_МАНИФЕСТА",
    "manifests": "ФАЙЛ_МАНИФЕСТОВ",
    "maximum_claim_effects": "ФАЙЛ_ПРЕДЕЛЬНЫХ_ПОСЛЕДСТВИЙ_ВЫВОДА",
    "maximum_permitted_claim": "ПРЕДЕЛЬНО_ДОПУСТИМЫЙ_ВЫВОД",
    "max_age_seconds": "МАКСИМАЛЬНЫЙ_ВОЗРАСТ_В_СЕКУНДАХ",
    "max_attempts": "МАКСИМУМ_ПОПЫТОК",
    "max_source_tasks": "МАКСИМУМ_ЗАДАЧ_ИСТОЧНИКА",
    "max_tasks": "МАКСИМУМ_ЗАДАЧ",
    "model": "ФАЙЛ_МОДЕЛИ",
    "notes": "ПРИМЕЧАНИЯ",
    "observations": "ФАЙЛ_НАБЛЮДЕНИЙ",
    "output": "ВЫХОДНОЙ_ФАЙЛ",
    "output_dir": "НОВАЯ_ПАПКА_АУДИТА",
    "parser_manifest": "ФАЙЛ_МАНИФЕСТА_ПАРСЕРА",
    "payload": "ФАЙЛ_ДАННЫХ",
    "period_id": "ИДЕНТИФИКАТОР_ПЕРИОДА",
    "plan": "ФАЙЛ_ПЛАНА",
    "plan_sha256": "ХЕШ_ПЛАНА",
    "position_card": "ФАЙЛ_КАРТОЧКИ_ПОЗИЦИИ",
    "position_cards": "ФАЙЛ_КАРТОЧЕК_ПОЗИЦИЙ",
    "position_card_id": "ИДЕНТИФИКАТОР_КАРТОЧКИ",
    "primary_decisions": "ФАЙЛ_ОСНОВНЫХ_РЕШЕНИЙ",
    "quality_binding": "ФАЙЛ_ПРИВЯЗКИ_КАЧЕСТВА",
    "query": "ЗАПРОС",
    "query_id": "ИДЕНТИФИКАТОР_ЗАПРОСА",
    "quotas": "ФАЙЛ_КВОТ",
    "quote": "ЦИТАТА",
    "raw": "ИСХОДНЫЙ_ФАЙЛ",
    "reason": "ОСНОВАНИЕ",
    "refresh_plan": "ФАЙЛ_ПЛАНА_ОБНОВЛЕНИЯ",
    "request": "ФАЙЛ_ЗАПРОСА",
    "requested_from": "ДАТА_ГГГГ-ММ-ДД",
    "requested_to": "ДАТА_ГГГГ-ММ-ДД",
    "required_chain_id": "ОБЯЗАТЕЛЬНАЯ_ЦЕПОЧКА",
    "resolutions": "ФАЙЛ_РЕШЕНИЙ",
    "reviewed_at": "ДАТА_И_ВРЕМЯ_ISO",
    "reviewer": "ПРОВЕРЯЮЩИЙ",
    "role": "РОЛЬ",
    "root": "КОРНЕВАЯ_ПАПКА",
    "route_coverage": "ФАЙЛ_ОХВАТА_МАРШРУТОВ",
    "run_id": "ИДЕНТИФИКАТОР_ЗАПУСКА",
    "sample_size": "РАЗМЕР_ВЫБОРКИ",
    "screening_candidates": "ФАЙЛ_КАНДИДАТОВ_ОТБОРА",
    "secondary_coding": "ФАЙЛ_ВТОРИЧНОЙ_РАЗМЕТКИ",
    "seed_id": "ИДЕНТИФИКАТОР_ИСТОЧНИКА",
    "snapshot": "ИДЕНТИФИКАТОР_СНИМКА",
    "snapshot_id": "ИДЕНТИФИКАТОР_СНИМКА",
    "source_chain_id": "ИДЕНТИФИКАТОР_ИСХОДНОЙ_ЦЕПОЧКИ",
    "source_court_id": "ИДЕНТИФИКАТОР_ИСХОДНОГО_СУДА",
    "source_reconciliation": "ФАЙЛ_СВЕРКИ_ИСТОЧНИКОВ",
    "source_role": "РОЛЬ_ИСТОЧНИКА",
    "source_workspace": "РАБОЧАЯ_ПАПКА_ИСТОЧНИКА",
    "subject_evidence_sha256": "ХЕШ_ПРЕДМЕТНЫХ_ДОКАЗАТЕЛЬСТВ",
    "supersedes_treatment_id": "ИДЕНТИФИКАТОР_ЗАМЕНЯЕМОЙ_СВЯЗИ",
    "target_authority_id": "ИДЕНТИФИКАТОР_ЦЕЛЕВОГО_АКТА",
    "target_identity": "ФАЙЛ_ДАННЫХ_ЦЕЛИ",
    "target_kind": "ВИД_ЦЕЛИ",
    "target_skill": "ЦЕЛЕВОЙ_НАВЫК",
    "temporal_analysis": "ФАЙЛ_ВРЕМЕННОГО_АНАЛИЗА",
    "text": "ТЕКСТОВЫЙ_ФАЙЛ",
    "thesis": "ТЕЗИС",
    "thesis_file": "ФАЙЛ_ТЕЗИСА",
    "trajectories": "ФАЙЛ_ТРАЕКТОРИЙ",
    "treatments": "ФАЙЛ_СВЯЗЕЙ",
    "treatment_id": "ИДЕНТИФИКАТОР_СВЯЗИ",
    "unresolved_segments": "ФАЙЛ_НЕРАЗРЕШЁННЫХ_СЕГМЕНТОВ",
    "url": "АДРЕС",
    "verification": "ФАЙЛ_ПРОВЕРКИ",
    "workspace": "РАБОЧАЯ_ПАПКА",
}


class RussianHelpFormatter(argparse.HelpFormatter):
    """Wrap prose without splitting executable names at their hyphens."""

    def _split_lines(self, text: str, width: int) -> list[str]:
        normalized = self._whitespace_matcher.sub(" ", text).strip()
        return textwrap.wrap(
            normalized,
            width,
            break_long_words=False,
            break_on_hyphens=False,
        )

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        normalized = self._whitespace_matcher.sub(" ", text).strip()
        return "\n".join(
            indent + line
            for line in textwrap.wrap(
                normalized,
                width,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )


class RussianExampleHelpFormatter(RussianHelpFormatter):
    """Wrap prose but preserve a deliberately line-broken shell example."""

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        prose, marker, example = text.partition("\n\nПример команды:\n")
        rendered = super()._fill_text(prose, width, indent)
        if not marker:
            return rendered
        example_lines = "\n".join(
            indent + line for line in example.rstrip().splitlines()
        )
        return f"{rendered}\n\n{indent}Пример команды:\n{example_lines}"


class RussianHelpArgumentParser(argparse.ArgumentParser):
    """Render Russian help and require exact option names."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "Использование:", 1)

    @staticmethod
    def _translate_parse_error(message: str) -> str:
        patterns = (
            (
                r"^the following arguments are required: (.+)$",
                "не указаны обязательные аргументы: {0}",
            ),
            (r"^unrecognized arguments: (.+)$", "неизвестные аргументы: {0}"),
            (
                r"^argument (.+): expected one argument$",
                "аргумент {0}: требуется одно значение",
            ),
            (
                r"^argument (.+): expected at least one argument$",
                "аргумент {0}: требуется хотя бы одно значение",
            ),
            (
                r"^one of the arguments (.+) is required$",
                "нужно указать один из аргументов: {0}",
            ),
            (
                r"^argument (.+): not allowed with argument (.+)$",
                "аргумент {0} нельзя использовать вместе с аргументом {1}",
            ),
            (
                r"^argument (.+): invalid choice: (.+) \(choose from (.+)\)$",
                "аргумент {0}: недопустимое значение {1} (допустимы: {2})",
            ),
            (
                r"^argument (.+): invalid (.+) value: (.+)$",
                "аргумент {0}: недопустимое значение {2}",
            ),
            (
                r"^ambiguous option: (.+) could match (.+)$",
                "неоднозначный параметр {0}; возможные варианты: {1}",
            ),
        )
        for pattern, template in patterns:
            match = re.fullmatch(pattern, message)
            if match is not None:
                return template.format(*match.groups())
        if re.search(r"[А-Яа-яЁё]", message) is not None:
            return message
        return (
            "не удалось разобрать параметры команды; проверьте их имена и "
            "значения через --help"
        )

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: ошибка: {self._translate_parse_error(message)}\n")

    def format_help(self) -> str:
        positional_heading = (
            "команды:"
            if any(
                isinstance(action, argparse._SubParsersAction)
                for action in self._actions
            )
            else "позиционные аргументы:"
        )
        original_metavars: list[tuple[argparse.Action, Any]] = []
        for action in self._actions:
            if (
                action.help == argparse.SUPPRESS
                or action.metavar is not None
                or action.nargs == 0
                or action.choices is not None
            ):
                continue
            original_metavars.append((action, action.metavar))
            action.metavar = _RUSSIAN_METAVARS.get(action.dest, "ЗНАЧЕНИЕ")

        try:
            rendered = super().format_help()
        finally:
            for action, metavar in original_metavars:
                action.metavar = metavar

        return (
            rendered.replace("usage:", "Использование:", 1)
            .replace("positional arguments:", positional_heading)
            .replace("optional arguments:", "необязательные аргументы:")
            .replace("options:", "параметры:")
            .replace(
                "show this help message and exit",
                "показать эту справку и выйти",
            )
        )


def _populate_subparser_descriptions(parser: argparse.ArgumentParser) -> None:
    """Use each command's short help as its own explanatory help heading."""

    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        help_by_name = {
            choice.dest: choice.help
            for choice in action._choices_actions
            if isinstance(choice.help, str) and choice.help.strip()
        }
        for name, child in action.choices.items():
            if child.description is None and name in help_by_name:
                child.description = help_by_name[name]
            _populate_subparser_descriptions(child)


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
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: строка {number} должна быть JSON-объектом")
        records.append(value)
    return records


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"Недопустимая JSON-константа {value}; NaN/Infinity запрещены.")


def _closed_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON содержит повторяющийся ключ.")
        result[key] = value
    return result


def _strict_json_loads(text: str, *, source: Path) -> Any:
    try:
        return json.loads(
            text,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_closed_json_object,
        )
    except (json.JSONDecodeError, UnicodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{source}: неверный строгий JSON: {exc}") from exc


def _strict_json_file(path: Path) -> tuple[Any, bytes]:
    if not path.is_file():
        raise ValueError(f"Не найден обязательный файл: {path}.")
    content = path.read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: требуется корректный UTF-8.") from exc
    return _strict_json_loads(text, source=path), content


def _strict_jsonl_file(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    if not path.is_file():
        raise ValueError(f"Не найден обязательный файл: {path}.")
    content = path.read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: требуется корректный UTF-8.") from exc
    records: list[dict[str, Any]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        value = _strict_json_loads(line, source=path)
        if not isinstance(value, dict):
            raise ValueError(f"{path}: строка {number} должна быть JSON-объектом.")
        records.append(value)
    return records, content


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_jsonl_bytes(records: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(_canonical_json_bytes(dict(record)) for record in records)


_AUDIT_BUNDLE_CONTENT_PATHS = (
    "screening-candidates.audit.jsonl",
    "primary-decisions.audit.jsonl",
    "coding-audit-plan.json",
    "secondary-review-queue.jsonl",
    "secondary-coding-template.jsonl",
    "independent-review-packet.zip",
)
_AUDIT_BUNDLE_PATHS = frozenset(
    (*_AUDIT_BUNDLE_CONTENT_PATHS, "coding-audit-inputs-manifest.json")
)
_BLINDED_REVIEW_PACKET_PATHS = (
    "CODING-BRIEF.json",
    "CODING-CODEBOOK.md",
    "REVIEW-INSTRUCTIONS.md",
    "review-materials.jsonl",
    "review-packet-manifest.json",
    "secondary-coding-template.jsonl",
)
_AUDIT_IMPORT_FILE_LIMITS = {
    "coding-audit-inputs-manifest.json": 2 * 1024 * 1024,
    "coding-audit-plan.json": 4 * 1024 * 1024,
    "independent-review-packet.zip": 256 * 1024 * 1024,
    "primary-decisions.audit.jsonl": 64 * 1024 * 1024,
    "screening-candidates.audit.jsonl": 64 * 1024 * 1024,
    "secondary-coding-template.jsonl": 64 * 1024 * 1024,
    "secondary-review-queue.jsonl": 64 * 1024 * 1024,
}
_AUDIT_IMPORT_SECONDARY_LIMIT = 64 * 1024 * 1024
_AUDIT_FINALIZATION_RESOLUTIONS_LIMIT = 64 * 1024 * 1024
_AUDIT_REVIEW_IMPORT_PATHS = frozenset(
    {
        "audit-decisions.jsonl",
        "coding-audit-review-import-receipt.json",
    }
)
_AUDIT_REVIEW_IMPORT_FILE_LIMITS = {
    "audit-decisions.jsonl": 64 * 1024 * 1024,
    "coding-audit-review-import-receipt.json": 8 * 1024 * 1024,
}
_AUDIT_IMPORT_CODEBOOK_LIMIT = 2 * 1024 * 1024
_AUDIT_IMPORT_ZIP_MEMBER_LIMIT = 192 * 1024 * 1024
_AUDIT_IMPORT_ZIP_TOTAL_LIMIT = 256 * 1024 * 1024
_AUDIT_IMPORT_ZIP_CENTRAL_DIRECTORY_LIMIT = 64 * 1024
_AUDIT_IMPORT_MAX_RECORDS = 10_000
_AUDIT_IMPORT_MAX_PHYSICAL_LINES = 20_000
_AUDIT_IMPORT_MAX_JSON_DEPTH = 24
_AUDIT_IMPORT_MAX_JSON_NODES = 400_000
_AUDIT_IMPORT_MAX_COLLECTION_ITEMS = 20_000
_AUDIT_IMPORT_MAX_STRING_BYTES = 16 * 1024 * 1024
_NATIVE_AUDIT_CANDIDATE_ID_PATTERN = re.compile(
    r"\Aaudit-candidate-sha256:[0-9a-f]{64}\Z"
)


def _is_native_audit_candidate_id(value: Any) -> bool:
    return isinstance(value, str) and bool(
        _NATIVE_AUDIT_CANDIDATE_ID_PATTERN.fullmatch(value)
    )


def _stable_file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        stat.S_IMODE(value.st_mode),
        value.st_uid,
        value.st_gid,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _stable_directory_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        stat.S_IMODE(value.st_mode),
        value.st_uid,
        value.st_gid,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_bounded_regular_fd(
    descriptor: int,
    *,
    label: str,
    byte_limit: int,
    path_stat: os.stat_result | None = None,
) -> tuple[bytes, tuple[int, ...]]:
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{label}: требуется обычный файл.")
    if before.st_nlink != 1:
        raise ValueError(f"{label}: вход через жёсткую ссылку запрещён.")
    if before.st_size < 0 or before.st_size > byte_limit:
        raise ValueError(f"{label}: размер превышает безопасный предел.")
    if path_stat is not None and (
        path_stat.st_dev != before.st_dev or path_stat.st_ino != before.st_ino
    ):
        raise ValueError(f"{label}: путь изменился во время открытия.")
    chunks: list[bytes] = []
    remaining = before.st_size
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            raise ValueError(f"{label}: файл изменился во время чтения.")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise ValueError(f"{label}: файл вырос во время чтения.")
    after = os.fstat(descriptor)
    identity = _stable_file_identity(before)
    if _stable_file_identity(after) != identity:
        raise ValueError(f"{label}: файл изменился во время чтения.")
    content = b"".join(chunks)
    if len(content) != before.st_size:
        raise ValueError(f"{label}: размер прочитанного содержимого не совпадает.")
    return content, identity


def _no_follow_open_flags() -> int:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if os.name != "nt" and not no_follow:
        raise ValueError(
            "Среда выполнения не поддерживает безопасное открытие O_NOFOLLOW."
        )
    nonblocking = getattr(os, "O_NONBLOCK", 0) if os.name != "nt" else 0
    return os.O_RDONLY | no_follow | nonblocking | getattr(os, "O_CLOEXEC", 0)


def _capture_regular_file(
    path: Path,
    *,
    label: str,
    byte_limit: int,
) -> dict[str, Any]:
    try:
        path_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_stat.st_mode):
            raise ValueError(f"{label}: требуется обычный файл.")
        descriptor = os.open(path, _no_follow_open_flags())
    except OSError as exc:
        raise ValueError(f"{label}: файл отсутствует или небезопасен.") from exc
    try:
        content, identity = _read_bounded_regular_fd(
            descriptor,
            label=label,
            byte_limit=byte_limit,
            path_stat=path_stat,
        )
    finally:
        os.close(descriptor)
    return {"content": content, "identity": identity}


def _bounded_directory_names(
    descriptor: int, *, maximum_entries: int, label: str
) -> list[str]:
    names: list[str] = []
    try:
        with os.scandir(descriptor) as entries:
            for entry in entries:
                if len(names) >= maximum_entries:
                    raise ValueError(f"{label}: слишком много записей в папке.")
                names.append(entry.name)
    except OSError as exc:
        raise ValueError(f"{label}: не удалось безопасно прочитать папку.") from exc
    return names


def _capture_audit_bundle_descriptor(descriptor: int) -> dict[str, Any]:
    directory_stat = os.fstat(descriptor)
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ValueError("--bundle должен быть обычной папкой.")
    names = _bounded_directory_names(
        descriptor,
        maximum_entries=len(_AUDIT_BUNDLE_PATHS),
        label="--bundle",
    )
    if set(names) != _AUDIT_BUNDLE_PATHS:
        raise ValueError(
            "--bundle должен содержать ровно семь файлов текущего контракта."
        )
    files: dict[str, dict[str, Any]] = {}
    for name in sorted(names):
        try:
            child_stat = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(child_stat.st_mode):
                raise ValueError(f"{name}: требуется обычный файл.")
            child = os.open(name, _no_follow_open_flags(), dir_fd=descriptor)
        except OSError as exc:
            raise ValueError(f"{name}: файл отсутствует или небезопасен.") from exc
        try:
            content, identity = _read_bounded_regular_fd(
                child,
                label=name,
                byte_limit=_AUDIT_IMPORT_FILE_LIMITS[name],
                path_stat=child_stat,
            )
        finally:
            os.close(child)
        files[name] = {"content": content, "identity": identity}
    final_directory_stat = os.fstat(descriptor)
    directory_identity = _stable_directory_identity(directory_stat)
    if _stable_directory_identity(final_directory_stat) != directory_identity:
        raise ValueError("--bundle изменился во время чтения.")
    return {"directory_identity": directory_identity, "files": files}


def _capture_audit_bundle_at(parent_descriptor: int, bundle_name: str) -> dict[str, Any]:
    if not bundle_name or Path(bundle_name).name != bundle_name:
        raise ValueError("--bundle имеет небезопасное имя папки.")
    flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
    try:
        path_stat = os.stat(
            bundle_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        descriptor = os.open(bundle_name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise ValueError("--bundle должен быть существующей безопасной папкой.") from exc
    try:
        directory_stat = os.fstat(descriptor)
        if not stat.S_ISDIR(directory_stat.st_mode) or (
            path_stat.st_dev != directory_stat.st_dev
            or path_stat.st_ino != directory_stat.st_ino
        ):
            raise ValueError("--bundle изменился во время открытия.")
        return _capture_audit_bundle_descriptor(descriptor)
    finally:
        os.close(descriptor)


def _open_audit_bundle_parent(path: Path) -> tuple[int, str, dict[str, Any]]:
    bundle_name = path.name
    if not bundle_name or bundle_name in {".", ".."}:
        raise ValueError("--bundle должен называть отдельную папку.")
    flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
    parent_descriptor: int | None = None
    try:
        path_stat = os.stat(path, follow_symlinks=False)
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError("--bundle должен быть существующей безопасной папкой.") from exc
    try:
        directory_stat = os.fstat(descriptor)
        if not stat.S_ISDIR(directory_stat.st_mode) or (
            path_stat.st_dev != directory_stat.st_dev
            or path_stat.st_ino != directory_stat.st_ino
        ):
            raise ValueError("--bundle изменился во время открытия.")
        parent_descriptor = os.open("..", flags, dir_fd=descriptor)
        parent_stat = os.fstat(parent_descriptor)
        if not stat.S_ISDIR(parent_stat.st_mode):
            raise ValueError("Родитель --bundle не является обычной папкой.")
        entry_stat = os.stat(
            bundle_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        if (
            entry_stat.st_dev != directory_stat.st_dev
            or entry_stat.st_ino != directory_stat.st_ino
        ):
            raise ValueError("--bundle перемещён во время открытия.")
        capture = _capture_audit_bundle_descriptor(descriptor)
    except Exception:
        if parent_descriptor is not None:
            os.close(parent_descriptor)
        raise
    finally:
        os.close(descriptor)
    return parent_descriptor, bundle_name, capture


def _capture_audit_bundle(path: Path) -> dict[str, Any]:
    parent_descriptor, bundle_name, _ = _open_audit_bundle_parent(path)
    try:
        return _capture_audit_bundle_at(parent_descriptor, bundle_name)
    finally:
        os.close(parent_descriptor)


def _capture_audit_review_import_descriptor(descriptor: int) -> dict[str, Any]:
    """Capture an exact native Release15 import without following mutable names."""

    directory_stat = os.fstat(descriptor)
    effective_uid = (
        os.geteuid()
        if hasattr(os, "geteuid")
        else os.getuid()
        if hasattr(os, "getuid")
        else directory_stat.st_uid
    )
    if (
        not stat.S_ISDIR(directory_stat.st_mode)
        or stat.S_IMODE(directory_stat.st_mode) != 0o700
        or (os.name == "posix" and directory_stat.st_uid != effective_uid)
    ):
        raise ValueError(
            "--audit-import должен быть приватной папкой штатного импорта с режимом 0700."
        )
    _assert_darwin_fd_has_no_extended_acl(
        descriptor,
        object_label="Каталог штатного импорта решений аудита",
    )
    directory_identity = _stable_directory_identity(directory_stat)
    names = _bounded_directory_names(
        descriptor,
        maximum_entries=len(_AUDIT_REVIEW_IMPORT_PATHS),
        label="--audit-import",
    )
    if set(names) != _AUDIT_REVIEW_IMPORT_PATHS:
        raise ValueError(
            "--audit-import должен содержать ровно audit-decisions.jsonl и "
            "coding-audit-review-import-receipt.json."
        )
    files: dict[str, dict[str, Any]] = {}
    for name in sorted(names):
        try:
            path_stat = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if (
                not stat.S_ISREG(path_stat.st_mode)
                or path_stat.st_nlink != 1
                or stat.S_IMODE(path_stat.st_mode) != 0o600
                or (os.name == "posix" and path_stat.st_uid != effective_uid)
            ):
                raise ValueError(
                    f"{name}: требуется приватный обычный файл режима 0600 без "
                    "жёстких ссылок."
                )
            child = os.open(name, _no_follow_open_flags(), dir_fd=descriptor)
        except OSError as exc:
            raise ValueError(f"{name}: файл импорта отсутствует или небезопасен.") from exc
        try:
            _assert_darwin_fd_has_no_extended_acl(
                child,
                object_label="Файл штатного импорта решений аудита",
            )
            content, identity = _read_bounded_regular_fd(
                child,
                label=name,
                byte_limit=_AUDIT_REVIEW_IMPORT_FILE_LIMITS[name],
                path_stat=path_stat,
            )
        finally:
            os.close(child)
        files[name] = {"content": content, "identity": identity}
    if _stable_directory_identity(os.fstat(descriptor)) != directory_identity:
        raise ValueError("--audit-import изменился во время чтения.")
    return {"directory_identity": directory_identity, "files": files}


def _capture_private_native_audit_bundle_at(
    parent_descriptor: int,
    bundle_name: str,
) -> dict[str, Any]:
    """Revalidate the modes, owner and ACLs promised by the native publisher."""

    capture = _capture_audit_bundle_at(parent_descriptor, bundle_name)
    flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(bundle_name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise ValueError("--bundle нельзя повторно открыть безопасно.") from exc
    try:
        directory_stat = os.fstat(descriptor)
        effective_uid = (
            os.geteuid()
            if hasattr(os, "geteuid")
            else os.getuid()
            if hasattr(os, "getuid")
            else directory_stat.st_uid
        )
        if (
            not stat.S_ISDIR(directory_stat.st_mode)
            or stat.S_IMODE(directory_stat.st_mode) != 0o700
            or (os.name == "posix" and directory_stat.st_uid != effective_uid)
            or _stable_directory_identity(directory_stat)
            != capture["directory_identity"]
        ):
            raise ValueError(
                "--bundle должен быть приватной папкой штатного пакета с режимом 0700."
            )
        _assert_darwin_fd_has_no_extended_acl(
            descriptor,
            object_label="Каталог штатного пакета аудита",
        )
        for name, captured in capture["files"].items():
            child_stat = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if (
                not stat.S_ISREG(child_stat.st_mode)
                or child_stat.st_nlink != 1
                or stat.S_IMODE(child_stat.st_mode) != 0o600
                or (os.name == "posix" and child_stat.st_uid != effective_uid)
                or _stable_file_identity(child_stat) != captured["identity"]
            ):
                raise ValueError(
                    f"{name}: файл штатного пакета должен иметь режим 0600, "
                    "одного владельца и не иметь жёстких ссылок."
                )
            child = os.open(name, _no_follow_open_flags(), dir_fd=descriptor)
            try:
                _assert_darwin_fd_has_no_extended_acl(
                    child,
                    object_label="Файл штатного пакета аудита",
                )
                if _stable_file_identity(os.fstat(child)) != captured["identity"]:
                    raise ValueError(f"{name}: файл пакета изменился при проверке ACL.")
            finally:
                os.close(child)
        if _stable_directory_identity(os.fstat(descriptor)) != capture[
            "directory_identity"
        ]:
            raise ValueError("--bundle изменился во время проверки приватности.")
    finally:
        os.close(descriptor)
    return capture


def _capture_audit_review_import_at(
    parent_descriptor: int,
    import_name: str,
) -> dict[str, Any]:
    if not import_name or Path(import_name).name != import_name:
        raise ValueError("--audit-import имеет небезопасное имя папки.")
    flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
    try:
        path_stat = os.stat(
            import_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        descriptor = os.open(import_name, flags, dir_fd=parent_descriptor)
    except OSError as exc:
        raise ValueError(
            "--audit-import должен быть существующей безопасной соседней папкой."
        ) from exc
    try:
        directory_stat = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(directory_stat.st_mode)
            or path_stat.st_dev != directory_stat.st_dev
            or path_stat.st_ino != directory_stat.st_ino
        ):
            raise ValueError("--audit-import изменился во время открытия.")
        capture = _capture_audit_review_import_descriptor(descriptor)
        final_path_stat = os.stat(
            import_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            final_path_stat.st_dev != directory_stat.st_dev
            or final_path_stat.st_ino != directory_stat.st_ino
        ):
            raise ValueError("--audit-import перемещён или заменён во время чтения.")
        return capture
    finally:
        os.close(descriptor)


def _capture_private_finalization_resolutions_at(
    parent_descriptor: int,
    resolutions_name: str,
) -> dict[str, Any]:
    """Capture one private sibling resolution file through the held parent."""

    if not resolutions_name or Path(resolutions_name).name != resolutions_name:
        raise ValueError("--resolutions имеет небезопасное имя файла.")
    effective_uid = (
        os.geteuid()
        if hasattr(os, "geteuid")
        else os.getuid()
        if hasattr(os, "getuid")
        else None
    )
    try:
        path_stat = os.stat(
            resolutions_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(path_stat.st_mode)
            or path_stat.st_nlink != 1
            or stat.S_IMODE(path_stat.st_mode) != 0o600
            or (
                os.name == "posix"
                and effective_uid is not None
                and path_stat.st_uid != effective_uid
            )
        ):
            raise ValueError(
                "--resolutions должен быть приватным обычным файлом режима 0600 "
                "текущего пользователя без жёстких ссылок."
            )
        descriptor = os.open(
            resolutions_name,
            _no_follow_open_flags(),
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise ValueError(
            "--resolutions должен быть существующим безопасным соседним файлом."
        ) from exc
    try:
        _assert_darwin_fd_has_no_extended_acl(
            descriptor,
            object_label="Файл решений по расхождениям",
        )
        content, identity = _read_bounded_regular_fd(
            descriptor,
            label="--resolutions",
            byte_limit=_AUDIT_FINALIZATION_RESOLUTIONS_LIMIT,
            path_stat=path_stat,
        )
        final_descriptor_stat = os.fstat(descriptor)
        if (
            stat.S_IMODE(final_descriptor_stat.st_mode) != 0o600
            or (
                os.name == "posix"
                and effective_uid is not None
                and final_descriptor_stat.st_uid != effective_uid
            )
            or _stable_file_identity(final_descriptor_stat) != identity
        ):
            raise ValueError("--resolutions изменился во время проверки приватности.")
    finally:
        os.close(descriptor)
    try:
        final_path_stat = os.stat(
            resolutions_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise ValueError("--resolutions перемещён или заменён во время чтения.") from exc
    if _stable_file_identity(final_path_stat) != identity:
        raise ValueError("--resolutions перемещён или заменён во время чтения.")
    return {"content": content, "identity": identity}


def _resolve_private_finalization_resolutions(
    raw_value: str,
    *,
    parent_descriptor: int,
) -> tuple[str, dict[str, Any]]:
    raw_resolutions = Path(raw_value).expanduser()
    if not raw_resolutions.is_absolute():
        raw_resolutions = Path.cwd() / raw_resolutions
    resolutions_name = raw_resolutions.name
    if not resolutions_name or resolutions_name in {".", ".."}:
        raise ValueError("--resolutions должен называть отдельный файл.")
    try:
        resolutions_parent = raw_resolutions.parent.resolve(strict=True)
        resolutions_parent_stat = os.stat(
            resolutions_parent,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise ValueError("Родитель --resolutions должен существовать.") from exc
    held_parent_stat = os.fstat(parent_descriptor)
    if (
        resolutions_parent_stat.st_dev != held_parent_stat.st_dev
        or resolutions_parent_stat.st_ino != held_parent_stat.st_ino
    ):
        raise ValueError(
            "--resolutions должен быть приватным соседним файлом рядом с "
            "--bundle, --audit-import и --output-dir."
        )
    return resolutions_name, _capture_private_finalization_resolutions_at(
        parent_descriptor,
        resolutions_name,
    )


def _resolve_existing_audit_import(
    raw_value: str,
    *,
    parent_descriptor: int,
    bundle_name: str,
) -> tuple[str, dict[str, Any]]:
    raw_import = Path(raw_value).expanduser()
    if not raw_import.is_absolute():
        raw_import = Path.cwd() / raw_import
    import_name = raw_import.name
    if not import_name or import_name in {".", ".."} or import_name == bundle_name:
        raise ValueError(
            "--bundle и --audit-import должны называть две разные соседние папки."
        )
    try:
        import_parent = raw_import.parent.resolve(strict=True)
        import_parent_stat = os.stat(import_parent, follow_symlinks=False)
    except OSError as exc:
        raise ValueError("Родитель --audit-import должен существовать.") from exc
    held_parent_stat = os.fstat(parent_descriptor)
    if (
        import_parent_stat.st_dev != held_parent_stat.st_dev
        or import_parent_stat.st_ino != held_parent_stat.st_ino
    ):
        raise ValueError(
            "--bundle, --audit-import и --output-dir должны быть соседними папками "
            "одного фактического родителя."
        )
    return import_name, _capture_audit_review_import_at(
        parent_descriptor,
        import_name,
    )


def _assert_json_resource_limits(value: Any, *, label: str) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _AUDIT_IMPORT_MAX_JSON_NODES:
            raise ValueError(f"{label}: JSON содержит слишком много элементов.")
        if depth > _AUDIT_IMPORT_MAX_JSON_DEPTH:
            raise ValueError(f"{label}: JSON имеет чрезмерную глубину.")
        if isinstance(current, str):
            if len(current.encode("utf-8")) > _AUDIT_IMPORT_MAX_STRING_BYTES:
                raise ValueError(f"{label}: строка превышает безопасный предел.")
        elif isinstance(current, list):
            if len(current) > _AUDIT_IMPORT_MAX_COLLECTION_ITEMS:
                raise ValueError(f"{label}: JSON-массив слишком велик.")
            stack.extend((item, depth + 1) for item in current)
        elif isinstance(current, dict):
            if len(current) > _AUDIT_IMPORT_MAX_COLLECTION_ITEMS:
                raise ValueError(f"{label}: JSON-объект слишком велик.")
            for key, item in current.items():
                if len(key.encode("utf-8")) > _AUDIT_IMPORT_MAX_STRING_BYTES:
                    raise ValueError(f"{label}: JSON-ключ слишком велик.")
                stack.append((item, depth + 1))


def _strict_json_bytes(content: bytes, *, label: str) -> Any:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label}: требуется корректный UTF-8.") from exc
    value = _strict_json_loads(text, source=Path(label))
    _assert_json_resource_limits(value, label=label)
    return value


def _strict_jsonl_bytes(content: bytes, *, label: str) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label}: требуется корректный UTF-8.") from exc
    records: list[dict[str, Any]] = []
    for number, line in enumerate(io.StringIO(text), start=1):
        if number > _AUDIT_IMPORT_MAX_PHYSICAL_LINES:
            raise ValueError(f"{label}: слишком много физических строк.")
        if len(line.encode("utf-8")) > _AUDIT_IMPORT_MAX_STRING_BYTES:
            raise ValueError(f"{label}: строка {number} превышает безопасный предел.")
        if not line.strip():
            continue
        value = _strict_json_loads(line, source=Path(label))
        _assert_json_resource_limits(value, label=f"{label}: строка {number}")
        if not isinstance(value, dict):
            raise ValueError(f"{label}: строка {number} должна быть JSON-объектом.")
        records.append(value)
        if len(records) > _AUDIT_IMPORT_MAX_RECORDS:
            raise ValueError(f"{label}: слишком много записей.")
    return records


_BLINDED_REVIEW_GUIDE_V1_1 = textwrap.dedent(
    """
    # Независимая проверка кодирования

    Этот ZIP предназначен только для второго кодировщика. Не передавайте весь
    родительский каталог audit-пакета: в нём находятся ответы первого кодировщика.

    Сопровождающий обязан сохранить показанный командой ожидаемый SHA-256 и
    передать его отдельно от ZIP по независимому каналу. До начала работы получите
    это значение и сравните его с результатом команды:
    `shasum -a 256 independent-review-packet.zip`. При несовпадении остановитесь.

    `codebook_version` задаётся сопровождающим отдельно как версия процедуры,
    проверяется на совпадение с первичными карточками и связан с приложенным
    `CODING-CODEBOOK.md`; ответ первого кодировщика не является источником этого
    значения. До разметки прочитайте этот справочник полностью, а направленную
    проверяемую гипотезу, нормы и правила включения возьмите из
    `CODING-BRIEF.json`. Поля `supports` и `adverse` относятся именно к этой
    гипотезе, а не к желаемому результату дела.

    Пакет скрывает первичную разметку, её хеши, автора первичной разметки,
    поисковые совпадения, конкретную поисковую дорожку и основание отбора.
    Сам факт включения показывает принадлежность документа объединённой
    audit-выборке. Пакет не скрывает исход судебного дела: факты, мотивы и
    результат видны в полном тексте и нужны для юридического кодирования.

    Для каждого `candidate_id`:

    1. Прочитайте весь соответствующий `text` из `review-materials.jsonl`.
    2. Скопируйте `secondary-coding-template.jsonl` в отдельный рабочий файл.
       Не изменяйте файлы внутри исходного ZIP.
    3. Не меняйте `candidate_id`, `chain_id`, `document_id` и `codebook_version`.
    4. Верните ровно одну запись с ровно 20 полями: `candidate_id`, `chain_id`,
       `document_id`, `label`, `speaker`, `proposition`, `quote`, `quote_locator`,
       `norm_edition_id`, `reasoning_to_outcome`, `reading_family`, `relation`,
       `remedy`, `coder`, `codebook_version`, `material_facts`,
       `alternative_grounds`, `human_review`, `quote_verified`,
       `full_text_reviewed`.
    5. Заполните все поля самостоятельно. Допустимые `label`:
       `core_merits`, `contextual`, `party_only`, `mentioned_only`,
       `quoted_not_adopted`, `false_positive`, `unclear`.
       Для `core_merits` и `contextual` поле `speaker` должно быть `court`.
       Допустимые `relation`: `supports`, `adverse`, `neutral`, `distinguishes`,
       `supersedes`.
    6. Укажите точную цитату и локатор, связь мотива с исходом, хотя бы один
       существенный факт, результат, reading family и своё отличающееся имя в
       `coder`. `alternative_grounds` может быть пустым списком; иначе каждый
       элемент содержит только `ground`, `independently_sufficient` и, при
       наличии, `quote`, `quote_locator`.
       `material_facts` — непустой список видимых строк. Поле
       `independently_sufficient` — логическое JSON-значение `true` или `false`.
       Остальные текстовые значения должны быть непустыми и видимыми,
       идентификаторы — каноническими, без крайних, повторных или управляющих
       пробелов и символов.
    7. Только после реального полного чтения поставьте `human_review="approved"`,
       `quote_verified=true` и `full_text_reviewed=true`.

    Верните сопровождающему отдельный строгий UTF-8 JSONL: ровно один закрытый
    JSON-объект на каждый обязательный `candidate_id`, без отсутствующих, лишних
    или повторных `candidate_id`, лишних полей, повторяющихся ключей, `NaN` или
    `Infinity`. Этот выпуск ещё не содержит
    штатного импорта решений или квитанции проверки текста. Возврат файла сам по
    себе не доказывает независимость, сверку цитат, согласие кодировщиков,
    юридическое одобрение или право на подачу.

    ZIP содержит полные судебные тексты и может содержать персональные либо иные
    чувствительные сведения. Передавайте его выбранному проверяющему по подходящему
    защищённому каналу. Подготовка пакета не разрешает публикацию, распространение
    текста или подачу жалобы.
    """
).lstrip().encode("utf-8")

_BLINDED_REVIEW_GUIDE_V1_2 = _BLINDED_REVIEW_GUIDE_V1_1.replace(
    (
        "Этот выпуск ещё не содержит\n"
        "штатного импорта решений или квитанции проверки текста. Возврат файла сам по\n"
        "себе не доказывает независимость, сверку цитат, согласие кодировщиков,\n"
        "юридическое одобрение или право на подачу."
    ).encode("utf-8"),
    (
        "После возврата файла сопровождающий использует штатную команду\n"
        "`quality coding-audit-review-import`, отдельно сохранённый SHA-256 манифеста\n"
        "пакета и заранее согласованную псевдонимную метку второго кодировщика.\n"
        "Эту метку выберите до передачи ZIP и сообщите отдельно; не используйте\n"
        "реальное имя. Импорт выполняет буквальную и нормализованную проверки\n"
        "присутствия цитат, но сам по себе не доказывает их смысловую правильность,\n"
        "личность, независимость,\n"
        "согласие кодировщиков, юридическое одобрение или право на подачу."
    ).encode("utf-8"),
).replace(
    (
        "   существенный факт, результат, reading family и своё отличающееся имя в\n"
        "   `coder`."
    ).encode("utf-8"),
    (
        "   существенный факт, результат, reading family и заранее согласованную\n"
        "   псевдонимную метку в `coder`; не указывайте реальное имя."
    ).encode("utf-8"),
).replace(
    "родительский каталог audit-пакета".encode("utf-8"),
    "родительский каталог пакета аудита".encode("utf-8"),
).replace(
    "результат, reading family и заранее согласованную".encode("utf-8"),
    (
        "результат, `reading_family` (семейство толкования) и заранее согласованную"
    ).encode("utf-8"),
).replace(
    "Поля `supports` и `adverse` относятся именно к этой".encode("utf-8"),
    (
        "Значения `supports` (поддерживает) и `adverse` (противоречит) относятся "
        "именно к этой"
    ).encode("utf-8"),
)
if _BLINDED_REVIEW_GUIDE_V1_2 == _BLINDED_REVIEW_GUIDE_V1_1:
    raise AssertionError(
        "Не удалось собрать инструкции пакета независимой проверки версии 1.2."
    )
if "своё отличающееся имя" in _BLINDED_REVIEW_GUIDE_V1_2.decode("utf-8"):
    raise AssertionError("Инструкции версии 1.2 не закрепили псевдонимную метку.")

_BLINDED_REVIEW_GUIDES = {
    "1.1": _BLINDED_REVIEW_GUIDE_V1_1,
    "1.2": _BLINDED_REVIEW_GUIDE_V1_2,
}
_CURRENT_AUDIT_BUNDLE_CONTRACT_VERSION = "1.2"


_AUDIT_CODEBOOK_PATHS = {"1.0": "coding-audit-codebook-v1.md"}

_NEUTRAL_CODING_BRIEF_FIELDS = {
    "schema_version",
    "artifact_type",
    "plan_sha256",
    "codebook_version",
    "title",
    "research_questions",
    "norm_editions",
    "population",
    "inclusion_rules",
    "exclusion_rules",
    "materiality_rule",
    "contradiction_rule",
    "brief_sha256",
}
_NEUTRAL_QUESTION_FIELDS = {"id", "status", "question", "norm_refs"}
_NEUTRAL_NORM_EDITION_FIELDS = {
    "id",
    "norm_ref",
    "valid_from",
    "valid_to",
    "official_source_url",
    "edition_status",
}
_NEUTRAL_POPULATION_FIELDS = {
    "unit",
    "date_from",
    "date_to",
    "courts",
    "regimes",
    "official_population_rule",
}


def _is_packet_visible_text(value: Any) -> bool:
    """Mirror visible_text without requiring jsonschema at runtime."""

    if not isinstance(value, str) or not value.strip():
        return False
    permitted_layout_controls = {"\t", "\n", "\r"}
    return not any(
        unicodedata.category(character) in {"Cf", "Cs"}
        or (
            unicodedata.category(character) == "Cc"
            and character not in permitted_layout_controls
        )
        for character in value
    )


def _is_packet_canonical_identifier(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in value
    ):
        return False
    return value == " ".join(value.split())


def _is_packet_iso_date(value: Any, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_nonempty_visible_text_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(_is_packet_visible_text(item) for item in value)
    )


def _validate_neutral_coding_brief(
    coding_brief: Any,
    *,
    plan_sha256: str,
    codebook_version: str,
    require_digest: bool,
) -> None:
    """Fail closed on the exact dependency-free neutral-brief contract."""

    expected_fields = set(_NEUTRAL_CODING_BRIEF_FIELDS)
    if not require_digest:
        expected_fields.remove("brief_sha256")
    if not isinstance(coding_brief, Mapping) or set(coding_brief) != expected_fields:
        raise ValueError("Нейтральный coding brief имеет неверный закрытый формат.")
    if (
        coding_brief.get("schema_version") != "1.0"
        or coding_brief.get("artifact_type") != "coding_audit_neutral_brief"
        or coding_brief.get("plan_sha256") != plan_sha256
        or re.fullmatch(r"[0-9a-f]{64}", plan_sha256) is None
        or coding_brief.get("codebook_version") != codebook_version
        or codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS
        or not _is_packet_visible_text(coding_brief.get("title"))
        or not _is_nonempty_visible_text_list(coding_brief.get("inclusion_rules"))
        or not _is_nonempty_visible_text_list(coding_brief.get("exclusion_rules"))
        or not _is_packet_visible_text(coding_brief.get("materiality_rule"))
        or not _is_packet_visible_text(coding_brief.get("contradiction_rule"))
    ):
        raise ValueError("Нейтральный coding brief не связан с допустимым планом.")

    questions = coding_brief.get("research_questions")
    if (
        not isinstance(questions, list)
        or len(questions) != 1
        or not isinstance(questions[0], Mapping)
        or set(questions[0]) != _NEUTRAL_QUESTION_FIELDS
        or not _is_packet_canonical_identifier(questions[0].get("id"))
        or questions[0].get("status") != "hypothesis_under_test"
        or not _is_packet_visible_text(questions[0].get("question"))
        or not _is_nonempty_visible_text_list(questions[0].get("norm_refs"))
    ):
        raise ValueError(
            "Нейтральный coding brief должен содержать ровно одну направленную гипотезу."
        )

    editions = coding_brief.get("norm_editions")
    if not isinstance(editions, list) or not editions:
        raise ValueError("Нейтральный coding brief не содержит редакций норм.")
    seen_edition_ids: set[str] = set()
    for edition in editions:
        if not isinstance(edition, Mapping) or set(edition) != _NEUTRAL_NORM_EDITION_FIELDS:
            raise ValueError("Редакция нормы в coding brief имеет неверный формат.")
        edition_id = edition.get("id")
        if (
            not _is_packet_canonical_identifier(edition_id)
            or edition_id in seen_edition_ids
            or not _is_packet_visible_text(edition.get("norm_ref"))
            or not _is_packet_iso_date(edition.get("valid_from"))
            or not _is_packet_iso_date(edition.get("valid_to"), nullable=True)
            or not _is_packet_visible_text(edition.get("official_source_url"))
            or edition.get("edition_status") != "verified"
        ):
            raise ValueError("Редакция нормы в coding brief неканонична.")
        valid_to = edition.get("valid_to")
        if valid_to is not None and valid_to < edition["valid_from"]:
            raise ValueError("Период редакции нормы в coding brief задан в обратном порядке.")
        seen_edition_ids.add(edition_id)

    population = coding_brief.get("population")
    if (
        not isinstance(population, Mapping)
        or set(population) != _NEUTRAL_POPULATION_FIELDS
        or population.get("unit") != "independent_case_chain"
        or not _is_packet_iso_date(population.get("date_from"))
        or not _is_packet_iso_date(population.get("date_to"))
        or population["date_from"] > population["date_to"]
        or not _is_nonempty_visible_text_list(population.get("courts"))
        or not _is_nonempty_visible_text_list(population.get("regimes"))
        or not _is_packet_visible_text(population.get("official_population_rule"))
    ):
        raise ValueError("Исследуемая совокупность в coding brief неканонична.")

    if require_digest:
        unsigned = {
            key: value for key, value in coding_brief.items() if key != "brief_sha256"
        }
        if coding_brief.get("brief_sha256") != canonical_digest(unsigned):
            raise ValueError("SHA-256 нейтрального coding brief не совпадает.")


def _load_audit_codebook(codebook_version: str) -> bytes:
    if codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS:
        raise ValueError("Запрошена неподдерживаемая версия справочника кодирования.")
    path = Path(__file__).resolve().parents[2] / "references" / _AUDIT_CODEBOOK_PATHS[
        codebook_version
    ]
    if not path.is_file() or path.is_symlink():
        raise ValueError("Штатный справочник кодирования отсутствует или небезопасен.")
    content = path.read_bytes()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Штатный справочник кодирования не является UTF-8.") from exc
    if not decoded.strip():
        raise ValueError("Штатный справочник кодирования пуст.")
    return content


def _build_neutral_coding_brief(
    frozen_plan: Mapping[str, Any], *, codebook_version: str
) -> dict[str, Any]:
    """Project the frozen plan into reviewer-needed, non-search metadata."""

    research_questions = frozen_plan.get("research_questions")
    if not isinstance(research_questions, list) or len(research_questions) != 1:
        raise ValueError(
            "Штатный аудит требует ровно один замороженный исследовательский "
            "вопрос; для нескольких вопросов подготовьте отдельные пакеты аудита."
        )
    if (
        not isinstance(research_questions[0], Mapping)
        or research_questions[0].get("status") != "hypothesis_under_test"
    ):
        raise ValueError(
            "Штатный аудит требует ровно одну направленную гипотезу со статусом "
            "hypothesis_under_test; открытый research_question сначала "
            "переформулируйте и заново заморозьте в отдельном плане."
        )
    if codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS:
        raise ValueError("Запрошена неподдерживаемая версия справочника кодирования.")

    payload = {
        "schema_version": "1.0",
        "artifact_type": "coding_audit_neutral_brief",
        "plan_sha256": frozen_plan["plan_sha256"],
        "codebook_version": codebook_version,
        "title": frozen_plan["title"],
        "research_questions": [
            {
                "id": question["id"],
                "status": question["status"],
                "question": question["question"],
                "norm_refs": list(question["norm_refs"]),
            }
            for question in research_questions
        ],
        "norm_editions": [
            {
                "id": edition["id"],
                "norm_ref": edition["norm_ref"],
                "valid_from": edition["valid_from"],
                "valid_to": edition["valid_to"],
                "official_source_url": edition["official_source_url"],
                "edition_status": edition["edition_status"],
            }
            for edition in frozen_plan["norm_editions"]
        ],
        "population": {
            "unit": frozen_plan["population"]["unit"],
            "date_from": frozen_plan["population"]["date_from"],
            "date_to": frozen_plan["population"]["date_to"],
            "courts": list(frozen_plan["population"]["courts"]),
            "regimes": list(frozen_plan["population"]["regimes"]),
            "official_population_rule": frozen_plan["population"][
                "official_population_rule"
            ],
        },
        "inclusion_rules": list(frozen_plan["inclusion_rules"]),
        "exclusion_rules": list(frozen_plan["exclusion_rules"]),
        "materiality_rule": frozen_plan["materiality_rule"],
        "contradiction_rule": frozen_plan["contradiction_rule"],
    }
    _validate_neutral_coding_brief(
        payload,
        plan_sha256=frozen_plan["plan_sha256"],
        codebook_version=codebook_version,
        require_digest=False,
    )
    result = {**payload, "brief_sha256": canonical_digest(payload)}
    _validate_neutral_coding_brief(
        result,
        plan_sha256=frozen_plan["plan_sha256"],
        codebook_version=codebook_version,
        require_digest=True,
    )
    return result


def _deterministic_flat_zip(files: Mapping[str, bytes]) -> bytes:
    """Build one byte-stable stored ZIP with safe flat ASCII member names."""

    if len(files) > len(_BLINDED_REVIEW_PACKET_PATHS):
        raise ValueError("Пакет независимой проверки содержит слишком много файлов.")
    estimated_zip_bytes = 22
    for name, content in files.items():
        if Path(name).name != name or not name.isascii():
            raise AssertionError(
                "Пути внутри ZIP для проверки должны быть плоскими и ASCII."
            )
        if not isinstance(content, bytes):
            raise ValueError("Файл пакета независимой проверки должен состоять из байтов.")
        if len(content) > _AUDIT_IMPORT_ZIP_MEMBER_LIMIT:
            raise ValueError(
                "Файл пакета независимой проверки превышает безопасный предел."
            )
        estimated_zip_bytes += len(content) + 76 + 2 * len(name.encode("ascii"))
        if estimated_zip_bytes > _AUDIT_IMPORT_ZIP_TOTAL_LIMIT:
            raise ValueError(
                "Пакет независимой проверки превышает безопасный общий предел."
            )

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_STORED,
        allowZip64=False,
    ) as archive:
        archive.comment = b""
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.extra = b""
            info.comment = b""
            archive.writestr(info, files[name])
    return buffer.getvalue()


def _build_blinded_review_packet(
    bundle: Mapping[str, Any],
    *,
    plan_sha256: str,
    codebook_content: bytes,
    coding_brief_content: bytes,
    bundle_contract_version: str = _CURRENT_AUDIT_BUNDLE_CONTRACT_VERSION,
    installed_codebook_content: bytes | None = None,
) -> bytes:
    """Validate and serialize the selected reviewer-only projection."""

    audit_plan = bundle.get("audit_plan")
    if not isinstance(audit_plan, Mapping):
        raise ValueError("Внутренний план аудита отсутствует или повреждён.")
    if audit_plan.get("plan_sha256") != plan_sha256:
        raise ValueError("Внутренний план аудита связан с другим замороженным планом.")
    required = audit_plan.get("required_candidate_ids")
    if (
        not isinstance(required, list)
        or not required
        or any(not isinstance(value, str) or not value for value in required)
        or required != sorted(set(required))
    ):
        raise ValueError(
            "Внутренний план аудита должен содержать непустой отсортированный "
            "набор уникальных required_candidate_ids."
        )

    codebook_version = bundle.get("codebook_version")
    if (
        not isinstance(codebook_version, str)
        or not codebook_version
        or codebook_version != codebook_version.strip()
        or any(
            unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            for character in codebook_version
        )
    ):
        raise ValueError("Внутренняя версия справочника кодирования неканонична.")
    if codebook_version not in NATIVE_AUDIT_CODEBOOK_VERSIONS:
        raise ValueError("Внутренняя версия справочника кодирования не поддерживается.")
    if not isinstance(codebook_content, bytes) or not codebook_content:
        raise ValueError("Внутренний справочник кодирования отсутствует.")
    try:
        decoded_codebook = codebook_content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Внутренний справочник кодирования не является UTF-8.") from exc
    if not decoded_codebook.strip():
        raise ValueError("Внутренний справочник кодирования пуст.")
    trusted_codebook_content = (
        _load_audit_codebook(codebook_version)
        if installed_codebook_content is None
        else installed_codebook_content
    )
    if codebook_content != trusted_codebook_content:
        raise ValueError("Внутренний справочник не совпадает со штатной версией.")
    codebook_sha256 = hashlib.sha256(codebook_content).hexdigest()
    try:
        coding_brief = json.loads(coding_brief_content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Внутренний нейтральный coding brief повреждён.") from exc
    _validate_neutral_coding_brief(
        coding_brief,
        plan_sha256=plan_sha256,
        codebook_version=codebook_version,
        require_digest=True,
    )
    if _canonical_json_bytes(coding_brief) != coding_brief_content:
        raise ValueError("Внутренний нейтральный coding brief неканоничен.")
    coding_brief_file_sha256 = hashlib.sha256(coding_brief_content).hexdigest()

    def index_records(key: str, *, exact: bool) -> dict[str, Mapping[str, Any]]:
        records = bundle.get(key)
        if not isinstance(records, list):
            raise ValueError(f"Внутренний набор {key} отсутствует или повреждён.")
        indexed: dict[str, Mapping[str, Any]] = {}
        observed: list[str] = []
        for record in records:
            if not isinstance(record, Mapping):
                raise ValueError(f"Внутренний набор {key} содержит не объект.")
            candidate_id = record.get("candidate_id")
            if not _is_native_audit_candidate_id(candidate_id):
                raise ValueError(
                    f"Внутренний набор {key} содержит неканонический candidate_id."
                )
            if candidate_id in indexed:
                raise ValueError(f"Внутренний набор {key} повторяет candidate_id.")
            indexed[candidate_id] = record
            observed.append(candidate_id)
        if exact and observed != required:
            raise ValueError(
                f"Внутренний набор {key} не совпадает по порядку и составу с "
                "required_candidate_ids."
            )
        return indexed

    screening = index_records("screening_candidates", exact=False)
    queue = index_records("secondary_review_queue", exact=True)
    templates = index_records("secondary_coding_templates", exact=True)
    materials = index_records("secondary_review_materials", exact=True)
    if not set(required).issubset(screening):
        raise ValueError(
            "required_candidate_ids не являются подмножеством кандидатов отбора."
        )

    pending_values = {
        "human_review": "pending",
        "quote_verified": False,
        "full_text_reviewed": False,
        "material_facts": [],
        "alternative_grounds": [],
    }
    identity_fields = ("candidate_id", "chain_id", "document_id")
    for candidate_id in required:
        frame = screening[candidate_id]
        queue_record = queue[candidate_id]
        template = templates[candidate_id]
        material = materials[candidate_id]
        if set(material) != NATIVE_AUDIT_REVIEW_MATERIAL_FIELDS:
            raise ValueError("Материал проверки содержит неожиданные поля.")
        if material.get("schema_version") != "1.0":
            raise ValueError("Материал проверки имеет неподдерживаемую схему.")
        if set(template) != AUDIT_CODING_RECORD_FIELDS:
            raise ValueError("Шаблон вторичной разметки содержит неожиданные поля.")
        for field in identity_fields:
            expected_value = material.get(field)
            if (
                not isinstance(expected_value, str)
                or not expected_value
                or any(
                    record.get(field) != expected_value
                    for record in (frame, queue_record, template)
                )
            ):
                raise ValueError(
                    f"Кандидат проверки имеет несовпадающее поле {field}."
                )
        if frame.get("plan_sha256") != plan_sha256:
            raise ValueError("Кандидат проверки связан с другим замороженным планом.")
        chain_id = material.get("chain_id")
        document_id = material.get("document_id")
        expected_candidate_id = "audit-candidate-sha256:" + canonical_digest(
            {
                "schema_version": "1.0",
                "plan_sha256": plan_sha256,
                "chain_id": chain_id,
                "document_id": document_id,
            }
        )
        if candidate_id != expected_candidate_id:
            raise ValueError("Кандидат проверки не связан с планом и документом.")
        source_text_sha256 = material.get("source_text_sha256")
        if (
            not isinstance(source_text_sha256, str)
            or len(source_text_sha256) != 64
            or any(character not in "0123456789abcdef" for character in source_text_sha256)
            or queue_record.get("source_text_sha256") != source_text_sha256
            or document_id != f"document-sha256:{source_text_sha256}"
        ):
            raise ValueError("Кандидат проверки имеет несогласованный хеш текста.")
        text = material.get("text")
        packet_text_sha256 = material.get("packet_text_sha256")
        if (
            not isinstance(text, str)
            or not text.strip()
            or any(
                unicodedata.category(character) in {"Cf", "Cs"}
                or (
                    unicodedata.category(character) == "Cc"
                    and character not in {"\t", "\n", "\v", "\f", "\r"}
                )
                for character in text
            )
            or packet_text_sha256 != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Кандидат проверки не связан с точным текстом пакета.")
        normalized_text = re.sub(
            r"\s+", " ", unicodedata.normalize("NFC", text)
        ).strip()
        if hashlib.sha256(normalized_text.encode("utf-8")).hexdigest() != source_text_sha256:
            raise ValueError(
                "Кандидат проверки не связан с нормализованным текстом хранилища."
            )
        if template.get("codebook_version") != queue_record.get("codebook_version"):
            raise ValueError(
                "Кандидат проверки имеет разные версии справочника кодирования."
            )
        if template.get("codebook_version") != codebook_version:
            raise ValueError(
                "Кандидат проверки связан с другой версией справочника кодирования."
            )
        if any(template.get(field) != value for field, value in pending_values.items()):
            raise ValueError(
                "Шаблон вторичной разметки не находится в состоянии ожидания (`pending`)."
            )
        fixed_template_fields = set(identity_fields) | {"codebook_version"} | set(
            pending_values
        )
        if any(
            template.get(field) is not None
            for field in AUDIT_CODING_RECORD_FIELDS - fixed_template_fields
        ):
            raise ValueError("Шаблон вторичной разметки заранее содержит ответ.")

    review_guide = _BLINDED_REVIEW_GUIDES.get(bundle_contract_version)
    if review_guide is None:
        raise ValueError("Версия пакета независимой проверки не поддерживается.")
    review_content_files: dict[str, bytes] = {
        "CODING-BRIEF.json": coding_brief_content,
        "CODING-CODEBOOK.md": codebook_content,
        "REVIEW-INSTRUCTIONS.md": review_guide,
        "review-materials.jsonl": _canonical_jsonl_bytes(
            materials[candidate_id] for candidate_id in required
        ),
        "secondary-coding-template.jsonl": _canonical_jsonl_bytes(
            templates[candidate_id] for candidate_id in required
        ),
    }
    review_file_entries = [
        {
            "path": name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content in sorted(review_content_files.items())
    ]
    unsigned_review_manifest = {
        "schema_version": "1.0",
        "artifact_type": "coding_audit_blinded_review_packet",
        "producer": "judicial_meaning.quality.coding_audit_prepare",
        "plan_sha256": plan_sha256,
        "codebook_version": codebook_version,
        "codebook_sha256": codebook_sha256,
        "coding_brief_file_sha256": coding_brief_file_sha256,
        "candidate_ids": required,
        "blinding_scope": "primary_coding_answer_only",
        "excluded_information": [
            "adjudication",
            "primary_coder_identity",
            "primary_coding",
            "primary_coding_sha256",
            "sample_lane",
            "screening_matches",
            "screening_queries",
        ],
        "contains_full_text": True,
        "contains_primary_coding": False,
        "review_state": "independent_secondary_required",
        "human_approval_created": False,
        "publication_safe": False,
        "legal_readiness": False,
        "files": review_file_entries,
    }
    review_manifest = {
        **unsigned_review_manifest,
        "manifest_sha256": canonical_digest(unsigned_review_manifest),
    }
    return _deterministic_flat_zip(
        {
            **review_content_files,
            "review-packet-manifest.json": _canonical_json_bytes(review_manifest),
        }
    )


_NATIVE_AUDIT_PARENT_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "bundle_contract_version",
        "artifact_type",
        "producer",
        "plan_sha256",
        "codebook_version",
        "codebook_sha256",
        "coding_brief_file_sha256",
        "source_plan_file_sha256",
        "source_screening_sha256",
        "source_primary_sha256",
        "source_sources_sha256",
        "source_text_inventory_sha256",
        "candidate_ids",
        "required_candidate_ids",
        "secondary_review_state",
        "human_approval_created",
        "legal_readiness",
        "files",
        "manifest_sha256",
    }
)
_NATIVE_AUDIT_PARENT_DIGEST_FIELDS = (
    "plan_sha256",
    "codebook_sha256",
    "coding_brief_file_sha256",
    "source_plan_file_sha256",
    "source_screening_sha256",
    "source_primary_sha256",
    "source_sources_sha256",
    "source_text_inventory_sha256",
    "manifest_sha256",
)


def _is_lower_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _validate_native_screening_records(
    records: list[dict[str, Any]], *, plan_sha256: str
) -> list[str]:
    candidate_ids: list[str] = []
    for row_number, record in enumerate(records, start=1):
        if set(record) != NATIVE_AUDIT_SCREENING_FIELDS:
            raise ValueError(
                f"screening-candidates.audit.jsonl: строка {row_number} имеет "
                "неверный закрытый формат."
            )
        candidate_id = record.get("candidate_id")
        chain_id = record.get("chain_id")
        document_id = record.get("document_id")
        source_ids = record.get("source_ids")
        matches = record.get("matches")
        expected_candidate_id = "audit-candidate-sha256:" + canonical_digest(
            {
                "schema_version": "1.0",
                "plan_sha256": plan_sha256,
                "chain_id": chain_id,
                "document_id": document_id,
            }
        )
        if (
            record.get("schema_version") != "1.0"
            or record.get("plan_sha256") != plan_sha256
            or not _is_packet_canonical_identifier(candidate_id)
            or candidate_id != expected_candidate_id
            or not _is_packet_canonical_identifier(chain_id)
            or not _is_packet_canonical_identifier(document_id)
            or re.fullmatch(r"document-sha256:[0-9a-f]{64}", str(document_id)) is None
            or record.get("status") != "candidate_needs_full_text_review"
            or not isinstance(source_ids, list)
            or not source_ids
            or any(
                isinstance(source_id, bool)
                or not isinstance(source_id, int)
                or source_id < 1
                for source_id in source_ids
            )
            or source_ids != sorted(set(source_ids))
            or not isinstance(matches, list)
            or not matches
        ):
            raise ValueError(
                f"screening-candidates.audit.jsonl: строка {row_number} неканонична."
            )
        match_digests: list[str] = []
        for match in matches:
            if not isinstance(match, Mapping) or set(match) != {
                "lane",
                "query",
                "start",
                "end",
            }:
                raise ValueError(
                    f"screening-candidates.audit.jsonl: поле matches строки {row_number} "
                    "имеют неверный формат."
                )
            start = match.get("start")
            end = match.get("end")
            if (
                not _is_packet_canonical_identifier(match.get("lane"))
                or not _is_packet_canonical_identifier(match.get("query"))
                or isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or not 0 <= start < end
            ):
                raise ValueError(
                    f"screening-candidates.audit.jsonl: поле matches строки {row_number} "
                    "неканоничны."
                )
            match_digests.append(canonical_digest(match))
        if len(match_digests) != len(set(match_digests)):
            raise ValueError(
                f"screening-candidates.audit.jsonl: строка {row_number} повторяет совпадение."
            )
        candidate_ids.append(candidate_id)
    if not candidate_ids or candidate_ids != sorted(set(candidate_ids)):
        raise ValueError(
            "screening-candidates.audit.jsonl должен иметь непустой отсортированный "
            "набор candidate_id."
        )
    return candidate_ids


def _preflight_blinded_review_zip(content: bytes) -> None:
    """Bound central-directory allocation before ``zipfile`` parses entries."""

    end_record_size = 22
    if len(content) < end_record_size or content[-end_record_size:-18] != b"PK\x05\x06":
        raise ValueError(
            "independent-review-packet.zip не имеет канонической конечной записи."
        )
    try:
        (
            signature,
            disk_number,
            central_directory_disk,
            entries_on_disk,
            entries_total,
            central_directory_size,
            central_directory_offset,
            comment_size,
        ) = struct.unpack("<4s4H2LH", content[-end_record_size:])
    except struct.error as exc:
        raise ValueError(
            "independent-review-packet.zip имеет повреждённую конечную запись."
        ) from exc
    if signature != b"PK\x05\x06" or comment_size != 0:
        raise ValueError(
            "independent-review-packet.zip содержит неканонический ZIP-комментарий."
        )
    if disk_number != 0 or central_directory_disk != 0:
        raise ValueError("independent-review-packet.zip не может быть многотомным.")
    if (
        entries_on_disk != len(_BLINDED_REVIEW_PACKET_PATHS)
        or entries_total != len(_BLINDED_REVIEW_PACKET_PATHS)
    ):
        raise ValueError(
            "independent-review-packet.zip должен объявлять ровно шесть файлов; "
            "ZIP64 и расширенные реестры запрещены."
        )
    if (
        central_directory_size > _AUDIT_IMPORT_ZIP_CENTRAL_DIRECTORY_LIMIT
        or central_directory_offset > len(content) - end_record_size
        or central_directory_offset + central_directory_size
        != len(content) - end_record_size
    ):
        raise ValueError(
            "independent-review-packet.zip имеет чрезмерный или неканонический "
            "центральный реестр."
        )


def _read_blinded_review_packet(
    content: bytes,
    *,
    bundle_contract_version: str,
    audit_plan: Mapping[str, Any],
    screening_records: list[dict[str, Any]],
    queue_records: list[dict[str, Any]],
    template_records: list[dict[str, Any]],
    codebook_version: str,
    installed_codebook_content: bytes,
) -> dict[str, Any]:
    _preflight_blinded_review_zip(content)
    try:
        with zipfile.ZipFile(io.BytesIO(content), mode="r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != list(_BLINDED_REVIEW_PACKET_PATHS) or len(names) != len(
                set(names)
            ):
                raise ValueError(
                    "independent-review-packet.zip должен содержать ровно шесть "
                    "уникальных файлов в каноническом порядке."
                )
            if archive.comment != b"":
                raise ValueError("independent-review-packet.zip содержит ZIP-комментарий.")
            stored_total = 0
            uncompressed_total = 0
            for info in infos:
                stored_total += info.compress_size
                uncompressed_total += info.file_size
                if (
                    Path(info.filename).name != info.filename
                    or not info.filename.isascii()
                    or info.is_dir()
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.flag_bits != 0
                    or info.compress_size != info.file_size
                    or info.file_size > _AUDIT_IMPORT_ZIP_MEMBER_LIMIT
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                    or info.create_system != 3
                    or info.external_attr != 0o100644 << 16
                    or info.extra != b""
                    or info.comment != b""
                ):
                    raise ValueError(
                        "Файл внутри ZIP имеет небезопасные или неканонические свойства."
                    )
            if (
                stored_total > _AUDIT_IMPORT_ZIP_TOTAL_LIMIT
                or uncompressed_total > _AUDIT_IMPORT_ZIP_TOTAL_LIMIT
            ):
                raise ValueError("independent-review-packet.zip превышает безопасный предел.")
            member_bytes = {info.filename: archive.read(info) for info in infos}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ValueError("independent-review-packet.zip повреждён или небезопасен.") from exc

    coding_brief = _strict_json_bytes(
        member_bytes["CODING-BRIEF.json"], label="CODING-BRIEF.json"
    )
    review_materials = _strict_jsonl_bytes(
        member_bytes["review-materials.jsonl"], label="review-materials.jsonl"
    )
    packet_templates = _strict_jsonl_bytes(
        member_bytes["secondary-coding-template.jsonl"],
        label="secondary-coding-template.jsonl внутри ZIP",
    )
    review_manifest = _strict_json_bytes(
        member_bytes["review-packet-manifest.json"],
        label="review-packet-manifest.json",
    )
    if (
        not isinstance(coding_brief, Mapping)
        or not isinstance(review_manifest, Mapping)
        or _canonical_json_bytes(coding_brief) != member_bytes["CODING-BRIEF.json"]
        or _canonical_jsonl_bytes(review_materials)
        != member_bytes["review-materials.jsonl"]
        or _canonical_jsonl_bytes(packet_templates)
        != member_bytes["secondary-coding-template.jsonl"]
        or _canonical_json_bytes(review_manifest)
        != member_bytes["review-packet-manifest.json"]
    ):
        raise ValueError("JSON/JSONL внутри пакета проверки не является каноническим.")
    bundle = {
        "audit_plan": dict(audit_plan),
        "screening_candidates": screening_records,
        "secondary_review_queue": queue_records,
        "secondary_coding_templates": template_records,
        "secondary_review_materials": review_materials,
        "codebook_version": codebook_version,
    }
    expected = _build_blinded_review_packet(
        bundle,
        plan_sha256=str(audit_plan["plan_sha256"]),
        codebook_content=member_bytes["CODING-CODEBOOK.md"],
        coding_brief_content=member_bytes["CODING-BRIEF.json"],
        bundle_contract_version=bundle_contract_version,
        installed_codebook_content=installed_codebook_content,
    )
    if expected != content:
        raise ValueError(
            "independent-review-packet.zip не совпадает побайтно со штатной сборкой."
        )
    return {
        "coding_brief": dict(coding_brief),
        "coding_brief_content": member_bytes["CODING-BRIEF.json"],
        "codebook_content": member_bytes["CODING-CODEBOOK.md"],
        "review_materials": review_materials,
        "templates": packet_templates,
        "review_manifest": dict(review_manifest),
    }


def _load_native_coding_audit_bundle(
    capture: Mapping[str, Any],
    *,
    expected_manifest_sha256: str,
    installed_codebook_content: bytes,
) -> dict[str, Any]:
    files = capture.get("files")
    if not isinstance(files, Mapping) or set(files) != _AUDIT_BUNDLE_PATHS:
        raise ValueError("Внутренний снимок --bundle неполон.")

    def file_bytes(name: str) -> bytes:
        item = files.get(name)
        if not isinstance(item, Mapping) or not isinstance(item.get("content"), bytes):
            raise ValueError(f"Внутренний снимок {name} повреждён.")
        content = item["content"]
        if len(content) > _AUDIT_IMPORT_FILE_LIMITS[name]:
            raise ValueError(f"{name}: файл превышает безопасный предел.")
        return content

    manifest_content = file_bytes("coding-audit-inputs-manifest.json")
    manifest = _strict_json_bytes(
        manifest_content, label="coding-audit-inputs-manifest.json"
    )
    if not isinstance(manifest, Mapping) or set(manifest) != _NATIVE_AUDIT_PARENT_MANIFEST_FIELDS:
        raise ValueError("Родительский манифест имеет неверный закрытый формат.")
    manifest = dict(manifest)
    if _canonical_json_bytes(manifest) != manifest_content:
        raise ValueError("Родительский манифест не является каноническим JSON.")
    unsigned_manifest = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if manifest.get("manifest_sha256") != canonical_digest(unsigned_manifest):
        raise ValueError("Собственная контрольная сумма родительского манифеста не совпадает.")
    if not _is_lower_sha256(expected_manifest_sha256):
        raise ValueError(
            "--expected-manifest-sha256 должен содержать 64 строчные шестнадцатеричные цифры."
        )
    if manifest["manifest_sha256"] != expected_manifest_sha256:
        raise ValueError(
            "Родительский манифест не совпадает с отдельно сохранённым ожидаемым SHA-256."
        )
    bundle_contract_version = manifest.get("bundle_contract_version")
    if (
        manifest.get("schema_version") != "1.0"
        or bundle_contract_version not in _BLINDED_REVIEW_GUIDES
        or manifest.get("artifact_type") != "coding_audit_input_bundle"
        or manifest.get("producer")
        != "judicial_meaning.quality.coding_audit_prepare"
        or manifest.get("secondary_review_state")
        != "independent_secondary_required"
        or manifest.get("human_approval_created") is not False
        or manifest.get("legal_readiness") is not False
        or manifest.get("codebook_version") not in NATIVE_AUDIT_CODEBOOK_VERSIONS
        or any(
            not _is_lower_sha256(manifest.get(field))
            for field in _NATIVE_AUDIT_PARENT_DIGEST_FIELDS
        )
    ):
        raise ValueError("Родительский манифест имеет неподдерживаемый контракт.")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != len(_AUDIT_BUNDLE_CONTENT_PATHS):
        raise ValueError("Родительский манифест имеет неверный файловый реестр.")
    for expected_name, entry in zip(_AUDIT_BUNDLE_CONTENT_PATHS, entries):
        content = file_bytes(expected_name)
        if (
            not isinstance(entry, Mapping)
            or set(entry) != {"path", "bytes", "sha256"}
            or entry.get("path") != expected_name
            or isinstance(entry.get("bytes"), bool)
            or entry.get("bytes") != len(content)
            or entry.get("sha256") != hashlib.sha256(content).hexdigest()
        ):
            raise ValueError(
                f"Родительский манифест не совпадает с файлом {expected_name}."
            )

    screening = _strict_jsonl_bytes(
        file_bytes("screening-candidates.audit.jsonl"),
        label="screening-candidates.audit.jsonl",
    )
    primary = _strict_jsonl_bytes(
        file_bytes("primary-decisions.audit.jsonl"),
        label="primary-decisions.audit.jsonl",
    )
    audit_plan = _strict_json_bytes(
        file_bytes("coding-audit-plan.json"), label="coding-audit-plan.json"
    )
    queue = _strict_jsonl_bytes(
        file_bytes("secondary-review-queue.jsonl"),
        label="secondary-review-queue.jsonl",
    )
    templates = _strict_jsonl_bytes(
        file_bytes("secondary-coding-template.jsonl"),
        label="secondary-coding-template.jsonl",
    )
    canonical_pairs = (
        (screening, "screening-candidates.audit.jsonl"),
        (primary, "primary-decisions.audit.jsonl"),
        (queue, "secondary-review-queue.jsonl"),
        (templates, "secondary-coding-template.jsonl"),
    )
    if any(
        _canonical_jsonl_bytes(records) != file_bytes(name)
        for records, name in canonical_pairs
    ):
        raise ValueError("Родительский JSONL должен иметь канонические байты.")
    if not isinstance(audit_plan, Mapping) or set(audit_plan) != CODING_AUDIT_PLAN_FIELDS:
        raise ValueError("coding-audit-plan.json имеет неверный закрытый формат.")
    audit_plan = dict(audit_plan)
    if _canonical_json_bytes(audit_plan) != file_bytes("coding-audit-plan.json"):
        raise ValueError("coding-audit-plan.json не является каноническим JSON.")
    plan_sha256 = manifest["plan_sha256"]
    candidate_ids = _validate_native_screening_records(
        screening, plan_sha256=plan_sha256
    )
    if candidate_ids != manifest.get("candidate_ids"):
        raise ValueError("Манифест candidate_ids не совпадает с рамкой отбора.")
    if [record.get("candidate_id") for record in primary] != candidate_ids:
        raise ValueError("Первичная разметка не совпадает по порядку с рамкой отбора.")
    regenerated_plan = build_coding_audit_plan(
        screening,
        primary,
        plan_sha256=plan_sha256,
        sample_size=audit_plan.get("sample_size"),
        exclusion_sample_size=audit_plan.get("exclusion_sample_size"),
    )
    if regenerated_plan != audit_plan:
        raise ValueError("coding-audit-plan.json не воспроизводится из исходных файлов пакета.")
    required = audit_plan.get("required_candidate_ids")
    if (
        not isinstance(required, list)
        or not required
        or required != sorted(set(required))
        or manifest.get("required_candidate_ids") != required
        or audit_plan.get("invalid_screening_record_ids") != []
        or audit_plan.get("invalid_primary_record_ids") != []
    ):
        raise ValueError("Обязательная выборка аудита или её входы недопустимы.")
    if [record.get("candidate_id") for record in queue] != required:
        raise ValueError("Очередь вторичной проверки не совпадает с обязательной выборкой.")
    if [record.get("candidate_id") for record in templates] != required:
        raise ValueError("Шаблон вторичной разметки не совпадает с обязательной выборкой.")
    screening_by_candidate = {record["candidate_id"]: record for record in screening}
    if any(
        record.get("source_ids")
        != screening_by_candidate[record["candidate_id"]].get("source_ids")
        for record in queue
    ):
        raise ValueError("Очередь вторичной проверки не связана с source_ids рамки отбора.")

    packet = _read_blinded_review_packet(
        file_bytes("independent-review-packet.zip"),
        bundle_contract_version=str(bundle_contract_version),
        audit_plan=audit_plan,
        screening_records=screening,
        queue_records=queue,
        template_records=templates,
        codebook_version=str(manifest["codebook_version"]),
        installed_codebook_content=installed_codebook_content,
    )
    if (
        packet["templates"] != templates
        or manifest["codebook_sha256"]
        != hashlib.sha256(packet["codebook_content"]).hexdigest()
        or manifest["coding_brief_file_sha256"]
        != hashlib.sha256(packet["coding_brief_content"]).hexdigest()
    ):
        raise ValueError("Родительский манифест не совпадает с содержимым пакета проверки.")
    return {
        "manifest": manifest,
        "manifest_content": manifest_content,
        "screening": screening,
        "primary": primary,
        "audit_plan": audit_plan,
        "queue": queue,
        "templates": templates,
        "packet": packet,
        "review_packet_content": file_bytes("independent-review-packet.zip"),
    }


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
    names: list[str] = list(_PRE_THESIS_CASE_RELATIVE_FILES)
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
    manifest: list[dict[str, Any]] = []
    for slot, path in enumerate(paths):
        present = path.exists()
        content = path.read_bytes() if present else b""
        manifest.append(
            {
                "slot": slot,
                "present": present,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest() if present else None,
            }
        )
    return _artifact_sha256(manifest)


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


def _latest_plan_path(workspace: Path) -> Path:
    versions: list[tuple[int, Path]] = []
    for path in (workspace / "plans").glob("plan-v*.json"):
        try:
            versions.append((int(path.stem.split("-v", 1)[1]), path))
        except (IndexError, ValueError):
            continue
    if not versions:
        raise ValueError("Нет замороженного плана. Выполните `plan freeze`.")
    return max(versions)[1]


def latest_plan(workspace: Path) -> dict[str, Any]:
    return read_json(_latest_plan_path(workspace))


def _verified_frozen_plan(workspace: Path) -> tuple[dict[str, Any], bytes]:
    plan_path = _latest_plan_path(workspace)
    value, content = _strict_json_file(plan_path)
    if not isinstance(value, dict):
        raise ValueError(f"{plan_path}: замороженный план должен быть JSON-объектом.")
    plan = dict(value)
    plan_sha256 = plan.get("plan_sha256")
    if plan.get("frozen") is not True or not isinstance(plan_sha256, str) or (
        len(plan_sha256) != 64
        or any(character not in "0123456789abcdef" for character in plan_sha256)
    ):
        raise ValueError("Последний план не имеет действительной frozen SHA-256 привязки.")
    unsigned = {
        key: item for key, item in plan.items() if key not in {"frozen", "plan_sha256"}
    }
    plan_errors = validate_plan(unsigned)
    if plan_errors:
        raise ValueError("Последний замороженный план невалиден: " + "; ".join(plan_errors))
    if canonical_digest(unsigned) != plan_sha256:
        raise ValueError("SHA-256 последнего замороженного плана не совпадает с его содержимым.")
    return plan, content


def _captured_workspace_source_texts(
    workspace: Path,
    source_records: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    for row_number, record in enumerate(source_records, start=1):
        if record.get("kind") != "doc":
            continue
        text: str | None = None
        inline_text = record.get("text")
        if isinstance(inline_text, str) and inline_text.strip():
            text = inline_text
        else:
            relpath = record.get("text_relpath")
            if not isinstance(relpath, str) or not relpath.strip():
                continue
            relative = Path(relpath)
            if relative.is_absolute():
                raise ValueError(
                    f"exports/sources.jsonl: строка {row_number} содержит абсолютный text_relpath."
                )
            try:
                text_path = (workspace / relative).resolve(strict=True)
                text_path.relative_to(workspace)
            except (OSError, ValueError) as exc:
                raise ValueError(
                    f"exports/sources.jsonl: text_relpath строки {row_number} выходит за рабочую папку или отсутствует."
                ) from exc
            if not text_path.is_file():
                raise ValueError(
                    f"exports/sources.jsonl: text_relpath строки {row_number} не является файлом."
                )
            try:
                text = text_path.read_bytes().decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"exports/sources.jsonl: полный текст строки {row_number} не является UTF-8."
                ) from exc
        captured.append(
            {
                "source_id": record.get("source_id"),
                "chain_id": record.get("chain_id"),
                "document_id": record.get("document_id"),
                "text_sha256": record.get("text_sha256"),
                "text": text,
            }
        )
    return captured


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


def _json_output_line(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"


def _write_stdout_line(line: str) -> None:
    written = sys.stdout.write(line)
    if written != len(line):
        raise OSError("Стандартный вывод принял не всю строку результата.")
    sys.stdout.flush()


def _print_json(value: Any) -> None:
    _write_stdout_line(_json_output_line(value))


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


def _quality_result(args: argparse.Namespace, result: Mapping[str, Any]) -> int:
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), dict(result))
    _print_json(result)
    return 0


def _quality_gate_exit_code(result: Mapping[str, Any]) -> int:
    return 0 if result.get("complete") is True else 3


def _quality_gate_result(args: argparse.Namespace, result: Mapping[str, Any]) -> int:
    _quality_result(args, result)
    return _quality_gate_exit_code(result)


def _quality_records(path_value: str, option: str) -> list[dict[str, Any]]:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"{option} должен указывать на существующий файл.")
    if path.suffix.casefold() == ".jsonl":
        return read_jsonl(path)
    value = read_json(path)
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ValueError(f"{option}: JSON-массив должен содержать только объекты.")
        return list(value)
    if isinstance(value, dict):
        if "items" in value:
            raise ValueError(
                f"{option} не принимает оболочку items; передайте "
                "сам массив записей или JSONL после успешного сбора."
            )
        return [value]
    raise ValueError(f"{option}: ожидался JSON-объект, массив объектов или JSONL.")


def _strict_quality_records(path_value: str, option: str) -> list[dict[str, Any]]:
    """Read a human-authored quality input without ambiguous JSON semantics."""

    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"{option} должен указывать на существующий файл.")
    if path.suffix.casefold() == ".jsonl":
        records, _ = _strict_jsonl_file(path)
        return records
    value, _ = _strict_json_file(path)
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ValueError(f"{option}: JSON-массив должен содержать только объекты.")
        return list(value)
    if isinstance(value, dict):
        if "items" in value:
            raise ValueError(
                f"{option} не принимает оболочку items; передайте "
                "сам массив записей или JSONL после успешного сбора."
            )
        return [value]
    raise ValueError(f"{option}: ожидался JSON-объект, массив объектов или JSONL.")


def _optional_json(path_value: str | None) -> Any:
    if not path_value:
        return None
    return read_json(Path(path_value).expanduser().resolve())


def _records_index(path_value: str, id_field: str) -> dict[str, dict[str, Any]]:
    records = _read_records(Path(path_value).expanduser().resolve())
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = record.get(id_field)
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"Запись не содержит {id_field}.")
        if identifier in result:
            raise ValueError(f"Повторный {id_field}: {identifier}.")
        result[identifier] = record
    return result


def cmd_quality_chain_propagation(args: argparse.Namespace) -> int:
    result = analyze_chain_stage_propagation(
        _read_records(Path(args.observations).expanduser().resolve()),
        required_chain_ids=args.required_chain_id or [],
    )
    return _quality_result(args, result)


def cmd_quality_uncertainty_profile(args: argparse.Namespace) -> int:
    trajectory_value = read_json(Path(args.trajectories).expanduser().resolve())
    if isinstance(trajectory_value, Mapping):
        trajectories = trajectory_value.get("trajectories")
    else:
        trajectories = trajectory_value
    if not isinstance(trajectories, list) or not all(
        isinstance(item, Mapping) for item in trajectories
    ):
        raise ValueError("--trajectories должен содержать массив trajectories.")
    finalization_receipt_path = getattr(
        args, "coding_audit_finalization_receipt", None
    )
    expected_finalization_receipt_sha256 = getattr(
        args, "expected_finalization_receipt_sha256", None
    )
    native_relation_requested = bool(
        finalization_receipt_path
        or expected_finalization_receipt_sha256 is not None
    )
    result = build_uncertainty_profile(
        fingerprint_sha256=args.fingerprint_sha256,
        position_cards=_read_records(Path(args.position_cards).expanduser().resolve()),
        comparisons=_records_index(args.comparisons, "position_card_id"),
        applicant_relations=_records_index(args.applicant_relations, "position_card_id"),
        temporal_analysis=_optional_json(args.temporal_analysis),
        trajectories=trajectories,
        source_reconciliation=_optional_json(args.source_reconciliation),
        coding_reliability=_optional_private_quality_json(
            args.coding_reliability,
            "--coding-reliability",
            strict=native_relation_requested,
            require_canonical=native_relation_requested,
        ),
        coding_audit_finalization_receipt=_optional_private_quality_json(
            finalization_receipt_path,
            "--coding-audit-finalization-receipt",
            strict=True,
        ),
        expected_finalization_receipt_sha256=(
            expected_finalization_receipt_sha256
        ),
        higher_authority_treatments=(
            _read_records(Path(args.higher_authority_treatments).expanduser().resolve())
            if args.higher_authority_treatments
            else []
        ),
    )
    return _quality_result(args, result)


def cmd_quality_coding_audit_plan(args: argparse.Namespace) -> int:
    result = build_coding_audit_plan(
        _read_records(Path(args.screening_candidates).expanduser().resolve()),
        _read_records(Path(args.primary_decisions).expanduser().resolve()),
        plan_sha256=args.plan_sha256,
        sample_size=args.sample_size,
        exclusion_sample_size=args.exclusion_sample_size,
    )
    return _quality_result(args, result)


def _atomic_rename_no_replace(source: Path, destination: Path) -> None:
    """Atomically publish a directory while refusing an existing destination."""

    if sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        try:
            renamex_np = libc.renamex_np
        except AttributeError as exc:
            raise OSError(
                errno.ENOTSUP,
                "Система не поддерживает атомарную публикацию без перезаписи.",
            ) from exc
        renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        renamex_np.restype = ctypes.c_int
        result = renamex_np(os.fsencode(source), os.fsencode(destination), 0x00000004)
    elif sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        try:
            renameat2 = libc.renameat2
        except AttributeError as exc:
            raise OSError(
                errno.ENOTSUP,
                "Система не поддерживает атомарную публикацию без перезаписи.",
            ) from exc
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            os.fsencode(source),
            -100,
            os.fsencode(destination),
            0x00000001,
        )
    elif os.name == "nt":
        os.rename(source, destination)
        return
    else:
        raise OSError(
            errno.ENOTSUP,
            "Система не поддерживает атомарную публикацию без перезаписи.",
        )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(
                error_number,
                "Каталог пакета аудита уже существует; перезапись запрещена.",
                destination,
            )
        raise OSError(error_number, os.strerror(error_number), destination)


def _atomic_rename_no_replace_at(
    parent_descriptor: int,
    source_name: str,
    destination_name: str,
    *,
    expected_source_identity: tuple[int, int] | None = None,
) -> None:
    """Atomically rename two flat names relative to one trusted directory fd."""

    if any(
        not name or Path(name).name != name or name in {".", ".."}
        for name in (source_name, destination_name)
    ):
        raise ValueError("Имена каталогов публикации должны быть плоскими.")
    if expected_source_identity is not None:
        try:
            source_stat = os.stat(
                source_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise OSError("Временная папка публикации исчезла до переноса.") from exc
        if (
            not stat.S_ISDIR(source_stat.st_mode)
            or (source_stat.st_dev, source_stat.st_ino) != expected_source_identity
        ):
            raise OSError("Временная папка публикации заменена до переноса.")
    if sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        try:
            renameatx_np = libc.renameatx_np
        except AttributeError as exc:
            raise OSError(
                errno.ENOTSUP,
                "Система не поддерживает атомарную публикацию относительно папки.",
            ) from exc
        renameatx_np.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameatx_np.restype = ctypes.c_int
        result = renameatx_np(
            parent_descriptor,
            os.fsencode(source_name),
            parent_descriptor,
            os.fsencode(destination_name),
            0x00000004,
        )
    elif sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        try:
            renameat2 = libc.renameat2
        except AttributeError as exc:
            raise OSError(
                errno.ENOTSUP,
                "Система не поддерживает атомарную публикацию относительно папки.",
            ) from exc
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            parent_descriptor,
            os.fsencode(source_name),
            parent_descriptor,
            os.fsencode(destination_name),
            0x00000001,
        )
    else:
        raise OSError(
            errno.ENOTSUP,
            "Система не поддерживает безопасную публикацию относительно папки.",
        )
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(
                error_number,
                "Каталог пакета аудита уже существует; перезапись запрещена.",
                destination_name,
            )
        raise OSError(error_number, os.strerror(error_number), destination_name)


def _fsync_directory(path: Path | int) -> None:
    if os.name == "nt":
        return
    if isinstance(path, int):
        os.fsync(path)
        return
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_darwin_extended_acl_functions() -> tuple[Any, Any]:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        acl_get_fd_np = libc.acl_get_fd_np
        acl_free = libc.acl_free
    except (AttributeError, OSError) as exc:
        raise OSError(
            "Среда macOS не предоставляет обязательную проверку расширенных ACL."
        ) from exc
    acl_get_fd_np.argtypes = [ctypes.c_int, ctypes.c_int]
    acl_get_fd_np.restype = ctypes.c_void_p
    acl_free.argtypes = [ctypes.c_void_p]
    acl_free.restype = ctypes.c_int
    return acl_get_fd_np, acl_free


def _acl_guard_fd_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        stat.S_IFMT(value.st_mode),
        value.st_uid,
        stat.S_IMODE(value.st_mode),
        value.st_nlink,
        value.st_ctime_ns,
    )


def _assert_fd_has_no_extended_acl(
    descriptor: int,
    *,
    acl_type: int,
    object_label: str,
    acl_get_fd_np: Any,
    acl_free: Any,
) -> None:
    try:
        before = os.fstat(descriptor)
    except OSError as exc:
        raise OSError(
            f"{object_label}: не удалось проверить идентичность перед проверкой ACL."
        ) from exc
    before_identity = _acl_guard_fd_identity(before)

    acl_failure: Exception | None = None
    ctypes.set_errno(0)
    try:
        acl = acl_get_fd_np(descriptor, acl_type)
    except Exception:
        acl_failure = OSError(
            f"{object_label}: системная проверка расширенного ACL завершилась ошибкой."
        )
    else:
        if not acl:
            if ctypes.get_errno() != errno.ENOENT:
                acl_failure = OSError(
                    f"{object_label}: отсутствие расширенного ACL не подтверждено."
                )
        else:
            ctypes.set_errno(0)
            try:
                free_result = acl_free(acl)
            except Exception:
                acl_failure = OSError(
                    f"{object_label}: освобождение системного объекта ACL не подтверждено."
                )
            else:
                if free_result != 0:
                    acl_failure = OSError(
                        f"{object_label}: освобождение системного объекта ACL не подтверждено."
                    )
                else:
                    acl_failure = ValueError(
                        f"{object_label}: обнаружен расширенный ACL macOS; "
                        "режим 0700/0600 не подтверждает приватность."
                    )

    try:
        after = os.fstat(descriptor)
    except OSError as exc:
        raise OSError(
            f"{object_label}: не удалось проверить идентичность после проверки ACL."
        ) from exc
    after_identity = _acl_guard_fd_identity(after)
    if after_identity != before_identity:
        raise OSError(
            f"{object_label}: объект изменился во время проверки расширенного ACL."
        )
    if acl_failure is not None:
        raise acl_failure


def _assert_darwin_fd_has_no_extended_acl(
    descriptor: int, *, object_label: str
) -> None:
    if sys.platform != "darwin":
        return
    acl_get_fd_np, acl_free = _load_darwin_extended_acl_functions()
    acl_type_extended = 0x100
    _assert_fd_has_no_extended_acl(
        descriptor,
        acl_type=acl_type_extended,
        object_label=object_label,
        acl_get_fd_np=acl_get_fd_np,
        acl_free=acl_free,
    )


def _assert_safe_publication_parent(descriptor: int) -> os.stat_result:
    parent_stat = os.fstat(descriptor)
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise ValueError("Родитель --output-dir не является обычной папкой.")
    if os.name == "posix":
        effective_uid = os.geteuid() if hasattr(os, "geteuid") else os.getuid()
        if parent_stat.st_uid != effective_uid:
            raise ValueError("Родитель --output-dir должен принадлежать текущему пользователю.")
        if parent_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError(
                "Родитель --output-dir не должен быть доступен для записи группе "
                "или другим пользователям."
            )
    if sys.platform == "darwin":
        _assert_darwin_fd_has_no_extended_acl(
            descriptor,
            object_label="Родительская папка публикации",
        )
        fresh_parent_stat = os.fstat(descriptor)
        if _acl_guard_fd_identity(fresh_parent_stat) != _acl_guard_fd_identity(
            parent_stat
        ):
            raise ValueError(
                "Родитель --output-dir изменён во время проверки приватности."
            )
        if (
            not stat.S_ISDIR(fresh_parent_stat.st_mode)
            or fresh_parent_stat.st_uid != effective_uid
            or fresh_parent_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            raise ValueError(
                "Родитель --output-dir больше не соответствует требованиям приватности."
            )
        parent_stat = fresh_parent_stat
    return parent_stat


def _assert_parent_path_matches_descriptor(path: Path, descriptor: int) -> None:
    try:
        path_stat = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise ValueError("Родитель --output-dir перемещён или заменён.") from exc
    descriptor_stat = os.fstat(descriptor)
    if (
        path_stat.st_dev != descriptor_stat.st_dev
        or path_stat.st_ino != descriptor_stat.st_ino
    ):
        raise ValueError("Родитель --output-dir перемещён или заменён.")


def _assert_published_audit_bundle(
    parent_descriptor: int,
    destination_name: str,
    expected_directory_identity: tuple[int, int],
    files: Mapping[str, bytes],
    expected_file_identities: Mapping[str, tuple[int, int]] | None = None,
) -> None:
    if expected_file_identities is not None and set(expected_file_identities) != set(
        files
    ):
        raise ValueError("Не задана точная идентичность всех файлов публикации.")
    effective_uid = (
        (os.geteuid() if hasattr(os, "geteuid") else os.getuid())
        if os.name == "posix"
        else None
    )
    try:
        path_stat = os.stat(
            destination_name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise ValueError("Опубликованный каталог перемещён или заменён.") from exc
    if (
        not stat.S_ISDIR(path_stat.st_mode)
        or (path_stat.st_dev, path_stat.st_ino) != expected_directory_identity
        or stat.S_IMODE(path_stat.st_mode) != 0o700
        or (effective_uid is not None and path_stat.st_uid != effective_uid)
    ):
        raise ValueError("Опубликованный каталог перемещён или заменён.")

    flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(
            destination_name,
            flags,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        raise ValueError("Опубликованный каталог нельзя безопасно открыть.") from exc
    try:
        _assert_darwin_fd_has_no_extended_acl(
            descriptor,
            object_label="Каталог проверяемого пакета аудита",
        )
        opened_stat = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(opened_stat.st_mode)
            or (opened_stat.st_dev, opened_stat.st_ino)
            != expected_directory_identity
            or stat.S_IMODE(opened_stat.st_mode) != 0o700
            or (effective_uid is not None and opened_stat.st_uid != effective_uid)
        ):
            raise ValueError("Опубликованный каталог перемещён или заменён.")
        directory_identity = _stable_directory_identity(opened_stat)
        names = _bounded_directory_names(
            descriptor,
            maximum_entries=len(files),
            label="Опубликованный каталог",
        )
        if set(names) != set(files):
            raise ValueError("Опубликованный каталог содержит неожиданный набор файлов.")
        for relative_path, expected_content in files.items():
            try:
                child_stat = os.stat(
                    relative_path,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(child_stat.st_mode)
                    or child_stat.st_nlink != 1
                    or stat.S_IMODE(child_stat.st_mode) != 0o600
                    or (
                        effective_uid is not None
                        and child_stat.st_uid != effective_uid
                    )
                    or child_stat.st_size != len(expected_content)
                    or (
                        expected_file_identities is not None
                        and (child_stat.st_dev, child_stat.st_ino)
                        != expected_file_identities[relative_path]
                    )
                ):
                    raise ValueError(
                        "Опубликованный каталог содержит небезопасный файл."
                    )
                child_descriptor = os.open(
                    relative_path,
                    _no_follow_open_flags(),
                    dir_fd=descriptor,
                )
            except OSError as exc:
                raise ValueError(
                    "Опубликованный каталог содержит небезопасный файл."
                ) from exc
            try:
                _assert_darwin_fd_has_no_extended_acl(
                    child_descriptor,
                    object_label="Файл проверяемого пакета аудита",
                )
                observed_content, child_identity = _read_bounded_regular_fd(
                    child_descriptor,
                    label=relative_path,
                    byte_limit=len(expected_content),
                    path_stat=child_stat,
                )
            finally:
                os.close(child_descriptor)
            try:
                final_child_stat = os.stat(
                    relative_path,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise ValueError(
                    "Опубликованный файл перемещён или заменён."
                ) from exc
            if (
                _stable_file_identity(final_child_stat) != child_identity
                or (
                    effective_uid is not None
                    and final_child_stat.st_uid != effective_uid
                )
                or observed_content != expected_content
            ):
                raise ValueError("Содержимое опубликованного файла изменено.")
        final_opened_stat = os.fstat(descriptor)
        try:
            final_path_stat = os.stat(
                destination_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise ValueError("Опубликованный каталог перемещён или заменён.") from exc
        if (
            _stable_directory_identity(final_opened_stat) != directory_identity
            or (final_path_stat.st_dev, final_path_stat.st_ino)
            != expected_directory_identity
            or stat.S_IMODE(final_path_stat.st_mode) != 0o700
            or (
                effective_uid is not None
                and (
                    final_opened_stat.st_uid != effective_uid
                    or final_path_stat.st_uid != effective_uid
                )
            )
        ):
            raise ValueError("Опубликованный каталог изменён во время проверки.")
    finally:
        os.close(descriptor)


class _PublicationRecoveryError(OSError):
    """A classified failure that already contains the publication stop rule."""


_PublishedCommandRecord = tuple[tuple[int, int], str, tuple[int, int]]


def _publication_state_uncertain_error(
    parent_identity: tuple[int, int],
    destination_name: str,
    published_directory_identity: tuple[int, int],
    created_file_identities: Mapping[str, tuple[int, int]] | None = None,
) -> _PublicationRecoveryError:
    recovery_entry_name = json.dumps(destination_name, ensure_ascii=True)
    file_coordinates = ""
    if created_file_identities:
        coordinates = ", ".join(
            (
                f"имя {json.dumps(name, ensure_ascii=True)}, устройство {identity[0]}, "
                f"inode {identity[1]}"
            )
            for name, identity in sorted(created_file_identities.items())
        )
        file_coordinates = f" Идентификаторы созданных файлов: {coordinates}."
    return _PublicationRecoveryError(
        "Состояние публикации после атомарного переноса не подтверждено: её "
        "расположение, целостность или защищённость могли измениться, а путь "
        "--output-dir может уже не вести к опубликованному каталогу. "
        "Координаты поиска в файловой системе: устройство "
        f"{parent_identity[0]}, inode родительской папки "
        f"{parent_identity[1]}, имя записи {recovery_entry_name}. "
        "Идентификатор самого опубликованного каталога: устройство "
        f"{published_directory_identity[0]}, inode "
        f"{published_directory_identity[1]}.{file_coordinates} "
        "Остановите автоматику, сохраните все входы неизменными, не "
        "повторяйте команду и не передавайте результат дальше. Это аварийное "
        "восстановление для системного администратора, а не штатная "
        "пользовательская команда: передайте администратору всю строку ошибки. "
        "Администратор должен найти родительскую папку и сам опубликованный "
        "каталог по устройству и inode, а также найти по указанным устройству и "
        "inode все имена и жёсткие ссылки каждого созданного файла. Каждую "
        "найденную копию нужно учесть и поместить в карантин до ручного "
        "восстановления. Если каталог, хотя бы один inode файла или все его ссылки "
        "нельзя полностью учесть, считайте чувствительную копию неучтённой и не "
        "продолжайте процесс без проверки оператора."
    )


def _staging_cleanup_uncertain_error(
    parent_identity: tuple[int, int],
    staging_name: str,
    staging_identity: tuple[int, int] | None,
    created_file_identities: Mapping[str, tuple[int, int]] | None = None,
) -> _PublicationRecoveryError:
    recovery_entry_name = json.dumps(staging_name, ensure_ascii=True)
    staging_coordinates = (
        "идентификатор временной папки получить не удалось"
        if staging_identity is None
        else (
            f"устройство временной папки {staging_identity[0]}, "
            f"inode {staging_identity[1]}"
        )
    )
    file_coordinates = ""
    if created_file_identities:
        coordinates = ", ".join(
            (
                f"имя {json.dumps(name, ensure_ascii=True)}, устройство {identity[0]}, "
                f"inode {identity[1]}"
            )
            for name, identity in sorted(created_file_identities.items())
        )
        file_coordinates = f" Созданные файлы: {coordinates}."
    return _PublicationRecoveryError(
        "Очистка временной публикации не подтверждена: чувствительные файлы "
        "могли остаться в перемещённой, заменённой, изменённой или уже перенесённой "
        "временной папке. После создания временной папки автоматическое удаление "
        "файлов или самой папки намеренно не выполняется: при конкурентной подмене "
        "имени нельзя переносимо и атомарно доказать, что удаляется именно созданный, "
        "а не чужой объект. "
        "Координаты: устройство родительской папки "
        f"{parent_identity[0]}, inode {parent_identity[1]}, прежнее имя "
        f"записи {recovery_entry_name}; {staging_coordinates}.{file_coordinates} "
        "В том числе за пределами временной папки могла сохраниться копия через "
        "жёсткую ссылку. "
        "Остановите автоматику, "
        "сохраните входы неизменными, не повторяйте команду и ничего не передавайте "
        "дальше. Передайте всю строку ошибки системному администратору: он должен "
        "найти по устройству и inode временную папку, а также все имена и жёсткие "
        "ссылки каждого указанного созданного файла, затем учесть и поместить в "
        "карантин каждую найденную копию. Штатной пользовательской команды "
        "восстановления нет. Если хотя бы один inode файла или все его ссылки нельзя "
        "полностью учесть, считайте чувствительную временную копию неучтённой."
    )


def _publication_confirmation_delivery_error(
    parent_identity: tuple[int, int],
    destination_name: str,
    published_directory_identity: tuple[int, int],
) -> _PublicationRecoveryError:
    recovery_entry_name = json.dumps(destination_name, ensure_ascii=True)
    return _PublicationRecoveryError(
        "Каталог результата полностью и долговечно опубликован, но финальное "
        "машиночитаемое подтверждение начали передавать, а завершение команды после "
        "начала передачи не подтверждено. Стандартный вывод мог остаться пустым или частичным либо "
        "выглядеть как полная строка JSON; во всех случаях считайте его "
        "недействительным и не разбирайте. Координаты результата: "
        f"устройство родительской папки {parent_identity[0]}, inode "
        f"{parent_identity[1]}, имя записи {recovery_entry_name}; устройство "
        f"каталога {published_directory_identity[0]}, inode "
        f"{published_directory_identity[1]}. Остановите автоматику, сохраните все "
        "входы и этот каталог неизменными, не используйте результат дальше и не "
        "повторяйте команду в ту же папку. После восстановления стандартного вывода "
        "повторите команду с теми же входами в другую отсутствующую соседнюю папку, "
        "получите одну полную строку JSON и побайтно сравните оба каталога. Для "
        "пакета аудита сохраните manifest_sha256 только из успешного повторного "
        "стандартного вывода по независимому каналу; не восстанавливайте этот якорь "
        "из первого пакета. Для импорта или финализации используйте контрольную "
        "сумму соответствующей квитанции и флаги дальнейших действий только из "
        "полного успешного повторного вывода "
        "после совпадения каталогов."
    )


def _publication_finalization_uncertain_error(
    parent_identity: tuple[int, int],
    destination_name: str,
    published_directory_identity: tuple[int, int],
) -> _PublicationRecoveryError:
    recovery_entry_name = json.dumps(destination_name, ensure_ascii=True)
    return _PublicationRecoveryError(
        "Каталог результата уже прошёл публикацию, но завершение команды после "
        "публикации не подтверждено из-за ошибки или прерывания до начала "
        "формирования финального стандартного вывода, в том числе при закрытии "
        "служебного дескриптора. "
        "Финальный стандартный вывод ещё не формировался и должен быть пуст; код 2 "
        "не доказывает отсутствия каталога. Координаты результата: устройство "
        f"родительской папки {parent_identity[0]}, inode {parent_identity[1]}, имя "
        f"записи {recovery_entry_name}; устройство каталога "
        f"{published_directory_identity[0]}, inode "
        f"{published_directory_identity[1]}. Остановите автоматику, сохраните все "
        "входы и найденный каталог неизменными, не используйте его дальше и не "
        "повторяйте команду в ту же папку. После устранения системной ошибки "
        "повторите команду с теми же входами в другую отсутствующую соседнюю папку, "
        "получите одну полную строку JSON и побайтно сравните оба каталога. Для "
        "пакета аудита сохраните manifest_sha256 только из успешного повторного "
        "стандартного вывода по независимому каналу; не восстанавливайте этот якорь "
        "из первого пакета. Для импорта или финализации используйте контрольную "
        "сумму соответствующей квитанции и флаги дальнейших действий только из "
        "полного успешного повторного вывода "
        "после совпадения каталогов."
    )


def _close_command_parent_descriptor(descriptor: int) -> None:
    os.close(descriptor)


def _close_published_descriptor(descriptor: int) -> None:
    os.close(descriptor)


def _neutralize_stdout_after_delivery_failure() -> None:
    try:
        stdout_descriptor = sys.stdout.fileno()
    except (AttributeError, OSError, ValueError):
        return
    null_descriptor: int | None = None
    try:
        null_descriptor = os.open(
            os.devnull,
            os.O_WRONLY | getattr(os, "O_CLOEXEC", 0),
        )
        if null_descriptor != stdout_descriptor:
            os.dup2(null_descriptor, stdout_descriptor)
    except OSError:
        return
    finally:
        if null_descriptor is not None and null_descriptor != stdout_descriptor:
            try:
                os.close(null_descriptor)
            except OSError:
                pass


def _deliver_published_confirmation(
    line: str,
    *,
    parent_identity: tuple[int, int],
    destination_name: str,
    published_directory_identity: tuple[int, int],
    delivery_state: list[str],
) -> None:
    try:
        delivery_state.append("started")
        _write_stdout_line(line)
        delivery_state.append("flushed")
    except BaseException as exc:
        try:
            _neutralize_stdout_after_delivery_failure()
        except BaseException:
            pass
        if isinstance(exc, _PublicationRecoveryError):
            raise
        raise _publication_confirmation_delivery_error(
            parent_identity,
            destination_name,
            published_directory_identity,
        ) from exc


def _postpublication_command_error(
    publication_state: list[_PublishedCommandRecord],
    delivery_state: list[str],
) -> _PublicationRecoveryError | None:
    if not publication_state:
        return None
    parent_identity, destination_name, published_directory_identity = (
        publication_state[-1]
    )
    if delivery_state:
        try:
            _neutralize_stdout_after_delivery_failure()
        except BaseException:
            pass
        return _publication_confirmation_delivery_error(
            parent_identity,
            destination_name,
            published_directory_identity,
        )
    return _publication_finalization_uncertain_error(
        parent_identity,
        destination_name,
        published_directory_identity,
    )


def _complete_published_command() -> int:
    return 0


def _publish_new_audit_bundle(
    destination: Path,
    files: Mapping[str, bytes],
    *,
    parent_descriptor: int | None = None,
    publication_state: list[_PublishedCommandRecord] | None = None,
) -> tuple[int, int]:
    if not destination.name or destination.name in {".", ".."}:
        raise ValueError("--output-dir должен называть новую папку.")
    parent = destination.parent
    owns_parent_descriptor = parent_descriptor is None
    if parent_descriptor is None:
        flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
        try:
            parent_stat = os.stat(parent, follow_symlinks=False)
            parent_descriptor = os.open(parent, flags)
        except OSError as exc:
            raise ValueError(
                "Родитель --output-dir должен быть существующей обычной папкой."
            ) from exc
        opened_parent_stat = os.fstat(parent_descriptor)
        if not stat.S_ISDIR(opened_parent_stat.st_mode) or (
            parent_stat.st_dev != opened_parent_stat.st_dev
            or parent_stat.st_ino != opened_parent_stat.st_ino
        ):
            os.close(parent_descriptor)
            raise ValueError("Родитель --output-dir изменился во время открытия.")
    try:
        verified_parent_stat = _assert_safe_publication_parent(parent_descriptor)
        effective_uid = (
            verified_parent_stat.st_uid if os.name == "posix" else None
        )
        publication_parent_identity = (
            verified_parent_stat.st_dev,
            verified_parent_stat.st_ino,
        )
        _assert_parent_path_matches_descriptor(parent, parent_descriptor)
    except Exception:
        if owns_parent_descriptor:
            os.close(parent_descriptor)
        raise

    try:
        os.stat(destination.name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        pass
    except OSError as exc:
        if owns_parent_descriptor:
            os.close(parent_descriptor)
        raise ValueError("Не удалось проверить --output-dir перед публикацией.") from exc
    else:
        if owns_parent_descriptor:
            os.close(parent_descriptor)
        raise ValueError("--output-dir уже существует; перезапись пакета аудита запрещена.")

    staging_name: str | None = None
    staging_created = False
    staging_descriptor: int | None = None
    staging_identity: tuple[int, int] | None = None
    created_file_descriptors: dict[str, int] = {}
    created_file_identities: dict[str, tuple[int, int]] = {}
    published = False
    try:
        for _ in range(100):
            candidate = f".{destination.name}.staging-{secrets.token_hex(12)}"
            try:
                os.mkdir(candidate, 0o700, dir_fd=parent_descriptor)
            except FileExistsError:
                continue
            staging_name = candidate
            staging_created = True
            break
        if staging_name is None:
            raise OSError("Не удалось выбрать уникальное имя временной папки.")
        directory_flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
        staging_descriptor = os.open(
            staging_name, directory_flags, dir_fd=parent_descriptor
        )
        opened_staging_stat = os.fstat(staging_descriptor)
        staging_identity = (opened_staging_stat.st_dev, opened_staging_stat.st_ino)
        if (
            not stat.S_ISDIR(opened_staging_stat.st_mode)
            or opened_staging_stat.st_nlink < 1
            or (
                effective_uid is not None
                and opened_staging_stat.st_uid != effective_uid
            )
        ):
            raise OSError("Не удалось безопасно открыть временную папку публикации.")
        os.fchmod(staging_descriptor, 0o700)
        _assert_darwin_fd_has_no_extended_acl(
            staging_descriptor,
            object_label="Временная папка публикации",
        )
        secured_staging_stat = os.fstat(staging_descriptor)
        if (
            not stat.S_ISDIR(secured_staging_stat.st_mode)
            or (secured_staging_stat.st_dev, secured_staging_stat.st_ino)
            != staging_identity
            or stat.S_IMODE(secured_staging_stat.st_mode) != 0o700
            or (
                effective_uid is not None
                and secured_staging_stat.st_uid != effective_uid
            )
        ):
            raise OSError("Временная папка публикации не стала приватной.")
        for relative_path, content in files.items():
            if Path(relative_path).name != relative_path:
                raise AssertionError("Пути файлов пакета аудита должны быть плоскими.")
            descriptor = os.open(
                relative_path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=staging_descriptor,
            )
            created_file_descriptors[relative_path] = descriptor
            created_stat = os.fstat(descriptor)
            created_file_identities[relative_path] = (
                created_stat.st_dev,
                created_stat.st_ino,
            )
            if (
                not stat.S_ISREG(created_stat.st_mode)
                or created_stat.st_nlink != 1
                or (
                    effective_uid is not None
                    and created_stat.st_uid != effective_uid
                )
            ):
                raise OSError(
                    f"Не удалось безопасно создать файл аудита {relative_path}."
                )
            os.fchmod(descriptor, 0o600)
            _assert_darwin_fd_has_no_extended_acl(
                descriptor,
                object_label="Созданный файл пакета аудита",
            )
            secured_file_stat = os.fstat(descriptor)
            if (
                not stat.S_ISREG(secured_file_stat.st_mode)
                or secured_file_stat.st_nlink != 1
                or (secured_file_stat.st_dev, secured_file_stat.st_ino)
                != created_file_identities[relative_path]
                or stat.S_IMODE(secured_file_stat.st_mode) != 0o600
                or (
                    effective_uid is not None
                    and secured_file_stat.st_uid != effective_uid
                )
            ):
                raise OSError(
                    f"Созданный файл аудита {relative_path} не стал приватным."
                )
            offset = 0
            while offset < len(content):
                written = os.write(descriptor, content[offset:])
                if written <= 0:
                    raise OSError(f"Не удалось записать файл аудита {relative_path}.")
                offset += written
            os.fsync(descriptor)
            target_stat = os.stat(
                relative_path, dir_fd=staging_descriptor, follow_symlinks=False
            )
            verification_descriptor = os.open(
                relative_path,
                _no_follow_open_flags(),
                dir_fd=staging_descriptor,
            )
            try:
                _assert_darwin_fd_has_no_extended_acl(
                    verification_descriptor,
                    object_label="Повторно открытый файл пакета аудита",
                )
                written_content, _ = _read_bounded_regular_fd(
                    verification_descriptor,
                    label=relative_path,
                    byte_limit=len(content),
                    path_stat=target_stat,
                )
            finally:
                os.close(verification_descriptor)
            if (
                written_content != content
                or stat.S_IMODE(target_stat.st_mode) != 0o600
                or (
                    effective_uid is not None
                    and target_stat.st_uid != effective_uid
                )
            ):
                raise OSError(f"Не удалось проверить записанный файл аудита {relative_path}.")
        _fsync_directory(staging_descriptor)
        staging_entry_stat = os.stat(
            staging_name, dir_fd=parent_descriptor, follow_symlinks=False
        )
        staging_descriptor_stat = os.fstat(staging_descriptor)
        if (
            not stat.S_ISDIR(staging_entry_stat.st_mode)
            or staging_entry_stat.st_dev != staging_descriptor_stat.st_dev
            or staging_entry_stat.st_ino != staging_descriptor_stat.st_ino
            or stat.S_IMODE(staging_entry_stat.st_mode) != 0o700
            or stat.S_IMODE(staging_descriptor_stat.st_mode) != 0o700
            or (
                effective_uid is not None
                and (
                    staging_entry_stat.st_uid != effective_uid
                    or staging_descriptor_stat.st_uid != effective_uid
                )
            )
            or set(
                _bounded_directory_names(
                    staging_descriptor,
                    maximum_entries=len(files),
                    label="Временная папка публикации",
                )
            )
            != set(files)
        ):
            raise OSError("Временная папка публикации изменилась до переноса.")
        _assert_published_audit_bundle(
            parent_descriptor,
            staging_name,
            staging_identity,
            files,
            created_file_identities,
        )
        _assert_safe_publication_parent(parent_descriptor)
        _assert_parent_path_matches_descriptor(parent, parent_descriptor)
        try:
            os.stat(destination.name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError(
                "--output-dir появился во время подготовки; пакет аудита не опубликован."
            )
        _assert_safe_publication_parent(parent_descriptor)
        _atomic_rename_no_replace_at(
            parent_descriptor,
            staging_name,
            destination.name,
            expected_source_identity=staging_identity,
        )
        published = True

        def assert_published_state() -> None:
            _assert_safe_publication_parent(parent_descriptor)
            _assert_parent_path_matches_descriptor(parent, parent_descriptor)
            _assert_published_audit_bundle(
                parent_descriptor,
                destination.name,
                staging_identity,
                files,
                created_file_identities,
            )

        try:
            assert_published_state()
        except (OSError, ValueError) as exc:
            if isinstance(exc, _PublicationRecoveryError):
                raise
            raise _publication_state_uncertain_error(
                publication_parent_identity,
                destination.name,
                staging_identity,
                created_file_identities,
            ) from exc
        try:
            _fsync_directory(parent_descriptor)
        except OSError as exc:
            if isinstance(exc, _PublicationRecoveryError):
                raise
            try:
                assert_published_state()
            except (OSError, ValueError) as location_exc:
                if isinstance(location_exc, _PublicationRecoveryError):
                    raise
                raise _publication_state_uncertain_error(
                    publication_parent_identity,
                    destination.name,
                    staging_identity,
                    created_file_identities,
                ) from location_exc
            raise _PublicationRecoveryError(
                "Долговечность публикации не подтверждена: полный "
                "каталог уже может быть виден после атомарного переноса; не удаляйте "
                "его автоматически "
                "и не передавайте его дальше. После восстановления файловой системы "
                "повторите эту команду с теми же неизменными входами, указав другую "
                "отсутствующую папку, и сравните оба результата побайтно."
            ) from exc
        try:
            assert_published_state()
        except (OSError, ValueError) as exc:
            if isinstance(exc, _PublicationRecoveryError):
                raise
            raise _publication_state_uncertain_error(
                publication_parent_identity,
                destination.name,
                staging_identity,
                created_file_identities,
            ) from exc

        close_failure: BaseException | None = None
        for descriptor in created_file_descriptors.values():
            try:
                _close_published_descriptor(descriptor)
            except BaseException as exc:
                if close_failure is None:
                    close_failure = exc
        created_file_descriptors.clear()
        if staging_descriptor is not None:
            try:
                _close_published_descriptor(staging_descriptor)
            except BaseException as exc:
                if close_failure is None:
                    close_failure = exc
            staging_descriptor = None
        if close_failure is not None:
            if isinstance(close_failure, _PublicationRecoveryError):
                raise close_failure
            raise _publication_finalization_uncertain_error(
                publication_parent_identity,
                destination.name,
                staging_identity,
            ) from close_failure
        if publication_state is not None:
            if publication_state:
                raise AssertionError(
                    "Состояние успешной публикации уже было зарегистрировано."
                )
            publication_state.append(
                (
                    publication_parent_identity,
                    destination.name,
                    staging_identity,
                )
            )
    except BaseException as exc:
        if (
            published
            and staging_identity is not None
            and not isinstance(exc, _PublicationRecoveryError)
        ):
            raise _publication_state_uncertain_error(
                publication_parent_identity,
                destination.name,
                staging_identity,
                created_file_identities,
            ) from exc
        raise
    finally:
        cleanup_error: _PublicationRecoveryError | None = None
        publication_error: _PublicationRecoveryError | None = None
        bookkeeping_failure: BaseException | None = None
        close_failure: BaseException | None = None
        if (
            not published
            and staging_created
            and staging_name is not None
        ):
            cleanup_error = _staging_cleanup_uncertain_error(
                publication_parent_identity,
                staging_name,
                staging_identity,
                created_file_identities,
            )
            if staging_identity is not None:
                try:
                    destination_path_stat = os.stat(
                        destination.name,
                        dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                    destination_name_matches = (
                        destination_path_stat.st_dev,
                        destination_path_stat.st_ino,
                    ) == staging_identity
                except BaseException as exc:
                    bookkeeping_failure = exc
                else:
                    if destination_name_matches:
                        publication_error = _publication_state_uncertain_error(
                            publication_parent_identity,
                            destination.name,
                            staging_identity,
                            created_file_identities,
                        )

        for descriptor in created_file_descriptors.values():
            try:
                os.close(descriptor)
            except BaseException as exc:
                if close_failure is None:
                    close_failure = exc
        created_file_descriptors.clear()

        if staging_descriptor is not None:
            try:
                os.close(staging_descriptor)
            except BaseException as exc:
                if close_failure is None:
                    close_failure = exc
            staging_descriptor = None
        if owns_parent_descriptor:
            try:
                os.close(parent_descriptor)
            except BaseException as exc:
                if close_failure is None:
                    close_failure = exc
        if publication_error is not None:
            raise publication_error
        if cleanup_error is not None:
            raise cleanup_error
        if close_failure is not None:
            if (
                published
                and staging_identity is not None
                and not isinstance(close_failure, _PublicationRecoveryError)
            ):
                raise _publication_finalization_uncertain_error(
                    publication_parent_identity,
                    destination.name,
                    staging_identity,
                ) from close_failure
            raise close_failure
        if bookkeeping_failure is not None:
            raise bookkeeping_failure
    if staging_identity is None:
        raise AssertionError("Не сохранена идентичность опубликованного каталога.")
    return staging_identity


def cmd_quality_coding_audit_prepare(args: argparse.Namespace) -> int:
    raw_destination = Path(args.output_dir).expanduser()
    if not raw_destination.is_absolute():
        raw_destination = Path.cwd() / raw_destination
    if not raw_destination.name or raw_destination.name in {".", ".."}:
        raise ValueError("--output-dir должен называть новую папку.")
    try:
        destination_parent = raw_destination.parent.resolve(strict=True)
        parent_path_stat = os.stat(destination_parent, follow_symlinks=False)
        flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
        parent_descriptor = os.open(destination_parent, flags)
    except OSError as exc:
        raise ValueError(
            "Родитель --output-dir должен быть существующей обычной папкой."
        ) from exc
    publication_state: list[_PublishedCommandRecord] = []
    delivery_state: list[str] = []
    parent_close_attempted = False
    try:
        parent_stat = _assert_safe_publication_parent(parent_descriptor)
        if (
            parent_path_stat.st_dev != parent_stat.st_dev
            or parent_path_stat.st_ino != parent_stat.st_ino
        ):
            raise ValueError("Родитель --output-dir изменился во время открытия.")
        confirmation_line, published_directory_identity = (
            _cmd_quality_coding_audit_prepare(
                args,
                output_parent_descriptor=parent_descriptor,
                output_parent_identity=(parent_stat.st_dev, parent_stat.st_ino),
                publication_state=publication_state,
            )
        )
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        parent_close_attempted = True
        _close_command_parent_descriptor(parent_descriptor)
        _deliver_published_confirmation(
            confirmation_line,
            parent_identity=parent_identity,
            destination_name=raw_destination.name,
            published_directory_identity=published_directory_identity,
            delivery_state=delivery_state,
        )
        return _complete_published_command()
    except BaseException as exc:
        if not parent_close_attempted:
            parent_close_attempted = True
            try:
                _close_command_parent_descriptor(parent_descriptor)
            except BaseException:
                pass
        if isinstance(exc, _PublicationRecoveryError):
            raise
        recovery_error = _postpublication_command_error(
            publication_state,
            delivery_state,
        )
        if recovery_error is not None:
            raise recovery_error from exc
        raise


def _cmd_quality_coding_audit_prepare(
    args: argparse.Namespace,
    *,
    output_parent_descriptor: int,
    output_parent_identity: tuple[int, int],
    publication_state: list[_PublishedCommandRecord],
) -> tuple[str, tuple[int, int]]:
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise ValueError("--workspace должен указывать на существующую рабочую папку.")

    raw_destination = Path(args.output_dir).expanduser()
    if not raw_destination.is_absolute():
        raw_destination = Path.cwd() / raw_destination
    try:
        destination_parent = raw_destination.parent.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Родитель --output-dir должен существовать.") from exc
    destination = destination_parent / raw_destination.name
    current_parent_stat = os.stat(destination_parent, follow_symlinks=False)
    held_parent_stat = os.fstat(output_parent_descriptor)
    if (
        (current_parent_stat.st_dev, current_parent_stat.st_ino)
        != output_parent_identity
        or (held_parent_stat.st_dev, held_parent_stat.st_ino)
        != output_parent_identity
    ):
        raise ValueError("Родитель --output-dir изменился во время проверки.")
    try:
        os.stat(
            raw_destination.name,
            dir_fd=output_parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        pass
    else:
        raise ValueError(
            "--output-dir уже существует; перезапись пакета аудита запрещена."
        )
    inside_workspace = False
    try:
        destination.relative_to(workspace)
    except ValueError:
        try:
            inside_workspace = any(
                os.path.samefile(ancestor, workspace)
                for ancestor in (destination_parent, *destination_parent.parents)
            )
        except OSError as exc:
            raise ValueError(
                "Не удалось надёжно проверить, что --output-dir находится вне --workspace."
            ) from exc
    else:
        inside_workspace = True
    if inside_workspace:
        raise ValueError(
            "--output-dir должен находиться вне --workspace, чтобы рабочая папка не изменялась."
        )

    frozen_plan, plan_file_bytes = _verified_frozen_plan(workspace)
    screening_path = workspace / "screening-candidates.jsonl"
    primary_path = workspace / "coding-decisions.jsonl"
    sources_path = workspace / "exports" / "sources.jsonl"
    screening_records, screening_file_bytes = _strict_jsonl_file(screening_path)
    primary_records, primary_file_bytes = _strict_jsonl_file(primary_path)
    source_records, sources_file_bytes = _strict_jsonl_file(sources_path)
    captured_sources = _captured_workspace_source_texts(workspace, source_records)
    codebook_content = _load_audit_codebook(args.codebook_version)
    coding_brief_content = _canonical_json_bytes(
        _build_neutral_coding_brief(
            frozen_plan,
            codebook_version=args.codebook_version,
        )
    )

    regenerated_screening: list[dict[str, Any]] = []
    for source in captured_sources:
        matches = screen_text(source["text"], frozen_plan["query_lanes"])
        if matches:
            regenerated_screening.append(
                {
                    "source_id": source["source_id"],
                    "document_id": source["document_id"],
                    "chain_id": source["chain_id"],
                    "matches": matches,
                    "status": "candidate_needs_full_text_review",
                }
            )
    try:
        saved_screening = sorted(screening_records, key=canonical_digest)
        current_screening = sorted(regenerated_screening, key=canonical_digest)
    except (TypeError, ValueError) as exc:
        raise ValueError("screening-candidates.jsonl содержит неканонический JSON.") from exc
    if saved_screening != current_screening:
        raise ValueError(
            "screening-candidates.jsonl не совпадает с повторным отбором по "
            "текущему замороженному плану и полным текстам."
        )

    bundle = build_native_coding_audit_inputs(
        screening_records,
        primary_records,
        captured_sources,
        plan_sha256=frozen_plan["plan_sha256"],
        codebook_version=args.codebook_version,
        sample_size=args.sample_size,
        exclusion_sample_size=args.exclusion_sample_size,
    )

    content_files: dict[str, bytes] = {
        "screening-candidates.audit.jsonl": _canonical_jsonl_bytes(
            bundle["screening_candidates"]
        ),
        "primary-decisions.audit.jsonl": _canonical_jsonl_bytes(
            bundle["primary_decisions"]
        ),
        "coding-audit-plan.json": _canonical_json_bytes(bundle["audit_plan"]),
        "secondary-review-queue.jsonl": _canonical_jsonl_bytes(
            bundle["secondary_review_queue"]
        ),
        "secondary-coding-template.jsonl": _canonical_jsonl_bytes(
            bundle["secondary_coding_templates"]
        ),
    }
    content_files["independent-review-packet.zip"] = _build_blinded_review_packet(
        bundle,
        plan_sha256=frozen_plan["plan_sha256"],
        codebook_content=codebook_content,
        coding_brief_content=coding_brief_content,
        bundle_contract_version=_CURRENT_AUDIT_BUNDLE_CONTRACT_VERSION,
    )
    file_entries = [
        {
            "path": name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content in content_files.items()
    ]
    audit_plan = bundle["audit_plan"]
    unsigned_manifest = {
        "schema_version": "1.0",
        "bundle_contract_version": _CURRENT_AUDIT_BUNDLE_CONTRACT_VERSION,
        "artifact_type": "coding_audit_input_bundle",
        "producer": "judicial_meaning.quality.coding_audit_prepare",
        "plan_sha256": frozen_plan["plan_sha256"],
        "codebook_version": args.codebook_version,
        "codebook_sha256": hashlib.sha256(codebook_content).hexdigest(),
        "coding_brief_file_sha256": hashlib.sha256(
            coding_brief_content
        ).hexdigest(),
        "source_plan_file_sha256": hashlib.sha256(plan_file_bytes).hexdigest(),
        "source_screening_sha256": hashlib.sha256(screening_file_bytes).hexdigest(),
        "source_primary_sha256": hashlib.sha256(primary_file_bytes).hexdigest(),
        "source_sources_sha256": hashlib.sha256(sources_file_bytes).hexdigest(),
        "source_text_inventory_sha256": bundle["source_text_inventory_sha256"],
        "candidate_ids": [
            record["candidate_id"] for record in bundle["screening_candidates"]
        ],
        "required_candidate_ids": audit_plan["required_candidate_ids"],
        "secondary_review_state": "independent_secondary_required",
        "human_approval_created": False,
        "legal_readiness": False,
        "files": file_entries,
    }
    manifest = {
        **unsigned_manifest,
        "manifest_sha256": canonical_digest(unsigned_manifest),
    }

    post_plan_value, post_plan_bytes = _strict_json_file(_latest_plan_path(workspace))
    post_screening, post_screening_bytes = _strict_jsonl_file(screening_path)
    post_primary, post_primary_bytes = _strict_jsonl_file(primary_path)
    post_sources, post_sources_bytes = _strict_jsonl_file(sources_path)
    post_captured_sources = _captured_workspace_source_texts(workspace, post_sources)
    if (
        post_plan_value != frozen_plan
        or post_plan_bytes != plan_file_bytes
        or post_screening != screening_records
        or post_screening_bytes != screening_file_bytes
        or post_primary != primary_records
        or post_primary_bytes != primary_file_bytes
        or post_sources != source_records
        or post_sources_bytes != sources_file_bytes
        or canonical_digest(post_captured_sources) != canonical_digest(captured_sources)
        or _load_audit_codebook(args.codebook_version) != codebook_content
    ):
        raise ValueError(
            "Рабочие входы изменились во время подготовки; пакет аудита не опубликован."
        )
    published_files = {
        **content_files,
        "coding-audit-inputs-manifest.json": _canonical_json_bytes(manifest),
    }
    _load_native_coding_audit_bundle(
        {
            "files": {
                name: {"content": content}
                for name, content in published_files.items()
            }
        },
        expected_manifest_sha256=manifest["manifest_sha256"],
        installed_codebook_content=codebook_content,
    )
    confirmation_line = _json_output_line(
        {
            "artifact_type": manifest["artifact_type"],
            "bundle_contract_version": manifest["bundle_contract_version"],
            "output_dir": str(destination),
            "manifest_sha256": manifest["manifest_sha256"],
            "independent_review_packet_sha256": hashlib.sha256(
                content_files["independent-review-packet.zip"]
            ).hexdigest(),
            "candidate_count": len(manifest["candidate_ids"]),
            "required_candidate_count": len(manifest["required_candidate_ids"]),
            "secondary_review_state": manifest["secondary_review_state"],
            "human_approval_created": False,
            "legal_readiness": False,
        }
    )
    published_directory_identity = _publish_new_audit_bundle(
        destination,
        published_files,
        parent_descriptor=output_parent_descriptor,
        publication_state=publication_state,
    )
    return confirmation_line, published_directory_identity


def _resolve_new_import_output(
    raw_value: str,
    *,
    bundle_parent_descriptor: int,
) -> Path:
    raw_destination = Path(raw_value).expanduser()
    if not raw_destination.is_absolute():
        raw_destination = Path.cwd() / raw_destination
    if not raw_destination.name or raw_destination.name in {".", ".."}:
        raise ValueError("--output-dir должен называть новую папку.")
    try:
        destination_parent = raw_destination.parent.resolve(strict=True)
    except OSError as exc:
        raise ValueError("Родитель --output-dir должен существовать.") from exc
    flags = _no_follow_open_flags() | getattr(os, "O_DIRECTORY", 0)
    try:
        destination_parent_stat = os.stat(
            destination_parent, follow_symlinks=False
        )
        destination_parent_descriptor = os.open(destination_parent, flags)
    except OSError as exc:
        raise ValueError("Родитель --output-dir должен быть обычной папкой.") from exc
    try:
        opened_parent_stat = os.fstat(destination_parent_descriptor)
        bundle_parent_stat = _assert_safe_publication_parent(
            bundle_parent_descriptor
        )
        if (
            not stat.S_ISDIR(opened_parent_stat.st_mode)
            or destination_parent_stat.st_dev != opened_parent_stat.st_dev
            or destination_parent_stat.st_ino != opened_parent_stat.st_ino
        ):
            raise ValueError("Родитель --output-dir изменился во время открытия.")
        if (
            opened_parent_stat.st_dev != bundle_parent_stat.st_dev
            or opened_parent_stat.st_ino != bundle_parent_stat.st_ino
        ):
            raise ValueError(
                "--output-dir должен быть новой соседней папкой рядом с --bundle."
            )
    finally:
        os.close(destination_parent_descriptor)
    destination = destination_parent / raw_destination.name
    try:
        os.stat(
            raw_destination.name,
            dir_fd=bundle_parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise ValueError("Не удалось проверить --output-dir.") from exc
    else:
        raise ValueError("--output-dir уже существует; перезапись запрещена.")
    return destination


def _secure_codebook_capture(codebook_version: str) -> dict[str, Any]:
    filename = _AUDIT_CODEBOOK_PATHS.get(codebook_version)
    if filename is None:
        raise ValueError("Пакет использует неподдерживаемую версию справочника кодирования.")
    path = Path(__file__).resolve().parents[2] / "references" / filename
    capture = _capture_regular_file(
        path,
        label="штатный справочник кодирования",
        byte_limit=_AUDIT_IMPORT_CODEBOOK_LIMIT,
    )
    try:
        decoded = capture["content"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Штатный справочник кодирования не является UTF-8.") from exc
    if not decoded.strip():
        raise ValueError("Штатный справочник кодирования пуст.")
    return capture


def _load_native_coding_review_import(
    capture: Mapping[str, Any],
    *,
    bundle: Mapping[str, Any],
    expected_import_receipt_sha256: str,
) -> dict[str, Any]:
    files = capture.get("files")
    if not isinstance(files, Mapping) or set(files) != _AUDIT_REVIEW_IMPORT_PATHS:
        raise ValueError("Внутренний снимок --audit-import неполон.")

    def file_bytes(name: str) -> bytes:
        item = files.get(name)
        if not isinstance(item, Mapping) or not isinstance(item.get("content"), bytes):
            raise ValueError(f"Внутренний снимок {name} повреждён.")
        content = item["content"]
        if len(content) > _AUDIT_REVIEW_IMPORT_FILE_LIMITS[name]:
            raise ValueError(f"{name}: файл превышает безопасный предел.")
        return content

    receipt_content = file_bytes("coding-audit-review-import-receipt.json")
    receipt_value = _strict_json_bytes(
        receipt_content,
        label="coding-audit-review-import-receipt.json",
    )
    if (
        not isinstance(receipt_value, Mapping)
        or set(receipt_value) != CODING_AUDIT_REVIEW_IMPORT_RECEIPT_FIELDS
    ):
        raise ValueError("Квитанция импорта имеет неверный закрытый формат.")
    receipt = dict(receipt_value)
    if _canonical_json_bytes(receipt) != receipt_content:
        raise ValueError("Квитанция импорта не является каноническим JSON.")
    unsigned_receipt = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    if receipt.get("receipt_sha256") != canonical_digest(unsigned_receipt):
        raise ValueError("Собственная контрольная сумма квитанции импорта не совпадает.")
    if not _is_lower_sha256(expected_import_receipt_sha256):
        raise ValueError(
            "--expected-import-receipt-sha256 должен содержать 64 строчные "
            "шестнадцатеричные цифры."
        )
    if receipt["receipt_sha256"] != expected_import_receipt_sha256:
        raise ValueError(
            "Квитанция импорта не совпадает с отдельно сохранённым ожидаемым SHA-256."
        )

    manifest = bundle["manifest"]
    audit_plan = bundle["audit_plan"]
    required_candidate_ids = audit_plan.get("required_candidate_ids")
    fixed_contract = {
        "schema_version": "1.0",
        "artifact_type": "coding_audit_review_import_receipt",
        "producer": "judicial_meaning.quality.coding_audit_review_import",
        "bundle_contract_version": manifest["bundle_contract_version"],
        "plan_sha256": manifest["plan_sha256"],
        "audit_plan_sha256": audit_plan["audit_plan_sha256"],
        "codebook_version": manifest["codebook_version"],
        "source_bundle_manifest_sha256": manifest["manifest_sha256"],
        "expected_source_bundle_manifest_sha256": manifest["manifest_sha256"],
        "source_bundle_manifest_file_sha256": hashlib.sha256(
            bundle["manifest_content"]
        ).hexdigest(),
        "review_packet_sha256": hashlib.sha256(
            bundle["review_packet_content"]
        ).hexdigest(),
        "codebook_sha256": manifest["codebook_sha256"],
        "coding_brief_file_sha256": manifest["coding_brief_file_sha256"],
        "candidate_ids": required_candidate_ids,
        "audited_fields": list(AUDITED_CODING_FIELDS),
        "non_audited_content_fields": list(NON_AUDITED_CODING_CONTENT_FIELDS),
        "secondary_coder_label_precommit_verified": False,
        "returned_quote_literal_presence_verified": True,
        "quote_locator_verified": False,
        "secondary_coder_label_differs_from_each_sampled_primary_label": True,
        "single_secondary_coder_label": True,
        "bundle_internal_consistency_verified": True,
        "expected_manifest_digest_match_verified": True,
        "norm_edition_allowlist_membership_verified": True,
        "source_workspace_reverified": False,
        "reviewer_packet_use_attested": False,
        "norm_edition_temporal_applicability_verified": False,
        "reviewer_identity_authenticated": False,
        "human_review_authenticated": False,
        "independence_verified": False,
        "receipt_authenticated": False,
        "publication_safe": False,
        "legal_readiness": False,
    }
    if any(receipt.get(key) != value for key, value in fixed_contract.items()):
        raise ValueError(
            "Квитанция импорта не связана с точным пакетом либо имеет неверные "
            "границы доказанного."
        )
    for field in (
        "secondary_coding_file_sha256",
        "secondary_coding_sha256",
        "audit_decisions_file_sha256",
        "expected_secondary_coder_label_sha256",
    ):
        if not _is_lower_sha256(receipt.get(field)):
            raise ValueError(f"Квитанция импорта содержит неверное поле {field}.")

    audit_decisions_content = file_bytes("audit-decisions.jsonl")
    audit_decisions = _strict_jsonl_bytes(
        audit_decisions_content,
        label="audit-decisions.jsonl",
    )
    if _canonical_jsonl_bytes(audit_decisions) != audit_decisions_content:
        raise ValueError("audit-decisions.jsonl не является каноническим JSONL.")
    if receipt["audit_decisions_file_sha256"] != hashlib.sha256(
        audit_decisions_content
    ).hexdigest():
        raise ValueError(
            "Квитанция импорта не совпадает с точными байтами audit-decisions.jsonl."
        )
    audited_differences = receipt.get("audited_field_differences")
    content_differences = receipt.get("non_audited_content_differences")
    if (
        not isinstance(audited_differences, list)
        or not isinstance(content_differences, list)
        or receipt.get("adjudication_required") is not bool(audited_differences)
        or receipt.get("non_audited_content_review_required")
        is not bool(content_differences)
    ):
        raise ValueError("Карты расхождений квитанции импорта неканоничны.")
    return {
        "receipt": receipt,
        "receipt_content": receipt_content,
        "audit_decisions": audit_decisions,
        "audit_decisions_content": audit_decisions_content,
    }


def cmd_quality_coding_audit_review_import(args: argparse.Namespace) -> int:
    raw_bundle = Path(args.bundle).expanduser()
    if not raw_bundle.is_absolute():
        raw_bundle = Path.cwd() / raw_bundle
    parent_descriptor, bundle_name, bundle_capture = _open_audit_bundle_parent(
        raw_bundle
    )
    publication_state: list[_PublishedCommandRecord] = []
    delivery_state: list[str] = []
    parent_close_attempted = False
    try:
        destination = _resolve_new_import_output(
            args.output_dir,
            bundle_parent_descriptor=parent_descriptor,
        )
        parent_stat = os.fstat(parent_descriptor)
        confirmation_line, published_directory_identity = (
            _cmd_quality_coding_audit_review_import(
                args,
                destination=destination,
                parent_descriptor=parent_descriptor,
                bundle_name=bundle_name,
                bundle_capture=bundle_capture,
                publication_state=publication_state,
            )
        )
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        parent_close_attempted = True
        _close_command_parent_descriptor(parent_descriptor)
        _deliver_published_confirmation(
            confirmation_line,
            parent_identity=parent_identity,
            destination_name=destination.name,
            published_directory_identity=published_directory_identity,
            delivery_state=delivery_state,
        )
        return _complete_published_command()
    except BaseException as exc:
        if not parent_close_attempted:
            parent_close_attempted = True
            try:
                _close_command_parent_descriptor(parent_descriptor)
            except BaseException:
                pass
        if isinstance(exc, _PublicationRecoveryError):
            raise
        recovery_error = _postpublication_command_error(
            publication_state,
            delivery_state,
        )
        if recovery_error is not None:
            raise recovery_error from exc
        raise


def _cmd_quality_coding_audit_review_import(
    args: argparse.Namespace,
    *,
    destination: Path,
    parent_descriptor: int,
    bundle_name: str,
    bundle_capture: Mapping[str, Any],
    publication_state: list[_PublishedCommandRecord],
) -> tuple[str, tuple[int, int]]:

    manifest_preview = _strict_json_bytes(
        bundle_capture["files"]["coding-audit-inputs-manifest.json"]["content"],
        label="coding-audit-inputs-manifest.json",
    )
    if not isinstance(manifest_preview, Mapping):
        raise ValueError("coding-audit-inputs-manifest.json должен содержать объект.")
    codebook_version = manifest_preview.get("codebook_version")
    if not isinstance(codebook_version, str):
        raise ValueError("Манифест не содержит версию справочника кодирования.")
    codebook_capture = _secure_codebook_capture(codebook_version)
    bundle = _load_native_coding_audit_bundle(
        bundle_capture,
        expected_manifest_sha256=args.expected_manifest_sha256,
        installed_codebook_content=codebook_capture["content"],
    )

    raw_secondary = Path(args.secondary_coding).expanduser()
    if not raw_secondary.is_absolute():
        raw_secondary = Path.cwd() / raw_secondary
    secondary_capture = _capture_regular_file(
        raw_secondary,
        label="--secondary-coding",
        byte_limit=_AUDIT_IMPORT_SECONDARY_LIMIT,
    )
    secondary_identity = secondary_capture["identity"][:2]
    if any(
        item["identity"][:2] == secondary_identity
        for item in bundle_capture["files"].values()
    ):
        raise ValueError("--secondary-coding не должен совпадать с файлом --bundle.")
    secondary_records = _strict_jsonl_bytes(
        secondary_capture["content"], label="--secondary-coding"
    )
    coding_brief = bundle["packet"]["coding_brief"]
    norm_editions = coding_brief.get("norm_editions")
    if not isinstance(norm_editions, list):
        raise ValueError("CODING-BRIEF.json не содержит допустимые редакции норм.")
    result = build_native_coding_review_import(
        bundle["audit_plan"],
        bundle["primary"],
        bundle["queue"],
        bundle["packet"]["review_materials"],
        secondary_records,
        codebook_version=codebook_version,
        norm_edition_ids=[
            edition.get("id") for edition in norm_editions if isinstance(edition, Mapping)
        ],
        expected_secondary_coder=args.expected_secondary_coder,
    )
    audit_decisions_content = _canonical_jsonl_bytes(result["audit_decisions"])
    manifest = bundle["manifest"]
    unsigned_receipt = {
        "schema_version": "1.0",
        "artifact_type": "coding_audit_review_import_receipt",
        "producer": "judicial_meaning.quality.coding_audit_review_import",
        "bundle_contract_version": manifest["bundle_contract_version"],
        "plan_sha256": manifest["plan_sha256"],
        "audit_plan_sha256": bundle["audit_plan"]["audit_plan_sha256"],
        "codebook_version": codebook_version,
        "source_bundle_manifest_sha256": manifest["manifest_sha256"],
        "expected_source_bundle_manifest_sha256": args.expected_manifest_sha256,
        "source_bundle_manifest_file_sha256": hashlib.sha256(
            bundle["manifest_content"]
        ).hexdigest(),
        "review_packet_sha256": hashlib.sha256(
            bundle["review_packet_content"]
        ).hexdigest(),
        "secondary_coding_file_sha256": hashlib.sha256(
            secondary_capture["content"]
        ).hexdigest(),
        "secondary_coding_sha256": result["secondary_coding_sha256"],
        "codebook_sha256": manifest["codebook_sha256"],
        "coding_brief_file_sha256": manifest["coding_brief_file_sha256"],
        "audit_decisions_file_sha256": hashlib.sha256(
            audit_decisions_content
        ).hexdigest(),
        "candidate_ids": result["candidate_ids"],
        "audited_fields": result["audited_fields"],
        "non_audited_content_fields": result["non_audited_content_fields"],
        "audited_field_agreement_candidate_ids": result[
            "audited_field_agreement_candidate_ids"
        ],
        "audited_field_disagreement_candidate_ids": result[
            "audited_field_disagreement_candidate_ids"
        ],
        "non_audited_content_difference_candidate_ids": result[
            "non_audited_content_difference_candidate_ids"
        ],
        "audited_field_differences": result["audited_field_differences"],
        "non_audited_content_differences": result[
            "non_audited_content_differences"
        ],
        "non_audited_content_review_required": result[
            "non_audited_content_review_required"
        ],
        "adjudication_required": result["adjudication_required"],
        "expected_secondary_coder_label_sha256": hashlib.sha256(
            result["expected_secondary_coder_label"].encode("utf-8")
        ).hexdigest(),
        "secondary_coder_label_precommit_verified": False,
        "returned_quote_literal_presence_verified": True,
        "quote_locator_verified": False,
        "secondary_coder_label_differs_from_each_sampled_primary_label": True,
        "single_secondary_coder_label": True,
        "bundle_internal_consistency_verified": True,
        "expected_manifest_digest_match_verified": True,
        "norm_edition_allowlist_membership_verified": True,
        "source_workspace_reverified": False,
        "reviewer_packet_use_attested": False,
        "norm_edition_temporal_applicability_verified": False,
        "reviewer_identity_authenticated": False,
        "human_review_authenticated": False,
        "independence_verified": False,
        "receipt_authenticated": False,
        "publication_safe": False,
        "legal_readiness": False,
    }
    receipt = {
        **unsigned_receipt,
        "receipt_sha256": canonical_digest(unsigned_receipt),
    }
    receipt_content = _canonical_json_bytes(receipt)

    if (
        _capture_audit_bundle_at(parent_descriptor, bundle_name) != bundle_capture
        or _capture_regular_file(
            raw_secondary,
            label="--secondary-coding",
            byte_limit=_AUDIT_IMPORT_SECONDARY_LIMIT,
        )
        != secondary_capture
        or _secure_codebook_capture(codebook_version) != codebook_capture
    ):
        raise ValueError(
            "Входы изменились во время импорта; решения и квитанция не опубликованы."
        )
    confirmation_line = _json_output_line(
        {
            "artifact_type": receipt["artifact_type"],
            "output_dir": str(destination),
            "receipt_sha256": receipt["receipt_sha256"],
            "audit_decisions_file_sha256": receipt[
                "audit_decisions_file_sha256"
            ],
            "candidate_count": len(result["candidate_ids"]),
            "audited_field_agreement_count": len(
                result["audited_field_agreement_candidate_ids"]
            ),
            "audited_field_disagreement_count": len(
                result["audited_field_disagreement_candidate_ids"]
            ),
            "non_audited_content_difference_count": len(
                result["non_audited_content_difference_candidate_ids"]
            ),
            "audited_field_differences": result["audited_field_differences"],
            "non_audited_content_differences": result[
                "non_audited_content_differences"
            ],
            "non_audited_content_review_required": result[
                "non_audited_content_review_required"
            ],
            "adjudication_required": result["adjudication_required"],
            "expected_secondary_coder_label_sha256": receipt[
                "expected_secondary_coder_label_sha256"
            ],
            "secondary_coder_label_precommit_verified": False,
            "returned_quote_literal_presence_verified": True,
            "quote_locator_verified": False,
            "secondary_coder_label_differs_from_each_sampled_primary_label": True,
            "single_secondary_coder_label": True,
            "bundle_internal_consistency_verified": True,
            "expected_manifest_digest_match_verified": True,
            "norm_edition_allowlist_membership_verified": True,
            "source_workspace_reverified": False,
            "reviewer_packet_use_attested": False,
            "norm_edition_temporal_applicability_verified": False,
            "reviewer_identity_authenticated": False,
            "human_review_authenticated": False,
            "independence_verified": False,
            "receipt_authenticated": False,
            "publication_safe": False,
            "legal_readiness": False,
        }
    )
    published_directory_identity = _publish_new_audit_bundle(
        destination,
        {
            "audit-decisions.jsonl": audit_decisions_content,
            "coding-audit-review-import-receipt.json": receipt_content,
        },
        parent_descriptor=parent_descriptor,
        publication_state=publication_state,
    )
    return confirmation_line, published_directory_identity


def cmd_quality_coding_audit_finalize(args: argparse.Namespace) -> int:
    raw_bundle = Path(args.bundle).expanduser()
    if not raw_bundle.is_absolute():
        raw_bundle = Path.cwd() / raw_bundle
    parent_descriptor, bundle_name, opened_bundle_capture = (
        _open_audit_bundle_parent(raw_bundle)
    )
    publication_state: list[_PublishedCommandRecord] = []
    delivery_state: list[str] = []
    parent_close_attempted = False
    try:
        destination = _resolve_new_import_output(
            args.output_dir,
            bundle_parent_descriptor=parent_descriptor,
        )
        import_name, import_capture = _resolve_existing_audit_import(
            args.audit_import,
            parent_descriptor=parent_descriptor,
            bundle_name=bundle_name,
        )
        if destination.name in {bundle_name, import_name}:
            raise ValueError(
                "--bundle, --audit-import и --output-dir должны называть три "
                "разные соседние папки."
            )
        bundle_capture = _capture_private_native_audit_bundle_at(
            parent_descriptor,
            bundle_name,
        )
        if bundle_capture != opened_bundle_capture:
            raise ValueError("--bundle изменился во время начальной проверки.")
        parent_stat = os.fstat(parent_descriptor)
        result_line, published_directory_identity = (
            _cmd_quality_coding_audit_finalize(
                args,
                destination=destination,
                parent_descriptor=parent_descriptor,
                bundle_name=bundle_name,
                bundle_capture=bundle_capture,
                import_name=import_name,
                import_capture=import_capture,
                publication_state=publication_state,
            )
        )
        parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        parent_close_attempted = True
        _close_command_parent_descriptor(parent_descriptor)
        if published_directory_identity is None:
            _write_stdout_line(result_line)
            return 3
        _deliver_published_confirmation(
            result_line,
            parent_identity=parent_identity,
            destination_name=destination.name,
            published_directory_identity=published_directory_identity,
            delivery_state=delivery_state,
        )
        return _complete_published_command()
    except BaseException as exc:
        if not parent_close_attempted:
            parent_close_attempted = True
            try:
                _close_command_parent_descriptor(parent_descriptor)
            except BaseException:
                pass
        if isinstance(exc, _PublicationRecoveryError):
            raise
        recovery_error = _postpublication_command_error(
            publication_state,
            delivery_state,
        )
        if recovery_error is not None:
            raise recovery_error from exc
        raise


def _value_free_reliability_diagnostics(value: Any) -> dict[str, Any]:
    """Project an unresolved reliability report without coding/person values."""

    if not isinstance(value, Mapping):
        raise ValueError("Неполный отчёт надёжности имеет неверный формат.")

    def safe_ids(field: str) -> list[str]:
        items = value.get(field)
        if not isinstance(items, list) or not all(
            isinstance(item, str)
            and (
                _is_native_audit_candidate_id(item)
                or item.startswith("audit-plan-")
            )
            for item in items
        ):
            raise ValueError(
                "Неполный отчёт надёжности содержит небезопасную диагностику."
            )
        return list(items)

    disagreement_population: list[dict[str, Any]] = []
    disagreements = value.get("field_disagreements")
    if not isinstance(disagreements, list):
        raise ValueError("Неполный отчёт надёжности не содержит карту расхождений.")
    for disagreement in disagreements:
        if not isinstance(disagreement, Mapping):
            raise ValueError("Карта расхождений надёжности имеет неверный формат.")
        candidate_id = disagreement.get("candidate_id")
        fields = disagreement.get("fields")
        if (
            not _is_native_audit_candidate_id(candidate_id)
            or not isinstance(fields, list)
            or not all(field in AUDITED_CODING_FIELDS for field in fields)
            or not isinstance(disagreement.get("resolved"), bool)
        ):
            raise ValueError("Карта расхождений надёжности неканонична.")
        disagreement_population.append(
            {
                "candidate_id": candidate_id,
                "fields": list(fields),
                "resolved": disagreement["resolved"],
            }
        )

    false_exclusions = value.get("false_exclusion_diagnostics")
    if not isinstance(false_exclusions, list) or not all(
        isinstance(item, Mapping)
        and _is_native_audit_candidate_id(item.get("candidate_id"))
        for item in false_exclusions
    ):
        raise ValueError("Диагностика ложных исключений имеет неверный формат.")
    evidence_sha256 = value.get("evidence_sha256")
    if not _is_lower_sha256(evidence_sha256):
        raise ValueError("Неполный отчёт надёжности не имеет точной контрольной суммы.")

    id_fields = (
        "required_candidate_ids",
        "audited_candidate_ids",
        "missing_candidate_ids",
        "same_reviewer_candidate_ids",
        "invalid_binding_candidate_ids",
        "invalid_provenance_candidate_ids",
        "invalid_screening_record_ids",
        "invalid_primary_record_ids",
        "invalid_audit_record_ids",
        "invalid_adjudication_record_ids",
        "unresolved_candidate_ids",
    )
    return {
        "evidence_sha256": evidence_sha256,
        **{field: safe_ids(field) for field in id_fields},
        "field_disagreements": disagreement_population,
        "false_exclusion_candidate_ids": [
            item["candidate_id"] for item in false_exclusions
        ],
        "stale": value.get("stale") is True,
        "complete": False,
    }


def _cmd_quality_coding_audit_finalize(
    args: argparse.Namespace,
    *,
    destination: Path,
    parent_descriptor: int,
    bundle_name: str,
    bundle_capture: Mapping[str, Any],
    import_name: str,
    import_capture: Mapping[str, Any],
    publication_state: list[_PublishedCommandRecord],
) -> tuple[str, tuple[int, int] | None]:
    manifest_preview = _strict_json_bytes(
        bundle_capture["files"]["coding-audit-inputs-manifest.json"]["content"],
        label="coding-audit-inputs-manifest.json",
    )
    if not isinstance(manifest_preview, Mapping):
        raise ValueError("coding-audit-inputs-manifest.json должен содержать объект.")
    codebook_version = manifest_preview.get("codebook_version")
    if not isinstance(codebook_version, str):
        raise ValueError("Манифест не содержит версию справочника кодирования.")
    codebook_capture = _secure_codebook_capture(codebook_version)
    bundle = _load_native_coding_audit_bundle(
        bundle_capture,
        expected_manifest_sha256=args.expected_manifest_sha256,
        installed_codebook_content=codebook_capture["content"],
    )
    imported = _load_native_coding_review_import(
        import_capture,
        bundle=bundle,
        expected_import_receipt_sha256=args.expected_import_receipt_sha256,
    )

    resolutions_capture: dict[str, Any] | None = None
    resolutions: list[dict[str, Any]] | None = None
    resolutions_name: str | None = None
    if args.resolutions is not None:
        resolutions_name, resolutions_capture = (
            _resolve_private_finalization_resolutions(
                args.resolutions,
                parent_descriptor=parent_descriptor,
            )
        )
        input_identities = {
            item["identity"][:2]
            for capture in (bundle_capture, import_capture)
            for item in capture["files"].values()
        }
        if resolutions_capture["identity"][:2] in input_identities:
            raise ValueError(
                "--resolutions должен быть отдельным файлом, а не файлом пакета "
                "или штатного импорта."
            )
        resolutions = _strict_jsonl_bytes(
            resolutions_capture["content"],
            label="--resolutions",
        )

    coding_brief = bundle["packet"]["coding_brief"]
    norm_editions = coding_brief.get("norm_editions")
    if not isinstance(norm_editions, list):
        raise ValueError("CODING-BRIEF.json не содержит допустимые редакции норм.")
    norm_edition_ids = [
        edition.get("id")
        for edition in norm_editions
        if isinstance(edition, Mapping)
    ]
    result = build_native_coding_audit_finalization(
        bundle["audit_plan"],
        bundle["primary"],
        bundle["packet"]["review_materials"],
        imported["audit_decisions"],
        imported["receipt"],
        resolutions,
        expected_import_receipt_sha256=args.expected_import_receipt_sha256,
        norm_edition_ids=norm_edition_ids,
    )
    required_result_fields = {
        "complete",
        "incomplete_reason",
        "candidate_ids",
        "required_difference_pairs",
        "missing_difference_pairs",
        "resolved_review_decisions",
        "resolved_review_decisions_sha256",
        "adjudications",
        "adjudications_sha256",
        "coding_reliability",
        "final_coding_sha256",
        "resolved_candidate_ids",
        "resolved_field_populations",
        "quote_locator_review_declared",
        "final_quote_literal_presence_verified",
        "final_quote_normalized_presence_verified",
        "difference_resolution_bijection_verified",
        "quote_locator_verified",
        "reliability_complete",
    }
    if not isinstance(result, Mapping) or not required_result_fields.issubset(result):
        raise ValueError("Внутренняя финализация вернула неполный результат.")

    current_bundle_capture = _capture_private_native_audit_bundle_at(
        parent_descriptor,
        bundle_name,
    )
    current_import_capture = _capture_audit_review_import_at(
        parent_descriptor,
        import_name,
    )
    current_codebook_capture = _secure_codebook_capture(codebook_version)
    current_resolutions_capture = (
        _capture_private_finalization_resolutions_at(
            parent_descriptor,
            resolutions_name,
        )
        if resolutions_capture is not None and resolutions_name is not None
        else None
    )
    if (
        current_bundle_capture != bundle_capture
        or current_import_capture != import_capture
        or current_codebook_capture != codebook_capture
        or current_resolutions_capture != resolutions_capture
    ):
        raise ValueError(
            "Входы изменились во время финализации; итоговая папка не опубликована."
        )

    if result.get("complete") is not True:
        incomplete_reason = result.get("incomplete_reason")
        if incomplete_reason == "resolution_incomplete":
            variable_diagnostics = {
                "missing_difference_pairs": result["missing_difference_pairs"],
            }
        elif incomplete_reason == "reliability_unresolved":
            variable_diagnostics = {
                "reliability_complete": False,
                "reliability_diagnostics": _value_free_reliability_diagnostics(
                    result.get("coding_reliability")
                ),
            }
        else:
            raise ValueError(
                "Внутренняя финализация вернула неизвестную причину неполноты."
            )
        incomplete_line = _json_output_line(
            {
                "artifact_type": "coding_audit_finalization_incomplete",
                "complete": False,
                "incomplete_reason": incomplete_reason,
                **variable_diagnostics,
                "output_created": False,
                "publication_safe": False,
                "legal_readiness": False,
            }
        )
        return incomplete_line, None

    if (
        result.get("missing_difference_pairs") != []
        or result.get("candidate_ids")
        != bundle["audit_plan"]["required_candidate_ids"]
        or result.get("difference_resolution_bijection_verified") is not True
        or result.get("final_quote_literal_presence_verified") is not True
        or result.get("final_quote_normalized_presence_verified") is not True
        or not isinstance(result.get("coding_reliability"), Mapping)
        or result["coding_reliability"].get("complete") is not True
        or result.get("reliability_complete") is not True
        or result.get("quote_locator_verified") is not False
        or not isinstance(result.get("resolved_review_decisions"), list)
        or not isinstance(result.get("adjudications"), list)
        or not _is_lower_sha256(result.get("final_coding_sha256"))
    ):
        raise ValueError(
            "Внутренняя финализация не подтвердила все обязательные технические проверки."
        )

    resolved_content = _canonical_jsonl_bytes(result["resolved_review_decisions"])
    adjudications_content = _canonical_jsonl_bytes(result["adjudications"])
    reliability_content = _canonical_json_bytes(result["coding_reliability"])
    if (
        result.get("resolved_review_decisions_sha256")
        != canonical_digest(result["resolved_review_decisions"])
        or result.get("adjudications_sha256")
        != canonical_digest(result["adjudications"])
        or result["final_coding_sha256"]
        != canonical_digest(
            [
                decision.get("final_coding")
                for decision in result["resolved_review_decisions"]
                if isinstance(decision, Mapping)
            ]
        )
    ):
        raise ValueError("Внутренние контрольные суммы финализации не совпадают.")
    manifest = bundle["manifest"]
    import_receipt = imported["receipt"]
    resolutions_present = resolutions_capture is not None
    resolutions_file_sha256 = (
        hashlib.sha256(resolutions_capture["content"]).hexdigest()
        if resolutions_capture is not None
        else None
    )
    resolutions_state_sha256 = canonical_digest(
        {
            "present": resolutions_present,
            "file_sha256": resolutions_file_sha256,
        }
    )
    unsigned_receipt = {
        "schema_version": "1.0",
        "artifact_type": "coding_audit_finalization_receipt",
        "producer": "judicial_meaning.quality.coding_audit_finalize",
        "bundle_contract_version": manifest["bundle_contract_version"],
        "plan_sha256": manifest["plan_sha256"],
        "audit_plan_sha256": bundle["audit_plan"]["audit_plan_sha256"],
        "codebook_version": codebook_version,
        "source_bundle_manifest_sha256": manifest["manifest_sha256"],
        "expected_source_bundle_manifest_sha256": args.expected_manifest_sha256,
        "source_bundle_manifest_file_sha256": hashlib.sha256(
            bundle["manifest_content"]
        ).hexdigest(),
        "audit_plan_file_sha256": hashlib.sha256(
            bundle_capture["files"]["coding-audit-plan.json"]["content"]
        ).hexdigest(),
        "primary_decisions_file_sha256": hashlib.sha256(
            bundle_capture["files"]["primary-decisions.audit.jsonl"]["content"]
        ).hexdigest(),
        "review_packet_sha256": hashlib.sha256(
            bundle["review_packet_content"]
        ).hexdigest(),
        "codebook_sha256": manifest["codebook_sha256"],
        "coding_brief_file_sha256": manifest["coding_brief_file_sha256"],
        "audit_import_receipt_sha256": import_receipt["receipt_sha256"],
        "expected_audit_import_receipt_sha256": args.expected_import_receipt_sha256,
        "audit_import_receipt_file_sha256": hashlib.sha256(
            imported["receipt_content"]
        ).hexdigest(),
        "audit_decisions_file_sha256": hashlib.sha256(
            imported["audit_decisions_content"]
        ).hexdigest(),
        "resolutions_present": resolutions_present,
        "resolutions_file_sha256": resolutions_file_sha256,
        "resolutions_state_sha256": resolutions_state_sha256,
        "resolved_review_decisions_file_sha256": hashlib.sha256(
            resolved_content
        ).hexdigest(),
        "adjudications_file_sha256": hashlib.sha256(
            adjudications_content
        ).hexdigest(),
        "coding_reliability_file_sha256": hashlib.sha256(
            reliability_content
        ).hexdigest(),
        "candidate_ids": result["candidate_ids"],
        "required_difference_pairs": result["required_difference_pairs"],
        "resolved_candidate_ids": result["resolved_candidate_ids"],
        "resolved_field_populations": result["resolved_field_populations"],
        "final_coding_sha256": result["final_coding_sha256"],
        "difference_resolution_bijection_verified": True,
        "final_quote_literal_presence_verified": True,
        "final_quote_normalized_presence_verified": True,
        "quote_locator_review_declared": result["quote_locator_review_declared"],
        "quote_locator_verified": False,
        "reliability_complete": True,
        "source_workspace_reverified": False,
        "reviewer_identity_authenticated": False,
        "human_review_authenticated": False,
        "independence_verified": False,
        "receipt_authenticated": False,
        "norm_edition_temporal_applicability_verified": False,
        "publication_safe": False,
        "legal_readiness": False,
    }
    receipt = {
        **unsigned_receipt,
        "receipt_sha256": canonical_digest(unsigned_receipt),
    }
    receipt_content = _canonical_json_bytes(receipt)
    confirmation_line = _json_output_line(
        {
            "artifact_type": receipt["artifact_type"],
            "receipt_sha256": receipt["receipt_sha256"],
            "output_files": [
                "resolved-review-decisions.jsonl",
                "adjudications.jsonl",
                "coding-reliability.json",
                "coding-audit-finalization-receipt.json",
            ],
            "candidate_count": len(receipt["candidate_ids"]),
            "required_difference_pair_count": len(
                receipt["required_difference_pairs"]
            ),
            "resolved_candidate_ids": receipt["resolved_candidate_ids"],
            "resolved_field_populations": receipt["resolved_field_populations"],
            "difference_resolution_bijection_verified": True,
            "final_quote_literal_presence_verified": True,
            "final_quote_normalized_presence_verified": True,
            "quote_locator_review_declared": receipt[
                "quote_locator_review_declared"
            ],
            "quote_locator_verified": False,
            "reliability_complete": True,
            "source_workspace_reverified": False,
            "reviewer_identity_authenticated": False,
            "human_review_authenticated": False,
            "independence_verified": False,
            "receipt_authenticated": False,
            "norm_edition_temporal_applicability_verified": False,
            "publication_safe": False,
            "legal_readiness": False,
        }
    )
    published_directory_identity = _publish_new_audit_bundle(
        destination,
        {
            "resolved-review-decisions.jsonl": resolved_content,
            "adjudications.jsonl": adjudications_content,
            "coding-reliability.json": reliability_content,
            "coding-audit-finalization-receipt.json": receipt_content,
        },
        parent_descriptor=parent_descriptor,
        publication_state=publication_state,
    )
    return confirmation_line, published_directory_identity


def cmd_quality_coding_reliability(args: argparse.Namespace) -> int:
    audit_plan, _ = _strict_json_file(Path(args.audit_plan).expanduser().resolve())
    if not isinstance(audit_plan, Mapping):
        raise ValueError("--audit-plan должен содержать JSON-объект.")
    result = assess_coding_reliability(
        audit_plan,
        _strict_quality_records(args.primary_decisions, "--primary-decisions"),
        _strict_quality_records(args.audit_decisions, "--audit-decisions"),
        (
            _strict_quality_records(args.adjudications, "--adjudications")
            if args.adjudications
            else []
        ),
    )
    return _quality_gate_result(args, result)


def cmd_quality_prefiling_refresh(args: argparse.Namespace) -> int:
    refresh_plan = read_json(Path(args.refresh_plan).expanduser().resolve())
    if not isinstance(refresh_plan, Mapping):
        raise ValueError("--refresh-plan должен содержать JSON-объект.")
    corpus_prefix = "corpus-evidence-sha256:"
    baseline_digest = args.baseline_corpus_digest.removeprefix(corpus_prefix)
    current_digest = args.current_corpus_digest.removeprefix(corpus_prefix)
    treatment_set = read_json(Path(args.treatments).expanduser().resolve())
    if (
        not isinstance(treatment_set, Mapping)
        or set(treatment_set)
        != {
            "schema_version",
            "export_type",
            "corpus_evidence_digest",
            "treatment_population_sha256",
            "integrity_issue_ids",
            "treatment_ids",
            "items",
            "set_sha256",
        }
    ):
        raise ValueError(
            "--treatments должен содержать полный JSON-экспорт команды "
            "cache treatment quality-export."
        )
    with PublicCorpus.open_read_only(Path(args.corpus_root)) as corpus:
        live_corpus_binding = corpus.verify_prefiling_inputs(
            refresh_plan=refresh_plan,
            treatment_set=treatment_set,
            current_corpus_digest=current_digest,
        )
    result = assess_prefiling_refresh(
        baseline_corpus_digest=baseline_digest,
        current_corpus_digest=current_digest,
        subject_evidence_sha256=args.subject_evidence_sha256,
        refresh_plan=refresh_plan,
        treatments=treatment_set,
        checked_through=args.checked_through,
        filing_cutoff=args.filing_cutoff,
        reviewer=args.reviewer,
        reviewed_at=args.reviewed_at,
        claim_ids=args.claim_id or [],
        live_corpus_binding=live_corpus_binding,
    )
    return _quality_gate_result(args, result)


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


def _unique_nonempty_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = " ".join(value.split())
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _selected_records(
    records: list[dict[str, Any]],
    *,
    id_field: str,
    required_ids: set[str],
    label: str,
) -> list[dict[str, Any]]:
    by_id = {
        str(record.get(id_field)): record
        for record in records
        if isinstance(record, dict) and record.get(id_field)
    }
    missing = sorted(required_ids - set(by_id))
    if missing:
        raise ValueError(f"{label}: отсутствуют выбранные ID: " + ", ".join(missing) + ".")
    return [by_id[identifier] for identifier in sorted(required_ids)]


def _load_v2_request(path_value: str) -> dict[str, Any]:
    request = read_json(Path(path_value).expanduser().resolve())
    if not isinstance(request, dict):
        raise ValueError("--request должен содержать JSON envelope v2.")
    checked = check_handoff(
        request,
        expected_target="ksrf-cassation-judicial-meaning",
    )
    if not checked.get("valid"):
        raise ValueError(
            "--request не прошёл fail-closed проверку: "
            + " ".join(str(item) for item in checked.get("errors", []))
        )
    if request.get("payload_type") != "unproven_research_questions":
        raise ValueError("--request должен иметь payload_type=unproven_research_questions.")
    return request


def _quality_artifact_type(value: Mapping[str, Any]) -> str:
    if value.get("artifact_type") == "coding_audit_finalization_receipt":
        return "coding_audit_finalization_receipt"
    if "profile_id" in value and "dimensions" in value:
        return "uncertainty_profile"
    if "refresh_id" in value and "status" in value:
        return "prefiling_refresh"
    if "audit_plan_sha256" in value and "required_candidate_ids" in value:
        if "field_disagreements" in value or "current_primary_coding_sha256" in value:
            return "coding_reliability"
        return "coding_audit_plan"
    if "trajectories" in value and "review_complete" in value:
        return "chain_stage_propagation"
    raise ValueError("Не удалось определить тип practice-quality артефакта.")


def _read_private_quality_json(
    path_value: str,
    option: str,
    *,
    strict: bool = False,
    require_canonical: bool = False,
) -> tuple[dict[str, Any], bytes]:
    """Read private quality input once and keep diagnostics value-free."""

    try:
        path = Path(path_value).expanduser().resolve()
        content = path.read_bytes()
        text_value = content.decode("utf-8")
        value = (
            json.loads(
                text_value,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_closed_json_object,
            )
            if strict
            else json.loads(text_value)
        )
        if not isinstance(value, dict):
            raise ValueError("not-an-object")
        if require_canonical and content != _canonical_json_bytes(value):
            raise ValueError("non-canonical")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ):
        raise ValueError(f"{option}: не удалось прочитать канонический JSON.") from None
    return value, content


def _optional_private_quality_json(
    path_value: str | None,
    option: str,
    *,
    strict: bool = False,
    require_canonical: bool = False,
) -> Any:
    """Read private quality input without echoing its path or contents on failure."""

    if not path_value:
        return None
    value, _ = _read_private_quality_json(
        path_value,
        option,
        strict=strict,
        require_canonical=require_canonical,
    )
    return value


def _load_quality_bindings(
    path_values: Iterable[str],
    *,
    expected_finalization_receipt_sha256: str | None = None,
) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for path_value in path_values:
        artifact, content = _read_private_quality_json(
            path_value,
            "--quality-binding",
            strict=True,
        )
        quality_type = _quality_artifact_type(artifact)
        if (
            quality_type == "coding_reliability"
            and content != _canonical_json_bytes(artifact)
        ):
            raise ValueError(
                "--quality-binding: coding-reliability должен сохранять точные "
                "канонические байты финализатора с одним завершающим LF."
            )
        binding = {
            "quality_type": quality_type,
            "artifact_sha256": artifact_sha256(artifact),
            "artifact": artifact,
        }
        if quality_type == "coding_audit_finalization_receipt":
            if expected_finalization_receipt_sha256 is None:
                raise ValueError(
                    "Квитанция финализации требует отдельно сохранённый внешний "
                    "SHA-256 из успешного coding-audit-finalize."
                )
            if not _is_lower_sha256(expected_finalization_receipt_sha256):
                raise ValueError(
                    "--expected-finalization-receipt-sha256 должен быть "
                    "строчным SHA-256 из 64 шестнадцатеричных знаков."
                )
            binding["expected_receipt_sha256"] = (
                expected_finalization_receipt_sha256
            )
        bindings.append(binding)
    receipt_count = sum(
        item["quality_type"] == "coding_audit_finalization_receipt"
        for item in bindings
    )
    if expected_finalization_receipt_sha256 is not None and receipt_count != 1:
        raise ValueError(
            "--expected-finalization-receipt-sha256 требует ровно одну "
            "квитанцию финализации среди --quality-binding."
        )
    return sorted(
        bindings,
        key=lambda item: (item["quality_type"], item["artifact_sha256"]),
    )


def _build_reviewed_handoff_payload(
    workspace: Path,
    args: argparse.Namespace,
    *,
    plan_sha256: str,
    evidence_sha256: str,
    fingerprint_sha256: str,
    maximum_permitted_claim: str,
    limitations: list[str],
) -> dict[str, Any]:
    """Derive a reviewed payload only from current approved workspace artifacts."""

    if not args.request:
        raise ValueError("Проверенный handoff требует --request v2.")
    request = _load_v2_request(args.request)
    request_payload = request["payload"]
    request_bindings = {
        str(binding.get("claim_id")): binding
        for binding in request_payload.get("claim_bindings", [])
        if isinstance(binding, dict) and binding.get("claim_id")
    }
    requested_claim_ids = set(args.claim_id or request_bindings)
    if not requested_claim_ids:
        raise ValueError("Не выбрано ни одного claim_id из request.")
    unknown_claim_ids = sorted(requested_claim_ids - set(request_bindings))
    if unknown_claim_ids:
        raise ValueError(
            "--claim-id отсутствует в request: " + ", ".join(unknown_claim_ids) + "."
        )
    omitted_claim_ids = sorted(set(request_bindings) - requested_claim_ids)
    if omitted_claim_ids:
        raise ValueError(
            "Частичный reviewed result запрещён: не выбраны claim_id "
            + ", ".join(omitted_claim_ids)
            + ". Создайте отдельный request для более узкого набора требований."
        )
    selected_claim_bindings = [
        request_bindings[claim_id] for claim_id in sorted(requested_claim_ids)
    ]

    bridge = read_json(workspace / "normative-bridge.json")
    decision = read_json(workspace / "human-decision.json")
    validation = read_json(workspace / "validation-report.json")
    adverse = read_json(workspace / "case-adverse-review.json")
    for label, value in (
        ("normative-bridge.json", bridge),
        ("human-decision.json", decision),
        ("validation-report.json", validation),
        ("case-adverse-review.json", adverse),
    ):
        if not isinstance(value, dict):
            raise ValueError(f"{label} должен быть JSON-объектом.")

    supporting_ids = bridge.get("supporting_position_card_ids", [])
    adverse_ids = bridge.get("adverse_position_card_ids", [])
    if not isinstance(supporting_ids, list) or not isinstance(adverse_ids, list):
        raise ValueError("Нормативный мост должен явно выбрать supporting/adverse карточки.")
    required_position_ids = {
        str(identifier)
        for identifier in [*supporting_ids, *adverse_ids]
        if isinstance(identifier, str) and identifier.strip()
    }
    selector_position_ids = set(args.position_card_id or required_position_ids)
    if selector_position_ids != required_position_ids:
        missing = sorted(required_position_ids - selector_position_ids)
        invented = sorted(selector_position_ids - required_position_ids)
        details = []
        if missing:
            details.append("пропущены " + ", ".join(missing))
        if invented:
            details.append("не выбраны мостом " + ", ".join(invented))
        raise ValueError(
            "--position-card-id должен точно совпадать с нормативным мостом: "
            + "; ".join(details)
            + "."
        )
    cards = _selected_records(
        read_jsonl(workspace / "position-cards.jsonl"),
        id_field="position_card_id",
        required_ids=required_position_ids,
        label="position-cards.jsonl",
    )
    comparisons = _selected_records(
        read_jsonl(workspace / "comparability-matrix.jsonl"),
        id_field="position_card_id",
        required_ids=required_position_ids,
        label="comparability-matrix.jsonl",
    )
    relations = _selected_records(
        read_jsonl(workspace / "applicant-relations.jsonl"),
        id_field="position_card_id",
        required_ids=required_position_ids,
        label="applicant-relations.jsonl",
    )
    selected_proofs = {
        "position_cards": cards,
        "comparisons": comparisons,
        "relations": relations,
        "adverse": adverse,
        "bridge": bridge,
        "human_decision": decision,
        "validation_report": validation,
    }
    approval_binding = {
        "human_decision_sha256": artifact_sha256(decision),
        "validation_report_sha256": artifact_sha256(validation),
        "normative_bridge_sha256": artifact_sha256(bridge),
        "reviewer": decision.get("reviewer"),
        "approved_at": decision.get("decided_at"),
    }
    common = {
        "drafting_ready": True,
        "request_handoff_id": request["handoff_id"],
        "request_sha256": request_payload["request_sha256"],
        "claim_set_sha256": request_payload["claim_set_sha256"],
        "claim_bindings": selected_claim_bindings,
        "supporting_position_card_ids": list(supporting_ids),
        "adverse_position_card_ids": list(adverse_ids),
        "approval_binding": approval_binding,
        "artifact_manifest": build_artifact_manifest(selected_proofs),
        "selected_position_set_sha256": build_selected_position_set_sha256(
            selected_proofs
        ),
        "selected_proofs": selected_proofs,
        "maximum_permitted_claim": maximum_permitted_claim,
        "limitations": limitations,
    }
    quality_bindings = _load_quality_bindings(
        getattr(args, "quality_binding", []) or [],
        expected_finalization_receipt_sha256=getattr(
            args, "expected_finalization_receipt_sha256", None
        ),
    )
    if quality_bindings:
        common["quality_bindings"] = quality_bindings
    if args.payload_type == "authority_cards":
        return {
            **common,
            "authority_cards": cards,
            "reviewer": decision.get("reviewer"),
            "review_state": "approved",
        }

    candidates = read_jsonl(workspace / "thesis-candidates.jsonl")
    decision_candidate_ids = {
        str(candidate_id)
        for candidate_id in decision.get("candidate_ids", [])
        if isinstance(candidate_id, str) and candidate_id.strip()
    }
    selected_candidate_ids = set(args.candidate_id or decision_candidate_ids)
    if not selected_candidate_ids:
        raise ValueError("Не выбрано ни одного одобренного candidate_id.")
    unknown_candidate_ids = sorted(selected_candidate_ids - decision_candidate_ids)
    if unknown_candidate_ids:
        raise ValueError(
            "--candidate-id отсутствует в human-decision: "
            + ", ".join(unknown_candidate_ids)
            + "."
        )
    selected_candidates = _selected_records(
        candidates,
        id_field="candidate_id",
        required_ids=selected_candidate_ids,
        label="thesis-candidates.jsonl",
    )
    findings = [
        build_approved_finding(candidate, sorted(requested_claim_ids), bridge)
        for candidate in selected_candidates
    ]
    return {**common, "findings": findings}


def _persist_trusted_source_material(
    workspace: Path,
    envelope: Mapping[str, Any],
    *,
    request_path: str,
) -> None:
    """Persist source-workspace trust anchors outside the portable envelope."""

    request = _load_v2_request(request_path)
    request_id = envelope["payload"]["request_handoff_id"]
    if request.get("handoff_id") != request_id:
        raise ValueError("Trusted request не совпадает с request_handoff_id результата.")
    write_json(
        workspace / "handoffs" / "trusted-requests" / f"{request_id}.json",
        request,
    )
    for binding in envelope["payload"].get("quality_bindings", []):
        write_json(
            workspace
            / "handoffs"
            / "trusted-quality"
            / f"{binding['quality_type']}-{binding['artifact_sha256']}.json",
            binding["artifact"],
        )
    write_json(
        workspace
        / "handoffs"
        / "trusted-results"
        / f"{envelope['handoff_id']}.json",
        build_trusted_source_receipt(envelope),
    )


def cmd_handoff_create(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    if args.payload_type == "selected_authorities":
        raise ValueError(
            "selected_authorities относится к legacy v1; используйте authority_cards v2."
        )
    if args.payload_type == "unproven_research_questions" and not args.payload:
        raise ValueError("unproven_research_questions требует --payload.")
    if (
        args.payload_type == "unproven_research_questions"
        and getattr(args, "expected_finalization_receipt_sha256", None) is not None
    ):
        raise ValueError(
            "Непроверенный handoff не принимает внешний SHA-256 финализации."
        )
    if args.payload_type != "unproven_research_questions" and args.payload:
        raise ValueError(
            "Проверенный handoff нельзя создавать из произвольного --payload; "
            "используйте --request и селекторы одобренных артефактов."
        )
    plan_sha256, evidence_sha256 = _handoff_hashes(workspace)
    limitations = _handoff_limitations(args)
    fingerprint = (
        read_json(workspace / "case-fingerprint.json").get("fingerprint_sha256")
        if (workspace / "case-fingerprint.json").exists()
        else None
    )
    if args.payload_type == "unproven_research_questions":
        payload_value = read_json(Path(args.payload).expanduser().resolve())
        if not isinstance(payload_value, dict):
            raise ValueError("Payload handoff должен быть JSON-объектом.")
        payload = bind_request_payload(payload_value)
    else:
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
        maximum_claim = state.get("maximum_permitted_claim")
        if not isinstance(maximum_claim, str) or not maximum_claim.strip():
            raise ValueError(
                "Текущий maximum_permitted_claim отсутствует; проверенный handoff заблокирован."
            )
        candidates = read_jsonl(workspace / "thesis-candidates.jsonl")
        limitations = _unique_nonempty_strings(
            [
                *limitations,
                *(
                    limitation
                    for candidate in candidates
                    for limitation in candidate.get("limitations", [])
                    if isinstance(candidate, dict)
                    and isinstance(candidate.get("limitations"), list)
                ),
                read_json(workspace / "case-adverse-review.json").get("no_hit_wording"),
            ]
        )
        if not limitations:
            raise ValueError("Проверенный handoff требует явные limitations.")
        if not isinstance(fingerprint, str):
            raise ValueError("Проверенный handoff требует fingerprint_sha256 дела заявителя.")
        payload = _build_reviewed_handoff_payload(
            workspace,
            args,
            plan_sha256=plan_sha256,
            evidence_sha256=evidence_sha256,
            fingerprint_sha256=fingerprint,
            maximum_permitted_claim=maximum_claim,
            limitations=limitations,
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
        limitations=limitations,
        created_at=args.created_at or utc_now(),
        fingerprint_sha256=fingerprint,
    )
    if args.payload_type != "unproven_research_questions":
        _persist_trusted_source_material(
            workspace,
            envelope,
            request_path=args.request,
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
    if (
        envelope.get("payload_type") != "unproven_research_questions"
        and not args.source_workspace
    ):
        raise ValueError(
            "Проверенный handoff требует --source-workspace полного cassation workspace."
        )
    plan_sha256, evidence_sha256, fingerprint_sha256, maximum_claim = _optional_current_context(args.source_workspace)
    result = check_handoff(
        envelope,
        expected_target=args.expected_target,
        current_plan_sha256=plan_sha256,
        current_evidence_sha256=evidence_sha256,
        current_fingerprint_sha256=fingerprint_sha256,
        current_maximum_permitted_claim=maximum_claim,
        trusted_source_workspace=args.source_workspace,
    )
    _print_json(result)
    return 0 if result.get("valid") else 2


def cmd_handoff_import(args: argparse.Namespace) -> int:
    envelope = read_json(Path(args.input).expanduser().resolve())
    if (
        envelope.get("payload_type") != "unproven_research_questions"
        and not args.source_workspace
    ):
        raise ValueError(
            "Проверенный handoff требует --source-workspace полного cassation workspace."
        )
    plan_sha256, evidence_sha256, fingerprint_sha256, maximum_claim = _optional_current_context(args.source_workspace)
    result = import_handoff(
        envelope,
        Path(args.ledger).expanduser().resolve(),
        expected_target=args.expected_target,
        current_plan_sha256=plan_sha256,
        current_evidence_sha256=evidence_sha256,
        current_fingerprint_sha256=fingerprint_sha256,
        current_maximum_permitted_claim=maximum_claim,
        trusted_source_workspace=args.source_workspace,
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
                document_id=args.document_id,
                chain_candidate_id=args.chain_id,
                query_lane=args.query_lane,
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
    coverage_requirements = _quality_records(
        args.coverage_requirements,
        "--coverage-requirements",
    )
    if not coverage_requirements:
        raise ValueError(
            "--coverage-requirements должен содержать хотя бы один сегмент охвата."
        )
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.plan_refresh(
            as_of=args.as_of,
            max_age_seconds=args.max_age_seconds,
            coverage_requirements=coverage_requirements,
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
            decision_reason=args.decision_reason,
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


def cmd_cache_treatment_quality_export(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    with PublicCorpus(Path(args.root).expanduser().resolve()) as corpus:
        result = corpus.treatment_quality_export()
    write_json(output, result)
    _print_json(result)
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
    parser = RussianHelpArgumentParser(
        prog="judicial_meaning.py",
        description="Локальное исследование кассационной практики до выбора тезиса жалобы в КС РФ.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    intake = sub.add_parser("intake", help="Инвентаризировать акты заявителя")
    intake.add_argument("--workspace", required=True)
    intake.add_argument("--inputs", nargs="+", required=True)
    intake.add_argument(
        "--role",
        default="applicant_judicial_act",
        help=(
            "Роль входного документа; по умолчанию applicant_judicial_act "
            "(судебный акт по делу заявителя)."
        ),
    )
    intake.set_defaults(func=cmd_intake)

    ocr = sub.add_parser("ocr", help="Явно распознать скан PDF локальными OCR-инструментами")
    ocr.add_argument("--input", required=True)
    ocr.add_argument("--output", required=True)
    ocr.add_argument(
        "--language",
        default="rus",
        help="Код языка Tesseract; по умолчанию rus (русский).",
    )
    ocr.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Разрешение изображения; по умолчанию 300 точек на дюйм.",
    )
    ocr.set_defaults(func=cmd_ocr)

    plan = sub.add_parser("plan", help="Создать или заморозить нейтральный план")
    plan_sub = plan.add_subparsers(dest="plan_command", required=True)
    template = plan_sub.add_parser("template", help="Создать заполняемый шаблон")
    template.add_argument("--workspace", required=True)
    template.add_argument(
        "--force",
        action="store_true",
        help=(
            "Перезаписать существующий черновик research-plan.json; ранее "
            "внесённые в него данные будут заменены."
        ),
    )
    template.set_defaults(func=cmd_plan_template)
    freeze = plan_sub.add_parser("freeze", help="Проверить и неизменяемо зафиксировать план")
    freeze.add_argument("--workspace", required=True)
    freeze.add_argument("--plan", required=True)
    freeze.set_defaults(func=cmd_plan_freeze)

    query = sub.add_parser("query", help="Подтвердить предложенный или добавить дополнительный запрос")
    query_sub = query.add_subparsers(dest="query_command", required=True)
    query_accept = query_sub.add_parser(
        "accept", help="Подтвердить предложения до заморозки плана"
    )
    query_accept.add_argument("--workspace", required=True)
    query_accept.add_argument("--query-id", action="append", required=True)
    query_accept.add_argument("--reviewer", required=True)
    query_accept.add_argument(
        "--confirmed-at",
        required=True,
        help="Дата и время подтверждения в формате ISO 8601.",
    )
    query_accept.set_defaults(func=cmd_query_accept)
    query_supplement = query_sub.add_parser(
        "supplement",
        help=(
            "Добавить дополнительный запрос после заморозки плана, не меняя "
            "состав исходной выборки"
        ),
    )
    query_supplement.add_argument("--workspace", required=True)
    query_supplement.add_argument(
        "--lane",
        choices=tuple(sorted(_QUERY_PLAN_LANE)),
        required=True,
        help=(
            "Вид дополнительного поиска: exact_norm — точная норма; "
            "court_language — формулировка суда; legal_mechanism — правовой "
            "механизм; controlled_synonym — согласованный синоним; "
            "opposite_reading — противоположное толкование; narrower_reading — "
            "более узкое толкование; alternative_ground — иное основание; "
            "later_legislation — последующее законодательство; "
            "higher_authority — более высокий источник; case_feature — признак дела."
        ),
    )
    query_supplement.add_argument("--query", required=True)
    query_supplement.add_argument("--reason", required=True)
    query_supplement.add_argument("--reviewer", required=True)
    query_supplement.add_argument(
        "--confirmed-at",
        required=True,
        help="Дата и время подтверждения в формате ISO 8601.",
    )
    query_supplement.set_defaults(func=cmd_query_supplement)

    collect = sub.add_parser("collect", help="Собрать официально наблюдаемый корпус")
    collect.add_argument("--workspace", required=True)
    collect.add_argument("--resume", action="store_true")
    collect.add_argument("--max-tasks", type=int)
    collect.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Максимум попыток для одной задачи; по умолчанию 3.",
    )
    collect.add_argument("--max-source-tasks", type=int)
    collect.add_argument(
        "--retry-now",
        action="store_true",
        help=(
            "Повторить сейчас задачи, срок новой попытки для которых уже наступил "
            "и повтор явно разрешён пользователем"
        ),
    )
    collect.add_argument("--fixture-dir", help=argparse.SUPPRESS)
    collect.set_defaults(func=cmd_collect)

    screen = sub.add_parser("screen", help="Отобрать кандидатов по дорожкам замороженного плана")
    screen.add_argument("--workspace", required=True)
    screen.set_defaults(func=cmd_screen)

    code = sub.add_parser("code", help="Создать или проверить полнотекстовое кодирование")
    code.add_argument("--workspace", required=True)
    code.add_argument("--input")
    code.set_defaults(func=cmd_code)

    analyze = sub.add_parser(
        "analyze",
        help="Посчитать независимые цепочки и определить статус в пределах проверенного корпуса",
    )
    analyze.add_argument("--workspace", required=True)
    analyze.set_defaults(func=cmd_analyze)

    review = sub.add_parser(
        "review",
        help=(
            "Записать проверку неблагоприятных материалов, полноты охвата и "
            "явно введённое решение проверяющего юриста; команда не принимает "
            "это решение автоматически"
        ),
    )
    review.add_argument("--workspace", required=True)
    review.add_argument(
        "--decision",
        choices=("evidence_reviewed", "approved", "rejected", "revise"),
        required=True,
        help=(
            "Решение юриста: evidence_reviewed — доказательства просмотрены без "
            "одобрения тезиса; approved — тезис одобрен; rejected — тезис "
            "отклонён; revise — вернуть тезис на доработку."
        ),
    )
    review.add_argument("--reviewer", required=True)
    review.add_argument(
        "--adverse-complete",
        action="store_true",
        help="Подтвердить ручную проверку всех неблагоприятных материалов.",
    )
    review.add_argument(
        "--coverage-complete",
        action="store_true",
        help="Подтвердить ручную проверку полноты охвата корпуса.",
    )
    review.add_argument("--notes", default="")
    review.add_argument("--adverse-file")
    review.add_argument("--thesis-file")
    review.set_defaults(func=cmd_review)

    validate = sub.add_parser("validate", help="Проверить артефакты и допуск тезиса")
    validate.add_argument("--workspace", required=True)
    validate.add_argument("--require-thesis-ready", action="store_true")
    validate.add_argument("--thesis")
    validate.set_defaults(func=cmd_validate)

    export = sub.add_parser(
        "export",
        help=(
            "Сформировать воспроизводимые отчёты JSON/JSONL: одинаковые входные "
            "данные дают одинаковый результат"
        ),
    )
    export.add_argument("--workspace", required=True)
    export.add_argument("--run-id")
    export.set_defaults(func=cmd_export)

    case = sub.add_parser("case", help="Подготовить отпечаток дела заявителя")
    case_sub = case.add_subparsers(dest="case_command", required=True)
    case_prepare = case_sub.add_parser(
        "prepare", help="Создать или обновить отпечаток дела и запросы"
    )
    case_prepare.add_argument("--workspace", required=True)
    case_prepare.add_argument(
        "--answers",
        help=(
            "JSON с полями issue, norm_refs и features; без него разрешён только "
            "интерактивный режим терминала"
        ),
    )
    case_prepare.set_defaults(func=cmd_case_prepare)
    case_dynamics = case_sub.add_parser(
        "dynamics",
        help=(
            "Описать проверенную динамику по годам и заранее заданным группам дел"
        ),
    )
    case_dynamics.add_argument("--workspace", required=True)
    case_dynamics.set_defaults(func=cmd_case_dynamics)

    position = sub.add_parser("position", help="Проверить карточку позиции суда")
    position_sub = position.add_subparsers(dest="position_command", required=True)
    position_check = position_sub.add_parser(
        "check",
        help=(
            "Проверить, кто сформулировал позицию, точность цитаты и влияние "
            "позиции на исход дела"
        ),
    )
    position_check.add_argument("--input", required=True)
    position_check.add_argument("--workspace")
    position_check.set_defaults(func=cmd_position_check)

    compare = sub.add_parser("compare", help="Сопоставить материальные признаки двух дел")
    compare.add_argument("--applicant", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--workspace")
    compare.add_argument("--reviewer")
    compare.add_argument(
        "--reviewed-at",
        help="Дата и время ручной проверки в формате ISO 8601.",
    )
    compare.add_argument("--position-card-id")
    compare.set_defaults(func=cmd_compare)

    relation = sub.add_parser("relation", help="Связать позицию кассации с делом заявителя")
    relation_sub = relation.add_subparsers(dest="relation_command", required=True)
    relation_classify = relation_sub.add_parser(
        "classify", help="Классифицировать проверенную позицию по текущему отпечатку дела"
    )
    relation_classify.add_argument("--position-card", required=True)
    relation_classify.add_argument("--comparison", required=True)
    relation_classify.add_argument("--applicant-position", required=True)
    relation_classify.add_argument("--workspace", required=True)
    relation_classify.add_argument("--reviewer", required=True)
    relation_classify.add_argument(
        "--reviewed-at",
        required=True,
        help="Дата и время ручной проверки в формате ISO 8601.",
    )
    relation_classify.set_defaults(func=cmd_relation_classify)

    queue = sub.add_parser("queue", help="Собрать объяснимую очередь проверки")
    queue_sub = queue.add_subparsers(dest="queue_command", required=True)
    queue_build = queue_sub.add_parser(
        "build", help="Сохранить каждого кандидата и объяснить его статус"
    )
    queue_build.add_argument("--candidates", required=True)
    queue_build.add_argument("--resolutions")
    queue_build.add_argument("--quotas", help="Квоты JSON по полям court_id, stratum_id и lane")
    queue_build.add_argument("--workspace")
    queue_build.set_defaults(func=cmd_queue_build)

    adverse = sub.add_parser("adverse", help="Проверить неблагоприятные дорожки")
    adverse_sub = adverse.add_subparsers(dest="adverse_command", required=True)
    adverse_build = adverse_sub.add_parser(
        "build", help="Собрать четыре раскрытые группы неблагоприятных материалов"
    )
    adverse_build.add_argument("--cards", required=True)
    adverse_build.add_argument(
        "--completed-buckets",
        nargs="+",
        choices=ADVERSE_BUCKETS,
        required=True,
        help=(
            "Полностью проверенные группы: opposite_reading — противоположное "
            "толкование; narrower_reading — более узкое толкование; "
            "alternative_ground — иное основание; later_authority — более поздний акт."
        ),
    )
    adverse_build.add_argument(
        "--searched-buckets",
        nargs="+",
        choices=ADVERSE_BUCKETS,
        required=True,
        help=(
            "Группы, по которым выполнен поиск: opposite_reading — противоположное "
            "толкование; narrower_reading — более узкое толкование; "
            "alternative_ground — иное основание; later_authority — более поздний акт."
        ),
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

    status = sub.add_parser(
        "status",
        help="Показать единый статус исследования с блокировкой при неопределённости",
    )
    status.add_argument("--workspace", required=True)
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="Сформировать автономный HTML-отчёт")
    report.add_argument("--workspace", required=True)
    report.add_argument("--model", help="Готовая модель JSON; иначе формируется из рабочей папки")
    report.add_argument("--html")
    report.add_argument("--manifest")
    report.set_defaults(func=cmd_report)

    quality = sub.add_parser(
        "quality",
        help="Проверить распространение позиций, неопределённость и надёжность кодирования",
    )
    quality_sub = quality.add_subparsers(dest="quality_command", required=True)
    quality_chain = quality_sub.add_parser(
        "chain-propagation",
        help="Проверить, кто и на какой стадии выразил либо поддержал позицию",
    )
    quality_chain.add_argument("--observations", required=True)
    quality_chain.add_argument("--required-chain-id", action="append", default=[])
    quality_chain.add_argument("--output")
    quality_chain.set_defaults(func=cmd_quality_chain_propagation)

    quality_uncertainty = quality_sub.add_parser(
        "uncertainty-profile",
        help=(
            "Описать источники неопределённости практики без сводной числовой оценки"
        ),
        description=(
            "Описать источники неопределённости практики без сводной числовой "
            "оценки. Успешная проверка нативной надёжности подтверждает только "
            "техническую цепочку файлов."
        ),
        epilog=(
            "Она не подтверждает личность или независимость проверяющего, "
            "юридическую правильность, актуальность права, разрешение на "
            "публикацию, одобрение результата или готовность к подаче."
        ),
    )
    quality_uncertainty.add_argument("--fingerprint-sha256", required=True)
    quality_uncertainty.add_argument("--position-cards", required=True)
    quality_uncertainty.add_argument("--comparisons", required=True)
    quality_uncertainty.add_argument("--applicant-relations", required=True)
    quality_uncertainty.add_argument("--trajectories", required=True)
    quality_uncertainty.add_argument("--temporal-analysis")
    quality_uncertainty.add_argument("--source-reconciliation")
    quality_uncertainty.add_argument("--coding-reliability")
    quality_uncertainty.add_argument(
        "--coding-audit-finalization-receipt",
        help=(
            "Файл coding-audit-finalization-receipt.json; используется только "
            "вместе с отдельно сохранённым SHA-256 успешного coding-audit-finalize."
        ),
    )
    quality_uncertainty.add_argument(
        "--expected-finalization-receipt-sha256",
        help=(
            "Внешний SHA-256, отдельно сохранённый из обычного успешного "
            "вывода coding-audit-finalize; это самохеш квитанции, а не хеш её "
            "полного JSON, и его нельзя восстанавливать из квитанции."
        ),
    )
    quality_uncertainty.add_argument("--higher-authority-treatments")
    quality_uncertainty.add_argument("--output")
    quality_uncertainty.set_defaults(func=cmd_quality_uncertainty_profile)

    quality_audit_plan = quality_sub.add_parser(
        "coding-audit-plan",
        help=(
            "Сохранить неизменяемую воспроизводимую выборку для независимой "
            "проверки кодирования"
        ),
    )
    quality_audit_plan.add_argument("--screening-candidates", required=True)
    quality_audit_plan.add_argument("--primary-decisions", required=True)
    quality_audit_plan.add_argument("--plan-sha256", required=True)
    quality_audit_plan.add_argument("--sample-size", type=int, required=True)
    quality_audit_plan.add_argument("--exclusion-sample-size", type=int, required=True)
    quality_audit_plan.add_argument("--output")
    quality_audit_plan.set_defaults(func=cmd_quality_coding_audit_plan)

    quality_audit_prepare = quality_sub.add_parser(
        "coding-audit-prepare",
        help=(
            "Подготовить из рабочей папки новый проверяемый пакет для "
            "независимого аудита кодирования"
        ),
        epilog=(
            "Команда без сетевого доступа повторно проверяет замороженный план, "
            "файл screening-candidates.jsonl, первичную разметку и сохранённые полные "
            "тексты. Она создаёт screening-candidates.audit.jsonl, "
            "primary-decisions.audit.jsonl, coding-audit-plan.json, "
            "secondary-review-queue.jsonl, secondary-coding-template.jsonl и "
            "coding-audit-inputs-manifest.json, а также отдельный "
            "independent-review-packet.zip: в нём CODING-BRIEF.json, штатный "
            "CODING-CODEBOOK.md, REVIEW-INSTRUCTIONS.md, выбранные полные тексты, "
            "пустые шаблоны без ответов и хешей первого кодировщика и внутренний "
            "манифест. Передавайте "
            "независимому проверяющему только ZIP, а не родительский каталог с "
            "первичной разметкой. Новый пакет имеет контракт 1.2. Сохраните "
            "показанные в стандартном выводе manifest_sha256 для последующего штатного импорта "
            "и independent_review_packet_sha256 для проверки передачи; второй "
            "хеш сообщите проверяющему отдельно "
            "по независимому каналу. Сверьте SHA-256 до распаковки. "
            "Такая слепая проверка скрывает только ответ "
            "первого кодировщика: факты и исход дела видны в судебном тексте. "
            "Версия справочника задаётся отдельно через --codebook-version и "
            "должна точно совпасть во всех первичных карточках; она не берётся "
            "из ответа первого кодировщика. План должен содержать ровно одну "
            "направленную гипотезу со статусом hypothesis_under_test: открытый "
            "вопрос нельзя однозначно разметить как supports или adverse. ZIP с "
            "полными текстами не считается "
            "автоматически безопасным для "
            "публикации. Папка --output-dir должна не существовать: перезапись "
            "запрещена. На macOS родительская, временная и итоговая папки, а также "
            "каждый файл пакета должны вовсе не иметь расширенных ACL. Любая запись "
            "ACL отклоняется, включая запрещающую запись и запись без наследования. "
            "Выберите приватную родительскую папку без ACL либо обратитесь к системному "
            "администратору; обычная смена режима через chmod сама по себе не "
            "подтверждает удаление ACL. Ошибка до создания временной папки не создаёт "
            "итоговую папку. "
            "После создания временной папки любая ошибка до атомарного переноса "
            "сохраняет её для безопасного разбора: программа намеренно не удаляет "
            "файлы или папку по изменяемому имени, чтобы при гонке не удалить чужой "
            "объект. Код 2 требует остановки без повтора и передачи всей строки ошибки "
            "системному администратору. По устройству и inode родителя, прежнему имени, "
            "inode временной папки и каждого созданного файла он должен найти, учесть "
            "и поместить в карантин папку и все имена либо жёсткие ссылки файлов. Если "
            "хотя бы один inode или все его ссылки не учтены, чувствительная временная "
            "копия считается неучтённой. Если после переноса отказала только синхронизация, а "
            "расположение родителя подтверждено, команда возвращает код 2: не удаляйте "
            "и не передавайте видимый каталог; восстановите файловую систему, повторите "
            "подготовку из тех же неизменных входов в другую отсутствующую папку и "
            "сравните оба результата побайтно. Если не подтверждено состояние "
            "публикации, её расположение, целостность или защищённость могли измениться, "
            "а путь --output-dir может уже не вести к результату: остановитесь, сохраните "
            "входы неизменными, не повторяйте команду и не передавайте результат. "
            "Это аварийная работа системного администратора, не штатная пользовательская "
            "команда: передайте ему всю строку ошибки для поиска и карантина по "
            "устройству и inode родителя, прежнему имени записи, а также устройству и "
            "inode опубликованного каталога и каждого созданного файла. Нужно учесть "
            "и поместить в карантин все имена и жёсткие ссылки; если каталог, хотя бы "
            "один inode или все его ссылки не найдены, считайте чувствительную копию "
            "неучтённой. Если завершение после публикации прервано до начала передачи "
            "подтверждения, в том числе при закрытии служебного дескриптора, финальный "
            "стандартный вывод ещё не создавался и должен быть пуст: код 2 не означает, "
            "что каталога нет. Если завершение не подтверждено после начала передачи "
            "либо после того, как удалось явно сбросить финальный JSON, стандартный "
            "вывод может быть пустым или частичным, а "
            "также выглядеть полным; он всегда недействителен. В обоих случаях сохраните входы "
            "и каталог, не "
            "используйте результат и не повторяйте команду в ту же папку. После "
            "устранения ошибки повторите те же входы в другую отсутствующую соседнюю "
            "папку, получите одну полную строку JSON и побайтно сравните каталоги. "
            "Сохраните manifest_sha256 только из успешного повторного стандартного "
            "вывода по независимому каналу и не восстанавливайте якорь из первого пакета. "
            "Шаблон остаётся ожидающим "
            "независимой вторичной проверки и сам не является её доказательством. "
            "После возврата отдельной ручной разметки используйте quality "
            "coding-audit-review-import, затем разрешите отмеченные расхождения и "
            "запустите quality coding-reliability. Создание пакета не означает юридическую "
            "готовность, одобрение или разрешение на подачу жалобы."
        ),
        formatter_class=RussianHelpFormatter,
    )
    quality_audit_prepare.add_argument(
        "--workspace",
        required=True,
        help=(
            "Существующая рабочая папка с замороженным планом, полной рамкой отбора, "
            "одобренной первичной разметкой и экспортом исходных текстов."
        ),
    )
    quality_audit_prepare.add_argument(
        "--codebook-version",
        required=True,
        choices=sorted(NATIVE_AUDIT_CODEBOOK_VERSIONS),
        help=(
            "Доверенная версия справочника кодирования, заданная хранителем "
            "отдельно от ответов первого кодировщика; должна точно совпасть во "
            "всех первичных карточках. Сейчас поддерживается версия 1.0."
        ),
    )
    quality_audit_prepare.add_argument(
        "--sample-size",
        type=int,
        required=True,
        help=(
            "Максимум кандидатов общей детерминированной выборки; фактическое "
            "число может быть меньше рамки."
        ),
    )
    quality_audit_prepare.add_argument(
        "--exclusion-sample-size",
        type=int,
        required=True,
        help=(
            "Максимум кандидатов проверки возможных ложных исключений; эта "
            "выборка может пересекаться с общей."
        ),
    )
    quality_audit_prepare.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Новая, ещё не существующая папка для полного пакета аудита; "
            "она должна быть вне рабочей папки, а её родитель — принадлежать текущему "
            "пользователю и не допускать запись группы или других пользователей. "
            "На macOS родитель и создаваемые папки и файлы не должны иметь ни одной "
            "расширенной записи ACL, даже запрещающей или ненаследуемой."
        ),
    )
    quality_audit_prepare.set_defaults(func=cmd_quality_coding_audit_prepare)

    quality_audit_import = quality_sub.add_parser(
        "coding-audit-review-import",
        help=(
            "Проверить возвращённую вторичную разметку и собрать решения аудита"
        ),
        epilog=(
            "Запускайте команду у хранителя после возврата отдельного JSONL "
            "вторым кодировщиком. Передайте --expected-manifest-sha256 из заранее "
            "сохранённого стандартного вывода успешной coding-audit-prepare, а не "
            "считывайте его заново из пакета. Для нового пакета 1.2 до передачи ZIP "
            "процедурно выберите одну псевдонимную метку без реального имени, сообщите "
            "её проверяющему отдельно и затем передайте в --expected-secondary-coder. "
            "Команда связывает хеш нормализованной метки с квитанцией, но не может "
            "доказать момент её выбора: secondary_coder_label_precommit_verified=false. "
            "Для уже возвращённого пакета 1.1 аргумент лишь проверяет единообразие "
            "имеющейся метки; если там реальное имя, запросите новую псевдонимную "
            "копию у автора и не исправляйте файл молча. Совпадение метки во всех "
            "строках не удостоверяет личность и независимость. "
            "Команда не изменяет пакет или возвращённый файл. Она проверяет "
            "закрытую структуру, нормализованное соответствие цитат тексту, а затем "
            "буквальное присутствие основной и альтернативных цитат в точном тексте, но не "
            "подтверждает формулировки, факты или "
            "рассуждение, не проверяет локаторы или юридическую правильность и не проверяет "
            "временную применимость редакции нормы. Обычная ошибка до атомарного "
            "переноса не создаёт итоговую папку только до создания временной папки. "
            "После её создания любая ошибка до переноса сохраняет временную папку для "
            "безопасного разбора: программа намеренно не удаляет файлы или папку по "
            "изменяемому имени, чтобы при гонке не удалить чужой объект. Код 2 требует "
            "остановки без повтора и передачи всей строки ошибки системному "
            "администратору. По устройству и inode родителя, прежнему имени, inode "
            "временной папки и каждого файла он должен найти, учесть и поместить в "
            "карантин папку и все имена либо жёсткие ссылки. Если хотя бы один inode "
            "или все его ссылки не учтены, чувствительная временная копия считается "
            "неучтённой. Если после переноса "
            "отказала только синхронизация, а расположение родителя подтверждено, "
            "команда возвращает код 2 с пустым стандартным выводом: не удаляйте и не "
            "передавайте видимый каталог; восстановите файловую систему, повторите "
            "импорт из тех же неизменных входов в другую отсутствующую соседнюю папку "
            "и сравните оба результата побайтно. Если не подтверждено состояние "
            "публикации, её расположение, целостность или защищённость могли измениться, "
            "а путь --output-dir может уже не вести к результату: "
            "остановитесь, сохраните входы неизменными, не повторяйте команду и не "
            "передавайте результат. Это аварийная работа системного администратора, "
            "не штатная пользовательская команда: передайте ему всю строку ошибки для "
            "поиска и карантина по устройству и inode родителя, прежнему имени записи, "
            "а также устройству и inode опубликованного каталога и каждого созданного "
            "файла. Нужно учесть и поместить в карантин все имена и жёсткие ссылки; "
            "если каталог, хотя бы один inode или все его ссылки не найдены, считайте "
            "чувствительную копию неучтённой. Если завершение после публикации "
            "прервано до начала передачи подтверждения, в том числе при закрытии "
            "служебного дескриптора, финальный стандартный вывод ещё не создавался и "
            "должен быть пуст: код 2 не означает, что каталога нет. Если завершение "
            "не подтверждено после начала передачи либо после того, как удалось явно "
            "сбросить финальный JSON, стандартный вывод "
            "может быть пустым или частичным, а также выглядеть полным; он всегда "
            "недействителен. В обоих случаях "
            "сохраните входы и каталог, не используйте результат и не повторяйте "
            "команду в ту же папку. После устранения ошибки повторите те же входы в "
            "другую отсутствующую соседнюю папку, получите одну полную строку JSON, "
            "побайтно сравните каталоги и только затем используйте контрольную сумму "
            "квитанции и флаги из успешного повторного вывода. При "
            "подтверждённом успехе папка имеет режим "
            "0700, а два файла — 0600: "
            "audit-decisions.jsonl и coding-audit-review-import-receipt.json. "
            "На macOS родительская, временная и итоговая папки, а также оба файла "
            "должны вовсе не иметь расширенных ACL. Любая запись ACL отклоняется, "
            "включая запрещающую запись и запись без наследования. Выберите приватную "
            "родительскую папку без ACL либо обратитесь к системному администратору; "
            "обычная смена режима через chmod сама по себе не подтверждает удаление ACL. "
            "Первый передаётся в coding-reliability. Квитанция и стандартный вывод "
            "ставят returned_quote_literal_presence_verified=true только для "
            "возвращённых цитат и "
            "secondary_coder_label_differs_from_each_sampled_primary_label=true только для "
            "сравнения строковых меток, не личностей. Они также "
            "показывают карты audited_field_differences и "
            "non_audited_content_differences: для каждого кандидата они называют "
            "различающиеся поля без их значений. Расхождения восьми аудируемых полей "
            "требуют adjudications.jsonl. "
            "Основные поля quote и quote_locator относятся к отдельной ручной проверке, а "
            "вложенные поля quote и quote_locator внутри alternative_grounds входят в это "
            "аудируемое поле. После любого разрешения поля alternative_grounds отдельно "
            "сверьте итоговые цитаты с текстом пакета: coding-reliability этого не "
            "делает, и complete=true не доказывает такую сверку. Сохраните внешнюю "
            "запись с candidate_id, полем alternative_grounds, псевдонимом проверяющего, "
            "reviewed_at, выводом, контрольной суммой пакета, манифеста или квитанции, "
            "канонической контрольной суммой решения расхождения и "
            "final_resolved_value_sha256 — SHA-256 от результата "
            "json.dumps(значение, sort_keys=True, separators=(\",\", \":\"), "
            "ensure_ascii=False, allow_nan=False).encode(\"utf-8\") без "
            "завершающего перевода строки — либо канонической "
            "контрольной суммой всей итоговой 20-полевой разметки. Штатной проверки или "
            "возобновления по этой записи пока нет: при нужной правке создайте новое "
            "решение расхождения и повторите проверку, при неразрешённом вопросе "
            "остановитесь. Различия в полях "
            "proposition, quote, quote_locator или material_facts требуют отдельной ручной записи "
            "проверки содержания. Этот сигнал пока предупредительный: coding-reliability "
            "не читает квитанцию и complete=true не доказывает его закрытие. Ни одна "
            "штатная команда выпуска 15 не сбрасывает этот флаг и не подтверждает "
            "возобновление. Продолжение возможно только по отдельному решению оператора, "
            "связанному с сохранённой внешней записью, без заявления о машинном "
            "закрытии. Если ошиблась вторичная разметка, получите исправленный полный "
            "JSONL и выполните новый импорт в новую папку. Если ошиблась первичная "
            "разметка, исправьте исходную первичную запись и заново пройдите подготовку "
            "пакета, вторичную проверку и импорт. Если вопрос не разрешён, остановитесь. "
            "При этом код 0 "
            "означает только успешное завершение импорта и публикации; автоматика обязана разобрать "
            "оба флага adjudication_required и non_audited_content_review_required и "
            "остановиться, если хотя бы один равен true. Квитанция не является "
            "аутентификацией, юридическим "
            "одобрением, разрешением на публикацию или готовностью к подаче. "
            "Пакет и решения могут содержать чувствительные судебные сведения. "
            "Закреплённый пакет версии 1.1 и новые пакеты версии 1.2 поддерживаются; "
            "старые пятифайловые пакеты остаются на ручном пути."
            "\n\nПример команды:\n"
            "  KSRF_SKILLS_ROOT=\"${KSRF_SKILLS_ROOT:-${CODEX_HOME:-$HOME/.codex}/skills}\"\n"
            "  JM=\"$KSRF_SKILLS_ROOT/ksrf-cassation-judicial-meaning/scripts/judicial_meaning.py\"\n"
            "  AUDIT_BUNDLE=\"./coding-audit-inputs\"\n"
            "  EXPECTED_MANIFEST_SHA256=\"<manifest_sha256 из сохранённого стандартного вывода>\"\n"
            "  EXPECTED_SECONDARY_CODER=\"псевдоним-второго-кодировщика\"\n"
            "  RETURNED_SECONDARY=\"./secondary-coding.completed.jsonl\"\n"
            "  AUDIT_IMPORT=\"./coding-audit-review-import\"\n"
            "  python3 \"$JM\" quality coding-audit-review-import \\\n"
            "    --bundle \"$AUDIT_BUNDLE\" \\\n"
            "    --expected-manifest-sha256 \"$EXPECTED_MANIFEST_SHA256\" \\\n"
            "    --expected-secondary-coder \"$EXPECTED_SECONDARY_CODER\" \\\n"
            "    --secondary-coding \"$RETURNED_SECONDARY\" \\\n"
            "    --output-dir \"$AUDIT_IMPORT\""
        ),
        formatter_class=RussianExampleHelpFormatter,
    )
    quality_audit_import.add_argument(
        "--bundle",
        required=True,
        help=(
            "Родительская папка штатного пакета аудита; второму кодировщику её не "
            "передают, потому что она содержит разметку первого кодировщика."
        ),
    )
    quality_audit_import.add_argument(
        "--expected-manifest-sha256",
        required=True,
        help=(
            "Отдельно сохранённый manifest_sha256 из успешного стандартного вывода "
            "coding-audit-prepare."
        ),
    )
    quality_audit_import.add_argument(
        "--expected-secondary-coder",
        required=True,
        help=(
            "Одна ожидаемая метка второго кодировщика для всего файла; это "
            "проверка согласованности строки, а не личности или момента выбора метки."
        ),
    )
    quality_audit_import.add_argument(
        "--secondary-coding",
        required=True,
        help="Отдельный строгий UTF-8 JSONL, возвращённый вторым кодировщиком.",
    )
    quality_audit_import.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Новая, ещё не существующая соседняя папка рядом с --bundle для решений и "
            "квитанции; родитель должен принадлежать текущему пользователю и не быть "
            "доступным для записи группе или другим пользователям. На macOS родитель "
            "и создаваемые папки и файлы не должны иметь ни одной расширенной записи "
            "ACL, даже запрещающей или ненаследуемой."
        ),
    )
    quality_audit_import.set_defaults(func=cmd_quality_coding_audit_review_import)

    quality_audit_finalize = quality_sub.add_parser(
        "coding-audit-finalize",
        help=(
            "Штатно разрешить все расхождения импорта и закрыть техническую "
            "проверку кодирования"
        ),
        epilog=(
            "Полная цепочка: coding-audit-prepare -> независимый возврат JSONL -> "
            "coding-audit-review-import -> ручное разрешение отмеченных расхождений, "
            "если они есть -> coding-audit-finalize. Передайте два SHA-256 именно "
            "из отдельно сохранённого стандартного вывода успешных prepare и import; "
            "не считывайте ожидаемые значения обратно из проверяемых папок. "
            "--bundle, --audit-import и новая отсутствующая --output-dir должны быть "
            "тремя разными соседними папками одного фактического приватного родителя. "
            "Если обе карты расхождений импорта пусты, --resolutions нужно опустить. "
            "Иначе --resolutions должен быть соседним приватным обычным файлом "
            "текущего пользователя: режим 0600, одна жёсткая ссылка и, на macOS, "
            "ни одной расширенной ACL. Передайте строгий UTF-8 JSONL: по одной "
            "закрытой строке на каждого "
            "кандидата с полями schema_version, import_receipt_sha256, candidate_id, "
            "difference_fields, primary_coding_sha256, secondary_coding_sha256, "
            "field_resolutions, reviewer_pseudonym, reviewed_at, human_review, "
            "full_text_reviewed, quote_locators_reviewed и final_coding_approved. "
            "difference_fields и field_resolutions обязаны покрывать все и только "
            "поля обеих карт в опубликованном порядке. Каждый field_resolutions "
            "имеет field и choice=primary|secondary либо choice=custom с единственным "
            "дополнительным полем value. reviewed_at — время RFC 3339 с секундами и "
            "часовым поясом, не в будущем; псевдоним должен отличаться от обеих меток "
            "кодировщиков. receipt_sha256 берётся из успешного stdout импорта; "
            "candidate_id и упорядоченные поля — из двух карт его квитанции; "
            "индивидуальные primary_coding_sha256 и secondary_coding_sha256 — из "
            "строки кандидата в audit-decisions.jsonl. Первичное значение сверяйте "
            "с primary-decisions.audit.jsonl, вторичное — с вложенным secondary_coding. "
            "Псевдоним и флаги — заявления пользователя, а не "
            "аутентификация личности, авторства, независимости, чтения пакета или "
            "самого факта проверки. Финальная 20-полевая запись выводится из точных "
            "primary/secondary/custom choices, а не принимается целиком. Основная "
            "цитата и каждая цитата alternative_grounds проверяются буквально и "
            "нормализованно по точному тексту пакета. Это не проверяет истинность "
            "proposition, отбор material_facts, достаточность мотивировки, юридическую "
            "правильность, временную применимость нормы или смысл локатора; "
            "quote_locator_verified всегда false. Решения расхождений и "
            "coding-reliability строятся из одного снимка. Самостоятельная команда "
            "coding-reliability остаётся экспертным совместимым путём, но её отчёт "
            "без штатной квитанции не закрывает расхождения Release15. Код 3 означает "
            "читаемую, но неполную или неразрешённую проверку: публикуемая папка не "
            "создаётся. При resolution_incomplete переменная часть stdout содержит "
            "только отсутствующие candidate_id/field; при reliability_unresolved — "
            "контрольную сумму и безопасную проекцию причин без значений разметки и "
            "меток людей. "
            "Код 2 означает неверный контракт/хеш, небезопасное состояние файловой "
            "системы или ошибку ввода-вывода. Код 0 требует точного complete=true и "
            "атомарно создаёт ровно resolved-review-decisions.jsonl, "
            "adjudications.jsonl, coding-reliability.json и "
            "coding-audit-finalization-receipt.json. Родитель должен принадлежать "
            "текущему пользователю и запрещать запись группе/остальным; итоговая "
            "папка имеет 0700, файлы 0600. На macOS у родителя, временной/итоговой "
            "папки и файлов не допускается ни одной расширенной ACL, включая deny и "
            "ненаследуемую запись; chmod сам по себе не доказывает отсутствие ACL, а "
            "для Linux проверка ACL не заявляется. После создания временной папки "
            "ничего автоматически не удаляется. При любой неопределённости сохраните "
            "входы и все объекты, остановите автоматику и передайте системному "
            "администратору полную строку с device/inode для учёта всех имён и жёстких "
            "ссылок. Не повторяйте ту же папку назначения. После исправления сбоя повторите "
            "неизменные входы в новую отсутствующую соседнюю папку, получите нормальный "
            "полный stdout и побайтно сравните две четырёхфайловые папки. Пустой, "
            "частичный или выглядящий полным stdout прерванной команды недействителен. "
            "После кода 0 сохраните receipt_sha256 только из полного успешного stdout "
            "отдельно от итоговой папки; при сбое подтверждения берите его лишь из "
            "успешного повтора после побайтного сравнения. Квитанция и stdout не "
            "раскрывают тексты, выбранные значения, метки людей, "
            "время их действий или абсолютные входные пути. Код 0 — только ограниченное "
            "техническое закрытие, не аутентифицированная проверка, не юридическое "
            "одобрение, не свежесть права, не разрешение публикации или подачи."
            "\n\nПример команды:\n"
            "  python3 \"$JM\" quality coding-audit-finalize \\\n"
            "    --bundle \"$AUDIT_BUNDLE\" \\\n"
            "    --expected-manifest-sha256 \"$EXPECTED_MANIFEST_SHA256\" \\\n"
            "    --audit-import \"$AUDIT_IMPORT\" \\\n"
            "    --expected-import-receipt-sha256 \"$EXPECTED_IMPORT_RECEIPT_SHA256\" \\\n"
            "    --resolutions \"$RESOLUTIONS\" \\\n"
            "    --output-dir \"$FINALIZATION\""
        ),
        formatter_class=RussianExampleHelpFormatter,
    )
    quality_audit_finalize.add_argument(
        "--bundle",
        required=True,
        help="Точная приватная папка штатного пакета coding-audit-prepare.",
    )
    quality_audit_finalize.add_argument(
        "--expected-manifest-sha256",
        required=True,
        help=(
            "Отдельно сохранённый manifest_sha256 из полного успешного stdout "
            "coding-audit-prepare."
        ),
    )
    quality_audit_finalize.add_argument(
        "--audit-import",
        required=True,
        help=(
            "Точная приватная двухфайловая папка успешного "
            "coding-audit-review-import."
        ),
    )
    quality_audit_finalize.add_argument(
        "--expected-import-receipt-sha256",
        required=True,
        help=(
            "Отдельно сохранённый receipt_sha256 из полного успешного stdout "
            "coding-audit-review-import."
        ),
    )
    quality_audit_finalize.add_argument(
        "--resolutions",
        help=(
            "Соседний приватный файл 0600 со строгим ограниченным JSONL полного "
            "ручного разрешения обеих карт; опустите только когда обе карты пусты."
        ),
    )
    quality_audit_finalize.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Новая отсутствующая соседняя папка для четырёх файлов финализации; "
            "перезапись запрещена."
        ),
    )
    quality_audit_finalize.set_defaults(func=cmd_quality_coding_audit_finalize)

    quality_gate_exit_help = (
        "Коды завершения проверки качества: 0 — ограниченная проверка "
        "завершена (complete=true), в том числе с явно раскрытыми "
        "ограничениями; 2 — ошибка параметров, входного файла или записи "
        "результата; 3 — проверка неполна или устарела (complete=false). "
        "При коде 3 полный JSON остаётся в стандартном выводе (stdout) и "
        "записывается в --output, если путь указан. Код 0 не означает "
        "юридическую готовность и не разрешает подачу жалобы."
    )
    quality_reliability = quality_sub.add_parser(
        "coding-reliability",
        help="Проверить независимое кодирование и неразрешённые расхождения",
        epilog=quality_gate_exit_help,
    )
    quality_reliability.add_argument("--audit-plan", required=True)
    quality_reliability.add_argument("--primary-decisions", required=True)
    quality_reliability.add_argument("--audit-decisions", required=True)
    quality_reliability.add_argument("--adjudications")
    quality_reliability.add_argument("--output")
    quality_reliability.set_defaults(func=cmd_quality_coding_reliability)

    quality_refresh = quality_sub.add_parser(
        "prefiling-refresh",
        help="Проверить актуальность корпуса непосредственно перед подачей жалобы",
        epilog=quality_gate_exit_help,
    )
    corpus_digest_help = (
        "SHA-256 корпуса: можно вставить как 64 hex-символа или прямо как "
        "corpus-evidence-sha256:<64 hex> из cache init/refresh-plan."
    )
    quality_refresh.add_argument(
        "--baseline-corpus-digest", required=True, help=corpus_digest_help
    )
    quality_refresh.add_argument(
        "--current-corpus-digest", required=True, help=corpus_digest_help
    )
    quality_refresh.add_argument("--subject-evidence-sha256", required=True)
    quality_refresh.add_argument(
        "--refresh-plan",
        required=True,
        help="JSON-план из cache refresh-plan с явными сегментами охвата.",
    )
    quality_refresh.add_argument(
        "--treatments",
        required=True,
        help=(
            "Полный JSON-набор связей из cache treatment quality-export; "
            "произвольный список не принимается."
        ),
    )
    quality_refresh.add_argument(
        "--corpus-root",
        required=True,
        help=(
            "Существующая корневая папка того же публичного корпуса. "
            "Проверка открывает её только для чтения и заново сверяет план, "
            "полный набор связей и контрольную сумму."
        ),
    )
    quality_refresh.add_argument(
        "--checked-through",
        required=True,
        help=(
            "Дата и время, по которые проверен корпус: RFC 3339, "
            "с секундами и часовым поясом."
        ),
    )
    quality_refresh.add_argument(
        "--filing-cutoff",
        required=True,
        help=(
            "Контрольный момент начала финального окна подготовки к подаче "
            "(не процессуальный срок): RFC 3339, с секундами и часовым поясом."
        ),
    )
    quality_refresh.add_argument("--reviewer", required=True)
    quality_refresh.add_argument(
        "--reviewed-at",
        required=True,
        help="Дата и время ручной проверки: RFC 3339, с секундами и часовым поясом.",
    )
    quality_refresh.add_argument(
        "--claim-id",
        action="append",
        required=True,
        help="Идентификатор требования; повторите параметр для каждого требования.",
    )
    quality_refresh.add_argument("--output")
    quality_refresh.set_defaults(func=cmd_quality_prefiling_refresh)

    handoff = sub.add_parser(
        "handoff",
        help=(
            "Подготовить и проверить пакет результатов для передачи другому навыку"
        ),
    )
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_create = handoff_sub.add_parser(
        "create",
        help=(
            "Создать пакет передачи, связанный с точными версиями исходных файлов"
        ),
        description=(
            "Создать пакет передачи, связанный с точными версиями исходных "
            "файлов. Успешная проверка подтверждает только техническую цепочку "
            "файлов."
        ),
        epilog=(
            "Она не подтверждает личность или независимость проверяющего, "
            "юридическую правильность, актуальность права, разрешение на "
            "публикацию, одобрение результата или готовность к подаче."
        ),
    )
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
        help=(
            "Вид данных: unproven_research_questions — непроверенные вопросы; "
            "approved_bounded_findings — одобренные выводы в доказанных пределах; "
            "authority_cards — карточки источников версии 2. "
            "selected_authorities — устаревший тип версии 1 только для аудита; "
            "create его отклоняет, используйте authority_cards."
        ),
    )
    handoff_create.add_argument(
        "--payload",
        help=(
            "Путь к JSON-файлу с непроверенными вопросами; для проверенных "
            "результатов этот параметр запрещён."
        ),
    )
    handoff_create.add_argument(
        "--request",
        help=(
            "Путь к JSON-файлу запроса версии 2 для результата, сформированного "
            "из проверенных файлов."
        ),
    )
    handoff_create.add_argument("--claim-id", action="append", default=[])
    handoff_create.add_argument("--candidate-id", action="append", default=[])
    handoff_create.add_argument("--position-card-id", action="append", default=[])
    handoff_create.add_argument(
        "--quality-binding",
        action="append",
        default=[],
        help=(
            "Путь к JSON-файлу проверки качества практики; параметр можно повторить."
        ),
    )
    handoff_create.add_argument(
        "--expected-finalization-receipt-sha256",
        help=(
            "Внешний SHA-256, отдельно сохранённый из обычного успешного "
            "вывода coding-audit-finalize; требуется для единственной квитанции "
            "финализации среди --quality-binding. Это самохеш квитанции, тогда "
            "как artifact_sha256 связывает её полный JSON; значение не берётся "
            "из проверяемого файла."
        ),
    )
    handoff_create.add_argument("--limitations")
    handoff_create.add_argument("--limitation", action="append", default=[])
    handoff_create.add_argument("--run-id")
    handoff_create.add_argument(
        "--created-at",
        help=(
            "Дата и время создания в формате ISO 8601; по умолчанию текущее "
            "время UTC."
        ),
    )
    handoff_create.add_argument("--output")
    handoff_create.set_defaults(func=cmd_handoff_create)
    handoff_check_description = (
        "Проверить пакет передачи и его хеши. Для reviewed-пакета команда "
        "проверяет шесть quality bindings: внешний самохеш квитанции уже должен "
        "быть внесён отдельным параметром handoff create, а artifact_sha256 "
        "связывает полный JSON квитанции. Отсутствующее внешнее значение не "
        "восстанавливается из проверяемого файла."
    )
    handoff_check = handoff_sub.add_parser(
        "check",
        help=handoff_check_description,
        description=handoff_check_description,
    )
    handoff_check.add_argument("--input", required=True)
    handoff_check.add_argument(
        "--source-workspace",
        "--workspace",
        dest="source_workspace",
        help="Доверенная рабочая папка источника; --workspace сохранён как совместимое имя",
    )
    handoff_check.add_argument("--expected-target", required=True)
    handoff_check.set_defaults(func=cmd_handoff_check)
    handoff_import_description = (
        "Без повторов добавить пакет передачи во входящий реестр. Reviewed-пакет "
        "принимается только с шестью связанными quality-артефактами; внешний "
        "самохеш квитанции переносится из отдельного параметра handoff create и "
        "не восстанавливается из проверяемого файла."
    )
    handoff_import = handoff_sub.add_parser(
        "import",
        help=handoff_import_description,
        description=handoff_import_description,
    )
    handoff_import.add_argument("--input", required=True)
    handoff_import.add_argument("--ledger", required=True)
    handoff_import.add_argument(
        "--source-workspace",
        "--workspace",
        dest="source_workspace",
        help="Доверенная рабочая папка источника; --workspace сохранён как совместимое имя",
    )
    handoff_import.add_argument("--expected-target", required=True)
    handoff_import.set_defaults(func=cmd_handoff_import)

    cache = sub.add_parser("cache", help="Управлять локальным публичным корпусом")
    cache_sub = cache.add_subparsers(dest="cache_command", required=True)
    cache_init = cache_sub.add_parser("init", help="Создать кэш SQLite и хранилище объектов")
    cache_init.add_argument("--root", required=True)
    cache_init.set_defaults(func=cmd_cache_init)
    cache_seed = cache_sub.add_parser("register-seed", help="Добавить исходный публичный URL")
    cache_seed.add_argument("--root", required=True)
    cache_seed.add_argument("--url", required=True)
    cache_seed.add_argument(
        "--role",
        default="official_user_seed",
        help=(
            "Роль источника; по умолчанию official_user_seed "
            "(официальный адрес, указанный пользователем)."
        ),
    )
    cache_seed.set_defaults(func=cmd_cache_register_seed)
    cache_ingest = cache_sub.add_parser(
        "ingest", help="Добавить проверенный снимок публичного источника и его текст"
    )
    cache_ingest.add_argument("--root", required=True)
    cache_ingest.add_argument("--seed-id", required=True)
    cache_ingest.add_argument("--raw", required=True)
    cache_ingest.add_argument("--content-type")
    cache_ingest.add_argument(
        "--fetched-at",
        required=True,
        help=(
            "Дата и время получения снимка: RFC 3339, с секундами и часовым "
            "поясом; будущее время запрещено."
        ),
    )
    cache_ingest.add_argument(
        "--parser-manifest",
        required=True,
        help="Путь к JSON-файлу с описанием использованного парсера.",
    )
    cache_ingest.add_argument("--text")
    cache_ingest.add_argument(
        "--document-id",
        help="Устойчивый идентификатор документа для индексируемого полного текста.",
    )
    cache_ingest.add_argument(
        "--chain-id",
        help="Идентификатор судебной цепочки для индексируемого полного текста.",
    )
    cache_ingest.add_argument(
        "--query-lane",
        help="Дорожка запроса, по которой найден индексируемый полный текст.",
    )
    cache_ingest.set_defaults(func=cmd_cache_ingest)
    cache_pin = cache_sub.add_parser(
        "pin-run", help="Неизменяемо закрепить снимки за публичным запуском"
    )
    cache_pin.add_argument("--root", required=True)
    cache_pin.add_argument("--run-id", required=True)
    cache_pin.add_argument("--snapshot", action="append", required=True)
    cache_pin.set_defaults(func=cmd_cache_pin_run)
    cache_export = cache_sub.add_parser(
        "export-run", help="Экспортировать переносимый пакет только с публичными данными"
    )
    cache_export.add_argument("--root", required=True)
    cache_export.add_argument("--run-id", required=True)
    cache_export.add_argument("--output", required=True)
    cache_export.set_defaults(func=cmd_cache_export_run)
    cache_import = cache_sub.add_parser(
        "import-run", help="Проверить и импортировать переносимый пакет только с публичными данными"
    )
    cache_import.add_argument("--root", required=True)
    cache_import.add_argument("--input", required=True)
    cache_import.set_defaults(func=cmd_cache_import_run)
    cache_search = cache_sub.add_parser("search", help="Искать только в локально индексированном тексте")
    cache_search.add_argument("--root", required=True)
    cache_search.add_argument("--query", required=True)
    cache_search.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Максимум результатов; по умолчанию 100.",
    )
    cache_search.set_defaults(func=cmd_cache_search)
    cache_refresh = cache_sub.add_parser(
        "refresh-plan", help="Составить план обновления исходных публичных адресов"
    )
    cache_refresh.add_argument("--root", required=True)
    cache_refresh.add_argument(
        "--as-of",
        required=True,
        help=(
            "Дата и время состояния корпуса: RFC 3339, "
            "с секундами и часовым поясом."
        ),
    )
    cache_refresh.add_argument("--max-age-seconds", type=int, required=True)
    cache_refresh.add_argument(
        "--coverage-requirements",
        required=True,
        help=(
            "JSON/JSONL с хотя бы одним явно проверяемым сегментом охвата: "
            "court_id, period_id, enumerator_id и/или source_role."
        ),
    )
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
        help=(
            "Этап цепочки: enumerated — дело найдено в перечне; card — получена "
            "карточка; document_link — найдена ссылка на документ; "
            "payload_validated — ответ источника проверен; full_text_extracted — "
            "извлечён полный текст; indexed — текст добавлен в поиск; screened — "
            "пройден первичный отбор; coded — текст размечен; "
            "approved_independent_chain — независимая цепочка одобрена; blocked — "
            "работа заблокирована; retryable_error — временная ошибка, можно "
            "повторить; official_page_no_text — на официальной странице нет текста; "
            "unextractable — текст нельзя извлечь; ocr_pending — ожидается OCR; "
            "human_verification_pending — нужна ручная проверка."
        ),
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
    treatment_write_epilog = (
        "Если публичный кэш занят другой операцией записи, команда завершится "
        "с кодом 2 и ничего не запишет в treatment и его историю. "
        "Автоматического повтора нет: после завершения другой операции явно "
        "повторите команду. Повтор не заменяет ручную юридическую проверку."
    )
    cache_treatment_discover = cache_treatment_sub.add_parser(
        "discover",
        help="Создать кандидата связи без придания доказательственной силы",
        epilog=treatment_write_epilog,
        formatter_class=RussianHelpFormatter,
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
        help=(
            "Отношение нового акта к позиции: applies — применяет; follows — "
            "следует ей; distinguishes — отличает обстоятельства; limits — "
            "ограничивает; rejects — отклоняет; supersedes — заменяет; unclear — "
            "отношение неясно; does_not_reach — вопрос не рассмотрен."
        ),
    )
    cache_treatment_discover.add_argument("--snapshot-id", required=True)
    cache_treatment_discover.add_argument(
        "--supersedes-treatment-id",
        help=(
            "ID ранее завершённой связи, которую заменяет новый кандидат. "
            "С момента создания кандидата прежняя связь показывается как "
            "superseded, а проверка перед подачей остаётся незавершённой до review."
        ),
    )
    cache_treatment_discover.set_defaults(func=cmd_cache_treatment_discover)
    cache_treatment_review = cache_treatment_sub.add_parser(
        "review",
        help="Неизменяемо подтвердить или отклонить кандидата",
        epilog=treatment_write_epilog,
        formatter_class=RussianHelpFormatter,
    )
    cache_treatment_review.add_argument("--root", required=True)
    cache_treatment_review.add_argument("--treatment-id", required=True)
    cache_treatment_review.add_argument(
        "--decision",
        choices=("verified", "rejected"),
        required=True,
        help=(
            "Решение проверяющего: verified — связь подтверждена; rejected — "
            "связь отклонена."
        ),
    )
    cache_treatment_review.add_argument("--reviewer", required=True)
    cache_treatment_review.add_argument("--quote")
    cache_treatment_review.add_argument("--locator")
    cache_treatment_review.add_argument(
        "--speaker",
        choices=("court", "party", "unknown"),
        help=(
            "Автор цитаты: court — суд, party — участник дела, unknown — автор "
            "не установлен."
        ),
    )
    cache_treatment_review.add_argument("--confirmed-target-authority-id")
    cache_treatment_review.add_argument(
        "--target-identity-confirmed",
        action="store_true",
        help="Подтвердить, что проверяющий вручную сверил целевой судебный акт.",
    )
    cache_treatment_review.add_argument(
        "--decision-reason",
        help=(
            "Причина отклонения кандидата; обязательна при --decision rejected."
        ),
    )
    cache_treatment_review.add_argument(
        "--reviewed-at",
        help=(
            "Дата и время ручной проверки: RFC 3339, с секундами и часовым "
            "поясом; по умолчанию текущее время UTC."
        ),
    )
    cache_treatment_review.set_defaults(func=cmd_cache_treatment_review)
    cache_treatment_list = cache_treatment_sub.add_parser(
        "list",
        help=(
            "Показать эффективное состояние связей; review_decision сохраняет "
            "исходное неизменяемое решение проверяющего"
        ),
    )
    cache_treatment_list.add_argument("--root", required=True)
    cache_treatment_list.add_argument(
        "--verified-only",
        action="store_true",
        help="Показать только активные verified-связи, исключив superseded.",
    )
    cache_treatment_list.set_defaults(func=cmd_cache_treatment_list)
    cache_treatment_history = cache_treatment_sub.add_parser(
        "history", help="Показать неизменяемую историю проверки связи"
    )
    cache_treatment_history.add_argument("--root", required=True)
    cache_treatment_history.add_argument("--treatment-id", required=True)
    cache_treatment_history.set_defaults(func=cmd_cache_treatment_history)
    cache_treatment_quality_export = cache_treatment_sub.add_parser(
        "quality-export",
        help=(
            "Выгрузить полный привязанный к корпусу набор всех связей для "
            "проверки перед подачей, включая pending и superseded"
        ),
    )
    cache_treatment_quality_export.add_argument(
        "--root", required=True, help="Корневая папка локального публичного корпуса."
    )
    cache_treatment_quality_export.add_argument(
        "--output",
        required=True,
        help=(
            "Файл полного набора: включает все ID, состояние корпуса, "
            "контрольную сумму популяции и контрольную сумму набора."
        ),
    )
    cache_treatment_quality_export.set_defaults(
        func=cmd_cache_treatment_quality_export
    )

    source = sub.add_parser("source", help="Сверить независимые маршруты официальных источников")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_reconcile = source_sub.add_parser(
        "reconcile", help="Сверить наблюдения без расширения заявленной полноты"
    )
    source_reconcile.add_argument("--manifests", required=True)
    source_reconcile.add_argument("--observations", required=True)
    source_reconcile.add_argument("--route-coverage", required=True)
    source_reconcile.add_argument(
        "--requested-from",
        required=True,
        help="Начальная дата периода в формате ГГГГ-ММ-ДД.",
    )
    source_reconcile.add_argument(
        "--requested-to",
        required=True,
        help="Конечная дата периода в формате ГГГГ-ММ-ДД.",
    )
    source_reconcile.add_argument("--workspace")
    source_reconcile.add_argument("--output")
    source_reconcile.set_defaults(func=cmd_source_reconcile)
    source_verify = source_sub.add_parser(
        "verify-manifest",
        help=(
            "Проверить правила получения перечня дел с блокировкой при "
            "неопределённости"
        ),
    )
    source_verify.add_argument("--input", required=True)
    source_verify.add_argument("--output")
    source_verify.set_defaults(func=cmd_source_verify_manifest)
    source_promote = source_sub.add_parser(
        "promote-enumerator", help="Повысить маршрут только после прохождения всех этапов проверки"
    )
    source_promote.add_argument("--manifest", required=True)
    source_promote.add_argument("--verification", required=True)
    source_promote.add_argument("--reviewer", required=True)
    source_promote.add_argument(
        "--reviewed-at",
        help=(
            "Дата и время ручной проверки в формате ISO 8601; по умолчанию "
            "текущее время UTC."
        ),
    )
    source_promote.add_argument("--output")
    source_promote.set_defaults(func=cmd_source_promote_enumerator)
    _populate_subparser_descriptions(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (
        OSError,
        TypeError,
        ValueError,
        RecursionError,
        sqlite3.Error,
        json.JSONDecodeError,
    ) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
