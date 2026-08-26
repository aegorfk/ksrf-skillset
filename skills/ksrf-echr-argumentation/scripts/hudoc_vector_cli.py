#!/usr/bin/env python3
"""Resolve a version-checked HUDOC hybrid-vector CLI without pinning a worktree."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_INDEXER = "hudoc-vector-indexer-v2"
EXPECTED_EVALUATOR = "hudoc-vector-evaluator-v2"
EXPECTED_KNOWLEDGE = "hudoc-knowledge-indexer-v3.7"
EXPECTED_RESEARCH = "hudoc-research-extractive-v6"
REPOSITORY_ENV = "HUDOC_KS_PARSER_REPO"


def _append_unique(values: list[Path], candidate: Path) -> None:
    candidate = candidate.expanduser().resolve()
    if candidate not in values:
        values.append(candidate)


def repository_candidates() -> list[Path]:
    values: list[Path] = []
    configured = os.environ.get(REPOSITORY_ENV)
    if configured:
        _append_unique(values, Path(configured))
    try:
        root = subprocess.run(
            ["git", "-C", str(Path.cwd()), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        root = ""
    if root:
        _append_unique(values, Path(root))
    _append_unique(values, Path.home() / "Documents" / "ks_parser")
    return values


def repository_worktrees(repository: Path) -> list[Path]:
    try:
        output = subprocess.run(
            ["git", "-C", str(repository), "worktree", "list", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [
        Path(line[len("worktree ") :])
        for line in output.splitlines()
        if line.startswith("worktree ")
    ]


def candidates() -> list[Path]:
    values: list[Path] = []
    configured = os.environ.get("HUDOC_VECTOR_CLI")
    if configured:
        _append_unique(values, Path(configured))
    for repository in repository_candidates():
        _append_unique(values, repository / "scripts" / "hudoc_vector_search.py")
        for worktree in repository_worktrees(repository):
            _append_unique(values, worktree / "scripts" / "hudoc_vector_search.py")
    return values


def module_version(module: Path, constant: str) -> str | None:
    if not module.is_file():
        return None
    match = re.search(
        rf'^{re.escape(constant)}\s*=\s*"([^"]+)"',
        module.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return match.group(1) if match else None


def is_expected_version(cli: Path) -> bool:
    repository = cli.parent.parent
    if not cli.is_file():
        return False
    return (
        module_version(
            repository / "src" / "hudoc_vector_search.py",
            "VECTOR_INDEXER_VERSION",
        )
        == EXPECTED_INDEXER
        and module_version(
            repository / "src" / "hudoc_vector_search.py",
            "RELEASE_EVALUATOR_VERSION",
        )
        == EXPECTED_EVALUATOR
        and module_version(
            repository / "src" / "hudoc_knowledge_base.py",
            "KNOWLEDGE_INDEXER_VERSION",
        )
        == EXPECTED_KNOWLEDGE
        and module_version(
            repository / "src" / "hudoc_research.py",
            "RESEARCH_EXTRACTOR_VERSION",
        )
        == EXPECTED_RESEARCH
    )


def main() -> None:
    for cli in candidates():
        cli = cli.resolve()
        if not is_expected_version(cli):
            continue
        repository = cli.parent.parent
        environment = dict(os.environ)
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            f"{repository}{os.pathsep}{existing}" if existing else str(repository)
        )
        os.chdir(repository)
        os.execve(sys.executable, [sys.executable, str(cli), *sys.argv[1:]], environment)
    raise SystemExit(
        "No version-checked HUDOC vector CLI found. Set HUDOC_VECTOR_CLI or "
        f"{REPOSITORY_ENV} to a repository with {EXPECTED_INDEXER}, "
        f"{EXPECTED_EVALUATOR}, {EXPECTED_KNOWLEDGE}, and {EXPECTED_RESEARCH}."
    )


if __name__ == "__main__":
    main()
