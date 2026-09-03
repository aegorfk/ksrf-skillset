"""Версионированная локальная рабочая папка одного обращения в КС РФ."""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from .contracts import (
    MATTER_WORKSPACE_SCHEMA,
    SCHEMA_VERSION,
    SETUP_PROFILES,
    ContractError,
    load_json_object,
    normalized_identifier,
    require_fields,
    sha256_file,
    stable_id,
    utc_now,
    write_json_exclusive,
)


class MatterWorkspaceError(ContractError):
    """Рабочая папка дела не может быть безопасно прочитана или изменена."""


ARTIFACT_PATHS = {
    "input_registry": "inputs/registry",
    "input_objects": "inputs/objects/sha256",
    "source_evidence": "evidence/source-evidence.json",
    "norm_version_passports": "evidence/norm-version-passports.json",
    "claim_application_ledger": "evidence/claim-application-ledger.json",
    "constitutional_issue_candidates": "evidence/constitutional-issue-candidates.json",
    "adverse_material": "evidence/adverse-material.json",
    "draft_evidence_map": "drafts/evidence-map.json",
    "release_artifacts": "release",
    "audit_events": "audit/events",
}

DIRECTORY_ARTIFACT_KEYS = frozenset(
    {"input_registry", "input_objects", "release_artifacts", "audit_events"}
)

LEDGER_TITLES = {
    "source_evidence": "Реестр доказательств по источникам",
    "norm_version_passports": "Паспорта редакций оспариваемых норм",
    "claim_application_ledger": "Реестр требований и применения норм",
    "constitutional_issue_candidates": "Варианты конституционно-правовой проблемы",
    "adverse_material": "Неблагоприятная практика и другие возражения",
    "draft_evidence_map": "Связь утверждений черновика с доказательствами",
}

UNRESOLVED_DEFAULTS = {
    "official_sources": {
        "state": "unknown",
        "item": "Официальные тексты значимых актов",
        "why": "Без официальных якорей нельзя использовать правовые положения как основание готовой жалобы.",
        "next_action": "Загрузите официальные файлы или зафиксируйте их официальные адреса и даты получения.",
    },
    "norm_versions": {
        "state": "unknown",
        "item": "Редакции оспариваемых норм на значимые даты",
        "why": "Нужно доказать, какой именно текст нормы регулировал спор и судебные стадии.",
        "next_action": "Укажите значимые даты и добавьте официальные тексты каждой применимой редакции.",
    },
    "norm_application": {
        "state": "unknown",
        "item": "Применение нормы судами",
        "why": "Жалоба должна показать прямое или доказанное имплицитное применение нормы, причинно повлиявшее на результат.",
        "next_action": "Добавьте полные тексты судебных актов с точными фрагментами рассуждения и резолютивной части.",
    },
    "admissibility": {
        "state": "unknown",
        "item": "Процессуальная допустимость обращения",
        "why": "Неизвестные сроки, исчерпание или предмет оспаривания не могут пройти проверку готовности.",
        "next_action": "Заполните судебную цепочку, даты актов и способ исчерпания средств защиты.",
    },
    "constitutional_issue": {
        "state": "unknown",
        "item": "Конституционно-правовая проблема и её граница с пересмотром фактов",
        "why": "Нужен доказанный нормативный смысл, а не только несогласие с исходом конкретного дела.",
        "next_action": "Сформулируйте объект проверки, применённый смысл, затронутое право и допустимый способ защиты.",
    },
    "release": {
        "state": "unknown",
        "item": "Проверенный комплект DOCX/PDF и приложений",
        "why": "Рабочий черновик нельзя называть готовым к подаче без формальной, доказательственной и визуальной проверки.",
        "next_action": "После юридической проверки соберите DOCX/PDF, опись, контрольные суммы и проверьте каждую страницу.",
    },
}

PROGRESS_LABELS = {
    "blocked": "заблокировано",
    "degraded": "доступно с ограничениями",
    "expert_review": "готово к проверке экспертом",
    "human_filing": "готово к подписи и подаче человеком",
}

AUTHORITY_CLASSES = {
    "official_primary",
    "official_derivative",
    "discovery_only",
    "user_supplied_unverified",
}
PRIVACY_CLASSES = {
    "local_confidential",
    "matter_local_private",
    "public_official",
    "consented_private_corpus",
    "anonymized_shared",
}


def _workspace_path(value: str | Path) -> Path:
    return Path(value).expanduser().absolute()


def _path_metadata(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MatterWorkspaceError(
            f"Рабочая папка небезопасна: не удалось проверить путь {path}: {exc}."
        ) from exc


def _resolved_for_preflight(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise MatterWorkspaceError(
            f"Рабочая папка небезопасна: не удалось разрешить путь {path}: {exc}."
        ) from exc


def _preflight_route(
    workspace: Path,
    resolved_workspace: Path,
    *,
    label: str,
    relative: str,
) -> os.stat_result | None:
    relative_path = Path(relative)
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or ".." in relative_path.parts
    ):
        raise MatterWorkspaceError(
            f"Рабочая папка небезопасна: путь {label} не является внутренним."
        )

    candidate = workspace / relative_path
    current = workspace
    endpoint_metadata: os.stat_result | None = None
    for index, component in enumerate(relative_path.parts):
        current = current / component
        metadata = _path_metadata(current)
        if metadata is None:
            break
        if stat.S_ISLNK(metadata.st_mode):
            raise MatterWorkspaceError(
                f"Рабочая папка небезопасна: путь {label} проходит через "
                f"символическую ссылку {current}."
            )
        is_endpoint = index == len(relative_path.parts) - 1
        if not is_endpoint and not stat.S_ISDIR(metadata.st_mode):
            raise MatterWorkspaceError(
                f"Рабочая папка небезопасна: компонент {current} пути {label} "
                "не является каталогом."
            )
        if is_endpoint:
            endpoint_metadata = metadata

    resolved_candidate = _resolved_for_preflight(candidate)
    try:
        resolved_candidate.relative_to(resolved_workspace)
    except ValueError as exc:
        raise MatterWorkspaceError(
            f"Рабочая папка небезопасна: путь {label} выходит за пределы дела."
        ) from exc
    return endpoint_metadata


def _directory_has_entries(path: Path, *, label: str) -> bool:
    try:
        with os.scandir(path) as entries:
            return next(entries, None) is not None
    except OSError as exc:
        raise MatterWorkspaceError(
            f"Рабочая папка небезопасна: не удалось проверить каталог {label}: {exc}."
        ) from exc


def _preflight_initialization_layout(workspace: Path) -> bool:
    """Проверить статический layout до чтения manifest и первой записи."""

    workspace_metadata = _path_metadata(workspace)
    if workspace_metadata is not None:
        if stat.S_ISLNK(workspace_metadata.st_mode):
            raise MatterWorkspaceError(
                "Рабочая папка небезопасна: сам путь является символической ссылкой."
            )
        if not stat.S_ISDIR(workspace_metadata.st_mode):
            raise MatterWorkspaceError(
                "Рабочая папка должна быть обычным каталогом."
            )
    resolved_workspace = _resolved_for_preflight(workspace)

    route_metadata: dict[str, os.stat_result | None] = {}
    route_metadata["matter_manifest"] = _preflight_route(
        workspace,
        resolved_workspace,
        label="matter.json",
        relative="matter.json",
    )
    for key, relative in ARTIFACT_PATHS.items():
        route_metadata[key] = _preflight_route(
            workspace,
            resolved_workspace,
            label=key,
            relative=relative,
        )

    manifest_metadata = route_metadata["matter_manifest"]
    manifest_present = manifest_metadata is not None
    if manifest_present and not stat.S_ISREG(manifest_metadata.st_mode):
        raise MatterWorkspaceError(
            "Рабочая папка небезопасна: matter.json должен быть обычным файлом."
        )

    for key in DIRECTORY_ARTIFACT_KEYS:
        metadata = route_metadata[key]
        if metadata is not None and not stat.S_ISDIR(metadata.st_mode):
            raise MatterWorkspaceError(
                f"Рабочая папка небезопасна: путь {key} должен быть каталогом."
            )
    if manifest_present:
        for key in LEDGER_TITLES:
            metadata = route_metadata[key]
            if metadata is not None and not stat.S_ISREG(metadata.st_mode):
                raise MatterWorkspaceError(
                    f"Рабочая папка небезопасна: реестр {key} должен быть обычным файлом."
                )
        return True

    for key in DIRECTORY_ARTIFACT_KEYS:
        metadata = route_metadata[key]
        if metadata is not None and _directory_has_entries(
            workspace / ARTIFACT_PATHS[key],
            label=key,
        ):
            raise MatterWorkspaceError(
                f"Каталог {key} уже содержит данные без matter.json; "
                "данные оставлены без изменений."
            )
    for key in LEDGER_TITLES:
        if route_metadata[key] is not None:
            ledger_path = workspace / ARTIFACT_PATHS[key]
            raise MatterWorkspaceError(
                f"Путь {ledger_path} уже существует без matter.json; "
                "данные оставлены без изменений."
            )
    return False


def _empty_ledger(matter_id: str, ledger_name: str, created_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "matter_id": matter_id,
        "ledger": ledger_name,
        "title": LEDGER_TITLES[ledger_name],
        "state": "unknown",
        "records": [],
        "created_at": created_at,
    }


def _write_audit_event(
    workspace: Path,
    matter_id: str,
    *,
    event_type: str,
    subject_id: str,
    occurred_at: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    event_id = stable_id(
        "event", f"{matter_id}|{event_type}|{subject_id}|{occurred_at}", length=24
    )
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "matter_id": matter_id,
        "event_type": event_type,
        "subject_id": subject_id,
        "occurred_at": occurred_at,
        "details": dict(details),
    }
    event_path = workspace / ARTIFACT_PATHS["audit_events"] / f"{event_id}.json"
    write_json_exclusive(event_path, event)
    return event


def initialize_matter(
    destination: str | Path,
    *,
    matter_identifier: str,
    profile: str = "basic",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Создать или идемпотентно открыть matter workspace, ничего не переписывая."""

    if profile not in SETUP_PROFILES:
        raise MatterWorkspaceError(f"Неизвестный профиль настройки: {profile}.")
    try:
        canonical_identifier = normalized_identifier(matter_identifier)
    except ContractError as exc:
        raise MatterWorkspaceError(str(exc)) from exc
    matter_id = stable_id("matter", canonical_identifier)
    workspace_id = stable_id("workspace", canonical_identifier)
    workspace = _workspace_path(destination)
    manifest_path = workspace / "matter.json"

    if _preflight_initialization_layout(workspace):
        existing = load_matter(workspace)
        if existing["matter_id"] != matter_id:
            raise MatterWorkspaceError(
                "Эта рабочая папка уже относится к другому делу; выберите другую папку."
            )
        if existing["setup_profile"] != profile:
            raise MatterWorkspaceError(
                f"Рабочая папка уже создана с профилем {existing['setup_profile']}; "
                "профиль не переписан. Используйте отдельное явное изменение конфигурации."
            )
        return existing

    workspace.mkdir(parents=True, exist_ok=True, mode=0o700)
    timestamp = created_at or utc_now()
    for key in ("input_registry", "input_objects", "release_artifacts", "audit_events"):
        (workspace / ARTIFACT_PATHS[key]).mkdir(parents=True, exist_ok=True, mode=0o700)

    for ledger_name in LEDGER_TITLES:
        ledger_path = workspace / ARTIFACT_PATHS[ledger_name]
        if ledger_path.exists():
            raise MatterWorkspaceError(
                f"Путь {ledger_path} уже существует без matter.json; данные оставлены без изменений."
            )
        write_json_exclusive(ledger_path, _empty_ledger(matter_id, ledger_name, timestamp))

    unresolved = json.loads(json.dumps(UNRESOLVED_DEFAULTS, ensure_ascii=False))
    matter = {
        "$schema": MATTER_WORKSPACE_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "matter_id": matter_id,
        "workspace_id": workspace_id,
        "matter_identifier": matter_identifier,
        "matter_identifier_normalized": canonical_identifier,
        "setup_profile": profile,
        "state": "initialized",
        "created_at": timestamp,
        "privacy": {
            "default_class": "local_confidential",
            "external_transmission_allowed": False,
            "cross_matter_index_allowed": False,
            "corpus_consent": False,
        },
        "artifact_paths": dict(ARTIFACT_PATHS),
        "unresolved": unresolved,
        "human_controls": {
            "expert_review_required": True,
            "signature_automated": False,
            "payment_automated": False,
            "filing_automated": False,
        },
    }
    if not write_json_exclusive(manifest_path, matter):
        existing = load_matter(workspace)
        if existing["matter_id"] != matter_id:
            raise MatterWorkspaceError(
                "Рабочая папка была одновременно создана для другого дела; данные не переписаны."
            )
        if existing["setup_profile"] != profile:
            raise MatterWorkspaceError(
                f"Рабочая папка уже создана с профилем {existing['setup_profile']}; "
                "профиль не переписан."
            )
        return existing
    _write_audit_event(
        workspace,
        matter_id,
        event_type="matter_initialized",
        subject_id=workspace_id,
        occurred_at=timestamp,
        details={"setup_profile": profile, "external_transmission_performed": False},
    )
    return matter


def load_matter(workspace: str | Path) -> dict[str, Any]:
    root = _workspace_path(workspace)
    path = root / "matter.json"
    try:
        matter = load_json_object(path)
        require_fields(
            matter,
            (
                "schema_version",
                "matter_id",
                "workspace_id",
                "setup_profile",
                "privacy",
                "artifact_paths",
                "unresolved",
                "human_controls",
            ),
            label="Контракт рабочей папки",
        )
    except ContractError as exc:
        raise MatterWorkspaceError(f"Контракт рабочей папки повреждён: {exc}") from exc
    expected_top_level = {
        "$schema",
        "schema_version",
        "matter_id",
        "workspace_id",
        "matter_identifier",
        "matter_identifier_normalized",
        "setup_profile",
        "state",
        "created_at",
        "privacy",
        "artifact_paths",
        "unresolved",
        "human_controls",
    }
    if set(matter) != expected_top_level:
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: состав полей не соответствует схеме."
        )
    if matter.get("$schema") != MATTER_WORKSPACE_SCHEMA:
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: указан неизвестный идентификатор схемы."
        )
    if matter["schema_version"] != SCHEMA_VERSION:
        raise MatterWorkspaceError(
            f"Контракт рабочей папки повреждён: версия {matter['schema_version']} не поддерживается."
        )
    if matter["setup_profile"] not in SETUP_PROFILES:
        raise MatterWorkspaceError("Контракт рабочей папки повреждён: неизвестный профиль.")
    if matter.get("state") != "initialized" or not str(matter.get("created_at") or "").strip():
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: состояние или дата создания недопустимы."
        )
    try:
        canonical_identifier = normalized_identifier(matter.get("matter_identifier"))
    except ContractError as exc:
        raise MatterWorkspaceError(
            f"Контракт рабочей папки повреждён: {exc}"
        ) from exc
    if matter.get("matter_identifier_normalized") != canonical_identifier:
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: нормализованный идентификатор дела не совпадает."
        )
    if matter.get("matter_id") != stable_id("matter", canonical_identifier):
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: matter_id не связан с идентификатором дела."
        )
    if matter.get("workspace_id") != stable_id("workspace", canonical_identifier):
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: workspace_id не связан с идентификатором дела."
        )
    privacy = matter["privacy"]
    safe_privacy = (
        isinstance(privacy, Mapping)
        and privacy.get("default_class") == "local_confidential"
        and privacy.get("external_transmission_allowed") is False
        and privacy.get("cross_matter_index_allowed") is False
        and privacy.get("corpus_consent") is False
    )
    if not safe_privacy:
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: безопасный режим хранения и передачи не подтверждён."
        )
    human_controls = matter["human_controls"]
    safe_human_controls = (
        isinstance(human_controls, Mapping)
        and human_controls.get("expert_review_required") is True
        and human_controls.get("signature_automated") is False
        and human_controls.get("payment_automated") is False
        and human_controls.get("filing_automated") is False
    )
    if not safe_human_controls:
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: подпись, оплата и подача — только действия человека."
        )
    artifact_paths = matter["artifact_paths"]
    if not isinstance(artifact_paths, Mapping) or dict(artifact_paths) != ARTIFACT_PATHS:
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: пути артефактов не совпадают с безопасным контрактом."
        )
    resolved_root = root.resolve()
    for key, relative in ARTIFACT_PATHS.items():
        candidate = root / relative
        resolved = candidate.resolve(strict=False)
        if resolved != resolved_root and resolved_root not in resolved.parents:
            raise MatterWorkspaceError(
                f"Контракт рабочей папки повреждён: путь {key} выходит за пределы дела."
            )
        if key in DIRECTORY_ARTIFACT_KEYS:
            if not candidate.is_dir():
                raise MatterWorkspaceError(
                    f"Контракт рабочей папки повреждён: каталог {key} отсутствует."
                )
        elif not candidate.is_file():
            raise MatterWorkspaceError(
                f"Контракт рабочей папки повреждён: реестр {key} отсутствует."
            )
    unresolved = matter["unresolved"]
    if not isinstance(unresolved, Mapping) or not set(UNRESOLVED_DEFAULTS).issubset(unresolved):
        raise MatterWorkspaceError(
            "Контракт рабочей папки повреждён: обязательные неизвестности дела отсутствуют."
        )
    required_unresolved_fields = {"state", "item", "why", "next_action"}
    for code, item in unresolved.items():
        if (
            not isinstance(item, Mapping)
            or set(item) != required_unresolved_fields
            or item.get("state") != "unknown"
            or any(not str(item.get(field) or "").strip() for field in required_unresolved_fields - {"state"})
        ):
            raise MatterWorkspaceError(
                f"Контракт рабочей папки повреждён: unresolved.{code} не соответствует схеме."
            )
    return matter


def _copy_content_addressed(source: Path, workspace: Path, digest: str) -> str:
    relative = Path(ARTIFACT_PATHS["input_objects"]) / digest[:2] / digest
    destination = workspace / relative
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists():
        if not destination.is_file() or sha256_file(destination) != digest:
            raise MatterWorkspaceError(
                f"Объект {destination} конфликтует с ожидаемой контрольной суммой; запись остановлена."
            )
        return relative.as_posix()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(destination, flags, 0o600)
    try:
        with source.open("rb") as source_handle, os.fdopen(descriptor, "wb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
            target_handle.flush()
            os.fsync(target_handle.fileno())
    except Exception:
        try:
            destination.unlink()
        except OSError:
            pass
        raise
    if sha256_file(destination) != digest:
        destination.unlink(missing_ok=True)
        raise MatterWorkspaceError("Контрольная сумма сохранённого объекта не совпала; запись отменена.")
    return relative.as_posix()


def register_input(
    workspace: str | Path,
    origin: str,
    *,
    document_role: str = "case_material",
    authority_class: str = "user_supplied_unverified",
    privacy_class: str = "local_confidential",
    extraction_method: str = "not_run",
    validation_status: str = "unresolved",
    received_at: str | None = None,
) -> dict[str, Any]:
    """Зарегистрировать локальный файл или URL без сетевого получения и перезаписи версий."""

    root = _workspace_path(workspace)
    matter = load_matter(root)
    if authority_class not in AUTHORITY_CLASSES:
        raise MatterWorkspaceError(
            f"Неизвестный класс авторитетности источника: {authority_class}. Запись остановлена."
        )
    if privacy_class not in PRIVACY_CLASSES:
        raise MatterWorkspaceError(
            f"Неизвестный класс приватности: {privacy_class}. Запись остановлена."
        )
    if not str(document_role).strip():
        raise MatterWorkspaceError("Роль документа не может быть пустой.")
    timestamp = received_at or utc_now()
    parsed = urlparse(origin)
    is_url = parsed.scheme in {"http", "https"}
    if parsed.scheme and not is_url and "://" in origin:
        raise MatterWorkspaceError("Поддерживаются только локальные файлы и URL http/https.")

    if is_url:
        canonical_origin = origin.strip()
        content_hash: str | None = None
        stored_object: str | None = None
        source_type = "url"
        retrieval_status = "not_requested"
        missing_fields = ["content_sha256", "retrieved_at", "content_type", "identity_check"]
    else:
        source = Path(origin).expanduser().absolute()
        if not source.is_file():
            raise MatterWorkspaceError(f"Локальный входной файл не найден: {source}")
        canonical_origin = str(source)
        content_hash = sha256_file(source)
        stored_object = _copy_content_addressed(source, root, content_hash)
        source_type = "file"
        retrieval_status = "received"
        missing_fields = ["content_type", "identity_check"]

    input_id = stable_id(
        "input", f"{source_type}|{canonical_origin}|{content_hash or 'unresolved'}", length=24
    )
    record = {
        "schema_version": SCHEMA_VERSION,
        "input_id": input_id,
        "matter_id": matter["matter_id"],
        "source_type": source_type,
        "origin": canonical_origin,
        "received_at": timestamp,
        "retrieved_at": None,
        "retrieval_status": retrieval_status,
        "content_sha256": content_hash,
        "stored_object": stored_object,
        "document_role": document_role,
        "authority_class": authority_class,
        "privacy_class": privacy_class,
        "extraction_method": extraction_method,
        "validation_status": validation_status,
        "cross_matter_reuse_allowed": False,
        "corpus_consent_record": None,
        "missing_fields": missing_fields,
    }
    record_path = root / ARTIFACT_PATHS["input_registry"] / f"{input_id}.json"
    if not write_json_exclusive(record_path, record):
        existing = load_json_object(record_path)
        if existing.get("content_sha256") != content_hash or existing.get("origin") != canonical_origin:
            raise MatterWorkspaceError(
                "Обнаружен конфликт неизменяемой записи входного документа; существующая запись сохранена."
            )
        return existing
    _write_audit_event(
        root,
        matter["matter_id"],
        event_type="input_registered",
        subject_id=input_id,
        occurred_at=timestamp,
        details={
            "source_type": source_type,
            "content_sha256": content_hash,
            "external_transmission_performed": False,
            "cross_matter_reuse_allowed": False,
        },
    )
    return record


def build_progress_projection(
    state: str,
    *,
    found: Sequence[str],
    missing: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if state not in PROGRESS_LABELS:
        raise MatterWorkspaceError(f"Неизвестное состояние прогресса: {state}.")
    normalized_missing = [
        {
            "item": str(item.get("item") or "Неуточнённый пробел"),
            "why": str(item.get("why") or "Значение пробела ещё не установлено."),
            "next_action": str(
                item.get("next_action") or "Передайте вопрос на проверку ответственному специалисту."
            ),
            **({"code": item["code"]} if "code" in item else {}),
        }
        for item in missing
    ]
    return {
        "state": state,
        "label": PROGRESS_LABELS[state],
        "found": list(found),
        "missing": normalized_missing,
        "next_actions": list(dict.fromkeys(item["next_action"] for item in normalized_missing)),
        "expert_review": {
            "required_before_release": True,
            "message": "До выпуска эксперт должен проверить применение нормы, формулировку проблемы, неблагоприятную практику и просительную часть.",
        },
        "human_filing": {
            "automated": False,
            "message": (
                "Даже после готовности комплекта подпись, оплата и подача выполняются заявителем или его представителем."
            ),
        },
    }


def matter_status(workspace: str | Path) -> dict[str, Any]:
    root = _workspace_path(workspace)
    matter = load_matter(root)
    registry = root / matter["artifact_paths"]["input_registry"]
    registered_inputs = len(list(registry.glob("*.json"))) if registry.is_dir() else 0
    found = [
        "Рабочая папка дела создана",
        f"Выбран профиль: {matter['setup_profile']}",
    ]
    if registered_inputs:
        found.append(f"Зарегистрировано входных документов: {registered_inputs}")
    else:
        found.append("Входные документы пока не зарегистрированы")
    missing = [
        {
            "code": code,
            "item": value["item"],
            "why": value["why"],
            "next_action": value["next_action"],
        }
        for code, value in matter["unresolved"].items()
        if value.get("state") != "ready"
    ]
    state = "blocked" if missing else "expert_review"
    return {
        "schema_version": SCHEMA_VERSION,
        "matter_id": matter["matter_id"],
        "workspace_id": matter["workspace_id"],
        "setup_profile": matter["setup_profile"],
        "registered_inputs": registered_inputs,
        "progress": build_progress_projection(state, found=found, missing=missing),
    }
