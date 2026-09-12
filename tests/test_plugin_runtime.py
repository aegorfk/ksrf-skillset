from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills/ksrf-complaint-cycle/scripts/plugin_runtime.py"
SPEC = importlib.util.spec_from_file_location("plugin_runtime", SCRIPT)
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class PluginRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        # macOS /var is a system symlink; use the actual test location.
        self.root = Path(self.temporary.name).resolve()
        self.state = self.root / "state"

    def test_requirements_are_complete_unique_exact_versions(self):
        pins = runtime.requirement_pins()
        self.assertEqual(set(pins), set(runtime.MODULES))
        self.assertEqual(len(pins), 11)
        self.assertEqual(len(runtime.requirements_hash()), 64)

    def test_state_rejects_broad_relative_and_package_paths_before_writes(self):
        for target in (".", "/", Path.home(), Path.home() / "Documents", SCRIPT.parent,
                       runtime.PACKAGE_ROOT, self.root / ".." / "other"):
            with self.subTest(target=target), self.assertRaises(runtime.RuntimeSetupError):
                runtime.validate_state_dir(target)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_state_rejects_symlink_parent_and_final_symlink(self):
        source = self.root / "real"
        source.mkdir(mode=0o700)
        linked = self.root / "linked"
        linked.symlink_to(source, target_is_directory=True)
        for target in (linked, linked / "state"):
            with self.subTest(target=target), self.assertRaises(runtime.RuntimeSetupError):
                runtime.validate_state_dir(target)
        self.assertEqual(list(source.iterdir()), [])

    def test_unmarked_foreign_directory_and_public_modes_are_preserved(self):
        self.state.mkdir(mode=0o700)
        original = self.state / "private-document.txt"
        original.write_text("untouched")
        with self.assertRaises(runtime.RuntimeSetupError):
            with runtime._setup_lock(self.state):
                self.fail("foreign directory accepted")
        self.assertEqual(original.read_text(), "untouched")
        original.unlink()
        if hasattr(os, "geteuid"):
            self.state.chmod(0o755)
            with self.assertRaises(runtime.RuntimeSetupError):
                runtime._check_state(self.state)

    def test_service_keys_approval_python_and_pip_environment_are_not_forwarded(self):
        env = runtime.child_environment({
            "HOME": str(self.root), "PATH": os.pathsep.join([".", "/usr/bin", "relative"]),
            "PYTHONPATH": "/foreign", "PYTHONHOME": "/foreign",
            "KSRF_SKILLS_ROOT": "/author/skills", "KSRF_TRUSTED_APPROVAL_VERIFIER_ID": "forged",
            "KSRF_AUTHENTICATED_REVIEW_CHANNEL": "forged", "CASUS_API_KEY": "secret",
            "OPENAI_API_KEY": "secret", "PIP_INDEX_URL": "https://secret:token@example.invalid",
            "PIP_CONFIG_FILE": "/foreign/config", "VIRTUAL_ENV": "/foreign",
        })
        self.assertEqual(env["KSRF_SKILLS_ROOT"], str(runtime.SKILLS_ROOT))
        self.assertEqual(env["PIP_CONFIG_FILE"], os.devnull)
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
        for key in ("PYTHONPATH", "PYTHONHOME", "KSRF_TRUSTED_APPROVAL_VERIFIER_ID",
                    "KSRF_AUTHENTICATED_REVIEW_CHANNEL", "CASUS_API_KEY", "OPENAI_API_KEY",
                    "PIP_INDEX_URL", "VIRTUAL_ENV"):
            self.assertNotIn(key, env)
        self.assertTrue(all(Path(p).is_absolute() for p in env["PATH"].split(os.pathsep)))

    def test_default_state_override_is_explicit_and_empty_is_rejected(self):
        self.assertEqual(runtime.default_state_dir({"KSRF_PLUGIN_STATE_DIR": str(self.state)}), self.state)
        with self.assertRaises(runtime.RuntimeSetupError):
            runtime.default_state_dir({"KSRF_PLUGIN_STATE_DIR": ""})

    def _probe(self, missing=()):
        return {"python": [3, 13, 0], "packages": {
            name: {"state": "unavailable" if name in missing else "ready", "version": version}
            for name, version in runtime.requirement_pins().items()}}

    def test_operation_doctor_does_not_confuse_pypdf_mutool_or_ocr_with_working_tools(self):
        with patch.object(runtime, "_module_probe", return_value=self._probe()), \
             patch.object(runtime, "_tool_probe", return_value={"state": "unavailable"}), \
             patch.object(runtime.shutil, "which", return_value=None):
            report = runtime.diagnose(self.state)
        operations = report["operations"]
        self.assertEqual(operations["case_workspace"]["state"], "ready")
        self.assertEqual(operations["text_docx_collection"]["state"], "ready")
        self.assertEqual(operations["pdf_text_collection"]["missing"], ["pdftotext"])
        self.assertEqual(operations["working_document_export"]["missing"], ["soffice", "pdftoppm"])
        self.assertIn("rus", operations["pdf_ocr"]["missing"])
        self.assertFalse(self.state.exists())
        self.assertEqual(report["state"], "degraded")
        self.assertFalse(report["filing_authority"])

    def test_ocr_probe_requires_russian_and_english_data(self):
        process = subprocess.CompletedProcess([], 0, stdout="List of available languages (1):\neng\n", stderr="")
        with patch.object(runtime, "_module_probe", return_value=self._probe()), \
             patch.object(runtime, "_tool_probe", return_value={"state": "ready"}), \
             patch.object(runtime.shutil, "which", return_value="/usr/bin/tesseract"), \
             patch.object(runtime.subprocess, "run", return_value=process):
            report = runtime.diagnose(self.state)
        self.assertEqual(report["operations"]["image_ocr"]["missing"], ["rus"])
        self.assertEqual(report["operations"]["working_document_export"]["state"], "ready")

    def test_lock_is_exclusive_and_stale_lock_is_not_deleted(self):
        with runtime._setup_lock(self.state):
            self.assertEqual(runtime._read_record(self.state / runtime.STATE_MARKER), {"format": runtime.STATE_FORMAT})
            with self.assertRaises(runtime.RuntimeSetupError):
                with runtime._setup_lock(self.state):
                    self.fail("parallel setup accepted")
        lock = self.state / ".setup.lock"
        self.assertFalse(lock.exists())
        lock.write_text("keep")
        with self.assertRaises(runtime.RuntimeSetupError):
            with runtime._setup_lock(self.state):
                pass
        self.assertEqual(lock.read_text(), "keep")

    def test_managed_pointer_cannot_escape_or_follow_symlink(self):
        with runtime._setup_lock(self.state):
            runtime._write_record(self.state, runtime.ACTIVE_FILE, {
                "format": runtime.STATE_FORMAT, "requirements_sha256": runtime.requirements_hash(),
                "environment": "../../foreign"})
        with self.assertRaises(runtime.RuntimeSetupError):
            runtime.managed_python(self.state)
        active = self.state / runtime.ACTIVE_FILE
        active.unlink()
        foreign = self.root / "foreign.json"
        foreign.write_text("{}")
        active.symlink_to(foreign)
        with self.assertRaises(runtime.RuntimeSetupError):
            runtime.managed_python(self.state)

    def test_hardlinked_marker_is_rejected(self):
        with runtime._setup_lock(self.state):
            pass
        os.link(self.state / runtime.STATE_MARKER, self.root / "shared-marker")
        with self.assertRaises(runtime.RuntimeSetupError):
            runtime._check_state(self.state)

    def test_pass_through_preserves_argument_boundaries_and_child_exit(self):
        arguments = ["--", "matter", "init", "--matter-id", "test", "--workspace", str(self.root / "with spaces; $data")]
        process = subprocess.CompletedProcess([], 3)
        with patch.object(runtime.subprocess, "run", return_value=process) as run:
            result = runtime.delegate(self.state, "run", arguments)
        self.assertEqual(result, 3)
        command = run.call_args.args[0]
        self.assertEqual(command[1:3], ["-I", "-B"])
        self.assertEqual(command[4:], arguments[1:])
        self.assertEqual(run.call_args.kwargs["env"]["KSRF_SKILLS_ROOT"], str(runtime.SKILLS_ROOT))
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertFalse(self.state.exists())

    def test_setup_uses_new_isolated_environment_pins_and_no_system_install(self):
        calls = []

        def fake_step(command, state, env, label):
            calls.append((command, env))
            if "venv" in command:
                destination = Path(command[-1])
                bin_dir = destination / ("Scripts" if sys.platform == "win32" else "bin")
                bin_dir.mkdir()
                (bin_dir / ("python.exe" if sys.platform == "win32" else "python")).write_text("fake")
                (destination / "pyvenv.cfg").write_text("include-system-site-packages = false\n")

        with patch.object(runtime, "_run_setup_step", side_effect=fake_step), \
             patch.object(runtime, "_module_probe", return_value=self._probe()):
            result = runtime.setup_documents(self.state)
        self.assertEqual(result["state"], "documents_ready")
        managed = runtime.managed_python(self.state)
        self.assertIsNotNone(managed)
        self.assertTrue(managed.is_relative_to(self.state))
        self.assertIn("--copies", calls[0][0])
        install = calls[1][0]
        for flag in ("--no-deps", "--only-binary=:all:", "--no-input", "--no-cache-dir"):
            self.assertIn(flag, install)
        self.assertEqual(install[0], str(managed))
        self.assertNotIn("--user", install)
        self.assertEqual(calls[1][1]["PIP_CONFIG_FILE"], os.devnull)
        self.assertFalse((self.state / ".setup.lock").exists())
        with patch.object(runtime, "_module_probe", return_value=self._probe()), \
             patch.object(runtime, "_run_setup_step") as repeat:
            reused = runtime.setup_documents(self.state)
        self.assertEqual(reused["state"], "already_ready")
        repeat.assert_not_called()

    def test_failed_setup_preserves_previous_active_environment(self):
        with runtime._setup_lock(self.state):
            runtime._write_record(self.state, runtime.ACTIVE_FILE, {"format": runtime.STATE_FORMAT,
                "environment": "old", "requirements_sha256": "0" * 64})
        previous = (self.state / runtime.ACTIVE_FILE).read_bytes()
        with patch.object(runtime, "_run_setup_step", side_effect=runtime.RuntimeSetupError("network unavailable")):
            with self.assertRaises(runtime.RuntimeSetupError):
                runtime.setup_documents(self.state)
        self.assertEqual((self.state / runtime.ACTIVE_FILE).read_bytes(), previous)
        self.assertFalse((self.state / ".setup.lock").exists())
        self.assertTrue(list((self.state / "environments").iterdir()))

    def test_clean_interpreter_help_start_and_text_collection(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(self.root / "poison"),
                   KSRF_SKILLS_ROOT="/author/stale", KSRF_TRUSTED_APPROVAL_VERIFIER_ID="forged")
        base = [sys.executable, "-I", "-B", str(SCRIPT), "--state-dir", str(self.state)]
        help_result = subprocess.run([*base, "--help"], env=env, capture_output=True, text=True, check=True)
        self.assertIn("Использование:", help_result.stdout)
        start = subprocess.run([*base, "run", "--", "start", "--json"], env=env,
                               capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(start.stdout)["state"], "skills_only")
        document = self.root / "synthetic.txt"
        document.write_text("Синтетический пример для технической проверки. Содержание не является реальным делом.", encoding="utf-8")
        collected = subprocess.run([*base, "collect", "--", str(document), "--no-ocr"], env=env,
                                   capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(collected.stdout)["document_count"], 1)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
