from __future__ import annotations

import mimetypes
from pathlib import Path

from .base import AdapterRequest, AdapterResult, SourceAdapter


class ManualImportAdapter(SourceAdapter):
    adapter_id = "manual-import-v1"

    def acquire(self, request: AdapterRequest) -> AdapterResult:
        path = Path(request.locator).expanduser()
        if not path.exists() or not path.is_file():
            return AdapterResult(
                status="not_found",
                transport="manual_import",
                terminal_rule_verified=True,
                error_code="file_not_found",
            )
        maximum = int(request.metadata.get("max_bytes") or 100 * 1024 * 1024)
        try:
            size = path.stat().st_size
            if size <= 0:
                return AdapterResult(
                    status="invalid_response",
                    transport="manual_import",
                    error_code="empty_file",
                )
            if size > maximum:
                return AdapterResult(
                    status="invalid_response",
                    transport="manual_import",
                    error_code="file_too_large",
                    error_detail=f"{size} > {maximum}",
                )
            content = path.read_bytes()
        except OSError as exc:
            return AdapterResult(
                status="unavailable",
                transport="manual_import",
                error_code="file_read_error",
                error_detail=str(exc),
            )
        return AdapterResult(
            status="retrieved",
            transport="manual_import",
            raw_bytes=content,
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            terminal_rule_verified=True,
        )
