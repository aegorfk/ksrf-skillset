from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional
from urllib.parse import urlparse


AUTHORITY_CLASSES = {
    "official_primary",
    "official_derivative",
    "discovery_only",
    "user_supplied_unverified",
}
RETRIEVAL_STATUSES = {
    "retrieved",
    "not_found",
    "unavailable",
    "interactive_required",
    "invalid_response",
    "conflict",
}


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _domain_matches(host: str, configured: str) -> bool:
    host = host.lower().rstrip(".")
    configured = configured.lower().rstrip(".")
    if configured.startswith("*."):
        suffix = configured[1:]
        return host.endswith(suffix) and host != suffix[1:]
    return host == configured


class SourceRegistry:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.schema_version = str(payload.get("schema_version") or "")
        sources = payload.get("sources")
        if not self.schema_version or not isinstance(sources, list):
            raise ValueError("source registry requires schema_version and sources[]")
        self._sources: Dict[str, Dict[str, Any]] = {}
        for item in sources:
            if not isinstance(item, dict):
                raise ValueError("source registry entries must be objects")
            source_id = str(item.get("source_id") or "")
            authority_class = str(item.get("authority_class") or "")
            if not source_id or source_id in self._sources:
                raise ValueError(f"missing or duplicate source_id: {source_id!r}")
            if authority_class not in AUTHORITY_CLASSES:
                raise ValueError(f"invalid authority class for {source_id}: {authority_class!r}")
            statuses = set(item.get("result_statuses") or [])
            if not RETRIEVAL_STATUSES.issubset(statuses):
                raise ValueError(f"source {source_id} does not declare all retrieval statuses")
            self._sources[source_id] = dict(item)

    @classmethod
    def load(cls, path: Path) -> "SourceRegistry":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def load_default(cls) -> "SourceRegistry":
        return cls.load(_repository_root() / "configs" / "ksrf_official_sources.v1.json")

    def get(self, source_id: str) -> Dict[str, Any]:
        try:
            return dict(self._sources[source_id])
        except KeyError as exc:
            raise KeyError(f"unknown source_id: {source_id}") from exc

    def all(self) -> list[Dict[str, Any]]:
        return [dict(item) for item in self._sources.values()]

    def resolve_url(self, url: str) -> Optional[Dict[str, Any]]:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            return None
        candidates = []
        for item in self._sources.values():
            if any(_domain_matches(host, str(domain)) for domain in item.get("domains") or []):
                candidates.append(item)
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: max((len(str(domain)) for domain in item.get("domains") or []), default=0),
            reverse=True,
        )
        return dict(candidates[0])


def load_norm_version_provider_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    config_path = path or (_repository_root() / "configs" / "ksrf_norm_version_providers.v1.json")
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not payload.get("schema_version") or not isinstance(payload.get("providers"), list):
        raise ValueError("provider registry requires schema_version and providers[]")
    seen = set()
    for provider in payload["providers"]:
        provider_id = str(provider.get("provider_id") or "")
        if not provider_id or provider_id in seen:
            raise ValueError(f"missing or duplicate provider_id: {provider_id!r}")
        seen.add(provider_id)
        if provider.get("authority_class") != "discovery_only":
            raise ValueError("norm-version enrichment providers must remain discovery_only")
        if provider.get("official_anchor_required") is not True:
            raise ValueError("provider registry must require official anchors")
    return payload
