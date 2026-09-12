#!/usr/bin/env python3
"""Retain lexical research candidates; never infer a court holding or speaker."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


MARKERS = {
    "proportionality": r"proportionnalit[eé]|proporzionalit[aà]|Verhältnismäßigkeit|juicio de proporcionalidad|proportionality test",
    "equality_comparator": r"diff[eé]rence de traitement|disparit[aà] di trattamento|Vergleichsgruppe|t[eé]rmino de comparaci[oó]n|similarly situated",
    "legitimate_expectations": r"confiance l[eé]gitime|legittimo affidamento|Vertrauensschutz|confianza leg[ií]tima|legitimate expectation",
    "legislative_discretion": r"marge d.appr[eé]ciation|discrezionalit[aà] del legislatore|Gestaltungsspielraum|libertad de configuraci[oó]n|legislative discretion",
    "temporal_effect": r"effets de la d[eé]claration|effetti temporali|Fortgeltung|efectos temporales|prospective effect",
    "minimum_protection": r"garanties l[eé]gales|nucleo (?:essenziale|irriducibile)|Existenzminimum|contenido esencial|minimum core",
    "cumulative_effect": r"effets cumul[eé]s|protrarsi|Gesamtbetrachtung|efecto acumulativo|cumulative effect",
}
PATTERNS = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in MARKERS.items()}
SCHEMA = """
CREATE TABLE IF NOT EXISTS processed (
 document_id TEXT, source_version TEXT, extractor_sha256 TEXT, processed_at TEXT,
 PRIMARY KEY(document_id,source_version,extractor_sha256)
);
CREATE TABLE IF NOT EXISTS candidates (
 candidate_id TEXT PRIMARY KEY, document_id TEXT, method_hint TEXT, data TEXT
);
CREATE TABLE IF NOT EXISTS rejected (
 document_id TEXT, source_version TEXT, extractor_sha256 TEXT,
 status TEXT NOT NULL, reason TEXT NOT NULL, rejected_at TEXT NOT NULL,
 PRIMARY KEY(document_id,source_version,extractor_sha256)
);
CREATE TABLE IF NOT EXISTS runs (
 id INTEGER PRIMARY KEY, finished_at TEXT, data TEXT
);
"""


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def source_version(doc):
    return sha(json.dumps(doc, ensure_ascii=False, sort_keys=True))


def validate_document(doc):
    if not isinstance(doc, dict):
        raise ValueError("Ожидалась карточка полного акта")
    for key in ("id", "court", "text", "source_url", "raw_sha256"):
        if not isinstance(doc.get(key), str) or not doc[key].strip():
            raise ValueError(f"Отсутствует строковое поле {key}")
    if doc.get("source_role") != "decision" or len(doc["text"].strip()) < 80:
        raise ValueError("Кандидаты извлекаются только из заявленного полного судебного текста")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", doc["raw_sha256"]):
        raise ValueError("Неверный хеш исходника")
    if not doc["source_url"].startswith("https://"):
        raise ValueError("Для исходника требуется HTTPS-ссылка")


def candidates(doc, extractor_sha256):
    validate_document(doc)
    text = doc["text"]
    text_hash = sha(text)
    version = source_version(doc)
    for family, pattern in PATTERNS.items():
        # One occurrence per family/document is a navigation sample, not a count
        # of all argumentative moves or evidence that this move was accepted.
        match = pattern.search(text)
        if not match:
            continue
        start, end = max(0, match.start() - 180), min(len(text), match.end() + 260)
        identity = sha("|".join([doc["id"], version, extractor_sha256, family, str(start)]))
        yield {
            "candidate_id": identity, "document_id": doc["id"], "court": doc["court"],
            "number": doc.get("number"), "date": doc.get("date"), "language": doc.get("language"),
            "source_url": doc["source_url"], "source_provider": doc.get("source_provider", "unspecified"),
            "raw_sha256": doc["raw_sha256"], "raw_hash_verified_by_extractor": False,
            "source_version": version,
            "text_sha256": text_hash, "extractor_sha256": extractor_sha256,
            "method_hint": family, "matched_marker": match.group(0),
            "quote_original": text[start:end], "char_start": start, "char_end": end,
            "status": "discovery_only", "speaker": "unverified", "court_adoption": "unverified",
            "holding": None, "legal_support_verified": False,
            "sampling": "first_marker_per_family_per_document", "review_required": "Read full context, speaker and court treatment before extracting a method.",
        }


def _read_only(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=20)
    connection.execute("PRAGMA query_only=ON")
    return connection


def candidate_counts(connection):
    versions = connection.execute("SELECT count(*) FROM candidates").fetchone()[0]
    unique = connection.execute("""
        SELECT count(*) FROM (
            SELECT DISTINCT document_id, method_hint,
                json_extract(data, '$.text_sha256'),
                json_extract(data, '$.char_start'), json_extract(data, '$.char_end')
            FROM candidates
        )
    """).fetchone()[0]
    return {
        "candidate_versions": versions, "unique_passage_candidates": unique,
        "candidate_count_note": "Версии кандидатов сохраняются при изменении источника или извлекателя; уникальные фрагменты считаются по акту, хешу текста, смещениям и маркеру, а не по числу версий.",
    }


def foreign_documents(path, known, extractor_hash):
    path = path.expanduser().resolve(strict=True)
    # This adapter is deliberately specific. HUDOC must use its query service.
    if path.name != "library.sqlite3" or any("hudoc" in part.casefold() or "еспч" in part.casefold() for part in path.parts):
        raise ValueError("Нужен library.sqlite3 из foreign_courts; живой HUDOC здесь не открывается")
    with closing(_read_only(path)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(documents)")}
        required = {"id", "court", "date", "number", "title", "text", "language", "data", "content_hash"}
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if columns != required or not {"versions", "imports", "documents_fts"} <= tables:
            raise ValueError("Файл не соответствует формату foreign_courts")
        # Read identities first and release the connection before processing.
        identities = connection.execute("SELECT id,content_hash FROM documents ORDER BY id").fetchall()
    pending = [(identity, version) for identity, version in identities if (identity, version, extractor_hash) not in known]
    for offset in range(0, len(pending), 40):
        batch = pending[offset:offset + 40]
        expected = dict(batch)
        with closing(_read_only(path)) as connection:
            rows = connection.execute("SELECT id,content_hash,data FROM documents WHERE id IN (" + ",".join("?" for _ in batch) + ") ORDER BY id", list(expected)).fetchall()
        for identity, version, raw in rows:
            yield json.loads(raw), version


def jsonl_documents(path):
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    doc = json.loads(line)
                except ValueError as exc:
                    raise ValueError(f"Неверный JSON в строке {number}") from exc
                yield doc, source_version(doc)


def run(output_dir, *, jsonl=None, foreign_library=None, limit=0):
    if limit < 0 or bool(jsonl) == bool(foreign_library):
        raise ValueError("Укажите один источник и неотрицательный предел")
    input_path = Path(jsonl or foreign_library).expanduser().resolve(strict=True)
    output_dir = Path(output_dir).expanduser()
    if output_dir.is_symlink():
        raise ValueError("Каталог очереди не должен быть символической ссылкой")
    output_dir = output_dir.resolve()
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError("Для очереди требуется отдельный каталог")
    queue_path = output_dir / "argument-candidates.sqlite3"
    if queue_path.is_symlink():
        raise ValueError("Файл очереди не должен быть символической ссылкой")
    if input_path == queue_path or (queue_path.exists() and queue_path.samefile(input_path)):
        raise ValueError("Очередь должна находиться отдельно от входа")
    if queue_path.exists() and not queue_path.is_file():
        raise ValueError("Очередь должна быть обычным файлом SQLite")
    # All input/output alias checks precede the first filesystem or SQL write.
    output_dir.mkdir(parents=True, exist_ok=True)
    extractor_hash = sha(Path(__file__).read_bytes())
    result = {"processed": 0, "skipped": 0, "candidates_added": 0, "rejected": 0, "rejected_skipped": 0,
              "errors": [], "extractor_sha256": extractor_hash, "status": "discovery_only",
              "full_corpus_semantic_review": False, "limit": limit}
    with closing(sqlite3.connect(queue_path, timeout=30)) as queue:
        queue.executescript(SCHEMA)
        known = set(queue.execute("SELECT document_id,source_version,extractor_sha256 FROM processed"))
        known_rejected = set(queue.execute("SELECT document_id,source_version,extractor_sha256 FROM rejected"))
        stream = foreign_documents(input_path, known, extractor_hash) if foreign_library else jsonl_documents(input_path)
        # Each document is committed atomically with its processing receipt.
        # A crash cannot retain a receipt without retaining its candidate rows.
        for doc, version in stream:
            if limit and result["processed"] + result["rejected"] >= limit:
                break
            identity = doc.get("id", "") if isinstance(doc, dict) else ""
            key = (identity, version, extractor_hash)
            if key in known:
                result["skipped"] += 1
                continue
            if key in known_rejected:
                result["rejected_skipped"] += 1
                continue
            try:
                rows = list(candidates(doc, extractor_hash))
            except ValueError as exc:
                result["rejected"] += 1
                if len(result["errors"]) < 20:
                    result["errors"].append({"document_id": identity, "error": str(exc)})
                with queue:
                    queue.execute("INSERT OR IGNORE INTO rejected VALUES(?,?,?,?,?,?)",
                                  (*key, "rejected", str(exc), stamp()))
                known_rejected.add(key)
                continue
            with queue:
                for candidate in rows:
                    cursor = queue.execute("INSERT OR IGNORE INTO candidates VALUES(?,?,?,?)", (candidate["candidate_id"], identity, candidate["method_hint"], json.dumps(candidate, ensure_ascii=False)))
                    result["candidates_added"] += cursor.rowcount
                queue.execute("INSERT OR IGNORE INTO processed VALUES(?,?,?,?)", (*key, stamp()))
            known.add(key)
            result["processed"] += 1
        result.update(candidate_counts(queue))
        result["queue_total"] = result["candidate_versions"]
        result["rejected_versions_total"] = queue.execute("SELECT count(*) FROM rejected").fetchone()[0]
        with queue:
            queue.execute("INSERT INTO runs(finished_at,data) VALUES(?,?)", (stamp(), json.dumps(result, ensure_ascii=False)))
    return result


def report(output_dir):
    path = Path(output_dir).expanduser().resolve() / "argument-candidates.sqlite3"
    with closing(_read_only(path)) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = candidate_counts(connection)
        return {**counts, "candidates": counts["candidate_versions"],
                "processed_versions": connection.execute("SELECT count(*) FROM processed").fetchone()[0],
                "rejected_versions": connection.execute("SELECT count(*) FROM rejected").fetchone()[0] if "rejected" in tables else 0,
                "by_method_hint": dict(connection.execute("SELECT method_hint,count(*) FROM candidates GROUP BY method_hint")),
                "status": "discovery_only", "full_corpus_semantic_review": False}


def main():
    parser = argparse.ArgumentParser(description="Выделить исследовательские кандидаты из полных актов; совпадение не является правовой позицией")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--jsonl", type=Path, help="JSONL с полными карточками актов")
    source.add_argument("--foreign-library", type=Path, help="Только library.sqlite3 формата foreign_courts")
    parser.add_argument("--output-dir", required=True, type=Path, help="Отдельная папка исследовательской очереди")
    parser.add_argument("--limit", type=int, default=0, help="Предел новых версий за запуск; 0 — все доступные")
    parser.add_argument("--report", action="store_true", help="Только прочитать состояние очереди")
    args = parser.parse_args()
    if args.report and (args.jsonl or args.foreign_library):
        parser.error("--report не принимает источник")
    try:
        result = report(args.output_dir) if args.report else run(args.output_dir, jsonl=args.jsonl, foreign_library=args.foreign_library, limit=args.limit)
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f"Извлечение не выполнено: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("rejected") else 0


if __name__ == "__main__":
    raise SystemExit(main())
