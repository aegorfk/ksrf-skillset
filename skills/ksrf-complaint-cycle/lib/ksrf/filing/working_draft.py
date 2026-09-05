"""Provisional documents for human review, separate from authenticated release."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .composer import ComplaintModelError, REQUIRED_SECTION_CODES, build_structured_complaint
from .renderer import find_unresolved_placeholders

NOTICE = "РАБОЧИЙ ПРОЕКТ. Для юридической проверки. Не для подписания и подачи."
SECTION_HEADINGS = dict(zip(REQUIRED_SECTION_CODES, (
    "Адресат", "Заявитель", "Предмет обращения", "Допустимость", "Факты",
    "Судебные стадии", "Конституционный вопрос", "Правовая аргументация",
    "Правовые источники", "Возможные возражения", "Просительная часть", "Приложения",
)))


def prepare_working_draft(payload: Mapping[str, Any]):
    """Keep original claims and uncertainties; never authenticate caller approvals."""
    source = deepcopy(dict(payload))
    sections = source.setdefault("sections", [])
    if not isinstance(sections, list) or any(not isinstance(s, dict) for s in sections):
        raise ComplaintModelError("sections должен быть списком разделов")
    present = {s.get("code") for s in sections}
    missing = [code for code in REQUIRED_SECTION_CODES if code not in present]
    for code in missing:
        sections.append({
            "code": code, "heading": SECTION_HEADINGS[code],
            "sentences": [{"text": "[НЕ ПРЕДОСТАВЛЕНО: " + SECTION_HEADINGS[code] + "]",
                           "role": "narrative", "support_status": "pending"}],
        })
    original = build_structured_complaint(source)
    gaps = [{"code": "section_missing", "section_code": code,
             "message": "Заполнить раздел: " + SECTION_HEADINGS[code]} for code in missing]
    marked_sections = []
    for section in original.sections:
        sentences = []
        if not section.sentences:
            gaps.append({"code": "section_empty", "section_code": section.code,
                         "message": "Проверить пустой раздел: " + section.heading})
        for sentence in section.sentences:
            uncertain = (sentence.filing_significant or not sentence.role_known
                         or bool(find_unresolved_placeholders(sentence.text))
                         or section.code in missing)
            if uncertain:
                gaps.append({
                    "code": "sentence_requires_review", "sentence_id": sentence.sentence_id,
                    "section_code": section.code, "role": sentence.role,
                    "declared_support_status": sentence.support_status,
                    "evidence_ids": list(sentence.evidence_ids),
                    "message": sentence.note or "Проверить содержание и опоры; независимое одобрение не подтверждено.",
                })
            sentences.append(replace(sentence, text=sentence.text + (
                f" (ПРОВЕРИТЬ: {sentence.sentence_id})" if uncertain else ""
            )))
        marked_sections.append(replace(section, sentences=tuple(sentences)))
    marked = replace(original, title=NOTICE + "\n" + original.title,
                     sections=tuple(marked_sections), approvals={}, formal_check={})
    return original, marked, gaps


def render_error_details(exc: Exception, *, stage: str | None = None) -> dict[str, Any]:
    codes = list(getattr(exc, "reason_codes", ()))
    if isinstance(exc, ComplaintModelError):
        authority = stage == "authority" or any(any(word in code for word in ("authority", "binding", "receipt")) for code in codes)
        reason = "evidence_authority_required" if authority else "draft_input_invalid"
        action = ("Подключите указанную доверенную проверку; для рабочего проекта используйте render draft."
                  if authority else "Исправьте структуру входного проекта по указанной ошибке.")
    elif isinstance(exc, (FileNotFoundError, ImportError)):
        reason, action = "document_tool_unavailable", "Проверьте указанный инструмент или библиотеку в локальном окружении."
    else:
        reason, action = "document_generation_failed", "Проверьте сообщение конвертации и сохранённые файлы; повторите после исправления причины."
    return {"reason_code": reason, "support_errors": codes, "error": str(exc), "next_action": action}


def _file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": sha256(data).hexdigest(), "size_bytes": len(data)}


def pdf_line_wrap_match(expected: str, extracted: str) -> bool:
    """Repair only a physical line break after a retained hyphen/dash, then compare."""
    from .renderer import normalize_text
    joined = re.sub(r"(?<=\w)([-–—])[ \t]*\n[ \t]*(?=\w)", r"\1", extracted)
    joined = re.sub(r"(?<=\w)[ \t]*\n[ \t]*([-–—])(?=\w)", r"\1", joined)
    return normalize_text(expected) == normalize_text(joined)


def build_working_draft(workspace: Path, payload: Mapping[str, Any], input_sha: str) -> dict[str, Any]:
    """Render an explicitly unapproved review copy, without creating release receipts."""
    from .renderer import render_docx, convert_docx_to_pdf, validate_rendered_pair, complaint_plain_text, extract_pdf_body_text
    from tempfile import mkdtemp

    original, marked, gaps = prepare_working_draft(payload["complaint"])
    root = workspace.resolve() / "drafts"
    root.mkdir(parents=True, exist_ok=True)
    output = Path(mkdtemp(prefix=input_sha[:12] + "-", dir=root))
    source = output / "original-text.txt"
    source.write_text(complaint_plain_text(original), encoding="utf-8")
    review = output / "review-gaps.json"
    review.write_text(json.dumps({"human_review": "pending", "gaps": gaps}, ensure_ascii=False, indent=2), encoding="utf-8")
    docx = render_docx(marked, output / "working-draft.docx")
    pdf = convert_docx_to_pdf(docx.path, output / "working-draft.pdf", soffice_path=payload.get("soffice_path"))
    previews = output / "previews"
    qa = validate_rendered_pair(marked, docx.path, pdf.path, preview_dir=previews, pdftoppm_path=payload.get("pdftoppm_path"))
    pdf_matches = qa.get("pdf_semantic_match") is True
    if not pdf_matches:
        pdf_matches = pdf_line_wrap_match(complaint_plain_text(marked), extract_pdf_body_text(pdf.path)[0])
    qa["working_draft_pdf_semantic_match"] = pdf_matches
    qa["pdf_line_wrap_recovered"] = pdf_matches and not qa.get("pdf_semantic_match")
    technical_passed = bool(qa.get("docx_semantic_match") and pdf_matches
                            and qa.get("page_count", 0) > 0
                            and qa.get("page_count") == qa.get("preview_count")
                            and not any(f.get("material") for f in qa.get("visual_findings", [])))
    preview_paths = sorted(previews.glob("page-*.png"))
    artifacts = [_file_record(Path(docx.path)), _file_record(Path(pdf.path)), _file_record(source),
                 _file_record(review), *[_file_record(p) for p in preview_paths]]
    manifest = {
        "schema_version": "1.0", "artifact_type": "WorkingDraftManifest",
        "state": "working_draft_created" if technical_passed else "blocked",
        "input_sha256": input_sha, "human_review": "pending", "filing_authority": False,
        "approval_authority": False, "release_eligible": False,
        "working_draft_technical_passed": technical_passed, "qa": qa,
        "artifacts": artifacts, "gaps": gaps,
        "sentence_map": [{"sentence_id": s.sentence_id, "section_code": section.code,
                          "role": s.role, "text": s.text, "evidence_ids": list(s.evidence_ids)}
                         for section in original.sections for s in section.sentences],
    }
    path = output / "working-draft-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**manifest, "output_dir": str(output), "manifest": _file_record(path),
            "docx": docx.to_dict(), "pdf": pdf.to_dict(), "preview_paths": [str(p) for p in preview_paths]}


def verify_working_draft(workspace: Path, result: Mapping[str, Any]) -> list[str]:
    """Recheck saved bytes; no result of this function conveys legal approval."""
    root = (workspace.resolve() / "drafts").resolve()
    errors = []
    try:
        record = result["manifest"]
        path = Path(record["path"]).resolve()
        if not path.is_relative_to(root) or _file_record(path) != record:
            return ["working_draft_manifest_changed"]
        manifest = json.loads(path.read_bytes())
        if (manifest.get("artifact_type") != "WorkingDraftManifest"
                or any(manifest.get(k) is not False for k in ("filing_authority", "approval_authority", "release_eligible"))
                or manifest.get("human_review") != "pending"):
            return ["working_draft_manifest_invalid"]
        for artifact in manifest["artifacts"]:
            target = Path(artifact["path"]).resolve()
            if not target.is_relative_to(root) or _file_record(target) != artifact:
                errors.append("working_draft_artifact_changed:" + target.name)
    except (OSError, KeyError, TypeError, ValueError):
        errors.append("working_draft_artifact_unavailable")
    return errors
