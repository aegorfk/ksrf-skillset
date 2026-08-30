#!/usr/bin/env python3
"""Validate the structural readiness of a KSRF authority ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse


ALLOWED_MODES = {"research", "drafting", "audit"}
ALLOWED_RELATIONS = {"supports", "weakens", "distinguishes", "blocks"}
ALLOWED_ROLES = {
    "constitutional_doctrine",
    "judicial_meaning",
    "application_evidence",
    "historical_line",
    "adverse_authority",
    "remedy_model",
}
ALLOWED_VERIFICATION_STATUSES = {
    "candidate",
    "full_text_opened",
    "official_verified",
    "rejected",
    "superseded",
}
ALLOWED_HUMAN_STATUSES = {"pending", "approved", "revise", "rejected"}
ALLOWED_QUERY_STATUSES = {"completed", "no_results", "failed", "unavailable"}
SENSITIVE_QUERY_KEYS = {
    "t",
    "token",
    "access_token",
    "auth",
    "authorization",
    "key",
    "api_key",
}


class Validator:
    def __init__(self, *, public: bool, require_drafting: bool) -> None:
        self.public = public
        self.require_drafting = require_drafting
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warn(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")

    def require_object(self, value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            self.error(path, "expected object")
            return {}
        return value

    def require_list(self, value: Any, path: str) -> list[Any]:
        if not isinstance(value, list):
            self.error(path, "expected array")
            return []
        return value

    def require_string(
        self, value: Any, path: str, *, allow_empty: bool = False
    ) -> str:
        if not isinstance(value, str):
            self.error(path, "expected string")
            return ""
        if not allow_empty and not value.strip():
            self.error(path, "must not be empty")
        return value

    def require_bool(self, value: Any, path: str) -> bool:
        if not isinstance(value, bool):
            self.error(path, "expected boolean")
            return False
        return value

    def validate(self, data: Any) -> None:
        root = self.require_object(data, "$")
        self.require_string(root.get("schema_version"), "$.schema_version")
        self.require_string(root.get("case_id"), "$.case_id")

        mode = self.require_string(root.get("mode"), "$.mode")
        if mode and mode not in ALLOWED_MODES:
            self.error("$.mode", f"unknown mode {mode!r}")

        self.validate_query_profile(root.get("query_profile"))
        query_ids = self.validate_query_log(root.get("query_log"), mode)
        authority_ids, has_drafting_ready = self.validate_authorities(
            root.get("authorities")
        )
        self.validate_adverse_pass(
            root.get("adverse_pass"), query_ids, authority_ids, has_drafting_ready
        )
        self.validate_drafting_blocks(root.get("drafting_blocks"), authority_ids)
        self.validate_human_approval(root.get("human_approval"))

    def validate_query_profile(self, value: Any) -> None:
        profile = self.require_object(value, "$.query_profile")
        required_strings = (
            "hypothesis_id",
            "challenged_norm",
            "norm_version",
            "applied_meaning",
            "harm_mechanism",
            "desired_remedy",
        )
        for field in required_strings:
            self.require_string(profile.get(field), f"$.query_profile.{field}")
        for field in (
            "constitutional_rights",
            "judicial_application_evidence_ids",
            "unknowns",
        ):
            items = self.require_list(profile.get(field), f"$.query_profile.{field}")
            for index, item in enumerate(items):
                self.require_string(item, f"$.query_profile.{field}[{index}]")

    def validate_query_log(self, value: Any, mode: str) -> set[str]:
        queries = self.require_list(value, "$.query_log")
        if mode in {"research", "drafting"} and not queries:
            self.error("$.query_log", f"must not be empty in {mode!r} mode")

        seen: set[str] = set()
        for index, item in enumerate(queries):
            path = f"$.query_log[{index}]"
            query = self.require_object(item, path)
            query_id = self.require_string(query.get("query_id"), f"{path}.query_id")
            if query_id:
                if query_id in seen:
                    self.error(f"{path}.query_id", f"duplicate id {query_id!r}")
                seen.add(query_id)
            for field in ("lane", "tool", "query", "executed_at", "coverage_note"):
                self.require_string(query.get(field), f"{path}.{field}")
            status = self.require_string(query.get("status"), f"{path}.status")
            if status and status not in ALLOWED_QUERY_STATUSES:
                self.error(f"{path}.status", f"unknown status {status!r}")
            result_ids = self.require_list(query.get("result_ids"), f"{path}.result_ids")
            for result_index, result_id in enumerate(result_ids):
                self.require_string(
                    result_id, f"{path}.result_ids[{result_index}]"
                )
        return seen

    def validate_authorities(self, value: Any) -> tuple[set[str], bool]:
        authorities = self.require_list(value, "$.authorities")
        seen: set[str] = set()
        has_drafting_ready = False

        for index, item in enumerate(authorities):
            path = f"$.authorities[{index}]"
            authority = self.require_object(item, path)
            authority_id = self.require_string(
                authority.get("authority_id"), f"{path}.authority_id"
            )
            if authority_id:
                if authority_id in seen:
                    self.error(
                        f"{path}.authority_id", f"duplicate id {authority_id!r}"
                    )
                seen.add(authority_id)

            hypothesis_ids = self.require_list(
                authority.get("hypothesis_ids"), f"{path}.hypothesis_ids"
            )
            if not hypothesis_ids:
                self.error(f"{path}.hypothesis_ids", "must not be empty")
            for hypothesis_index, hypothesis_id in enumerate(hypothesis_ids):
                self.require_string(
                    hypothesis_id,
                    f"{path}.hypothesis_ids[{hypothesis_index}]",
                )

            for field in ("court", "act_type", "date", "number", "title"):
                self.require_string(authority.get(field), f"{path}.{field}")
            case_number = authority.get("case_number")
            if case_number is not None:
                self.require_string(case_number, f"{path}.case_number")

            roles = self.require_list(authority.get("roles"), f"{path}.roles")
            if not roles:
                self.error(f"{path}.roles", "must not be empty")
            for role_index, role in enumerate(roles):
                role_path = f"{path}.roles[{role_index}]"
                role_value = self.require_string(role, role_path)
                if role_value and role_value not in ALLOWED_ROLES:
                    self.error(role_path, f"unknown role {role_value!r}")

            relation = self.require_string(
                authority.get("relation"), f"{path}.relation"
            )
            if relation and relation not in ALLOWED_RELATIONS:
                self.error(f"{path}.relation", f"unknown relation {relation!r}")
            self.require_string(authority.get("proposition"), f"{path}.proposition")
            self.require_string(
                authority.get("position_summary"), f"{path}.position_summary"
            )

            source = self.validate_source(authority.get("source"), f"{path}.source")
            quote = self.validate_quote(
                authority.get("quote"), f"{path}.quote", source
            )
            transfer = self.validate_transfer(
                authority.get("transfer"), f"{path}.transfer"
            )
            transfer_limit = transfer.get("limit")

            risks = self.require_list(authority.get("risks"), f"{path}.risks")
            for risk_index, risk in enumerate(risks):
                self.require_string(risk, f"{path}.risks[{risk_index}]")

            verification_status = self.require_string(
                authority.get("verification_status"),
                f"{path}.verification_status",
            )
            if (
                verification_status
                and verification_status not in ALLOWED_VERIFICATION_STATUSES
            ):
                self.error(
                    f"{path}.verification_status",
                    f"unknown status {verification_status!r}",
                )
            if verification_status == "official_verified" and not source.get(
                "official_verified", False
            ):
                self.error(
                    f"{path}.source.official_verified",
                    "must be true for official_verified status",
                )

            drafting_ready = self.require_bool(
                authority.get("drafting_ready"), f"{path}.drafting_ready"
            )
            has_drafting_ready = has_drafting_ready or drafting_ready
            if drafting_ready:
                if verification_status not in {
                    "full_text_opened",
                    "official_verified",
                }:
                    self.error(
                        f"{path}.verification_status",
                        "drafting-ready authority needs opened full text",
                    )
                if not source.get("full_text_opened", False):
                    self.error(
                        f"{path}.source.full_text_opened",
                        "must be true for drafting-ready authority",
                    )
                if not isinstance(transfer_limit, str) or not transfer_limit.strip():
                    self.error(
                        f"{path}.transfer.limit",
                        "must explain the transfer limit before drafting",
                    )
                if quote.get("key_quote", False):
                    if not source.get("official_verified", False):
                        self.error(
                            f"{path}.source.official_verified",
                            "key quote requires official verification",
                        )
                    if not quote.get("verified_against_official", False):
                        self.error(
                            f"{path}.quote.verified_against_official",
                            "key quote must be checked against official source",
                        )

        return seen, has_drafting_ready

    def validate_source(self, value: Any, path: str) -> dict[str, Any]:
        source = self.require_object(value, path)
        for field in ("casuslegal_url", "official_url"):
            url = source.get(field)
            if url is not None:
                url_value = self.require_string(url, f"{path}.{field}")
                if self.public and url_value and self.has_sensitive_query(url_value):
                    self.error(
                        f"{path}.{field}",
                        "public ledger must not contain access/query token",
                    )
        self.require_bool(source.get("full_text_opened"), f"{path}.full_text_opened")
        self.require_bool(source.get("official_verified"), f"{path}.official_verified")
        self.require_string(source.get("checked_at"), f"{path}.checked_at")
        return source

    def validate_quote(
        self, value: Any, path: str, source: dict[str, Any]
    ) -> dict[str, Any]:
        quote = self.require_object(value, path)
        text = self.require_string(quote.get("text"), f"{path}.text", allow_empty=True)
        locator = quote.get("locator")
        if locator is not None:
            self.require_string(locator, f"{path}.locator")
        key_quote = self.require_bool(quote.get("key_quote"), f"{path}.key_quote")
        self.require_bool(
            quote.get("verified_against_official"),
            f"{path}.verified_against_official",
        )
        if text.strip():
            if not isinstance(locator, str) or not locator.strip():
                self.error(f"{path}.locator", "quote text requires a locator")
            if not source.get("full_text_opened", False):
                self.error(
                    f"{path}.text", "quote text requires opened full text"
                )
        if key_quote and not text.strip():
            self.error(f"{path}.text", "key quote must not be empty")
        return quote

    def validate_transfer(self, value: Any, path: str) -> dict[str, Any]:
        transfer = self.require_object(value, path)
        for field in ("matches", "differences"):
            items = self.require_list(transfer.get(field), f"{path}.{field}")
            for index, item in enumerate(items):
                self.require_string(item, f"{path}.{field}[{index}]")
        for field in (
            "norm_fit",
            "norm_version_fit",
            "temporal_fit",
            "remedy_fit",
            "limit",
        ):
            self.require_string(transfer.get(field), f"{path}.{field}")
        return transfer

    def validate_adverse_pass(
        self,
        value: Any,
        query_ids: set[str],
        authority_ids: set[str],
        has_drafting_ready: bool,
    ) -> None:
        adverse = self.require_object(value, "$.adverse_pass")
        performed = self.require_bool(
            adverse.get("performed"), "$.adverse_pass.performed"
        )
        adverse_query_ids = self.require_list(
            adverse.get("query_ids"), "$.adverse_pass.query_ids"
        )
        adverse_authority_ids = self.require_list(
            adverse.get("authority_ids"), "$.adverse_pass.authority_ids"
        )
        no_result_note = adverse.get("no_result_note")
        if no_result_note is not None:
            self.require_string(
                no_result_note,
                "$.adverse_pass.no_result_note",
                allow_empty=True,
            )

        for index, query_id in enumerate(adverse_query_ids):
            query_value = self.require_string(
                query_id, f"$.adverse_pass.query_ids[{index}]"
            )
            if query_value and query_value not in query_ids:
                self.error(
                    f"$.adverse_pass.query_ids[{index}]",
                    f"unknown query id {query_value!r}",
                )
        for index, authority_id in enumerate(adverse_authority_ids):
            authority_value = self.require_string(
                authority_id, f"$.adverse_pass.authority_ids[{index}]"
            )
            if authority_value and authority_value not in authority_ids:
                self.error(
                    f"$.adverse_pass.authority_ids[{index}]",
                    f"unknown authority id {authority_value!r}",
                )

        if performed and not adverse_query_ids:
            self.error(
                "$.adverse_pass.query_ids",
                "performed adverse pass must reference at least one query",
            )
        if performed and not adverse_authority_ids:
            if not isinstance(no_result_note, str) or not no_result_note.strip():
                self.error(
                    "$.adverse_pass.no_result_note",
                    "required when adverse search found no authority",
                )
        if has_drafting_ready and not performed:
            self.error(
                "$.adverse_pass.performed",
                "drafting-ready authorities require a completed adverse pass",
            )

    def validate_drafting_blocks(
        self, value: Any, authority_ids: set[str]
    ) -> None:
        blocks = self.require_list(value, "$.drafting_blocks")
        if self.require_drafting and not blocks:
            self.error(
                "$.drafting_blocks",
                "at least one drafting block is required",
            )
        seen: set[str] = set()
        for index, item in enumerate(blocks):
            path = f"$.drafting_blocks[{index}]"
            block = self.require_object(item, path)
            block_id = self.require_string(block.get("block_id"), f"{path}.block_id")
            if block_id:
                if block_id in seen:
                    self.error(f"{path}.block_id", f"duplicate id {block_id!r}")
                seen.add(block_id)
            for field in (
                "hypothesis_id",
                "thesis",
                "applicability_bridge",
                "conclusion",
                "adverse_response",
                "status",
            ):
                self.require_string(block.get(field), f"{path}.{field}")
            ids = self.require_list(block.get("authority_ids"), f"{path}.authority_ids")
            if not ids:
                self.error(f"{path}.authority_ids", "must not be empty")
            for authority_index, authority_id in enumerate(ids):
                authority_value = self.require_string(
                    authority_id,
                    f"{path}.authority_ids[{authority_index}]",
                )
                if authority_value and authority_value not in authority_ids:
                    self.error(
                        f"{path}.authority_ids[{authority_index}]",
                        f"unknown authority id {authority_value!r}",
                    )

    def validate_human_approval(self, value: Any) -> None:
        approval = self.require_object(value, "$.human_approval")
        status = self.require_string(
            approval.get("status"), "$.human_approval.status"
        )
        if status and status not in ALLOWED_HUMAN_STATUSES:
            self.error(
                "$.human_approval.status", f"unknown status {status!r}"
            )
        for field in ("approved_by", "reason"):
            field_value = approval.get(field)
            if field_value is not None:
                self.require_string(field_value, f"$.human_approval.{field}")
        if status == "approved":
            for field in ("approved_by", "reason"):
                field_value = approval.get(field)
                if not isinstance(field_value, str) or not field_value.strip():
                    self.error(
                        f"$.human_approval.{field}",
                        "required when status is approved",
                    )
        if self.require_drafting and status != "approved":
            self.error(
                "$.human_approval.status",
                "must be approved when --require-drafting is used",
            )

    @staticmethod
    def has_sensitive_query(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        return any(
            key.lower() in SENSITIVE_QUERY_KEYS
            for key, _ in parse_qsl(parsed.query, keep_blank_values=True)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a KSRF practice authority ledger JSON file."
    )
    parser.add_argument("path", type=Path, help="Path to authority ledger JSON")
    parser.add_argument(
        "--public",
        action="store_true",
        help="Reject access/query tokens in URLs",
    )
    parser.add_argument(
        "--require-drafting",
        action="store_true",
        help="Require human approval and at least one drafting block",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.path}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: cannot read {args.path}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            file=sys.stderr,
        )
        return 2

    validator = Validator(
        public=args.public,
        require_drafting=args.require_drafting,
    )
    validator.validate(data)

    for warning in validator.warnings:
        print(f"WARNING: {warning}")
    if validator.errors:
        for error in validator.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"Authority ledger validation failed: {len(validator.errors)} error(s).",
            file=sys.stderr,
        )
        return 1

    authorities = data.get("authorities", []) if isinstance(data, dict) else []
    print(
        "Authority ledger is structurally valid "
        f"({len(authorities)} authority record(s))."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
