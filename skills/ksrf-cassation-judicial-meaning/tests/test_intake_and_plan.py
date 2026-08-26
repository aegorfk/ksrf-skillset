import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from judicial_meaning.intake import intake_document, ocr_pdf_to_text, public_intake_record
from judicial_meaning.plan import freeze_plan, make_research_question, validate_plan


FIXTURES = Path(__file__).parent / "fixtures"


def complete_plan():
    return {
        "schema_version": "1.0",
        "title": "Проверка судебного смысла нормы",
        "research_questions": [
            {
                "id": "rq-1",
                "status": "research_question",
                "question": "Какие исходозначимые толкования нормы применяются в сопоставимых делах?",
                "norm_refs": ["ст. 10 Примерного кодекса"],
            }
        ],
        "norm_editions": [
            {
                "id": "edition-1",
                "norm_ref": "ст. 10 Примерного кодекса",
                "valid_from": "2019-10-01",
                "valid_to": None,
                "official_source_url": "https://example.invalid/norm",
                "edition_status": "verified",
            }
        ],
        "population": {
            "unit": "independent_case_chain",
            "date_from": "2024-03-07",
            "date_to": "2024-03-07",
            "courts": ["1kas"],
            "regimes": ["ksoyu_post_2019"],
            "official_population_rule": "Все официально обнаружимые опубликованные материалы в замкнутом календарном обходе.",
        },
        "query_lanes": {
            "exact_norm": ["статья 10"],
            "synonyms": ["примерная норма"],
            "mechanisms": ["отказ по формальному основанию"],
            "opposite_readings": ["не препятствует рассмотрению"],
            "other_grounds": ["иной самостоятельный мотив"],
            "later_authority": ["последующее разъяснение"],
        },
        "inclusion_rules": ["Полный текст и исходозначимое применение нормы"],
        "exclusion_rules": ["Норма приведена только в доводах стороны"],
        "materiality_rule": "Толкование связано с мотивом и итогом дела.",
        "adverse_review": {
            "required": True,
            "queries": ["противоположное толкование"],
            "no_hit_wording": "В наблюдаемом корпусе противоположные акты не обнаружены; отсутствие в практике не доказано.",
        },
        "contradiction_rule": "Существенно отличающиеся факты кодируются отдельно.",
        "coverage_expectation": "closed_official_population_observed",
        "maximum_claim_if_incomplete": "corroborated_observed_corpus",
        "approved_by": "human-reviewer",
    }


class IntakeAndPlanTests(unittest.TestCase):
    def test_text_html_and_json_are_extracted_without_project_code(self):
        for name in ("applicant_property.txt", "applicant_procedure.html", "applicant_record.json"):
            with self.subTest(name=name):
                record = intake_document(FIXTURES / name)
                self.assertEqual("extracted", record["extraction_status"])
                self.assertTrue(record["sha256"])
                self.assertGreater(len(record["text"]), 20)
                self.assertNotIn("ks_parser", json.dumps(record, ensure_ascii=False))

    def test_docx_is_extracted_with_standard_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "act.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    "<?xml version='1.0'?><w:document xmlns:w='x'><w:body>"
                    "<w:p><w:r><w:t>Суд применил статью 10 в исходозначимом толковании.</w:t></w:r></w:p>"
                    "</w:body></w:document>",
                )
            record = intake_document(path)
            self.assertEqual("extracted", record["extraction_status"])
            self.assertIn("Суд применил", record["text"])

    def test_unsupported_input_fails_closed_and_public_export_has_no_raw_text(self):
        record = intake_document(FIXTURES / "image_only.pdf")
        self.assertEqual("unextractable", record["extraction_status"])
        self.assertEqual("", record["text"])
        public = public_intake_record(record)
        self.assertNotIn("text", public)
        self.assertNotIn("source_path", public)
        self.assertEqual(record["sha256"], public["sha256"])

    def test_pdf_uses_detected_local_helper_and_records_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Path(tmp) / "pdftotext"
            tool.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"-v\" ]; then echo 'pdftotext fixture 1.0' >&2; exit 0; fi\n"
                "printf '%s\\n' 'Суд применил спорную норму как основание итогового отказа.' > \"$3\"\n",
                encoding="utf-8",
            )
            tool.chmod(0o755)
            with patch.dict(os.environ, {"PATH": tmp}):
                record = intake_document(FIXTURES / "image_only.pdf")
        self.assertEqual("extracted", record["extraction_status"])
        self.assertEqual("pdftotext", record["extraction_method"])
        self.assertIn("fixture 1.0", record["helper_version"])
        self.assertIn("Суд применил", record["text"])

    def test_explicit_ocr_helper_writes_text_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdftoppm = root / "pdftoppm"
            tesseract = root / "tesseract"
            pdftoppm.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "if '-v' in sys.argv:\n"
                "    print('pdftoppm fixture 1.0')\n"
                "else:\n"
                "    pathlib.Path(sys.argv[-1] + '-1.png').write_bytes(b'fixture png')\n",
                encoding="utf-8",
            )
            tesseract.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if '--version' in sys.argv:\n"
                "    print('tesseract fixture 1.0')\n"
                "else:\n"
                "    print('Суд применил спорную норму в исходозначимом смысле.')\n",
                encoding="utf-8",
            )
            pdftoppm.chmod(0o755)
            tesseract.chmod(0o755)
            output = root / "ocr.txt"
            with patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ.get("PATH", "")}):
                provenance = ocr_pdf_to_text(FIXTURES / "image_only.pdf", output)
            self.assertIn("Суд применил", output.read_text(encoding="utf-8"))
            self.assertFalse(provenance["human_verified"])
            self.assertEqual("rus", provenance["language"])
            self.assertTrue((root / "ocr.txt.provenance.json").exists())

    def test_question_is_neutral_before_corpus(self):
        question = make_research_question(
            "Суды применяют только одно толкование",
            ["ст. 10 Примерного кодекса"],
        )
        self.assertEqual("hypothesis_under_test", question["status"])
        self.assertFalse(question["supported"])
        self.assertNotIn("drafting_ready", question.values())

    def test_plan_is_subject_neutral_and_freeze_is_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = complete_plan()
            errors = validate_plan(plan)
            self.assertEqual([], errors)
            frozen = freeze_plan(plan, Path(tmp))
            self.assertTrue(frozen["frozen"])
            self.assertEqual(64, len(frozen["plan_sha256"]))
            self.assertTrue((Path(tmp) / "plans" / "plan-v1.json").exists())
            self.assertTrue((Path(tmp) / "research-questions.jsonl").exists())
            self.assertTrue((Path(tmp) / "queries.jsonl").exists())
            payload = json.dumps(frozen, ensure_ascii=False).lower()
            self.assertNotIn("комиссия по трудовым спорам", payload)
            self.assertNotIn(" ктс", payload)

    def test_unresolved_norm_edition_blocks_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = complete_plan()
            plan["norm_editions"][0]["edition_status"] = "unresolved"
            with self.assertRaisesRegex(ValueError, "редакц"):
                freeze_plan(plan, Path(tmp))

    def test_temporal_strata_and_official_event_are_validated_and_hashed(self):
        plan = complete_plan()
        plan["population"]["date_from"] = "2023-06-14"
        plan["population"]["date_to"] = "2023-06-16"
        plan["temporal_strata"] = [
            {
                "id": "before-event",
                "label": "До события",
                "date_from": "2023-06-14",
                "date_to": "2023-06-14",
            },
            {
                "id": "after-event",
                "label": "После события",
                "date_from": "2023-06-15",
                "date_to": "2023-06-16",
            },
        ]
        plan["interpretive_events"] = [
            {
                "id": "event-1",
                "label": "Официальное толкование",
                "effective_date": "2023-06-15",
                "official_source_url": "https://official.example.invalid/decision",
                "before_stratum_id": "before-event",
                "after_stratum_id": "after-event",
            }
        ]
        self.assertEqual([], validate_plan(plan))
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first = freeze_plan(plan, Path(first_tmp))
            changed = json.loads(json.dumps(plan))
            changed["interpretive_events"][0]["label"] = "Уточнённое официальное толкование"
            second = freeze_plan(changed, Path(second_tmp))
        self.assertNotEqual(first["plan_sha256"], second["plan_sha256"])

    def test_temporal_strata_reject_gaps_overlap_and_invalid_event_links(self):
        base = complete_plan()
        base["population"]["date_from"] = "2023-06-14"
        base["population"]["date_to"] = "2023-06-17"
        base["temporal_strata"] = [
            {"id": "before", "label": "До", "date_from": "2023-06-14", "date_to": "2023-06-14"},
            {"id": "after", "label": "После", "date_from": "2023-06-15", "date_to": "2023-06-17"},
        ]
        base["interpretive_events"] = [
            {
                "id": "event",
                "label": "Событие",
                "effective_date": "2023-06-15",
                "official_source_url": "https://official.example.invalid/decision",
                "before_stratum_id": "before",
                "after_stratum_id": "after",
            }
        ]

        invalid_plans = []
        gap = json.loads(json.dumps(base))
        gap["temporal_strata"][1]["date_from"] = "2023-06-16"
        invalid_plans.append(gap)
        overlap = json.loads(json.dumps(base))
        overlap["temporal_strata"][0]["date_to"] = "2023-06-15"
        invalid_plans.append(overlap)
        unknown = json.loads(json.dumps(base))
        unknown["interpretive_events"][0]["after_stratum_id"] = "missing"
        invalid_plans.append(unknown)
        wrong_date = json.loads(json.dumps(base))
        wrong_date["interpretive_events"][0]["effective_date"] = "2023-06-16"
        invalid_plans.append(wrong_date)

        for plan in invalid_plans:
            with self.subTest(plan=plan):
                self.assertTrue(validate_plan(plan))

    def test_empty_temporal_fields_keep_legacy_plan_valid(self):
        plan = complete_plan()
        plan["temporal_strata"] = []
        plan["interpretive_events"] = []
        self.assertEqual([], validate_plan(plan))


if __name__ == "__main__":
    unittest.main()
