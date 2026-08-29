"""Ограниченная прямая загрузка без обхода интерактивных защит."""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .base import AdapterRequest, AdapterResult


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

        if status >= 400:
            return AdapterResult(
                status="unavailable",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="unexpected_http_status",
            )
        if not content:
            return AdapterResult(
                status="invalid_response",
                transport="direct_http",
                origin_url=origin_url,
                http_status=status,
                response_headers=headers,
                error_code="empty_response",
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
            )
        return AdapterResult(
            status="retrieved",
            transport="direct_http",
            origin_url=origin_url,
            raw_bytes=content,
            content_type=headers.get("Content-Type") or headers.get("content-type"),
            http_status=status,
            response_headers=headers,
        )
