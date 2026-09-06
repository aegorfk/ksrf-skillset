"""Offline observability contracts; synthetic metadata, no legal-quality claims."""
import asyncio
from contextlib import nullcontext
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


TOOL = Path(__file__).resolve().parents[1] / "tools/argument_probe_observability.py"
SPEC = importlib.util.spec_from_file_location("argument_probe_observability", TOOL)
bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bridge)


def source():
    text = "Synthetic locator fixture."
    return {"source_id": "S1", "locator": "pages 2-3", "text": text,
            "text_sha256": bridge.hashlib.sha256(text.encode()).hexdigest()}


def metadata():
    return {"experiment_id": bridge.EXPERIMENT, "hypothesis_id": "H1", "call_id": "baseline",
            "model": "gpt-6-astra", "provider": "openai_via_codex_cli",
            "model_reasoning_effort": "xhigh", "service_tier": "priority",
            "status": "completed", "prompt_sha256": "a" * 64, "output_sha256": "b" * 64,
            "packet_sha256": "c" * 64, "tool_sha256": "d" * 64,
            "elapsed_seconds": 1.5, "price": None, "token_usage": None,
            "isolation": {"private_path": "DO-NOT-LOG"}, "error_class": "PRIVATE-ERROR"}


def make_run(directory: Path, *, call="baseline", review_output=False, hypothesis="H1"):
    runner_path = bridge.REPO_ROOT / "tools/run_argument_method_probe.py"
    runner = bridge.load_runner(runner_path, bridge.file_hash(runner_path))
    item = source()
    item.update(role="technical_fixture", document_sha256="a" * 64)
    packet = {"schema_version": "1.0", "hypothesis_id": hypothesis, "task": "Inspect fixture.",
              "intervention": "Check alternative.", "sources": [item], "coverage_gaps": [],
              "output_word_limit": 700}
    directory.mkdir(parents=True, exist_ok=True)
    bridge.private_json(directory / "packet.json", packet)
    output = {"answer": call + " fixture", "citations": [{"source_id": "S1", "locator": "pages 2-3"}],
              "uncertainties": []}
    if review_output:
        for arm in ("baseline", "candidate"):
            make_run(directory, call=arm, hypothesis=hypothesis)
        output = {"assessments": [{"label": label, "dimensions": [
            {"name": dimension, "score": None, "reason": "Unknown fixture", "citations": []}
            for dimension in bridge.DIMENSIONS], "critical_defects": [], "coverage": "insufficient"}
            for label in ("A", "B")], "preference": "insufficient", "reason": "Fixture only"}
        prompt = runner.build_review_prompt(packet, bridge.read_json(directory / "baseline.json"),
            bridge.read_json(directory / "candidate.json"), reverse=call == "review-reversed")
    else:
        prompt = runner.build_trial_prompt(packet, call)
    (directory / f"{call}.prompt.txt").write_text(prompt, encoding="utf-8")
    bridge.private_json(directory / f"{call}.json", output)
    receipt = metadata()
    receipt.update(call_id=call, hypothesis_id=hypothesis, kind="review" if review_output else "trial",
                   prompt_version=bridge.EXPERIMENT + (".review" if review_output else ".trial"),
                   prompt_sha256=bridge.hashlib.sha256(prompt.encode()).hexdigest(),
                   output_sha256=bridge.file_hash(directory / f"{call}.json"),
                   packet_sha256=bridge.canonical_hash(packet), tool_sha256=bridge.file_hash(runner_path))
    bridge.private_json(directory / f"{call}.metadata.json", receipt)
    return packet, receipt


class LocatorTests(unittest.TestCase):
    def test_exact_is_mechanical_only(self):
        result = bridge.locator_diagnostic([{"source_id": "S1", "locator": "pages 2-3"}], [source()])
        self.assertEqual(result["score"], 1)
        self.assertFalse(result["semantic_grounding_verified"])

    def test_unknown_source_is_invalid(self):
        result = bridge.locator_diagnostic([{"source_id": "not-present", "locator": "pages 2-3"}], [source()])
        self.assertEqual(result["score"], 0)

    def test_empty_locator_is_invalid(self):
        self.assertEqual(bridge.locator_diagnostic([{"source_id": "S1", "locator": " "}], [source()])["score"], 0)

    def test_narrower_locator_is_unknown_not_failure(self):
        result = bridge.locator_diagnostic([{"source_id": "S1", "locator": "page 2"}], [source()])
        self.assertIsNone(result["score"])
        self.assertEqual(result["unverified_locator"], 1)

    def test_no_citations_is_unknown_not_vacuous_pass(self):
        self.assertIsNone(bridge.locator_diagnostic([], [source()])["score"])

    def test_duplicate_sources_rejected(self):
        with self.assertRaises(ValueError):
            bridge.locator_diagnostic([], [source(), source()])


class TelemetryTests(unittest.TestCase):
    def test_allowlist_excludes_arbitrary_text_and_paths(self):
        value = metadata()
        value.update({"prompt": "DO-NOT-LOG", "answer": "PRIVATE", "secret": "CREDENTIAL"})
        output = json.dumps(bridge.telemetry_metadata(value))
        for forbidden in ("DO-NOT-LOG", "PRIVATE", "CREDENTIAL"):
            self.assertNotIn(forbidden, output)

    def test_unknown_cost_and_usage_stay_null(self):
        result = bridge.telemetry_metadata(metadata())
        self.assertIsNone(result["price"])
        self.assertIsNone(result["token_usage"])
        self.assertTrue(result["price_unknown"])

    def test_numeric_usage_allowlisted(self):
        value = metadata()
        value["token_usage"] = {"input_tokens": 4, "output_tokens": 2, "untrusted": "PRIVATE"}
        self.assertEqual(bridge.telemetry_metadata(value)["token_usage"], {"input_tokens": 4, "output_tokens": 2})

    def test_wrong_model_and_bad_hash_fail_closed(self):
        for key, value in (("model", "unregistered"), ("prompt_sha256", "plaintext")):
            altered = metadata()
            altered[key] = value
            with self.assertRaises(ValueError):
                bridge.telemetry_metadata(altered)

    def test_nonfinite_price_is_not_emitted(self):
        altered = metadata()
        altered["price"] = float("nan")
        with self.assertRaises(ValueError):
            bridge.telemetry_metadata(altered)

    def test_stale_score_readback_fails(self):
        trace = SimpleNamespace(id="t", name=bridge.EXPERIMENT,
            metadata={"experiment_id": bridge.EXPERIMENT, "artifact_sha256": "a"},
            observations=[SimpleNamespace(type="GENERATION", name="H1.baseline", metadata={"receipt_sha256": "x"})],
            scores=[SimpleNamespace(name="quality", value=0)])
        client = SimpleNamespace(api=SimpleNamespace(trace=SimpleNamespace(get=lambda **_: trace)))
        with self.assertRaises(RuntimeError):
            bridge.readback(client, "t", expected_hash="a", score_names={"quality"},
                            expected_scores={"quality": 2}, timeout=0)

    def test_reports_private_and_outside_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            bridge.private_json(path, {"score": None})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIsNone(bridge.read_json(path)["score"])
        with self.assertRaises(ValueError):
            bridge.private_json(bridge.REPO_ROOT / "forbidden-report.json", {})


class ReceiptTests(unittest.TestCase):
    def test_canonical_packet_binding_does_not_depend_on_pretty_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet, receipt = make_run(root / "H1")
            self.assertNotEqual(bridge.file_hash(root / "H1/packet.json"), receipt["packet_sha256"])
            checked, _ = bridge.validate_receipt(root, "H1", "baseline")
            self.assertEqual(checked["packet_sha256"], bridge.canonical_hash(packet))

    def test_swapped_receipt_fails_arm_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, receipt = make_run(root / "H1")
            receipt["call_id"] = "candidate"
            bridge.private_json(root / "H1/baseline.metadata.json", receipt)
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                bridge.validate_receipt(root, "H1", "baseline")

    def test_modified_prompt_and_rehashed_receipt_still_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, receipt = make_run(root / "H1")
            prompt = root / "H1/baseline.prompt.txt"
            prompt.write_text("Tampered but consistently rehashed prompt", encoding="utf-8")
            receipt["prompt_sha256"] = bridge.file_hash(prompt)
            bridge.private_json(root / "H1/baseline.metadata.json", receipt)
            with self.assertRaisesRegex(ValueError, "Prompt hash mismatch"):
                bridge.validate_receipt(root, "H1", "baseline")

    def test_wrong_review_order_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_run(root / "H1", call="review-forward", review_output=True)
            _, receipt = make_run(root / "H1", call="review-reversed", review_output=True)
            forward = root / "H1/review-forward.prompt.txt"
            reverse = root / "H1/review-reversed.prompt.txt"
            reverse.write_bytes(forward.read_bytes())
            receipt["prompt_sha256"] = bridge.file_hash(reverse)
            bridge.private_json(root / "H1/review-reversed.metadata.json", receipt)
            with self.assertRaisesRegex(ValueError, "Prompt hash mismatch"):
                bridge.validate_receipt(root, "H1", "review-reversed")


@unittest.skipUnless(importlib.util.find_spec("deepeval"), "requires registered DeepEval runtime")
class DeepEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case_type, cls.locator_type, cls.dimension_type = bridge.deepeval_types()

    def test_actual_basemetric_no_model_and_async_unknown(self):
        from deepeval.metrics import BaseMetric
        metric = self.locator_type()
        self.assertIsInstance(metric, BaseMetric)
        case = self.case_type(input="synthetic", actual_output="fixture",
                              metadata={"citations": [], "sources": [source()]})
        self.assertIsNone(asyncio.run(metric.a_measure(case)))
        self.assertIsNone(metric.is_successful())
        self.assertIsNone(metric.model)

    def test_frozen_score_is_consumed_not_rejudged(self):
        metric = self.dimension_type("source_fidelity")
        case = self.case_type(input="synthetic", actual_output="fixture", metadata={"dimension":
            {"name": "source_fidelity", "score": 2, "reason": "Frozen fixture reason"}})
        self.assertEqual(metric.measure(case), 2)
        self.assertIsNone(metric.is_successful())
        self.assertIsNone(metric.model)

    def test_frozen_unknown_is_not_zero(self):
        metric = self.dimension_type("source_fidelity")
        case = self.case_type(input="synthetic", actual_output="fixture", metadata={"dimension":
            {"name": "source_fidelity", "score": None, "reason": "Insufficient source coverage"}})
        self.assertIsNone(metric.measure(case))
        self.assertTrue(metric.skipped)

    def test_invalid_frozen_values_rejected(self):
        for score in (True, -1, 3, "2"):
            metric = self.dimension_type("source_fidelity")
            case = self.case_type(input="synthetic", actual_output="fixture", metadata={"dimension":
                {"name": "source_fidelity", "score": score, "reason": "fixture"}})
            with self.assertRaises(ValueError):
                metric.measure(case)

    def test_partial_run_reports_missing_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge.private_json(root / "packets/H1.json", {"sources": [source()]})
            report = bridge.diagnose(root / "packets", root / "runs", ("H1",))
            self.assertEqual(len(report["missing"]), 4)
            self.assertEqual(report["completed_calls"], 0)
            self.assertFalse(report["scope_complete"])
            self.assertFalse(report["all_ten_complete"])

    def test_publish_preserves_unknowns_and_only_emits_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet, _ = make_run(root / "runs/H1", call="review-forward", review_output=True)
            bridge.private_json(root / "packets/H1.json", packet)
            report = bridge.diagnose(root / "packets", root / "runs", ("H1",))
            bridge.private_json(root / "diagnostics.json", report)
            self.assertEqual(report["unknown_score_count"], 10)
            client = mock.MagicMock()
            client.start_as_current_observation.side_effect = lambda **_: nullcontext()
            with mock.patch.dict(sys.modules, {"langfuse": SimpleNamespace(
                    propagate_attributes=lambda **_: nullcontext())}), \
                    mock.patch.object(bridge, "langfuse_client", return_value=client), \
                    mock.patch.object(bridge, "readback", return_value={"authenticated_readback": True}) as readback:
                receipt = bridge.publish(root / "runs", root / "diagnostics.json", root / "unused.env", ("H1",))
            self.assertEqual(receipt["unknown_score_count"], 10)
            self.assertEqual(receipt["completed_call_count"], 3)
            self.assertFalse(receipt["all_ten_complete"])
            client.create_score.assert_not_called()
            readback.assert_called_once()
            self.assertEqual(len(readback.call_args.kwargs["expected_generations"]), 3)
            for invocation in client.start_as_current_observation.call_args_list:
                encoded = json.dumps(invocation.kwargs)
                self.assertNotIn("Synthetic locator fixture.", encoded)
                self.assertNotIn("Unknown fixture", encoded)
                self.assertNotIn("DO-NOT-LOG", encoded)

    def test_publish_rejects_rewritten_judge_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet, _ = make_run(root / "runs/H1", call="review-forward", review_output=True)
            bridge.private_json(root / "packets/H1.json", packet)
            report = bridge.diagnose(root / "packets", root / "runs", ("H1",))
            report["rows"][-1]["metrics"][0]["score"] = 2
            bridge.private_json(root / "diagnostics.json", report)
            with mock.patch.dict(sys.modules, {"langfuse": SimpleNamespace(
                    propagate_attributes=lambda **_: nullcontext())}):
                with self.assertRaisesRegex(ValueError, "changed the frozen"):
                    bridge.publish(root / "runs", root / "diagnostics.json", root / "unused.env", ("H1",))

    def test_publish_rejects_injected_trial_and_failed_review_metrics(self):
        for call, status in (("baseline", "completed"), ("candidate", "completed"),
                             ("baseline", "failed"), ("review-forward", "failed")):
            with self.subTest(call=call, status=status), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                packet, receipt = make_run(root / "runs/H1", call=call,
                                           review_output=call.startswith("review"))
                if status == "failed":
                    receipt.update(status="failed", output_sha256=None)
                    bridge.private_json(root / f"runs/H1/{call}.metadata.json", receipt)
                bridge.private_json(root / "packets/H1.json", packet)
                report = bridge.diagnose(root / "packets", root / "runs", ("H1",))
                row = next(item for item in report["rows"] if item["call_id"] == call)
                row["metrics"] = [{"label": "A", "dimension": "source_fidelity", "score": 2}]
                bridge.private_json(root / "diagnostics.json", report)
                with mock.patch.dict(sys.modules, {"langfuse": SimpleNamespace(
                        propagate_attributes=lambda **_: nullcontext())}), \
                        mock.patch.object(bridge, "langfuse_client") as connect:
                    with self.assertRaisesRegex(ValueError, "Only completed reviews"):
                        bridge.publish(root / "runs", root / "diagnostics.json", root / "unused.env", ("H1",))
                    connect.assert_not_called()

    def test_all_ten_complete_uses_actual_receipts_not_diagnostic_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for hypothesis in bridge.HYPOTHESES:
                for call in ("review-forward", "review-reversed"):
                    packet, _ = make_run(root / "runs" / hypothesis, call=call,
                                         review_output=True, hypothesis=hypothesis)
                bridge.private_json(root / "packets" / f"{hypothesis}.json", packet)
            for failed in (False, True):
                if failed:
                    path = root / "runs/H10/review-reversed.metadata.json"
                    metadata = bridge.read_json(path)
                    metadata.update(status="failed", output_sha256=None)
                    bridge.private_json(path, metadata)
                report = bridge.diagnose(root / "packets", root / "runs", bridge.HYPOTHESES)
                report["all_ten_complete"] = failed  # Opposite of the actual receipts.
                bridge.private_json(root / "diagnostics.json", report)
                client = mock.MagicMock()
                client.start_as_current_observation.side_effect = lambda **_: nullcontext()
                with mock.patch.dict(sys.modules, {"langfuse": SimpleNamespace(
                        propagate_attributes=lambda **_: nullcontext())}), \
                        mock.patch.object(bridge, "langfuse_client", return_value=client), \
                        mock.patch.object(bridge, "readback", return_value={"authenticated_readback": True}):
                    receipt = bridge.publish(root / "runs", root / "diagnostics.json", root / "unused.env", bridge.HYPOTHESES)
                self.assertEqual(receipt["all_ten_complete"], not failed)
                self.assertEqual(receipt["failed_call_count"], int(failed))


if __name__ == "__main__":
    unittest.main()
