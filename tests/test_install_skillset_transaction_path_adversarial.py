from __future__ import annotations

import os
from pathlib import Path
import subprocess
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


def _generation(target: Path) -> set[str]:
    values: set[str] = set()
    for skill_name in SKILL_NAMES:
        marker = target / skill_name / "SKILL.md"
        if marker.is_file():
            for line in marker.read_text(encoding="utf-8").splitlines():
                if line.startswith("generation="):
                    values.add(line.removeprefix("generation="))
    return values


class TransactionPathAdversarialRegressionTests(unittest.TestCase):
    def test_retarget_inside_managed_rename_uses_held_dirfd_not_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            actual_target = target.resolve(strict=True)
            moved_target = root.resolve(strict=True) / "moved-during-rename"
            original_replace = os.replace
            injected = {"done": False}

            def retarget_at_rename(
                source: os.PathLike[str] | str,
                destination: os.PathLike[str] | str,
                *args: object,
                **kwargs: object,
            ) -> None:
                source_path = Path(source)
                if (
                    not injected["done"]
                    and "src_dir_fd" in kwargs
                    and source_path.parent == Path(".")
                    and source_path.name in SKILL_NAMES
                ):
                    injected["done"] = True
                    original_replace(actual_target, moved_target)
                    actual_target.mkdir()
                    (actual_target / "replacement-marker.txt").write_text(
                        "replacement must not receive managed renames\n",
                        encoding="utf-8",
                    )
                original_replace(source, destination, *args, **kwargs)

            with patch.object(os, "replace", side_effect=retarget_at_rename):
                with self.assertRaisesRegex(InstallationError, r"(?i)(target|inode|anchor)"):
                    copy_skillset(source_b, target)

            self.assertTrue(injected["done"])
            self.assertEqual(
                (target / "replacement-marker.txt").read_text(encoding="utf-8"),
                "replacement must not receive managed renames\n",
            )
            self.assertEqual(_generation(target), set())
            self.assertNotEqual(_generation(moved_target), {"B"})

    def test_retargeted_target_cannot_admit_a_second_writer_or_receive_first_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            source_c = _make_source(root, "C")
            target = root / "target"
            copy_skillset(source_a, target)
            moved_target = root / "moved-target"
            second_result: dict[str, subprocess.CompletedProcess[str]] = {}
            original_recovery = installer._recover_existing_transaction
            injected = {"done": False}

            def retarget_after_real_lock(actual_target: Path) -> str | None:
                result = original_recovery(actual_target)
                if not injected["done"]:
                    injected["done"] = True
                    os.replace(actual_target, moved_target)
                    actual_target.mkdir()
                    (actual_target / "unmanaged.txt").write_text(
                        "new path must remain untouched\n",
                        encoding="utf-8",
                    )
                    second_result["value"] = subprocess.run(
                        [
                            sys.executable,
                            str(TOOLS / "install_skillset.py"),
                            "--source",
                            str(source_c),
                            "--target",
                            str(actual_target),
                        ],
                        cwd=REPO,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                return result

            with patch.object(
                installer,
                "_recover_existing_transaction",
                side_effect=retarget_after_real_lock,
            ):
                with self.assertRaisesRegex(InstallationError, r"(?i)(target|inode|anchor)"):
                    copy_skillset(source_b, target)

            self.assertTrue(injected["done"])
            self.assertNotEqual(second_result["value"].returncode, 0)
            self.assertEqual(
                (target / "unmanaged.txt").read_text(encoding="utf-8"),
                "new path must remain untouched\n",
            )
            self.assertEqual(_generation(target), set())
            self.assertEqual(_generation(moved_target), {"A"})

    def test_late_destination_mutation_is_retained_as_evidence_not_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            actual_target = target.resolve(strict=True)
            original_write = installer._write_journal
            injected = {"done": False}

            def mutate_after_backing_up_intent(
                transaction_root: Path,
                journal: dict[str, object],
            ) -> None:
                original_write(transaction_root, journal)
                skills = journal["skills"]
                assert isinstance(skills, list)
                first = skills[0]
                assert isinstance(first, dict)
                if not injected["done"] and first["progress"] == "backing_up":
                    injected["done"] = True
                    (actual_target / SKILL_NAMES[0] / "late-user-file.txt").write_text(
                        "must survive fail-closed handling\n",
                        encoding="utf-8",
                    )

            with patch.object(
                installer,
                "_write_journal",
                side_effect=mutate_after_backing_up_intent,
            ):
                with self.assertRaisesRegex(
                    InstallationError,
                    r"(?i)(backup|identity|rollback|recovery|evidence)",
                ):
                    copy_skillset(source_b, target)

            transactions = list(target.glob(f"{installer.INSTALL_TRANSACTION_PREFIX}*"))
            self.assertEqual(len(transactions), 1)
            retained = transactions[0] / "backups" / SKILL_NAMES[0] / "late-user-file.txt"
            self.assertEqual(
                retained.read_text(encoding="utf-8"),
                "must survive fail-closed handling\n",
            )

    def test_nested_device_boundary_is_rejected_before_transaction_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            boundary = target.resolve(strict=True) / SKILL_NAMES[0] / "external-volume"
            boundary.mkdir()
            precious = boundary / "precious.bin"
            precious.write_bytes(b"external bytes\n")
            original_lstat = Path.lstat

            def different_device(path: Path):
                metadata = original_lstat(path)
                if path == boundary:
                    values = list(metadata)
                    values[2] = metadata.st_dev + 1
                    return os.stat_result(values)
                return metadata

            with patch.object(Path, "lstat", new=different_device):
                with self.assertRaisesRegex(
                    InstallationError,
                    r"(?i)(device|mount|managed tree)",
                ):
                    copy_skillset(source_b, target)

            self.assertEqual(precious.read_bytes(), b"external bytes\n")
            self.assertEqual(
                list(target.glob(f"{installer.INSTALL_TRANSACTION_PREFIX}*")),
                [],
            )

    def test_temp_only_prejournal_failure_is_cleaned_and_retry_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source_a = _make_source(root, "A")
            source_b = _make_source(root, "B")
            target = root / "target"
            copy_skillset(source_a, target)
            original_replace = os.replace
            injected = {"done": False}

            def fail_first_journal_publish(
                source: os.PathLike[str] | str,
                destination: os.PathLike[str] | str,
                *args: object,
                **kwargs: object,
            ) -> None:
                source_path = Path(source)
                destination_path = Path(destination)
                if (
                    not injected["done"]
                    and source_path.name == installer._JOURNAL_TEMP_NAME
                    and destination_path.name == installer.INSTALL_TRANSACTION_JOURNAL_NAME
                ):
                    injected["done"] = True
                    raise OSError("injected pre-journal publication failure")
                original_replace(source, destination, *args, **kwargs)

            with patch.object(os, "replace", side_effect=fail_first_journal_publish):
                with self.assertRaises(OSError):
                    copy_skillset(source_b, target)

            self.assertTrue(injected["done"])
            self.assertEqual(
                list(target.glob(f"{installer.INSTALL_TRANSACTION_PREFIX}*")),
                [],
            )
            copy_skillset(source_b, target)
            self.assertEqual(_generation(target), {"B"})


if __name__ == "__main__":
    unittest.main()
