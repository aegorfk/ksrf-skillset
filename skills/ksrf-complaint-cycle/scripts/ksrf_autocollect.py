#!/usr/bin/env python3
"""Собрать первичный CaseFile из материалов дела для скиллов КС РФ."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


TOOL_DIRS = [
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/opt/anaconda3/bin"),
    Path("/usr/bin"),
    Path("/bin"),
]
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
    r"\s+\d{4}\s*г(?:ода|\.)?)\b",
    re.IGNORECASE,
)
CASE_RE = re.compile(
    r"(?:дел[аоуе]\s*)?(?:N|№)\s*[А-ЯA-Z0-9Ёа-яa-z./-]{2,}(?:\s*/\s*\d{2,4})?",
    re.IGNORECASE,
)
LEGAL_REF_RE = re.compile(
    r"\b(?:(?:п\.|пункт(?:а|ом)?|ч\.|част[ьи]|абз\.|ст\.|стать[ьяеи])\s*"
    r"[\d.]+(?:\s*[-–]\s*[\d.]+)?\s*){1,4}"
    r"(?:Конституци[ияи]\s+РФ|ФКЗ|ГК\s+РФ|ГПК\s+РФ|АПК\s+РФ|КАС\s+РФ|УПК\s+РФ|КоАП\s+РФ|НК\s+РФ|ТК\s+РФ|УК\s+РФ|[Фф]едеральн\w*\s+закона|Закона\s+N|Закона\s+№)?",
    re.IGNORECASE,
)
CONSTITUTION_RE = re.compile(r"(?:ст\.|стать[ьяеи])\s*\d+(?:\.\d+)?\s+Конституци[ияи]\s+(?:РФ|Российской Федерации)", re.IGNORECASE)
CONSTITUTION_LIST_RE = re.compile(
    r"Конституци[ияи]\s+Российской\s+Федерации,?\s*(?:е[её]\s+)?"
    r"стать[ьяеиюм]+\s+([0-9,\s().частией-]{1,120})",
    re.IGNORECASE,
)
KSRF_RE = re.compile(
    r"(?:Постановлени[ея]|Определени[ея])\s+Конституционного\s+Суда\s+(?:РФ|Российской Федерации)"
    r".{0,80}?(?:N|№)\s*[\d-]+-?[ПО]?",
    re.IGNORECASE | re.DOTALL,
)
COURT_RE = re.compile(
    r"\b(?:Конституционный Суд РФ|Конституционный Суд Российской Федерации|Верховный Суд РФ|Верховный Суд Российской Федерации|"
    r"[А-ЯЁ][А-Яа-яЁё -]{2,80}?(?:районный|городской|областной|краевой|республиканский|арбитражный|кассационный|апелляционный)\s+суд[А-Яа-яЁё -]*)\b"
)
STAGE_WORDS = {
    "первая инстанция": re.compile(r"перв\w+\s+инстанц", re.IGNORECASE),
    "апелляция": re.compile(r"апелляц", re.IGNORECASE),
    "кассация": re.compile(r"кассац", re.IGNORECASE),
    "верховный суд": re.compile(r"Верховн\w+\s+Суд", re.IGNORECASE),
    "надзор": re.compile(r"надзор", re.IGNORECASE),
    "конституционный суд": re.compile(r"Конституционн\w+\s+Суд", re.IGNORECASE),
}
APPLIED_WORDS_RE = re.compile(
    r"примен\w+|руководств\w+|истолков\w+|толкован\w+|отказ\w+|не\s+предусмотр\w+|"
    r"не\s+допуска\w+|исключа\w+|запреща\w+|обязыва\w+|позволя\w+",
    re.IGNORECASE,
)
TEST_PATTERNS = {
    "proportionality": {
        "pattern": re.compile(r"соразмер|пропорцион|необходим\w+|чрезмерн|санкц|ограничени", re.IGNORECASE),
        "missing": ["цель ограничения", "менее обременительные альтернативы", "тяжесть последствий", "индивидуальная оценка"],
    },
    "balance": {
        "pattern": re.compile(r"баланс|сбалансирован|конкурирующ|интересы других лиц|слабая сторона", re.IGNORECASE),
        "missing": ["конкурирующие интересы", "распределение бремени", "процедурные гарантии"],
    },
    "equality": {
        "pattern": re.compile(r"равенств|дискримин|одинаков|различи[ея]|категори[ия]", re.IGNORECASE),
        "missing": ["сравнимая категория", "различие в правах", "цель различия", "объективное оправдание"],
    },
    "legal_certainty": {
        "pattern": re.compile(r"неопредел|неясн|недвусмыслен|произвол|единообраз|противоречив|судебн\w+\s+хаос", re.IGNORECASE),
        "missing": ["текстовая неясность", "расходящаяся практика", "почему разъяснения не устраняют дефект"],
    },
    "retroactivity": {
        "pattern": re.compile(r"обратн\w+\s+сил|ретроактив|прошл\w+\s+период|ухудша\w+\s+положени", re.IGNORECASE),
        "missing": ["дата юридического факта", "дата изменения закона", "ухудшение положения", "переходные правила"],
    },
    "legitimate_expectations": {
        "pattern": re.compile(r"правомерн\w+\s+ожидан|доверие|приобрет[её]нн\w+\s+прав|адаптац|компенсац", re.IGNORECASE),
        "missing": ["прежнее регулирование", "факты доверия", "переходный период", "компенсация"],
    },
    "gap_or_procedural_omission": {
        "pattern": re.compile(r"пробел|не\s+предусмотр|отсутств\w+\s+(?:механизм|процедур|порядок)|не\s+позволя", re.IGNORECASE),
        "missing": ["какой механизм отсутствует", "почему право без него нереализуемо", "соседнее регулирование"],
    },
    "effective_remedy": {
        "pattern": re.compile(r"эффективн\w+\s+средств|судебн\w+\s+защит|обжалован|приостанов", re.IGNORECASE),
        "missing": ["какое средство требуется", "почему существующее средство неэффективно", "необратимые последствия"],
    },
    "notification_and_right_to_be_heard": {
        "pattern": re.compile(r"уведом|известить|ознаком|выразить\s+мнен|быть\s+услышан|позици[яю]", re.IGNORECASE),
        "missing": ["кто должен уведомить", "срок для позиции", "последствие отсутствия уведомления"],
    },
}
ATTACHMENT_PATTERNS = {
    "судебный акт": re.compile(r"решени[ея]|определени[ея]|постановлени[ея]|приговор", re.IGNORECASE),
    "жалоба или ходатайство": re.compile(r"жалоб|ходатайств|заявлени", re.IGNORECASE),
    "доверенность": re.compile(r"доверенн", re.IGNORECASE),
    "госпошлина": re.compile(r"госпошлин|пошлин|квитанц|плат[её]ж", re.IGNORECASE),
    "паспорт": re.compile(r"паспорт", re.IGNORECASE),
    "перевод": re.compile(r"перевод", re.IGNORECASE),
    "экспертные материалы": re.compile(r"эксперт|заключени", re.IGNORECASE),
    "нормативный акт": re.compile(r"закон|кодекс|фкз|норматив", re.IGNORECASE),
}
DOCUMENT_TYPE_PATTERNS = [
    ("formal_ksrf_guide", re.compile(r"(?:как\s+избежать\s+ошибок\s+при\s+обращении\s+в\s+КС|схема\s+прохождения\s+жалоб[ыи]\s+в\s+КС|типичн\w+\s+ошибк\w+\s+.*КС|примерн\w+\s+структур\w+\s+жалоб)", re.IGNORECASE | re.DOTALL)),
    ("legal_writing_methodology", re.compile(r"(?:Основы\s+письма\s+для\s+юристов|юридическ\w+\s+письм|legal\s+writing|legal\s+drafting|структур[аы]\s+текста)", re.IGNORECASE | re.DOTALL)),
    ("research_report", re.compile(r"(?:Исполнительное\s+резюме|deliverable|deep\s+research|автоматизаци[яи].{0,80}(?:жалоб|КС|практик)|таксономи[яи].{0,80}автоматизац)", re.IGNORECASE | re.DOTALL)),
    ("service_or_tool_spec", re.compile(r"(?:ТЗ|техническ\w+\s+задан|сервис[ыа]?|архитектур\w+\s+сервис|MVP|roadmap|product|pipeline).{0,160}(?:жалоб|КС|практик|автоматизац|бот|канал)", re.IGNORECASE | re.DOTALL)),
    ("echr_or_un_material", re.compile(r"(?:ЕСПЧ|Европейск\w+\s+Суд|Конвенци[яи]|Article\s+\d+|CASE\s+OF|United\s+Nations|ООН|Организаци[яи]\s+Объедин[её]нных\s+Наций|Комитет\s+по\s+правам\s+человека|Комитет\s+ООН|Международн\w+\s+пакт|правозащитн\w+\s+механизм)", re.IGNORECASE | re.DOTALL)),
    ("practice_retrieval_skill_material", re.compile(r"(?:Тезис:|PRO-формула|CONTRA-формула|подтверждающ\w+\s+практик|опровергающ\w+\s+практик|встречн\w+\s+поиск)", re.IGNORECASE | re.DOTALL)),
    ("telegram_or_channel_research", re.compile(r"(?:Telegram|https://t\.me|t\.me/|permalink|пермалинк|скрейпинг)", re.IGNORECASE | re.DOTALL)),
    ("post_decision_review_motion", re.compile(r"пересмотр.*(?:дела|решени|судебн)", re.IGNORECASE | re.DOTALL)),
    ("request_supplement", re.compile(r"дополнени[ея].{0,180}(?:запрос|Конституционн\w+\s+Суд)", re.IGNORECASE | re.DOTALL)),
    ("court_request_motion", re.compile(r"ходатайств.*(?:запрос|Конституционн\w+\s+Суд)", re.IGNORECASE | re.DOTALL)),
    ("deputy_or_authorized_body_request", re.compile(r"(?:запрос.{0,1200}(?:депутат|Государственн\w+\s+Дум|Совет\w+\s+Федераци|Президент|Правительств|законодательн\w+\s+орган)|(?:депутат|Государственн\w+\s+Дум|Совет\w+\s+Федераци|Президент|Правительств).{0,1200}запрос|ч\.\s*2\s+ст\.\s*125.{0,1200}запрос)", re.IGNORECASE | re.DOTALL)),
    ("court_request_by_court", re.compile(r"(?:запросом|запрос)\s+.*Конституционн\w+\s+Суд|Запрос_ВС", re.IGNORECASE | re.DOTALL)),
    ("institutional_position_or_amicus", re.compile(r"(?:позици[яи]|мнение|заключени[ея]).{0,160}(?:ТПП|торгово-промышленн|международн\w+\s+коммерческ|amicus|инициативн\w+\s+научн)", re.IGNORECASE | re.DOTALL)),
    ("amicus_or_expert_conclusion", re.compile(r"amicus|заключени[ея].{0,120}(?:Конституционн\w+\s+Суд|стандарт|сравнительн)", re.IGNORECASE | re.DOTALL)),
    ("ksrf_complaint", re.compile(r"жалоб[аы].{0,160}(?:Конституционн\w+\s+Суд|конституционн\w+\s+прав)", re.IGNORECASE | re.DOTALL)),
    ("science_or_methodology", re.compile(r"(?:теория\s+и\s+практика|конституционн\w+\s+правосуди|право\s+быть\s+услышанным|автор\s+использует\s+эмпирическ|научн\w+\s+заключени)", re.IGNORECASE | re.DOTALL)),
    ("judicial_act", re.compile(r"(?:решени[ея]|определени[ея]|постановлени[ея]|приговор).{0,120}(?:суд|суда|судебн)", re.IGNORECASE | re.DOTALL)),
    ("power_of_attorney", re.compile(r"доверенн", re.IGNORECASE)),
    ("state_fee_or_payment", re.compile(r"госпошлин|пошлин|квитанц|плат[её]ж", re.IGNORECASE)),
    ("translation", re.compile(r"перевод|translated|translation", re.IGNORECASE)),
    ("normative_act_excerpt", re.compile(r"выдержк[аи].{0,80}(?:нпа|закона|кодекса)|текст\s+обжалуем", re.IGNORECASE | re.DOTALL)),
]
FILENAME_TYPE_PATTERNS = [
    ("telegram_or_channel_research", re.compile(r"(deep-research-report_тг|тг[ _-]*канал|telegram)", re.IGNORECASE)),
    ("formal_ksrf_guide", re.compile(r"(как\s+избежать\s+ошибок|ошибок\s+при\s+обращении|примерная_структура|образец_страница|образец_жалобы)", re.IGNORECASE)),
    ("legal_writing_methodology", re.compile(r"(по\s+письму|osnovy.*pisma|legal[_ -]?writing)", re.IGNORECASE)),
    ("research_report", re.compile(r"(deep-research-report)", re.IGNORECASE)),
    ("practice_retrieval_skill_material", re.compile(r"(судебная_практика|praktika|tezis|тезис)", re.IGNORECASE)),
    ("service_or_tool_spec", re.compile(r"(^тз|/тз|сервисы|services|service)", re.IGNORECASE)),
    ("echr_or_un_material", re.compile(r"(case_of|echr|eспч|espch|оон|oon|un|pravozashchit|burkov|против_россии|protection_internationale)", re.IGNORECASE)),
    ("science_or_methodology", re.compile(r"(kryazhkova|muranov|pravovaja-sila|zhkp|жкп|sko-)", re.IGNORECASE)),
    ("institutional_position_or_amicus", re.compile(r"(pozic|pozits|mchp|tpp|amicus)", re.IGNORECASE)),
    ("request_supplement", re.compile(r"(dopolnenie|pervoe-dopolnenie|vtoroe-dopolnenie|дополнени).*(zapros|vto|кс|ks)", re.IGNORECASE)),
    ("deputy_or_authorized_body_request", re.compile(r"(zapros|запрос).*(deputat|gosdum|fsb|vto|vas|госдум|депутат|фсб|вас)", re.IGNORECASE)),
    ("ksrf_complaint", re.compile(r"(zhaloba|zhalob|жалоб)", re.IGNORECASE)),
]
PRAYER_RE = re.compile(r"\b(?:ПРОШУ|ПРОСИМ|просим|просит|прошу суд|Требование,\s+обращ)", re.IGNORECASE)
APPLICANT_RE = re.compile(r"(?:Заявител[ьиь]|Административн\w+\s+истец|Истец)\s*:?\s*([^\n]{3,180})", re.IGNORECASE)
ADDRESSEE_RE = re.compile(r"(Конституционный\s+Суд\s+Российской\s+Федерации|Конституционный\s+Суд\s+РФ|[А-ЯЁ][^\n]{3,120}суд[^\n]{0,80})")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def which_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for directory in TOOL_DIRS:
        candidate = directory / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def extract_pdf(path: Path) -> str:
    pdftotext = which_tool("pdftotext")
    if not pdftotext:
        return ""
    proc = subprocess.run(
        [pdftotext, "-layout", str(path), "-"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return repair_cyrillic_mojibake(proc.stdout.decode("utf-8", "replace"))


def text_quality_signals(text: str) -> dict[str, Any]:
    sample = text[:12000]
    letters = [ch for ch in sample if ch.isalpha()]
    cyrillic = [ch for ch in letters if "а" <= ch.lower() <= "я" or ch.lower() == "ё"]
    cyrillic_ratio = len(cyrillic) / len(letters) if letters else 0.0
    mojibake_hits = len(re.findall(r"\b(?:KOH|KONCT|CYA|CYD|Tocy|HCT|YIM|Npeg|BTO|VTO)\w*", sample, re.IGNORECASE))
    return {
        "letters": len(letters),
        "cyrillic_ratio": round(cyrillic_ratio, 3),
        "mojibake_hits": mojibake_hits,
    }


def repair_cyrillic_mojibake(text: str) -> str:
    signals = text_quality_signals(text)
    latin1_cyrillic_noise = len(re.findall(r"[À-ÿ]{4,}", text))
    if signals["cyrillic_ratio"] > 0.15 or latin1_cyrillic_noise < 10:
        return text
    try:
        repaired = text.encode("latin1", "ignore").decode("cp1251", "ignore")
    except UnicodeError:
        return text
    repaired_signals = text_quality_signals(repaired)
    if repaired_signals["cyrillic_ratio"] > max(0.5, signals["cyrillic_ratio"] + 0.4):
        return repaired
    return text


def expects_cyrillic(path: Path) -> bool:
    name = path.name.lower()
    if any("а" <= ch <= "я" or ch == "ё" for ch in name):
        return True
    return bool(re.search(r"(zhalob|zapros|dopolnenie|ksrf|ks_|_ks|tilda|pravo|zakon|sud|rossii|russia.*translation)", name))


def should_try_ocr(text: str, path: Path) -> bool:
    if len(text.strip()) < 500:
        return True
    if path.suffix.lower() != ".pdf":
        return False
    signals = text_quality_signals(text)
    name = path.name.lower()
    russian_legal_name = expects_cyrillic(path)
    return russian_legal_name and signals["letters"] > 200 and (
        signals["cyrillic_ratio"] < 0.35 or signals["mojibake_hits"] >= 3
    )


def text_score(text: str) -> float:
    signals = text_quality_signals(text)
    return len(text.strip()) * (0.25 + signals["cyrillic_ratio"]) - signals["mojibake_hits"] * 200


def tesseract_language_args(tesseract: str, tessdata_dir: str | None) -> tuple[list[str], list[str]]:
    list_cmd = [tesseract, "--list-langs"]
    if tessdata_dir:
        list_cmd.extend(["--tessdata-dir", tessdata_dir])
    proc = subprocess.run(list_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    langs = set(proc.stdout.decode("utf-8", "replace").splitlines())
    flags: list[str] = []
    if "rus" in langs and "eng" in langs:
        lang = "rus+eng"
    elif "rus" in langs:
        lang = "rus"
    elif "eng" in langs:
        lang = "eng"
        flags.append("tesseract_rus_unavailable")
    else:
        lang = "eng"
        flags.append("tesseract_language_unavailable")
    args: list[str] = []
    if tessdata_dir:
        args.extend(["--tessdata-dir", tessdata_dir])
    args.extend(["-l", lang])
    flags.append(f"tesseract_lang_{lang}")
    return args, flags


def extract_pdf_ocr(path: Path, max_pages: int, tessdata_dir: str | None = None) -> tuple[str, list[str]]:
    pdftoppm = which_tool("pdftoppm")
    tesseract = which_tool("tesseract")
    if not pdftoppm or not tesseract:
        return "", ["ocr_unavailable"]
    lang_args, lang_flags = tesseract_language_args(tesseract, tessdata_dir)
    with tempfile.TemporaryDirectory(prefix="ksrf_ocr_") as tmp:
        prefix = str(Path(tmp) / "page")
        proc = subprocess.run(
            [pdftoppm, "-r", "200", "-f", "1", "-l", str(max_pages), "-png", str(path), prefix],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            return "", ["ocr_render_failed"]
        parts: list[str] = []
        for image in sorted(Path(tmp).glob("page-*.png")):
            ocr = subprocess.run(
                [tesseract, str(image), "stdout", *lang_args, "--psm", "6"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            if ocr.stdout:
                parts.append(ocr.stdout.decode("utf-8", "replace"))
        return "\n".join(parts), ["ocr_attempted", *lang_flags]


def extract_docx(path: Path) -> str:
    parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if name.startswith("word/") and name.endswith(".xml"):
                try:
                    root = ElementTree.fromstring(zf.read(name))
                except ElementTree.ParseError:
                    continue
                for node in root.iter():
                    if node.text:
                        parts.append(node.text)
    return "\n".join(parts)


def extract_legacy_doc(path: Path) -> tuple[str, str]:
    textutil = which_tool("textutil")
    if textutil:
        proc = subprocess.run(
            [textutil, "-convert", "txt", "-stdout", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        text = proc.stdout.decode("utf-8", "replace")
        if len(text.strip()) > 500:
            return text, "textutil"
    proc = subprocess.run(["strings", str(path)], check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return proc.stdout.decode("utf-8", "replace"), "strings"


def extract_image_ocr(path: Path, tessdata_dir: str | None = None) -> tuple[str, dict[str, Any]]:
    tesseract = which_tool("tesseract")
    details: dict[str, Any] = {"method": "image_ocr", "fallbacks": [], "ocr_pages": 1}
    if not tesseract:
        details["fallbacks"].append("ocr_unavailable")
        return "", details
    lang_args, lang_flags = tesseract_language_args(tesseract, tessdata_dir)
    details["fallbacks"].extend(["ocr_attempted", *lang_flags])
    proc = subprocess.run(
        [tesseract, str(path), "stdout", *lang_args, "--psm", "6"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return proc.stdout.decode("utf-8", "replace"), details


def extract_text(path: Path, enable_ocr: bool = True, ocr_pages: int = 8, tessdata_dir: str | None = None) -> tuple[str, dict[str, Any]]:
    suffix = path.suffix.lower()
    details: dict[str, Any] = {"method": "none", "fallbacks": [], "ocr_pages": 0}
    if suffix == ".pdf":
        text = extract_pdf(path)
        details["method"] = "pdftotext"
        if enable_ocr and should_try_ocr(text, path):
            if len(text.strip()) >= 500:
                details["fallbacks"].append("pdftotext_low_cyrillic_or_mojibake")
            ocr_text, flags = extract_pdf_ocr(path, ocr_pages, tessdata_dir=tessdata_dir)
            details["fallbacks"].extend(flags)
            details["ocr_pages"] = ocr_pages if ocr_text else 0
            if text_score(ocr_text) > text_score(text):
                text = ocr_text
                details["method"] = "ocr"
        return text, details
    if suffix == ".docx":
        details["method"] = "docx_xml"
        return extract_docx(path), details
    if suffix in {".txt", ".md", ".rtf", ".html", ".htm", ".mhtml"}:
        details["method"] = "plain_text"
        return path.read_text("utf-8", errors="replace"), details
    if suffix == ".doc":
        text, method = extract_legacy_doc(path)
        details["method"] = method
        if method == "textutil":
            details["fallbacks"].append("legacy_doc_textutil")
        return text, details
    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return extract_image_ocr(path, tessdata_dir=tessdata_dir)
    return "", details


def unique(items: list[str], limit: int = 80) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = re.sub(r"\s+", " ", item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
        if len(out) >= limit:
            break
    return out


def context(text: str, start: int, end: int, width: int = 180) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def lines(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]


def extract_title(text: str, name: str) -> str:
    for line in lines(text)[:40]:
        if line.startswith("=====") or re.fullmatch(r"(?:PAGE|СТРАНИЦА)\s*\d+", line, re.IGNORECASE):
            continue
        if 8 <= len(line) <= 180 and any(ch.isalpha() for ch in line):
            return line
    return name


def extract_constitutional_refs(text: str) -> list[str]:
    refs = [m.group(0) for m in CONSTITUTION_RE.finditer(text)]
    for match in CONSTITUTION_LIST_RE.finditer(text):
        numbers = re.findall(r"\d+(?:\.\d+)?", match.group(1))
        refs.extend([f"статья {num} Конституции Российской Федерации" for num in numbers])
    return unique(refs, 80)


def classify_document(text: str, name: str) -> str:
    for doc_type, pattern in FILENAME_TYPE_PATTERNS:
        if pattern.search(name):
            return doc_type
    haystack = f"{name}\n{text[:6000]}"
    for doc_type, pattern in DOCUMENT_TYPE_PATTERNS:
        if pattern.search(haystack):
            return doc_type
    return "other"


def extract_prayer_block(text: str) -> str:
    text_lines = lines(text)
    for index, line in enumerate(text_lines):
        if PRAYER_RE.search(line):
            block = [item for item in text_lines[index:index + 16] if item]
            return "\n".join(block)[:2500]
    return ""


def extract_labeled_candidates(pattern: re.Pattern[str], text: str, limit: int = 12) -> list[str]:
    return unique([match.group(1) if match.lastindex else match.group(0) for match in pattern.finditer(text[:12000])], limit)


def extraction_quality(text: str, path: Path, details: dict[str, Any]) -> dict[str, Any]:
    low_text = len(text.strip()) < 500 and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    signals = text_quality_signals(text)
    quality = "ok"
    if low_text:
        quality = "low_text"
    elif details.get("method") == "ocr":
        quality = "ocr_review_needed"
    elif path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"} and (
        signals["mojibake_hits"] >= 3 or (expects_cyrillic(path) and signals["cyrillic_ratio"] < 0.35)
    ):
        quality = "encoding_or_ocr_review_needed"
    return {
        "method": details.get("method", "none"),
        "quality": quality,
        "fallbacks": details.get("fallbacks", []),
        "ocr_pages": details.get("ocr_pages", 0),
        "text_quality": signals,
    }


def infer_application_effect(window: str) -> str:
    lowered = window.lower()
    if "не предусмотр" in lowered or "не позволяет" in lowered:
        return "не предусматривающую или не позволяющую реализовать необходимый механизм"
    if "не допуска" in lowered or "запрещ" in lowered:
        return "запрещающую или исключающую реализацию права"
    if "отказ" in lowered:
        return "служащую основанием отказа"
    if "обязыва" in lowered:
        return "возлагающую обязанность или запускающую неблагоприятное последствие"
    if "ответствен" in lowered or "санкц" in lowered:
        return "допускающую ответственность или санкцию"
    if "истолков" in lowered or "толкован" in lowered:
        return "истолкованную судами в спорном конституционно-правовом смысле"
    return "примененную как основание спорного правового эффекта"


def build_application_bridge_candidates(applied_contexts: list[dict[str, str]], limit: int = 8) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for item in applied_contexts:
        norm = item["norm"]
        effect = infer_application_effect(item["context"])
        candidates.append({
            "norm": norm,
            "effect": effect,
        "bridge": f"Суды применили {norm} как {effect}, что требует проверки связи с конкретным конституционным вредом заявителя.",
            "bridge": f"Суды применили {norm} в значении или с эффектом: {effect}; это нужно связать с конкретным конституционным вредом заявителя.",
            "source_context": item["context"],
        })
        if len(candidates) >= limit:
            break
    return candidates


def suggest_constitutional_tests(text: str, limit: int = 8) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for code, cfg in TEST_PATTERNS.items():
        matches = [context(text, m.start(), m.end(), 120) for m in cfg["pattern"].finditer(text)]
        if matches:
            suggestions.append({
                "test_code": code,
                "confidence": min(0.95, 0.45 + len(matches) * 0.1),
                "signals": unique(matches, 3),
                "missing_evidence": cfg["missing"],
            })
        if len(suggestions) >= limit:
            break
    return suggestions


def build_request_formula_candidates(passport: dict[str, Any], bridge_candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    norms = passport.get("challenged_norm_candidates") or []
    constitutional_refs = passport.get("constitutional_refs") or []
    if not norms:
        return []
    norm = norms[0]
    articles = ", ".join(constitutional_refs[:5]) if constitutional_refs else "[статьи Конституции РФ]"
    effect = bridge_candidates[0]["effect"] if bridge_candidates else "[оспариваемый конституционно-правовой эффект]"
    formulas = [{
        "formula_type": "individual_complaint",
        "text": f"Признать {norm} не соответствующей Конституции РФ ({articles}) в той мере, в какой указанная норма {effect} в деле заявителя.",
        "review_flags": "Проверить точность нормы, статьи Конституции, фактический крючок и чрезмерную широту формулы.",
    }]
    if passport.get("document_type") == "court_request_motion":
        formulas.append({
            "formula_type": "court_request_motion",
            "text": f"Направить запрос в Конституционный Суд РФ о проверке соответствия {norm} Конституции РФ ({articles}) в той мере, в какой указанная норма {effect}.",
            "review_flags": "Проверить, что норма подлежит применению текущим судом и вопрос необходим для разрешения дела.",
        })
    return formulas


def build_practice_matrix_candidates(doc: dict[str, Any], applied_contexts: list[dict[str, str]]) -> list[dict[str, str]]:
    courts = doc.get("courts", [])
    dates = doc.get("dates", [])
    case_numbers = doc.get("case_numbers", [])
    rows: list[dict[str, str]] = []
    for index, item in enumerate(applied_contexts[:10]):
        rows.append({
            "case": case_numbers[0] if case_numbers else "[номер дела не извлечен]",
            "court": courts[index % len(courts)] if courts else "[суд не извлечен]",
            "date": dates[index % len(dates)] if dates else "[дата не извлечена]",
            "norm": item["norm"],
            "interpretive_move": infer_application_effect(item["context"]),
            "proof_source": item["context"],
            "harmful_effect": "[требует ручной привязки к конституционному вреду]",
            "relevance": "Кандидат для проверки: единичное применение, устойчивая практика или неопределенность.",
        })
    return rows


def build_repeatability_detector(passport: dict[str, Any]) -> dict[str, Any]:
    ksrf_refs = passport.get("ksrf_refs", [])
    norms = passport.get("challenged_norm_candidates", [])
    if not ksrf_refs:
        return {
            "has_prior_ksrf_refs": False,
            "risk": "unknown",
            "review_note": "В документе не найдены ссылки на прежние акты КС РФ; нужен отдельный поиск по норме.",
        }
    return {
        "has_prior_ksrf_refs": True,
        "risk": "review_needed",
        "same_norm_candidates": norms[:10],
        "prior_ksrf_refs": ksrf_refs[:10],
        "new_argument_questions": [
            "Это тот же аспект нормы или новый аспект применения?",
            "Есть ли новое конкретное дело или новая категория заявителя?",
            "Появились ли новые доводы, практика, международный или социальный контекст?",
            "Нужно ли формулировать обращение как новый аспект, а не обжалование прежнего акта КС РФ?",
        ],
    }


def build_execution_packet(passport: dict[str, Any], text: str) -> dict[str, Any]:
    if not passport.get("ksrf_refs") and not re.search(r"пересмотр|вновь открывш|новые обстоятельства", text, re.IGNORECASE):
        return {}
    return {
        "ksrf_act_candidates": passport.get("ksrf_refs", [])[:10],
        "possible_post_decision_route": bool(re.search(r"пересмотр|вновь открывш|новые обстоятельства", text, re.IGNORECASE)),
        "operative_meaning": "[извлечь из резолютивной части акта КС РФ вручную или отдельным парсером]",
        "affected_persons": "[заявитель / лица в аналогичном положении — требует проверки]",
        "competent_court": "[определить по процессуальному кодексу и делу]",
        "missing_attachments": [
            "акт КС РФ",
            "судебные акты по делу заявителя",
            "доказательство вступления акта в силу",
            "доверенность/полномочия",
        ],
    }


def build_qa_matrix(doc: dict[str, Any]) -> list[dict[str, str]]:
    passport = doc["document_passport"]
    doc_type = passport.get("document_type")
    checks = [
        ("document_type", bool(doc_type and doc_type != "other"), "Тип документа определен.", "Тип документа не определен."),
        ("extraction_quality", doc["extraction"]["quality"] == "ok", "Извлечение текста не требует ручной проверки.", "Извлечение текста требует ручной проверки."),
    ]
    core_procedural_docs = {
        "ksrf_complaint",
        "court_request_motion",
        "court_request_by_court",
        "deputy_or_authorized_body_request",
        "post_decision_review_motion",
    }
    if doc_type in core_procedural_docs:
        checks.extend([
            ("challenged_norm", bool(passport.get("challenged_norm_candidates")), "Есть кандидат оспариваемой нормы.", "Не найден кандидат оспариваемой нормы."),
            ("constitutional_refs", bool(passport.get("constitutional_refs")), "Есть ссылки на Конституцию РФ.", "Не найдены ссылки на Конституцию РФ."),
            ("application_context", bool(doc.get("applied_norm_contexts")), "Есть контекст применения или толкования нормы.", "Не найден контекст применения или толкования нормы."),
            ("prayer_block", bool(passport.get("prayer_block")), "Есть просительная часть или просьба.", "Не найдена просительная часть или просьба."),
        ])
    elif doc_type == "request_supplement":
        checks.extend([
            ("supplement_delta", bool(passport.get("case_numbers") or passport.get("ksrf_refs") or passport.get("challenged_norm_candidates")), "Есть зацепка для связи с базовым запросом.", "Не найдена явная связь с базовым запросом; нужна ручная delta map."),
            ("extraction_quality_for_delta", doc["extraction"]["quality"] == "ok", "Текст дополнения можно сопоставлять с базовым обращением.", "Текст дополнения нельзя надежно сопоставить с базовым обращением без ручной проверки."),
        ])
    elif doc_type in {"institutional_position_or_amicus", "amicus_or_expert_conclusion"}:
        checks.extend([
            ("support_function", bool(passport.get("constitutional_refs") or passport.get("ksrf_refs") or doc.get("applied_norm_contexts")), "Материал имеет признаки функциональной связи с конституционным вопросом.", "Нужно вручную определить, какой элемент теста поддерживает материал."),
        ])
    elif doc_type == "science_or_methodology":
        checks.extend([
            ("supporting_source", True, "Научный или методологический материал не требует просительной части; используй его только как supporting source.", "Научный материал требует ручной функции в жалобе."),
        ])
    elif doc_type in {"research_report", "service_or_tool_spec", "telegram_or_channel_research", "practice_retrieval_skill_material", "formal_ksrf_guide", "legal_writing_methodology"}:
        checks.extend([
            ("methodology_source", True, "Материал используется для донасыщения скиллов или продуктовой методологии, а не как самостоятельная жалоба.", "Нужно вручную определить, какой скилл он усиливает."),
        ])
    elif doc_type == "echr_or_un_material":
        checks.extend([
            ("international_support_function", True, "Международный/ООН/ЕСПЧ материал используется только как функциональный supporting source.", "Нужно вручную привязать международный материал к конкретному тесту."),
        ])
    return [
        {"check_code": code, "result": "pass" if ok else "review", "message": pass_message if ok else review_message}
        for code, ok, pass_message, review_message in checks
    ]


def collect_from_document(path: Path, root: Path, enable_ocr: bool, ocr_pages: int, tessdata_dir: str | None = None) -> dict[str, Any]:
    text, extraction_details = extract_text(path, enable_ocr=enable_ocr, ocr_pages=ocr_pages, tessdata_dir=tessdata_dir)
    lower_name = path.name.lower()
    stages = [stage for stage, rx in STAGE_WORDS.items() if rx.search(text) or rx.search(lower_name)]
    legal_refs = unique([m.group(0) for m in LEGAL_REF_RE.finditer(text)])
    constitutional_refs = extract_constitutional_refs(text)
    ksrf_refs = unique([m.group(0) for m in KSRF_RE.finditer(text)])
    applied_contexts: list[dict[str, str]] = []
    for match in LEGAL_REF_RE.finditer(text):
        window = context(text, match.start(), match.end())
        if APPLIED_WORDS_RE.search(window):
            applied_contexts.append({"norm": re.sub(r"\s+", " ", match.group(0)).strip(), "context": window})
        if len(applied_contexts) >= 20:
            break
    attachment_signals = [name for name, rx in ATTACHMENT_PATTERNS.items() if rx.search(path.name) or rx.search(text[:5000])]
    doc_type = classify_document(text, path.name)
    prayer_block = extract_prayer_block(text)
    passport = {
        "document_type": doc_type,
        "title": extract_title(text, path.name),
        "applicant_candidates": extract_labeled_candidates(APPLICANT_RE, text),
        "addressee_candidates": unique([m.group(0) for m in ADDRESSEE_RE.finditer(text[:12000])], 12),
        "case_numbers": unique([m.group(0) for m in CASE_RE.finditer(text)], 30),
        "challenged_norm_candidates": [ref for ref in legal_refs if "Конституци" not in ref][:50],
        "constitutional_refs": constitutional_refs,
        "ksrf_refs": ksrf_refs,
        "prayer_block": prayer_block,
        "attachment_signals": attachment_signals,
    }
    bridge_candidates = build_application_bridge_candidates(applied_contexts)
    test_suggestions = suggest_constitutional_tests(text)
    request_formula_candidates = build_request_formula_candidates(passport, bridge_candidates)
    doc_stub = {
        "courts": unique([m.group(0) for m in COURT_RE.finditer(text)]),
        "dates": unique([m.group(0) for m in DATE_RE.finditer(text)], 120),
        "case_numbers": unique([m.group(0) for m in CASE_RE.finditer(text)]),
    }
    analysis = {
        "application_bridge_candidates": bridge_candidates,
        "constitutional_test_suggestions": test_suggestions,
        "request_formula_candidates": request_formula_candidates,
        "practice_matrix_candidates": build_practice_matrix_candidates(doc_stub, applied_contexts),
        "repeatability_detector": build_repeatability_detector(passport),
        "ksrf_execution_packet": build_execution_packet(passport, text),
    }
    qa_matrix = build_qa_matrix({
        "document_passport": passport,
        "applied_norm_contexts": applied_contexts,
        "extraction": extraction_quality(text, path, extraction_details),
    })
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else path.name,
        "name": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "text_chars": len(text),
        "extraction": extraction_quality(text, path, extraction_details),
        "extraction_quality": extraction_quality(text, path, extraction_details),
        "low_text_risk": len(text.strip()) < 500 and path.suffix.lower() in {".pdf", ".doc", ".docx"},
        "document_passport": passport,
        "case_numbers": unique([m.group(0) for m in CASE_RE.finditer(text)]),
        "dates": unique([m.group(0) for m in DATE_RE.finditer(text)], 120),
        "courts": unique([m.group(0) for m in COURT_RE.finditer(text)]),
        "stages": stages,
        "legal_refs": legal_refs,
        "constitutional_refs": constitutional_refs,
        "ksrf_refs": ksrf_refs,
        "applied_norm_contexts": applied_contexts,
        "automation_analysis": analysis,
        "qa_matrix": qa_matrix,
        "attachment_signals": attachment_signals,
    }


def merge(documents: list[dict[str, Any]]) -> dict[str, Any]:
    missing: list[str] = []
    if not any(doc["applied_norm_contexts"] for doc in documents):
        missing.append("Не найден явный контекст применения нормы: проверь судебные акты вручную.")
    if not any("кассация" in doc["stages"] or "верховный суд" in doc["stages"] for doc in documents):
        missing.append("Не найдены очевидные признаки кассации или Верховного Суда: проверь исчерпание.")
    if not any("госпошлина" in doc["attachment_signals"] for doc in documents):
        missing.append("Не найден документ госпошлины или ходатайство о льготе/отсрочке.")
    if not any("доверенность" in doc["attachment_signals"] for doc in documents):
        missing.append("Не найдена доверенность; это нормально только если заявитель подает лично без представителя.")
    if any(doc["low_text_risk"] for doc in documents):
        missing.append("Есть PDF/DOC/DOCX с малым извлеченным текстом: может понадобиться OCR или ручная проверка.")

    next_questions = []
    if any("проверь исчерпание" in item for item in missing):
        next_questions.append("Каким актом завершилось исчерпание и есть ли отказ/акт ВС РФ?")
    if any("применения нормы" in item for item in missing):
        next_questions.append("В каком судебном акте суд применил или истолковал оспариваемую норму?")
    if not any(doc["constitutional_refs"] for doc in documents):
        next_questions.append("Сохранялся ли конституционный аргумент в обычных судах и в каком документе?")

    return {
        "case_numbers": unique([item for doc in documents for item in doc["case_numbers"]], 120),
        "dates": unique([item for doc in documents for item in doc["dates"]], 200),
        "courts": unique([item for doc in documents for item in doc["courts"]], 120),
        "stages": unique([item for doc in documents for item in doc["stages"]], 40),
        "legal_refs": unique([item for doc in documents for item in doc["legal_refs"]], 200),
        "constitutional_refs": unique([item for doc in documents for item in doc["constitutional_refs"]], 80),
        "ksrf_refs": unique([item for doc in documents for item in doc["ksrf_refs"]], 80),
        "applied_norm_contexts": [ctx for doc in documents for ctx in doc["applied_norm_contexts"]][:80],
        "document_passports": [doc["document_passport"] for doc in documents],
        "application_bridge_candidates": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("application_bridge_candidates", [])
        ][:80],
        "constitutional_test_suggestions": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("constitutional_test_suggestions", [])
        ][:80],
        "request_formula_candidates": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("request_formula_candidates", [])
        ][:30],
        "practice_matrix_candidates": [
            item for doc in documents for item in doc.get("automation_analysis", {}).get("practice_matrix_candidates", [])
        ][:80],
        "repeatability_review_items": [
            {"document": doc["relative_path"], **doc.get("automation_analysis", {}).get("repeatability_detector", {})}
            for doc in documents
            if doc.get("automation_analysis", {}).get("repeatability_detector", {}).get("has_prior_ksrf_refs")
        ][:40],
        "ksrf_execution_packets": [
            {"document": doc["relative_path"], **doc.get("automation_analysis", {}).get("ksrf_execution_packet", {})}
            for doc in documents
            if doc.get("automation_analysis", {}).get("ksrf_execution_packet")
        ][:40],
        "qa_review_items": [
            {"document": doc["relative_path"], **item}
            for doc in documents
            for item in doc.get("qa_matrix", [])
            if item["result"] != "pass"
        ][:120],
        "attachment_signals": {
            signal: [doc["relative_path"] for doc in documents if signal in doc["attachment_signals"]]
            for signal in ATTACHMENT_PATTERNS
        },
        "missing_or_risky": missing,
        "next_questions": next_questions,
    }


def iter_files(paths: list[Path]) -> list[Path]:
    allowed = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".html", ".htm", ".mhtml", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in allowed)
        elif path.is_file() and path.suffix.lower() in allowed:
            files.append(path)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Собрать первичный CaseFile из документов дела для скиллов КС РФ.")
    parser.add_argument("paths", nargs="+", help="Файлы или папки с материалами дела")
    parser.add_argument("--out", help="Куда записать JSON. По умолчанию вывод в stdout.")
    parser.add_argument("--no-ocr", action="store_true", help="Не запускать OCR fallback для PDF с малым извлеченным текстом.")
    parser.add_argument("--ocr-pages", type=int, default=8, help="Сколько первых страниц PDF пробовать через OCR fallback.")
    parser.add_argument("--tessdata-dir", help="Папка с языковыми пакетами Tesseract, если русский язык не установлен системно.")
    args = parser.parse_args()

    input_paths = [Path(p).expanduser().resolve() for p in args.paths]
    files = iter_files(input_paths)
    if not files:
        print("Не найдено поддерживаемых файлов.", file=sys.stderr)
        return 2
    root = input_paths[0] if input_paths[0].is_dir() else input_paths[0].parent
    documents = [collect_from_document(path, root, enable_ocr=not args.no_ocr, ocr_pages=args.ocr_pages, tessdata_dir=args.tessdata_dir) for path in files]
    report = {
        "schema": "ksrf.casefile.v2",
        "inputs": [str(p) for p in input_paths],
        "document_count": len(documents),
        "documents": documents,
        "summary": merge(documents),
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).expanduser().resolve().write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
