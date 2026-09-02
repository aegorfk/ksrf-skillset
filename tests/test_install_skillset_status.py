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
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


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

    def test_clean_status_points_to_separate_runtime_freshness_check(self) -> None:
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
            command_line = action.splitlines()[0]
            self.assertTrue(command_line.startswith("Команда проверки: "))
            command = shlex.split(command_line.removeprefix("Команда проверки: "))
            installer_entrypoint = REPO / "install.sh"
            self.assertTrue(installer_entrypoint.is_file())
            self.assertEqual(
                command,
                [
                    str(installer_entrypoint),
                    "--verify-current",
                    "--target",
                    str(installer._absolute_without_resolving(target)),
                ],
            )
            self.assertIn("--verify-current", action)
            self.assertNotIn("подтверждается обычной установкой", action)
            self.assertIn("Что делать:", human)
            self.assertIn("--verify-current", human)
            self.assertEqual(_snapshot(target), before)

    def test_clean_guidance_has_honest_fallback_without_repo_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            detached_tool = Path(raw) / "tools" / "install_skillset.py"
            with patch.object(installer, "__file__", str(detached_tool)):
                action = installer._status_runtime_freshness_action(
                    Path(raw) / "skills"
                )

            self.assertIn("недоступна", action)
            self.assertIn("Обновите репозиторий", action)
            self.assertNotIn("Команда проверки:", action)

    def test_clean_guidance_does_not_emit_non_executable_entrypoint(self) -> None:
        with patch.object(installer.os, "access", return_value=False):
            action = installer._status_runtime_freshness_action(
                Path("/tmp/ksrf-runtime-target")
            )

        self.assertIn("недоступна", action)
        self.assertIn("Обновите репозиторий", action)
        self.assertNotIn("Команда проверки:", action)

    def test_clean_guidance_rejects_control_characters_without_line_spoofing(
        self,
    ) -> None:
        for marker in ("\nЛОЖНЫЙ УСПЕХ", "\rподмена", "\x1b[31mкрасный", "\tсдвиг"):
            with self.subTest(marker=repr(marker)):
                action = installer._status_runtime_freshness_action(
                    Path("/tmp/ksrf-runtime" + marker)
                )

                self.assertIn("сформировать нельзя", action)
                self.assertNotIn("Команда проверки:", action)
                self.assertNotIn(marker, action)

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
                    self.assertIn(r"\x0aЛОЖНЫЙ УСПЕХ", output)
                    self.assertNotIn("\nЛОЖНЫЙ УСПЕХ", output)

    @unittest.skipUnless(os.name == "posix", "surrogateescaped paths require POSIX")
    def test_clean_guidance_does_not_emit_dead_command_for_non_utf8_target(self) -> None:
        target = Path(os.fsdecode(b"/tmp/ksrf-status-\xff"))

        action = installer._status_runtime_freshness_action(target)

        self.assertIn("непечатаемые байты", action)
        self.assertIn("сформировать нельзя", action)
        self.assertIn("UTF-8-пути", action)
        self.assertNotIn("Команда проверки:", action)

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
            validator = (
                checkout
                / "skills"
                / "ksrf-complaint-cycle"
                / "scripts"
                / "validate_ksrf_skillset.py"
            )
            validator.parent.mkdir(parents=True)
            validator.write_text(
                "import json, os, sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
                "raise SystemExit(int(os.environ['KSRF_FAKE_EXIT']))\n",
                encoding="utf-8",
            )
            tools = checkout / "tools"
            tools.mkdir()
            (tools / "install_skillset.py").write_text(
                "raise SystemExit(0)\n",
                encoding="utf-8",
            )
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
                            "--skills-root",
                            str(target),
                            "--profile",
                            "runtime",
                            "--strict",
                            "--check-updates",
                            "--require-current",
                        ],
                    )
            self.assertEqual(_snapshot(root), before)

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
            self.assertIn("валидатор", no_validator.stderr.lower())

    @unittest.skipUnless(os.name == "posix", "symlink preflight requires POSIX")
    def test_shell_verify_current_preflight_blocks_unsafe_targets_before_validator(
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
            validator = (
                checkout
                / "skills"
                / "ksrf-complaint-cycle"
                / "scripts"
                / "validate_ksrf_skillset.py"
            )
            validator.parent.mkdir(parents=True)
            validator.write_text(
                "print('validator-ran')\nraise SystemExit(0)\n",
                encoding="utf-8",
            )
            actual = root / "actual"
            actual.mkdir()
            symlink = root / "linked-skills"
            symlink.symlink_to(actual, target_is_directory=True)
            fake_home = root / "home"
            fake_home.mkdir()

            for target in (symlink, Path("/"), fake_home):
                with self.subTest(target=target):
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
                    self.assertNotIn("validator-ran", completed.stderr)

    def test_shell_verify_current_and_status_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "missing"
            before = _snapshot(Path(raw))
            for arguments in (
                ["--status", "--verify-current", "--target", str(target)],
                ["--verify-current", "--status", "--target", str(target)],
                ["--verify-current", "--json", "--target", str(target)],
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
