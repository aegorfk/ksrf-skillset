#!/usr/bin/env python3
"""Single file-selection contract for the public KSRF skillset payload."""

from __future__ import annotations

import argparse
import html
from hashlib import sha256
from pathlib import Path
import re
from typing import Iterable, Sequence


SKILL_NAMES = (
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

RUNTIME_PARTS = frozenset({".git", ".serena", ".pytest_cache", "__pycache__"})
DEVELOPMENT_ONLY_PARTS = frozenset({"evals", "tests"})
RUNTIME_NAMES = frozenset({".DS_Store"})
RUNTIME_SUFFIXES = frozenset({".pyc", ".pyo"})
SECRET_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "secrets.json",
        "token.json",
        "id_rsa",
        "id_ed25519",
    }
)
SECRET_SUFFIXES = frozenset({".pem", ".p12", ".pfx", ".key"})
FORBIDDEN_SOURCE_DOCUMENT_SUFFIXES = frozenset(
    {
        ".7z",
        ".bmp",
        ".doc",
        ".docm",
        ".docx",
        ".heic",
        ".jpeg",
        ".jpg",
        ".odt",
        ".pages",
        ".pdf",
        ".png",
        ".rar",
        ".rtf",
        ".tif",
        ".tiff",
        ".webp",
        ".zip",
    }
)
TEXT_REVIEW_SUFFIXES = frozenset({".html", ".json", ".md", ".ocr", ".txt", ".yaml", ".yml"})
FORBIDDEN_BINARY_SIGNATURES = (
    b"%PDF-",
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    b"PK\x03\x04",
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"II*\x00",
    b"MM\x00*",
    b"7z\xbc\xaf\x27\x1c",
    b"Rar!\x1a\x07",
)
APPROVED_SYNTHETIC_BINARY_FIXTURES = {
    "skills/ksrf-cassation-judicial-meaning/tests/fixtures/image_only.pdf": (
        "dea9e1253fc7b51e1608ff50d0eb14ca00f8e08e9e26b80428cb96af8e8d0d29"
    ),
}
COMPLAINT_STRUCTURE_PATTERNS = {
    "court": re.compile(
        r"^\s*(?:в\s+)?конституционн(?:ый|ого)\s+суд\s+российской\s+федерации\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "title": re.compile(r"^\s*жалоба(?:\s|$)", re.IGNORECASE | re.MULTILINE),
    "applicant": re.compile(r"^\s*заявител(?:ь|и)\s*:", re.IGNORECASE | re.MULTILINE),
    "representative": re.compile(
        r"^\s*представител(?:ь|и)(?:\s+заявител[ья])?\s*:",
        re.IGNORECASE | re.MULTILINE,
    ),
    "request": re.compile(
        r"^\s*(?:на\s+основании[^\n]{0,240})?прошу(?:\s+конституционный\s+суд[^\n]{0,160})?\s*:?[ \t]*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "attachments": re.compile(
        r"^\s*(?:приложения|перечень\s+прилагаемых\s+документов)\s*:",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# These files are mirrored from ksrf-argument-patterns/scripts into repo tools/.
# A rename/removal must move the old filename to RETIRED_MIRRORED_TOOL_NAMES so
# sync can remove only that explicitly owned stale mirror.
MIRRORED_TOOL_NAMES = (
    "build_constitutionalist_authority_corpus.py",
    "enrich_ksrf_argument_patterns.py",
    "extract_ksrf_argument_patterns.py",
)
RETIRED_MIRRORED_TOOL_NAMES: tuple[str, ...] = ()

# The manifest cannot hash itself, but it covers every executable release tool.
# Clean HEAD == live main additionally binds all other versioned documentation,
# tests and OpenSpec files to the published Git commit.
RELEASE_FILE_PATHS = (
    "install.sh",
    "tools/generate_skills_manifest.py",
    "tools/install_skillset.py",
    "tools/skillset_file_contract.py",
    "tools/sync_global_skills.sh",
    "tools/verify_publication_state.py",
    *(f"tools/{name}" for name in MIRRORED_TOOL_NAMES),
)


class FileContractError(RuntimeError):
    """A source tree cannot be represented by the public payload contract."""


def is_excluded(relative_path: Path, *, include_development: bool = False) -> bool:
    """Return whether a payload-relative file is runtime or secret material."""

    lowered = relative_path.name.lower()
    return (
        any(part in RUNTIME_PARTS for part in relative_path.parts)
        or (
            not include_development
            and any(part in DEVELOPMENT_ONLY_PARTS for part in relative_path.parts)
        )
        or relative_path.name in RUNTIME_NAMES
        or relative_path.suffix.lower() in RUNTIME_SUFFIXES
        or lowered in SECRET_NAMES
        or (lowered.startswith(".env.") and lowered != ".env.example")
        or relative_path.suffix.lower() in SECRET_SUFFIXES
    )


def _decode_review_text(content: bytes) -> str:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("cp1251", errors="replace")
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _looks_like_reproduced_complaint(content: bytes) -> bool:
    text = _decode_review_text(content)
    markers = {
        name for name, pattern in COMPLAINT_STRUCTURE_PATTERNS.items() if pattern.search(text)
    }
    return (
        len(markers) >= 4
        or {"court", "title", "applicant"}.issubset(markers)
        or {"court", "title", "request"}.issubset(markers)
    )


def validate_public_artifact(path: Path, relative_path: Path) -> None:
    """Reject source complaints and reconstructive derivatives from public payloads."""

    content = path.read_bytes()
    identity = relative_path.as_posix()
    suffix = path.suffix.lower()
    binary_source = suffix in FORBIDDEN_SOURCE_DOCUMENT_SUFFIXES or any(
        content.startswith(signature) for signature in FORBIDDEN_BINARY_SIGNATURES
    )
    if binary_source:
        approved_digest = APPROVED_SYNTHETIC_BINARY_FIXTURES.get(identity)
        actual_digest = sha256(content).hexdigest()
        if approved_digest == actual_digest:
            return
        if approved_digest is not None:
            raise FileContractError(
                f"approved synthetic fixture changed content and is blocked: {relative_path}"
            )
        raise FileContractError(
            "source documents are forbidden in the public KSRF repository: "
            f"{relative_path}; publish only a non-reconstructive method card, synthetic eval "
            "and active external source links"
        )
    if suffix in TEXT_REVIEW_SUFFIXES and _looks_like_reproduced_complaint(content):
        raise FileContractError(
            "complaint-like full text is forbidden in the public KSRF repository: "
            f"{relative_path}; replace it with a non-reconstructive method card"
        )


def validate_public_repository(root: Path) -> None:
    """Validate every non-runtime artifact before a public manifest is generated."""

    if root.is_symlink():
        raise FileContractError(f"symlinked repository root is forbidden: {root}")
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if is_excluded(relative, include_development=True):
            continue
        if path.is_symlink():
            raise FileContractError(f"symlink inside payload tree is forbidden: {path}")
        if path.is_file():
            validate_public_artifact(path, relative)

def payload_files(root: Path, *, include_development: bool = False) -> list[Path]:
    """Return the exact sorted file payload covered by skill manifests/copies."""

    if root.is_symlink():
        raise FileContractError(f"symlinked payload root is forbidden: {root}")
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise FileContractError(f"symlink inside payload tree is forbidden: {path}")
        relative = path.relative_to(root)
        if path.is_file() and not is_excluded(
            relative, include_development=include_development
        ):
            validate_public_artifact(path, Path("skills") / root.name / relative)
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def development_files(root: Path) -> list[Path]:
    """Return safe source-only files that a reverse sync must preserve in-place."""

    return [
        path
        for path in payload_files(root, include_development=True)
        if any(
            part in DEVELOPMENT_ONLY_PARTS
            for part in path.relative_to(root).parts
        )
    ]


def tree_digest(root: Path, files: Iterable[Path]) -> str:
    digest = sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print versioned KSRF file-contract values.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--active-mirrored-tools", action="store_true")
    group.add_argument("--retired-mirrored-tools", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    names = MIRRORED_TOOL_NAMES if args.active_mirrored_tools else RETIRED_MIRRORED_TOOL_NAMES
    for name in names:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
