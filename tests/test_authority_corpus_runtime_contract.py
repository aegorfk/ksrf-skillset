from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO / "tools" / "build_constitutionalist_authority_corpus.py"
REFERENCE_ROOT = REPO / "skills" / "ksrf-argument-patterns" / "references"
JSON_CORPUS = REFERENCE_ROOT / "constitutionalist-authority-corpus.json"
MARKDOWN_CORPUS = REFERENCE_ROOT / "constitutionalist-authority-corpus.md"
METHOD_CARD_FILES = (
    "constitutional-methodology-verified-cards.md",
    "constitutional-methodology-reference-only-corpus.md",
)
LEGACY_QUEUE_AUTHORITY_IDS = (
    "authority-7814ba1f3105",
    "authority-5561e3e7a448",
    "authority-116784cc7c04",
    "authority-939af428dd37",
    "authority-1e736462bf95",
    "authority-6a804151c234",
    "authority-b4621f60d0d1",
    "authority-3bbe0fc62bba",
    "authority-d225ecd80e3f",
    "authority-cd85d6d609e3",
    "authority-b310b50fba8c",
    "authority-45e8f8fae5fa",
    "authority-883a6fb43cf0",
    "authority-afc16318634f",
    "authority-2dcc9718b74d",
    "authority-45d0c3e755f1",
    "authority-75e8969d25f8",
    "authority-38fa3c8054f1",
    "authority-95f2fc7f914a",
    "authority-c38f1194e80e",
    "authority-7659f78e4ea3",
    "authority-725c7079049d",
    "authority-3033c7f7cd14",
    "authority-f1353d7aca65",
    "authority-24f0dcf7f5cc",
    "authority-84281f2059a3",
    "authority-9a21b4c8950e",
    "authority-140d928da1ca",
    "authority-c2015efcb370",
    "authority-726693a5ce24",
    "authority-06dc49d4b1e8",
)


def _canonical_digest(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

SPEC = importlib.util.spec_from_file_location("authority_corpus_builder", BUILDER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Не удалось загрузить {BUILDER_PATH}")
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


class AuthorityCorpusRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(JSON_CORPUS.read_text(encoding="utf-8"))
        cls.markdown = MARKDOWN_CORPUS.read_text(encoding="utf-8")

    def test_runtime_json_uses_clean_schema_without_maintainer_surfaces(self) -> None:
        self.assertEqual(self.payload["schema_version"], "2.0")
        self.assertNotIn("next_extraction_wave", self.payload)
        self.assertNotIn("local_source_hint", json.dumps(self.payload, ensure_ascii=False))
        self.assertNotIn("ТЗ/", json.dumps(self.payload, ensure_ascii=False))
        for source in self.payload["sources"]:
            with self.subTest(kind=source["kind"]):
                self.assertTrue({"kind", "label", "coverage"}.issubset(source))
                self.assertLessEqual(
                    set(source),
                    {"kind", "label", "coverage", "url"},
                )

    def test_complete_registry_and_provenance_summary_remain_available(self) -> None:
        authorities = self.payload["authorities"]
        self.assertEqual(len(authorities), 1_652)
        self.assertEqual(sum(len(row["works"]) for row in authorities), 4_178)
        self.assertEqual(self.payload["summary"]["authorities_total"], 1_652)
        self.assertEqual(self.payload["summary"]["works_total"], 4_178)
        self.assertEqual(len({row["id"] for row in authorities}), 1_652)
        self.assertTrue(all(row["source_counts"] for row in authorities))
        self.assertTrue(
            any(
                work.get("url")
                for row in authorities
                for work in row["works"]
            )
        )
        self.assertEqual(
            _canonical_digest(authorities),
            "1b86c629ae9274af5925bb7fb23c64270006240a5096ba47d852daab1915f7eb",
        )
        self.assertEqual(
            _canonical_digest(self.payload["summary"]),
            "ca664591b1e71780f9daa285d538750944a85d07aff8d1ca3191152cfafaa09e",
        )
        self.assertEqual(
            _canonical_digest(self.payload["sources"]),
            "bed6a6023a48b3d02cd3b7bdedc3cd995f0042eb075b7d27d037df04dd4e2d8d",
        )

        by_id = {row["id"]: row for row in authorities}
        self.assertEqual(set(LEGACY_QUEUE_AUTHORITY_IDS) - set(by_id), set())
        self.assertEqual(
            sum(len(by_id[row_id]["works"]) for row_id in LEGACY_QUEUE_AUTHORITY_IDS),
            276,
        )

    def test_markdown_replaces_stale_wave_with_truthful_card_routes(self) -> None:
        for marker in (
            "Следующая широкая волна извлечения",
            "Дополнение после широкой волны",
            "Что извлекать",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.markdown)

        self.assertIn("Статусы этого реестра — срез сборщика", self.markdown)
        self.assertIn("19 карточек до этапа внедрения", self.markdown)
        self.assertIn("84 карточки с проверенными источниками", self.markdown)
        self.assertIn(
            "не разрешает перевод в обязательные правила",
            self.markdown,
        )
        self.assertIn("`law_as_of=2026-08-14`", self.markdown)
        self.assertEqual(self.markdown.count("- **"), 1_652)
        for name in METHOD_CARD_FILES:
            with self.subTest(name=name):
                self.assertIn(f"]({name})", self.markdown)
                self.assertTrue((REFERENCE_ROOT / name).is_file())

    def test_root_builder_emits_the_same_user_runtime_contract(self) -> None:
        self.assertEqual(builder.SCHEMA_VERSION, "2.0")
        self.assertFalse(hasattr(builder, "NEXT_EXTRACTION_WAVE"))
        empty_payload = builder.serialize({}, "2026-09-02")
        self.assertNotIn("next_extraction_wave", empty_payload)
        self.assertTrue(
            all(
                "local_source_hint" not in source
                for source in empty_payload["sources"]
            )
        )
        builder.validate(self.payload)
        with self.assertRaises(AssertionError):
            builder.validate({**self.payload, "next_extraction_wave": []})
        with self.assertRaises(AssertionError):
            builder.validate(
                {
                    **self.payload,
                    "sources": [
                        {
                            **self.payload["sources"][0],
                            "local_source_hint": "private/source.pdf",
                        },
                        *self.payload["sources"][1:],
                    ],
                }
            )

        rendered = builder.render_markdown(self.payload)
        self.assertEqual(rendered, self.markdown)


if __name__ == "__main__":
    unittest.main()
