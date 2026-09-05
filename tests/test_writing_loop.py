"""Synthetic editing workflow checks; no legal outcome labels or private text."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LIB = Path(__file__).resolve().parents[1] / "skills/ksrf-complaint-cycle/lib"
sys.path.insert(0, str(LIB))
from ksrf.filing.cli import main
from ksrf.filing.matter import initialize_matter
from ksrf.filing.writing import WritingWorkflow, _digest, _wording
from ksrf.filing.working_draft import prepare_working_draft


SID = "sent-0000000000000001"
SOURCE = "Синтетическая запись: суд упомянул правило А. Результат теста Б. Иное основание В."


class WritingLoopTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.matter = initialize_matter(self.root, matter_identifier="synthetic-writing")
        self.matter_id = self.matter["matter_id"]
        self.writer = WritingWorkflow(self.root, self.matter_id)
        self.source = {"source_id": "synthetic-source", "role": "court_reasoning",
                       "object": self.writer.store.put_bytes(SOURCE.encode())}

    def plan_input(self):
        return {"schema_version": "1.0.0", "matter_id": self.matter_id,
                "options": [{"option_id": "one", "question": "Синтетический вопрос?", "norm": "Правило А"}],
                "proposed_principal": "one", "choice_reason": "Синтетическая причина выбора."}

    def card(self, **updates):
        result = {"argument_id": "arg-one", "sentence_id": SID, "thesis": "Синтетический тезис.",
                  "applicability": "Предел применимости требует проверки.", "conclusion": "Синтетический вывод.",
                  "strongest_objection": "Упоминание не доказывает причинность.", "response": "Сузить вывод.",
                  "inference_level": "mentioned", "proposed_text": "В тестовой записи правило А упомянуто.",
                  "evidence": [{"source_id": "synthetic-source", "start": 0, "end": len(SOURCE),
                                "quote": SOURCE, "proof_role": "norm_mention"}]}
        result.update(updates)
        return result

    def complaint(self):
        return {"matter_id": self.matter_id, "draft_id": "synthetic-draft", "title": "Синтетический проект",
                "approvals": {"legal_review": "approved"}, "formal_check": {"passed": True},
                "sections": [{"code": "legal_arguments", "heading": "Доводы", "sentences": [
                    {"sentence_id": SID, "role": "application_finding", "text": "Исходный тестовый текст.",
                     "support_status": "verified"}]},
                    {"code": "facts", "heading": "Факты", "sentences": [{"text": "Второй тестовый абзац.", "role": "fact"}]}]}

    def compose_input(self, plan):
        return {"schema_version": "1.0.0", "matter_id": self.matter_id, "parent": plan["packet"],
                "complaint": self.complaint(), "sources": [self.source], "arguments": [self.card()]}

    def compose(self):
        plan = self.writer.run("plan", self.plan_input())
        result = self.writer.run("compose", self.compose_input(plan))
        return result, self.writer.read(result["packet"])

    def review_input(self, result, packet, *, status="addressed"):
        finding = copy.deepcopy(packet["objections"][0])
        finding.update(status=status, wording_sha256=_wording(packet["candidate"]["sections"][0]["sentences"][0]["text"]),
                       review_reason="Синтетическая редакторская проверка; юридическое одобрение не дано.")
        return {"schema_version": "1.0.0", "matter_id": self.matter_id, "parent": result["packet"],
                "base_draft_sha256": result["draft_sha256"], "findings": [finding]}

    def revision_input(self, result, packet):
        return {"schema_version": "1.0.0", "matter_id": self.matter_id, "parent": result["packet"],
                "base_draft_sha256": result["draft_sha256"], "edits": [{"sentence_id": SID,
                    "before_sha256": _wording(packet["candidate"]["sections"][0]["sentences"][0]["text"]),
                    "reason": "Уточнить предел утверждения.", "objection_ids": [packet["objections"][0]["objection_id"]],
                    "argument": self.card(proposed_text="Запись подтверждает только упоминание правила А.")} ]}

    def cli(self, action, payload=None):
        args = ["writing", action, "--workspace", str(self.root), "--json"]
        if payload is not None:
            path = self.root / "input.json"
            path.write_text(json.dumps(payload, ensure_ascii=False))
            args.extend(["--payload", str(path)])
        output, errors = io.StringIO(), io.StringIO()
        code = main(args, stdout=output, stderr=errors)
        return code, json.loads(output.getvalue()) if output.getvalue() else None, errors.getvalue()

    def test_plan_retains_unknown_fields_and_proposed_choice(self):
        result = self.writer.run("plan", self.plan_input())
        packet = self.writer.read(result["packet"])
        self.assertEqual(packet["concept"]["proposed_principal"], "one")
        self.assertEqual(packet["concept"]["options"][0]["norm_version"], "")
        self.assertTrue(any("редакция нормы" in gap for gap in result["gaps"]))
        self.assertFalse(result["filing_authority"])
        self.assertIn("ТРЕБУЕТ УТОЧНЕНИЯ", (Path(result["output_dir"]) / "concept.md").read_text())

    def test_duplicate_or_absent_concept_choice_fails(self):
        for duplicate in (False, True):
            payload = self.plan_input()
            if duplicate:
                payload["options"] *= 2
            else:
                payload["proposed_principal"] = "absent"
            with self.assertRaises(ValueError):
                self.writer.run("plan", payload)

    def test_composition_preserves_original_and_resets_approval(self):
        result, packet = self.compose()
        self.assertEqual(packet["original"]["sections"][0]["sentences"][0]["text"], "Исходный тестовый текст.")
        self.assertEqual(packet["original"]["approvals"], {"legal_review": "approved"})
        self.assertEqual(packet["candidate"]["approvals"], {})
        self.assertEqual(packet["candidate"]["formal_check"], {})
        self.assertEqual(packet["candidate"]["sections"][0]["sentences"][0]["support_status"], "pending")
        self.assertFalse(packet["arguments"][0]["legal_support_verified"])
        self.assertEqual(len(packet["unmapped_sentence_ids"]), 1)
        self.assertIn("-Исходный", (Path(result["output_dir"]) / "changes.diff").read_text())
        self.assertEqual(len(packet["objections"]), 1)
        self.assertEqual(packet["objections"][0]["status"], "open")

    def test_compose_can_assemble_text_from_components_without_proposed_text(self):
        plan = self.writer.run("plan", self.plan_input())
        payload = self.compose_input(plan)
        del payload["arguments"][0]["proposed_text"]
        result = self.writer.run("compose", payload)
        text = self.writer.read(result["packet"])["candidate"]["sections"][0]["sentences"][0]["text"]
        self.assertIn("Синтетический тезис.", text)
        self.assertIn(SOURCE, text)
        self.assertIn("Возможное возражение:", text)

    def test_render_payload_is_compatible_with_existing_working_draft(self):
        result, _ = self.compose()
        payload = json.loads((Path(result["output_dir"]) / "render-payload.json").read_text())
        original, marked, gaps = prepare_working_draft(payload["complaint"])
        self.assertEqual(original.matter_id, self.matter_id)
        self.assertEqual(marked.approvals, {})
        self.assertTrue(gaps)
        self.assertIn("ПРОВЕРИТЬ", marked.sections[0].sentences[0].text)

    def test_quote_wrong_bounds_unknown_source_and_noninteger_bounds_fail(self):
        plan = self.writer.run("plan", self.plan_input())
        for change in ({"quote": "Не тот фрагмент"}, {"start": -1}, {"end": len(SOURCE)+1},
                       {"source_id": "missing"}, {"start": False}):
            with self.subTest(change=change):
                payload = self.compose_input(plan)
                payload["arguments"][0]["evidence"][0].update(change)
                with self.assertRaises(ValueError):
                    self.writer.run("compose", payload)

    def test_unicode_locators_use_characters_not_utf8_bytes(self):
        plan = self.writer.run("plan", self.plan_input())
        payload = self.compose_input(plan)
        start = SOURCE.index("правило")
        payload["arguments"][0]["evidence"][0].update(start=start, end=start+7, quote=SOURCE[start:start+7])
        result = self.writer.run("compose", payload)
        self.assertTrue(self.writer.read(result["packet"])["arguments"][0]["evidence"][0]["quote_match"])

    def test_quoted_party_claim_cannot_fill_court_reasoning_requirements(self):
        plan = self.writer.run("plan", self.plan_input())
        payload = self.compose_input(plan)
        payload["sources"][0] = {**self.source, "role": "party_submission"}
        payload["arguments"][0]["inference_level"] = "causal"
        result = self.writer.run("compose", payload)
        self.assertTrue(any("outcome_link" in gap for gap in result["gaps"]))
        self.assertFalse(result["legal_support_verified"])

    def test_duplicate_argument_or_sentence_ids_are_rejected(self):
        plan = self.writer.run("plan", self.plan_input())
        for target in ("arguments", "sentences"):
            payload = self.compose_input(plan)
            if target == "arguments":
                payload["arguments"] *= 2
            else:
                payload["complaint"]["sections"][0]["sentences"] *= 2
            with self.assertRaises(ValueError):
                self.writer.run("compose", payload)

    def test_unknown_sentence_and_foreign_matter_are_rejected(self):
        plan = self.writer.run("plan", self.plan_input())
        for mode in ("sentence", "payload", "complaint"):
            payload = self.compose_input(plan)
            if mode == "sentence": payload["arguments"][0]["sentence_id"] = "sent-ffffffffffffffff"
            elif mode == "payload": payload["matter_id"] = "foreign"
            else: payload["complaint"]["matter_id"] = "foreign"
            with self.assertRaises(ValueError):
                self.writer.run("compose", payload)

    def test_review_revision_and_recheck_preserve_original_and_objection_history(self):
        composed, first = self.compose()
        reviewed = self.writer.run("review", self.review_input(composed, first))
        second = self.writer.read(reviewed["packet"])
        self.assertEqual(second["objections"][0]["status"], "addressed")
        revised = self.writer.run("revise", self.revision_input(reviewed, second))
        third = self.writer.read(revised["packet"])
        self.assertEqual(third["objections"][0]["status"], "needs_recheck")
        self.assertEqual(third["original"], first["original"])
        self.assertNotEqual(revised["draft_sha256"], composed["draft_sha256"])
        self.assertEqual(third["objections"][0]["history"][-1]["status"], "addressed")
        checked = self.writer.run("review", self.review_input(revised, third))
        final = self.writer.read(checked["packet"])
        self.assertEqual(final["objections"][0]["status"], "addressed")
        self.assertFalse(final["independent_legal_review"])
        self.assertEqual(self.writer.read(composed["packet"])["candidate"], first["candidate"])

    def test_review_cannot_silently_drop_or_redefine_old_objection(self):
        result, packet = self.compose()
        payload = self.review_input(result, packet)
        payload["findings"] = []
        reviewed = self.writer.run("review", payload)
        self.assertEqual(self.writer.read(reviewed["packet"])["objections"], packet["objections"])
        payload = self.review_input(result, packet)
        payload["findings"][0]["reason"] = "Иное замечание."
        with self.assertRaises(ValueError): self.writer.run("review", payload)

    def test_stale_draft_or_wording_hash_rejects_review_and_revision(self):
        result, packet = self.compose()
        for action in ("review", "revise"):
            for target in ("draft", "wording"):
                payload = self.review_input(result, packet) if action == "review" else self.revision_input(result, packet)
                if target == "draft": payload["base_draft_sha256"] = "0"*64
                elif action == "review": payload["findings"][0]["wording_sha256"] = "0"*64
                else: payload["edits"][0]["before_sha256"] = "0"*64
                with self.subTest(action=action, target=target):
                    with self.assertRaises(ValueError): self.writer.run(action, payload)

    def test_strengthened_inference_remains_visible_and_requires_review(self):
        result, packet = self.compose()
        payload = self.revision_input(result, packet)
        payload["edits"][0]["argument"].update(inference_level="causal", proposed_text="Синтетическое усиление причинного утверждения.")
        revised = self.writer.run("revise", payload)
        updated = self.writer.read(revised["packet"])
        self.assertTrue(updated["changes"][0]["inference_strengthened"])
        self.assertTrue(any("Вывод усилен" in gap for gap in revised["gaps"]))
        self.assertTrue(any("alternative_ground_analysis" in gap for gap in revised["gaps"]))
        self.assertIn("УСИЛЕНИЕ ВЫВОДА", (Path(revised["output_dir"]) / "changes.md").read_text())

    def test_unknown_objection_in_patch_fails(self):
        result, packet = self.compose()
        payload = self.revision_input(result, packet)
        payload["edits"][0]["objection_ids"] = ["absent"]
        with self.assertRaises(ValueError): self.writer.run("revise", payload)

    def test_source_cannot_be_replaced_under_existing_id(self):
        result, packet = self.compose()
        payload = self.revision_input(result, packet)
        payload["sources"] = [{**self.source, "object": self.writer.store.put_bytes(b"changed")}]
        with self.assertRaises(ValueError): self.writer.run("revise", payload)

    def test_changed_packet_artifact_and_source_are_detected(self):
        for target in ("packet", "artifact", "source"):
            with self.subTest(target=target):
                # Restore source in case an earlier subcase corrupted it.
                path = self.root / self.source["object"]["object_path"]
                path.write_bytes(SOURCE.encode())
                result, _ = self.compose()
                if target == "packet": path = self.root / result["packet"]["object_path"]
                elif target == "artifact": path = Path(result["output_dir"]) / "proposed-draft.md"
                path.write_text("changed")
                with self.assertRaises(ValueError): self.writer.read(result["packet"])

    def test_foreign_packet_and_path_escape_are_rejected(self):
        result, packet = self.compose()
        packet["matter_id"] = "foreign"
        foreign = self.writer.store.put_bytes(json.dumps(packet).encode())
        with self.assertRaises(ValueError): self.writer.read(foreign)
        payload = self.plan_input()
        plan = self.writer.run("plan", payload)
        payload = self.compose_input(plan)
        payload["sources"][0] = copy.deepcopy(self.source)
        payload["sources"][0]["object"]["object_path"] = "../../outside"
        with self.assertRaises(ValueError): self.writer.run("compose", payload)

    def test_cli_full_cycle_and_status_ignore_status_events(self):
        code, output, errors = self.cli("plan", self.plan_input())
        self.assertEqual(code, 0, errors)
        plan = output["result"]
        code, output, errors = self.cli("compose", self.compose_input(plan))
        self.assertEqual(code, 0, errors)
        composed = output["result"]
        packet = self.writer.read(composed["packet"])
        code, output, errors = self.cli("review", self.review_input(composed, packet))
        self.assertEqual(code, 0, errors)
        reviewed = output["result"]
        code, output, errors = self.cli("revise", self.revision_input(reviewed, self.writer.read(reviewed["packet"])))
        self.assertEqual(code, 0, errors)
        for _ in range(2):
            code, output, errors = self.cli("status")
            self.assertEqual(code, 0, errors)
            self.assertTrue(output["result"]["artifacts_revalidated"])
            self.assertEqual(output["result"]["latest_action"], "revise")
            self.assertFalse(output["filing_performed"])
        (Path(output["result"]["output_dir"]) / "proposed-draft.md").write_text("changed")
        code, output, errors = self.cli("status")
        self.assertEqual(code, 3, errors)
        self.assertEqual(output["result"]["reason_code"], "writing_integrity_failed")

    def test_cli_rejects_a_parent_that_is_no_longer_latest(self):
        _, first, _ = self.cli("plan", self.plan_input())
        self.cli("plan", self.plan_input())
        code, _, errors = self.cli("compose", self.compose_input(first["result"]))
        self.assertEqual(code, 2)
        self.assertIn("устарел", errors)

    def test_real_entrypoint_is_available_without_network(self):
        entrypoint = LIB.parent / "scripts/ksrf.py"
        run = subprocess.run([sys.executable, str(entrypoint), "writing", "--help"], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("предлагаемая правка", " ".join(run.stdout.split()))


if __name__ == "__main__":
    unittest.main()
