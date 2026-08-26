from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from judicial_meaning.ksoyu import (
    build_result_date_search_url,
    classify_result_search,
    parse_result_search,
)


class KsoyuResultSearchTests(unittest.TestCase):
    def test_builds_official_result_date_query(self) -> None:
        url = build_result_date_search_url("2kas.sudrf.ru", "2025-10-16")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(urlparse(url).netloc, "2kas.sudrf.ru")
        self.assertEqual(query["name_op"], ["r"])
        self.assertEqual(query["srv_num"], ["1"])
        self.assertEqual(query["delo_id"], ["2800001"])
        self.assertEqual(query["new"], ["2800001"])
        self.assertEqual(query["case_type"], ["0"])
        self.assertEqual(query["delo_table"], ["g33_case"])
        self.assertEqual(query["g33_case__RESULT_DATE1D"], ["16.10.2025"])
        self.assertEqual(query["g33_case__RESULT_DATE2D"], ["16.10.2025"])
        self.assertEqual(query["list"], ["ON"])

    def test_builder_is_bounded_to_second_ksoyu_civil_route(self) -> None:
        for unsupported_host in ("1kas.sudrf.ru", "example.org"):
            with self.subTest(host=unsupported_host):
                with self.assertRaisesRegex(ValueError, "2kas"):
                    build_result_date_search_url(unsupported_host, "2025-10-16")

    def test_parses_same_origin_cases_documents_and_observed_pagination(self) -> None:
        url = build_result_date_search_url("2kas.sudrf.ru", "2025-10-16")
        html = """
        <main><h1>Результат поиска</h1>
          <table><tr><td>
            <a href="/modules.php?name=sud_delo&amp;srv_num=1&amp;name_op=case&amp;case_id=1&amp;case_uid=u1&amp;delo_id=2800001">8Г-1/2025</a>
            <a href="/modules.php?name=sud_delo&amp;srv_num=1&amp;name_op=doc&amp;number=9&amp;delo_id=2800001">Акт</a>
            <a href="https://evil.example/modules.php?name=sud_delo&amp;name_op=case&amp;case_id=2">чужая ссылка</a>
          </td></tr></table>
          <div>Страницы: <b>1</b> | <a title="Следующая страница" href="/modules.php?name=sud_delo&amp;srv_num=1&amp;name_op=r&amp;page=2&amp;g33_case__RESULT_DATE1D=16.10.2025&amp;g33_case__RESULT_DATE2D=16.10.2025">2</a></div>
        </main>
        """
        parsed = parse_result_search(html, url, "2025-10-16")
        self.assertEqual(len(parsed.case_urls), 1)
        self.assertEqual(len(parsed.doc_urls), 1)
        self.assertEqual(len(parsed.pagination_urls), 1)
        self.assertEqual(
            parsed.pagination_urls[0],
            build_result_date_search_url("2kas.sudrf.ru", "2025-10-16", page=2),
        )
        self.assertTrue(parsed.query_date_confirmed)
        self.assertEqual(classify_result_search(200, parsed), "success_nonempty")

    def test_empty_requires_exact_query_explicit_marker_and_no_pagination(self) -> None:
        url = build_result_date_search_url("2kas.sudrf.ru", "2026-08-01")
        html = "<main><h1>Результат поиска</h1><div id='error'>Данных по запросу не обнаружено. Уточните критерии поиска.</div></main>"
        parsed = parse_result_search(html, url, "2026-08-01")
        self.assertTrue(parsed.explicit_empty)
        self.assertEqual(parsed.empty_evidence_code, "result_date_search_zero_results")
        self.assertEqual(classify_result_search(200, parsed), "success_empty")

        paginated = parse_result_search(
            html + '<a title="Следующая страница" href="?name=sud_delo&amp;name_op=r&amp;page=2">2</a>',
            url,
            "2026-08-01",
        )
        self.assertFalse(paginated.explicit_empty)
        self.assertNotEqual(classify_result_search(200, paginated), "success_empty")

    def test_wrong_query_date_or_protection_fails_closed(self) -> None:
        wrong_url = build_result_date_search_url("2kas.sudrf.ru", "2026-08-02")
        html = "<main><h1>Результат поиска</h1><div id='error'>Данных по запросу не обнаружено.</div></main>"
        wrong = parse_result_search(html, wrong_url, "2026-08-01")
        self.assertFalse(wrong.query_date_confirmed)
        self.assertEqual(classify_result_search(200, wrong), "invalid_structure")

        blocked = parse_result_search(html + "<p>Проверка, что вы не робот</p>", wrong_url, "2026-08-02")
        self.assertEqual(classify_result_search(200, blocked), "blocked")

    def test_tampered_route_parameters_cannot_confirm_the_bounded_query(self) -> None:
        url = build_result_date_search_url("2kas.sudrf.ru", "2025-10-16")
        html = "<main><h1>Результат поиска</h1><div>Данных по запросу не обнаружено.</div></main>"
        foreign = parse_result_search(
            html=html,
            base_url=url.replace("//2kas.sudrf.ru/", "//1kas.sudrf.ru/"),
            result_date="2025-10-16",
        )
        self.assertFalse(foreign.query_date_confirmed)
        self.assertEqual(classify_result_search(200, foreign), "invalid_structure")

        for field, replacement in (
            ("srv_num", "2"),
            ("delo_id", "123"),
            ("new", "123"),
            ("case_type", "1"),
            ("delo_table", "u33_case"),
            ("list", "OFF"),
        ):
            with self.subTest(field=field):
                parsed_url = urlparse(url)
                query = parse_qs(parsed_url.query)
                query[field] = [replacement]
                tampered = urlunparse(parsed_url._replace(query=urlencode(query, doseq=True)))
                result = parse_result_search(html, tampered, "2025-10-16")
                self.assertFalse(result.query_date_confirmed)
                self.assertFalse(result.explicit_empty)
                self.assertEqual(classify_result_search(200, result), "invalid_structure")

    def test_same_origin_case_outside_civil_scope_is_a_fail_closed_conflict(self) -> None:
        url = build_result_date_search_url("2kas.sudrf.ru", "2025-10-16")
        html = """
        <main><h1>Результат поиска</h1>
          <div>Данных по запросу не обнаружено.</div>
          <a href="/modules.php?name=sud_delo&amp;srv_num=1&amp;name_op=case&amp;case_id=3&amp;delo_id=1540005">другая категория</a>
        </main>
        """
        result = parse_result_search(html, url, "2025-10-16")
        self.assertTrue(result.scope_conflict)
        self.assertFalse(result.explicit_empty)
        self.assertEqual(classify_result_search(200, result), "invalid_structure")


if __name__ == "__main__":
    unittest.main()
