"""Безопасный browser handoff: интерактивное действие выполняет человек."""

from __future__ import annotations

from .base import AdapterRequest, AdapterResult


class BrowserHandoffAdapter:
    def acquire(self, request: AdapterRequest) -> AdapterResult:
        return AdapterResult(
            status="interactive_required",
            transport="browser",
            origin_url=request.locator,
            error_code="manual_browser_verification_required",
            error_detail=(
                "Откройте официальный адрес в Chrome/Chromium, выполните интерактивную проверку "
                "самостоятельно и импортируйте полученный официальный файл."
            ),
        )
