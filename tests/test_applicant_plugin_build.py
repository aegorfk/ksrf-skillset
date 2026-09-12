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

SAFE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">'
    '<rect x="32" y="32" width="448" height="448" rx="40" fill="#244A62"/>'
    '<path d="M 160 256 L 224 320 L 352 192" fill="none" stroke="#ffffff" stroke-width="24"/>'
    '</svg>\n'
)

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
            target.write_text(SAFE_SVG if target.suffix == ".svg" else "{}\n" if target.suffix == ".json" else content)
        (self.repo / "plugin/manifest.json").write_text(json.dumps({
            "name": builder.NAME, "version": "1.0.1", "skills": "./skills/",
            "interface": {"displayName": "Synthetic applicant", "shortDescription": "Review a working draft",
                          "longDescription": "Synthetic directory metadata for package tests.",
                          "developerName": "Synthetic test publisher", "category": "Productivity",
                          "defaultPrompt": ["Review my synthetic draft."],
                          "logo": builder.BRANDING_ASSET, "composerIcon": builder.BRANDING_ASSET}}))

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
                self.assertIn("ksrf-applicant/assets/applicant.svg", names)
                self.assertIn("ksrf-applicant/plugin/SUPPORT.md", names)
                self.assertIn("ksrf-applicant/plugin/TERMS.md", names)
            self.assertEqual((root / "assets/applicant.svg").read_text(), SAFE_SVG)

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

    def test_listing_limits_and_single_line_fields_before_output(self):
        path = self.repo / "plugin/manifest.json"
        original = json.loads(path.read_text())
        changes = [("displayName", "a" * 31), ("shortDescription", "a" * 31),
                   ("longDescription", "a" * 4001), ("developerName", "a" * 81),
                   ("displayName", "first\nsecond"), ("shortDescription", "first\u2028second"),
                   ("developerName", "first\tsecond"), ("longDescription", ""),
                   ("displayName", None)]
        for field, value in changes:
            with self.subTest(field=field, value_type=type(value).__name__):
                metadata = json.loads(json.dumps(original))
                metadata["interface"][field] = value
                path.write_text(json.dumps(metadata))
                with self.assertRaises(ValueError):
                    builder.build(self.repo, self.base / "bad-listing")
                self.assertFalse((self.base / "bad-listing").exists())
        boundary = json.loads(json.dumps(original))
        boundary["interface"].update({"displayName": "x" * 30, "shortDescription": "x" * 30,
                                      "longDescription": "x" * 4000, "developerName": "x" * 80})
        builder.validate_listing(boundary)

    def test_prompt_limits_normalization_and_mentions(self):
        metadata = json.loads((self.repo / "plugin/manifest.json").read_text())
        invalid = [["x" * 129], ["a", "b", "c", "d"], [" "] , ["same text", "same\u00a0text"],
                   ["Café", "Cafe\u0301"], ["\u00a8prompt", "\u0308prompt"],
                   ["use @remote"], ["first\nsecond"], [None], {"prompt": "value"}]
        for prompts in invalid:
            with self.subTest(prompts_type=type(prompts).__name__):
                metadata["interface"]["defaultPrompt"] = prompts
                with self.assertRaises(ValueError):
                    builder.validate_listing(metadata)
        metadata["interface"]["defaultPrompt"] = ["x" * 128, "Different prompt", "Third prompt"]
        builder.validate_listing(metadata)
        metadata["interface"]["defaultPrompt"] = "One supported prompt"
        builder.validate_listing(metadata)

    def test_branding_paths_cannot_escape_or_select_other_files(self):
        path = self.repo / "plugin/manifest.json"
        original = json.loads(path.read_text())
        for field in ("logo", "composerIcon"):
            for bad in ("../outside.svg", "/absolute.svg", "https://example.invalid/icon.svg",
                        "./assets/../applicant.svg", "./assets/other.svg", None):
                with self.subTest(field=field, bad=bad):
                    metadata = json.loads(json.dumps(original))
                    metadata["interface"][field] = bad
                    path.write_text(json.dumps(metadata))
                    with self.assertRaisesRegex(ValueError, "must reference"):
                        builder.build(self.repo, self.base / "bad-branding")
                    self.assertFalse((self.base / "bad-branding").exists())

    def test_svg_dimensions_xml_and_encoding(self):
        invalid = [
            SAFE_SVG.replace('height="512"', 'height="256"'),
            SAFE_SVG.replace('width="512"', 'width="47"').replace('height="512"', 'height="47"'),
            SAFE_SVG.replace('width="512"', 'width="512px"'),
            SAFE_SVG.replace('width="512"', 'width="1e999"'),
            SAFE_SVG.replace('viewBox="0 0 512 512"', 'viewBox="0 0 512 256"'),
            SAFE_SVG.replace('viewBox="0 0 512 512"', 'viewBox="0 0 512"'),
            SAFE_SVG.replace('width="512" height="512" viewBox="0 0 512 512"', ''),
            SAFE_SVG.replace('</svg>', ''),
        ]
        for value in invalid:
            with self.subTest(value=value[:80]), self.assertRaises(ValueError):
                builder.validate_branding_svg(value.encode())
        with self.assertRaises(UnicodeDecodeError):
            builder.validate_branding_svg(b"\xff")
        builder.validate_branding_svg(SAFE_SVG.encode())
        builder.validate_branding_svg(SAFE_SVG.replace('width="512" height="512" ', '').encode())

    def test_active_svg_and_resource_references_rejected_before_output(self):
        path = self.repo / "plugin/assets/applicant.svg"
        invalid = [
            SAFE_SVG.replace('</svg>', '<script>alert(1)</script></svg>'),
            SAFE_SVG.replace('width="512"', 'onload="alert(1)" width="512"', 1),
            SAFE_SVG.replace('</svg>', '<foreignObject width="100" height="100"/></svg>'),
            SAFE_SVG.replace('</svg>', '<image href="https://example.invalid/image.png"/></svg>'),
            SAFE_SVG.replace('</svg>', '<use href="#shape"/></svg>'),
            SAFE_SVG.replace('fill="#244A62"', 'fill="url(https://example.invalid/image.svg)"'),
            SAFE_SVG.replace('fill="#244A62"', 'style="fill: #244A62"'),
            SAFE_SVG.replace('stroke-width="24"', 'unknown="value"'),
            '<!DOCTYPE svg [<!ENTITY x "unsafe">]>' + SAFE_SVG,
            '<?xml-stylesheet href="https://example.invalid/style.css"?>' + SAFE_SVG,
        ]
        for index, content in enumerate(invalid):
            with self.subTest(index=index):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    builder.build(self.repo, self.base / "unsafe-svg")
                self.assertFalse((self.base / "unsafe-svg").exists())

    def test_branding_still_uses_private_content_guard(self):
        path = self.repo / "plugin/assets/applicant.svg"
        path.write_text(SAFE_SVG.replace('</svg>', '<desc>' + 'sk' + '-' + 'a' * 35 + '</desc></svg>'))
        with self.assertRaisesRegex(ValueError, "credential"):
            builder.build(self.repo, self.base / "private-svg")
        self.assertFalse((self.base / "private-svg").exists())


if __name__ == "__main__":
    unittest.main()
