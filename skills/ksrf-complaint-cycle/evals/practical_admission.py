"""Evaluate reviewed, outcome-blind case decisions; never estimate filing success."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import re
from pathlib import Path


def evaluate(cases, predictions, reviews):
    ids = [c['case_id'] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate case_id')
    for rows in (predictions, reviews):
        row_ids = [r['case_id'] for r in rows]
        if len(row_ids) != len(set(row_ids)) or not set(row_ids).issubset(ids):
            raise ValueError('duplicate or unknown case_id')
    predicted = {p['case_id']: p for p in predictions}
    reviewed = {r['case_id']: r for r in reviews}
    metrics = {k: {'errors': 0, 'denominator': 0, 'abstentions': 0} for k in ('false_admission', 'false_rejection')}
    gaps = []
    for case in cases:
        cid = case['case_id']; p = predicted.get(cid, {}); r = reviewed.get(cid, {})
        valid = (re.fullmatch(r'[0-9a-f]{64}', str(case.get('input_sha256', '')))
                 and r.get('review_status') == 'completed' and r.get('independent_reviewer_id')
                 and r.get('rubric_version') and r.get('reviewed_at')
                 and r.get('input_sha256') == case.get('input_sha256')
                 and r.get('blind_to_model_identity') is True
                 and case.get('outcome_in_runner_input') is False
                 and p.get('input_sha256') == case.get('input_sha256'))
        if not valid:
            gaps.append({'case_id': cid, 'reason': 'review_or_input_binding_missing'})
            continue
        for metric, key, eligible, error in (
            ('false_admission', 'filing_eligible', False, True),
            ('false_rejection', 'research_should_continue', True, False),
        ):
            actual = r.get(key); value = p.get(key)
            if value is not None and type(value) is not bool:
                raise ValueError('decisions must be boolean or null')
            if type(actual) is not bool:
                gaps.append({'case_id': cid, 'reason': 'review_label_missing:' + key})
                continue
            if actual is eligible:
                metrics[metric]['denominator'] += 1
                metrics[metric]['abstentions'] += value is None
                metrics[metric]['errors'] += value is error
    for m in metrics.values():
        n = m['denominator']
        m['rate'] = m['errors'] / n if n else None
        m['decision_coverage'] = (n - m['abstentions']) / n if n else None
    synthetic = any(c.get('case_kind') != 'real' for c in cases)
    return {'schema_version': '1.0', 'metrics': metrics, 'unscored': gaps,
            'scope': 'synthetic_contract' if synthetic else 'reviewed_cases',
            'acceptance_probability': None, 'promotion_eligible': False,
            'limits': ['Rates require denominators and decision coverage.',
                       'Historical outcomes are evaluator-only and not labels of legal merit.',
                       'Reviewed cases do not establish causal improvement or future acceptance.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--cases', required=True, type=Path)
    parser.add_argument('--predictions', required=True, type=Path)
    parser.add_argument('--reviews', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    paths = [args.cases, args.predictions, args.reviews]
    data = [json.loads(p.read_text()) for p in paths]
    result = evaluate(*data)
    result['input_files_sha256'] = {p.name: sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
