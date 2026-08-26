import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from judicial_meaning.handoff_workbench import (
    check_handoff,
    create_handoff,
    import_handoff,
)


def canonical_digest(envelope):
    unsigned = {key: value for key, value in envelope.items() if key != "handoff_id"}
    payload = json.dumps(
        unsigned,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class HandoffWorkbenchTests(unittest.TestCase):
    def make_approved(self, *, run_id="run-1", evidence_sha256="b" * 64):
        return create_handoff(
            source_skill="ksrf-cassation-judicial-meaning",
            target_skill="ksrf-complaint-qa",
            run_id=run_id,
            plan_sha256="a" * 64,
            evidence_sha256=evidence_sha256,
            payload_type="approved_bounded_findings",
            payload={
                "drafting_ready": True,
                "maximum_permitted_claim": "mixed_post_event",
                "findings": [{"candidate_id": "thesis-1"}],
                "supporting_position_card_ids": ["position-support-1"],
                "adverse_position_card_ids": ["position-adverse-1"],
            },
            limitations=["Только раскрытый наблюдаемый корпус."],
            created_at="2026-08-26T12:00:00Z",
            fingerprint_sha256="c" * 64,
        )

    def test_create_and_check_typed_handoff_with_digest(self):
        envelope = self.make_approved()
        self.assertEqual(envelope["schema_version"], "1.0")
        self.assertEqual(envelope["handoff_id"], canonical_digest(envelope))

        valid = check_handoff(
            envelope,
            expected_target="ksrf-complaint-qa",
            current_plan_sha256="a" * 64,
            current_evidence_sha256="b" * 64,
        )
        self.assertTrue(valid["valid"])
        self.assertEqual(valid["status"], "valid")

        tampered = json.loads(json.dumps(envelope))
        tampered["payload"]["maximum_permitted_claim"] = "all_practice"
        tamper_result = check_handoff(tampered)
        self.assertFalse(tamper_result["valid"])
        self.assertEqual(tamper_result["status"], "tampered")

        stale_result = check_handoff(
            envelope,
            current_plan_sha256="a" * 64,
            current_evidence_sha256="d" * 64,
        )
        self.assertFalse(stale_result["valid"])
        self.assertEqual(stale_result["status"], "stale")
        self.assertIn("evidence_sha256", " ".join(stale_result["errors"]))

        stale_fingerprint = check_handoff(
            envelope,
            current_fingerprint_sha256="d" * 64,
        )
        self.assertFalse(stale_fingerprint["valid"])
        self.assertEqual("stale", stale_fingerprint["status"])

        excessive = check_handoff(
            envelope,
            current_maximum_permitted_claim="unproven_research_question",
        )
        self.assertFalse(excessive["valid"])
        self.assertEqual("incompatible", excessive["status"])
        self.assertIn("maximum_permitted_claim", " ".join(excessive["errors"]))

    def test_typed_payloads_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "drafting_ready"):
            create_handoff(
                source_skill="ksrf-explore-arguments",
                target_skill="ksrf-cassation-judicial-meaning",
                run_id="run-input",
                plan_sha256="a" * 64,
                evidence_sha256="b" * 64,
                payload_type="unproven_research_questions",
                payload={"drafting_ready": True, "questions": []},
                limitations=[],
                created_at="2026-08-26T12:00:00Z",
            )

        with self.assertRaisesRegex(ValueError, "maximum_permitted_claim"):
            create_handoff(
                source_skill="ksrf-cassation-judicial-meaning",
                target_skill="ksrf-complaint-qa",
                run_id="run-output",
                plan_sha256="a" * 64,
                evidence_sha256="b" * 64,
                payload_type="approved_bounded_findings",
                payload={"drafting_ready": True},
                limitations=[],
                created_at="2026-08-26T12:00:00Z",
            )

        with self.assertRaisesRegex(ValueError, "supporting_position_card_ids"):
            create_handoff(
                source_skill="ksrf-cassation-judicial-meaning",
                target_skill="ksrf-complaint-qa",
                run_id="run-output",
                plan_sha256="a" * 64,
                evidence_sha256="b" * 64,
                payload_type="approved_bounded_findings",
                payload={
                    "drafting_ready": True,
                    "maximum_permitted_claim": "bounded",
                    "findings": [{"candidate_id": "thesis-1"}],
                    "adverse_position_card_ids": [],
                },
                limitations=["Только наблюдаемый корпус."],
                created_at="2026-08-26T12:00:00Z",
                fingerprint_sha256="c" * 64,
            )

        unproven = create_handoff(
            source_skill="ksrf-cassation-judicial-meaning",
            target_skill="ksrf-complaint-cycle",
            run_id="run-input",
            plan_sha256="a" * 64,
            evidence_sha256="b" * 64,
            payload_type="unproven_research_questions",
            payload={"drafting_ready": False, "questions": ["Каков судебный смысл?"]},
            limitations=[],
            created_at="2026-08-26T12:00:00Z",
        )
        injected = json.loads(json.dumps(unproven))
        injected["payload"]["findings"] = [{"claim": "готовый вывод"}]
        injected["handoff_id"] = canonical_digest(injected)
        result = check_handoff(injected)
        self.assertFalse(result["valid"])
        self.assertEqual("incompatible", result["status"])

    def test_import_is_atomic_idempotent_and_rejects_stale_or_tampered_input(self):
        first = self.make_approved()
        second = self.make_approved(run_id="run-2", evidence_sha256="e" * 64)

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "inbox" / "import-ledger.jsonl"
            imported = import_handoff(
                first,
                ledger,
                expected_target="ksrf-complaint-qa",
                current_plan_sha256="a" * 64,
                current_evidence_sha256="b" * 64,
            )
            self.assertEqual(imported["status"], "imported")
            self.assertTrue(imported["imported"])
            original_bytes = ledger.read_bytes()
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 1)

            duplicate = import_handoff(first, ledger, expected_target="ksrf-complaint-qa")
            self.assertEqual(duplicate["status"], "idempotent_noop")
            self.assertFalse(duplicate["imported"])
            self.assertEqual(ledger.read_bytes(), original_bytes)

            tampered = json.loads(json.dumps(first))
            tampered["payload"]["findings"].append({"candidate_id": "injected"})
            rejected = import_handoff(tampered, ledger)
            self.assertEqual(rejected["status"], "tampered")
            self.assertEqual(ledger.read_bytes(), original_bytes)

            stale = import_handoff(
                first,
                ledger,
                current_evidence_sha256="f" * 64,
            )
            self.assertEqual(stale["status"], "stale")
            self.assertEqual(ledger.read_bytes(), original_bytes)

            with patch(
                "judicial_meaning.handoff_workbench.os.replace",
                side_effect=OSError("simulated atomic replace failure"),
            ):
                with self.assertRaisesRegex(OSError, "atomic replace failure"):
                    import_handoff(second, ledger, expected_target="ksrf-complaint-qa")
            self.assertEqual(ledger.read_bytes(), original_bytes)
            self.assertFalse(list(ledger.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
