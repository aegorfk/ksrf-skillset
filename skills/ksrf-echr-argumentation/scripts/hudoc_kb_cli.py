#!/usr/bin/env python3
"""Resolve a version-checked HUDOC knowledge CLI without pinning a worktree."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_INDEXER = "hudoc-knowledge-indexer-v3.8"
EXPECTED_RESEARCH = "hudoc-research-extractive-v7"
EXPECTED_PRIVACY = "hudoc-knowledge-privacy-sanitizer-v2"
REPOSITORY_ENV = "HUDOC_KS_PARSER_REPO"
DIRECT_CLI_ENV = "HUDOC_KB_CLI"
CLI_RELATIVE_PATH = Path("scripts/hudoc_knowledge_base.py")


def _append_unique(values: list[Path], candidate: Path) -> None:
    try:
        candidate = candidate.expanduser().resolve()
    except (OSError, RuntimeError):
        return
    if candidate not in values:
        values.append(candidate)


def configured_path(name: str, *, no_fallback_message: str) -> Path:
    value = os.environ[name]
    if not value.strip():
        raise SystemExit(
            f"{name} задан, но значение пусто. {no_fallback_message}"
        )
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise SystemExit(
            f"Не удалось прочитать {name}={value!r}: {error}. "
            f"{no_fallback_message}"
        ) from None


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


def candidates() -> tuple[str, list[Path], Path | None]:
    if DIRECT_CLI_ENV in os.environ:
        cli = configured_path(
            DIRECT_CLI_ENV,
            no_fallback_message="Другие пути не проверялись.",
        )
        return "direct", [cli], cli

    if REPOSITORY_ENV in os.environ:
        repository = configured_path(
            REPOSITORY_ENV,
            no_fallback_message="Другие каталоги не проверялись.",
        )
        repositories: list[Path] = []
        _append_unique(repositories, repository)
        for worktree in repository_worktrees(repository):
            _append_unique(repositories, worktree)
        return (
            "repository",
            [candidate / CLI_RELATIVE_PATH for candidate in repositories],
            repository,
        )

    return "unconfigured", [], None


def module_version(module: Path, constant: str) -> str | None:
    try:
        if not module.is_file():
            return None
        content = module.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(
        rf'^{re.escape(constant)}\s*=\s*"([^"]+)"', content, flags=re.MULTILINE
    )
    return match.group(1) if match else None


def is_expected_version(cli: Path) -> bool:
    repository = cli.parent.parent
    try:
        if not cli.is_file():
            return False
    except OSError:
        return False
    return (
        module_version(
            repository / "src" / "hudoc_knowledge_base.py",
            "KNOWLEDGE_INDEXER_VERSION",
        )
        == EXPECTED_INDEXER
        and module_version(
            repository / "src" / "hudoc_research.py",
            "RESEARCH_EXTRACTOR_VERSION",
        )
        == EXPECTED_RESEARCH
        and module_version(
            repository / "src" / "hudoc_knowledge_base.py",
            "PRIVACY_SANITIZER_VERSION",
        )
        == EXPECTED_PRIVACY
    )


def main() -> None:
    mode, candidate_paths, configured = candidates()
    for cli in candidate_paths:
        try:
            cli = cli.resolve()
        except (OSError, RuntimeError):
            continue
        if not is_expected_version(cli):
            continue
        repository = cli.parent.parent
        environment = dict(os.environ)
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            f"{repository}{os.pathsep}{existing}" if existing else str(repository)
        )
        try:
            os.chdir(repository)
            os.execve(
                sys.executable,
                [sys.executable, str(cli), *sys.argv[1:]],
                environment,
            )
        except OSError as error:
            raise SystemExit(
                f"Не удалось запустить HUDOC knowledge CLI {cli}: {error}."
            ) from None

    required = f"{EXPECTED_INDEXER} + {EXPECTED_RESEARCH} + {EXPECTED_PRIVACY}"
    if mode == "direct":
        raise SystemExit(
            f"{DIRECT_CLI_ENV} задан, но точный файл {configured} не найден или "
            f"не прошёл проверку интерфейса; требуются {required}. "
            "Другие пути не проверялись."
        )
    if mode == "repository":
        raise SystemExit(
            f"{REPOSITORY_ENV}={configured} задан, но в этом корне и его "
            f"git-worktrees нет совместимого HUDOC knowledge CLI; требуются "
            f"{required}. Исправьте {REPOSITORY_ENV} или задайте точный "
            f"{DIRECT_CLI_ENV}. Другие каталоги не проверялись."
        )
    raise SystemExit(
        "Движок HUDOC knowledge CLI не настроен и не входит в пакет skills. "
        f"Укажите {DIRECT_CLI_ENV} (точный путь к {CLI_RELATIVE_PATH}) или "
        f"{REPOSITORY_ENV} (корень ks_parser). Автопоиск по HOME и текущему "
        "git-репозиторию отключён."
    )


if __name__ == "__main__":
    main()
