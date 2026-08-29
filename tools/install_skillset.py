#!/usr/bin/env python3
"""Copy the exact manifest-covered KSRF payload into a skills directory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Sequence

from skillset_file_contract import FileContractError, SKILL_NAMES, payload_files, tree_digest


class InstallationError(RuntimeError):
    """The requested copy cannot be performed without risking another path."""


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _validate_source(source_root: Path) -> dict[str, list[Path]]:
    source_root = source_root.resolve(strict=True)
    undeclared = sorted(
        path.name
        for path in source_root.glob("ksrf-*")
        if path.is_dir() and path.name not in SKILL_NAMES
    )
    if undeclared:
        raise InstallationError(f"undeclared bundled skills: {', '.join(undeclared)}")

    files_by_skill: dict[str, list[Path]] = {}
    for skill_name in SKILL_NAMES:
        skill_root = source_root / skill_name
        if skill_root.is_symlink():
            raise InstallationError(f"refusing symlinked source skill: {skill_root}")
        if not skill_root.is_dir() or not (skill_root / "SKILL.md").is_file():
            raise InstallationError(f"required source skill is missing: {skill_root}")
        try:
            files_by_skill[skill_name] = payload_files(skill_root)
        except FileContractError as exc:
            raise InstallationError(str(exc)) from exc
    return files_by_skill


def _validate_target(target: Path) -> Path:
    target = _absolute_without_resolving(target)
    root = Path(target.anchor)
    home = Path.home().resolve()
    if target == root or target.resolve(strict=False) == home:
        raise InstallationError(f"refusing broad install target: {target}")
    if target.is_symlink():
        raise InstallationError(f"refusing symlinked install target: {target}")
    if target.exists() and not target.is_dir():
        raise InstallationError(f"install target exists and is not a directory: {target}")
    for skill_name in SKILL_NAMES:
        destination = target / skill_name
        if destination.is_symlink():
            raise InstallationError(f"refusing symlinked skill destination: {destination}")
        if destination.exists() and not destination.is_dir():
            raise InstallationError(
                f"skill destination exists and is not a directory: {destination}"
            )
    return target


def copy_skillset(source_root: Path, target: Path) -> Path:
    """Validate all paths, stage the exact payload, then replace canonical destinations."""

    source_root = source_root.resolve(strict=True)
    files_by_skill = _validate_source(source_root)
    target = _validate_target(target)

    target.mkdir(parents=True, exist_ok=True)
    staging_parent = Path(tempfile.mkdtemp(prefix=".ksrf-install-", dir=target))
    try:
        for skill_name in SKILL_NAMES:
            source_skill = source_root / skill_name
            staged_skill = staging_parent / skill_name
            staged_skill.mkdir()
            for source_file in files_by_skill[skill_name]:
                relative = source_file.relative_to(source_skill)
                staged_file = staged_skill / relative
                staged_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, staged_file)

            staged_files = payload_files(staged_skill)
            source_relatives = [
                path.relative_to(source_skill).as_posix() for path in files_by_skill[skill_name]
            ]
            staged_relatives = [path.relative_to(staged_skill).as_posix() for path in staged_files]
            if source_relatives != staged_relatives or tree_digest(
                source_skill, files_by_skill[skill_name]
            ) != tree_digest(staged_skill, staged_files):
                raise InstallationError(f"staged payload verification failed: {skill_name}")

        for skill_name in SKILL_NAMES:
            destination = target / skill_name
            if destination.exists():
                shutil.rmtree(destination)
            (staging_parent / skill_name).replace(destination)
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return target


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", type=Path)
    source.add_argument("--source-skills-root", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source_root = args.repo / "skills" if args.repo is not None else args.source_skills_root
    assert source_root is not None
    try:
        target = copy_skillset(source_root, args.target)
    except (InstallationError, FileNotFoundError, OSError) as exc:
        print(f"Skillset installation refused: {exc}", file=sys.stderr)
        return 1
    print(f"Installed exact manifest-covered KSRF skill payload into {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
