import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'skills/ksrf-complaint-cycle/evals/practical_admission.py'
spec = importlib.util.spec_from_file_location('practical_eval', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PracticalEvaluationTests(unittest.TestCase):
    def sample(self):
        case = {'case_id': 'synthetic-1', 'input_sha256': 'a'*64, 'case_kind': 'synthetic', 'outcome_in_runner_input': False}
        prediction = {'case_id': case['case_id'], 'input_sha256': case['input_sha256'], 'filing_eligible': True, 'research_should_continue': False}
        review = {**prediction, 'filing_eligible': False, 'research_should_continue': True,
                  'review_status': 'completed', 'independent_reviewer_id': 'synthetic-review-fixture',
                  'rubric_version': 'test-1', 'reviewed_at': 'synthetic', 'blind_to_model_identity': True}
        return case, prediction, review

    def test_opposite_errors_are_counted_separately(self):
        c,p,r = self.sample(); result=module.evaluate([c],[p],[r])
        self.assertEqual(result['metrics']['false_admission']['errors'],1)
        self.assertEqual(result['metrics']['false_rejection']['errors'],1)
        self.assertFalse(result['promotion_eligible'])
        self.assertEqual(result['scope'],'synthetic_contract')

    def test_no_human_review_is_not_a_zero_error_score(self):
        c,p,_=self.sample(); result=module.evaluate([c],[p],[])
        self.assertIsNone(result['metrics']['false_rejection']['rate'])
        self.assertEqual(len(result['unscored']),1)

    def test_abstentions_are_visible(self):
        c,p,r=self.sample();p['filing_eligible']=None
        result=module.evaluate([c],[p],[r])['metrics']['false_admission']
        self.assertEqual(result['decision_coverage'],0)
        self.assertEqual(result['abstentions'],1)

    def test_outcome_leakage_and_changed_input_are_unscored(self):
        c,p,r=self.sample();c['outcome_in_runner_input']=True
        self.assertTrue(module.evaluate([c],[p],[r])['unscored'])
        c['outcome_in_runner_input']=False;p['input_sha256']='b'*64
        self.assertTrue(module.evaluate([c],[p],[r])['unscored'])

    def test_duplicate_cases_rejected(self):
        c,p,r=self.sample()
        with self.assertRaises(ValueError):module.evaluate([c,c],[p],[r])
