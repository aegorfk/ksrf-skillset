#!/usr/bin/env python3
"""Verify that every KSRF skill routes to a portable bundled practice core."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from validate_ksrf_skillset import is_source_only_artifact


SKILLS_ROOT = Path(__file__).resolve().parents[2]
CORE = SKILLS_ROOT / "ksrf-complaint-cycle" / "references" / "offline-practice-core.md"
CORE_LINK = "offline-practice-core.md"
UID_WORKFLOW = (
    SKILLS_ROOT
    / "ksrf-complaint-cycle"
    / "references"
    / "uid-first-case-workflow.md"
)
UID_SCENARIOS = (
    SKILLS_ROOT
    / "ksrf-complaint-cycle"
    / "references"
    / "uid-first-scenario-contract.json"
)
FORBIDDEN_RUNTIME_MARKERS = (
    "/Users/",
    "ТЗ/Каналы/",
    "t.me/s/",
    'Path.home() / "Documents" / "ks_parser_lower_court_marker"',
)
REQUIRED_CORE_HEADINGS = (
    "## 0. Контракт автономности",
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
REQUIRED_UID_HEADINGS = (
    "## Целевой пользовательский сценарий",
    "## 2. Скачай досье по всем ожидаемым стадиям",
    "## 4. Сначала проверь допустимость",
    "## 5. Предложи варианты конституционно-правовой проблемы",
    "## 6. Дай рекомендацию по маршруту",
    "## 7. Минимальное взаимодействие с пользователем",
)
REQUIRED_UID_RULES = (
    "`pass / fail / unknown / not_applicable`",
    "портфель вариантов и `preferred_option_id` не обязательны",
    "Приоритет между близкими статусами",
    "После поиска допустимы только четыре типа взаимодействия",
    "ноль найденных стадий",
    "source-routing table",
)
UID_CONSUMERS = (
    "ksrf-complaint-cycle",
    "ksrf-case-triage",
    "ksrf-exhaustion-planner",
    "ksrf-explore-arguments",
    "ksrf-complaint-qa",
)


def validate_uid_scenarios(errors: list[str]) -> None:
    if not UID_SCENARIOS.is_file():
        errors.append(f"missing UID-first scenario contract: {UID_SCENARIOS}")
        return

    try:
        payload = json.loads(UID_SCENARIOS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid UID-first scenario contract: {exc}")
        return

    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("UID-first scenario contract has no scenarios list")
        return

    by_id = {
        item.get("id"): item
        for item in scenarios
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    required_ids = {
        "malformed_uid",
        "ambiguous_uid",
        "not_found_uid",
        "adapter_zero_slots",
        "expired_noncurable_deadline",
        "factual_only_dispute",
        "critical_act_unavailable_after_search",
        "known_obtainable_gap",
        "active_proceeding",
        "complete_viable_case_without_connector",
        "single_viable_theory",
        "multiple_viable_theories",
    }
    missing = sorted(required_ids - set(by_id))
    if missing:
        errors.append(f"UID-first scenario contract misses: {', '.join(missing)}")
        return

    for scenario_id in ("malformed_uid", "ambiguous_uid", "not_found_uid"):
        scenario = by_id[scenario_id]
        if scenario.get("case_analysis_allowed") is not False:
            errors.append(f"{scenario_id} must block case analysis before identity resolution")
        if scenario.get("allowed_question") != "corrected_uid_or_one_identifying_requisite":
            errors.append(f"{scenario_id} must allow only a narrow identity question")

    zero_slots = by_id["adapter_zero_slots"]
    if zero_slots.get("chain_state") != "unknown" or zero_slots.get("complete_allowed") is not False:
        errors.append("zero-slot adapter result must remain incomplete with unknown chain")

    for scenario_id in ("expired_noncurable_deadline", "factual_only_dispute"):
        scenario = by_id[scenario_id]
        if scenario.get("decision") != "NO_GO_KSRF":
            errors.append(f"{scenario_id} must end in NO_GO_KSRF")
        if scenario.get("options_required") is not False or scenario.get("preferred_option_id") is not None:
            errors.append(f"{scenario_id} must not fabricate an issue option")

    unavailable = by_id["critical_act_unavailable_after_search"]
    if unavailable.get("decision") != "ABSTAIN_PENDING_RECORD":
        errors.append("unavailable critical act must end in ABSTAIN_PENDING_RECORD")

    fixable = by_id["known_obtainable_gap"]
    if fixable.get("decision") != "FIX_FIRST" or fixable.get("curability") != "known_and_controlled":
        errors.append("known obtainable gap must end in FIX_FIRST")

    if by_id["active_proceeding"].get("decision") != "COURT_REQUEST_ROUTE":
        errors.append("active proceeding fixture must preserve COURT_REQUEST_ROUTE")

    complete = by_id["complete_viable_case_without_connector"]
    if (
        complete.get("decision") != "GO_TO_KSRF"
        or complete.get("all_applicable_gates") != "pass"
        or complete.get("options_required") is not True
        or complete.get("connector_available") is not False
    ):
        errors.append("complete no-connector fixture must remain a valid GO candidate")

    single = by_id["single_viable_theory"]
    if (
        single.get("viable_option_count") != 1
        or int(single.get("rejected_alternatives_min") or 0) < 1
        or single.get("options_required") is not True
    ):
        errors.append("single viable theory must retain rejected alternatives without fabrication")

    multiple = by_id["multiple_viable_theories"]
    if (
        not (
            2
            <= int(multiple.get("viable_option_count_min") or 0)
            <= int(multiple.get("viable_option_count_max") or 0)
            <= 4
        )
        or multiple.get("human_selection") != "pending"
        or multiple.get("options_required") is not True
    ):
        errors.append("multiple viable theories must present 2-4 options for human selection")


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

    if not UID_WORKFLOW.is_file():
        errors.append(f"missing UID-first workflow: {UID_WORKFLOW}")
        uid_text = ""
    else:
        uid_text = UID_WORKFLOW.read_text(encoding="utf-8")

    for heading in REQUIRED_UID_HEADINGS:
        if heading not in uid_text:
            errors.append(f"UID-first workflow missing required section: {heading}")

    for rule in REQUIRED_UID_RULES:
        if rule not in uid_text:
            errors.append(f"UID-first workflow missing required rule: {rule}")

    for marker in FORBIDDEN_RUNTIME_MARKERS:
        if marker in uid_text:
            errors.append(f"UID-first workflow contains external runtime marker: {marker}")

    validate_uid_scenarios(errors)

    # Runtime matter/workspace directories may intentionally share the
    # ``ksrf-*`` prefix.  A package participates in this check only when it has
    # the required skill entrypoint; workspace contents are neither skills nor
    # publication inputs.
    skill_dirs = sorted(
        path
        for path in SKILLS_ROOT.glob("ksrf-*")
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
    skill_files = [skill_dir / "SKILL.md" for skill_dir in skill_dirs]
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

        if (
            skill_file.parent.name in UID_CONSUMERS
            and "uid-first-case-workflow.md" not in text
        ):
            errors.append(
                f"skill does not route UID-first intake: {skill_file.parent.name}"
            )

    for skill_dir in skill_dirs:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_symlink():
                try:
                    path.resolve().relative_to(SKILLS_ROOT.resolve())
                except (OSError, ValueError):
                    errors.append(f"external symlink: {path}")

    for skill_dir in skill_dirs:
        for markdown in sorted(skill_dir.rglob("*.md")):
            logical_path = Path(skill_dir.name) / markdown.relative_to(skill_dir)
            if is_source_only_artifact(logical_path):
                continue
            markdown_text = markdown.read_text(encoding="utf-8")
            for raw_target in re.findall(r"`([^`\n]+\.md(?:#[^`\s]+)?)`", markdown_text):
                target = raw_target.split("#", 1)[0]
                if (
                    "://" in target
                    or "*" in target
                    or target.startswith("<")
                    or target.startswith("ТЗ/")
                ):
                    continue
                resolved = (markdown.parent / target).resolve()
                try:
                    resolved.relative_to(SKILLS_ROOT.resolve())
                except ValueError:
                    errors.append(f"markdown path escapes skillset: {markdown}: {raw_target}")
                    continue
                if not resolved.is_file():
                    errors.append(f"broken bundled markdown path: {markdown}: {raw_target}")

    for script in sorted(SKILLS_ROOT.glob("ksrf-*/scripts/*.py")):
        if script.resolve() == Path(__file__).resolve():
            continue
        script_text = script.read_text(encoding="utf-8")
        for marker in FORBIDDEN_RUNTIME_MARKERS:
            if marker in script_text:
                errors.append(f"script contains external runtime marker {marker}: {script}")

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
