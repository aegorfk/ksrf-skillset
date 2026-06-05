#!/usr/bin/env python3
"""Извлечь признаки конституционно-правовых паттернов из PDF Постановлений КС РФ."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from PyPDF2 import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore

try:
    import pdfplumber
except Exception:  # pragma: no cover
    pdfplumber = None  # type: ignore


DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / "ТЗ" / "Постановления КС РФ"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "analysis_results" / "ksrf_argument_patterns"


@dataclass(frozen=True)
class Pattern:
    code: str
    title: str
    markers: List[str]
    automation_idea: str

    def regex(self) -> re.Pattern[str]:
        return re.compile("|".join(f"(?:{marker})" for marker in self.markers), flags=re.IGNORECASE | re.UNICODE)


PATTERNS: List[Pattern] = [
    Pattern(
        code="practice-split",
        title="Разнобой и неоднозначность правоприменения",
        markers=[
            r"неоднозначн\w*\s+(?:толкован|пониман|применен)",
            r"различн\w*\s+(?:толкован|пониман|подход)",
            r"противоречив\w*\s+судебн\w*\s+практик",
            r"единообразн\w*\s+(?:применен|толкован)",
            r"расхожден\w*\s+в\s+судебн\w*\s+практик",
        ],
        automation_idea="Найти кассационные акты по той же норме, кластеризовать competing holdings и проверить, есть ли несовместимые подходы.",
    ),
    Pattern(
        code="legal-certainty",
        title="Правовая определенность и предсказуемость",
        markers=[
            r"правов\w*\s+определенн",
            r"формальн\w*\s+определенн",
            r"ясн\w*\s+и\s+недвусмысленн",
            r"предсказуем\w*\s+(?:правов|регулирован|последств)",
            r"не\s+позволя\w*\s+(?:определ|установ)",
            r"критери\w*\s+(?:не\s+содерж|отсутств)",
        ],
        automation_idea="Проверить норму и судебные акты на отсутствие критериев, оценочные понятия без теста и смену толкования во времени.",
    ),
    Pattern(
        code="proportionality",
        title="Соразмерность ограничения",
        markers=[
            r"соразмерн\w*",
            r"пропорциональн\w*",
            r"чрезмерн\w*\s+(?:огранич|вмешательств|бремен)",
            r"необходим\w*\s+и\s+достаточн",
            r"должн\w*\s+быть\s+соразмер",
        ],
        automation_idea="Собрать право, публичную цель, средство, тяжесть последствий и менее обременительные альтернативы.",
    ),
    Pattern(
        code="interest-balance",
        title="Баланс частных и публичных интересов",
        markers=[
            r"баланс\w*\s+(?:частн|публичн|конституционн|интерес)",
            r"справедлив\w*\s+равновеси",
            r"чрезмерн\w*\s+бремен",
            r"компенсационн\w*\s+механизм",
            r"баланс\w*\s+конституционно\s+значим",
        ],
        automation_idea="Сопоставить, кто получает преимущество, кто несет бремя, есть ли компенсация и процедурная защита.",
    ),
    Pattern(
        code="effective-remedy",
        title="Эффективная судебная защита и процессуальные гарантии",
        markers=[
            r"судебн\w*\s+защит",
            r"эффективн\w*\s+(?:восстановлен|средств|защит)",
            r"процессуальн\w*\s+гаранти",
            r"прав\w*\s+быть\s+выслушан",
            r"доступ\w*\s+к\s+правосуд",
            r"рассмотрен\w*\s+(?:довод|аргумент)",
        ],
        automation_idea="Проверить, какие доводы заявителя суды не рассмотрели, и был ли реальный способ восстановить право.",
    ),
    Pattern(
        code="equality-differentiation",
        title="Равенство и необоснованная дифференциация",
        markers=[
            r"равенств\w*\s+(?:перед\s+законом|прав)",
            r"дискриминац",
            r"необоснованн\w*\s+дифференциац",
            r"объективн\w*\s+и\s+разумн\w*\s+оправдан",
            r"находящ\w*\s+в\s+одинаков\w*\s+положен",
        ],
        automation_idea="Найти группы сравнения, отличие последствий и проверить объективное оправдание различия.",
    ),
    Pattern(
        code="legitimate-expectations",
        title="Доверие к праву, стабильность и ретроактивность",
        markers=[
            r"довер\w*\s+к\s+(?:закону|праву)",
            r"законн\w*\s+ожидан",
            r"обратн\w*\s+сил",
            r"стабильн\w*\s+правов\w*\s+положен",
            r"ухудшен\w*\s+положен",
            r"предвидет\w*\s+последств",
        ],
        automation_idea="Построить timeline: когда возникло право, когда изменилась норма/практика и мог ли заявитель предвидеть последствия.",
    ),
    Pattern(
        code="non-mechanical-application",
        title="Запрет механического применения без учета обстоятельств",
        markers=[
            r"без\s+учет\w*\s+(?:конкретн|фактическ|существенн)",
            r"формальн\w*\s+подход",
            r"индивидуализац",
            r"автоматическ\w*\s+применен",
            r"суд\w*\s+обязан\w*\s+учитыват",
        ],
        automation_idea="Сравнить значимые обстоятельства дела с тем, что реально оценили суды; отметить механические выводы.",
    ),
]


def extract_text_with_pypdf(path: Path) -> str:
    if PdfReader is None:
        return ""
    reader = PdfReader(str(path))
    chunks: List[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_text_with_pdfplumber(path: Path) -> str:
    if pdfplumber is None:
        return ""
    chunks: List[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def extract_text(path: Path) -> str:
    for extractor in (extract_text_with_pypdf, extract_text_with_pdfplumber):
        try:
            text = extractor(path)
        except Exception:
            text = ""
        if len(text.strip()) > 500:
            return normalize_text(text)
    return ""


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def iter_pdfs(source: Path) -> Iterable[Path]:
    def sort_key(path: Path) -> tuple[int, int, str]:
        year = int(path.parent.name) if path.parent.name.isdigit() else 0
        number_match = re.search(r"(\d+)-П", path.name)
        number = int(number_match.group(1)) if number_match else 0
        return year, number, path.name

    yield from sorted(source.glob("*/*.pdf"), key=sort_key)


def context_window(text: str, start: int, end: int, radius: int = 650) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    snippet = text[left:right]
    snippet = re.sub(r"\s+", " ", snippet).strip()
    return snippet


def decision_meta(path: Path) -> Dict[str, object]:
    number = path.name.split("__", 1)[0].replace("_", "/")
    return {
        "year": path.parent.name,
        "number": number,
        "file": str(path),
    }


def build_report(summary: Dict[str, object], pattern_hits: Dict[str, List[Dict[str, object]]]) -> str:
    lines = [
        "# Проход по корпусу паттернов аргументации КС РФ",
        "",
        f"Сгенерировано: {summary['generated_at']}",
        f"PDF обработано: {summary['processed_pdf_count']}",
        f"PDF с извлеченным текстом: {summary['text_pdf_count']}",
        "",
        "## Количество по паттернам",
        "",
    ]
    for pattern in PATTERNS:
        stats = summary["patterns"][pattern.code]
        lines.append(f"- **{pattern.title}** (`{pattern.code}`): {stats['hit_count']} попаданий в {stats['decision_count']} постановлениях")
    lines.extend(["", "## Ранние и свежие примеры", ""])
    for pattern in PATTERNS:
        hits = pattern_hits.get(pattern.code, [])
        lines.append(f"### {pattern.title}")
        lines.append("")
        lines.append(f"Идея автоматизации: {pattern.automation_idea}")
        lines.append("")
        for hit in (hits[:2] + hits[-2:] if len(hits) > 4 else hits[:4]):
            snippet = str(hit["snippet"])
            if len(snippet) > 500:
                snippet = snippet[:500].rstrip() + "..."
            lines.append(f"- `{hit['number']}` ({hit['year']}): {snippet}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-per-pattern", type=int, default=200)
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    text_dir = out / "texts"
    out.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    compiled = {pattern.code: pattern.regex() for pattern in PATTERNS}
    pattern_hits: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    decision_counts: Dict[str, Counter[str]] = {pattern.code: Counter() for pattern in PATTERNS}
    hit_counts: Counter[str] = Counter()
    corpus_index: List[Dict[str, object]] = []

    processed = 0
    text_count = 0
    failures: List[Dict[str, str]] = []

    for pdf_path in iter_pdfs(source):
        processed += 1
        meta = decision_meta(pdf_path)
        text = extract_text(pdf_path)
        if not text:
            failures.append({"file": str(pdf_path), "error": "не удалось извлечь текст"})
            continue

        text_count += 1
        text_path = text_dir / f"{meta['year']}__{meta['number']}.txt".replace("/", "_")
        text_path.write_text(text, encoding="utf-8")

        matched_patterns: List[str] = []
        for pattern in PATTERNS:
            regex = compiled[pattern.code]
            matches = list(regex.finditer(text))
            if not matches:
                continue
            matched_patterns.append(pattern.code)
            decision_counts[pattern.code][str(meta["number"])] += 1
            for match in matches[:4]:
                hit_counts[pattern.code] += 1
                if len(pattern_hits[pattern.code]) >= args.max_per_pattern:
                    continue
                pattern_hits[pattern.code].append(
                    {
                        **meta,
                        "marker": match.group(0),
                        "snippet": context_window(text, match.start(), match.end()),
                    }
                )

        corpus_index.append(
            {
                **meta,
                "text_file": str(text_path),
                "text_length": len(text),
                "patterns": matched_patterns,
            }
        )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "processed_pdf_count": processed,
        "text_pdf_count": text_count,
        "failed_text_count": len(failures),
        "patterns": {
            pattern.code: {
                "title": pattern.title,
                "hit_count": hit_counts[pattern.code],
                "decision_count": len(decision_counts[pattern.code]),
                "automation_idea": pattern.automation_idea,
            }
            for pattern in PATTERNS
        },
    }

    (out / "corpus_index.json").write_text(json.dumps(corpus_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "pattern_hits.json").write_text(json.dumps(pattern_hits, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "pattern_summary.md").write_text(build_report(summary, pattern_hits), encoding="utf-8")

    print(f"processed={processed} text={text_count} failures={len(failures)} out={out}")
    for pattern in PATTERNS:
        stats = summary["patterns"][pattern.code]
        print(f"{pattern.code}: hits={stats['hit_count']} decisions={stats['decision_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
