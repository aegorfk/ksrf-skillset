#!/usr/bin/env python3
"""Fail-closed validation and publish-manifest builder for canonical KSRF skills.

The script never installs dependencies, follows links outside the skillset,
publishes files, or reads secret values from environment variables.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import selectors
import shutil
import signal
import ssl
import stat
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from http.client import HTTPException
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

try:
    import yaml
except ImportError:  # pragma: no cover - exercised as a fail-closed runtime path
    yaml = None


SCHEMA_VERSION = "1.1.0"
CANONICAL_KSRF_PACKAGES = (
    "ksrf-argument-patterns",
    "ksrf-case-triage",
    "ksrf-cassation-judicial-meaning",
    "ksrf-complaint-cycle",
    "ksrf-complaint-facts-demands",
    "ksrf-complaint-qa",
    "ksrf-court-request-motion",
    "ksrf-decision-execution",
    "ksrf-doctrine-research",
    "ksrf-echr-argumentation",
    "ksrf-exhaustion-planner",
    "ksrf-explore-arguments",
    "ksrf-formal-filing-check",
    "ksrf-practice-authority-builder",
    "ksrf-rights-argument-builder",
)

MAX_SKILL_LINES = 500
LONG_REFERENCE_LINES = 100
EARLY_TOC_LAST_LINE = 60
MIN_BEHAVIORAL_EVALS = 3
AUTHORITY_CORPUS_STATUSES = frozenset(
    {
        "method_integrated",
        "full_text_available",
        "triangulated_academic",
        "academic_indexed",
        "bibliographic_lead",
        "discovery_only",
    }
)
AUTHORITY_CORPUS_WARNING = (
    "Присутствие в реестре не превращает доктрину в право. "
    "Discovery-only записи нельзя цитировать как авторитет без проверки автора и работы."
)
AUTHORITY_CORPUS_STATUS_LABELS = {
    "method_integrated": "метод извлечён и встроен",
    "full_text_available": "полный текст доступен; метод ожидает извлечения",
    "triangulated_academic": "автор подтверждён несколькими академическими слоями",
    "academic_indexed": "автор найден в официальном академическом указателе",
    "bibliographic_lead": "библиографический след у Блохина",
    "discovery_only": "разведочный кандидат; авторитетность не подтверждена",
}
AUTHORITY_CORPUS_ROUTE_LABELS = {
    "admissibility_and_route": (
        "допустимость, доступ к КС РФ и граница сверхинстанционности"
    ),
    "interpretation_and_positions": (
        "толкование, правовые позиции, прецедент и перенос правила"
    ),
    "proportionality_equality_dignity": (
        "соразмерность, равенство, достоинство и интенсивность контроля"
    ),
    "evidence_empirics_consequences": (
        "доказывание, законодательные факты, эмпирика и последствия"
    ),
    "remedy_execution_review": (
        "средство защиты, исполнение, пересмотр и действие решения"
    ),
    "institutional_design_and_legitimacy": (
        "институциональный дизайн, компетенция и легитимность контроля"
    ),
    "comparative_and_international": (
        "сравнительное право и международные стандарты прав человека"
    ),
    "certainty_communication_writing": (
        "правовая определённость, аргументация, коммуникация и письмо"
    ),
    "identity_sovereignty_systems": (
        "конституционная идентичность, суверенитет и взаимодействие систем"
    ),
    "social_economic_and_property_rights": (
        "социальные, трудовые, налоговые и имущественные права"
    ),
    "democracy_federalism_public_power": (
        "демократия, федерализм и организация публичной власти"
    ),
    "bioethics_privacy_technology": (
        "биоэтика, частная жизнь, данные и технологии"
    ),
}
AUTHORITY_CORPUS_ACADEMIC_SOURCES = frozenset(
    {"blokhin_bibliography", "sko_index", "mp_index"}
)
AUTHORITY_CORPUS_NON_AUTHORITATIVE_SOURCES = frozenset(
    {"zakon_discovery", "curated_method", "local_full_text"}
)
AUTHORITY_CORPUS_DECLARED_SOURCES = frozenset(
    {
        "blokhin_bibliography",
        "sko_index",
        "mp_index",
        "zakon_discovery",
        "curated_method",
    }
)
AUTHORITY_CORPUS_INTERNAL_SOURCES = frozenset({"local_full_text"})
AUTHORITY_CORPUS_SEMANTIC_SHA256 = (
    "39c1110705ede4c9dd20f4e0fe62af145b71ec6685d5c62e2e4e8b19fd74d2e2"
)
NON_PUBLIC_DNS_SUFFIXES = (
    ".alt",
    ".arpa",
    ".corp",
    ".home",
    ".internal",
    ".invalid",
    ".lan",
    ".local",
    ".localdomain",
    ".onion",
    ".private",
    ".test",
    ".example",
)
DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")

RUNTIME_PARTS = {".git", ".serena", ".pytest_cache", "__pycache__"}
DEVELOPMENT_ONLY_PARTS = {"evals", "tests"}
ROOT_ONLY_TOOL_SKILL_PATHS = frozenset(
    {
        "ksrf-argument-patterns/scripts/build_constitutionalist_authority_corpus.py",
        "ksrf-argument-patterns/scripts/enrich_ksrf_argument_patterns.py",
        "ksrf-argument-patterns/scripts/extract_ksrf_argument_patterns.py",
    }
)
SOURCE_ONLY_SKILLSET_PATHS = frozenset(
    {
        "ksrf-argument-patterns/references/argument_techniques_from_decisions.json",
        "ksrf-argument-patterns/references/automation-backlog.md",
        "ksrf-argument-patterns/references/complaint-methodology-sources.md",
        "ksrf-argument-patterns/references/evidence_maps.json",
        "ksrf-argument-patterns/references/hearing_argument_techniques.json",
        "ksrf-argument-patterns/references/language_formulas.json",
        "ksrf-complaint-cycle/scripts/add_reference_tocs.py",
    }
) | ROOT_ONLY_TOOL_SKILL_PATHS
VALIDATION_PROFILES = ("source", "runtime")
RUNTIME_CONTENT_ALGORITHM = "sha256-path-length-content-v1"
RUNTIME_CONTENT_DIGEST_FORMAT = (
    "sha256 over 4-byte big-endian relative path length + relative path + "
    "8-byte big-endian content length + content, files sorted by POSIX relative path"
)
_FRESHNESS_REF_URL = (
    "https://api.github.com/repos/aegorfk/ksrf-skillset/git/ref/heads/main"
)
_FRESHNESS_RAW_PREFIX = (
    "https://raw.githubusercontent.com/aegorfk/ksrf-skillset/"
)
_FRESHNESS_CONTENTS_MANIFEST_PREFIX = (
    "https://api.github.com/repos/aegorfk/ksrf-skillset/contents/"
    "skills-manifest.json?ref="
)
_FRESHNESS_GIT_REPOSITORY = "https://github.com/aegorfk/ksrf-skillset.git"
_FRESHNESS_GIT_REF = "refs/heads/main"
_FRESHNESS_JSON_ACCEPT = "application/vnd.github+json, application/json"
_FRESHNESS_CONTENTS_ACCEPT = "application/vnd.github.raw+json"
_FRESHNESS_GITHUB_API_VERSION = "2026-03-10"
_FRESHNESS_REF_MAX_BYTES = 64 * 1024
_FRESHNESS_MANIFEST_MAX_BYTES = 256 * 1024
_FRESHNESS_GIT_MAX_BYTES = 256
_FRESHNESS_TIMEOUT_SECONDS = 5.0
_FRESHNESS_HTTP_DEADLINE_SECONDS = 10.0
_FRESHNESS_HTTP_HELPER_FLAG = "--_freshness-http-helper"
_FRESHNESS_HTTP_HELPER_NETWORK_EXIT = 20
_FRESHNESS_HTTP_HELPER_INVALID_EXIT = 21
_FRESHNESS_HTTP_HELPER_OVERSIZE_EXIT = 22
_FRESHNESS_REASON_LABELS = {
    "local_identity_unavailable": "локальный отпечаток недоступен",
    "network_error": "сеть или удалённый сервис недоступны",
    "response_too_large": "ответ превысил безопасный размер",
    "invalid_response": "удалённый ответ не прошёл строгую проверку",
}


class _NoFreshnessRedirects(HTTPRedirectHandler):
    """Reject redirects before a request can leave either fixed endpoint."""

    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def _default_freshness_opener(request: Request, *, timeout: float) -> Any:
    context = ssl.create_default_context()
    default_paths = ssl.get_default_verify_paths()
    if default_paths.cafile is None and default_paths.capath is None:
        system_root = Path(Path(sys.executable).anchor)
        for ca_file in (
            system_root.joinpath("etc", "ssl", "cert.pem"),
            system_root.joinpath("private", "etc", "ssl", "cert.pem"),
        ):
            if ca_file.is_file():
                context.load_verify_locations(cafile=str(ca_file))
                break
    opener = build_opener(
        ProxyHandler({}),
        HTTPSHandler(context=context),
        _NoFreshnessRedirects(),
    )
    return opener.open(request, timeout=timeout)


_FRESHNESS_OPENER = _default_freshness_opener
_FRESHNESS_GIT_FINDER = shutil.which
PUBLIC_SOURCE_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3] / "tools" / "skillset_file_contract.py"
)
RUNTIME_NAMES = {".DS_Store"}
RUNTIME_SUFFIXES = {".pyc", ".pyo"}
SECRET_NAMES = {
    ".env",
    "credentials.json",
    "secrets.json",
    "token.json",
    "id_rsa",
    "id_ed25519",
}
SECRET_SUFFIXES = {".pem", ".p12", ".pfx", ".key"}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".toml",
    ".csv",
    ".tsv",
    ".html",
    ".js",
    ".sh",
}
BINARY_RUNTIME_SUFFIXES = {
    ".docx",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mov",
    ".mp3",
    ".mp4",
    ".otf",
    ".pdf",
    ".png",
    ".pptx",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xlsx",
    ".zip",
}
BUILTIN_TOOL_NAMES = {
    "Bash",
    "Edit",
    "Glob",
    "Grep",
    "NotebookEdit",
    "Read",
    "Task",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "Write",
    "shell",
    "shell_command",
}
MCP_PROVIDER_PREFIXES = (
    "casuslegal_",
    "firecrawl_",
    "hudoc_",
    "ksrf_neo4j_",
    "ksrf_qdrant_",
    "neo4j_",
    "qdrant_",
)
MCP_FULL_NAME = re.compile(r"^mcp__[A-Za-z0-9_-]+__[A-Za-z0-9_-]+$")
MARKDOWN_LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
CODE_TOKEN = re.compile(r"`([A-Za-z][A-Za-z0-9_.-]*)`")
TOC_HEADING = re.compile(
    r"^#{1,4}\s+(?:Содержание|Оглавление|Индекс|Table of contents)\s*$",
    re.I,
)
TOC_LINK = re.compile(r"^-\s+\[[^\]]+\]\(#[^)]+\)\s*$")
THIRD_PERSON_START = re.compile(r"^(?:Скилл|Этот скилл|Навык|The skill)\b", re.I)
TRIGGER_CUE = re.compile(
    r"(?:\bприменяется\b|\bиспользуется\b|\bкогда\b|\bперед\b|\bпосле\b|"
    r"\bпри\s+[а-яёa-z]|\bначиная\s+с\b|\buse(?:d)?\s+when\b)",
    re.I,
)

# Concatenation keeps the validator from flagging its own rule definition.
REPOSITORY_SOURCE_PREFIX = "Т" + "З/"
PROJECT_ROOT_PLACEHOLDER = "<project" + "-root>"
UNRESOLVED_COMMAND_ROOTS = (
    "<skill" + "-dir>",
    "<skill" + "-root>",
    "/" + "path/to/installed/" + "skills",
)
HARDCODED_DEFAULT_SKILL_ROOT = "~/" + ".codex/" + "skills"
PATH_HOME_CALL = re.compile(
    r"\b" + "path" + r"\s*\.\s*" + "home" + r"\s*\(\s*\)",
    re.IGNORECASE,
)
HOME_ENV_ACCESS = re.compile(
    r"(?:\$\{?"
    + "home"
    + r"\}?|\b(?:"
    + "os"
    + r"\s*\.\s*)?"
    + "environ"
    + r"\s*(?:\[\s*[\"']"
    + "home"
    + r"[\"']\s*\]|\.\s*get\s*\(\s*[\"']"
    + "home"
    + r"[\"']\s*(?:,[^)]{0,512})?\))|\b(?:"
    + "os"
    + r"\s*\.\s*)?"
    + "getenv"
    + r"\s*\(\s*[\"']"
    + "home"
    + r"[\"']\s*(?:,[^)]{0,512})?\))",
    re.IGNORECASE,
)
EXPANDUSER_CALL = re.compile(
    r"(?:\b(?:"
    + "os"
    + r"\s*\.\s*"
    + "path"
    + r"\s*\.\s*)?"
    + "expand"
    + "user"
    + r"\s*\(|\.\s*"
    + "expand"
    + "user"
    + r"\s*\()",
    re.IGNORECASE,
)
DOCUMENTS_KS_PARSER = re.compile(
    "documents" + r"[\s/\"'()]*" + "ks_" + "parser" + r"(?![\w-])",
    re.IGNORECASE,
)
GIT_ROOT_DISCOVERY_PARTS = ("rev" + "-parse", "--show" + "-toplevel")
GIT_COMMAND_TOKEN = re.compile(r"(?<![\w-])git(?![\w-])", re.IGNORECASE)
HUDOC_REPOSITORY_ENV_NAME = "hudoc_" + "ks_parser_repo"
HUDOC_REPOSITORY_BINDING = re.compile(
    r"\s*(?:,\s*)?(?:[\"']?\$\{?"
    + re.escape(HUDOC_REPOSITORY_ENV_NAME)
    + r"\}?[\"']?|\b"
    + "os"
    + r"\s*\.\s*(?:"
    + "environ"
    + r"\s*\[\s*[\"']"
    + re.escape(HUDOC_REPOSITORY_ENV_NAME)
    + r"[\"']\s*\]|"
    + "getenv"
    + r"\s*\(\s*[\"']"
    + re.escape(HUDOC_REPOSITORY_ENV_NAME)
    + r"[\"']\s*\)))",
    re.IGNORECASE,
)
HTTP_URL_PATTERN = re.compile(
    r"(?<![\w+.\-:])https?://[^\s`\"'<>()]+",
    re.IGNORECASE,
)
RUNTIME_USER_HOME_PATTERNS = (
    re.compile(
        "/" + "U" + r"sers/[^/\s`\"']+(?:/[^\s`\"']+)?",
        re.IGNORECASE,
    ),
    re.compile(
        "/" + "h" + r"ome/[^/\s`\"']+(?:/[^\s`\"']+)?",
        re.IGNORECASE,
    ),
    re.compile(
        "/"
        + "r"
        + r"oot(?=/|$|[\s`\"'<>()\]};,.!?])(?:/[^\s`\"']+)?",
        re.IGNORECASE,
    ),
)
PRIVATE_KEY_MARKER = re.compile(
    "BEGIN " + r"(?:RSA |OPENSSH |EC )?PRIVATE KEY"
)
TOKEN_LITERAL = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,})"
)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password|passwd)\b\s*[:=]\s*"
    r"[\"']?([^\s\"']{12,})"
)
SAFE_SECRET_WORDS = ("example", "placeholder", "redacted", "replace", "dummy", "test")


class _FreshnessLookupError(RuntimeError):
    """A bounded public reason for an optional freshness lookup failure."""

    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


if yaml is not None:
    class _UniqueKeyLoader(yaml.SafeLoader):
        pass


    def _construct_unique_mapping(
        loader: Any, node: Any, deep: bool = False
    ) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"duplicate key: {key}",
                    key_node.start_mark,
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping


    _UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_unique_mapping,
    )


def _finding(
    severity: str,
    code: str,
    message: str,
    *,
    package: str | None = None,
    path: str | None = None,
    line: int | None = None,
    evidence: Any | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if package is not None:
        item["package"] = package
    if path is not None:
        item["path"] = path
    if line is not None:
        item["line"] = line
    if evidence is not None:
        item["evidence"] = evidence
    return item


def _is_complete_canonical_scope(package_names: Sequence[str]) -> bool:
    packages = tuple(package_names)
    return (
        len(packages) == len(CANONICAL_KSRF_PACKAGES)
        and len(packages) == len(set(packages))
        and set(packages) == set(CANONICAL_KSRF_PACKAGES)
    )


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _load_yaml(text: str) -> Any:
    if yaml is None:
        raise RuntimeError("Для строгой YAML-проверки нужен PyYAML; установка автоматически не выполняется.")
    return yaml.load(text, Loader=_UniqueKeyLoader)


def _frontmatter(text: str) -> tuple[Mapping[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md должен начинаться строкой ---.")
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        raise ValueError("Не найдена закрывающая строка --- во frontmatter.")
    payload = _load_yaml("\n".join(lines[1:closing]))
    if not isinstance(payload, Mapping):
        raise ValueError("YAML frontmatter должен быть объектом.")
    return payload, "\n".join(lines[closing + 1 :])


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"duplicate key: {key}")
        payload[key] = value
    return payload


def _reject_nonfinite_json_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {token}")


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )


def _declared_tool_values(payload: Any, *, parent_key: str = "") -> Iterable[str]:
    if isinstance(payload, Mapping):
        for raw_key, value in payload.items():
            key = str(raw_key).lower().replace("-", "_")
            if key in {"tools", "allowed_tools", "mcp_tools"}:
                if isinstance(value, str):
                    yield from value.replace(",", " ").split()
                elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                    for item in value:
                        if isinstance(item, str):
                            yield item
            yield from _declared_tool_values(value, parent_key=key)
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        for item in payload:
            yield from _declared_tool_values(item, parent_key=parent_key)


def _looks_like_unqualified_mcp(name: str) -> bool:
    token = name.strip().split("(", 1)[0]
    if not token or token in BUILTIN_TOOL_NAMES or MCP_FULL_NAME.fullmatch(token):
        return False
    lowered = token.lower()
    return lowered.startswith(MCP_PROVIDER_PREFIXES) or lowered.startswith("mcp_")


def _mcp_tokens_declared_in_markdown(text: str) -> Iterable[tuple[str, int]]:
    lines = text.splitlines()
    mcp_document = any(
        re.match(r"^#{1,4}\s+.*\bMCP\b", line, re.I) for line in lines
    )
    if not mcp_document:
        return
    for line_number, line in enumerate(lines, start=1):
        for token in CODE_TOKEN.findall(line):
            if _looks_like_unqualified_mcp(token):
                yield token, line_number


def _validate_mcp_declarations(
    findings: list[dict[str, Any]],
    payload: Any,
    *,
    package: str,
    relative_path: str,
) -> None:
    seen: set[str] = set()
    for token in _declared_tool_values(payload):
        normalized = token.strip().split("(", 1)[0]
        if normalized in seen:
            continue
        seen.add(normalized)
        if _looks_like_unqualified_mcp(normalized):
            findings.append(
                _finding(
                    "error",
                    "MCP_TOOL_NOT_FULLY_QUALIFIED",
                    f"MCP-инструмент {normalized} должен быть указан как mcp__server__tool.",
                    package=package,
                    path=relative_path,
                    evidence=normalized,
                )
            )


def _validate_skill_file(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> tuple[Mapping[str, Any] | None, str]:
    package = package_dir.name
    skill_file = package_dir / "SKILL.md"
    relative_path = _relative(skill_file, skills_root)
    if not skill_file.is_file():
        findings.append(
            _finding(
                "error",
                "SKILL_FILE_MISSING",
                "В пакете отсутствует SKILL.md.",
                package=package,
                path=relative_path,
            )
        )
        return None, ""
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        findings.append(
            _finding(
                "error",
                "SKILL_FILE_UNREADABLE",
                f"SKILL.md не читается как UTF-8: {exc}",
                package=package,
                path=relative_path,
            )
        )
        return None, ""
    line_count = len(text.splitlines())
    if line_count > MAX_SKILL_LINES:
        findings.append(
            _finding(
                "error",
                "SKILL_TOO_LONG",
                f"SKILL.md содержит {line_count} строк; разрешено не более {MAX_SKILL_LINES}.",
                package=package,
                path=relative_path,
                evidence={"lines": line_count, "limit": MAX_SKILL_LINES},
            )
        )
    try:
        frontmatter, body = _frontmatter(text)
    except Exception as exc:
        findings.append(
            _finding(
                "error",
                "FRONTMATTER_INVALID",
                f"Некорректный YAML frontmatter: {exc}",
                package=package,
                path=relative_path,
            )
        )
        return None, text
    name = frontmatter.get("name")
    if name != package:
        findings.append(
            _finding(
                "error",
                "FRONTMATTER_NAME_MISMATCH",
                f"Поле name должно точно совпадать с именем пакета {package}.",
                package=package,
                path=relative_path,
                evidence={"actual": name, "expected": package},
            )
        )
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        findings.append(
            _finding(
                "error",
                "DESCRIPTION_MISSING",
                "Во frontmatter отсутствует непустой description.",
                package=package,
                path=relative_path,
            )
        )
    else:
        normalized = " ".join(description.split())
        if len(normalized) > 1024:
            findings.append(
                _finding(
                    "error",
                    "DESCRIPTION_TOO_LONG",
                    "Description превышает 1024 символа.",
                    package=package,
                    path=relative_path,
                    evidence={"characters": len(normalized)},
                )
            )
        if not THIRD_PERSON_START.search(normalized):
            findings.append(
                _finding(
                    "error",
                    "DESCRIPTION_NOT_THIRD_PERSON",
                    "Description должен от третьего лица описывать, что делает скилл.",
                    package=package,
                    path=relative_path,
                )
            )
        generic = bool(re.search(r"(?:для всего|на все случаи|anything|everything)", normalized, re.I))
        if len(normalized) < 90 or not TRIGGER_CUE.search(normalized) or generic:
            findings.append(
                _finding(
                    "error",
                    "DESCRIPTION_TRIGGER_NOT_PRECISE",
                    "Description должен точно объяснять предмет и контекст срабатывания скилла.",
                    package=package,
                    path=relative_path,
                )
            )
    _validate_mcp_declarations(
        findings,
        frontmatter,
        package=package,
        relative_path=relative_path,
    )
    for token, line_number in _mcp_tokens_declared_in_markdown(text):
        findings.append(
            _finding(
                "error",
                "MCP_TOOL_NOT_FULLY_QUALIFIED",
                f"MCP-инструмент {token} должен быть указан как mcp__server__tool.",
                package=package,
                path=relative_path,
                line=line_number,
                evidence=token,
            )
        )
    return frontmatter, body


def _validate_agent_metadata(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    package = package_dir.name
    path = package_dir / "agents" / "openai.yaml"
    relative_path = _relative(path, skills_root)
    if not path.is_file():
        findings.append(
            _finding(
                "error",
                "AGENT_METADATA_MISSING",
                "Отсутствует agents/openai.yaml.",
                package=package,
                path=relative_path,
            )
        )
        return
    try:
        payload = _load_yaml(path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append(
            _finding(
                "error",
                "AGENT_METADATA_INVALID",
                f"Некорректный agents/openai.yaml: {exc}",
                package=package,
                path=relative_path,
            )
        )
        return
    if not isinstance(payload, Mapping):
        findings.append(
            _finding(
                "error",
                "AGENT_METADATA_INVALID",
                "agents/openai.yaml должен содержать YAML-объект.",
                package=package,
                path=relative_path,
            )
        )
        return
    interface = payload.get("interface")
    required = ("display_name", "short_description", "default_prompt")
    if not isinstance(interface, Mapping) or any(
        not isinstance(interface.get(key), str) or not str(interface.get(key)).strip()
        for key in required
    ):
        findings.append(
            _finding(
                "error",
                "AGENT_INTERFACE_INCOMPLETE",
                "interface должен содержать display_name, short_description и default_prompt.",
                package=package,
                path=relative_path,
            )
        )
    else:
        prompt = str(interface["default_prompt"])
        exact_reference = f"${package}"
        declared_references = set(re.findall(r"\$ksrf-[a-z0-9-]+", prompt))
        if exact_reference not in declared_references or declared_references != {exact_reference}:
            findings.append(
                _finding(
                    "error",
                    "AGENT_SKILL_REFERENCE_MISMATCH",
                    f"default_prompt должен ссылаться ровно на {exact_reference}.",
                    package=package,
                    path=relative_path,
                    evidence=sorted(declared_references),
                )
            )
        if len(str(interface["short_description"])) > 160:
            findings.append(
                _finding(
                    "error",
                    "AGENT_SHORT_DESCRIPTION_TOO_LONG",
                    "short_description превышает 160 символов.",
                    package=package,
                    path=relative_path,
                )
            )
    policy = payload.get("policy")
    if policy is not None and (
        not isinstance(policy, Mapping)
        or (
            "allow_implicit_invocation" in policy
            and not isinstance(policy["allow_implicit_invocation"], bool)
        )
    ):
        findings.append(
            _finding(
                "error",
                "AGENT_INVOCATION_POLICY_INVALID",
                "allow_implicit_invocation должен быть логическим значением.",
                package=package,
                path=relative_path,
            )
        )
    _validate_mcp_declarations(
        findings,
        payload,
        package=package,
        relative_path=relative_path,
    )


def _validate_behavioral_evals(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    package = package_dir.name
    path = package_dir / "evals" / "evals.json"
    relative_path = _relative(path, skills_root)
    if not path.is_file():
        findings.append(
            _finding(
                "error",
                "BEHAVIORAL_EVALS_MISSING",
                "Отсутствует evals/evals.json.",
                package=package,
                path=relative_path,
            )
        )
        return
    try:
        payload = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "BEHAVIORAL_EVALS_INVALID",
                f"Некорректный evals/evals.json: {exc}",
                package=package,
                path=relative_path,
            )
        )
        return
    if not isinstance(payload, Mapping) or payload.get("skill_name") != package:
        findings.append(
            _finding(
                "error",
                "BEHAVIORAL_EVAL_SKILL_MISMATCH",
                "skill_name в evals/evals.json должен совпадать с пакетом.",
                package=package,
                path=relative_path,
            )
        )
    evals = payload.get("evals") if isinstance(payload, Mapping) else None
    if not isinstance(evals, list) or len(evals) < MIN_BEHAVIORAL_EVALS:
        findings.append(
            _finding(
                "error",
                "BEHAVIORAL_EVALS_INSUFFICIENT",
                f"Нужно не менее {MIN_BEHAVIORAL_EVALS} behavioral evals.",
                package=package,
                path=relative_path,
                evidence={"actual": len(evals) if isinstance(evals, list) else 0},
            )
        )
        return
    identifiers: set[Any] = set()
    for index, item in enumerate(evals):
        valid = isinstance(item, Mapping)
        if valid:
            identifier = item.get("id")
            valid = (
                identifier is not None
                and identifier not in identifiers
                and isinstance(item.get("prompt"), str)
                and bool(str(item.get("prompt")).strip())
                and isinstance(item.get("expected_output"), str)
                and bool(str(item.get("expected_output")).strip())
                and isinstance(item.get("files", []), list)
            )
            identifiers.add(identifier)
        if not valid:
            findings.append(
                _finding(
                    "error",
                    "BEHAVIORAL_EVAL_INVALID",
                    f"Behavioral eval с индексом {index} неполон или имеет повторный id.",
                    package=package,
                    path=relative_path,
                )
            )


def _validate_trigger_evals(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    package = package_dir.name
    path = package_dir / "evals" / "trigger-evals.json"
    relative_path = _relative(path, skills_root)
    if not path.is_file():
        findings.append(
            _finding(
                "error",
                "TRIGGER_EVALS_MISSING",
                "Отсутствует evals/trigger-evals.json.",
                package=package,
                path=relative_path,
            )
        )
        return
    try:
        payload = _read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "TRIGGER_EVALS_INVALID",
                f"Некорректный trigger-evals.json: {exc}",
                package=package,
                path=relative_path,
            )
        )
        return
    if isinstance(payload, Mapping):
        if "skill_name" in payload and payload["skill_name"] != package:
            findings.append(
                _finding(
                    "error",
                    "TRIGGER_EVAL_SKILL_MISMATCH",
                    "skill_name в trigger evals должен совпадать с пакетом.",
                    package=package,
                    path=relative_path,
                )
            )
        cases = payload.get("evals", payload.get("queries"))
    else:
        cases = payload
    if not isinstance(cases, list):
        findings.append(
            _finding(
                "error",
                "TRIGGER_EVALS_INVALID",
                "Trigger evals должны быть списком либо объектом с evals/queries.",
                package=package,
                path=relative_path,
            )
        )
        return
    polarities: set[bool] = set()
    queries: set[str] = set()
    for index, item in enumerate(cases):
        valid = (
            isinstance(item, Mapping)
            and isinstance(item.get("query"), str)
            and bool(str(item.get("query")).strip())
            and isinstance(item.get("should_trigger"), bool)
        )
        if not valid:
            findings.append(
                _finding(
                    "error",
                    "TRIGGER_EVAL_INVALID",
                    f"Trigger eval с индексом {index} должен иметь query и should_trigger boolean.",
                    package=package,
                    path=relative_path,
                )
            )
            continue
        query = " ".join(str(item["query"]).split())
        if query in queries:
            findings.append(
                _finding(
                    "error",
                    "TRIGGER_EVAL_DUPLICATE",
                    f"Повторный trigger query с индексом {index}.",
                    package=package,
                    path=relative_path,
                )
            )
        queries.add(query)
        polarities.add(bool(item["should_trigger"]))
    if polarities != {False, True}:
        findings.append(
            _finding(
                "error",
                "TRIGGER_EVAL_POLARITY_MISSING",
                "Нужны как положительные, так и отрицательные trigger evals.",
                package=package,
                path=relative_path,
                evidence={"present": sorted(polarities)},
            )
        )


def _markdown_target(raw: str) -> str | None:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif re.search(r"\s+[\"']", target):
        target = re.split(r"\s+[\"']", target, maxsplit=1)[0]
    if not target or target.startswith("#"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    return unquote(parsed.path)


def _validate_markdown_links(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    package = package_dir.name
    root_resolved = skills_root.resolve()
    for markdown in sorted(package_dir.rglob("*.md")):
        if any(part in RUNTIME_PARTS for part in markdown.parts):
            continue
        relative_path = _relative(markdown, skills_root)
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(
                _finding(
                    "error",
                    "MARKDOWN_UNREADABLE",
                    f"Markdown не читается как UTF-8: {exc}",
                    package=package,
                    path=relative_path,
                )
            )
            continue
        for raw_target in MARKDOWN_LINK.findall(text):
            target = _markdown_target(raw_target)
            if target is None:
                continue
            resolved = (markdown.parent / target).resolve()
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                findings.append(
                    _finding(
                        "error",
                        "MARKDOWN_LINK_ESCAPES_SKILLSET",
                        f"Относительная ссылка выходит за пределы skillset: {raw_target}",
                        package=package,
                        path=relative_path,
                    )
                )
                continue
            if not resolved.exists():
                findings.append(
                    _finding(
                        "error",
                        "BROKEN_MARKDOWN_LINK",
                        f"Относительная ссылка не разрешается: {raw_target}",
                        package=package,
                        path=relative_path,
                    )
                )


def _validate_reference_tocs(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    package = package_dir.name
    reference_root = package_dir / "references"
    if not reference_root.is_dir():
        return
    for path in sorted(reference_root.rglob("*.md")):
        relative_path = _relative(path, skills_root)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        if len(lines) <= LONG_REFERENCE_LINES:
            continue
        early = lines[:EARLY_TOC_LAST_LINE]
        heading_positions = [index for index, line in enumerate(early) if TOC_HEADING.match(line.strip())]
        toc_ok = False
        for position in heading_positions:
            if any(TOC_LINK.match(line.strip()) for line in early[position + 1 :]):
                toc_ok = True
                break
        if not toc_ok:
            findings.append(
                _finding(
                    "error",
                    "REFERENCE_TOC_MISSING",
                    (
                        f"Reference содержит {len(lines)} строк, но в первых "
                        f"{EARLY_TOC_LAST_LINE} строках нет TOC с внутренней ссылкой."
                    ),
                    package=package,
                    path=relative_path,
                    evidence={"lines": len(lines)},
                )
            )


def _validate_application_evidence_contract(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    """Keep the normative preservation vocabulary aligned with its JSON Schema."""

    package = package_dir.name
    if package != "ksrf-complaint-cycle":
        return

    schema_path = (
        package_dir
        / "schemas"
        / "ksrf_filing"
        / "application-evidence.schema.json"
    )
    reference_path = package_dir / "references" / "implicit-application-gate.md"

    try:
        schema = _read_json(schema_path)
        expected = schema["properties"]["preservation_exhaustion"]["enum"]
        if (
            not isinstance(expected, list)
            or not expected
            or any(not isinstance(value, str) or not value for value in expected)
            or len(expected) != len(set(expected))
        ):
            raise ValueError("preservation_exhaustion.enum must be a unique non-empty string list")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "APPLICATION_EVIDENCE_CONTRACT_INVALID",
                f"Не удалось прочитать canonical preservation_exhaustion enum: {exc}",
                package=package,
                path=_relative(schema_path, skills_root),
            )
        )
        return

    try:
        lines = reference_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        findings.append(
            _finding(
                "error",
                "APPLICATION_EVIDENCE_CONTRACT_INVALID",
                f"Не удалось прочитать normative application-evidence reference: {exc}",
                package=package,
                path=_relative(reference_path, skills_root),
            )
        )
        return

    heading_positions = [
        index
        for index, line in enumerate(lines)
        if line.strip() == "### `preservation_exhaustion`"
    ]
    if len(heading_positions) != 1:
        findings.append(
            _finding(
                "error",
                "APPLICATION_EVIDENCE_CONTRACT_INVALID",
                "Reference должен содержать ровно одну секцию ### `preservation_exhaustion`.",
                package=package,
                path=_relative(reference_path, skills_root),
                evidence={"heading_count": len(heading_positions)},
            )
        )
        return

    actual: list[str] = []
    for line in lines[heading_positions[0] + 1 :]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break
        if not stripped.startswith("-"):
            continue
        actual.extend(CODE_TOKEN.findall(stripped))

    if actual != expected:
        findings.append(
            _finding(
                "error",
                "APPLICATION_EVIDENCE_ENUM_DRIFT",
                (
                    "Normative preservation_exhaustion list расходится "
                    "с canonical application-evidence schema."
                ),
                package=package,
                path=_relative(reference_path, skills_root),
                evidence={"expected": expected, "actual": actual},
            )
        )


def _validate_argument_graph_contract(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    """Reject graph records that present unshipped automation as runtime tools."""

    if package_dir.name != "ksrf-argument-patterns":
        return
    graph_path = package_dir / "references" / "constitutional_graph.json"
    if not graph_path.exists():
        return

    try:
        graph = _read_json(graph_path)
        nodes = graph["nodes"]
        edges = graph["edges"]
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise ValueError("nodes and edges must be lists")
        if any(not isinstance(node, dict) for node in nodes):
            raise ValueError("every node must be an object")
        if any(not isinstance(edge, dict) for edge in edges):
            raise ValueError("every edge must be an object")
        node_ids: list[str] = []
        for index, node in enumerate(nodes):
            node_id = node.get("id")
            node_kind = node.get("kind")
            if not isinstance(node_id, str) or not node_id.strip():
                raise ValueError(f"node[{index}].id must be a non-empty string")
            if not isinstance(node_kind, str) or not node_kind.strip():
                raise ValueError(f"node[{index}].kind must be a non-empty string")
            node_ids.append(node_id)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node ids must be unique")
        node_id_set = set(node_ids)
        for index, edge in enumerate(edges):
            for field in ("from", "to", "type"):
                value = edge.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"edge[{index}].{field} must be a non-empty string"
                    )
            if edge["from"] not in node_id_set or edge["to"] not in node_id_set:
                raise ValueError(f"edge[{index}] endpoints must reference existing nodes")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "ARGUMENT_GRAPH_CONTRACT_INVALID",
                f"Не удалось проверить пользовательский граф аргументации: {exc}",
                package=package_dir.name,
                path=_relative(graph_path, skills_root),
            )
        )
        return

    automation_kind_ids = [
        str(node.get("id", ""))
        for node in nodes
        if node.get("kind") == "automation_hook"
    ]
    tool_node_ids = [
        str(node.get("id", ""))
        for node in nodes
        if str(node.get("id", "")).startswith("tool:")
    ]
    supported_edge_indexes = [
        index for index, edge in enumerate(edges) if edge.get("type") == "supported_by"
    ]
    tool_endpoint_indexes = [
        index
        for index, edge in enumerate(edges)
        if str(edge.get("from", "")).startswith("tool:")
        or str(edge.get("to", "")).startswith("tool:")
    ]
    if any(
        (
            automation_kind_ids,
            tool_node_ids,
            supported_edge_indexes,
            tool_endpoint_indexes,
        )
    ):
        findings.append(
            _finding(
                "error",
                "UNSHIPPED_AUTOMATION_IN_RUNTIME_GRAPH",
                (
                    "Пользовательский граф выдаёт нереализованную автоматизацию "
                    "за доступные инструменты или связи."
                ),
                package=package_dir.name,
                path=_relative(graph_path, skills_root),
                evidence={
                    "automation_kind_count": len(automation_kind_ids),
                    "tool_node_count": len(tool_node_ids),
                    "supported_by_edge_count": len(supported_edge_indexes),
                    "tool_endpoint_edge_count": len(tool_endpoint_indexes),
                    "examples": (
                        automation_kind_ids[:3]
                        + tool_node_ids[:3]
                        + [f"edge:{index}" for index in supported_edge_indexes[:2]]
                        + [f"edge:{index}" for index in tool_endpoint_indexes[:2]]
                    ),
                },
            )
        )


def _validate_authority_corpus_contract(
    findings: list[dict[str, Any]],
    package_dir: Path,
    skills_root: Path,
    *,
    expected_semantic_sha256: str = AUTHORITY_CORPUS_SEMANTIC_SHA256,
) -> None:
    """Validate the shipped authority corpus without exposing maintainer metadata."""

    if package_dir.name != "ksrf-argument-patterns":
        return
    corpus_path = (
        package_dir
        / "references"
        / "constitutionalist-authority-corpus.json"
    )
    if not corpus_path.exists():
        findings.append(
            _finding(
                "error",
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
                "Обязательный пользовательский корпус авторитетов отсутствует.",
                package=package_dir.name,
                path=_relative(corpus_path, skills_root),
            )
        )
        return

    try:
        raw_payload = corpus_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
                f"Не удалось проверить пользовательский корпус авторитетов: {exc}",
                package=package_dir.name,
                path=_relative(corpus_path, skills_root),
            )
        )
        return

    raw_retired_queue = '"next_extraction_wave"' in raw_payload
    raw_local_hint = '"local_source_hint"' in raw_payload
    raw_local_coordinate = REPOSITORY_SOURCE_PREFIX in raw_payload
    if raw_retired_queue or raw_local_hint or raw_local_coordinate:
        findings.append(
            _finding(
                "error",
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
                (
                    "Пользовательский корпус содержит служебную очередь или "
                    "локальные координаты, недоступные после установки."
                ),
                package=package_dir.name,
                path=_relative(corpus_path, skills_root),
                evidence={
                    "retired_queue_count": int(raw_retired_queue),
                    "local_source_hint_count": int(raw_local_hint),
                    "local_coordinate_present": raw_local_coordinate,
                },
            )
        )
        return

    try:
        payload = json.loads(
            raw_payload,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
                f"Не удалось проверить пользовательский корпус авторитетов: {exc}",
                package=package_dir.name,
                path=_relative(corpus_path, skills_root),
            )
        )
        return

    sources = payload.get("sources") if isinstance(payload, dict) else None
    retired_queue_count = 0
    local_hint_count = 0
    pending: list[Any] = [payload]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            retired_queue_count += "next_extraction_wave" in item
            local_hint_count += "local_source_hint" in item
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    has_retired_queue = retired_queue_count > 0
    has_local_coordinate = REPOSITORY_SOURCE_PREFIX in json.dumps(
        payload,
        ensure_ascii=False,
    )
    if has_retired_queue or local_hint_count or has_local_coordinate:
        findings.append(
            _finding(
                "error",
                "AUTHORITY_CORPUS_MAINTAINER_METADATA_PRESENT",
                (
                    "Пользовательский корпус содержит служебную очередь или "
                    "локальные координаты, недоступные после установки."
                ),
                package=package_dir.name,
                path=_relative(corpus_path, skills_root),
                evidence={
                    "retired_queue_count": retired_queue_count,
                    "local_source_hint_count": local_hint_count,
                    "local_coordinate_present": has_local_coordinate,
                },
            )
        )
        return

    try:
        if not isinstance(payload, dict):
            raise ValueError("root must be an object")
        if payload.get("schema_version") != "2.0":
            raise ValueError("schema_version must be 2.0")
        for field in ("as_of", "purpose", "warning"):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        if payload.get("warning") != AUTHORITY_CORPUS_WARNING:
            raise ValueError("warning must preserve the canonical non-promotion boundary")
        status_legend = payload.get("status_legend")
        if status_legend != AUTHORITY_CORPUS_STATUS_LABELS:
            raise ValueError("status_legend must preserve the canonical status boundaries")
        route_legend = payload.get("route_legend")
        if route_legend != AUTHORITY_CORPUS_ROUTE_LABELS:
            raise ValueError("route_legend must preserve the canonical route boundaries")

        def public_http_url(value: Any) -> bool:
            if (
                not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
                or re.search(r"[\x00-\x20\x7f]", value) is not None
            ):
                return False
            try:
                parsed = urlsplit(value)
                hostname = parsed.hostname
                port = parsed.port
            except ValueError:
                return False
            if (
                parsed.scheme not in {"http", "https"}
                or not hostname
                or "%" in parsed.netloc
                or "\\" in parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or port == 0
            ):
                return False
            normalized_host = hostname.rstrip(".").casefold()
            if normalized_host == "localhost" or normalized_host.endswith(
                ".localhost"
            ):
                return False
            try:
                address = ip_address(normalized_host)
            except ValueError:
                if parsed.netloc.startswith("["):
                    return False
                try:
                    ascii_host = normalized_host.encode("idna").decode("ascii")
                except UnicodeError:
                    return False
                labels = ascii_host.split(".")
                if (
                    len(ascii_host) > 253
                    or len(labels) < 2
                    or ascii_host == "localhost"
                    or ascii_host.endswith(".localhost")
                    or any(
                        not label
                        or len(label) > 63
                        or DNS_LABEL.fullmatch(label) is None
                        for label in labels
                    )
                    or ascii_host.endswith(NON_PUBLIC_DNS_SUFFIXES)
                    or re.fullmatch(
                        r"(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+))*",
                        ascii_host,
                    )
                ):
                    return False
                return True
            return address.is_global

        def runtime_skill_reference_exists(value: str) -> bool:
            references = [item.strip() for item in value.split(";")]
            if not references or any(not item for item in references):
                return False
            for reference in references:
                if reference in CANONICAL_KSRF_PACKAGES:
                    if not (skills_root / reference / "SKILL.md").is_file():
                        return False
                    continue
                relative = Path(reference)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or relative.suffix.casefold() != ".md"
                ):
                    return False
                candidates = (
                    package_dir / "references" / relative,
                    *(
                        skills_root / package / "references" / relative
                        for package in CANONICAL_KSRF_PACKAGES
                    ),
                )
                if not any(candidate.is_file() for candidate in candidates):
                    return False
            return True

        if not isinstance(sources, list) or not sources:
            raise ValueError("sources must be a non-empty list")
        allowed_source_keys = {"kind", "label", "coverage", "url"}
        source_kinds: list[str] = []
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                raise ValueError(f"source[{index}] must be an object")
            if set(source) - allowed_source_keys:
                raise ValueError(f"source[{index}] has unsupported fields")
            for field in ("kind", "label", "coverage"):
                value = source.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"source[{index}].{field} must be a non-empty string"
                    )
            source_kinds.append(source["kind"])
            url = source.get("url")
            if url is not None and not public_http_url(url):
                raise ValueError(f"source[{index}].url must be a public HTTP(S) URL")
        if set(source_kinds) != AUTHORITY_CORPUS_DECLARED_SOURCES:
            raise ValueError("sources must preserve the canonical source-kind set")
        if len(source_kinds) != len(set(source_kinds)):
            raise ValueError("source kinds must be unique")
        declared_source_kinds = set(source_kinds)

        authorities = payload.get("authorities")
        if not isinstance(authorities, list) or not authorities:
            raise ValueError("authorities must be a non-empty list")
        authority_ids: list[str] = []
        identity_keys: list[str] = []
        canonical_names: list[str] = []
        works_total = 0
        status_counts: Counter[str] = Counter()
        source_people_counts: Counter[str] = Counter()
        route_counts: Counter[str] = Counter()
        needs_review_total = 0
        for index, authority in enumerate(authorities):
            if not isinstance(authority, dict):
                raise ValueError(f"authority[{index}] must be an object")
            for field in ("id", "identity_key", "canonical_name", "status"):
                value = authority.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(
                        f"authority[{index}].{field} must be a non-empty string"
                    )
            authority_ids.append(authority["id"])
            identity_keys.append(authority["identity_key"])
            canonical_names.append(authority["canonical_name"])
            status: str = authority["status"]
            if status not in AUTHORITY_CORPUS_STATUSES:
                raise ValueError(f"authority[{index}].status is unsupported")
            if authority.get("status_label") != AUTHORITY_CORPUS_STATUS_LABELS[status]:
                raise ValueError(
                    f"authority[{index}].status_label contradicts status_legend"
                )
            method_cards = authority.get("method_cards")
            if not isinstance(method_cards, list):
                raise ValueError(f"authority[{index}].method_cards must be a list")
            for card_index, card in enumerate(method_cards):
                if not isinstance(card, dict):
                    raise ValueError(
                        f"authority[{index}].method_cards[{card_index}] must be an object"
                    )
                for field in ("method", "usable_for", "guardrail", "skill_reference"):
                    value = card.get(field)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            f"authority[{index}].method_cards[{card_index}].{field} "
                            "must be a non-empty string"
                        )
                if not runtime_skill_reference_exists(card["skill_reference"]):
                    raise ValueError(
                        f"authority[{index}].method_cards[{card_index}]."
                        "skill_reference must resolve in the installed skillset"
                    )
            full_text_sources = authority.get("full_text_sources")
            if not isinstance(full_text_sources, list) or any(
                not isinstance(source, str) or not source.strip()
                for source in full_text_sources
            ):
                raise ValueError(
                    f"authority[{index}].full_text_sources must contain strings"
                )
            for field in (
                "method_integrated",
                "needs_identity_or_method_review",
            ):
                if not isinstance(authority.get(field), bool):
                    raise ValueError(f"authority[{index}].{field} must be boolean")
            routes = authority.get("routes")
            if not isinstance(routes, list) or any(
                not isinstance(route, str)
                or not route.strip()
                or route not in AUTHORITY_CORPUS_ROUTE_LABELS
                for route in routes
            ):
                raise ValueError(
                    f"authority[{index}].routes must use declared route strings"
                )
            if len(routes) != len(set(routes)):
                raise ValueError(f"authority[{index}].routes must be unique")
            source_counts = authority.get("source_counts")
            if not isinstance(source_counts, dict) or not source_counts:
                raise ValueError(
                    f"authority[{index}].source_counts must be a non-empty object"
                )
            if any(
                not isinstance(source, str)
                or not source.strip()
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count < 1
                for source, count in source_counts.items()
            ):
                raise ValueError(
                    f"authority[{index}].source_counts entries are invalid"
                )
            allowed_source_counts = (
                AUTHORITY_CORPUS_DECLARED_SOURCES
                | AUTHORITY_CORPUS_INTERNAL_SOURCES
            )
            if not set(source_counts).issubset(allowed_source_counts):
                raise ValueError(
                    f"authority[{index}].source_counts contains an unknown source"
                )

            works = authority.get("works")
            if not isinstance(works, list):
                raise ValueError(f"authority[{index}].works must be a list")
            curated_work_titles: set[str] = set()
            for work_index, work in enumerate(works):
                if not isinstance(work, dict):
                    raise ValueError(
                        f"authority[{index}].works[{work_index}] must be an object"
                    )
                for field in ("source", "title"):
                    value = work.get(field)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(
                            f"authority[{index}].works[{work_index}].{field} "
                            "must be a non-empty string"
                        )
                if work["source"] not in source_counts:
                    raise ValueError(
                        f"authority[{index}].works[{work_index}].source "
                        "must be represented in source_counts"
                    )
                if work["source"] not in declared_source_kinds:
                    raise ValueError(
                        f"authority[{index}].works[{work_index}].source "
                        "must be declared in top-level sources"
                    )
                if work["source"] == "curated_method":
                    curated_work_titles.add(work["title"])
                work_url = work.get("url")
                if work_url is not None and not public_http_url(work_url):
                    raise ValueError(
                        f"authority[{index}].works[{work_index}].url "
                        "must be a public HTTP(S) URL"
                    )

            if len(full_text_sources) != len(set(full_text_sources)):
                raise ValueError(
                    f"authority[{index}].full_text_sources must be unique"
                )
            if not set(full_text_sources).issubset(curated_work_titles):
                raise ValueError(
                    f"authority[{index}].full_text_sources must resolve to "
                    "curated_method works"
                )
            local_full_text_count = source_counts.get("local_full_text", 0)
            if local_full_text_count != len(full_text_sources):
                raise ValueError(
                    f"authority[{index}].local_full_text count must match "
                    "full_text_sources"
                )
            has_curated_method = "curated_method" in source_counts
            if bool(method_cards or full_text_sources) != has_curated_method:
                raise ValueError(
                    f"authority[{index}].curated_method must match "
                    "method cards or full-text provenance"
                )
            if method_cards and not full_text_sources:
                raise ValueError(
                    f"authority[{index}].method_cards require full-text provenance"
                )

            academic_sources = (
                set(source_counts) & AUTHORITY_CORPUS_ACADEMIC_SOURCES
            )
            if method_cards:
                expected_status = "method_integrated"
            elif full_text_sources:
                expected_status = "full_text_available"
            elif len(academic_sources) >= 2:
                expected_status = "triangulated_academic"
            elif academic_sources & {"sko_index", "mp_index"}:
                expected_status = "academic_indexed"
            elif "blokhin_bibliography" in academic_sources:
                expected_status = "bibliographic_lead"
            else:
                expected_status = "discovery_only"
            if status != expected_status:
                raise ValueError(
                    f"authority[{index}].status contradicts source and method evidence"
                )
            if authority["method_integrated"] != bool(method_cards):
                raise ValueError(
                    f"authority[{index}].method_integrated contradicts method_cards"
                )
            authoritative_sources = set(source_counts) - (
                AUTHORITY_CORPUS_NON_AUTHORITATIVE_SOURCES
            )
            expected_needs_review = (
                expected_status in {"academic_indexed", "discovery_only"}
                and len(authoritative_sources) < 2
            )
            if (
                authority["needs_identity_or_method_review"]
                != expected_needs_review
            ):
                raise ValueError(
                    f"authority[{index}].needs_identity_or_method_review "
                    "contradicts source evidence"
                )
            works_total += len(works)
            status_counts[expected_status] += 1
            source_people_counts.update(source_counts.keys())
            route_counts.update(routes)
            needs_review_total += expected_needs_review
        if len(authority_ids) != len(set(authority_ids)):
            raise ValueError("authority ids must be unique")
        if len(identity_keys) != len(set(identity_keys)):
            raise ValueError("authority identity_key values must be unique")
        if len(canonical_names) != len(set(canonical_names)):
            raise ValueError("authority canonical_name values must be unique")

        summary = payload.get("summary")
        if not isinstance(summary, dict):
            raise ValueError("summary must be an object")
        expected_summary = {
            "authorities_total": len(authorities),
            "status_counts": dict(status_counts),
            "source_people_counts": dict(source_people_counts),
            "route_counts": dict(route_counts),
            "works_total": works_total,
            "needs_review_total": needs_review_total,
        }
        if summary != expected_summary:
            raise ValueError("summary must match all derived corpus counters")
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        semantic_sha256 = hashlib.sha256(canonical_payload).hexdigest()
        if semantic_sha256 != expected_semantic_sha256:
            raise ValueError(
                "semantic projection does not match the published corpus contract"
            )
    except (KeyError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                "error",
                "AUTHORITY_CORPUS_CONTRACT_INVALID",
                f"Нарушен контракт пользовательского корпуса авторитетов: {exc}",
                package=package_dir.name,
                path=_relative(corpus_path, skills_root),
            )
        )


def _is_secret_path(path: Path) -> bool:
    name = path.name
    lowered = name.lower()
    if lowered == ".env.example":
        return False
    return (
        lowered in SECRET_NAMES
        or (lowered.startswith(".env.") and lowered != ".env.example")
        or path.suffix.lower() in SECRET_SUFFIXES
    )


def is_runtime_artifact(path: Path) -> bool:
    return (
        any(part in RUNTIME_PARTS for part in path.parts)
        or path.name in RUNTIME_NAMES
        or path.suffix.lower() in RUNTIME_SUFFIXES
    )


def is_source_only_artifact(path: Path) -> bool:
    return (
        any(part in DEVELOPMENT_ONLY_PARTS for part in path.parts)
        or path.as_posix() in SOURCE_ONLY_SKILLSET_PATHS
    )


def parse_runtime_json_strict(text: str) -> Any:
    """Decode runtime JSON while rejecting duplicate object keys."""

    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_nonfinite_json_constant,
    )


def _strip_valid_http_urls(text: str) -> str:
    """Remove only absolute HTTP(S) URLs with a non-empty network host."""

    def replace(match: re.Match[str]) -> str:
        candidate = match.group(0)
        try:
            parsed = urlsplit(candidate)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError:
            return candidate
        if (
            parsed.scheme.casefold() not in {"http", "https"}
            or not hostname
            or port == 0
        ):
            return candidate
        try:
            ip_address(hostname)
            valid_host = True
        except ValueError:
            try:
                ascii_host = hostname.rstrip(".").encode("idna").decode("ascii")
            except UnicodeError:
                valid_host = False
            else:
                valid_host = bool(ascii_host) and all(
                    DNS_LABEL.fullmatch(label) is not None
                    for label in ascii_host.split(".")
                )
        if valid_host:
            return ""
        return candidate

    return HTTP_URL_PATTERN.sub(replace, text)


def _has_implicit_cwd_repository_discovery(coordinate_key: str) -> bool:
    """Detect git-root lookup unless the same invocation binds -C to HUDOC config."""

    revision_token, root_token = GIT_ROOT_DISCOVERY_PARTS
    cursor = 0
    while True:
        revision_index = coordinate_key.find(revision_token, cursor)
        if revision_index < 0:
            return False
        root_index = coordinate_key.find(
            root_token,
            revision_index + len(revision_token),
            revision_index + len(revision_token) + 512,
        )
        if root_index < 0:
            cursor = revision_index + len(revision_token)
            continue

        window_start = max(0, revision_index - 512)
        command_window = coordinate_key[window_start:revision_index]
        git_tokens = tuple(GIT_COMMAND_TOKEN.finditer(command_window))
        if not git_tokens:
            return True
        invocation_start = window_start + git_tokens[-1].start()
        prefix = coordinate_key[invocation_start:revision_index]
        root_option = re.search(
            r'(?:["\']-c["\']|(?<![\w-])-c(?![\w-]))',
            prefix,
        )
        explicitly_bound = False
        if root_option is not None:
            explicitly_bound = (
                HUDOC_REPOSITORY_BINDING.match(prefix, root_option.end())
                is not None
            )

        if not explicitly_bound:
            return True
        cursor = root_index + len(root_token)


def runtime_local_coordinate_markers(
    path: Path,
    text: str,
) -> tuple[str, ...]:
    """Return location-dependence classes without exposing matched coordinates."""

    searchable = [text]
    if path.suffix.casefold() == ".json":
        try:
            decoded = parse_runtime_json_strict(text)
            searchable = [json.dumps(decoded, ensure_ascii=False)]
        except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
            pass

    markers: set[str] = set()
    for candidate in searchable:
        normalized = unicodedata.normalize("NFKC", candidate)
        normalized = normalized.replace("\\/", "/")
        normalized = re.sub(r"\\+", "/", normalized)
        normalized = _strip_valid_http_urls(normalized)
        normalized = re.sub(r"/+", "/", normalized)
        coordinate_key = normalized.casefold()
        if REPOSITORY_SOURCE_PREFIX.casefold() in coordinate_key:
            markers.add("repository-source-tree")
        if PROJECT_ROOT_PLACEHOLDER.casefold() in coordinate_key:
            markers.add("project-root-placeholder")
        if any(pattern.search(normalized) for pattern in RUNTIME_USER_HOME_PATTERNS):
            markers.add("user-home-absolute-path")
        if any(
            unresolved.casefold() in coordinate_key
            for unresolved in UNRESOLVED_COMMAND_ROOTS
        ):
            markers.add("unresolved-command-root")
        if HARDCODED_DEFAULT_SKILL_ROOT.casefold() in coordinate_key:
            markers.add("hardcoded-default-skill-root")
        implicit_home = (
            PATH_HOME_CALL.search(normalized) is not None
            or HOME_ENV_ACCESS.search(normalized) is not None
            or (
                "~" in normalized
                and EXPANDUSER_CALL.search(normalized) is not None
            )
        )
        if implicit_home and DOCUMENTS_KS_PARSER.search(normalized):
            markers.add("implicit-home-repository-discovery")
        if _has_implicit_cwd_repository_discovery(coordinate_key):
            markers.add("implicit-cwd-repository-discovery")
    return tuple(sorted(markers))


def _validate_runtime_self_containment(
    findings: list[dict[str, Any]],
    package_dir: Path,
    skills_root: Path,
) -> None:
    """Reject location-dependent content from every runtime-eligible text file."""

    for path in sorted(package_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        logical_path = Path(package_dir.name) / path.relative_to(package_dir)
        if (
            is_runtime_artifact(logical_path)
            or is_source_only_artifact(logical_path)
        ):
            continue
        relative_path = _relative(path, skills_root)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            if path.suffix.casefold() in BINARY_RUNTIME_SUFFIXES:
                continue
            code = (
                "RUNTIME_TEXT_UNREADABLE"
                if path.suffix.casefold() in TEXT_SUFFIXES
                else "RUNTIME_FORMAT_UNCHECKED"
            )
            findings.append(
                _finding(
                    "error",
                    code,
                    f"Не удалось проверить автономность runtime-файла: {exc}",
                    package=package_dir.name,
                    path=relative_path,
                )
            )
            continue
        except OSError as exc:
            findings.append(
                _finding(
                    "error",
                    "RUNTIME_TEXT_UNREADABLE",
                    f"Не удалось проверить автономность runtime-файла: {exc}",
                    package=package_dir.name,
                    path=relative_path,
                )
            )
            continue

        if path.suffix.casefold() == ".json":
            try:
                parse_runtime_json_strict(text)
            except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
                findings.append(
                    _finding(
                        "error",
                        "RUNTIME_REFERENCE_JSON_INVALID",
                        f"Runtime JSON не прошёл строгий разбор: {exc}",
                        package=package_dir.name,
                        path=relative_path,
                    )
                )

        markers = runtime_local_coordinate_markers(path, text)
        if markers:
            marker_classes = ", ".join(markers)
            findings.append(
                _finding(
                    "error",
                    "RUNTIME_LOCAL_COORDINATE",
                    (
                        "Runtime-файл содержит неразрешённый или локально-зависимый "
                        "маршрут, недоступный после пользовательской установки: "
                        f"{marker_classes}."
                    ),
                    package=package_dir.name,
                    path=relative_path,
                    evidence={"marker_classes": list(markers)},
                )
            )


def _development_artifact(path: Path) -> bool:
    return is_source_only_artifact(path)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_path_snapshot(
    skills_root: Path,
    package_names: Sequence[str],
    *,
    validation_profile: str,
) -> tuple[str, ...]:
    """Observe the complete eligible path set without reading file content."""

    paths: list[str] = []
    try:
        for package in package_names:
            package_dir = skills_root / package
            if not package_dir.is_dir():
                continue
            for path in sorted(package_dir.rglob("*")):
                relative = path.relative_to(skills_root).as_posix()
                relative_object = Path(relative)
                if _development_artifact(relative_object):
                    if validation_profile == "runtime":
                        paths.append(f"!invalid:{relative}")
                    continue
                if is_runtime_artifact(relative_object):
                    continue
                metadata = path.lstat()
                if stat.S_ISDIR(metadata.st_mode):
                    continue
                if not stat.S_ISREG(metadata.st_mode) or _is_secret_path(path):
                    paths.append(f"!invalid:{relative}")
                    continue
                paths.append(relative)
    except (OSError, ValueError):
        return ("!snapshot-unavailable",)
    return tuple(sorted(paths))


def _runtime_content_identity(
    findings: list[dict[str, Any]],
    skills_root: Path,
    package_names: Sequence[str],
    files: Sequence[Mapping[str, Any]],
    *,
    validation_profile: str,
) -> dict[str, Any]:
    """Re-read manifest rows and derive the deterministic runtime tree identity."""

    total_files = len(files)
    total_bytes = sum(
        int(item.get("size", 0))
        for item in files
        if isinstance(item.get("size"), int)
        and not isinstance(item.get("size"), bool)
    )
    aggregate = hashlib.sha256()
    root_resolved = skills_root.resolve()
    expected_paths = tuple(str(item.get("path", "")) for item in files)

    if (
        _runtime_path_snapshot(
            skills_root,
            package_names,
            validation_profile=validation_profile,
        )
        != expected_paths
    ):
        findings.append(
            _finding(
                "error",
                "RUNTIME_IDENTITY_CHANGED",
                "Состав runtime-дерева изменился между проходами проверки.",
                path="runtime",
            )
        )
        return {
            "algorithm": RUNTIME_CONTENT_ALGORITHM,
            "tree_sha256": None,
            "total_files": total_files,
            "total_bytes": total_bytes,
        }

    for item in files:
        relative = item.get("path")
        expected_hash = item.get("sha256")
        expected_size = item.get("size")
        relative_object = Path(relative) if isinstance(relative, str) else Path(".")
        if (
            not isinstance(relative, str)
            or not relative
            or relative_object.is_absolute()
            or ".." in relative_object.parts
            or relative_object.as_posix() != relative
            or not isinstance(expected_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
        ):
            findings.append(
                _finding(
                    "error",
                    "RUNTIME_IDENTITY_CHANGED",
                    "Runtime-дерево нельзя однозначно перечитать для итогового отпечатка.",
                    path=relative if isinstance(relative, str) else "runtime",
                )
            )
            return {
                "algorithm": RUNTIME_CONTENT_ALGORITHM,
                "tree_sha256": None,
                "total_files": total_files,
                "total_bytes": total_bytes,
            }

        path = skills_root / relative_object
        file_digest = hashlib.sha256()
        observed_size = 0
        try:
            resolved_before = path.resolve(strict=True)
            resolved_before.relative_to(root_resolved)
            entry_before = path.lstat()
            if not stat.S_ISREG(entry_before.st_mode):
                raise OSError("not a regular directory entry")
            with path.open("rb") as handle:
                before = os.fstat(handle.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise OSError("not a regular file")
                aggregate.update(len(relative.encode("utf-8")).to_bytes(4, "big"))
                aggregate.update(relative.encode("utf-8"))
                aggregate.update(before.st_size.to_bytes(8, "big"))
                while chunk := handle.read(1024 * 1024):
                    observed_size += len(chunk)
                    file_digest.update(chunk)
                    aggregate.update(chunk)
                after = os.fstat(handle.fileno())
            resolved_after = path.resolve(strict=True)
            entry_after = path.lstat()
        except (OSError, ValueError):
            findings.append(
                _finding(
                    "error",
                    "RUNTIME_IDENTITY_CHANGED",
                    "Runtime-файл изменился или стал недоступен при повторной проверке.",
                    path=relative,
                )
            )
            return {
                "algorithm": RUNTIME_CONTENT_ALGORITHM,
                "tree_sha256": None,
                "total_files": total_files,
                "total_bytes": total_bytes,
            }

        stable_file = (
            resolved_before == resolved_after
            and stat.S_ISREG(entry_after.st_mode)
            and entry_before.st_dev == before.st_dev == after.st_dev == entry_after.st_dev
            and entry_before.st_ino == before.st_ino == after.st_ino == entry_after.st_ino
            and entry_before.st_size == before.st_size == after.st_size == entry_after.st_size == observed_size
            and entry_before.st_mtime_ns
            == before.st_mtime_ns
            == after.st_mtime_ns
            == entry_after.st_mtime_ns
        )
        if (
            not stable_file
            or observed_size != expected_size
            or file_digest.hexdigest() != expected_hash
        ):
            findings.append(
                _finding(
                    "error",
                    "RUNTIME_IDENTITY_CHANGED",
                    "Runtime-файл изменился между проходами проверки.",
                    path=relative,
                )
            )
            return {
                "algorithm": RUNTIME_CONTENT_ALGORITHM,
                "tree_sha256": None,
                "total_files": total_files,
                "total_bytes": total_bytes,
            }

    if (
        _runtime_path_snapshot(
            skills_root,
            package_names,
            validation_profile=validation_profile,
        )
        != expected_paths
    ):
        findings.append(
            _finding(
                "error",
                "RUNTIME_IDENTITY_CHANGED",
                "Состав runtime-дерева изменился во время повторной проверки.",
                path="runtime",
            )
        )
        return {
            "algorithm": RUNTIME_CONTENT_ALGORITHM,
            "tree_sha256": None,
            "total_files": total_files,
            "total_bytes": total_bytes,
        }

    return {
        "algorithm": RUNTIME_CONTENT_ALGORITHM,
        "tree_sha256": aggregate.hexdigest(),
        "total_files": total_files,
        "total_bytes": total_bytes,
    }


def _freshness_request_spec(
    route: str,
    commit_sha: str | None,
) -> tuple[str, str, int, str, str | None, bool]:
    if route == "ref" and commit_sha is None:
        return (
            _FRESHNESS_REF_URL,
            "api.github.com",
            _FRESHNESS_REF_MAX_BYTES,
            _FRESHNESS_JSON_ACCEPT,
            None,
            False,
        )
    if (
        route not in {"raw", "contents"}
        or not isinstance(commit_sha, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None
    ):
        raise _FreshnessLookupError("invalid_response")
    if route == "raw":
        return (
            f"{_FRESHNESS_RAW_PREFIX}{commit_sha}/skills-manifest.json",
            "raw.githubusercontent.com",
            _FRESHNESS_MANIFEST_MAX_BYTES,
            _FRESHNESS_JSON_ACCEPT,
            None,
            True,
        )
    return (
        f"{_FRESHNESS_CONTENTS_MANIFEST_PREFIX}{commit_sha}",
        "api.github.com",
        _FRESHNESS_MANIFEST_MAX_BYTES,
        _FRESHNESS_CONTENTS_ACCEPT,
        _FRESHNESS_GITHUB_API_VERSION,
        True,
    )


def _read_freshness_payload_direct(
    route: str,
    commit_sha: str | None,
    *,
    opener: Any,
) -> bytes:
    (
        url,
        expected_host,
        max_bytes,
        accept,
        api_version,
        strict_manifest_http,
    ) = _freshness_request_spec(route, commit_sha)
    headers = {
        "Accept": accept,
        "User-Agent": "ksrf-runtime-validator/1",
    }
    if api_version is not None:
        headers["X-GitHub-Api-Version"] = api_version
    request = Request(
        url,
        headers=headers,
    )
    try:
        with opener(
            request,
            timeout=_FRESHNESS_TIMEOUT_SECONDS,
        ) as response:
            try:
                final_url = str(response.geturl())
                requested = urlsplit(url)
                final = urlsplit(final_url)
                final_port = final.port
            except ValueError as exc:
                raise _FreshnessLookupError("invalid_response") from exc
            if (
                final.scheme != "https"
                or final.hostname != expected_host
                or final_port not in {None, 443}
                or final.username is not None
                or final.password is not None
                or final.path != requested.path
                or final.query != requested.query
                or final.fragment
                or getattr(
                    response,
                    "status",
                    None if strict_manifest_http else 200,
                ) != 200
            ):
                raise _FreshnessLookupError("invalid_response")
            payload = response.read(max_bytes + 1)
    except _FreshnessLookupError:
        raise
    except HTTPError as exc:
        if strict_manifest_http:
            reason = (
                "network_error"
                if exc.code in {408, 429} or 500 <= exc.code <= 599
                else "invalid_response"
            )
        else:
            reason = "invalid_response" if 300 <= exc.code < 400 else "network_error"
        raise _FreshnessLookupError(reason) from exc
    except ValueError as exc:
        raise _FreshnessLookupError("invalid_response") from exc
    except (HTTPException, OSError, TimeoutError, URLError) as exc:
        raise _FreshnessLookupError("network_error") from exc

    if not isinstance(payload, bytes):
        raise _FreshnessLookupError("invalid_response")
    if len(payload) > max_bytes:
        raise _FreshnessLookupError("response_too_large")
    return payload


def _direct_freshness_http_transport(
    route: str,
    commit_sha: str | None,
) -> bytes:
    """Exercise the child-side transport through the explicit test seam."""

    return _read_freshness_payload_direct(
        route,
        commit_sha,
        opener=_FRESHNESS_OPENER,
    )


def _read_freshness_json(
    route: str,
    commit_sha: str | None = None,
) -> Any:
    _, _, max_bytes, _, _, _ = _freshness_request_spec(route, commit_sha)
    payload = _FRESHNESS_HTTP_TRANSPORT(route, commit_sha)
    if not isinstance(payload, bytes):
        raise _FreshnessLookupError("invalid_response")
    if len(payload) > max_bytes:
        raise _FreshnessLookupError("response_too_large")
    try:
        return json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
        raise _FreshnessLookupError("invalid_response") from exc


def _kill_freshness_process_group(process: subprocess.Popen[bytes]) -> None:
    """Kill and reap a bounded helper without exposing process diagnostics."""

    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
    else:  # pragma: no cover - the public installer is POSIX-only
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _finish_freshness_process_group(
    process: subprocess.Popen[bytes],
    deadline: float,
) -> int:
    """Observe the leader without reaping, kill its group, then reap safely."""

    if os.name != "posix":  # pragma: no cover - installer contract is POSIX-only
        remaining = deadline - _FRESHNESS_MONOTONIC()
        if remaining <= 0:
            _kill_freshness_process_group(process)
            raise _FreshnessLookupError("network_error")
        try:
            return process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _kill_freshness_process_group(process)
            raise _FreshnessLookupError("network_error") from exc

    if not all(
        hasattr(os, name)
        for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")
    ):
        _kill_freshness_process_group(process)
        raise _FreshnessLookupError("network_error")

    options = os.WEXITED | os.WNOHANG | os.WNOWAIT
    while True:
        remaining = deadline - _FRESHNESS_MONOTONIC()
        if remaining <= 0:
            _kill_freshness_process_group(process)
            raise _FreshnessLookupError("network_error")
        try:
            observed = os.waitid(os.P_PID, process.pid, options)
        except ChildProcessError as exc:
            # Another reaper would make the numeric PGID unsafe to signal.
            raise _FreshnessLookupError("network_error") from exc
        except OSError as exc:
            _kill_freshness_process_group(process)
            raise _FreshnessLookupError("network_error") from exc
        if observed is None or observed.si_pid == 0:
            _FRESHNESS_SLEEP(min(0.01, remaining))
            continue
        if observed.si_pid != process.pid:
            _kill_freshness_process_group(process)
            raise _FreshnessLookupError("network_error")
        if deadline - _FRESHNESS_MONOTONIC() <= 0:
            _kill_freshness_process_group(process)
            raise _FreshnessLookupError("network_error")

        # WNOWAIT keeps the leader's PID/PGID reserved. Terminating the group
        # here cannot target a later, unrelated process group with a reused id.
        _kill_freshness_process_group(process)
        return_code = process.returncode
        if not isinstance(return_code, int) or isinstance(return_code, bool):
            raise _FreshnessLookupError("network_error")
        return return_code


def _run_bounded_freshness_process(
    argv: Sequence[str],
    *,
    env: Mapping[str, str],
    cwd: str,
    timeout: float,
    max_stdout: int,
) -> tuple[int, bytes]:
    """Run one non-interactive helper with bounded time and stdout."""

    deadline = _FRESHNESS_MONOTONIC() + timeout
    process: subprocess.Popen[bytes] | None = None
    selector: selectors.BaseSelector | None = None
    cleanup_owned_by_runner = True
    try:
        process = subprocess.Popen(
            tuple(argv),
            shell=False,
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=os.name == "posix",
        )
        if process.stdout is None:  # pragma: no cover - PIPE guarantees the handle
            raise _FreshnessLookupError("network_error")

        output = bytearray()
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - _FRESHNESS_MONOTONIC()
            if remaining <= 0:
                raise _FreshnessLookupError("network_error")
            events = selector.select(remaining)
            if not events:
                raise _FreshnessLookupError("network_error")
            if deadline - _FRESHNESS_MONOTONIC() <= 0:
                raise _FreshnessLookupError("network_error")
            chunk = os.read(
                process.stdout.fileno(),
                min(4096, max_stdout + 1 - len(output)),
            )
            if deadline - _FRESHNESS_MONOTONIC() <= 0:
                raise _FreshnessLookupError("network_error")
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > max_stdout:
                raise _FreshnessLookupError("response_too_large")

        cleanup_owned_by_runner = False
        return_code = _finish_freshness_process_group(process, deadline)
        if deadline - _FRESHNESS_MONOTONIC() <= 0:
            raise _FreshnessLookupError("network_error")
        return return_code, bytes(output)
    except _FreshnessLookupError:
        raise
    except (OSError, ValueError) as exc:
        raise _FreshnessLookupError("network_error") from exc
    finally:
        if process is not None and cleanup_owned_by_runner:
            _kill_freshness_process_group(process)
        if selector is not None:
            try:
                selector.close()
            except OSError:
                pass
        if process is not None and process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass


_FRESHNESS_MONOTONIC = time.monotonic
_FRESHNESS_SLEEP = time.sleep
_FRESHNESS_GIT_RUNNER = _run_bounded_freshness_process
_FRESHNESS_HTTP_PROCESS_RUNNER = _run_bounded_freshness_process


def _freshness_http_environment() -> dict[str, str]:
    """Return the complete environment allowlist for an HTTP helper."""

    return {
        "LC_ALL": "C",
        "LANG": "C",
    }


def _run_freshness_http_helper(
    route: str,
    commit_sha: str | None,
) -> bytes:
    """Run one fixed-route HTTPS request behind a hard process deadline."""

    _, _, max_bytes, _, _, _ = _freshness_request_spec(route, commit_sha)
    python_executable = sys.executable
    validator_path = Path(__file__)
    if not validator_path.is_absolute():
        validator_path = Path.cwd() / validator_path
    try:
        validator_meta = validator_path.lstat()
        validator_path = validator_path.resolve(strict=True)
        resolved_meta = validator_path.stat()
    except OSError as exc:
        raise _FreshnessLookupError("network_error") from exc
    if (
        not isinstance(python_executable, str)
        or not os.path.isabs(python_executable)
        or not stat.S_ISREG(validator_meta.st_mode)
        or stat.S_ISLNK(validator_meta.st_mode)
        or not stat.S_ISREG(resolved_meta.st_mode)
        or (validator_meta.st_dev, validator_meta.st_ino)
        != (resolved_meta.st_dev, resolved_meta.st_ino)
    ):
        raise _FreshnessLookupError("network_error")

    coordinate = "-" if route == "ref" else str(commit_sha)
    argv = (
        python_executable,
        "-I",
        "-S",
        "-B",
        str(validator_path),
        _FRESHNESS_HTTP_HELPER_FLAG,
        route,
        coordinate,
    )
    try:
        return_code, payload = _FRESHNESS_HTTP_PROCESS_RUNNER(
            argv,
            env=_freshness_http_environment(),
            cwd=Path(python_executable).anchor or os.sep,
            timeout=_FRESHNESS_HTTP_DEADLINE_SECONDS,
            max_stdout=max_bytes,
        )
    except _FreshnessLookupError:
        raise
    except (OSError, subprocess.SubprocessError, TimeoutError, TypeError, ValueError) as exc:
        raise _FreshnessLookupError("network_error") from exc

    if not isinstance(return_code, int) or isinstance(return_code, bool):
        raise _FreshnessLookupError("network_error")
    if not isinstance(payload, bytes):
        raise _FreshnessLookupError("network_error")
    if len(payload) > max_bytes:
        raise _FreshnessLookupError("response_too_large")
    helper_reasons = {
        _FRESHNESS_HTTP_HELPER_NETWORK_EXIT: "network_error",
        _FRESHNESS_HTTP_HELPER_INVALID_EXIT: "invalid_response",
        _FRESHNESS_HTTP_HELPER_OVERSIZE_EXIT: "response_too_large",
    }
    if return_code != 0:
        raise _FreshnessLookupError(
            helper_reasons.get(return_code, "network_error")
        )
    return payload


def _freshness_http_helper_main(
    args: Sequence[str],
    *,
    stdout: Any = None,
) -> int:
    """Execute the closed child protocol without printing diagnostics."""

    if len(args) != 2:
        return _FRESHNESS_HTTP_HELPER_INVALID_EXIT
    route, coordinate = args
    commit_sha: str | None
    if route == "ref" and coordinate == "-":
        commit_sha = None
    elif route in {"raw", "contents"}:
        commit_sha = coordinate
    else:
        return _FRESHNESS_HTTP_HELPER_INVALID_EXIT
    try:
        payload = _read_freshness_payload_direct(
            route,
            commit_sha,
            opener=_default_freshness_opener,
        )
        output = sys.stdout.buffer if stdout is None else stdout
        written = output.write(payload)
        if written is not None and written != len(payload):
            return _FRESHNESS_HTTP_HELPER_NETWORK_EXIT
        output.flush()
    except _FreshnessLookupError as exc:
        return {
            "network_error": _FRESHNESS_HTTP_HELPER_NETWORK_EXIT,
            "invalid_response": _FRESHNESS_HTTP_HELPER_INVALID_EXIT,
            "response_too_large": _FRESHNESS_HTTP_HELPER_OVERSIZE_EXIT,
        }.get(exc.reason_code, _FRESHNESS_HTTP_HELPER_NETWORK_EXIT)
    except Exception:
        return _FRESHNESS_HTTP_HELPER_NETWORK_EXIT
    return 0


def _subprocess_freshness_http_transport(
    route: str,
    commit_sha: str | None,
) -> bytes:
    return _run_freshness_http_helper(route, commit_sha)


_FRESHNESS_HTTP_TRANSPORT = _subprocess_freshness_http_transport


def _freshness_git_environment() -> dict[str, str]:
    """Return a minimal environment that cannot inherit Git routing policy."""

    return {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "LANG": "C",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_COUNT": "0",
        "GIT_DIR": os.devnull,
        "GIT_ALLOW_PROTOCOL": "https",
    }


def _resolve_remote_main_sha_via_git() -> str:
    git_executable = _FRESHNESS_GIT_FINDER("git", path=os.defpath)
    if (
        not isinstance(git_executable, str)
        or not os.path.isabs(git_executable)
    ):
        raise _FreshnessLookupError("network_error")

    argv = (
        git_executable,
        "-c",
        "credential.helper=",
        "-c",
        "core.askPass=",
        "-c",
        "credential.interactive=never",
        "-c",
        "http.followRedirects=false",
        "ls-remote",
        "--exit-code",
        "--refs",
        _FRESHNESS_GIT_REPOSITORY,
        _FRESHNESS_GIT_REF,
    )
    try:
        return_code, payload = _FRESHNESS_GIT_RUNNER(
            argv,
            env=_freshness_git_environment(),
            cwd=Path(sys.executable).anchor or os.sep,
            timeout=_FRESHNESS_TIMEOUT_SECONDS,
            max_stdout=_FRESHNESS_GIT_MAX_BYTES,
        )
    except _FreshnessLookupError:
        raise
    except (OSError, subprocess.SubprocessError, TimeoutError, TypeError, ValueError) as exc:
        raise _FreshnessLookupError("network_error") from exc

    if not isinstance(return_code, int) or isinstance(return_code, bool):
        raise _FreshnessLookupError("invalid_response")
    if not isinstance(payload, bytes):
        raise _FreshnessLookupError("invalid_response")
    if len(payload) > _FRESHNESS_GIT_MAX_BYTES:
        raise _FreshnessLookupError("response_too_large")
    if return_code == 2:
        raise _FreshnessLookupError("invalid_response")
    if return_code != 0:
        raise _FreshnessLookupError("network_error")

    expected = re.fullmatch(
        rb"([0-9a-f]{40})\trefs/heads/main\n",
        payload,
    )
    if expected is None:
        raise _FreshnessLookupError("invalid_response")
    return expected.group(1).decode("ascii")


def _resolve_remote_main_sha_via_rest() -> str:
    payload = _read_freshness_json("ref")
    if not isinstance(payload, Mapping):
        raise _FreshnessLookupError("invalid_response")
    reference = payload.get("ref")
    git_object = payload.get("object")
    if (
        reference != "refs/heads/main"
        or not isinstance(git_object, Mapping)
        or git_object.get("type") != "commit"
    ):
        raise _FreshnessLookupError("invalid_response")
    commit_sha = git_object.get("sha")
    if (
        not isinstance(commit_sha, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None
    ):
        raise _FreshnessLookupError("invalid_response")
    return commit_sha


def _resolve_remote_main_sha() -> str:
    try:
        return _resolve_remote_main_sha_via_rest()
    except _FreshnessLookupError as exc:
        if exc.reason_code != "network_error":
            raise
    return _resolve_remote_main_sha_via_git()


def _fetch_remote_runtime_manifest(commit_sha: str) -> Any:
    if (
        not isinstance(commit_sha, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None
    ):
        raise _FreshnessLookupError("invalid_response")
    try:
        return _read_freshness_json("raw", commit_sha)
    except _FreshnessLookupError as exc:
        if exc.reason_code != "network_error":
            raise

    return _read_freshness_json("contents", commit_sha)


def _fetch_remote_runtime_identity(commit_sha: str) -> dict[str, Any]:
    payload = _fetch_remote_runtime_manifest(commit_sha)
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version") != "1.2"
        or payload.get("digest_format") != RUNTIME_CONTENT_DIGEST_FORMAT
    ):
        raise _FreshnessLookupError("invalid_response")

    total_skills = payload.get("total_skills")
    total_files = payload.get("total_files")
    total_bytes = payload.get("total_bytes")
    tree_sha256 = payload.get("tree_sha256")
    valid_counts = (
        isinstance(total_skills, int)
        and not isinstance(total_skills, bool)
        and total_skills == len(CANONICAL_KSRF_PACKAGES)
        and isinstance(total_files, int)
        and not isinstance(total_files, bool)
        and 0 < total_files <= 1_000_000
        and isinstance(total_bytes, int)
        and not isinstance(total_bytes, bool)
        and 0 <= total_bytes <= (2**63 - 1)
    )
    if (
        not valid_counts
        or not isinstance(tree_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", tree_sha256) is None
    ):
        raise _FreshnessLookupError("invalid_response")
    return {
        "tree_sha256": tree_sha256,
        "total_files": total_files,
        "total_bytes": total_bytes,
    }


def _runtime_freshness(
    runtime_content: Mapping[str, Any],
    *,
    check_updates: bool,
) -> dict[str, Any]:
    local_hash = runtime_content.get("tree_sha256")
    result: dict[str, Any] = {
        "status": "not_checked",
        "reason_code": "not_requested",
        "remote_main_sha": None,
        "local_tree_sha256": local_hash if isinstance(local_hash, str) else None,
        "remote_tree_sha256": None,
    }
    if not check_updates:
        return result
    if not isinstance(local_hash, str):
        result.update(
            status="unknown",
            reason_code="local_identity_unavailable",
        )
        return result

    remote_sha: str | None = None
    try:
        remote_sha = _resolve_remote_main_sha()
        remote_content = _fetch_remote_runtime_identity(remote_sha)
    except _FreshnessLookupError as exc:
        result.update(
            status="unknown",
            reason_code=exc.reason_code,
            remote_main_sha=remote_sha,
        )
        return result

    remote_hash = str(remote_content["tree_sha256"])
    matches = (
        local_hash == remote_hash
        and runtime_content.get("total_files") == remote_content["total_files"]
        and runtime_content.get("total_bytes") == remote_content["total_bytes"]
    )
    result.update(
        status="current" if matches else "different",
        reason_code="content_matches" if matches else "content_differs",
        remote_main_sha=remote_sha,
        remote_tree_sha256=remote_hash,
    )
    return result


def _content_security_findings(
    path: Path,
    *,
    package: str,
    relative_path: str,
) -> list[dict[str, Any]]:
    if path.suffix.lower() not in TEXT_SUFFIXES or "tests" in path.parts:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    findings: list[dict[str, Any]] = []
    if "user-home-absolute-path" in runtime_local_coordinate_markers(path, text):
        findings.append(
            _finding(
                "error",
                "ABSOLUTE_RUNTIME_PATH",
                "Публикуемый текст содержит абсолютный локальный runtime path.",
                package=package,
                path=relative_path,
            )
        )
    for line_number, line in enumerate(text.splitlines(), start=1):
        secret_detected = bool(PRIVATE_KEY_MARKER.search(line) or TOKEN_LITERAL.search(line))
        assignment = SECRET_ASSIGNMENT.search(line)
        if assignment:
            value = assignment.group(1).lower()
            secret_detected = secret_detected or not any(word in value for word in SAFE_SECRET_WORDS)
        if secret_detected:
            findings.append(
                _finding(
                    "error",
                    "POTENTIAL_SECRET",
                    "Публикуемый текст похож на встроенный секрет; значение намеренно не выводится.",
                    package=package,
                    path=relative_path,
                    line=line_number,
                )
            )
    return findings


def _build_publish_manifest(
    findings: list[dict[str, Any]],
    skills_root: Path,
    package_names: Sequence[str],
    *,
    validation_profile: str,
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for package in package_names:
        package_dir = skills_root / package
        if not package_dir.is_dir():
            continue
        excluded_runtime: list[str] = []
        for path in sorted(package_dir.rglob("*")):
            relative_path = _relative(path, skills_root)
            relative_object = Path(relative_path)
            if (
                validation_profile == "source"
                and relative_object.as_posix() in ROOT_ONLY_TOOL_SKILL_PATHS
            ):
                findings.append(
                    _finding(
                        "error",
                        "ROOT_ONLY_DUPLICATE_PRESENT",
                        "Корневой инструмент сопровождения не должен иметь дубль в пользовательском скилле.",
                        package=package,
                        path=relative_path,
                    )
                )
            if _development_artifact(relative_object):
                if validation_profile == "source" and path.is_symlink():
                    findings.append(
                        _finding(
                            "error",
                            "SYMLINK_NOT_PUBLISHABLE",
                            "Символические ссылки не допускаются в source QA assets.",
                            package=package,
                            path=relative_path,
                        )
                    )
                elif validation_profile == "source" and path.is_file():
                    if _is_secret_path(path):
                        findings.append(
                            _finding(
                                "error",
                                "FORBIDDEN_SECRET_FILE",
                                "Файл с секретным назначением запрещён в source QA assets.",
                                package=package,
                                path=relative_path,
                            )
                        )
                    else:
                        findings.extend(
                            _content_security_findings(
                                path,
                                package=package,
                                relative_path=relative_path,
                            )
                        )
                continue
            if is_runtime_artifact(relative_object):
                if path.is_file():
                    excluded_runtime.append(relative_path)
                continue
            if path.is_symlink():
                findings.append(
                    _finding(
                        "error",
                        "SYMLINK_NOT_PUBLISHABLE",
                        "Символические ссылки не включаются в publish manifest.",
                        package=package,
                        path=relative_path,
                    )
                )
                continue
            if not path.is_file():
                continue
            if _is_secret_path(path):
                findings.append(
                    _finding(
                        "error",
                        "FORBIDDEN_SECRET_FILE",
                        "Файл с секретным назначением исключён из publish manifest.",
                        package=package,
                        path=relative_path,
                    )
                )
                continue
            parts = relative_object.parts
            if relative_object.is_absolute() or ".." in parts:
                findings.append(
                    _finding(
                        "error",
                        "PUBLISH_PATH_NOT_RELATIVE",
                        "Publish manifest может содержать только нормализованные относительные пути.",
                        package=package,
                        path=relative_path,
                    )
                )
                continue
            content_findings = _content_security_findings(
                path,
                package=package,
                relative_path=relative_path,
            )
            if content_findings:
                findings.extend(content_findings)
                continue
            try:
                checksum = _hash_file(path)
                size = path.stat().st_size
            except OSError as exc:
                findings.append(
                    _finding(
                        "error",
                        "PUBLISH_FILE_UNREADABLE",
                        f"Файл не удалось прочитать для manifest: {exc}",
                        package=package,
                        path=relative_path,
                    )
                )
                continue
            files.append({"path": relative_path, "sha256": checksum, "size": size})
        if excluded_runtime:
            findings.append(
                _finding(
                    "warning",
                    "RUNTIME_ARTIFACT_EXCLUDED",
                    "Runtime-артефакты исключены из publish manifest.",
                    package=package,
                    evidence={
                        "count": len(excluded_runtime),
                        "examples": excluded_runtime[:10],
                    },
                )
            )
    files.sort(key=lambda item: item["path"])
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_profile": validation_profile,
        "package_count": len(package_names),
        "packages": list(package_names),
        "files": files,
    }


def _validate_markdown_mcp_references(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    package = package_dir.name
    for markdown in sorted(package_dir.rglob("*.md")):
        if any(part in RUNTIME_PARTS for part in markdown.parts) or markdown.name == "SKILL.md":
            continue
        try:
            text = markdown.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        relative_path = _relative(markdown, skills_root)
        for token, line_number in _mcp_tokens_declared_in_markdown(text):
            findings.append(
                _finding(
                    "error",
                    "MCP_TOOL_NOT_FULLY_QUALIFIED",
                    f"MCP-инструмент {token} должен быть указан как mcp__server__tool.",
                    package=package,
                    path=relative_path,
                    line=line_number,
                    evidence=token,
                )
            )


def _validate_unique_skill_entrypoints(
    findings: list[dict[str, Any]],
    skills_root: Path,
    packages: Sequence[str],
) -> None:
    """Reject hidden snapshots that redeclare a canonical skill name.

    Package allowlists protect publication, but agent discovery can recurse more
    broadly than the publisher.  A workspace nested below the skills root must
    therefore never contain a second entrypoint with a canonical name.
    """

    expected = {
        package: (skills_root / package / "SKILL.md").resolve()
        for package in packages
    }
    for skill_file in sorted(skills_root.rglob("SKILL.md")):
        try:
            text = skill_file.read_text(encoding="utf-8")
            frontmatter, _ = _frontmatter(text)
        except Exception:
            continue
        name = frontmatter.get("name")
        if not isinstance(name, str) or name not in expected:
            continue
        if skill_file.resolve() == expected[name]:
            continue
        findings.append(
            _finding(
                "error",
                "NESTED_SKILL_DUPLICATE",
                "Внутри skills root найден второй SKILL.md с именем канонического пакета.",
                package=name,
                path=_relative(skill_file, skills_root),
                evidence={
                    "canonical_path": _relative(expected[name], skills_root),
                    "duplicate_path": _relative(skill_file, skills_root),
                },
            )
        )


def _validate_runtime_profile_cleanliness(
    findings: list[dict[str, Any]], package_dir: Path, skills_root: Path
) -> None:
    source_only_paths = [
        _relative(path, skills_root)
        for path in sorted(package_dir.rglob("*"))
        if _development_artifact(
            Path(package_dir.name) / path.relative_to(package_dir)
        )
    ]
    if source_only_paths:
        findings.append(
            _finding(
                "error",
                "SOURCE_ONLY_ARTIFACT_PRESENT",
                "Рабочий профиль требует дерево без служебных материалов контроля качества и сопровождения.",
                package=package_dir.name,
                path=package_dir.name,
                evidence={
                    "count": len(source_only_paths),
                    "examples": source_only_paths[:10],
                },
            )
        )


def _load_public_source_contract() -> tuple[Any, Any, type[Exception]]:
    if not PUBLIC_SOURCE_CONTRACT_PATH.is_file():
        raise FileNotFoundError(PUBLIC_SOURCE_CONTRACT_PATH)
    spec = importlib.util.spec_from_file_location(
        "_ksrf_public_source_contract",
        PUBLIC_SOURCE_CONTRACT_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("public source contract cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifact_validator = getattr(module, "validate_public_artifact", None)
    repository_validator = getattr(module, "validate_public_repository", None)
    error_type = getattr(module, "FileContractError", None)
    if not callable(artifact_validator) or not callable(repository_validator):
        raise RuntimeError("public source artifact validator is unavailable")
    if not isinstance(error_type, type) or not issubclass(error_type, Exception):
        raise RuntimeError("public source contract error type is unavailable")
    return artifact_validator, repository_validator, error_type


def _validate_source_public_safety(
    findings: list[dict[str, Any]],
    skills_root: Path,
    package_names: Sequence[str],
) -> tuple[str, str]:
    try:
        artifact_validator, repository_validator, contract_error = (
            _load_public_source_contract()
        )
    except Exception:
        findings.append(
            _finding(
                "warning",
                "PUBLIC_SOURCE_SAFETY_NOT_CHECKED",
                "Канонический public-source guard недоступен; source release QA не подтверждён.",
                path="skills",
            )
        )
        return "not_checked", "not_checked"

    for package in package_names:
        package_dir = skills_root / package
        if not package_dir.is_dir():
            continue
        for path in sorted(package_dir.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            relative_path = Path("skills") / path.relative_to(skills_root)
            try:
                artifact_validator(path, relative_path)
            except contract_error:
                findings.append(
                    _finding(
                        "error",
                        "FORBIDDEN_PUBLIC_SOURCE_ARTIFACT",
                        "Source QA обнаружил запрещённый публичный артефакт.",
                        package=package,
                        path=relative_path.as_posix(),
                    )
                )
            except Exception:
                findings.append(
                    _finding(
                        "error",
                        "PUBLIC_SOURCE_GUARD_FAILED",
                        "Public-source guard завершился ошибкой без разрешения публикации.",
                        package=package,
                        path=relative_path.as_posix(),
                    )
                )
    repository_safety = "not_checked"
    repository_root = PUBLIC_SOURCE_CONTRACT_PATH.parents[1]
    canonical_skills_root = repository_root / "skills"
    if skills_root.resolve() == canonical_skills_root.resolve():
        repository_safety = "validated"
        try:
            repository_validator(repository_root)
        except contract_error:
            findings.append(
                _finding(
                    "error",
                    "FORBIDDEN_PUBLIC_REPOSITORY_ARTIFACT",
                    "Repository source QA обнаружил запрещённый публичный артефакт.",
                    path="repository",
                )
            )
        except Exception:
            findings.append(
                _finding(
                    "error",
                    "PUBLIC_REPOSITORY_GUARD_FAILED",
                    "Repository public-source guard завершился ошибкой без разрешения публикации.",
                    path="repository",
                )
            )
    return "validated", repository_safety


def _required_runtime_root_anchor(root: Path) -> tuple[int, int, int, str]:
    metadata = root.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise OSError("runtime root is a symlink or not a directory")
    resolved = root.resolve(strict=True)
    filesystem_root = Path(resolved.anchor)
    if resolved == filesystem_root or resolved == Path.home().resolve():
        raise OSError("runtime root is too broad")
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        str(resolved),
    )


def _required_runtime_root_matches(
    root: Path,
    anchor: tuple[int, int, int, str],
) -> bool:
    try:
        metadata = root.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            return False
        observed = (
            metadata.st_dev,
            metadata.st_ino,
            stat.S_IFMT(metadata.st_mode),
            str(root.resolve(strict=True)),
        )
    except (OSError, ValueError):
        return False
    return observed == anchor


def _required_runtime_descriptor_matches(
    root: Path,
    descriptor: int,
    anchor: tuple[int, int, int, str],
) -> bool:
    """Bind a descriptor-backed traversal path to the caller-held root."""

    try:
        anchored = os.fstat(descriptor)
        observed = root.stat()
    except (OSError, ValueError):
        return False
    expected_identity = anchor[:3]
    return (
        stat.S_ISDIR(anchored.st_mode)
        and stat.S_ISDIR(observed.st_mode)
        and (
            anchored.st_dev,
            anchored.st_ino,
            stat.S_IFMT(anchored.st_mode),
        )
        == expected_identity
        == (
            observed.st_dev,
            observed.st_ino,
            stat.S_IFMT(observed.st_mode),
        )
    )


def _required_runtime_observation_matches(
    root: Path,
    anchor: tuple[int, int, int, str],
    descriptor: int | None,
) -> bool:
    if descriptor is None:
        return _required_runtime_root_matches(root, anchor)
    return _required_runtime_descriptor_matches(root, descriptor, anchor)


def _required_runtime_root_failure_report(
    packages: Sequence[str],
    *,
    code: str = "RUNTIME_ROOT_UNSAFE",
    message: str = "Корень runtime-проверки небезопасен, слишком широк или недоступен.",
) -> dict[str, Any]:
    finding = _finding(
        "error",
        code,
        message,
        path="runtime",
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_profile": "runtime",
        "validation_coverage": {
            "evals": "not_checked",
            "runtime_self_containment": "not_checked",
            "public_source_safety": "not_checked",
            "public_repository_safety": "not_checked",
        },
        "source_release_eligible": False,
        "status": "fail",
        "expected_package_count": len(packages),
        "validated_package_count": 0,
        "validated_packages": [],
        "summary": {"errors": 1, "warnings": 0},
        "findings": [finding],
        "runtime_content": {
            "algorithm": RUNTIME_CONTENT_ALGORITHM,
            "tree_sha256": None,
            "total_files": 0,
            "total_bytes": 0,
        },
        "freshness": {
            "status": "unknown",
            "reason_code": "local_identity_unavailable",
            "remote_main_sha": None,
            "local_tree_sha256": None,
            "remote_tree_sha256": None,
        },
        "publish_manifest": None,
    }


def validate_skillset(
    skills_root: str | Path,
    *,
    package_names: Sequence[str] = CANONICAL_KSRF_PACKAGES,
    profile: str = "source",
    check_updates: bool = False,
    require_current: bool = False,
    expected_runtime_root_anchor: tuple[int, int, int, str] | None = None,
    expected_runtime_root_descriptor: int | None = None,
    preserve_relative_runtime_root: bool = False,
) -> dict[str, Any]:
    """Validate packages and return a JSON-serializable evidence report."""

    if profile not in VALIDATION_PROFILES:
        raise ValueError(
            f"unknown validation profile {profile!r}; expected source or runtime"
        )
    requested_root = Path(skills_root).expanduser()
    if preserve_relative_runtime_root:
        if requested_root != Path("."):
            raise ValueError(
                "preserved relative runtime root must be the held working directory"
            )
        root = requested_root
    else:
        root = requested_root.absolute()
    packages = tuple(package_names)
    if require_current and not check_updates:
        raise ValueError("require_current requires check_updates")
    if check_updates and (
        profile != "runtime" or not _is_complete_canonical_scope(packages)
    ):
        raise ValueError(
            "check_updates requires the runtime profile and complete canonical package scope"
        )
    if expected_runtime_root_anchor is not None:
        valid_expected_anchor = (
            isinstance(expected_runtime_root_anchor, tuple)
            and len(expected_runtime_root_anchor) == 4
            and all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in expected_runtime_root_anchor[:3]
            )
            and isinstance(expected_runtime_root_anchor[3], str)
            and bool(expected_runtime_root_anchor[3])
        )
        if (
            not valid_expected_anchor
            or profile != "runtime"
            or not _is_complete_canonical_scope(packages)
        ):
            raise ValueError(
                "expected runtime root anchor requires the complete runtime profile"
            )
    if expected_runtime_root_descriptor is not None and (
        expected_runtime_root_anchor is None
        or not isinstance(expected_runtime_root_descriptor, int)
        or isinstance(expected_runtime_root_descriptor, bool)
        or expected_runtime_root_descriptor < 0
    ):
        raise ValueError(
            "expected runtime root descriptor requires a valid expected root anchor"
        )
    if preserve_relative_runtime_root and expected_runtime_root_descriptor is None:
        raise ValueError(
            "preserved relative runtime root requires a held root descriptor"
        )
    required_root_anchor: tuple[int, int, int, str] | None = None
    if expected_runtime_root_anchor is not None:
        required_root_anchor = expected_runtime_root_anchor
        if not _required_runtime_observation_matches(
            root,
            required_root_anchor,
            expected_runtime_root_descriptor,
        ):
            return _required_runtime_root_failure_report(
                packages,
                code="RUNTIME_ROOT_CHANGED",
                message="Корень runtime-проверки изменился после исходного наблюдения.",
            )
    elif require_current:
        try:
            required_root_anchor = _required_runtime_root_anchor(root)
        except (OSError, ValueError):
            return _required_runtime_root_failure_report(packages)
    findings: list[dict[str, Any]] = []
    if yaml is None:
        findings.append(
            _finding(
                "error",
                "YAML_PARSER_UNAVAILABLE",
                "PyYAML недоступен; строгая YAML-проверка остановлена, установка не выполнялась.",
            )
        )
    if len(packages) != len(set(packages)):
        findings.append(
            _finding(
                "error",
                "PACKAGE_ALLOWLIST_DUPLICATE",
                "В allowlist пакетов есть повторения.",
            )
        )
    _validate_unique_skill_entrypoints(findings, root, packages)
    validated_packages: list[str] = []
    for package in packages:
        package_dir = root / package
        if not package_dir.is_dir():
            findings.append(
                _finding(
                    "error",
                    "PACKAGE_MISSING",
                    "Ожидаемый KSRF skill package отсутствует.",
                    package=package,
                    path=package,
                )
            )
            continue
        validated_packages.append(package)
        _validate_skill_file(findings, package_dir, root)
        _validate_agent_metadata(findings, package_dir, root)
        if profile == "source":
            _validate_behavioral_evals(findings, package_dir, root)
            _validate_trigger_evals(findings, package_dir, root)
        else:
            _validate_runtime_profile_cleanliness(findings, package_dir, root)
        _validate_runtime_self_containment(findings, package_dir, root)
        _validate_markdown_links(findings, package_dir, root)
        _validate_reference_tocs(findings, package_dir, root)
        _validate_application_evidence_contract(findings, package_dir, root)
        _validate_argument_graph_contract(findings, package_dir, root)
        _validate_authority_corpus_contract(findings, package_dir, root)
        _validate_markdown_mcp_references(findings, package_dir, root)
    public_source_safety = "not_checked"
    public_repository_safety = "not_checked"
    if profile == "source":
        public_source_safety, public_repository_safety = (
            _validate_source_public_safety(
                findings,
                root,
                packages,
            )
        )
    manifest = _build_publish_manifest(
        findings,
        root,
        packages,
        validation_profile=profile,
    )
    runtime_content = _runtime_content_identity(
        findings,
        root,
        packages,
        manifest["files"],
        validation_profile=profile,
    )
    if (
        required_root_anchor is not None
        and not _required_runtime_observation_matches(
            root,
            required_root_anchor,
            expected_runtime_root_descriptor,
        )
    ):
        findings.append(
            _finding(
                "error",
                "RUNTIME_ROOT_CHANGED",
                "Корень runtime-проверки был заменён во время проверки.",
                path="runtime",
            )
        )
        runtime_content = {**runtime_content, "tree_sha256": None}
    freshness = _runtime_freshness(
        runtime_content,
        check_updates=check_updates,
    )
    if require_current and freshness["status"] == "current":
        post_network_findings: list[dict[str, Any]] = []
        post_network_content = _runtime_content_identity(
            post_network_findings,
            root,
            packages,
            manifest["files"],
            validation_profile=profile,
        )
        if post_network_findings or post_network_content != runtime_content:
            findings.extend(post_network_findings)
            if not post_network_findings:
                findings.append(
                    _finding(
                        "error",
                        "RUNTIME_IDENTITY_CHANGED",
                        "Runtime-дерево изменилось во время сетевой проверки актуальности.",
                        path="runtime",
                    )
                )
            runtime_content = {
                **runtime_content,
                "tree_sha256": None,
            }
            freshness.update(
                status="unknown",
                reason_code="local_identity_unavailable",
                local_tree_sha256=None,
            )
    elif expected_runtime_root_anchor is not None:
        final_findings: list[dict[str, Any]] = []
        final_content = _runtime_content_identity(
            final_findings,
            root,
            packages,
            manifest["files"],
            validation_profile=profile,
        )
        if final_findings or final_content != runtime_content:
            findings.extend(final_findings)
            if not final_findings and not any(
                item.get("code") == "RUNTIME_IDENTITY_CHANGED"
                for item in findings
            ):
                findings.append(
                    _finding(
                        "error",
                        "RUNTIME_IDENTITY_CHANGED",
                        "Runtime-дерево изменилось между проходами проверки.",
                        path="runtime",
                    )
                )
            runtime_content = {
                **runtime_content,
                "tree_sha256": None,
            }
            freshness.update(
                status="unknown" if check_updates else "not_checked",
                reason_code=(
                    "local_identity_unavailable"
                    if check_updates
                    else "not_requested"
                ),
                local_tree_sha256=None,
            )
    if (
        required_root_anchor is not None
        and not _required_runtime_observation_matches(
            root,
            required_root_anchor,
            expected_runtime_root_descriptor,
        )
    ):
        if not any(
            item.get("code") == "RUNTIME_ROOT_CHANGED"
            for item in findings
        ):
            findings.append(
                _finding(
                    "error",
                    "RUNTIME_ROOT_CHANGED",
                    "Корень runtime-проверки был заменён во время проверки.",
                    path="runtime",
                )
            )
        runtime_content = {**runtime_content, "tree_sha256": None}
        freshness.update(
            status="unknown",
            reason_code="local_identity_unavailable",
            local_tree_sha256=None,
        )
    severity_order = {"error": 0, "warning": 1}
    findings.sort(
        key=lambda item: (
            severity_order.get(str(item.get("severity")), 9),
            str(item.get("package", "")),
            str(item.get("path", "")),
            int(item.get("line", 0)),
            str(item.get("code", "")),
        )
    )
    error_count = sum(item["severity"] == "error" for item in findings)
    warning_count = sum(item["severity"] == "warning" for item in findings)
    source_release_eligible = (
        profile == "source"
        and _is_complete_canonical_scope(packages)
        and len(validated_packages) == len(packages)
        and public_source_safety == "validated"
        and public_repository_safety == "validated"
        and error_count == 0
        and warning_count == 0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_profile": profile,
        "validation_coverage": {
            "evals": "validated" if profile == "source" else "not_checked",
            "runtime_self_containment": "validated",
            "public_source_safety": public_source_safety,
            "public_repository_safety": public_repository_safety,
        },
        "source_release_eligible": source_release_eligible,
        "status": "fail" if error_count else "pass",
        "expected_package_count": len(packages),
        "validated_package_count": len(validated_packages),
        "validated_packages": validated_packages,
        "summary": {"errors": error_count, "warnings": warning_count},
        "findings": findings,
        "runtime_content": runtime_content,
        "freshness": freshness,
        "publish_manifest": manifest if profile == "source" else None,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _render_text(
    report: Mapping[str, Any],
    *,
    require_current: bool = False,
    strict: bool = False,
) -> str:
    summary = report["summary"]
    validation_failed = report["status"] != "pass" or (
        strict and bool(summary["warnings"])
    )
    status = "НЕ ПРОЙДЕНО" if validation_failed else "ПРОЙДЕНО"
    profile = str(report["validation_profile"])
    runtime_content = report["runtime_content"]
    local_tree_sha256 = runtime_content["tree_sha256"]
    heading = f"Проверка KSRF skillset: {status}"
    if require_current and not validation_failed:
        current_headings = {
            "current": "ЛОКАЛЬНЫЙ ОТПЕЧАТОК СОВПАДАЕТ С МАНИФЕСТОМ MAIN",
            "different": "СОДЕРЖИМОЕ ОТЛИЧАЕТСЯ",
            "unknown": "АКТУАЛЬНОСТЬ НЕ УСТАНОВЛЕНА",
        }
        freshness_status = report["freshness"].get("status")
        current_heading = current_headings.get(
            freshness_status,
            "РЕЗУЛЬТАТ АКТУАЛЬНОСТИ НЕ ПОЛУЧЕН",
        )
        heading = f"Проверка установленного набора: {current_heading}"
    lines = [
        heading,
        (
            f"Профиль: {profile}; evals: "
            f"{report['validation_coverage']['evals']}; "
            "runtime self-containment: "
            f"{report['validation_coverage']['runtime_self_containment']}; "
            "public-source safety: "
            f"{report['validation_coverage']['public_source_safety']}; "
            "public-repository safety: "
            f"{report['validation_coverage']['public_repository_safety']}; "
            "source/release QA: "
            f"{'полностью подтверждено' if report['source_release_eligible'] else 'не подтверждено'}."
        ),
        (
            f"Пакеты: {report['validated_package_count']}/"
            f"{report['expected_package_count']}; ошибок: {summary['errors']}; "
            f"предупреждений: {summary['warnings']}."
        ),
    ]
    if isinstance(local_tree_sha256, str):
        lines.append(
            "Отпечаток runtime-содержимого: "
            f"{local_tree_sha256} ({runtime_content['total_files']} файлов; "
            f"{runtime_content['total_bytes']} байт)."
        )
    else:
        lines.append(
            "Отпечаток runtime-содержимого не сформирован: дерево изменилось "
            "или было недоступно при проверке."
        )
    if profile == "runtime":
        freshness = report["freshness"]
        freshness_status = freshness["status"]
        if freshness_status == "current":
            lines.append(
                "Актуальность установленного набора: локальный runtime-отпечаток "
                "совпадает с манифестом commit "
                f"{freshness['remote_main_sha']}; это не доказывает происхождение установки."
            )
        elif freshness_status == "different":
            lines.append(
                "Актуальность установленного набора: локальный runtime-отпечаток "
                "отличается от манифеста commit "
                f"{freshness['remote_main_sha']}; набор может быть старым, настроенным, "
                "более новым/неопубликованным или локально изменённым."
            )
        elif freshness_status == "unknown":
            reason = _FRESHNESS_REASON_LABELS.get(
                str(freshness["reason_code"]),
                "причина не распознана",
            )
            lines.append(
                "Актуальность установленного набора не установлена: проверка не получила достаточных "
                f"данных ({reason})."
            )
        else:
            lines.append(
                "Актуальность установленного набора по сети не проверялась; "
                "для явной проверки добавьте "
                "--check-updates."
            )
        lines.append(
            "Runtime-проверка не заменяет source/release QA и не даёт полномочий на публикацию."
        )
        lines.append(
            "Совпадение набора не подтверждает актуальность права и практики "
            "или готовность конкретной жалобы к подаче."
        )
    for item in report["findings"]:
        location = str(item.get("path") or item.get("package") or "skillset")
        if item.get("line"):
            location += f":{item['line']}"
        label = "ОШИБКА" if item["severity"] == "error" else "ПРЕДУПРЕЖДЕНИЕ"
        lines.append(f"- {label} {item['code']} [{location}]: {item['message']}")
    return "\n".join(lines) + "\n"


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        description="Проверить canonical KSRF skills и собрать безопасный publish manifest."
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Корень глобальных skills.",
    )
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="Проверить указанный пакет; параметр можно повторять.",
    )
    parser.add_argument("--json", action="store_true", help="Вывести полный JSON-отчёт.")
    parser.add_argument("--report-out", type=Path, help="Сохранить полный JSON-отчёт.")
    parser.add_argument("--manifest-out", type=Path, help="Сохранить только publish manifest.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Считать предупреждения ненулевым результатом процесса.",
    )
    parser.add_argument(
        "--profile",
        choices=VALIDATION_PROFILES,
        default="source",
        help=(
            "Профиль проверки: source требует evals и пригоден для release QA; "
            "runtime проверяет установленное дерево без source-only assets."
        ),
    )
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help=(
            "В runtime-профиле сравнить локальный отпечаток с manifest текущего "
            "canonical main; сеть используется только по этому явному флагу."
        ),
    )
    parser.add_argument(
        "--require-current",
        action="store_true",
        help=(
            "Вместе с полной runtime-проверкой вернуть 10, если содержимое "
            "отличается от текущего main, и 20, если актуальность не установлена."
        ),
    )
    args = parser.parse_args(argv)
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    if args.profile == "runtime" and args.manifest_out:
        errors.write(
            "Runtime-профиль не создаёт standalone publish manifest; "
            "используйте полный JSON-отчёт или source-профиль.\n"
        )
        return 2
    if args.require_current and args.report_out:
        errors.write(
            "--require-current нельзя сочетать с --report-out; используйте stdout.\n"
        )
        return 2
    requested_packages = (
        tuple(args.packages) if args.packages else CANONICAL_KSRF_PACKAGES
    )
    if args.require_current and (
        not args.check_updates
        or args.profile != "runtime"
        or not _is_complete_canonical_scope(requested_packages)
    ):
        errors.write(
            "--require-current требует --check-updates, runtime-профиль и "
            "полный canonical набор KSRF-пакетов.\n"
        )
        return 2
    if args.check_updates and (
        args.profile != "runtime"
        or not _is_complete_canonical_scope(requested_packages)
    ):
        errors.write(
            "--check-updates доступен только для runtime-профиля и полного "
            "canonical набора KSRF-пакетов.\n"
        )
        return 2
    try:
        report = validate_skillset(
            args.skills_root,
            package_names=requested_packages,
            profile=args.profile,
            check_updates=args.check_updates,
            require_current=args.require_current,
        )
        if args.report_out:
            _write_json(args.report_out, report)
        if args.manifest_out:
            _write_json(args.manifest_out, report["publish_manifest"])
        if args.json:
            json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
        else:
            output.write(
                _render_text(
                    report,
                    require_current=args.require_current,
                    strict=args.strict and args.require_current,
                )
            )
        if report["status"] == "fail":
            return 1
        if args.strict and report["summary"]["warnings"]:
            return 1
        if args.require_current:
            freshness_exit_codes = {
                "current": 0,
                "different": 10,
                "unknown": 20,
            }
            freshness_status = report["freshness"].get("status")
            if freshness_status not in freshness_exit_codes:
                errors.write(
                    "Требуемый результат актуальности не получен; "
                    "положительный код не выдан.\n"
                )
                return 2
            return freshness_exit_codes[freshness_status]
        return 0
    except Exception as exc:  # fail closed for unexpected packaging errors
        errors.write(f"Валидатор остановлен без публикации: {type(exc).__name__}: {exc}\n")
        return 2


def _entrypoint() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == _FRESHNESS_HTTP_HELPER_FLAG:
        return _freshness_http_helper_main(tuple(sys.argv[2:]))
    return main()


if __name__ == "__main__":
    raise SystemExit(_entrypoint())
