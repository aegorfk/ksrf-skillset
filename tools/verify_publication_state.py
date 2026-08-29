#!/usr/bin/env python3
"""Fail-closed guard for installing or syncing the public KSRF skillset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence
from urllib.parse import urlparse

from generate_skills_manifest import build_manifest


EXPECTED_REPOSITORY = "aegorfk/ksrf-skillset"
DEFAULT_REMOTE = "origin"
DEFAULT_BRANCH = "main"


class PublicationStateError(RuntimeError):
    """The checkout cannot be trusted as the current published release."""


def _run_git(repo: Path, *args: str) -> str:
    command = ["git", "-C", str(repo), *args]
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        raise PublicationStateError("git is required for publication verification") from exc
    except subprocess.TimeoutExpired as exc:
        raise PublicationStateError(f"git command timed out: {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "unknown git error").strip()
        raise PublicationStateError(f"git {' '.join(args)} failed: {detail}") from exc
    return completed.stdout.strip()


def _github_repository(remote_url: str) -> str | None:
    value = remote_url.strip().rstrip("/")
    scp_match = re.fullmatch(r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?", value)
    if scp_match:
        return scp_match.group(1).removesuffix(".git")

    parsed = urlparse(value)
    if parsed.hostname != "github.com" or parsed.scheme not in {"https", "http", "ssh"}:
        return None
    repository = parsed.path.strip("/").removesuffix(".git")
    if repository.count("/") != 1:
        return None
    return repository


def _manifest_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    skill_rows = manifest.get("skills")
    if not isinstance(skill_rows, list):
        raise PublicationStateError("skills-manifest.json has no valid skills list")
    projected_skills = []
    for row in skill_rows:
        if not isinstance(row, dict):
            raise PublicationStateError("skills-manifest.json contains an invalid skill row")
        projected_skills.append(
            {
                "name": row.get("name"),
                "files": row.get("files"),
                "bytes": row.get("bytes"),
                "tree_sha256": row.get("tree_sha256"),
            }
        )
    release_rows = manifest.get("release_files")
    if not isinstance(release_rows, list):
        raise PublicationStateError("skills-manifest.json has no valid release_files list")
    projected_release_files = []
    for row in release_rows:
        if not isinstance(row, dict):
            raise PublicationStateError("skills-manifest.json contains an invalid release file row")
        projected_release_files.append(
            {
                "path": row.get("path"),
                "bytes": row.get("bytes"),
                "sha256": row.get("sha256"),
            }
        )
    return {
        "schema_version": manifest.get("schema_version"),
        "total_skills": manifest.get("total_skills"),
        "total_files": manifest.get("total_files"),
        "total_bytes": manifest.get("total_bytes"),
        "tree_sha256": manifest.get("tree_sha256"),
        "skills": projected_skills,
        "total_release_files": manifest.get("total_release_files"),
        "total_release_bytes": manifest.get("total_release_bytes"),
        "release_tree_sha256": manifest.get("release_tree_sha256"),
        "release_files": projected_release_files,
    }


def verify_manifest(repo: Path) -> dict[str, str]:
    manifest_path = repo / "skills-manifest.json"
    try:
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PublicationStateError(f"missing versioned manifest: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise PublicationStateError(f"invalid JSON manifest: {manifest_path}: {exc}") from exc
    if not isinstance(recorded, dict):
        raise PublicationStateError("skills-manifest.json must contain a JSON object")

    base_commit = recorded.get("remote_base_commit")
    if not isinstance(base_commit, str) or re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        raise PublicationStateError(
            "skills-manifest.json remote_base_commit must be a full lowercase 40-hex SHA"
        )
    try:
        calculated = build_manifest(repo, base_commit)
    except SystemExit as exc:
        raise PublicationStateError(f"could not calculate current manifest: {exc}") from exc
    if _manifest_projection(recorded) != _manifest_projection(calculated):
        raise PublicationStateError(
            "bundled skills or release tools do not match skills-manifest.json; "
            "regenerate and publish the manifest"
        )
    tree_sha = recorded.get("tree_sha256")
    if not isinstance(tree_sha, str) or not tree_sha:
        raise PublicationStateError("skills-manifest.json has no tree_sha256")
    release_tree_sha = recorded.get("release_tree_sha256")
    if not isinstance(release_tree_sha, str) or not release_tree_sha:
        raise PublicationStateError("skills-manifest.json has no release_tree_sha256")
    return {
        "tree_sha256": tree_sha,
        "release_tree_sha256": release_tree_sha,
        "remote_base_commit": base_commit,
    }


def verify_publication_state(
    repo: Path,
    *,
    remote: str = DEFAULT_REMOTE,
    branch: str = DEFAULT_BRANCH,
    expected_repository: str = EXPECTED_REPOSITORY,
) -> dict[str, str]:
    repo = repo.resolve()
    if not repo.is_dir():
        raise PublicationStateError(f"repository directory does not exist: {repo}")

    top_level = Path(_run_git(repo, "rev-parse", "--show-toplevel")).resolve()
    if top_level != repo:
        raise PublicationStateError(f"guard must run at repository root: {top_level}")

    remote_url = _run_git(repo, "remote", "get-url", remote)
    observed_repository = _github_repository(remote_url)
    if observed_repository != expected_repository:
        raise PublicationStateError(
            f"unexpected {remote} remote: {remote_url!r}; expected GitHub {expected_repository}"
        )

    dirty = _run_git(repo, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        preview = " | ".join(dirty.splitlines()[:10])
        raise PublicationStateError(f"checkout is dirty; publication is incomplete: {preview}")

    local_sha = _run_git(repo, "rev-parse", "HEAD")
    remote_ref = f"refs/heads/{branch}"
    live_output = _run_git(repo, "ls-remote", remote, remote_ref)
    rows = [line.split() for line in live_output.splitlines() if line.strip()]
    live_shas = [row[0] for row in rows if len(row) == 2 and row[1] == remote_ref]
    if len(live_shas) != 1:
        raise PublicationStateError(f"could not resolve one live SHA for {remote}/{remote_ref}")
    live_sha = live_shas[0]
    if local_sha != live_sha:
        raise PublicationStateError(
            f"stale or unpublished checkout: local HEAD {local_sha} != live {branch} {live_sha}"
        )

    manifest = verify_manifest(repo)
    base_commit = manifest["remote_base_commit"]
    try:
        _run_git(repo, "cat-file", "-e", f"{base_commit}^{{commit}}")
    except PublicationStateError as exc:
        raise PublicationStateError(
            f"manifest remote_base_commit is not a local commit: {base_commit}"
        ) from exc
    try:
        first_parent = _run_git(repo, "rev-parse", "HEAD^")
    except PublicationStateError as exc:
        raise PublicationStateError(
            "release HEAD has no first parent; atomic publication verification is impossible"
        ) from exc
    if base_commit != first_parent:
        raise PublicationStateError(
            "manifest remote_base_commit must equal the release HEAD first parent: "
            f"manifest={base_commit} first_parent={first_parent}"
        )
    return {
        "repository": observed_repository,
        "local_sha": local_sha,
        "live_sha": live_sha,
        "manifest_tree_sha256": manifest["tree_sha256"],
        "release_tree_sha256": manifest["release_tree_sha256"],
        "remote_base_commit": base_commit,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify that this checkout is the exact clean release published on live main."
    )
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--expected-repository", default=EXPECTED_REPOSITORY)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_publication_state(
            args.repo,
            remote=args.remote,
            branch=args.branch,
            expected_repository=args.expected_repository,
        )
    except PublicationStateError as exc:
        print(f"Publication guard refused: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Verified published KSRF skillset: "
            f"{result['repository']} live_sha={result['live_sha']} "
            f"manifest_tree_sha256={result['manifest_tree_sha256']} "
            f"release_tree_sha256={result['release_tree_sha256']} "
            f"remote_base_commit={result['remote_base_commit']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
