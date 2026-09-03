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
SUCCESS = (
    "OK: базовая структура и ссылки соответствуют контракту; "
    "юридическая готовность не проверялась\n"
)


def _artifact() -> dict[str, object]:
    return {
        "case_id": "CASE-CORE",
        "findings": [
            {
                "finding_id": "finding-1",
                "case_id": "CASE-CORE",
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


def _empty_artifact() -> dict[str, object]:
    return {
        "case_id": "CASE-EMPTY",
        "findings": [],
        "hypotheses": [],
        "portfolio": {
            "human_approval": "pending",
            "principal_hypothesis_id": None,
            "reserve_hypothesis_ids": [],
            "experimental_hypothesis_ids": [],
            "rejected_hypothesis_ids": [],
        },
        "future_extension": {"opaque": True},
    }


def _load_validator(script: Path):
    spec = importlib.util.spec_from_file_location(
        "argument_research_validator_core",
        script,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


class ArgumentResearchValidatorCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validate = staticmethod(
            _load_validator(REPO / "skills" / SCRIPT_RELATIVE)
        )

    def test_required_root_containers_do_not_default_to_empty(self) -> None:
        payload = _empty_artifact()
        del payload["findings"]
        del payload["hypotheses"]

        self.assertEqual(
            self.validate(payload),
            ["root missing findings", "root missing hypotheses"],
        )

        payload = _empty_artifact()
        del payload["portfolio"]
        self.assertEqual(self.validate(payload), ["root missing portfolio"])

    def test_complete_empty_research_and_unknown_extensions_remain_valid(self) -> None:
        payload = _empty_artifact()
        payload["portfolio"]["hard_gates"] = "opaque-for-this-validator"
        payload["portfolio"]["dimension_comparison"] = [7, None]

        self.assertEqual(self.validate(payload), [])

    def test_portfolio_requires_only_the_five_executable_core_fields(self) -> None:
        payload = _empty_artifact()
        payload["portfolio"] = {}

        self.assertEqual(
            self.validate(payload),
            [
                "portfolio missing experimental_hypothesis_ids",
                "portfolio missing human_approval",
                "portfolio missing principal_hypothesis_id",
                "portfolio missing rejected_hypothesis_ids",
                "portfolio missing reserve_hypothesis_ids",
            ],
        )

    def test_every_published_nested_field_remains_required(self) -> None:
        controls = _artifact()
        for section in ("findings", "hypotheses"):
            item = controls[section][0]
            for field in tuple(item):
                with self.subTest(section=section, field=field):
                    payload = _artifact()
                    del payload[section][0][field]
                    self.assertIn(
                        f"{section}[0] missing {field}",
                        self.validate(payload),
                    )

    def test_finding_scalar_and_list_types_are_enforced_without_coercion(self) -> None:
        targets = {
            "finding_id": "findings[0].finding_id must be a non-empty string",
            "case_id": "findings[0].case_id must be a non-empty string",
            "direction": "findings[0].direction must be a non-empty string",
            "thesis": "findings[0].thesis must be a non-empty string",
            "source_anchor": "findings[0].source_anchor must be a non-empty string",
        }
        for field, expected in targets.items():
            for value in (None, True, 7, [], {}, "  "):
                with self.subTest(field=field, value=value):
                    payload = _artifact()
                    payload["findings"][0][field] = value
                    self.assertIn(expected, self.validate(payload))

        payload = _artifact()
        payload["findings"][0].update(
            {
                "locator": 5,
                "hypothesis_ids": "hypothesis-1",
                "limitations": ["", 7],
                "contains_sensitive_data": "false",
            }
        )
        self.assertEqual(
            self.validate(payload),
            [
                "findings[0].locator must be null or a non-empty string",
                "findings[0] verified without locator",
                "findings[0].hypothesis_ids must be an array",
                "findings[0].limitations[0] must be a non-empty string",
                "findings[0].limitations[1] must be a non-empty string",
                "findings[0].contains_sensitive_data must be a boolean",
            ],
        )

    def test_hypothesis_text_and_list_types_are_enforced(self) -> None:
        text_fields = (
            "hypothesis_id",
            "title",
            "normative_mechanism",
            "constitutional_harm",
            "review_line",
            "falsifier",
            "fact_dispute_risk",
            "refusal_model",
            "primary_relief",
            "narrower_relief",
        )
        for field in text_fields:
            with self.subTest(field=field):
                payload = _artifact()
                payload["hypotheses"][0][field] = {}
                self.assertIn(
                    f"hypotheses[0].{field} must be a non-empty string",
                    self.validate(payload),
                )

        payload = _artifact()
        payload["hypotheses"][0]["missing_materials"] = [None, " "]
        self.assertEqual(
            self.validate(payload),
            [
                "hypotheses[0].missing_materials[0] must be a non-empty string",
                "hypotheses[0].missing_materials[1] must be a non-empty string",
            ],
        )

    def test_finding_to_hypothesis_references_are_resolved(self) -> None:
        payload = _artifact()
        payload["findings"][0]["hypothesis_ids"] = [
            "unknown-z",
            "hypothesis-1",
            "unknown-a",
        ]

        self.assertEqual(
            self.validate(payload),
            [
                "findings[0] references unknown hypotheses: "
                "['unknown-a', 'unknown-z']"
            ],
        )

    def test_approved_portfolio_requires_known_principal_and_string_reviewer(self) -> None:
        payload = _artifact()
        payload["portfolio"]["human_approval"] = "approved"

        self.assertEqual(
            self.validate(payload),
            [
                "approved portfolio requires principal_hypothesis_id",
                "approved portfolio requires approved_by as a non-empty string",
            ],
        )

        payload["portfolio"]["principal_hypothesis_id"] = "hypothesis-1"
        payload["portfolio"]["approved_by"] = True
        self.assertEqual(
            self.validate(payload),
            ["approved portfolio requires approved_by as a non-empty string"],
        )

        payload["portfolio"]["approved_by"] = "Юрист"
        self.assertEqual(self.validate(payload), [])

    def test_source_and_clean_install_share_failure_and_limited_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            install = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            invalid = {"case_id": "CASE-BROKEN", "portfolio": {}}
            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    case_root = root / location
                    case_root.mkdir()
                    invalid_path = case_root / "invalid.json"
                    original = json.dumps(invalid, ensure_ascii=False) + "\n"
                    invalid_path.write_text(original, encoding="utf-8")
                    valid_path = case_root / "valid.json"
                    valid_path.write_text(
                        json.dumps(_empty_artifact(), ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    script = skills_root / SCRIPT_RELATIVE

                    failed = self._run(script, invalid_path, cwd=case_root)
                    passed = self._run(script, valid_path, cwd=case_root)

                    self.assertEqual(failed.returncode, 1)
                    self.assertEqual(
                        failed.stdout,
                        "ERROR: root missing findings\n"
                        "ERROR: root missing hypotheses\n"
                        "ERROR: portfolio missing experimental_hypothesis_ids\n"
                        "ERROR: portfolio missing human_approval\n"
                        "ERROR: portfolio missing principal_hypothesis_id\n"
                        "ERROR: portfolio missing rejected_hypothesis_ids\n"
                        "ERROR: portfolio missing reserve_hypothesis_ids\n",
                    )
                    self.assertEqual(failed.stderr, "")
                    self.assertNotIn("Traceback", failed.stdout + failed.stderr)
                    self.assertEqual(
                        invalid_path.read_text(encoding="utf-8"), original
                    )
                    self.assertEqual(passed.returncode, 0, passed.stderr)
                    self.assertEqual(passed.stdout, SUCCESS)
                    self.assertEqual(passed.stderr, "")

    def test_russian_output_and_unicode_ids_survive_ascii_process_encoding(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installed = root / "installed skills"
            install = subprocess.run(
                [str(REPO / "install.sh"), "--target", str(installed)],
                cwd=root,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            valid_path = root / "valid.json"
            valid_path.write_text(
                json.dumps(_empty_artifact(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            invalid = _artifact()
            invalid["findings"][0]["hypothesis_ids"] = ["гипотеза-🚫"]
            invalid_path = root / "invalid.json"
            invalid_path.write_text(
                json.dumps(invalid, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            environment = {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "ascii",
            }

            for location, skills_root in (
                ("source", REPO / "skills"),
                ("installed", installed),
            ):
                with self.subTest(location=location):
                    script = skills_root / SCRIPT_RELATIVE
                    passed = subprocess.run(
                        [PYTHON, str(script), str(valid_path)],
                        cwd=root,
                        env=environment,
                        capture_output=True,
                        check=False,
                    )
                    failed = subprocess.run(
                        [PYTHON, str(script), str(invalid_path)],
                        cwd=root,
                        env=environment,
                        capture_output=True,
                        check=False,
                    )

                    self.assertEqual(passed.returncode, 0, passed.stderr)
                    self.assertEqual(passed.stdout, SUCCESS.encode("utf-8"))
                    self.assertEqual(passed.stderr, b"")
                    self.assertEqual(failed.returncode, 1, failed.stderr)
                    self.assertEqual(
                        failed.stdout,
                        (
                            "ERROR: findings[0] references unknown hypotheses: "
                            "['гипотеза-🚫']\n"
                        ).encode("utf-8"),
                    )
                    self.assertEqual(failed.stderr, b"")
                    self.assertNotIn(b"Traceback", failed.stdout + failed.stderr)

    def _run(
        self,
        script: Path,
        artifact: Path,
        *,
        cwd: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), str(artifact)],
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
