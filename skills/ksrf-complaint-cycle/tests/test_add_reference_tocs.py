from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_reference_tocs.py"
SPEC = importlib.util.spec_from_file_location("add_reference_tocs", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Не удалось подготовить импорт {SCRIPT}")
TOCS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOCS)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _long_reference(*, heading: str = "# Справочник") -> str:
    return (
        f"{heading}\n\n"
        "Вводный юридический текст остаётся неизменным.\n\n"
        "## Первый раздел\n\n"
        "Смысл первого раздела.\n\n"
        "## Второй раздел\n\n"
        "Смысл второго раздела.\n"
        + "\n".join(f"Строка корпуса {index}" for index in range(95))
        + "\n"
    )


class ReferenceTocAdderTests(unittest.TestCase):
    def test_dry_run_is_default_and_does_not_modify_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "ksrf-test" / "references" / "guide.md"
            original = _long_reference()
            _write(reference, original)

            report = TOCS.process_skillset(
                root,
                package_names=("ksrf-test",),
                write=False,
            )

            self.assertEqual(reference.read_text(encoding="utf-8"), original)
            self.assertEqual(report["summary"]["would_update"], 1)
            self.assertEqual(report["summary"]["updated"], 0)
            self.assertEqual(report["changes"][0]["status"], "would_update")

    def test_explicit_write_adds_h2_toc_once_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "ksrf-test" / "references" / "guide.md"
            original = _long_reference()
            _write(reference, original)

            first = TOCS.process_skillset(
                root,
                package_names=("ksrf-test",),
                write=True,
            )
            after_first = reference.read_text(encoding="utf-8")
            second = TOCS.process_skillset(
                root,
                package_names=("ksrf-test",),
                write=True,
            )

            self.assertEqual(first["summary"]["updated"], 1)
            self.assertEqual(second["summary"]["updated"], 0)
            self.assertEqual(second["summary"]["skipped_existing"], 1)
            self.assertEqual(after_first.count("## Содержание"), 1)
            self.assertIn("- [Первый раздел](#первый-раздел)", after_first)
            self.assertIn("- [Второй раздел](#второй-раздел)", after_first)
            self.assertIn(original.split("\n", 1)[1], after_first)
            self.assertEqual(reference.read_text(encoding="utf-8"), after_first)

    def test_existing_early_contents_or_index_is_never_touched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            references = root / "ksrf-test" / "references"
            contents = _long_reference().replace(
                "# Справочник\n",
                "# Справочник\n\n## Содержание\n\n- [Первый раздел](#первый-раздел)\n",
                1,
            )
            index = _long_reference().replace(
                "# Справочник\n",
                "# Справочник\n\n## Индекс\n\n- [Первый раздел](#первый-раздел)\n",
                1,
            )
            _write(references / "contents.md", contents)
            _write(references / "index.md", index)

            report = TOCS.process_skillset(
                root,
                package_names=("ksrf-test",),
                write=True,
            )

            self.assertEqual(report["summary"]["updated"], 0)
            self.assertEqual(report["summary"]["skipped_existing"], 2)
            self.assertEqual((references / "contents.md").read_text(encoding="utf-8"), contents)
            self.assertEqual((references / "index.md").read_text(encoding="utf-8"), index)

    def test_reference_at_or_below_threshold_is_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "ksrf-test" / "references" / "short.md"
            original = "\n".join(f"Строка {index}" for index in range(100))
            _write(reference, original)

            report = TOCS.process_skillset(
                root,
                package_names=("ksrf-test",),
                write=True,
            )

            self.assertEqual(reference.read_text(encoding="utf-8"), original)
            self.assertEqual(report["summary"]["skipped_short"], 1)


if __name__ == "__main__":
    unittest.main()
