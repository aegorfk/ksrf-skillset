from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import install_skillset as installer  # noqa: E402
from install_skillset import InstallationError, copy_skillset  # noqa: E402
from skillset_file_contract import SKILL_NAMES, payload_files, tree_digest  # noqa: E402


LOCK_FILE_NAME = getattr(installer, "INSTALL_LOCK_FILE_NAME", ".ksrf-install.lock")
TRANSACTION_PREFIX = getattr(
    installer,
    "INSTALL_TRANSACTION_PREFIX",
    ".ksrf-install-transaction-",
)
JOURNAL_FILE_NAME = getattr(
    installer,
    "INSTALL_TRANSACTION_JOURNAL_NAME",
    "journal.json",
)


class _PreservationReadBeforeLock(RuntimeError):
    pass


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


def _path_snapshot(path: Path) -> tuple[tuple[object, ...], ...] | None:
    if not path.exists() and not path.is_symlink():
        return None
    entries: list[tuple[object, ...]] = []

    def append_entry(item: Path, relative: str) -> None:
        metadata = item.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if item.is_symlink():
            entries.append((relative, "symlink", mode, os.readlink(item)))
        elif item.is_dir():
            entries.append((relative, "directory", mode))
        elif item.is_file():
            entries.append((relative, "file", mode, item.read_bytes()))
        else:
            entries.append((relative, "other", mode))

    append_entry(path, ".")
    if path.is_dir() and not path.is_symlink():
        for item in sorted(path.rglob("*"), key=lambda candidate: candidate.as_posix()):
            append_entry(item, item.relative_to(path).as_posix())
    return tuple(entries)


def _managed_snapshot(target: Path) -> dict[str, tuple[tuple[object, ...], ...] | None]:
    return {
        skill_name: _path_snapshot(target / skill_name)
        for skill_name in SKILL_NAMES
    }


def _transaction_artifacts(target: Path) -> list[str]:
    prefixes = {
        ".ksrf-install-",
        ".ksrf-transaction-",
        str(TRANSACTION_PREFIX),
    }
    return sorted(
        item.name
        for item in target.iterdir()
        if item.name != LOCK_FILE_NAME
        and any(item.name.startswith(prefix) for prefix in prefixes)
    )


def _transaction_artifact_paths(target: Path) -> list[Path]:
    names = set(_transaction_artifacts(target))
    return sorted(
        (target / name for name in names),
        key=lambda item: item.name,
    )


def _is_direct_managed_destination(destination: object, target: Path, name: str) -> bool:
    if not isinstance(destination, (str, os.PathLike)):
        return False
    candidate = Path(destination)
    if not candidate.is_absolute():
        return candidate.parent == Path(".") and candidate.name == name
    candidate = Path(os.path.abspath(candidate))
    return candidate.parent == target.resolve(strict=True) and candidate.name == name


@contextmanager
def _fail_once_on_live_destination(
    target: Path,
    skill_name: str,
    exception_factory: object,
):
    target = Path(os.path.abspath(target))
    state = {"triggered": False}
    original_replace = os.replace
    original_rename = os.rename

    def maybe_fail(original: object):
        def wrapped(source: object, destination: object, *args: object, **kwargs: object):
            if (
                not state["triggered"]
                and _is_direct_managed_destination(destination, target, skill_name)
            ):
                state["triggered"] = True
                raise exception_factory()  # type: ignore[operator]
            return original(source, destination, *args, **kwargs)  # type: ignore[operator]

        return wrapped

    with patch.object(os, "replace", maybe_fail(original_replace)), patch.object(
        os,
        "rename",
        maybe_fail(original_rename),
    ):
        yield state


CRASH_INSTALL_SCRIPT = textwrap.dedent(
    r"""
    import os
    from pathlib import Path
    import sys
    from unittest.mock import patch

    tools, source_value, target_value = sys.argv[1:]
    sys.path.insert(0, tools)
    from install_skillset import copy_skillset
    from skillset_file_contract import SKILL_NAMES

    source = Path(source_value)
    target = Path(os.path.abspath(target_value)).resolve(strict=True)
    trigger_name = SKILL_NAMES[1]
    original_replace = os.replace
    original_rename = os.rename

    def direct_target(destination):
        try:
            candidate = Path(os.fspath(destination))
        except TypeError:
            return False
        if not candidate.is_absolute():
            return candidate.parent == Path(".") and candidate.name == trigger_name
        candidate = Path(os.path.abspath(candidate))
        return candidate.parent == target and candidate.name == trigger_name

    def crash_once(original):
        def wrapped(source_path, destination_path, *args, **kwargs):
            if direct_target(destination_path):
                os._exit(86)
            return original(source_path, destination_path, *args, **kwargs)
        return wrapped

    with patch.object(os, "replace", crash_once(original_replace)), patch.object(
        os, "rename", crash_once(original_rename)
    ):
        copy_skillset(source, target)
    raise SystemExit(87)
    """
)


LOCK_HOLDER_SCRIPT = textwrap.dedent(
    r"""
    import fcntl
    import os
    from pathlib import Path
    import sys

    lock_path = Path(sys.argv[1])
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    print("READY", flush=True)
    sys.stdin.buffer.read()
    """
)


COMMITTED_CLEANUP_CRASH_SCRIPT = textwrap.dedent(
    r"""
    import os
    from pathlib import Path
    import sys
    from unittest.mock import patch

    tools, source_value, target_value, transaction_prefix = sys.argv[1:]
    sys.path.insert(0, tools)
    import install_skillset as installer
    from skillset_file_contract import SKILL_NAMES

    source = Path(source_value)
    target = Path(os.path.abspath(target_value)).resolve(strict=True)
    original_remove = installer._remove_owned_directory

    def complete_new_generation():
        for skill_name in SKILL_NAMES:
            marker = target / skill_name / "SKILL.md"
            if not marker.is_file() or "generation=B" not in marker.read_text(encoding="utf-8"):
                return False
        return True

    def crash_before_cleanup(path, *args, **kwargs):
        candidate = Path(os.path.abspath(os.fspath(path)))
        installer_owned = (
            (
                candidate.parent == target
                and (
                    candidate.name.startswith(".ksrf-install-")
                    or candidate.name.startswith(transaction_prefix)
                )
            )
            or (
                candidate.parent.parent == target
                and candidate.parent.name.startswith(".ksrf-install-gc-")
            )
        )
        if installer_owned and complete_new_generation():
            os._exit(88)
        return original_remove(path, *args, **kwargs)

    with patch.object(installer, "_remove_owned_directory", crash_before_cleanup):
        installer.copy_skillset(source, target)
    raise SystemExit(87)
    """
)


ROLLBACK_CRASH_SCRIPT = textwrap.dedent(
    r"""
    import os
    from pathlib import Path
    import sys
    from unittest.mock import patch

    tools, source_value, target_value = sys.argv[1:]
    sys.path.insert(0, tools)
    from install_skillset import copy_skillset
    from skillset_file_contract import SKILL_NAMES

    source = Path(source_value)
    target = Path(os.path.abspath(target_value)).resolve(strict=True)
    trigger_name = SKILL_NAMES[3]
    original_replace = os.replace
    original_rename = os.rename
    state = {"forward_failed": False}

    def direct_target(destination):
        try:
            candidate = Path(os.fspath(destination))
        except TypeError:
            return False
        if not candidate.is_absolute():
            return candidate.parent == Path(".") and candidate.name in SKILL_NAMES
        candidate = Path(os.path.abspath(candidate))
        return candidate.parent == target and candidate.name in SKILL_NAMES

    def fail_forward_then_crash_rollback(original):
        def wrapped(source_path, destination_path, *args, **kwargs):
            if direct_target(destination_path):
                candidate = Path(os.fspath(destination_path))
                if candidate.is_absolute():
                    candidate = Path(os.path.abspath(candidate))
                if state["forward_failed"]:
                    os._exit(89)
                if candidate.name == trigger_name:
                    state["forward_failed"] = True
                    raise OSError("injected forward failure before rollback crash")
            return original(source_path, destination_path, *args, **kwargs)
        return wrapped

    with patch.object(
        os, "replace", fail_forward_then_crash_rollback(original_replace)
    ), patch.object(os, "rename", fail_forward_then_crash_rollback(original_rename)):
        copy_skillset(source, target)
    raise SystemExit(90)
    """
)


@contextmanager
def _held_target_lock(target: Path):
    holder = subprocess.Popen(
        [sys.executable, "-c", LOCK_HOLDER_SCRIPT, str(target / LOCK_FILE_NAME)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    try:
        assert holder.stdout is not None
        ready = holder.stdout.readline().strip()
        if ready != "READY":
            stderr = holder.stderr.read() if holder.stderr is not None else ""
            raise AssertionError(f"lock holder did not start: {ready!r} {stderr!r}")
        yield holder
    finally:
        if holder.stdin is not None:
            holder.stdin.close()
        holder.wait(timeout=5)
        if holder.stdout is not None:
            holder.stdout.close()
        if holder.stderr is not None:
            holder.stderr.close()


class TransactionalSkillsetInstallRegressionTests(unittest.TestCase):
    def _unmanaged_fixture(self, target: Path) -> dict[str, object]:
        unrelated_skill = target / "unmanaged-user-skill"
        unrelated_skill.mkdir(parents=True)
        (unrelated_skill / "SKILL.md").write_bytes(b"# user-owned\n")
        note = target / "user-note.txt"
        note.write_bytes(b"must remain byte-identical\n")
        return {
            "skill": _path_snapshot(unrelated_skill),
            "note": note.read_bytes(),
        }

    def _assert_unmanaged_unchanged(
        self,
        target: Path,
        expected: dict[str, object],
    ) -> None:
        self.assertEqual(
            _path_snapshot(target / "unmanaged-user-skill"),
            expected["skill"],
        )
        self.assertEqual((target / "user-note.txt").read_bytes(), expected["note"])

    def test_oserror_mid_commit_rolls_back_exactly_including_absent_skill(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            absent_name = SKILL_NAMES[0]
            shutil.rmtree(target / absent_name)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)

            observed: BaseException | None = None
            with _fail_once_on_live_destination(
                target,
                SKILL_NAMES[2],
                lambda: OSError("injected mid-commit failure"),
            ) as fault:
                try:
                    copy_skillset(source_b, target)
                except (InstallationError, OSError) as exc:
                    observed = exc

            self.assertIsNotNone(observed)
            self.assertTrue(fault["triggered"])
            self.assertEqual(_managed_snapshot(target), before)
            self.assertIsNone(_path_snapshot(target / absent_name))
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_keyboard_interrupt_mid_commit_rolls_back_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)

            observed: BaseException | None = None
            with _fail_once_on_live_destination(
                target,
                SKILL_NAMES[3],
                lambda: KeyboardInterrupt(),
            ) as fault:
                try:
                    copy_skillset(source_b, target)
                except KeyboardInterrupt as exc:
                    observed = exc

            self.assertIsInstance(observed, KeyboardInterrupt)
            self.assertTrue(fault["triggered"])
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_held_target_lock_refuses_before_preservation_or_target_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            preserved = target / SKILL_NAMES[0] / "tests" / "fixture.json"
            preserved.parent.mkdir(parents=True)
            preserved.write_bytes(b'{"preserve": true}\n')
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)

            with _held_target_lock(target):
                observed: BaseException | None = None
                with patch.object(
                    installer,
                    "development_files",
                    side_effect=_PreservationReadBeforeLock(
                        "target preservation was read before lock refusal"
                    ),
                ) as development_mock:
                    try:
                        copy_skillset(
                            source_b,
                            target,
                            preserve_target_development=True,
                        )
                    except BaseException as exc:  # inspect exact fail-closed class below
                        observed = exc
                self.assertIsInstance(observed, InstallationError)
                self.assertRegex(str(observed), r"(?i)(lock|install.*progress|writer)")
                development_mock.assert_not_called()

            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)

    def test_process_death_recovers_old_generation_before_new_source_validation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)

            crashed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    CRASH_INSTALL_SCRIPT,
                    str(TOOLS),
                    str(source_b),
                    str(target),
                ],
                cwd=REPO,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                crashed.returncode,
                86,
                msg=f"stdout={crashed.stdout}\nstderr={crashed.stderr}",
            )

            invalid_new_source = root / "source-does-not-exist"
            observed: BaseException | None = None
            try:
                copy_skillset(invalid_new_source, target)
            except (FileNotFoundError, InstallationError, OSError) as exc:
                observed = exc

            self.assertIsNotNone(observed)
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_process_death_after_durable_commit_keeps_new_and_finishes_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            expected_new = {
                skill_name: _path_snapshot(source_b / skill_name)
                for skill_name in SKILL_NAMES
            }

            crashed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    COMMITTED_CLEANUP_CRASH_SCRIPT,
                    str(TOOLS),
                    str(source_b),
                    str(target),
                    str(TRANSACTION_PREFIX),
                ],
                cwd=REPO,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                crashed.returncode,
                88,
                msg=f"stdout={crashed.stdout}\nstderr={crashed.stderr}",
            )
            self.assertEqual(_managed_snapshot(target), expected_new)
            self.assertTrue(_transaction_artifacts(target))

            observed: BaseException | None = None
            try:
                copy_skillset(root / "invalid-new-source", target)
            except (FileNotFoundError, InstallationError, OSError) as exc:
                observed = exc

            self.assertIsNotNone(observed)
            self.assertEqual(_managed_snapshot(target), expected_new)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_process_death_during_rollback_is_idempotently_finished_next_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            expected_old = _managed_snapshot(target)

            crashed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    ROLLBACK_CRASH_SCRIPT,
                    str(TOOLS),
                    str(source_b),
                    str(target),
                ],
                cwd=REPO,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                crashed.returncode,
                89,
                msg=f"stdout={crashed.stdout}\nstderr={crashed.stderr}",
            )
            self.assertTrue(_transaction_artifacts(target))

            observed: BaseException | None = None
            try:
                copy_skillset(root / "invalid-new-source", target)
            except (FileNotFoundError, InstallationError, OSError) as exc:
                observed = exc

            self.assertIsNotNone(observed)
            self.assertEqual(_managed_snapshot(target), expected_old)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_missing_required_backup_after_crash_fails_closed_and_retains_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)

            crashed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    CRASH_INSTALL_SCRIPT,
                    str(TOOLS),
                    str(source_b),
                    str(target),
                ],
                cwd=REPO,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(crashed.returncode, 86)
            transactions = _transaction_artifact_paths(target)
            self.assertEqual(len(transactions), 1)
            transaction = transactions[0]
            old_backups = sorted(
                {
                    marker.parent
                    for marker in transaction.rglob("SKILL.md")
                    if "generation=A" in marker.read_text(encoding="utf-8")
                },
                key=lambda item: item.as_posix(),
            )
            self.assertGreaterEqual(
                len(old_backups),
                2,
                msg="crash recovery evidence contains no complete old backups",
            )
            missing_backup = old_backups[0]
            retained_backup = old_backups[1]
            retained_before = _path_snapshot(retained_backup)
            shutil.rmtree(missing_backup)
            managed_after_damage = _managed_snapshot(target)

            observed: BaseException | None = None
            try:
                copy_skillset(root / "invalid-new-source", target)
            except (FileNotFoundError, InstallationError, OSError, ValueError) as exc:
                observed = exc

            self.assertIsInstance(observed, InstallationError)
            self.assertRegex(str(observed), r"(?i)(backup|recover|transaction)")
            self.assertEqual(_managed_snapshot(target), managed_after_damage)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertTrue(transaction.is_dir())
            self.assertFalse(missing_backup.exists())
            self.assertEqual(_path_snapshot(retained_backup), retained_before)
            self.assertTrue(list(transaction.rglob(JOURNAL_FILE_NAME)))

    def test_multiple_transaction_directories_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)
            transactions = [
                target / f"{TRANSACTION_PREFIX}one",
                target / f"{TRANSACTION_PREFIX}two",
            ]
            for transaction in transactions:
                transaction.mkdir()
                (transaction / JOURNAL_FILE_NAME).write_bytes(b"{}\n")

            observed: BaseException | None = None
            try:
                copy_skillset(source_b, target)
            except (InstallationError, OSError, ValueError) as exc:
                observed = exc

            self.assertIsInstance(observed, InstallationError)
            self.assertRegex(str(observed), r"(?i)(multiple|transaction|recover)")
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)
            for transaction in transactions:
                self.assertEqual(
                    (transaction / JOURNAL_FILE_NAME).read_bytes(),
                    b"{}\n",
                )

    def test_symlinked_transaction_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)
            external = root / "external-transaction"
            external.mkdir()
            external_journal = external / JOURNAL_FILE_NAME
            external_journal.write_bytes(b"external evidence\n")
            transaction_link = target / f"{TRANSACTION_PREFIX}symlink"
            transaction_link.symlink_to(external, target_is_directory=True)

            observed: BaseException | None = None
            try:
                copy_skillset(source_b, target)
            except (InstallationError, OSError, ValueError) as exc:
                observed = exc

            self.assertIsInstance(observed, InstallationError)
            self.assertRegex(str(observed), r"(?i)(symlink|transaction|unsafe)")
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertTrue(transaction_link.is_symlink())
            self.assertEqual(external_journal.read_bytes(), b"external evidence\n")

    def test_same_digest_reinstall_failure_rolls_back_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)

            observed: BaseException | None = None
            with _fail_once_on_live_destination(
                target,
                SKILL_NAMES[2],
                lambda: OSError("same-digest reinstall failure"),
            ) as fault:
                try:
                    copy_skillset(source_a, target)
                except (InstallationError, OSError) as exc:
                    observed = exc

            self.assertIsNotNone(observed)
            self.assertTrue(fault["triggered"])
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_corrupt_journal_fails_closed_without_touching_target_or_unmanaged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)
            corrupt_transaction = target / f"{TRANSACTION_PREFIX}corrupt"
            corrupt_transaction.mkdir()
            corrupt_journal = corrupt_transaction / JOURNAL_FILE_NAME
            corrupt_journal.write_bytes(b'{"schema_version":')

            observed: BaseException | None = None
            try:
                copy_skillset(source_b, target)
            except (InstallationError, OSError, ValueError) as exc:
                observed = exc

            self.assertIsInstance(observed, InstallationError)
            self.assertRegex(str(observed), r"(?i)(journal|transaction|recover|corrupt)")
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertTrue(corrupt_transaction.is_dir())
            self.assertEqual(corrupt_journal.read_bytes(), b'{"schema_version":')

    def test_success_is_exact_preserves_unmanaged_and_leaves_no_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            stale = target / SKILL_NAMES[0] / "stale-runtime.txt"
            stale.write_bytes(b"remove on successful exact install\n")
            unmanaged = self._unmanaged_fixture(target)

            installed = copy_skillset(source_b, target)

            self.assertEqual(installed, target)
            for skill_name in SKILL_NAMES:
                with self.subTest(skill_name=skill_name):
                    source_skill = source_b / skill_name
                    installed_skill = target / skill_name
                    source_payload = payload_files(source_skill)
                    installed_payload = payload_files(installed_skill)
                    self.assertEqual(
                        [item.relative_to(source_skill) for item in source_payload],
                        [item.relative_to(installed_skill) for item in installed_payload],
                    )
                    self.assertEqual(
                        tree_digest(source_skill, source_payload),
                        tree_digest(installed_skill, installed_payload),
                    )
            self.assertFalse(stale.exists())
            self._assert_unmanaged_unchanged(target, unmanaged)
            self.assertEqual(_transaction_artifacts(target), [])

    def test_install_sh_under_held_lock_prints_no_success_or_export(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            target = root / "target with space and apostrophe's"
            copy_skillset(source_a, target)
            unmanaged = self._unmanaged_fixture(target)
            before = _managed_snapshot(target)

            with _held_target_lock(target):
                completed = subprocess.run(
                    [str(REPO / "install.sh"), "--target", str(target)],
                    cwd=REPO,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    text=True,
                    capture_output=True,
                    check=False,
                )

            self.assertNotEqual(completed.returncode, 0)
            combined = completed.stdout + completed.stderr
            self.assertRegex(combined, r"(?i)(lock|install.*progress|writer)")
            self.assertNotIn("Installed exact manifest-covered", completed.stdout)
            self.assertNotIn("Synchronized exact KSRF runtime", completed.stdout)
            self.assertNotIn("export KSRF_SKILLS_ROOT=", completed.stdout)
            self.assertEqual(_managed_snapshot(target), before)
            self._assert_unmanaged_unchanged(target, unmanaged)


if __name__ == "__main__":
    unittest.main()
