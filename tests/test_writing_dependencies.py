"""Mechanical dependency-control fixtures; not a legal case or outcome evaluation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

LIB = Path(__file__).resolve().parents[1] / "skills/ksrf-complaint-cycle/lib"
sys.path.insert(0, str(LIB))
from ksrf.filing.matter import initialize_matter
from ksrf.filing.writing import WritingWorkflow, _wording


ROOT, MIDDLE, REMEDY, RESERVE, OTHER = [f"sent-{n:016x}" for n in range(1, 6)]


class WritingDependencyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.matter_id = initialize_matter(self.root, matter_identifier="dependency-control")["matter_id"]
        self.writer = WritingWorkflow(self.root, self.matter_id)

    def card(self, sid, text=None):
        return {"argument_id": "arg-" + sid, "sentence_id": sid,
                "thesis": "Control-flow premise.", "applicability": "Declared dependency only.",
                "conclusion": "Control-flow conclusion.", "strongest_objection": "Review this text.",
                "response": "Check the declared premise.", "inference_level": "argument",
                "proposed_text": text or "Control-flow text for " + sid, "evidence": []}

    @staticmethod
    def link(name, premise, dependent):
        return {"dependency_id": name, "premise_sentence_id": premise,
                "dependent_sentence_id": dependent, "reason": "Declared necessity: " + name}

    def compose_payload(self, dependencies=None):
        plan = self.writer.run("plan", {"matter_id": self.matter_id,
            "options": [{"option_id": "control", "question": "Control-flow question"}],
            "proposed_principal": "control", "choice_reason": "Mechanical fixture only."})
        complaint = {"matter_id": self.matter_id, "draft_id": "dependency-control", "title": "Control-flow fixture",
            "sections": [{"code": "arguments", "heading": "Arguments", "sentences": [
                {"sentence_id": sid, "text": "Initial text for " + sid, "role": "narrative"}
                for sid in (ROOT, MIDDLE, RESERVE, OTHER)]},
                {"code": "remedy", "heading": "Request", "sentences": [
                    {"sentence_id": REMEDY, "text": "Unmapped request text.", "role": "requested_remedy"}]}]}
        payload = {"matter_id": self.matter_id, "parent": plan["packet"], "complaint": complaint,
                   "sources": [], "arguments": [self.card(sid) for sid in (ROOT, MIDDLE, RESERVE, OTHER)]}
        if dependencies is not None:
            payload["dependencies"] = dependencies
        return payload

    def compose(self, dependencies=None):
        payload = self.compose_payload(dependencies)
        result = self.writer.run("compose", payload)
        return result, self.writer.read(result["packet"])

    @staticmethod
    def texts(packet):
        return {s["sentence_id"]: s["text"] for section in packet["candidate"]["sections"]
                for s in section["sentences"]}

    def review(self, result, packet, *, omit_context=False):
        findings = copy.deepcopy(packet["objections"])
        texts = self.texts(packet)
        for finding in findings:
            finding.update(status="addressed", wording_sha256=_wording(texts[finding["sentence_id"]]),
                           review_reason="Mechanical test review; no legal approval.")
            if omit_context:
                finding.pop("impact_context", None)
        reviewed = self.writer.run("review", {"matter_id": self.matter_id, "parent": result["packet"],
            "base_draft_sha256": result["draft_sha256"], "findings": findings})
        return reviewed, self.writer.read(reviewed["packet"])

    def revision_payload(self, result, packet, roots=(ROOT,), **extra):
        texts = self.texts(packet)
        return {"matter_id": self.matter_id, "parent": result["packet"],
                "base_draft_sha256": result["draft_sha256"], "edits": [
                    {"sentence_id": sid, "before_sha256": _wording(texts[sid]),
                     "reason": "Change control-flow premise.", "argument": self.card(sid, texts[sid] + " Revised.")}
                    for sid in roots], **extra}

    def revise(self, result, packet, roots=(ROOT,), **extra):
        revised = self.writer.run("revise", self.revision_payload(result, packet, roots, **extra))
        return revised, self.writer.read(revised["packet"])

    @staticmethod
    def impacts(packet):
        return {o["sentence_id"]: o for o in packet["objections"] if "impact_context" in o}

    def assert_rejected_before_save(self, action, payload):
        with mock.patch.object(self.writer, "_save", wraps=self.writer._save) as save:
            with self.assertRaises(ValueError):
                self.writer.run(action, payload)
            save.assert_not_called()

    def test_changed_premise_reopens_unchanged_chain_and_unmapped_remedy(self):
        links = [self.link("root-middle", ROOT, MIDDLE), self.link("middle-remedy", MIDDLE, REMEDY)]
        composed, first = self.compose(links)
        reviewed, before = self.review(composed, first)
        revised, after = self.revise(reviewed, before)
        old_middle = next(o for o in before["objections"] if o["sentence_id"] == MIDDLE)
        new_middle = next(o for o in after["objections"] if o["objection_id"] == old_middle["objection_id"])
        self.assertEqual(new_middle["status"], "needs_recheck")
        self.assertEqual(set(self.impacts(after)), {MIDDLE, REMEDY})
        self.assertEqual(self.texts(before)[REMEDY], self.texts(after)[REMEDY])
        self.assertEqual(self.texts(before)[MIDDLE], self.texts(after)[MIDDLE])
        self.assertIn(REMEDY, after["unmapped_sentence_ids"])
        self.assertEqual(after["original"], first["original"])
        self.assertFalse(revised["legal_support_verified"])
        self.assertFalse(revised["filing_authority"])

    def test_declared_links_survive_omission_and_report_does_not_claim_completeness(self):
        links = [self.link("root-middle", ROOT, MIDDLE)]
        composed, first = self.compose(links)
        reviewed, second = self.review(composed, first)
        revised, third = self.revise(reviewed, second)
        self.assertEqual(first["dependencies"], links)
        self.assertEqual(second["dependencies"], links)
        self.assertEqual(third["dependencies"], links)
        report = Path(revised["output_dir"]) / "dependency-impact.md"
        text = report.read_text()
        for value in (ROOT, MIDDLE, "root-middle", links[0]["reason"]):
            self.assertIn(value, text)
        self.assertFalse(third["dependency_completeness_verified"])
        self.assertFalse(third["dependency_legal_validity_verified"])

    def test_unrelated_reserve_findings_and_texts_are_exactly_preserved(self):
        composed, first = self.compose([self.link("root-middle", ROOT, MIDDLE)])
        reviewed, before = self.review(composed, first)
        _, after = self.revise(reviewed, before)
        for sid in (RESERVE, OTHER):
            self.assertEqual(self.texts(after)[sid], self.texts(before)[sid])
            self.assertEqual([o for o in after["objections"] if o["sentence_id"] == sid],
                             [o for o in before["objections"] if o["sentence_id"] == sid])
        self.assertNotIn(RESERVE, self.impacts(after))
        self.assertNotIn(OTHER, self.impacts(after))

    def test_multiple_roots_and_cycle_are_order_independent_and_invalidate_once(self):
        links = [self.link("root-middle", ROOT, MIDDLE), self.link("other-middle", OTHER, MIDDLE),
                 self.link("middle-root", MIDDLE, ROOT), self.link("middle-remedy", MIDDLE, REMEDY)]
        composed, first = self.compose(links)
        reviewed, before = self.review(composed, first)
        _, forward = self.revise(reviewed, before, (ROOT, OTHER))
        _, reverse = self.revise(reviewed, before, (OTHER, ROOT))
        self.assertEqual(forward["candidate"], reverse["candidate"])
        self.assertEqual(forward["dependency_impact"], reverse["dependency_impact"])
        self.assertEqual(self.impacts(forward), self.impacts(reverse))
        self.assertEqual(len({o["objection_id"] for o in forward["objections"]}), len(forward["objections"]))
        old_by_id = {o["objection_id"]: o for o in before["objections"]}
        for objection in forward["objections"]:
            old = old_by_id.get(objection["objection_id"])
            if old and objection["sentence_id"] in (ROOT, OTHER, MIDDLE):
                self.assertEqual(objection["status"], "needs_recheck")
                self.assertEqual(len(objection["history"]), len(old["history"]) + 1)
        remedy_context = self.impacts(forward)[REMEDY]["impact_context"]
        self.assertEqual(set(remedy_context["changed_sentence_ids"]), {ROOT, OTHER})
        self.assertEqual(set(remedy_context["dependency_ids"]), {d["dependency_id"] for d in links})

    def test_dependency_only_addition_checks_unchanged_target_and_downstream(self):
        composed, before = self.compose([self.link("middle-remedy", MIDDLE, REMEDY)])
        added = self.link("root-middle", ROOT, MIDDLE)
        revised, after = self.revise(composed, before, roots=(), dependencies=[added])
        self.assertEqual(after["candidate"], before["candidate"])
        self.assertEqual(after["draft_sha256"], before["draft_sha256"])
        self.assertEqual(set(self.impacts(after)), {MIDDLE, REMEDY})
        self.assertEqual(self.impacts(after)[REMEDY]["impact_context"]["changed_sentence_ids"], [])
        self.assertEqual(self.impacts(after)[REMEDY]["impact_context"]["trigger_dependency_ids"], ["root-middle"])
        self.assertFalse(revised["approval_authority"])

    def test_empty_revision_without_actual_link_change_remains_invalid(self):
        link = self.link("root-middle", ROOT, MIDDLE)
        composed, before = self.compose([link])
        for extra in ({}, {"dependencies": []}, {"dependencies": [link]}, {"dependency_removals": []}):
            with self.subTest(extra=extra):
                self.assert_rejected_before_save("revise", self.revision_payload(composed, before, (), **extra))

    def test_explicit_retirement_records_reason_and_traverses_old_new_union(self):
        old = self.link("root-middle", ROOT, MIDDLE)
        downstream = self.link("middle-remedy", MIDDLE, REMEDY)
        composed, first = self.compose([old, downstream])
        reviewed, before = self.review(composed, first)
        reason = "This declared relation is being retired for manual reconsideration."
        revised, after = self.revise(reviewed, before,
            dependency_removals=[{"dependency_id": old["dependency_id"], "reason": reason}],
            dependencies=[self.link("root-other", ROOT, OTHER)])
        self.assertEqual({d["dependency_id"] for d in after["dependencies"]}, {"middle-remedy", "root-other"})
        self.assertEqual(after["dependency_history"], [{"dependency": old, "reason": reason}])
        self.assertEqual(set(self.impacts(after)), {MIDDLE, REMEDY, OTHER})
        self.assertIn("root-middle", self.impacts(after)[REMEDY]["impact_context"]["dependency_ids"])
        report = (Path(revised["output_dir"]) / "dependency-impact.md").read_text()
        self.assertIn(reason, report)
        self.assertIn(old["reason"], report)
        checked, checked_packet = self.review(revised, after)
        _, again = self.revise(checked, checked_packet)
        self.assertEqual(again["dependency_history"], after["dependency_history"])
        self.assertEqual({item["sentence_id"] for item in again["dependency_impact"]}, {OTHER})
        self.assertEqual(self.impacts(again)[MIDDLE], self.impacts(checked_packet)[MIDDLE])

    def test_retirement_without_text_edits_still_checks_previous_dependents(self):
        link = self.link("root-remedy", ROOT, REMEDY)
        composed, before = self.compose([link])
        _, after = self.revise(composed, before, roots=(),
            dependency_removals=[{"dependency_id": link["dependency_id"], "reason": "Retirement explanation."}])
        self.assertEqual(after["dependencies"], [])
        self.assertEqual(after["candidate"], before["candidate"])
        self.assertEqual(set(self.impacts(after)), {REMEDY})
        self.assertEqual(self.impacts(after)[REMEDY]["impact_context"]["trigger_dependency_ids"], [link["dependency_id"]])

    def test_link_add_then_retirement_has_distinct_context_even_without_text_changes(self):
        composed, first = self.compose()
        link = self.link("root-remedy", ROOT, REMEDY)
        added, second = self.revise(composed, first, roots=(), dependencies=[link])
        reviewed, third = self.review(added, second)
        _, fourth = self.revise(reviewed, third, roots=(),
            dependency_removals=[{"dependency_id": link["dependency_id"], "reason": "Manual reassessment of the declaration."}])
        previous = self.impacts(third)[REMEDY]
        current = self.impacts(fourth)[REMEDY]
        self.assertEqual(fourth["draft_sha256"], second["draft_sha256"])
        self.assertEqual(current["objection_id"], previous["objection_id"])
        self.assertEqual(current["status"], "needs_recheck")
        self.assertNotEqual(current["impact_context"], previous["impact_context"])
        self.assertEqual(previous["impact_context"]["added_dependency_ids"], [link["dependency_id"]])
        self.assertEqual(current["impact_context"]["retired_dependency_ids"], [link["dependency_id"]])
        self.assertEqual(current["history"][-1]["impact_context"], previous["impact_context"])

    def test_review_omission_preserves_context_and_later_impact_reopens_same_item(self):
        composed, first = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        revised, affected = self.revise(composed, first)
        initial = copy.deepcopy(self.impacts(affected)[REMEDY])
        checked, checked_packet = self.review(revised, affected, omit_context=True)
        checked_item = self.impacts(checked_packet)[REMEDY]
        self.assertEqual(checked_item["impact_context"], initial["impact_context"])
        self.assertEqual(checked_item["status"], "addressed")
        _, repeated = self.revise(checked, checked_packet)
        item = self.impacts(repeated)[REMEDY]
        self.assertEqual(item["objection_id"], initial["objection_id"])
        self.assertEqual(item["status"], "needs_recheck")
        self.assertEqual(item["history"][-1]["impact_context"], checked_item["impact_context"])
        self.assertEqual(item["history"][-1]["status"], "addressed")
        self.assertEqual(len(item["history"]), len(checked_item["history"]) + 1)
        self.assertNotEqual(item["impact_context"], checked_item["impact_context"])
        self.assertEqual(item["impact_context"]["base_draft_sha256"], repeated["draft_sha256"])
        context = {s["sentence_id"]: s["wording_sha256"] for s in item["impact_context"]["sentence_context"]}
        self.assertEqual(context[ROOT], _wording(self.texts(repeated)[ROOT]))
        self.assertEqual(context[REMEDY], _wording(self.texts(repeated)[REMEDY]))

    def test_sequential_root_edits_preserve_all_unreviewed_causes(self):
        links = [self.link("root-remedy", ROOT, REMEDY), self.link("other-remedy", OTHER, REMEDY)]
        composed, first = self.compose(links)
        reviewed, second = self.review(composed, first)
        revised, third = self.revise(reviewed, second)
        _, fourth = self.revise(revised, third, roots=(OTHER,))
        previous = self.impacts(third)[REMEDY]
        current = self.impacts(fourth)[REMEDY]
        self.assertEqual(current["status"], "needs_recheck")
        self.assertEqual(set(current["impact_context"]["changed_sentence_ids"]), {ROOT, OTHER})
        self.assertEqual(set(current["impact_context"]["dependency_ids"]), {"root-remedy", "other-remedy"})
        context = {item["sentence_id"]: item["wording_sha256"]
                   for item in current["impact_context"]["sentence_context"]}
        for sid in (ROOT, OTHER, REMEDY):
            self.assertEqual(context[sid], _wording(self.texts(fourth)[sid]))
        self.assertEqual(current["history"][-1]["impact_context"], previous["impact_context"])

    def test_addressed_prior_cause_remains_in_history_not_as_new_unresolved_cause(self):
        composed, first = self.compose([self.link("root-remedy", ROOT, REMEDY),
                                       self.link("other-remedy", OTHER, REMEDY)])
        revised, second = self.revise(composed, first)
        checked, third = self.review(revised, second)
        _, fourth = self.revise(checked, third, roots=(OTHER,))
        current = self.impacts(fourth)[REMEDY]
        self.assertEqual(current["status"], "needs_recheck")
        self.assertEqual(current["impact_context"]["changed_sentence_ids"], [OTHER])
        self.assertEqual(current["history"][-1]["impact_context"]["changed_sentence_ids"], [ROOT])
        self.assertEqual(current["history"][-1]["status"], "addressed")

    def test_pending_retired_link_cause_refreshes_without_reopening_reviewed_retirement(self):
        link = self.link("root-remedy", ROOT, REMEDY)
        composed, first = self.compose([link])
        reviewed, second = self.review(composed, first)
        retired, third = self.revise(reviewed, second, roots=(),
            dependency_removals=[{"dependency_id": link["dependency_id"], "reason": "Retirement requires reconsideration."}])
        _, pending = self.revise(retired, third)
        current = self.impacts(pending)[REMEDY]
        self.assertEqual(current["status"], "needs_recheck")
        context = {item["sentence_id"]: item["wording_sha256"]
                   for item in current["impact_context"]["sentence_context"]}
        self.assertEqual(context[ROOT], _wording(self.texts(pending)[ROOT]))
        self.assertEqual(current["impact_context"]["base_draft_sha256"], pending["draft_sha256"])
        self.assertIn("root-remedy", current["impact_context"]["dependency_ids"])
        self.assertIn(REMEDY, {item["sentence_id"] for item in pending["dependency_impact"]})
        checked, checked_packet = self.review(retired, third)
        _, independent = self.revise(checked, checked_packet)
        self.assertEqual(self.impacts(independent)[REMEDY], self.impacts(checked_packet)[REMEDY])
        self.assertNotIn(REMEDY, {item["sentence_id"] for item in independent["dependency_impact"]})

    def test_unrelated_edit_keeps_pending_report_without_inventing_another_cause_or_history_event(self):
        composed, first = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        revised, second = self.revise(composed, first)
        _, third = self.revise(revised, second, roots=(RESERVE,))
        previous = self.impacts(second)[REMEDY]
        current = self.impacts(third)[REMEDY]
        self.assertIn(REMEDY, {item["sentence_id"] for item in third["dependency_impact"]})
        self.assertEqual(current["status"], "needs_recheck")
        self.assertEqual(current["history"], previous["history"])
        self.assertEqual(current["impact_context"]["changed_sentence_ids"], [ROOT])
        self.assertEqual(current["impact_context"]["dependency_ids"], ["root-remedy"])
        self.assertEqual(current["impact_context"]["sentence_context"], previous["impact_context"]["sentence_context"])

    def test_direct_target_edit_rebinds_existing_impact_without_losing_provenance(self):
        composed, first = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        revised, second = self.revise(composed, first)
        checked, third = self.review(revised, second)
        direct, fourth = self.revise(checked, third, roots=(REMEDY,))
        previous = self.impacts(third)[REMEDY]
        current = self.impacts(fourth)[REMEDY]
        self.assertEqual(current["objection_id"], previous["objection_id"])
        self.assertEqual(current["status"], "needs_recheck")
        self.assertEqual(current["wording_sha256"], _wording(self.texts(fourth)[REMEDY]))
        self.assertEqual(current["impact_context"]["base_draft_sha256"], fourth["draft_sha256"])
        self.assertEqual(current["impact_context"]["target_edit_sentence_ids"], [REMEDY])
        self.assertEqual(current["impact_context"]["dependency_ids"], previous["impact_context"]["dependency_ids"])
        self.assertEqual(current["history"][-1]["impact_context"], previous["impact_context"])
        self.assertEqual(len(current["history"]), len(previous["history"]) + 1)
        context = {item["sentence_id"]: item["wording_sha256"]
                   for item in current["impact_context"]["sentence_context"]}
        self.assertEqual(context[REMEDY], _wording(self.texts(fourth)[REMEDY]))
        stale = copy.deepcopy(current)
        stale.update(status="addressed", review_reason="Mechanical current review.",
                     impact_context=copy.deepcopy(previous["impact_context"]))
        self.assert_rejected_before_save("review", {"matter_id": self.matter_id, "parent": direct["packet"],
            "base_draft_sha256": direct["draft_sha256"], "findings": [stale]})
        _, rechecked = self.review(direct, fourth, omit_context=True)
        self.assertEqual(self.impacts(rechecked)[REMEDY]["impact_context"], current["impact_context"])

    def test_review_rejects_replaced_impact_context_and_stale_draft(self):
        composed, first = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        revised, affected = self.revise(composed, first)
        finding = copy.deepcopy(self.impacts(affected)[REMEDY])
        finding.update(status="addressed", review_reason="Mechanical review.")
        base = {"matter_id": self.matter_id, "parent": revised["packet"],
                "base_draft_sha256": revised["draft_sha256"], "findings": [finding]}
        for mode in ("missing_root", "null_context", "stale_draft", "stale_wording"):
            with self.subTest(mode=mode):
                payload = copy.deepcopy(base)
                if mode == "missing_root":
                    payload["findings"][0]["impact_context"]["changed_sentence_ids"] = []
                elif mode == "null_context":
                    payload["findings"][0]["impact_context"] = None
                elif mode == "stale_draft":
                    payload["base_draft_sha256"] = composed["draft_sha256"]
                else:
                    payload["findings"][0]["wording_sha256"] = "0" * 64
                self.assert_rejected_before_save("review", payload)

    def test_review_cannot_forge_impact_identity_or_context_on_an_ordinary_finding(self):
        composed, packet = self.compose()
        ordinary = copy.deepcopy(packet["objections"][0])
        ordinary.update(status="addressed", review_reason="Mechanical review.")
        cases = [{**ordinary, "impact_context": {}},
                 {**ordinary, "objection_id": "impact-manually-created"},
                 {**ordinary, "objection_id": "new-ordinary", "impact_context": {}}]
        for finding in cases:
            with self.subTest(finding=finding):
                self.assert_rejected_before_save("review", {"matter_id": self.matter_id,
                    "parent": composed["packet"], "base_draft_sha256": composed["draft_sha256"],
                    "findings": [finding]})

    def test_each_impact_context_contains_relevant_paths_not_sibling_branches(self):
        links = [self.link("root-middle", ROOT, MIDDLE), self.link("middle-remedy", MIDDLE, REMEDY),
                 self.link("root-other", ROOT, OTHER)]
        composed, packet = self.compose(links)
        _, affected = self.revise(composed, packet)
        impacts = self.impacts(affected)
        self.assertEqual(impacts[MIDDLE]["impact_context"]["dependency_ids"], ["root-middle"])
        self.assertEqual(impacts[OTHER]["impact_context"]["dependency_ids"], ["root-other"])
        context = impacts[REMEDY]["impact_context"]
        self.assertEqual(set(context["dependency_ids"]), {"root-middle", "middle-remedy"})
        self.assertEqual({item["sentence_id"] for item in context["sentence_context"]}, {ROOT, MIDDLE, REMEDY})
        self.assertEqual({item["dependency_id"] for item in context["dependencies"]}, set(context["dependency_ids"]))

    def test_dependency_report_is_integrity_bound_to_the_saved_packet(self):
        composed, packet = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        revised, _ = self.revise(composed, packet)
        report = Path(revised["output_dir"]) / "dependency-impact.md"
        self.assertTrue(any(item["path"].endswith("/dependency-impact.md") for item in revised["artifacts"]))
        report.write_text("Altered mechanical report.")
        with self.assertRaises(ValueError):
            self.writer.read(revised["packet"])

    def test_omitted_findings_cannot_drop_existing_impact(self):
        composed, first = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        revised, affected = self.revise(composed, first)
        reviewed = self.writer.run("review", {"matter_id": self.matter_id, "parent": revised["packet"],
            "base_draft_sha256": revised["draft_sha256"], "findings": []})
        after = self.writer.read(reviewed["packet"])
        self.assertEqual(after["objections"], affected["objections"])
        self.assertEqual(after["dependency_impact"], affected["dependency_impact"])

    def test_malformed_dependency_fields_fail_before_save(self):
        base = self.compose_payload()
        valid = self.link("root-middle", ROOT, MIDDLE)
        cases = [None, {}, "not a list", [None], ["not a record"]]
        for field, values in {
                "dependency_id": [None, "", "  ", True, [], {}],
                "premise_sentence_id": [None, "", True, [], {}, "unknown", "sent-ffffffffffffffff"],
                "dependent_sentence_id": [None, "", True, [], {}, "unknown", "sent-ffffffffffffffff", ROOT],
                "reason": [None, "", "  ", True, [], {}]}.items():
            for value in values:
                cases.append([{**valid, field: value}])
            missing = dict(valid)
            del missing[field]
            cases.append([missing])
        cases.append([valid, valid])
        cases.append([{**valid, "unknown_field": "Cannot silently reinterpret a relation."}])
        for dependencies in cases:
            with self.subTest(dependencies=dependencies):
                self.assert_rejected_before_save("compose", {**base, "dependencies": dependencies})

    def test_compose_rejects_retirement_instead_of_inventing_prior_history(self):
        link = self.link("root-middle", ROOT, MIDDLE)
        payload = self.compose_payload([link])
        payload["dependency_removals"] = [{"dependency_id": link["dependency_id"], "reason": "No prior declaration exists."}]
        self.assert_rejected_before_save("compose", payload)

    def test_same_dependency_id_cannot_be_redefined_but_exact_reassertion_is_allowed(self):
        link = self.link("root-middle", ROOT, MIDDLE)
        composed, before = self.compose([link])
        _, same = self.revise(composed, before, dependencies=[copy.deepcopy(link)])
        self.assertEqual(same["dependencies"], [link])
        for field, value in (("reason", "Changed meaning."), ("premise_sentence_id", OTHER),
                             ("dependent_sentence_id", REMEDY)):
            with self.subTest(field=field):
                self.assert_rejected_before_save("revise", self.revision_payload(composed, before,
                    dependencies=[{**link, field: value}]))

    def test_malformed_unknown_duplicate_and_ambiguous_retirements_fail(self):
        link = self.link("root-middle", ROOT, MIDDLE)
        composed, before = self.compose([link])
        valid = {"dependency_id": link["dependency_id"], "reason": "Retirement explanation."}
        bad = [None, {}, "bad", [None], ["bad"], [valid, valid],
               [{**valid, "dependency_id": "absent"}], [{**valid, "dependency_id": []}],
               [{**valid, "dependency_id": True}], [{"dependency_id": link["dependency_id"]}],
               [{**valid, "reason": " "}], [{**valid, "reason": True}], [{**valid, "reason": {}}]]
        for removals in bad:
            with self.subTest(removals=removals):
                self.assert_rejected_before_save("revise", self.revision_payload(composed, before,
                    dependency_removals=removals))
        self.assert_rejected_before_save("revise", self.revision_payload(composed, before,
            dependencies=[link], dependency_removals=[valid]))
        added = self.link("new-root-remedy", ROOT, REMEDY)
        self.assert_rejected_before_save("revise", self.revision_payload(composed, before,
            dependencies=[added], dependency_removals=[{"dependency_id": added["dependency_id"], "reason": "Ambiguous."}]))

    def test_retired_ids_cannot_be_reused_or_retired_again(self):
        link = self.link("root-middle", ROOT, MIDDLE)
        composed, before = self.compose([link])
        removal = {"dependency_id": link["dependency_id"], "reason": "Retirement explanation."}
        retired, after = self.revise(composed, before, dependency_removals=[removal])
        for declaration in (link, {**link, "dependent_sentence_id": REMEDY}):
            with self.subTest(declaration=declaration):
                self.assert_rejected_before_save("revise", self.revision_payload(retired, after,
                    dependencies=[declaration]))
        self.assert_rejected_before_save("revise", self.revision_payload(retired, after,
            dependency_removals=[removal]))

    def test_dependency_field_omission_supports_legacy_payload_and_stored_packet(self):
        composed, first = self.compose()
        reviewed, second = self.review(composed, first)
        _, after = self.revise(reviewed, second)
        self.assertFalse(self.impacts(after))
        old_middle = next(o for o in second["objections"] if o["sentence_id"] == MIDDLE)
        self.assertIn(old_middle, after["objections"])
        legacy = copy.deepcopy(second)
        for key in list(legacy):
            if key.startswith("dependency_") or key == "dependencies":
                del legacy[key]
        legacy_ref = self.writer.store.put_bytes(json.dumps(legacy).encode())
        legacy_result = {**reviewed, "packet": legacy_ref}
        _, upgraded = self.revise(legacy_result, legacy)
        self.assertEqual(upgraded["candidate"], after["candidate"])
        self.assertFalse(self.impacts(upgraded))

    def test_packet_cannot_claim_dependency_completeness_or_legal_validity(self):
        _, packet = self.compose([self.link("root-remedy", ROOT, REMEDY)])
        for key in ("dependency_completeness_verified", "dependency_legal_validity_verified"):
            for value in (True, None, 0, "false"):
                with self.subTest(key=key, value=value):
                    forged = copy.deepcopy(packet)
                    forged[key] = value
                    reference = self.writer.store.put_bytes(json.dumps(forged).encode())
                    with self.assertRaises(ValueError):
                        self.writer.read(reference)


if __name__ == "__main__":
    unittest.main()
