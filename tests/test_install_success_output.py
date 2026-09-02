from __future__ import annotations

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
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


class InstallSuccessOutputTests(unittest.TestCase):
    def _checkout(
        self,
        root: Path,
        *,
        guard_source: str,
        installer_source: str,
    ) -> Path:
        checkout = root / "checkout"
        checkout.mkdir()
        shutil.copy2(REPO / "install.sh", checkout / "install.sh")
        tools = checkout / "tools"
        tools.mkdir()
        (tools / "verify_publication_state.py").write_text(
            textwrap.dedent(guard_source),
            encoding="utf-8",
        )
        (tools / "install_skillset.py").write_text(
            textwrap.dedent(installer_source),
            encoding="utf-8",
        )
        return checkout

    def test_real_installer_success_renderer_is_concise_russian(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "skills"
            stdout = io.StringIO()
            with patch.object(installer, "copy_skillset", return_value=target):
                with redirect_stdout(stdout):
                    exit_code = installer.main(
                        [
                            "--source-skills-root",
                            str(root / "source"),
                            "--target",
                            str(target),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                stdout.getvalue(),
                f"Точный состав навыков КС РФ из манифеста установлен в {target}\n",
            )
            self.assertNotIn("runtime", stdout.getvalue().lower())
            self.assertNotIn("sha", stdout.getvalue().lower())

    def test_canonical_success_hides_nested_maintainer_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_home = root / "home"
            fake_home.mkdir()
            checkout = self._checkout(
                root,
                guard_source="""
                    print(
                        "Verified published KSRF skillset: aegorfk/ksrf-skillset "
                        "live_sha=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa "
                        "manifest_tree_sha256=tree-secret "
                        "release_tree_sha256=release-secret "
                        "remote_base_commit=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                    )
                """,
                installer_source="""
                    from pathlib import Path
                    import sys

                    target = Path(sys.argv[sys.argv.index("--target") + 1])
                    print(f"Навыки КС РФ установлены в {target}")
                """,
            )

            completed = subprocess.run(
                [str(checkout / "install.sh")],
                cwd=checkout,
                env={
                    **os.environ,
                    "HOME": str(fake_home),
                    "CODEX_HOME": str(fake_home / ".codex"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertIn("Навыки КС РФ установлены", completed.stdout)
            self.assertIn("export KSRF_SKILLS_ROOT=", completed.stdout)
            self.assertEqual(len(completed.stdout.splitlines()), 2)
            for maintainer_fragment in (
                "Verified published KSRF skillset",
                "aegorfk/ksrf-skillset",
                "live_sha=",
                "manifest_tree_sha256=",
                "release_tree_sha256=",
                "remote_base_commit=",
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "tree-secret",
                "release-secret",
            ):
                with self.subTest(fragment=maintainer_fragment):
                    self.assertNotIn(maintainer_fragment, completed.stdout)

    def test_publication_refusal_stops_before_writer_and_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_home = root / "home"
            fake_home.mkdir()
            writer_marker = root / "writer-called"
            checkout = self._checkout(
                root,
                guard_source="""
                    import sys

                    print("Publication guard refused: fixture", file=sys.stderr)
                    raise SystemExit(7)
                """,
                installer_source="""
                    import os
                    from pathlib import Path

                    Path(os.environ["WRITER_MARKER"]).write_text("called", encoding="utf-8")
                    print("Навыки КС РФ установлены")
                """,
            )

            completed = subprocess.run(
                [str(checkout / "install.sh")],
                cwd=checkout,
                env={
                    **os.environ,
                    "HOME": str(fake_home),
                    "CODEX_HOME": str(fake_home / ".codex"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "WRITER_MARKER": str(writer_marker),
                },
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 7)
            self.assertEqual(completed.stdout, "")
            self.assertIn("Publication guard refused: fixture", completed.stderr)
            self.assertFalse(writer_marker.exists())
            self.assertNotIn("Навыки КС РФ установлены", completed.stdout)
            self.assertNotIn("export KSRF_SKILLS_ROOT=", completed.stdout)


if __name__ == "__main__":
    unittest.main()
