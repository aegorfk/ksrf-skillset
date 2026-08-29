#!/usr/bin/env python3
"""Generate the reproducible manifest for the 14 canonical KSRF skills."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable


SKILL_NAMES = (
    "ksrf-argument-patterns",
    "ksrf-case-triage",
    "ksrf-cassation-judicial-meaning",
    "ksrf-complaint-cycle",
    "ksrf-complaint-facts-demands",
    "ksrf-complaint-qa",
    "ksrf-court-request-motion",
    "ksrf-decision-execution",
    "ksrf-echr-argumentation",
    "ksrf-exhaustion-planner",
    "ksrf-explore-arguments",
    "ksrf-formal-filing-check",
    "ksrf-practice-authority-builder",
    "ksrf-rights-argument-builder",
)
RUNTIME_PARTS = {".git", ".serena", ".pytest_cache", "__pycache__"}
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


def _excluded(path: Path) -> bool:
    lowered = path.name.lower()
    return (
        any(part in RUNTIME_PARTS for part in path.parts)
        or path.name in RUNTIME_NAMES
        or path.suffix.lower() in RUNTIME_SUFFIXES
        or lowered in SECRET_NAMES
        or (lowered.startswith(".env.") and lowered != ".env.example")
        or path.suffix.lower() in SECRET_SUFFIXES
    )


def _files(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if path.is_file() and not _excluded(path.relative_to(root))),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def _tree_digest(root: Path, files: Iterable[Path]) -> str:
    digest = sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def build_manifest(repo_root: Path, base_commit: str) -> dict[str, object]:
    skills_root = repo_root / "skills"
    skill_rows: list[dict[str, object]] = []
    all_files: list[Path] = []
    for name in SKILL_NAMES:
        skill_root = skills_root / name
        if not (skill_root / "SKILL.md").is_file():
            raise SystemExit(f"Missing canonical skill: {skill_root}")
        files = _files(skill_root)
        all_files.extend(files)
        skill_rows.append(
            {
                "name": name,
                "files": len(files),
                "bytes": sum(path.stat().st_size for path in files),
                "tree_sha256": _tree_digest(skill_root, files),
            }
        )
    return {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "~/.codex/skills canonical 14-package allowlist",
        "remote_base_commit": base_commit,
        "exclusions": [
            ".DS_Store",
            ".git/",
            ".serena/",
            ".pytest_cache/",
            "__pycache__/",
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
        "tree_sha256": _tree_digest(skills_root, all_files),
        "skills": skill_rows,
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
