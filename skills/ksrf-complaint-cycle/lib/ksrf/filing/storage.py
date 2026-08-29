from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional


_NAMESPACE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}:sha256:{sha256_bytes(canonical_json_bytes(value))}"


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(canonical_json_bytes(payload))
        handle.write(b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class ContentAddressedStore:
    """Immutable SHA-256 object store with verified reads."""

    def __init__(self, root: Path, namespace: str) -> None:
        if not _NAMESPACE_RE.fullmatch(namespace):
            raise ValueError(f"invalid storage namespace: {namespace!r}")
        self.root = Path(root).resolve()
        self.namespace = namespace
        self.objects_root = self.root / namespace / "objects" / "sha256"
        self.objects_root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, content: bytes) -> Dict[str, Any]:
        if not isinstance(content, bytes):
            raise TypeError("content must be bytes")
        digest = sha256_bytes(content)
        path = self.objects_root / digest[:2] / digest
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError("content-address collision or corrupted object")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        return {
            "sha256": digest,
            "size": len(content),
            "object_path": str(path.relative_to(self.root)),
        }

    def read_bytes(self, object_record: Mapping[str, Any]) -> bytes:
        digest = str(object_record.get("sha256") or "")
        path_value = str(object_record.get("object_path") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not path_value:
            raise ValueError("invalid content-addressed object record")
        path = (self.root / path_value).resolve()
        if self.root not in path.parents:
            raise ValueError("object path escapes storage root")
        content = path.read_bytes()
        if sha256_bytes(content) != digest:
            raise ValueError("stored object hash mismatch")
        return content


class AppendOnlyJsonlLedger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: Mapping[str, Any]) -> None:
        line = canonical_json_bytes(payload) + b"\n"
        with self.path.open("ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"non-object JSONL record at {self.path}:{line_number}")
                yield value

    def records(self) -> list[Dict[str, Any]]:
        return list(iter(self))

    def latest_by(self, key: str, value: Any) -> Optional[Dict[str, Any]]:
        latest = None
        for record in self:
            if record.get(key) == value:
                latest = record
        return latest


def count_by(records: Iterable[Mapping[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for record in records:
        label = str(record.get(key) if record.get(key) is not None else "unknown")
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))
