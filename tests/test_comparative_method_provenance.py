"""Publication integrity checks; these do not grade legal reasoning or live law."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/constitutional-comparative-research"


def test_published_quote_bindings_are_consistent_and_source_specific():
    ledger = json.loads((PACKAGE / "references/source-provenance.json").read_text())
    cards = ledger["cards"]
    assert len({c["card_id"] for c in cards}) == len(cards)
    assert len({c["doc_id"] for c in cards}) == len(cards)
    methods = (PACKAGE / "references/act-derived-methods.md").read_text()
    for card in cards:
        assert re.fullmatch(r"[a-f0-9]{64}", card["raw_sha256"])
        assert re.fullmatch(r"[a-f0-9]{64}", card["text_sha256"])
        assert urlsplit(card["source_url"]).scheme == "https"
        assert card["source_record_id"]
        assert card["source_voice"]["role_basis"]
        assert card["authority_status"] == "comparative_method_only"
        assert card["russian_bridge_status"] == "research_question_only_not_verified_domestic_authority"
        anchor_id = "method-" + card["card_id"].rsplit("-", 1)[1]
        assert f'id="{anchor_id}"' in methods
        for anchor in card["anchors"]:
            quote = anchor["quote_original"]
            assert anchor["end_char"] - anchor["start_char"] == len(quote)
            assert anchor["start_char"] >= 0
            assert hashlib.sha256(quote.encode()).hexdigest() == anchor["quote_sha256"]
            assert anchor["official_locator"] and anchor["role"]
            assert " ".join(quote.split()) in " ".join(methods.split())
        assert card["verification"]["original_quoted_words"] == sum(
            len(a["quote_original"].split()) for a in card["anchors"]
        )


def test_official_crosscheck_does_not_relabel_third_party_primary_copy():
    cards = json.loads((PACKAGE / "references/source-provenance.json").read_text())["cards"]
    card = next(c for c in cards if c["doc_id"] == "in-sc:2025_1_1009_1040")
    crosscheck = card["official_cross_check"]
    assert card["source_provider"] == "dattam_labs_open_data"
    assert "amazonaws.com" in urlsplit(card["source_url"]).netloc
    assert urlsplit(crosscheck["url"]).netloc == "api.sci.gov.in"
    assert crosscheck["raw_sha256"] != card["raw_sha256"]
    assert crosscheck["quote_matches"] is True
    assert crosscheck["scope"]
    assert all(1 <= page <= crosscheck["pdf_pages"] for page in crosscheck["quote_pages"])
    assert card["verification"]["live_limit_ru"]


def test_development_prompts_are_self_contained_and_not_run_claims():
    data = json.loads((PACKAGE / "evals/evals.json").read_text())
    cases = data["evals"]
    assert len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        assert case["prompt"] and case["expectations"]
        assert not case["files"]  # No private records or nonexistent source fixtures.
        assert "actual_output" not in case
        assert "passed" not in case
    assert "not proof of execution" in data["evaluation_scope"]
