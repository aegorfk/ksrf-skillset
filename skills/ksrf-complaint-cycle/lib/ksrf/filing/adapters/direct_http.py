"""Ограниченная прямая загрузка без обхода интерактивных защит."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from urllib.parse import urlparse
from collections.abc import Callable
from typing import Any

from .base import AdapterRequest, AdapterResult


def _domain_matches(host: str, declared: str) -> bool:
    expected = declared.lower().strip()
    if expected.startswith("*."):
        suffix = expected[2:]
        return host == suffix or host.endswith(f".{suffix}")
    return host == expected


class DirectHttpAdapter:
    def __init__(self, *, opener: Callable[..., Any] | None = None) -> None:
        self._opener = opener or urllib.request.urlopen

    def acquire(self, request: AdapterRequest) -> AdapterResult:
        if not request.locator.lower().startswith(("http://", "https://")):
            return AdapterResult(
                status="invalid_response",
                transport="direct_http",
                error_code="unsupported_url_scheme",
            )
        maximum = int(request.metadata.get("max_bytes") or 25 * 1024 * 1024)
        http_request = urllib.request.Request(
            request.locator,
            headers={"User-Agent": "ksrf-filing-readiness/1.0 (+manual verification)"},
        )
        try:
            with self._opener(http_request, timeout=request.timeout_seconds) as response:
                status = int(getattr(response, "status", 200) or 200)
                content = response.read(maximum + 1)
                headers = {str(key): str(value) for key, value in response.headers.items()}
                origin_url = str(getattr(response, "url", request.locator) or request.locator)
        except urllib.error.HTTPError as exc:
            body = exc.read(256 * 1024) if hasattr(exc, "read") else b""
            lowered = body.lower()
            if exc.code == 403 and any(marker in lowered for marker in (b"captcha", b"recaptcha", b"cloudflare")):
                return AdapterResult(
                    status="interactive_required",
                    transport="direct_http",
                    origin_url=request.locator,
                    http_status=exc.code,
                    error_code="interactive_control",
                    error_detail="Официальный источник требует ручного браузерного действия.",
                )
            if exc.code in {404, 410}:
                return AdapterResult(
                    status="not_found",
                    transport="direct_http",
                    origin_url=request.locator,
                    http_status=exc.code,
                    terminal_rule_verified=bool(request.metadata.get("terminal_rule_verified")),
                    error_code="http_not_found",
                )
            return AdapterResult(
                status="unavailable",
                transport="direct_http",
                origin_url=request.locator,
                http_status=exc.code,
                error_code="http_error",
                error_detail=str(exc.reason),
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            return AdapterResult(
                status="unavailable",
                transport="direct_http",
                origin_url=request.locator,
                error_code="network_unavailable",
                error_detail=str(exc),
            )

        redirect_chain = tuple(dict.fromkeys((request.locator, origin_url)))
        final_host = (urlparse(origin_url).hostname or "").lower()
        allowed_domains = tuple(
            str(item).lower()
            for item in (request.metadata.get("allowed_domains") or [])
            if str(item).strip()
        )
        if not allowed_domains:
            initial_host = (urlparse(request.locator).hostname or "").lower()
            allowed_domains = (initial_host,) if initial_host else ()
        if not final_host or not any(_domain_matches(final_host, item) for item in allowed_domains):
            return AdapterResult(
                status="conflict",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="final_origin_registry_mismatch",
                error_detail="Конечный адрес после перенаправления не относится к выбранному официальному источнику.",
                redirect_chain=redirect_chain,
            )
        if status >= 400:
            return AdapterResult(
                status="unavailable",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="unexpected_http_status",
                redirect_chain=redirect_chain,
            )
        if not content:
            return AdapterResult(
                status="invalid_response",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="empty_response",
                redirect_chain=redirect_chain,
            )
        if len(content) > maximum:
            return AdapterResult(
                status="invalid_response",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="response_too_large",
                error_detail=f"> {maximum}",
                redirect_chain=redirect_chain,
            )
        lowered = content[:512_000].lower()
        if any(marker in lowered for marker in (b"captcha", b"recaptcha", b"verify you are human")):
            return AdapterResult(
                status="interactive_required",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="interactive_control",
                error_detail="Получена интерактивная проверка; автоматический обход запрещён.",
                redirect_chain=redirect_chain,
            )
        return AdapterResult(
            status="retrieved",
            transport="direct_http",
            origin_url=origin_url,
            raw_bytes=content,
            content_type=headers.get("Content-Type") or headers.get("content-type"),
            http_status=status,
            response_headers=headers,
            redirect_chain=redirect_chain,
        )
