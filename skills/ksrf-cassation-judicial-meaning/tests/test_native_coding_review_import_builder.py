from __future__ import annotations

import copy
import hashlib
import unittest

from judicial_meaning.practice_quality import (
    AUDIT_CODING_RECORD_FIELDS,
    AUDITED_CODING_FIELDS,
    CODING_AUDIT_DECISION_FIELDS,
    NON_AUDITED_CODING_CONTENT_FIELDS,
    assess_coding_reliability,
    build_native_coding_audit_inputs,
    build_native_coding_review_import,
    canonical_digest,
)


class NativeCodingReviewImportBuilderTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def _record(
        *,
        chain_id: str,
        document_id: str,
        quote: str,
        coder: str,
    ) -> dict[str, object]:
        return {
            "chain_id": chain_id,
            "document_id": document_id,
            "label": "false_positive",
            "speaker": "court",
            "proposition": "Суд сформулировал проверяемое правило.",
            "quote": quote,
            "quote_locator": "абзац 1",
            "norm_edition_id": "edition-old",
            "reasoning_to_outcome": "Этот мотив определил отмену акта.",
            "reading_family": "fixture-reading",
            "relation": "supports",
            "remedy": "отмена",
            "coder": coder,
            "codebook_version": "1.0",
            "material_facts": ["существенный факт"],
            "alternative_grounds": [],
            "human_review": "approved",
            "quote_verified": True,
            "full_text_reviewed": True,
        }

    def _fixture(self) -> dict[str, object]:
        rows: list[tuple[int, str, str, str]] = [
            (
                101,
                "chain-first",
                "Суд установил точную цитату первого акта. Основание указано отдельно.",
                "точную цитату первого акта",
            ),
            (
                202,
                "chain-second",
                "Суд привёл точную цитату второго акта. Иной довод отклонён.",
                "точную цитату второго акта",
            ),
        ]
        sources: list[dict[str, object]] = []
        screening: list[dict[str, object]] = []
        primary: list[dict[str, object]] = []
        for ordinal, (source_id, chain_id, text, quote) in enumerate(rows, start=1):
            text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
            document_id = f"document-sha256:{text_sha256}"
            sources.append(
                {
                    "source_id": source_id,
                    "chain_id": chain_id,
                    "document_id": document_id,
                    "text_sha256": text_sha256,
                    "text": text,
                }
            )
            screening.append(
                {
                    "source_id": source_id,
                    "document_id": document_id,
                    "chain_id": chain_id,
                    "matches": [
                        {
                            "lane": "fixture",
                            "query": "точную цитату",
                            "start": 13,
                            "end": 27,
                        }
                    ],
                    "status": "candidate_needs_full_text_review",
                }
            )
            primary.append(
                self._record(
                    chain_id=chain_id,
                    document_id=document_id,
                    quote=quote,
                    coder=f"Primary Reviewer {ordinal}",
                )
            )
        native = build_native_coding_audit_inputs(
            screening,
            primary,
            sources,
            plan_sha256="a" * 64,
            codebook_version="1.0",
            sample_size=2,
            exclusion_sample_size=0,
        )
        secondaries = []
        primary_by_id = {
            record["candidate_id"]: record for record in native["primary_decisions"]
        }
        for candidate_id in reversed(native["audit_plan"]["required_candidate_ids"]):
            secondary = copy.deepcopy(primary_by_id[candidate_id])
            secondary["coder"] = "Secondary Reviewer"
            secondaries.append(secondary)
        return {"native": native, "secondary": secondaries}

    @staticmethod
    def _invoke(
        fixture: dict[str, object],
        *,
        expected_secondary_coder: str = "  SECONDARY   reviewer  ",
    ) -> dict[str, object]:
        native = fixture["native"]
        return build_native_coding_review_import(
            native["audit_plan"],
            native["primary_decisions"],
            native["secondary_review_queue"],
            native["secondary_review_materials"],
            fixture["secondary"],
            codebook_version="1.0",
            norm_edition_ids=("edition-old", "edition-new"),
            expected_secondary_coder=expected_secondary_coder,
        )

    def test_builds_four_field_decisions_in_frozen_order_and_reports_partitions(self) -> None:
        fixture = self._fixture()
        native = fixture["native"]
        candidate_ids = native["audit_plan"]["required_candidate_ids"]
        secondary_by_id = {
            record["candidate_id"]: record for record in fixture["secondary"]
        }
        secondary_by_id[candidate_ids[0]]["proposition"] = "Независимая формулировка правила."
        secondary_by_id[candidate_ids[1]]["norm_edition_id"] = "edition-new"

        result = self._invoke(fixture)

        self.assertEqual(candidate_ids, result["candidate_ids"])
        self.assertEqual(
            candidate_ids,
            [record["candidate_id"] for record in result["audit_decisions"]],
        )
        for decision in result["audit_decisions"]:
            self.assertEqual(CODING_AUDIT_DECISION_FIELDS, set(decision))
            self.assertEqual(
                canonical_digest(decision["secondary_coding"]),
                decision["secondary_coding_sha256"],
            )
        self.assertEqual(
            canonical_digest(result["audit_decisions"]),
            result["audit_decisions_sha256"],
        )
        secondary_digest_order = sorted(
            secondary_by_id.values(), key=canonical_digest
        )
        self.assertNotEqual(
            candidate_ids,
            [record["candidate_id"] for record in secondary_digest_order],
        )
        self.assertEqual(
            canonical_digest(secondary_digest_order),
            result["secondary_coding_sha256"],
        )
        self.assertEqual(list(AUDITED_CODING_FIELDS), result["audited_fields"])
        self.assertEqual(
            list(NON_AUDITED_CODING_CONTENT_FIELDS),
            result["non_audited_content_fields"],
        )
        self.assertEqual(
            [candidate_ids[0]], result["audited_field_agreement_candidate_ids"]
        )
        self.assertEqual(
            [candidate_ids[1]], result["audited_field_disagreement_candidate_ids"]
        )
        self.assertEqual(
            [{"candidate_id": candidate_ids[1], "fields": ["norm_edition_id"]}],
            result["audited_field_differences"],
        )
        self.assertEqual(
            [candidate_ids[0]],
            result["non_audited_content_difference_candidate_ids"],
        )
        self.assertEqual(
            [{"candidate_id": candidate_ids[0], "fields": ["proposition"]}],
            result["non_audited_content_differences"],
        )
        self.assertEqual(
            [candidate_ids[1]], result["adjudication_required_candidate_ids"]
        )
        self.assertIs(result["adjudication_required"], True)
        self.assertIs(result["non_audited_content_review_required"], True)
        self.assertEqual("secondary reviewer", result["expected_secondary_coder_label"])

    def test_coder_only_difference_needs_no_adjudication(self) -> None:
        result = self._invoke(self._fixture())

        self.assertEqual(result["candidate_ids"], result["audited_field_agreement_candidate_ids"])
        self.assertEqual([], result["audited_field_disagreement_candidate_ids"])
        self.assertEqual([], result["audited_field_differences"])
        self.assertEqual([], result["non_audited_content_difference_candidate_ids"])
        self.assertEqual([], result["non_audited_content_differences"])
        self.assertEqual([], result["adjudication_required_candidate_ids"])
        self.assertIs(result["adjudication_required"], False)
        self.assertIs(result["non_audited_content_review_required"], False)

    def test_content_review_signal_is_advisory_to_eight_field_reliability(self) -> None:
        fixture = self._fixture()
        fixture["secondary"][0]["proposition"] = "Независимая формулировка правила."
        imported = self._invoke(fixture)

        reliability = assess_coding_reliability(
            fixture["native"]["audit_plan"],
            fixture["native"]["primary_decisions"],
            imported["audit_decisions"],
        )
        self.assertIs(imported["non_audited_content_review_required"], True)
        self.assertIs(imported["adjudication_required"], False)
        self.assertIs(reliability["complete"], True)

        disputed = self._fixture()
        disputed["secondary"][0]["label"] = "mentioned_only"
        disputed_import = self._invoke(disputed)
        candidate_id = disputed_import["candidate_ids"][0]
        decision = next(
            item
            for item in disputed_import["audit_decisions"]
            if item["candidate_id"] == candidate_id
        )
        invalid_adjudication = {
            "candidate_id": candidate_id,
            "primary_coding_sha256": decision["primary_coding_sha256"],
            "secondary_coding_sha256": decision["secondary_coding_sha256"],
            "resolved_fields": {
                "label": "false_positive",
                "proposition": "Неподдерживаемое поле",
            },
            "adjudicator": "supervisor-reviewer",
            "reviewed_at": "2026-09-03T12:00:00Z",
            "human_review": "approved",
        }
        blocked = assess_coding_reliability(
            disputed["native"]["audit_plan"],
            disputed["native"]["primary_decisions"],
            disputed_import["audit_decisions"],
            [invalid_adjudication],
        )
        self.assertIs(disputed_import["adjudication_required"], True)
        self.assertIs(blocked["complete"], False)
        self.assertEqual(
            [candidate_id], blocked["invalid_adjudication_record_ids"]
        )

    def test_rejects_missing_duplicate_or_open_secondary_population(self) -> None:
        mutations = {}
        missing = self._fixture()
        missing["secondary"].pop()
        mutations["missing"] = missing
        duplicate = self._fixture()
        duplicate["secondary"].append(copy.deepcopy(duplicate["secondary"][0]))
        mutations["duplicate"] = duplicate
        open_record = self._fixture()
        open_record["secondary"][0]["unexpected"] = True
        mutations["open"] = open_record

        for name, fixture in mutations.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                self._invoke(fixture)

    def test_rejects_incomplete_secondary_record(self) -> None:
        for field, value, expected_fragment in (
            ("human_review", "pending", "human_review=approved"),
            ("quote_verified", False, "quote_verified=true"),
            ("full_text_reviewed", False, "full_text_reviewed=true"),
        ):
            fixture = self._fixture()
            fixture["secondary"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError) as caught:
                self._invoke(fixture)
            message = str(caught.exception)
            self.assertIn(expected_fragment, message)
            self.assertNotIn("одобрено человеком", message)
            self.assertNotIn("не проверен", message)
            self.assertNotIn("не сверена", message)

    def test_rejects_foreign_identity_codebook_or_norm_edition(self) -> None:
        for field, value in (
            ("chain_id", "foreign-chain"),
            ("document_id", "document-sha256:" + "f" * 64),
            ("codebook_version", "2.0"),
            ("norm_edition_id", "edition-unknown"),
        ):
            fixture = self._fixture()
            fixture["secondary"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self._invoke(fixture)

    def test_all_rows_must_use_pinned_distinct_coder(self) -> None:
        wrong = self._fixture()
        wrong["secondary"][0]["coder"] = "Other Reviewer"
        with self.assertRaisesRegex(ValueError, "не совпадает с ожидаемой меткой"):
            self._invoke(wrong)

        same = self._fixture()
        target = same["secondary"][0]
        primary_by_id = {
            record["candidate_id"]: record
            for record in same["native"]["primary_decisions"]
        }
        pinned_primary_coder = primary_by_id[target["candidate_id"]]["coder"]
        for record in same["secondary"]:
            record["coder"] = pinned_primary_coder
        with self.assertRaisesRegex(ValueError, "совпадает с меткой первичного"):
            self._invoke(
                same,
                expected_secondary_coder=pinned_primary_coder,
            )

    def test_requires_literal_main_and_alternative_quotes_after_normalized_check(self) -> None:
        main = self._fixture()
        main["secondary"][0]["quote"] = main["secondary"][0]["quote"].upper()
        with self.assertRaisesRegex(ValueError, "буквальной подстрокой"):
            self._invoke(main)

        alternative = self._fixture()
        target = alternative["secondary"][0]
        target["alternative_grounds"] = [
            {
                "ground": "Отдельное основание",
                "independently_sufficient": True,
                "quote": "ОСНОВАНИЕ УКАЗАНО ОТДЕЛЬНО",
                "quote_locator": "абзац 1",
            }
        ]
        with self.assertRaisesRegex(ValueError, "буквальной подстрокой"):
            self._invoke(alternative)

    def test_rejects_tampered_plan_queue_and_material_bindings(self) -> None:
        plan = self._fixture()
        plan["native"]["audit_plan"]["audit_plan_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "план аудита"):
            self._invoke(plan)

        queue = self._fixture()
        queue["native"]["secondary_review_queue"][0]["primary_coding_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "не связана с первичной разметкой"):
            self._invoke(queue)

        material = self._fixture()
        material["native"]["secondary_review_materials"][0]["packet_text_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "Хеш полного текста"):
            self._invoke(material)

    def test_returned_record_contract_stays_exactly_twenty_fields(self) -> None:
        fixture = self._fixture()
        self.assertEqual(
            {20}, {len(record) for record in fixture["secondary"]}
        )
        self.assertTrue(
            all(set(record) == AUDIT_CODING_RECORD_FIELDS for record in fixture["secondary"])
        )
        self._invoke(fixture)


if __name__ == "__main__":
    unittest.main()
