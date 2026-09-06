import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills/ksrf-argument-patterns"
SPEC = importlib.util.spec_from_file_location("proof_remedy_checker", SKILL / "scripts/check_argument.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture():
    text = "Учебный акт: основание меры и её объём проверяются отдельно."
    evidence = [{"document_id": "doc", "start": 0, "end": len(text),
                 "quote": text, "speaker": "synthetic"}]
    claims = [{"id": cid, "kind": "observation", "slot": slot, "text": text,
               "evidence": copy.deepcopy(evidence)}
              for cid, slot in (("d", "demand"), ("o", "outcome"),
                                ("g", "ground"), ("other", "ground"))]
    for claim in claims[2:]:
        claim["for_demand_ids"] = ["d"]
    issue = {field: "Условная синтетическая проверка." for field in MODULE.ISSUE_TEXT}
    issue.update(id="issue", method_ids=[], custom_method="Сопоставить оператор и объём меры.",
                 support_ids=["g"], adverse_ids=[], independent_grounds=[], unknowns=[])
    return {"mode": "prospective", "as_of": "2026-09-06",
            "documents": [{"id": "doc", "role": "hypothetical_facts", "text": text,
                           "available_on": "2026-09-06", "completeness": "complete"}],
            "claims": claims, "issues": [issue],
            "branches": [{"id": "branch", "demand_id": "d", "outcome_id": "o",
                          "ground_ids": ["g"], "independence": "single_ground"}]}


def checked_fixture():
    packet = fixture()
    for claim in packet["claims"]:
        claim["finding_operator"] = "proven"
    packet["reasoning_checks"] = {
        "operator_checks": [{"id": "op", "premise_id": "g", "conclusion_id": "o",
                             "same_proposition": True, "relation": "equivalent",
                             "explanation": "Одинаковый объявленный оператор учебного тезиса."}],
        "residual_checks": [{"id": "res", "branch_id": "branch", "remaining_ground_ids": ["g"],
                             "entitlement": {"assessment": "supported", "reason": "Основание сохраняется.",
                                             "support_ids": ["g"]},
                             "extent": {"assessment": "supported", "reason": "Объём отдельно обоснован.",
                                        "support_ids": ["g"]}}]}
    return packet


class ProofAndRemedyScopeTests(unittest.TestCase):
    def assert_invalid(self, packet):
        result = MODULE.check(packet)
        self.assertEqual(result["status"], "invalid", result)
        self.assertTrue(result["errors"])
        self.assertFalse(result["semantic_truth_verified"])
        self.assertFalse(result["filing_ready"])

    def test_declared_finding_operator_is_checked_without_reasoning_checks(self):
        for value in (None, False, 1, [], {}, "", "PROVEN", "not-proven"):
            with self.subTest(value=value):
                packet = fixture()
                packet["claims"][0]["finding_operator"] = value
                result = MODULE.check(packet)
                self.assertEqual(result["status"], "invalid")
                self.assertIn("finding_operator", result["errors"][0])
                self.assertFalse(result["semantic_truth_verified"])

    def test_declared_operator_enum_and_legacy_packets_are_valid(self):
        for value in MODULE.FINDING_OPERATORS:
            with self.subTest(value=value):
                packet = fixture()
                packet["claims"][0]["finding_operator"] = value
                self.assertEqual(MODULE.check(packet)["status"], "structurally_traceable_candidate")
        self.assertEqual(MODULE.check(fixture())["status"], "structurally_traceable_candidate")

    def test_optional_checks_report_presence_counts_and_no_truth_without_mutation(self):
        legacy = MODULE.check(fixture())
        self.assertEqual(legacy["reasoning_checks"], {"provided": False, "operator_checks_checked": 0,
                         "residual_checks_checked": 0, "semantic_truth_verified": False})
        packet = checked_fixture()
        original = copy.deepcopy(packet)
        result = MODULE.check(packet)
        self.assertEqual(packet, original)
        self.assertEqual(result["status"], "structurally_traceable_candidate")
        self.assertEqual(result["reasoning_checks"], {"provided": True, "operator_checks_checked": 1,
                         "residual_checks_checked": 1, "semantic_truth_verified": False})
        self.assertFalse(result["semantic_truth_verified"])
        self.assertFalse(result["historical_eval_allowed"])
        packet["reasoning_checks"] = {"operator_checks": [], "residual_checks": []}
        self.assertTrue(MODULE.check(packet)["reasoning_checks"]["provided"])

    def test_checks_object_and_both_lists_are_required_if_provided(self):
        for value in (None, False, [], "", {}, {"operator_checks": []}, {"residual_checks": []}):
            with self.subTest(value=value):
                packet = fixture(); packet["reasoning_checks"] = value
                self.assert_invalid(packet)
        for field in ("operator_checks", "residual_checks"):
            for value in (None, False, {}, "", [None], [{"id": " "}]):
                with self.subTest(field=field, value=value):
                    packet = checked_fixture(); packet["reasoning_checks"][field] = value
                    self.assert_invalid(packet)

    def test_different_known_operators_and_different_propositions_are_not_equivalent(self):
        for left in MODULE.FINDING_OPERATORS - {"unknown"}:
            for right in MODULE.FINDING_OPERATORS - {"unknown", left}:
                with self.subTest(left=left, right=right):
                    packet = checked_fixture()
                    packet["claims"][2]["finding_operator"] = left
                    packet["claims"][1]["finding_operator"] = right
                    self.assert_invalid(packet)
        packet = checked_fixture()
        packet["reasoning_checks"]["operator_checks"][0]["same_proposition"] = False
        self.assert_invalid(packet)

    def test_missing_unknown_and_additional_premise_are_evidence_gaps(self):
        for index in (1, 2):
            for missing in (True, False):
                packet = checked_fixture()
                if missing:
                    packet["claims"][index].pop("finding_operator")
                else:
                    packet["claims"][index]["finding_operator"] = "unknown"
                result = MODULE.check(packet)
                self.assertEqual(result["status"], "needs_evidence")
                self.assertTrue(result["gaps"])
        packet = checked_fixture()
        packet["reasoning_checks"]["operator_checks"][0].update(
            relation="requires_additional_premise", same_proposition=False)
        packet["claims"][2]["finding_operator"] = "not_proven"
        result = MODULE.check(packet)
        self.assertEqual(result["status"], "needs_evidence")
        self.assertTrue(any("дополнительная посылка" in gap for gap in result["gaps"]))

    def test_operator_fields_types_references_and_explanation_fail_closed(self):
        bad = {"premise_id": ["missing", None, True, []], "conclusion_id": ["missing", {}, 1],
               "same_proposition": [None, 0, 1, "true", []],
               "relation": [None, True, [], "typo"], "explanation": [None, True, [], " "]}
        for field, values in bad.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    packet = checked_fixture()
                    packet["reasoning_checks"]["operator_checks"][0][field] = value
                    self.assert_invalid(packet)
            packet = checked_fixture()
            packet["reasoning_checks"]["operator_checks"][0].pop(field)
            self.assert_invalid(packet)

    def test_duplicate_check_ids_fail_within_and_between_lists(self):
        for field in ("operator_checks", "residual_checks"):
            packet = checked_fixture()
            packet["reasoning_checks"][field].append(copy.deepcopy(packet["reasoning_checks"][field][0]))
            self.assert_invalid(packet)
        packet = checked_fixture()
        packet["reasoning_checks"]["residual_checks"][0]["id"] = "op"
        self.assert_invalid(packet)

    def test_residual_requires_distinct_entitlement_and_extent_objects(self):
        for field in ("entitlement", "extent"):
            for value in (None, False, True, [], "supported"):
                with self.subTest(field=field, value=value):
                    packet = checked_fixture()
                    packet["reasoning_checks"]["residual_checks"][0][field] = value
                    self.assert_invalid(packet)
            packet = checked_fixture()
            packet["reasoning_checks"]["residual_checks"][0].pop(field)
            self.assert_invalid(packet)

    def test_residual_branch_and_remaining_ground_ids_are_scoped(self):
        bad = {"branch_id": [None, True, [], "missing"],
               "remaining_ground_ids": [None, True, "g", [False], ["g", "g"],
                                        ["missing"], ["other"], ["d"], ["o"]]}
        for field, values in bad.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    packet = checked_fixture()
                    packet["reasoning_checks"]["residual_checks"][0][field] = value
                    self.assert_invalid(packet)
            packet = checked_fixture()
            packet["reasoning_checks"]["residual_checks"][0].pop(field)
            self.assert_invalid(packet)
        packet = checked_fixture(); packet.pop("branches")
        self.assert_invalid(packet)
        packet = checked_fixture()
        packet["claims"][2]["for_demand_ids"] = []
        self.assert_invalid(packet)

    def test_residual_assessment_fields_and_support_are_required_and_scoped(self):
        bad = {"assessment": [None, True, False, [], "typo"],
               "reason": [None, False, [], " "],
               "support_ids": [None, False, "g", [1], ["missing"], ["other"], []]}
        for side in ("entitlement", "extent"):
            for field, values in bad.items():
                for value in values:
                    with self.subTest(side=side, field=field, value=value):
                        packet = checked_fixture()
                        packet["reasoning_checks"]["residual_checks"][0][side][field] = value
                        self.assert_invalid(packet)
                packet = checked_fixture()
                packet["reasoning_checks"]["residual_checks"][0][side].pop(field)
                self.assert_invalid(packet)

    def test_branch_ground_removed_from_remainder_cannot_support_either_assessment(self):
        for side in ("entitlement", "extent"):
            packet = checked_fixture()
            packet["branches"][0].update(ground_ids=["g", "other"], independence="interdependent")
            packet["reasoning_checks"]["residual_checks"][0][side]["support_ids"] = ["other"]
            self.assert_invalid(packet)

    def test_unknown_extent_is_not_filled_by_supported_entitlement(self):
        for side in ("entitlement", "extent"):
            packet = checked_fixture()
            packet["reasoning_checks"]["residual_checks"][0][side].update(assessment="unknown", support_ids=[])
            result = MODULE.check(packet)
            self.assertEqual(result["status"], "needs_evidence")
            self.assertTrue(any(f"res.{side}" in gap for gap in result["gaps"]))
            self.assertFalse(result["reasoning_checks"]["semantic_truth_verified"])

    def test_empty_remainder_allows_only_unsupported_or_unknown_assessments(self):
        for value, status in (("not_supported", "structurally_traceable_candidate"),
                              ("unknown", "needs_evidence"), ("supported", "invalid")):
            with self.subTest(value=value):
                packet = checked_fixture()
                row = packet["reasoning_checks"]["residual_checks"][0]
                row["remaining_ground_ids"] = []
                for side in ("entitlement", "extent"):
                    row[side].update(assessment=value, support_ids=[])
                result = MODULE.check(packet)
                self.assertEqual(result["status"], status, result)

    def test_matching_known_operators_do_not_verify_textual_identity_or_truth(self):
        for value in MODULE.FINDING_OPERATORS - {"unknown"}:
            packet = checked_fixture()
            packet["claims"][1].update(finding_operator=value, text="Другой учебный текст вывода.")
            packet["claims"][2]["finding_operator"] = value
            result = MODULE.check(packet)
            self.assertEqual(result["status"], "structurally_traceable_candidate")
            self.assertFalse(result["semantic_truth_verified"])
            self.assertFalse(result["claim_checks"]["o"]["meaning_verified"])

    def test_all_new_fields_change_full_context_hash(self):
        base = checked_fixture()
        base["branches"][0].update(ground_ids=["g", "other"], independence="interdependent")
        base["branches"].append(dict(base["branches"][0], id="branch2"))
        base["reasoning_checks"]["residual_checks"][0]["remaining_ground_ids"] = ["g", "other"]
        first = MODULE.check(base)
        self.assertEqual(first["status"], "structurally_traceable_candidate")
        mutations = [
            (("claims", 0, "finding_operator"), "not_proven"),
            (("reasoning_checks", "operator_checks", 0, "id"), "op2"),
            (("reasoning_checks", "operator_checks", 0, "premise_id"), "other"),
            (("reasoning_checks", "operator_checks", 0, "conclusion_id"), "other"),
            (("reasoning_checks", "operator_checks", 0, "relation"), "requires_additional_premise"),
            (("reasoning_checks", "operator_checks", 0, "explanation"), "Иное объяснение."),
            (("reasoning_checks", "residual_checks", 0, "id"), "res2"),
            (("reasoning_checks", "residual_checks", 0, "branch_id"), "branch2"),
            (("reasoning_checks", "residual_checks", 0, "remaining_ground_ids"), ["g"]),
        ]
        for side in ("entitlement", "extent"):
            prefix = ("reasoning_checks", "residual_checks", 0, side)
            mutations.extend([(prefix + ("assessment",), "unknown"),
                              (prefix + ("reason",), "Новое обоснование."),
                              (prefix + ("support_ids",), ["other"])])
        for path, value in mutations:
            with self.subTest(path=path):
                packet = copy.deepcopy(base); target = packet
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                result = MODULE.check(packet)
                self.assertIn(result["status"], ("structurally_traceable_candidate", "needs_evidence"), result)
                self.assertNotEqual(first["input_context_sha256"], result["input_context_sha256"])
                self.assertEqual(first["source_sha256"], result["source_sha256"])
        base["reasoning_checks"]["operator_checks"][0]["relation"] = "requires_additional_premise"
        before = MODULE.check(base)["input_context_sha256"]
        base["reasoning_checks"]["operator_checks"][0]["same_proposition"] = False
        self.assertNotEqual(before, MODULE.check(base)["input_context_sha256"])
        packet = fixture(); before = MODULE.check(packet)["input_context_sha256"]
        packet["reasoning_checks"] = {"operator_checks": [], "residual_checks": []}
        self.assertNotEqual(before, MODULE.check(packet)["input_context_sha256"])

    def test_new_checks_do_not_open_historical_or_backdated_evaluation(self):
        for change in ({"mode": "historical"}, {"as_of": "2026-09-05"}):
            packet = checked_fixture(); packet.update(change)
            result = MODULE.check(packet)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["historical_eval_allowed"])

    def test_copied_skill_runs_without_corpus_or_network(self):
        with tempfile.TemporaryDirectory(prefix="proof-remedy-standalone-") as temp:
            root = Path(temp)
            for rel in ("scripts/check_argument.py", "references/universal-methods.json"):
                destination = root / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SKILL / rel, destination)
            wrapper = '''
import sys, pathlib, runpy, socket, subprocess, argparse, hashlib, json, re, datetime
root = pathlib.Path.cwd().resolve()
stdlib = pathlib.Path(json.__file__).resolve().parent.parent
def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.")) or event in ("os.system", "os.exec", "os.spawn"):
        raise PermissionError("forbidden external operation")
    if event == "open" and not isinstance(args[0], int):
        path = pathlib.Path(args[0]).resolve()
        if not path.is_relative_to(root) and not path.is_relative_to(stdlib):
            raise PermissionError("outside copied skill")
sys.addaudithook(guard)
try:
    socket.socket()
    raise AssertionError("network guard inactive")
except PermissionError:
    pass
try:
    pathlib.Path("/outside-copied-skill.json").read_text()
    raise AssertionError("file guard inactive")
except PermissionError:
    pass
sys.argv = [str(root / "scripts/check_argument.py"), str(root / "input.json")]
runpy.run_path(sys.argv[0], run_name="__main__")
'''
            valid = checked_fixture()
            gap = copy.deepcopy(valid)
            gap["reasoning_checks"]["residual_checks"][0]["extent"].update(assessment="unknown", support_ids=[])
            invalid = copy.deepcopy(valid)
            invalid["claims"][2]["finding_operator"] = "not_proven"
            invalid["claims"][1]["finding_operator"] = "proven_not"
            for packet, status, exit_code in ((valid, "structurally_traceable_candidate", 0),
                                             (gap, "needs_evidence", 2), (invalid, "invalid", 2)):
                with self.subTest(status=status):
                    (root / "input.json").write_text(json.dumps(packet, ensure_ascii=False))
                    run = subprocess.run([sys.executable, "-I", "-B", "-c", wrapper], cwd=root,
                                         text=True, capture_output=True, timeout=15)
                    self.assertEqual(run.returncode, exit_code, run.stderr + run.stdout)
                    result = json.loads(run.stdout)
                    self.assertEqual(result["status"], status)
                    self.assertFalse(result["requires_source_corpus"])
                    self.assertFalse(result["semantic_truth_verified"])
                    self.assertFalse(result["filing_ready"])
                    self.assertFalse(result["historical_eval_allowed"])
                    if status != "invalid":
                        self.assertEqual(result["input_context_sha256"], MODULE.check(packet)["input_context_sha256"])
                        self.assertEqual(result["reasoning_checks"]["operator_checks_checked"], 1)
                        self.assertEqual(result["reasoning_checks"]["residual_checks_checked"], 1)


if __name__ == "__main__":
    unittest.main()
