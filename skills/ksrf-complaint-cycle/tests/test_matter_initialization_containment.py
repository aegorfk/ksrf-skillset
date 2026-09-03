from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
LIB_ROOT = SKILL / "lib"
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from ksrf.filing import matter as matter_module
from ksrf.filing.matter import MatterWorkspaceError, initialize_matter


SCRIPT = SKILL / "scripts" / "ksrf.py"
CREATED_AT = "2026-09-03T00:00:00Z"


def _snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    if not root.exists() and not root.is_symlink():
        return ((".", "absent"),)

    rows: list[tuple[object, ...]] = []

    def visit(path: Path, relative: str) -> None:
        metadata = path.lstat()
        permissions = stat.S_IMODE(metadata.st_mode)
        common = (relative, permissions, metadata.st_mtime_ns)
        if stat.S_ISLNK(metadata.st_mode):
            rows.append((*common, "symlink", os.readlink(path)))
            return
        if stat.S_ISDIR(metadata.st_mode):
            rows.append((*common, "directory"))
            for child in sorted(path.iterdir(), key=lambda item: os.fsencode(item.name)):
                child_relative = (
                    child.name if relative == "." else f"{relative}/{child.name}"
                )
                visit(child, child_relative)
            return
        if stat.S_ISREG(metadata.st_mode):
            rows.append((*common, "file", path.read_bytes()))
            return
        rows.append((*common, "special", stat.S_IFMT(metadata.st_mode)))

    visit(root, ".")
    return tuple(rows)


class MatterInitializationContainmentTests(unittest.TestCase):
    def test_rejects_symlink_on_every_artifact_lane_before_any_write(self):
        for lane in (
            "inputs",
            "inputs/objects",
            "evidence",
            "drafts",
            "release",
            "audit",
        ):
            with self.subTest(lane=lane), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                workspace = root / "matter"
                outside = root / "outside"
                workspace.mkdir()
                outside.mkdir()
                linked = workspace / lane
                linked.parent.mkdir(parents=True, exist_ok=True)
                linked.symlink_to(outside, target_is_directory=True)
                workspace_before = _snapshot(workspace)
                outside_before = _snapshot(outside)

                with self.assertRaisesRegex(
                    MatterWorkspaceError,
                    r"(символическ|предел|небезопас)",
                ):
                    initialize_matter(
                        workspace,
                        matter_identifier=f"security-{lane.replace('/', '-')}",
                        created_at=CREATED_AT,
                    )

                self.assertEqual(workspace_before, _snapshot(workspace))
                self.assertEqual(outside_before, _snapshot(outside))

    def test_rejects_symlinked_workspace_root_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outside = root / "outside"
            outside.mkdir()
            workspace = root / "matter-link"
            workspace.symlink_to(outside, target_is_directory=True)
            workspace_before = _snapshot(workspace)
            outside_before = _snapshot(outside)

            with self.assertRaisesRegex(
                MatterWorkspaceError,
                r"(символическ|небезопас)",
            ):
                initialize_matter(
                    workspace,
                    matter_identifier="security-root-link",
                    created_at=CREATED_AT,
                )

            self.assertEqual(workspace_before, _snapshot(workspace))
            self.assertEqual(outside_before, _snapshot(outside))

    def test_rejects_regular_file_as_workspace_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "matter"
            workspace.write_bytes(b"preserve\n")
            before = _snapshot(workspace)

            with self.assertRaises(MatterWorkspaceError):
                initialize_matter(
                    workspace,
                    matter_identifier="security-regular-workspace",
                    created_at=CREATED_AT,
                )

            self.assertEqual(before, _snapshot(workspace))

    def test_rejects_internal_artifact_symlink_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "matter"
            internal = workspace / "existing"
            internal.mkdir(parents=True)
            (workspace / "evidence").symlink_to(internal, target_is_directory=True)
            before = _snapshot(workspace)

            with self.assertRaisesRegex(MatterWorkspaceError, r"символическ"):
                initialize_matter(
                    workspace,
                    matter_identifier="security-internal-link",
                    created_at=CREATED_AT,
                )

            self.assertEqual(before, _snapshot(workspace))

    def test_rejects_symlinked_manifest_before_reading_its_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "matter"
            workspace.mkdir()
            outside_manifest = root / "outside-matter.json"
            outside_manifest.write_text("{}\n", encoding="utf-8")
            (workspace / "matter.json").symlink_to(outside_manifest)
            workspace_before = _snapshot(workspace)
            outside_before = _snapshot(outside_manifest)

            with mock.patch.object(
                matter_module,
                "load_json_object",
                side_effect=AssertionError("symlink target was read"),
            ) as loader:
                with self.assertRaisesRegex(MatterWorkspaceError, r"символическ"):
                    initialize_matter(
                        workspace,
                        matter_identifier="security-manifest-link",
                        created_at=CREATED_AT,
                    )

            loader.assert_not_called()
            self.assertEqual(workspace_before, _snapshot(workspace))
            self.assertEqual(outside_before, _snapshot(outside_manifest))

    def test_rejects_non_regular_manifest_without_opening_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "matter"
            manifest = workspace / "matter.json"
            manifest.mkdir(parents=True)
            before = _snapshot(workspace)

            with mock.patch.object(
                matter_module,
                "load_json_object",
                side_effect=AssertionError("non-regular manifest was opened"),
            ) as loader:
                with self.assertRaisesRegex(MatterWorkspaceError, r"обычным файлом"):
                    initialize_matter(
                        workspace,
                        matter_identifier="security-non-regular-manifest",
                        created_at=CREATED_AT,
                    )

            loader.assert_not_called()
            self.assertEqual(before, _snapshot(workspace))

    def test_rejects_dangling_manifest_symlink_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "matter"
            workspace.mkdir()
            (workspace / "matter.json").symlink_to(root / "missing-target.json")
            before = _snapshot(workspace)

            with mock.patch.object(
                matter_module,
                "load_json_object",
                side_effect=AssertionError("dangling symlink was opened"),
            ) as loader:
                with self.assertRaisesRegex(MatterWorkspaceError, r"символическ"):
                    initialize_matter(
                        workspace,
                        matter_identifier="security-dangling-manifest",
                        created_at=CREATED_AT,
                    )

            loader.assert_not_called()
            self.assertEqual(before, _snapshot(workspace))

    def test_existing_manifest_is_not_read_before_all_routes_are_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "matter"
            initialize_matter(
                workspace,
                matter_identifier="security-existing-route",
                created_at=CREATED_AT,
            )
            release = workspace / "release"
            release.rmdir()
            outside = root / "outside"
            outside.mkdir()
            release.symlink_to(outside, target_is_directory=True)
            workspace_before = _snapshot(workspace)
            outside_before = _snapshot(outside)

            with mock.patch.object(
                matter_module,
                "load_json_object",
                side_effect=AssertionError("manifest read before route preflight"),
            ) as loader:
                with self.assertRaisesRegex(MatterWorkspaceError, r"символическ"):
                    initialize_matter(
                        workspace,
                        matter_identifier="security-existing-route",
                        created_at=CREATED_AT,
                    )

            loader.assert_not_called()
            self.assertEqual(workspace_before, _snapshot(workspace))
            self.assertEqual(outside_before, _snapshot(outside))

    def test_path_inspection_error_uses_matter_error_without_writes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "matter"
            before = _snapshot(workspace)

            with mock.patch.object(
                Path,
                "lstat",
                side_effect=PermissionError("inspection denied"),
            ):
                with self.assertRaisesRegex(
                    MatterWorkspaceError,
                    r"не удалось.*провер",
                ):
                    initialize_matter(
                        workspace,
                        matter_identifier="security-inspection-error",
                        created_at=CREATED_AT,
                    )

            self.assertEqual(before, _snapshot(workspace))

    def test_every_ledger_conflict_is_detected_before_creating_anything(self):
        for key in matter_module.LEDGER_TITLES:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir) / "matter"
                conflict = workspace / matter_module.ARTIFACT_PATHS[key]
                conflict.parent.mkdir(parents=True)
                conflict.write_bytes(b'{"preserve": true}\n')
                before = _snapshot(workspace)

                with self.assertRaisesRegex(MatterWorkspaceError, r"уже существует"):
                    initialize_matter(
                        workspace,
                        matter_identifier=f"security-ledger-{key}",
                        created_at=CREATED_AT,
                    )

                self.assertEqual(before, _snapshot(workspace))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "special path test requires POSIX")
    def test_non_regular_ledger_kinds_are_rejected_before_any_write(self):
        for kind in ("directory", "dangling_symlink", "fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                workspace = root / "matter"
                conflict = (
                    workspace
                    / matter_module.ARTIFACT_PATHS["draft_evidence_map"]
                )
                conflict.parent.mkdir(parents=True)
                if kind == "directory":
                    conflict.mkdir()
                elif kind == "dangling_symlink":
                    conflict.symlink_to(root / "missing-ledger.json")
                else:
                    os.mkfifo(conflict)
                before = _snapshot(workspace)
                expected_message = (
                    r"символическ"
                    if kind == "dangling_symlink"
                    else r"уже существует"
                )

                with self.assertRaisesRegex(
                    MatterWorkspaceError,
                    expected_message,
                ):
                    initialize_matter(
                        workspace,
                        matter_identifier=f"security-ledger-{kind}",
                        created_at=CREATED_AT,
                    )

                self.assertEqual(before, _snapshot(workspace))

    def test_incompatible_directory_route_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "matter"
            workspace.mkdir()
            (workspace / "release").write_bytes(b"preserve\n")
            before = _snapshot(workspace)

            with self.assertRaises(MatterWorkspaceError):
                initialize_matter(
                    workspace,
                    matter_identifier="security-directory-conflict",
                    created_at=CREATED_AT,
                )

            self.assertEqual(before, _snapshot(workspace))

    def test_nonempty_reserved_directory_is_not_adopted_by_new_matter(self):
        for relative in (
            "inputs/registry",
            "inputs/objects/sha256",
            "release",
            "audit/events",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir) / "matter"
                reserved = workspace / relative
                reserved.mkdir(parents=True)
                (reserved / "foreign-record.json").write_bytes(b'{"foreign": true}\n')
                before = _snapshot(workspace)

                with self.assertRaisesRegex(
                    MatterWorkspaceError,
                    r"(содержит данные|не пуст)",
                ):
                    initialize_matter(
                        workspace,
                        matter_identifier=f"security-nonempty-{relative}",
                        created_at=CREATED_AT,
                    )

                self.assertEqual(before, _snapshot(workspace))

    def test_empty_reserved_directories_and_unrelated_file_remain_compatible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "matter"
            for key in (
                "input_registry",
                "input_objects",
                "release_artifacts",
                "audit_events",
            ):
                (workspace / matter_module.ARTIFACT_PATHS[key]).mkdir(
                    parents=True,
                    exist_ok=True,
                )
            note = workspace / "user-note.txt"
            note.write_bytes(b"preserve unrelated note\n")

            initialized = initialize_matter(
                workspace,
                matter_identifier="safe-precreated-directories",
                created_at=CREATED_AT,
            )

            self.assertEqual("initialized", initialized["state"])
            self.assertEqual(b"preserve unrelated note\n", note.read_bytes())

    def test_public_cli_rejects_external_symlink_without_partial_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "matter"
            outside = root / "outside"
            workspace.mkdir()
            outside.mkdir()
            (workspace / "evidence").symlink_to(outside, target_is_directory=True)
            workspace_before = _snapshot(workspace)
            outside_before = _snapshot(outside)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "matter",
                    "init",
                    "--matter-id",
                    "security-cli-link",
                    "--workspace",
                    str(workspace),
                ],
                cwd=root,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONPATH": "",
                },
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
            self.assertEqual("", completed.stdout)
            self.assertIn("Ошибка:", completed.stderr)
            self.assertEqual(workspace_before, _snapshot(workspace))
            self.assertEqual(outside_before, _snapshot(outside))

    def test_safe_initialization_and_idempotent_reopen_remain_exact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "matter"
            created = initialize_matter(
                workspace,
                matter_identifier="safe-compatible-matter",
                profile="basic",
                created_at=CREATED_AT,
            )
            before_reopen = _snapshot(workspace)

            reopened = initialize_matter(
                workspace,
                matter_identifier="safe-compatible-matter",
                profile="basic",
                created_at="2099-01-01T00:00:00Z",
            )

            self.assertEqual(created, reopened)
            self.assertEqual(before_reopen, _snapshot(workspace))


if __name__ == "__main__":
    unittest.main()
