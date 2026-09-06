from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCES = REPO / "docs/KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md"
POLICY = REPO / "skills/ksrf-complaint-cycle/references/source-authority-and-route.md"
EXAMPLES = REPO / "skills/ksrf-explore-arguments/references"


class PublicSourcePresentationTests(unittest.TestCase):
    def test_reader_facing_descriptions_omit_missing_link_notices(self) -> None:
        paths = [
            REPO / "README.md",
            *sorted((REPO / "docs").glob("KSRF_*.md")),
            *sorted(EXAMPLES.glob("example-*.md")),
            REPO / "skills/ksrf-argument-patterns/references/complaint-methodology-sources.md",
        ]
        forbidden = re.compile(
            r"(?:публичн(?:ая|ый) (?:ссылка|источник)[^\n.]{0,180}"
            r"не установлен[аы]?|публикация точного текста жалобы не найдена)",
            re.IGNORECASE,
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertNotRegex(path.read_text(), forbidden)

    def test_rules_preserve_internal_provenance_and_no_source_copy(self) -> None:
        content = POLICY.read_text()
        for marker in (
            "ComplaintSourceAttribution",
            "missing_complaint_source",
            "missing_donor_channel",
            "private_source_public_credit",
            "credited_role_wording",
            "опущенная ссылка не считается проверенной",
            "без оговорок о результатах поиска и без заглушек",
            "не восстанавливай ссылку по имени файла",
            "Не публикуй файл жалобы",
            "отсутствие акта прямо указано",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, content)
        self.assertNotIn("отсутствие публичной ссылки на точный текст жалобы указывается прямо", content)
        qa = (REPO / "skills/ksrf-complaint-qa/SKILL.md").read_text()
        self.assertIn("внутренний статус проверки не превращай в текст публичной оговорки", qa)

    def test_professional_links_keep_their_actual_role(self) -> None:
        for filename, urls, wording in (
            ("example-37-p-2024.md", ("https://borzoff.com/",), "профессиональную страницу, а не копию жалобы"),
            ("example-44-p-2026.md", ("https://sila-slova.pro/", "https://sila-slova.pro/komanda/chelohsaev-timur-adamovich/", "https://sila-slova.pro/komanda/advokat-vitaliy-katsko/"), "профессиональные страницы, а не копии жалобы"),
        ):
            content = (EXAMPLES / filename).read_text()
            for url in urls:
                self.assertIn(url, content)
            self.assertIn(wording, content)
            self.assertIn("SHA-256 частного источника:", content)

    def test_publication_instructions_record_editorial_scope(self) -> None:
        agents = (REPO / "AGENTS.md").read_text()
        publication = (REPO / "docs/PUBLICATION_CONTRACT.md").read_text()
        self.assertIn("неподтверждённую ссылку просто опускай", agents)
        self.assertIn("внутреннему учёту пробелов", agents)
        self.assertIn("без поясняющих оговорок и заглушек", publication)
        self.assertIn("не изменяет внутренний учёт происхождения", publication)

    def test_complaint_table_keeps_consecutive_numbers(self) -> None:
        content = SOURCES.read_text().split("## Публичные жалобы и связанные акты КС РФ", 1)[1]
        table = re.search(r"(?m)^\| № \|[^\n]*\n(?:\|[^\n]*\n)+", content)
        self.assertIsNotNone(table)
        rows = table.group(0).splitlines()
        numbers = [int(row.split("|", 2)[1].strip()) for row in rows[2:]]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertTrue(numbers)


if __name__ == "__main__":
    unittest.main()
