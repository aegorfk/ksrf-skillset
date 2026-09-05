import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/ksrf-argument-patterns"
SPEC = importlib.util.spec_from_file_location("portable_argument", SKILL / "scripts/check_argument.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture():
    text = "Учебный акт. Отказ вызван только закрытием формы приёма. Иных оснований суд не установил."
    return {
        "mode": "prospective", "as_of": "2026-09-05",
        "documents": [{"id": "d1", "role": "hypothetical_facts", "available_on": "2026-09-05", "text": text}],
        "claims": [{"id": "c1", "kind": "observation", "text": "В учебном акте указано единственное основание отказа.",
                    "evidence": [{"document_id": "d1", "start": 0, "end": len(text), "quote": text, "speaker": "synthetic"}]}],
        "issues": [{"id": "i1", "method_ids": ["U01", "U07"], "norm": "Описанное правило подачи",
                    "judicial_meaning": "Отказ при закрытой форме", "situation": "Своевременное обращение объективно невозможно",
                    "harm": "Утрата возможности рассмотрения", "constitutional_bridge": "Условная гарантия доступной процедуры",
                    "narrow_question": "Достаточен ли механизм подачи при объективно закрытой форме?",
                    "support_ids": ["c1"], "adverse_ids": [], "counterargument": "Существование равноценного доступного способа подачи",
                    "decisive_fact": "Наличие своевременно доступной альтернативы", "if_reversed": "При доступной альтернативе довод о невозможности ослабевает",
                    "independent_grounds": [], "remedy_limit": "Проверить восстановление доступа, не присудить благо автоматически", "unknowns": []}]
    }


class UniversalArgumentTests(unittest.TestCase):
    def test_traceability_is_not_truth_or_filing(self):
        result = MODULE.check(fixture())
        self.assertEqual(result["status"], "structurally_traceable_candidate")
        self.assertFalse(result["filing_ready"])
        self.assertFalse(result["semantic_truth_verified"])
        self.assertFalse(result["historical_eval_allowed"])
        self.assertFalse(result["claim_checks"]["c1"]["attribution_verified"])
        self.assertEqual(len(result["source_sha256"]["d1"]), 64)

    def test_every_method_has_two_directions_and_discriminator(self):
        library = json.loads((SKILL / "references/universal-methods.json").read_text())
        ids = [row["id"] for row in library["methods"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(library["closed_typology"])
        self.assertFalse(library["requires_source_corpus"])
        for method in library["methods"]:
            with self.subTest(method=method["id"]):
                for field in ("trigger", "operation", "plus", "minus", "decisive_question", "limit", "question_form"):
                    self.assertTrue(method[field].strip())
                self.assertNotEqual(method["plus"], method["minus"])
                self.assertGreaterEqual(len(method["evidence"]), 2)
                packet = fixture()
                packet["issues"][0]["method_ids"] = [method["id"]]
                self.assertEqual(MODULE.check(packet)["status"], "structurally_traceable_candidate")

    def test_all_required_issue_links_missing_remain_gaps(self):
        for field in MODULE.ISSUE_TEXT:
            with self.subTest(field=field):
                packet = fixture(); packet["issues"][0].pop(field)
                self.assertEqual(MODULE.check(packet)["status"], "needs_evidence")

    def test_unknowns_are_not_false_or_verified(self):
        packet = fixture(); packet["issues"][0]["unknowns"] = ["Неизвестно, работал ли альтернативный способ"]
        self.assertEqual(MODULE.check(packet)["status"], "needs_evidence")
        packet = fixture(); packet["documents"][0]["available_on"] = None
        self.assertEqual(MODULE.check(packet)["status"], "needs_evidence")
        packet = fixture(); packet["claims"][0]["evidence"] = []
        self.assertEqual(MODULE.check(packet)["status"], "needs_evidence")

    def test_outcome_future_and_historical_are_blocked(self):
        changes = [lambda p: p.update(mode="historical"),
                   lambda p: p.update(as_of="2026-09-04"),
                   lambda p: p["documents"][0].update(role="target_outcome"),
                   lambda p: p["documents"][0].update(known_outcome=True),
                   lambda p: p["documents"][0].update(available_on="2027-01-01")]
        for change in changes:
            packet = fixture(); change(packet)
            self.assertEqual(MODULE.check(packet)["status"], "blocked")

    def test_wrong_quotes_bounds_ids_and_roles_do_not_pass(self):
        mutations = [lambda p: p["claims"][0]["evidence"][0].update(quote="Другой текст"),
                     lambda p: p["claims"][0]["evidence"][0].update(start=True),
                     lambda p: p["claims"][0]["evidence"][0].update(end=999999),
                     lambda p: p["claims"][0]["evidence"][0].update(speaker="unknown"),
                     lambda p: p["claims"][0]["evidence"][0].update(document_id="missing"),
                     lambda p: p["issues"][0].update(support_ids=["missing"]),
                     lambda p: p["issues"][0].update(method_ids=["typo"]),
                     lambda p: p["documents"].append(copy.deepcopy(p["documents"][0])),
                     lambda p: p["claims"].append(copy.deepcopy(p["claims"][0])),
                     lambda p: p["documents"][0].update(known_outcome="false")]
        for mutation in mutations:
            packet = fixture(); mutation(packet)
            self.assertEqual(MODULE.check(packet)["status"], "invalid")

    def test_own_method_without_library_match_is_allowed(self):
        packet = fixture(); issue = packet["issues"][0]
        issue["method_ids"] = []; issue["custom_method"] = "Проверка новой причинной связи с явно названным опровержением"
        self.assertEqual(MODULE.check(packet)["status"], "structurally_traceable_candidate")

    def test_party_or_case_quote_does_not_become_legal_anchor(self):
        packet = fixture(); packet["claims"][0]["kind"] = "legal_anchor"
        self.assertEqual(MODULE.check(packet)["status"], "needs_evidence")

    def test_bad_input_has_no_successful_readiness(self):
        for value in (None, [], {}, {"mode": "prospective"}, dict(fixture(), as_of="20260905")):
            result = MODULE.check(value)
            self.assertIn(result["status"], ("invalid", "blocked"))
            self.assertFalse(result["filing_ready"])

    def test_portable_core_runs_without_repository_corpus_or_network(self):
        with tempfile.TemporaryDirectory(prefix="ksrf-universal-unit-") as temp:
            root = Path(temp)
            for rel in ("scripts/check_argument.py", "references/universal-methods.json"):
                destination = root / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SKILL / rel, destination)
            packet = root / "input.json"; packet.write_text(json.dumps(fixture(), ensure_ascii=False))
            # Python isolation plus a deny hook: no network/child process and
            # no file outside the copied core and the interpreter's stdlib.
            wrapper = '''
import sys, pathlib, runpy, socket, subprocess, argparse, hashlib, json, re, datetime
root = pathlib.Path.cwd().resolve()
stdlib = pathlib.Path(json.__file__).resolve().parent.parent
def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.")) or event in ("os.system", "os.exec", "os.spawn"):
        raise PermissionError("forbidden external operation")
    if event == "open" and not isinstance(args[0], int):
        path = pathlib.Path(args[0]).resolve()
        if not path.is_relative_to(root) and not path.is_relative_to(stdlib):
            raise PermissionError("outside portable core")
sys.addaudithook(guard)
try:
    socket.socket()
    raise AssertionError("network guard inactive")
except PermissionError:
    pass
sys.argv = [str(root / "scripts/check_argument.py"), str(root / "input.json")]
runpy.run_path(sys.argv[0], run_name="__main__")
'''
            run = subprocess.run([sys.executable, "-I", "-B", "-c", wrapper],
                                 cwd=root, text=True, capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            result = json.loads(run.stdout)
            self.assertEqual(result["status"], "structurally_traceable_candidate")
            self.assertFalse(result["requires_source_corpus"])


if __name__ == "__main__":
    unittest.main()
