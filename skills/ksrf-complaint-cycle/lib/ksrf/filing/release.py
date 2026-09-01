"""Build a hash-addressed filing pack while keeping filing human-controlled."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .composer import StructuredComplaint, require_release_support
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
from .renderer import (
    convert_docx_to_pdf,
    file_sha256,
    render_docx,
    validate_rendered_pair,
)
from .storage import canonical_json_bytes, stable_id
from .trusted_approvals import TrustedApprovalLedger


REQUIRED_APPROVALS = (
    "source_evidence",
    "norm_application",
    "constitutional_issue",
    "adverse_material",
    "legal_review",
)

_UPSTREAM_APPROVAL_PURPOSES = {
    "source_evidence": ("source_identity", "filing_source_evidence"),
    "norm_application": ("application", "filing_norm_application"),
    "constitutional_issue": ("issue", "filing_constitutional_issue"),
    "adverse_material": ("issue", "filing_adverse_material"),
    "legal_review": ("issue", "filing_legal_review"),
}
_REQUIRED_ARTIFACTS = {
    "complaint_docx": (
        "artifacts/constitutional-complaint.docx",
        ".docx",
        b"PK",
    ),
    "complaint_pdf": (
        "artifacts/constitutional-complaint.pdf",
        ".pdf",
        b"%PDF",
    ),
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTENCE_ID_RE = re.compile(r"^sent-[0-9a-f]{16}$")
_SOURCE_EVIDENCE_ID_RE = re.compile(r"^source-evidence:sha256:[0-9a-f]{64}$")
_APPROVAL_REQUEST_FIELDS = {
    "purpose",
    "subject_type",
    "subject_id",
    "fingerprint",
    "bindings",
}
_MANIFEST_STATUSES = {
    "blocked",
    "ready_for_expert_review",
    "ready_for_human_signing_filing",
}
_PRACTICE_BINDING_RECEIPT_FIELDS = {
    "schema_version",
    "sentence_id",
    "section_code",
    "practice_binding_sha256",
    "claim_id",
    "practice_claim_id",
    "issue_option_id",
    "evidence_ids",
    "maximum_supported_inference",
    "matter_binding",
    "practice_state_sha256",
    "ready_binding",
    "result_handoff_id",
    "result_sha256",
    "finding_receipts",
    "wording_review_event_sha256",
    "wording_review_sha256",
    "filing_validation_sha256",
    "prefiling_refresh_receipt",
    "issue_candidate_fingerprint",
    "issue_approval_requests",
    "trusted_approval_ids",
    "authority_revision_id",
    "checked_at",
}
_SCHEMA_DIRECTORY = Path(__file__).resolve().parents[3] / "schemas" / "ksrf_filing"
_MANIFEST_SCHEMA_FILE = _SCHEMA_DIRECTORY / "filing-package.schema.json"
_TRUSTED_APPROVAL_REFERENCE_SCHEMA_FILE = (
    _SCHEMA_DIRECTORY / "trusted-approval-reference.v1.schema.json"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


@lru_cache(maxsize=1)
def _filing_manifest_validator() -> Draft202012Validator:
    manifest_schema = json.loads(_MANIFEST_SCHEMA_FILE.read_text(encoding="utf-8"))
    approval_reference_schema = json.loads(
        _TRUSTED_APPROVAL_REFERENCE_SCHEMA_FILE.read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(manifest_schema)
    Draft202012Validator.check_schema(approval_reference_schema)
    approval_resource = Resource.from_contents(approval_reference_schema)
    registry = Registry().with_resource(
        str(approval_reference_schema["$id"]),
        approval_resource,
    )
    return Draft202012Validator(
        manifest_schema,
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _manifest_schema_errors(manifest: Mapping[str, Any]) -> list[str]:
    try:
        validation_errors = sorted(
            _filing_manifest_validator().iter_errors(dict(manifest)),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                str(error.validator),
            ),
        )
    except Exception as exc:
        return [f"manifest_schema_runtime_error:{type(exc).__name__}"]
    errors: list[str] = []
    for error in validation_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"manifest_schema_invalid:{location}:{error.validator}")
    return errors


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [str(item) for item in value]


def _upstream_review_basis(
    *,
    matter_id: Any,
    draft_id: Any,
    source_versions: Any,
    norm_passport_ids: Any,
    issue_option_ids: Any,
    issue_option_id: Any,
    sentence_evidence_map: Any,
    formal_check: Any,
) -> dict[str, Any]:
    return {
        "matter_id": str(matter_id or ""),
        "draft_id": str(draft_id or ""),
        "source_versions": _as_string_list(source_versions),
        "norm_passport_ids": _as_string_list(norm_passport_ids),
        "issue_option_ids": _as_string_list(issue_option_ids),
        "issue_option_id": str(issue_option_id or ""),
        "sentence_evidence_map": (
            [dict(item) for item in sentence_evidence_map]
            if isinstance(sentence_evidence_map, Sequence)
            and not isinstance(sentence_evidence_map, (str, bytes))
            and all(isinstance(item, Mapping) for item in sentence_evidence_map)
            else []
        ),
        "formal_check": dict(formal_check) if isinstance(formal_check, Mapping) else {},
    }


def _upstream_approval_request(
    approval_code: str,
    basis: Mapping[str, Any],
) -> dict[str, Any]:
    if approval_code not in _UPSTREAM_APPROVAL_PURPOSES:
        raise ValueError(f"unknown upstream approval code: {approval_code}")
    purpose, subject_type = _UPSTREAM_APPROVAL_PURPOSES[approval_code]
    bindings = {
        "approval_code": approval_code,
        "release_upstream_basis": dict(basis),
    }
    subject_id = f"{basis.get('draft_id') or 'missing-draft'}:{approval_code}"
    return {
        "purpose": purpose,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "fingerprint": stable_id("release-upstream-approval", bindings),
        "bindings": bindings,
    }


def release_upstream_approval_request(
    complaint: StructuredComplaint,
    approval_code: str,
) -> dict[str, Any]:
    """Build the exact trusted-approval request for one release prerequisite."""

    basis = _upstream_review_basis(
        matter_id=complaint.matter_id,
        draft_id=complaint.draft_id,
        source_versions=complaint.source_versions,
        norm_passport_ids=complaint.norm_passport_ids,
        issue_option_ids=complaint.issue_option_ids,
        issue_option_id=complaint.issue_option_id,
        sentence_evidence_map=complaint.sentence_evidence_map(),
        formal_check=complaint.formal_check,
    )
    return _upstream_approval_request(approval_code, basis)


def _manifest_upstream_approval_request(
    manifest: Mapping[str, Any], approval_code: str
) -> dict[str, Any]:
    basis = _upstream_review_basis(
        matter_id=manifest.get("matter_id"),
        draft_id=manifest.get("draft_id"),
        source_versions=manifest.get("source_versions"),
        norm_passport_ids=manifest.get("norm_passport_ids"),
        issue_option_ids=manifest.get("issue_option_ids"),
        issue_option_id=manifest.get("issue_option_id"),
        sentence_evidence_map=manifest.get("sentence_evidence_map"),
        formal_check=manifest.get("formal_check"),
    )
    return _upstream_approval_request(approval_code, basis)


def _approval_reference(value: Any) -> dict[str, Any] | None:
    raw: Any = value
    if isinstance(value, str):
        try:
            raw = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw, Mapping):
        return None
    approval_id = str(raw.get("approval_id") or "").strip()
    request = raw.get("approval_request")
    if not approval_id or not isinstance(request, Mapping):
        return None
    if set(request) != _APPROVAL_REQUEST_FIELDS:
        return None
    if not all(str(request.get(key) or "").strip() for key in _APPROVAL_REQUEST_FIELDS - {"bindings"}):
        return None
    if not isinstance(request.get("bindings"), Mapping) or not request["bindings"]:
        return None
    reference = dict(raw)
    reference["approval_id"] = approval_id
    reference["approval_request"] = {
        "purpose": str(request["purpose"]),
        "subject_type": str(request["subject_type"]),
        "subject_id": str(request["subject_id"]),
        "fingerprint": str(request["fingerprint"]),
        "bindings": dict(request["bindings"]),
    }
    return reference


def _copy_enclosures(
    enclosure_sources: Iterable[str | Path],
    enclosure_refs: Sequence[str],
    destination: Path,
) -> list[dict[str, Any]]:
    destination.mkdir(parents=True, exist_ok=True)
    sources = list(enclosure_sources)
    references = [str(item).strip() for item in enclosure_refs]
    items: list[dict[str, Any]] = []
    used_names: set[str] = set()
    total = max(len(sources), len(references))
    for ordinal in range(1, total + 1):
        reference = references[ordinal - 1] if ordinal <= len(references) else ""
        source_value = sources[ordinal - 1] if ordinal <= len(sources) else ""
        source_text = str(source_value).strip()
        source = Path(source_text).resolve() if source_text else None
        if source is None or not source.is_file():
            items.append(
                {
                    "number": ordinal,
                    "reference": reference,
                    "file_name": source.name if source is not None else None,
                    "source": str(source) if source is not None else None,
                    "status": "missing",
                }
            )
            continue
        name = source.name
        if name in used_names:
            name = f"{ordinal:02d}-{name}"
        used_names.add(name)
        target = destination / name
        shutil.copy2(source, target)
        digest = file_sha256(target)
        relative_path = f"enclosures/{name}"
        enclosure_id = stable_id(
            "release-enclosure",
            {
                "number": ordinal,
                "reference": reference,
                "file_name": name,
                "relative_path": relative_path,
                "sha256": digest,
            },
        )
        items.append(
            {
                "number": ordinal,
                "enclosure_id": enclosure_id,
                "reference": reference,
                "file_name": name,
                "relative_path": relative_path,
                "source": str(source),
                "path": str(target),
                "status": "included",
                "sha256": digest,
                "size": target.stat().st_size,
            }
        )
    return items


def _qa_artifacts(previews_dir: Path, pack_root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(
        previews_dir.glob("page-*.png"),
        key=lambda item: int(item.stem.split("-")[-1]),
    ):
        page_number = int(path.stem.split("-")[-1])
        digest = file_sha256(path)
        relative_path = path.relative_to(pack_root).as_posix()
        item = {
            "kind": "page_preview",
            "page_number": page_number,
            "file_name": path.name,
            "relative_path": relative_path,
            "path": str(path),
            "mime_type": "image/png",
            "size": path.stat().st_size,
            "sha256": digest,
            "status": "complete",
        }
        item["qa_artifact_id"] = stable_id(
            "release-qa-artifact",
            {
                "kind": item["kind"],
                "page_number": page_number,
                "relative_path": relative_path,
                "sha256": digest,
            },
        )
        items.append(item)
    return items


def _formal_check_ready(formal_check: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if formal_check.get("status") != "passed":
        reasons.append("formal_check_not_passed")
    if formal_check.get("fresh") is not True:
        reasons.append("formal_check_not_fresh")
    if not formal_check.get("official_anchor"):
        reasons.append("formal_check_official_anchor_missing")
    return not reasons, reasons


def _release_basis_payload(manifest: Mapping[str, Any]) -> dict[str, Any]:
    # Bind every stable manifest field, including future substantive additions.
    # Only approval/projection fields that necessarily change during approval and
    # machine-local locators are excluded from the release basis.
    excluded_top_level = {
        "status",
        "release_approval",
        "release_basis_sha256",
        "pack_root",
        "manifest_path",
        "manifest_sha256",
    }
    payload = {
        key: value
        for key, value in manifest.items()
        if key not in excluded_top_level
    }
    artifacts = manifest.get("artifacts")
    artifact_items = (
        list(artifacts)
        if isinstance(artifacts, Sequence) and not isinstance(artifacts, (str, bytes))
        else []
    )
    payload["artifacts"] = [
        ({key: value for key, value in item.items() if key != "path"}
         if isinstance(item, Mapping)
         else item)
        for item in artifact_items
    ]
    qa_artifacts = manifest.get("qa_artifacts")
    qa_items = (
        list(qa_artifacts)
        if isinstance(qa_artifacts, Sequence)
        and not isinstance(qa_artifacts, (str, bytes))
        else []
    )
    payload["qa_artifacts"] = [
        ({key: value for key, value in item.items() if key != "path"}
         if isinstance(item, Mapping)
         else item)
        for item in qa_items
    ]
    enclosures = manifest.get("enclosures")
    enclosure_items = (
        list(enclosures)
        if isinstance(enclosures, Sequence) and not isinstance(enclosures, (str, bytes))
        else []
    )
    payload["enclosures"] = [
        (
            {
                key: value
                for key, value in item.items()
                if key not in {"path", "source"}
            }
            if isinstance(item, Mapping)
            else item
        )
        for item in enclosure_items
    ]
    return payload


def release_basis_sha256(manifest: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _release_basis_payload(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def release_approval_request(manifest: Mapping[str, Any]) -> dict[str, Any]:
    basis_sha256 = release_basis_sha256(manifest)
    bindings = {
        "matter_id": str(manifest.get("matter_id") or ""),
        "draft_id": str(manifest.get("draft_id") or ""),
        "release_basis_sha256": basis_sha256,
    }
    return {
        "purpose": "release",
        "subject_type": "filing_release_pack",
        "subject_id": bindings["draft_id"],
        "fingerprint": stable_id("release-approval", bindings),
        "bindings": bindings,
    }


def build_release_pack(
    complaint: StructuredComplaint,
    output_dir: str | Path,
    *,
    enclosure_sources: Iterable[str | Path] = (),
    soffice_path: str | Path | None = None,
    pdftoppm_path: str | Path | None = None,
    relief_binding_authority: ReliefEvidenceBindingAuthority | Any | None = None,
    holding_binding_authority: HoldingEvidenceBindingAuthority | Any | None = None,
    practice_binding_authority: (
        PracticeClaimEvidenceBindingAuthority | Any | None
    ) = None,
) -> dict[str, Any]:
    """Create real filing artifacts and return a release manifest.

    The function never signs, pays, transmits, or claims that a filing occurred.
    """

    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    artifacts_dir = destination / "artifacts"
    previews_dir = destination / "previews"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []
    relief_binding_receipts: list[dict[str, Any]] = []
    holding_binding_receipts: list[dict[str, Any]] = []
    holding_binding_index_receipt: dict[str, Any] | None = None
    practice_binding_receipts: list[dict[str, Any]] = []
    practice_binding_index_receipt: dict[str, Any] | None = None
    try:
        support_receipts = require_release_support(
            complaint,
            relief_binding_authority=relief_binding_authority,
            holding_binding_authority=holding_binding_authority,
            practice_binding_authority=practice_binding_authority,
            require_holding_index=True,
            require_practice_index=True,
        )
        relief_binding_receipts = list(
            support_receipts.relief_binding_receipts
        )
        holding_binding_receipts = list(
            support_receipts.holding_binding_receipts
        )
        if support_receipts.holding_binding_index_receipt is not None:
            holding_binding_index_receipt = dict(
                support_receipts.holding_binding_index_receipt
            )
        practice_binding_receipts = list(
            support_receipts.practice_binding_receipts
        )
        if support_receipts.practice_binding_index_receipt is not None:
            practice_binding_index_receipt = dict(
                support_receipts.practice_binding_index_receipt
            )
    except ValueError as exc:
        blockers.append(str(exc))

    docx_path = artifacts_dir / "constitutional-complaint.docx"
    pdf_path = artifacts_dir / "constitutional-complaint.pdf"
    artifacts: list[dict[str, Any]] = []
    qa_artifacts: list[dict[str, Any]] = []
    qa: dict[str, Any] = {"passed": False, "reason": "not_run"}
    try:
        docx = render_docx(complaint, docx_path)
        artifacts.append(
            {
                **docx.to_dict(),
                "file_name": docx_path.name,
                "relative_path": docx_path.relative_to(destination).as_posix(),
            }
        )
        pdf = convert_docx_to_pdf(
            docx_path, pdf_path, soffice_path=soffice_path
        )
        artifacts.append(
            {
                **pdf.to_dict(),
                "file_name": pdf_path.name,
                "relative_path": pdf_path.relative_to(destination).as_posix(),
            }
        )
        qa = validate_rendered_pair(
            complaint,
            docx_path,
            pdf_path,
            preview_dir=previews_dir,
            pdftoppm_path=pdftoppm_path,
        )
        qa_artifacts = _qa_artifacts(previews_dir, destination)
        if not qa.get("passed"):
            blockers.append("render_or_visual_qa_failed")
        if not qa_artifacts:
            blockers.append("qa_artifacts_missing")
    except Exception as exc:  # error becomes a fail-closed manifest, not a false release
        blockers.append(f"artifact_generation_failed: {exc}")
        qa = {"passed": False, "reason": str(exc)}

    enclosure_refs = [str(item).strip() for item in complaint.enclosure_refs]
    enclosures = _copy_enclosures(
        enclosure_sources,
        enclosure_refs,
        destination / "enclosures",
    )
    missing_enclosures = [item for item in enclosures if item["status"] != "included"]
    if missing_enclosures:
        blockers.append("missing_enclosure_files")
    if len(complaint.enclosure_refs) != len(enclosures):
        blockers.append("enclosure_reference_count_mismatch")
    for item in enclosures:
        reference = str(item.get("reference") or "")
        file_name = str(item.get("file_name") or "")
        if item.get("status") != "included":
            blockers.append(f"missing_enclosure:{reference or file_name or item['number']}")
        elif reference != file_name:
            blockers.append(
                "enclosure_reference_file_mismatch:"
                f"{item['number']}:{reference or '<missing>'}:{file_name or '<missing>'}"
            )

    formal_ready, formal_reasons = _formal_check_ready(complaint.formal_check)
    blockers.extend(formal_reasons)
    approval_references: dict[str, dict[str, Any]] = {}
    missing_approvals: list[str] = []
    for code in REQUIRED_APPROVALS:
        reference = _approval_reference(complaint.approvals.get(code))
        expected_request = release_upstream_approval_request(complaint, code)
        if reference is None or reference.get("approval_request") != expected_request:
            missing_approvals.append(code)
            continue
        approval_references[code] = reference

    if not complaint.source_versions:
        blockers.append("source_versions_missing")
    if not complaint.norm_passport_ids:
        blockers.append("norm_passport_ids_missing")
    if not complaint.issue_option_ids:
        blockers.append("issue_option_ids_missing")

    release_status = "blocked" if blockers else "ready_for_expert_review"
    relief_binding_index_receipt = (
        dict(relief_binding_receipts[0].get("binding_index_receipt") or {})
        if relief_binding_receipts
        else None
    )

    manifest_path = destination / "filing-package-manifest.json"

    manifest: dict[str, Any] = {
        "schema_version": "1.3",
        "matter_id": complaint.matter_id,
        "draft_id": complaint.draft_id,
        "created_at": _now(),
        "status": release_status,
        "human_only_actions": ["signature", "fee_or_exemption_confirmation", "filing"],
        "filing_performed": False,
        "source_versions": list(complaint.source_versions),
        "norm_passport_ids": list(complaint.norm_passport_ids),
        "issue_option_ids": list(complaint.issue_option_ids),
        "issue_option_id": complaint.issue_option_id,
        "approvals": approval_references,
        "missing_approvals": missing_approvals,
        "formal_check": dict(complaint.formal_check),
        "formal_check_ready": formal_ready,
        "sentence_evidence_map": complaint.sentence_evidence_map(),
        "relief_binding_receipts": relief_binding_receipts,
        "relief_binding_index_receipt": relief_binding_index_receipt,
        "holding_binding_receipts": holding_binding_receipts,
        "holding_binding_index_receipt": holding_binding_index_receipt,
        "practice_binding_receipts": practice_binding_receipts,
        "practice_binding_index_receipt": practice_binding_index_receipt,
        "enclosure_refs": enclosure_refs,
        "artifacts": artifacts,
        "qa_artifacts": qa_artifacts,
        "enclosures": enclosures,
        "render_qa": qa,
        "blockers": sorted(set(blockers)),
        "pack_root": str(destination),
        "manifest_path": str(manifest_path),
    }
    schema_errors = _manifest_schema_errors(manifest)
    if schema_errors:
        manifest["blockers"] = sorted(set(manifest["blockers"] + schema_errors))
        manifest["status"] = "blocked"
    manifest["release_basis_sha256"] = release_basis_sha256(manifest)
    _write_json(manifest_path, manifest)
    manifest["manifest_sha256"] = file_sha256(manifest_path)
    return manifest


def _pack_location(
    manifest: Mapping[str, Any],
) -> tuple[Path | None, Path | None, list[str]]:
    errors: list[str] = []
    root_value = str(manifest.get("pack_root") or "").strip()
    manifest_value = str(manifest.get("manifest_path") or "").strip()
    if not root_value:
        errors.append("pack_root_missing")
        return None, None, errors
    root = Path(root_value).resolve()
    if root == Path(root.anchor):
        errors.append(f"unsafe_pack_root:{root}")
        return None, None, errors
    if not manifest_value:
        errors.append("manifest_path_missing")
        return root, None, errors
    manifest_path = Path(manifest_value).resolve()
    expected_manifest = (root / "filing-package-manifest.json").resolve()
    if manifest_path != expected_manifest:
        errors.append(f"manifest_path_not_pack_local:{manifest_path}")
    if not manifest_path.is_file():
        errors.append(f"missing:{manifest_path}")
    return root, manifest_path, errors


def _declared_file_errors(
    item: Mapping[str, Any],
    *,
    pack_root: Path | None,
    expected_relative_path: str,
    expected_status: str,
    label: str,
    expected_magic: bytes | None = None,
) -> tuple[list[str], Path | None]:
    errors: list[str] = []
    if item.get("status") != expected_status:
        errors.append(f"declared_file_incomplete:{label}")
    relative_value = str(item.get("relative_path") or "")
    relative = Path(relative_value)
    if (
        not relative_value
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.as_posix() != expected_relative_path
    ):
        errors.append(f"declared_relative_path_mismatch:{label}:{relative_value}")
    path_value = str(item.get("path") or "")
    if not path_value or pack_root is None:
        errors.append(f"declared_path_missing:{label}")
        return errors, None
    lexical_path = Path(path_value)
    declared_path = lexical_path.resolve()
    expected_path = (pack_root / expected_relative_path).resolve()
    try:
        declared_path.relative_to(pack_root)
    except ValueError:
        errors.append(f"unsafe_pack_path:{label}:{declared_path}")
    if lexical_path.is_symlink():
        errors.append(f"unsafe_pack_symlink:{label}:{lexical_path}")
    if declared_path != expected_path:
        errors.append(f"declared_path_mismatch:{label}:{declared_path}")
    digest = str(item.get("sha256") or "")
    if not _SHA256_RE.fullmatch(digest):
        errors.append(f"invalid_sha256:{label}")
    size = item.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        errors.append(f"invalid_size:{label}")
    if not declared_path.is_file():
        errors.append(f"missing:{declared_path}")
        return errors, expected_path
    if isinstance(size, int) and declared_path.stat().st_size != size:
        errors.append(f"size_mismatch:{declared_path}")
    if _SHA256_RE.fullmatch(digest) and file_sha256(declared_path) != digest:
        errors.append(f"hash_mismatch:{declared_path}")
    if expected_magic is not None:
        try:
            magic = declared_path.read_bytes()[: len(expected_magic)]
        except OSError:
            magic = b""
        if magic != expected_magic:
            errors.append(f"invalid_file_signature:{label}")
    return errors, expected_path


def _manifest_file_errors(
    manifest: Mapping[str, Any],
    manifest_path: Path | None,
) -> list[str]:
    if manifest_path is None or not manifest_path.is_file():
        return []
    errors: list[str] = []
    declared_hash = str(manifest.get("manifest_sha256") or "")
    if declared_hash:
        if not _SHA256_RE.fullmatch(declared_hash):
            errors.append("manifest_hash_invalid")
        elif file_sha256(manifest_path) != declared_hash:
            errors.append("manifest_hash_mismatch")
    try:
        stored_value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append("manifest_file_invalid_json")
        return errors
    if not isinstance(stored_value, Mapping):
        errors.append("manifest_file_not_object")
        return errors
    expected = dict(manifest)
    expected.pop("manifest_sha256", None)
    observed = dict(stored_value)
    observed.pop("manifest_sha256", None)
    if observed != expected:
        errors.append("manifest_file_content_mismatch")
    return errors


def _upstream_approval_errors(
    manifest: Mapping[str, Any],
    approval_ledger: TrustedApprovalLedger | None,
) -> list[str]:
    errors: list[str] = []
    approvals = manifest.get("approvals")
    approval_map = approvals if isinstance(approvals, Mapping) else {}
    structurally_missing: list[str] = []
    for code in REQUIRED_APPROVALS:
        reference = _approval_reference(approval_map.get(code))
        expected_request = _manifest_upstream_approval_request(manifest, code)
        if reference is None:
            structurally_missing.append(code)
            errors.append(f"upstream_approval_missing:{code}")
            continue
        if reference.get("approval_request") != expected_request:
            structurally_missing.append(code)
            errors.append(f"upstream_approval_binding_mismatch:{code}")
            continue
        if approval_ledger is None:
            errors.append(f"upstream_approval_host_verifier_required:{code}")
            continue
        validation = approval_ledger.validate_approval(
            str(reference.get("approval_id") or ""),
            **expected_request,
        )
        if validation.get("valid") is not True:
            errors.append(
                f"upstream_approval_invalid:{code}:"
                + str(validation.get("reason_code") or "approval_invalid")
            )
    declared_missing = manifest.get("missing_approvals")
    if not isinstance(declared_missing, list) or declared_missing != structurally_missing:
        errors.append("missing_approvals_projection_mismatch")
    return errors


def _manifest_contract_errors(
    manifest: Mapping[str, Any],
    *,
    approval_ledger: TrustedApprovalLedger | None,
    verify_manifest_file: bool = True,
) -> list[str]:
    errors = _manifest_schema_errors(manifest)
    if manifest.get("schema_version") != "1.3":
        errors.append("manifest_schema_version_invalid")
    if not str(manifest.get("matter_id") or "").strip():
        errors.append("manifest_matter_id_missing")
    if not str(manifest.get("draft_id") or "").strip():
        errors.append("manifest_draft_id_missing")
    if manifest.get("status") not in _MANIFEST_STATUSES:
        errors.append("manifest_status_invalid")
    if manifest.get("filing_performed") is not False:
        errors.append("filing_performed_must_be_false")
    if not _as_string_list(manifest.get("source_versions")):
        errors.append("source_versions_missing")
    if not _as_string_list(manifest.get("norm_passport_ids")):
        errors.append("norm_passport_ids_missing")
    if not _as_string_list(manifest.get("issue_option_ids")):
        errors.append("issue_option_ids_missing")
    required_human_actions = {
        "signature",
        "fee_or_exemption_confirmation",
        "filing",
    }
    if not required_human_actions.issubset(
        set(_as_string_list(manifest.get("human_only_actions")))
    ):
        errors.append("human_only_actions_incomplete")
    blockers = manifest.get("blockers")
    if not isinstance(blockers, list):
        errors.append("manifest_blockers_invalid")
    elif manifest.get("status") in {
        "ready_for_expert_review",
        "ready_for_human_signing_filing",
    } and blockers:
        errors.append("ready_manifest_has_blockers")
    errors.extend(_manifest_relief_binding_projection_errors(manifest))
    errors.extend(_manifest_holding_binding_projection_errors(manifest))
    errors.extend(_manifest_practice_binding_projection_errors(manifest))

    pack_root, manifest_path, location_errors = _pack_location(manifest)
    errors.extend(location_errors)
    if verify_manifest_file:
        errors.extend(_manifest_file_errors(manifest, manifest_path))
    declared_paths: set[Path] = set()
    if manifest_path is not None:
        declared_paths.add(manifest_path)

    artifacts = manifest.get("artifacts")
    artifact_list = (
        list(artifacts)
        if isinstance(artifacts, Sequence) and not isinstance(artifacts, (str, bytes))
        else []
    )
    for kind, (relative_path, suffix, magic) in _REQUIRED_ARTIFACTS.items():
        matches = [
            item
            for item in artifact_list
            if isinstance(item, Mapping) and item.get("kind") == kind
        ]
        if not matches:
            errors.append(f"required_artifact_missing:{kind}")
            errors.append(f"missing_file:{relative_path}")
            continue
        if len(matches) != 1:
            errors.append(f"required_artifact_duplicate:{kind}")
            continue
        item = matches[0]
        if Path(str(item.get("file_name") or item.get("path") or "")).suffix.lower() != suffix:
            errors.append(f"required_artifact_wrong_format:{kind}")
        file_errors, expected_path = _declared_file_errors(
            item,
            pack_root=pack_root,
            expected_relative_path=relative_path,
            expected_status="complete",
            label=kind,
            expected_magic=magic,
        )
        errors.extend(file_errors)
        if expected_path is not None:
            declared_paths.add(expected_path)
    unexpected_artifact_kinds: list[str] = []
    for item in artifact_list:
        if not isinstance(item, Mapping):
            unexpected_artifact_kinds.append("<invalid>")
        elif item.get("kind") not in _REQUIRED_ARTIFACTS:
            unexpected_artifact_kinds.append(str(item.get("kind") or "<missing>"))
    unexpected_artifact_kinds.sort()
    errors.extend(f"unexpected_artifact:{kind}" for kind in unexpected_artifact_kinds)

    qa = manifest.get("render_qa")
    qa_map = qa if isinstance(qa, Mapping) else {}
    if qa_map.get("passed") is not True:
        errors.append("render_or_visual_qa_not_passed")
    preview_count = qa_map.get("preview_count")
    page_count = qa_map.get("page_count")
    if (
        not isinstance(preview_count, int)
        or isinstance(preview_count, bool)
        or preview_count <= 0
        or page_count != preview_count
    ):
        errors.append("render_qa_page_inventory_invalid")
    qa_artifacts = manifest.get("qa_artifacts")
    qa_list = (
        list(qa_artifacts)
        if isinstance(qa_artifacts, Sequence)
        and not isinstance(qa_artifacts, (str, bytes))
        else []
    )
    if not qa_list:
        errors.append("qa_artifacts_missing")
    elif isinstance(preview_count, int) and len(qa_list) != preview_count:
        errors.append("qa_artifact_count_mismatch")
    seen_qa_ids: set[str] = set()
    for ordinal, raw_item in enumerate(qa_list, start=1):
        if not isinstance(raw_item, Mapping):
            errors.append(f"qa_artifact_invalid:{ordinal}")
            continue
        page_number = raw_item.get("page_number")
        if page_number != ordinal or raw_item.get("kind") != "page_preview":
            errors.append(f"qa_artifact_sequence_mismatch:{ordinal}")
        relative_path = f"previews/page-{ordinal}.png"
        file_errors, expected_path = _declared_file_errors(
            raw_item,
            pack_root=pack_root,
            expected_relative_path=relative_path,
            expected_status="complete",
            label=f"qa_page:{ordinal}",
            expected_magic=b"\x89PNG\r\n\x1a\n",
        )
        errors.extend(file_errors)
        if expected_path is not None:
            declared_paths.add(expected_path)
        expected_id = stable_id(
            "release-qa-artifact",
            {
                "kind": "page_preview",
                "page_number": ordinal,
                "relative_path": relative_path,
                "sha256": str(raw_item.get("sha256") or ""),
            },
        )
        qa_id = str(raw_item.get("qa_artifact_id") or "")
        if qa_id != expected_id:
            errors.append(f"qa_artifact_id_mismatch:{ordinal}")
        if not qa_id or qa_id in seen_qa_ids:
            errors.append(f"qa_artifact_id_duplicate:{ordinal}")
        seen_qa_ids.add(qa_id)

    references = _as_string_list(manifest.get("enclosure_refs"))
    enclosures = manifest.get("enclosures")
    enclosure_list = (
        list(enclosures)
        if isinstance(enclosures, Sequence) and not isinstance(enclosures, (str, bytes))
        else []
    )
    if len(references) != len(enclosure_list):
        errors.append("enclosure_reference_count_mismatch")
    seen_enclosure_ids: set[str] = set()
    seen_paths: set[str] = set()
    for ordinal, raw_item in enumerate(enclosure_list, start=1):
        if not isinstance(raw_item, Mapping):
            errors.append(f"enclosure_invalid:{ordinal}")
            continue
        reference = references[ordinal - 1] if ordinal <= len(references) else ""
        file_name = str(raw_item.get("file_name") or "")
        if raw_item.get("number") != ordinal or raw_item.get("reference") != reference:
            errors.append(f"enclosure_reference_mismatch:{ordinal}:{reference}")
        if not reference or Path(reference).name != reference or file_name != reference:
            errors.append(
                f"enclosure_reference_file_mismatch:{ordinal}:"
                f"{reference or '<missing>'}:{file_name or '<missing>'}"
            )
        relative_path = f"enclosures/{file_name}"
        file_errors, expected_path = _declared_file_errors(
            raw_item,
            pack_root=pack_root,
            expected_relative_path=relative_path,
            expected_status="included",
            label=f"enclosure:{ordinal}:{reference or file_name}",
        )
        errors.extend(file_errors)
        if expected_path is not None:
            declared_paths.add(expected_path)
        expected_id = stable_id(
            "release-enclosure",
            {
                "number": ordinal,
                "reference": reference,
                "file_name": file_name,
                "relative_path": relative_path,
                "sha256": str(raw_item.get("sha256") or ""),
            },
        )
        enclosure_id = str(raw_item.get("enclosure_id") or "")
        if enclosure_id != expected_id:
            errors.append(f"enclosure_id_mismatch:{ordinal}:{reference or file_name}")
        if not enclosure_id or enclosure_id in seen_enclosure_ids:
            errors.append(f"enclosure_id_duplicate:{ordinal}")
        if relative_path in seen_paths:
            errors.append(f"enclosure_path_duplicate:{relative_path}")
        seen_enclosure_ids.add(enclosure_id)
        seen_paths.add(relative_path)

    errors.extend(_upstream_approval_errors(manifest, approval_ledger))

    formal_check_value = manifest.get("formal_check")
    formal_check = (
        dict(formal_check_value)
        if isinstance(formal_check_value, Mapping)
        else {}
    )
    formal_ready, _formal_reasons = _formal_check_ready(formal_check)
    if manifest.get("formal_check_ready") is not formal_ready:
        errors.append("formal_check_projection_mismatch")

    if pack_root is not None and pack_root.is_dir() and not location_errors:
        for candidate in sorted(pack_root.rglob("*")):
            if not (candidate.is_file() or candidate.is_symlink()):
                continue
            resolved = candidate.resolve()
            relative_name = candidate.relative_to(pack_root).as_posix()
            if candidate.is_symlink():
                errors.append(f"unsafe_pack_symlink:{relative_name}")
            if resolved not in declared_paths:
                errors.append(f"extra_file:{relative_name}")
    return errors


def _manifest_binding_identifier_list(
    value: Any,
    *,
    label: str,
) -> tuple[list[str], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"relief_binding_identifier_list_invalid:{label}"]
    identifiers: list[str] = []
    errors: list[str] = []
    for ordinal, raw in enumerate(value, start=1):
        if (
            not isinstance(raw, str)
            or not raw
            or raw != " ".join(raw.split())
        ):
            errors.append(
                f"relief_binding_identifier_invalid:{label}:{ordinal}"
            )
            continue
        identifiers.append(raw)
    if len(identifiers) != len(set(identifiers)):
        errors.append(f"relief_binding_identifier_duplicate:{label}")
    return identifiers, errors


def _manifest_binding_string(
    value: Any,
    *,
    label: str,
) -> tuple[str, list[str]]:
    if (
        not isinstance(value, str)
        or not value
        or value != " ".join(value.split())
    ):
        return "", [f"relief_binding_string_invalid:{label}"]
    return value, []


def _manifest_relief_binding_requests(
    manifest: Mapping[str, Any],
) -> tuple[
    list[tuple[dict[str, Any], Mapping[str, Any]]],
    list[dict[str, Any]],
    list[str],
]:
    raw_entries = manifest.get("sentence_evidence_map")
    entries: list[Any] = []
    errors: list[str] = []
    if isinstance(raw_entries, Sequence) and not isinstance(
        raw_entries, (str, bytes)
    ):
        entries = list(raw_entries)
    else:
        errors.append("relief_binding_sentence_evidence_map_invalid")
    raw_receipts = manifest.get("relief_binding_receipts")
    receipts: list[Any] = []
    if isinstance(raw_receipts, Sequence) and not isinstance(
        raw_receipts, (str, bytes)
    ):
        receipts = list(raw_receipts)
    else:
        errors.append("relief_binding_receipts_invalid")
    receipt_by_sentence: dict[str, Mapping[str, Any]] = {}
    for ordinal, raw in enumerate(receipts, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"relief_binding_receipt_invalid:{ordinal}")
            continue
        raw_sentence_id = raw.get("sentence_id")
        if not isinstance(raw_sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            raw_sentence_id
        ):
            errors.append(f"relief_binding_receipt_sentence_id_invalid:{ordinal}")
            continue
        sentence_id = raw_sentence_id
        if sentence_id in receipt_by_sentence:
            errors.append(f"relief_binding_receipt_duplicate:{sentence_id}")
        else:
            receipt_by_sentence[sentence_id] = raw

    entry_sentence_ids: dict[int, str] = {}
    seen_sentence_ids: set[str] = set()
    for ordinal, raw in enumerate(entries, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"relief_binding_manifest_entry_invalid:{ordinal}")
            continue
        raw_sentence_id = raw.get("sentence_id")
        if not isinstance(raw_sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            raw_sentence_id
        ):
            errors.append(f"relief_binding_sentence_id_invalid:{ordinal}")
            continue
        entry_sentence_ids[ordinal] = raw_sentence_id
        if raw_sentence_id in seen_sentence_ids:
            errors.append(f"relief_binding_sentence_duplicate:{raw_sentence_id}")
        seen_sentence_ids.add(raw_sentence_id)

    pairs: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    requests: list[dict[str, Any]] = []
    expected_sentence_ids: set[str] = set()
    requested_remedy_count = 0
    issue_option_id_values, issue_option_errors = _manifest_binding_identifier_list(
        manifest.get("issue_option_ids"), label="issue_option_ids"
    )
    norm_passport_id_values, norm_passport_errors = (
        _manifest_binding_identifier_list(
            manifest.get("norm_passport_ids"), label="norm_passport_ids"
        )
    )
    errors.extend(issue_option_errors)
    errors.extend(norm_passport_errors)
    issue_option_ids = set(issue_option_id_values)
    norm_passport_ids = set(norm_passport_id_values)
    for ordinal, raw in enumerate(entries, start=1):
        if not isinstance(raw, Mapping):
            continue
        is_remedy_section = raw.get("section_code") == "requested_remedy"
        is_remedy_role = raw.get("role") == "requested_remedy"
        if not is_remedy_section and not is_remedy_role:
            continue
        requested_remedy_count += 1
        entry_errors: list[str] = []
        if is_remedy_section and not is_remedy_role:
            entry_errors.append(
                "relief_binding_manifest_role_mismatch:"
                f"{raw.get('sentence_id') or ordinal}"
            )
        if is_remedy_role and not is_remedy_section:
            entry_errors.append(
                "relief_binding_manifest_section_mismatch:"
                f"{raw.get('sentence_id') or ordinal}"
            )
        raw_sentence_id = entry_sentence_ids.get(ordinal)
        if raw_sentence_id is None:
            sentence_id = f"<invalid:{ordinal}>"
        else:
            sentence_id = raw_sentence_id
        expected_sentence_ids.add(sentence_id)
        if raw.get("relief_binding_status") != "bound":
            entry_errors.append(f"relief_binding_status_not_bound:{sentence_id}")
        application_record_ids, application_errors = (
            _manifest_binding_identifier_list(
                raw.get("application_record_ids"),
                label=f"{sentence_id}:application_record_ids",
            )
        )
        evidence_ids, evidence_errors = _manifest_binding_identifier_list(
            raw.get("evidence_ids"), label=f"{sentence_id}:evidence_ids"
        )
        entry_errors.extend(application_errors)
        entry_errors.extend(evidence_errors)
        required_values: dict[str, str] = {"sentence_id": sentence_id}
        for key, source_key in (
            ("sentence_text", "text"),
            ("claim_id", "claim_id"),
            ("issue_option_id", "issue_option_id"),
            ("norm_passport_id", "norm_passport_id"),
        ):
            value, value_errors = _manifest_binding_string(
                raw.get(source_key), label=f"{sentence_id}:{source_key}"
            )
            required_values[key] = value
            entry_errors.extend(value_errors)
        if not application_record_ids or not evidence_ids:
            entry_errors.append(
                f"relief_binding_projection_incomplete:{sentence_id}:"
                "application_or_evidence_ids"
            )
        if entry_errors:
            errors.extend(entry_errors)
            continue
        missing = [key for key, value in required_values.items() if not value]
        if missing:
            errors.append(
                f"relief_binding_projection_incomplete:{sentence_id or '<missing>'}:"
                + ",".join(missing)
            )
            continue
        request = build_relief_binding_request(
            matter_id=str(manifest.get("matter_id") or ""),
            draft_id=str(manifest.get("draft_id") or ""),
            sentence_id=required_values["sentence_id"],
            sentence_text=required_values["sentence_text"],
            claim_id=required_values["claim_id"],
            issue_option_id=required_values["issue_option_id"],
            norm_passport_id=required_values["norm_passport_id"],
            application_record_ids=application_record_ids,
            evidence_ids=evidence_ids,
        )
        if raw.get("relief_binding_sha256") != request["relief_binding_sha256"]:
            errors.append(f"relief_binding_projection_sha_mismatch:{sentence_id}")
        if required_values["issue_option_id"] not in issue_option_ids:
            errors.append(f"relief_binding_issue_projection_mismatch:{sentence_id}")
        if required_values["norm_passport_id"] not in norm_passport_ids:
            errors.append(f"relief_binding_passport_projection_mismatch:{sentence_id}")
        requests.append(request)
        receipt = receipt_by_sentence.get(sentence_id)
        if receipt is None:
            errors.append(f"relief_binding_receipt_missing:{sentence_id}")
            continue
        if receipt.get("relief_binding_sha256") != request["relief_binding_sha256"]:
            errors.append(f"relief_binding_receipt_sha_mismatch:{sentence_id}")
        pairs.append((request, receipt))

    if requested_remedy_count == 0:
        errors.append("relief_binding_requested_remedy_missing")
    extra_receipts = sorted(set(receipt_by_sentence) - expected_sentence_ids)
    errors.extend(f"relief_binding_receipt_orphan:{item}" for item in extra_receipts)
    stored_index = manifest.get("relief_binding_index_receipt")
    if pairs and not isinstance(stored_index, Mapping):
        errors.append("relief_binding_index_receipt_missing")
    if isinstance(stored_index, Mapping):
        for _request, receipt in pairs:
            if receipt.get("binding_index_receipt") != stored_index:
                errors.append(
                    "relief_binding_index_receipt_projection_mismatch:"
                    f"{receipt.get('sentence_id')}"
                )
    return pairs, requests, errors


def _manifest_relief_binding_projection_errors(
    manifest: Mapping[str, Any],
) -> list[str]:
    _pairs, _requests, errors = _manifest_relief_binding_requests(manifest)
    return errors


def _manifest_relief_binding_authority_errors(
    manifest: Mapping[str, Any],
    authority: ReliefEvidenceBindingAuthority | Any | None,
) -> list[str]:
    pairs, requests, errors = _manifest_relief_binding_requests(manifest)
    current_receipts: list[tuple[str, Mapping[str, Any], dict[str, Any]]] = []
    for request, stored_receipt in pairs:
        binding_errors, current_receipt = resolve_relief_evidence_binding(
            request, authority
        )
        sentence_id = str(request.get("sentence_id") or "")
        errors.extend(
            f"relief_binding:{sentence_id}:{error}" for error in binding_errors
        )
        if current_receipt is not None:
            current_receipts.append((sentence_id, stored_receipt, current_receipt))

    matter_id, matter_id_errors = _manifest_binding_string(
        manifest.get("matter_id"), label="matter_id"
    )
    draft_id, draft_id_errors = _manifest_binding_string(
        manifest.get("draft_id"), label="draft_id"
    )
    errors.extend(matter_id_errors)
    errors.extend(draft_id_errors)
    index_errors, current_index_receipt = resolve_relief_evidence_binding_index(
        matter_id=matter_id,
        draft_id=draft_id,
        binding_requests=requests,
        authority=authority,
    )
    errors.extend(index_errors)
    stored_index_receipt = manifest.get("relief_binding_index_receipt")
    if (
        current_index_receipt is not None
        and stored_index_receipt != current_index_receipt
    ):
        errors.append("relief_binding_index_receipt_stale")
    for sentence_id, stored_receipt, current_receipt in current_receipts:
        if current_index_receipt is not None:
            current_receipt = {
                **current_receipt,
                "binding_index_receipt": dict(current_index_receipt),
            }
        if dict(stored_receipt) != current_receipt:
            errors.append(f"relief_binding_receipt_stale:{sentence_id}")
    return errors


def _manifest_holding_identifier_list(
    value: Any,
    *,
    label: str,
    allow_empty: bool = False,
) -> tuple[list[str], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"holding_binding_identifier_list_invalid:{label}"]
    identifiers: list[str] = []
    errors: list[str] = []
    for ordinal, raw in enumerate(value, start=1):
        if (
            not isinstance(raw, str)
            or not raw
            or raw != " ".join(raw.split())
            or not _SOURCE_EVIDENCE_ID_RE.fullmatch(raw)
        ):
            errors.append(
                f"holding_binding_identifier_invalid:{label}:{ordinal}"
            )
            continue
        identifiers.append(raw)
    if not identifiers and not allow_empty:
        errors.append(f"holding_binding_identifier_list_empty:{label}")
    if len(identifiers) != len(set(identifiers)):
        errors.append(f"holding_binding_identifier_duplicate:{label}")
    if identifiers != sorted(identifiers):
        errors.append(f"holding_binding_identifier_order_invalid:{label}")
    return identifiers, errors


def _manifest_holding_string(
    value: Any,
    *,
    label: str,
) -> tuple[str, list[str]]:
    if (
        not isinstance(value, str)
        or not value
        or value != " ".join(value.split())
    ):
        return "", [f"holding_binding_string_invalid:{label}"]
    return value, []


def _holding_index_binding_from_request(
    request: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "sentence_id": str(request.get("sentence_id") or ""),
        "section_code": str(request.get("section_code") or ""),
        "role": "legal_holding",
        "holding_binding_sha256": str(
            request.get("holding_binding_sha256") or ""
        ),
    }


def _manifest_holding_binding_requests(
    manifest: Mapping[str, Any],
) -> tuple[
    list[tuple[dict[str, Any], Mapping[str, Any]]],
    list[dict[str, Any]],
    list[dict[str, str]],
    list[str],
]:
    raw_entries = manifest.get("sentence_evidence_map")
    entries: list[Any] = []
    errors: list[str] = []
    if isinstance(raw_entries, Sequence) and not isinstance(
        raw_entries, (str, bytes)
    ):
        entries = list(raw_entries)
    else:
        errors.append("holding_binding_sentence_evidence_map_invalid")

    raw_receipts = manifest.get("holding_binding_receipts")
    receipts: list[Any] = []
    if isinstance(raw_receipts, Sequence) and not isinstance(
        raw_receipts, (str, bytes)
    ):
        receipts = list(raw_receipts)
    else:
        errors.append("holding_binding_receipts_invalid")

    receipt_by_sentence: dict[str, Mapping[str, Any]] = {}
    for ordinal, raw in enumerate(receipts, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"holding_binding_receipt_invalid:{ordinal}")
            continue
        sentence_id = raw.get("sentence_id")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            sentence_id
        ):
            errors.append(
                f"holding_binding_receipt_sentence_id_invalid:{ordinal}"
            )
            continue
        if sentence_id in receipt_by_sentence:
            errors.append(f"holding_binding_receipt_duplicate:{sentence_id}")
            continue
        receipt_by_sentence[sentence_id] = raw

    entry_sentence_ids: dict[int, str] = {}
    seen_sentence_ids: set[str] = set()
    for ordinal, raw in enumerate(entries, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"holding_binding_manifest_entry_invalid:{ordinal}")
            continue
        sentence_id = raw.get("sentence_id")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            sentence_id
        ):
            errors.append(f"holding_binding_sentence_id_invalid:{ordinal}")
            continue
        entry_sentence_ids[ordinal] = sentence_id
        if sentence_id in seen_sentence_ids:
            errors.append(f"holding_binding_sentence_duplicate:{sentence_id}")
        seen_sentence_ids.add(sentence_id)

    matter_id, matter_errors = _manifest_holding_string(
        manifest.get("matter_id"), label="matter_id"
    )
    draft_id, draft_errors = _manifest_holding_string(
        manifest.get("draft_id"), label="draft_id"
    )
    errors.extend(matter_errors)
    errors.extend(draft_errors)

    pairs: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    requests: list[dict[str, Any]] = []
    expected_receipt_sentence_ids: set[str] = set()
    for ordinal, raw in enumerate(entries, start=1):
        if not isinstance(raw, Mapping) or raw.get("role") != "legal_holding":
            continue
        sentence_id = entry_sentence_ids.get(ordinal, f"<invalid:{ordinal}>")
        expected_receipt_sentence_ids.add(sentence_id)
        entry_errors: list[str] = []
        if raw.get("holding_binding_status") != "bound":
            entry_errors.append(
                f"holding_binding_status_not_bound:{sentence_id}"
            )
        evidence_ids, evidence_errors = _manifest_holding_identifier_list(
            raw.get("evidence_ids"), label=f"{sentence_id}:evidence_ids"
        )
        entry_errors.extend(evidence_errors)
        required_values: dict[str, str] = {"sentence_id": sentence_id}
        for key, source_key in (
            ("section_code", "section_code"),
            ("sentence_text", "text"),
            ("claim_id", "claim_id"),
            ("maximum_supported_inference", "maximum_supported_inference"),
        ):
            value, value_errors = _manifest_holding_string(
                raw.get(source_key), label=f"{sentence_id}:{source_key}"
            )
            required_values[key] = value
            entry_errors.extend(value_errors)
        if entry_errors or not matter_id or not draft_id:
            errors.extend(entry_errors)
            continue

        request = build_holding_binding_request(
            matter_id=matter_id,
            draft_id=draft_id,
            sentence_id=required_values["sentence_id"],
            section_code=required_values["section_code"],
            sentence_text=required_values["sentence_text"],
            claim_id=required_values["claim_id"],
            evidence_ids=evidence_ids,
            maximum_supported_inference=required_values[
                "maximum_supported_inference"
            ],
        )
        if raw.get("holding_binding_sha256") != request["holding_binding_sha256"]:
            errors.append(
                f"holding_binding_projection_sha_mismatch:{sentence_id}"
            )
        requests.append(request)

        receipt = receipt_by_sentence.get(sentence_id)
        if receipt is None:
            errors.append(f"holding_binding_receipt_missing:{sentence_id}")
            continue
        expected_receipt_fields = {
            "schema_version",
            "sentence_id",
            "section_code",
            "holding_binding_sha256",
            "claim_id",
            "evidence_ids",
            "maximum_supported_inference",
            "source_evidence_receipts",
            "current_authority_results",
            "claim_scope_receipts",
            "scope_gate_receipt",
        }
        if set(receipt) != expected_receipt_fields:
            errors.append(
                f"holding_binding_receipt_fields_mismatch:{sentence_id}"
            )
        expected_core = {
            "schema_version": "1.0.0",
            "sentence_id": sentence_id,
            "section_code": request["section_code"],
            "holding_binding_sha256": request["holding_binding_sha256"],
            "claim_id": request["claim_id"],
            "evidence_ids": request["evidence_ids"],
            "maximum_supported_inference": request[
                "maximum_supported_inference"
            ],
        }
        for field, expected_value in expected_core.items():
            if receipt.get(field) != expected_value:
                errors.append(
                    f"holding_binding_receipt_projection_mismatch:"
                    f"{sentence_id}:{field}"
                )
        for field in (
            "source_evidence_receipts",
            "current_authority_results",
            "claim_scope_receipts",
        ):
            projection = receipt.get(field)
            if not isinstance(projection, Mapping):
                errors.append(
                    f"holding_binding_receipt_projection_invalid:"
                    f"{sentence_id}:{field}"
                )
            elif set(projection) != set(evidence_ids):
                errors.append(
                    f"holding_binding_receipt_evidence_set_mismatch:"
                    f"{sentence_id}:{field}"
                )
        gate = receipt.get("scope_gate_receipt")
        if not isinstance(gate, Mapping):
            errors.append(
                f"holding_binding_scope_gate_receipt_invalid:{sentence_id}"
            )
        else:
            for field, expected_value in expected_core.items():
                if field == "schema_version":
                    continue
                if gate.get(field) != expected_value:
                    errors.append(
                        f"holding_binding_scope_gate_projection_mismatch:"
                        f"{sentence_id}:{field}"
                    )
        if "binding_index_receipt" in receipt:
            errors.append(
                f"holding_binding_index_nested_in_receipt:{sentence_id}"
            )
        pairs.append((request, receipt))

    extra_receipts = sorted(
        set(receipt_by_sentence) - expected_receipt_sentence_ids
    )
    errors.extend(
        f"holding_binding_receipt_orphan:{sentence_id}"
        for sentence_id in extra_receipts
    )

    expected_bindings = sorted(
        (_holding_index_binding_from_request(request) for request in requests),
        key=lambda item: item["sentence_id"],
    )
    stored_index = manifest.get("holding_binding_index_receipt")
    ready_status = manifest.get("status") in {
        "ready_for_expert_review",
        "ready_for_human_signing_filing",
    }
    index_required = ready_status or bool(requests) or bool(receipts)
    if stored_index is None:
        if index_required:
            errors.append("holding_binding_index_receipt_missing")
    elif not isinstance(stored_index, Mapping):
        errors.append("holding_binding_index_receipt_invalid")
    else:
        expected_index_fields = {
            "schema_version",
            "matter_id",
            "draft_id",
            "bindings",
            "binding_index_sha256",
            "authority_revision_id",
            "checked_at",
        }
        if set(stored_index) != expected_index_fields:
            errors.append("holding_binding_index_receipt_fields_mismatch")
        if stored_index.get("schema_version") != "1.0.0":
            errors.append("holding_binding_index_receipt_schema_invalid")
        if stored_index.get("matter_id") != matter_id:
            errors.append("holding_binding_index_receipt_matter_mismatch")
        if stored_index.get("draft_id") != draft_id:
            errors.append("holding_binding_index_receipt_draft_mismatch")
        raw_bindings = stored_index.get("bindings")
        stored_bindings = (
            list(raw_bindings)
            if isinstance(raw_bindings, Sequence)
            and not isinstance(raw_bindings, (str, bytes))
            else []
        )
        if not isinstance(raw_bindings, Sequence) or isinstance(
            raw_bindings, (str, bytes)
        ):
            errors.append("holding_binding_index_bindings_invalid")
        if stored_bindings != expected_bindings:
            errors.append("holding_binding_index_projection_mismatch")
        index_basis = {
            "schema_version": "1.0.0",
            "matter_id": matter_id,
            "draft_id": draft_id,
            "bindings": expected_bindings,
        }
        expected_index_sha = sha256(
            canonical_json_bytes(index_basis)
        ).hexdigest()
        if stored_index.get("binding_index_sha256") != expected_index_sha:
            errors.append("holding_binding_index_sha256_mismatch")

    return pairs, requests, expected_bindings, errors


def _manifest_holding_binding_projection_errors(
    manifest: Mapping[str, Any],
) -> list[str]:
    _pairs, _requests, _expected_bindings, errors = (
        _manifest_holding_binding_requests(manifest)
    )
    return errors


def _manifest_holding_binding_authority_errors(
    manifest: Mapping[str, Any],
    authority: HoldingEvidenceBindingAuthority | Any | None,
) -> list[str]:
    pairs, requests, expected_bindings, errors = (
        _manifest_holding_binding_requests(manifest)
    )
    for request, stored_receipt in pairs:
        binding_errors, current_receipt = resolve_holding_evidence_binding(
            request, authority
        )
        sentence_id = str(request.get("sentence_id") or "")
        errors.extend(
            f"holding_binding:{sentence_id}:{error}"
            for error in binding_errors
        )
        if current_receipt is not None and dict(stored_receipt) != current_receipt:
            errors.append(f"holding_binding_receipt_stale:{sentence_id}")

    stored_index = manifest.get("holding_binding_index_receipt")
    should_resolve_index = (
        manifest.get("status")
        in {"ready_for_expert_review", "ready_for_human_signing_filing"}
        or bool(requests)
        or isinstance(stored_index, Mapping)
    )
    if should_resolve_index:
        matter_id, matter_errors = _manifest_holding_string(
            manifest.get("matter_id"), label="matter_id"
        )
        draft_id, draft_errors = _manifest_holding_string(
            manifest.get("draft_id"), label="draft_id"
        )
        errors.extend(matter_errors)
        errors.extend(draft_errors)
        index_errors, current_index = resolve_holding_evidence_binding_index(
            matter_id=matter_id,
            draft_id=draft_id,
            expected_bindings=expected_bindings,
            authority=authority,
        )
        errors.extend(index_errors)
        if current_index is not None and stored_index != current_index:
            errors.append("holding_binding_index_receipt_stale")
    return errors


def _manifest_practice_identifier_list(
    value: Any,
    *,
    label: str,
) -> tuple[list[str], list[str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [], [f"practice_binding_identifier_list_invalid:{label}"]
    identifiers: list[str] = []
    errors: list[str] = []
    for ordinal, raw in enumerate(value, start=1):
        if (
            not isinstance(raw, str)
            or not _SHA256_RE.fullmatch(raw)
        ):
            errors.append(
                f"practice_binding_identifier_invalid:{label}:{ordinal}"
            )
            continue
        identifiers.append(raw)
    if not identifiers:
        errors.append(f"practice_binding_identifier_list_empty:{label}")
    if len(identifiers) != len(set(identifiers)):
        errors.append(f"practice_binding_identifier_duplicate:{label}")
    if identifiers != sorted(identifiers):
        errors.append(f"practice_binding_identifier_order_invalid:{label}")
    return identifiers, errors


def _manifest_practice_string(
    value: Any,
    *,
    label: str,
) -> tuple[str, list[str]]:
    if (
        not isinstance(value, str)
        or not value
        or value != " ".join(value.split())
    ):
        return "", [f"practice_binding_string_invalid:{label}"]
    return value, []


def _manifest_practice_text(
    value: Any,
    *,
    label: str,
) -> tuple[str, list[str]]:
    """Validate exact prose without collapsing meaningful internal whitespace."""

    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
    ):
        return "", [f"practice_binding_string_invalid:{label}"]
    return value, []


def _practice_index_binding_from_request(
    request: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "sentence_id": str(request.get("sentence_id") or ""),
        "section_code": str(request.get("section_code") or ""),
        "role": "practice_claim",
        "claim_id": str(request.get("claim_id") or ""),
        "practice_claim_id": str(request.get("practice_claim_id") or ""),
        "issue_option_id": str(request.get("issue_option_id") or ""),
        "practice_binding_sha256": str(
            request.get("practice_binding_sha256") or ""
        ),
    }


def _manifest_practice_binding_requests(
    manifest: Mapping[str, Any],
) -> tuple[
    list[tuple[dict[str, Any], Mapping[str, Any]]],
    list[dict[str, Any]],
    list[dict[str, str]],
    list[str],
]:
    raw_entries = manifest.get("sentence_evidence_map")
    entries: list[Any] = []
    errors: list[str] = []
    if isinstance(raw_entries, Sequence) and not isinstance(
        raw_entries, (str, bytes)
    ):
        entries = list(raw_entries)
    else:
        errors.append("practice_binding_sentence_evidence_map_invalid")

    raw_receipts = manifest.get("practice_binding_receipts")
    receipts: list[Any] = []
    if isinstance(raw_receipts, Sequence) and not isinstance(
        raw_receipts, (str, bytes)
    ):
        receipts = list(raw_receipts)
    else:
        errors.append("practice_binding_receipts_invalid")

    receipt_by_sentence: dict[str, Mapping[str, Any]] = {}
    for ordinal, raw in enumerate(receipts, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"practice_binding_receipt_invalid:{ordinal}")
            continue
        sentence_id = raw.get("sentence_id")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            sentence_id
        ):
            errors.append(
                f"practice_binding_receipt_sentence_id_invalid:{ordinal}"
            )
            continue
        if sentence_id in receipt_by_sentence:
            errors.append(f"practice_binding_receipt_duplicate:{sentence_id}")
            continue
        receipt_by_sentence[sentence_id] = raw

    entry_sentence_ids: dict[int, str] = {}
    seen_sentence_ids: set[str] = set()
    for ordinal, raw in enumerate(entries, start=1):
        if not isinstance(raw, Mapping):
            errors.append(f"practice_binding_manifest_entry_invalid:{ordinal}")
            continue
        sentence_id = raw.get("sentence_id")
        if not isinstance(sentence_id, str) or not _SENTENCE_ID_RE.fullmatch(
            sentence_id
        ):
            errors.append(f"practice_binding_sentence_id_invalid:{ordinal}")
            continue
        entry_sentence_ids[ordinal] = sentence_id
        if sentence_id in seen_sentence_ids:
            errors.append(f"practice_binding_sentence_duplicate:{sentence_id}")
        seen_sentence_ids.add(sentence_id)

    matter_id, matter_errors = _manifest_practice_string(
        manifest.get("matter_id"), label="matter_id"
    )
    draft_id, draft_errors = _manifest_practice_string(
        manifest.get("draft_id"), label="draft_id"
    )
    errors.extend(matter_errors)
    errors.extend(draft_errors)
    issue_option_values, issue_option_errors = (
        _manifest_binding_identifier_list(
            manifest.get("issue_option_ids"), label="issue_option_ids"
        )
    )
    errors.extend(
        error.replace("relief_binding_", "practice_binding_", 1)
        for error in issue_option_errors
    )
    issue_option_ids = set(issue_option_values)

    pairs: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    requests: list[dict[str, Any]] = []
    expected_receipt_sentence_ids: set[str] = set()
    for ordinal, raw in enumerate(entries, start=1):
        if not isinstance(raw, Mapping) or raw.get("role") != "practice_claim":
            continue
        sentence_id = entry_sentence_ids.get(ordinal, f"<invalid:{ordinal}>")
        expected_receipt_sentence_ids.add(sentence_id)
        entry_errors: list[str] = []
        if raw.get("practice_binding_status") != "bound":
            entry_errors.append(
                f"practice_binding_status_not_bound:{sentence_id}"
            )
        evidence_ids, evidence_errors = _manifest_practice_identifier_list(
            raw.get("evidence_ids"), label=f"{sentence_id}:evidence_ids"
        )
        entry_errors.extend(evidence_errors)
        required_values: dict[str, str] = {"sentence_id": sentence_id}
        for key, source_key in (
            ("section_code", "section_code"),
            ("sentence_text", "text"),
            ("claim_id", "claim_id"),
            ("practice_claim_id", "practice_claim_id"),
            ("issue_option_id", "issue_option_id"),
            ("maximum_supported_inference", "maximum_supported_inference"),
        ):
            value, value_errors = (
                _manifest_practice_text(
                    raw.get(source_key), label=f"{sentence_id}:{source_key}"
                )
                if source_key == "text"
                else _manifest_practice_string(
                    raw.get(source_key), label=f"{sentence_id}:{source_key}"
                )
            )
            required_values[key] = value
            entry_errors.extend(value_errors)
        if entry_errors or not matter_id or not draft_id:
            errors.extend(entry_errors)
            continue

        try:
            request = build_practice_claim_binding_request(
                matter_id=matter_id,
                draft_id=draft_id,
                sentence_id=required_values["sentence_id"],
                section_code=required_values["section_code"],
                sentence_text=required_values["sentence_text"],
                claim_id=required_values["claim_id"],
                practice_claim_id=required_values["practice_claim_id"],
                issue_option_id=required_values["issue_option_id"],
                evidence_ids=evidence_ids,
                maximum_supported_inference=required_values[
                    "maximum_supported_inference"
                ],
            )
        except (TypeError, ValueError) as exc:
            errors.append(
                f"practice_binding_request_invalid:{sentence_id}:{exc}"
            )
            continue
        if raw.get("practice_binding_sha256") != request["practice_binding_sha256"]:
            errors.append(
                f"practice_binding_projection_sha_mismatch:{sentence_id}"
            )
        if required_values["issue_option_id"] not in issue_option_ids:
            errors.append(
                f"practice_binding_issue_projection_mismatch:{sentence_id}"
            )
        requests.append(request)

        receipt = receipt_by_sentence.get(sentence_id)
        if receipt is None:
            errors.append(f"practice_binding_receipt_missing:{sentence_id}")
            continue
        expected_core = {
            "schema_version": "1.0.0",
            "sentence_id": sentence_id,
            "section_code": request["section_code"],
            "practice_binding_sha256": request["practice_binding_sha256"],
            "claim_id": request["claim_id"],
            "practice_claim_id": request["practice_claim_id"],
            "issue_option_id": request["issue_option_id"],
            "evidence_ids": request["evidence_ids"],
            "maximum_supported_inference": request[
                "maximum_supported_inference"
            ],
        }
        if set(receipt) != _PRACTICE_BINDING_RECEIPT_FIELDS:
            errors.append(
                f"practice_binding_receipt_fields_mismatch:{sentence_id}"
            )
        for field, expected_value in expected_core.items():
            if receipt.get(field) != expected_value:
                errors.append(
                    f"practice_binding_receipt_projection_mismatch:"
                    f"{sentence_id}:{field}"
                )
        for field in (
            "matter_binding",
            "ready_binding",
            "prefiling_refresh_receipt",
            "issue_approval_requests",
            "trusted_approval_ids",
        ):
            if not isinstance(receipt.get(field), Mapping):
                errors.append(
                    f"practice_binding_receipt_projection_invalid:"
                    f"{sentence_id}:{field}"
                )
        finding_receipts = receipt.get("finding_receipts")
        if not isinstance(finding_receipts, Sequence) or isinstance(
            finding_receipts, (str, bytes)
        ):
            errors.append(
                f"practice_binding_receipt_projection_invalid:"
                f"{sentence_id}:finding_receipts"
            )
        elif not all(isinstance(item, Mapping) for item in finding_receipts):
            errors.append(
                f"practice_binding_receipt_projection_invalid:"
                f"{sentence_id}:finding_receipts"
            )
        elif [item.get("finding_id") for item in finding_receipts] != evidence_ids:
            errors.append(
                f"practice_binding_receipt_finding_set_mismatch:{sentence_id}"
            )
        if "binding_index_receipt" in receipt:
            errors.append(
                f"practice_binding_index_nested_in_receipt:{sentence_id}"
            )
        pairs.append((request, receipt))

    extra_receipts = sorted(
        set(receipt_by_sentence) - expected_receipt_sentence_ids
    )
    errors.extend(
        f"practice_binding_receipt_orphan:{sentence_id}"
        for sentence_id in extra_receipts
    )

    expected_bindings = sorted(
        (_practice_index_binding_from_request(request) for request in requests),
        key=lambda item: item["sentence_id"],
    )
    stored_index = manifest.get("practice_binding_index_receipt")
    ready_status = manifest.get("status") in {
        "ready_for_expert_review",
        "ready_for_human_signing_filing",
    }
    index_required = ready_status or bool(requests) or bool(receipts)
    if stored_index is None:
        if index_required:
            errors.append("practice_binding_index_receipt_missing")
    elif not isinstance(stored_index, Mapping):
        errors.append("practice_binding_index_receipt_invalid")
    else:
        expected_index_fields = {
            "schema_version",
            "matter_id",
            "draft_id",
            "bindings",
            "binding_index_sha256",
            "authority_revision_id",
            "checked_at",
        }
        if set(stored_index) != expected_index_fields:
            errors.append("practice_binding_index_receipt_fields_mismatch")
        if stored_index.get("schema_version") != "1.0.0":
            errors.append("practice_binding_index_receipt_schema_invalid")
        if stored_index.get("matter_id") != matter_id:
            errors.append("practice_binding_index_receipt_matter_mismatch")
        if stored_index.get("draft_id") != draft_id:
            errors.append("practice_binding_index_receipt_draft_mismatch")
        raw_bindings = stored_index.get("bindings")
        stored_bindings = (
            list(raw_bindings)
            if isinstance(raw_bindings, Sequence)
            and not isinstance(raw_bindings, (str, bytes))
            else []
        )
        if not isinstance(raw_bindings, Sequence) or isinstance(
            raw_bindings, (str, bytes)
        ):
            errors.append("practice_binding_index_bindings_invalid")
        if stored_bindings != expected_bindings:
            errors.append("practice_binding_index_projection_mismatch")
        index_basis = {
            "schema_version": "1.0.0",
            "matter_id": matter_id,
            "draft_id": draft_id,
            "bindings": expected_bindings,
        }
        expected_index_sha = sha256(
            canonical_json_bytes(index_basis)
        ).hexdigest()
        if stored_index.get("binding_index_sha256") != expected_index_sha:
            errors.append("practice_binding_index_sha256_mismatch")
        if pairs:
            receipt_revisions = [
                receipt.get("authority_revision_id") for _request, receipt in pairs
            ]
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
                for _request, receipt in pairs
                if isinstance(receipt.get("matter_binding"), Mapping)
            ]
            shared_matter_snapshot = (
                matter_snapshot_values[0] if matter_snapshot_values else ()
            )
            one_matter_snapshot = bool(matter_snapshot_values) and all(
                snapshot == shared_matter_snapshot
                for snapshot in matter_snapshot_values[1:]
            )
            index_revision = stored_index.get("authority_revision_id")
            if (
                not receipt_revisions
                or any(revision != index_revision for revision in receipt_revisions)
                or len(matter_snapshot_values) != len(pairs)
                or not one_matter_snapshot
                or shared_matter_snapshot[:2] != (matter_id, draft_id)
                or stored_index.get("matter_id") != matter_id
                or stored_index.get("draft_id") != draft_id
            ):
                errors.append("practice_binding_authority_snapshot_mismatch")

    return pairs, requests, expected_bindings, errors


def _manifest_practice_binding_projection_errors(
    manifest: Mapping[str, Any],
) -> list[str]:
    _pairs, _requests, _expected_bindings, errors = (
        _manifest_practice_binding_requests(manifest)
    )
    return errors


def _manifest_practice_binding_authority_errors(
    manifest: Mapping[str, Any],
    authority: PracticeClaimEvidenceBindingAuthority | Any | None,
) -> list[str]:
    pairs, requests, expected_bindings, errors = (
        _manifest_practice_binding_requests(manifest)
    )
    for request, stored_receipt in pairs:
        binding_errors, current_receipt = (
            resolve_practice_claim_evidence_binding(request, authority)
        )
        sentence_id = str(request.get("sentence_id") or "")
        errors.extend(
            f"practice_binding:{sentence_id}:{error}"
            for error in binding_errors
        )
        if current_receipt is not None and dict(stored_receipt) != current_receipt:
            errors.append(f"practice_binding_receipt_stale:{sentence_id}")

    stored_index = manifest.get("practice_binding_index_receipt")
    should_resolve_index = (
        manifest.get("status")
        in {"ready_for_expert_review", "ready_for_human_signing_filing"}
        or bool(requests)
        or isinstance(stored_index, Mapping)
    )
    if should_resolve_index:
        matter_id, matter_errors = _manifest_practice_string(
            manifest.get("matter_id"), label="matter_id"
        )
        draft_id, draft_errors = _manifest_practice_string(
            manifest.get("draft_id"), label="draft_id"
        )
        errors.extend(matter_errors)
        errors.extend(draft_errors)
        index_errors, current_index = (
            resolve_practice_claim_evidence_binding_index(
                matter_id=matter_id,
                draft_id=draft_id,
                expected_bindings=expected_bindings,
                authority=authority,
            )
        )
        errors.extend(index_errors)
        if current_index is not None and stored_index != current_index:
            errors.append("practice_binding_index_receipt_stale")
    return errors


def approve_release_pack(
    manifest_path: str | Path,
    *,
    approval_ledger: TrustedApprovalLedger | None = None,
    approval_id: str | None = None,
    approval_as_of: str | None = None,
    reviewer: str | None = None,
    reviewed_at: str | None = None,
    relief_binding_authority: ReliefEvidenceBindingAuthority | Any | None = None,
    holding_binding_authority: HoldingEvidenceBindingAuthority | Any | None = None,
    practice_binding_authority: (
        PracticeClaimEvidenceBindingAuthority | Any | None
    ) = None,
) -> dict[str, Any]:
    """Именно и явно одобрить неизменившийся реальный пакет после визуальной проверки."""

    del approval_as_of
    path = Path(manifest_path).resolve()
    loaded_manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded_manifest, Mapping):
        raise ValueError("Release manifest должен быть JSON-объектом")
    manifest = dict(loaded_manifest)
    if manifest.get("status") == "blocked" or manifest.get("blockers"):
        raise ValueError("Заблокированный пакет нельзя одобрить")
    if manifest.get("missing_approvals"):
        raise ValueError("Не завершены обязательные юридические одобрения")
    render_qa = manifest.get("render_qa")
    if not isinstance(render_qa, Mapping) or render_qa.get("passed") is not True:
        raise ValueError("Визуальная и семантическая проверка файлов не пройдена")
    if approval_ledger is None or not str(approval_id or "").strip():
        raise ValueError("Для выпуска нужен заранее созданный trusted approval_id")
    integrity_errors = verify_release_manifest(
        manifest,
        approval_ledger=approval_ledger,
        relief_binding_authority=relief_binding_authority,
        holding_binding_authority=holding_binding_authority,
        practice_binding_authority=practice_binding_authority,
    )
    if integrity_errors:
        raise ValueError("Нарушена целостность пакета: " + ", ".join(integrity_errors))
    observed_basis = release_basis_sha256(manifest)
    if manifest.get("release_basis_sha256") != observed_basis:
        raise ValueError("Основание выпуска изменилось; пакет нужно пересобрать и проверить заново")
    approval_request = release_approval_request(manifest)
    validation = approval_ledger.validate_approval(
        str(approval_id),
        **approval_request,
    )
    if validation.get("valid") is not True:
        raise ValueError(
            "Trusted approval выпуска недействителен: "
            + str(validation.get("reason_code") or "approval_invalid")
        )
    approval_record = validation["approval"]
    approved_manifest = dict(manifest)
    approved_manifest["release_approval"] = {
        "status": "approved",
        "approval_id": approval_record["approval_id"],
        "approval_request": approval_request,
        "actor_id": approval_record["actor_id"],
        "actor_display_name": approval_record["actor_display_name"],
        "reviewer": approval_record["actor_display_name"],
        "approved_at": approval_record["approved_at"],
        "reviewed_at": approval_record["approved_at"],
        "expires_at": approval_record["expires_at"],
        "validated_at": validation["checked_at"],
        "validation_state": "valid",
        "basis_sha256": observed_basis,
        "actor_provenance": dict(approval_record["actor_provenance"]),
        "raw_reviewer_diagnostic": str(reviewer or "").strip() or None,
        "raw_reviewed_at_diagnostic": reviewed_at,
    }
    approved_manifest["status"] = "ready_for_human_signing_filing"
    approved_errors = _verify_release_manifest(
        approved_manifest,
        approval_ledger=approval_ledger,
        verify_manifest_file=False,
        relief_binding_authority=relief_binding_authority,
        holding_binding_authority=holding_binding_authority,
        practice_binding_authority=practice_binding_authority,
    )
    if approved_errors:
        raise ValueError(
            "Одобренный пакет не прошёл повторную проверку: "
            + ", ".join(approved_errors)
        )
    _write_json(path, approved_manifest)
    persisted_manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(persisted_manifest, Mapping):
        _write_json(path, manifest)
        raise ValueError("Записанный release manifest повреждён")
    persisted_errors = verify_release_manifest(
        persisted_manifest,
        approval_ledger=approval_ledger,
        relief_binding_authority=relief_binding_authority,
        holding_binding_authority=holding_binding_authority,
        practice_binding_authority=practice_binding_authority,
    )
    if persisted_errors:
        _write_json(path, manifest)
        raise ValueError(
            "Записанный одобренный пакет не прошёл повторную проверку: "
            + ", ".join(persisted_errors)
        )
    result = dict(persisted_manifest)
    result["manifest_sha256"] = file_sha256(path)
    return result


def verify_release_manifest(
    manifest: Mapping[str, Any],
    *,
    approval_ledger: TrustedApprovalLedger | None = None,
    relief_binding_authority: ReliefEvidenceBindingAuthority | Any | None = None,
    holding_binding_authority: HoldingEvidenceBindingAuthority | Any | None = None,
    practice_binding_authority: (
        PracticeClaimEvidenceBindingAuthority | Any | None
    ) = None,
) -> list[str]:
    """Return integrity errors without mutating the filing pack."""

    return _verify_release_manifest(
        manifest,
        approval_ledger=approval_ledger,
        verify_manifest_file=True,
        relief_binding_authority=relief_binding_authority,
        holding_binding_authority=holding_binding_authority,
        practice_binding_authority=practice_binding_authority,
    )


def _verify_release_manifest(
    manifest: Mapping[str, Any],
    *,
    approval_ledger: TrustedApprovalLedger | None,
    verify_manifest_file: bool,
    relief_binding_authority: ReliefEvidenceBindingAuthority | Any | None,
    holding_binding_authority: HoldingEvidenceBindingAuthority | Any | None,
    practice_binding_authority: (
        PracticeClaimEvidenceBindingAuthority | Any | None
    ),
) -> list[str]:
    """Validate a manifest projection, optionally before its persistence."""

    errors = _manifest_contract_errors(
        manifest,
        approval_ledger=approval_ledger,
        verify_manifest_file=verify_manifest_file,
    )
    errors.extend(
        _manifest_relief_binding_authority_errors(
            manifest, relief_binding_authority
        )
    )
    errors.extend(
        _manifest_holding_binding_authority_errors(
            manifest, holding_binding_authority
        )
    )
    errors.extend(
        _manifest_practice_binding_authority_errors(
            manifest, practice_binding_authority
        )
    )
    observed_basis = release_basis_sha256(manifest)
    if manifest.get("release_basis_sha256") != observed_basis:
        errors.append("release_basis_mismatch")
    if manifest.get("status") == "ready_for_human_signing_filing":
        approval_value = manifest.get("release_approval")
        approval = approval_value if isinstance(approval_value, Mapping) else {}
        if (
            approval.get("status") != "approved"
            or not approval.get("approval_id")
            or approval.get("approval_request") != release_approval_request(manifest)
            or not approval.get("reviewer")
            or not approval.get("reviewed_at")
            or not approval.get("expires_at")
            or not approval.get("validated_at")
            or approval.get("validation_state") != "valid"
            or approval.get("basis_sha256") != observed_basis
            or (approval.get("actor_provenance") or {}).get("channel")
            != "authenticated_server"
        ):
            errors.append("release_approval_missing_or_stale")
        elif approval_ledger is None:
            errors.append("release_approval_host_verifier_required")
        else:
            expected_request = release_approval_request(manifest)
            validation = approval_ledger.validate_approval(
                str(approval.get("approval_id")),
                **expected_request,
            )
            if validation.get("valid") is not True:
                errors.append(
                    "release_approval_invalid:"
                    + str(validation.get("reason_code") or "approval_invalid")
                )
            else:
                approval_record = validation["approval"]
                if (
                    approval.get("actor_id") != approval_record.get("actor_id")
                    or approval.get("actor_display_name")
                    != approval_record.get("actor_display_name")
                    or approval.get("approved_at") != approval_record.get("approved_at")
                    or approval.get("expires_at") != approval_record.get("expires_at")
                    or approval.get("actor_provenance")
                    != approval_record.get("actor_provenance")
                ):
                    errors.append("release_approval_projection_mismatch")
    return sorted(set(errors))
