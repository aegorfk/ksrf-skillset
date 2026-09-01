from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_HEADING = "### Исполнимый контракт CourtRequestApplicabilityBinding"
REQUIRED_FIELDS = {
    "passport_id",
    "passport_revision_id",
    "timepoint_id",
    "edition_id",
    "applicability_status",
    "blockers",
}


class CourtRequestApplicabilityContractTest(unittest.TestCase):
    def test_reference_exposes_safe_default_top_level_binding(self) -> None:
        reference = self._read("references/workflow-reference.md")
        binding = self._canonical_binding(reference)

        self.assertEqual(REQUIRED_FIELDS, set(binding))
        self.assertEqual("blocked", binding["applicability_status"])
        self.assertEqual(["FIX_FIRST"], binding["blockers"])

    def test_reference_requires_exact_passed_revision_and_unique_mapping(self) -> None:
        reference = self._read("references/workflow-reference.md")

        for marker in (
            "`gate.status=passed`",
            "`passport_revision_id`",
            "`timepoint_id → edition_id`",
            "`ABSTAIN_PENDING_OFFICIAL_SOURCE`",
            "`ABSTAIN_PENDING_RECORD`",
            "`FIX_FIRST`",
            "`assess_norm_version_passport(...)`",
            "не доверяй сохранённым `gate.status`",
            "методологическая статическая проекция",
            "необходимое, но недостаточное условие",
            "подтверждённый горизонт будущего решения",
            "не придумывай дату решения",
            "не выдавай готовую к подаче формулу",
        ):
            self.assertIn(marker, reference)

    def test_contract_parser_ignores_earlier_decoy_and_rejects_nested_binding(
        self,
    ) -> None:
        valid_binding = {
            "CourtRequestApplicabilityBinding": {
                "passport_id": "",
                "passport_revision_id": "",
                "timepoint_id": "",
                "edition_id": "",
                "applicability_status": "blocked",
                "blockers": ["FIX_FIRST"],
            }
        }
        adversarial_reference = (
            "```json\n"
            f"{json.dumps(valid_binding)}\n"
            "```\n\n"
            f"{CONTRACT_HEADING}\n\n"
            "```json\n"
            f"{json.dumps({'wrapper': valid_binding})}\n"
            "```\n"
        )

        with self.assertRaises(AssertionError):
            self._canonical_binding(adversarial_reference)

    def test_contract_parser_rejects_binding_inside_html_comment(self) -> None:
        commented_reference = f"""<!--
{CONTRACT_HEADING}

```json
{{
  "CourtRequestApplicabilityBinding": {{
    "passport_id": "",
    "passport_revision_id": "",
    "timepoint_id": "",
    "edition_id": "",
    "applicability_status": "blocked",
    "blockers": ["FIX_FIRST"]
  }}
}}
```
-->
"""

        with self.assertRaises(AssertionError):
            self._canonical_binding(commented_reference)

    def test_contract_parser_rejects_binding_after_unclosed_html_comment(
        self,
    ) -> None:
        adversarial_reference = f"""<!--
{CONTRACT_HEADING}

```json
{{"CourtRequestApplicabilityBinding": {{"passport_id": ""}}}}
```
"""

        with self.assertRaises(AssertionError):
            self._canonical_binding(adversarial_reference)

    def test_contract_parser_rejects_heading_inside_outer_code_fence(self) -> None:
        adversarial_reference = f"""````text
{CONTRACT_HEADING}

```json
{{
  "CourtRequestApplicabilityBinding": {{
    "passport_id": "",
    "passport_revision_id": "",
    "timepoint_id": "",
    "edition_id": "",
    "applicability_status": "blocked",
    "blockers": ["FIX_FIRST"]
  }}
}}
```
````
"""

        with self.assertRaises(AssertionError):
            self._canonical_binding(adversarial_reference)

    def test_eval_blocks_unverified_transition_source(self) -> None:
        payload = json.loads(self._read("evals/evals.json"))
        matching = [
            item
            for item in payload["evals"]
            if item.get("expected_output") == "Blocked applicability binding."
        ]

        self.assertEqual(1, len(matching))
        expectations = "\n".join(matching[0]["expectations"])
        self.assertIn("ABSTAIN_PENDING_OFFICIAL_SOURCE", expectations)
        self.assertIn("applicability_status=blocked", expectations)
        self.assertIn("filing-ready formula", expectations)

    def test_eval_recomputes_gate_and_blocks_unknown_future_horizon(self) -> None:
        payload = json.loads(self._read("evals/evals.json"))
        matching = [
            item
            for item in payload["evals"]
            if item.get("expected_output")
            == "Recomputed gate and unknown-horizon stop."
        ]

        self.assertEqual(1, len(matching))
        expectations = "\n".join(matching[0]["expectations"])
        self.assertIn("assess_norm_version_passport", expectations)
        self.assertIn("approval ID", expectations)
        self.assertIn("does not invent a decision date", expectations)
        self.assertIn("ABSTAIN_PENDING_RECORD", expectations)

    def test_eval_blocks_known_horizon_event_time_trap(self) -> None:
        payload = json.loads(self._read("evals/evals.json"))
        matching = [
            item
            for item in payload["evals"]
            if item.get("expected_output") == "Known-horizon event-time trap."
        ]

        self.assertEqual(1, len(matching))
        expectations = "\n".join(matching[0]["expectations"])
        self.assertIn("unique event-time mapping is not sufficient", expectations)
        self.assertIn("governs the future decision", expectations)
        self.assertIn("applicability_status=blocked", expectations)

    def _canonical_binding(self, reference: str) -> dict[str, object]:
        visible_reference = re.sub(
            r"<!--(?:.*?-->|.*\Z)",
            "",
            reference,
            flags=re.DOTALL,
        )
        lines = visible_reference.splitlines()
        heading_indexes: list[int] = []
        active_fence: tuple[str, int] | None = None

        for index, line in enumerate(lines):
            stripped = line.lstrip()
            if active_fence is not None:
                fence_character, minimum_length = active_fence
                if re.fullmatch(
                    rf"{re.escape(fence_character)}{{{minimum_length},}}\s*",
                    stripped,
                ):
                    active_fence = None
                continue

            fence = re.match(r"^(`{3,}|~{3,})", stripped)
            if fence is not None:
                marker = fence.group(1)
                active_fence = (marker[0], len(marker))
                continue
            if line == CONTRACT_HEADING:
                heading_indexes.append(index)

        self.assertEqual(1, len(heading_indexes))
        heading_index = heading_indexes[0]
        self.assertLess(heading_index + 3, len(lines))
        self.assertEqual("", lines[heading_index + 1])
        self.assertEqual("```json", lines[heading_index + 2])
        closing_index = next(
            (
                index
                for index in range(heading_index + 3, len(lines))
                if lines[index] == "```"
            ),
            None,
        )
        self.assertIsNotNone(closing_index)
        body = "\n".join(lines[heading_index + 3 : closing_index])
        payload = json.loads(body)
        self.assertIsInstance(payload, dict)
        self.assertIn("CourtRequestApplicabilityBinding", payload)
        binding = payload["CourtRequestApplicabilityBinding"]
        self.assertIsInstance(binding, dict)
        return binding

    def _read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
