from pathlib import Path
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))

from skillset_file_contract import FileContractError  # noqa: E402
from skillset_file_contract import validate_public_artifact  # noqa: E402
from skillset_file_contract import validate_public_repository  # noqa: E402


class PublicSourceGuardTests(unittest.TestCase):
    def test_current_repository_contains_no_forbidden_source_complaints(self) -> None:
        validate_public_repository(REPO)

    def test_rejects_office_document_by_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "complaint.docx"
            source.write_bytes(b"not even a valid office document")
            with self.assertRaisesRegex(FileContractError, "source documents are forbidden"):
                validate_public_artifact(source, Path("docs/complaint.docx"))

    def test_rejects_renamed_pdf_by_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "method-card.bin"
            source.write_bytes(b"%PDF-1.7\nprivate complaint")
            with self.assertRaisesRegex(FileContractError, "source documents are forbidden"):
                validate_public_artifact(source, Path("docs/method-card.bin"))

    def test_rejects_complaint_like_full_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "card.md"
            source.write_text(
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

Представитель заявителя: Петров Петр Петрович

ЖАЛОБА

ПРОШУ:

Перечень прилагаемых документов:
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileContractError, "complaint-like full text"):
                validate_public_artifact(source, Path("docs/card.md"))

    def test_repository_guard_still_scans_development_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "skills" / "example" / "tests" / "private.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileContractError, "complaint-like full text"):
                validate_public_repository(Path(temporary))

    def test_repository_guard_still_scans_development_evals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "skills" / "example" / "evals" / "private.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileContractError, "complaint-like full text"):
                validate_public_repository(Path(temporary))

    def test_repository_guard_scans_exact_maintainer_only_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = (
                Path(temporary)
                / "skills"
                / "ksrf-argument-patterns"
                / "references"
                / "evidence_maps.json"
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileContractError, "complaint-like full text"):
                validate_public_repository(Path(temporary))

    def test_repository_guard_scans_source_only_provenance_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = (
                Path(temporary)
                / "skills"
                / "ksrf-argument-patterns"
                / "references"
                / "complaint-methodology-sources.md"
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileContractError, "complaint-like full text"):
                validate_public_repository(Path(temporary))

    def test_repository_guard_scans_source_only_automation_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = (
                Path(temporary)
                / "skills"
                / "ksrf-argument-patterns"
                / "references"
                / "automation-backlog.md"
            )
            source.parent.mkdir(parents=True)
            source.write_text(
                """В Конституционный Суд Российской Федерации

Заявитель: Иванов Иван Иванович

ЖАЛОБА

ПРОШУ:
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(FileContractError, "complaint-like full text"):
                validate_public_repository(Path(temporary))

    def test_rejects_unsafe_content_in_each_root_only_release_tool(self) -> None:
        unsafe_samples = {
            "secret assignment": "api_key = 'synthetic-live-value-123456789012345'\n",
            "access token": "TOKEN = 'ghp_abcdefghijklmnopqrstuvwxyz123456'\n",
            "private key": "KEY = '-----BEGIN PRIVATE KEY-----'\n",
            "absolute path": 'SOURCE = "/Users/alice/Documents/private/input.pdf"\n',
        }
        for name in (
            "build_constitutionalist_authority_corpus.py",
            "enrich_ksrf_argument_patterns.py",
            "extract_ksrf_argument_patterns.py",
        ):
            for label, content in unsafe_samples.items():
                with self.subTest(name=name, label=label):
                    with tempfile.TemporaryDirectory() as temporary:
                        path = Path(temporary) / name
                        path.write_text(content, encoding="utf-8")
                        with self.assertRaisesRegex(
                            FileContractError,
                            "unsafe root-only release tool content",
                        ) as caught:
                            validate_public_artifact(path, Path("tools") / name)
                        self.assertNotIn("synthetic-live-value", str(caught.exception))
                        self.assertNotIn("ghp_", str(caught.exception))

    def test_repository_guard_rejects_benign_root_only_skill_duplicate(self) -> None:
        for name in (
            "build_constitutionalist_authority_corpus.py",
            "enrich_ksrf_argument_patterns.py",
            "extract_ksrf_argument_patterns.py",
        ):
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temporary:
                    duplicate = (
                        Path(temporary)
                        / "skills"
                        / "ksrf-argument-patterns"
                        / "scripts"
                        / name
                    )
                    duplicate.parent.mkdir(parents=True)
                    duplicate.write_text("# benign duplicate\n", encoding="utf-8")
                    with self.assertRaisesRegex(
                        FileContractError,
                        "root-only tool duplicate is forbidden",
                    ):
                        validate_public_repository(Path(temporary))

    def test_allows_non_reconstructive_method_card(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            card = Path(temporary) / "card.md"
            card.write_text(
                "# Методическая карточка\n\n"
                "Проверяется связь нормы, судебного смысла и конституционного вреда.\n",
                encoding="utf-8",
            )
            validate_public_artifact(card, Path("docs/card.md"))

    def test_only_exact_synthetic_binary_fixture_is_allowed(self) -> None:
        fixture = (
            REPO
            / "skills"
            / "ksrf-cassation-judicial-meaning"
            / "tests"
            / "fixtures"
            / "image_only.pdf"
        )
        logical_path = Path(
            "skills/ksrf-cassation-judicial-meaning/tests/fixtures/image_only.pdf"
        )
        validate_public_artifact(fixture, logical_path)
        with self.assertRaisesRegex(FileContractError, "source documents are forbidden"):
            validate_public_artifact(fixture, Path("docs/image_only.pdf"))


if __name__ == "__main__":
    unittest.main()
