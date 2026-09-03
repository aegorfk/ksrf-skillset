from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SCRIPT_RELATIVE = Path(
    "ksrf-explore-arguments/scripts/validate_argument_research.py"
)

VALID_ARTIFACT = {
    "case_id": "CASE-TOTALITY",
    "findings": [
        {
            "finding_id": "finding-1",
            "case_id": "CASE-TOTALITY",
            "direction": "supporting",
            "thesis": "Проверяемый тезис.",
            "source_anchor": "source-1",
            "locator": "p. 1",
            "relation": "supports",
            "hypothesis_ids": ["hypothesis-1"],
            "verification_status": "verified",
            "confidence": "high",
            "limitations": [],
            "contains_sensitive_data": False,
        }
    ],
    "hypotheses": [
        {
            "hypothesis_id": "hypothesis-1",
            "title": "Проверяемая гипотеза",
            "status": "active",
            "normative_mechanism": "Механизм применения нормы.",
            "constitutional_harm": "Конституционно значимое последствие.",
            "review_line": "Линия проверки.",
            "supporting_finding_ids": ["finding-1"],
            "adverse_finding_ids": [],
            "falsifier": "Опровергающий материал.",
            "fact_dispute_risk": "low",
            "refusal_model": "Модель возможного отказа.",
            "primary_relief": "Основной способ защиты.",
            "narrower_relief": "Более узкий способ защиты.",
            "missing_materials": [],
        }
    ],
    "portfolio": {
        "human_approval": "pending",
        "principal_hypothesis_id": None,
        "reserve_hypothesis_ids": [],
        "experimental_hypothesis_ids": [],
        "rejected_hypothesis_ids": [],
    },
}


def _fresh_artifact() -> dict[str, object]:
    return json.loads(json.dumps(VALID_ARTIFACT, ensure_ascii=False))


def _load_validator(script: Path):
    spec = importlib.util.spec_from_file_location(
        "argument_research_validator_totality",
        script,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


class ArgumentResearchValidatorTotalityTests(unittest.TestCase):
    def test_validate_is_total_for_every_unsafe_json_field_family(self) -> None:
        validate = _load_validator(REPO / "skills" / SCRIPT_RELATIVE)

        for value in (None, True, 7, 1.5, "text", []):
            with self.subTest(kind="root", value=value):
                self.assertEqual(validate(value), ["root must be an object"])

        enum_targets = (
            ("findings", "relation"),
            ("findings", "verification_status"),
            ("findings", "confidence"),
            ("hypotheses", "status"),
            ("portfolio", "human_approval"),
        )
        wrong_enum_values = (None, True, 7, 1.5, [], {})
        for section, field in enum_targets:
            for value in wrong_enum_values:
                with self.subTest(kind="enum", section=section, field=field, value=value):
                    payload = _fresh_artifact()
                    holder = payload[section]
                    if isinstance(holder, list):
                        holder[0][field] = value
                    else:
                        holder[field] = value
                    self._assert_total(validate, payload)

        reference_targets = (
            ("hypotheses", "supporting_finding_ids"),
            ("hypotheses", "adverse_finding_ids"),
            ("portfolio", "reserve_hypothesis_ids"),
            ("portfolio", "experimental_hypothesis_ids"),
            ("portfolio", "rejected_hypothesis_ids"),
        )
        wrong_containers = (None, True, 7, 1.5, "identifier", {})
        wrong_entries = (None, True, 7, 1.5, [], {}, "")
        for section, field in reference_targets:
            for value in wrong_containers:
                with self.subTest(
                    kind="container",
                    section=section,
                    field=field,
                    value=value,
                ):
                    payload = _fresh_artifact()
                    holder = payload[section]
                    if isinstance(holder, list):
                        holder[0][field] = value
                    else:
                        holder[field] = value
                    self._assert_total(validate, payload)
            for value in wrong_entries:
                with self.subTest(
                    kind="entry",
                    section=section,
                    field=field,
                    value=value,
                ):
                    payload = _fresh_artifact()
                    holder = payload[section]
                    if isinstance(holder, list):
                        holder[0][field] = [value]
                    else:
                        holder[field] = [value]
                    self._assert_total(validate, payload)

        for value in (True, 7, 1.5, [], {}):
            with self.subTest(kind="principal", value=value):
                payload = _fresh_artifact()
                payload["portfolio"]["principal_hypothesis_id"] = value
                self._assert_total(validate, payload)

    def test_reference_errors_are_addressed_and_deterministic(self) -> None:
        validate = _load_validator(REPO / "skills" / SCRIPT_RELATIVE)
        payload = _fresh_artifact()
        hypothesis = payload["hypotheses"][0]
        hypothesis["supporting_finding_ids"] = None
        hypothesis["adverse_finding_ids"] = [
            {},
            "unknown-finding",
            7,
            "",
            ["nested"],
            None,
        ]
        portfolio = payload["portfolio"]
        portfolio["reserve_hypothesis_ids"] = None
        portfolio["experimental_hypothesis_ids"] = [
            "unknown-hypothesis",
            {},
            "",
            1,
        ]

        errors = validate(payload)

        self.assertEqual(
            errors,
            [
                "hypotheses[0].supporting_finding_ids must be an array",
                "hypotheses[0].adverse_finding_ids[0] must be a non-empty string",
                "hypotheses[0].adverse_finding_ids[2] must be a non-empty string",
                "hypotheses[0].adverse_finding_ids[3] must be a non-empty string",
                "hypotheses[0].adverse_finding_ids[4] must be a non-empty string",
                "hypotheses[0].adverse_finding_ids[5] must be a non-empty string",
                "hypotheses[0] references unknown findings: ['unknown-finding']",
                "portfolio.reserve_hypothesis_ids must be an array",
                "portfolio.experimental_hypothesis_ids[1] must be a non-empty string",
                "portfolio.experimental_hypothesis_ids[2] must be a non-empty string",
                "portfolio.experimental_hypothesis_ids[3] must be a non-empty string",
                "portfolio.experimental_hypothesis_ids references unknown hypotheses: ['unknown-hypothesis']",
            ],
        )

    def test_enum_and_principal_objects_report_errors_without_cascade_crash(self) -> None:
        validate = _load_validator(REPO / "skills" / SCRIPT_RELATIVE)
        payload = _fresh_artifact()
        finding = payload["findings"][0]
        finding["relation"] = {}
        finding["verification_status"] = []
        finding["confidence"] = {}
        payload["hypotheses"][0]["status"] = []
        payload["portfolio"]["human_approval"] = {}
        payload["portfolio"]["principal_hypothesis_id"] = {}

        errors = validate(payload)

        self.assertEqual(
            errors,
            [
                "findings[0] has invalid relation",
                "findings[0] has invalid verification_status",
                "findings[0] has invalid confidence",
                "hypotheses[0] has invalid status",
                "portfolio.human_approval is invalid",
                "portfolio.principal_hypothesis_id must be a non-empty string or null",
                "principal hypothesis requires human_approval=approved",
            ],
        )

    def test_source_and_clean_install_report_semantic_errors_without_traceback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)
            malformed = _fresh_artifact()
            malformed["hypotheses"][0]["supporting_finding_ids"] = None

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    case_root = root / location
                    case_root.mkdir()
                    artifact = case_root / "research.json"
                    original = json.dumps(malformed, ensure_ascii=False) + "\n"
                    artifact.write_text(original, encoding="utf-8")

                    completed = self._run(
                        skills_root / SCRIPT_RELATIVE,
                        [str(artifact)],
                        cwd=case_root,
                    )

                    self.assertEqual(completed.returncode, 1)
                    self.assertEqual(
                        completed.stdout,
                        "ERROR: hypotheses[0].supporting_finding_ids must be an array\n",
                    )
                    self.assertEqual(completed.stderr, "")
                    self.assertNotIn("Traceback", completed.stdout + completed.stderr)
                    self.assertEqual(artifact.read_text(encoding="utf-8"), original)

    def test_source_and_clean_install_normalize_non_object_root_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    case_root = root / f"root-{location}"
                    case_root.mkdir()
                    artifact = case_root / "research.json"
                    artifact.write_text("[]\n", encoding="utf-8")

                    completed = self._run(
                        skills_root / SCRIPT_RELATIVE,
                        [str(artifact)],
                        cwd=case_root,
                    )

                    self.assertEqual(completed.returncode, 1)
                    self.assertEqual(completed.stdout, "ERROR: root must be an object\n")
                    self.assertEqual(completed.stderr, "")
                    self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def test_source_and_clean_install_escape_duplicate_surrogate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)
            surrogate = json.loads('"\\ud800"')
            malformed = _fresh_artifact()
            finding = malformed["findings"][0]
            finding["finding_id"] = surrogate
            finding["hypothesis_ids"] = [surrogate]
            malformed["findings"].append(dict(finding))
            hypothesis = malformed["hypotheses"][0]
            hypothesis["hypothesis_id"] = surrogate
            hypothesis["supporting_finding_ids"] = [surrogate]
            malformed["hypotheses"].append(dict(hypothesis))
            expected = (
                "ERROR: duplicate finding_id: \\ud800\n"
                "ERROR: duplicate hypothesis_id: \\ud800\n"
            )

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    case_root = root / f"surrogate-{location}"
                    case_root.mkdir()
                    artifact = case_root / "research.json"
                    original = json.dumps(malformed, ensure_ascii=True) + "\n"
                    artifact.write_text(original, encoding="utf-8")

                    completed = self._run(
                        skills_root / SCRIPT_RELATIVE,
                        [str(artifact)],
                        cwd=case_root,
                    )

                    self.assertEqual(completed.returncode, 1)
                    self.assertEqual(completed.stdout, expected)
                    self.assertEqual(completed.stderr, "")
                    self.assertNotIn("Traceback", completed.stdout + completed.stderr)
                    self.assertEqual(artifact.read_text(encoding="utf-8"), original)

    def test_source_and_clean_install_contain_decoder_failures(self) -> None:
        invalid_inputs = [
            ("invalid-utf8", b"\xff"),
            ("excessive-nesting", b"[" * 10000 + b"]" * 10000),
        ]
        get_digit_limit = getattr(sys, "get_int_max_str_digits", None)
        if get_digit_limit is not None:
            digit_limit = get_digit_limit()
            if digit_limit > 0:
                invalid_inputs.append(
                    ("overlong-integer", b"9" * (digit_limit + 1))
                )

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                script = skills_root / SCRIPT_RELATIVE
                for case_name, content in invalid_inputs:
                    with self.subTest(location=location, case=case_name):
                        case_root = root / f"decode-{location}-{case_name}"
                        case_root.mkdir()
                        artifact = case_root / "research.json"
                        artifact.write_bytes(content)

                        completed = self._run(
                            script,
                            [str(artifact)],
                            cwd=case_root,
                        )

                        self.assertEqual(completed.returncode, 2)
                        self.assertEqual(completed.stdout, "")
                        self.assertTrue(completed.stderr.startswith("invalid input: "))
                        self.assertNotIn("Traceback", completed.stderr)

    def test_source_and_clean_install_preserve_success_and_json_error_channels(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            self._install(installed, cwd=root)

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    case_root = root / f"controls-{location}"
                    case_root.mkdir()
                    valid_path = case_root / "valid.json"
                    valid_path.write_text(
                        json.dumps(_fresh_artifact(), ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    invalid_path = case_root / "invalid.json"
                    invalid_path.write_text('{"case_id":', encoding="utf-8")
                    script = skills_root / SCRIPT_RELATIVE

                    valid = self._run(script, [str(valid_path)], cwd=case_root)
                    invalid = self._run(script, [str(invalid_path)], cwd=case_root)

                    self.assertEqual(valid.returncode, 0, valid.stderr)
                    self.assertEqual(
                        valid.stdout,
                        "OK: базовая структура и ссылки соответствуют контракту; "
                        "юридическая готовность не проверялась\n",
                    )
                    self.assertEqual(valid.stderr, "")
                    self.assertEqual(invalid.returncode, 2)
                    self.assertEqual(invalid.stdout, "")
                    self.assertTrue(invalid.stderr.startswith("invalid input: "))
                    self.assertNotIn("Traceback", invalid.stderr)

    def _assert_total(self, validate, payload: dict[str, object]) -> None:
        before = json.loads(json.dumps(payload, ensure_ascii=False))
        errors = validate(payload)
        self.assertIsInstance(errors, list)
        self.assertTrue(errors)
        self.assertTrue(all(isinstance(error, str) for error in errors))
        self.assertEqual(payload, before)

    def _install(self, target: Path, *, cwd: Path) -> None:
        completed = subprocess.run(
            [str(REPO / "install.sh"), "--target", str(target)],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def _run(
        self,
        script: Path,
        arguments: list[str],
        *,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *arguments],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
