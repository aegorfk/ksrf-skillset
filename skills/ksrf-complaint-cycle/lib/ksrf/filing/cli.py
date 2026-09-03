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
    "admissibility",
    "application",
    "issues",
    "failures",
    "evaluate",
    "render",
    "release",
}

ROUTE_TITLES = {
    "sources": "Проверка официальных источников и редакций норм",
    "admissibility": "Проверка допустимости и выбор маршрута обращения",
    "application": (
        "Доказательство прямого или неявного (имплицитного) применения нормы"
    ),
    "issues": "Формирование вариантов конституционно-правовой проблемы",
    "failures": "Исследование неудачных обращений и неблагоприятной практики",
    "evaluate": "Оценка качества без учёта известного исхода дела",
    "render": "Сборка и визуальная проверка документов DOCX и PDF",
    "release": (
        "Проверка комплекта перед передачей проверяющему юристу; команда не "
        "одобряет и не подаёт жалобу"
    ),
}

ROUTE_ACTIONS = {
    "sources": "verify",
    "admissibility": "derive",
    "application": "analyze",
    "issues": "generate",
    "failures": "research",
    "evaluate": "run",
    "render": "build",
    "release": "check",
}

ROUTE_ACTION_HELP = {
    "sources": "verify — проверить официальные источники и редакции норм",
    "application": "analyze — проанализировать применение нормы в деле",
    "issues": "generate — сформировать варианты конституционно-правовой проблемы",
    "failures": "research — исследовать неудачные обращения и неблагоприятную практику",
    "evaluate": "run — выполнить оценку качества материалов",
    "render": "build — собрать документы для визуальной проверки",
    "release": "check — проверить комплект перед ручной юридической проверкой",
}


class CLIUsageError(ValueError):
    pass


class _RussianArgumentParser(argparse.ArgumentParser):
    """Показывать русскую справку и требовать точные имена параметров."""

    _HELP_METAVARS = {
        "command": "КОМАНДА",
        "matter_command": "КОМАНДА",
        "matter_id": "ИДЕНТИФИКАТОР",
        "workspace": "ПАПКА",
        "input": "ФАЙЛ_ИЛИ_URL",
        "manifest": "ПУТЬ",
        "document_role": "РОЛЬ",
        "action": "ДЕЙСТВИЕ",
        "payload": "ФАЙЛ",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def format_help(self) -> str:
        localized = [
            (action, action.metavar)
            for action in self._actions
            if action.dest in self._HELP_METAVARS
        ]
        for action, _metavar in localized:
            action.metavar = self._HELP_METAVARS[action.dest]
        try:
            rendered = super().format_help()
        finally:
            for action, metavar in localized:
                action.metavar = metavar
        return (
            rendered
            .replace("usage:", "Использование:", 1)
            .replace("positional arguments:", "позиционные аргументы:", 1)
            .replace("optional arguments:", "параметры:", 1)
            .replace("options:", "параметры:", 1)
            .replace(
                "show this help message and exit",
                "показать эту справку и выйти",
            )
        )

    def error(self, message: str) -> NoReturn:
        raise CLIUsageError(f"Некорректные параметры команды: {message}")


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывести результат в техническом формате JSON.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = _RussianArgumentParser(
        prog="ksrf",
        description=(
            "Локальная подготовка жалобы в Конституционный Суд РФ с проверкой "
            "каждого вывода по источникам."
        ),
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
        title="команды",
    )

    start_description = (
        "Показать, с чего начать, или создать локальную рабочую папку дела."
    )
    start = commands.add_parser(
        "start",
        help=start_description,
        description=start_description,
    )
    start.add_argument(
        "--profile",
        choices=("basic", "research", "expert"),
        default="basic",
        help=(
            "Режим работы: basic — базовый (по умолчанию), research — "
            "исследовательский, expert — экспертный."
        ),
    )
    start.add_argument(
        "--matter-id",
        "--id",
        dest="matter_id",
        help="Идентификатор дела; для создания папки укажите вместе с --workspace.",
    )
    start.add_argument(
        "--workspace",
        "--destination",
        dest="workspace",
        type=Path,
        help="Путь к локальной рабочей папке дела; укажите вместе с --matter-id.",
    )
    start.add_argument(
        "--input",
        action="append",
        default=[],
        help="Файл или URL для регистрации; параметр можно повторить.",
    )
    _add_json_flag(start)

    doctor_description = "Проверить возможности без установки программ."
    doctor_parser = commands.add_parser(
        "doctor",
        help=doctor_description,
        description=doctor_description,
    )
    doctor_parser.add_argument(
        "--profile",
        choices=("basic", "research", "expert"),
        default="basic",
        help=(
            "Режим проверки: basic — базовый (по умолчанию), research — "
            "исследовательский, expert — экспертный."
        ),
    )
    doctor_parser.add_argument(
        "--manifest",
        type=Path,
        help="Путь к файлу с описанием доступных возможностей.",
    )
    doctor_parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Разрешить только ограниченные сетевые проверки без отправки документов.",
    )
    _add_json_flag(doctor_parser)

    matter_description = "Управлять локальной рабочей папкой дела."
    matter = commands.add_parser(
        "matter",
        help=matter_description,
        description=matter_description,
    )
    matter_commands = matter.add_subparsers(
        dest="matter_command",
        required=True,
        title="команды",
    )
    matter_init_description = "Создать рабочую папку дела с журналом версий."
    matter_init = matter_commands.add_parser(
        "init",
        help=matter_init_description,
        description=matter_init_description,
    )
    matter_init.add_argument(
        "--matter-id",
        "--id",
        dest="matter_id",
        required=True,
        help="Идентификатор дела.",
    )
    matter_init.add_argument(
        "--workspace",
        "--destination",
        dest="workspace",
        type=Path,
        required=True,
        help="Путь к локальной рабочей папке дела.",
    )
    matter_init.add_argument(
        "--profile",
        choices=("basic", "research", "expert"),
        default="basic",
        help=(
            "Режим работы: basic — базовый (по умолчанию), research — "
            "исследовательский, expert — экспертный."
        ),
    )
    matter_init.add_argument(
        "--input",
        action="append",
        default=[],
        help="Файл или URL для регистрации; параметр можно повторить.",
    )
    _add_json_flag(matter_init)
    matter_status_description = (
        "Показать, каких материалов не хватает и что делать дальше."
    )
    matter_view = matter_commands.add_parser(
        "status",
        help=matter_status_description,
        description=matter_status_description,
    )
    matter_view.add_argument(
        "--workspace",
        "--destination",
        dest="workspace",
        type=Path,
        required=True,
        help="Путь к локальной рабочей папке дела.",
    )
    _add_json_flag(matter_view)

    intake_description = (
        "Зарегистрировать входные материалы в неизменяемом журнале дела."
    )
    intake = commands.add_parser(
        "intake",
        help=intake_description,
        description=intake_description,
    )
    intake.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Путь к локальной рабочей папке дела.",
    )
    intake.add_argument(
        "--input",
        action="append",
        required=True,
        help="Файл или URL для регистрации; параметр можно повторить.",
    )
    intake.add_argument(
        "--document-role",
        default="case_material",
        help="Роль документа; по умолчанию case_material (материал дела).",
    )
    _add_json_flag(intake)

    aliases = {
        "sources": ["source"],
        "admissibility": [],
        "application": ["norm-application"],
        "issues": ["issue"],
        "failures": ["failure-research", "corpus"],
        "evaluate": ["eval"],
        "render": [],
        "release": [],
    }
    for route, route_aliases in aliases.items():
        route_parser = commands.add_parser(
            route,
            aliases=route_aliases,
            help=ROUTE_TITLES[route],
            description=ROUTE_TITLES[route],
        )
        if route == "admissibility":
            route_parser.add_argument(
                "action",
                nargs="?",
                choices=("validate", "derive", "status"),
                default=ROUTE_ACTIONS[route],
                help=(
                    "Действие: validate — проверить, derive — определить маршрут "
                    "обращения (по умолчанию), status — показать состояние."
                ),
            )
        else:
            route_parser.add_argument(
                "action",
                nargs="?",
                default=ROUTE_ACTIONS[route],
                help=(
                    f"Действие: {ROUTE_ACTION_HELP[route]} (по умолчанию)."
                ),
            )
        route_parser.add_argument(
            "--workspace",
            type=Path,
            required=True,
            help="Путь к локальной рабочей папке дела.",
        )
        route_parser.add_argument(
            "--payload",
            type=Path,
            help="Путь к JSON-файлу с входными данными текущего этапа.",
        )
        if route == "sources":
            route_parser.add_argument(
                "--allow-network",
                action="store_true",
                help=(
                    "Разрешить ограниченное получение документа с официального сайта; "
                    "проверку «я не робот» пользователь проходит вручную."
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
