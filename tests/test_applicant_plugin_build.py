from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import marshal
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import build_applicant_plugin as builder

spec = importlib.util.spec_from_file_location("plugin_verify", REPO / "plugin/verify.py")
verifier = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(verifier)


class PluginBuildTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "source"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "fixture"], check=True)
        (self.repo / "LICENSE").write_text("Synthetic license fixture\n")
        for name in builder.SKILL_NAMES:
            root = self.repo / "skills" / name
            root.mkdir(parents=True)
            (root / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Synthetic fixture\n---\nUse local materials.\n")
            (root / "tests").mkdir()
            (root / "tests/test_source.py").write_text("SOURCE_ONLY = True\n")
            (root / ".env").write_text("EXAMPLE=dummy-value\n")
        for name in builder.SUPPORT_FILES:
            target = self.repo / "plugin" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            content = "# Synthetic support\n" if target.suffix == ".py" else "Synthetic support\n"
            target.write_text("{}\n" if target.suffix == ".json" else content)
        (self.repo / "plugin/manifest.json").write_text(json.dumps({
            "name": builder.NAME, "version": "1.0.0", "skills": "./skills/"}))

    def test_complete_deterministic_and_runtime_only(self):
        first = builder.build(self.repo, self.base / "one")
        second = builder.build(self.repo, self.base / "two")
        self.assertEqual(first, second)
        for package in first["packages"]:
            root = self.base / "one" / package["directory"]
            result = verifier.verify(root)
            self.assertEqual(result["skills"], 16)
            self.assertFalse(result["filing_authority"])
            archive_path = self.base / "one" / package["archive"]
            self.assertEqual(sha256(archive_path.read_bytes()).hexdigest(), package["sha256"])
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertTrue(all(name.startswith("ksrf-applicant/") for name in names))
                self.assertFalse(any("/tests/" in name or name.endswith("/.env") for name in names))
                self.assertFalse(any(name.endswith(".mcp.json") for name in names))

    def test_tampering_and_unlisted_files_rejected(self):
        result = builder.build(self.repo, self.base / "out", ("web",))
        root = self.base / "out" / result["packages"][0]["directory"]
        entry = root / "LICENSE"
        original = entry.read_bytes()
        entry.write_text("changed")
        with self.assertRaisesRegex(ValueError, "Changed"):
            verifier.verify(root)
        entry.write_bytes(original)
        (root / "unexpected.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "Unlisted"):
            verifier.verify(root)

    def test_unlisted_executable_bytecode_rejected(self):
        source = self.repo / "skills/ksrf-complaint-cycle/scripts/cache_probe.py"
        source.parent.mkdir()
        source.write_text("VALUE = 'source-original'\n")
        result = builder.build(self.repo, self.base / "out", ("web",))
        root = self.base / "out" / result["packages"][0]["directory"]
        target = root / source.relative_to(self.repo)
        cache = Path(importlib.util.cache_from_source(str(target)))
        cache.parent.mkdir()
        stat = target.stat()
        replacement = compile("VALUE = 'cache-modified'\n", str(target), "exec")
        cache.write_bytes(importlib.util.MAGIC_NUMBER
                          + struct.pack("<III", 0, int(stat.st_mtime), stat.st_size)
                          + marshal.dumps(replacement))
        # Python can execute the unlisted cache while the source is unchanged.
        imported = subprocess.check_output([
            sys.executable, "-B", "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); import cache_probe; print(cache_probe.VALUE)",
            str(target.parent)], text=True).strip()
        self.assertEqual(imported, "cache-modified")
        with self.assertRaisesRegex(ValueError, "Unlisted"):
            verifier.verify(root)

    def test_windows_drive_and_alternate_stream_manifest_paths_rejected(self):
        result = builder.build(self.repo, self.base / "out", ("web",))
        root = self.base / "out" / result["packages"][0]["directory"]
        path = root / "distribution-manifest.json"
        original = json.loads(path.read_text())
        for name in ("C:outside", "C:/outside", "LICENSE:stream", "../outside", "..\\outside"):
            with self.subTest(name=name):
                manifest = json.loads(json.dumps(original))
                manifest["files"][0]["path"] = name
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, "Invalid"):
                    verifier.verify(root)

    def test_unsafe_source_does_not_create_output(self):
        root = self.repo / "skills" / builder.SKILL_NAMES[0]
        (root / "outside").symlink_to(self.base)
        with self.assertRaises((ValueError, builder.FileContractError)):
            builder.build(self.repo, self.base / "out")
        self.assertFalse((self.base / "out").exists())

    def test_missing_dependency_rejected(self):
        (self.repo / "skills/constitutional-comparative-research/SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "Missing skill"):
            builder.build(self.repo, self.base / "out")

    def test_dirty_release_and_unsafe_outputs_rejected(self):
        with self.assertRaisesRegex(ValueError, "clean published"):
            builder.build(self.repo, self.base / "out", require_clean=True)
        for target in [self.repo, self.repo / "build", Path.home(), self.base]:
            with self.assertRaises(ValueError):
                builder.build(self.repo, target)

    def test_linked_parent_and_encoded_secret_rejected(self):
        (self.base / "linked").symlink_to(self.base)
        with self.assertRaisesRegex(ValueError, "Symlinked output"):
            builder.build(self.repo, self.base / "linked/out")
        (self.repo / "plugin/PRIVACY.md").write_text("sk" + "-" + "a" * 35)
        with self.assertRaisesRegex(ValueError, "credential"):
            builder.build(self.repo, self.base / "out")

    def test_generic_literal_credential_rejected_before_build_output(self):
        source = self.repo / "skills/ksrf-complaint-cycle/scripts/credential_probe.py"
        source.parent.mkdir()
        # Synthetic value only: do not print it or use a real credential.
        value = "qX83" + "rT57" + "mP24" + "vN61"
        source.write_text("api_key = " + repr(value) + "\n")
        with self.assertRaisesRegex(ValueError, "credential"):
            builder.build(self.repo, self.base / "out")
        self.assertFalse((self.base / "out").exists())

    def test_literal_secret_forms_and_safe_references(self):
        value = "qX83" + "rT57" + "mP24" + "vN61"
        rejected = [
            (".py", "self.api_key = " + repr(value)),
            (".py", "ACCESS_TOKEN: str = " + repr(value)),
            (".py", "config = {'nested': {'apiKey': " + repr(value) + "}}"),
            (".py", "config['password'] = " + repr(value)),
            (".json", json.dumps({"nested": [{"clientSecret": value}]})),
            (".yaml", "api_key: " + value),
            (".yaml", "  - access_token: '" + value + "'"),
            (".md", '```python\napi_key = "' + value + '"\n```'),
        ]
        for index, (suffix, content) in enumerate(rejected):
            with self.subTest(rejected=index):
                source = self.base / ("literal" + suffix)
                source.write_text(content)
                with self.assertRaisesRegex(ValueError, "credential"):
                    builder.read_safe(source)
        accepted = [
            (".py", "import os\napi_key = os.environ['API_KEY']\n"),
            (".py", "import os\napi_key = os.getenv('API_KEY')\n"),
            (".py", "api_key = '<your-api-key>'\n"),
            (".py", "config = {'apiKey': '${API_KEY}'}\n"),
            (".json", json.dumps({"api_key": "REPLACE_ME", "secret": "<your-secret>"})),
            (".yaml", "api_key: ${API_KEY}"),
            (".yaml", "access_token: placeholder-token"),
            (".md", "api_key = os.environ.get('API_KEY')"),
        ]
        for index, (suffix, content) in enumerate(accepted):
            with self.subTest(accepted=index):
                source = self.base / ("reference" + suffix)
                source.write_text(content)
                self.assertEqual(builder.read_safe(source), content.encode())

    def test_runtime_requires_real_host_capabilities(self):
        result = builder.build(self.repo, self.base / "out")
        for pkg in result["packages"]:
            surface = json.loads((self.base / "out" / pkg["directory"] / "surface.json").read_text())
            self.assertIsNone(surface["hosted_endpoint"])
            self.assertFalse(surface["accounts_included"])
            self.assertEqual(surface["runtime"], "requires_host_execution")


if __name__ == "__main__":
    unittest.main()
