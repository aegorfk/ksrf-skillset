"""Проверка локальных и явно разрешённых возможностей рабочего окружения."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from .contracts import (
    CAPABILITY_MANIFEST_SCHEMA,
    CAPABILITY_REPORT_SCHEMA,
    CAPABILITY_REQUIREMENTS,
    CAPABILITY_STATES,
    SCHEMA_VERSION,
    SETUP_PROFILES,
    ContractError,
    load_json_object,
    require_fields,
    utc_now,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "configs" / "ksrf_filing_capabilities.v1.json"
LOCAL_SERVICE_HOSTS = {"localhost", "127.0.0.1", "::1"}
MAX_PROBE_TIMEOUT_SECONDS = 5.0


def load_capability_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path).expanduser() if path is not None else DEFAULT_MANIFEST_PATH
    manifest = load_json_object(manifest_path)
    validate_capability_manifest(manifest)
    return manifest


def validate_capability_manifest(manifest: Mapping[str, Any]) -> None:
    require_fields(
        manifest,
        ("schema_version", "manifest_id", "initial_state", "safety", "profiles", "capabilities"),
        label="Манифест возможностей",
    )
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ContractError(
            f"Неподдерживаемая версия манифеста возможностей: {manifest['schema_version']}."
        )
    if manifest["initial_state"] != "skills_only":
        raise ContractError("Начальное состояние манифеста должно быть skills_only.")
    profiles = manifest["profiles"]
    if not isinstance(profiles, Mapping) or set(profiles) != set(SETUP_PROFILES):
        raise ContractError("Манифест должен определять профили basic, research и expert.")
    capabilities = manifest["capabilities"]
    if not isinstance(capabilities, list):
        raise ContractError("Поле capabilities должно быть списком.")
    seen: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, Mapping):
            raise ContractError("Каждая возможность должна быть JSON-объектом.")
        require_fields(
            capability,
            (
                "id",
                "title",
                "purpose",
                "privacy",
                "cost",
                "dependency",
                "remediation",
                "profiles",
                "dependent_gates",
                "probe",
            ),
            label="Описание возможности",
        )
        capability_id = str(capability["id"])
        if capability_id in seen:
            raise ContractError(f"Возможность {capability_id} объявлена повторно.")
        seen.add(capability_id)
        profile_map = capability["profiles"]
        if not isinstance(profile_map, Mapping) or set(profile_map) != set(SETUP_PROFILES):
            raise ContractError(
                f"Возможность {capability_id} должна быть размечена для всех трёх профилей."
            )
        if not set(profile_map.values()) <= set(CAPABILITY_REQUIREMENTS):
            raise ContractError(f"Возможность {capability_id} содержит неверный тип зависимости.")


def _timeout(probe: Mapping[str, Any]) -> float:
    raw = probe.get("timeout_seconds", 2.0)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 2.0
    return max(0.1, min(value, MAX_PROBE_TIMEOUT_SECONDS))


def _executable_probe(
    probe: Mapping[str, Any],
    *,
    which: Callable[[str], str | None],
    kind: str,
) -> dict[str, Any]:
    names = [str(item) for item in probe.get("executables", []) if str(item).strip()]
    declared_paths = [Path(str(item)).expanduser() for item in probe.get("paths", [])]
    found: list[str] = []
    missing: list[str] = []
    for name in names:
        resolved = which(name)
        if resolved:
            found.append(str(resolved))
        else:
            missing.append(name)
    for path in declared_paths:
        if path.is_file() and os.access(path, os.X_OK):
            found.append(str(path))
        else:
            missing.append(str(path))
    if found:
        partial = bool(probe.get("require_all", False)) and bool(missing)
        return {
            "probe_kind": kind,
            "state": "degraded" if partial else "ready",
            "message": (
                "Найдена только часть обязательной локальной цепочки."
                if partial
                else "Локальный инструмент найден."
            ),
            "evidence": {
                "found": sorted(set(found)),
                "missing": missing,
                "checked": names + [str(p) for p in declared_paths],
            },
        }
    return {
        "probe_kind": kind,
        "state": "unavailable",
        "message": "Ни один из объявленных локальных инструментов не найден.",
        "evidence": {
            "found": [],
            "missing": missing,
            "checked": names + [str(p) for p in declared_paths],
        },
    }


def _credential_probe(probe: Mapping[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    names = [str(item) for item in probe.get("environment", []) if str(item).strip()]
    present = [name for name in names if bool(env.get(name))]
    return {
        "probe_kind": "credential_presence",
        "state": "ready" if present else "unavailable",
        "message": (
            "Обнаружен признак настроенного доступа; значение секрета не читалось и не выводится."
            if present
            else "Признак настроенного доступа не найден; это не мешает независимым локальным этапам."
        ),
        "evidence": {"checked": names, "present": present, "secret_values_reported": False},
    }


def _python_module_probe(probe: Mapping[str, Any]) -> dict[str, Any]:
    modules = [str(item).strip() for item in probe.get("modules", ()) if str(item).strip()]
    if not modules:
        return {
            "probe_kind": "python_module",
            "state": "unknown",
            "message": "Не перечислены проверяемые Python-модули.",
            "evidence": {"found": [], "missing": [], "request_sent": False},
        }
    found: list[str] = []
    missing: list[str] = []
    for module in modules:
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, AttributeError, ValueError):
            available = False
        (found if available else missing).append(module)
    if not missing:
        state = "ready"
        message = "Все объявленные Python-модули доступны локально."
    elif found:
        state = "degraded"
        message = "Часть объявленных Python-модулей отсутствует."
    else:
        state = "unavailable"
        message = "Объявленные Python-модули не найдены."
    return {
        "probe_kind": "python_module",
        "state": state,
        "message": message,
        "evidence": {"found": found, "missing": missing, "request_sent": False},
    }


def _any_of_probe(
    probe: Mapping[str, Any],
    *,
    allow_network: bool,
    env: Mapping[str, str],
    which: Callable[[str], str | None],
    urlopen: Callable[..., Any],
) -> dict[str, Any]:
    alternatives = probe.get("alternatives") or []
    if not isinstance(alternatives, list) or not alternatives:
        return {
            "probe_kind": "any_of",
            "state": "unknown",
            "message": "Не перечислены допустимые альтернативы проверки.",
            "evidence": {
                "alternatives": [],
                "selected_index": None,
                "request_sent": False,
            },
        }
    results: list[dict[str, Any]] = []
    selected_index: int | None = None
    for index, alternative in enumerate(alternatives):
        if not isinstance(alternative, Mapping) or alternative.get("kind") == "any_of":
            result = {
                "probe_kind": "unknown",
                "state": "unknown",
                "message": "Альтернатива проверки имеет неподдерживаемый формат.",
                "evidence": {"request_sent": False},
            }
        else:
            result = run_probe(
                alternative,
                allow_network=allow_network,
                env=env,
                which=which,
                urlopen=urlopen,
            )
        results.append(result)
        if result["state"] == "ready":
            selected_index = index
            break
    states = [item["state"] for item in results]
    if selected_index is not None:
        state = "ready"
        message = "Найдена рабочая локальная альтернатива."
    elif "degraded" in states:
        state = "degraded"
        message = "Одна из альтернатив доступна частично."
    elif "interactive_required" in states:
        state = "interactive_required"
        message = "Для одной из альтернатив требуется явный ручной шаг."
    elif states and all(item == "unavailable" for item in states):
        state = "unavailable"
        message = "Ни одна из объявленных альтернатив не доступна."
    else:
        state = "unknown"
        message = "Готовность альтернатив не удалось подтвердить."
    return {
        "probe_kind": "any_of",
        "state": state,
        "message": message,
        "evidence": {
            "alternatives": results,
            "selected_index": selected_index,
            "request_sent": any(
                bool((item.get("evidence") or {}).get("request_sent")) for item in results
            ),
            "external": any(
                bool((item.get("evidence") or {}).get("external")) for item in results
            ),
        },
    }


def _directory_probe(probe: Mapping[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    env_name = probe.get("path_environment")
    raw_path = env.get(str(env_name)) if env_name else probe.get("path")
    if not raw_path:
        return {
            "probe_kind": "directory",
            "state": "unknown",
            "message": "Локальная папка не указана; проверка ничего не создавала.",
            "evidence": {"path_environment": env_name, "path": None, "created": False},
        }
    path = Path(str(raw_path)).expanduser()
    exists = path.is_dir()
    readable = exists and os.access(path, os.R_OK)
    writable = exists and os.access(path, os.W_OK)
    state = "ready" if readable and (writable or not probe.get("write_required", False)) else "unavailable"
    return {
        "probe_kind": "directory",
        "state": state,
        "message": (
            "Локальная папка доступна; проверка не создавала и не изменяла файлы."
            if state == "ready"
            else "Локальная папка отсутствует или недоступна с нужными правами."
        ),
        "evidence": {
            "path": str(path),
            "exists": exists,
            "readable": readable,
            "writable": writable,
            "created": False,
        },
    }


def _request_probe(
    probe: Mapping[str, Any],
    *,
    kind: str,
    allow_network: bool,
    urlopen: Callable[..., Any],
) -> dict[str, Any]:
    url = str(probe.get("url") or "")
    parsed = urlparse(url)
    local = parsed.hostname in LOCAL_SERVICE_HOSTS
    permitted = local or allow_network
    if not url or parsed.scheme not in {"http", "https"}:
        return {
            "probe_kind": kind,
            "state": "unknown",
            "message": "Адрес проверки отсутствует или имеет неподдерживаемую схему.",
            "evidence": {"url": url, "request_sent": False, "absence_inference_allowed": False},
        }
    if not permitted:
        return {
            "probe_kind": kind,
            "state": "interactive_required",
            "message": "Внешняя сетевая проверка не запускалась: требуется явное разрешение пользователя.",
            "evidence": {
                "url": url,
                "request_sent": False,
                "external": True,
                "absence_inference_allowed": False,
            },
        }
    timeout = _timeout(probe)
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "ksrf-doctor/1.0"})
    try:
        response = urlopen(request, timeout=timeout)
        status = int(getattr(response, "status", 200) or 200)
        close = getattr(response, "close", None)
        if callable(close):
            close()
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return {
                "probe_kind": kind,
                "state": "interactive_required",
                "message": "Сервис отвечает, но требует интерактивного входа или проверки доступа.",
                "evidence": {
                    "url": url,
                    "http_status": exc.code,
                    "request_sent": True,
                    "external": not local,
                    "absence_inference_allowed": False,
                },
            }
        return {
            "probe_kind": kind,
            "state": "unknown",
            "message": "Сервис ответил ошибкой; это не означает, что искомый акт или позиция отсутствует.",
            "evidence": {
                "url": url,
                "http_status": exc.code,
                "request_sent": True,
                "external": not local,
                "absence_inference_allowed": False,
            },
        }
    except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
        return {
            "probe_kind": kind,
            "state": "unavailable",
            "message": "Источник сейчас недоступен; это не означает, что искомый акт или позиция отсутствует.",
            "evidence": {
                "url": url,
                "error_type": type(exc).__name__,
                "request_sent": True,
                "external": not local,
                "absence_inference_allowed": False,
            },
        }
    state = "ready" if 200 <= status < 400 else "unknown"
    return {
        "probe_kind": kind,
        "state": state,
        "message": (
            "Сервис доступен для технической проверки."
            if state == "ready"
            else "Получен неоднозначный ответ; вывод об отсутствии правового материала запрещён."
        ),
        "evidence": {
            "url": url,
            "http_status": status,
            "request_sent": True,
            "external": not local,
            "absence_inference_allowed": False,
        },
    }


def run_probe(
    probe: Mapping[str, Any],
    *,
    allow_network: bool = False,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
    urlopen: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Выполнить один ограниченный probe без установки или изменения окружения."""

    environment = os.environ if env is None else env
    executable_lookup = shutil.which if which is None else which
    opener = urllib.request.urlopen if urlopen is None else urlopen
    kind = str(probe.get("kind") or "")
    if kind in {"executable", "renderer", "ocr", "browser"}:
        return _executable_probe(probe, which=executable_lookup, kind=kind)
    if kind == "python_module":
        return _python_module_probe(probe)
    if kind == "any_of":
        return _any_of_probe(
            probe,
            allow_network=allow_network,
            env=environment,
            which=executable_lookup,
            urlopen=opener,
        )
    if kind == "credential_presence":
        return _credential_probe(probe, environment)
    if kind == "trusted_approval_verifier":
        verifier_env = str(
            probe.get("verifier_id_environment") or "KSRF_TRUSTED_APPROVAL_VERIFIER_ID"
        )
        channel_env = str(
            probe.get("channel_environment") or "KSRF_AUTHENTICATED_REVIEW_CHANNEL"
        )
        verifier_id = str(environment.get(verifier_env) or "").strip()
        channel = str(environment.get(channel_env) or "").strip()
        configured = bool(verifier_id and channel == "authenticated_server")
        return {
            "probe_kind": kind,
            "state": "ready" if configured else "not_configured",
            "message": (
                "Объявлены признаки host verifier и аутентифицированного серверного канала; каждое решение всё равно проверяется криптографически."
                if configured
                else "Host verifier и аутентифицированный серверный канал не настроены."
            ),
            "evidence": {
                "configured": configured,
                "verifier_id": verifier_id or None,
                "channel": channel or None,
                "checked": [verifier_env, channel_env],
                "request_sent": False,
                "automatic_installation_performed": False,
                "automatic_account_creation_performed": False,
                "named_human_reviewer_alone_sufficient": False,
            },
        }
    if kind == "directory":
        return _directory_probe(probe, environment)
    if kind in {"service", "bounded_network"}:
        return _request_probe(
            probe,
            kind=kind,
            allow_network=allow_network,
            urlopen=opener,
        )
    if kind == "manual":
        return {
            "probe_kind": kind,
            "state": "interactive_required",
            "message": "Нужно явное подтверждение человека; автоматический вывод запрещён.",
            "evidence": {"request_sent": False, "absence_inference_allowed": False},
        }
    return {
        "probe_kind": kind or "unknown",
        "state": "unknown",
        "message": "Тип проверки не распознан; возможность нельзя считать готовой.",
        "evidence": {"request_sent": False, "absence_inference_allowed": False},
    }


def diagnose_capabilities(
    manifest: Mapping[str, Any],
    *,
    profile: str,
    allow_network: bool = False,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
    urlopen: Callable[..., Any] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    validate_capability_manifest(manifest)
    if profile not in SETUP_PROFILES:
        raise ContractError(f"Неизвестный профиль настройки: {profile}.")
    timestamp = checked_at or utc_now()
    rows: list[dict[str, Any]] = []
    blocking: list[str] = []
    optional_gaps: list[str] = []
    external_transmission = False
    for capability in manifest["capabilities"]:
        requirement = capability["profiles"][profile]
        probe_result = run_probe(
            capability["probe"],
            allow_network=allow_network,
            env=env,
            which=which,
            urlopen=urlopen,
        )
        probe_state = probe_result["state"]
        state = probe_state
        if (
            requirement == "required"
            and probe_state != "ready"
            and bool(capability.get("blocking_when_missing", False))
        ):
            state = "blocked"
        if state not in CAPABILITY_STATES:
            state = "unknown"
        if requirement == "required" and probe_state != "ready":
            blocking.append(str(capability["id"]))
        if requirement == "optional" and probe_state != "ready":
            optional_gaps.append(str(capability["id"]))
        evidence = probe_result.get("evidence", {})
        if evidence.get("request_sent") and evidence.get("external"):
            external_transmission = True
        rows.append(
            {
                "capability_id": capability["id"],
                "title": capability["title"],
                "requirement": requirement,
                "state": state,
                "probe_state": probe_state,
                "message": probe_result["message"],
                "evidence": evidence,
                "last_checked_at": timestamp,
                "dependent_gates": list(capability["dependent_gates"]),
                "purpose": capability["purpose"],
                "privacy": capability["privacy"],
                "cost": capability["cost"],
                "dependency": capability["dependency"],
                "remediation": capability["remediation"],
            }
        )
    state = "blocked" if blocking else "degraded" if optional_gaps else "ready"
    found = [row["title"] for row in rows if row["probe_state"] == "ready"]
    missing = [
        {
            "capability_id": row["capability_id"],
            "item": row["title"],
            "why": row["dependency"],
            "next_action": row["remediation"],
            "state": row["state"],
        }
        for row in rows
        if row["requirement"] != "not_used" and row["probe_state"] != "ready"
    ]
    return {
        "$schema": CAPABILITY_REPORT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "manifest_id": manifest["manifest_id"],
        "profile": profile,
        "state": state,
        "checked_at": timestamp,
        "network_probe_authorized": allow_network,
        "external_transmission_performed": external_transmission,
        "blocking_capabilities": blocking,
        "optional_gaps": optional_gaps,
        "capabilities": rows,
        "found": found,
        "missing": missing,
        "next_actions": [item["next_action"] for item in missing],
        "expert_review": {
            "required_before_release": True,
            "message": "Юрист должен проверить применённую норму, конституционную проблему и просительную часть.",
        },
        "human_filing": {
            "automated": False,
            "message": "Подписание, оплата и подача остаются действиями человека.",
        },
    }


def doctor(
    *,
    profile: str = "basic",
    manifest_path: str | Path | None = None,
    allow_network: bool = False,
) -> dict[str, Any]:
    return diagnose_capabilities(
        load_capability_manifest(manifest_path),
        profile=profile,
        allow_network=allow_network,
    )


def render_doctor_report(report: Mapping[str, Any]) -> str:
    state_labels = {
        "ready": "основные возможности готовы",
        "degraded": "работа возможна с ограничениями",
        "blocked": "есть блокирующие пробелы",
    }
    lines = [
        f"Профиль: {report['profile']}",
        f"Состояние: {state_labels.get(str(report['state']), str(report['state']))}",
        "",
        "Что найдено:",
    ]
    found = list(report.get("found", []))
    lines.extend(f"- {item}" for item in found) if found else lines.append("- Пока ничего не подтверждено.")
    lines.extend(["", "Чего не хватает:"])
    missing = list(report.get("missing", []))
    if missing:
        for item in missing:
            lines.append(f"- {item['item']}: {item['why']}")
    else:
        lines.append("- Обязательных пробелов не найдено.")
    lines.extend(["", "Следующее действие:"])
    actions = list(report.get("next_actions", []))
    lines.extend(f"- {item}" for item in actions) if actions else lines.append("- Создайте рабочую папку дела.")
    lines.extend(
        [
            "",
            "Проверка человеком:",
            f"- {report['expert_review']['message']}",
            f"- {report['human_filing']['message']}",
        ]
    )
    return "\n".join(lines) + "\n"


def manifest_as_json(manifest: Mapping[str, Any]) -> str:
    """Стабильная сериализация для диагностических и тестовых сценариев."""

    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
