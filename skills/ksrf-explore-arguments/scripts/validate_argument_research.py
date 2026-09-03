#!/usr/bin/env python3
"""Validate the minimal adaptive KSRF research artifact contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FINDING_FIELDS = {
    "finding_id",
    "case_id",
    "direction",
    "thesis",
    "source_anchor",
    "locator",
    "relation",
    "hypothesis_ids",
    "verification_status",
    "confidence",
    "limitations",
    "contains_sensitive_data",
}
FINDING_STRING_FIELDS = (
    "finding_id",
    "case_id",
    "direction",
    "thesis",
    "source_anchor",
)
HYPOTHESIS_FIELDS = {
    "hypothesis_id",
    "title",
    "status",
    "normative_mechanism",
    "constitutional_harm",
    "review_line",
    "supporting_finding_ids",
    "adverse_finding_ids",
    "falsifier",
    "fact_dispute_risk",
    "refusal_model",
    "primary_relief",
    "narrower_relief",
    "missing_materials",
}
HYPOTHESIS_STRING_FIELDS = (
    "hypothesis_id",
    "title",
    "normative_mechanism",
    "constitutional_harm",
    "review_line",
    "falsifier",
    "fact_dispute_risk",
    "refusal_model",
    "primary_relief",
    "narrower_relief",
)
PORTFOLIO_FIELDS = {
    "human_approval",
    "principal_hypothesis_id",
    "reserve_hypothesis_ids",
    "experimental_hypothesis_ids",
    "rejected_hypothesis_ids",
}
RELATIONS = {"supports", "weakens", "distinguishes", "blocks"}
VERIFICATION = {"candidate", "verified", "rejected", "superseded"}
CONFIDENCE = {"low", "medium", "high"}
HYPOTHESIS_STATUS = {"active", "promoted", "reserve", "experimental", "rejected"}
APPROVAL = {"pending", "approved", "revise", "rejected"}


def missing_fields(item: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(required - item.keys())


def diagnostic_identifier(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)[1:-1]


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_string_fields(
    item: dict[str, Any],
    fields: tuple[str, ...],
    *,
    path: str,
    errors: list[str],
) -> None:
    for field in fields:
        if field in item and not is_non_empty_string(item[field]):
            errors.append(f"{path}.{field} must be a non-empty string")


def validate_string_list(
    item: dict[str, Any],
    field: str,
    *,
    path: str,
    errors: list[str],
) -> None:
    value = item[field]
    if not isinstance(value, list):
        errors.append(f"{path}.{field} must be an array")
        return

    for index, entry in enumerate(value):
        if not is_non_empty_string(entry):
            errors.append(
                f"{path}.{field}[{index}] must be a non-empty string"
            )


def validated_id_set(
    item: dict[str, Any],
    field: str,
    *,
    path: str,
    errors: list[str],
) -> set[str]:
    value = item[field]
    if not isinstance(value, list):
        errors.append(f"{path}.{field} must be an array")
        return set()

    identifiers: set[str] = set()
    for index, identifier in enumerate(value):
        if not is_non_empty_string(identifier):
            errors.append(
                f"{path}.{field}[{index}] must be a non-empty string"
            )
            continue
        identifiers.add(identifier)
    return identifiers


def validate(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["root must be an object"]

    errors: list[str] = []
    case_id = payload.get("case_id")
    if "findings" not in payload:
        errors.append("root missing findings")
        findings: Any = []
    else:
        findings = payload["findings"]
    if "hypotheses" not in payload:
        errors.append("root missing hypotheses")
        hypotheses: Any = []
    else:
        hypotheses = payload["hypotheses"]
    portfolio_present = "portfolio" in payload
    if not portfolio_present:
        errors.append("root missing portfolio")
        portfolio: Any = {}
    else:
        portfolio = payload["portfolio"]

    if not isinstance(case_id, str) or not case_id.strip():
        errors.append("case_id must be a non-empty string")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        findings = []
    if not isinstance(hypotheses, list):
        errors.append("hypotheses must be an array")
        hypotheses = []
    if not isinstance(portfolio, dict):
        errors.append("portfolio must be an object")
        portfolio = {}
        portfolio_present = False

    finding_ids: set[str] = set()
    finding_references: list[tuple[int, set[str]]] = []
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"findings[{index}] must be an object")
            continue
        for field in missing_fields(finding, FINDING_FIELDS):
            errors.append(f"findings[{index}] missing {field}")
        validate_string_fields(
            finding,
            FINDING_STRING_FIELDS,
            path=f"findings[{index}]",
            errors=errors,
        )
        finding_id = finding.get("finding_id")
        if is_non_empty_string(finding_id):
            if finding_id in finding_ids:
                errors.append(
                    f"duplicate finding_id: {diagnostic_identifier(finding_id)}"
                )
            finding_ids.add(finding_id)
        finding_case_id = finding.get("case_id")
        if (
            is_non_empty_string(case_id)
            and is_non_empty_string(finding_case_id)
            and finding_case_id != case_id
        ):
            errors.append(f"findings[{index}] crosses case scope")
        locator = finding.get("locator")
        locator_is_valid = locator is None or is_non_empty_string(locator)
        if "locator" in finding and not locator_is_valid:
            errors.append(
                f"findings[{index}].locator must be null or a non-empty string"
            )
        relation = finding.get("relation")
        if "relation" in finding and (
            not isinstance(relation, str) or relation not in RELATIONS
        ):
            errors.append(f"findings[{index}] has invalid relation")
        verification_status = finding.get("verification_status")
        if "verification_status" in finding and (
            not isinstance(verification_status, str)
            or verification_status not in VERIFICATION
        ):
            errors.append(f"findings[{index}] has invalid verification_status")
        confidence = finding.get("confidence")
        if "confidence" in finding and (
            not isinstance(confidence, str) or confidence not in CONFIDENCE
        ):
            errors.append(f"findings[{index}] has invalid confidence")
        if verification_status == "verified" and not is_non_empty_string(locator):
            errors.append(f"findings[{index}] verified without locator")
        if "hypothesis_ids" in finding:
            finding_references.append(
                (
                    index,
                    validated_id_set(
                        finding,
                        "hypothesis_ids",
                        path=f"findings[{index}]",
                        errors=errors,
                    ),
                )
            )
        if "limitations" in finding:
            validate_string_list(
                finding,
                "limitations",
                path=f"findings[{index}]",
                errors=errors,
            )
        if "contains_sensitive_data" in finding and not isinstance(
            finding["contains_sensitive_data"], bool
        ):
            errors.append(
                f"findings[{index}].contains_sensitive_data must be a boolean"
            )

    hypothesis_ids: set[str] = set()
    hypothesis_references: list[tuple[int, set[str]]] = []
    for index, hypothesis in enumerate(hypotheses):
        if not isinstance(hypothesis, dict):
            errors.append(f"hypotheses[{index}] must be an object")
            continue
        for field in missing_fields(hypothesis, HYPOTHESIS_FIELDS):
            errors.append(f"hypotheses[{index}] missing {field}")
        validate_string_fields(
            hypothesis,
            HYPOTHESIS_STRING_FIELDS,
            path=f"hypotheses[{index}]",
            errors=errors,
        )
        hypothesis_id = hypothesis.get("hypothesis_id")
        if is_non_empty_string(hypothesis_id):
            if hypothesis_id in hypothesis_ids:
                errors.append(
                    "duplicate hypothesis_id: "
                    f"{diagnostic_identifier(hypothesis_id)}"
                )
            hypothesis_ids.add(hypothesis_id)
        status = hypothesis.get("status")
        if "status" in hypothesis and (
            not isinstance(status, str) or status not in HYPOTHESIS_STATUS
        ):
            errors.append(f"hypotheses[{index}] has invalid status")
        referenced: set[str] = set()
        for field in ("supporting_finding_ids", "adverse_finding_ids"):
            if field in hypothesis:
                referenced |= validated_id_set(
                    hypothesis,
                    field,
                    path=f"hypotheses[{index}]",
                    errors=errors,
                )
        hypothesis_references.append((index, referenced))
        if "missing_materials" in hypothesis:
            validate_string_list(
                hypothesis,
                "missing_materials",
                path=f"hypotheses[{index}]",
                errors=errors,
            )

    for index, references in hypothesis_references:
        unknown = sorted(references - finding_ids)
        if unknown:
            errors.append(
                f"hypotheses[{index}] references unknown findings: {unknown}"
            )
    for index, references in finding_references:
        unknown = sorted(references - hypothesis_ids)
        if unknown:
            errors.append(
                f"findings[{index}] references unknown hypotheses: {unknown}"
            )

    if portfolio_present:
        for field in missing_fields(portfolio, PORTFOLIO_FIELDS):
            errors.append(f"portfolio missing {field}")

        approval = portfolio.get("human_approval")
        if "human_approval" in portfolio and (
            not isinstance(approval, str) or approval not in APPROVAL
        ):
            errors.append("portfolio.human_approval is invalid")
        principal = portfolio.get("principal_hypothesis_id")
        if "principal_hypothesis_id" in portfolio and principal is not None:
            if not is_non_empty_string(principal):
                errors.append(
                    "portfolio.principal_hypothesis_id must be a non-empty "
                    "string or null"
                )
            elif principal not in hypothesis_ids:
                errors.append("portfolio principal references unknown hypothesis")
        if (
            "principal_hypothesis_id" in portfolio
            and approval != "approved"
            and principal is not None
        ):
            errors.append("principal hypothesis requires human_approval=approved")
        if approval == "approved" and principal is None:
            errors.append("approved portfolio requires principal_hypothesis_id")
        if approval == "approved" and not is_non_empty_string(
            portfolio.get("approved_by")
        ):
            errors.append(
                "approved portfolio requires approved_by as a non-empty string"
            )
        for key in (
            "reserve_hypothesis_ids",
            "experimental_hypothesis_ids",
            "rejected_hypothesis_ids",
        ):
            if key not in portfolio:
                continue
            references = validated_id_set(
                portfolio,
                key,
                path="portfolio",
                errors=errors,
            )
            unknown = sorted(references - hypothesis_ids)
            if unknown:
                errors.append(
                    f"portfolio.{key} references unknown hypotheses: {unknown}"
                )

    return errors


class _RussianArgumentParser(argparse.ArgumentParser):
    """Показывать стандартные элементы справки argparse по-русски."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["allow_abbrev"] = False
        super().__init__(*args, **kwargs)

    def format_help(self) -> str:
        return (
            super()
            .format_help()
            .replace("usage:", "Использование:", 1)
            .replace("positional arguments:", "позиционные аргументы:", 1)
            .replace("optional arguments:", "параметры:", 1)
            .replace("options:", "параметры:", 1)
            .replace(
                "show this help message and exit",
                "показать эту справку и выйти",
            )
        )


def _build_help_parser() -> argparse.ArgumentParser:
    parser = _RussianArgumentParser(
        prog="validate_argument_research.py",
        description=(
            "Проверить файл исследования аргументов для жалобы в КС РФ."
        ),
    )
    parser.add_argument(
        "path",
        metavar="ПУТЬ",
        help="Путь к проверяемому JSON-файлу исследования аргументов.",
    )
    return parser


def _configure_standard_streams() -> None:
    """Keep Russian CLI text deterministic under a restrictive locale."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    _configure_standard_streams()
    if len(sys.argv) == 2 and sys.argv[1] in {"-h", "--help"}:
        _build_help_parser().print_help()
        return 0
    if len(sys.argv) != 2:
        print("usage: validate_argument_research.py PATH", file=sys.stderr)
        return 2
    raw_path = sys.argv[1]
    option_token = raw_path.partition("=")[0]
    if (
        option_token.startswith("--")
        and len(option_token) > 2
        and option_token != "--help"
        and "--help".startswith(option_token)
    ):
        _build_help_parser().error(f"неизвестный параметр: {raw_path}")
    path = Path(raw_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return 2
    errors = validate(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: базовая структура и ссылки соответствуют контракту; "
        "юридическая готовность не проверялась"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
