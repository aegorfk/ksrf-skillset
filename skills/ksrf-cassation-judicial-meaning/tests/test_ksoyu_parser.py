import unittest
from pathlib import Path

from judicial_meaning.ksoyu import (
    build_listing_url,
    classify_listing,
    decode_response,
    parse_listing,
    parse_source_page,
)


FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://1kas.sudrf.ru/modules.php?name=sud_delo&srv_num=1&H_date=07.03.2024"


class KsoyuParserTests(unittest.TestCase):
    def test_build_listing_url_uses_official_endpoint(self):
        self.assertEqual(BASE, build_listing_url("1kas.sudrf.ru", "2024-03-07"))

    def test_cp1251_decode_and_case_doc_extraction(self):
        html = (FIXTURES / "listing_nonempty.html").read_text(encoding="utf-8")
        page = decode_response(html.encode("cp1251"), {"content-type": "text/html; charset=windows-1251"})
        self.assertEqual("cp1251", page.encoding)
        result = parse_listing(page.text, BASE, "2024-03-07")
        self.assertTrue(result.structural_ok)
        self.assertEqual(1, len(result.rows))
        self.assertEqual(1, len(result.case_urls))
        self.assertEqual(1, len(result.doc_urls))
        self.assertIn("case_uid=UID-001", result.case_urls[0])

    def test_synthetic_pagination_is_followed_but_never_invented(self):
        html = (FIXTURES / "listing_pagination.html").read_text(encoding="utf-8")
        result = parse_listing(html, BASE, "2024-03-07")
        self.assertEqual(1, len(result.pagination_urls))
        self.assertIn("page=2", result.pagination_urls[0])
        no_navigation = parse_listing(
            (FIXTURES / "listing_nonempty.html").read_text(encoding="utf-8"), BASE, "2024-03-07"
        )
        self.assertEqual("no_navigation_observed", no_navigation.navigation_state)
        self.assertEqual([], no_navigation.pagination_urls)

    def test_empty_and_blocked_are_distinct(self):
        empty = parse_listing((FIXTURES / "listing_empty.html").read_text(), BASE, "2024-03-07")
        blocked = parse_listing((FIXTURES / "protective.html").read_text(), BASE, "2024-03-07")
        self.assertEqual("success_empty", classify_listing(200, empty))
        self.assertEqual("blocked", classify_listing(200, blocked))
        self.assertEqual("blocked", classify_listing(403, empty))
        self.assertEqual("retryable_error", classify_listing(503, empty))

    def test_card_discovers_docs_and_doc_extracts_content(self):
        card = parse_source_page((FIXTURES / "card.html").read_text(), BASE, "card")
        self.assertEqual(2, len(card.doc_urls))
        doc = parse_source_page((FIXTURES / "doc.html").read_text(), BASE, "doc")
        self.assertEqual("full_text", doc.status)
        self.assertIn("кассационный суд установил", doc.text.lower())
        self.assertNotIn("Главное меню", doc.text)


if __name__ == "__main__":
    unittest.main()
