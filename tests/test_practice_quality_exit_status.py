from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker


REPO = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SKILL = "ksrf-cassation-judicial-meaning"
SCRIPT = Path(SKILL) / "scripts" / "judicial_meaning.py"
SOURCE_LIB = REPO / "skills" / SKILL / "lib"
sys.path.insert(0, str(SOURCE_LIB))

from judicial_meaning.practice_quality import (  # noqa: E402
    build_coding_audit_plan,
    canonical_digest,
)
from judicial_meaning.public_corpus import PublicCorpus  # noqa: E402


HELP_REQUIRED = (
    "Коды завершения проверки качества:",
    "0 — ограниченная проверка завершена (complete=true)",
    "в том числе с явно раскрытыми ограничениями",
    "2 — ошибка параметров, входного файла или записи результата",
    "3 — проверка неполна или устарела (complete=false)",
    "полный JSON остаётся в стандартном выводе (stdout)",
    "записывается в --output, если путь указан",
    "Код 0 не означает юридическую готовность",
    "не разрешает подачу жалобы",
)


def definition_validator(schema, name):
    return Draft202012Validator(
        {
            "$schema": schema.get("$schema"),
            "$ref": f"#/definitions/{name}",
            "definitions": schema["definitions"],
        },
        format_checker=FormatChecker(),
    )


def _primary(*, remedy: str = "отмена") -> dict[str, object]:
    return {
        "candidate_id": "candidate-1",
        "chain_id": "chain-candidate-1",
        "document_id": "document-candidate-1",
        "label": "core_merits",
        "speaker": "court",
        "proposition": "Проверенная позиция суда.",
        "norm_edition_id": "edition-1",
        "reading_family": "family-a",
        "relation": "supports",
        "reasoning_to_outcome": "Проверенная связь с исходом.",
        "alternative_grounds": [],
        "remedy": remedy,
        "quote": "проверенная позиция суда",
        "quote_locator": "абзац 18",
        "quote_verified": True,
        "full_text_reviewed": True,
        "coder": "primary-a",
        "codebook_version": "1.0",
        "material_facts": ["проверяемый факт"],
        "human_review": "approved",
    }


def _refresh_plan(
    *,
    evidence_sha256: str = "a" * 64,
    as_of: str = "2026-09-03T12:00:00Z",
    max_age_seconds: int = 604800,
    entries: list[dict[str, object]] | None = None,
    coverage_gaps: list[dict[str, object]] | None = None,
    coverage_requirements: list[dict[str, object]] | None = None,
    treatment_ids: list[str] | None = None,
    treatment_population_sha256: str = "f" * 64,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "as_of": as_of,
        "max_age_seconds": max_age_seconds,
        "evidence_digest": f"corpus-evidence-sha256:{evidence_sha256}",
        "treatment_ids": treatment_ids or [],
        "treatment_population_sha256": treatment_population_sha256,
        "coverage_requirements": coverage_requirements or [{"court_id": "2kas"}],
        "entries": entries or [],
        "coverage_gaps": coverage_gaps or [],
    }
    return {
        "plan_id": f"refresh-plan-sha256:{canonical_digest(payload)}",
        **payload,
    }


TREATMENT_BOUND_FIELDS = (
    "source_chain_id",
    "source_court_id",
    "target_authority_id",
    "target_kind",
    "target_identity",
    "target_identity_confirmed",
    "treatment_type",
    "review_decision",
    "snapshot_id",
    "supersedes_treatment_id",
    "superseded_by_treatment_id",
    "speaker",
    "document_id",
    "document_sha256",
    "text_sha256",
    "source_role",
    "official_url",
    "quote",
    "quote_locator",
    "proposition",
    "decision_reason",
    "created_at",
)


def _reviewed_treatment() -> dict[str, object]:
    source: dict[str, object] = {
        "source_chain_id": "chain-2kas-1",
        "source_court_id": "2kas",
        "target_authority_id": "ksrf-32-p-2023",
        "target_kind": "constitutional_court_act",
        "target_identity": {"act_number": "32-П"},
        "target_identity_confirmed": True,
        "treatment_type": "applies",
        "review_decision": "verified",
        "snapshot_id": f"snapshot-sha256:{'d' * 64}",
        "supersedes_treatment_id": None,
        "superseded_by_treatment_id": None,
        "speaker": "court",
        "document_id": "document-treatment-1",
        "document_sha256": "d" * 64,
        "text_sha256": "e" * 64,
        "source_role": "official_user_seed",
        "official_url": "https://2kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1",
        "quote": "суд применил правовую позицию к спорному правоотношению",
        "quote_locator": "абзац 24, предложение 2",
        "proposition": (
            "Судебный акт chain-2kas-1 содержит проверенное отношение "
            "applies к акту ksrf-32-p-2023."
        ),
        "decision_reason": None,
        "created_at": "2026-09-03T12:00:00Z",
    }
    return {
        "treatment_id": "treatment-reviewed",
        "status": "verified",
        **source,
        "source_binding_sha256": canonical_digest(source),
        "reviewer": "П.П. Петров",
        "reviewed_at": "2026-09-03T12:05:00Z",
        "human_review": "approved",
        "quote_verified": True,
        "full_text_reviewed": True,
    }


def _treatment_set(
    items: list[object],
    *,
    corpus_digest: str = "a" * 64,
    treatment_population_sha256: str = "f" * 64,
) -> dict[str, object]:
    copied = copy.deepcopy(items)
    if (
        all(
            isinstance(item, dict) and isinstance(item.get("treatment_id"), str)
            for item in copied
        )
        and len({item["treatment_id"] for item in copied}) == len(copied)
    ):
        copied.sort(key=lambda item: item["treatment_id"])
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "export_type": "public_corpus_treatment_quality_set",
        "corpus_evidence_digest": f"corpus-evidence-sha256:{corpus_digest}",
        "treatment_population_sha256": treatment_population_sha256,
        "integrity_issue_ids": [],
        "treatment_ids": [
            item.get("treatment_id") if isinstance(item, dict) else None
            for item in copied
        ],
        "items": copied,
    }
    return {**payload, "set_sha256": canonical_digest(payload)}


class PracticeQualityExitStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.installed = cls.root / "installed skills"
        installed = subprocess.run(
            [str(REPO / "install.sh"), "--target", str(cls.installed)],
            cwd=cls.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        if installed.returncode != 0:
            raise AssertionError(installed.stderr)

        cls.corpus_root = cls.root / "trusted-public-cache"
        with PublicCorpus(cls.corpus_root) as corpus:
            seed = corpus.register_seed(
                url="https://2kas.sudrf.ru/modules.php?name=sud_delo&number=live",
                role="official_user_seed",
                public=True,
            )
            snapshot = corpus.store_snapshot(
                seed_id=seed["seed_id"],
                raw="Проверенный полный текст судебного акта.".encode("utf-8"),
                content_type="text/html; charset=utf-8",
                fetched_at="2026-09-03T12:00:00Z",
                parser_manifest={"adapter_id": "test", "parser_version": "1.0"},
            )
            corpus.record_funnel(
                "chain-live",
                "enumerated",
                source_role="official_user_seed",
                court_id="2kas",
                period_id="current",
                enumerator_id="bounded-test",
            )
            for status in (
                "card",
                "document_link",
                "payload_validated",
                "full_text_extracted",
            ):
                corpus.record_funnel(
                    "chain-live",
                    status,
                    snapshot_id=snapshot["snapshot_id"],
                    source_role="official_user_seed",
                    court_id="2kas",
                    period_id="current",
                    enumerator_id="bounded-test",
                )
            current_plan = corpus.plan_refresh(
                as_of="2026-09-03T12:00:00Z",
                max_age_seconds=604800,
                coverage_requirements=[{"court_id": "2kas"}],
            )
            bounded_plan = corpus.plan_refresh(
                as_of="2026-09-03T12:00:00Z",
                max_age_seconds=604800,
                coverage_requirements=[{"court_id": "foreign-court"}],
            )
            empty_treatment_set = corpus.treatment_quality_export()
        cls.corpus_digest = str(current_plan["evidence_digest"]).removeprefix(
            "corpus-evidence-sha256:"
        )
        cls.treatment_population_sha256 = str(
            current_plan["treatment_population_sha256"]
        )

        primary = _primary()
        changed_primary = _primary(remedy="новое средство защиты")
        audit_plan = build_coding_audit_plan(
            [{"candidate_id": "candidate-1"}],
            [primary],
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        incomplete_plan_payload = {
            "primary_coding_sha256": canonical_digest([primary]),
            "required_candidate_ids": ["candidate-1"],
            "invalid_screening_record_ids": [],
            "invalid_primary_record_ids": [],
            "frozen": True,
        }
        incomplete_plan = {
            **incomplete_plan_payload,
            "audit_plan_sha256": canonical_digest(incomplete_plan_payload),
        }
        aliased_plan_payload = {
            key: copy.deepcopy(value)
            for key, value in audit_plan.items()
            if key != "audit_plan_sha256"
        }
        aliased_plan_payload["sample_size"] = 2
        aliased_plan_payload["sample_candidate_ids"] = [
            "candidate-1",
            "  candidate-1  ",
        ]
        aliased_plan_payload["required_candidate_ids"] = [
            "candidate-1",
            "  candidate-1  ",
        ]
        aliased_plan = {
            **aliased_plan_payload,
            "audit_plan_sha256": canonical_digest(aliased_plan_payload),
        }
        secondary = copy.deepcopy(primary)
        secondary["coder"] = "secondary-b"
        audit = {
            "candidate_id": "candidate-1",
            "primary_coding_sha256": canonical_digest(primary),
            "secondary_coding": secondary,
            "secondary_coding_sha256": canonical_digest(secondary),
        }
        quote_changed_secondary = copy.deepcopy(secondary)
        quote_changed_secondary["quote"] = "иная проверенная цитата"
        quote_changed_audit = {
            **audit,
            "secondary_coding": quote_changed_secondary,
            "secondary_coding_sha256": canonical_digest(quote_changed_secondary),
        }
        cross_document_secondary = copy.deepcopy(secondary)
        cross_document_secondary["chain_id"] = "other-chain"
        cross_document_secondary["document_id"] = "other-document"
        cross_document_audit = {
            **audit,
            "secondary_coding": cross_document_secondary,
            "secondary_coding_sha256": canonical_digest(cross_document_secondary),
        }
        same_reviewer_secondary = copy.deepcopy(secondary)
        same_reviewer_secondary["coder"] = "PRIMARY-A"
        same_reviewer_audit = {
            **audit,
            "secondary_coding": same_reviewer_secondary,
            "secondary_coding_sha256": canonical_digest(same_reviewer_secondary),
        }
        extra_field_audit = {**audit, "garbage": True}
        foreign_secondary = _primary()
        foreign_secondary.update(
            {
                "candidate_id": "candidate-foreign",
                "chain_id": "chain-candidate-foreign",
                "document_id": "document-candidate-foreign",
                "coder": "secondary-foreign",
            }
        )
        foreign_audit = {
            "candidate_id": "candidate-foreign",
            "primary_coding_sha256": "a" * 64,
            "secondary_coding": foreign_secondary,
            "secondary_coding_sha256": canonical_digest(foreign_secondary),
        }
        remedy_secondary = copy.deepcopy(secondary)
        remedy_secondary["remedy"] = "оставить без изменения"
        remedy_audit = {
            **audit,
            "secondary_coding": remedy_secondary,
            "secondary_coding_sha256": canonical_digest(remedy_secondary),
        }
        adjudication_base = {
            "candidate_id": "candidate-1",
            "primary_coding_sha256": canonical_digest(primary),
            "secondary_coding_sha256": canonical_digest(remedy_secondary),
            "resolved_fields": {"remedy": "отмена"},
            "adjudicator": "supervisor-c",
            "reviewed_at": "2026-09-03T12:20:00Z",
            "human_review": "approved",
        }
        null_adjudication = {
            **adjudication_base,
            "resolved_fields": {"remedy": None},
        }
        date_only_adjudication = {
            **adjudication_base,
            "reviewed_at": "2026-09-03",
        }
        extra_field_adjudication = {**adjudication_base, "garbage": True}
        aliased_reviewer_adjudication = {
            **adjudication_base,
            "adjudicator": "  PRIMARY-A  ",
        }
        orphan_adjudication = {
            **adjudication_base,
            "secondary_coding_sha256": canonical_digest(secondary),
        }
        mismatched_secondary = copy.deepcopy(secondary)
        mismatched_secondary["candidate_id"] = "different-candidate"
        mismatched_audit = {
            **audit,
            "secondary_coding": mismatched_secondary,
            "secondary_coding_sha256": canonical_digest(mismatched_secondary),
        }
        minimal_primary = {
            "candidate_id": "candidate-minimal",
            "coder": "primary-a",
            "human_review": "approved",
            "quote_verified": True,
            "full_text_reviewed": True,
        }
        minimal_plan = build_coding_audit_plan(
            [{"candidate_id": "candidate-minimal"}],
            [minimal_primary],
            plan_sha256="e" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        minimal_secondary = {**minimal_primary, "coder": "secondary-b"}
        minimal_audit = {
            "candidate_id": "candidate-minimal",
            "primary_coding_sha256": canonical_digest(minimal_primary),
            "secondary_coding": minimal_secondary,
            "secondary_coding_sha256": canonical_digest(minimal_secondary),
        }
        malformed_types_primary = _primary()
        malformed_types_primary.update(
            {
                "candidate_id": "candidate-types",
                "chain_id": 7,
                "document_id": {"value": "document-candidate-types"},
                "proposition": 123,
                "quote": {"text": "проверенная позиция суда"},
                "quote_locator": ["абзац 18"],
                "norm_edition_id": 7,
                "reading_family": ["family-a"],
                "reasoning_to_outcome": "Проверенная связь с исходом.",
                "alternative_grounds": [None],
                "remedy": ["отмена"],
                "codebook_version": 1,
                "material_facts": [None],
            }
        )
        malformed_types_plan = build_coding_audit_plan(
            [{"candidate_id": "candidate-types"}],
            [malformed_types_primary],
            plan_sha256="f" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        malformed_types_secondary = {
            **malformed_types_primary,
            "coder": "secondary-b",
        }
        malformed_types_audit = {
            "candidate_id": "candidate-types",
            "primary_coding_sha256": canonical_digest(malformed_types_primary),
            "secondary_coding": malformed_types_secondary,
            "secondary_coding_sha256": canonical_digest(malformed_types_secondary),
        }

        cls.audit_plan = cls._write_json("audit-plan.json", audit_plan)
        cls.incomplete_plan = cls._write_json(
            "incomplete-audit-plan.json",
            incomplete_plan,
        )
        cls.aliased_plan = cls._write_json(
            "aliased-audit-plan.json",
            aliased_plan,
        )
        cls.invalid_audit_plan = cls.root / "invalid-audit-plan.json"
        cls.invalid_audit_plan.write_text("{invalid\n", encoding="utf-8")
        cls.deep_json = cls.root / "deep-json.json"
        cls.deep_json.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
        cls.missing_corpus_root = cls.root / "must-not-be-created"
        cls.malformed_corpus_root = cls.root / "malformed-public-cache"
        cls.malformed_corpus_root.mkdir()
        malformed_connection = sqlite3.connect(
            cls.malformed_corpus_root / "public-corpus.sqlite3"
        )
        try:
            for table in (
                "seeds",
                "snapshots",
                "observations",
                "indexed_texts",
                "funnel_state",
                "treatments",
                "treatment_review_history",
            ):
                malformed_connection.execute(f"CREATE TABLE {table}(placeholder TEXT)")
            malformed_connection.commit()
        finally:
            malformed_connection.close()
        cls.wal_corpus_root = cls.root / "wal-public-cache"
        cls.wal_corpus_root.mkdir()
        wal_database = cls.wal_corpus_root / "public-corpus.sqlite3"
        wal_connection = sqlite3.connect(wal_database)
        try:
            wal_connection.execute("PRAGMA journal_mode=WAL")
            wal_connection.execute("CREATE TABLE marker(value TEXT)")
            wal_connection.commit()
        finally:
            wal_connection.close()
        for suffix in ("-wal", "-shm"):
            auxiliary = Path(str(wal_database) + suffix)
            if auxiliary.exists():
                auxiliary.unlink()
        cls.primary = cls._write_json("primary.json", [primary])
        cls.changed_primary = cls._write_json(
            "changed-primary.json",
            [changed_primary],
        )
        cls.audit = cls._write_json("audit.json", [audit])
        cls.quote_changed_audit = cls._write_json(
            "quote-changed-audit.json",
            [quote_changed_audit],
        )
        cls.cross_document_audit = cls._write_json(
            "cross-document-audit.json",
            [cross_document_audit],
        )
        cls.same_reviewer_audit = cls._write_json(
            "same-reviewer-audit.json",
            [same_reviewer_audit],
        )
        cls.extra_field_audit = cls._write_json(
            "extra-field-audit.json",
            [extra_field_audit],
        )
        cls.foreign_audit = cls._write_json(
            "foreign-audit.json",
            [audit, foreign_audit],
        )
        cls.remedy_audit = cls._write_json("remedy-audit.json", [remedy_audit])
        cls.valid_adjudication = cls._write_json(
            "valid-adjudication.json",
            [adjudication_base],
        )
        cls.null_adjudication = cls._write_json(
            "null-adjudication.json",
            [null_adjudication],
        )
        cls.date_only_adjudication = cls._write_json(
            "date-only-adjudication.json",
            [date_only_adjudication],
        )
        cls.extra_field_adjudication = cls._write_json(
            "extra-field-adjudication.json",
            [extra_field_adjudication],
        )
        cls.aliased_reviewer_adjudication = cls._write_json(
            "aliased-reviewer-adjudication.json",
            [aliased_reviewer_adjudication],
        )
        cls.orphan_adjudication = cls._write_json(
            "orphan-adjudication.json",
            [orphan_adjudication],
        )
        cls.mismatched_audit = cls._write_json(
            "mismatched-audit.json",
            [mismatched_audit],
        )
        cls.minimal_plan = cls._write_json("minimal-plan.json", minimal_plan)
        cls.minimal_primary = cls._write_json(
            "minimal-primary.json",
            [minimal_primary],
        )
        cls.minimal_audit = cls._write_json("minimal-audit.json", [minimal_audit])
        cls.malformed_types_plan = cls._write_json(
            "malformed-types-plan.json",
            malformed_types_plan,
        )
        cls.malformed_types_primary = cls._write_json(
            "malformed-types-primary.json",
            [malformed_types_primary],
        )
        cls.malformed_types_audit = cls._write_json(
            "malformed-types-audit.json",
            [malformed_types_audit],
        )
        cls.empty_audit = cls._write_json("empty-audit.json", [])
        cls.empty_treatments = cls._write_json(
            "treatments.json", empty_treatment_set
        )
        cls.coverage_requirements = cls._write_json(
            "coverage-requirements.json",
            [{"court_id": "2kas"}],
        )
        cls.failed_records_envelope = cls._write_json(
            "failed-records-envelope.json",
            {"items": [], "complete": False, "error": "network failed"},
        )
        cls.refresh_current = cls._write_json(
            "refresh-current.json",
            current_plan,
        )
        cls.refresh_bounded = cls._write_json(
            "refresh-bounded.json",
            bounded_plan,
        )
        cls.refresh_pending = cls._write_json(
            "refresh-pending.json",
            _refresh_plan(
                evidence_sha256=cls.corpus_digest,
                treatment_population_sha256=cls.treatment_population_sha256,
                entries=[
                    {
                        "seed_id": "seed-needs-refresh",
                        "url": "https://2kas.sudrf.ru/modules.php?name=sud_delo",
                        "role": "official_user_seed",
                        "last_fetched_at": None,
                        "reason": "never_fetched",
                    }
                ],
            ),
        )
        cls.refresh_invalid_contract = cls._write_json(
            "refresh-invalid-contract.json",
            {"plan_id": "refresh-1", "entries": [], "coverage_gaps": []},
        )
        cls.refresh_invalid_gap = cls._write_json(
            "refresh-invalid-gap.json",
            _refresh_plan(
                evidence_sha256=cls.corpus_digest,
                treatment_population_sha256=cls.treatment_population_sha256,
                coverage_gaps=[{"reason": "coverage_gap_not_observed"}],
            ),
        )
        cls.refresh_wrong_digest = cls._write_json(
            "refresh-wrong-digest.json",
            _refresh_plan(evidence_sha256="c" * 64),
        )
        stale_plan = _refresh_plan(as_of="2026-09-02T12:00:00Z")
        cls.refresh_stale_as_of = cls._write_json(
            "refresh-stale-as-of.json",
            _refresh_plan(
                evidence_sha256=cls.corpus_digest,
                treatment_population_sha256=cls.treatment_population_sha256,
                as_of="2026-09-02T12:00:00Z",
            ),
        )
        cls.input_snapshot = {
            path: path.read_bytes()
            for path in (
                cls.audit_plan,
                cls.incomplete_plan,
                cls.aliased_plan,
                cls.invalid_audit_plan,
                cls.deep_json,
                cls.primary,
                cls.changed_primary,
                cls.audit,
                cls.quote_changed_audit,
                cls.cross_document_audit,
                cls.same_reviewer_audit,
                cls.extra_field_audit,
                cls.foreign_audit,
                cls.remedy_audit,
                cls.valid_adjudication,
                cls.null_adjudication,
                cls.date_only_adjudication,
                cls.extra_field_adjudication,
                cls.aliased_reviewer_adjudication,
                cls.orphan_adjudication,
                cls.mismatched_audit,
                cls.minimal_plan,
                cls.minimal_primary,
                cls.minimal_audit,
                cls.malformed_types_plan,
                cls.malformed_types_primary,
                cls.malformed_types_audit,
                cls.empty_audit,
                cls.empty_treatments,
                cls.coverage_requirements,
                cls.failed_records_envelope,
                cls.refresh_current,
                cls.refresh_bounded,
                cls.refresh_pending,
                cls.refresh_invalid_contract,
                cls.refresh_invalid_gap,
                cls.refresh_wrong_digest,
                cls.refresh_stale_as_of,
            )
        }
        cls.corpus_tree_snapshots = {
            root: cls._tree_snapshot(root)
            for root in (
                cls.corpus_root,
                cls.malformed_corpus_root,
                cls.wal_corpus_root,
            )
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def _write_json(cls, name: str, value: object) -> Path:
        path = cls.root / name
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | None]]:
        snapshot: dict[str, tuple[str, bytes | None]] = {".": ("dir", None)}
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                snapshot[relative] = ("symlink", os.readlink(path).encode("utf-8"))
            elif path.is_dir():
                snapshot[relative] = ("dir", None)
            elif path.is_file():
                snapshot[relative] = ("file", path.read_bytes())
            else:
                snapshot[relative] = ("other", None)
        return snapshot

    def _locations(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("source", REPO / "skills" / SCRIPT),
            ("installed", self.installed / SCRIPT),
        )

    def _run(
        self,
        script: Path,
        arguments: list[str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *arguments],
            cwd=self.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )

    def _reliability_arguments(
        self,
        *,
        primary: Path,
        audit: Path,
        output: Path,
        plan: Path | None = None,
        adjudications: Path | None = None,
    ) -> list[str]:
        arguments = [
            "quality",
            "coding-reliability",
            "--audit-plan",
            str(plan or self.audit_plan),
            "--primary-decisions",
            str(primary),
            "--audit-decisions",
            str(audit),
        ]
        if adjudications is not None:
            arguments.extend(["--adjudications", str(adjudications)])
        arguments.extend(
            [
                "--output",
                str(output),
            ]
        )
        return arguments

    def _refresh_arguments(
        self,
        *,
        plan: Path,
        output: Path,
        current_digest: str | None = None,
        baseline_digest: str | None = None,
        subject_digest: str = "b" * 64,
        treatments: Path | None = None,
        checked_through: str = "2026-09-03T12:00:00Z",
        filing_cutoff: str = "2026-09-03T11:00:00Z",
        reviewed_at: str = "2026-09-03T12:10:00Z",
        claim_ids: tuple[str, ...] = ("claim-1",),
        corpus_root: Path | None = None,
    ) -> list[str]:
        effective_current_digest = current_digest or self.corpus_digest
        effective_baseline_digest = baseline_digest or self.corpus_digest
        arguments = [
            "quality",
            "prefiling-refresh",
            "--baseline-corpus-digest",
            effective_baseline_digest,
            "--current-corpus-digest",
            effective_current_digest,
            "--subject-evidence-sha256",
            subject_digest,
            "--refresh-plan",
            str(plan),
            "--treatments",
            str(treatments or self.empty_treatments),
            "--corpus-root",
            str(corpus_root or self.corpus_root),
            "--checked-through",
            checked_through,
            "--filing-cutoff",
            filing_cutoff,
            "--reviewer",
            "И.И. Иванов",
            "--reviewed-at",
            reviewed_at,
        ]
        for claim_id in claim_ids:
            arguments.extend(["--claim-id", claim_id])
        arguments.extend(["--output", str(output)])
        return arguments

    def _assert_persisted_result(
        self,
        completed: subprocess.CompletedProcess[str],
        output: Path,
        expected_code: int,
    ) -> dict[str, object]:
        self.assertEqual(completed.returncode, expected_code, completed.stderr)
        self.assertEqual(completed.stderr, "")
        stdout_payload = json.loads(completed.stdout)
        self.assertTrue(output.is_file())
        self.assertEqual(
            json.loads(output.read_text(encoding="utf-8")),
            stdout_payload,
        )
        self.assertFalse(output.with_suffix(output.suffix + ".tmp").exists())
        return stdout_payload

    def _assert_inputs_unchanged(self) -> None:
        for path, expected in self.input_snapshot.items():
            self.assertEqual(path.read_bytes(), expected, path.name)
        for root, expected in self.corpus_tree_snapshots.items():
            self.assertEqual(self._tree_snapshot(root), expected, str(root))
        self.assertFalse(self.missing_corpus_root.exists())

    def test_complete_quality_results_return_zero(self) -> None:
        observed: dict[str, list[dict[str, object]]] = {}
        for location, script in self._locations():
            location_results: list[dict[str, object]] = []
            cases = (
                (
                    "reliability",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.audit,
                        output=self.root / f"{location}-reliability-complete.json",
                    ),
                    "complete",
                    True,
                ),
                (
                    "refresh-current",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        output=self.root / f"{location}-refresh-current.json",
                    ),
                    "status",
                    "current_no_material_change",
                ),
                (
                    "refresh-bounded",
                    self._refresh_arguments(
                        plan=self.refresh_bounded,
                        output=self.root / f"{location}-refresh-bounded.json",
                    ),
                    "status",
                    "bounded_current_with_disclosed_gaps",
                ),
            )
            for name, arguments, field, expected in cases:
                with self.subTest(location=location, case=name):
                    output = Path(arguments[-1])
                    payload = self._assert_persisted_result(
                        self._run(script, list(arguments)),
                        output,
                        0,
                    )
                    self.assertIs(payload["complete"], True)
                    self.assertEqual(payload[field], expected)
                    location_results.append(payload)
            observed[location] = location_results
        self.assertEqual(observed["source"], observed["installed"])
        self._assert_inputs_unchanged()

    def test_reliability_binds_audit_and_adjudication_inputs(self) -> None:
        observed: dict[str, list[dict[str, object]]] = {}
        for location, script in self._locations():
            location_results: list[dict[str, object]] = []
            cases = (
                (
                    "original-audit",
                    self.audit,
                    None,
                ),
                (
                    "changed-audit",
                    self.quote_changed_audit,
                    None,
                ),
                (
                    "resolved-disagreement",
                    self.remedy_audit,
                    self.valid_adjudication,
                ),
            )
            for name, audit, adjudications in cases:
                with self.subTest(location=location, case=name):
                    output = self.root / f"{location}-{name}-binding.json"
                    payload = self._assert_persisted_result(
                        self._run(
                            script,
                            self._reliability_arguments(
                                primary=self.primary,
                                audit=audit,
                                adjudications=adjudications,
                                output=output,
                            ),
                        ),
                        output,
                        0,
                    )
                    self.assertRegex(payload["audit_decisions_sha256"], r"^[0-9a-f]{64}$")
                    self.assertRegex(payload["adjudications_sha256"], r"^[0-9a-f]{64}$")
                    location_results.append(payload)
            self.assertNotEqual(
                location_results[0]["audit_decisions_sha256"],
                location_results[1]["audit_decisions_sha256"],
            )
            self.assertNotEqual(
                location_results[0]["evidence_sha256"],
                location_results[1]["evidence_sha256"],
            )
            observed[location] = location_results
        self.assertEqual(observed["source"], observed["installed"])
        self._assert_inputs_unchanged()

    def test_incomplete_and_stale_quality_results_return_three(self) -> None:
        observed: dict[str, list[dict[str, object]]] = {}
        for location, script in self._locations():
            location_results: list[dict[str, object]] = []
            cases = (
                (
                    "reliability-missing",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.empty_audit,
                        output=self.root / f"{location}-reliability-missing.json",
                    ),
                    None,
                ),
                (
                    "reliability-stale",
                    self._reliability_arguments(
                        primary=self.changed_primary,
                        audit=self.audit,
                        output=self.root / f"{location}-reliability-stale.json",
                    ),
                    None,
                ),
                (
                    "reliability-mismatched-secondary",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.mismatched_audit,
                        output=(
                            self.root / f"{location}-reliability-mismatch.json"
                        ),
                    ),
                    None,
                ),
                (
                    "reliability-cross-document-secondary",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.cross_document_audit,
                        output=self.root / f"{location}-reliability-cross-document.json",
                    ),
                    None,
                ),
                (
                    "reliability-same-reviewer-alias",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.same_reviewer_audit,
                        output=self.root / f"{location}-reliability-same-reviewer.json",
                    ),
                    None,
                ),
                (
                    "reliability-extra-audit-field",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.extra_field_audit,
                        output=self.root / f"{location}-reliability-extra-audit.json",
                    ),
                    None,
                ),
                (
                    "reliability-foreign-audit",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.foreign_audit,
                        output=self.root / f"{location}-reliability-foreign-audit.json",
                    ),
                    None,
                ),
                (
                    "reliability-null-adjudication",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.remedy_audit,
                        adjudications=self.null_adjudication,
                        output=self.root / f"{location}-reliability-null-adjudication.json",
                    ),
                    None,
                ),
                (
                    "reliability-date-only-adjudication",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.remedy_audit,
                        adjudications=self.date_only_adjudication,
                        output=self.root / f"{location}-reliability-date-adjudication.json",
                    ),
                    None,
                ),
                (
                    "reliability-extra-adjudication-field",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.remedy_audit,
                        adjudications=self.extra_field_adjudication,
                        output=self.root / f"{location}-reliability-extra-adjudication.json",
                    ),
                    None,
                ),
                (
                    "reliability-aliased-adjudicator",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.remedy_audit,
                        adjudications=self.aliased_reviewer_adjudication,
                        output=self.root / f"{location}-reliability-aliased-adjudicator.json",
                    ),
                    None,
                ),
                (
                    "reliability-orphan-adjudication",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.audit,
                        adjudications=self.orphan_adjudication,
                        output=self.root / f"{location}-reliability-orphan-adjudication.json",
                    ),
                    None,
                ),
                (
                    "reliability-incomplete-coding-records",
                    self._reliability_arguments(
                        plan=self.minimal_plan,
                        primary=self.minimal_primary,
                        audit=self.minimal_audit,
                        output=(
                            self.root / f"{location}-reliability-incomplete.json"
                        ),
                    ),
                    None,
                ),
                (
                    "reliability-incomplete-audit-plan",
                    self._reliability_arguments(
                        plan=self.incomplete_plan,
                        primary=self.primary,
                        audit=self.audit,
                        output=(
                            self.root / f"{location}-reliability-incomplete-plan.json"
                        ),
                    ),
                    None,
                ),
                (
                    "reliability-malformed-coding-types",
                    self._reliability_arguments(
                        plan=self.malformed_types_plan,
                        primary=self.malformed_types_primary,
                        audit=self.malformed_types_audit,
                        output=(
                            self.root / f"{location}-reliability-malformed-types.json"
                        ),
                    ),
                    None,
                ),
                (
                    "reliability-aliased-audit-plan",
                    self._reliability_arguments(
                        plan=self.aliased_plan,
                        primary=self.primary,
                        audit=self.audit,
                        output=(
                            self.root / f"{location}-reliability-aliased-plan.json"
                        ),
                    ),
                    None,
                ),
                (
                    "refresh-timezone-missing",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        checked_through="2026-09-03T12:00:00",
                        filing_cutoff="2026-09-03T11:00:00",
                        reviewed_at="2026-09-03T12:10:00",
                        output=self.root / f"{location}-refresh-timezone-missing.json",
                    ),
                    "refresh_incomplete",
                ),
                (
                    "refresh-invalid-plan-contract",
                    self._refresh_arguments(
                        plan=self.refresh_invalid_contract,
                        output=self.root / f"{location}-refresh-invalid-plan.json",
                    ),
                    "refresh_incomplete",
                ),
                (
                    "refresh-invalid-coverage-gap",
                    self._refresh_arguments(
                        plan=self.refresh_invalid_gap,
                        output=self.root / f"{location}-refresh-invalid-gap.json",
                    ),
                    "refresh_incomplete",
                ),
                (
                    "refresh-wrong-corpus-binding",
                    self._refresh_arguments(
                        plan=self.refresh_wrong_digest,
                        output=self.root / f"{location}-refresh-wrong-digest.json",
                    ),
                    "refresh_incomplete",
                ),
                (
                    "refresh-stale-plan-time",
                    self._refresh_arguments(
                        plan=self.refresh_stale_as_of,
                        output=self.root / f"{location}-refresh-stale-plan.json",
                    ),
                    "refresh_incomplete",
                ),
                (
                    "refresh-pending",
                    self._refresh_arguments(
                        plan=self.refresh_pending,
                        output=self.root / f"{location}-refresh-pending.json",
                    ),
                    "refresh_incomplete",
                ),
                (
                    "refresh-material-change",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        current_digest="c" * 64,
                        output=self.root / f"{location}-refresh-changed.json",
                    ),
                    "material_change_requires_reanalysis",
                ),
            )
            for name, arguments, expected_status in cases:
                with self.subTest(location=location, case=name):
                    output = Path(arguments[-1])
                    payload = self._assert_persisted_result(
                        self._run(script, list(arguments)),
                        output,
                        3,
                    )
                    self.assertIs(payload["complete"], False)
                    if name == "reliability-missing":
                        self.assertFalse(payload["stale"])
                    elif name == "reliability-stale":
                        self.assertTrue(payload["stale"])
                    elif name == "reliability-mismatched-secondary":
                        self.assertEqual(
                            payload["invalid_binding_candidate_ids"],
                            ["candidate-1"],
                        )
                    elif name == "reliability-cross-document-secondary":
                        self.assertEqual(
                            payload["invalid_binding_candidate_ids"],
                            ["candidate-1"],
                        )
                    elif name == "reliability-same-reviewer-alias":
                        self.assertEqual(
                            payload["same_reviewer_candidate_ids"],
                            ["candidate-1"],
                        )
                    elif name in {
                        "reliability-extra-audit-field",
                        "reliability-foreign-audit",
                    }:
                        self.assertTrue(payload["invalid_audit_record_ids"])
                    elif name.startswith("reliability-") and name.endswith(
                        "adjudication"
                    ):
                        self.assertTrue(payload["invalid_adjudication_record_ids"])
                        self.assertEqual(
                            payload["unresolved_candidate_ids"],
                            ["candidate-1"],
                        )
                    elif name == "reliability-incomplete-coding-records":
                        self.assertEqual(
                            payload["invalid_primary_record_ids"],
                            ["candidate-minimal"],
                        )
                        self.assertEqual(
                            payload["invalid_audit_record_ids"],
                            ["candidate-minimal"],
                        )
                        self.assertEqual(
                            payload["unresolved_candidate_ids"],
                            ["candidate-minimal"],
                        )
                    elif name in {
                        "reliability-incomplete-audit-plan",
                        "reliability-aliased-audit-plan",
                    }:
                        self.assertIs(payload["audit_plan_digest_valid"], True)
                        self.assertIs(payload["audit_plan_contract_valid"], False)
                        self.assertIs(payload["stale"], True)
                        self.assertIn(
                            "audit-plan-contract-invalid",
                            payload["unresolved_candidate_ids"],
                        )
                    elif name == "reliability-malformed-coding-types":
                        self.assertEqual(
                            payload["invalid_primary_record_ids"],
                            ["candidate-types"],
                        )
                        self.assertEqual(
                            payload["invalid_audit_record_ids"],
                            ["candidate-types"],
                        )
                        self.assertEqual(
                            payload["unresolved_candidate_ids"],
                            ["candidate-types"],
                        )
                    elif name == "refresh-timezone-missing":
                        self.assertIn("timestamp_timezone_missing", payload["reasons"])
                    elif name.startswith("refresh-") and name in {
                        "refresh-invalid-plan-contract",
                        "refresh-invalid-coverage-gap",
                        "refresh-wrong-corpus-binding",
                        "refresh-stale-plan-time",
                    }:
                        self.assertIs(payload["refresh_plan_contract_valid"], False)
                        self.assertIn("refresh_plan_contract_invalid", payload["reasons"])
                    if expected_status is not None:
                        self.assertEqual(payload["status"], expected_status)
                    location_results.append(payload)
            observed[location] = location_results
        self.assertEqual(observed["source"], observed["installed"])
        self._assert_inputs_unchanged()

    def test_invalid_inputs_remain_code_two_without_partial_output(self) -> None:
        for location, script in self._locations():
            missing_primary = self.root / "missing-primary.jsonl"
            missing_audit = self.root / "missing-audit.jsonl"
            missing_adjudications = self.root / "missing-adjudications.jsonl"
            missing_treatments = self.root / "missing-treatments.jsonl"
            cases = (
                (
                    "malformed-audit-plan",
                    self._reliability_arguments(
                        plan=self.invalid_audit_plan,
                        primary=self.primary,
                        audit=self.audit,
                        output=self.root / f"{location}-invalid-reliability.json",
                    ),
                ),
                (
                    "deep-json",
                    self._reliability_arguments(
                        plan=self.deep_json,
                        primary=self.primary,
                        audit=self.audit,
                        output=self.root / f"{location}-deep-json.json",
                    ),
                ),
                (
                    "missing-primary",
                    self._reliability_arguments(
                        primary=missing_primary,
                        audit=self.audit,
                        output=self.root / f"{location}-missing-primary.json",
                    ),
                ),
                (
                    "missing-audit",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=missing_audit,
                        output=self.root / f"{location}-missing-audit.json",
                    ),
                ),
                (
                    "missing-adjudications",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.audit,
                        adjudications=missing_adjudications,
                        output=self.root / f"{location}-missing-adjudications.json",
                    ),
                ),
                (
                    "invalid-corpus-digest",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        baseline_digest="not-a-digest",
                        output=self.root / f"{location}-invalid-refresh.json",
                    ),
                ),
                (
                    "invalid-subject-digest",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        subject_digest="not-a-digest",
                        output=self.root / f"{location}-invalid-subject.json",
                    ),
                ),
                (
                    "missing-treatments",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        treatments=missing_treatments,
                        output=self.root / f"{location}-missing-treatments.json",
                    ),
                ),
                (
                    "missing-corpus-root",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        corpus_root=self.missing_corpus_root,
                        output=self.root / f"{location}-missing-corpus-root.json",
                    ),
                ),
                (
                    "malformed-corpus-schema",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        corpus_root=self.malformed_corpus_root,
                        output=self.root / f"{location}-malformed-corpus-schema.json",
                    ),
                ),
                (
                    "wal-corpus-root",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        corpus_root=self.wal_corpus_root,
                        output=self.root / f"{location}-wal-corpus-root.json",
                    ),
                ),
                (
                    "failed-primary-envelope",
                    self._reliability_arguments(
                        primary=self.failed_records_envelope,
                        audit=self.audit,
                        output=self.root / f"{location}-failed-primary-envelope.json",
                    ),
                ),
                (
                    "failed-audit-envelope",
                    self._reliability_arguments(
                        primary=self.primary,
                        audit=self.failed_records_envelope,
                        output=self.root / f"{location}-failed-audit-envelope.json",
                    ),
                ),
                (
                    "failed-treatment-envelope",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        treatments=self.failed_records_envelope,
                        output=self.root / f"{location}-failed-treatment-envelope.json",
                    ),
                ),
                (
                    "date-only-timestamps",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        checked_through="2026-09-03",
                        filing_cutoff="2026-09-03",
                        reviewed_at="2026-09-03",
                        output=self.root / f"{location}-date-only-timestamps.json",
                    ),
                ),
                (
                    "treatments-is-directory",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        treatments=self.root,
                        output=self.root / f"{location}-directory-treatments.json",
                    ),
                ),
                (
                    "empty-claim-id",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        claim_ids=("",),
                        output=self.root / f"{location}-empty-claim-id.json",
                    ),
                ),
                (
                    "missing-claim-id",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        claim_ids=(),
                        output=self.root / f"{location}-missing-claim-id.json",
                    ),
                ),
                (
                    "duplicate-claim-id",
                    self._refresh_arguments(
                        plan=self.refresh_current,
                        claim_ids=("claim-1", "claim-1"),
                        output=self.root / f"{location}-duplicate-claim-id.json",
                    ),
                ),
            )
            for name, arguments in cases:
                with self.subTest(location=location, case=name):
                    output = Path(arguments[-1])
                    completed = self._run(script, list(arguments))
                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(completed.stdout, "")
                    if name == "missing-claim-id":
                        self.assertIn(
                            "the following arguments are required: --claim-id",
                            completed.stderr,
                        )
                    else:
                        self.assertTrue(completed.stderr.startswith("Ошибка: "))
                        self.assertEqual(
                            completed.stderr.count("\n"),
                            1,
                            "input failures must remain one-line diagnostics",
                        )
                    if name == "invalid-subject-digest":
                        self.assertEqual(
                            completed.stderr,
                            "Ошибка: Параметр --subject-evidence-sha256 должен "
                            "содержать 64 строчные шестнадцатеричные цифры.\n",
                        )
                    elif name == "date-only-timestamps":
                        self.assertEqual(
                            completed.stderr,
                            "Ошибка: Параметры --checked-through, --filing-cutoff и "
                            "--reviewed-at должны содержать дату и время "
                            "в формате ISO 8601.\n",
                        )
                    self.assertFalse(output.exists())
        self._assert_inputs_unchanged()

    def test_quality_gate_exit_helper_requires_exact_boolean_true(self) -> None:
        from judicial_meaning.cli import _quality_gate_exit_code

        for payload, expected in (
            ({"complete": True}, 0),
            ({"complete": False}, 3),
            ({"complete": 1}, 3),
            ({"complete": "true"}, 3),
            ({"complete": None}, 3),
            ({}, 3),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(_quality_gate_exit_code(payload), expected)

    def test_help_explains_exit_contract_in_source_and_install(self) -> None:
        invocations = (
            ("coding-reliability", ["quality", "coding-reliability", "--help"]),
            ("prefiling-refresh", ["quality", "prefiling-refresh", "--help"]),
        )
        for location, script in self._locations():
            for route, arguments in invocations:
                with self.subTest(location=location, route=route):
                    completed = self._run(script, list(arguments))
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    normalized = " ".join(completed.stdout.split())
                    for required in HELP_REQUIRED:
                        self.assertIn(required, normalized)
                    if route == "prefiling-refresh":
                        for required in (
                            "--corpus-root",
                            "открывает её только для чтения",
                            "заново сверяет план",
                            "не процессуальный срок",
                        ):
                            self.assertIn(required, normalized)

    def test_refresh_plan_producer_feeds_prefiling_gate(self) -> None:
        observed: dict[str, dict[str, object]] = {}
        for location, script in self._locations():
            with self.subTest(location=location):
                cache_root = self.root / f"{location}-public-cache"
                produced = self._run(
                    script,
                    [
                        "cache",
                        "refresh-plan",
                        "--root",
                        str(cache_root),
                        "--as-of",
                        "2026-09-03T12:00:00Z",
                        "--max-age-seconds",
                        "604800",
                        "--coverage-requirements",
                        str(self.coverage_requirements),
                    ],
                )
                self.assertEqual(produced.returncode, 0, produced.stderr)
                self.assertEqual(produced.stderr, "")
                plan = json.loads(produced.stdout)
                plan_path = self._write_json(f"{location}-produced-refresh.json", plan)
                producer_digest = str(plan["evidence_digest"])
                treatment_path = self.root / f"{location}-produced-treatments.json"
                treatment_export = self._run(
                    script,
                    [
                        "cache",
                        "treatment",
                        "quality-export",
                        "--root",
                        str(cache_root),
                        "--output",
                        str(treatment_path),
                    ],
                )
                self.assertEqual(treatment_export.returncode, 0, treatment_export.stderr)
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._refresh_arguments(
                            plan=plan_path,
                            baseline_digest=producer_digest,
                            current_digest=producer_digest,
                            treatments=treatment_path,
                            corpus_root=cache_root,
                            output=self.root / f"{location}-produced-prefiling.json",
                        ),
                    ),
                    self.root / f"{location}-produced-prefiling.json",
                    0,
                )
                self.assertIs(result["refresh_plan_contract_valid"], True)
                self.assertEqual(
                    result["current_corpus_digest"],
                    producer_digest.removeprefix("corpus-evidence-sha256:"),
                )
                self.assertEqual(result["refresh_plan_as_of"], plan["as_of"])
                self.assertEqual(
                    result["refresh_plan_max_age_seconds"],
                    plan["max_age_seconds"],
                )
                self.assertEqual(
                    result["refresh_plan_evidence_digest"],
                    plan["evidence_digest"],
                )
                self.assertEqual(
                    result["refresh_plan_coverage_requirements"],
                    plan["coverage_requirements"],
                )
                observed[location] = result
        self.assertEqual(observed["source"], observed["installed"])

    def test_refresh_plan_cli_rejects_empty_coverage_scope(self) -> None:
        for location, script in self._locations():
            with self.subTest(location=location):
                completed = self._run(
                    script,
                    [
                        "cache",
                        "refresh-plan",
                        "--root",
                        str(self.root / f"{location}-empty-coverage-cache"),
                        "--as-of",
                        "2026-09-03T12:00:00Z",
                        "--max-age-seconds",
                        "604800",
                        "--coverage-requirements",
                        str(self.empty_audit),
                    ],
                )
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertIn("хотя бы один сегмент охвата", completed.stderr)

    def test_official_treatment_producer_feeds_prefiling_gate(self) -> None:
        observed: dict[str, dict[str, object]] = {}
        raw = self.root / "official-treatment.html"
        raw.write_text(
            "Суд применяет правовую позицию Конституционного Суда.",
            encoding="utf-8",
        )
        text_path = self.root / "official-treatment.txt"
        text_path.write_text(raw.read_text(encoding="utf-8"), encoding="utf-8")
        parser_manifest = self._write_json(
            "treatment-parser-manifest.json",
            {"adapter_id": "bounded-test", "parser_version": "1.0"},
        )
        target_identity = self._write_json(
            "treatment-target-identity.json",
            {"act_number": "32-П", "act_date": "2023-06-15"},
        )
        for location, script in self._locations():
            cache_root = self.root / f"{location}-treatment-cache"
            seed = self._run(
                script,
                [
                    "cache", "register-seed", "--root", str(cache_root),
                    "--url", "https://2kas.sudrf.ru/modules.php?name=sud_delo&number=77",
                    "--role", "official_user_seed",
                ],
            )
            self.assertEqual(seed.returncode, 0, seed.stderr)
            seed_id = json.loads(seed.stdout)["seed_id"]
            ingested = self._run(
                script,
                [
                    "cache", "ingest", "--root", str(cache_root),
                    "--seed-id", seed_id, "--raw", str(raw),
                    "--content-type", "text/html; charset=utf-8",
                    "--fetched-at", "2026-09-03T11:59:00Z",
                    "--parser-manifest", str(parser_manifest),
                    "--text", str(text_path),
                    "--document-id", "document-treatment-e2e",
                    "--chain-id", "chain-treatment-e2e",
                    "--query-lane", "higher_authority",
                ],
            )
            self.assertEqual(ingested.returncode, 0, ingested.stderr)
            snapshot_id = json.loads(ingested.stdout)["snapshot_id"]
            discovered = self._run(
                script,
                [
                    "cache", "treatment", "discover", "--root", str(cache_root),
                    "--source-chain-id", "chain-treatment-e2e",
                    "--source-court-id", "2kas",
                    "--target-authority-id", "ksrf-32-p-2023",
                    "--target-kind", "constitutional_court_act",
                    "--target-identity", str(target_identity),
                    "--treatment-type", "applies",
                    "--snapshot-id", snapshot_id,
                ],
            )
            self.assertEqual(discovered.returncode, 0, discovered.stderr)
            treatment_id = json.loads(discovered.stdout)["treatment_id"]
            reviewed = self._run(
                script,
                [
                    "cache", "treatment", "review", "--root", str(cache_root),
                    "--treatment-id", treatment_id,
                    "--decision", "verified", "--reviewer", "П.П. Петров",
                    "--quote", "Суд применяет правовую позицию Конституционного Суда",
                    "--locator", "абзац 1", "--speaker", "court",
                    "--confirmed-target-authority-id", "ksrf-32-p-2023",
                    "--target-identity-confirmed",
                ],
            )
            self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
            treatment_reviewed_at = json.loads(reviewed.stdout)["reviewed_at"]
            treatment_export_path = self.root / f"{location}-treatment-export.json"
            exported = self._run(
                script,
                [
                    "cache", "treatment", "quality-export", "--root", str(cache_root),
                    "--output", str(treatment_export_path),
                ],
            )
            self.assertEqual(exported.returncode, 0, exported.stderr)
            treatment_set = json.loads(exported.stdout)
            self.assertEqual([treatment_id], treatment_set["treatment_ids"])
            self.assertEqual("verified", treatment_set["items"][0]["status"])
            refresh = self._run(
                script,
                [
                    "cache", "refresh-plan", "--root", str(cache_root),
                    "--as-of", treatment_reviewed_at,
                    "--max-age-seconds", "604800",
                    "--coverage-requirements", str(self.coverage_requirements),
                ],
            )
            self.assertEqual(refresh.returncode, 0, refresh.stderr)
            plan = json.loads(refresh.stdout)
            self.assertEqual([treatment_id], plan["treatment_ids"])
            self.assertEqual(
                treatment_set["treatment_population_sha256"],
                plan["treatment_population_sha256"],
            )
            plan_path = self._write_json(
                f"{location}-treatment-refresh-plan.json", plan
            )
            digest = str(plan["evidence_digest"])
            output = self.root / f"{location}-treatment-prefiling.json"
            result = self._assert_persisted_result(
                self._run(
                    script,
                    self._refresh_arguments(
                        plan=plan_path,
                        baseline_digest=digest,
                        current_digest=digest,
                        treatments=treatment_export_path,
                        corpus_root=cache_root,
                        output=output,
                        checked_through=treatment_reviewed_at,
                        reviewed_at=treatment_reviewed_at,
                    ),
                ),
                output,
                0,
            )
            self.assertEqual([treatment_id], result["verified_treatment_ids"])
            self.assertIs(result["treatment_set_contract_valid"], True)
            observed[location] = result
        for field in (
            "status",
            "complete",
            "verified_treatment_ids",
            "pending_treatment_ids",
            "treatment_set_contract_valid",
        ):
            self.assertEqual(observed["source"][field], observed["installed"][field])

    def test_corrupt_live_cache_cannot_produce_complete_prefiling_result(self) -> None:
        cache_root = self.root / "corrupt-live-cache"
        with PublicCorpus(cache_root) as corpus:
            seed = corpus.register_seed(
                url="https://2kas.sudrf.ru/modules.php?name=sud_delo&number=corrupt",
                role="official_user_seed",
                public=True,
            )
            snapshot = corpus.store_snapshot(
                seed_id=seed["seed_id"],
                raw="Проверенный текст.".encode("utf-8"),
                content_type="text/html; charset=utf-8",
                fetched_at="2026-09-03T12:00:00Z",
                parser_manifest={"adapter_id": "test", "parser_version": "1.0"},
            )
            corpus.record_funnel(
                "chain-corrupt-live",
                "enumerated",
                source_role="official_user_seed",
                court_id="2kas",
            )
            for status in (
                "card",
                "document_link",
                "payload_validated",
                "full_text_extracted",
            ):
                corpus.record_funnel(
                    "chain-corrupt-live",
                    status,
                    snapshot_id=snapshot["snapshot_id"],
                    source_role="official_user_seed",
                    court_id="2kas",
                )
            plan = corpus.plan_refresh(
                as_of="2026-09-03T12:00:00Z",
                max_age_seconds=604800,
                coverage_requirements=[{"court_id": "2kas"}],
            )
            treatment_set = corpus.treatment_quality_export()
        plan_path = self._write_json("corrupt-live-plan.json", plan)
        treatment_path = self._write_json(
            "corrupt-live-treatments.json", treatment_set
        )
        Path(snapshot["object_path"]).unlink()
        cache_before = self._tree_snapshot(cache_root)
        digest = str(plan["evidence_digest"])
        for location, script in self._locations():
            with self.subTest(location=location):
                output = self.root / f"{location}-corrupt-live-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._refresh_arguments(
                            plan=plan_path,
                            baseline_digest=digest,
                            current_digest=digest,
                            treatments=treatment_path,
                            corpus_root=cache_root,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertIs(result["complete"], False)
                self.assertIn(
                    "live_cache_integrity_invalid",
                    result["live_binding_issue_ids"],
                )
                self.assertEqual(cache_before, self._tree_snapshot(cache_root))

    def test_discovery_only_cache_is_valid_input_but_not_official_coverage(self) -> None:
        cache_root = self.root / "discovery-only-cache"
        with PublicCorpus(cache_root) as corpus:
            seed = corpus.register_seed(
                url="https://example.org/discovery/case-1",
                role="discovery_only",
                public=True,
            )
            corpus.record_funnel(
                "chain-discovery",
                "enumerated",
                source_role="discovery_only",
                court_id="discovery-court",
            )
            plan = corpus.plan_refresh(
                as_of="2026-09-03T12:00:00Z",
                max_age_seconds=604800,
                coverage_requirements=[{"court_id": "discovery-court"}],
            )
            treatment_set = corpus.treatment_quality_export()
        self.assertTrue(plan["entries"])
        self.assertTrue(plan["coverage_gaps"])
        plan_path = self._write_json("discovery-only-plan.json", plan)
        treatment_path = self._write_json(
            "discovery-only-treatments.json", treatment_set
        )
        digest = str(plan["evidence_digest"])
        for location, script in self._locations():
            with self.subTest(location=location):
                output = self.root / f"{location}-discovery-only-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._refresh_arguments(
                            plan=plan_path,
                            baseline_digest=digest,
                            current_digest=digest,
                            treatments=treatment_path,
                            corpus_root=cache_root,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertIs(result["refresh_plan_contract_valid"], True)
                self.assertIn(
                    "stale_or_unfetched_public_seeds", result["reasons"]
                )

    def test_rfc3339_reduced_times_fail_closed_in_source_and_install(self) -> None:
        for location, script in self._locations():
            for invalid_time in (
                "2026-09-03T12Z",
                "2026-09-03T12:20Z",
                "2026-W36-4T12:20:00Z",
                " 2026-09-03T12:20:00Z ",
            ):
                with self.subTest(location=location, invalid_time=invalid_time):
                    produced = self._run(
                        script,
                        [
                            "cache",
                            "refresh-plan",
                            "--root",
                            str(self.root / f"{location}-invalid-time-cache"),
                            "--as-of",
                            invalid_time,
                            "--max-age-seconds",
                            "604800",
                            "--coverage-requirements",
                            str(self.coverage_requirements),
                        ],
                    )
                    self.assertEqual(produced.returncode, 2)
                    self.assertEqual(produced.stdout, "")
                    self.assertTrue(produced.stderr.startswith("Ошибка: "))
                    output = self.root / f"{location}-{canonical_digest(invalid_time)}.json"
                    completed = self._run(
                        script,
                        self._refresh_arguments(
                            plan=self.refresh_current,
                            checked_through=invalid_time,
                            output=output,
                        ),
                    )
                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(completed.stdout, "")
                    self.assertTrue(completed.stderr.startswith("Ошибка: "))
                    self.assertFalse(output.exists())

    def test_reduced_adjudication_times_are_rejected_by_runtime_and_schema(self) -> None:
        schema = json.loads(
            (REPO / "skills" / SKILL / "schemas" / "practice-quality.v1.json").read_text(
                encoding="utf-8"
            )
        )
        validator = definition_validator(schema, "coding_adjudication")
        valid_records = json.loads(self.valid_adjudication.read_text(encoding="utf-8"))
        for invalid_time in (
            "2026-09-03T12Z",
            "2026-09-03T12:20Z",
            "2026-W36-4T12:20:00Z",
            " 2026-09-03T12:20:00Z ",
        ):
            invalid_records = copy.deepcopy(valid_records)
            invalid_records[0]["reviewed_at"] = invalid_time
            self.assertTrue(list(validator.iter_errors(invalid_records[0])))
            invalid_path = self._write_json(
                f"adjudication-{canonical_digest(invalid_time)}.json",
                invalid_records,
            )
            for location, script in self._locations():
                with self.subTest(location=location, invalid_time=invalid_time):
                    output = self.root / (
                        f"{location}-invalid-adjudication-"
                        f"{canonical_digest(invalid_time)}.json"
                    )
                    result = self._assert_persisted_result(
                        self._run(
                            script,
                            self._reliability_arguments(
                                primary=self.primary,
                                audit=self.remedy_audit,
                                adjudications=invalid_path,
                                output=output,
                            ),
                        ),
                        output,
                        3,
                    )
                    self.assertIs(result["complete"], False)
                    self.assertTrue(result["invalid_adjudication_record_ids"])

    def test_resolved_treatment_requires_official_relation_provenance(self) -> None:
        valid = _reviewed_treatment()
        localhost = copy.deepcopy(valid)
        localhost["official_url"] = "http://localhost/private"
        localhost["source_binding_sha256"] = canonical_digest(
            {field: localhost.get(field) for field in TREATMENT_BOUND_FIELDS}
        )
        missing_relation = copy.deepcopy(valid)
        del missing_relation["source_chain_id"]
        missing_relation["source_binding_sha256"] = canonical_digest(
            {field: missing_relation.get(field) for field in TREATMENT_BOUND_FIELDS}
        )
        treatment_files = {
            "valid": self._write_json(
                "valid-reviewed-treatment.json",
                _treatment_set(
                    [valid],
                    corpus_digest=self.corpus_digest,
                    treatment_population_sha256=self.treatment_population_sha256,
                ),
            ),
            "localhost": self._write_json(
                "localhost-treatment.json",
                _treatment_set(
                    [localhost],
                    corpus_digest=self.corpus_digest,
                    treatment_population_sha256=self.treatment_population_sha256,
                ),
            ),
            "missing-relation": self._write_json(
                "missing-relation-treatment.json",
                _treatment_set(
                    [missing_relation],
                    corpus_digest=self.corpus_digest,
                    treatment_population_sha256=self.treatment_population_sha256,
                ),
            ),
        }
        treatment_plan = self._write_json(
            "reviewed-treatment-refresh-plan.json",
            _refresh_plan(
                evidence_sha256=self.corpus_digest,
                treatment_ids=["treatment-reviewed"],
                treatment_population_sha256=self.treatment_population_sha256,
            ),
        )
        for location, script in self._locations():
            for name, treatment_file in treatment_files.items():
                with self.subTest(location=location, case=name):
                    output = self.root / f"{location}-{name}-treatment-result.json"
                    payload = self._assert_persisted_result(
                        self._run(
                            script,
                            self._refresh_arguments(
                                plan=treatment_plan,
                                treatments=treatment_file,
                                output=output,
                            ),
                        ),
                        output,
                        3,
                    )
                    self.assertIs(payload["complete"], False)
                    if name == "valid":
                        self.assertIs(payload["treatment_set_contract_valid"], True)
                        self.assertIn("live_corpus_binding_mismatch", payload["reasons"])
                    else:
                        self.assertEqual(
                            payload["invalid_resolved_treatment_ids"]
                            if "invalid_resolved_treatment_ids" in payload
                            else payload["pending_treatment_ids"],
                            ["treatment-reviewed"],
                        )

    def test_audit_routes_require_explicit_canonical_candidate_ids(self) -> None:
        valid_screening = {"candidate_id": "candidate-1"}
        for case_name, invalid_id in (("missing", None), ("whitespace", "  alias  ")):
            malformed_screening = {
                "chain_id": "legacy-chain",
                "document_id": "legacy-document",
            }
            malformed_primary = _primary()
            malformed_primary["chain_id"] = "legacy-chain"
            malformed_primary["document_id"] = "legacy-document"
            if invalid_id is not None:
                malformed_screening["candidate_id"] = invalid_id
                malformed_primary["candidate_id"] = invalid_id
            else:
                malformed_primary.pop("candidate_id")
            screening_path = self._write_json(
                f"{case_name}-candidate-frame.json",
                [valid_screening, malformed_screening],
            )
            primary_path = self._write_json(
                f"{case_name}-candidate-primary.json",
                [json.loads(self.primary.read_text(encoding="utf-8"))[0], malformed_primary],
            )
            for location, script in self._locations():
                with self.subTest(location=location, case=case_name):
                    plan_path = self.root / f"{location}-{case_name}-strict-plan.json"
                    produced = self._run(
                        script,
                        [
                            "quality",
                            "coding-audit-plan",
                            "--screening-candidates",
                            str(screening_path),
                            "--primary-decisions",
                            str(primary_path),
                            "--plan-sha256",
                            "d" * 64,
                            "--sample-size",
                            "1",
                            "--exclusion-sample-size",
                            "0",
                            "--output",
                            str(plan_path),
                        ],
                    )
                    self.assertEqual(produced.returncode, 0, produced.stderr)
                    plan = json.loads(produced.stdout)
                    self.assertTrue(plan["invalid_screening_record_ids"])
                    self.assertTrue(plan["invalid_primary_record_ids"])
                    result_path = self.root / f"{location}-{case_name}-strict-result.json"
                    result = self._assert_persisted_result(
                        self._run(
                            script,
                            self._reliability_arguments(
                                plan=plan_path,
                                primary=primary_path,
                                audit=self.audit,
                                output=result_path,
                            ),
                        ),
                        result_path,
                        3,
                    )
                    self.assertIs(result["complete"], False)
                    self.assertTrue(result["invalid_screening_record_ids"])
                    self.assertTrue(result["invalid_primary_record_ids"])

    def test_zero_width_reviewer_alias_cannot_pass_independence_gate(self) -> None:
        primary = _primary()
        primary["coder"] = "A"
        secondary = copy.deepcopy(primary)
        secondary["coder"] = "A\u200b"
        plan = build_coding_audit_plan(
            [{"candidate_id": "candidate-1"}],
            [primary],
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        audit = {
            "candidate_id": "candidate-1",
            "primary_coding_sha256": canonical_digest(primary),
            "secondary_coding": secondary,
            "secondary_coding_sha256": canonical_digest(secondary),
        }
        plan_path = self._write_json("zero-width-plan.json", plan)
        primary_path = self._write_json("zero-width-primary.json", [primary])
        audit_path = self._write_json("zero-width-audit.json", [audit])
        for location, script in self._locations():
            with self.subTest(location=location):
                output = self.root / f"{location}-zero-width-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._reliability_arguments(
                            plan=plan_path,
                            primary=primary_path,
                            audit=audit_path,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertEqual(result["same_reviewer_candidate_ids"], [])
                self.assertEqual(
                    result["invalid_audit_record_ids"], ["candidate-1"]
                )
                self.assertIs(result["complete"], False)

    def test_invisible_coding_content_cannot_simulate_agreement(self) -> None:
        mutations = {
            "speaker": lambda record: record.update(
                {"label": "false_positive", "speaker": "\u200b"}
            ),
            "proposition": lambda record: record.update({"proposition": "\u200b"}),
            "quote": lambda record: record.update({"quote": "\u200b"}),
            "quote_locator": lambda record: record.update({"quote_locator": "\u200b"}),
            "reasoning": lambda record: record.update(
                {"reasoning_to_outcome": "\u200b"}
            ),
            "material_fact": lambda record: record.update(
                {"material_facts": ["\u200b"]}
            ),
            "alternative_ground": lambda record: record.update(
                {
                    "alternative_grounds": [
                        {"ground": "\u200b", "independently_sufficient": False}
                    ]
                }
            ),
        }
        for case_name, mutate in mutations.items():
            primary = _primary()
            mutate(primary)
            secondary = copy.deepcopy(primary)
            secondary["coder"] = "secondary-b"
            plan = build_coding_audit_plan(
                [{"candidate_id": "candidate-1"}],
                [primary],
                plan_sha256="d" * 64,
                sample_size=1,
                exclusion_sample_size=0,
            )
            audit = {
                "candidate_id": "candidate-1",
                "primary_coding_sha256": canonical_digest(primary),
                "secondary_coding": secondary,
                "secondary_coding_sha256": canonical_digest(secondary),
            }
            plan_path = self._write_json(f"{case_name}-plan.json", plan)
            primary_path = self._write_json(f"{case_name}-primary.json", [primary])
            audit_path = self._write_json(f"{case_name}-audit.json", [audit])
            for location, script in self._locations():
                with self.subTest(case=case_name, location=location):
                    output = self.root / f"{location}-{case_name}-result.json"
                    result = self._assert_persisted_result(
                        self._run(
                            script,
                            self._reliability_arguments(
                                plan=plan_path,
                                primary=primary_path,
                                audit=audit_path,
                                output=output,
                            ),
                        ),
                        output,
                        3,
                    )
                    self.assertEqual(
                        result["invalid_primary_record_ids"], ["candidate-1"]
                    )
                    self.assertEqual(
                        result["invalid_audit_record_ids"], ["candidate-1"]
                    )

    def test_multiline_coding_content_remains_valid(self) -> None:
        primary = _primary()
        primary.update(
            {
                "proposition": "Первая строка.\nВторая строка.",
                "quote": "Первая строка.\r\nВторая строка.",
                "quote_locator": "абзац 1\tпредложение 2",
                "reasoning_to_outcome": "Основание.\nСледствие.",
                "material_facts": ["Факт 1.\nФакт 2."],
                "alternative_grounds": [
                    {
                        "ground": "Иное основание.\nПродолжение.",
                        "independently_sufficient": False,
                        "quote": "Цитата.\nПродолжение.",
                        "quote_locator": "абзац 3\tпредложение 1",
                    }
                ],
            }
        )
        secondary = copy.deepcopy(primary)
        secondary["coder"] = "secondary-b"
        plan = build_coding_audit_plan(
            [{"candidate_id": "candidate-1"}],
            [primary],
            plan_sha256="d" * 64,
            sample_size=1,
            exclusion_sample_size=0,
        )
        audit = {
            "candidate_id": "candidate-1",
            "primary_coding_sha256": canonical_digest(primary),
            "secondary_coding": secondary,
            "secondary_coding_sha256": canonical_digest(secondary),
        }
        plan_path = self._write_json("multiline-plan.json", plan)
        primary_path = self._write_json("multiline-primary.json", [primary])
        audit_path = self._write_json("multiline-audit.json", [audit])
        for location, script in self._locations():
            with self.subTest(location=location):
                output = self.root / f"{location}-multiline-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._reliability_arguments(
                            plan=plan_path,
                            primary=primary_path,
                            audit=audit_path,
                            output=output,
                        ),
                    ),
                    output,
                    0,
                )
                self.assertIs(result["complete"], True)

    def test_missing_primary_candidate_blocks_audit_plan(self) -> None:
        screening_path = self._write_json(
            "omitted-primary-screening.json",
            [{"candidate_id": "candidate-1"}, {"candidate_id": "candidate-2"}],
        )
        primary_path = self._write_json("omitted-primary-decisions.json", [_primary()])
        for location, script in self._locations():
            with self.subTest(location=location):
                plan_path = self.root / f"{location}-omitted-primary-plan.json"
                produced = self._run(
                    script,
                    [
                        "quality",
                        "coding-audit-plan",
                        "--screening-candidates",
                        str(screening_path),
                        "--primary-decisions",
                        str(primary_path),
                        "--plan-sha256",
                        "d" * 64,
                        "--sample-size",
                        "1",
                        "--exclusion-sample-size",
                        "0",
                        "--output",
                        str(plan_path),
                    ],
                )
                self.assertEqual(produced.returncode, 0, produced.stderr)
                plan = json.loads(produced.stdout)
                self.assertEqual(plan["invalid_primary_record_ids"], ["candidate-2"])
                output = self.root / f"{location}-omitted-primary-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._reliability_arguments(
                            plan=plan_path,
                            primary=primary_path,
                            audit=self.audit,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertEqual(result["invalid_primary_record_ids"], ["candidate-2"])
                self.assertIs(result["complete"], False)

    def test_invisible_adjudication_and_prefiling_reviewer_fail_closed(self) -> None:
        adjudications = json.loads(
            self.valid_adjudication.read_text(encoding="utf-8")
        )
        adjudications[0]["resolved_fields"] = {"norm_edition_id": "\u200b"}
        adjudication_path = self._write_json(
            "invisible-adjudication.json", adjudications
        )
        for location, script in self._locations():
            with self.subTest(location=location, case="adjudication"):
                output = self.root / f"{location}-invisible-adjudication-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._reliability_arguments(
                            primary=self.primary,
                            audit=self.remedy_audit,
                            adjudications=adjudication_path,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertEqual(
                    result["invalid_adjudication_record_ids"], ["candidate-1"]
                )
            with self.subTest(location=location, case="prefiling-reviewer"):
                output = self.root / f"{location}-invisible-reviewer-result.json"
                arguments = self._refresh_arguments(
                    plan=self.refresh_current,
                    output=output,
                )
                arguments[arguments.index("--reviewer") + 1] = "\u200b"
                completed = self._run(script, arguments)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(completed.stdout, "")
                self.assertTrue(completed.stderr.startswith("Ошибка: "))
                self.assertFalse(output.exists())

    def test_schema_rejects_invisible_quality_fields(self) -> None:
        schema = json.loads(
            (REPO / "skills" / SKILL / "schemas" / "practice-quality.v1.json").read_text(
                encoding="utf-8"
            )
        )
        primary = _primary()
        secondary = copy.deepcopy(primary)
        secondary["coder"] = "secondary-b"
        secondary["quote"] = "\u200b"
        audit = {
            "candidate_id": "candidate-1",
            "primary_coding_sha256": canonical_digest(primary),
            "secondary_coding": secondary,
            "secondary_coding_sha256": canonical_digest(secondary),
        }
        self.assertTrue(
            list(
                definition_validator(schema, "coding_audit_decision").iter_errors(
                    audit
                )
            )
        )

        adjudication = json.loads(
            self.valid_adjudication.read_text(encoding="utf-8")
        )[0]
        adjudication["adjudicator"] = "\u200b"
        self.assertTrue(
            list(
                definition_validator(schema, "coding_adjudication").iter_errors(
                    adjudication
                )
            )
        )

        output = self.root / "schema-prefiling-source.json"
        valid_result = self._assert_persisted_result(
            self._run(
                REPO / "skills" / SCRIPT,
                self._refresh_arguments(
                    plan=self.refresh_current,
                    output=output,
                ),
            ),
            output,
            0,
        )
        valid_result["reviewer"] = "\u200b"
        self.assertTrue(
            list(
                definition_validator(schema, "prefiling_refresh").iter_errors(
                    valid_result
                )
            )
        )

    def test_future_check_and_human_review_times_fail_closed(self) -> None:
        future_plan = self._write_json(
            "future-refresh-plan.json",
            _refresh_plan(as_of="2099-01-01T12:00:00Z"),
        )
        future_adjudication = json.loads(
            self.valid_adjudication.read_text(encoding="utf-8")
        )
        future_adjudication[0]["reviewed_at"] = "2099-01-01T00:00:00Z"
        future_adjudication_path = self._write_json(
            "future-adjudication.json", future_adjudication
        )
        for location, script in self._locations():
            with self.subTest(location=location, case="producer"):
                produced = self._run(
                    script,
                    [
                        "cache",
                        "refresh-plan",
                        "--root",
                        str(self.root / f"{location}-future-cache"),
                        "--as-of",
                        "2099-01-01T12:00:00Z",
                        "--max-age-seconds",
                        "604800",
                        "--coverage-requirements",
                        str(self.coverage_requirements),
                    ],
                )
                self.assertEqual(produced.returncode, 2)
                self.assertEqual(produced.stdout, "")
            with self.subTest(location=location, case="prefiling"):
                output = self.root / f"{location}-future-prefiling.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._refresh_arguments(
                            plan=future_plan,
                            checked_through="2099-01-01T12:00:00Z",
                            filing_cutoff="2099-01-01T11:00:00Z",
                            reviewed_at="2099-01-01T12:10:00Z",
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertIn("timestamp_in_future", result["reasons"])
                self.assertIs(result["complete"], False)
            with self.subTest(location=location, case="adjudication"):
                output = self.root / f"{location}-future-adjudication-result.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._reliability_arguments(
                            primary=self.primary,
                            audit=self.remedy_audit,
                            adjudications=future_adjudication_path,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertTrue(result["invalid_adjudication_record_ids"])
                self.assertIs(result["complete"], False)

    def test_emitted_incomplete_artifacts_remain_schema_valid(self) -> None:
        schema = json.loads(
            (REPO / "skills" / SKILL / "schemas" / "practice-quality.v1.json").read_text(
                encoding="utf-8"
            )
        )
        reliability_validator = definition_validator(schema, "coding_reliability")
        refresh_validator = definition_validator(schema, "prefiling_refresh")
        malformed_plan = self._write_json(
            "malformed-output-audit-plan.json",
            {
                "audit_plan_sha256": 7,
                "primary_coding_sha256": 7,
                "required_candidate_ids": ["candidate-1"],
                "invalid_screening_record_ids": [],
                "invalid_primary_record_ids": [],
                "frozen": True,
            },
        )
        malformed_refresh = self._write_json(
            "malformed-output-refresh-plan.json",
            {
                "plan_id": 7,
                "as_of": 7,
                "max_age_seconds": True,
                "evidence_digest": 7,
                "entries": [],
                "coverage_gaps": [],
            },
        )
        for location, script in self._locations():
            with self.subTest(location=location, artifact="reliability"):
                output = self.root / f"{location}-schema-valid-incomplete-reliability.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._reliability_arguments(
                            plan=malformed_plan,
                            primary=self.primary,
                            audit=self.audit,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertEqual(list(reliability_validator.iter_errors(result)), [])
                self.assertIsNone(result["audit_plan_sha256"])
                self.assertIsNone(result["primary_coding_sha256"])
                self.assertRegex(result["audit_plan_input_sha256"], r"^[0-9a-f]{64}$")
            with self.subTest(location=location, artifact="refresh-plan"):
                output = self.root / f"{location}-schema-valid-incomplete-refresh.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._refresh_arguments(
                            plan=malformed_refresh,
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertEqual(list(refresh_validator.iter_errors(result)), [])
                self.assertIsNone(result["refresh_plan_as_of"])
                self.assertIsNone(result["refresh_plan_max_age_seconds"])
                self.assertIsNone(result["refresh_plan_evidence_digest"])
            with self.subTest(location=location, artifact="naive-refresh-time"):
                output = self.root / f"{location}-schema-valid-naive-refresh.json"
                result = self._assert_persisted_result(
                    self._run(
                        script,
                        self._refresh_arguments(
                            plan=self.refresh_current,
                            checked_through="2026-09-03T12:00:00",
                            filing_cutoff="2026-09-03T11:00:00",
                            reviewed_at="2026-09-03T12:10:00",
                            output=output,
                        ),
                    ),
                    output,
                    3,
                )
                self.assertEqual(list(refresh_validator.iter_errors(result)), [])

    def test_launcher_does_not_create_bytecode_in_clean_install(self) -> None:
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        before = sorted(path.relative_to(self.installed) for path in self.installed.rglob("*"))
        completed = subprocess.run(
            [PYTHON, str(self.installed / SCRIPT), "quality", "coding-reliability", "--help"],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        after = sorted(path.relative_to(self.installed) for path in self.installed.rglob("*"))
        self.assertEqual(after, before)
        self.assertFalse(any(path.name == "__pycache__" for path in self.installed.rglob("*")))

    def test_inputs_remain_byte_identical(self) -> None:
        self._assert_inputs_unchanged()


if __name__ == "__main__":
    unittest.main()
