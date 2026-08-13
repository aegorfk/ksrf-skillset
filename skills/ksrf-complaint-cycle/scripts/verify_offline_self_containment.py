#!/usr/bin/env python3
"""Verify that every KSRF skill routes to the bundled offline practice core."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]
CORE = SKILLS_ROOT / "ksrf-complaint-cycle" / "references" / "offline-practice-core.md"
CORE_LINK = "offline-practice-core.md"
FORBIDDEN_RUNTIME_MARKERS = (
    "/Users/",
    "ТЗ/Каналы/",
    "t.me/s/",
)
REQUIRED_CORE_HEADINGS = (
    "## 2. Маршрут до текста",
    "## 3. Hard gates как зависимая цепочка",
    "## 4. Anti-appeal filter",
    "## 6. Архитектура аргумента",
    "## 8. Ходатайство о запросе суда",
    "## 9. Drafting",
    "## 10. Формальная подача и Секретариат",
    "## 11. Проектирование последствий",
    "## 12. Финальный автономный контроль",
)


def main() -> int:
    errors: list[str] = []
    if not CORE.is_file():
        errors.append(f"missing core: {CORE}")
        core_text = ""
    else:
        core_text = CORE.read_text(encoding="utf-8")

    for marker in FORBIDDEN_RUNTIME_MARKERS:
        if marker in core_text:
            errors.append(f"core contains external runtime marker: {marker}")

    for heading in REQUIRED_CORE_HEADINGS:
        if heading not in core_text:
            errors.append(f"core missing required section: {heading}")

    skill_files = sorted(SKILLS_ROOT.glob("ksrf-*/SKILL.md"))
    if not skill_files:
        errors.append("no KSRF skills found")

    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8")
        if CORE_LINK not in text:
            errors.append(f"skill does not route to offline core: {skill_file.parent.name}")
        for marker in FORBIDDEN_RUNTIME_MARKERS:
            if marker in text:
                errors.append(
                    f"skill contains external runtime marker {marker}: {skill_file.parent.name}"
                )

        for relative_link in re.findall(r"`([^`]*offline-practice-core\.md)`", text):
            resolved = (skill_file.parent / relative_link).resolve()
            if resolved != CORE.resolve():
                errors.append(
                    f"skill has broken offline core link: {skill_file.parent.name}: {relative_link}"
                )

    if errors:
        print("Offline self-containment verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"Offline self-containment verified: {len(skill_files)} KSRF skills, "
        f"core={CORE}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
