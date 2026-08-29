"""Единая русскоязычная команда для подготовки материалов обращения в КС РФ."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, NoReturn, Sequence, TextIO

from .capabilities import doctor, load_capability_manifest, render_doctor_report
from .contracts import ContractError, SCHEMA_VERSION
from .matter import (
    MatterWorkspaceError,
    build_progress_projection,
    initialize_matter,
    matter_status,
    register_input,
)


ROUTE_COMMANDS = {
    "intake",
    "sources",
    "application",
    "issues",
    "failures",
    "evaluate",
    "render",
    "release",
}

ROUTE_TITLES = {
    "sources": "Проверка официальных источников и редакций норм",
    "application": "Доказательство прямого или имплицитного применения нормы",
    "issues": "Формирование вариантов конституционно-правовой проблемы",
    "failures": "Исследование неудачных обращений и неблагоприятной практики",
    "evaluate": "Outcome-blind оценка качества",
    "render": "Сборка и визуальная проверка DOCX/PDF",
    "release": "Проверка комплекта перед передачей человеку",
}

ROUTE_ACTIONS = {
    "sources": "verify",
    "application": "analyze",
    "issues": "generate",
    "failures": "research",
    "evaluate": "run",
    "render": "build",
    "release": "check",
}


class CLIUsageError(ValueError):
    pass


class _RussianArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CLIUsageError(f"Некорректные параметры команды: {message}")


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Вывести версионированный JSON.")


def build_parser() -> argparse.ArgumentParser:
    parser = _RussianArgumentParser(
        prog="ksrf",
        description="Локальная подготовка доказательственно проверяемой жалобы в Конституционный Суд РФ.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="Показать безопасный старт или создать рабочую папку.")
    start.add_argument("--profile", choices=("basic", "research", "expert"), default="basic")
    start.add_argument("--matter-id", "--id", dest="matter_id")
    start.add_argument("--workspace", "--destination", dest="workspace", type=Path)
    start.add_argument("--input", action="append", default=[], help="Локальный файл или URL для регистрации.")
    _add_json_flag(start)

    doctor_parser = commands.add_parser("doctor", help="Проверить возможности без установки программ.")
    doctor_parser.add_argument(
        "--profile", choices=("basic", "research", "expert"), default="basic"
    )
    doctor_parser.add_argument("--manifest", type=Path, help="Путь к манифесту возможностей.")
    doctor_parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Явно разрешить только объявленные ограниченные сетевые проверки без отправки документов.",
    )
    _add_json_flag(doctor_parser)

    matter = commands.add_parser("matter", help="Управлять локальной рабочей папкой дела.")
    matter_commands = matter.add_subparsers(dest="matter_command", required=True)
    matter_init = matter_commands.add_parser("init", help="Создать версионированную рабочую папку.")
    matter_init.add_argument("--matter-id", "--id", dest="matter_id", required=True)
    matter_init.add_argument(
        "--workspace", "--destination", dest="workspace", type=Path, required=True
    )
    matter_init.add_argument(
        "--profile", choices=("basic", "research", "expert"), default="basic"
    )
    matter_init.add_argument("--input", action="append", default=[])
    _add_json_flag(matter_init)
    matter_view = matter_commands.add_parser("status", help="Показать пробелы и следующие действия.")
    matter_view.add_argument(
        "--workspace", "--destination", dest="workspace", type=Path, required=True
    )
    _add_json_flag(matter_view)

    intake = commands.add_parser("intake", help="Неизменяемо зарегистрировать входные материалы.")
    intake.add_argument("--workspace", type=Path, required=True)
    intake.add_argument("--input", action="append", required=True)
    intake.add_argument("--document-role", default="case_material")
    _add_json_flag(intake)

    aliases = {
        "sources": ["source"],
        "application": ["norm-application"],
        "issues": ["issue"],
        "failures": ["failure-research"],
        "evaluate": ["eval"],
        "render": [],
        "release": [],
    }
    for route, route_aliases in aliases.items():
        route_parser = commands.add_parser(
            route,
            aliases=route_aliases,
            help=ROUTE_TITLES[route],
        )
        route_parser.add_argument("action", nargs="?", default=ROUTE_ACTIONS[route])
        route_parser.add_argument("--workspace", type=Path, required=True)
        route_parser.add_argument(
            "--payload",
            type=Path,
            help="Путь к версионированному локальному JSON-входу этапа.",
        )
        if route == "sources":
            route_parser.add_argument(
                "--allow-network",
                action="store_true",
                help=(
                    "Явно разрешить только ограниченное получение публичного официального адреса; "
                    "CAPTCHA остаётся ручным действием."
                ),
            )
        else:
            route_parser.set_defaults(allow_network=False)
        _add_json_flag(route_parser)
        route_parser.set_defaults(route=route)
    return parser


def _emit_json(payload: Mapping[str, Any], stdout: TextIO) -> None:
    json.dump(payload, stdout, ensure_ascii=False, indent=2, sort_keys=True)
    stdout.write("\n")


def _start_payload(profile: str) -> dict[str, Any]:
    manifest = load_capability_manifest()
    return {
        "schema_version": SCHEMA_VERSION,
        "state": "skills_only",
        "message": (
            "Скиллы установлены, но готовность окружения и доказательств ещё не проверена. "
            "Можно начать полностью локально и без платной подписки: ничего не устанавливается, "
            "внешняя учётная запись не создаётся, материалы никуда не отправляются."
        ),
        "selected_profile": profile,
        "profiles": {
            code: {"title": value["title"], "purpose": value["purpose"]}
            for code, value in manifest["profiles"].items()
        },
        "minimum_evidence": [
            "Полные тексты судебных актов по всем значимым инстанциям",
            "Точный текст оспариваемой нормы и значимые даты",
            "Документы, подтверждающие, как норма повлияла на права и исход дела",
            "Сведения о сроках и исчерпании средств судебной защиты",
        ],
        "next_actions": [
            f"Запустите ksrf doctor --profile {profile}.",
            "Создайте локальную папку: ksrf matter init --matter-id ИД --workspace ПУТЬ.",
        ],
        "external_transmission_performed": False,
        "automatic_installation_performed": False,
        "external_account_created": False,
    }


def _render_start(payload: Mapping[str, Any]) -> str:
    lines = [str(payload["message"]), "", "Минимально нужны:"]
    lines.extend(f"- {item}" for item in payload["minimum_evidence"])
    lines.extend(["", "Следующие действия:"])
    lines.extend(f"- {item}" for item in payload["next_actions"])
    return "\n".join(lines) + "\n"


def _initialized_payload(workspace: Path, matter: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "matter": dict(matter),
        "progress": matter_status(workspace)["progress"],
        "external_transmission_performed": False,
    }


def _render_initialized(payload: Mapping[str, Any]) -> str:
    matter = payload["matter"]
    progress = payload["progress"]
    lines = [
        f"Рабочая папка создана: {matter['workspace_id']}",
        f"Состояние: {progress['label']}",
        "",
        "Чего не хватает:",
    ]
    lines.extend(f"- {item['item']}: {item['why']}" for item in progress["missing"])
    lines.extend(["", "Следующие действия:"])
    lines.extend(f"- {item}" for item in progress["next_actions"])
    return "\n".join(lines) + "\n"


def _initialize_with_inputs(args: argparse.Namespace) -> dict[str, Any]:
    matter = initialize_matter(
        args.workspace,
        matter_identifier=args.matter_id,
        profile=args.profile,
    )
    for origin in args.input:
        register_input(args.workspace, origin)
    return _initialized_payload(args.workspace, matter)


def _render_status(payload: Mapping[str, Any]) -> str:
    progress = payload["progress"]
    lines = [f"Состояние дела: {progress['label']}", "", "Что найдено:"]
    lines.extend(f"- {item}" for item in progress["found"])
    lines.extend(["", "Чего не хватает:"])
    lines.extend(f"- {item['item']}: {item['why']}" for item in progress["missing"])
    lines.extend(["", "Следующие действия:"])
    lines.extend(f"- {item}" for item in progress["next_actions"])
    return "\n".join(lines) + "\n"


def _pending_route_payload(route: str, action: str, workspace: Path) -> dict[str, Any]:
    status = matter_status(workspace)
    title = ROUTE_TITLES[route]
    if route == "release":
        next_action = (
            "Сначала завершите доказательственные и экспертные проверки; подпись, оплата и подача выполняются только человеком."
        )
    else:
        next_action = (
            f"Завершите реализацию и проверку этапа «{title}» по версионированному контракту; "
            "до этого результат нельзя использовать как подтверждение готовности к подаче."
        )
    progress = build_progress_projection(
        "blocked",
        found=["Маршрут зарегистрирован в единой команде", *status["progress"]["found"]],
        missing=[
            {
                "item": title,
                "why": "Исполнитель этапа ещё не подключён к доказательственному контракту.",
                "next_action": next_action,
            }
        ],
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "route": route,
        "action": action,
        "title": title,
        "state": "blocked",
        "implemented": False,
        "progress": progress,
        "external_transmission_performed": False,
    }


def _render_pending(payload: Mapping[str, Any]) -> str:
    progress = payload["progress"]
    return (
        f"Этап: {payload['title']}\n"
        f"Состояние: {progress['label']}\n"
        f"Почему: {progress['missing'][0]['why']}\n"
        f"Следующее действие: {progress['next_actions'][0]}\n"
        f"{progress['expert_review']['message']}\n"
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "start":
            if bool(args.workspace) != bool(args.matter_id):
                raise CLIUsageError(
                    "Для создания дела одновременно укажите идентификатор --matter-id и локальную папку --workspace."
                )
            if args.workspace:
                payload = _initialize_with_inputs(args)
                rendered = _render_initialized(payload)
            else:
                if args.input:
                    raise CLIUsageError(
                        "Сначала укажите идентификатор и рабочую папку, затем регистрируйте входные файлы."
                    )
                payload = _start_payload(args.profile)
                rendered = _render_start(payload)
        elif args.command == "doctor":
            payload = doctor(
                profile=args.profile,
                manifest_path=args.manifest,
                allow_network=args.allow_network,
            )
            rendered = render_doctor_report(payload)
        elif args.command == "matter" and args.matter_command == "init":
            payload = _initialize_with_inputs(args)
            rendered = _render_initialized(payload)
        elif args.command == "matter" and args.matter_command == "status":
            payload = matter_status(args.workspace)
            rendered = _render_status(payload)
        elif args.command == "intake":
            records = [
                register_input(args.workspace, origin, document_role=args.document_role)
                for origin in args.input
            ]
            payload = {
                "schema_version": SCHEMA_VERSION,
                "state": "registered",
                "records": records,
                "external_transmission_performed": False,
            }
            rendered = (
                f"Локально зарегистрировано документов: {len(records)}. "
                "Межделовое использование и внешняя передача не разрешены.\n"
            )
        else:
            route = str(args.route)
            action = str(args.action)
            if args.payload is None and action not in {"status", "coverage"}:
                payload = _pending_route_payload(route, action, args.workspace)
                rendered = _render_pending(payload)
                exit_code = 3
            else:
                # Lazy import keeps doctor/start/matter usable without the
                # optional DOCX/PDF dependency set.
                from .workflow import (
                    WorkflowInputError,
                    WorkflowRouter,
                    load_versioned_payload,
                    render_workflow_result,
                    workflow_exit_code,
                )

                try:
                    route_payload = (
                        load_versioned_payload(args.payload) if args.payload is not None else None
                    )
                    payload = WorkflowRouter(args.workspace).dispatch(
                        route,
                        action,
                        route_payload,
                        allow_network=args.allow_network,
                    )
                except WorkflowInputError as exc:
                    raise CLIUsageError(str(exc)) from exc
                rendered = render_workflow_result(payload)
                exit_code = workflow_exit_code(payload)
            if args.json:
                _emit_json(payload, output)
            else:
                output.write(rendered)
            return exit_code
        if args.json:
            _emit_json(payload, output)
        else:
            output.write(rendered)
        return 0
    except (CLIUsageError, ContractError, MatterWorkspaceError) as exc:
        errors.write(f"Ошибка: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
