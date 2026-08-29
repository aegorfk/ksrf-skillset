"""Build a hash-addressed filing pack while keeping filing human-controlled."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any, Iterable, Mapping

from .composer import StructuredComplaint, require_release_support
from .renderer import (
    convert_docx_to_pdf,
    file_sha256,
    render_docx,
    validate_rendered_pair,
)


REQUIRED_APPROVALS = (
    "norm_application",
    "constitutional_issue",
    "adverse_material",
    "legal_review",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _copy_enclosures(
    enclosure_sources: Iterable[str | Path],
    destination: Path,
) -> list[dict[str, Any]]:
    destination.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for ordinal, source_value in enumerate(enclosure_sources, start=1):
        source = Path(source_value).resolve()
        if not source.is_file():
            items.append(
                {
                    "number": ordinal,
                    "source": str(source),
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
        items.append(
            {
                "number": ordinal,
                "source": str(source),
                "path": str(target),
                "status": "included",
                "sha256": file_sha256(target),
                "size": target.stat().st_size,
            }
        )
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
    return {
        "schema_version": manifest.get("schema_version"),
        "matter_id": manifest.get("matter_id"),
        "draft_id": manifest.get("draft_id"),
        "source_versions": list(manifest.get("source_versions", ())),
        "norm_passport_ids": list(manifest.get("norm_passport_ids", ())),
        "issue_option_id": manifest.get("issue_option_id"),
        "approvals": dict(manifest.get("approvals", {})),
        "formal_check": dict(manifest.get("formal_check", {})),
        "sentence_evidence_map": list(manifest.get("sentence_evidence_map", ())),
        "artifacts": [
            {
                key: item.get(key)
                for key in (
                    "kind",
                    "sha256",
                    "size",
                    "status",
                    "renderer",
                    "renderer_version",
                    "page_count",
                )
            }
            for item in manifest.get("artifacts", ())
        ],
        "enclosures": [
            {
                key: item.get(key)
                for key in ("number", "sha256", "size", "status")
            }
            for item in manifest.get("enclosures", ())
        ],
        "render_qa": dict(manifest.get("render_qa", {})),
        "blockers": list(manifest.get("blockers", ())),
        "missing_approvals": list(manifest.get("missing_approvals", ())),
    }


def release_basis_sha256(manifest: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _release_basis_payload(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def build_release_pack(
    complaint: StructuredComplaint,
    output_dir: str | Path,
    *,
    enclosure_sources: Iterable[str | Path] = (),
    soffice_path: str | Path | None = None,
    pdftoppm_path: str | Path | None = None,
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
    try:
        require_release_support(complaint)
    except ValueError as exc:
        blockers.append(str(exc))

    docx_path = artifacts_dir / "constitutional-complaint.docx"
    pdf_path = artifacts_dir / "constitutional-complaint.pdf"
    artifacts: list[dict[str, Any]] = []
    qa: dict[str, Any] = {"passed": False, "reason": "not_run"}
    try:
        docx = render_docx(complaint, docx_path)
        artifacts.append(docx.to_dict())
        pdf = convert_docx_to_pdf(
            docx_path, pdf_path, soffice_path=soffice_path
        )
        artifacts.append(pdf.to_dict())
        qa = validate_rendered_pair(
            complaint,
            docx_path,
            pdf_path,
            preview_dir=previews_dir,
            pdftoppm_path=pdftoppm_path,
        )
        if not qa.get("passed"):
            blockers.append("render_or_visual_qa_failed")
    except Exception as exc:  # error becomes a fail-closed manifest, not a false release
        blockers.append(f"artifact_generation_failed: {exc}")
        qa = {"passed": False, "reason": str(exc)}

    enclosures = _copy_enclosures(enclosure_sources, destination / "enclosures")
    missing_enclosures = [item for item in enclosures if item["status"] != "included"]
    if missing_enclosures:
        blockers.append("missing_enclosure_files")
    if len(complaint.enclosure_refs) != len(enclosures):
        blockers.append("enclosure_reference_count_mismatch")

    formal_ready, formal_reasons = _formal_check_ready(complaint.formal_check)
    blockers.extend(formal_reasons)
    missing_approvals = [
        code
        for code in REQUIRED_APPROVALS
        if complaint.approvals.get(code) != "approved"
    ]

    release_status = "blocked" if blockers else "ready_for_expert_review"

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "matter_id": complaint.matter_id,
        "draft_id": complaint.draft_id,
        "created_at": _now(),
        "status": release_status,
        "human_only_actions": ["signature", "fee_or_exemption_confirmation", "filing"],
        "filing_performed": False,
        "source_versions": list(complaint.source_versions),
        "norm_passport_ids": list(complaint.norm_passport_ids),
        "issue_option_id": complaint.issue_option_id,
        "approvals": dict(complaint.approvals),
        "missing_approvals": missing_approvals,
        "formal_check": dict(complaint.formal_check),
        "formal_check_ready": formal_ready,
        "sentence_evidence_map": complaint.sentence_evidence_map(),
        "artifacts": artifacts,
        "enclosures": enclosures,
        "render_qa": qa,
        "blockers": sorted(set(blockers)),
        "release_approval": None,
    }
    manifest["release_basis_sha256"] = release_basis_sha256(manifest)
    manifest_path = destination / "filing-package-manifest.json"
    _write_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    manifest["manifest_sha256"] = file_sha256(manifest_path)
    return manifest


def approve_release_pack(
    manifest_path: str | Path,
    *,
    reviewer: str,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Именно и явно одобрить неизменившийся реальный пакет после визуальной проверки."""

    path = Path(manifest_path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    reviewer_name = str(reviewer or "").strip()
    if not reviewer_name:
        raise ValueError("Для выпуска нужен именованный проверяющий")
    if manifest.get("status") == "blocked" or manifest.get("blockers"):
        raise ValueError("Заблокированный пакет нельзя одобрить")
    if manifest.get("missing_approvals"):
        raise ValueError("Не завершены обязательные юридические одобрения")
    if not (manifest.get("render_qa") or {}).get("passed"):
        raise ValueError("Визуальная и семантическая проверка файлов не пройдена")
    integrity_errors = verify_release_manifest(manifest)
    if integrity_errors:
        raise ValueError("Нарушена целостность пакета: " + ", ".join(integrity_errors))
    observed_basis = release_basis_sha256(manifest)
    if manifest.get("release_basis_sha256") != observed_basis:
        raise ValueError("Основание выпуска изменилось; пакет нужно пересобрать и проверить заново")
    manifest["release_approval"] = {
        "status": "approved",
        "reviewer": reviewer_name,
        "reviewed_at": reviewed_at or _now(),
        "basis_sha256": observed_basis,
    }
    manifest["status"] = "ready_for_human_signing_filing"
    _write_json(path, manifest)
    manifest["manifest_path"] = str(path)
    manifest["manifest_sha256"] = file_sha256(path)
    return manifest


def verify_release_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return integrity errors without mutating the filing pack."""

    errors: list[str] = []
    for item in list(manifest.get("artifacts", ())) + list(manifest.get("enclosures", ())):
        if item.get("status") not in {"complete", "included"}:
            continue
        path = Path(str(item.get("path", "")))
        if not path.is_file():
            errors.append(f"missing:{path}")
            continue
        observed = file_sha256(path)
        if observed != item.get("sha256"):
            errors.append(f"hash_mismatch:{path}")
    if manifest.get("filing_performed") is not False:
        errors.append("filing_performed_must_be_false")
    observed_basis = release_basis_sha256(manifest)
    if manifest.get("release_basis_sha256") != observed_basis:
        errors.append("release_basis_mismatch")
    if manifest.get("status") == "ready_for_human_signing_filing":
        approval = manifest.get("release_approval") or {}
        if (
            approval.get("status") != "approved"
            or not approval.get("reviewer")
            or not approval.get("reviewed_at")
            or approval.get("basis_sha256") != observed_basis
        ):
            errors.append("release_approval_missing_or_stale")
    return errors
