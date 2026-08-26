"""Portable parsers for the public KSOYU pages.

The module deliberately uses only the Python standard library.  It does not
decide that an empty-looking response is an empty court list unless the page
contains the expected court structure and an explicit empty-result marker.
"""

from __future__ import annotations

import codecs
import re
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from typing import Mapping
from urllib.parse import parse_qs, urldefrag, urljoin, urlparse


_PROTECTIVE_MARKERS = (
    "captcha",
    "recaptcha",
    "код с картинки",
    "доступ временно ограничен",
    "доступ ограничен",
    "проверка, что вы не робот",
    "проверка что вы не робот",
    "access denied",
    "forbidden",
    "cloudflare",
)
_EMPTY_MARKERS = (
    "по заданным параметрам дел не найдено",
    "дел не найдено",
    "ничего не найдено",
)
_IGNORED_TEXT_TAGS = {"script", "style", "noscript", "template"}
_CHROME_TAGS = {"nav", "header", "footer", "form", "aside"}
KSOYU_ADAPTER_ID = "ksoyu_daily_v2"
KSOYU_PARSER_VERSION = "2.0"


@dataclass(frozen=True)
class DecodedResponse:
    text: str
    encoding: str


@dataclass(frozen=True)
class ListingRow:
    text: str
    case_urls: tuple[str, ...] = ()
    doc_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class ListingResult:
    listing_date: str
    structural_ok: bool
    rows: list[ListingRow]
    case_urls: list[str]
    doc_urls: list[str]
    pagination_urls: list[str]
    navigation_state: str
    protective: bool = False
    explicit_empty: bool = False
    page_text: str = ""
    listing_shell_seen: bool = False
    listing_table_seen: bool = False
    control_date_confirmed: bool = False
    content_date_confirmed: bool = False
    date_confirmed: bool = False
    empty_evidence_code: str | None = None
    case_row_count: int = 0


@dataclass(frozen=True)
class SourcePage:
    kind: str
    status: str
    text: str = ""
    doc_urls: list[str] = field(default_factory=list)
    protective: bool = False
    structural_ok: bool = False


@dataclass
class _Anchor:
    href: str
    rel: tuple[str, ...]
    in_navigation: bool
    text_parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return _clean_text(" ".join(self.text_parts))


@dataclass
class _MutableRow:
    text_parts: list[str] = field(default_factory=list)
    hrefs: list[str] = field(default_factory=list)
    has_data_cell: bool = False


class _CourtHTMLParser(HTMLParser):
    """Collect structural evidence without depending on BeautifulSoup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool, bool]] = []
        self.ignored_depth = 0
        self.chrome_depth = 0
        self.content_depth = 0
        self.listing_table_depth = 0
        self.listing_table_seen = False
        self.listing_form_depth = 0
        self.listing_form_seen = False
        self.listing_name_control_seen = False
        self.listing_server_control_seen = False
        self.listing_date_value: str | None = None
        self.current_row: _MutableRow | None = None
        self.rows: list[_MutableRow] = []
        self.current_anchor: _Anchor | None = None
        self.anchors: list[_Anchor] = []
        self.all_text: list[str] = []
        self.content_text: list[str] = []
        self.fallback_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr = {key.lower(): (value or "") for key, value in attrs}
        starts_ignored = tag in _IGNORED_TEXT_TAGS
        starts_chrome = tag in _CHROME_TAGS
        starts_content = tag in {"main", "article"} or attr.get("id", "").lower() in {
            "content",
            "main",
            "document",
            "doccontent",
        }
        starts_listing = tag == "table" and (
            attr.get("id", "").lower() == "tablcont"
            or "tablcont" in attr.get("class", "").lower().split()
        )
        starts_listing_form = tag == "form" and attr.get("id", "").casefold() == "calformh"
        self.stack.append((tag, starts_ignored, starts_chrome, starts_content))
        if starts_ignored:
            self.ignored_depth += 1
        if starts_chrome:
            self.chrome_depth += 1
        if starts_content:
            self.content_depth += 1
        if starts_listing:
            self.listing_table_seen = True
            self.listing_table_depth += 1
        elif self.listing_table_depth and tag == "table":
            self.listing_table_depth += 1
        if starts_listing_form:
            self.listing_form_seen = True
            self.listing_form_depth += 1
        elif self.listing_form_depth and tag == "form":
            self.listing_form_depth += 1

        if tag == "input" and self.listing_form_depth:
            control_name = attr.get("name", "").casefold()
            control_value = attr.get("value", "").strip()
            if control_name == "name" and control_value.casefold() == "sud_delo":
                self.listing_name_control_seen = True
            elif control_name == "srv_num" and control_value == "1":
                self.listing_server_control_seen = True
            elif control_name == "h_date" and control_value:
                self.listing_date_value = control_value

        if tag == "tr" and self.listing_table_depth:
            self.current_row = _MutableRow()
        elif tag == "td" and self.current_row is not None:
            self.current_row.has_data_cell = True

        if tag == "a":
            href = attr.get("href", "").strip()
            rel = tuple(part.lower() for part in attr.get("rel", "").split() if part)
            in_navigation = any(frame[0] == "nav" for frame in self.stack) or "next" in rel
            self.current_anchor = _Anchor(href=href, rel=rel, in_navigation=in_navigation)
            if self.current_row is not None and href:
                self.current_row.hrefs.append(href)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        value = _clean_text(data)
        if not value:
            return
        self.all_text.append(value)
        if self.current_anchor is not None:
            self.current_anchor.text_parts.append(value)
        if self.current_row is not None:
            self.current_row.text_parts.append(value)
        if not self.chrome_depth:
            self.fallback_text.append(value)
            if self.content_depth:
                self.content_text.append(value)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self.current_anchor is not None:
            self.anchors.append(self.current_anchor)
            self.current_anchor = None
        if tag == "tr" and self.current_row is not None:
            if self.current_row.has_data_cell:
                self.rows.append(self.current_row)
            self.current_row = None

        # Court HTML is normally balanced.  Searching backwards also keeps a
        # malformed inner element from corrupting all following depth flags.
        frame_index = next(
            (index for index in range(len(self.stack) - 1, -1, -1) if self.stack[index][0] == tag),
            None,
        )
        if frame_index is None:
            return
        removed = self.stack[frame_index:]
        del self.stack[frame_index:]
        for removed_tag, starts_ignored, starts_chrome, starts_content in reversed(removed):
            if starts_ignored:
                self.ignored_depth = max(0, self.ignored_depth - 1)
            if starts_chrome:
                self.chrome_depth = max(0, self.chrome_depth - 1)
            if starts_content:
                self.content_depth = max(0, self.content_depth - 1)
            if removed_tag == "table" and self.listing_table_depth:
                self.listing_table_depth -= 1
            if removed_tag == "form" and self.listing_form_depth:
                self.listing_form_depth -= 1


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalise_encoding(name: str) -> str | None:
    name = name.strip().strip("\"'")
    if not name:
        return None
    try:
        return codecs.lookup(name).name
    except LookupError:
        return None


def _content_type(headers: Mapping[str, str] | object | None) -> str:
    if headers is None:
        return ""
    try:
        items = headers.items()  # type: ignore[union-attr]
    except AttributeError:
        return ""
    for key, value in items:
        if str(key).lower() == "content-type":
            return str(value)
    return ""


def decode_response(raw: bytes, headers: Mapping[str, str] | object | None = None) -> DecodedResponse:
    """Decode a court response, honoring HTTP and HTML charset declarations."""

    candidates: list[str] = []
    content_type = _content_type(headers)
    header_match = re.search(r"charset\s*=\s*['\"]?([^;\s'\"]+)", content_type, re.I)
    if header_match:
        candidates.append(header_match.group(1))

    prefix = raw[:8192].decode("latin-1", errors="ignore")
    meta_match = re.search(
        r"<meta[^>]+charset\s*=\s*['\"]?\s*([^\s'\"/>;]+)", prefix, re.I
    )
    if not meta_match:
        meta_match = re.search(
            r"<meta[^>]+content\s*=\s*['\"][^'\"]*charset\s*=\s*([^\s'\";>]+)",
            prefix,
            re.I,
        )
    if meta_match:
        candidates.append(meta_match.group(1))
    if raw.startswith(codecs.BOM_UTF8):
        candidates.insert(0, "utf-8-sig")
    candidates.extend(("utf-8", "cp1251"))

    tried: set[str] = set()
    for candidate in candidates:
        encoding = _normalise_encoding(candidate)
        if not encoding or encoding in tried:
            continue
        tried.add(encoding)
        try:
            return DecodedResponse(raw.decode(encoding), encoding)
        except UnicodeDecodeError:
            continue
    # cp1251 maps every byte and is the least misleading fallback for these
    # Russian court endpoints.  Replacement is explicit for pathological data.
    return DecodedResponse(raw.decode("cp1251", errors="replace"), "cp1251")


def build_listing_url(host: str, listing_date: str) -> str:
    """Build the official daily listing endpoint for one KSOYU host."""

    parsed_date = date.fromisoformat(listing_date)
    clean_host = host.strip().lower()
    if clean_host.startswith("http://") or clean_host.startswith("https://"):
        parsed_host = urlparse(clean_host)
        clean_host = parsed_host.netloc
    if not clean_host or "/" in clean_host:
        raise ValueError("host must be a bare court host")
    return (
        f"https://{clean_host}/modules.php?name=sud_delo&srv_num=1"
        f"&H_date={parsed_date.strftime('%d.%m.%Y')}"
    )


def _absolute_url(base_url: str, href: str) -> str:
    return urldefrag(urljoin(base_url, href.strip()))[0]


def _same_origin(base_url: str, candidate_url: str) -> bool:
    base = urlparse(base_url)
    candidate = urlparse(candidate_url)
    return bool(
        base.scheme.casefold() in {"http", "https"}
        and candidate.scheme.casefold() == base.scheme.casefold()
        and candidate.netloc.casefold() == base.netloc.casefold()
    )


def _operation(url: str) -> str:
    values = parse_qs(urlparse(url).query).get("name_op", [])
    return values[0].lower() if values else ""


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _is_pagination(anchor: _Anchor, absolute_url: str) -> bool:
    query = parse_qs(urlparse(absolute_url).query)
    explicit_page_parameter = any(
        key.lower() in {"page", "pagen", "page_num", "pagenum", "start"} for key in query
    )
    label = anchor.text.casefold()
    explicit_label = bool(
        re.search(r"(?:следующ|далее|next|предыдущ|назад)", label)
        or label in {">", ">>", "›", "»", "<", "<<", "‹", "«"}
    )
    return "next" in anchor.rel or "prev" in anchor.rel or (
        explicit_page_parameter and (anchor.in_navigation or explicit_label)
    )


def _parse(html: str) -> _CourtHTMLParser:
    parser = _CourtHTMLParser()
    parser.feed(html)
    parser.close()
    return parser


def parse_listing(html: str, base_url: str, listing_date: str) -> ListingResult:
    """Parse one listing page and retain only observed navigation links."""

    parser = _parse(html)
    page_text = _clean_text(" ".join(parser.all_text))
    content_text = _clean_text(" ".join(parser.content_text or parser.fallback_text))
    folded = page_text.casefold()
    content_folded = content_text.casefold()
    protective = any(marker in folded for marker in _PROTECTIVE_MARKERS)
    expected_date = date.fromisoformat(listing_date).strftime("%d.%m.%Y")
    control_date_confirmed = parser.listing_date_value == expected_date
    content_date_confirmed = expected_date in content_text
    listing_shell_seen = bool(
        parser.listing_form_seen
        and parser.listing_name_control_seen
        and parser.listing_server_control_seen
        and parser.listing_date_value
    )
    date_confirmed = bool(
        listing_shell_seen and control_date_confirmed and content_date_confirmed
    )
    dated_empty = bool(
        re.search(
            rf"\bна\s+{re.escape(expected_date)}\s+дел\s+не\s+назначено\b",
            content_folded,
        )
    )
    generic_empty = any(marker in content_folded for marker in _EMPTY_MARKERS)

    case_urls: list[str] = []
    doc_urls: list[str] = []
    pagination_urls: list[str] = []
    for anchor in parser.anchors:
        if not anchor.href:
            continue
        absolute = _absolute_url(base_url, anchor.href)
        if not _same_origin(base_url, absolute):
            continue
        operation = _operation(absolute)
        if operation == "case":
            case_urls.append(absolute)
        elif operation == "doc":
            doc_urls.append(absolute)
        elif _is_pagination(anchor, absolute):
            pagination_urls.append(absolute)

    rows: list[ListingRow] = []
    for raw_row in parser.rows:
        row_cases: list[str] = []
        row_docs: list[str] = []
        for href in raw_row.hrefs:
            absolute = _absolute_url(base_url, href)
            if not _same_origin(base_url, absolute):
                continue
            operation = _operation(absolute)
            if operation == "case":
                row_cases.append(absolute)
            elif operation == "doc":
                row_docs.append(absolute)
        rows.append(
            ListingRow(
                text=_clean_text(" ".join(raw_row.text_parts)),
                case_urls=tuple(_unique(row_cases)),
                doc_urls=tuple(_unique(row_docs)),
            )
        )

    pagination_urls = _unique(pagination_urls)
    case_row_count = sum(bool(row.case_urls or row.doc_urls) for row in rows)
    exact_dated_empty = bool(
        listing_shell_seen
        and control_date_confirmed
        and content_date_confirmed
        and dated_empty
        and not case_urls
        and not doc_urls
        and not pagination_urls
        and case_row_count == 0
    )
    table_empty = bool(
        listing_shell_seen
        and control_date_confirmed
        and content_date_confirmed
        and parser.listing_table_seen
        and generic_empty
        and not case_urls
        and not doc_urls
        and not pagination_urls
        and case_row_count == 0
    )
    explicit_empty = exact_dated_empty or table_empty
    if exact_dated_empty:
        empty_evidence_code = "dated_no_scheduled_cases"
    elif table_empty:
        empty_evidence_code = "dated_table_zero_results"
    else:
        empty_evidence_code = None
    structural_ok = bool(
        not protective
        and date_confirmed
        and listing_shell_seen
    )
    if pagination_urls:
        navigation_state = "pagination_observed"
    elif structural_ok:
        navigation_state = "no_navigation_observed"
    else:
        navigation_state = "structure_unavailable"
    return ListingResult(
        listing_date=listing_date,
        structural_ok=structural_ok,
        rows=rows,
        case_urls=_unique(case_urls),
        doc_urls=_unique(doc_urls),
        pagination_urls=pagination_urls,
        navigation_state=navigation_state,
        protective=protective,
        explicit_empty=explicit_empty,
        page_text=page_text,
        listing_shell_seen=listing_shell_seen,
        listing_table_seen=parser.listing_table_seen,
        control_date_confirmed=control_date_confirmed,
        content_date_confirmed=content_date_confirmed,
        date_confirmed=date_confirmed,
        empty_evidence_code=empty_evidence_code,
        case_row_count=case_row_count,
    )


def classify_listing(http_status: int, result: ListingResult) -> str:
    """Classify transport/protection/empty outcomes without conflating them."""

    if http_status in {401, 403, 407, 429, 451}:
        return "blocked"
    if http_status == 408 or http_status >= 500:
        return "retryable_error"
    if http_status < 200 or http_status >= 300:
        return "http_error"
    if result.protective:
        return "blocked"
    if not result.structural_ok:
        return "invalid_structure"
    if result.case_row_count or result.case_urls or result.doc_urls:
        return "success_nonempty"
    if result.explicit_empty:
        return "success_empty"
    return "ambiguous_empty"


def parse_source_page(html: str, base_url: str, kind: str) -> SourcePage:
    """Parse a case card or a document page from an official court site."""

    if kind not in {"card", "doc"}:
        raise ValueError("kind must be 'card' or 'doc'")
    parser = _parse(html)
    all_text = _clean_text(" ".join(parser.all_text))
    folded = all_text.casefold()
    protective = any(marker in folded for marker in _PROTECTIVE_MARKERS)
    doc_urls = _unique(
        [
            _absolute_url(base_url, anchor.href)
            for anchor in parser.anchors
            if anchor.href
            and _same_origin(base_url, _absolute_url(base_url, anchor.href))
            and _operation(_absolute_url(base_url, anchor.href)) == "doc"
        ]
    )
    if protective:
        return SourcePage(kind=kind, status="blocked", doc_urls=doc_urls, protective=True)
    if kind == "card":
        return SourcePage(
            kind=kind,
            status="card",
            text=all_text,
            doc_urls=doc_urls,
            structural_ok=bool(doc_urls or all_text),
        )

    fragments = parser.content_text or parser.fallback_text
    text = _clean_text(" ".join(fragments))
    status = "full_text" if len(text) >= 40 else "no_text"
    return SourcePage(
        kind=kind,
        status=status,
        text=text,
        doc_urls=doc_urls,
        structural_ok=bool(text),
    )
