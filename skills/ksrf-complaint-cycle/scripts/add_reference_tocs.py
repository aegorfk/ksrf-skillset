#!/usr/bin/env python3
"""Mechanically add early H2-based TOCs to long KSRF reference Markdown files.

The command is dry-run by default. It writes only when ``--write`` is supplied,
never follows symlinks, and leaves files with an early TOC or index untouched.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence, TextIO


def _load_validator_module() -> Any:
    path = Path(__file__).with_name("validate_ksrf_skillset.py")
    spec = importlib.util.spec_from_file_location("_ksrf_skillset_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Не удалось подготовить импорт {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_VALIDATOR = _load_validator_module()
CANONICAL_KSRF_PACKAGES = tuple(_VALIDATOR.CANONICAL_KSRF_PACKAGES)
REFERENCE_LINE_THRESHOLD = int(_VALIDATOR.LONG_REFERENCE_LINES)
EARLY_TOC_LAST_LINE = int(_VALIDATOR.EARLY_TOC_LAST_LINE)

EARLY_TOC_HEADING = re.compile(
    r"^#{1,4}\s+(?:Содержание|Оглавление|Индекс|Table of contents)\s*$",
    re.I,
)
H1_HEADING = re.compile(r"^#(?!#)\s+.+?\s*$")
H2_HEADING = re.compile(r"^##(?!#)\s+(.+?)\s*#*\s*$")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
EXPLICIT_ID = re.compile(r"\s*\{#([A-Za-z0-9_.:-]+)\}\s*$")


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _has_early_toc(lines: list[str]) -> bool:
    return any(
        EARLY_TOC_HEADING.match(line.lstrip("\ufeff").strip())
        for line in lines[:EARLY_TOC_LAST_LINE]
    )


def _plain_heading_title(raw: str) -> str:
    title = EXPLICIT_ID.sub("", raw.strip())
    title = MARKDOWN_LINK.sub(r"\1", title)
    title = re.sub(r"[`*_~]", "", title)
    return " ".join(title.split())


def _github_anchor(title: str) -> str:
    explicit = EXPLICIT_ID.search(title)
    if explicit:
        return explicit.group(1)
    cleaned = MARKDOWN_LINK.sub(r"\1", title).casefold()
    cleaned = re.sub(r"[`*_~]", "", cleaned)
    characters: list[str] = []
    for character in cleaned:
        if character.isalnum() or character in {" ", "-", "_"}:
            characters.append(character)
    return re.sub(r"\s+", "-", "".join(characters).strip())


def _toc_entries(lines: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    anchor_counts: dict[str, int] = {}
    for line in lines:
        match = H2_HEADING.match(line.strip())
        if not match:
            continue
        raw = match.group(1).strip()
        if EARLY_TOC_HEADING.match(f"## {raw}"):
            continue
        title = _plain_heading_title(raw)
        base_anchor = _github_anchor(raw)
        if not title or not base_anchor:
            continue
        duplicate_index = anchor_counts.get(base_anchor, 0)
        anchor_counts[base_anchor] = duplicate_index + 1
        anchor = base_anchor if duplicate_index == 0 else f"{base_anchor}-{duplicate_index}"
        label = title.replace("[", r"\[").replace("]", r"\]")
        entries.append((label, anchor))
    return entries


def _detect_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _insertion_index(lines: list[str]) -> int:
    for index, line in enumerate(lines[:EARLY_TOC_LAST_LINE]):
        if H1_HEADING.match(line.lstrip("\ufeff").strip()):
            return index + 1
    return 0


def add_toc_to_text(text: str) -> tuple[str | None, str, int]:
    """Return ``(new_text, reason, entry_count)`` without touching a file."""

    lines = text.splitlines(keepends=True)
    plain_lines = text.splitlines()
    if _line_count(text) <= REFERENCE_LINE_THRESHOLD:
        return None, "short", 0
    if _has_early_toc(plain_lines):
        return None, "existing", 0
    entries = _toc_entries(plain_lines)
    if not entries:
        return None, "no_headings", 0

    newline = _detect_newline(text)
    toc = "## Содержание" + newline + newline
    toc += newline.join(f"- [{label}](#{anchor})" for label, anchor in entries)
    toc += newline + newline

    index = _insertion_index(plain_lines)
    prefix = "".join(lines[:index])
    suffix = "".join(lines[index:])
    if prefix and not prefix.endswith((newline + newline)):
        toc = newline + toc
    return prefix + toc + suffix, "update", len(entries)


def _atomic_write(path: Path, text: str) -> None:
    mode = path.stat().st_mode & 0o777
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.toc-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def process_skillset(
    skills_root: str | Path,
    *,
    package_names: Sequence[str] = CANONICAL_KSRF_PACKAGES,
    write: bool = False,
) -> dict[str, Any]:
    root = Path(skills_root).expanduser().absolute()
    findings: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    summary = {
        "packages": len(package_names),
        "references_scanned": 0,
        "long_references": 0,
        "would_update": 0,
        "updated": 0,
        "skipped_short": 0,
        "skipped_existing": 0,
        "skipped_no_headings": 0,
        "errors": 0,
    }

    for package in package_names:
        package_dir = root / package
        if not package_dir.is_dir():
            findings.append(
                {
                    "severity": "error",
                    "code": "PACKAGE_MISSING",
                    "package": package,
                    "path": package,
                    "message": "Ожидаемый KSRF skill package отсутствует.",
                }
            )
            continue
        references_dir = package_dir / "references"
        if not references_dir.is_dir() or references_dir.is_symlink():
            continue
        for path in sorted(references_dir.rglob("*.md")):
            if path.is_symlink() or not path.is_file():
                continue
            summary["references_scanned"] += 1
            relative_path = _relative(path, root)
            try:
                original = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeError) as exc:
                findings.append(
                    {
                        "severity": "error",
                        "code": "REFERENCE_UNREADABLE",
                        "package": package,
                        "path": relative_path,
                        "message": f"Reference не удалось прочитать как UTF-8: {exc}",
                    }
                )
                continue

            updated, reason, entry_count = add_toc_to_text(original)
            if reason == "short":
                summary["skipped_short"] += 1
                continue
            summary["long_references"] += 1
            if reason == "existing":
                summary["skipped_existing"] += 1
                continue
            if reason == "no_headings":
                summary["skipped_no_headings"] += 1
                findings.append(
                    {
                        "severity": "error",
                        "code": "REFERENCE_HAS_NO_H2",
                        "package": package,
                        "path": relative_path,
                        "message": "Reference длиннее 100 строк, но не содержит H2 для TOC.",
                    }
                )
                continue
            if updated is None:
                continue

            status = "updated" if write else "would_update"
            changes.append(
                {
                    "package": package,
                    "path": relative_path,
                    "status": status,
                    "toc_entries": entry_count,
                }
            )
            if write:
                try:
                    _atomic_write(path, updated)
                except OSError as exc:
                    findings.append(
                        {
                            "severity": "error",
                            "code": "REFERENCE_WRITE_FAILED",
                            "package": package,
                            "path": relative_path,
                            "message": f"Не удалось атомарно записать TOC: {exc}",
                        }
                    )
                    changes[-1]["status"] = "write_failed"
                    continue
                summary["updated"] += 1
            else:
                summary["would_update"] += 1

    summary["errors"] = sum(1 for item in findings if item["severity"] == "error")
    return {
        "schema_version": "1.0.0",
        "status": "fail" if summary["errors"] else "pass",
        "mode": "write" if write else "dry-run",
        "line_threshold": REFERENCE_LINE_THRESHOLD,
        "early_toc_last_line": EARLY_TOC_LAST_LINE,
        "packages": list(package_names),
        "summary": summary,
        "changes": changes,
        "findings": findings,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Добавить раннее содержание из H2 в длинные references canonical KSRF skills; "
            "по умолчанию только показать план."
        )
    )
    parser.add_argument(
        "--skills-root",
        default=str(Path.home() / ".codex" / "skills"),
        help="Корень глобальных skills.",
    )
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="Обработать указанный пакет; параметр можно повторять.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Явно разрешить атомарную запись; без флага действует dry-run.",
    )
    parser.add_argument("--json", action="store_true", help="Вывести полный JSON-отчёт.")
    return parser


def _print_text_report(report: dict[str, Any], stream: TextIO) -> None:
    summary = report["summary"]
    print(
        "KSRF reference TOC: "
        f"режим={report['mode']}; проверено={summary['references_scanned']}; "
        f"длинных={summary['long_references']}; "
        f"план={summary['would_update']}; обновлено={summary['updated']}; "
        f"ошибок={summary['errors']}.",
        file=stream,
    )
    for item in report["changes"]:
        print(f"- {item['status']}: {item['path']} ({item['toc_entries']} H2)", file=stream)
    for item in report["findings"]:
        print(f"- ОШИБКА {item['code']}: {item.get('path', '')}", file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    packages = tuple(args.packages) if args.packages else CANONICAL_KSRF_PACKAGES
    try:
        report = process_skillset(
            args.skills_root,
            package_names=packages,
            write=bool(args.write),
        )
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"TOC-проход остановлен без записи: {exc}", file=sys.stderr)
        return 2
    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_text_report(report, sys.stdout)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
