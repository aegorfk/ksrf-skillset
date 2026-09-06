"""Neutral technical fixtures, not invented legal cases or legal-quality gold."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("argument_probe", Path(__file__).resolve().parents[1] / "tools/run_argument_method_probe.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def packet():
    text = "Neutral source text for transport-contract testing."
    return {"schema_version": "1.0", "hypothesis_id": "H1", "task": "Inspect this text.",
            "intervention": "INTERVENTION_SENTINEL", "coverage_gaps": ["COVERAGE_SENTINEL"],
            "output_word_limit": 700,
            "sources": [{"source_id": "S1", "role": "technical_fixture", "locator": "line 1",
                         "text": text, "text_sha256": probe.sha256(text.encode()), "document_sha256": "a" * 64}]}


def answer(label="answer"):
    return {"answer": label, "citations": [{"source_id": "S1", "locator": "line 1"}], "uncertainties": []}


def review():
    return {"assessments": [{"label": label, "dimensions": [
        {"name": name, "score": None, "reason": "Unavailable", "citations": []}
        for name in probe.DIMENSIONS], "critical_defects": [], "coverage": "insufficient"}
        for label in ("A", "B")], "preference": "insufficient", "reason": "Missing coverage"}


class PacketTests(unittest.TestCase):
    def test_valid_packet(self):
        probe.validate_packet(packet())

    def test_text_hash_mismatch(self):
        item = packet()
        item["sources"][0]["text"] += " changed"
        with self.assertRaisesRegex(ValueError, "text_sha256"):
            probe.validate_packet(item)

    def test_duplicate_source(self):
        item = packet()
        item["sources"].append(copy.deepcopy(item["sources"][0]))
        with self.assertRaises(ValueError):
            probe.validate_packet(item)

    def test_invalid_hypothesis_and_limits(self):
        for key, value in (("hypothesis_id", "H11"), ("output_word_limit", True), ("output_word_limit", 99)):
            item = packet()
            item[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                probe.validate_packet(item)

    def test_common_prompt_and_single_intervention(self):
        baseline = probe.build_trial_prompt(packet(), "baseline")
        candidate = probe.build_trial_prompt(packet(), "candidate")
        self.assertTrue(candidate.startswith(baseline))
        self.assertNotIn("INTERVENTION_SENTINEL", baseline)
        self.assertEqual(candidate.count("INTERVENTION_SENTINEL"), 1)
        self.assertIn("COVERAGE_SENTINEL", baseline)
        self.assertNotIn('"hypothesis_id"', candidate)

    def test_concealed_and_reversed_review(self):
        item = packet()
        item["gold_answer"] = "SECRET_EXPECTATION"
        forward = probe.build_review_prompt(item, answer("BASE_SENTINEL"), answer("CAND_SENTINEL"))
        backward = probe.build_review_prompt(item, answer("BASE_SENTINEL"), answer("CAND_SENTINEL"), reverse=True)
        for prompt in (forward, backward):
            self.assertNotIn("INTERVENTION_SENTINEL", prompt)
            self.assertNotIn("SECRET_EXPECTATION", prompt)
            self.assertNotIn('"hypothesis_id"', prompt)
        self.assertLess(forward.index("BASE_SENTINEL"), forward.index("CAND_SENTINEL"))
        self.assertGreater(backward.index("BASE_SENTINEL"), backward.index("CAND_SENTINEL"))


class OutputTests(unittest.TestCase):
    def test_valid_trial_and_unknown_review(self):
        probe.validate_output(answer())
        probe.validate_output(review(), review=True)

    def test_boolean_is_not_integer_score(self):
        item = review()
        item["assessments"][0]["dimensions"][0]["score"] = True
        with self.assertRaises(ValueError):
            probe.validate_output(item, review=True)

    def test_exact_labels_and_dimensions(self):
        for mutation in ("duplicate_label", "duplicate_dimension", "missing_dimension"):
            item = review()
            if mutation == "duplicate_label":
                item["assessments"][1]["label"] = "A"
            elif mutation == "duplicate_dimension":
                item["assessments"][0]["dimensions"][0]["name"] = probe.DIMENSIONS[1]
            else:
                item["assessments"][0]["dimensions"].pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                probe.validate_output(item, review=True)

    def test_forbid_extra_output_keys(self):
        item = answer()
        item["chain_of_thought"] = "not accepted"
        with self.assertRaises(ValueError):
            probe.validate_output(item)

    def test_usage_and_tool_detection(self):
        events = '\n'.join([json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 4}}),
                            json.dumps({"type": "item.completed", "item": {"type": "command_execution"}})])
        usage, detected = probe.extract_usage(events)
        self.assertEqual(usage["output_tokens"], 4)
        self.assertTrue(detected)
        self.assertEqual(probe.extract_usage("not json"), (None, False))


class RuntimeTests(unittest.TestCase):
    def test_explicit_model_and_isolation_config(self):
        command = probe.build_command(probe.CODEX_BIN, Path("/private/task"), Path("/private/schema"), Path("/private/result"))
        self.assertIn("gpt-6-astra", command)
        self.assertIn('model_reasoning_effort="xhigh"', command)
        self.assertIn('service_tier="priority"', command)
        self.assertIn(probe.FS_CONFIG, command)
        self.assertIn(probe.NET_CONFIG, command)
        self.assertIn("skip_host_skill_discovery", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_private_output_rejects_git_and_broad_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".git").write_text("gitdir: elsewhere")
            with self.assertRaises(ValueError):
                probe.private_directory(root / "private")
        for selected in (Path("/"), Path.home(), Path("relative")):
            with self.assertRaises(ValueError):
                probe.private_directory(selected)

    def test_atomic_json_is_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "receipt.json"
            probe.atomic_json(target, {"price": None})
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertIsNone(json.loads(target.read_bytes())["price"])

    def test_timeout_retained_and_not_silently_retried(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(probe, "verify_isolation", return_value={"verified": True}), \
                    patch.object(probe.subprocess, "run", side_effect=subprocess.TimeoutExpired("codex", 1)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    probe.run_call("text", output_dir=root, label="baseline", hypothesis_id="H1", timeout_seconds=1)
            receipt = json.loads((root / "baseline.metadata.json").read_bytes())
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(receipt["error_class"], "timeout")
            self.assertIsNone(receipt["price"])
            self.assertIsNone(receipt["token_usage"])
            self.assertGreaterEqual(receipt["elapsed_seconds"], 0)
            with self.assertRaises(FileExistsError):
                probe.run_call("text", output_dir=root, label="baseline", hypothesis_id="H1")

    def test_success_preserves_final_only_and_usage(self):
        def fake_run(command, **kwargs):
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text(json.dumps(answer()))
            events = json.dumps({"type": "turn.completed", "usage": {"input_tokens": 2, "output_tokens": 5}})
            return subprocess.CompletedProcess(command, 0, events, "private stderr must not be recorded")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(probe, "verify_isolation", return_value={"verified": True}), patch.object(probe.subprocess, "run", side_effect=fake_run):
                receipt = probe.run_call("input", output_dir=root, label="baseline", hypothesis_id="H1")
            self.assertEqual(receipt["status"], "completed")
            self.assertEqual(receipt["token_usage"]["output_tokens"], 5)
            self.assertEqual(receipt["output_sha256"], probe.sha256((root / "baseline.json").read_bytes()))
            self.assertNotIn("private stderr", json.dumps(receipt))

    def test_isolation_requires_positive_control(self):
        completed = subprocess.CompletedProcess([], 1, b"", b"denied")
        with patch.object(probe.subprocess, "run", return_value=completed), self.assertRaises(RuntimeError):
            probe.verify_isolation(probe.CODEX_BIN, Path("/workspace"), Path("/secret"))

    def test_failed_process_retains_private_stderr_not_stdout(self):
        failed = subprocess.CompletedProcess([], 1, "do not retain model reasoning", "transport diagnostic")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(probe, "verify_isolation", return_value={"verified": True}), \
                    patch.object(probe.subprocess, "run", return_value=failed), self.assertRaises(RuntimeError):
                probe.run_call("input", output_dir=root, label="candidate", hypothesis_id="H1")
            diagnostic = root / "candidate.stderr.txt"
            self.assertEqual(diagnostic.read_text(), "transport diagnostic")
            self.assertEqual(diagnostic.stat().st_mode & 0o777, 0o600)
            receipt = json.loads((root / "candidate.metadata.json").read_bytes())
            self.assertEqual(receipt["stderr_sha256"], probe.sha256(diagnostic.read_bytes()))
            self.assertNotIn("model reasoning", json.dumps(receipt))

    def test_changed_packet_rejected_before_model_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            probe.atomic_json(root / "packet.json", packet())
            item = packet()
            item["task"] += " changed"
            with patch.object(probe, "run_call") as call, self.assertRaises(ValueError):
                probe.run_stage(item, root)
            call.assert_not_called()


class ReceiptBindingTests(unittest.TestCase):
    def _write_pair(self, root, item):
        probe.atomic_json(root / "packet.json", item)
        for label in ("baseline", "candidate"):
            output = answer(label + " output")
            prompt = probe.build_trial_prompt(item, label).encode()
            probe.atomic_json(root / f"{label}.json", output)
            probe.atomic_bytes(root / f"{label}.prompt.txt", prompt)
            probe.atomic_json(root / f"{label}.metadata.json", {
                "experiment_id": probe.EXPERIMENT_ID,
                "call_id": label, "kind": "trial", "status": "completed",
                "packet_sha256": probe.sha256(probe.canonical_bytes(item)),
                "hypothesis_id": item["hypothesis_id"],
                "output_sha256": probe.sha256(probe.canonical_bytes(output)),
                "prompt_sha256": probe.sha256(prompt),
                "prompt_version": probe.EXPERIMENT_ID + ".trial",
                "model": probe.MODEL, "provider": "openai_via_codex_cli",
                "model_reasoning_effort": probe.REASONING,
                "service_tier": probe.SERVICE_TIER,
                "tool_sha256": probe.sha256(Path(probe.__file__).read_bytes()),
            })

    def _assert_no_review_call(self, root, item):
        with patch.object(probe, "run_call") as call:
            with self.assertRaises(ValueError):
                probe.run_stage(item, root, review=True)
            call.assert_not_called()

    def test_genuine_pair_enters_both_reviews(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, item = Path(temporary), packet()
            self._write_pair(root, item)
            with patch.object(probe, "run_call", return_value={"status": "completed"}) as call:
                receipts = probe.run_stage(item, root, review=True)
            self.assertEqual(len(receipts), 2)
            self.assertEqual(call.call_count, 2)
            self.assertEqual({entry.kwargs["label"] for entry in call.call_args_list},
                             {"review-forward", "review-reversed"})

    def test_swapped_answers_and_receipts_rejected_before_review(self):
        for swap_prompts in (False, True):
            with self.subTest(swap_prompts=swap_prompts), tempfile.TemporaryDirectory() as temporary:
                root, item = Path(temporary), packet()
                self._write_pair(root, item)
                suffixes = [".json", ".metadata.json"] + ([".prompt.txt"] if swap_prompts else [])
                for suffix in suffixes:
                    baseline = root / ("baseline" + suffix)
                    candidate = root / ("candidate" + suffix)
                    a, b = baseline.read_bytes(), candidate.read_bytes()
                    probe.atomic_bytes(baseline, b)
                    probe.atomic_bytes(candidate, a)
                self._assert_no_review_call(root, item)

    def test_each_wrong_receipt_binding_rejected_before_review(self):
        mutations = {
            "experiment_id": "another-experiment", "call_id": "candidate",
            "kind": "review", "status": "failed", "packet_sha256": "0" * 64,
            "hypothesis_id": "H2", "output_sha256": "0" * 64,
            "prompt_sha256": "0" * 64, "prompt_version": "another-version",
            "model": "another-model", "provider": "another-provider",
            "model_reasoning_effort": "low", "service_tier": "another-tier",
            "tool_sha256": "0" * 64,
        }
        for field, changed in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root, item = Path(temporary), packet()
                self._write_pair(root, item)
                path = root / "baseline.metadata.json"
                receipt = json.loads(path.read_bytes())
                receipt[field] = changed
                probe.atomic_json(path, receipt)
                self._assert_no_review_call(root, item)

    def test_saved_prompt_rejected_even_with_matching_tampered_hash(self):
        for update_receipt in (False, True):
            with self.subTest(update_receipt=update_receipt), tempfile.TemporaryDirectory() as temporary:
                root, item = Path(temporary), packet()
                self._write_pair(root, item)
                wrong_prompt = b"A self-consistent but unregistered prompt"
                probe.atomic_bytes(root / "baseline.prompt.txt", wrong_prompt)
                if update_receipt:
                    path = root / "baseline.metadata.json"
                    receipt = json.loads(path.read_bytes())
                    receipt["prompt_sha256"] = probe.sha256(wrong_prompt)
                    probe.atomic_json(path, receipt)
                self._assert_no_review_call(root, item)


if __name__ == "__main__":
    unittest.main()
