#!/usr/bin/env python3
"""Регрессии автономного извлечения нормы, дат и цепочки права/вреда."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("ksrf_autocollect.py")
SPEC = importlib.util.spec_from_file_location("ksrf_autocollect", SCRIPT)
assert SPEC and SPEC.loader
AUTOCOLLECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUTOCOLLECT)


class AutonomousIntakeTests(unittest.TestCase):
    def test_exact_instrument_requisites(self) -> None:
        cases = {
            "Суд применил статью 31 ЖК РФ.": "ст. 31 ЖК РФ",
            "Суд руководствовался пунктом 2 статьи 35 Земельного кодекса РФ.": "п. 2 ст. 35 Земельного кодекса РФ",
            "Суд применил статью 69 СК РФ.": "ст. 69 СК РФ",
            "Суд применил ч. 1 ст. 3 Федерального закона от 02.05.2006 № 59-ФЗ.": "ч. 1 ст. 3 Федерального закона от 02.05.2006 № 59-ФЗ",
            "Суд применил ст. 15 Закона РФ от 15.05.1991 № 1244-1.": "ст. 15 Закона РФ от 15.05.1991 № 1244-1",
            "Суд применил статью 3 Федерального конституционного закона № 1-ФКЗ.": "ст. 3 Федерального конституционного закона № 1-ФКЗ",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                occurrence = AUTOCOLLECT.extract_legal_ref_occurrences(source)[0]
                self.assertEqual(expected, occurrence["value"])
                self.assertEqual("complete_instrument_candidate", occurrence["requisites_status"])

        numberless_fkz = AUTOCOLLECT.extract_legal_ref_occurrences(
            "Суд применил статью 3 Федерального конституционного закона."
        )[0]
        self.assertEqual("date_or_number_missing", numberless_fkz["requisites_status"])
        self.assertFalse(AUTOCOLLECT.is_constitution_reference(numberless_fkz["value"]))

    def test_bare_locator_is_not_exact_application_anchor(self) -> None:
        norm = "ст. 10"
        document = {
            "relative_path": "act.txt",
            "document_passport": {
                "prayer_block": "",
                "document_type": "judicial_act",
                "challenged_norm_candidates": [norm],
            },
            "applied_norm_contexts": [{
                "norm": norm,
                "context": "Суд применил ст. 10 и отказал.",
                "evidence_role": "judicial_application_candidate",
                "instrument_candidate": "",
                "requisites_status": "instrument_missing",
            }],
        }
        candidate = AUTOCOLLECT.rank_challenged_norm_candidates([document])[0]
        self.assertEqual("application_locator_candidate", candidate["candidate_role"])
        self.assertEqual("candidate_requires_normative_instrument_recovery", candidate["status"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decision.txt"
            path.write_text(
                "РЕШЕНИЕ суда от 12.03.2024. Дело № 2-999/2024. "
                "Суд применил статью 10 и отказал заявителю.",
                encoding="utf-8",
            )
            collected = AUTOCOLLECT.collect_from_document(path, path.parent, False, 1)
        gaps = {
            item["gap_code"]
            for item in AUTOCOLLECT.merge([collected])["autonomous_intake"]["unresolved_candidates_before_verification"]
        }
        self.assertIn("normative_instrument_not_identified", gaps)
        self.assertIn("judicial_application_not_confirmed", gaps)

    def test_federal_constitutional_law_is_not_filtered_as_constitution(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decision.txt"
            path.write_text(
                "РЕШЕНИЕ суда от 12.03.2024. Суд сослался на статью 46 Конституции РФ. "
                "Суд применил статью 3 Федерального конституционного закона № 1-ФКЗ и отказал.",
                encoding="utf-8",
            )
            document = AUTOCOLLECT.collect_from_document(path, path.parent, False, 1)
        expected = "ст. 3 Федерального конституционного закона № 1-ФКЗ"
        self.assertIn(expected, document["document_passport"]["challenged_norm_candidates"])
        self.assertTrue(any(item["norm"] == expected for item in document["applied_norm_contexts"]))
        self.assertNotIn("ст. 46 Конституции РФ", document["document_passport"]["challenged_norm_candidates"])

    def test_interpretive_locator_and_case_number_false_positives(self) -> None:
        source = "input/outcome benchmark и № 52-П/2024"
        self.assertEqual(["№ 52-П/2024"], [match.group(0) for match in AUTOCOLLECT.CASE_RE.finditer(source)])
        context = "Суд применил пункт 30 Постановления Пленума Верховного Суда РФ."
        self.assertTrue(AUTOCOLLECT.is_interpretive_source_locator("п. 30", context))
        document = {
            "relative_path": "act.txt",
            "document_passport": {
                "prayer_block": "",
                "document_type": "judicial_act",
                "challenged_norm_candidates": ["п. 30"],
            },
            "applied_norm_contexts": [{
                "norm": "п. 30",
                "context": context,
                "evidence_role": "interpretive_source_locator",
                "instrument_candidate": "",
                "requisites_status": "instrument_missing",
            }],
        }
        self.assertFalse(AUTOCOLLECT.rank_challenged_norm_candidates([document]))

    def test_complaint_and_benchmark_cannot_impersonate_judicial_act(self) -> None:
        complaint = (
            "В Конституционный Суд Российской Федерации\n"
            "ЖАЛОБА на нарушение конституционных прав\n"
            "Решение суда обязало работодателя совершить действие. "
            "По мнению заявителя, суд применил статью 419 ТК РФ и отказал."
        )
        self.assertEqual("ksrf_complaint", AUTOCOLLECT.classify_document(complaint, "document.txt"))
        benchmark = (
            "# Пример: исходная жалоба\n"
            "Это ретроспективный input/outcome benchmark.\n"
            "## Input-only\n"
            "Решение суда обязало работодателя; жалоба утверждает, что суд применил "
            "статью 419 ТК РФ, пункт 1 статьи 308.3 ГК РФ и часть 3 статьи 206 ГПК РФ."
        )
        self.assertEqual("case_study_or_benchmark", AUTOCOLLECT.classify_document(benchmark, "example.md"))
        with tempfile.TemporaryDirectory() as folder:
            complaint_path = Path(folder) / "complaint.txt"
            complaint_path.write_text(complaint, encoding="utf-8")
            collected = AUTOCOLLECT.collect_from_document(complaint_path, complaint_path.parent, False, 1)
        ranked = AUTOCOLLECT.rank_challenged_norm_candidates([collected])
        self.assertTrue(ranked)
        self.assertNotIn("application_anchor_candidate", {item["candidate_role"] for item in ranked})
        self.assertIn("reported_application_candidate", {item["candidate_role"] for item in ranked})

    def test_act_title_dates_are_court_decisions(self) -> None:
        cases = [
            "РЕШЕНИЕ суда от 12.03.2024",
            "Определение от 12 марта 2024 года",
            "Апелляционное определение 12.03.2024",
        ]
        for source in cases:
            with self.subTest(source=source):
                candidates = AUTOCOLLECT.build_timeline_candidates(source, "act.txt")
                self.assertEqual("court_decision", candidates[0]["event_type"])
        normative_date = "Решением суда применена ст. 3 Федерального закона от 02.05.2006 № 59-ФЗ"
        self.assertEqual(
            "unclassified_date",
            AUTOCOLLECT.build_timeline_candidates(normative_date, "act.txt")[0]["event_type"],
        )

    def test_bare_right_and_neutral_topic_do_not_invent_harm(self) -> None:
        def hypotheses(source: str):
            refs = AUTOCOLLECT.extract_constitutional_refs(source)
            return AUTOCOLLECT.build_right_harm_hypotheses(source, "act.txt", refs, [])

        bare = hypotheses("Упомянута статья 37 Конституции РФ; иных сведений нет.")
        self.assertEqual("right_candidate_without_harm", bare[0]["status"])
        self.assertFalse(hypotheses("Ссылка на статью 35 Конституции РФ отсутствует."))
        neutral = hypotheses("Заявитель осуществлял распространение информации в сети Интернет.")
        self.assertFalse(any(item["status"] == "right_and_harm_hypothesis" for item in neutral))
        adverse = hypotheses("Заявитель привлечён к ответственности за распространение информации.")
        self.assertTrue(any(
            item["hypothesis_code"] == "freedom_of_expression"
            and item["status"] == "right_and_harm_hypothesis"
            for item in adverse
        ))


if __name__ == "__main__":
    unittest.main()
