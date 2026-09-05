#!/usr/bin/env python3
"""Проверить доказательные условия переноса. Не юридическое заключение."""
import argparse
import json
import re
from datetime import date
from pathlib import Path


def evidence_bound(condition):
    if not isinstance(condition, dict) or type(condition.get("value")) is not bool:
        return None
    evidence = condition.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return None
    for anchor in evidence:
        if not isinstance(anchor, dict):
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", str(anchor.get("source_sha256", ""))):
            return None
        if not isinstance(anchor.get("locator"), str) or not anchor["locator"].strip():
            return None
        if anchor.get("source_checked") is not True or not str(anchor.get("source_role", "")).strip():
            return None
    return condition["value"]


def assess(library, request):
    result = {"historical_eval_allowed": False, "filing_ready": False,
              "evidence_validation": "anchor_structure_only_not_semantic_truth"}
    if not isinstance(request, dict):
        return dict(result, status="blocked", reasons=["invalid_request"])
    if request.get("mode", "prospective") != "prospective":
        return dict(result, status="blocked", reasons=["evaluator_derived_release_forbidden_in_historical_eval"])
    released = date.fromisoformat(library["released_on"])
    if "as_of" not in request:
        return dict(result, status="needs_evidence", reasons=["as_of_required"])
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", request["as_of"]):
            raise ValueError("date")
        as_of = date.fromisoformat(request["as_of"])
    except (ValueError, TypeError):
        return dict(result, status="blocked", reasons=["invalid_as_of"])
    if released > as_of:
        return dict(result, status="blocked", reasons=["release_after_as_of"])
    methods = [item for item in library["methods"] if item["id"] == request.get("method_id")]
    if len(methods) != 1:
        return dict(result, status="blocked", reasons=["unknown_method"])
    method = methods[0]
    necessary, defeaters = method["necessary"], method["defeaters"]
    if not necessary or not defeaters or set(necessary) & set(defeaters):
        return dict(result, status="blocked", reasons=["invalid_method_conditions"])
    conditions = request.get("conditions", {})
    if not isinstance(conditions, dict):
        return dict(result, status="blocked", reasons=["invalid_conditions"])
    extra = sorted(set(conditions) - set(necessary) - set(defeaters))
    if extra:
        return dict(result, status="blocked", reasons=["unknown_condition:" + key for key in extra])
    values = {key: evidence_bound(conditions.get(key)) for key in (*necessary, *defeaters)}
    failed = [key for key in necessary if values[key] is False]
    defeated = [key for key in defeaters if values[key] is True]
    missing = [key for key, value in values.items() if value is None]
    status = "blocked" if defeated else "not_applicable" if failed else "needs_evidence" if missing else "candidate"
    result.update(method_id=method["id"], status=status, necessary_failed=failed,
                  defeaters_present=defeated, unknown=missing,
                  questions={key: (necessary | defeaters)[key] for key in missing},
                  counterargument=method["counterargument"], transfer_limit=method["transfer_limit"])
    if status == "candidate":
        result["drafting_question_template"] = method["question"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON: method_id, mode, as_of, conditions")
    args = parser.parse_args()
    try:
        library = json.loads((Path(__file__).resolve().parents[1] / "references/transfer-methods.json").read_text())
        result = assess(library, json.loads(args.input.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "blocked", "error": "Не удалось проверить вход: " + str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
