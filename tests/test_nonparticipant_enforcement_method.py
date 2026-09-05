from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from tests.test_runtime_retrospective_examples import CASE_SURFACE, EXAMPLES


REPO = Path(__file__).resolve().parents[1]
EXECUTION = REPO / "skills" / "ksrf-decision-execution"
METHOD = EXECUTION / "references" / "nonparticipant-enforcement-and-protection.md"


class NonparticipantEnforcementMethodTests(unittest.TestCase):
    def test_routes_and_credit_stay_in_their_sections(self) -> None:
        execution = (EXECUTION / "SKILL.md").read_text()
        route = execution.index(METHOD.name)
        self.assertLess(execution.index("### Лицо, не участвовавшее"), route)
        self.assertLess(route, execution.index("### Другая жалоба"))
        qa = (REPO / "skills/ksrf-complaint-qa/SKILL.md").read_text()
        self.assertLess(qa.index("\n5.2."), qa.index("\n5.3."))
        self.assertLess(qa.index("\n5.3."), qa.index("\n6."))
        owner = (REPO / "skills/ksrf-explore-arguments/SKILL.md").read_text()
        self.assertLess(owner.index(EXAMPLES["30"].name), owner.index(EXAMPLES["16"].name))
        sources = (REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md").read_text()
        row_end = sources.index("\n", sources.index("| Семья Однодворцевых;"))
        self.assertTrue(sources[row_end + 1:].startswith("| Александр Николаевич Дубовец;"))

    def test_method_routes_and_preserves_noncompensating_boundaries(self) -> None:
        method = METHOD.read_text()
        for wording in (
            "Состояние исполнения",
            "на дату прежнего постановления",
            "Отказ в пересмотре",
            "Отказ остановить исполнение",
            "не считается применённым только потому",
            "Подача жалобы, её принятие и уведомление не означают автоматического приостановления",
            "Непродолжение исполнения не отменяет решение",
            "Частный взыскатель, полностью исполненное до постановления решение",
            "пустое поле не считается подтверждением",
            "проверь последующие изменения и действующий механизм",
        ):
            with self.subTest(wording=wording):
                self.assertIn(wording.casefold(), method.casefold())
        for path in (
            EXECUTION / "SKILL.md",
            REPO / "skills/ksrf-complaint-qa/SKILL.md",
            EXAMPLES["30"],
        ):
            self.assertIn(METHOD.name, path.read_text())

    def test_public_attribution_has_exact_source_donor_and_outcome(self) -> None:
        for path in (
            EXAMPLES["30"],
            REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md",
            REPO / "docs/KSRF_ANALYZED_AUTHORS.md",
        ):
            text = path.read_text()
            for url in CASE_SURFACE["30"]["urls"]:
                with self.subTest(path=path.name, url=url):
                    self.assertIn(url, text)
            self.assertIn("Григорий Викторович Вайпан", text)
        card = EXAMPLES["30"].read_text()
        self.assertIn("Единоличное авторство из подписи не выводится", card)
        self.assertIn("с. 19–20", card)
        self.assertIn("с. 20", card)
        self.assertIn("свежая доступность не подтверждена", card)

    def test_real_objection_method_preserves_counterexample_scope(self) -> None:
        # Editorial contract only: this does not assess a generated legal response.
        method = METHOD.read_text()
        section = method.split(
            "## Ответ на возражение о невозможности отдельной защиты\n", 1
        )[1].split("## Границы переноса", 1)[0]
        for wording in (
            "отсутствие определённого основания",
            "отсутствие автоматического эффекта",
            "пересказ заявителей не заменяет сам отзыв",
            "Согласие взыскателя и самостоятельное основание мирового соглашения не переносятся",
            "не доказывает право заявителя на прекращение исполнения",
            "не устраняет другие самостоятельные основания отказа",
            "не наделяет суд новым полномочием",
            "Это позиции участников, а не выводы КС РФ",
            "актуальное право и результат нового дела проверяются отдельно",
        ):
            with self.subTest(wording=wording):
                self.assertIn(wording, section)
        self.assertIn("Отзыв-А.А.Клишаса.pdf), с. 9", section)
        self.assertIn("Однодворцевы_ВозраженияФИН.pdf), с. 3–4", section)
        self.assertIn("argument-quality-revision.md#35-", section)

    def test_synthetic_execution_cases_need_no_historical_source(self) -> None:
        source = EXECUTION / "evals/evals.json"
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            "fcbe1313ad9c06c7fc5aa8a73c3a07c59ab8407db94382ac243e29d88c4692fa",
        )
        payload = json.loads(source.read_text())
        entries = {entry["id"]: entry for entry in payload["evals"]}
        self.assertEqual(set(entries), set(range(1, 12)))
        for number in range(4, 9):
            with self.subTest(number=number):
                self.assertEqual(entries[number]["files"], [])
                self.assertGreaterEqual(len(entries[number]["expectations"]), 2)
        self.assertIn("полностью исполнены до", entries[5]["prompt"])
        self.assertIn("Жалоба только подана", entries[6]["prompt"])
        self.assertIn("не представлены", entries[7]["prompt"])
        self.assertIn("двух частных лиц", entries[8]["prompt"])


if __name__ == "__main__":
    unittest.main()
