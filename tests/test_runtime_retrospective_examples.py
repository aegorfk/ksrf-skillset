from __future__ import annotations

import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

import skillset_file_contract as contract  # noqa: E402
from install_skillset import copy_skillset  # noqa: E402


SKILL_ROOT = REPO / "skills" / "ksrf-explore-arguments"
OWNER = SKILL_ROOT / "SKILL.md"
EXAMPLES = {
    "275": SKILL_ROOT / "references" / "example-275-o-p-2007.md",
    "37": SKILL_ROOT / "references" / "example-37-p-2024.md",
    "52": SKILL_ROOT / "references" / "example-52-p-2024.md",
}
PUBLIC_DOCS = {
    "readme": REPO / "README.md",
    "methodology": REPO / "docs" / "KSRF_SKILLS_METHODOLOGY.md",
    "sources": REPO / "docs" / "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md",
}
EVAL = SKILL_ROOT / "evals" / "evals.json"
EVAL_SHA256 = "a2174e6c286ad071243453ce60a0db126bfc299a6de79e4d1fc8f9c79297e607"
TRIGGER_EVAL = SKILL_ROOT / "evals" / "trigger-evals.json"
TRIGGER_EVAL_SHA256 = "07e060025b7e8a94439c89f2afc4354e5ca4d70f419094aad5d8b69eb5ee81d4"
REVIEWED_RUNTIME_FILES = {
    OWNER: (
        199,
        28_994,
        "db3edad49e64fc3a0a80937827010a13f1d87fbbb52ea8dbeb81a02e532332aa",
    ),
    EXAMPLES["275"]: (
        136,
        19_392,
        "82bde507e71d0e5a09d76a598517d0ddcb687d2e643e5d6ade542b5a44508d07",
    ),
    EXAMPLES["37"]: (
        123,
        17_869,
        "0ab9dd02e1899f63874d6e5095032017f8483deec49910e37abbd8d9df975d32",
    ),
    EXAMPLES["52"]: (
        212,
        28_426,
        "3f781cb272320429774a855cb083a0c85cddc846825fcce33478dbf90ccd6897",
    ),
}

FORBIDDEN_RUNTIME_WORDING = (
    "benchmark",
    "forward-test",
    "forward-evaluation",
    "eval-контур",
    "commit артефактов",
    "artifact commit",
    "blind firewall",
    "fixture",
    "hash/private ID",
    "replay",
    "Input-only",
    "Outcome-blind",
    "Held-out outcome",
    "Research replay",
    "Adaptive replay",
    "Критерии регрессии",
    "Скилл проходит",
    "ретроспективных replay",
    "ретроспективным replay",
    "Пример применён корректно",
)

COMMON_HEADINGS = (
    "## Что следует только из исходного материала",
    "## Портфель гипотез до сверки с последующим актом",
    "## Что установил последующий акт КС РФ",
    "## Контрольные вопросы для нового дела",
)

CASE_SURFACE = {
    "275": {
        "sha": "f318b6b353830146aa30270762c713c3250fd635832561cf8661e9fa03cb7ac7",
        "urls": (
            "https://studopedia.net/19_11065_konstitutsii-rossiyskoy-federatsii-stati-.html",
            "https://rplbg.com/",
            "https://www.ksrf.ru/doc/KSRFDecision16344.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3."),
        "facts": (),
        "gate_rows": 7,
        "result_points": 4,
        "checklist_points": 7,
        "markers": (
            "Сергей Юрьевич Линев",
            "к.ю.н. Е. С. Герасимова",
            "пункт 2 статьи 26",
            "статья 413 ТК РФ",
            "статьями 5, 252 и 413 ТК РФ",
            "частный локальный оригинал не входит в репозиторий",
            "сайт профсоюза — профессиональным каналом, а не доказательством каждого предложения жалобы",
            "`falsifier`:",
            "`reserve relief`:",
            "КС РФ отказал в принятии жалобы",
            "формальный отказ нельзя автоматически маркировать",
        ),
    },
    "37": {
        "sha": "1540b55263794f91d2271a3bd445bb7dfa4bec6fd1cc3e89257192d39c71df30",
        "urls": (
            "https://borzoff.com/",
            "https://www.ksrf.ru/doc/KSRFDecision770474.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 5,
        "checklist_points": 6,
        "markers": (
            "Е.В. Емельянов",
            "статья 71 УПК РФ",
            "статью 70 УПК РФ",
            "статье 61 УПК РФ",
            "часть вторая статьи 71",
            "точная публичная ссылка на текст жалобы не установлена",
            "`falsifier`:",
            "`reserve relief`:",
            "не могут признаваться допустимыми",
            "оставить их без изменения",
        ),
    },
    "52": {
        "sha": "1e8bc7e4115963cbfdc2fbe674623ec13ea4f044b314badcb2a8ed636810d6c3",
        "urls": ("https://www.ksrf.ru/doc/KSRFDecision794940.pdf",),
        "hypotheses": ("H1.", "H2.", "H3.", "H4.", "H5."),
        "facts": ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9"),
        "gate_rows": 7,
        "result_points": 6,
        "checklist_points": 8,
        "markers": (
            "п. 1 ст. 308.3 ГК РФ",
            "ч. 3 ст. 206 ГПК РФ",
            "ст. 419 ТК РФ",
            "обезличенный image-only PDF",
            "частный локальный оригинал не входит в репозиторий",
            "`2022`",
            "`2002`",
            "прошлый период",
            "`principal`: H1",
            "`reserve`: H2 и H3",
            "`experimental`: H4",
            "`likely rejected`: H5",
            "Сам по себе пересмотр не означает автоматического взыскания",
        ),
    },
}


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^## |\Z)",
        text,
    )
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


def numbered_points(text: str) -> int:
    return len(re.findall(r"(?m)^\d+\. ", text))


def numbered_items(text: str) -> list[str]:
    return re.findall(r"(?ms)^\d+\. (.*?)(?=^\d+\. |\Z)", text)


def bullet_points(text: str) -> int:
    return len(re.findall(r"(?m)^- ", text))


def anchor_for_heading(heading: str) -> str:
    anchor = re.sub(r"[^\w\- ]", "", heading.lower())
    return re.sub(r" +", "-", anchor.strip())


class RuntimeRetrospectiveExamplesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = OWNER.read_text(encoding="utf-8")
        self.examples = {
            name: path.read_text(encoding="utf-8") for name, path in EXAMPLES.items()
        }

    def test_reviewed_runtime_files_have_exact_digests(self) -> None:
        for path, (expected_lines, expected_bytes, expected_sha256) in (
            REVIEWED_RUNTIME_FILES.items()
        ):
            content = path.read_bytes()
            with self.subTest(path=path):
                self.assertEqual(content.count(b"\n"), expected_lines)
                self.assertEqual(len(content), expected_bytes)
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected_sha256)

    def test_installed_examples_use_plain_two_pass_language(self) -> None:
        for name, text in self.examples.items():
            with self.subTest(example=name):
                for wording in FORBIDDEN_RUNTIME_WORDING:
                    self.assertNotIn(wording.casefold(), text.casefold())
                for heading in COMMON_HEADINGS:
                    self.assertEqual(text.count(heading), 1)
                positions = [text.index(heading) for heading in COMMON_HEADINGS]
                self.assertEqual(positions, sorted(positions))
                self.assertIn("не шаблон жалобы", text)
                self.assertIn("не прогноз", text)
                self.assertIn("подготовлена после", text)
                self.assertIn("Сначала зафиксируй", text)
                self.assertIn("Только после этого открой", text)
                self.assertIn("не подгоняй", text)
                result = section(text, "## Что установил последующий акт КС РФ")
                for source_gate in (
                    "официальным полным текстом",
                    "указанное место",
                    "автора вывода",
                    "контекст",
                    "редакцию нормы",
                    "останови второй проход",
                    "вывод непроверенным",
                    "учитывай только редакцию нормы, которую проверял КС РФ",
                    "применимость к новому делу устанавливай заново",
                ):
                    self.assertIn(source_gate, result)
                for outcome in numbered_items(result):
                    self.assertIn("официальный PDF", outcome)
                    self.assertIn("КС РФ", outcome)
                    self.assertIn("контекст", outcome)

        for wording in FORBIDDEN_RUNTIME_WORDING:
            self.assertNotIn(wording.casefold(), self.owner.casefold())
        self.assertIn("три ретроспективных двухпроходных разбора", self.owner)

    def test_case_specific_legal_and_source_surface_is_preserved(self) -> None:
        for name, expected in CASE_SURFACE.items():
            text = self.examples[name]
            with self.subTest(example=name):
                self.assertIn(expected["sha"], text)
                for url in expected["urls"]:
                    self.assertIn(url, text)
                for hypothesis in expected["hypotheses"]:
                    self.assertEqual(text.count(f"### {hypothesis}"), 1)
                for finding in expected["facts"]:
                    self.assertEqual(text.count(f"| {finding} |"), 1)
                for marker in expected["markers"]:
                    self.assertIn(marker, text)

                if expected["gate_rows"]:
                    gates = section(text, "## Hard gates по одной жалобе")
                    self.assertEqual(
                        len(re.findall(r"(?m)^\| (?!-{3})[^\n]+\|$", gates)) - 1,
                        expected["gate_rows"],
                    )

                result = section(text, "## Что установил последующий акт КС РФ")
                self.assertEqual(numbered_points(result), expected["result_points"])

    def test_each_example_ends_with_a_new_case_checklist(self) -> None:
        for name, expected in CASE_SURFACE.items():
            text = self.examples[name]
            checklist = section(text, "## Контрольные вопросы для нового дела")
            with self.subTest(example=name):
                for non_scoring_instruction in (
                    "проверь каждый вопрос отдельно",
                    "«подтверждено», «пробел» или «не применимо»",
                    "Общий итоговый балл не выводи",
                ):
                    self.assertIn(non_scoring_instruction, checklist)
                for transfer_boundary in (
                    "не являются готовыми ответами для любого дела",
                    "собственным первичным документам",
                    "Исторический закрытый оригинал не требуется",
                    "не освобождает от сбора материалов нового дела",
                ):
                    self.assertIn(transfer_boundary, checklist)
                self.assertEqual(bullet_points(checklist), expected["checklist_points"])
                for safeguard in (
                    "исход",
                    "примен",
                    "гипотез",
                    "средств",
                ):
                    self.assertIn(safeguard, checklist.lower())
                for stop_rule in (
                    "у нового дела ещё нет последующего акта КС РФ",
                    "остановись после первого прохода",
                    "обычные обязательные проверки",
                    "ручной выбор",
                    "второй проход не имитируй",
                    "официальный полный текст",
                ):
                    self.assertIn(stop_rule.casefold(), checklist.casefold())
                for forbidden in (
                    "Скилл проходит",
                    "проходной балл",
                    "итоговая оценка",
                    "Пример применён корректно",
                    "готова к подаче",
                ):
                    self.assertNotIn(forbidden.casefold(), checklist.casefold())

    def test_case_specific_legal_boundaries_do_not_drift(self) -> None:
        gates_275 = section(self.examples["275"], "## Hard gates по одной жалобе")
        statuses_275 = [
            status
            for status in re.findall(
                r"(?m)^\| [^|]+ \| ([^|]+) \| [^|]+ \|$", gates_275
            )
            if status not in {"Предварительный статус", "---"}
        ]
        self.assertEqual(
            statuses_275,
            [
                "pass candidate",
                "pass candidate",
                "pass candidate",
                "pass candidate",
                "pass candidate",
                "supporting only",
                "review needed",
            ],
        )
        for boundary in (
            "формальный отказ нельзя автоматически маркировать как отсутствие полезной правовой позиции",
            "нельзя выдавать мотивировку отказного определения за удовлетворение первоначальной просительной части",
            "Материалы МОТ используются для проверки широты запрета",
        ):
            self.assertIn(boundary, self.examples["275"])

        for boundary in (
            "не позволяет скиллу автоматически выводить оправдание, отмену приговора",
            "вправе оставить их без изменения",
            "не тождественны автоматическому выводу о результате уголовного дела",
        ):
            self.assertIn(boundary, self.examples["37"])

        gates_52 = section(self.examples["52"], "## Hard gates по одной жалобе")
        statuses_52 = [
            status
            for status in re.findall(
                r"(?m)^\| [^|]+ \| ([^|]+) \| [^|]+ \|$", gates_52
            )
            if status not in {"Предварительный статус", "---"}
        ]
        self.assertEqual(
            statuses_52,
            [
                "pass candidate",
                "pass candidate",
                "pass с замечанием",
                "pass candidate",
                "unknown",
                "review needed",
                "pending",
            ],
        )
        relations_52 = re.findall(
            r"(?m)^\| F\d+ \| [^|]+ \| [^|]+ \| ([^|]+) \|$",
            self.examples["52"],
        )
        self.assertEqual(
            relations_52,
            [
                "supports H1/H2",
                "supports separation; weakens H4/H5",
                "supports H1",
                "supports practice-meaning claim",
                "supports H1/H2",
                "weakens drafting quality; opens H2/H3 research",
                "weakens original relief; supports H1 narrow relief",
                "source-integrity warning",
                "blocks using that fact in input",
            ],
        )
        for boundary in (
            "производство по п. 1 ст. 308.3 ГК РФ",
            "производство по ст. 419 ТК РФ",
            "не означает автоматического взыскания",
        ):
            self.assertIn(boundary, self.examples["52"])

    def test_contents_links_match_second_level_headings(self) -> None:
        for name, text in self.examples.items():
            toc_anchors = re.findall(r"(?m)^- \[[^]]+\]\(#([^)]+)\)$", text)
            headings = [
                anchor_for_heading(heading)
                for heading in re.findall(r"(?m)^## (.+)$", text)
                if heading != "Содержание"
            ]
            with self.subTest(example=name):
                self.assertEqual(toc_anchors, headings)

    def test_owner_routes_once_to_each_installed_example(self) -> None:
        for path in EXAMPLES.values():
            relative = path.relative_to(SKILL_ROOT).as_posix()
            with self.subTest(path=relative):
                self.assertEqual(self.owner.count(relative), 1)
        for wording in (
            "исходные жалобы и их полнотекстовые производные",
            "сначала фиксируются факты, гипотезы, альтернативы, опровержения, пробелы",
            "только затем открывается последующий официальный акт",
            "не доказывает способность предсказывать",
        ):
            self.assertIn(wording.casefold(), self.owner.casefold())

    def test_public_docs_separate_retrospective_cards_from_source_evals(self) -> None:
        docs = {
            name: path.read_text(encoding="utf-8")
            for name, path in PUBLIC_DOCS.items()
        }
        for name, text in docs.items():
            with self.subTest(document=name):
                self.assertIn("ретроспектив", text.casefold())
                self.assertIn("пользовательск", text.casefold())
                self.assertIn("не доказ", text.casefold())
                self.assertIn("известн", text.casefold())

        for wording in (
            "Каталог `evals/` проверяется отдельно и не входит в пользовательскую установку",
            "заранее зафиксированный вход без известного исхода",
            "Три ретроспективные карточки не являются такими прогонами",
        ):
            self.assertIn(wording, docs["readme"])

        for wording in (
            "Служебные файлы проверки остаются только в исходном репозитории",
            "не устанавливаются пользователю",
            "Три пользовательские карточки — ретроспективные двухпроходные разборы",
            "Для активного дела без последующего акта КС РФ работа на этом останавливается",
        ):
            self.assertIn(wording, docs["methodology"])

        for wording in (
            "Служебные `evals.json` и `trigger-evals.json` остаются в исходном репозитории",
            "не устанавливаются пользователю",
            "Три опубликованные карточки — не такие прогоны",
            "В активном новом деле без последующего акта КС РФ",
            "В историческом деле второй проход допустим только по официальному полному тексту",
        ):
            self.assertIn(wording, docs["sources"])

        combined = "\n".join(docs.values())
        for retired_claim in (
            "воспроизводимая калибровка изменений без подглядывания в известный результат дела",
            "Настроен контур калибровки без подглядывания в исход",
            "результат можно раскрыть только после фиксации прогноза",
        ):
            self.assertNotIn(retired_claim.casefold(), combined.casefold())

    def test_eval_is_unchanged_source_only_and_cleanroom_excludes_it(self) -> None:
        self.assertEqual(hashlib.sha256(EVAL.read_bytes()).hexdigest(), EVAL_SHA256)
        self.assertEqual(
            hashlib.sha256(TRIGGER_EVAL.read_bytes()).hexdigest(),
            TRIGGER_EVAL_SHA256,
        )
        payload = {
            path.relative_to(SKILL_ROOT).as_posix()
            for path in contract.payload_files(SKILL_ROOT)
        }
        self.assertNotIn("evals/evals.json", payload)
        self.assertNotIn("evals/trigger-evals.json", payload)
        for path in EXAMPLES.values():
            self.assertIn(path.relative_to(SKILL_ROOT).as_posix(), payload)

        with tempfile.TemporaryDirectory() as temporary:
            installed_root = Path(temporary) / "skills"
            copy_skillset(REPO / "skills", installed_root)
            installed_skill = installed_root / SKILL_ROOT.name
            self.assertFalse((installed_skill / "evals").exists())
            for path in EXAMPLES.values():
                installed = installed_skill / path.relative_to(SKILL_ROOT)
                with self.subTest(path=path.name):
                    self.assertEqual(installed.read_bytes(), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
