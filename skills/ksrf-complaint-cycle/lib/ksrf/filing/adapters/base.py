from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Mapping, Optional
from urllib.parse import parse_qsl, urlparse


_SECRET_QUERY_KEYS = {
    "api_key",
    "apikey",
    "auth",
    "key",
    "password",
    "secret",
    "session",
    "signature",
    "token",
}


@dataclass(frozen=True)
class AdapterRequest:
    source_id: str
    locator: str
    bounded_scope: Mapping[str, Any]
    max_attempts: int = 1
    timeout_seconds: float = 20.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id or not self.locator:
            raise ValueError("source_id and locator are required")
        parsed = urlparse(self.locator)
        if parsed.scheme in {"http", "https"}:
            query_keys = {key.lower() for key, _value in parse_qsl(parsed.query, keep_blank_values=True)}
            if query_keys.intersection(_SECRET_QUERY_KEYS):
                raise ValueError("secret-bearing source URL is not permitted")
        if not isinstance(self.bounded_scope, Mapping) or not self.bounded_scope:
            raise ValueError("bounded_scope must be a non-empty object")
        if not 1 <= int(self.max_attempts) <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if not 0 < float(self.timeout_seconds) <= 60:
            raise ValueError("timeout_seconds must be in (0, 60]")


@dataclass(frozen=True)
class AdapterResult:
    status: str
    transport: str
    origin_url: Optional[str] = None
    raw_bytes: Optional[bytes] = field(default=None, repr=False)
    extracted_bytes: Optional[bytes] = field(default=None, repr=False)
    content_type: Optional[str] = None
    http_status: Optional[int] = None
    response_headers: Mapping[str, str] = field(default_factory=dict)
    terminal_rule_verified: bool = False
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    transform_chain: tuple[Mapping[str, Any], ...] = ()
    fetched_at: Optional[str] = None
    attempt_count: int = 1
    discovery_transport: Optional[str] = None
    redirect_chain: tuple[str, ...] = ()
    derived_identity_checks: tuple[Mapping[str, Any], ...] = ()

    def with_attempt_count(self, count: int) -> "AdapterResult":
        return replace(self, attempt_count=count)


class SourceAdapter(ABC):
    adapter_id = "abstract"

    @abstractmethod
    def acquire(self, request: AdapterRequest) -> AdapterResult:
        """Perform one bounded attempt. CAPTCHA must return interactive_required."""


def interactive_required(*, transport: str, detail: str = "interactive control") -> AdapterResult:
    return AdapterResult(
        status="interactive_required",
        transport=transport,
        error_code="captcha_or_interactive_control",
        error_detail=detail,
    )
