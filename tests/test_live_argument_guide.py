from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
SKILL_ROOT = REPO / "skills" / "ksrf-complaint-cycle"
GUIDE = SKILL_ROOT / "references" / "ksrf-live-argument-patterns.md"
TOOL_LAYER = SKILL_ROOT / "references" / "ksrf-tool-layer.md"
AUTOCOLLECT_PATH = SKILL_ROOT / "scripts" / "ksrf_autocollect.py"

sys.path.insert(0, str(TOOLS))

import skillset_file_contract as contract  # noqa: E402


EXPECTED_GUIDE_SHA256 = (
    "88676c07982a7b897a3ff93f89f0860083eb4ed3e9cff37e7db75802062805dd"
)


class LiveArgumentGuideTests(unittest.TestCase):
    def test_guide_is_exact_truthful_projection(self) -> None:
        data = GUIDE.read_bytes()
        text = data.decode("utf-8")

        self.assertEqual(len(text.splitlines()), 424)
        self.assertEqual(len(data), 52_749)
        self.assertEqual(hashlib.sha256(data).hexdigest(), EXPECTED_GUIDE_SHA256)
        self.assertNotIn(
            "- [Автоматизация](#функциональность-для-максимальной-автоматизации)",
            text,
        )
        self.assertNotIn("## Функциональность для максимальной автоматизации", text)
        self.assertNotIn("Автоматический индикатор:", text)
        self.assertEqual(text.count("Проверочный сигнал:"), 2)

    def test_shipped_routes_survive_without_dead_section_references(self) -> None:
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("## Как использовать в скиллах", text)
        routes = text.split("## Как использовать в скиллах", maxsplit=1)[1]

        for skill_name in (
            "ksrf-case-triage",
            "ksrf-exhaustion-planner",
            "ksrf-complaint-facts-demands",
            "ksrf-rights-argument-builder",
            "ksrf-court-request-motion",
            "ksrf-complaint-qa",
            "ksrf-formal-filing-check",
            "ksrf-decision-execution",
        ):
            with self.subTest(skill_name=skill_name):
                self.assertIn(f"`{skill_name}`", routes)

        self.assertNotIn("конструктор требования", routes)
        self.assertNotIn("QA-карта", routes)
        self.assertIn("[`ksrf-tool-layer.md`](ksrf-tool-layer.md)", text)
        self.assertIn(
            "сверяй каждую часть требования с фактическим крючком и полномочиями КС РФ",
            routes,
        )
        self.assertIn(
            "проверяй каждый довод по независимым обязательным критериям; "
            "не сворачивай их в общий балл",
            routes,
        )

    def test_unrelated_automation_language_is_not_overmatched(self) -> None:
        text = GUIDE.read_text(encoding="utf-8")

        for preserved in (
            "Deep-research отчеты по автоматизации жалобы",
            "не согласиться с ним автоматически",
            "Не обещай автоматический пересмотр всех похожих дел.",
        ):
            with self.subTest(preserved=preserved):
                self.assertIn(preserved, text)

    def test_guide_remains_in_payload_and_consumer_backlinks_resolve(self) -> None:
        payload = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in contract.payload_files(SKILL_ROOT)
        }
        self.assertIn("references/ksrf-live-argument-patterns.md", payload)

        relative_link = "../ksrf-complaint-cycle/references/ksrf-live-argument-patterns.md"
        for consumer in (
            "ksrf-court-request-motion",
            "ksrf-formal-filing-check",
            "ksrf-exhaustion-planner",
            "ksrf-decision-execution",
        ):
            skill_file = REPO / "skills" / consumer / "SKILL.md"
            with self.subTest(consumer=consumer):
                self.assertIn(relative_link, skill_file.read_text(encoding="utf-8"))
                self.assertTrue((skill_file.parent / relative_link).resolve().is_file())

    def test_shipped_autocollect_outputs_have_truthful_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "complaint.txt"
            source.write_text(
                "В Конституционный Суд Российской Федерации. ЖАЛОБА. "
                "Суд применил статью 236 ТК РФ и отказал заявителю. "
                "Нарушена статья 37 Конституции РФ. "
                "Постановление Конституционного Суда РФ № 1-П/2024. "
                "ПРОШУ признать положение не соответствующим Конституции РФ.",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [sys.executable, str(AUTOCOLLECT_PATH), str(source), "--no-ocr"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            document = report["documents"][0]
            summary = report["summary"]

        self.assertIn("document_passport", document)
        self.assertEqual(
            set(document["automation_analysis"]),
            {
                "application_bridge_candidates",
                "constitutional_test_suggestions",
                "request_formula_candidates",
                "practice_matrix_candidates",
                "repeatability_detector",
                "ksrf_execution_packet",
            },
        )
        self.assertIn("qa_matrix", document)
        expected_aggregate_keys = {
            "document_passports",
            "application_bridge_candidates",
            "constitutional_test_suggestions",
            "request_formula_candidates",
            "practice_matrix_candidates",
            "repeatability_review_items",
            "qa_review_items",
            "ksrf_execution_packets",
        }
        self.assertTrue(expected_aggregate_keys.issubset(summary))

        contract_text = TOOL_LAYER.read_text(encoding="utf-8")
        for output_key in expected_aggregate_keys:
            with self.subTest(output_key=output_key):
                self.assertIn(f"`summary.{output_key}`", contract_text)
        self.assertIn("только кандидаты по переданным локальным файлам", contract_text)
        self.assertIn("не доказывает устойчивость", contract_text)
        self.assertIn(
            "без ссылок не попадает в агрегированный список и сохраняет `risk=unknown`",
            contract_text,
        )
        self.assertIn("фиксированные задания для ручной проверки", contract_text)
        self.assertIn("Не заменяет полный `ksrf-complaint-qa`", contract_text)
        self.assertIn("законодательной истории сборщик отдельного результата не формирует", contract_text)
        self.assertIn("Международный и сравнительный пакет также не создаётся", contract_text)


if __name__ == "__main__":
    unittest.main()
