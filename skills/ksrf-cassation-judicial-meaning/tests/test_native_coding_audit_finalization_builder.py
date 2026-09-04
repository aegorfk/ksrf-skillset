from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re
import unittest
import unicodedata

from jsonschema import Draft202012Validator

from judicial_meaning.practice_quality import (
    AUDIT_CODING_RECORD_FIELDS,
    CODING_REVIEW_RESOLUTION_FIELDS,
    RESOLVED_REVIEW_DECISION_FIELDS,
    build_native_coding_audit_finalization,
    build_native_coding_audit_inputs,
    build_native_coding_review_import,
    canonical_digest,
)


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "practice-quality.v1.json"


class NativeCodingAuditFinalizationBuilderTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def _primary_record(*, chain_id: str, document_id: str) -> dict[str, object]:
        return {
            "chain_id": chain_id,
            "document_id": document_id,
            "label": "false_positive",
            "speaker": "court",
            "proposition": "Первичная формулировка правила.",
            "quote": "Основная точная цитата",
            "quote_locator": "абзац 1",
            "norm_edition_id": "edition-old",
            "reasoning_to_outcome": "Этот мотив определил исход дела.",
            "reading_family": "fixture-reading",
            "relation": "supports",
            "remedy": "отмена",
            "coder": "primary-reviewer",
            "codebook_version": "1.0",
            "material_facts": ["первичный факт"],
            "alternative_grounds": [],
            "human_review": "approved",
            "quote_verified": True,
            "full_text_reviewed": True,
        }

    def _fixture(
        self,
        *,
        with_differences: bool = True,
        primary_reasoning: str | None = None,
        secondary_reasoning: str | None = None,
    ) -> dict[str, object]:
        text = (
            "Суд указал: Основная точная цитата. "
            "Основание указано отдельно. Дополнительная   цитата."
        )
        normalized_text = re.sub(
            r"\s+", " ", unicodedata.normalize("NFC", text)
        ).strip()
        text_sha256 = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        chain_id = "chain-finalization"
        document_id = f"document-sha256:{text_sha256}"
        primary_record = self._primary_record(
            chain_id=chain_id, document_id=document_id
        )
        if primary_reasoning is not None:
            primary_record["reasoning_to_outcome"] = primary_reasoning
        native = build_native_coding_audit_inputs(
            [
                {
                    "source_id": 101,
                    "chain_id": chain_id,
                    "document_id": document_id,
                    "matches": [
                        {
                            "lane": "fixture",
                            "query": "Основная точная цитата",
                            "start": 12,
                            "end": 35,
                        }
                    ],
                    "status": "candidate_needs_full_text_review",
                }
            ],
            [primary_record],
            [
                {
                    "source_id": 101,
                    "chain_id": chain_id,
                    "document_id": document_id,
                    "text_sha256": text_sha256,
                    "text": text,
                }
            ],
            plan_sha256="a" * 64,
            codebook_version="1.0",
            sample_size=1,
            exclusion_sample_size=0,
        )
        secondary = copy.deepcopy(native["primary_decisions"][0])
        secondary["coder"] = "secondary-reviewer"
        if with_differences:
            secondary.update(
                {
                    "label": "mentioned_only",
                    "proposition": "Вторичная формулировка правила.",
                    "quote": "Основание указано отдельно",
                    "quote_locator": "абзац 2",
                    "material_facts": ["вторичный факт"],
                    "alternative_grounds": [
                        {
                            "ground": "Второе основание",
                            "independently_sufficient": True,
                            "quote": "Основание указано отдельно",
                            "quote_locator": "абзац 2",
                        }
                    ],
                }
            )
        if secondary_reasoning is not None:
            secondary["reasoning_to_outcome"] = secondary_reasoning
        imported = build_native_coding_review_import(
            native["audit_plan"],
            native["primary_decisions"],
            native["secondary_review_queue"],
            native["secondary_review_materials"],
            [secondary],
            codebook_version="1.0",
            norm_edition_ids=("edition-old", "edition-new"),
            expected_secondary_coder="secondary-reviewer",
        )
        receipt = self._receipt(native, imported)
        return {
            "native": native,
            "imported": imported,
            "receipt": receipt,
            "expected_receipt": receipt["receipt_sha256"],
        }

    @staticmethod
    def _receipt(
        native: dict[str, object], imported: dict[str, object]
    ) -> dict[str, object]:
        audit_plan = native["audit_plan"]
        unsigned: dict[str, object] = {
            "schema_version": "1.0",
            "artifact_type": "coding_audit_review_import_receipt",
            "producer": "judicial_meaning.quality.coding_audit_review_import",
            "bundle_contract_version": "1.2",
            "plan_sha256": audit_plan["plan_sha256"],
            "audit_plan_sha256": audit_plan["audit_plan_sha256"],
            "codebook_version": "1.0",
            "source_bundle_manifest_sha256": "b" * 64,
            "expected_source_bundle_manifest_sha256": "b" * 64,
            "source_bundle_manifest_file_sha256": "c" * 64,
            "review_packet_sha256": "d" * 64,
            "secondary_coding_file_sha256": "e" * 64,
            "secondary_coding_sha256": imported["secondary_coding_sha256"],
            "codebook_sha256": "f" * 64,
            "coding_brief_file_sha256": "1" * 64,
            "audit_decisions_file_sha256": "2" * 64,
            "candidate_ids": imported["candidate_ids"],
            "audited_fields": imported["audited_fields"],
            "non_audited_content_fields": imported["non_audited_content_fields"],
            "audited_field_agreement_candidate_ids": imported[
                "audited_field_agreement_candidate_ids"
            ],
            "audited_field_disagreement_candidate_ids": imported[
                "audited_field_disagreement_candidate_ids"
            ],
            "non_audited_content_difference_candidate_ids": imported[
                "non_audited_content_difference_candidate_ids"
            ],
            "audited_field_differences": imported["audited_field_differences"],
            "non_audited_content_differences": imported[
                "non_audited_content_differences"
            ],
            "non_audited_content_review_required": imported[
                "non_audited_content_review_required"
            ],
            "adjudication_required": imported["adjudication_required"],
            "expected_secondary_coder_label_sha256": hashlib.sha256(
                b"secondary-reviewer"
            ).hexdigest(),
            "secondary_coder_label_precommit_verified": False,
            "returned_quote_literal_presence_verified": True,
            "quote_locator_verified": False,
            "secondary_coder_label_differs_from_each_sampled_primary_label": True,
            "single_secondary_coder_label": True,
            "bundle_internal_consistency_verified": True,
            "expected_manifest_digest_match_verified": True,
            "norm_edition_allowlist_membership_verified": True,
            "source_workspace_reverified": False,
            "reviewer_packet_use_attested": False,
            "norm_edition_temporal_applicability_verified": False,
            "reviewer_identity_authenticated": False,
            "human_review_authenticated": False,
            "independence_verified": False,
            "receipt_authenticated": False,
            "publication_safe": False,
            "legal_readiness": False,
        }
        return {**unsigned, "receipt_sha256": canonical_digest(unsigned)}

    @staticmethod
    def _resolution(fixture: dict[str, object]) -> dict[str, object]:
        native = fixture["native"]
        imported = fixture["imported"]
        receipt = fixture["receipt"]
        candidate_id = imported["candidate_ids"][0]
        decision = imported["audit_decisions"][0]
        fields = (
            imported["audited_field_differences"][0]["fields"]
            + imported["non_audited_content_differences"][0]["fields"]
        )
        variants: dict[str, dict[str, object]] = {
            "label": {"field": "label", "choice": "secondary"},
            "reasoning_to_outcome": {
                "field": "reasoning_to_outcome",
                "choice": "secondary",
            },
            "alternative_grounds": {
                "field": "alternative_grounds",
                "choice": "custom",
                "value": [
                    {
                        "ground": "Итоговое основание",
                        "independently_sufficient": True,
                        "quote": "Основание указано отдельно",
                        "quote_locator": "абзац 2",
                    }
                ],
            },
            "proposition": {
                "field": "proposition",
                "choice": "custom",
                "value": "Итоговая формулировка правила.",
            },
            "quote": {"field": "quote", "choice": "secondary"},
            "quote_locator": {"field": "quote_locator", "choice": "primary"},
            "material_facts": {
                "field": "material_facts",
                "choice": "custom",
                "value": ["итоговый факт"],
            },
        }
        row = {
            "schema_version": "1.0",
            "import_receipt_sha256": receipt["receipt_sha256"],
            "candidate_id": candidate_id,
            "difference_fields": fields,
            "primary_coding_sha256": decision["primary_coding_sha256"],
            "secondary_coding_sha256": decision["secondary_coding_sha256"],
            "field_resolutions": [variants[field] for field in fields],
            "reviewer_pseudonym": "resolver-reviewer",
            "reviewed_at": "2025-09-03T12:00:00Z",
            "human_review": "approved",
            "full_text_reviewed": True,
            "quote_locators_reviewed": True,
            "final_coding_approved": True,
        }
        assert set(row) == CODING_REVIEW_RESOLUTION_FIELDS
        return row

    @staticmethod
    def _invoke(
        fixture: dict[str, object], resolutions: object = None
    ) -> dict[str, object]:
        native = fixture["native"]
        imported = fixture["imported"]
        return build_native_coding_audit_finalization(
            native["audit_plan"],
            native["primary_decisions"],
            native["secondary_review_materials"],
            imported["audit_decisions"],
            fixture["receipt"],
            resolutions,
            expected_import_receipt_sha256=fixture["expected_receipt"],
            norm_edition_ids=("edition-old", "edition-new"),
        )

    def test_builds_one_exact_state_with_value_free_choice_provenance(self) -> None:
        fixture = self._fixture()
        resolution = self._resolution(fixture)

        result = self._invoke(fixture, [resolution])

        self.assertIs(result["complete"], True)
        self.assertIsNone(result["incomplete_reason"])
        self.assertEqual([], result["missing_difference_pairs"])
        candidate_id = fixture["imported"]["candidate_ids"][0]
        expected_fields = resolution["difference_fields"]
        self.assertEqual(
            [
                {"candidate_id": candidate_id, "field": field}
                for field in expected_fields
            ],
            result["required_difference_pairs"],
        )
        self.assertEqual([candidate_id], result["resolved_candidate_ids"])
        self.assertEqual(
            [{"candidate_id": candidate_id, "fields": expected_fields}],
            result["resolved_field_populations"],
        )
        resolved = result["resolved_review_decisions"][0]
        self.assertEqual(RESOLVED_REVIEW_DECISION_FIELDS, set(resolved))
        self.assertEqual(AUDIT_CODING_RECORD_FIELDS, set(resolved["final_coding"]))
        self.assertEqual(canonical_digest(resolution), resolved["resolution_sha256"])
        self.assertEqual(
            canonical_digest(resolved["final_coding"]),
            resolved["final_coding_sha256"],
        )
        self.assertEqual(
            [{"field": item["field"], "choice": item["choice"]} for item in resolution["field_resolutions"]],
            resolved["field_choices"],
        )
        self.assertFalse(
            any("value" in item for item in resolved["field_choices"])
        )
        final = resolved["final_coding"]
        self.assertEqual("mentioned_only", final["label"])
        self.assertEqual("Итоговая формулировка правила.", final["proposition"])
        self.assertEqual("абзац 1", final["quote_locator"])
        self.assertEqual("resolver-reviewer", final["coder"])
        self.assertEqual(
            canonical_digest([final]), result["final_coding_sha256"]
        )
        self.assertEqual(1, len(result["adjudications"]))
        adjudication = result["adjudications"][0]
        self.assertEqual(
            {"label", "alternative_grounds"}, set(adjudication["resolved_fields"])
        )
        self.assertIs(result["coding_reliability"]["complete"], True)
        self.assertIs(result["difference_resolution_bijection_verified"], True)
        self.assertIs(result["final_quote_literal_presence_verified"], True)
        self.assertIs(result["final_quote_normalized_presence_verified"], True)
        self.assertIs(result["quote_locator_review_declared"], True)
        self.assertIs(result["quote_locator_verified"], False)

        repeated = self._invoke(fixture, [copy.deepcopy(resolution)])
        self.assertEqual(result, repeated)

    def test_empty_maps_need_no_resolution_or_invented_adjudication(self) -> None:
        fixture = self._fixture(with_differences=False)

        result = self._invoke(fixture)

        self.assertIs(result["complete"], True)
        self.assertEqual([], result["required_difference_pairs"])
        self.assertEqual([], result["resolved_candidate_ids"])
        self.assertEqual([], result["resolved_field_populations"])
        self.assertEqual([], result["adjudications"])
        resolved = result["resolved_review_decisions"][0]
        self.assertEqual([], resolved["difference_fields"])
        self.assertEqual([], resolved["field_choices"])
        self.assertIsNone(resolved["resolution_sha256"])
        self.assertEqual(
            fixture["native"]["primary_decisions"][0], resolved["final_coding"]
        )
        self.assertIs(result["quote_locator_review_declared"], False)

        with self.assertRaisesRegex(ValueError, "нельзя передавать"):
            self._invoke(fixture, [])

    def test_omitted_and_readable_partial_resolutions_are_value_free_incomplete(self) -> None:
        fixture = self._fixture()
        expected_pairs = [
            {
                "candidate_id": fixture["imported"]["candidate_ids"][0],
                "field": field,
            }
            for field in self._resolution(fixture)["difference_fields"]
        ]

        omitted = self._invoke(fixture)
        self.assertIs(omitted["complete"], False)
        self.assertEqual("resolution_incomplete", omitted["incomplete_reason"])
        self.assertEqual(expected_pairs, omitted["missing_difference_pairs"])
        self.assertEqual([], omitted["resolved_review_decisions"])
        self.assertIsNone(omitted["final_coding_sha256"])

        partial_row = self._resolution(fixture)
        partial_row["field_resolutions"] = partial_row["field_resolutions"][:2]
        partial = self._invoke(fixture, [partial_row])
        self.assertIs(partial["complete"], False)
        self.assertEqual(expected_pairs[2:], partial["missing_difference_pairs"])
        self.assertEqual(
            [
                {
                    "candidate_id": expected_pairs[0]["candidate_id"],
                    "fields": partial_row["difference_fields"][:2],
                }
            ],
            partial["resolved_field_populations"],
        )
        serialized = json.dumps(partial, ensure_ascii=False)
        for forbidden in (
            "Итоговая формулировка",
            "resolver-reviewer",
            "2025-09-03",
        ):
            self.assertNotIn(forbidden, serialized)

        empty_choices = self._resolution(fixture)
        empty_choices["field_resolutions"] = []
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(empty_choices)
        empty_result = self._invoke(fixture, [empty_choices])
        self.assertIs(empty_result["complete"], False)
        self.assertEqual(expected_pairs, empty_result["missing_difference_pairs"])

    def test_valid_visible_reasoning_with_layout_whitespace_is_finalizable(self) -> None:
        cases = (
            (
                "primary",
                "Первичное  обоснование\nсуда.",
                "Вторичное обоснование суда.",
                None,
                "Первичное  обоснование\nсуда.",
            ),
            (
                "secondary",
                "Первичное обоснование суда.",
                "Вторичное  обоснование\nсуда.",
                None,
                "Вторичное  обоснование\nсуда.",
            ),
            (
                "custom",
                "Первичное обоснование суда.",
                "Вторичное обоснование суда.",
                "Итоговое  обоснование\nсуда.",
                "Итоговое  обоснование\nсуда.",
            ),
        )
        for choice, primary_value, secondary_value, custom_value, expected in cases:
            with self.subTest(choice=choice):
                fixture = self._fixture(
                    primary_reasoning=primary_value,
                    secondary_reasoning=secondary_value,
                )
                row = self._resolution(fixture)
                variant = next(
                    item
                    for item in row["field_resolutions"]
                    if item["field"] == "reasoning_to_outcome"
                )
                variant["choice"] = choice
                if custom_value is not None:
                    variant["value"] = custom_value

                result = self._invoke(fixture, [row])

                self.assertIs(result["complete"], True)
                self.assertEqual(
                    expected,
                    result["resolved_review_decisions"][0]["final_coding"][
                        "reasoning_to_outcome"
                    ],
                )
                self.assertEqual(
                    expected,
                    result["adjudications"][0]["resolved_fields"][
                        "reasoning_to_outcome"
                    ],
                )

    def test_unhashable_json_variant_values_always_raise_value_error(self) -> None:
        fixture = self._fixture()
        for malformed_choice in ([], {}):
            with self.subTest(kind="choice", value=malformed_choice):
                row = self._resolution(fixture)
                row["field_resolutions"][0]["choice"] = malformed_choice
                with self.assertRaises(ValueError):
                    self._invoke(fixture, [row])

        for malformed_label in ([], {}):
            with self.subTest(kind="custom-label", value=malformed_label):
                row = self._resolution(fixture)
                variant = next(
                    item
                    for item in row["field_resolutions"]
                    if item["field"] == "label"
                )
                variant.update({"choice": "custom", "value": malformed_label})
                with self.assertRaises(ValueError):
                    self._invoke(fixture, [row])

        malformed_candidate = self._resolution(fixture)
        malformed_candidate["candidate_id"] = []
        with self.assertRaises(ValueError):
            self._invoke(fixture, [malformed_candidate])

        malformed_receipt_fixture = copy.deepcopy(fixture)
        receipt = malformed_receipt_fixture["receipt"]
        receipt["bundle_contract_version"] = []
        receipt["receipt_sha256"] = canonical_digest(
            {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        )
        malformed_receipt_fixture["expected_receipt"] = receipt["receipt_sha256"]
        with self.assertRaises(ValueError):
            self._invoke(
                malformed_receipt_fixture,
                [self._resolution(fixture)],
            )

    def test_rejects_wrong_prebindings_duplicates_variants_and_declarations(self) -> None:
        fixture = self._fixture()
        base = self._resolution(fixture)
        mutations: list[list[dict[str, object]]] = []

        wrong_receipt = copy.deepcopy(base)
        wrong_receipt["import_receipt_sha256"] = "9" * 64
        mutations.append([wrong_receipt])

        duplicate = copy.deepcopy(base)
        mutations.append([duplicate, copy.deepcopy(duplicate)])

        extra_field = copy.deepcopy(base)
        extra_field["difference_fields"].append("remedy")
        mutations.append([extra_field])

        wrong_order = copy.deepcopy(base)
        wrong_order["field_resolutions"][0], wrong_order["field_resolutions"][1] = (
            wrong_order["field_resolutions"][1],
            wrong_order["field_resolutions"][0],
        )
        mutations.append([wrong_order])

        ambiguous_variant = copy.deepcopy(base)
        ambiguous_variant["field_resolutions"][0]["value"] = "mentioned_only"
        mutations.append([ambiguous_variant])

        same_reviewer = copy.deepcopy(base)
        same_reviewer["reviewer_pseudonym"] = "secondary-reviewer"
        mutations.append([same_reviewer])

        noncanonical_reviewer = copy.deepcopy(base)
        noncanonical_reviewer["reviewer_pseudonym"] = " Resolver-Reviewer "
        mutations.append([noncanonical_reviewer])

        future = copy.deepcopy(base)
        future["reviewed_at"] = "2999-01-01T00:00:00Z"
        mutations.append([future])

        false_declaration = copy.deepcopy(base)
        false_declaration["final_coding_approved"] = False
        mutations.append([false_declaration])

        illegal_custom = copy.deepcopy(base)
        proposition = next(
            item
            for item in illegal_custom["field_resolutions"]
            if item["field"] == "proposition"
        )
        proposition["value"] = ""
        mutations.append([illegal_custom])

        for rows in mutations:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    self._invoke(fixture, rows)

    def test_rejects_normalized_only_custom_main_and_alternative_quotes(self) -> None:
        fixture = self._fixture()

        main = self._resolution(fixture)
        quote_variant = next(
            item for item in main["field_resolutions"] if item["field"] == "quote"
        )
        quote_variant.update(
            {"choice": "custom", "value": "Дополнительная цитата"}
        )
        with self.assertRaisesRegex(ValueError, "буквальной подстрокой"):
            self._invoke(fixture, [main])

        alternative = self._resolution(fixture)
        ground_variant = next(
            item
            for item in alternative["field_resolutions"]
            if item["field"] == "alternative_grounds"
        )
        ground_variant["value"][0]["quote"] = "Дополнительная цитата"
        with self.assertRaisesRegex(ValueError, "буквальной подстрокой"):
            self._invoke(fixture, [alternative])

    def test_rejects_self_consistent_receipt_rewrite_and_wrong_external_anchor(self) -> None:
        fixture = self._fixture()
        tampered = copy.deepcopy(fixture)
        tampered_receipt = tampered["receipt"]
        tampered_receipt["audited_field_differences"] = []
        tampered_receipt["audited_field_disagreement_candidate_ids"] = []
        tampered_receipt["audited_field_agreement_candidate_ids"] = tampered_receipt[
            "candidate_ids"
        ]
        tampered_receipt["adjudication_required"] = False
        unsigned = {
            key: value
            for key, value in tampered_receipt.items()
            if key != "receipt_sha256"
        }
        tampered_receipt["receipt_sha256"] = canonical_digest(unsigned)
        tampered["expected_receipt"] = tampered_receipt["receipt_sha256"]

        with self.assertRaisesRegex(ValueError, "Квитанция импорта"):
            self._invoke(tampered, [self._resolution(fixture)])

        with self.assertRaisesRegex(ValueError, "отдельно сохранённой"):
            build_native_coding_audit_finalization(
                fixture["native"]["audit_plan"],
                fixture["native"]["primary_decisions"],
                fixture["native"]["secondary_review_materials"],
                fixture["imported"]["audit_decisions"],
                fixture["receipt"],
                [self._resolution(fixture)],
                expected_import_receipt_sha256="8" * 64,
                norm_edition_ids=("edition-old", "edition-new"),
            )


if __name__ == "__main__":
    unittest.main()
