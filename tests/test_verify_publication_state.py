from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import verify_publication_state as guard  # noqa: E402
from generate_skills_manifest import _validate_base_commit  # noqa: E402
from generate_skills_manifest import build_manifest  # noqa: E402
from skillset_file_contract import RELEASE_FILE_PATHS, SKILL_NAMES  # noqa: E402


SHA = "a" * 40
OTHER_SHA = "b" * 40
BASE_SHA = "c" * 40


class PublicationGuardTests(unittest.TestCase):
    def test_direct_human_and_json_output_keep_maintainer_evidence(self) -> None:
        result = {
            "repository": "aegorfk/ksrf-skillset",
            "local_sha": SHA,
            "live_sha": SHA,
            "manifest_tree_sha256": "tree-sha",
            "release_tree_sha256": "release-tree-sha",
            "remote_base_commit": BASE_SHA,
        }
        for extra_args, expected in (
            (
                [],
                (
                    "Verified published KSRF skillset: aegorfk/ksrf-skillset "
                    f"live_sha={SHA} manifest_tree_sha256=tree-sha "
                    "release_tree_sha256=release-tree-sha "
                    f"remote_base_commit={BASE_SHA}\n"
                ),
            ),
            (["--json"], json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"),
        ):
            with self.subTest(extra_args=extra_args), patch.object(
                guard,
                "verify_publication_state",
                return_value=result,
            ):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = guard.main(["--repo", ".", *extra_args])
                self.assertEqual(exit_code, 0)
                self.assertEqual(stdout.getvalue(), expected)

    def test_accepts_expected_github_remote_forms(self) -> None:
        self.assertEqual(
            guard._github_repository("git@github.com:aegorfk/ksrf-skillset.git"),
            guard.EXPECTED_REPOSITORY,
        )
        self.assertEqual(
            guard._github_repository("https://github.com/aegorfk/ksrf-skillset.git"),
            guard.EXPECTED_REPOSITORY,
        )
        self.assertEqual(
            guard._github_repository("ssh://git@github.com/aegorfk/ksrf-skillset.git"),
            guard.EXPECTED_REPOSITORY,
        )
        self.assertIsNone(guard._github_repository("https://example.com/aegorfk/ksrf-skillset"))

    def test_accepts_clean_checkout_at_live_main(self) -> None:
        with tempfile.TemporaryDirectory() as raw_repo:
            repo = Path(raw_repo).resolve()

            def fake_git(_repo: Path, *args: str) -> str:
                commands = {
                    ("rev-parse", "--show-toplevel"): str(repo),
                    ("remote", "get-url", "origin"): "git@github.com:aegorfk/ksrf-skillset.git",
                    ("status", "--porcelain", "--untracked-files=all"): "",
                    ("rev-parse", "HEAD"): SHA,
                    ("ls-remote", "origin", "refs/heads/main"): f"{SHA}\trefs/heads/main",
                    ("cat-file", "-e", f"{BASE_SHA}^{{commit}}"): "",
                    ("rev-parse", "HEAD^"): BASE_SHA,
                }
                return commands[args]

            with patch.object(guard, "_run_git", side_effect=fake_git), patch.object(
                guard,
                "verify_manifest",
                return_value={
                    "tree_sha256": "tree-sha",
                    "release_tree_sha256": "release-tree-sha",
                    "remote_base_commit": BASE_SHA,
                },
            ):
                result = guard.verify_publication_state(repo)
            self.assertEqual(result["live_sha"], SHA)
            self.assertEqual(result["manifest_tree_sha256"], "tree-sha")
            self.assertEqual(result["release_tree_sha256"], "release-tree-sha")

    def test_refuses_dirty_checkout_before_live_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as raw_repo:
            repo = Path(raw_repo).resolve()

            def fake_git(_repo: Path, *args: str) -> str:
                commands = {
                    ("rev-parse", "--show-toplevel"): str(repo),
                    ("remote", "get-url", "origin"): "git@github.com:aegorfk/ksrf-skillset.git",
                    ("status", "--porcelain", "--untracked-files=all"): " M README.md",
                }
                return commands[args]

            with patch.object(guard, "_run_git", side_effect=fake_git):
                with self.assertRaisesRegex(guard.PublicationStateError, "checkout is dirty"):
                    guard.verify_publication_state(repo)

    def test_refuses_stale_or_unpublished_head(self) -> None:
        with tempfile.TemporaryDirectory() as raw_repo:
            repo = Path(raw_repo).resolve()

            def fake_git(_repo: Path, *args: str) -> str:
                commands = {
                    ("rev-parse", "--show-toplevel"): str(repo),
                    ("remote", "get-url", "origin"): "git@github.com:aegorfk/ksrf-skillset.git",
                    ("status", "--porcelain", "--untracked-files=all"): "",
                    ("rev-parse", "HEAD"): SHA,
                    ("ls-remote", "origin", "refs/heads/main"): f"{OTHER_SHA}\trefs/heads/main",
                }
                return commands[args]

            with patch.object(guard, "_run_git", side_effect=fake_git):
                with self.assertRaisesRegex(guard.PublicationStateError, "stale or unpublished"):
                    guard.verify_publication_state(repo)

    def test_current_versioned_manifest_matches_skill_tree(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        result = guard.verify_manifest(repo)
        self.assertRegex(result["tree_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["release_tree_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(result["remote_base_commit"], r"^[0-9a-f]{40}$")
        manifest = json.loads((repo / "skills-manifest.json").read_text(encoding="utf-8"))
        covered = {row["path"] for row in manifest["release_files"]}
        self.assertIn("install.sh", covered)
        self.assertIn("tools/sync_global_skills.sh", covered)
        self.assertIn("tools/verify_publication_state.py", covered)
        self.assertIn("tools/install_skillset.py", covered)

    def test_rejects_malformed_manifest_base_sha(self) -> None:
        with self.assertRaisesRegex(SystemExit, "full lowercase 40-hex"):
            _validate_base_commit("08a6317")
        with self.assertRaisesRegex(SystemExit, "full lowercase 40-hex"):
            _validate_base_commit("A" * 40)

    def test_refuses_manifest_base_that_is_not_release_first_parent(self) -> None:
        with tempfile.TemporaryDirectory() as raw_repo:
            repo = Path(raw_repo).resolve()

            def fake_git(_repo: Path, *args: str) -> str:
                commands = {
                    ("rev-parse", "--show-toplevel"): str(repo),
                    ("remote", "get-url", "origin"): "git@github.com:aegorfk/ksrf-skillset.git",
                    ("status", "--porcelain", "--untracked-files=all"): "",
                    ("rev-parse", "HEAD"): SHA,
                    ("ls-remote", "origin", "refs/heads/main"): f"{SHA}\trefs/heads/main",
                    ("cat-file", "-e", f"{BASE_SHA}^{{commit}}"): "",
                    ("rev-parse", "HEAD^"): OTHER_SHA,
                }
                return commands[args]

            manifest = {
                "tree_sha256": "tree-sha",
                "release_tree_sha256": "release-tree-sha",
                "remote_base_commit": BASE_SHA,
            }
            with patch.object(guard, "_run_git", side_effect=fake_git), patch.object(
                guard, "verify_manifest", return_value=manifest
            ):
                with self.assertRaisesRegex(guard.PublicationStateError, "must equal.*first parent"):
                    guard.verify_publication_state(repo)

    def test_generator_and_manifest_verifier_refuse_nested_source_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            for name in SKILL_NAMES:
                skill = repo / "skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
            for relative_name in RELEASE_FILE_PATHS:
                release_file = repo / relative_name
                release_file.parent.mkdir(parents=True, exist_ok=True)
                release_file.write_text(f"fixture: {relative_name}\n", encoding="utf-8")

            recorded = build_manifest(repo, BASE_SHA)
            (repo / "skills-manifest.json").write_text(
                json.dumps(recorded, ensure_ascii=False), encoding="utf-8"
            )
            external_secret = repo / "external-secret.txt"
            external_secret.write_text("must-not-be-read\n", encoding="utf-8")
            leak = repo / "skills" / SKILL_NAMES[0] / "leak.txt"
            leak.symlink_to(external_secret)

            with self.assertRaisesRegex(SystemExit, "symlink inside payload tree"):
                build_manifest(repo, BASE_SHA)
            with self.assertRaisesRegex(
                guard.PublicationStateError, "symlink inside payload tree"
            ):
                guard.verify_manifest(repo)


if __name__ == "__main__":
    unittest.main()
