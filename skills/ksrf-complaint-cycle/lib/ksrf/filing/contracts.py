"""Общие детерминированные контракты контура подготовки жалобы в КС РФ."""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
CAPABILITY_MANIFEST_SCHEMA = "capability-manifest.setup-or-matter.v1.json"
CAPABILITY_REPORT_SCHEMA = "capability-report.setup-or-matter.v1.json"
MATTER_WORKSPACE_SCHEMA = "matter-workspace.setup-or-matter.v1.json"

SETUP_PROFILES = ("basic", "research", "expert")
CAPABILITY_REQUIREMENTS = ("required", "optional", "not_used")
CAPABILITY_STATES = (
    "ready",
    "degraded",
    "blocked",
    "unknown",
    "unavailable",
    "not_configured",
    "interactive_required",
)
PROGRESS_STATES = ("blocked", "degraded", "expert_review", "human_filing")


class ContractError(ValueError):
    """Артефакт отсутствует, повреждён или не соответствует базовому контракту."""


def utc_now() -> str:
    """Вернуть текущий момент в UTC в стабильном ISO-формате."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalized_identifier(value: str) -> str:
    """Нормализовать пользовательский идентификатор без потери исходного значения."""

    normalized = unicodedata.normalize("NFKC", str(value)).strip().casefold()
    if not normalized:
        raise ContractError("Идентификатор дела не может быть пустым.")
    return " ".join(normalized.split())


def stable_id(prefix: str, value: str, *, length: int = 20) -> str:
    """Построить воспроизводимый непрозрачный идентификатор из канонической строки."""

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"Не найден обязательный файл: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"Не удалось прочитать JSON-файл {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"JSON-файл {path} должен содержать объект.")
    return payload


def write_json_exclusive(path: Path, payload: Mapping[str, Any], *, mode: int = 0o600) -> bool:
    """Записать JSON только если пути ещё нет; существующие данные не переписывать."""

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, mode)
    except FileExistsError:
        return False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return True


def require_fields(payload: Mapping[str, Any], fields: tuple[str, ...], *, label: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        joined = ", ".join(missing)
        raise ContractError(f"{label} повреждён: отсутствуют поля {joined}.")
