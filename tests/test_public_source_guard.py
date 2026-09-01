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
