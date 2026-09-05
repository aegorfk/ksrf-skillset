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


REFERENCE_ROOT = REPO / "skills" / "ksrf-argument-patterns" / "references"
DERIVED = REFERENCE_ROOT / "hearing-derived-argument-patterns.md"
CONSTITUTIONAL = REFERENCE_ROOT / "hearing-constitutional-justifications.md"
TECHNIQUES = REFERENCE_ROOT / "hearing-argument-techniques.md"

GUIDES = (DERIVED, CONSTITUTIONAL, TECHNIQUES)

SHARED_STATUS_CONTRACT = (
    "Статусы проверок не суммируются, не усредняются и не превращаются в "
    "показатель готовности. Подтвержденный признак не компенсирует предупреждение, "
    "недостаток данных или состояние `fail/unknown` обязательного gate. "
    "Недостаточно данных создает блокирующую задачу сбора или проверки материала."
)

HEURISTIC_SCOPE_CONTRACT = (
    "Это результаты эвристической проверки, а не новые состояния обязательных "
    "проверок и не вывод о допустимости, юридической корректности, готовности к "
    "подаче или исходе дела."
)


class HearingGuideScalarReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.texts = {path: path.read_text(encoding="utf-8") for path in GUIDES}

    def test_scalar_readiness_vocabulary_is_absent(self) -> None:
        forbidden_literals = (
            "**Автооценка:**",
            "Автооценка должна",
            "**Автоматизированная оценка дела:**",
            "Оценивай каждый блок от 0 до 2",
            "плюс к перспективности",
            "высокий балл",
            "низкий балл",
            "Снизить оценку",
            "Снижать оценку",
            "Снизить риск",
            "начисляй баллы",
        )
        for path, text in self.texts.items():
            for marker in forbidden_literals:
                with self.subTest(path=path.name, marker=marker):
                    self.assertNotIn(marker, text)
            self.assertIsNone(re.search(r"(?m)^Сумма \d", text), path.name)
            self.assertIsNone(re.search(r"(?m)^- `[^`]+`: [012] -", text), path.name)
            self.assertIsNone(re.search(r"автооценк", text, re.IGNORECASE), path.name)
            self.assertIsNone(
                re.search(r"автоматизированн(?:ая|ой) оценк", text, re.IGNORECASE),
                path.name,
            )
            self.assertIsNone(
                re.search(r"(?<!\w)(?:плюс|минус)(?!\w)", text, re.IGNORECASE),
                path.name,
            )
            self.assertNotIn("`Подтверждено`", text)
            self.assertNotIn("`Предупреждение`", text)

    def test_all_forty_checks_use_one_non_scalar_label(self) -> None:
        expected_counts = {DERIVED: 15, CONSTITUTIONAL: 14, TECHNIQUES: 11}
        for path, expected_count in expected_counts.items():
            with self.subTest(path=path.name):
                self.assertEqual(
                    self.texts[path].count("**Проверка по признакам:**"),
                    expected_count,
                )

    def test_each_guide_declares_independent_statuses_and_non_compensation(self) -> None:
        for path, text in self.texts.items():
            with self.subTest(path=path.name):
                self.assertIn("`подтверждено`", text)
                self.assertIn("`предупреждение`", text)
                self.assertIn("`недостаточно данных`", text)
                self.assertIn(HEURISTIC_SCOPE_CONTRACT, text)
                self.assertIn(SHARED_STATUS_CONTRACT, text)

    def test_numbered_sections_dimensions_and_technique_ids_are_preserved(self) -> None:
        self.assertEqual(
            len(re.findall(r"(?m)^## \d+\. ", self.texts[DERIVED])),
            15,
        )
        self.assertEqual(
            len(re.findall(r"(?m)^## \d+\. ", self.texts[CONSTITUTIONAL])),
            14,
        )

        for dimension in (
            "Норма и применение",
            "Нормативный дефект",
            "Практика/переносимость",
            "Конституционный тест",
            "Материалы",
            "Remedy",
        ):
            self.assertIn(f"`{dimension}`", self.texts[DERIVED])

        for dimension in (
            "Право",
            "Дефект",
            "Тест",
            "Материалы",
            "Просительная часть",
        ):
            self.assertIn(f"`{dimension}`", self.texts[CONSTITUTIONAL])

        expected_codes = {
            "hearing-subject-frame",
            "hearing-practice-meaning",
            "hearing-saving-meaning",
            "hearing-systemic-linkage",
            "hearing-balance-proportionality",
            "hearing-individualization",
            "hearing-effective-protection",
            "hearing-legal-certainty-trust",
            "hearing-equality-comparator",
            "hearing-good-faith-abuse",
            "hearing-remedy-design",
        }
        actual_codes = set(
            re.findall(r"(?m)^\*\*Код:\*\* `([^`]+)`$", self.texts[TECHNIQUES])
        )
        self.assertEqual(actual_codes, expected_codes)

    def test_approved_full_guide_projections_are_exact(self) -> None:
        expected_hashes = {
            DERIVED: "d99c9a92578e93d2b61a49e9c8749419912405dbe2a50c6fedb5ce32d9df9554",
            CONSTITUTIONAL: "c4fd63d1ce4efda5d32b43c6d048106406b1403665e5650aba0823ce5b0074f6",
            TECHNIQUES: "4e47d23d8efc5637ad976cd930c416961069701d69709277f7644e3f7a4d84f8",
        }
        for path, expected_hash in expected_hashes.items():
            with self.subTest(path=path.name):
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    expected_hash,
                )

        source_registry = REFERENCE_ROOT / "hearing_argument_techniques.json"
        self.assertEqual(
            hashlib.sha256(source_registry.read_bytes()).hexdigest(),
            "9910ffedac5d8a1cecba8375d5f99988f1773a7f963e346ef33d210292ef03f7",
        )

    def test_legal_automatic_mechanism_language_is_not_overmatched(self) -> None:
        self.assertIn("автоматизм надо привязывать к норме", self.texts[DERIVED])
        self.assertIn("заданном законом автоматизме", self.texts[DERIVED])
        self.assertIn(
            "автоматизм должен быть конституционно проверен",
            self.texts[CONSTITUTIONAL],
        )
        self.assertIn("Автоматическая санкция или отказ", self.texts[TECHNIQUES])
        self.assertIn(
            "Запрет механического применения без оценки обстоятельств",
            self.texts[TECHNIQUES],
        )
        self.assertIn("переоценить доказательства", self.texts[DERIVED])
        self.assertIn("оценить ход расследования", self.texts[CONSTITUTIONAL])

    def test_admissibility_risk_signals_are_not_weakened(self) -> None:
        self.assertEqual(
            self.texts[DERIVED].count("предупреждение о высоком риске недопустимости"),
            2,
        )
        self.assertIn("высокий риск недопустимости", self.texts[CONSTITUTIONAL])

    def test_known_missing_request_formula_is_warning_not_unknown(self) -> None:
        self.assertIn(
            "в предоставленном проекте просительная формула отсутствует",
            self.texts[CONSTITUTIONAL],
        )
        self.assertIn(
            "`недостаточно данных`, если проект просительной части не предоставлен",
            self.texts[CONSTITUTIONAL],
        )

    def test_internal_table_of_contents_anchors_resolve(self) -> None:
        expected_counts = {DERIVED: 18, CONSTITUTIONAL: 18, TECHNIQUES: 5}

        def anchor_for_heading(heading: str) -> str:
            anchor = re.sub(r"[^\w\- ]", "", heading.lower())
            return re.sub(r" +", "-", anchor.strip())

        for path, expected_count in expected_counts.items():
            text = self.texts[path]
            toc_anchors = re.findall(r"(?m)^- \[[^]]+\]\(#([^)]+)\)$", text)
            heading_anchors = {
                anchor_for_heading(heading)
                for heading in re.findall(r"(?m)^#{2,6} (.+)$", text)
            }
            with self.subTest(path=path.name):
                self.assertEqual(len(toc_anchors), expected_count)
                self.assertTrue(set(toc_anchors).issubset(heading_anchors))

    def test_payload_membership_and_consumer_backlinks_are_preserved(self) -> None:
        payload = {
            path.relative_to(REFERENCE_ROOT.parent).as_posix()
            for path in canonical.payload_files(REFERENCE_ROOT.parent)
        }
        for path in GUIDES:
            self.assertIn(f"references/{path.name}", payload)

        patterns_skill = (
            REPO / "skills" / "ksrf-argument-patterns" / "SKILL.md"
        ).read_text(encoding="utf-8")
        explore_skill = (
            REPO / "skills" / "ksrf-explore-arguments" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "`references/argument-techniques-from-decisions.md`, "
            "`references/hearing-derived-argument-patterns.md`, "
            "`references/hearing-constitutional-justifications.md`, "
            "`references/hearing-argument-techniques.md` — эвристики, вопросы и "
            "stress-tests, не обязательные схемы.",
            patterns_skill,
        )
        self.assertIn(
            "`../ksrf-argument-patterns/references/hearing-constitutional-justifications.md` — "
            "библиотека возможных связок и вопросов, не обязательная схема обоснования.",
            explore_skill,
        )
        self.assertIn(
            "`../ksrf-argument-patterns/references/hearing-derived-argument-patterns.md` и "
            "`../ksrf-argument-patterns/references/hearing-argument-techniques.md` — "
            "материал для stress-test и моделирования заседания.",
            explore_skill,
        )


if __name__ == "__main__":
    unittest.main()
