#!/usr/bin/env python3
"""Build reproducible applicant plugins from the canonical runtime file contract."""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Sequence
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

from skillset_file_contract import (
    FileContractError, SKILL_NAMES, TOKEN_LITERAL, PRIVATE_KEY_MARKER,
    ABSOLUTE_LOCAL_PATH_PATTERNS, payload_files, validate_public_repository,
)
from verify_publication_state import PublicationStateError, verify_publication_state

NAME = "ksrf-applicant"
SOURCE_URL = "https://github.com/aegorfk/ksrf-skillset"
SUPPORT_FILES = (
    "README.md", "PRIVACY.md", "SURFACES.md", "SUPPORT.md", "TERMS.md", "use-cases.json", "verify.py",
    "assets/applicant.svg",
    "environment/Dockerfile", "environment/Dockerfile.dockerignore", "environment/README.md", "environment/smoke.py", "environment/soffice.py",
)
BRANDING_ASSET = "./assets/applicant.svg"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_ATTRIBUTES = {
    "svg": {"width", "height", "viewBox", "fill", "stroke", "stroke-width"},
    "g": {"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "transform"},
    "path": {"d", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "fill-rule", "transform"},
    "rect": {"x", "y", "width", "height", "rx", "ry", "fill", "stroke", "stroke-width", "transform"},
    "circle": {"cx", "cy", "r", "fill", "stroke", "stroke-width", "transform"},
    "ellipse": {"cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width", "transform"},
    "line": {"x1", "y1", "x2", "y2", "stroke", "stroke-width", "stroke-linecap", "transform"},
    "polyline": {"points", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "transform"},
    "polygon": {"points", "fill", "stroke", "stroke-width", "stroke-linejoin", "transform"},
    "title": set(), "desc": set(),
}
SVG_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
SENSITIVE_KEY_ENDINGS = (
    "apikey", "accesstoken", "authtoken", "bearertoken", "clientsecret",
    "secretkey", "password", "passwd",
)
EXPLICIT_PLACEHOLDER = re.compile(
    r"(?:<[^<>\r\n]+>|\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*|"
    r"(?:your|replace|insert)[_ -](?:api[_ -]?key|access[_ -]?token|secret|password)(?:[_ -]here)?|"
    r"(?:example|placeholder|redacted|dummy)(?:[_ -](?:value|key|token|secret|password))?|"
    r"test[_ -](?:value|key|token|secret|password)|replace_me|change_me|changeme)", re.IGNORECASE,
)
TEXT_ASSIGNMENT = re.compile(
    r"^\s*(?:[-*]\s+)?(?:export\s+)?[\"']?"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)[\"']?\s*[:=]\s*"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s#,;\r\n]+)"
    r"\s*[,;]?\s*(?:#.*)?$", re.MULTILINE,
)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def source_revision(repo: Path) -> dict:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    commit = git("rev-parse", "HEAD")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Source is not a Git commit")
    return {"repository": SOURCE_URL, "commit": commit,
            "working_tree_modified": bool(git("status", "--porcelain"))}


def sensitive_key(name: object) -> bool:
    if not isinstance(name, str):
        return False
    normalized = re.sub(r"[_.-]", "", name).casefold()
    return normalized in {"secret", "token"} or normalized.endswith(SENSITIVE_KEY_ENDINGS)


def credential_literal(value: object) -> bool:
    """Detect plausible literal credentials, not every possible secret encoding."""
    if not isinstance(value, (str, bytes)):
        return False
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    text = text.strip()
    return len(text) >= 12 and not EXPLICIT_PLACEHOLDER.fullmatch(text)


def python_target_name(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
        return target.slice.value if isinstance(target.slice.value, str) else None
    return None


def env_reference(expression: str) -> bool:
    """Allow pure documented environment lookups, never a literal fallback."""
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return False
    if isinstance(node, ast.Subscript):
        return (isinstance(node.value, ast.Attribute) and node.value.attr == "environ"
                and isinstance(node.value.value, ast.Name) and node.value.value.id == "os"
                and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str))
    if isinstance(node, ast.Call) and len(node.args) == 1 and not node.keywords:
        return (ast.unparse(node.func) in {"os.getenv", "os.environ.get"}
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str))
    return False


def has_literal_credential(text: str, suffix: str) -> bool:
    if suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            raise ValueError("Cannot inspect invalid Python package input") from None
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if isinstance(node.value, ast.Constant) and credential_literal(node.value.value):
                    if any(sensitive_key(python_target_name(target)) for target in targets):
                        return True
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (isinstance(key, ast.Constant) and sensitive_key(key.value)
                            and isinstance(value, ast.Constant) and credential_literal(value.value)):
                        return True
        return False
    if suffix == ".json":
        def inspect(value: object) -> bool:
            if isinstance(value, dict):
                return any((sensitive_key(key) and credential_literal(item)) or inspect(item)
                           for key, item in value.items())
            return isinstance(value, list) and any(inspect(item) for item in value)
        return inspect(json.loads(text))
    # Text examples and YAML are inspected conservatively without executing or
    # depending on a YAML parser; quoted literals and simple bare values count.
    for match in TEXT_ASSIGNMENT.finditer(text):
        if not sensitive_key(match["key"]):
            continue
        raw = match["value"]
        quoted = raw[:1] in {"'", '"'}
        value = raw[1:-1] if quoted else raw
        if credential_literal(value) and (quoted or not env_reference(value)):
            return True
    return False


def read_safe(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or symlinked package input: {path.name}")
    data = path.read_bytes()
    text = data.decode("utf-8")
    if (TOKEN_LITERAL.search(text) or PRIVATE_KEY_MARKER.search(text)
            or any(pattern.search(text) for pattern in ABSOLUTE_LOCAL_PATH_PATTERNS)
            or has_literal_credential(text, path.suffix.lower())):
        raise ValueError(f"Private path or credential in package input: {path.name}")
    return data


def validate_listing(metadata: object) -> None:
    """Check public-directory text and the single supported branding path.

    Limits: https://developers.openai.com/plugins/deploy/submission-errors.
    Publisher identity verification remains a portal operation, not a local claim.
    """
    if not isinstance(metadata, dict):
        raise ValueError("Plugin metadata must be an object")
    interface = metadata.get("interface")
    if not isinstance(interface, dict):
        raise ValueError("Plugin interface must be an object")

    def text_field(value: object, name: str, limit: int, multiline: bool = False) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"Invalid {name}: required text, at most {limit} characters")
        if any((ord(char) < 32 or ord(char) == 127) and not (multiline and char in "\n\r\t") for char in value):
            raise ValueError(f"Invalid control character in {name}")
        if not multiline and any(char in "\r\n\v\f\x85\u2028\u2029" for char in value):
            raise ValueError(f"{name} must be single-line")
        return value

    for field, limit in (("displayName", 30), ("shortDescription", 30), ("developerName", 80)):
        text_field(interface.get(field), field, limit)
    text_field(interface.get("longDescription"), "longDescription", 4000, multiline=True)
    prompts = interface.get("defaultPrompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]
    if not isinstance(prompts, list) or len(prompts) > 3:
        raise ValueError("defaultPrompt must contain at most three prompts")
    normalized = []
    for prompt in prompts:
        value = text_field(prompt, "defaultPrompt", 128)
        if "@" in value:
            raise ValueError("Starter prompts must not contain MCP server mentions")
        normalized.append(" ".join(unicodedata.normalize("NFKC", value).split()))
    if len(normalized) != len(set(normalized)):
        raise ValueError("Starter prompts must be distinct after normalization")
    for field in ("logo", "composerIcon"):
        if interface.get(field) != BRANDING_ASSET:
            raise ValueError(f"{field} must reference the bundled {BRANDING_ASSET}")


def validate_branding_svg(data: bytes) -> None:
    """Permit only inert geometry in the bundled applicant icon, never active SVG."""
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("Branding SVG exceeds 5 MiB")
    text = data.decode("utf-8")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)|<\?(?!xml(?:\s|\?))", text, re.IGNORECASE):
        raise ValueError("SVG declarations, entities, and processing instructions are not permitted")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError("Branding SVG is not valid XML") from exc
    if root.tag != f"{{{SVG_NAMESPACE}}}svg":
        raise ValueError("Branding SVG must have a namespaced svg root")

    def number(value: str) -> float:
        if not re.fullmatch(SVG_NUMBER, value):
            raise ValueError("SVG dimensions must be unitless finite numbers")
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("SVG dimensions must be finite")
        return result

    geometry: list[tuple[float, float]] = []
    if "width" in root.attrib or "height" in root.attrib:
        geometry.append((number(root.get("width", "")), number(root.get("height", ""))))
    if "viewBox" in root.attrib:
        parts = re.split(r"[\s,]+", root.attrib["viewBox"].strip())
        if len(parts) != 4:
            raise ValueError("SVG viewBox must contain four numbers")
        numbers = [number(part) for part in parts]
        geometry.append((numbers[2], numbers[3]))
    if not geometry or any(width < 48 or width != height for width, height in geometry):
        raise ValueError("Branding SVG must be square and at least 48 units wide")

    for element in root.iter():
        if not isinstance(element.tag, str) or not element.tag.startswith(f"{{{SVG_NAMESPACE}}}"):
            raise ValueError("Unexpected SVG namespace")
        tag = element.tag.split("}", 1)[1]
        if tag not in SVG_ATTRIBUTES or set(element.attrib) - SVG_ATTRIBUTES[tag]:
            raise ValueError("Unexpected or active SVG element/attribute")
        if element is not root and tag == "svg":
            raise ValueError("Nested SVG viewports are not supported")
        if tag not in {"title", "desc"} and (element.text or "").strip():
            raise ValueError("Unexpected SVG text")
        if (element.tail or "").strip():
            raise ValueError("Unexpected SVG tail text")
        for attribute, value in element.attrib.items():
            if attribute in {"fill", "stroke"}:
                valid = bool(re.fullmatch(r"(?:#[0-9A-Fa-f]{3}|#[0-9A-Fa-f]{6}|none|currentColor)", value))
            elif attribute == "stroke-linecap":
                valid = value in {"butt", "round", "square"}
            elif attribute == "stroke-linejoin":
                valid = value in {"miter", "round", "bevel"}
            elif attribute == "fill-rule":
                valid = value in {"nonzero", "evenodd"}
            elif attribute == "transform":
                valid = bool(re.fullmatch(r"\s*(?:(?:matrix|translate|scale|rotate|skewX|skewY)\([0-9eE+., \t-]+\)\s*)+", value))
            elif attribute == "d":
                valid = bool(re.fullmatch(r"[MmZzLlHhVvCcSsQqTtAa0-9eE+., \t\r\n-]+", value))
            elif attribute in {"points", "viewBox"}:
                valid = bool(re.fullmatch(r"[0-9eE+., \t\r\n-]+", value))
            else:
                number(value)
                valid = True
            if not valid:
                raise ValueError("Unsupported SVG geometry or resource reference")


def collect(repo: Path, variant: str) -> tuple[dict[str, bytes], dict]:
    if variant not in {"web", "desktop"}:
        raise ValueError("Unknown package variant")
    validate_public_repository(repo)
    metadata = json.loads(read_safe(repo / "plugin/manifest.json"))
    validate_listing(metadata)
    if metadata.get("name") != NAME or not re.fullmatch(r"\d+\.\d+\.\d+", metadata.get("version", "")):
        raise ValueError("Invalid plugin identity or version")
    if metadata.get("mcpServers") or metadata.get("apps"):
        raise ValueError("Do not imply configured external services in portable package")
    entries = {".codex-plugin/plugin.json": json_bytes(metadata), "LICENSE": read_safe(repo / "LICENSE")}
    for name in SKILL_NAMES:
        root = repo / "skills" / name
        if not (root / "SKILL.md").is_file():
            raise ValueError(f"Missing skill: {name}")
        for path in payload_files(root):
            rel = path.relative_to(repo).as_posix()
            entries[rel] = read_safe(path)
    for name in SUPPORT_FILES:
        destination = f"plugin/{name}" if name in {"README.md", "PRIVACY.md", "SURFACES.md", "SUPPORT.md", "TERMS.md", "use-cases.json"} else name
        content = read_safe(repo / "plugin" / name)
        if name == "assets/applicant.svg":
            validate_branding_svg(content)
        entries[destination] = content
    entries["README.md"] = ("# Обращение в КС РФ — помощь заявителю\n\n"
        "Начните с описания ситуации или документов. Попросите помощника: «Хочу обратиться в КС РФ. Помоги разобраться, с чего начать».\n\n"
        "[Как установить и начать](plugin/README.md) · [Браузер и настольное приложение](plugin/SURFACES.md) · "
        "[Документы и конфиденциальность](plugin/PRIVACY.md).\n\n"
        "Проверка файлов: `python3 verify.py`. Полный набор методологии, кода и схем находится в `skills/`. "
        "Подготовленный рабочий проект требует отдельной проверки; подписание, платёж и подача остаются за человеком.\n").encode()
    # Resources and code are portable; neither profile silently declares a local MCP server.
    entries["surface.json"] = json_bytes({
        "schema_version": 1, "variant": variant,
        "methodology": "all_packaged_skills", "runtime": "requires_host_execution",
        "local_state": "outside_plugin", "accounts_included": False,
        "hosted_endpoint": None, "catalog_approval": "not_implied_by_package",
        "default_profile": "basic", "filing_authority": False,
    })
    return entries, metadata


def inventory(entries: dict[str, bytes]) -> list[dict]:
    return [{"path": path, "bytes": len(data), "sha256": sha256(data).hexdigest()}
            for path, data in sorted(entries.items())]


def safe_destination(output: Path, repo: Path) -> Path:
    output = output.expanduser().absolute()
    for parent in [output, *output.parents]:
        if parent.is_symlink():
            raise ValueError("Symlinked output path is forbidden")
    resolved = output.resolve()
    home = Path.home().resolve()
    if resolved in {Path(resolved.anchor), home, repo.resolve()} or repo.resolve() in resolved.parents:
        raise ValueError("Output must be a fresh directory outside the source repository and home root")
    if output.exists():
        raise ValueError("Output already exists; use a new directory")
    return output


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, data in sorted(entries.items()):
            info = zipfile.ZipInfo(f"{NAME}/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 << 16)
            archive.writestr(info, data)


def build(repo: Path, output: Path, variants: Sequence[str] = ("web", "desktop"),
          *, require_clean: bool = False) -> dict:
    if repo.is_symlink():
        raise ValueError("Source root cannot be a symlink")
    repo = repo.resolve()
    output = safe_destination(output, repo)
    source = source_revision(repo)
    if require_clean and source["working_tree_modified"]:
        raise ValueError("Release packages require a clean published source checkout")
    publication = verify_publication_state(repo) if require_clean else None
    if not variants or len(set(variants)) != len(variants):
        raise ValueError("At least one unique variant is required")
    packages = {variant: collect(repo, variant) for variant in variants}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".ksrf-build-", dir=output.parent))
    reports = []
    try:
        for variant, (entries, metadata) in packages.items():
            manifest = {"schema_version": 1, "name": NAME, "version": metadata["version"],
                        "variant": variant, "source": source,
                        "published_source_verified": publication is not None,
                        "skills": sorted(SKILL_NAMES), "files": inventory(entries)}
            entries["distribution-manifest.json"] = json_bytes(manifest)
            root = temporary / variant / NAME
            for rel, data in sorted(entries.items()):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            archive_name = f"{NAME}-{variant}-{metadata['version']}.zip"
            archive_path = temporary / archive_name
            write_zip(archive_path, entries)
            reports.append({"variant": variant, "directory": f"{variant}/{NAME}",
                            "archive": archive_name, "sha256": sha256(archive_path.read_bytes()).hexdigest(),
                            "bytes": archive_path.stat().st_size, "skills": len(SKILL_NAMES),
                            "files": len(entries)})
        # The distributable repository is generated, never a second editable skill source.
        preferred = "web" if "web" in packages else next(iter(packages))
        marketplace = temporary / "marketplace"
        shutil.copytree(temporary / preferred / NAME, marketplace / "plugins" / NAME)
        catalog = marketplace / ".agents/plugins/marketplace.json"
        catalog.parent.mkdir(parents=True)
        catalog.write_bytes(json_bytes({
            "name": "ksrf-applicants",
            "interface": {"displayName": "Помощь заявителю в КС РФ"},
            "plugins": [{"name": NAME, "source": {"source": "local", "path": f"./plugins/{NAME}"},
                         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                         "category": "Productivity"}],
        }))
        (marketplace / "README.md").write_text(
            "# Обращение в КС РФ — помощь заявителю\n\n"
            "Плагин для людей, которые готовят обращение самостоятельно, и для юристов. "
            "Начать можно с обычного описания ситуации или документов.\n\n"
            "Включены все 16 навыков, методические материалы, схемы и исполняемый код. "
            "[Инструкция для ChatGPT и Codex](plugins/ksrf-applicant/plugin/README.md). "
            "[Возможности разных сред](plugins/ksrf-applicant/plugin/SURFACES.md).\n\n"
            "## Установка в Codex\n\n"
            "Попросите Codex: «Установи плагин ksrf-applicant из репозитория "
            "https://github.com/aegorfk/ksrf-applicant-plugin и помоги начать работу с моими документами».\n\n"
            "Для технической установки:\n\n```sh\n"
            "codex plugin marketplace add https://github.com/aegorfk/ksrf-applicant-plugin.git\n"
            "codex plugin add ksrf-applicant@ksrf-applicants\n```\n\n"
            "## ChatGPT в браузере\n\n"
            "В рабочем пространстве с импортом плагинов администратор может импортировать этот GitHub marketplace. "
            "Доступ к загрузке плагинов зависит от аккаунта и прав. Установка методологии не включает "
            "автоматически локальные программы, внешние аккаунты или размещённый сервер; "
            "[подробности](plugins/ksrf-applicant/plugin/SURFACES.md).\n\n"
            "## Источник\n\n"
            "Это автоматически собранная дистрибуция [канонического набора](https://github.com/aegorfk/ksrf-skillset). "
            "Версия исходников и хеш каждого файла записаны в "
            "[манифесте](plugins/ksrf-applicant/distribution-manifest.json). "
            "Файлы методологии изменяются в каноническом наборе.\n\n"
            "[Конфиденциальность](plugins/ksrf-applicant/plugin/PRIVACY.md). "
            "Плагин помогает подготовить и проверить проект; подписание, платёж, подача и юридическое одобрение остаются за человеком.\n",
            encoding="utf-8",
        )
        (marketplace / "LICENSE").write_bytes(read_safe(repo / "LICENSE"))
        # Source changed during a build: never label a mixture as a single revision.
        if source_revision(repo) != source:
            raise ValueError("Source revision/status changed during build; retry from a stable tree")
        for variant, (before, _) in packages.items():
            after, _ = collect(repo, variant)
            before_without_manifest = {k: v for k, v in before.items() if k != "distribution-manifest.json"}
            if after != before_without_manifest:
                raise ValueError("Source bytes changed during build; retry from a stable tree")
        if require_clean and verify_publication_state(repo) != publication:
            raise ValueError("Published source changed during build")
        result = {"schema_version": 1, "source": source, "packages": reports,
                  "marketplace_directory": "marketplace", "marketplace_name": "ksrf-applicants",
                  "scope": "software_distribution", "catalog_approval": "not_submitted"}
        (temporary / "build-report.json").write_bytes(json_bytes(result))
        (temporary / "SHA256SUMS").write_text("".join(f"{p['sha256']}  {p['archive']}\n" for p in reports))
        os.rename(temporary, output)
        return result
    except BaseException:
        shutil.rmtree(temporary)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Собрать полный плагин для заявителей в КС РФ.")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--variant", choices=("web", "desktop", "both"), default="both")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    try:
        result = build(args.repo, args.output, ("web", "desktop") if args.variant == "both" else (args.variant,),
                       require_clean=args.require_clean)
    except (ValueError, OSError, FileContractError, PublicationStateError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Сборка отклонена: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
