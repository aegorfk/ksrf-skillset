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

    def test_real_sudrf_empty_layout_requires_shell_exact_date_and_dated_marker(self):
        html = (FIXTURES / "listing_empty_sudrf.html").read_text(encoding="utf-8")
        result = parse_listing(html, BASE, "2024-03-07")
        self.assertEqual("success_empty", classify_listing(200, result))
        self.assertTrue(result.listing_shell_seen)
        self.assertTrue(result.date_confirmed)
        self.assertEqual("dated_no_scheduled_cases", result.empty_evidence_code)

        wrong_date = parse_listing(html, BASE, "2024-03-08")
        self.assertNotEqual("success_empty", classify_listing(200, wrong_date))
        self.assertFalse(wrong_date.date_confirmed)

    def test_empty_marker_without_shell_and_shell_without_marker_remain_unresolved(self):
        marker_only = parse_listing(
            "<main id='content'>На 07.03.2024 дел не назначено</main>",
            BASE,
            "2024-03-07",
        )
        self.assertNotEqual("success_empty", classify_listing(200, marker_only))

        shell_only = parse_listing(
            "<form id='calformH'><input name='name' value='sud_delo'>"
            "<input name='srv_num' value='1'><input name='H_date' value='07.03.2024'></form>",
            BASE,
            "2024-03-07",
        )
        self.assertEqual("invalid_structure", classify_listing(200, shell_only))

    def test_protection_wins_over_empty_marker_and_service_row_is_not_a_case(self):
        protected = parse_listing(
            (FIXTURES / "listing_empty_sudrf.html").read_text(encoding="utf-8")
            + "<div>Проверка, что вы не робот</div>",
            BASE,
            "2024-03-07",
        )
        self.assertEqual("blocked", classify_listing(200, protected))

        service_row = parse_listing(
            "<form id='calformH'><input name='name' value='sud_delo'>"
            "<input name='srv_num' value='1'><input name='H_date' value='07.03.2024'></form>"
            "<table id='tablcont'><tr><td>Служебная строка без дела</td></tr></table>",
            BASE,
            "2024-03-07",
        )
        self.assertNotEqual("success_nonempty", classify_listing(200, service_row))

    def test_conflicting_date_table_only_empty_and_paginated_empty_fail_closed(self):
        mismatched_date = parse_listing(
            "<form id='calformH'><input name='name' value='sud_delo'>"
            "<input name='srv_num' value='1'><input name='H_date' value='08.03.2024'></form>"
            "<main id='content'>Информация по делам на 07.03.2024"
            "<table id='tablcont'><tr><td><a href='/modules.php?name=sud_delo&amp;srv_num=1&amp;name_op=case&amp;case_id=1'>Дело</a></td></tr></table></main>",
            BASE,
            "2024-03-07",
        )
        self.assertFalse(mismatched_date.structural_ok)
        self.assertNotEqual("success_nonempty", classify_listing(200, mismatched_date))

        table_only = parse_listing(
            "<main id='content'>На 07.03.2024 дел не найдено"
            "<table id='tablcont'><tr><td>Пусто</td></tr></table></main>",
            BASE,
            "2024-03-07",
        )
        self.assertNotEqual("success_empty", classify_listing(200, table_only))

        paginated_empty = parse_listing(
            (FIXTURES / "listing_empty_sudrf.html").read_text(encoding="utf-8")
            + "<a rel='next' href='/modules.php?name=sud_delo&amp;srv_num=1&amp;H_date=07.03.2024&amp;page=2'>Следующая</a>",
            BASE,
            "2024-03-07",
        )
        self.assertEqual(1, len(paginated_empty.pagination_urls))
        self.assertNotEqual("success_empty", classify_listing(200, paginated_empty))

    def test_listing_ignores_external_case_and_document_links(self):
        external = parse_listing(
            "<form id='calformH'><input name='name' value='sud_delo'>"
            "<input name='srv_num' value='1'><input name='H_date' value='07.03.2024'></form>"
            "<main id='content'>Информация по делам на 07.03.2024"
            "<table id='tablcont'><tr><td>"
            "<a href='https://example.invalid/modules.php?name=sud_delo&amp;name_op=case'>Чужое дело</a>"
            "<a href='https://example.invalid/modules.php?name=sud_delo&amp;name_op=doc'>Чужой акт</a>"
            "</td></tr></table></main>",
            BASE,
            "2024-03-07",
        )
        self.assertEqual([], external.case_urls)
        self.assertEqual([], external.doc_urls)
        self.assertNotEqual("success_nonempty", classify_listing(200, external))
        external_card = parse_source_page(
            "<a href='https://example.invalid/modules.php?name=sud_delo&amp;name_op=doc'>Чужой акт</a>",
            BASE,
            "card",
        )
        self.assertEqual([], external_card.doc_urls)

    def test_card_discovers_docs_and_doc_extracts_content(self):
        card = parse_source_page((FIXTURES / "card.html").read_text(), BASE, "card")
        self.assertEqual(2, len(card.doc_urls))
        doc = parse_source_page((FIXTURES / "doc.html").read_text(), BASE, "doc")
        self.assertEqual("full_text", doc.status)
        self.assertIn("кассационный суд установил", doc.text.lower())
        self.assertNotIn("Главное меню", doc.text)


if __name__ == "__main__":
    unittest.main()
