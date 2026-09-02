from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO / "tools" / "skillset_file_contract.py"
VALIDATOR_PATH = (
    REPO
    / "skills"
    / "ksrf-complaint-cycle"
    / "scripts"
    / "validate_ksrf_skillset.py"
)
LAWINFO_JSON = (
    REPO
    / "skills"
    / "ksrf-argument-patterns"
    / "references"
    / "lawinfo_constitutional_method_cards.json"
)
SPEC = importlib.util.spec_from_file_location("skillset_file_contract", CONTRACT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Не удалось загрузить {CONTRACT_PATH}")
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)

VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "runtime_self_containment_validator",
    VALIDATOR_PATH,
)
if VALIDATOR_SPEC is None or VALIDATOR_SPEC.loader is None:
    raise RuntimeError(f"Не удалось загрузить {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


def _canonical_digest(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class RuntimeReferenceSelfContainmentTests(unittest.TestCase):
    def test_exact_runtime_payload_has_no_repository_local_coordinates(self) -> None:
        offenders: list[str] = []
        for package in CONTRACT.SKILL_NAMES:
            package_root = REPO / "skills" / package
            for path in CONTRACT.payload_files(package_root):
                logical = f"{package}/{path.relative_to(package_root).as_posix()}"
                try:
                    raw = path.read_text(encoding="utf-8")
                except UnicodeError:
                    if path.suffix.casefold() in VALIDATOR.BINARY_RUNTIME_SUFFIXES:
                        continue
                    offenders.append(f"{logical}: unchecked non-text format")
                    continue
                if path.suffix.casefold() == ".json":
                    try:
                        VALIDATOR.parse_runtime_json_strict(raw)
                    except (RecursionError, TypeError, ValueError) as exc:
                        offenders.append(f"{logical}: invalid JSON ({exc})")
                markers = VALIDATOR.runtime_local_coordinate_markers(path, raw)
                if markers:
                    offenders.append(f"{logical}: {', '.join(markers)}")

        self.assertEqual(offenders, [])

    def test_lawinfo_schema_two_preserves_substantive_projections(self) -> None:
        payload = json.loads(LAWINFO_JSON.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "2.0")
        self.assertEqual(
            {
                key: payload[key]
                for key in ("generated_at", "family", "layer", "runtime_source")
            },
            {
                "generated_at": "2026-08-27",
                "family": "KSRF",
                "layer": "methodology_only",
                "runtime_source": "global_skill_reference",
            },
        )
        retired_keys = {"original_inbox", "archive_roots", "excluded_path"}
        pending = [payload]
        found_retired: set[str] = set()
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                found_retired.update(set(item) & retired_keys)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        self.assertEqual(found_retired, set())
        source_scope = payload["source_scope"]
        self.assertEqual(
            source_scope,
            {
                "publisher_group": "Lawinfo",
                "years": "2023-2026",
                "runtime_reference": "lawinfo-constitutional-methods-2023-2026.md",
                "source_materials_bundled": False,
                "public_locator_field": "sources[].doi",
                "supported_pdf_count_audited": 39,
                "readable_pdf_count": 37,
                "unreadable_or_empty_text_count": 2,
            },
        )
        self.assertEqual(
            source_scope["readable_pdf_count"]
            + source_scope["unreadable_or_empty_text_count"],
            source_scope["supported_pdf_count_audited"],
        )
        self.assertEqual(len(payload["sources"]), 16)
        self.assertEqual(len(payload["cards"]), 15)
        self.assertEqual(len(payload["quarantine"]), 2)
        self.assertEqual(
            _canonical_digest(payload["sources"]),
            "cc3fd54ef9b6c370dc1063908bc8838c5b2920774fb2878230ae5ffcca5a56f0",
        )
        self.assertEqual(
            _canonical_digest(payload["cards"]),
            "55039ef631e8845b2f8078b9ea808bb33e7cee174ee9d637744e45eb5fcda68b",
        )
        self.assertEqual(
            _canonical_digest(payload["quarantine"]),
            "570eb92339e51512bc4e507fe1b47ef9ada5021a4edc613d0ccbe0e75cd7c5d6",
        )
        self.assertEqual(
            _canonical_digest(payload["promotion_policy"]),
            "ba8d82b99f2d00879642cf7e04eff22b7865f8c794fa31e16629d75c0babddb5",
        )
        self.assertEqual(
            payload["promotion_policy"],
            {
                "scholarship_is_law": False,
                "official_russian_anchor_required": True,
                "case_application_evidence_required": True,
                "model_conflict_action": "human_review_or_abstain",
                "scalar_score_authorizes_filing": False,
            },
        )
        for item in payload["quarantine"]:
            self.assertEqual(item["status"], "quarantined_unreadable_scan")
            self.assertEqual(
                item["allowed_use"],
                "identity_and_acquisition_lead_only",
            )

    def test_cleaned_markdown_keeps_user_value_and_availability_boundaries(
        self,
    ) -> None:
        references = REPO / "skills"
        argument = (
            references
            / "ksrf-argument-patterns"
            / "references"
            / "argument-techniques-from-decisions.md"
        ).read_text(encoding="utf-8")
        constitutional = (
            references
            / "ksrf-argument-patterns"
            / "references"
            / "constitutional-review-methods.md"
        ).read_text(encoding="utf-8")
        hearing = (
            references
            / "ksrf-argument-patterns"
            / "references"
            / "hearing-argument-techniques.md"
        ).read_text(encoding="utf-8")
        lawinfo = (
            references
            / "ksrf-argument-patterns"
            / "references"
            / "lawinfo-constitutional-methods-2023-2026.md"
        ).read_text(encoding="utf-8")
        embedded = (
            references
            / "ksrf-complaint-cycle"
            / "references"
            / "ksrf-embedded-guides.md"
        ).read_text(encoding="utf-8")
        science = (
            references
            / "ksrf-complaint-cycle"
            / "references"
            / "science-support-pack.md"
        ).read_text(encoding="utf-8")

        self.assertIn("997 постановлениям КС РФ", argument)
        self.assertIn("не исходный корпус", argument)
        self.assertIn("Перед буквальным цитированием проверяй полный текст", argument)
        self.assertIn("П. Д. Блохин", constitutional)
        self.assertIn("Жалоба адвоката А. Ю. Крылова", constitutional)
        for digest in (
            "a94c15e08467f192b2678f99e7464cd429e8876b95d6e9768a69dea2420c15e7",
            "0c9f8125b0a14df5fba0de6f1381e420a857e0630616ff79e8bbdef6c14ee45c",
        ):
            self.assertIn(digest, constitutional)
        self.assertIn("Исходные файлы не входят в пользовательскую установку", constitutional)
        self.assertIn("не предоставляет доступ", constitutional)
        self.assertIn(
            "Диссертация является научной методикой, а жалоба — состязательным образцом",
            constitutional,
        )
        self.assertIn("официальным актуальным источникам", constitutional)
        self.assertIn("Обработано стенограмм: 373", hearing)
        self.assertIn("Пропущено записей без стенограммы: 0", hearing)
        self.assertIn("Служебный журнал обработки", hearing)
        self.assertIn("не входят в пользовательскую установку", hearing)
        lawinfo_payload = json.loads(LAWINFO_JSON.read_text(encoding="utf-8"))
        for doi in (item["doi"] for item in lawinfo_payload["sources"]):
            self.assertEqual(lawinfo.count(doi), 1, doi)
        for card in lawinfo_payload["cards"]:
            self.assertIn(f"### {card['id']}", lawinfo)
        self.assertIn("получи оригинал законным способом", lawinfo)
        self.assertIn("URFAQ/ЕСПЧ-Навигатор", embedded)
        self.assertIn("сами транскрипции не входят в пользовательскую установку", embedded)
        for official_anchor in ("ФКЗ о КС РФ", "Регламенту", "практике КС РФ"):
            self.assertIn(official_anchor, embedded)
        self.assertIn("https://mp-journal.ru/", science)
        self.assertIn("Охват методической выжимки", science)
        self.assertIn("отдельный служебный файл не входит", science)
        self.assertIn("sko-complaint-methods-2017-2026.md", science)
        self.assertIn("двенадцати статей", science)
        self.assertIn("действующим официальным источникам", science)


if __name__ == "__main__":
    unittest.main()
