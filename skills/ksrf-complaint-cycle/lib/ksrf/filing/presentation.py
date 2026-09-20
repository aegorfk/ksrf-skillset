"""Court-facing view of the unchanged sentence/evidence model."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .composer import StructuredComplaint

COMPLAINT_TITLE = ("ЖАЛОБА", "на нарушение конституционных прав и свобод")
REVIEW_SECTION_CODES = frozenset({"review_notes"})
FACTS_HEADING = "I. Фактические обстоятельства дела"
REASONING_HEADING = "II. Позиция заявителя и её конституционно-правовое обоснование"
REQUEST_HEADING = "III. Требование, обращённое к Конституционному Суду Российской Федерации"

# Bounded detection of explicit workflow markers, never a classifier of legal prose.
SERVICE_MARKERS = re.compile(
    r"РАБОЧИЙ ПРОЕКТ|ПРОВЕРИТЬ\s*:|\bhigh[ -]risk\b|\b(?:review|draft)\b|"
    r"высокий риск|sentence[_ -]?id|matter[_ -]?id|evidence[_ -]?map|"
    r"я не оспариваю|я не прошу|жалоба не исходит|"
    r"(?:нет в исследованном комплекте|в исследованном комплекте нет)", re.IGNORECASE
)


class PresentationError(ValueError):
    reason_codes = ("service_notes_require_explicit_separation",)


def service_note_findings(complaint: StructuredComplaint) -> list[dict[str, str]]:
    """Find known markers outside explicit review notes; retain the whole sentence."""
    return [
        {"section_code": section.code, "sentence_id": sentence.sentence_id,
         "text": sentence.text, "message": "Разделить служебную заметку и юридический текст явно."}
        for section in complaint.sections if section.code not in REVIEW_SECTION_CODES
        for sentence in section.sentences if SERVICE_MARKERS.search(sentence.text)
    ]


@dataclass(frozen=True)
class PresentationBlock:
    kind: str
    text: str


def complaint_blocks(complaint: StructuredComplaint) -> tuple[PresentationBlock, ...]:
    """Group content for court without mutating claims, IDs or support states.

    Only explicitly separate review notes stay in the companion report.
    Adverse material remains substantive content and is never filtered by wording.
    A representative is never invented: a supplied representative section is
    explicit presentation input, which the drafting workflow must obtain from
    the user's representation instruction.
    """
    findings = service_note_findings(complaint)
    if findings:
        locators = ", ".join(item["section_code"] + "/" + item["sentence_id"] for item in findings)
        raise PresentationError("Служебные пометки требуют явного переноса в review_notes: " + locators)
    sections = {section.code: section for section in complaint.sections}
    blocks: list[PresentationBlock] = []
    used: set[str] = set(REVIEW_SECTION_CODES)

    def content(codes: tuple[str, ...], kind: str = "body") -> None:
        for code in codes:
            used.add(code)
            section = sections.get(code)
            if section is not None:
                blocks.extend(PresentationBlock(kind, sentence.text) for sentence in section.sentences)

    content(("addressee", "applicant", "representative", "respondent"), "header")
    blocks.extend(PresentationBlock("title", text) for text in COMPLAINT_TITLE)
    content(("object_of_review", "admissibility"))
    blocks.append(PresentationBlock("heading", FACTS_HEADING))
    content(("facts", "judicial_chain"))
    blocks.append(PresentationBlock("heading", REASONING_HEADING))
    content(("constitutional_issue", "rights_analysis", "authorities", "adverse_material"))
    # Preserve additional substantive sections instead of silently dropping them.
    for section in complaint.sections:
        if section.code not in used | {"requested_remedy", "enclosures", "signature"}:
            blocks.append(PresentationBlock("subheading", section.heading))
            content((section.code,))
    blocks.append(PresentationBlock("heading", REQUEST_HEADING))
    content(("requested_remedy",))
    blocks.append(PresentationBlock("heading", "Приложения"))
    content(("enclosures",))
    content(("signature",))
    return tuple(blocks)


def source_plain_text(complaint: StructuredComplaint) -> str:
    """Exact source prose, including review content omitted from the court view."""
    chunks = [complaint.title]
    for section in complaint.sections:
        chunks.append(section.heading)
        chunks.extend(sentence.text for sentence in section.sentences)
    return "\n".join(chunks)
