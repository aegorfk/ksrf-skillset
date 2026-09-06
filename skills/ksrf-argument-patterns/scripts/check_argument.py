#!/usr/bin/env python3
"""Проверить связи довода с переданными текстами без сети и корпуса."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


ROLES = {"case_record", "party_submission", "norm_text", "prior_authority", "hypothetical_facts"}
SPEAKERS = {"court", "party", "cited_authority", "analyst", "legislator", "synthetic"}
ISSUE_TEXT = ("norm", "judicial_meaning", "situation", "harm", "constitutional_bridge",
              "narrow_question", "counterargument", "decisive_fact", "if_reversed", "remedy_limit")
CHECKER_RELEASE = "2026-09-06"
FINDING_OPERATORS = {"proven", "not_proven", "proven_not", "act_exists", "unknown"}


def full_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Требуется полная дата YYYY-MM-DD")
    return date.fromisoformat(value)


def records(value, label):
    if not isinstance(value, list):
        raise ValueError(f"{label}: требуется список")
    result = {}
    for row in value:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError(f"{label}: отсутствует строковый id")
        if row["id"] in result:
            raise ValueError(f"{label}: повтор id {row['id']}")
        result[row["id"]] = row
    return result


def string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f"{label}: требуется список непустых строк")
    return value


def span(row, text, label):
    if not isinstance(row, dict):
        raise ValueError(f"{label}: недействительный фрагмент")
    start, end = row.get("start"), row.get("end")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
        raise ValueError(f"{label}: недействительные границы цитаты")
    if row.get("quote") != text[start:end]:
        raise ValueError(f"{label}: цитата не совпадает с переданным текстом")
    return start, end


def check_branches(request, claims):
    if "branches" not in request:
        return {"provided": False, "checked": 0, "semantic_truth_verified": False}
    branches = records(request["branches"], "branches")
    for bid, branch in branches.items():
        for field, slot in (("demand_id", "demand"), ("outcome_id", "outcome")):
            cid = branch.get(field)
            if not isinstance(cid, str) or cid not in claims or claims[cid].get("slot") != slot:
                raise ValueError(f"{bid}: неверная ссылка {field}")
        grounds = string_list(branch.get("ground_ids"), f"{bid}.ground_ids")
        if len(grounds) != len(set(grounds)):
            raise ValueError(f"{bid}: повтор основания")
        if branch.get("independence") not in {"single_ground", "multiple_independent", "interdependent", "unknown"}:
            raise ValueError(f"{bid}: не определена независимость оснований")
        if branch["independence"] == "multiple_independent" and len(grounds) < 2:
            raise ValueError(f"{bid}: самостоятельные основания не перечислены")
        for gid in grounds:
            if gid not in claims or claims[gid].get("slot") != "ground":
                raise ValueError(f"{bid}: неизвестное основание")
            demands = string_list(claims[gid].get("for_demand_ids"), f"{gid}.for_demand_ids")
            if any(d not in claims or claims[d].get("slot") != "demand" for d in demands):
                raise ValueError(f"{gid}: неверное требование основания")
            if branch["demand_id"] not in demands:
                raise ValueError(f"{bid}: основание относится к другому требованию")
    return {"provided": True, "checked": len(branches), "semantic_truth_verified": False}


def check_reasoning(request, claims, gaps):
    result = {"provided": "reasoning_checks" in request, "operator_checks_checked": 0,
              "residual_checks_checked": 0, "semantic_truth_verified": False}
    if not result["provided"]:
        return result
    checks = request["reasoning_checks"]
    if not isinstance(checks, dict):
        raise ValueError("reasoning_checks: требуется объект")
    operators = records(checks.get("operator_checks"), "operator_checks")
    residuals = records(checks.get("residual_checks"), "residual_checks")
    if set(operators) & set(residuals):
        raise ValueError("reasoning_checks: повтор id между списками проверок")
    for cid, row in operators.items():
        values = []
        for field in ("premise_id", "conclusion_id"):
            ref = row.get(field)
            if not isinstance(ref, str) or ref not in claims:
                raise ValueError(f"{cid}: неверная ссылка {field}")
            values.append(claims[ref].get("finding_operator", "unknown"))
        if not isinstance(row.get("same_proposition"), bool):
            raise ValueError(f"{cid}: same_proposition должен быть boolean")
        relation = row.get("relation")
        if not isinstance(relation, str) or relation not in {"equivalent", "requires_additional_premise"}:
            raise ValueError(f"{cid}: неизвестная relation")
        if not isinstance(row.get("explanation"), str) or not row["explanation"].strip():
            raise ValueError(f"{cid}: отсутствует explanation")
        if relation == "equivalent":
            if not row["same_proposition"]:
                raise ValueError(f"{cid}: эквивалентность требует same_proposition=true")
            if "unknown" not in values and values[0] != values[1]:
                raise ValueError(f"{cid}: разные известные операторы не эквивалентны")
        else:
            gaps.append(f"{cid}: дополнительная посылка необходима, но не проверена")
        if "unknown" in values:
            gaps.append(f"{cid}: оператор отсутствует или неизвестен; связь не подтверждена")
    branches = records(request.get("branches", []), "branches")
    for cid, row in residuals.items():
        bid = row.get("branch_id")
        if not isinstance(bid, str) or bid not in branches:
            raise ValueError(f"{cid}: неизвестная branch_id")
        remaining = string_list(row.get("remaining_ground_ids"), f"{cid}.remaining_ground_ids")
        if len(remaining) != len(set(remaining)):
            raise ValueError(f"{cid}: повтор оставшегося основания")
        if set(remaining) - set(branches[bid]["ground_ids"]):
            raise ValueError(f"{cid}: оставшееся основание вне указанной ветви")
        for field in ("entitlement", "extent"):
            assessment = row.get(field)
            if not isinstance(assessment, dict):
                raise ValueError(f"{cid}: {field} требует отдельного объекта оценки")
            value = assessment.get("assessment")
            if not isinstance(value, str) or value not in {"supported", "not_supported", "unknown"}:
                raise ValueError(f"{cid}.{field}: неизвестная assessment")
            if not isinstance(assessment.get("reason"), str) or not assessment["reason"].strip():
                raise ValueError(f"{cid}.{field}: отсутствует reason")
            refs = string_list(assessment.get("support_ids"), f"{cid}.{field}.support_ids")
            if set(refs) - set(remaining):
                raise ValueError(f"{cid}.{field}: опора вне оставшихся оснований")
            if value == "supported" and not refs:
                raise ValueError(f"{cid}.{field}: supported требует непустой опоры")
            if value == "unknown":
                gaps.append(f"{cid}.{field}: оценка неизвестна, нужны доказательства")
    result.update(operator_checks_checked=len(operators), residual_checks_checked=len(residuals))
    return result


def check(request):
    result = {"schema": "ksrf-argument-check.v1", "filing_ready": False,
              "semantic_truth_verified": False, "historical_eval_allowed": False,
              "requires_source_corpus": False, "checker_release": CHECKER_RELEASE,
              "exclusion_detection_automatic": False, "errors": [], "gaps": []}
    if not isinstance(request, dict):
        return dict(result, status="invalid", errors=["Требуется JSON-объект"])
    if request.get("mode") != "prospective":
        return dict(result, status="blocked", errors=["Этот методический релиз запрещён для historical EVAL"])
    errors, gaps = result["errors"], result["gaps"]
    try:
        cutoff = full_date(request.get("as_of"))
        library = json.loads((Path(__file__).resolve().parents[1] / "references/universal-methods.json").read_text())
        if cutoff < max(full_date(library["released_on"]), full_date(CHECKER_RELEASE)):
            return dict(result, status="blocked", errors=["Методика выпущена позже as-of"])
        method_ids = {row["id"] for row in library["methods"]}
        docs = records(request.get("documents"), "documents")
        claims = records(request.get("claims"), "claims")
        issues = records(request.get("issues"), "issues")
        if not issues:
            gaps.append("Нет проверяемых гипотез")
        source_hashes, excluded, completeness = {}, {}, {}
        for did, doc in docs.items():
            if "known_outcome" in doc and not isinstance(doc["known_outcome"], bool):
                raise ValueError(f"{did}: known_outcome должен быть boolean")
            if doc.get("known_outcome") is True or doc.get("role") not in ROLES:
                return dict(result, status="blocked", errors=[f"{did}: недопустимая роль источника или известный исход"])
            if not isinstance(doc.get("text"), str) or not doc["text"].strip():
                raise ValueError(f"{did}: отсутствует текст")
            available = doc.get("available_on")
            if available is None:
                gaps.append(f"{did}: доступность на as-of не установлена")
            elif full_date(available) > cutoff:
                return dict(result, status="blocked", errors=[f"{did}: документ позже as-of"])
            source_hashes[did] = hashlib.sha256(doc["text"].encode()).hexdigest()
            quality = doc.get("completeness", "not_declared")
            if quality not in {"complete", "partial", "unknown", "not_declared"}:
                raise ValueError(f"{did}: неизвестная полнота документа")
            completeness[did] = quality
            if quality in {"partial", "unknown"}:
                gaps.append(f"{did}: исходный судебный текст неполон или его полнота неизвестна")
            exclusions = doc.get("excluded_spans", [])
            if not isinstance(exclusions, list):
                raise ValueError(f"{did}: excluded_spans должен быть списком")
            excluded[did] = []
            for exclusion in exclusions:
                bounds = span(exclusion, doc["text"], did)
                if not isinstance(exclusion.get("reason"), str) or not exclusion["reason"].strip():
                    raise ValueError(f"{did}: не объяснено исключение фрагмента")
                excluded[did].append(bounds)
        claim_checks = {}
        for cid, claim in claims.items():
            if "finding_operator" in claim:
                operator = claim["finding_operator"]
                if not isinstance(operator, str) or operator not in FINDING_OPERATORS:
                    raise ValueError(f"{cid}: неизвестный finding_operator")
            if not isinstance(claim.get("text"), str) or not claim["text"].strip():
                raise ValueError(f"{cid}: отсутствует текст утверждения")
            if claim.get("kind") not in {"observation", "hypothesis", "legal_anchor"}:
                raise ValueError(f"{cid}: неизвестный kind")
            anchors = claim.get("evidence")
            if not isinstance(anchors, list):
                raise ValueError(f"{cid}: evidence должен быть списком")
            if not anchors:
                gaps.append(f"{cid}: {'гипотеза без опоры' if claim['kind'] == 'hypothesis' else 'утверждение без опоры'}")
            checked = 0
            for anchor in anchors:
                if not isinstance(anchor, dict):
                    raise ValueError(f"{cid}: недействительная ссылка")
                did = anchor.get("document_id")
                if not isinstance(did, str) or did not in docs:
                    raise ValueError(f"{cid}: неизвестный документ")
                text = docs[did]["text"]
                start, end = span(anchor, text, cid)
                if any(max(start, a) < min(end, b) for a, b in excluded[did]):
                    return dict(result, status="blocked", errors=[f"{cid}: цитата использует исключённый фрагмент"])
                if anchor.get("speaker") not in SPEAKERS:
                    raise ValueError(f"{cid}: не указана роль говорящего")
                if claim["kind"] == "legal_anchor" and docs[did]["role"] not in {"norm_text", "prior_authority"}:
                    gaps.append(f"{cid}: выбранный источник не подтверждает официальный нормативный якорь")
                checked += 1
            claim_checks[cid] = {"literal_spans_checked": checked, "meaning_verified": False,
                                 "attribution_verified": False}
        for iid, issue in issues.items():
            for field in ISSUE_TEXT:
                if not isinstance(issue.get(field), str) or not issue[field].strip():
                    gaps.append(f"{iid}: не заполнено {field}")
            methods = string_list(issue.get("method_ids", []), f"{iid}.method_ids")
            if set(methods) - method_ids:
                raise ValueError(f"{iid}: неизвестный id метода; используйте custom_method для собственной операции")
            if not methods and not (isinstance(issue.get("custom_method"), str) and issue["custom_method"].strip()):
                gaps.append(f"{iid}: не объяснена операция вывода")
            for field in ("support_ids", "adverse_ids"):
                refs = string_list(issue.get(field), f"{iid}.{field}")
                if set(refs) - set(claims):
                    raise ValueError(f"{iid}: ссылка на неизвестное утверждение")
                if field == "support_ids" and not refs:
                    gaps.append(f"{iid}: нет посылок вывода")
            unknowns = string_list(issue.get("unknowns"), f"{iid}.unknowns")
            gaps.extend(f"{iid}: {unknown}" for unknown in unknowns)
            string_list(issue.get("independent_grounds"), f"{iid}.independent_grounds")
        branch_checks = check_branches(request, claims)
        reasoning_checks = check_reasoning(request, claims, gaps)
        context = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        result.update(source_sha256=source_hashes, claim_checks=claim_checks,
                      input_context_sha256=hashlib.sha256(context.encode()).hexdigest(),
                      branch_checks=branch_checks, document_completeness=completeness,
                      reasoning_checks=reasoning_checks,
                      method_release=library["released_on"], issues_checked=len(issues),
                      status="needs_evidence" if gaps else "structurally_traceable_candidate")
    except (ValueError, TypeError, KeyError) as exc:
        errors.append(str(exc))
        result["status"] = "invalid"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON с текстами нового дела и доводами")
    args = parser.parse_args()
    try:
        result = check(json.loads(args.input.read_text()))
    except (OSError, ValueError) as exc:
        result = {"status": "invalid", "errors": [str(exc)], "filing_ready": False,
                  "semantic_truth_verified": False, "historical_eval_allowed": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "structurally_traceable_candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
