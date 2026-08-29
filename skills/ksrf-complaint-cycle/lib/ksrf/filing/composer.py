"""Structured complaint composition with sentence-level provenance.

The composer deliberately does not generate legal facts or propositions.  It
normalizes an already prepared complaint model and prevents unsupported filing
sentences from being promoted to the release renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "1.0"

REQUIRED_SECTION_CODES: tuple[str, ...] = (
    "addressee",
    "applicant",
    "object_of_review",
    "admissibility",
    "facts",
    "judicial_chain",
    "constitutional_issue",
    "rights_analysis",
    "authorities",
    "adverse_material",
    "requested_remedy",
    "enclosures",
)

FILING_SIGNIFICANT_ROLES = frozenset(
    {
        "fact",
        "court_reasoning",
        "norm_text",
        "legal_holding",
        "application_finding",
        "practice_claim",
        "adverse_authority",
        "requested_remedy",
    }
)

SUPPORTED_STATES = frozenset({"verified", "human_approved"})


class ComplaintModelError(ValueError):
    """Raised when a complaint model violates a release-significant contract."""


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def stable_sentence_id(
    matter_id: str,
    section_code: str,
    ordinal: int,
    text: str,
) -> str:
    """Return an identifier stable for identical semantic input."""

    payload = "\x1f".join(
        (matter_id.strip(), section_code.strip(), str(ordinal), _clean_text(text))
    )
    return f"sent-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class SentenceEvidence:
    sentence_id: str
    section_code: str
    text: str
    role: str
    evidence_ids: tuple[str, ...] = ()
    support_status: str = "pending"
    note: str | None = None

    @property
    def filing_significant(self) -> bool:
        return self.role in FILING_SIGNIFICANT_ROLES

    @property
    def release_supported(self) -> bool:
        if not self.filing_significant:
            return True
        return bool(self.evidence_ids) and self.support_status in SUPPORTED_STATES

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentence_id": self.sentence_id,
            "section_code": self.section_code,
            "text": self.text,
            "role": self.role,
            "evidence_ids": list(self.evidence_ids),
            "support_status": self.support_status,
            "note": self.note,
        }


@dataclass(frozen=True)
class ComplaintSection:
    code: str
    heading: str
    sentences: tuple[SentenceEvidence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "heading": self.heading,
            "sentences": [sentence.to_dict() for sentence in self.sentences],
        }


@dataclass
class StructuredComplaint:
    matter_id: str
    draft_id: str
    title: str
    sections: tuple[ComplaintSection, ...]
    enclosure_refs: tuple[str, ...] = ()
    source_versions: tuple[str, ...] = ()
    norm_passport_ids: tuple[str, ...] = ()
    issue_option_id: str | None = None
    approvals: dict[str, str] = field(default_factory=dict)
    formal_check: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def sentence_evidence_map(self) -> list[dict[str, Any]]:
        return [
            sentence.to_dict()
            for section in self.sections
            for sentence in section.sentences
        ]

    def unsupported_sentences(self) -> list[SentenceEvidence]:
        return [
            sentence
            for section in self.sections
            for sentence in section.sentences
            if not sentence.release_supported
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "matter_id": self.matter_id,
            "draft_id": self.draft_id,
            "title": self.title,
            "sections": [section.to_dict() for section in self.sections],
            "sentence_evidence_map": self.sentence_evidence_map(),
            "enclosure_refs": list(self.enclosure_refs),
            "source_versions": list(self.source_versions),
            "norm_passport_ids": list(self.norm_passport_ids),
            "issue_option_id": self.issue_option_id,
            "approvals": dict(self.approvals),
            "formal_check": dict(self.formal_check),
        }


def _iter_sentence_payloads(section: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    sentences = section.get("sentences")
    if sentences is None:
        sentences = section.get("paragraphs", ())
    if not isinstance(sentences, Sequence) or isinstance(sentences, (str, bytes)):
        raise ComplaintModelError(
            f"Раздел {section.get('code')!r}: sentences должен быть списком"
        )
    for sentence in sentences:
        if isinstance(sentence, str):
            yield {"text": sentence, "role": "narrative"}
        elif isinstance(sentence, Mapping):
            yield sentence
        else:
            raise ComplaintModelError("Предложение должно быть строкой или объектом")


def build_structured_complaint(payload: Mapping[str, Any]) -> StructuredComplaint:
    """Normalize and validate a complaint payload.

    This function accepts plain mappings so callers can use it without a
    database or a framework-specific model.
    """

    matter_id = _clean_text(payload.get("matter_id"))
    draft_id = _clean_text(payload.get("draft_id"))
    if not matter_id or not draft_id:
        raise ComplaintModelError("Нужны matter_id и draft_id")

    raw_sections = payload.get("sections", ())
    if not isinstance(raw_sections, Sequence) or isinstance(
        raw_sections, (str, bytes)
    ):
        raise ComplaintModelError("sections должен быть списком")

    sections: list[ComplaintSection] = []
    seen_codes: set[str] = set()
    for raw_section in raw_sections:
        if not isinstance(raw_section, Mapping):
            raise ComplaintModelError("Каждый раздел должен быть объектом")
        code = _clean_text(raw_section.get("code"))
        heading = _clean_text(raw_section.get("heading"))
        if not code or not heading:
            raise ComplaintModelError("У каждого раздела нужны code и heading")
        if code in seen_codes:
            raise ComplaintModelError(f"Повторяющийся раздел: {code}")
        seen_codes.add(code)

        sentences: list[SentenceEvidence] = []
        for ordinal, item in enumerate(_iter_sentence_payloads(raw_section), start=1):
            text = _clean_text(item.get("text"))
            if not text:
                raise ComplaintModelError(f"Раздел {code}: найдено пустое предложение")
            sentence_id = _clean_text(item.get("sentence_id")) or stable_sentence_id(
                matter_id, code, ordinal, text
            )
            evidence_ids = tuple(
                _clean_text(value)
                for value in item.get("evidence_ids", ())
                if _clean_text(value)
            )
            sentences.append(
                SentenceEvidence(
                    sentence_id=sentence_id,
                    section_code=code,
                    text=text,
                    role=_clean_text(item.get("role")) or "narrative",
                    evidence_ids=evidence_ids,
                    support_status=_clean_text(item.get("support_status")) or "pending",
                    note=_clean_text(item.get("note")) or None,
                )
            )
        sections.append(ComplaintSection(code=code, heading=heading, sentences=tuple(sentences)))

    missing = [code for code in REQUIRED_SECTION_CODES if code not in seen_codes]
    if missing:
        raise ComplaintModelError(
            "Отсутствуют обязательные разделы: " + ", ".join(missing)
        )

    complaint = StructuredComplaint(
        matter_id=matter_id,
        draft_id=draft_id,
        title=_clean_text(payload.get("title")) or "Жалоба в Конституционный Суд РФ",
        sections=tuple(sections),
        enclosure_refs=tuple(
            _clean_text(value)
            for value in payload.get("enclosure_refs", ())
            if _clean_text(value)
        ),
        source_versions=tuple(
            _clean_text(value)
            for value in payload.get("source_versions", ())
            if _clean_text(value)
        ),
        norm_passport_ids=tuple(
            _clean_text(value)
            for value in payload.get("norm_passport_ids", ())
            if _clean_text(value)
        ),
        issue_option_id=_clean_text(payload.get("issue_option_id")) or None,
        approvals={
            _clean_text(key): _clean_text(value)
            for key, value in dict(payload.get("approvals", {})).items()
            if _clean_text(key)
        },
        formal_check=dict(payload.get("formal_check", {})),
    )
    return complaint


def require_release_support(complaint: StructuredComplaint) -> None:
    """Raise with exact sentence identifiers when filing support is incomplete."""

    unsupported = complaint.unsupported_sentences()
    if unsupported:
        labels = ", ".join(sentence.sentence_id for sentence in unsupported)
        raise ComplaintModelError(
            "Не подтверждены значимые предложения: " + labels
        )
