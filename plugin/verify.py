#!/usr/bin/env python3
"""Offline integrity check of a generated plugin. Does not establish authenticity."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import sys


def verify(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Plugin root must be a real directory")
    manifest_path = root / "distribution-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Missing regular distribution manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("Unsupported distribution manifest")
    expected: dict[str, str] = {}
    for record in manifest["files"]:
        name = record["path"]
        rel = PurePosixPath(name)
        if (not name or rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name
                or name != rel.as_posix() or name in expected
                or name == "distribution-manifest.json"):
            raise ValueError("Invalid or duplicate manifest path")
        expected[name] = record["sha256"]
        path = root.joinpath(*rel.parts)
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or unsafe file: {name}")
        data = path.read_bytes()
        if len(data) != record["bytes"] or sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"Changed file: {name}")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlinks are not permitted in the plugin")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if name == "distribution-manifest.json":
                continue
            actual.add(name)
    if actual != set(expected):
        raise ValueError("Unlisted or missing files in plugin")
    declared = manifest.get("skills", [])
    observed = sorted(p.name for p in (root / "skills").iterdir() if p.is_dir())
    if declared != observed or not declared:
        raise ValueError("Skill inventory differs from distribution manifest")
    for name in declared:
        if f"skills/{name}/SKILL.md" not in expected:
            raise ValueError("Missing skill entrypoint")
    return {"status": "verified", "skills": len(declared), "files": len(expected),
            "variant": manifest["variant"], "source_commit": manifest["source"]["commit"],
            "scope": "local_integrity_only", "filing_authority": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверить целостность файлов плагина без сети.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
          f"Файлы плагина целы: {result['skills']} навыков. Это проверка файлов, не юридическое заключение.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
