#!/usr/bin/env python3
"""Single file-selection contract for the public KSRF skillset payload."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
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


def is_excluded(relative_path: Path) -> bool:
    """Return whether a payload-relative file is runtime or secret material."""

    lowered = relative_path.name.lower()
    return (
        any(part in RUNTIME_PARTS for part in relative_path.parts)
        or relative_path.name in RUNTIME_NAMES
        or relative_path.suffix.lower() in RUNTIME_SUFFIXES
        or lowered in SECRET_NAMES
        or (lowered.startswith(".env.") and lowered != ".env.example")
        or relative_path.suffix.lower() in SECRET_SUFFIXES
    )


def payload_files(root: Path) -> list[Path]:
    """Return the exact sorted file payload covered by skill manifests/copies."""

    if root.is_symlink():
        raise FileContractError(f"symlinked payload root is forbidden: {root}")
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise FileContractError(f"symlink inside payload tree is forbidden: {path}")
        if path.is_file() and not is_excluded(path.relative_to(root)):
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


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
