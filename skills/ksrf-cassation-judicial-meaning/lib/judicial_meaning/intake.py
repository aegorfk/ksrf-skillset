"""Local, subject-neutral intake of applicant-provided judicial acts."""

from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import re
import shutil
import subprocess
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


_WHITESPACE_RE = re.compile(r"\s+")


def _normalise_text(value: str) -> str:
    """Return stable human-readable text without changing its meaning."""

    return _WHITESPACE_RE.sub(" ", value).strip()


class _VisibleTextParser(HTMLParser):
    """Extract visible HTML text without depending on a browser or parser package."""

    _ignored = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in self._ignored:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in self._ignored and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data)


def _decode_text(raw: bytes) -> str:
    """Decode user material conservatively, rejecting undecodable input."""

    if b"\x00" in raw:
        raise ValueError("Файл похож на двоичный, а не на текстовый документ.")
    for encoding in ("utf-8-sig", "utf-8", "windows-1251"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Не удалось надёжно определить кодировку текста.")


def _extract_html(raw: bytes) -> str:
    parser = _VisibleTextParser()
    parser.feed(_decode_text(raw))
    parser.close()
    return _normalise_text(html.unescape(" ".join(parser.parts)))


def _json_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        parts: list[str] = []
        for key in sorted(value, key=str):
            parts.extend(_json_strings(value[key]))
        return parts
    if isinstance(value, list):
        parts = []
        for item in value:
            parts.extend(_json_strings(item))
        return parts
    return []


def _extract_json(raw: bytes) -> str:
    value = json.loads(_decode_text(raw))
    return _normalise_text(" ".join(_json_strings(value)))


def _extract_docx(path: Path) -> str:
    """Extract DOCX text from its OOXML payload using only the standard library."""

    with zipfile.ZipFile(path) as archive:
        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as exc:
            raise ValueError("В DOCX отсутствует word/document.xml.") from exc
    root = ElementTree.fromstring(document_xml)
    pieces: list[str] = []
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name in {"t", "tab", "br", "cr"}:
            if local_name == "t" and element.text:
                pieces.append(element.text)
            else:
                pieces.append(" ")
    return _normalise_text(" ".join(pieces))


def _extract_pdf(path: Path) -> tuple[str, dict[str, Any]]:
    """Use an explicitly detected local helper; never make it a hidden import."""

    executable = shutil.which("pdftotext")
    if not executable:
        raise ValueError(
            "PDF требует локальный pdftotext либо вручную проверенную текстовую копию; помощник не найден."
        )
    try:
        version_result = subprocess.run(
            [executable, "-v"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        helper_version = _normalise_text(version_result.stderr or version_result.stdout)[:300]
    except (OSError, subprocess.SubprocessError):
        helper_version = "version_unavailable"
    with tempfile.TemporaryDirectory(prefix="judicial-meaning-pdf-") as temporary_directory:
        destination = Path(temporary_directory) / "extracted.txt"
        try:
            result = subprocess.run(
                [executable, "-layout", str(path), str(destination)],
                capture_output=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError(f"pdftotext не выполнил извлечение: {exc.__class__.__name__}") from exc
        if result.returncode != 0 or not destination.exists():
            diagnostic = (result.stderr or b"").decode("utf-8", errors="replace")[:300]
            raise ValueError(f"pdftotext завершился с кодом {result.returncode}: {diagnostic}")
        raw_text = destination.read_bytes()
    text = _normalise_text(_decode_text(raw_text))
    if not text:
        raise ValueError(
            "PDF не содержит извлекаемого текстового слоя; нужен локальный OCR или проверенная текстовая копия."
        )
    return text, {
        "extraction_method": "pdftotext",
        "helper_name": "pdftotext",
        "helper_version": helper_version,
        "command_profile": "pdftotext -layout INPUT OUTPUT",
    }


def _helper_version(executable: str, flag: str) -> str:
    try:
        result = subprocess.run(
            [executable, flag],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "version_unavailable"
    return _normalise_text(result.stdout or result.stderr)[:300] or "version_unavailable"


def ocr_pdf_to_text(
    source: str | Path,
    destination: str | Path,
    *,
    language: str = "rus",
    dpi: int = 300,
) -> dict[str, Any]:
    """Run an explicit local OCR step and persist a provenance sidecar.

    OCR is intentionally separate from intake: its output remains unverified
    until a person compares it with the rendered pages and then supplies the
    text file to ``intake``.
    """

    pdf_path = Path(source).expanduser().resolve()
    output_path = Path(destination).expanduser().resolve()
    if pdf_path.suffix.casefold() != ".pdf" or not pdf_path.is_file():
        raise ValueError("Для OCR нужен существующий PDF-файл.")
    if dpi < 150 or dpi > 600:
        raise ValueError("OCR DPI должен быть в диапазоне 150–600.")
    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        raise ValueError("OCR требует локальные pdftoppm и tesseract.")

    with tempfile.TemporaryDirectory(prefix="judicial-meaning-ocr-") as temporary_directory:
        prefix = Path(temporary_directory) / "page"
        render = subprocess.run(
            [pdftoppm, "-r", str(dpi), "-png", str(pdf_path), str(prefix)],
            capture_output=True,
            timeout=600,
            check=False,
        )
        pages = sorted(prefix.parent.glob(prefix.name + "-*.png"))
        if render.returncode != 0 or not pages:
            diagnostic = (render.stderr or b"").decode("utf-8", errors="replace")[:300]
            raise ValueError(f"pdftoppm не подготовил страницы для OCR: {diagnostic}")
        extracted_pages: list[str] = []
        for page_number, page in enumerate(pages, start=1):
            result = subprocess.run(
                [tesseract, str(page), "stdout", "-l", language],
                capture_output=True,
                timeout=600,
                check=False,
            )
            if result.returncode != 0:
                diagnostic = (result.stderr or b"").decode("utf-8", errors="replace")[:300]
                raise ValueError(f"tesseract не распознал страницу {page_number}: {diagnostic}")
            text = _normalise_text(_decode_text(result.stdout))
            if not text:
                raise ValueError(f"OCR не извлёк текст со страницы {page_number}.")
            extracted_pages.append(f"[Страница {page_number}]\n{text}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n\n".join(extracted_pages) + "\n"
    output_path.write_text(output_text, encoding="utf-8", newline="\n")
    source_bytes = pdf_path.read_bytes()
    provenance = {
        "schema_version": "1.0",
        "source_file": pdf_path.name,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "output_file": output_path.name,
        "output_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "page_count": len(extracted_pages),
        "language": language,
        "dpi": dpi,
        "helpers": {
            "pdftoppm": _helper_version(pdftoppm, "-v"),
            "tesseract": _helper_version(tesseract, "--version"),
        },
        "command_profiles": [
            "pdftoppm -r DPI -png INPUT PAGE_PREFIX",
            "tesseract PAGE stdout -l LANGUAGE",
        ],
        "human_verified": False,
        "warning": "Сверьте OCR с изображениями всех страниц до юридического кодирования.",
    }
    sidecar = output_path.with_suffix(output_path.suffix + ".provenance.json")
    sidecar.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return provenance


def _base_record(path: Path, raw: bytes) -> dict[str, Any]:
    guessed_type, _ = mimetypes.guess_type(path.name)
    return {
        "schema_version": "1.0",
        "file_name": path.name,
        "source_path": str(path.resolve()),
        "media_type": guessed_type or "application/octet-stream",
        "byte_size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def intake_document(source: str | Path) -> dict[str, Any]:
    """Inventory and extract one applicant document.

    Unsupported, malformed, empty, or binary documents are reported as
    ``unextractable``.  Their bytes are never interpreted as legal text.  The raw
    text remains in the private record so a caller can store it locally; use
    :func:`public_intake_record` for logs or exports.
    """

    path = Path(source)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {
            "schema_version": "1.0",
            "file_name": path.name,
            "source_path": str(path.absolute()),
            "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "byte_size": None,
            "sha256": None,
            "extraction_status": "unavailable",
            "text": "",
            "extraction_error": f"Файл недоступен: {exc.__class__.__name__}",
        }

    record = _base_record(path, raw)
    suffix = path.suffix.casefold()
    extraction_metadata: dict[str, Any] = {"extraction_method": "stdlib"}
    try:
        if suffix in {".txt", ".md", ".csv"}:
            text = _normalise_text(_decode_text(raw))
        elif suffix in {".html", ".htm"}:
            text = _extract_html(raw)
        elif suffix == ".json":
            text = _extract_json(raw)
        elif suffix == ".docx":
            text = _extract_docx(path)
        elif suffix == ".pdf":
            text, extraction_metadata = _extract_pdf(path)
        else:
            raise ValueError(f"Формат {suffix or '[без расширения]'} не поддерживается встроенным извлечением.")
        if not text:
            raise ValueError("Из документа не извлечён содержательный текст.")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        record.update(
            {
                "extraction_status": "unextractable",
                "text": "",
                "extraction_error": str(exc),
            }
        )
        return record

    record.update(
        {
            "extraction_status": "extracted",
            "text": text,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "character_count": len(text),
            "extraction_error": None,
            **extraction_metadata,
        }
    )
    return record


def public_intake_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return provenance metadata safe for a manifest or diagnostic report."""

    private_fields = {"text", "source_path"}
    return {key: value for key, value in record.items() if key not in private_fields}
