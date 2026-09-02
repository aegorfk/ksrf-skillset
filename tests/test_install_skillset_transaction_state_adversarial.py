from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import install_skillset as installer  # noqa: E402
from install_skillset import InstallationError, copy_skillset  # noqa: E402
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


def _path_snapshot(path: Path) -> tuple[tuple[object, ...], ...] | None:
    if not path.exists() and not path.is_symlink():
        return None
    entries: list[tuple[object, ...]] = []
    paths = [path]
    if path.is_dir() and not path.is_symlink():
        paths.extend(sorted(path.rglob("*"), key=lambda item: item.as_posix()))
    for item in paths:
        metadata = item.lstat()
        relative = "." if item == path else item.relative_to(path).as_posix()
        mode = stat.S_IMODE(metadata.st_mode)
        if item.is_symlink():
            entries.append((relative, "symlink", mode, os.readlink(item)))
        elif item.is_dir():
            entries.append((relative, "directory", mode))
        elif item.is_file():
            entries.append((relative, "file", mode, item.read_bytes()))
        else:
            entries.append((relative, "other", mode))
    return tuple(entries)


def _managed_snapshot(target: Path) -> dict[str, tuple[tuple[object, ...], ...] | None]:
    return {skill_name: _path_snapshot(target / skill_name) for skill_name in SKILL_NAMES}


def _active_transactions(target: Path) -> list[Path]:
    return sorted(
        target.glob(f"{installer.INSTALL_TRANSACTION_PREFIX}*"),
        key=lambda item: item.name,
    )


def _garbage_roots(target: Path) -> list[Path]:
    return sorted(
        target.glob(f"{installer.INSTALL_GC_PREFIX}*"),
        key=lambda item: item.name,
    )


class TransactionStateAdversarialRegressionTests(unittest.TestCase):
    def test_gc_journal_temp_left_before_replace_is_discarded_on_retry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)

            with patch.object(
                installer,
                "_remove_owned_directory",
                side_effect=OSError("retain committed GC before container deletion"),
            ):
                with self.assertRaises(OSError):
                    copy_skillset(source_b, target)

            garbage = _garbage_roots(target)
            self.assertEqual(len(garbage), 1)
            garbage_root = garbage[0]
            actual_garbage_root = garbage_root.resolve(strict=True)
            original_replace = os.replace
            injected = {"done": False}

            def die_before_cleanup_journal_replace(
                source: os.PathLike[str] | str,
                destination: os.PathLike[str] | str,
                *args: object,
                **kwargs: object,
            ) -> None:
                source_path = Path(source)
                if (
                    not injected["done"]
                    and source_path.parent == actual_garbage_root
                    and source_path.name == installer._JOURNAL_TEMP_NAME
                ):
                    injected["done"] = True
                    raise SystemExit(91)
                original_replace(source, destination, *args, **kwargs)

            with patch.object(os, "replace", side_effect=die_before_cleanup_journal_replace):
                with self.assertRaisesRegex(SystemExit, "91"):
                    copy_skillset(source_b, target)

            self.assertTrue(injected["done"])
            self.assertTrue((garbage_root / installer._JOURNAL_TEMP_NAME).is_file())

            copy_skillset(source_b, target)

            self.assertEqual(_garbage_roots(target), [])

    def test_building_copy_failure_discards_staging_without_nonterminal_gc(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            old_generation = _managed_snapshot(target)
            original_copy = shutil.copy2
            injected = {"done": False}

            def fail_first_staged_copy(*args: object, **kwargs: object):
                if not injected["done"]:
                    injected["done"] = True
                    raise OSError("injected building copy failure")
                return original_copy(*args, **kwargs)

            with patch.object(shutil, "copy2", side_effect=fail_first_staged_copy):
                with self.assertRaises(OSError):
                    copy_skillset(source_b, target)

            self.assertTrue(injected["done"])
            self.assertEqual(_managed_snapshot(target), old_generation)
            self.assertEqual(_active_transactions(target), [])
            self.assertEqual(_garbage_roots(target), [])

            copy_skillset(source_b, target)
            self.assertEqual(_garbage_roots(target), [])

    def test_interrupted_building_cleanup_remains_retryable_under_its_journal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            original_copy = shutil.copy2
            original_remove = installer._remove_owned_directory
            copy_fault = {"done": False}
            cleanup_fault = {"done": False}

            def fail_after_one_staged_copy(*args: object, **kwargs: object):
                result = original_copy(*args, **kwargs)
                if not copy_fault["done"]:
                    copy_fault["done"] = True
                    raise OSError("injected building failure after one copy")
                return result

            def partially_remove_staging_then_fail(path: Path) -> None:
                if not cleanup_fault["done"] and path.name == "staging":
                    victim = next(
                        candidate
                        for candidate in sorted(path.rglob("*"))
                        if candidate.is_file()
                    )
                    victim.unlink()
                    cleanup_fault["done"] = True
                    raise OSError("injected interrupted building cleanup")
                original_remove(path)

            with patch.object(
                shutil,
                "copy2",
                side_effect=fail_after_one_staged_copy,
            ), patch.object(
                installer,
                "_remove_owned_directory",
                side_effect=partially_remove_staging_then_fail,
            ):
                with self.assertRaises(InstallationError):
                    copy_skillset(source_b, target)

            self.assertTrue(copy_fault["done"])
            self.assertTrue(cleanup_fault["done"])
            self.assertEqual(len(_active_transactions(target)), 1)
            self.assertEqual(_garbage_roots(target), [])

            copy_skillset(source_b, target)

            self.assertEqual(_active_transactions(target), [])
            self.assertEqual(_garbage_roots(target), [])

    def test_partial_terminal_gc_deletion_resumes_from_durable_cleanup_intent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            original_remove = installer._remove_owned_directory
            injected = {"done": False}

            def delete_one_backup_file_then_fail(path: Path) -> None:
                if not injected["done"] and path.name == "backups":
                    victim = next(
                        candidate
                        for candidate in sorted(path.rglob("*"))
                        if candidate.is_file()
                    )
                    victim.unlink()
                    injected["done"] = True
                    raise OSError("injected partial terminal GC deletion")
                original_remove(path)

            with patch.object(
                installer,
                "_remove_owned_directory",
                side_effect=delete_one_backup_file_then_fail,
            ):
                with self.assertRaises(OSError):
                    copy_skillset(source_b, target)

            self.assertTrue(injected["done"])
            garbage = _garbage_roots(target)
            self.assertEqual(len(garbage), 1)
            journal = json.loads(
                (garbage[0] / installer.INSTALL_TRANSACTION_JOURNAL_NAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(journal["cleanup"]["backups"], "deleting")

            copy_skillset(source_b, target)

            self.assertEqual(_garbage_roots(target), [])
            self.assertEqual(
                {
                    (target / name / "SKILL.md").read_text(encoding="utf-8").splitlines()[1]
                    for name in SKILL_NAMES
                },
                {"generation=B"},
            )

    def test_forged_gc_namespace_fails_closed_without_deleting_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.mkdir()
            garbage_root = target / f"{installer.INSTALL_GC_PREFIX}{'0' * 32}"
            precious = garbage_root / "backups" / "not-a-managed-skill" / "precious.bin"
            precious.parent.mkdir(parents=True)
            precious.write_bytes(b"user bytes in an unproved GC namespace\n")
            evidence_before = _path_snapshot(garbage_root)

            with self.assertRaisesRegex(
                InstallationError,
                r"(?i)(garbage|journal|transaction|evidence|unsafe)",
            ):
                copy_skillset(root / "missing-source", target)

            self.assertEqual(_path_snapshot(garbage_root), evidence_before)

    def test_stale_committed_gc_revalidates_live_before_deleting_old_backups(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)

            with patch.object(
                installer,
                "_remove_owned_directory",
                side_effect=OSError("stop after durable transaction-to-GC handoff"),
            ):
                with self.assertRaises(OSError):
                    copy_skillset(source_b, target)

            garbage = _garbage_roots(target)
            self.assertEqual(len(garbage), 1)
            garbage_root = garbage[0]
            self.assertTrue(
                (garbage_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME).is_file()
            )
            self.assertTrue(any((garbage_root / "backups").iterdir()))
            evidence_before = _path_snapshot(garbage_root)

            live_marker = target / SKILL_NAMES[0] / "SKILL.md"
            live_marker.write_bytes(b"corrupt live generation\n")
            live_before = _managed_snapshot(target)

            with self.assertRaisesRegex(
                InstallationError,
                r"(?i)(aggregate|committed|generation|garbage|transaction|recover)",
            ):
                copy_skillset(root / "missing-source", target)

            self.assertEqual(_managed_snapshot(target), live_before)
            self.assertEqual(_path_snapshot(garbage_root), evidence_before)

    def test_committed_marker_fsync_failure_cannot_return_success_or_discard_old(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            old_generation = _managed_snapshot(target)
            original_fsync_directory = installer._fsync_directory
            fault = {"triggered": False}

            def fail_committed_marker_fsync(path: Path) -> None:
                journal_path = path / installer.INSTALL_TRANSACTION_JOURNAL_NAME
                if (
                    not fault["triggered"]
                    and path.name.startswith(installer.INSTALL_TRANSACTION_PREFIX)
                    and journal_path.is_file()
                    and json.loads(journal_path.read_text(encoding="utf-8"))["phase"]
                    == "committed"
                ):
                    fault["triggered"] = True
                    raise OSError("injected committed-marker directory fsync failure")
                original_fsync_directory(path)

            with patch.object(
                installer,
                "_fsync_directory",
                side_effect=fail_committed_marker_fsync,
            ):
                with self.assertRaises((InstallationError, OSError)):
                    copy_skillset(source_b, target)

            self.assertTrue(fault["triggered"])
            recovery_evidence = _active_transactions(target) + _garbage_roots(target)
            self.assertTrue(
                _managed_snapshot(target) == old_generation or recovery_evidence,
                "a failed commit-marker fsync must restore old bytes or retain recovery evidence",
            )

    def test_unreachable_rolling_back_progress_vector_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            original_replace_path = installer._replace_path
            actual_target = target.resolve(strict=True)

            def exit_before_second_placement(source: Path, destination: Path) -> None:
                if destination == actual_target / SKILL_NAMES[1]:
                    raise SystemExit(86)
                original_replace_path(source, destination)

            with patch.object(
                installer,
                "_replace_path",
                side_effect=exit_before_second_placement,
            ):
                with self.assertRaisesRegex(SystemExit, "86"):
                    copy_skillset(source_b, target)

            transactions = _active_transactions(target)
            self.assertEqual(len(transactions), 1)
            transaction_root = transactions[0]
            journal_path = transaction_root / installer.INSTALL_TRANSACTION_JOURNAL_NAME
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertEqual(journal["skills"][0]["progress"], "placed")
            self.assertEqual(journal["skills"][1]["progress"], "placing")
            self.assertEqual(journal["skills"][2]["progress"], "pending")

            journal["phase"] = "rolling_back"
            journal["skills"][2]["progress"] = "restored"
            journal_path.write_text(
                json.dumps(journal, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            target_before = _managed_snapshot(target)
            evidence_before = _path_snapshot(transaction_root)

            with self.assertRaisesRegex(
                InstallationError,
                r"(?i)(progress|state|transaction|recover|ambiguous)",
            ):
                copy_skillset(root / "missing-source", target)

            self.assertEqual(_managed_snapshot(target), target_before)
            self.assertEqual(_path_snapshot(transaction_root), evidence_before)


if __name__ == "__main__":
    unittest.main()
