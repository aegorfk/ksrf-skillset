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
    "16": SKILL_ROOT / "references" / "example-16-p-2017.md",
    "22": SKILL_ROOT / "references" / "example-22-p-2021.md",
    "30": SKILL_ROOT / "references" / "example-30-p-2020.md",
    "275": SKILL_ROOT / "references" / "example-275-o-p-2007.md",
    "33": SKILL_ROOT / "references" / "example-33-p-2026.md",
    "39": SKILL_ROOT / "references" / "example-39-p-2019.md",
    "37": SKILL_ROOT / "references" / "example-37-p-2024.md",
    "44": SKILL_ROOT / "references" / "example-44-p-2026.md",
    "52": SKILL_ROOT / "references" / "example-52-p-2024.md",
}
PUBLIC_DOCS = {
    "readme": REPO / "README.md",
    "methodology": REPO / "docs" / "KSRF_SKILLS_METHODOLOGY.md",
    "sources": REPO / "docs" / "KSRF_PROJECT_WORK_AND_PUBLIC_SOURCES.md",
}
AUTHORS = REPO / "docs" / "KSRF_ANALYZED_AUTHORS.md"
NORM_MAP = (
    REPO
    / "skills"
    / "ksrf-complaint-facts-demands"
    / "references"
    / "norm-application-defect-map.md"
)
QA_SKILL = REPO / "skills" / "ksrf-complaint-qa" / "SKILL.md"
EVAL = SKILL_ROOT / "evals" / "evals.json"
EVAL_SHA256 = "80942d11f1a2cc78048951783988942c7f8d491ca6515ffe3468d55bd0ab63da"
TRIGGER_EVAL = SKILL_ROOT / "evals" / "trigger-evals.json"
TRIGGER_EVAL_SHA256 = "07e060025b7e8a94439c89f2afc4354e5ca4d70f419094aad5d8b69eb5ee81d4"
QA_EVAL = REPO / "skills" / "ksrf-complaint-qa" / "evals" / "evals.json"
QA_EVAL_SHA256 = "3fd8b3495006a16a717fca127905b5b99908169f4753c2c0c603702efb730b71"
REVIEWED_RUNTIME_FILES = {
    OWNER: (
        227,
        33892,
        "bc5d83a23252829317042b12c9c59bec83f3909b3511f29c0be502fd31725f76",
    ),
    EXAMPLES["39"]: (
        83,
        18609,
        "efc5e974585e936723aae04fc2241b2b31a9cb94b73b9dfa6baba6f8256a6088",
    ),
    EXAMPLES["30"]: (
        80,
        17_811,
        "67a8acab2aa483527b1aec1536ddd1ef707d536f4bc1b1e40eea528338fe6511",
    ),
    EXAMPLES["16"]: (
        139,
        27_050,
        "881649bc6b2f691c89110739962e04ab0229a28298ec840b9fe1448f8d5e64da",
    ),
    EXAMPLES["22"]: (
        135,
        24_095,
        "b2afb472ab99a9cc51398256ac05f07ed40fc2bd94244fb06c3dedeaa96d8e68",
    ),
    EXAMPLES["275"]: (
        136,
        19_392,
        "82bde507e71d0e5a09d76a598517d0ddcb687d2e643e5d6ade542b5a44508d07",
    ),
    EXAMPLES["33"]: (
        149,
        23_934,
        "c848cbb694a2b45810ebf1236c8a16ae95247cbcbe485c3aa3ac3233e4d68818",
    ),
    EXAMPLES["37"]: (
        123,
        17_809,
        "cf7bb1e91eb32b912ac12b29b8cd4fe01e5f222cf1c049e8180195fdbf2fe154",
    ),
    EXAMPLES["44"]: (
        144,
        21_964,
        "c8a82feed736da88844ec979a342cca8dc320eed3e74639f64a8c41ef77b57db",
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
    "39": {
        "sha": "c73b5f65d1f76bb965b69487c12621fab97f4bc5d9ec5087d621ce60aa233ed7",
        "urls": (
            "https://academia.ilpp.ru/wp-content/uploads/2019/12/%D0%A8%D0%B0%D1%88%D0%B5%D0%B2%D0%B0_%D0%96%D0%B0%D0%BB%D0%BE%D0%B1%D0%B0-%D0%9A%D0%A1_17-03-2019.pdf",
            "https://ilpp.ru/legal-practice/deti-gulaga",
            "https://doc.ksrf.ru/decision/KSRFDecision442846.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3.", "H4.", "H5."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 6,
        "checklist_points": 8,
        "markers": (
            "Григорий Викторович Вайпан",
            "17 марта 2019 года",
            "ст. 13 Закона РФ № 1761-1",
            "п. 3 и 5 ст. 7",
            "п. 1 ч. 1 и ч. 2 ст. 8",
            "cb3cf84207bf3c127776d641e968dc6c65804b0cecf8eb93f0c58d0ebbf3b10f",
            "не является персональным прогнозом",
            "не является позицией большинства",
        ),
    },
    "30": {
        "sha": "8cb93fd1ea54bd034c4e3988cd871bffda514d67379a47c67b99b9e51b311a61",
        "urls": (
            "https://academia.ilpp.ru/wp-content/uploads/2020/03/%D0%9E%D0%B4%D0%BD%D0%BE%D0%B4%D0%B2%D0%BE%D1%80%D1%86%D0%B5%D0%B2%D1%8B-%D0%A1%D0%90%D0%99%D0%A2-19.03.2020.pdf",
            "https://ilpp.ru/legal-practice/zhilye",
            "https://academia.ilpp.ru/blog/30x30/good-faith-purchaser/",
            "https://doc.ksrf.ru/decision/KSRFDecision476600.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3.", "H4."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 5,
        "checklist_points": 8,
        "markers": (
            "Григорий Викторович Вайпан",
            "представителем заявителей и подписантом",
            "28 ноября 2019 года",
            "ч. 1 ст. 439 ГПК РФ",
            "п. 4 ч. 1 ст. 43",
            "ч. 3 и 5 ст. 79",
            "Единоличное авторство из подписи не выводится",
            "на дату соответствующего постановления",
            "не является текстом жалобы или актом суда",
            "повторная загрузка с сайта КС возвращала 403",
            "непродолжение исполнения не равно отмене решения",
            "сохраняющее толкование",
        ),
    },
    "16": {
        "sha": "ce95e77dbe8ba7a6ae576d734e77347704879a64420049debd8e87fbdced9624",
        "urls": (
            "https://ilpp.ru/legal-practice/zhilye",
            "https://epam.ru/ru/news/view/dmitrii-stepanov-zashchitil-interesy-doveritelya-v-konstitutsionnom-sude-rf",
            "https://epam.ru/ru/media/view/dobrosovestnye-priobretateli-protiv-nedobrosovestnogo-gosudarstva-delo-aleksandra-dubovtsa-v-konstitutsionnom-sude",
            "https://www.ksrf.ru/doc/KSRFDecision276597.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3.", "H4.", "H5."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 8,
        "checklist_points": 9,
        "markers": (
            "Александра Николаевича Дубовца",
            "Дмитрием Ивановичем Степановым",
            "Ольга Германовна Подоплелова",
            "ed5e85df2f0d7d5c0efaac0c70b0aff127a9b776c828e9d5546a90f999e3ff24",
            "пункта 1 статьи 302 ГК РФ",
            "Никулинского районного суда",
            "вывод об авторстве текста из подписи не делается",
            "`principal`:",
            "`reserve`:",
            "`adverse`:",
            "не признал само понятие добросовестного приобретателя",
            "пересмотр решений А.Н. Дубовца",
        ),
    },
    "22": {
        "sha": "13865fccea652571e7625b4fc407ccdacf696321fb7ea43bee87366a48b2611c",
        "urls": (
            "https://prodoctorov.ru/info/legal-case/3/",
            "https://companies.rbc.ru/news/0FqyrMQM55/ekspert-medroket-provela-zanyatie-po-zaschite-reputatsii-dlya-studentov-kubgu/",
            "https://doc.ksrf.ru/decision/KSRFDecision535809.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3.", "H4.", "H5."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 7,
        "checklist_points": 9,
        "markers": (
            "ООО «МедРейтинг»",
            "Сергеем Ростиславовичем Федосовым",
            "Тамары Сергеевны Тимошенко",
            "пункта 8 части 1 статьи 6 Федерального закона № 152-ФЗ",
            "№ 14-КГ19-15",
            "метаданных документа не используются как достаточное основание",
            "`principal`:",
            "`reserve`:",
            "`experimental`:",
            "систематическом злоупотреблении",
            "ступенчатый способ защиты",
        ),
    },
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
    "33": {
        "sha": "42eae9f2330adf520c1bfc1a454da52b93e17e8965db09672a045232c7cd6cec",
        "urls": (
            "https://www.klgd.ru/administration/",
            "https://www.ksrf.ru/doc/KSRFDecision909841.pdf",
        ),
        "hypotheses": ("H1.", "H2.", "H3.", "H4."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 7,
        "checklist_points": 8,
        "markers": (
            "Администрация городского округа «Город Калининград»",
            "Елены Ивановны Дятловой",
            "пункт 32 части 1 статьи 16",
            "подпункт «б» пункта 3",
            "№ 71-КАС24-82-КЗ",
            "метаданные PDF не используются как достаточное основание",
            "пересмотру",
            "право требовать последующего возмещения",
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
            "профессиональную страницу, а не копию жалобы",
            "`falsifier`:",
            "`reserve relief`:",
            "не могут признаваться допустимыми",
            "оставить их без изменения",
        ),
    },
    "44": {
        "sha": "3278936be1237c0d984e5102e35950d09fdc961c0acd40f9132df7ed65486dfb",
        "urls": (
            "http://publication.pravo.gov.ru/document/0001202607010001",
            "https://sila-slova.pro/",
            "https://sila-slova.pro/komanda/chelohsaev-timur-adamovich/",
            "https://sila-slova.pro/komanda/advokat-vitaliy-katsko/",
        ),
        "hypotheses": ("H1.", "H2.", "H3.", "H4."),
        "facts": (),
        "gate_rows": 0,
        "result_points": 7,
        "checklist_points": 8,
        "markers": (
            "Николай Николаевич Каримов",
            "Тимур Челохсаев",
            "Виталий Кацко",
            "АБ Краснодарского края «Сила Слова»",
            "пункт 2 части первой и часть пятую статьи 108",
            "часть четвёртую статьи 210 УПК РФ",
            "профессиональные страницы, а не копии жалобы",
            "`falsifier`:",
            "`principal relief`:",
            "пересмотру не подлежит",
            "не влечёт автоматического заключения под стражу",
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
        self.assertIn("девять ретроспективных двухпроходных разборов", self.owner)

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
            "Девять ретроспективных карточек не являются такими прогонами",
        ):
            self.assertIn(wording, docs["readme"])

        for wording in (
            "Служебные файлы проверки остаются только в исходном репозитории",
            "не устанавливаются пользователю",
            "Девять пользовательских карточек — ретроспективные двухпроходные разборы",
            "Для активного дела без последующего акта КС РФ работа на этом останавливается",
        ):
            self.assertIn(wording, docs["methodology"])

        for wording in (
            "Служебные `evals.json` и `trigger-evals.json` остаются в исходном репозитории",
            "не устанавливаются пользователю",
            "Подробные примеры и тематические карточки — не такие прогоны",
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

    def test_source_evals_are_digest_bound_and_cleanroom_excludes_them(self) -> None:
        self.assertEqual(hashlib.sha256(EVAL.read_bytes()).hexdigest(), EVAL_SHA256)
        self.assertEqual(
            hashlib.sha256(QA_EVAL.read_bytes()).hexdigest(), QA_EVAL_SHA256
        )
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

    def test_medrating_method_and_public_credit_are_role_bound(self) -> None:
        norm_map = NORM_MAP.read_text(encoding="utf-8")
        qa_skill = QA_SKILL.read_text(encoding="utf-8")
        sources = PUBLIC_DOCS["sources"].read_text(encoding="utf-8")
        authors = AUTHORS.read_text(encoding="utf-8")

        for marker in (
            "## DataPublicationBalanceMatrix",
            "Категории данных",
            "Систематическое злоупотребление",
            "Ступенчатый способ защиты",
            "ABSTAIN_DATA_PUBLICATION_BALANCE",
        ):
            self.assertIn(marker, norm_map)
        for marker in (
            "DataPublicationBalanceMatrix",
            "статус распространителя",
            "ступенчатый способ защиты",
            "систематического злоупотребления",
        ):
            self.assertIn(marker, qa_skill)

        for marker in (
            "ООО «МедРейтинг»",
            "Сергеем Ростиславовичем Федосовым",
            "https://prodoctorov.ru/info/legal-case/3/",
            "https://doc.ksrf.ru/decision/KSRFDecision535809.pdf",
        ):
            self.assertIn(marker, sources)
        for marker in (
            "Тамара Сергеевна Тимошенко",
            "Способы защиты деловой репутации",
            "https://companies.rbc.ru/news/0FqyrMQM55/ekspert-medroket-provela-zanyatie-po-zaschite-reputatsii-dlya-studentov-kubgu/",
        ):
            self.assertIn(marker, authors)

        combined = "\n".join((sources, authors))
        self.assertNotIn("автор жалобы — Сергей Ростиславович Федосов", combined)
        self.assertNotIn("публичный текст жалобы", section(sources, "## Публичные жалобы и связанные акты КС РФ").split("ООО «МедРейтинг»", 1)[1].split("\n", 1)[0])

    def test_dubovets_method_and_public_credit_are_role_bound(self) -> None:
        norm_map = NORM_MAP.read_text(encoding="utf-8")
        qa_skill = QA_SKILL.read_text(encoding="utf-8")
        sources = PUBLIC_DOCS["sources"].read_text(encoding="utf-8")
        authors = AUTHORS.read_text(encoding="utf-8")

        for marker in (
            "## PublicOwnerRelianceAndRiskMatrix",
            "Сведения на дату сделки",
            "Действия и бездействие публичного собственника",
            "Раздельные результаты",
            "ABSTAIN_PUBLIC_OWNER_RISK",
        ):
            self.assertIn(marker, norm_map)
        for marker in (
            "PublicOwnerRelianceAndRiskMatrix",
            "сведения на дату сделки",
            "публичного бездействия",
            "полностью подтверждённой",
        ):
            self.assertIn(marker, qa_skill)

        for marker in (
            "Александр Николаевич Дубовец",
            "Дмитрий Иванович Степанов",
            "https://ilpp.ru/legal-practice/zhilye",
            "https://epam.ru/ru/news/view/dmitrii-stepanov-zashchitil-interesy-doveritelya-v-konstitutsionnom-sude-rf",
            "https://www.ksrf.ru/doc/KSRFDecision276597.pdf",
        ):
            self.assertIn(marker, sources)
        for marker in (
            "Ольга Германовна Подоплелова",
            "Дмитрий Иванович Степанов",
            "Добросовестные приобретатели против недобросовестного государства",
            "https://epam.ru/ru/media/view/dobrosovestnye-priobretateli-protiv-nedobrosovestnogo-gosudarstva-delo-aleksandra-dubovtsa-v-konstitutsionnom-sude",
        ):
            self.assertIn(marker, authors)

        combined = "\n".join((sources, authors))
        self.assertNotIn("автор жалобы — Дмитрий Иванович Степанов", combined)
        self.assertNotIn("автор жалобы — Ольга Германовна Подоплелова", combined)


if __name__ == "__main__":
    unittest.main()
