from __future__ import annotations

import io
import errno
import json
import os
from pathlib import Path
import shutil
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

            incomplete = _status(target)

            self.assertEqual(incomplete["status"], "incomplete")
            self.assertEqual(incomplete["exit_code"], 20)
            self.assertEqual(incomplete["managed_skills"]["missing"], [missing_name])
            self.assertEqual(_snapshot(target), partial_before)

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

            with patch.object(
                installer,
                "_status_read_regular_at",
                side_effect=change_after_first_journal_read,
            ):
                changing = _status(target)

            self.assertEqual(changing["status"], "recovery_required")

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

            with patch.object(
                installer,
                "_status_read_regular_at",
                side_effect=repair_after_invalid_read,
            ):
                report = _status(target)

            self.assertEqual(report["status"], "recovery_required")
            self.assertEqual(report["reason_code"], "observation_changed")

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
