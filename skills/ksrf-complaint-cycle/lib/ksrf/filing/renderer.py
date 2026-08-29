"""DOCX/PDF renderer and deterministic semantic/visual checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from PIL import Image
from pypdf import PdfReader

from .composer import StructuredComplaint


PLACEHOLDER_PATTERNS = (
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"\[(?:УКАЗАТЬ|ВСТАВИТЬ|ЗАПОЛНИТЬ)[^\]]*\]", re.IGNORECASE),
)


@dataclass(frozen=True)
class RenderedArtifact:
    kind: str
    path: str
    mime_type: str
    size: int
    sha256: str
    renderer: str
    renderer_version: str
    status: str
    page_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "mime_type": self.mime_type,
            "size": self.size,
            "sha256": self.sha256,
            "renderer": self.renderer,
            "renderer_version": self.renderer_version,
            "status": self.status,
            "page_count": self.page_count,
        }


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    return " ".join((value or "").replace("\u00a0", " ").split())


def complaint_plain_text(complaint: StructuredComplaint) -> str:
    chunks = [complaint.title]
    for section in complaint.sections:
        chunks.append(section.heading)
        chunks.extend(sentence.text for sentence in section.sentences)
    return "\n".join(chunks)


def _set_cell_margins(cell: Any, top: int = 80, start: int = 80, bottom: int = 80, end: int = 80) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def _add_page_number(paragraph: Any) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instr, end))


def _configure_document(document: Document, complaint: StructuredComplaint) -> None:
    for section in document.sections:
        section.top_margin = Mm(20)
        section.bottom_margin = Mm(20)
        section.left_margin = Mm(30)
        section.right_margin = Mm(15)
        _add_page_number(section.footer.paragraphs[0])

    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(14)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.first_line_indent = Mm(12.5)
    normal.paragraph_format.widow_control = True

    if "KSRF Heading" not in document.styles:
        heading = document.styles.add_style("KSRF Heading", WD_STYLE_TYPE.PARAGRAPH)
    else:
        heading = document.styles["KSRF Heading"]
    heading.font.name = "Times New Roman"
    heading._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    heading.font.size = Pt(14)
    heading.font.bold = True
    heading.paragraph_format.space_before = Pt(12)
    heading.paragraph_format.space_after = Pt(6)
    heading.paragraph_format.keep_with_next = True

    properties = document.core_properties
    properties.title = complaint.title
    properties.subject = f"Matter {complaint.matter_id}; draft {complaint.draft_id}"
    properties.author = "KSRF filing-readiness system"
    properties.keywords = "КС РФ, конституционная жалоба, evidence map"
    stable_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
    properties.created = stable_time
    properties.modified = stable_time


def render_docx(complaint: StructuredComplaint, output_path: str | Path) -> RenderedArtifact:
    """Render a real DOCX artifact from a validated complaint model."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    _configure_document(document, complaint)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.first_line_indent = Mm(0)
    run = title.add_run(complaint.title)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)

    for section in complaint.sections:
        document.add_paragraph(section.heading, style="KSRF Heading")
        for sentence in section.sentences:
            paragraph = document.add_paragraph(sentence.text)
            paragraph.style = document.styles["Normal"]

    document.save(destination)
    return RenderedArtifact(
        kind="complaint_docx",
        path=str(destination),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=destination.stat().st_size,
        sha256=file_sha256(destination),
        renderer="python-docx",
        renderer_version="1.2",
        status="complete",
    )


def extract_docx_text(path: str | Path) -> str:
    document = Document(str(path))
    chunks: list[str] = []
    chunks.extend(paragraph.text for paragraph in document.paragraphs if paragraph.text)
    for table in document.tables:
        for row in table.rows:
            chunks.extend(cell.text for cell in row.cells if cell.text)
    return "\n".join(chunks)


def resolve_executable(name: str, explicit: str | Path | None = None) -> str | None:
    if explicit:
        candidate = Path(explicit)
        if candidate.is_file() and candidate.exists():
            return str(candidate)
        return None
    return shutil.which(name)


def convert_docx_to_pdf(
    docx_path: str | Path,
    pdf_path: str | Path,
    *,
    soffice_path: str | Path | None = None,
    timeout_seconds: int = 60,
) -> RenderedArtifact:
    """Convert through LibreOffice without invoking a shell."""

    source = Path(docx_path).resolve()
    destination = Path(pdf_path).resolve()
    executable = resolve_executable("soffice", soffice_path) or resolve_executable(
        "libreoffice", soffice_path
    )
    if not executable:
        raise RuntimeError("Не найден LibreOffice/soffice для преобразования PDF")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ksrf-pdf-") as tmp:
        completed = subprocess.run(
            [
                executable,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmp,
                str(source),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        produced = Path(tmp) / f"{source.stem}.pdf"
        if completed.returncode != 0 or not produced.is_file():
            detail = normalize_text(completed.stderr or completed.stdout)
            raise RuntimeError(f"LibreOffice не создал PDF: {detail or 'unknown error'}")
        shutil.copy2(produced, destination)

    reader = PdfReader(str(destination))
    return RenderedArtifact(
        kind="complaint_pdf",
        path=str(destination),
        mime_type="application/pdf",
        size=destination.stat().st_size,
        sha256=file_sha256(destination),
        renderer="LibreOffice",
        renderer_version=_executable_version(executable),
        status="complete",
        page_count=len(reader.pages),
    )


def _executable_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return normalize_text(completed.stdout or completed.stderr) or "unknown"


def extract_pdf_text(path: str | Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text, len(reader.pages)


def extract_pdf_body_text(path: str | Path) -> tuple[str, int]:
    """Extract body text while ignoring renderer-added standalone page numbers."""

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        lines = (page.extract_text() or "").splitlines()
        pages.append("\n".join(line for line in lines if not line.strip().isdigit()))
    return "\n".join(pages), len(reader.pages)


def find_unresolved_placeholders(text: str) -> list[str]:
    found: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        found.extend(match.group(0) for match in pattern.finditer(text or ""))
    return sorted(set(found))


def _page_image_findings(path: Path) -> list[dict[str, Any]]:
    with Image.open(path) as source:
        image = source.convert("L")
        width, height = image.size
        histogram = image.histogram()
        dark_count = sum(histogram[:245])
        coverage = dark_count / max(width * height, 1)
        findings: list[dict[str, Any]] = []
        if coverage < 0.0005:
            findings.append({"code": "unexpected_blank_page", "material": True})
        edges = (
            image.crop((0, 0, width, min(3, height))),
            image.crop((0, max(height - 3, 0), width, height)),
            image.crop((0, 0, min(3, width), height)),
            image.crop((max(width - 3, 0), 0, width, height)),
        )
        if any(sum(edge.histogram()[:245]) for edge in edges):
            findings.append({"code": "content_touches_page_edge", "material": True})
        return findings


def render_pdf_previews(
    pdf_path: str | Path,
    preview_dir: str | Path,
    *,
    pdftoppm_path: str | Path | None = None,
    timeout_seconds: int = 60,
) -> list[Path]:
    executable = resolve_executable("pdftoppm", pdftoppm_path)
    if not executable:
        raise RuntimeError("Не найден pdftoppm для визуальной проверки PDF")
    destination = Path(preview_dir)
    destination.mkdir(parents=True, exist_ok=True)
    prefix = destination / "page"
    completed = subprocess.run(
        [executable, "-png", "-r", "120", str(Path(pdf_path).resolve()), str(prefix)],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    pages = sorted(destination.glob("page-*.png"))
    if completed.returncode != 0 or not pages:
        detail = normalize_text(completed.stderr or completed.stdout)
        raise RuntimeError(f"Не удалось отрисовать страницы PDF: {detail or 'unknown error'}")
    return pages


def validate_rendered_pair(
    complaint: StructuredComplaint,
    docx_path: str | Path,
    pdf_path: str | Path,
    *,
    preview_dir: str | Path,
    pdftoppm_path: str | Path | None = None,
) -> dict[str, Any]:
    expected = normalize_text(complaint_plain_text(complaint))
    docx_text = normalize_text(extract_docx_text(docx_path))
    pdf_raw, page_count = extract_pdf_body_text(pdf_path)
    pdf_text = normalize_text(pdf_raw)

    missing_in_docx = expected not in docx_text
    missing_in_pdf = expected not in pdf_text
    placeholders = find_unresolved_placeholders("\n".join((docx_text, pdf_text)))
    pages = render_pdf_previews(
        pdf_path, preview_dir, pdftoppm_path=pdftoppm_path
    )
    visual_findings: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        for finding in _page_image_findings(page):
            visual_findings.append({"page": index, **finding})

    checks = {
        "docx_semantic_match": not missing_in_docx,
        "pdf_semantic_match": not missing_in_pdf,
        "page_count": page_count,
        "preview_count": len(pages),
        "placeholders": placeholders,
        "visual_findings": visual_findings,
    }
    checks["passed"] = (
        checks["docx_semantic_match"]
        and checks["pdf_semantic_match"]
        and not placeholders
        and not any(item.get("material") for item in visual_findings)
        and page_count == len(pages)
    )
    return checks
