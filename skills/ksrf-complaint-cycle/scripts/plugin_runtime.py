#!/usr/bin/env python3
"""Portable plugin adapter; all legal operations stay in the bundled runtime."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Any, Iterator, Mapping, Sequence
import uuid


SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = SKILL_ROOT.parent
PACKAGE_ROOT = SKILLS_ROOT.parent
REQUIREMENTS = SKILL_ROOT / "configs" / "plugin-requirements.txt"
STATE_MARKER = ".ksrf-plugin-state.json"
STATE_FORMAT = "ksrf-applicant-runtime-v1"
ACTIVE_FILE = "active-documents.json"
MODULES = {
    "python-docx": "docx", "pypdf": "pypdf", "Pillow": "PIL",
    "jsonschema": "jsonschema", "referencing": "referencing", "PyYAML": "yaml",
    "lxml": "lxml", "typing_extensions": "typing_extensions", "attrs": "attrs",
    "jsonschema-specifications": "jsonschema_specifications", "rpds-py": "rpds",
}
DOCUMENT_MODULES = ("python-docx", "pypdf", "Pillow", "jsonschema", "referencing")
COMMON_BIN_DIRS = (
    "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
    "/Applications/LibreOffice.app/Contents/MacOS",
)


class RuntimeSetupError(ValueError):
    """Actionable local setup error, with no raw child-process output."""


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def default_state_dir(env: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if env is None else env
    override = environment.get("KSRF_PLUGIN_STATE_DIR")
    if override is not None:
        if not override.strip():
            raise RuntimeSetupError("KSRF_PLUGIN_STATE_DIR не может быть пустым.")
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(environment.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(environment.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "ksrf-applicant"


def _no_symlink_components(path: Path) -> None:
    for current in (*reversed(path.parents), path):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeSetupError("Путь окружения проходит через символическую ссылку; выберите фактическую отдельную папку.")
        if current != path and not stat.S_ISDIR(info.st_mode):
            raise RuntimeSetupError("Вместо родительской папки окружения найден файл.")


def validate_state_dir(raw: str | Path) -> Path:
    if not str(raw).strip():
        raise RuntimeSetupError("Путь окружения не может быть пустым.")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise RuntimeSetupError("Укажите абсолютный путь к отдельной папке окружения.")
    if ".." in path.parts:
        raise RuntimeSetupError("Путь окружения не должен содержать переходы '..'.")
    home = Path.home().absolute()
    broad = {Path(path.anchor), home, Path.cwd().absolute(),
             Path("/tmp"), Path("/private/tmp"), Path("/var/tmp"),
             Path("/usr"), Path("/usr/local"), Path("/opt"), Path("/home"),
             home / "Documents", home / "Desktop", home / "Downloads",
             home / ".local", home / ".local/share", home / "Library",
             home / "Library/Application Support"}
    if path in broad or _inside(home, path):
        raise RuntimeSetupError("Нужна отдельная папка KSRF, а не корень диска, домашняя или общая рабочая папка.")
    if _inside(path, PACKAGE_ROOT) or _inside(PACKAGE_ROOT, path):
        raise RuntimeSetupError("Окружение должно находиться вне установленного пакета и его родительских папок.")
    _no_symlink_components(path)
    if path.exists() and not path.is_dir():
        raise RuntimeSetupError("Вместо папки окружения найден файл.")
    return path


def _private_owned(path: Path, *, directory: bool = False) -> os.stat_result:
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise RuntimeSetupError("Служебный путь окружения имеет неподдерживаемый тип.")
    if hasattr(os, "geteuid") and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise RuntimeSetupError("Папка и служебные файлы окружения должны принадлежать пользователю и быть доступны только ему.")
    if not directory and info.st_nlink != 1:
        raise RuntimeSetupError("Служебный файл окружения имеет дополнительные жёсткие ссылки.")
    return info


def _read_record(path: Path) -> dict[str, Any]:
    _private_owned(path)
    if path.stat().st_size > 32768:
        raise RuntimeSetupError("Служебная запись окружения слишком велика.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeSetupError("Служебная запись окружения повреждена.") from exc
    if not isinstance(value, dict):
        raise RuntimeSetupError("Служебная запись окружения должна быть объектом.")
    return value


def _check_state(state: Path) -> bool:
    validate_state_dir(state)
    if not state.exists():
        return False
    _private_owned(state, directory=True)
    marker = state / STATE_MARKER
    if not marker.exists() and not marker.is_symlink():
        if any(state.iterdir()):
            raise RuntimeSetupError("Выбранная папка уже содержит посторонние файлы; выберите новую пустую папку.")
        return False
    if _read_record(marker) != {"format": STATE_FORMAT}:
        raise RuntimeSetupError("Папка принадлежит другому или повреждённому окружению.")
    return True


def _write_record(state: Path, name: str, payload: Mapping[str, Any]) -> None:
    _no_symlink_components(state)
    _private_owned(state, directory=True)
    target = state / name
    if target.exists() or target.is_symlink():
        _private_owned(target)
    temporary = state / (".record-" + uuid.uuid4().hex)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(dict(payload), output, ensure_ascii=False, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        _no_symlink_components(state)
        if target.exists() or target.is_symlink():
            _private_owned(target)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def _setup_lock(state: Path) -> Iterator[None]:
    owned = _check_state(state)
    if not state.exists():
        state.mkdir(parents=True, mode=0o700)
    _private_owned(state, directory=True)
    lock = state / ".setup.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError as exc:
        raise RuntimeSetupError("Настройка уже выполняется или была прервана. Сохраните окружение; для нового запуска можно выбрать другую отдельную папку.") from exc
    info = os.fstat(descriptor)
    os.close(descriptor)
    try:
        if not owned:
            if set(p.name for p in state.iterdir()) != {".setup.lock"}:
                raise RuntimeSetupError("Содержимое новой папки изменилось; настройка остановлена.")
            _write_record(state, STATE_MARKER, {"format": STATE_FORMAT})
        yield
    finally:
        try:
            now = lock.lstat()
            if (now.st_dev, now.st_ino) == (info.st_dev, info.st_ino):
                lock.unlink()
        except FileNotFoundError:
            pass


def requirement_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    if REQUIREMENTS.is_symlink() or not REQUIREMENTS.is_file():
        raise RuntimeSetupError("В пакете отсутствует обычный файл зависимостей.")
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_-]+)==([0-9]+(?:\.[0-9]+)*)", line)
        if not match or match.group(1) in pins:
            raise RuntimeSetupError("Список зависимостей повреждён: требуются уникальные точные версии.")
        pins[match.group(1)] = match.group(2)
    if set(pins) != set(MODULES):
        raise RuntimeSetupError("Набор зависимостей не соответствует этому адаптеру.")
    return pins


def requirements_hash() -> str:
    requirement_pins()
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def child_environment(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Keep OS/tool settings, never inherit service keys or approval assertions."""
    source = os.environ if env is None else env
    allowed = {"HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "SYSTEMROOT", "WINDIR",
               "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE",
               "PATH", "TESSDATA_PREFIX", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    result = {key: value for key, value in source.items() if key.upper() in allowed}
    paths = [p for p in result.get("PATH", "").split(os.pathsep) if p and Path(p).is_absolute()]
    extras = list(COMMON_BIN_DIRS)
    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = source.get(variable)
            if base:
                extras.append(str(Path(base) / "LibreOffice" / "program"))
    for extra in extras:
        if Path(extra).is_dir() and extra not in paths:
            paths.append(extra)
    result["PATH"] = os.pathsep.join(paths)
    result["KSRF_SKILLS_ROOT"] = str(SKILLS_ROOT)
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    result["PYTHONNOUSERSITE"] = "1"
    # PIP_CONFIG_FILE disables *all* pip configuration, including site/global files.
    result["PIP_CONFIG_FILE"] = os.devnull
    result["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    result["PIP_KEYRING_PROVIDER"] = "disabled"
    return result


def managed_python(state: Path, *, require_current: bool = True) -> Path | None:
    if not _check_state(state):
        return None
    active = state / ACTIVE_FILE
    if not active.exists() and not active.is_symlink():
        return None
    record = _read_record(active)
    if record.get("format") != STATE_FORMAT:
        raise RuntimeSetupError("Служебная запись активного окружения повреждена.")
    if record.get("requirements_sha256") != requirements_hash():
        if not require_current:
            return None
        raise RuntimeSetupError("Окружение создано для другого набора зависимостей. Повторите setup --documents для этого выпуска.")
    directory = record.get("environment")
    if not isinstance(directory, str) or not re.fullmatch(r"documents-py[0-9]+-[a-f0-9]{12}-[a-f0-9]{32}", directory):
        raise RuntimeSetupError("Путь управляемого Python повреждён.")
    root = state / "environments" / directory
    _no_symlink_components(root)
    _private_owned(state / "environments", directory=True)
    _private_owned(root, directory=True)
    python = root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    _no_symlink_components(python)
    config = root / "pyvenv.cfg"
    if config.is_symlink() or not config.is_file() or not python.is_file():
        raise RuntimeSetupError("Управляемое окружение неполно; повторите setup --documents.")
    values = {key.strip(): value.strip() for line in config.read_text(encoding="utf-8").splitlines()
              if "=" in line for key, value in [line.split("=", 1)]}
    if values.get("include-system-site-packages", "").lower() != "false":
        raise RuntimeSetupError("Окружение не изолировано от системных Python-пакетов.")
    return python


def _module_probe(python: Path, env: Mapping[str, str]) -> dict[str, Any]:
    program = """import importlib, importlib.metadata, json, sys
result = {'python': list(sys.version_info[:3]), 'packages': {}}
for name, module in json.loads(sys.argv[1]).items():
    try:
        importlib.import_module(module)
        result['packages'][name] = {'state': 'ready', 'version': importlib.metadata.version(name)}
    except Exception as error:
        result['packages'][name] = {'state': 'unavailable', 'error_type': type(error).__name__}
print(json.dumps(result))
"""
    try:
        completed = subprocess.run([str(python), "-I", "-B", "-c", program, json.dumps(MODULES)],
                                   env=dict(env), capture_output=True, text=True, timeout=30, check=False)
        result = json.loads(completed.stdout)
        if completed.returncode != 0 or not isinstance(result.get("packages"), dict):
            raise ValueError("invalid probe result")
        return result
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise RuntimeSetupError("Выбранный Python не прошёл локальную проверку библиотек.") from exc


def _tool_probe(name: str, arguments: Sequence[str], env: Mapping[str, str]) -> dict[str, Any]:
    executable = shutil.which(name, path=env.get("PATH"))
    if not executable:
        return {"state": "unavailable"}
    try:
        process = subprocess.run([executable, *arguments], env=dict(env), capture_output=True,
                                 text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "unavailable", "reason": "probe_failed"}
    return {"state": "ready" if process.returncode == 0 else "unavailable",
            "exit_code": process.returncode}


def diagnose(state: Path) -> dict[str, Any]:
    selected = managed_python(state)
    python = selected or Path(sys.executable)
    env = child_environment()
    modules = _module_probe(python, env)
    pins = requirement_pins()
    for name, package in modules["packages"].items():
        package["expected_version"] = pins[name]
        package["matches_pin"] = package.get("version") == pins[name]
    tools = {name: _tool_probe(name, arguments, env) for name, arguments in (
        ("pdftotext", ["-v"]), ("pdftoppm", ["-v"]), ("soffice", ["--version"]),
        ("tesseract", ["--version"]))}
    if tools["soffice"]["state"] != "ready":
        tools["soffice"] = _tool_probe("libreoffice", ["--version"], env)
    languages: list[str] = []
    tesseract = shutil.which("tesseract", path=env.get("PATH"))
    if tesseract and tools["tesseract"]["state"] == "ready":
        try:
            process = subprocess.run([tesseract, "--list-langs"], env=env, capture_output=True,
                                     text=True, timeout=10, check=False)
            if process.returncode == 0:
                languages = sorted({line.strip() for line in (process.stdout + "\n" + process.stderr).splitlines()
                                    if re.fullmatch(r"[A-Za-z0-9_/-]+", line.strip())})
        except (OSError, subprocess.TimeoutExpired):
            pass
    tools["tesseract"]["languages"] = languages
    missing_languages = sorted({"rus", "eng"} - set(languages))
    missing_packages = [name for name in DOCUMENT_MODULES if modules["packages"][name]["state"] != "ready"]

    def operation(title: str, missing: list[str], next_action: str) -> dict[str, Any]:
        return {"title": title, "state": "ready" if not missing else "unavailable",
                "missing": missing, "next_action": "Можно выполнять эту локальную операцию." if not missing else next_action}

    def absent(*names: str) -> list[str]:
        return [name for name in names if tools[name]["state"] != "ready"]

    operations = {
        "case_workspace": operation("Папка дела, регистрация файлов и текстовый рабочий маршрут", [], ""),
        "text_docx_collection": operation("Извлечение текста TXT, Markdown и DOCX", [], ""),
        "pdf_text_collection": operation("Извлечение существующего текстового слоя PDF", absent("pdftotext"),
                                         "Установите Poppler (pdftotext) или используйте доступный инструмент чтения PDF в агенте."),
        "image_ocr": operation("Локальное распознавание изображений на русском и английском", absent("tesseract") + missing_languages,
                               "Нужен Tesseract и его языковые данные rus и eng; доступный текст можно разбирать отдельно."),
        "pdf_ocr": operation("Локальное распознавание сканированного PDF", absent("pdftoppm", "tesseract") + missing_languages,
                             "Нужны Poppler (pdftoppm), Tesseract и языковые данные rus и eng."),
        "working_document_export": operation("Рабочие DOCX/PDF и изображения страниц", missing_packages + absent("soffice", "pdftoppm"),
                                             "Для Python-пакетов выполните setup --documents; для PDF нужны LibreOffice и Poppler. Текстовый проект можно продолжать."),
    }
    return {"format": STATE_FORMAT, "state": "ready" if all(row["state"] == "ready" for row in operations.values()) else "degraded",
            "interpreter": "managed" if selected else "current", "python": modules["python"],
            "python_packages": modules["packages"], "tools": tools, "operations": operations,
            "state_dir": str(state), "managed_environment_present": selected is not None,
            "automatic_installation_performed": False, "document_transmission_performed": False,
            "network_probe_performed": False, "filing_authority": False,
            "raw_runtime_doctor": "run -- doctor --profile basic --json",
            "note": "Техническая готовность операции не подтверждает полноту чтения, правовую оценку, актуальность норм или право подачи. Скан требует сверки; OCR по умолчанию ограничен первыми 8 страницами PDF."}


def _run_setup_step(command: Sequence[str], state: Path, env: Mapping[str, str], label: str) -> None:
    # No pip logs are echoed: index/proxy credentials must never enter diagnostics.
    try:
        result = subprocess.run(list(command), cwd=state, env=dict(env), capture_output=True,
                                text=True, timeout=600, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeSetupError(f"{label}: время ожидания истекло. Незавершённое окружение сохранено отдельно; повторите настройку после устранения причины.") from exc
    if result.returncode:
        raise RuntimeSetupError(f"{label}: код {result.returncode}. Проверьте наличие Python venv/pip, доступ к PyPI и системные сертификаты; недоверенные сертификаты не отключайте. Повторная настройка создаст отдельное окружение.")


def setup_documents(state: Path) -> dict[str, Any]:
    if sys.version_info < (3, 11):
        raise RuntimeSetupError("Для документного окружения нужен Python 3.11 или новее. Запустите setup через него; базовый анализ доступен отдельно.")
    pins = requirement_pins()
    digest = requirements_hash()
    env = child_environment()
    existing = managed_python(state, require_current=False)
    if existing:
        current = _module_probe(existing, env)
        if all(current["packages"][name].get("version") == version and current["packages"][name]["state"] == "ready" for name, version in pins.items()):
            return {"format": STATE_FORMAT, "state": "already_ready", "state_dir": str(state),
                    "packages_installed": False, "network_used": False, "filing_authority": False}
    with _setup_lock(state):
        environments = state / "environments"
        if not environments.exists():
            environments.mkdir(mode=0o700)
        _no_symlink_components(environments)
        _private_owned(environments, directory=True)
        name = f"documents-py{sys.version_info.major}{sys.version_info.minor}-{digest[:12]}-{uuid.uuid4().hex}"
        destination = environments / name
        destination.mkdir(mode=0o700)
        _run_setup_step([sys.executable, "-I", "-B", "-m", "venv", "--copies", str(destination)], state, env, "Создание venv")
        _check_state(state)
        _no_symlink_components(destination)
        python = destination / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        _no_symlink_components(python)
        _run_setup_step([str(python), "-I", "-B", "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                         "--no-cache-dir", "--keyring-provider", "disabled", "--index-url", "https://pypi.org/simple",
                         "--only-binary=:all:", "--no-deps", "-r", str(REQUIREMENTS)], state, env, "Установка объявленных Python-пакетов")
        checked = _module_probe(python, env)
        if any(checked["packages"][name].get("version") != version or checked["packages"][name]["state"] != "ready" for name, version in pins.items()):
            raise RuntimeSetupError("Установленные библиотеки не совпали с объявленными версиями; окружение не активировано.")
        _run_setup_step([str(python), "-I", "-B", "-m", "pip", "check"], state, env, "Проверка связей зависимостей")
        _check_state(state)
        _write_record(state, ACTIVE_FILE, {"format": STATE_FORMAT, "environment": destination.name,
                                        "requirements_sha256": digest})
    return {"format": STATE_FORMAT, "state": "documents_ready", "state_dir": str(state),
            "packages_installed": True, "network_used": True, "index": "https://pypi.org/simple",
            "system_packages_installed": False, "package_modified": False, "filing_authority": False,
            "next_action": "Выполните doctor: LibreOffice, Poppler и OCR устанавливаются отдельно при необходимости."}


def delegate(state: Path, route: str, arguments: Sequence[str]) -> int:
    script = SKILL_ROOT / "scripts" / ("ksrf.py" if route == "run" else "ksrf_autocollect.py")
    if script.is_symlink() or not script.is_file():
        raise RuntimeSetupError("Исполняемый файл основного маршрута отсутствует в пакете.")
    forwarded = list(arguments)
    if forwarded[:1] == ["--"]:
        forwarded.pop(0)
    if not forwarded:
        forwarded = ["--help"]
    python = managed_python(state) or Path(sys.executable)
    completed = subprocess.run([str(python), "-I", "-B", str(script), *forwarded],
                               env=child_environment(), check=False)
    return completed.returncode


class RussianParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any):
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "Использование:").replace("options:", "параметры:").replace("positional arguments:", "команды:").replace("show this help message and exit", "показать справку и выйти")

    def error(self, message: str) -> None:
        translations = {"the following arguments are required:": "обязательные параметры:",
                        "unrecognized arguments:": "неизвестные параметры:",
                        "invalid choice:": "неподдерживаемое значение:",
                        "choose from": "допустимые значения", "expected one argument": "требуется одно значение"}
        for original, translated in translations.items():
            message = message.replace(original, translated)
        self.print_usage(sys.stderr)
        self.exit(2, "Ошибка параметров: " + message + "\n")


def parser() -> argparse.ArgumentParser:
    result = RussianParser(description="Локальная среда плагина КС РФ: диагностика, отдельный Python и существующие команды.")
    result.add_argument("--state-dir", type=Path, metavar="ПАПКА", help="Абсолютный путь вне плагина; по умолчанию KSRF_PLUGIN_STATE_DIR или папка данных пользователя.")
    commands = result.add_subparsers(dest="command", required=True)
    for name, help_text in (("doctor", "Проверить возможности по операциям без установки и внешней сети."),
                            ("setup", "Подготовить отдельное окружение; --documents явно разрешает загрузку пакетов с PyPI.")):
        sub = commands.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("--json", action="store_true", help="Вывести машиночитаемый отчёт.")
        if name == "setup":
            sub.add_argument("--documents", action="store_true", required=True, help="Создать отдельный venv с закреплёнными документными библиотеками.")
    for name, help_text in (("run", "Передать параметры основному ksrf.py."),
                            ("collect", "Передать файлы, папки и параметры ksrf_autocollect.py.")):
        sub = commands.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("arguments", nargs=argparse.REMAINDER, metavar="ПАРАМЕТРЫ", help="Параметры после -- передаются без изменения.")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        state = validate_state_dir(arguments.state_dir if arguments.state_dir is not None else default_state_dir())
        if arguments.command in {"run", "collect"}:
            return delegate(state, arguments.command, arguments.arguments)
        report = diagnose(state) if arguments.command == "doctor" else setup_documents(state)
        if arguments.json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        elif arguments.command == "doctor":
            print("Возможности локального плагина:")
            for row in report["operations"].values():
                print(f"- {row['title']}: {'доступно' if row['state'] == 'ready' else 'нужна настройка'}. {row['next_action']}")
            print(report["note"])
        else:
            print("Документное Python-окружение готово. Основной Python и файлы плагина не изменены.")
            print("Проверьте doctor для LibreOffice, Poppler и OCR. Подписание и подача остаются действиями человека.")
        return 0
    except (RuntimeSetupError, OSError) as exc:
        message = str(exc) if isinstance(exc, RuntimeSetupError) else "Не удалось прочитать или создать локальные файлы окружения. Проверьте выбранную папку и права доступа."
        if getattr(arguments, "json", False):
            print(json.dumps({"format": STATE_FORMAT, "state": "blocked", "message": message, "filing_authority": False}, ensure_ascii=False))
        else:
            print("Ошибка: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
