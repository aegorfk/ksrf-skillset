import json
import tempfile
import unittest
from pathlib import Path

from judicial_meaning.handoff import make_envelope, validate_envelope, write_envelope


class HandoffTests(unittest.TestCase):
    def test_versioned_envelope_is_stable_and_idempotent(self):
        payload = {"questions": [{"id": "rq-1", "status": "research_question"}]}
        first = make_envelope(
            source_skill="ksrf-complaint-cycle",
            target_skill="ksrf-cassation-judicial-meaning",
            run_id="run-1",
            plan_sha256="a" * 64,
            evidence_sha256="b" * 64,
            payload_type="unproven_research_questions",
            payload=payload,
            limitations=["Тезис до корпуса не сформирован"],
            created_at="2026-08-22T00:00:00Z",
        )
        second = make_envelope(
            source_skill="ksrf-complaint-cycle",
            target_skill="ksrf-cassation-judicial-meaning",
            run_id="run-1",
            plan_sha256="a" * 64,
            evidence_sha256="b" * 64,
            payload_type="unproven_research_questions",
            payload=payload,
            limitations=["Тезис до корпуса не сформирован"],
            created_at="2026-08-22T00:00:00Z",
        )
        self.assertEqual(first["handoff_id"], second["handoff_id"])
        self.assertEqual([], validate_envelope(first))

    def test_write_replay_does_not_duplicate_or_mutate(self):
        envelope = make_envelope(
            source_skill="ksrf-cassation-judicial-meaning",
            target_skill="ksrf-complaint-qa",
            run_id="run-1",
            plan_sha256="a" * 64,
            evidence_sha256="b" * 64,
            payload_type="approved_bounded_findings",
            payload={"maximum_permitted_claim": "corroborated_observed_corpus"},
            limitations=[],
            created_at="2026-08-22T00:00:00Z",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "handoffs.jsonl"
            self.assertEqual("written", write_envelope(path, envelope))
            before = path.read_bytes()
            self.assertEqual("already_present", write_envelope(path, envelope))
            self.assertEqual(before, path.read_bytes())

    def test_incompatible_or_tampered_envelope_fails(self):
        envelope = make_envelope(
            source_skill="a",
            target_skill="b",
            run_id="run-1",
            plan_sha256="a" * 64,
            evidence_sha256="b" * 64,
            payload_type="x",
            payload={},
            limitations=[],
            created_at="2026-08-22T00:00:00Z",
        )
        envelope["schema_version"] = "9.0"
        self.assertTrue(validate_envelope(envelope))


if __name__ == "__main__":
    unittest.main()
