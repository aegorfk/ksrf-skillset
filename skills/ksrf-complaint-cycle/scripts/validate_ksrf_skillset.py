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
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:  # pragma: no cover - exercised as a fail-closed runtime path
    yaml = None


SCHEMA_VERSION = "1.0.0"
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

RUNTIME_PARTS = {".git", ".serena", ".pytest_cache", "__pycache__"}
DEVELOPMENT_ONLY_PARTS = {"evals", "tests"}
ROOT_ONLY_TOOL_SKILL_PATHS = frozenset(
    {
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
ABSOLUTE_RUNTIME_PATTERNS = (
    re.compile(
        "/" + r"Users/[A-Za-z0-9._-]+/(?:Documents|Desktop|Downloads|Library|\.codex)/[^\s`\"']+"
    ),
    re.compile(
        "/" + r"home/[A-Za-z0-9._-]+/(?:Documents|Desktop|Downloads|\.config|\.local)/[^\s`\"']+"
    ),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\[^\s`\"']+"),
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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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


def _runtime_artifact(path: Path) -> bool:
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


def _development_artifact(path: Path) -> bool:
    return is_source_only_artifact(path)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(pattern.search(line) for pattern in ABSOLUTE_RUNTIME_PATTERNS):
            findings.append(
                _finding(
                    "error",
                    "ABSOLUTE_RUNTIME_PATH",
                    "Публикуемый текст содержит абсолютный локальный runtime path.",
                    package=package,
                    path=relative_path,
                    line=line_number,
                )
            )
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
            if _runtime_artifact(relative_object):
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


def validate_skillset(
    skills_root: str | Path,
    *,
    package_names: Sequence[str] = CANONICAL_KSRF_PACKAGES,
    profile: str = "source",
) -> dict[str, Any]:
    """Validate packages and return a JSON-serializable evidence report."""

    if profile not in VALIDATION_PROFILES:
        raise ValueError(
            f"unknown validation profile {profile!r}; expected source or runtime"
        )
    root = Path(skills_root).expanduser().absolute()
    packages = tuple(package_names)
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
        _validate_markdown_links(findings, package_dir, root)
        _validate_reference_tocs(findings, package_dir, root)
        _validate_application_evidence_contract(findings, package_dir, root)
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
        and packages == CANONICAL_KSRF_PACKAGES
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


def _render_text(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    status = "ПРОЙДЕНО" if report["status"] == "pass" else "НЕ ПРОЙДЕНО"
    profile = str(report["validation_profile"])
    lines = [
        f"Проверка KSRF skillset: {status}",
        (
            f"Профиль: {profile}; evals: "
            f"{report['validation_coverage']['evals']}; "
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
    if profile == "runtime":
        lines.append(
            "Runtime-проверка не заменяет source/release QA и не даёт полномочий на публикацию."
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
    args = parser.parse_args(argv)
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    if args.profile == "runtime" and args.manifest_out:
        errors.write(
            "Runtime-профиль не создаёт standalone publish manifest; "
            "используйте полный JSON-отчёт или source-профиль.\n"
        )
        return 2
    try:
        report = validate_skillset(
            args.skills_root,
            package_names=tuple(args.packages) if args.packages else CANONICAL_KSRF_PACKAGES,
            profile=args.profile,
        )
        if args.report_out:
            _write_json(args.report_out, report)
        if args.manifest_out:
            _write_json(args.manifest_out, report["publish_manifest"])
        if args.json:
            json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
        else:
            output.write(_render_text(report))
        if report["status"] == "fail":
            return 1
        if args.strict and report["summary"]["warnings"]:
            return 1
        return 0
    except Exception as exc:  # fail closed for unexpected packaging errors
        errors.write(f"Валидатор остановлен без публикации: {type(exc).__name__}: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
