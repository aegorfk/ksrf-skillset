#!/usr/bin/env python3
"""Generate the reproducible manifest for the canonical KSRF skills."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from skillset_file_contract import (
    FileContractError,
    RELEASE_FILE_PATHS,
    SKILL_NAMES,
    file_digest,
    payload_files,
    tree_digest,
    validate_public_repository,
)


def _validate_base_commit(base_commit: str) -> None:
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise SystemExit("--base-commit must be a full lowercase 40-hex Git commit SHA")


def build_manifest(repo_root: Path, base_commit: str) -> dict[str, object]:
    _validate_base_commit(base_commit)
    try:
        validate_public_repository(repo_root)
    except FileContractError as exc:
        raise SystemExit(str(exc)) from exc
    skills_root = repo_root / "skills"
    skill_rows: list[dict[str, object]] = []
    all_files: list[Path] = []
    for name in SKILL_NAMES:
        skill_root = skills_root / name
        if not (skill_root / "SKILL.md").is_file():
            raise SystemExit(f"Missing canonical skill: {skill_root}")
        try:
            files = payload_files(skill_root)
        except FileContractError as exc:
            raise SystemExit(str(exc)) from exc
        all_files.extend(files)
        skill_rows.append(
            {
                "name": name,
                "files": len(files),
                "bytes": sum(path.stat().st_size for path in files),
                "tree_sha256": tree_digest(skill_root, files),
            }
        )

    release_files: list[Path] = []
    release_rows: list[dict[str, object]] = []
    for relative_name in RELEASE_FILE_PATHS:
        relative = Path(relative_name)
        path = repo_root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"Missing or symlinked release file: {path}")
        release_files.append(path)
        release_rows.append(
            {
                "path": relative.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_digest(path),
            }
        )
    return {
        "schema_version": "1.2",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "~/.codex/skills canonical 15-package allowlist",
        "remote_base_commit": base_commit,
        "exclusions": [
            ".DS_Store",
            ".git/",
            ".serena/",
            ".pytest_cache/",
            "__pycache__/",
            "evals/",
            "tests/",
            "*.pyc",
            "*.pyo",
            "secret credential and private-key paths",
        ],
        "digest_format": (
            "sha256 over 4-byte big-endian relative path length + relative path + "
            "8-byte big-endian content length + content, files sorted by POSIX relative path"
        ),
        "total_skills": len(SKILL_NAMES),
        "total_files": len(all_files),
        "total_bytes": sum(path.stat().st_size for path in all_files),
        "tree_sha256": tree_digest(skills_root, all_files),
        "skills": skill_rows,
        "release_files_note": (
            "Executable release surface excluding this self-referential manifest; "
            "clean HEAD == live main binds all remaining versioned files"
        ),
        "total_release_files": len(release_files),
        "total_release_bytes": sum(path.stat().st_size for path in release_files),
        "release_tree_sha256": tree_digest(repo_root, release_files),
        "release_files": release_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-commit", required=True)
    args = parser.parse_args()
    repo_root = args.repo.resolve()
    manifest = build_manifest(repo_root, args.base_commit)
    output = repo_root / "skills-manifest.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {output}: {manifest['total_skills']} skills, "
        f"{manifest['total_files']} files, {manifest['total_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
