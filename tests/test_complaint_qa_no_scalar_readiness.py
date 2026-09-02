from __future__ import annotations

import hashlib
import re
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import skillset_file_contract as canonical  # noqa: E402


QA_ROOT = REPO / "skills" / "ksrf-complaint-qa"
REFERENCE = QA_ROOT / "references" / "workflow-reference.md"
SKILL = QA_ROOT / "SKILL.md"

DIMENSIONS = (
    "Норма и применение",
    "Конституционный дефект",
    "Корпусная опора",
    "Контроль фактического спора",
    "Требование",
    "Контраргументы",
)

ROW_MEANINGS = {
    "Норма и применение": (
        ("точная норма и цитатное окно применения",),
        ("норма названа, применение спорно", "норма не применена"),
        ("норма неясна", "актов недостаточно"),
    ),
    "Конституционный дефект": (
        ("дефект связан с правом, вредом и практикой",),
        ("дефект назван, но не раскрыт", "обычная судебная ошибка"),
        ("отличить дефект нормы от обычной судебной ошибки",),
    ),
    "Корпусная опора": (
        (
            "есть релевантные позиции КС РФ и совпадающий паттерн",
            "корпусная опора не заявлена и прямые официальные опоры проверены",
        ),
        ("нет опоры", "слабая аналогия или вторичный источник"),
        ("поиск или проверка официальных источников не завершены",),
    ),
    "Контроль фактического спора": (
        ("факты служат только применению нормы и вреду",),
        ("факты частично переупакованы", "спор о фактах"),
        ("проекта и актов недостаточно",),
    ),
    "Требование": (
        ("зеркалит дефект и просит допустимый смысл или способ защиты",),
        ("в целом связано с дефектом", "шире полномочий КС РФ"),
        ("нет проверяемой формулировки требования",),
    ),
    "Контраргументы": (
        ("отказная логика разобрана и отремонтирована",),
        ("не проверены", "названы, но без ремонта"),
        ("недоступны материалы",),
    ),
}

HEURISTIC_SCOPE = (
    "Это результаты эвристической проверки, а не новые состояния обязательных "
    "проверок и не вывод о допустимости, юридической корректности, готовности к "
    "подаче, выборе основного довода или исходе дела."
)
PRESERVED_PROJECTION_SHA256 = (
    "6e48efe07a0cab58ac32b135ec5b9315ec7f282125ea229a35183c6f762f658d"
)
FULL_REFERENCE_SHA256 = (
    "4968c07ce87f1cf833aad39a6ac3852146ae7c6f241e92fd5e79f7b707bf8296"
)


def preserved_projection(text: str) -> str:
    replacements = (
        (r"(?m)^Следующие пороги .*`готово`:$", "<HARD_GATE_CROSSREF>"),
        (r"(?m)^- `Рубрика доводов`: .*$", "<OUTPUT_CROSSREF>"),
        (
            r"(?ms)^## Рубрика качества доводов\n.*?"
            r"(?=^## Карта фактов для допустимости$)",
            "<TARGET_SECTION>\n\n",
        ),
    )
    for pattern, replacement in replacements:
        matches = re.findall(pattern, text)
        if len(matches) != 1:
            raise AssertionError((pattern, len(matches)))
        text = re.sub(pattern, replacement, text, count=1)
    return text


class ComplaintQaScalarReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = REFERENCE.read_text(encoding="utf-8")
        self.section = self.text.split("## Рубрика качества доводов", 1)[1].split(
            "\n## Карта фактов для допустимости", 1
        )[0]

    def test_scalar_rubric_and_ranges_are_absent(self) -> None:
        for marker in (
            "Оцени каждый основной довод от 0 до 2",
            "| Критерий | 0 | 1 | 2 |",
            "`10-12`",
            "`7-9`",
            "`4-6`",
            "`0-3`",
            "низкий балл",
            "средний балл",
            "таблица 0-2",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.text)
        self.assertIsNone(re.search(r"(?m)^- `\d+-\d+`:", self.section))
        self.assertIn(
            "Следующие пороги проверяются отдельно от эвристической проверки "
            "качества доводов и блокируют `готово`:",
            self.text,
        )

    def test_six_independent_checks_preserve_all_eighteen_meanings(self) -> None:
        self.assertIn("## Рубрика качества доводов", self.text)
        self.assertIn(
            "| Критерий | Подтверждено | Предупреждение | Недостаточно данных |",
            self.text,
        )
        for dimension in DIMENSIONS:
            with self.subTest(dimension=dimension):
                self.assertEqual(self.section.count(f"| {dimension} |"), 1)
        for dimension, expected_columns in ROW_MEANINGS.items():
            match = re.search(
                rf"(?m)^\| {re.escape(dimension)} \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
                self.section,
            )
            self.assertIsNotNone(match, dimension)
            for column_number, expected_fragments in enumerate(expected_columns, start=1):
                for fragment in expected_fragments:
                    with self.subTest(
                        dimension=dimension,
                        column=column_number,
                        fragment=fragment,
                    ):
                        self.assertIn(fragment, match.group(column_number), dimension)

    def test_statuses_are_heuristic_non_compensating_and_fail_closed(self) -> None:
        for status in ("`подтверждено`", "`предупреждение`", "`недостаточно данных`"):
            self.assertIn(status, self.text)
        self.assertIn(HEURISTIC_SCOPE, self.text)
        self.assertIn(
            "Статусы не суммируются, не усредняются, не взвешиваются и не "
            "компенсируют друг друга.",
            self.text,
        )
        self.assertIn(
            "Недостаточно данных создает блокирующую задачу сбора или проверки "
            "материала для этого довода",
            self.text,
        )
        self.assertIn(
            "`fail/unknown` обязательной проверки",
            self.text,
        )
        self.assertIn("краткую причину и идентификаторы доказательств", self.section)
        self.assertIn(
            "Отсутствие пользовательской юридической выжимки само по себе этого "
            "статуса не создает",
            self.section,
        )
        self.assertIn(
            "отсутствие известного паттерна само по себе не является дефектом новой линии",
            self.section,
        )
        self.assertIn(
            "Если корпусная опора не заявлена, после завершенной проверки прямых "
            "официальных опор зафиксируй `подтверждено`, но не приписывай линии "
            "совпадающий паттерн",
            self.section,
        )
        for portfolio_status in ("strong", "mixed", "weak"):
            self.assertNotIn(f"`{portfolio_status}`", self.section)

    def test_four_practical_actions_are_preserved_without_score_thresholds(self) -> None:
        for action in (
            "вести как основной",
            "нужен ремонт или поддержка",
            "вспомогательный или переработать",
            "снять, чтобы не вредил жалобе",
        ):
            with self.subTest(action=action):
                self.assertIn(action, self.text)
        self.assertIn("явного выбора человека", self.text)
        self.assertIn(
            "`вести / чинить / оставить вспомогательным / переработать / снять`",
            self.text,
        )
        self.assertIn(
            "`Рубрика доводов`: независимые статусы по шести критериям и решение",
            self.text,
        )

    def test_document_structure_and_toc_anchors_are_preserved(self) -> None:
        self.assertEqual(len(re.findall(r"(?m)^## ", self.text)), 18)
        toc_anchors = re.findall(r"(?m)^- \[[^]]+\]\(#([^)]+)\)$", self.text)
        self.assertEqual(len(toc_anchors), 17)

        def anchor_for_heading(heading: str) -> str:
            anchor = re.sub(r"[^\w\- ]", "", heading.lower())
            return re.sub(r" +", "-", anchor.strip())

        heading_anchors = {
            anchor_for_heading(heading)
            for heading in re.findall(r"(?m)^#{2,6} (.+)$", self.text)
        }
        self.assertTrue(set(toc_anchors).issubset(heading_anchors))
        self.assertIn(
            "- [Рубрика качества доводов](#рубрика-качества-доводов)",
            self.text,
        )

    def test_everything_outside_the_approved_replacement_scope_is_exact(self) -> None:
        encoded = self.text.encode("utf-8")
        self.assertEqual(self.text.count("\n"), 344)
        self.assertEqual(len(encoded), 43_067)
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), FULL_REFERENCE_SHA256)

        projection = preserved_projection(self.text)
        self.assertEqual(projection.count("\n"), 311)
        self.assertEqual(len(projection.encode("utf-8")), 35_078)
        self.assertEqual(
            hashlib.sha256(projection.encode("utf-8")).hexdigest(),
            PRESERVED_PROJECTION_SHA256,
        )

    def test_runtime_payload_and_exact_skill_backlink_are_preserved(self) -> None:
        payload = {
            path.relative_to(QA_ROOT).as_posix()
            for path in canonical.payload_files(QA_ROOT)
        }
        self.assertIn("references/workflow-reference.md", payload)
        self.assertIn(
            "`references/workflow-reference.md` — подробный checklist и rewrite map.",
            SKILL.read_text(encoding="utf-8"),
        )

    def test_controlling_non_scalar_contracts_remain_explicit(self) -> None:
        skill_text = SKILL.read_text(encoding="utf-8")
        evaluation = (
            REPO
            / "skills"
            / "ksrf-explore-arguments"
            / "references"
            / "evaluation-and-promotion.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Не сворачивай проверку в разрешающий scalar score", skill_text)
        self.assertIn("Юридические hard gates нельзя компенсировать", skill_text)
        self.assertIn("`unknown` создаёт blocking task, а не средний балл", evaluation)
        self.assertIn("сравни без обязательной суммы", evaluation)


if __name__ == "__main__":
    unittest.main()
