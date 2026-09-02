from __future__ import annotations

import io
import errno
import json
import os
from pathlib import Path
import shutil
import shlex
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import install_skillset as installer  # noqa: E402
from skillset_file_contract import SKILL_NAMES  # noqa: E402


def _make_source(root: Path, generation: str) -> Path:
    source = root / f"source-{generation}"
    source.mkdir()
    for index, skill_name in enumerate(SKILL_NAMES):
        skill = source / skill_name
        (skill / "nested").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"# {skill_name}\ngeneration={generation}\n",
            encoding="utf-8",
        )
        (skill / "nested" / "payload.txt").write_text(
            f"{generation}:{index}:{skill_name}\n",
            encoding="utf-8",
        )
    return source


def _snapshot(path: Path) -> tuple[tuple[object, ...], ...] | None:
    if not path.exists() and not path.is_symlink():
        return None
    rows: list[tuple[object, ...]] = []
    items = [path]
    if path.is_dir() and not path.is_symlink():
        items.extend(sorted(path.rglob("*"), key=lambda item: item.as_posix()))
    for item in items:
        metadata = item.lstat()
        relative = "." if item == path else item.relative_to(path).as_posix()
        mode = stat.S_IMODE(metadata.st_mode)
        if item.is_symlink():
            rows.append((relative, "symlink", mode, os.readlink(item)))
        elif item.is_dir():
            rows.append((relative, "directory", mode, metadata.st_mtime_ns))
        elif item.is_file():
            rows.append(
                (
                    relative,
                    "file",
                    mode,
                    metadata.st_mtime_ns,
                    item.read_bytes(),
                )
            )
        else:
            rows.append((relative, "other", mode, metadata.st_mtime_ns))
    return tuple(rows)


def _status(target: Path) -> dict[str, object]:
    return installer.inspect_installation_status(target)


def _write_fake_repo_verification_policy(checkout: Path) -> None:
    scripts = (
        checkout
        / "skills"
        / "ksrf-complaint-cycle"
        / "scripts"
    )
    scripts.mkdir(parents=True)
    for name in (
        "validate_ksrf_skillset.py",
        "verify_offline_self_containment.py",
    ):
        (scripts / name).write_text("# fixed repo-side test policy\n", encoding="utf-8")


def _tracked_payload_inventory(
    target: Path,
    transaction: Path,
) -> dict[tuple[int, int], int]:
    inventory: dict[tuple[int, int], int] = {}
    roots = [transaction]
    roots.extend(
        target / skill_name
        for skill_name in SKILL_NAMES
        if (target / skill_name).is_dir()
    )
    for root in roots:
        for path in [root, *root.rglob("*")]:
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                continue
            key = (metadata.st_dev, metadata.st_ino)
            if key in inventory:
                raise AssertionError(f"duplicate tracked payload inode: {path}")
            if metadata.st_size <= 0 or metadata.st_size >= 1024 * 1024:
                raise AssertionError(f"fixture payload size is outside the test bound: {path}")
            inventory[key] = metadata.st_size
    return inventory


def _measure_tracked_semantic_reads(
    target: Path,
    transaction: Path,
    operation,
):
    inventory = _tracked_payload_inventory(target, transaction)
    original_read = installer.os.read
    original_observe = installer._status_observe_evidence_once
    active_sample: int | None = None
    sample_count = 0
    bytes_by_sample: dict[tuple[int, tuple[int, int]], int] = {}
    positive_calls_by_sample: dict[tuple[int, tuple[int, int]], int] = {}

    def counted_read(descriptor: int, size: int) -> bytes:
        metadata = os.fstat(descriptor)
        content = original_read(descriptor, size)
        key = (metadata.st_dev, metadata.st_ino)
        if key in inventory and active_sample is None and content:
            raise AssertionError("tracked payload read outside a semantic sample")
        if active_sample is not None and key in inventory:
            sample_key = (active_sample, key)
            bytes_by_sample[sample_key] = (
                bytes_by_sample.get(sample_key, 0) + len(content)
            )
            if content:
                positive_calls_by_sample[sample_key] = (
                    positive_calls_by_sample.get(sample_key, 0) + 1
                )
        return content

    def observed_once(*args, **kwargs):
        nonlocal active_sample, sample_count
        if active_sample is not None:
            raise AssertionError("semantic samples must not be nested")
        sample_count += 1
        active_sample = sample_count
        try:
            return original_observe(*args, **kwargs)
        finally:
            active_sample = None

    with (
        patch.object(installer.os, "read", side_effect=counted_read),
        patch.object(
            installer,
            "_status_observe_evidence_once",
            side_effect=observed_once,
        ),
    ):
        result = operation()
    return (
        result,
        inventory,
        sample_count,
        bytes_by_sample,
        positive_calls_by_sample,
    )


def _measure_early_invalid_reads(
    target: Path,
    transaction: Path,
    operation,
):
    inventory = _tracked_payload_inventory(target, transaction)
    original_read = installer.os.read
    original_semantic = installer._status_observe_evidence_once
    original_raw = installer._status_raw_observation_fingerprint
    active_phase: tuple[str, int] | None = None
    semantic_count = 0
    raw_count = 0
    bytes_by_phase: dict[tuple[str, int, tuple[int, int]], int] = {}
    positive_calls_by_phase: dict[tuple[str, int, tuple[int, int]], int] = {}

    def counted_read(descriptor: int, size: int) -> bytes:
        metadata = os.fstat(descriptor)
        content = original_read(descriptor, size)
        key = (metadata.st_dev, metadata.st_ino)
        if key in inventory and active_phase is None and content:
            raise AssertionError("tracked payload read outside a measured phase")
        if active_phase is not None and key in inventory:
            phase_key = (*active_phase, key)
            bytes_by_phase[phase_key] = (
                bytes_by_phase.get(phase_key, 0) + len(content)
            )
            if content:
                positive_calls_by_phase[phase_key] = (
                    positive_calls_by_phase.get(phase_key, 0) + 1
                )
        return content

    def semantic_once(*args, **kwargs):
        nonlocal active_phase, semantic_count
        if active_phase is not None:
            raise AssertionError("status payload phases must not be nested")
        semantic_count += 1
        active_phase = ("semantic", semantic_count)
        try:
            return original_semantic(*args, **kwargs)
        finally:
            active_phase = None

    def raw_once(*args, **kwargs):
        nonlocal active_phase, raw_count
        if active_phase is not None:
            raise AssertionError("status payload phases must not be nested")
        raw_count += 1
        active_phase = ("raw", raw_count)
        try:
            return original_raw(*args, **kwargs)
        finally:
            active_phase = None

    with (
        patch.object(installer.os, "read", side_effect=counted_read),
        patch.object(
            installer,
            "_status_observe_evidence_once",
            side_effect=semantic_once,
        ),
        patch.object(
            installer,
            "_status_raw_observation_fingerprint",
            side_effect=raw_once,
        ),
    ):
        result = operation()
    return (
        result,
        inventory,
        semantic_count,
        raw_count,
        bytes_by_phase,
        positive_calls_by_phase,
    )


def _leave_interrupted_transaction(root: Path, target: Path) -> Path:
    source_a = _make_source(root, "A")
    source_b = _make_source(root, "B")
    installer.copy_skillset(source_a, target)
    original_replace = installer._replace_path
    actual_target = target.resolve(strict=True)

    def die_during_placement(source: Path, destination: Path) -> None:
        if destination == actual_target / SKILL_NAMES[1]:
            raise SystemExit(91)
        original_replace(source, destination)

    with patch.object(installer, "_replace_path", side_effect=die_during_placement):
        try:
            installer.copy_skillset(source_b, target)
        except SystemExit as exc:
            if exc.code != 91:
                raise
        else:
            raise AssertionError("interrupted transaction fixture did not stop")
    transaction_roots = sorted(target.glob(f"{installer.INSTALL_TRANSACTION_PREFIX}*"))
    if len(transaction_roots) != 1:
        raise AssertionError(f"expected one interrupted transaction, got {transaction_roots}")
    return transaction_roots[0]


class ReadOnlyInstallerStatusTests(unittest.TestCase):
    def test_direct_status_disables_local_bytecode_writes_before_imports(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tools = root / "tools"
            tools.mkdir()
            for name in ("install_skillset.py", "skillset_file_contract.py"):
                shutil.copy2(TOOLS / name, tools / name)
            target = root / "missing-target"
            environment = dict(os.environ)
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            environment.pop("PYTHONPYCACHEPREFIX", None)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(tools / "install_skillset.py"),
                    "--status",
                    "--target",
                    str(target),
                    "--json",
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 10, completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertFalse((tools / "__pycache__").exists())

    def test_missing_target_is_not_installed_and_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw)
            target = parent / "missing" / "skills"
            before = _snapshot(parent)

            report = _status(target)

            self.assertEqual(report["schema_version"], "1.0")
            self.assertEqual(report["status"], "not_installed")
            self.assertEqual(report["exit_code"], 10)
            self.assertFalse(report["target_exists"])
            self.assertEqual(_snapshot(parent), before)
            self.assertFalse(target.exists())

    def test_clean_and_incomplete_status_are_exact_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            before = _snapshot(target)

            with (
                patch.object(installer, "_status_linux_fd_mount_id", return_value=1),
                patch.object(
                    installer.os,
                    "read",
                    side_effect=AssertionError(
                        "clean status must not read managed payload bytes"
                    ),
                ),
            ):
                clean = _status(target)

            self.assertEqual(clean["status"], "clean")
            self.assertEqual(clean["exit_code"], 0)
            self.assertEqual(clean["managed_skills"]["present"], len(SKILL_NAMES))
            self.assertEqual(clean["managed_skills"]["missing"], [])
            self.assertEqual(_snapshot(target), before)

            missing_name = SKILL_NAMES[-1]
            missing = target / missing_name
            for child in sorted(missing.rglob("*"), reverse=True):
                child.unlink() if child.is_file() else child.rmdir()
            missing.rmdir()
            partial_before = _snapshot(target)

            with (
                patch.object(installer, "_status_linux_fd_mount_id", return_value=1),
                patch.object(
                    installer.os,
                    "read",
                    side_effect=AssertionError(
                        "incomplete status must not read managed payload bytes"
                    ),
                ),
            ):
                incomplete = _status(target)

            self.assertEqual(incomplete["status"], "incomplete")
            self.assertEqual(incomplete["exit_code"], 20)
            self.assertEqual(incomplete["managed_skills"]["missing"], [missing_name])
            self.assertEqual(_snapshot(target), partial_before)

    def test_clean_status_recommends_offline_then_optional_online_checks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            before = _snapshot(target)

            with (
                patch.object(
                    socket,
                    "create_connection",
                    side_effect=AssertionError("status must stay offline"),
                ),
                patch.object(
                    installer,
                    "copy_skillset",
                    side_effect=AssertionError("status must not install"),
                ),
                patch.object(
                    installer,
                    "verify_installed_skillset",
                    side_effect=AssertionError("status must not execute verification"),
                ),
                patch.object(
                    installer,
                    "_load_repo_verification_policy",
                    side_effect=AssertionError("status must not load validator policy"),
                ),
            ):
                report = _status(target)
                human = installer.render_installation_status(report)

            self.assertEqual(report["schema_version"], "1.0")
            self.assertEqual(report["status"], "clean")
            self.assertEqual(report["exit_code"], 0)
            self.assertIn("структур", str(report["message"]).lower())
            self.assertIn("содержим", str(report["message"]).lower())
            self.assertIn("актуальност", str(report["message"]).lower())
            action = str(report["recommended_action"])
            action_lines = action.splitlines()
            offline_prefix = "Сначала — проверка содержимого без сети: "
            online_prefix = (
                "При необходимости — сравнение с текущей опубликованной версией "
                "(нужна сеть): "
            )
            self.assertTrue(action_lines[0].startswith(offline_prefix))
            self.assertTrue(action_lines[1].startswith(online_prefix))
            offline_command = shlex.split(action_lines[0].removeprefix(offline_prefix))
            online_command = shlex.split(action_lines[1].removeprefix(online_prefix))
            installer_entrypoint = REPO / "install.sh"
            self.assertTrue(installer_entrypoint.is_file())
            self.assertEqual(
                offline_command,
                [
                    str(installer_entrypoint),
                    "--verify",
                    "--target",
                    str(installer._absolute_without_resolving(target)),
                ],
            )
            self.assertEqual(
                online_command,
                [
                    str(installer_entrypoint),
                    "--verify-current",
                    "--target",
                    str(installer._absolute_without_resolving(target)),
                ],
            )
            self.assertLess(action.index(offline_prefix), action.index(online_prefix))
            self.assertIn("без сети", action.lower())
            self.assertIn("нужна сеть", action.lower())
            self.assertIn("--verify-current", action)
            self.assertNotIn("main", action)
            self.assertNotIn("коды 10", action)
            self.assertNotIn("подтверждается обычной установкой", action)
            self.assertIn("Что делать:", human)
            self.assertIn("--verify", human)
            self.assertIn("--verify-current", human)
            self.assertEqual(_snapshot(target), before)

    def test_clean_json_preserves_schema_while_exposing_ordered_checks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target with spaces and 'quote'"
            installer.copy_skillset(source, target)
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = installer.main(
                    ["--status", "--target", str(target), "--json"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            report = json.loads(stdout.getvalue())
            self.assertEqual(
                set(report),
                {
                    "schema_version",
                    "status",
                    "severity",
                    "exit_code",
                    "reason_code",
                    "target",
                    "target_exists",
                    "managed_skills",
                    "transaction",
                    "message",
                    "recommended_action",
                    "observation",
                },
            )
            action_lines = str(report["recommended_action"]).splitlines()
            offline_prefix = "Сначала — проверка содержимого без сети: "
            online_prefix = (
                "При необходимости — сравнение с текущей опубликованной версией "
                "(нужна сеть): "
            )
            offline_command = shlex.split(
                action_lines[0].removeprefix(offline_prefix)
            )
            online_command = shlex.split(
                action_lines[1].removeprefix(online_prefix)
            )
            exact_target = str(installer._absolute_without_resolving(target))
            self.assertEqual(offline_command[-3:], ["--verify", "--target", exact_target])
            self.assertEqual(
                online_command[-3:], ["--verify-current", "--target", exact_target]
            )
            self.assertEqual(offline_command[0], online_command[0])
            self.assertFalse(report["observation"]["explicit_mutations_performed"])

    def test_clean_guidance_has_honest_fallback_without_repo_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            detached_tool = Path(raw) / "tools" / "install_skillset.py"
            with patch.object(installer, "__file__", str(detached_tool)):
                action = installer._status_runtime_verification_action(
                    Path(raw) / "skills"
                )

            self.assertIn("недоступна", action)
            self.assertIn("Обновите репозиторий", action)
            self.assertNotIn("--verify", action)

    def test_clean_guidance_does_not_emit_non_executable_entrypoint(self) -> None:
        with patch.object(installer.os, "access", return_value=False):
            action = installer._status_runtime_verification_action(
                Path("/tmp/ksrf-runtime-target")
            )

        self.assertIn("недоступна", action)
        self.assertIn("Обновите репозиторий", action)
        self.assertNotIn("--verify", action)

    def test_clean_guidance_does_not_emit_symlinked_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tools = root / "tools"
            tools.mkdir()
            detached_tool = tools / "install_skillset.py"
            actual_entrypoint = root / "actual-installer.sh"
            actual_entrypoint.write_text("#!/bin/sh\n", encoding="utf-8")
            actual_entrypoint.chmod(0o755)
            (root / "install.sh").symlink_to(actual_entrypoint)

            with patch.object(installer, "__file__", str(detached_tool)):
                action = installer._status_runtime_verification_action(
                    root / "skills"
                )

        self.assertIn("недоступна", action)
        self.assertNotIn("--verify", action)

    def test_clean_guidance_rejects_control_characters_without_line_spoofing(
        self,
    ) -> None:
        actions: set[str] = set()
        for marker in ("\nЛОЖНЫЙ УСПЕХ", "\rподмена", "\x1b[31mкрасный", "\tсдвиг"):
            with self.subTest(marker=repr(marker)):
                action = installer._status_runtime_verification_action(
                    Path("/tmp/ksrf-runtime" + marker)
                )
                actions.add(action)

                self.assertIn("сформировать нельзя", action)
                self.assertNotIn("--verify", action)
                self.assertNotIn(marker, action)
        self.assertEqual(len(actions), 1)

    def test_non_clean_actions_are_unchanged_and_do_not_inspect_entrypoint(self) -> None:
        expected_actions = {
            "not_installed": "Запустите обычную установку из опубликованного набора.",
            "incomplete": "Запустите обычную установку, чтобы восстановить полный набор.",
            "recovery_required": (
                "Если установка ещё выполняется, дождитесь её завершения и повторите "
                "проверку; иначе запустите обычную установку для проверенного восстановления."
            ),
            "unsafe": (
                "Не удаляйте служебные данные вручную; сохраните найденные доказательства "
                "и проверьте путь или журнал перед новой установкой."
            ),
        }

        with patch.object(
            installer,
            "_status_runtime_verification_action",
            side_effect=AssertionError("non-clean status must not inspect entrypoint"),
        ):
            for status_name, expected_action in expected_actions.items():
                with self.subTest(status=status_name):
                    report = installer._status_report(
                        status_name,
                        Path("/tmp/ksrf-status-target"),
                        target_exists=status_name != "not_installed",
                    )
                    self.assertEqual(report["recommended_action"], expected_action)

    def test_status_and_verify_preflight_escape_control_characters_end_to_end(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "missing\nЛОЖНЫЙ УСПЕХ"
            for mode, expected_exit, stream_name in (
                ("--status", 10, "stdout"),
                ("--verify-current", 1, "stderr"),
            ):
                with self.subTest(mode=mode):
                    completed = subprocess.run(
                        [
                            str(REPO / "install.sh"),
                            mode,
                            "--target",
                            str(target),
                        ],
                        cwd=REPO,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    output = getattr(completed, stream_name)
                    self.assertEqual(completed.returncode, expected_exit)
                    if mode == "--status":
                        self.assertIn(r"\x0aЛОЖНЫЙ УСПЕХ", output)
                    else:
                        self.assertIn("Проверка не выполнена", output)
                        self.assertNotIn(r"\x0aЛОЖНЫЙ УСПЕХ", output)
                    self.assertNotIn("\nЛОЖНЫЙ УСПЕХ", output)

    @unittest.skipUnless(os.name == "posix", "surrogateescaped paths require POSIX")
    def test_clean_guidance_does_not_emit_dead_command_for_non_utf8_target(self) -> None:
        target = Path(os.fsdecode(b"/tmp/ksrf-status-\xff"))

        action = installer._status_runtime_verification_action(target)

        self.assertIn("непечатаемые байты", action)
        self.assertIn("сформировать нельзя", action)
        self.assertIn("UTF-8-пути", action)
        self.assertNotIn("--verify", action)

    def test_status_never_creates_or_locks_persistent_lock_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            lock_path = target / installer.INSTALL_LOCK_FILE_NAME
            lock_path.unlink()
            before = _snapshot(target)
            real_open = os.open

            def read_only_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
                forbidden = os.O_CREAT | os.O_TRUNC | os.O_WRONLY | os.O_RDWR
                self.assertEqual(flags & forbidden, 0, f"mutating os.open flags: {flags}")
                if not flags & getattr(os, "O_DIRECTORY", 0):
                    self.assertNotEqual(
                        flags & getattr(os, "O_NONBLOCK", 0),
                        0,
                        f"status file open can block on a substituted FIFO: {flags}",
                    )
                return real_open(path, flags, *args, **kwargs)

            with (
                patch.object(installer.fcntl, "flock", side_effect=AssertionError("flock")),
                patch.object(installer.os, "open", side_effect=read_only_open),
                patch.object(
                    installer,
                    "_write_journal",
                    side_effect=AssertionError("journal write"),
                ),
                patch.object(
                    installer,
                    "_fsync_directory",
                    side_effect=AssertionError("fsync"),
                ),
                patch.object(
                    installer,
                    "_recover_existing_transaction",
                    side_effect=AssertionError("recovery"),
                ),
                patch.object(
                    installer,
                    "_cleanup_stale_garbage",
                    side_effect=AssertionError("cleanup"),
                ),
            ):
                report = _status(target)

            self.assertEqual(report["status"], "clean")
            self.assertFalse(lock_path.exists())
            self.assertEqual(_snapshot(target), before)

    def test_valid_interrupted_transaction_is_recovery_required_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            installer.copy_skillset(source_a, target)
            original_replace = installer._replace_path
            actual_target = target.resolve(strict=True)

            def die_during_placement(source: Path, destination: Path) -> None:
                if destination == actual_target / SKILL_NAMES[1]:
                    raise SystemExit(91)
                original_replace(source, destination)

            with patch.object(installer, "_replace_path", side_effect=die_during_placement):
                with self.assertRaisesRegex(SystemExit, "91"):
                    installer.copy_skillset(source_b, target)

            transaction_roots = sorted(target.glob(f"{installer.INSTALL_TRANSACTION_PREFIX}*"))
            self.assertEqual(len(transaction_roots), 1)
            transaction_root = transaction_roots[0]
            journal = json.loads(
                (transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME).read_text(
                    encoding="utf-8"
                )
            )
            before = _snapshot(target)

            report = _status(target)

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(report["exit_code"], 20)
            self.assertEqual(report["transaction"]["kind"], "transaction")
            self.assertEqual(report["transaction"]["phase"], journal["phase"])
            self.assertEqual(report["transaction"]["evidence_paths"], [str(transaction_root)])
            serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
            self.assertNotIn(str(journal["old_aggregate"]), serialized)
            self.assertNotIn(str(journal["incoming_aggregate"]), serialized)
            self.assertEqual(_snapshot(target), before)

    def test_multiple_roots_symlink_target_and_unsafe_lock_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.mkdir()
            for suffix in ("a" * 32, "b" * 32):
                (target / f"{installer.INSTALL_TRANSACTION_PREFIX}{suffix}").mkdir()
            multiple_before = _snapshot(target)
            multiple = _status(target)
            self.assertEqual(multiple["status"], "unsafe")
            self.assertEqual(multiple["exit_code"], 30)
            self.assertEqual(_snapshot(target), multiple_before)

            actual = root / "actual"
            actual.mkdir()
            alias = root / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            symlink_before = _snapshot(alias)
            symlinked = _status(alias)
            self.assertEqual(symlinked["status"], "unsafe")
            self.assertEqual(_snapshot(alias), symlink_before)

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            target.mkdir()
            lock = target / installer.INSTALL_LOCK_FILE_NAME
            lock.write_bytes(b"")
            lock.chmod(0o666)
            lock_before = _snapshot(target)
            unsafe_lock = _status(target)
            self.assertEqual(unsafe_lock["status"], "unsafe")
            self.assertEqual(_snapshot(target), lock_before)

    def test_target_replacement_after_open_is_unsafe_and_replacement_is_not_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            held = root / "held-original"
            original_snapshot = _snapshot(target)
            original_top_snapshot = installer._status_top_level_snapshot
            replaced = False

            def replace_after_first_sample(*args: object, **kwargs: object):
                nonlocal replaced
                result = original_top_snapshot(*args, **kwargs)
                if not replaced:
                    target.rename(held)
                    shutil.copytree(held, target)
                    (target / "replacement-sentinel.txt").write_bytes(b"do not scan\n")
                    replaced = True
                return result

            with patch.object(
                installer,
                "_status_top_level_snapshot",
                side_effect=replace_after_first_sample,
            ):
                report = _status(target)

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(_snapshot(held), original_snapshot)
            self.assertEqual(
                (target / "replacement-sentinel.txt").read_bytes(),
                b"do not scan\n",
            )

    def test_byte_identical_skill_inode_change_is_not_reported_clean(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            skill = target / SKILL_NAMES[0]
            previous = root / "previous-skill"
            original_top_snapshot = installer._status_top_level_snapshot
            replaced = False

            def replace_skill_after_first_sample(*args: object, **kwargs: object):
                nonlocal replaced
                result = original_top_snapshot(*args, **kwargs)
                if not replaced:
                    skill.rename(previous)
                    shutil.copytree(previous, skill)
                    replaced = True
                return result

            with patch.object(
                installer,
                "_status_top_level_snapshot",
                side_effect=replace_skill_after_first_sample,
            ):
                report = _status(target)

            self.assertEqual(report["status"], "recovery_required")
            self.assertNotEqual(report["status"], "clean")

    def test_evidence_root_replacement_stays_on_held_inode_and_never_returns_clean(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction_root = _leave_interrupted_transaction(root, target)
            retained = root / "retained-transaction"
            replacement = root / "replacement-evidence"
            replacement.mkdir()
            (replacement / "sentinel.txt").write_bytes(b"foreign evidence\n")
            original_open = installer._status_open_directory_at
            substituted = False

            def substitute_after_open(
                parent_descriptor: int,
                name: str,
                *,
                expected_device: int,
            ):
                nonlocal substituted
                result = original_open(
                    parent_descriptor,
                    name,
                    expected_device=expected_device,
                )
                if name == transaction_root.name and not substituted:
                    transaction_root.rename(retained)
                    transaction_root.symlink_to(replacement, target_is_directory=True)
                    substituted = True
                return result

            with patch.object(
                installer,
                "_status_open_directory_at",
                side_effect=substitute_after_open,
            ):
                report = _status(target)

            self.assertNotEqual(report["status"], "clean")
            self.assertIn(report["status"], {"recovery_required", "unsafe"})
            self.assertEqual((replacement / "sentinel.txt").read_bytes(), b"foreign evidence\n")
            self.assertTrue(retained.is_dir())

    def test_changing_journal_is_recovery_required_but_stable_malformed_is_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction_root = _leave_interrupted_transaction(root, target)
            journal_path = transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME
            original_read = installer._status_read_regular_at
            changed = False

            def change_after_first_journal_read(
                parent_descriptor: int,
                name: str,
                *,
                expected_device: int,
                capture_limit: int | None = None,
            ):
                nonlocal changed
                result = original_read(
                    parent_descriptor,
                    name,
                    expected_device=expected_device,
                    capture_limit=capture_limit,
                )
                if name == installer.INSTALL_TRANSACTION_JOURNAL_NAME and not changed:
                    journal_path.write_bytes(journal_path.read_bytes() + b" \n")
                    changed = True
                return result

            with (
                patch.object(
                    installer,
                    "_status_read_regular_at",
                    side_effect=change_after_first_journal_read,
                ),
                patch.object(
                    installer,
                    "_status_observe_evidence_once",
                    wraps=installer._status_observe_evidence_once,
                ) as semantic_scan,
                patch.object(
                    installer,
                    "_status_raw_observation_fingerprint",
                    wraps=installer._status_raw_observation_fingerprint,
                ) as raw_scan,
            ):
                changing = _status(target)

            self.assertEqual(changing["status"], "recovery_required")
            self.assertEqual(semantic_scan.call_count, 2)
            self.assertEqual(raw_scan.call_count, 0)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction_root = _leave_interrupted_transaction(root, target)
            journal_path = transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME
            journal_path.write_bytes(b"{stable malformed journal\n")
            before = _snapshot(target)

            malformed = _status(target)

            self.assertEqual(malformed["status"], "unsafe")
            self.assertEqual(_snapshot(target), before)

    def test_repaired_journal_after_invalid_read_is_reported_as_changed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction_root = _leave_interrupted_transaction(root, target)
            journal_path = transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME
            valid_payload = journal_path.read_bytes()
            journal_path.write_bytes(b"{temporarily malformed journal\n")
            original_read = installer._status_read_regular_at
            repaired = False

            def repair_after_invalid_read(
                parent_descriptor: int,
                name: str,
                *,
                expected_device: int,
                capture_limit: int | None = None,
            ):
                nonlocal repaired
                result = original_read(
                    parent_descriptor,
                    name,
                    expected_device=expected_device,
                    capture_limit=capture_limit,
                )
                if name == installer.INSTALL_TRANSACTION_JOURNAL_NAME and not repaired:
                    journal_path.write_bytes(valid_payload)
                    repaired = True
                return result

            with (
                patch.object(
                    installer,
                    "_status_read_regular_at",
                    side_effect=repair_after_invalid_read,
                ),
                patch.object(
                    installer,
                    "_status_observe_evidence_once",
                    wraps=installer._status_observe_evidence_once,
                ) as semantic_scan,
                patch.object(
                    installer,
                    "_status_raw_observation_fingerprint",
                    wraps=installer._status_raw_observation_fingerprint,
                ) as raw_scan,
            ):
                report = _status(target)

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(report["reason_code"], "observation_changed")
            self.assertEqual(semantic_scan.call_count, 2)
            self.assertEqual(raw_scan.call_count, 1)

    def test_type_confused_or_deep_journal_is_bounded_unsafe(self) -> None:
        mutations = (
            ("phase", lambda journal: journal.__setitem__("phase", [])),
            (
                "progress",
                lambda journal: journal["skills"][0].__setitem__("progress", []),
            ),
            (
                "cleanup",
                lambda journal: journal["cleanup"].__setitem__(
                    installer._STAGING_NAME,
                    [],
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                target = root / "target"
                transaction_root = _leave_interrupted_transaction(root, target)
                journal_path = transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
                mutate(journal)
                journal_path.write_text(json.dumps(journal), encoding="utf-8")

                report = _status(target)

                self.assertEqual(report["status"], "unsafe")
                self.assertEqual(report["exit_code"], 30)
                self.assertEqual(report["reason_code"], "unsafe_evidence")

        parser_bombs = (
            b"[" * 1500 + b"0" + b"]" * 1500,
            b'{"oversized_integer":' + b"9" * 5000 + b"}",
        )
        for payload in parser_bombs:
            with self.subTest(parser_bomb=len(payload)), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                target = root / "target"
                target.mkdir()
                transaction_root = target / (
                    installer.INSTALL_TRANSACTION_PREFIX + "d" * 32
                )
                transaction_root.mkdir(mode=0o700)
                journal_path = (
                    transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME
                )
                journal_path.write_bytes(payload)

                report = _status(target)

                self.assertEqual(report["status"], "unsafe")
                self.assertEqual(report["exit_code"], 30)

    def test_prejournal_metadata_and_nonterminal_gc_fail_closed(self) -> None:
        for label, mutate in (
            ("writable-root", lambda transaction: transaction.chmod(0o777)),
            (
                "writable-temp",
                lambda transaction: (
                    transaction / installer._JOURNAL_TEMP_NAME
                ).chmod(0o666),
            ),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                target = root / "target"
                target.mkdir()
                transaction = target / (
                    installer.INSTALL_TRANSACTION_PREFIX + "e" * 32
                )
                transaction.mkdir(mode=0o700)
                temporary = transaction / installer._JOURNAL_TEMP_NAME
                temporary.write_bytes(b"partial journal")
                temporary.chmod(0o600)
                mutate(transaction)

                report = _status(target)

                self.assertEqual(report["status"], "unsafe")
                self.assertEqual(report["exit_code"], 30)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction = _leave_interrupted_transaction(root, target)
            garbage = target / transaction.name.replace(
                installer.INSTALL_TRANSACTION_PREFIX,
                installer.INSTALL_GC_PREFIX,
                1,
            )
            transaction.rename(garbage)

            report = _status(target)

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(report["exit_code"], 30)

    def test_oversized_prejournal_file_is_rejected_before_any_read(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            target.mkdir()
            transaction = target / (
                installer.INSTALL_TRANSACTION_PREFIX + "c" * 32
            )
            transaction.mkdir(mode=0o700)
            temporary = transaction / installer._JOURNAL_TEMP_NAME
            with temporary.open("wb") as stream:
                stream.truncate(64 * 1024 * 1024 + 1)
            temporary.chmod(0o600)

            with patch.object(
                installer.os,
                "read",
                side_effect=AssertionError("oversized evidence must not be read"),
            ):
                report = _status(target)

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(report["exit_code"], 30)
            self.assertEqual(report["reason_code"], "unsafe_evidence")

    def test_oversized_prejournal_that_shrinks_during_budget_check_is_changing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            target.mkdir()
            transaction = target / (
                installer.INSTALL_TRANSACTION_PREFIX + "d" * 32
            )
            transaction.mkdir(mode=0o700)
            temporary = transaction / installer._JOURNAL_TEMP_NAME
            with temporary.open("wb") as stream:
                stream.truncate(installer._STATUS_SCAN_MAX_FILE_BYTES + 1)
            temporary.chmod(0o600)
            original_account = installer._StatusScanBudget.account
            shrunk = False

            def shrink_after_budget_stat(
                budget: installer._StatusScanBudget,
                components: tuple[str, ...],
                metadata: os.stat_result,
            ) -> None:
                nonlocal shrunk
                if (
                    not shrunk
                    and components == (installer._JOURNAL_TEMP_NAME,)
                    and metadata.st_size > installer._STATUS_SCAN_MAX_FILE_BYTES
                ):
                    shrunk = True
                    temporary.write_bytes(b"partial journal")
                    temporary.chmod(0o600)
                original_account(budget, components, metadata)

            with patch.object(
                installer._StatusScanBudget,
                "account",
                autospec=True,
                side_effect=shrink_after_budget_stat,
            ):
                report = _status(target)

            self.assertTrue(shrunk)
            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(report["exit_code"], 20)
            self.assertEqual(report["reason_code"], "observation_changed")

    def test_valid_recovery_reads_one_complete_payload_per_comparison_sample(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction = _leave_interrupted_transaction(root, target)

            with patch.object(
                installer,
                "_status_linux_fd_mount_id",
                return_value=1,
            ):
                with patch.object(
                    installer,
                    "_status_raw_observation_fingerprint",
                    wraps=installer._status_raw_observation_fingerprint,
                ) as raw_scan, patch.object(
                    installer,
                    "_status_capture_mount_boundary",
                    wraps=installer._status_capture_mount_boundary,
                ) as mount_samples:
                    (
                        report,
                        inventory,
                        sample_count,
                        bytes_by_sample,
                        positive_calls_by_sample,
                    ) = _measure_tracked_semantic_reads(
                        target,
                        transaction,
                        lambda: _status(target),
                    )

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(raw_scan.call_count, 0)
            self.assertEqual(mount_samples.call_count, 2)
            self.assertEqual(sample_count, 2)
            for sample in (1, 2):
                for key, size in inventory.items():
                    self.assertEqual(bytes_by_sample.get((sample, key), 0), size)
                    self.assertEqual(
                        positive_calls_by_sample.get((sample, key), 0),
                        1,
                    )

    def test_late_invalid_reuses_each_complete_semantic_sample(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction = _leave_interrupted_transaction(root, target)
            victim = target / SKILL_NAMES[2] / "SKILL.md"
            victim.write_text(
                victim.read_text(encoding="utf-8") + "late-invalid\n",
                encoding="utf-8",
            )

            with patch.object(
                installer,
                "_status_linux_fd_mount_id",
                return_value=1,
            ):
                with patch.object(
                    installer,
                    "_status_raw_observation_fingerprint",
                    wraps=installer._status_raw_observation_fingerprint,
                ) as raw_scan, patch.object(
                    installer,
                    "_status_capture_mount_boundary",
                    wraps=installer._status_capture_mount_boundary,
                ) as mount_samples:
                    (
                        report,
                        inventory,
                        sample_count,
                        bytes_by_sample,
                        positive_calls_by_sample,
                    ) = _measure_tracked_semantic_reads(
                        target,
                        transaction,
                        lambda: _status(target),
                    )

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(raw_scan.call_count, 0)
            self.assertEqual(mount_samples.call_count, 2)
            self.assertEqual(sample_count, 2)
            for sample in (1, 2):
                for key, size in inventory.items():
                    self.assertEqual(bytes_by_sample.get((sample, key), 0), size)
                    self.assertEqual(
                        positive_calls_by_sample.get((sample, key), 0),
                        1,
                    )

    def test_early_invalid_keeps_one_raw_completion_per_sample(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            transaction = _leave_interrupted_transaction(root, target)
            (transaction / installer.INSTALL_TRANSACTION_JOURNAL_NAME).write_bytes(b"{")

            journal = transaction / installer.INSTALL_TRANSACTION_JOURNAL_NAME
            journal_metadata = journal.lstat()
            journal_key = (journal_metadata.st_dev, journal_metadata.st_ino)
            with patch.object(
                installer,
                "_status_capture_mount_boundary",
                wraps=installer._status_capture_mount_boundary,
            ) as mount_samples:
                (
                    report,
                    inventory,
                    semantic_count,
                    raw_count,
                    bytes_by_phase,
                    positive_calls_by_phase,
                ) = _measure_early_invalid_reads(
                    target,
                    transaction,
                    lambda: _status(target),
                )

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(raw_count, 2)
            self.assertEqual(semantic_count, 2)
            self.assertEqual(mount_samples.call_count, 2)
            for sample in (1, 2):
                for key, size in inventory.items():
                    semantic_bytes = bytes_by_phase.get(
                        ("semantic", sample, key),
                        0,
                    )
                    semantic_calls = positive_calls_by_phase.get(
                        ("semantic", sample, key),
                        0,
                    )
                    if key == journal_key:
                        self.assertEqual(semantic_bytes, size)
                        self.assertEqual(semantic_calls, 1)
                    else:
                        self.assertEqual(semantic_bytes, 0)
                        self.assertEqual(semantic_calls, 0)
                    self.assertEqual(
                        bytes_by_phase.get(("raw", sample, key), 0),
                        size,
                    )
                    self.assertEqual(
                        positive_calls_by_phase.get(("raw", sample, key), 0),
                        1,
                    )

    def test_mount_checks_use_fd_mount_id_without_global_mount_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            _leave_interrupted_transaction(root, target)

            with (
                patch.object(
                    installer,
                    "_status_linux_fd_mount_id",
                    return_value=17,
                    create=True,
                ),
                patch.object(
                    installer,
                    "_status_linux_mountinfo_available",
                    return_value=True,
                    create=True,
                ),
                patch.object(
                    installer,
                    "_linux_mount_points",
                    wraps=installer._linux_mount_points,
                ) as mount_points,
            ):
                report = _status(target)

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(mount_points.call_count, 0)

    def test_fd_mount_id_rejects_same_device_bind_mount(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            child = target / "child"
            child.mkdir(parents=True)
            target_descriptor = os.open(target, installer._status_directory_flags())
            child_descriptor = os.open(child, installer._status_directory_flags())
            try:
                with patch.object(
                    installer,
                    "_status_linux_fd_mount_id",
                    side_effect=lambda descriptor: (
                        31 if descriptor == target_descriptor else 32
                    ),
                    create=True,
                ), patch.object(
                    installer,
                    "_status_linux_mountinfo_available",
                    return_value=True,
                    create=True,
                ):
                    boundary = installer._status_capture_mount_boundary(
                        target_descriptor
                    )
                    token = installer._STATUS_MOUNT_BOUNDARY.set(boundary)
                    try:
                        with (
                            patch.object(installer.os.path, "ismount", return_value=False),
                            patch.object(
                                installer,
                                "_linux_mount_points",
                                side_effect=AssertionError(
                                    "fd mount IDs must not parse the global mount table"
                                ),
                            ),
                        ):
                            self.assertTrue(
                                installer._status_fd_is_mount(child_descriptor)
                            )
                    finally:
                        installer._STATUS_MOUNT_BOUNDARY.reset(token)
            finally:
                os.close(child_descriptor)
                os.close(target_descriptor)

    def test_mount_boundary_samples_are_independent_classification_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            target_metadata = target.stat()
            target_sample = 0

            def changing_mount_id(descriptor: int) -> int:
                nonlocal target_sample
                metadata = os.fstat(descriptor)
                if (
                    metadata.st_dev == target_metadata.st_dev
                    and metadata.st_ino == target_metadata.st_ino
                ):
                    target_sample += 1
                return 40 + target_sample

            with (
                patch.object(
                    installer,
                    "_status_linux_fd_mount_id",
                    side_effect=changing_mount_id,
                    create=True,
                ),
                patch.object(
                    installer,
                    "_status_linux_mountinfo_available",
                    return_value=True,
                    create=True,
                ),
            ):
                report = _status(target)

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(report["reason_code"], "observation_changed")

    def test_mount_boundary_change_is_not_masked_by_unsafe_first_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            (target / installer.INSTALL_LOCK_FILE_NAME).chmod(0o666)
            target_metadata = target.stat()
            target_sample = 0

            def changing_mount_id(descriptor: int) -> int:
                nonlocal target_sample
                metadata = os.fstat(descriptor)
                if (
                    metadata.st_dev == target_metadata.st_dev
                    and metadata.st_ino == target_metadata.st_ino
                ):
                    target_sample += 1
                return 40 + target_sample

            with (
                patch.object(
                    installer,
                    "_status_linux_fd_mount_id",
                    side_effect=changing_mount_id,
                ),
                patch.object(
                    installer,
                    "_status_linux_mountinfo_available",
                    return_value=True,
                ),
            ):
                sentinel = ("path_ismount_only", None)
                token = installer._STATUS_MOUNT_BOUNDARY.set(sentinel)
                try:
                    report = _status(target)
                    self.assertEqual(installer._STATUS_MOUNT_BOUNDARY.get(), sentinel)
                finally:
                    installer._STATUS_MOUNT_BOUNDARY.reset(token)

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(report["reason_code"], "observation_changed")

    def test_journal_free_evidence_fingerprint_includes_live_skills(self) -> None:
        for label, prefix, with_temporary in (
            ("pre-journal", installer.INSTALL_TRANSACTION_PREFIX, True),
            ("empty-gc", installer.INSTALL_GC_PREFIX, False),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                source = _make_source(root, "A")
                target = root / "target"
                installer.copy_skillset(source, target)
                evidence = target / f"{prefix}{'f' * 32}"
                evidence.mkdir(mode=0o700)
                if with_temporary:
                    temporary = evidence / installer._JOURNAL_TEMP_NAME
                    temporary.write_bytes(b"partial journal")
                    temporary.chmod(0o600)
                victim = target / SKILL_NAMES[0] / "SKILL.md"
                original_observe = installer._status_observe_evidence_once
                observations = 0

                def mutate_after_first_sample(*args, **kwargs):
                    nonlocal observations
                    result = original_observe(*args, **kwargs)
                    observations += 1
                    if observations == 1:
                        content = victim.read_text(encoding="utf-8")
                        victim.write_text(
                            content.replace("generation=A", "generation=B"),
                            encoding="utf-8",
                        )
                    return result

                with patch.object(
                    installer,
                    "_status_observe_evidence_once",
                    side_effect=mutate_after_first_sample,
                ):
                    report = _status(target)

                self.assertEqual(observations, 2)
                self.assertEqual(report["status"], "recovery_required")
                self.assertEqual(report["reason_code"], "observation_changed")

    def test_mount_boundary_fallback_is_live_only_when_linux_requires_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            child = target / "child"
            child.mkdir(parents=True)
            target_descriptor = os.open(target, installer._status_directory_flags())
            child_descriptor = os.open(child, installer._status_directory_flags())
            try:
                with (
                    patch.object(
                        installer,
                        "_status_linux_mountinfo_available",
                        return_value=True,
                    ),
                    patch.object(
                        installer,
                        "_status_linux_fd_mount_id",
                        return_value=None,
                    ),
                ):
                    boundary = installer._status_capture_mount_boundary(
                        target_descriptor
                    )
                self.assertEqual(boundary, ("live_mountinfo_fallback", None))
                token = installer._STATUS_MOUNT_BOUNDARY.set(boundary)
                try:
                    with (
                        patch.object(installer.os.path, "ismount", return_value=False),
                        patch.object(
                            installer,
                            "_linux_mount_points",
                            return_value={str(child.resolve(strict=True))},
                        ) as mount_points,
                    ):
                        self.assertTrue(installer._status_fd_is_mount(child_descriptor))
                    mount_points.assert_called_once_with()
                finally:
                    installer._STATUS_MOUNT_BOUNDARY.reset(token)

                token = installer._STATUS_MOUNT_BOUNDARY.set(("linux_mnt_id", 73))
                try:
                    with (
                        patch.object(
                            installer,
                            "_status_linux_fd_mount_id",
                            return_value=None,
                        ),
                        patch.object(
                            installer,
                            "_linux_mount_points",
                            side_effect=AssertionError(
                                "child fdinfo failure must fail closed"
                            ),
                        ),
                    ):
                        self.assertTrue(
                            installer._status_fd_is_mount(child_descriptor)
                        )
                finally:
                    installer._STATUS_MOUNT_BOUNDARY.reset(token)

                with patch.object(
                    installer,
                    "_status_linux_mountinfo_available",
                    return_value=False,
                ):
                    boundary = installer._status_capture_mount_boundary(
                        target_descriptor
                    )
                self.assertEqual(boundary, ("path_ismount_only", None))
                token = installer._STATUS_MOUNT_BOUNDARY.set(boundary)
                try:
                    with (
                        patch.object(installer.os.path, "ismount", return_value=False),
                        patch.object(
                            installer,
                            "_linux_mount_points",
                            side_effect=AssertionError(
                                "non-Linux mount checks must not load Linux mountinfo"
                            ),
                        ),
                    ):
                        self.assertFalse(installer._status_fd_is_mount(child_descriptor))
                finally:
                    installer._STATUS_MOUNT_BOUNDARY.reset(token)
            finally:
                os.close(child_descriptor)
                os.close(target_descriptor)

    def test_linux_fd_mount_id_parser_is_bounded_and_strict(self) -> None:
        cases = (
            (b"pos:\t0\nmnt_id:\t73\n", 73),
            (b"mnt_id:\t73\nmnt_id:\t74\n", None),
            (b"mnt_id:\tnot-a-number\n", None),
            (b"mnt_id:\t" + b"9" * 5000 + b"\n", None),
            (b"x" * (installer._STATUS_FDINFO_MAX_BYTES + 1), None),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                read_results = [payload]
                if len(payload) <= installer._STATUS_FDINFO_MAX_BYTES:
                    read_results.append(b"")
                with (
                    patch.object(installer.os, "open", return_value=91),
                    patch.object(installer.os, "read", side_effect=read_results) as read,
                    patch.object(installer.os, "close") as close,
                ):
                    actual = installer._status_linux_fd_mount_id(7)

                self.assertEqual(actual, expected)
                self.assertEqual(
                    read.call_args_list[0].args,
                    (
                        91,
                        installer._STATUS_FDINFO_MAX_BYTES + 1,
                    ),
                )
                self.assertLessEqual(read.call_count, 2)
                self.assertGreaterEqual(read.call_count, 1)
                close.assert_called_once_with(91)
                self.assertLessEqual(
                    sum(len(result) for result in read_results),
                    installer._STATUS_FDINFO_MAX_BYTES + 1,
                )

    def test_status_semantic_identity_uses_global_relative_path_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skill = Path(raw) / "skill"
            (skill / "a").mkdir(parents=True)
            (skill / "!before-root").write_bytes(b"punctuation\n")
            (skill / "a" / "inside").write_bytes(b"inside\n")
            (skill / "a.txt").write_bytes(b"sibling\n")
            expected = installer._directory_identity(skill)
            descriptor = os.open(skill, installer._status_directory_flags())
            try:
                actual, _ = installer._status_scan_open_directory(
                    descriptor,
                    expected_device=os.fstat(descriptor).st_dev,
                )
            finally:
                os.close(descriptor)

            self.assertEqual(actual, expected)

    def test_prejournal_building_and_committed_gc_are_read_only_recovery_states(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            transaction = target / f"{installer.INSTALL_TRANSACTION_PREFIX}{'a' * 32}"
            transaction.mkdir(mode=0o700)
            (transaction / installer._JOURNAL_TEMP_NAME).write_bytes(b"partial journal")
            before = _snapshot(target)

            prejournal = _status(target)

            self.assertEqual(prejournal["status"], "recovery_required")
            self.assertEqual(prejournal["transaction"]["phase"], "pre_journal")
            human = installer.render_installation_status(prejournal)
            self.assertNotIn("pre_journal", human)
            self.assertIn("до записи основного журнала", human)
            self.assertEqual(_snapshot(target), before)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            installer.copy_skillset(source_a, target)
            original_write = installer._write_journal
            stopped = False

            def stop_after_building_journal(
                transaction_root: Path,
                journal: dict[str, object],
            ) -> None:
                nonlocal stopped
                original_write(transaction_root, journal)
                if journal["phase"] == "building" and not stopped:
                    stopped = True
                    raise SystemExit(92)

            with patch.object(
                installer,
                "_write_journal",
                side_effect=stop_after_building_journal,
            ):
                with self.assertRaisesRegex(SystemExit, "92"):
                    installer.copy_skillset(source_b, target)
            before = _snapshot(target)

            building = _status(target)

            self.assertEqual(building["status"], "recovery_required")
            self.assertEqual(building["transaction"]["phase"], "building")
            self.assertEqual(_snapshot(target), before)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            installer.copy_skillset(source_a, target)

            with patch.object(
                installer,
                "_cleanup_stale_garbage_root",
                side_effect=SystemExit(93),
            ):
                with self.assertRaisesRegex(SystemExit, "93"):
                    installer.copy_skillset(source_b, target)
            garbage = sorted(target.glob(f"{installer.INSTALL_GC_PREFIX}*"))
            self.assertEqual(len(garbage), 1)
            before = _snapshot(target)

            committed_gc = _status(target)

            self.assertEqual(committed_gc["status"], "recovery_required")
            self.assertEqual(committed_gc["transaction"]["kind"], "gc")
            self.assertEqual(committed_gc["transaction"]["phase"], "committed")
            self.assertEqual(_snapshot(target), before)

    def test_unsafe_output_is_bounded_and_never_echoes_unknown_entry_names(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            transaction = target / f"{installer.INSTALL_TRANSACTION_PREFIX}{'f' * 32}"
            transaction.mkdir()
            private_names = [f"private-local-name-{index:03d}" for index in range(80)]
            for name in private_names:
                (transaction / name).write_bytes(b"local\n")
            before = _snapshot(target)

            report = _status(target)
            serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(report["reason_code"], "unsafe_evidence")
            self.assertLess(len(serialized), 5000)
            for name in private_names:
                self.assertNotIn(name, serialized)
            self.assertNotRegex(report["message"], r"[A-Za-z]{8,}")
            self.assertEqual(_snapshot(target), before)

    @unittest.skipUnless(os.name == "posix", "raw byte filenames require POSIX")
    def test_non_utf8_evidence_name_is_bounded_unsafe(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            target.mkdir()
            transaction = target / (
                installer.INSTALL_TRANSACTION_PREFIX + "f" * 32
            )
            transaction.mkdir(mode=0o700)
            descriptor = os.open(transaction, installer._status_directory_flags())
            try:
                try:
                    bad_descriptor = os.open(
                        b"\xff-private",
                        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                        0o600,
                        dir_fd=descriptor,
                    )
                except OSError as exc:
                    if exc.errno == errno.EILSEQ:
                        self.skipTest("filesystem rejects non-UTF-8 names")
                    raise
                os.close(bad_descriptor)
            finally:
                os.close(descriptor)

            report = _status(target)

            self.assertEqual(report["status"], "unsafe")
            self.assertEqual(report["exit_code"], 30)
            self.assertEqual(report["reason_code"], "unsafe_evidence")

    def test_direct_cli_json_has_exit_parity_and_bounded_schema(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "missing"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = installer.main(
                    ["--status", "--target", str(target), "--json"]
                )

            self.assertEqual(exit_code, 10)
            self.assertEqual(stderr.getvalue(), "")
            report = json.loads(stdout.getvalue())
            self.assertEqual(report["exit_code"], exit_code)
            self.assertEqual(
                set(report),
                {
                    "schema_version",
                    "status",
                    "severity",
                    "exit_code",
                    "reason_code",
                    "target",
                    "target_exists",
                    "managed_skills",
                    "transaction",
                    "message",
                    "recommended_action",
                    "observation",
                },
            )
            self.assertEqual(report["observation"]["consistency"], "unlocked_read_only")
            self.assertFalse(report["observation"]["explicit_mutations_performed"])
            self.assertTrue(
                report["observation"]["filesystem_access_time_updates_possible"]
            )
            self.assertFalse(report["observation"]["atomic_snapshot"])

    def test_status_discloses_filesystem_access_time_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _make_source(root, "A")
            target = root / "target"
            installer.copy_skillset(source, target)
            target_metadata = target.stat()
            os.utime(
                target,
                ns=(1_000_000_000, target_metadata.st_mtime_ns),
            )

            report = _status(target)
            human = installer.render_installation_status(report)

            self.assertFalse(report["observation"]["explicit_mutations_performed"])
            self.assertTrue(
                report["observation"]["filesystem_access_time_updates_possible"]
            )
            self.assertIn("время последнего доступа", human.lower())

    @unittest.skipUnless(os.name == "posix", "bytes argv requires POSIX")
    def test_surrogateescaped_target_has_valid_utf8_json_and_human_output(self) -> None:
        base_arguments = [
            os.fsencode(sys.executable),
            os.fsencode(TOOLS / "install_skillset.py"),
            b"--status",
            b"--target",
            b"/tmp/ksrf-status-\xff-missing",
        ]
        for label, suffix in (("json", [b"--json"]), ("human", [])):
            with self.subTest(label=label):
                completed = subprocess.run(
                    [*base_arguments, *suffix],
                    cwd=REPO,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )

                self.assertEqual(completed.returncode, 10)
                self.assertEqual(completed.stderr, b"")
                decoded = completed.stdout.decode("utf-8", errors="strict")
                self.assertIn(r"\xff", decoded)
                if label == "json":
                    report = json.loads(decoded)
                    self.assertEqual(report["status"], "not_installed")
                    self.assertNotIn("\udcff", report["target"])

    def test_human_shell_status_is_russian_and_never_installs_or_exports(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "missing path's"
            before = _snapshot(Path(raw))

            completed = subprocess.run(
                [str(REPO / "install.sh"), "--status", "--target", str(target)],
                cwd=REPO,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 10)
            self.assertRegex(completed.stdout, r"[А-Яа-яЁё]")
            self.assertIn("не выполняла операций записи", completed.stdout.lower())
            self.assertIn("время последнего доступа", completed.stdout.lower())
            self.assertNotIn("Installed exact manifest-covered", completed.stdout)
            self.assertNotIn("export KSRF_SKILLS_ROOT=", completed.stdout)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(_snapshot(Path(raw)), before)

    def test_shell_verify_current_delegates_target_and_exit_codes_without_install(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            checkout = root / "release checkout"
            checkout.mkdir()
            shutil.copy2(REPO / "install.sh", checkout / "install.sh")
            tools = checkout / "tools"
            tools.mkdir()
            (tools / "install_skillset.py").write_text(
                "import json, os, sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
                "raise SystemExit(int(os.environ['KSRF_FAKE_EXIT']))\n",
                encoding="utf-8",
            )
            _write_fake_repo_verification_policy(checkout)
            target = root / "target skills"
            before = _snapshot(root)

            for expected_exit in (0, 10, 20, 1, 2):
                with self.subTest(expected_exit=expected_exit):
                    completed = subprocess.run(
                        [
                            str(checkout / "install.sh"),
                            "--verify-current",
                            "--target",
                            str(target),
                        ],
                        cwd=checkout,
                        env={
                            **os.environ,
                            "HOME": str(root / "home"),
                            "KSRF_FAKE_EXIT": str(expected_exit),
                            "PYTHONDONTWRITEBYTECODE": "1",
                        },
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(
                        completed.returncode,
                        expected_exit,
                        completed.stderr,
                    )
                    self.assertEqual(completed.stderr, "")
                    self.assertEqual(
                        json.loads(completed.stdout),
                        [
                            "--verify-runtime",
                            "--repo",
                            str(checkout),
                            "--target",
                            str(target),
                            "--require-current",
                        ],
                    )
            self.assertEqual(_snapshot(root), before)

    def test_shell_verify_delegates_exact_target_offline_and_propagates_exit_codes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            checkout = root / "release checkout"
            checkout.mkdir()
            shutil.copy2(REPO / "install.sh", checkout / "install.sh")
            tools = checkout / "tools"
            tools.mkdir()
            (tools / "install_skillset.py").write_text(
                "import json, os, sys\n"
                "for forbidden in ('--require-current',):\n"
                "    assert forbidden not in sys.argv[1:]\n"
                "print(json.dumps(sys.argv[1:]))\n"
                "raise SystemExit(int(os.environ['KSRF_FAKE_EXIT']))\n",
                encoding="utf-8",
            )
            _write_fake_repo_verification_policy(checkout)
            target = root / "target skills"
            before = _snapshot(root)

            for expected_exit in (0, 1, 2):
                with self.subTest(expected_exit=expected_exit):
                    completed = subprocess.run(
                        [
                            str(checkout / "install.sh"),
                            "--verify",
                            "--target",
                            str(target),
                        ],
                        cwd=checkout,
                        env={
                            **os.environ,
                            "HOME": str(root / "home"),
                            "KSRF_FAKE_EXIT": str(expected_exit),
                            "PYTHONDONTWRITEBYTECODE": "1",
                        },
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(
                        completed.returncode,
                        expected_exit,
                        completed.stderr,
                    )
                    self.assertEqual(completed.stderr, "")
                    self.assertEqual(
                        json.loads(completed.stdout),
                        [
                            "--verify-runtime",
                            "--repo",
                            str(checkout),
                            "--target",
                            str(target),
                        ],
                    )
            self.assertEqual(_snapshot(root), before)

    def test_shell_verify_stops_after_nonclean_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            checkout = root / "checkout"
            checkout.mkdir()
            shutil.copy2(REPO / "install.sh", checkout / "install.sh")
            tools = checkout / "tools"
            tools.mkdir()
            (tools / "install_skillset.py").write_text(
                "import sys\n"
                "print('структурная проверка: неполная установка', file=sys.stderr)\n"
                "print('безопасная полная установка', file=sys.stderr)\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            _write_fake_repo_verification_policy(checkout)
            target = root / "target"
            before = _snapshot(root)

            completed = subprocess.run(
                [str(checkout / "install.sh"), "--verify", "--target", str(target)],
                cwd=checkout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(completed.stdout, "")
            self.assertIn("неполная установка", completed.stderr)
            self.assertIn("безопасная полная установка", completed.stderr)
            self.assertEqual(_snapshot(root), before)

    def test_repo_side_verify_coordinator_is_offline_and_never_executes_target_policy(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            installer.copy_skillset(REPO / "skills", target)
            sentinel = root / "target-policy-executed"
            target_validator = (
                target
                / "ksrf-complaint-cycle"
                / "scripts"
                / "validate_ksrf_skillset.py"
            )
            target_validator.write_text(
                "from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('executed', encoding='utf-8')\n",
                encoding="utf-8",
            )
            before = _snapshot(target)
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch.object(
                socket,
                "socket",
                side_effect=AssertionError("offline coordinator attempted network"),
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertIn(exit_code, {0, 1})
            self.assertFalse(sentinel.exists())
            self.assertIn("ПРОВЕРКА БЕЗ СЕТИ", stdout.getvalue())
            self.assertIn("не провер", stdout.getvalue().lower())
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(_snapshot(target), before)

    def test_verify_coordinator_renders_public_offline_success_in_plain_russian(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = installer.verify_installed_skillset(
                REPO,
                target,
                require_current=False,
                stdout=stdout,
                stderr=stderr,
            )

            rendered = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА", rendered)
            self.assertIn("Проверено навыков: 15 из 15", rendered)
            self.assertIn("Интернет не использовался", rendered)
            self.assertIn("./install.sh --verify-current", rendered)
            self.assertNotIn("--check-updates", rendered)
            self.assertNotIn("evals:", rendered)
            self.assertNotIn("runtime self-containment", rendered)
            self.assertNotIn("source/release QA", rendered)

    def test_current_renderer_explains_every_outcome_without_maintainer_labels(
        self,
    ) -> None:
        base_report = {
            "status": "pass",
            "summary": {"errors": 0, "warnings": 0},
            "validated_package_count": 15,
            "expected_package_count": 15,
            "runtime_content": {
                "tree_sha256": "a" * 64,
                "total_files": 238,
                "total_bytes": 8_165_136,
            },
            "freshness": {
                "status": "current",
                "reason_code": "content_matches",
                "remote_main_sha": "b" * 40,
            },
            "findings": [],
        }
        cases = (
            (
                "current",
                False,
                "СОДЕРЖИМОЕ СОВПАДАЕТ С ОПУБЛИКОВАННОЙ ВЕРСИЕЙ",
                "Установленное содержимое совпадает с ней",
            ),
            (
                "different",
                False,
                "СОДЕРЖИМОЕ ОТЛИЧАЕТСЯ ОТ ОПУБЛИКОВАННОЙ ВЕРСИИ",
                "может быть более старой, более новой, настроенной",
            ),
            (
                "unknown",
                False,
                "СРАВНЕНИЕ НЕ ЗАВЕРШЕНО",
                "сеть или удалённый сервис недоступны",
            ),
            (
                "current",
                True,
                "СОДЕРЖИМОЕ НЕ ПРОШЛО ПРОВЕРКУ",
                "Сравнение с опубликованной версией не подтверждено",
            ),
        )
        forbidden = (
            "Профиль: runtime",
            "evals:",
            "not_checked",
            "validated",
            "runtime self-containment",
            "public-source",
            "public-repository",
            "source/release QA",
        )

        for freshness_status, validation_failed, heading, explanation in cases:
            with self.subTest(
                freshness_status=freshness_status,
                validation_failed=validation_failed,
            ):
                report = json.loads(json.dumps(base_report))
                report["freshness"]["status"] = freshness_status
                if freshness_status == "unknown":
                    report["freshness"]["reason_code"] = "network_error"
                    report["freshness"]["remote_main_sha"] = None
                if validation_failed:
                    report["status"] = "fail"
                    report["summary"] = {"errors": 1, "warnings": 0}
                rendered = installer._render_current_verification_report(
                    report,
                    validation_failed=validation_failed,
                )

                self.assertIn(heading, rendered.splitlines()[0])
                self.assertIn(explanation, rendered)
                self.assertIn("Проверено навыков: 15 из 15", rendered)
                self.assertIn("a" * 64, rendered)
                self.assertIn("прав", rendered.lower())
                self.assertIn("жалоб", rendered.lower())
                self.assertIn("не входят в пользовательскую установку", rendered)
                if freshness_status in {"current", "different"} and not validation_failed:
                    self.assertIn("b" * 40, rendered)
                for marker in forbidden:
                    self.assertNotIn(marker, rendered)
                self.assertNotIn("main", rendered.lower())

    def test_current_renderer_keeps_bounded_findings_and_remote_version(self) -> None:
        report = {
            "status": "fail",
            "summary": {"errors": 1, "warnings": 0},
            "validated_package_count": 14,
            "expected_package_count": 15,
            "runtime_content": {
                "tree_sha256": None,
                "total_files": 237,
                "total_bytes": 8_000_000,
            },
            "freshness": {
                "status": "unknown",
                "reason_code": "local_identity_unavailable",
                "remote_main_sha": "b" * 40,
            },
            "findings": [
                {
                    "severity": "error",
                    "code": "MISSING_FILE",
                    "package": "ksrf-test",
                    "path": "references/missing.md\nЛОЖНЫЙ УСПЕХ",
                    "line": 7,
                    "message": "Не найден обязательный файл.\x1b[31m",
                }
            ],
        }

        rendered = installer._render_current_verification_report(
            report,
            validation_failed=True,
        )

        self.assertIn("Контрольный отпечаток не сформирован", rendered)
        self.assertIn("ОШИБКА [references/missing.md\\x0aЛОЖНЫЙ УСПЕХ:7]", rendered)
        self.assertIn("Не найден обязательный файл.\\x1b[31m", rendered)
        self.assertNotIn("MISSING_FILE", rendered)
        self.assertNotIn("\nЛОЖНЫЙ УСПЕХ", rendered)
        self.assertNotIn("\x1b[31m", rendered)
        self.assertNotIn("СОВПАДАЕТ С ОПУБЛИКОВАННОЙ", rendered)

    def test_public_verification_findings_are_count_bounded(self) -> None:
        findings = [
            {
                "severity": "error",
                "code": f"INTERNAL_{index}",
                "path": f"references/finding-{index:02d}.md",
                "message": f"Проблема {index}.",
            }
            for index in range(55)
        ]
        report = {
            "status": "fail",
            "summary": {"errors": 55, "warnings": 0},
            "validated_package_count": 15,
            "expected_package_count": 15,
            "runtime_content": {
                "tree_sha256": None,
                "total_files": 238,
                "total_bytes": 8_165_136,
            },
            "freshness": {
                "status": "unknown",
                "reason_code": "local_identity_unavailable",
                "remote_main_sha": None,
            },
            "findings": findings,
        }

        rendered = installer._render_current_verification_report(
            report,
            validation_failed=True,
        )

        self.assertIn("references/finding-00.md", rendered)
        self.assertIn("references/finding-49.md", rendered)
        self.assertNotIn("references/finding-50.md", rendered)
        self.assertIn("Показаны первые 50 проблем. Не показано: 5", rendered)
        self.assertNotIn("INTERNAL_", rendered)
        offline_rendered = installer._render_offline_verification_report(
            report,
            target=Path("/tmp/ksrf-runtime-target"),
            validation_failed=True,
        )
        self.assertIn("Показаны первые 50 проблем. Не показано: 5", offline_rendered)
        self.assertNotIn("INTERNAL_", offline_rendered)

    def test_public_verification_findings_hide_internal_exception_details(self) -> None:
        sensitive_codes = (
            "SKILL_FILE_UNREADABLE",
            "FRONTMATTER_INVALID",
            "AGENT_METADATA_INVALID",
            "BEHAVIORAL_EVALS_INVALID",
            "TRIGGER_EVALS_INVALID",
            "MARKDOWN_UNREADABLE",
            "MARKDOWN_LINK_ESCAPES_SKILLSET",
            "BROKEN_MARKDOWN_LINK",
            "MCP_TOOL_NOT_FULLY_QUALIFIED",
            "APPLICATION_EVIDENCE_CONTRACT_INVALID",
            "ARGUMENT_GRAPH_CONTRACT_INVALID",
            "AUTHORITY_CORPUS_CONTRACT_INVALID",
            "RUNTIME_TEXT_UNREADABLE",
            "RUNTIME_FORMAT_UNCHECKED",
            "RUNTIME_REFERENCE_JSON_INVALID",
            "PUBLISH_FILE_UNREADABLE",
            "RUNTIME_LOCAL_COORDINATE",
            "RUNTIME_IDENTITY_CHANGED",
            "RUNTIME_ROOT_CHANGED",
            "OFFLINE_SELF_CONTAINMENT_FAILED",
        )
        findings = []
        for index, code in enumerate(sensitive_codes):
            path = (
                "/private/validator-secret"
                if code == "PUBLISH_FILE_UNREADABLE"
                else "runtime"
                if code.startswith("RUNTIME_")
                or code == "OFFLINE_SELF_CONTAINMENT_FAILED"
                else f"ksrf-case-triage/references/problem-{index}.md"
            )
            findings.append(
                {
                    "severity": "error",
                    "code": code,
                    "path": path,
                    "message": (
                        "Raw policy detail: UnicodeDecodeError: invalid start byte; "
                        "OSError: permission denied at /private/validator-secret; "
                        "marker_classes=repository-source-tree; field_name=secret"
                    ),
                }
            )
        report = {
            "status": "fail",
            "summary": {"errors": len(findings), "warnings": 0},
            "validated_package_count": 15,
            "expected_package_count": 15,
            "runtime_content": {
                "tree_sha256": None,
                "total_files": 238,
                "total_bytes": 8_165_136,
            },
            "freshness": {
                "status": "unknown",
                "reason_code": "local_identity_unavailable",
                "remote_main_sha": None,
            },
            "findings": findings,
        }
        original_report = json.loads(json.dumps(report))

        rendered_outputs = (
            installer._render_current_verification_report(
                report,
                validation_failed=True,
            ),
            installer._render_offline_verification_report(
                report,
                target=Path("/tmp/ksrf-runtime-target"),
                validation_failed=True,
            ),
        )

        self.assertEqual(report, original_report)
        for rendered in rendered_outputs:
            self.assertIn("Файл SKILL.md не удалось безопасно прочитать", rendered)
            self.assertIn("ОШИБКА [установка]", rendered)
            self.assertIn("Содержимое установки изменилось во время проверки", rendered)
            self.assertIn("Автономность установки не подтверждена", rendered)
            self.assertIn("локальную ссылку, недоступную после установки", rendered)
            self.assertIn("ведёт за пределы установленного набора", rendered)
            self.assertIn("ведёт к отсутствующему файлу", rendered)
            self.assertIn("некорректная ссылка на служебный инструмент", rendered)
            for forbidden in (
                "UnicodeDecodeError",
                "invalid start byte",
                "OSError",
                "permission denied",
                "/private/validator-secret",
                "[runtime]",
                "marker_classes",
                "repository-source-tree",
                "field_name",
                "Raw policy detail",
            ):
                self.assertNotIn(forbidden, rendered)

    def test_current_coordinator_uses_public_renderer_and_preserves_exit_codes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            target.mkdir()
            runtime_content = {
                "algorithm": "sha256-path-length-content-v1",
                "tree_sha256": "a" * 64,
                "total_files": 238,
                "total_bytes": 8_165_136,
            }
            base_report = {
                "schema_version": "1.1.0",
                "validation_profile": "runtime",
                "validation_coverage": {
                    "evals": "not_checked",
                    "runtime_self_containment": "validated",
                    "public_source_safety": "not_checked",
                    "public_repository_safety": "not_checked",
                },
                "source_release_eligible": False,
                "status": "pass",
                "summary": {"errors": 0, "warnings": 0},
                "validated_package_count": 15,
                "expected_package_count": 15,
                "validated_packages": list(installer.SKILL_NAMES),
                "runtime_content": runtime_content,
                "freshness": {
                    "status": "not_checked",
                    "reason_code": "not_requested",
                    "remote_main_sha": None,
                    "local_tree_sha256": "a" * 64,
                    "remote_tree_sha256": None,
                },
                "findings": [],
                "publish_manifest": None,
            }
            cases = (
                ("current", "current", False, None, 0),
                ("different", "different", False, None, 10),
                ("different-count-only", "different", False, "same-tree", 10),
                ("unknown", "unknown", False, None, 20),
                (
                    "contradictory-local-unavailable",
                    "unknown",
                    False,
                    "local-unavailable",
                    2,
                ),
                ("validation-failed", "current", True, None, 1),
                ("missing-outcome", "not_checked", False, None, 2),
                ("invalid-remote-sha", "current", False, "remote-sha", 2),
                ("missing-local-digest", "current", False, "local-digest", 2),
                ("boolean-summary", "current", False, "boolean-summary", 2),
                ("float-package-count", "current", False, "float-package-count", 2),
                ("wrong-profile", "current", False, "wrong-profile", 2),
                ("mismatched-packages", "current", False, "mismatched-packages", 2),
                ("inconsistent-findings", "current", False, "inconsistent-findings", 2),
                ("current-files-over-cap", "current", False, "files-over-cap", 2),
                ("current-bytes-over-cap", "current", False, "bytes-over-cap", 2),
            )

            with installer._held_verification_root(target) as (
                target_descriptor,
                expected_anchor,
            ):
                for (
                    label,
                    freshness_status,
                    validation_failed,
                    malformed,
                    expected_exit,
                ) in cases:
                    with self.subTest(
                        label=label,
                        freshness_status=freshness_status,
                        validation_failed=validation_failed,
                    ):
                        case_base_report = json.loads(json.dumps(base_report))
                        if malformed == "local-digest":
                            case_base_report["runtime_content"]["tree_sha256"] = None
                            case_base_report["freshness"]["local_tree_sha256"] = None
                        if malformed == "files-over-cap":
                            case_base_report["runtime_content"]["total_files"] = 1_000_001
                        if malformed == "bytes-over-cap":
                            case_base_report["runtime_content"]["total_bytes"] = 2**63
                        final_report = json.loads(json.dumps(case_base_report))
                        remote_tree_sha256 = (
                            "a" * 64
                            if freshness_status == "current" or malformed == "same-tree"
                            else "c" * 64
                            if freshness_status == "different"
                            else None
                        )
                        final_report["freshness"].update(
                            status=freshness_status,
                            reason_code=(
                                "network_error"
                                if freshness_status == "unknown"
                                else "content_differs"
                                if freshness_status == "different"
                                else "content_matches"
                            ),
                            remote_main_sha=(
                                None if freshness_status == "unknown" else "b" * 40
                            ),
                            remote_tree_sha256=remote_tree_sha256,
                        )
                        if malformed == "remote-sha":
                            final_report["freshness"]["remote_main_sha"] = None
                        if malformed == "boolean-summary":
                            final_report["summary"] = {
                                "errors": False,
                                "warnings": False,
                            }
                        if malformed == "float-package-count":
                            final_report["validated_package_count"] = 15.0
                            final_report["expected_package_count"] = 15.0
                        if malformed == "wrong-profile":
                            final_report["validation_profile"] = "source"
                        if malformed == "mismatched-packages":
                            final_report["validated_packages"] = list(
                                reversed(installer.SKILL_NAMES)
                            )
                        if malformed == "inconsistent-findings":
                            final_report["findings"] = [
                                {
                                    "severity": "warning",
                                    "code": "IMPOSSIBLE_PASS_FINDING",
                                    "message": "Неучтённое предупреждение.",
                                    "path": "runtime",
                                }
                            ]
                        if malformed == "local-unavailable":
                            final_report["freshness"]["reason_code"] = (
                                "local_identity_unavailable"
                            )
                        if validation_failed:
                            final_report["status"] = "fail"
                            final_report["summary"] = {"errors": 1, "warnings": 0}
                        validator = Mock()
                        validator.CANONICAL_KSRF_PACKAGES = ("ksrf-test",)
                        validator._required_runtime_root_matches.return_value = True
                        validator._render_text.side_effect = AssertionError(
                            "public coordinator must not forward maintainer prose"
                        )
                        validator.validate_skillset.side_effect = (
                            [final_report]
                            if validation_failed
                            else [final_report, case_base_report]
                        )
                        offline_policy = Mock()
                        offline_policy.validate_offline_self_containment.return_value = []
                        stdout = io.StringIO()
                        stderr = io.StringIO()

                        with patch.object(
                            installer,
                            "_inspect_installation_status_anchored",
                            return_value={"exit_code": 0},
                        ):
                            exit_code = installer._verify_installed_skillset_anchored(
                                target,
                                validator=validator,
                                offline_policy=offline_policy,
                                expected_anchor=expected_anchor,
                                target_descriptor=target_descriptor,
                                require_current=True,
                                stdout=stdout,
                                stderr=stderr,
                            )

                        self.assertEqual(exit_code, expected_exit)
                        if expected_exit == 2:
                            self.assertIn("внутренней ошибки", stderr.getvalue())
                            self.assertIn("Обновите репозиторий", stderr.getvalue())
                            self.assertNotIn("валидатор", stderr.getvalue().lower())
                            self.assertEqual(stdout.getvalue(), "")
                        else:
                            self.assertEqual(stderr.getvalue(), "")
                        self.assertNotIn("evals:", stdout.getvalue())

    @unittest.skipUnless(os.name == "posix", "symlink evidence requires POSIX")
    def test_verify_coordinator_cannot_hide_unsafe_state_during_both_status_calls(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            installer.copy_skillset(REPO / "skills", target)
            clean_decoy = root / "clean-decoy"
            shutil.copytree(target, clean_decoy)
            unsafe_held = root / "unsafe-held"
            unsafe_lock = target / installer.INSTALL_LOCK_FILE_NAME
            unsafe_lock.unlink()
            unsafe_lock.symlink_to(root / "outside")
            original_status = installer._inspect_installation_status_anchored
            status_calls = 0

            def hide_unsafe_state(path: Path, descriptor: int):
                nonlocal status_calls
                status_calls += 1
                target.rename(unsafe_held)
                clean_decoy.rename(target)
                try:
                    return original_status(path, descriptor)
                finally:
                    target.rename(clean_decoy)
                    unsafe_held.rename(target)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_inspect_installation_status_anchored",
                side_effect=hide_unsafe_state,
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 1)
            self.assertGreaterEqual(status_calls, 1)
            self.assertNotIn("ПРОЙДЕНА", stdout.getvalue())
            self.assertEqual(
                installer.inspect_installation_status(target)["status"],
                "unsafe",
            )

    def test_verify_coordinator_binds_offline_policy_to_content_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            validator, offline_policy = installer._load_repo_verification_policy(REPO)
            original_policy = offline_policy.validate_offline_self_containment
            core = (
                target
                / "ksrf-complaint-cycle"
                / "references"
                / "offline-practice-core.md"
            )

            def mutate_after_policy(*args: object, **kwargs: object):
                errors = original_policy(*args, **kwargs)
                text = core.read_text(encoding="utf-8")
                core.write_text(
                    text.replace("## 0. Контракт автономности", "## 0. Удалено", 1),
                    encoding="utf-8",
                )
                return errors

            offline_policy.validate_offline_self_containment = mutate_after_policy
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_load_repo_verification_policy",
                return_value=(validator, offline_policy),
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 1)
            self.assertNotIn("ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА", stdout.getvalue())

    def test_verify_coordinator_runs_offline_policy_on_one_immutable_snapshot(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            validator, offline_policy = installer._load_repo_verification_policy(REPO)
            original_policy = offline_policy.validate_offline_self_containment
            core = (
                target
                / "ksrf-complaint-cycle"
                / "references"
                / "offline-practice-core.md"
            )
            valid_text = core.read_text(encoding="utf-8")
            invalid_text = valid_text.replace(
                "## 0. Контракт автономности",
                "## 0. Удалено",
                1,
            )
            self.assertNotEqual(valid_text, invalid_text)
            core.write_text(invalid_text, encoding="utf-8")

            def expose_valid_live_tree_only_during_policy(
                *args: object,
                **kwargs: object,
            ) -> list[str]:
                core.write_text(valid_text, encoding="utf-8")
                try:
                    return original_policy(*args, **kwargs)
                finally:
                    core.write_text(invalid_text, encoding="utf-8")

            offline_policy.validate_offline_self_containment = (
                expose_valid_live_tree_only_during_policy
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_load_repo_verification_policy",
                return_value=(validator, offline_policy),
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("ПРОВЕРКА БЕЗ СЕТИ НЕ ПРОЙДЕНА", stdout.getvalue())
            self.assertNotIn("ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    @unittest.skipUnless(os.name == "posix", "descriptor no-follow requires POSIX")
    def test_verification_snapshot_refuses_nested_symlink_swap_before_read(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            installer.copy_skillset(REPO / "skills", target)
            core = (
                target
                / "ksrf-complaint-cycle"
                / "references"
                / "offline-practice-core.md"
            )
            held = root / "held-offline-practice-core.md"
            outside = root / "outside-private.md"
            outside.write_text("НЕ ДОЛЖНО БЫТЬ ПРОЧИТАНО", encoding="utf-8")
            original_core_text = core.read_text(encoding="utf-8")
            original_read = installer._status_read_regular_at
            swap_attempted = False
            nofollow_rejected = False

            def swap_regular_for_symlink_before_descriptor_read(
                parent_descriptor: int,
                name: str,
                **kwargs: object,
            ) -> tuple[bytes | None, str, tuple[int, ...]]:
                nonlocal swap_attempted, nofollow_rejected
                if name == core.name and not swap_attempted:
                    swap_attempted = True
                    core.rename(held)
                    core.symlink_to(outside)
                    try:
                        try:
                            return original_read(
                                parent_descriptor,
                                name,
                                **kwargs,
                            )
                        except installer.InstallationError:
                            nofollow_rejected = True
                            raise
                    finally:
                        core.unlink()
                        held.rename(core)
                return original_read(parent_descriptor, name, **kwargs)

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_status_read_regular_at",
                side_effect=swap_regular_for_symlink_before_descriptor_read,
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertTrue(swap_attempted)
            self.assertTrue(nofollow_rejected)
            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Проверка не выполнена", stderr.getvalue())
            self.assertEqual(core.read_text(encoding="utf-8"), original_core_text)

    def test_verification_snapshot_refuses_oversized_unmanaged_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            oversized = target / "ksrf-case-triage" / "unmanaged-large.bin"
            with oversized.open("wb") as handle:
                handle.truncate(installer._STATUS_SCAN_MAX_FILE_BYTES + 1)
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = installer.verify_installed_skillset(
                REPO,
                target,
                require_current=False,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Проверка не выполнена", stderr.getvalue())

    def test_verify_coordinator_traverses_held_root_not_lexical_decoy(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            installer.copy_skillset(REPO / "skills", target)
            clean_decoy = root / "clean-decoy"
            shutil.copytree(target, clean_decoy)
            held_original = root / "held-original"
            skill_file = target / "ksrf-case-triage" / "SKILL.md"
            skill_file.write_text(
                skill_file.read_text(encoding="utf-8").replace(
                    "name: ksrf-case-triage",
                    "name: wrong-package-name",
                    1,
                ),
                encoding="utf-8",
            )
            validator, offline_policy = installer._load_repo_verification_policy(REPO)
            original_validate = validator.validate_skillset
            validation_calls = 0

            def validate_while_lexical_target_is_decoy(*args: object, **kwargs: object):
                nonlocal validation_calls
                validation_calls += 1
                target.rename(held_original)
                clean_decoy.rename(target)
                try:
                    return original_validate(*args, **kwargs)
                finally:
                    target.rename(clean_decoy)
                    held_original.rename(target)

            validator.validate_skillset = validate_while_lexical_target_is_decoy
            stdout = io.StringIO()
            stderr = io.StringIO()
            cwd_before = Path.cwd()
            with patch.object(
                installer,
                "_load_repo_verification_policy",
                return_value=(validator, offline_policy),
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertGreaterEqual(validation_calls, 1)
            self.assertEqual(Path.cwd(), cwd_before)
            self.assertEqual(exit_code, 1)
            self.assertIn("НЕ ПРОЙДЕНА", stdout.getvalue())
            self.assertNotIn("ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА", stdout.getvalue())

    def test_verify_coordinator_maps_invalid_utf8_target_data_to_validation_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            core = (
                target
                / "ksrf-complaint-cycle"
                / "references"
                / "offline-practice-core.md"
            )
            core.write_bytes(b"\xff\xfeinvalid runtime text")
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = installer.verify_installed_skillset(
                REPO,
                target,
                require_current=False,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("НЕ ПРОЙДЕНА", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    @unittest.skipUnless(os.name == "posix", "raw byte filenames require POSIX")
    def test_verify_coordinator_maps_non_utf8_runtime_path_to_validation_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            package_bytes = os.fsencode(target / "ksrf-case-triage")
            raw_path = package_bytes + b"/invalid-\xff.md"
            try:
                descriptor = os.open(raw_path, os.O_WRONLY | os.O_CREAT, 0o600)
            except OSError as exc:
                self.skipTest(f"filesystem rejects non-UTF-8 names: {exc}")
            try:
                os.write(descriptor, b"runtime text\n")
            finally:
                os.close(descriptor)
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = installer.verify_installed_skillset(
                REPO,
                target,
                require_current=False,
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("НЕ ПРОЙДЕНА", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_verify_coordinator_restores_working_directory_after_policy_fault(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            validator, offline_policy = installer._load_repo_verification_policy(REPO)
            original_validate = validator.validate_skillset
            calls = 0

            def fail_second_validation(*args: object, **kwargs: object):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("trusted policy fault")
                return original_validate(*args, **kwargs)

            validator.validate_skillset = fail_second_validation
            cwd_before = Path.cwd()
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_load_repo_verification_policy",
                return_value=(validator, offline_policy),
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 2)
            self.assertEqual(Path.cwd(), cwd_before)
            self.assertTrue((Path("tools") / "install_skillset.py").is_file())
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("внутренней ошибки", stderr.getvalue())
            self.assertIn("Обновите репозиторий", stderr.getvalue())
            self.assertNotIn("RuntimeError", stderr.getvalue())
            self.assertNotIn("trusted policy fault", stderr.getvalue())

    def test_verify_coordinator_maps_initial_root_race_to_local_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)

            @contextmanager
            def changing_root(_target: Path):
                raise installer._ObservationChanged("root changed while opening")
                yield  # pragma: no cover

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_held_verification_root",
                side_effect=changing_root,
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Проверка не выполнена", stderr.getvalue())
            self.assertIn("повторите", stderr.getvalue().lower())
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertNotIn("_ObservationChanged", stderr.getvalue())

    def test_verify_coordinator_maps_trusted_policy_load_fault_to_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills"
            installer.copy_skillset(REPO / "skills", target)
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch.object(
                installer,
                "_load_repo_verification_policy",
                side_effect=SyntaxError("broken trusted policy"),
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            rendered_error = stderr.getvalue()
            self.assertIn("внутренней ошибки", rendered_error.lower())
            self.assertIn("Обновите репозиторий", rendered_error)
            for marker in (
                "SyntaxError",
                "broken trusted policy",
                "Traceback",
                "доверенной политики",
                "валидатор",
            ):
                self.assertNotIn(marker, rendered_error)

    def test_verify_success_omits_dead_current_command_for_control_character_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "skills\nподмена"
            installer.copy_skillset(REPO / "skills", target)
            stdout = io.StringIO()
            stderr = io.StringIO()

            exit_code = installer.verify_installed_skillset(
                REPO,
                target,
                require_current=False,
                stdout=stdout,
                stderr=stderr,
            )

            rendered = stdout.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("ПРОВЕРКА БЕЗ СЕТИ ПРОЙДЕНА", rendered)
            self.assertIn("сформировать нельзя", rendered)
            self.assertNotIn("--verify-current --target", rendered)
            self.assertNotIn("\nподмена", rendered)

    def test_verify_coordinator_rejects_byte_identical_root_replacement_after_preflight(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            installer.copy_skillset(REPO / "skills", target)
            original_status = installer._inspect_installation_status_anchored
            displaced = root / "displaced-skills"
            calls = 0

            def replace_after_clean_preflight(path: Path, descriptor: int):
                nonlocal calls
                report = original_status(path, descriptor)
                calls += 1
                if calls == 1 and report["status"] == "clean":
                    target.rename(displaced)
                    shutil.copytree(displaced, target)
                return report

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_inspect_installation_status_anchored",
                side_effect=replace_after_clean_preflight,
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 1)
            self.assertNotIn("ПРОЙДЕНО", stdout.getvalue())
            self.assertIn("измен", stderr.getvalue().lower())

    def test_verify_coordinator_withholds_success_when_postflight_is_nonclean(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            installer.copy_skillset(REPO / "skills", target)
            original_status = installer._inspect_installation_status_anchored
            calls = 0

            def fail_second_observation(path: Path, descriptor: int):
                nonlocal calls
                report = original_status(path, descriptor)
                calls += 1
                if calls == 2:
                    report = dict(report)
                    report["status"] = "recovery_required"
                    report["severity"] = "warning"
                    report["exit_code"] = 20
                    report["reason_code"] = "observation_changed"
                    report["message"] = "Состояние изменилось перед завершением проверки."
                return report

            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.object(
                installer,
                "_inspect_installation_status_anchored",
                side_effect=fail_second_observation,
            ):
                exit_code = installer.verify_installed_skillset(
                    REPO,
                    target,
                    require_current=False,
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("проверка не выполнена", stderr.getvalue().lower())
            self.assertNotIn("postflight", stderr.getvalue().lower())
            self.assertNotIn("preflight", stderr.getvalue().lower())
            self.assertNotIn("ПРОЙДЕНА", stderr.getvalue())

    def test_shell_verify_current_fails_honestly_without_python_or_validator(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            checkout = root / "checkout"
            checkout.mkdir()
            shutil.copy2(REPO / "install.sh", checkout / "install.sh")
            no_python = subprocess.run(
                ["/bin/bash", str(checkout / "install.sh"), "--verify-current"],
                cwd=checkout,
                env={**os.environ, "PATH": str(root / "empty-bin")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(no_python.returncode, 1)
            self.assertEqual(no_python.stdout, "")
            self.assertIn("python3", no_python.stderr)

            tools = checkout / "tools"
            tools.mkdir()
            (tools / "install_skillset.py").write_text(
                "raise SystemExit(0)\n",
                encoding="utf-8",
            )
            no_validator = subprocess.run(
                [str(checkout / "install.sh"), "--verify-current"],
                cwd=checkout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(no_validator.returncode, 1)
            self.assertEqual(no_validator.stdout, "")
            self.assertIn("Файлы проверки недоступны", no_validator.stderr)
            self.assertIn("Обновите репозиторий", no_validator.stderr)
            self.assertNotIn("repo-side", no_validator.stderr.lower())
            self.assertNotIn("main", no_validator.stderr.lower())

    @unittest.skipUnless(os.name == "posix", "symlink preflight requires POSIX")
    def test_shell_verify_modes_preflight_blocks_unsafe_targets_before_policy(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            checkout = root / "checkout"
            checkout.mkdir()
            shutil.copy2(REPO / "install.sh", checkout / "install.sh")
            tools = checkout / "tools"
            tools.mkdir()
            for name in ("install_skillset.py", "skillset_file_contract.py"):
                shutil.copy2(TOOLS / name, tools / name)
            policy_dir = (
                checkout
                / "skills"
                / "ksrf-complaint-cycle"
                / "scripts"
            )
            policy_dir.mkdir(parents=True)
            source_policy_dir = (
                REPO
                / "skills"
                / "ksrf-complaint-cycle"
                / "scripts"
            )
            for name in (
                "validate_ksrf_skillset.py",
                "verify_offline_self_containment.py",
            ):
                shutil.copy2(source_policy_dir / name, policy_dir / name)
            actual = root / "actual"
            actual.mkdir()
            symlink = root / "linked-skills"
            symlink.symlink_to(actual, target_is_directory=True)
            fake_home = root / "home"
            fake_home.mkdir()

            for mode in ("--verify", "--verify-current"):
                for target in (symlink, Path("/"), fake_home):
                    with self.subTest(mode=mode, target=target):
                        completed = subprocess.run(
                            [
                                str(checkout / "install.sh"),
                                mode,
                                "--target",
                                str(target),
                            ],
                            cwd=checkout,
                            env={
                                **os.environ,
                                "HOME": str(fake_home),
                                "PYTHONDONTWRITEBYTECODE": "1",
                            },
                            text=True,
                            capture_output=True,
                            check=False,
                        )

                        self.assertEqual(completed.returncode, 1)
                        self.assertEqual(completed.stdout, "")
                        self.assertRegex(completed.stderr, r"[А-Яа-яЁё]")

    def test_shell_verify_current_and_status_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "missing"
            before = _snapshot(Path(raw))
            for arguments in (
                ["--status", "--verify-current", "--target", str(target)],
                ["--verify-current", "--status", "--target", str(target)],
                ["--verify-current", "--json", "--target", str(target)],
                ["--status", "--verify", "--target", str(target)],
                ["--verify", "--status", "--target", str(target)],
                ["--verify", "--verify-current", "--target", str(target)],
                ["--verify-current", "--verify", "--target", str(target)],
                ["--verify", "--json", "--target", str(target)],
                ["--json", "--target", str(target)],
            ):
                with self.subTest(arguments=arguments):
                    completed = subprocess.run(
                        [str(REPO / "install.sh"), *arguments],
                        cwd=REPO,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        text=True,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(completed.stdout, "")
                    self.assertRegex(completed.stderr, r"[А-Яа-яЁё]")
                    self.assertEqual(_snapshot(Path(raw)), before)

    def test_shell_rejects_option_tokens_as_target_values_before_any_install(self) -> None:
        cases = (
            (["--target", "--status"], "--status"),
            (["--status", "--target", "--json"], "--json"),
            (["--target", "-h"], "-h"),
            (["--status", "--target", "-x"], "-x"),
        )
        for arguments, accidental_name in cases:
            with self.subTest(arguments=arguments):
                accidental_target = REPO / accidental_name
                self.assertFalse(accidental_target.exists())

                completed = subprocess.run(
                    [str(REPO / "install.sh"), *arguments],
                    cwd=REPO,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertRegex(completed.stderr, r"[А-Яа-яЁё]")
                self.assertIn("путь", completed.stderr.lower())
                self.assertFalse(accidental_target.exists())

    def test_shell_and_direct_help_are_russian_and_explain_status(self) -> None:
        completed = subprocess.run(
            [str(REPO / "install.sh"), "--help"],
            cwd=REPO,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        self.assertIn("Использование:", completed.stdout)
        self.assertIn("без записи", completed.stdout)
        self.assertIn("--verify", completed.stdout)
        self.assertIn("офлайн", completed.stdout.lower())
        self.assertIn("--verify-current", completed.stdout)
        self.assertIn("сеть", completed.stdout.lower())
        self.assertNotIn("Usage:", completed.stdout)
        direct_help = installer._parser().format_help()
        self.assertIn("Использование:", direct_help)
        self.assertIn("параметры:", direct_help)
        self.assertIn("без записи", direct_help)
        self.assertNotIn("show this help message", direct_help)

    def test_invalid_mode_combinations_are_usage_errors_before_target_read(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "target"
            for argv in (
                ["--target", str(target), "--json", "--repo", str(REPO)],
                ["--status", "--target", str(target), "--repo", str(REPO)],
                [
                    "--status",
                    "--target",
                    str(target),
                    "--repo",
                    str(REPO),
                    "--source-skills-root",
                    str(REPO / "skills"),
                ],
                ["--s", "--target", str(target)],
                [
                    "--status",
                    "--target",
                    str(target),
                    "--preserve-target-development",
                ],
                [
                    "--status",
                    "--verify-runtime",
                    "--target",
                    str(target),
                ],
                [
                    "--verify-runtime",
                    "--target",
                    str(target),
                ],
                [
                    "--verify-runtime",
                    "--repo",
                    str(REPO),
                    "--target",
                    str(target),
                    "--json",
                ],
                [
                    "--require-current",
                    "--repo",
                    str(REPO),
                    "--target",
                    str(target),
                ],
                [
                    "--status",
                    "--require-current",
                    "--target",
                    str(target),
                ],
            ):
                with self.subTest(argv=argv):
                    errors = io.StringIO()
                    with redirect_stderr(errors):
                        with self.assertRaises(SystemExit) as caught:
                            installer.main(argv)
                    self.assertEqual(caught.exception.code, 2)
                    self.assertRegex(errors.getvalue(), r"[А-Яа-яЁё]")
                    self.assertIn("ошибка", errors.getvalue().lower())
                    self.assertNotIn("cannot be combined", errors.getvalue())
                    self.assertNotIn("requires --status", errors.getvalue())
                    self.assertNotIn("not allowed with argument", errors.getvalue())
                    self.assertNotIn("ambiguous option", errors.getvalue())
                    self.assertNotIn("unrecognized arguments", errors.getvalue())
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
