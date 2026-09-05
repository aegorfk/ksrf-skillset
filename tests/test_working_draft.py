import sys
import unittest
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "skills/ksrf-complaint-cycle/lib"
sys.path.insert(0, str(LIB))
from ksrf.filing.composer import ComplaintModelError
from ksrf.filing.working_draft import NOTICE, prepare_working_draft, render_error_details
from ksrf.filing.working_draft import pdf_line_wrap_match, verify_working_draft, _file_record
import json
import tempfile


class WorkingDraftTests(unittest.TestCase):
    def test_foreign_matter_is_rejected_before_rendering(self):
        from ksrf.filing.workflow import WorkflowRouter, WorkflowInputError
        router=object.__new__(WorkflowRouter);router.matter={'matter_id':'one'}
        with self.assertRaises(WorkflowInputError):
            router._render('draft',{'complaint':{'matter_id':'two'}},{'sha256':'a'*64})

    def test_strict_status_does_not_reuse_working_draft(self):
        from ksrf.filing.workflow import WorkflowRouter
        router=object.__new__(WorkflowRouter)
        calls=[]
        def latest(route, actions=None):
            calls.append(actions)
            return None,None
        router._latest_operation=latest
        result=router._render('status',None,None)
        self.assertEqual(calls,[{'build'}])
        self.assertEqual(result['state'],'blocked')
        self.assertEqual(result['result']['reason_code'],'strict_render_missing')

    def test_pdf_line_wrap_repair_does_not_hide_text_loss_or_join_words(self):
        self.assertTrue(pdf_line_wrap_match('Тест: 5-КФ, 10—11', 'Тест: 5-\nКФ, 10—\n11'))
        self.assertFalse(pdf_line_wrap_match('Тест: 5-КФ', 'Тест: 5-\nФ'))
        self.assertFalse(pdf_line_wrap_match('два слова', 'дваслова'))
        self.assertTrue(pdf_line_wrap_match('C — 1,00', 'C —\n1,00'))
        self.assertTrue(pdf_line_wrap_match('10—11', '10\n—11'))
        self.assertFalse(pdf_line_wrap_match('10—11', '10\n—12'))

    def test_status_detects_changed_manifest_and_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); d=root/'drafts';d.mkdir();p=d/'draft.txt';p.write_text('original')
            m=d/'manifest.json';m.write_text(json.dumps({'artifact_type':'WorkingDraftManifest',
                'filing_authority':False,'approval_authority':False,'release_eligible':False,
                'human_review':'pending','artifacts':[_file_record(p)]}))
            result={'manifest':_file_record(m)}
            self.assertEqual(verify_working_draft(root,result),[])
            p.write_text('changed')
            self.assertTrue(verify_working_draft(root,result))
            m.write_text('{}')
            self.assertEqual(verify_working_draft(root,result),['working_draft_manifest_changed'])
    def test_pending_evidence_and_missing_sections_remain_visible(self):
        payload = {"matter_id": "synthetic", "draft_id": "draft-1", "sections": [{
            "code": "facts", "heading": "Факты", "sentences": [{
                "text": "Синтетическое утверждение", "role": "fact", "support_status": "verified",
            }],
        }], "approvals": {"legal_review": "approved"}}
        original, marked, gaps = prepare_working_draft(payload)
        self.assertEqual(len(payload["sections"]), 1)
        self.assertTrue(marked.title.startswith(NOTICE))
        self.assertEqual(marked.approvals, {})
        self.assertIn("ПРОВЕРИТЬ", marked.sections[0].sentences[0].text)
        self.assertEqual(original.sections[0].sentences[0].text, "Синтетическое утверждение")
        self.assertTrue(any(g["code"] == "section_missing" for g in gaps))

    def test_authority_error_does_not_recommend_converter_installation(self):
        error = ComplaintModelError("missing index", reason_codes=("sentence_role_index_authority_required",))
        result = render_error_details(error)
        self.assertEqual(result["reason_code"], "evidence_authority_required")
        self.assertIn("render draft", result["next_action"])
        self.assertNotIn("LibreOffice", result["next_action"])

    def test_invalid_role_stays_a_structural_error(self):
        with self.assertRaises(ComplaintModelError):
            prepare_working_draft({"matter_id": "synthetic", "draft_id": "draft-1", "sections": [{
                "code": "facts", "heading": "Факты", "sentences": [{"text": "text", "role": None}],
            }]})


if __name__ == "__main__":
    unittest.main()
