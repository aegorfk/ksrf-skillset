"""Structured complaint composition with sentence-level provenance.

The composer deliberately does not generate legal facts or propositions.  It
normalizes an already prepared complaint model and prevents unsupported filing
sentences from being promoted to the release renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import re
from typing import Any, Iterable, Mapping, Sequence, overload

from .holding_binding import (
    HoldingEvidenceBindingAuthority,
    build_holding_binding_request,
    resolve_holding_evidence_binding,
    resolve_holding_evidence_binding_index,
)
from .practice_binding import (
    PracticeClaimEvidenceBindingAuthority,
    build_practice_claim_binding_request,
    resolve_practice_claim_evidence_binding,
    resolve_practice_claim_evidence_binding_index,
)
from .relief_binding import (
    ReliefEvidenceBindingAuthority,
    build_relief_binding_request,
    resolve_relief_evidence_binding,
    resolve_relief_evidence_binding_index,
)

SCHEMA_VERSION = "1.3"
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")

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


@dataclass(frozen=True)
class ReleaseSupportReceipts(Sequence[dict[str, Any]]):
    """Compatibility sequence plus typed receipts for every exact support gate."""

    relief_binding_receipts: tuple[dict[str, Any], ...] = ()
    holding_binding_receipts: tuple[dict[str, Any], ...] = ()
    holding_binding_index_receipt: dict[str, Any] | None = None
    practice_binding_receipts: tuple[dict[str, Any], ...] = ()
    practice_binding_index_receipt: dict[str, Any] | None = None

    def __len__(self) -> int:
        return len(self.relief_binding_receipts)

    @overload
    def __getitem__(self, index: int) -> dict[str, Any]: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[dict[str, Any], ...]: ...

    def __getitem__(
        self, index: int | slice
    ) -> dict[str, Any] | tuple[dict[str, Any], ...]:
        return self.relief_binding_receipts[index]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _exact_sentence_text(value: Any, *, label: str) -> str:
    """Keep release-significant prose byte-exact, including internal newlines."""

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        raise ComplaintModelError(
            f"{label} должен быть непустым точным текстом без краевых пробелов"
        )
    return value


def _optional_identifier(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ComplaintModelError(f"{label} должен быть непустой строкой")
    if value != _clean_text(value):
        raise ComplaintModelError(f"{label} должен быть канонической строкой без лишних пробелов")
    return value


def _strict_identifier_sequence(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ComplaintModelError(f"{label} должен быть списком строк")
    identifiers: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ComplaintModelError(f"{label} содержит пустой или нестроковый идентификатор")
        if item != _clean_text(item):
            raise ComplaintModelError(
                f"{label} содержит неканонический идентификатор с лишними пробелами"
            )
        identifiers.append(item)
    if len(identifiers) != len(set(identifiers)):
        raise ComplaintModelError(f"{label} содержит повторяющиеся идентификаторы (duplicate)")
    return tuple(sorted(identifiers))


def stable_sentence_id(
    matter_id: str,
    section_code: str,
    ordinal: int,
    text: str,
) -> str:
    """Return an identifier stable for identical semantic input."""

    payload = "\x1f".join(
        (matter_id.strip(), section_code.strip(), str(ordinal), text)
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
    claim_id: str | None = None
    practice_claim_id: str | None = None
    issue_option_id: str | None = None
    norm_passport_id: str | None = None
    application_record_ids: tuple[str, ...] = ()
    maximum_supported_inference: str | None = None

    @property
    def filing_significant(self) -> bool:
        return self.role in FILING_SIGNIFICANT_ROLES

    @property
    def release_supported(self) -> bool:
        if not self.filing_significant:
            return True
        return bool(self.evidence_ids) and self.support_status in SUPPORTED_STATES

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "sentence_id": self.sentence_id,
            "section_code": self.section_code,
            "text": self.text,
            "role": self.role,
            "evidence_ids": list(self.evidence_ids),
            "support_status": self.support_status,
            "note": self.note,
        }
        if self.claim_id is not None:
            result["claim_id"] = self.claim_id
        if self.practice_claim_id is not None:
            result["practice_claim_id"] = self.practice_claim_id
        if self.issue_option_id is not None:
            result["issue_option_id"] = self.issue_option_id
        if self.norm_passport_id is not None:
            result["norm_passport_id"] = self.norm_passport_id
        if self.application_record_ids:
            result["application_record_ids"] = list(self.application_record_ids)
        if self.maximum_supported_inference is not None:
            result["maximum_supported_inference"] = self.maximum_supported_inference
        if self.role == "legal_holding":
            result["holding_binding_status"] = (
                "bound"
                if (
                    self.evidence_ids
                    and self.claim_id
                    and self.maximum_supported_inference
                )
                else "unbound"
            )
        if self.role == "practice_claim":
            result["practice_binding_status"] = (
                "bound"
                if (
                    self.evidence_ids
                    and self.claim_id
                    and self.practice_claim_id
                    and self.issue_option_id
                    and self.maximum_supported_inference
                )
                else "unbound"
            )
        if self.role == "requested_remedy" and self.section_code == "requested_remedy":
            result["relief_binding_status"] = (
                "bound"
                if (
                    self.evidence_ids
                    and self.claim_id
                    and self.issue_option_id
                    and self.norm_passport_id
                    and self.application_record_ids
                )
                else "unbound"
            )
        return result


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
    issue_option_ids: tuple[str, ...] = ()
    issue_option_id: str | None = None
    approvals: dict[str, str] = field(default_factory=dict)
    formal_check: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def sentence_evidence_map(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for section in self.sections:
            for sentence in section.sentences:
                entry = sentence.to_dict()
                request = self.relief_binding_request(sentence)
                if request is not None:
                    entry["relief_binding_sha256"] = request[
                        "relief_binding_sha256"
                    ]
                holding_request = self.holding_binding_request(sentence)
                if holding_request is not None:
                    entry["holding_binding_sha256"] = holding_request[
                        "holding_binding_sha256"
                    ]
                practice_request = self.practice_claim_binding_request(sentence)
                if practice_request is not None:
                    entry["practice_binding_sha256"] = practice_request[
                        "practice_binding_sha256"
                    ]
                result.append(entry)
        return result

    def relief_binding_request(
        self, sentence: SentenceEvidence
    ) -> dict[str, Any] | None:
        if (
            sentence.role != "requested_remedy"
            or sentence.section_code != "requested_remedy"
        ):
            return None
        if not (
            sentence.claim_id
            and sentence.issue_option_id
            and sentence.norm_passport_id
            and sentence.application_record_ids
        ):
            return None
        return build_relief_binding_request(
            matter_id=self.matter_id,
            draft_id=self.draft_id,
            sentence_id=sentence.sentence_id,
            sentence_text=sentence.text,
            claim_id=sentence.claim_id,
            issue_option_id=sentence.issue_option_id,
            norm_passport_id=sentence.norm_passport_id,
            application_record_ids=sentence.application_record_ids,
            evidence_ids=sentence.evidence_ids,
        )

    def holding_binding_request(
        self, sentence: SentenceEvidence
    ) -> dict[str, Any] | None:
        if sentence.role != "legal_holding":
            return None
        if not (
            sentence.claim_id
            and sentence.evidence_ids
            and sentence.maximum_supported_inference
        ):
            return None
        return build_holding_binding_request(
            matter_id=self.matter_id,
            draft_id=self.draft_id,
            sentence_id=sentence.sentence_id,
            section_code=sentence.section_code,
            sentence_text=sentence.text,
            claim_id=sentence.claim_id,
            evidence_ids=sentence.evidence_ids,
            maximum_supported_inference=sentence.maximum_supported_inference,
        )

    def practice_claim_binding_request(
        self, sentence: SentenceEvidence
    ) -> dict[str, Any] | None:
        if sentence.role != "practice_claim":
            return None
        if not (
            sentence.claim_id
            and sentence.practice_claim_id
            and sentence.issue_option_id
            and sentence.evidence_ids
            and sentence.maximum_supported_inference
        ):
            return None
        return build_practice_claim_binding_request(
            matter_id=self.matter_id,
            draft_id=self.draft_id,
            sentence_id=sentence.sentence_id,
            section_code=sentence.section_code,
            sentence_text=sentence.text,
            claim_id=sentence.claim_id,
            practice_claim_id=sentence.practice_claim_id,
            issue_option_id=sentence.issue_option_id,
            evidence_ids=sentence.evidence_ids,
            maximum_supported_inference=sentence.maximum_supported_inference,
        )

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
            "issue_option_ids": list(self.issue_option_ids),
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

    matter_id = _optional_identifier(payload.get("matter_id"), label="matter_id")
    draft_id = _optional_identifier(payload.get("draft_id"), label="draft_id")
    if matter_id is None or draft_id is None:
        raise ComplaintModelError("Нужны matter_id и draft_id")

    raw_sections = payload.get("sections", ())
    if not isinstance(raw_sections, Sequence) or isinstance(
        raw_sections, (str, bytes)
    ):
        raise ComplaintModelError("sections должен быть списком")

    sections: list[ComplaintSection] = []
    seen_codes: set[str] = set()
    seen_sentence_ids: set[str] = set()
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
            raw_role = _clean_text(item.get("role")) or "narrative"
            role = "requested_remedy" if code == "requested_remedy" else raw_role
            text = (
                _exact_sentence_text(
                    item.get("text"), label=f"Раздел {code}: practice_claim.text"
                )
                if role == "practice_claim"
                else _clean_text(item.get("text"))
            )
            if not text:
                raise ComplaintModelError(f"Раздел {code}: найдено пустое предложение")
            if "sentence_id" in item:
                raw_sentence_id = item.get("sentence_id")
                if not isinstance(raw_sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
                    raw_sentence_id
                ):
                    raise ComplaintModelError(
                        "sentence_id должен соответствовать sent-<16 lowercase hex>"
                    )
                sentence_id = raw_sentence_id
            else:
                sentence_id = stable_sentence_id(matter_id, code, ordinal, text)
            if sentence_id in seen_sentence_ids:
                raise ComplaintModelError(
                    f"Повторяющийся sentence_id: {sentence_id}"
                )
            seen_sentence_ids.add(sentence_id)
            if raw_role == "requested_remedy" and code != "requested_remedy":
                raise ComplaintModelError(
                    f"requested_remedy_section_role_mismatch:{sentence_id}"
                )
            if role in {"requested_remedy", "legal_holding", "practice_claim"}:
                evidence_ids = _strict_identifier_sequence(
                    item.get("evidence_ids", ()), label=f"{sentence_id}.evidence_ids"
                )
            else:
                evidence_ids = tuple(
                    _clean_text(value)
                    for value in item.get("evidence_ids", ())
                    if _clean_text(value)
                )
            if role == "requested_remedy":
                application_record_ids = _strict_identifier_sequence(
                    item.get("application_record_ids", ()),
                    label=f"{sentence_id}.application_record_ids",
                )
            else:
                application_record_ids = ()
            sentences.append(
                SentenceEvidence(
                    sentence_id=sentence_id,
                    section_code=code,
                    text=text,
                    role=role,
                    evidence_ids=evidence_ids,
                    support_status=_clean_text(item.get("support_status")) or "pending",
                    note=_clean_text(item.get("note")) or None,
                    claim_id=_optional_identifier(
                        item.get("claim_id"), label=f"{sentence_id}.claim_id"
                    ),
                    practice_claim_id=_optional_identifier(
                        item.get("practice_claim_id"),
                        label=f"{sentence_id}.practice_claim_id",
                    ),
                    issue_option_id=_optional_identifier(
                        item.get("issue_option_id"),
                        label=f"{sentence_id}.issue_option_id",
                    ),
                    norm_passport_id=_optional_identifier(
                        item.get("norm_passport_id"),
                        label=f"{sentence_id}.norm_passport_id",
                    ),
                    application_record_ids=application_record_ids,
                    maximum_supported_inference=_optional_identifier(
                        item.get("maximum_supported_inference"),
                        label=f"{sentence_id}.maximum_supported_inference",
                    ),
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
        norm_passport_ids=_strict_identifier_sequence(
            payload.get("norm_passport_ids", ()), label="norm_passport_ids"
        ),
        issue_option_ids=(
            _strict_identifier_sequence(
                payload.get("issue_option_ids"), label="issue_option_ids"
            )
            if "issue_option_ids" in payload
            else ()
        ),
        issue_option_id=_optional_identifier(
            payload.get("issue_option_id"), label="issue_option_id"
        ),
        approvals={
            _clean_text(key): _clean_text(value)
            for key, value in dict(payload.get("approvals", {})).items()
            if _clean_text(key)
        },
        formal_check=dict(payload.get("formal_check", {})),
    )
    return complaint


def require_release_support(
    complaint: StructuredComplaint,
    *,
    relief_binding_authority: ReliefEvidenceBindingAuthority | Any | None = None,
    holding_binding_authority: HoldingEvidenceBindingAuthority | Any | None = None,
    practice_binding_authority: PracticeClaimEvidenceBindingAuthority | Any | None = None,
    require_holding_index: bool = False,
    require_practice_index: bool = False,
) -> ReleaseSupportReceipts:
    """Raise with exact sentence identifiers when filing support is incomplete."""

    integrity_errors: list[str] = []
    seen_sentence_ids: set[str] = set()
    seen_section_codes: set[str] = set()
    for section in complaint.sections:
        if section.code in seen_section_codes:
            integrity_errors.append(f"complaint_section_duplicate:{section.code}")
        seen_section_codes.add(section.code)
        for sentence in section.sentences:
            if sentence.section_code != section.code:
                integrity_errors.append(
                    "relief_binding_sentence_section_mismatch:"
                    f"{sentence.sentence_id}"
                )
            if not isinstance(sentence.sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
                sentence.sentence_id
            ):
                integrity_errors.append(
                    f"relief_binding_sentence_id_invalid:{sentence.sentence_id}"
                )
            elif sentence.sentence_id in seen_sentence_ids:
                integrity_errors.append(
                    f"relief_binding_sentence_duplicate:{sentence.sentence_id}"
                )
            seen_sentence_ids.add(sentence.sentence_id)
    for missing_code in sorted(set(REQUIRED_SECTION_CODES) - seen_section_codes):
        integrity_errors.append(f"complaint_section_missing:{missing_code}")
    if integrity_errors:
        raise ComplaintModelError(
            "Нарушена целостность предложений жалобы: "
            + ", ".join(dict.fromkeys(integrity_errors))
        )

    unsupported = complaint.unsupported_sentences()
    if unsupported:
        labels = ", ".join(sentence.sentence_id for sentence in unsupported)
        raise ComplaintModelError(
            "Не подтверждены значимые предложения: " + labels
        )

    binding_errors: list[str] = []
    receipts: list[dict[str, Any]] = []
    binding_requests: list[dict[str, Any]] = []
    requested_remedy_count = 0
    for section in complaint.sections:
        for sentence in section.sentences:
            is_remedy_section = section.code == "requested_remedy"
            is_remedy_role = sentence.role == "requested_remedy"
            if is_remedy_section != is_remedy_role:
                binding_errors.append(
                    f"requested_remedy_section_role_mismatch:{sentence.sentence_id}"
                )
            if not is_remedy_section:
                continue
            requested_remedy_count += 1
            if not is_remedy_role:
                continue
            missing = [
                label
                for label, value in (
                    ("claim_id", sentence.claim_id),
                    ("issue_option_id", sentence.issue_option_id),
                    ("norm_passport_id", sentence.norm_passport_id),
                    ("application_record_ids", sentence.application_record_ids),
                )
                if not value
            ]
            if missing:
                binding_errors.extend(
                    f"{sentence.sentence_id}:relief_binding_{label}_missing"
                    for label in missing
                )
                continue
            if sentence.issue_option_id not in complaint.issue_option_ids:
                binding_errors.append(
                    f"{sentence.sentence_id}:issue_option_not_in_complaint_projection"
                )
            if sentence.norm_passport_id not in complaint.norm_passport_ids:
                binding_errors.append(
                    f"{sentence.sentence_id}:norm_passport_not_in_complaint_projection"
                )
            request = complaint.relief_binding_request(sentence)
            if request is None:
                binding_errors.append(
                    f"{sentence.sentence_id}:relief_binding_request_incomplete"
                )
                continue
            binding_requests.append(request)
            errors, receipt = resolve_relief_evidence_binding(
                request, relief_binding_authority
            )
            binding_errors.extend(
                f"{sentence.sentence_id}:{error}" for error in errors
            )
            if receipt is not None:
                receipts.append(receipt)

    if requested_remedy_count == 0:
        binding_errors.append("requested_remedy_sentence_missing")
    elif binding_requests:
        index_errors, index_receipt = resolve_relief_evidence_binding_index(
            matter_id=complaint.matter_id,
            draft_id=complaint.draft_id,
            binding_requests=binding_requests,
            authority=relief_binding_authority,
        )
        binding_errors.extend(index_errors)
        if index_receipt is not None:
            receipts = [
                {**receipt, "binding_index_receipt": dict(index_receipt)}
                for receipt in receipts
            ]

    if binding_errors:
        raise ComplaintModelError(
            "Недействительны привязки просительной части: "
            + ", ".join(binding_errors)
        )

    holding_errors: list[str] = []
    holding_receipts: list[dict[str, Any]] = []
    holding_index_bindings: list[dict[str, Any]] = []
    for section in complaint.sections:
        for sentence in section.sentences:
            if sentence.role != "legal_holding":
                continue
            missing = [
                label
                for label, value in (
                    ("claim_id", sentence.claim_id),
                    ("evidence_ids", sentence.evidence_ids),
                    (
                        "maximum_supported_inference",
                        sentence.maximum_supported_inference,
                    ),
                )
                if not value
            ]
            if missing:
                holding_errors.extend(
                    f"{sentence.sentence_id}:holding_binding_{label}_missing"
                    for label in missing
                )
                continue
            request = complaint.holding_binding_request(sentence)
            if request is None:
                holding_errors.append(
                    f"{sentence.sentence_id}:holding_binding_request_incomplete"
                )
                continue
            holding_index_bindings.append(
                {
                    "sentence_id": sentence.sentence_id,
                    "section_code": section.code,
                    "role": "legal_holding",
                    "holding_binding_sha256": request["holding_binding_sha256"],
                }
            )
            errors, receipt = resolve_holding_evidence_binding(
                request, holding_binding_authority
            )
            holding_errors.extend(
                f"{sentence.sentence_id}:{error}" for error in errors
            )
            if receipt is not None:
                holding_receipts.append(receipt)

    holding_index_receipt: dict[str, Any] | None = None
    if holding_index_bindings or require_holding_index:
        index_errors, holding_index_receipt = (
            resolve_holding_evidence_binding_index(
                matter_id=complaint.matter_id,
                draft_id=complaint.draft_id,
                expected_bindings=holding_index_bindings,
                authority=holding_binding_authority,
            )
        )
        holding_errors.extend(index_errors)

    if holding_errors:
        raise ComplaintModelError(
            "Недействительны привязки правовых позиций: "
            + ", ".join(holding_errors)
        )

    practice_errors: list[str] = []
    practice_receipts: list[dict[str, Any]] = []
    practice_index_bindings: list[dict[str, Any]] = []
    for section in complaint.sections:
        for sentence in section.sentences:
            if sentence.role != "practice_claim":
                continue
            missing = [
                label
                for label, value in (
                    ("claim_id", sentence.claim_id),
                    ("practice_claim_id", sentence.practice_claim_id),
                    ("issue_option_id", sentence.issue_option_id),
                    ("evidence_ids", sentence.evidence_ids),
                    (
                        "maximum_supported_inference",
                        sentence.maximum_supported_inference,
                    ),
                )
                if not value
            ]
            if missing:
                practice_errors.extend(
                    f"{sentence.sentence_id}:practice_binding_{label}_missing"
                    for label in missing
                )
                continue
            if sentence.issue_option_id not in complaint.issue_option_ids:
                practice_errors.append(
                    f"{sentence.sentence_id}:practice_issue_not_in_complaint_projection"
                )
            request = complaint.practice_claim_binding_request(sentence)
            if request is None:
                practice_errors.append(
                    f"{sentence.sentence_id}:practice_binding_request_incomplete"
                )
                continue
            practice_index_bindings.append(
                {
                    "sentence_id": sentence.sentence_id,
                    "section_code": section.code,
                    "role": "practice_claim",
                    "claim_id": sentence.claim_id,
                    "practice_claim_id": sentence.practice_claim_id,
                    "issue_option_id": sentence.issue_option_id,
                    "practice_binding_sha256": request["practice_binding_sha256"],
                }
            )
            errors, receipt = resolve_practice_claim_evidence_binding(
                request, practice_binding_authority
            )
            practice_errors.extend(
                f"{sentence.sentence_id}:{error}" for error in errors
            )
            if receipt is not None:
                practice_receipts.append(receipt)

    practice_index_receipt: dict[str, Any] | None = None
    if practice_index_bindings or require_practice_index:
        index_errors, practice_index_receipt = (
            resolve_practice_claim_evidence_binding_index(
                matter_id=complaint.matter_id,
                draft_id=complaint.draft_id,
                expected_bindings=practice_index_bindings,
                authority=practice_binding_authority,
            )
        )
        practice_errors.extend(index_errors)
    if practice_index_receipt is not None and practice_receipts:
        index_revision = practice_index_receipt.get("authority_revision_id")
        receipt_revisions = {
            receipt.get("authority_revision_id") for receipt in practice_receipts
        }
        stable_matter_fields = (
            "matter_id",
            "draft_id",
            "case_id",
            "workspace_revision_id",
            "input_bindings_sha256",
        )
        matter_snapshot_values = [
            tuple(
                receipt["matter_binding"].get(field)
                for field in stable_matter_fields
            )
            for receipt in practice_receipts
            if isinstance(receipt.get("matter_binding"), Mapping)
        ]
        expected_matter_prefix = (complaint.matter_id, complaint.draft_id)
        shared_matter_snapshot = (
            matter_snapshot_values[0] if matter_snapshot_values else ()
        )
        one_matter_snapshot = bool(matter_snapshot_values) and all(
            snapshot == shared_matter_snapshot
            for snapshot in matter_snapshot_values[1:]
        )
        if (
            receipt_revisions != {index_revision}
            or len(matter_snapshot_values) != len(practice_receipts)
            or not one_matter_snapshot
            or shared_matter_snapshot[:2] != expected_matter_prefix
            or practice_index_receipt.get("matter_id") != complaint.matter_id
            or practice_index_receipt.get("draft_id") != complaint.draft_id
        ):
            practice_errors.append(
                "practice_binding_authority_snapshot_mismatch"
            )

    if practice_errors:
        raise ComplaintModelError(
            "Недействительны привязки судебной практики: "
            + ", ".join(practice_errors)
        )
    return ReleaseSupportReceipts(
        relief_binding_receipts=tuple(receipts),
        holding_binding_receipts=tuple(holding_receipts),
        holding_binding_index_receipt=holding_index_receipt,
        practice_binding_receipts=tuple(practice_receipts),
        practice_binding_index_receipt=practice_index_receipt,
    )
