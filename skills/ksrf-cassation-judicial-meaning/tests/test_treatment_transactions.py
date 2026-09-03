import io
import json
import sqlite3
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import judicial_meaning.public_corpus as public_corpus_module
from judicial_meaning.cli import build_parser, main
from judicial_meaning.public_corpus import (
    PublicCorpus,
    PublicCorpusError,
    TreatmentReviewError,
    _identifier,
)


OFFICIAL_URL = (
    "https://2kas.sudrf.ru/modules.php?name=sud_delo&name_op=doc&number=txn"
)


class _TimeoutRestoreFailingConnection:
    def __init__(self, connection, *, restored_timeout):
        self._connection = connection
        self._restore_statement = f"PRAGMA BUSY_TIMEOUT={restored_timeout}"
        self.closed = False

    @property
    def in_transaction(self):
        return self._connection.in_transaction

    def execute(self, statement, *args, **kwargs):
        normalized = " ".join(statement.upper().split())
        if normalized == self._restore_statement:
            raise sqlite3.OperationalError("injected timeout restoration failure")
        return self._connection.execute(statement, *args, **kwargs)

    def close(self):
        if not self.closed:
            self.closed = True
            self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


class _RollbackFailingConnection:
    def __init__(self, connection):
        self._connection = connection
        self.closed = False

    @property
    def in_transaction(self):
        return self._connection.in_transaction

    def execute(self, statement, *args, **kwargs):
        if " ".join(statement.upper().split()) == "ROLLBACK":
            raise sqlite3.OperationalError("injected rollback failure")
        return self._connection.execute(statement, *args, **kwargs)

    def close(self):
        if not self.closed:
            self.closed = True
            self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


class _CommitSucceededThenRaisedConnection:
    def __init__(self, connection):
        self._connection = connection
        self.closed = False

    @property
    def in_transaction(self):
        return self._connection.in_transaction

    def execute(self, statement, *args, **kwargs):
        if " ".join(statement.upper().split()) == "COMMIT":
            self._connection.execute(statement, *args, **kwargs)
            raise sqlite3.OperationalError("injected post-commit failure")
        return self._connection.execute(statement, *args, **kwargs)

    def close(self):
        if not self.closed:
            self.closed = True
            self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


class _TimeoutSetAppliedThenRaisedConnection:
    def __init__(self, connection):
        self._connection = connection
        self.injected = False

    @property
    def in_transaction(self):
        return self._connection.in_transaction

    def execute(self, statement, *args, **kwargs):
        normalized = " ".join(statement.upper().split())
        if normalized == "PRAGMA BUSY_TIMEOUT=0" and not self.injected:
            self.injected = True
            self._connection.execute(statement, *args, **kwargs)
            raise sqlite3.OperationalError("injected post-timeout-set failure")
        return self._connection.execute(statement, *args, **kwargs)

    def close(self):
        self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


class _TimeoutRestoreAndCloseFailingConnection(_TimeoutRestoreFailingConnection):
    def __init__(self, connection, *, restored_timeout):
        super().__init__(connection, restored_timeout=restored_timeout)
        self.close_attempted = False

    def close(self):
        self.close_attempted = True
        raise sqlite3.OperationalError("injected close failure")

    def force_close(self):
        self._connection.close()


class TreatmentTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.corpus = PublicCorpus(self.root)

    def tearDown(self):
        self.corpus.close()
        self.tmp.cleanup()

    @property
    def database_path(self):
        return self.root / "public-corpus.sqlite3"

    def _busy_error_type(self):
        error_type = getattr(public_corpus_module, "PublicCorpusBusyError", None)
        self.assertIsNotNone(
            error_type,
            "PublicCorpusBusyError must be part of the public-corpus API",
        )
        return error_type

    def _busy_classifier(self):
        classifier = getattr(
            public_corpus_module,
            "_is_sqlite_busy_or_locked",
            None,
        )
        self.assertTrue(
            callable(classifier),
            "_is_sqlite_busy_or_locked must classify SQLite contention narrowly",
        )
        return classifier

    def _raw_connection(self, *, timeout=0.0):
        connection = sqlite3.connect(self.database_path, timeout=timeout)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _indexed_snapshot(self, *, chain_id="chain-transaction", text=None):
        if text is None:
            text = "Суд проверил применение правовой позиции."
        seed = self.corpus.register_seed(
            url=OFFICIAL_URL,
            role="official_user_seed",
            public=True,
        )
        snapshot = self.corpus.store_snapshot(
            seed_id=seed["seed_id"],
            raw=text.encode("utf-8"),
            content_type="text/html; charset=utf-8",
            fetched_at="2026-08-01T00:00:00Z",
            parser_manifest={
                "adapter_id": "ksoyu_daily_v2",
                "parser_version": "2.0",
            },
        )
        self.corpus.index_text(
            snapshot["snapshot_id"],
            text,
            document_id=f"document-{chain_id}",
            chain_candidate_id=chain_id,
            query_lane="higher_authority",
        )
        return snapshot

    def _proposal_kwargs(
        self,
        snapshot_id,
        *,
        chain_id="chain-transaction",
        target_authority_id="ksrf-32-p-2023",
        treatment_type="applies",
        supersedes_treatment_id=None,
    ):
        return {
            "source_chain_id": chain_id,
            "source_court_id": "2kas",
            "target_authority_id": target_authority_id,
            "target_kind": "constitutional_court_act",
            "target_identity": {"act_number": "32-П"},
            "treatment_type": treatment_type,
            "snapshot_id": snapshot_id,
            "supersedes_treatment_id": supersedes_treatment_id,
        }

    def _candidate(self, **overrides):
        chain_id = overrides.pop("chain_id", "chain-transaction")
        snapshot = overrides.pop("snapshot", None)
        if snapshot is None:
            snapshot = self._indexed_snapshot(chain_id=chain_id)
        proposal = self._proposal_kwargs(
            snapshot["snapshot_id"],
            chain_id=chain_id,
            **overrides,
        )
        return snapshot, proposal, self.corpus.propose_treatment(**proposal)

    def _review_kwargs(
        self,
        *,
        reviewer="И.И. Иванов",
        reviewed_at=None,
        target_authority_id="ksrf-32-p-2023",
    ):
        result = {
            "decision": "verified",
            "reviewer": reviewer,
            "quote": "Суд проверил применение правовой позиции",
            "locator": "абз. 1",
            "speaker": "court",
            "confirmed_target_authority_id": target_authority_id,
            "target_identity_confirmed": True,
        }
        if reviewed_at is not None:
            result["reviewed_at"] = reviewed_at
        return result

    def _status(self, treatment_id):
        row = self.corpus.conn.execute(
            "SELECT status FROM treatments WHERE treatment_id=?",
            (treatment_id,),
        ).fetchone()
        return None if row is None else str(row["status"])

    def _count(self, table, *, treatment_id=None):
        if treatment_id is None:
            return int(
                self.corpus.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            )
        return int(
            self.corpus.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE treatment_id=?",
                (treatment_id,),
            ).fetchone()[0]
        )

    def _trace_index(self, statements, predicate, description):
        matches = [
            index
            for index, statement in enumerate(statements)
            if predicate(statement)
        ]
        self.assertTrue(matches, f"trace did not contain {description}: {statements}")
        return matches[0]

    def test_busy_classifier_accepts_only_busy_and_locked_base_codes(self):
        classifier = self._busy_classifier()

        for base_code in (5, 6):
            with self.subTest(base_code=base_code):
                error = sqlite3.OperationalError("unrelated wording")
                error.sqlite_errorcode = base_code | (73 << 8)
                self.assertTrue(classifier(error))

        coded_io_error = sqlite3.OperationalError("database is locked")
        coded_io_error.sqlite_errorcode = 10 | (73 << 8)
        self.assertFalse(classifier(coded_io_error))
        self.assertFalse(classifier(sqlite3.IntegrityError("database is locked")))
        self.assertFalse(classifier(sqlite3.OperationalError("disk I/O error")))

    def test_busy_classifier_has_narrow_legacy_message_fallback(self):
        classifier = self._busy_classifier()

        self.assertTrue(classifier(sqlite3.OperationalError("database is locked")))
        self.assertTrue(
            classifier(sqlite3.OperationalError("database table is locked"))
        )
        self.assertFalse(
            classifier(
                sqlite3.OperationalError(
                    "validation failed because upstream said database is locked yesterday"
                )
            )
        )
        self.assertFalse(
            classifier(sqlite3.OperationalError("attempt to write a readonly database"))
        )

    def test_treatment_write_help_explains_busy_exit_and_no_automatic_retry(self):
        for command in ("discover", "review"):
            with self.subTest(command=command):
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as stopped:
                    build_parser().parse_args(
                        ["cache", "treatment", command, "--help"]
                    )
                self.assertEqual(0, stopped.exception.code)
                help_text = output.getvalue().lower()
                self.assertIn("занят", help_text)
                self.assertRegex(help_text, r"код(?:ом)? 2")
                self.assertIn("автоматического повтора нет", help_text)

    def test_cli_treatment_contention_is_code_two_stderr_only(self):
        snapshot, _, candidate = self._candidate()
        target_identity = self.root / "target-identity.json"
        target_identity.write_text(
            json.dumps({"act_number": "32-П"}, ensure_ascii=False),
            encoding="utf-8",
        )

        class BorrowedCorpus:
            def __enter__(borrowed_self):
                return self.corpus

            def __exit__(borrowed_self, exc_type, exc, traceback):
                return False

        commands = (
            [
                "cache",
                "treatment",
                "discover",
                "--root",
                str(self.root),
                "--source-chain-id",
                "chain-transaction",
                "--source-court-id",
                "2kas",
                "--target-authority-id",
                "ksrf-cli-busy",
                "--target-kind",
                "constitutional_court_act",
                "--target-identity",
                str(target_identity),
                "--treatment-type",
                "applies",
                "--snapshot-id",
                snapshot["snapshot_id"],
            ],
            [
                "cache",
                "treatment",
                "review",
                "--root",
                str(self.root),
                "--treatment-id",
                candidate["treatment_id"],
                "--decision",
                "verified",
                "--reviewer",
                "И.И. Иванов",
                "--quote",
                "Суд проверил применение правовой позиции",
                "--locator",
                "абз. 1",
                "--speaker",
                "court",
                "--confirmed-target-authority-id",
                "ksrf-32-p-2023",
                "--target-identity-confirmed",
            ],
        )
        for command in commands:
            with self.subTest(command=command[2]):
                locker = self._raw_connection(timeout=0.0)
                locker.execute("BEGIN IMMEDIATE")
                stdout = io.StringIO()
                stderr = io.StringIO()
                try:
                    with patch(
                        "judicial_meaning.cli.PublicCorpus",
                        return_value=BorrowedCorpus(),
                    ), redirect_stdout(stdout), redirect_stderr(stderr):
                        exit_code = main(command)
                finally:
                    locker.rollback()
                    locker.close()
                self.assertEqual(2, exit_code)
                self.assertEqual("", stdout.getvalue())
                self.assertIn("публичный кэш занят", stderr.getvalue().lower())
                self.assertIn("автоматического повтора нет", stderr.getvalue().lower())

        self.assertEqual(1, self._count("treatments"))
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        self.assertEqual(
            1,
            self._count(
                "treatment_review_history",
                treatment_id=candidate["treatment_id"],
            ),
        )

    def test_proposal_reserves_before_provenance_and_returns_before_commit(self):
        snapshot = self._indexed_snapshot()
        statements = []
        self.corpus.conn.set_trace_callback(
            lambda statement: statements.append(" ".join(statement.upper().split()))
        )
        try:
            self.corpus.propose_treatment(
                **self._proposal_kwargs(snapshot["snapshot_id"])
            )
        finally:
            self.corpus.conn.set_trace_callback(None)

        begin_index = self._trace_index(
            statements,
            lambda statement: statement.startswith("BEGIN IMMEDIATE"),
            "BEGIN IMMEDIATE",
        )
        provenance_indices = [
            index
            for index, statement in enumerate(statements)
            if statement.startswith("SELECT")
            and any(
                table in statement
                for table in (
                    " FROM SNAPSHOTS",
                    " FROM TREATMENTS",
                    " FROM TREATMENT_REVIEW_HISTORY",
                    " FROM INDEXED_TEXTS",
                    " FROM OBSERVATIONS",
                    " FROM SEEDS",
                )
            )
        ]
        self.assertTrue(provenance_indices, statements)
        self.assertGreater(min(provenance_indices), begin_index, statements)
        commit_index = self._trace_index(
            statements,
            lambda statement: statement == "COMMIT",
            "COMMIT",
        )
        self.assertFalse(
            any(statement.startswith("SELECT") for statement in statements[commit_index + 1 :]),
            statements,
        )

    def test_review_reserves_before_first_database_provenance_read(self):
        _, _, candidate = self._candidate()
        statements = []
        self.corpus.conn.set_trace_callback(
            lambda statement: statements.append(" ".join(statement.upper().split()))
        )
        try:
            self.corpus.review_treatment(
                candidate["treatment_id"],
                **self._review_kwargs(),
            )
        finally:
            self.corpus.conn.set_trace_callback(None)

        begin_index = self._trace_index(
            statements,
            lambda statement: statement.startswith("BEGIN IMMEDIATE"),
            "BEGIN IMMEDIATE",
        )
        first_provenance = self._trace_index(
            statements,
            lambda statement: statement.startswith("SELECT")
            and any(
                table in statement
                for table in (
                    " FROM TREATMENTS",
                    " FROM TREATMENT_REVIEW_HISTORY",
                    " FROM SNAPSHOTS",
                    " FROM INDEXED_TEXTS",
                    " FROM OBSERVATIONS",
                    " FROM SEEDS",
                )
            ),
            "review provenance SELECT",
        )
        self.assertGreater(first_provenance, begin_index, statements)

    def test_source_chain_mutation_cannot_interleave_during_review(self):
        _, _, candidate = self._candidate()
        attacker = self._raw_connection(timeout=0.0)
        original_integrity = self.corpus._indexed_text_integrity
        attack = {"committed": False, "error": None}

        def integrity_with_attack(snapshot_id):
            result = original_integrity(snapshot_id)
            try:
                attacker.execute(
                    "UPDATE treatments SET source_chain_id='chain-poison' "
                    "WHERE treatment_id=?",
                    (candidate["treatment_id"],),
                )
                attacker.commit()
                attack["committed"] = True
            except sqlite3.OperationalError as exc:
                attacker.rollback()
                attack["error"] = exc
            return result

        try:
            with patch.object(
                self.corpus,
                "_indexed_text_integrity",
                side_effect=integrity_with_attack,
            ):
                reviewed = self.corpus.review_treatment(
                    candidate["treatment_id"],
                    **self._review_kwargs(),
                )
        finally:
            attacker.close()

        self.assertEqual("verified", reviewed["status"])
        self.assertFalse(attack["committed"], attack)
        self.assertIsNotNone(attack["error"], attack)
        self.assertTrue(self._busy_classifier()(attack["error"]))
        row = self.corpus.conn.execute(
            "SELECT source_chain_id, status FROM treatments WHERE treatment_id=?",
            (candidate["treatment_id"],),
        ).fetchone()
        self.assertEqual("chain-transaction", row["source_chain_id"])
        self.assertEqual("verified", row["status"])

    def test_predecessor_mutation_cannot_be_validated_then_bypassed(self):
        snapshot, proposal, predecessor = self._candidate()
        self.corpus.review_treatment(
            predecessor["treatment_id"],
            **self._review_kwargs(),
        )
        replacement_kwargs = self._proposal_kwargs(
            snapshot["snapshot_id"],
            chain_id=proposal["source_chain_id"],
            treatment_type="limits",
            supersedes_treatment_id=predecessor["treatment_id"],
        )
        attacker = self._raw_connection(timeout=0.0)
        original_check = self.corpus._require_replacement_context
        attack = {"attempted": False, "committed": False, "error": None}

        def check_then_attack(**kwargs):
            result = original_check(**kwargs)
            attack["attempted"] = True
            try:
                attacker.execute(
                    "UPDATE treatments SET status='candidate' WHERE treatment_id=?",
                    (predecessor["treatment_id"],),
                )
                attacker.commit()
                attack["committed"] = True
            except sqlite3.OperationalError as exc:
                attacker.rollback()
                attack["error"] = exc
            return result

        try:
            with patch.object(
                self.corpus,
                "_require_replacement_context",
                side_effect=check_then_attack,
            ):
                replacement = self.corpus.propose_treatment(**replacement_kwargs)
        finally:
            attacker.close()

        self.assertTrue(attack["attempted"])
        self.assertFalse(attack["committed"])
        self.assertIsNotNone(attack["error"])
        self.assertTrue(self._busy_classifier()(attack["error"]))
        self.assertEqual("candidate", replacement["status"])
        self.assertEqual("verified", self._status(predecessor["treatment_id"]))
        successors = self.corpus.conn.execute(
            "SELECT treatment_id FROM treatments WHERE supersedes_treatment_id=?",
            (predecessor["treatment_id"],),
        ).fetchall()
        self.assertEqual(
            [replacement["treatment_id"]],
            [row["treatment_id"] for row in successors],
        )

    def test_two_connection_review_loser_is_busy_then_retry_is_immutable(self):
        _, _, candidate = self._candidate()
        loser = PublicCorpus(self.root)
        original_integrity = self.corpus._indexed_text_integrity
        loser_attempt = {"called": False, "result": None, "error": None}
        loser_review = self._review_kwargs(reviewer="П.П. Петров")

        def integrity_with_losing_review(snapshot_id):
            result = original_integrity(snapshot_id)
            if not loser_attempt["called"]:
                loser_attempt["called"] = True
                try:
                    loser_attempt["result"] = loser.review_treatment(
                        candidate["treatment_id"],
                        **loser_review,
                    )
                except BaseException as exc:
                    loser_attempt["error"] = exc
            return result

        try:
            with patch.object(
                self.corpus,
                "_indexed_text_integrity",
                side_effect=integrity_with_losing_review,
            ):
                winner = self.corpus.review_treatment(
                    candidate["treatment_id"],
                    **self._review_kwargs(reviewer="И.И. Иванов"),
                )

            self.assertEqual("verified", winner["status"])
            self.assertTrue(loser_attempt["called"])
            self.assertIsNone(loser_attempt["result"])
            self.assertIsInstance(
                loser_attempt["error"],
                self._busy_error_type(),
            )
            with self.assertRaises(TreatmentReviewError) as immutable:
                loser.review_treatment(
                    candidate["treatment_id"],
                    **loser_review,
                )
            self.assertIn("immutable", str(immutable.exception).lower())
        finally:
            loser.close()

        history = self.corpus.treatment_history(candidate["treatment_id"])
        self.assertEqual(2, len(history))
        self.assertEqual(
            ["candidate_created", "verified"],
            [item["event_type"] for item in history],
        )
        self.assertEqual("И.И. Иванов", history[1]["reviewer"])

    def test_two_connection_successor_loser_is_busy_then_retry_conflicts(self):
        snapshot, proposal, predecessor = self._candidate()
        self.corpus.review_treatment(
            predecessor["treatment_id"],
            **self._review_kwargs(),
        )
        winner_proposal = self._proposal_kwargs(
            snapshot["snapshot_id"],
            chain_id=proposal["source_chain_id"],
            treatment_type="limits",
            supersedes_treatment_id=predecessor["treatment_id"],
        )
        loser_proposal = self._proposal_kwargs(
            snapshot["snapshot_id"],
            chain_id=proposal["source_chain_id"],
            treatment_type="distinguishes",
            supersedes_treatment_id=predecessor["treatment_id"],
        )
        loser = PublicCorpus(self.root)
        loser_attempt = {"called": False, "result": None, "error": None}
        statements = []

        def race_on_first_provenance_read(statement):
            normalized = " ".join(statement.upper().split())
            statements.append(normalized)
            if (
                not loser_attempt["called"]
                and normalized.startswith("SELECT")
                and any(
                    table in normalized
                    for table in (
                        " FROM SNAPSHOTS",
                        " FROM TREATMENTS",
                        " FROM TREATMENT_REVIEW_HISTORY",
                    )
                )
            ):
                loser_attempt["called"] = True
                try:
                    loser_attempt["result"] = loser.propose_treatment(
                        **loser_proposal
                    )
                except BaseException as exc:
                    loser_attempt["error"] = exc

        try:
            self.corpus.conn.set_trace_callback(race_on_first_provenance_read)
            try:
                winner = self.corpus.propose_treatment(**winner_proposal)
            finally:
                self.corpus.conn.set_trace_callback(None)

            self.assertEqual("candidate", winner["status"])
            self.assertTrue(loser_attempt["called"], statements)
            self.assertIsNone(loser_attempt["result"])
            self.assertIsInstance(
                loser_attempt["error"],
                self._busy_error_type(),
            )
            with self.assertRaises(TreatmentReviewError) as conflict:
                loser.propose_treatment(**loser_proposal)
            self.assertIn("replacement", str(conflict.exception).lower())
        finally:
            loser.close()

        successors = self.corpus.conn.execute(
            """
            SELECT treatment_id FROM treatments
            WHERE supersedes_treatment_id=? ORDER BY treatment_id
            """,
            (predecessor["treatment_id"],),
        ).fetchall()
        self.assertEqual([winner["treatment_id"]], [row[0] for row in successors])
        winner_history = self.corpus.treatment_history(winner["treatment_id"])
        self.assertEqual(1, len(winner_history))
        self.assertEqual("candidate_created", winner_history[0]["event_type"])

    def test_held_writer_is_typed_no_wait_one_attempt_and_timeout_is_restored(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        self.corpus.conn.execute("PRAGMA busy_timeout=1800")
        locker = self._raw_connection(timeout=0.0)
        locker.execute("BEGIN IMMEDIATE")
        statements = []
        self.corpus.conn.set_trace_callback(
            lambda statement: statements.append(" ".join(statement.upper().split()))
        )

        started = time.monotonic()
        try:
            with self.assertRaises(self._busy_error_type()):
                self.corpus.propose_treatment(**proposal)
        finally:
            elapsed = time.monotonic() - started
            self.corpus.conn.set_trace_callback(None)
            locker.rollback()
            locker.close()

        self.assertLess(elapsed, 0.75)
        begin_attempts = [
            statement
            for statement in statements
            if statement.startswith("BEGIN IMMEDIATE")
        ]
        self.assertEqual(1, len(begin_attempts), statements)
        restored_timeout = self.corpus.conn.execute(
            "PRAGMA busy_timeout"
        ).fetchone()[0]
        self.assertEqual(1800, restored_timeout)
        self.assertEqual(0, self._count("treatments"))
        self.assertEqual(0, self._count("treatment_review_history"))

        replayed = self.corpus.propose_treatment(**proposal)
        self.assertEqual("candidate", replayed["status"])
        restored_after_retry = self.corpus.conn.execute(
            "PRAGMA busy_timeout"
        ).fetchone()[0]
        self.assertEqual(1800, restored_after_retry)

    def test_timeout_restore_failure_after_commit_closes_with_committed_diagnostic(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        restored_timeout = 1717
        self.corpus.conn.execute(f"PRAGMA busy_timeout={restored_timeout}")
        wrapped = _TimeoutRestoreFailingConnection(
            self.corpus.conn,
            restored_timeout=restored_timeout,
        )
        self.corpus.conn = wrapped

        with self.assertRaisesRegex(PublicCorpusError, "зафиксирована") as raised:
            self.corpus.propose_treatment(**proposal)

        self.assertNotIsInstance(raised.exception, self._busy_error_type())
        self.assertTrue(wrapped.closed)
        observer = self._raw_connection()
        try:
            treatment = observer.execute(
                "SELECT status FROM treatments"
            ).fetchone()
            history = observer.execute(
                "SELECT event_type FROM treatment_review_history"
            ).fetchone()
        finally:
            observer.close()
        self.assertEqual("candidate", treatment["status"])
        self.assertEqual("candidate_created", history["event_type"])

    def test_timeout_restore_failure_after_busy_closes_with_no_commit_diagnostic(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        restored_timeout = 1919
        self.corpus.conn.execute(f"PRAGMA busy_timeout={restored_timeout}")
        wrapped = _TimeoutRestoreFailingConnection(
            self.corpus.conn,
            restored_timeout=restored_timeout,
        )
        self.corpus.conn = wrapped
        locker = self._raw_connection()
        locker.execute("BEGIN IMMEDIATE")

        try:
            with self.assertRaisesRegex(
                PublicCorpusError,
                "не зафиксирована",
            ) as raised:
                self.corpus.propose_treatment(**proposal)
        finally:
            locker.rollback()
            locker.close()

        self.assertNotIsInstance(raised.exception, self._busy_error_type())
        self.assertTrue(wrapped.closed)
        observer = self._raw_connection()
        try:
            self.assertEqual(
                0,
                observer.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
            )
            self.assertEqual(
                0,
                observer.execute(
                    "SELECT COUNT(*) FROM treatment_review_history"
                ).fetchone()[0],
            )
        finally:
            observer.close()

    def test_timeout_set_applied_then_raised_is_restored_and_reusable(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        restored_timeout = 2121
        self.corpus.conn.execute(f"PRAGMA busy_timeout={restored_timeout}")
        wrapped = _TimeoutSetAppliedThenRaisedConnection(self.corpus.conn)
        self.corpus.conn = wrapped

        with self.assertRaisesRegex(
            sqlite3.OperationalError,
            "post-timeout-set",
        ):
            self.corpus.propose_treatment(**proposal)

        self.assertEqual(
            restored_timeout,
            self.corpus.conn.execute("PRAGMA busy_timeout").fetchone()[0],
        )
        self.assertEqual(0, self._count("treatments"))
        created = self.corpus.propose_treatment(**proposal)
        self.assertEqual("candidate", created["status"])

    def test_commit_succeeded_then_raised_is_uncertain_and_quarantined(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        wrapped = _CommitSucceededThenRaisedConnection(self.corpus.conn)
        self.corpus.conn = wrapped

        with self.assertRaisesRegex(
            PublicCorpusError,
            "(?s)Не удалось подтвердить.*зафиксирована",
        ) as raised:
            self.corpus.propose_treatment(**proposal)

        self.assertNotIsInstance(raised.exception, self._busy_error_type())
        self.assertTrue(wrapped.closed)
        with self.assertRaises(PublicCorpusError):
            self.corpus.conn.execute("SELECT 1")
        observer = self._raw_connection()
        try:
            self.assertEqual(
                1,
                observer.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
            )
            self.assertEqual(
                1,
                observer.execute(
                    "SELECT COUNT(*) FROM treatment_review_history"
                ).fetchone()[0],
            )
        finally:
            observer.close()

    def test_close_failure_is_reported_and_corpus_stays_quarantined(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        restored_timeout = 2323
        self.corpus.conn.execute(f"PRAGMA busy_timeout={restored_timeout}")
        wrapped = _TimeoutRestoreAndCloseFailingConnection(
            self.corpus.conn,
            restored_timeout=restored_timeout,
        )
        self.corpus.conn = wrapped

        try:
            with self.assertRaisesRegex(
                PublicCorpusError,
                "(?s)зафиксирована.*Закрытие.*не подтверждено",
            ):
                self.corpus.propose_treatment(**proposal)
            self.assertTrue(wrapped.close_attempted)
            with self.assertRaises(PublicCorpusError):
                self.corpus.conn.execute("SELECT 1")
            observer = self._raw_connection()
            try:
                self.assertEqual(
                    1,
                    observer.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
                )
                self.assertEqual(
                    1,
                    observer.execute(
                        "SELECT COUNT(*) FROM treatment_review_history"
                    ).fetchone()[0],
                )
            finally:
                observer.close()
        finally:
            wrapped.force_close()

    def test_delete_mode_commit_contention_is_typed_and_rolls_back(self):
        snapshot = self._indexed_snapshot()
        proposal = self._proposal_kwargs(snapshot["snapshot_id"])
        mode = self.corpus.conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        self.assertEqual("delete", str(mode).lower())
        self.corpus.conn.execute("PRAGMA busy_timeout=1337")
        reader = self._raw_connection(timeout=0.0)
        reader.execute("PRAGMA journal_mode=DELETE")
        reader_started = {"value": False}

        def hold_read_snapshot():
            reader.execute("BEGIN")
            reader.execute("SELECT COUNT(*) FROM treatments").fetchone()
            reader_started["value"] = True
            return 1

        self.corpus.conn.create_function(
            "test_hold_treatment_reader",
            0,
            hold_read_snapshot,
        )
        self.corpus.conn.execute(
            """
            CREATE TRIGGER test_hold_reader_after_candidate_history
            AFTER INSERT ON treatment_review_history
            WHEN NEW.event_type='candidate_created'
            BEGIN
                SELECT test_hold_treatment_reader();
            END
            """
        )
        self.corpus.conn.commit()
        statements = []
        self.corpus.conn.set_trace_callback(
            lambda statement: statements.append(" ".join(statement.upper().split()))
        )

        try:
            with self.assertRaises(self._busy_error_type()):
                self.corpus.propose_treatment(**proposal)
        finally:
            self.corpus.conn.set_trace_callback(None)
            reader.rollback()
            reader.close()

        self.assertTrue(reader_started["value"])
        self.assertFalse(self.corpus.conn.in_transaction)
        self.assertEqual(
            1337,
            self.corpus.conn.execute("PRAGMA busy_timeout").fetchone()[0],
        )
        self.assertEqual(0, self._count("treatments"))
        self.assertEqual(0, self._count("treatment_review_history"))
        self.assertEqual(1, statements.count("COMMIT"), statements)

    def test_exact_ordinary_and_replacement_proposals_are_idempotent(self):
        snapshot, proposal, candidate = self._candidate()
        original_history = self.corpus.treatment_history(candidate["treatment_id"])

        replayed_candidate = self.corpus.propose_treatment(**proposal)
        self.assertEqual(candidate, replayed_candidate)
        self.assertEqual(
            original_history,
            self.corpus.treatment_history(candidate["treatment_id"]),
        )

        self.corpus.review_treatment(
            candidate["treatment_id"],
            **self._review_kwargs(),
        )
        reviewed_history = self.corpus.treatment_history(candidate["treatment_id"])
        replayed_reviewed = self.corpus.propose_treatment(**proposal)
        self.assertEqual("verified", replayed_reviewed["status"])
        self.assertEqual(
            reviewed_history,
            self.corpus.treatment_history(candidate["treatment_id"]),
        )

        replacement_proposal = self._proposal_kwargs(
            snapshot["snapshot_id"],
            chain_id=proposal["source_chain_id"],
            treatment_type="limits",
            supersedes_treatment_id=candidate["treatment_id"],
        )
        replacement = self.corpus.propose_treatment(**replacement_proposal)
        replacement_history = self.corpus.treatment_history(
            replacement["treatment_id"]
        )
        replayed_replacement = self.corpus.propose_treatment(**replacement_proposal)
        self.assertEqual(replacement, replayed_replacement)
        self.assertEqual(
            replacement_history,
            self.corpus.treatment_history(replacement["treatment_id"]),
        )

    def test_json_compatible_python_identity_is_canonicalized_before_replay(self):
        snapshot = self._indexed_snapshot(chain_id="chain-json-identity")
        proposal = self._proposal_kwargs(
            snapshot["snapshot_id"],
            chain_id="chain-json-identity",
        )
        proposal["target_identity"] = {
            "aliases": ("32-П", "32-P"),
            "legacy": {7: "legacy-key"},
        }

        created = self.corpus.propose_treatment(**proposal)
        expected_identity = {
            "aliases": ["32-П", "32-P"],
            "legacy": {"7": "legacy-key"},
        }
        stored_identity = self.corpus.conn.execute(
            "SELECT target_identity_json FROM treatments WHERE treatment_id=?",
            (created["treatment_id"],),
        ).fetchone()[0]
        self.assertEqual(expected_identity, json.loads(stored_identity))

        replay = dict(proposal)
        replay["target_identity"] = expected_identity
        self.assertEqual(created, self.corpus.propose_treatment(**replay))
        self.assertEqual(
            ["candidate_created"],
            [
                item["event_type"]
                for item in self.corpus.treatment_history(created["treatment_id"])
            ],
        )

    def test_exact_replay_rejects_same_id_with_changed_immutable_columns(self):
        _, proposal, candidate = self._candidate()
        with self.corpus.conn:
            self.corpus.conn.execute(
                "UPDATE treatments SET target_identity_json=? WHERE treatment_id=?",
                ('{"act_number":"FORGED"}', candidate["treatment_id"]),
            )

        with self.assertRaises(TreatmentReviewError):
            self.corpus.propose_treatment(**proposal)
        self.assertEqual(1, self._count("treatments"))
        self.assertEqual(1, self._count("treatment_review_history"))

    def test_exact_replay_rejects_sqlite_type_changed_immutable_text(self):
        cases = (
            ("source_court_id", "None", None),
            ("target_kind", "b'x'", sqlite3.Binary(b"x")),
        )
        for field, original_value, changed_value in cases:
            with self.subTest(field=field):
                chain_id = f"chain-type-{field}"
                snapshot = self._indexed_snapshot(
                    chain_id=chain_id,
                    text=f"Суд проверил тип поля {field}.",
                )
                proposal = self._proposal_kwargs(
                    snapshot["snapshot_id"],
                    chain_id=chain_id,
                )
                proposal[field] = original_value
                candidate = self.corpus.propose_treatment(**proposal)
                with self.corpus.conn:
                    self.corpus.conn.execute(
                        f"UPDATE treatments SET {field}=? WHERE treatment_id=?",
                        (changed_value, candidate["treatment_id"]),
                    )

                with self.assertRaises(TreatmentReviewError):
                    self.corpus.propose_treatment(**proposal)
                self.assertEqual("candidate", self._status(candidate["treatment_id"]))

    def test_exact_replay_rejects_missing_candidate_history(self):
        _, proposal, candidate = self._candidate()
        with self.corpus.conn:
            self.corpus.conn.execute(
                "DELETE FROM treatment_review_history WHERE treatment_id=?",
                (candidate["treatment_id"],),
            )

        with self.assertRaises(TreatmentReviewError):
            self.corpus.propose_treatment(**proposal)
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        self.assertEqual(0, self._count("treatment_review_history"))

    def test_review_rejects_missing_candidate_history_before_update(self):
        _, _, candidate = self._candidate()
        with self.corpus.conn:
            self.corpus.conn.execute(
                "DELETE FROM treatment_review_history WHERE treatment_id=?",
                (candidate["treatment_id"],),
            )

        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                **self._review_kwargs(),
            )
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        self.assertEqual(0, self._count("treatment_review_history"))

    def test_review_rejects_extra_candidate_history_before_update(self):
        _, _, candidate = self._candidate()
        with self.corpus.conn:
            self.corpus.conn.execute(
                """
                INSERT INTO treatment_review_history(
                    history_id, treatment_id, event_type, reviewer, payload_json, event_at
                ) VALUES (?, ?, 'forged', 'Attacker', '{}', '2026-08-02T00:00:00Z')
                """,
                ("history-extra", candidate["treatment_id"]),
            )

        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                **self._review_kwargs(),
            )
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        self.assertEqual(2, self._count("treatment_review_history"))

    def test_review_rejects_forged_candidate_history_before_update(self):
        _, _, candidate = self._candidate()
        with self.corpus.conn:
            self.corpus.conn.execute(
                """
                UPDATE treatment_review_history
                SET reviewer='Attacker', payload_json='{}'
                WHERE treatment_id=? AND event_type='candidate_created'
                """,
                (candidate["treatment_id"],),
            )

        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                **self._review_kwargs(),
            )
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        self.assertEqual(1, self._count("treatment_review_history"))

    def test_review_history_collision_rolls_back_candidate_update(self):
        snapshot, _, candidate = self._candidate()
        decoy_proposal = self._proposal_kwargs(
            snapshot["snapshot_id"],
            target_authority_id="ksrf-decoy",
        )
        decoy = self.corpus.propose_treatment(**decoy_proposal)
        row = self.corpus.conn.execute(
            "SELECT created_at FROM treatments WHERE treatment_id=?",
            (candidate["treatment_id"],),
        ).fetchone()
        reviewed_at = str(row["created_at"])
        review_kwargs = self._review_kwargs(reviewed_at=reviewed_at)
        expected_payload = {
            "quote": review_kwargs["quote"],
            "locator": review_kwargs["locator"],
            "speaker": review_kwargs["speaker"],
            "confirmed_target_authority_id": review_kwargs[
                "confirmed_target_authority_id"
            ],
            "target_identity_confirmed": True,
            "decision_reason": None,
        }
        colliding_history_id = _identifier(
            "treatment-history",
            {
                "treatment_id": candidate["treatment_id"],
                "event_type": "verified",
                "reviewer": review_kwargs["reviewer"],
                "payload": expected_payload,
                "event_at": reviewed_at,
            },
        )
        with self.corpus.conn:
            self.corpus.conn.execute(
                """
                INSERT INTO treatment_review_history(
                    history_id, treatment_id, event_type, reviewer, payload_json, event_at
                ) VALUES (?, ?, 'forged', 'Attacker', '{}', ?)
                """,
                (colliding_history_id, decoy["treatment_id"], reviewed_at),
            )

        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                **review_kwargs,
            )
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        self.assertEqual(
            1,
            self._count(
                "treatment_review_history",
                treatment_id=candidate["treatment_id"],
            ),
        )
        forged = self.corpus.conn.execute(
            "SELECT treatment_id, event_type FROM treatment_review_history WHERE history_id=?",
            (colliding_history_id,),
        ).fetchone()
        self.assertEqual(decoy["treatment_id"], forged["treatment_id"])
        self.assertEqual("forged", forged["event_type"])

    def test_proposal_history_rowcount_failure_rolls_back_treatment(self):
        snapshot = self._indexed_snapshot()
        self.corpus.conn.execute(
            """
            CREATE TRIGGER test_ignore_candidate_history
            BEFORE INSERT ON treatment_review_history
            WHEN NEW.event_type='candidate_created'
            BEGIN
                SELECT RAISE(IGNORE);
            END
            """
        )
        self.corpus.conn.commit()

        with self.assertRaises(TreatmentReviewError):
            self.corpus.propose_treatment(
                **self._proposal_kwargs(snapshot["snapshot_id"])
            )
        self.assertFalse(self.corpus.conn.in_transaction)
        self.assertEqual(0, self._count("treatments"))
        self.assertEqual(0, self._count("treatment_review_history"))

    def test_rollback_failure_quarantines_and_close_rolls_back_partial_state(self):
        snapshot = self._indexed_snapshot()
        self.corpus.conn.execute(
            """
            CREATE TRIGGER test_abort_candidate_history_before_failed_rollback
            BEFORE INSERT ON treatment_review_history
            WHEN NEW.event_type='candidate_created'
            BEGIN
                SELECT RAISE(ABORT, 'blocked candidate history');
            END
            """
        )
        self.corpus.conn.commit()
        wrapped = _RollbackFailingConnection(self.corpus.conn)
        self.corpus.conn = wrapped

        with self.assertRaisesRegex(
            PublicCorpusError,
            "(?s)подтвердить откат.*Вручную проверьте",
        ) as raised:
            self.corpus.propose_treatment(
                **self._proposal_kwargs(snapshot["snapshot_id"])
            )

        self.assertNotIsInstance(raised.exception, self._busy_error_type())
        self.assertTrue(wrapped.closed)
        with self.assertRaises(PublicCorpusError):
            self.corpus.conn.execute("SELECT 1")
        observer = self._raw_connection()
        try:
            self.assertEqual(
                0,
                observer.execute("SELECT COUNT(*) FROM treatments").fetchone()[0],
            )
            self.assertEqual(
                0,
                observer.execute(
                    "SELECT COUNT(*) FROM treatment_review_history"
                ).fetchone()[0],
            )
        finally:
            observer.close()

    def test_review_history_trigger_failure_rolls_back_status(self):
        _, _, candidate = self._candidate()
        self.corpus.conn.execute(
            """
            CREATE TRIGGER test_abort_verified_history
            BEFORE INSERT ON treatment_review_history
            WHEN NEW.event_type='verified'
            BEGIN
                SELECT RAISE(ABORT, 'blocked review history');
            END
            """
        )
        self.corpus.conn.commit()

        with self.assertRaises(TreatmentReviewError):
            self.corpus.review_treatment(
                candidate["treatment_id"],
                **self._review_kwargs(),
            )
        self.assertFalse(self.corpus.conn.in_transaction)
        self.assertEqual("candidate", self._status(candidate["treatment_id"]))
        history = self.corpus.treatment_history(candidate["treatment_id"])
        self.assertEqual(["candidate_created"], [item["event_type"] for item in history])

    def test_proposal_refuses_caller_owned_transaction_without_ending_it(self):
        snapshot = self._indexed_snapshot()
        seed = self.corpus.conn.execute(
            "SELECT seed_id, created_at FROM seeds LIMIT 1"
        ).fetchone()
        original_created_at = str(seed["created_at"])
        self.corpus.conn.execute("BEGIN")
        self.corpus.conn.execute(
            "UPDATE seeds SET created_at='caller-owned' WHERE seed_id=?",
            (seed["seed_id"],),
        )
        try:
            with self.assertRaisesRegex(
                PublicCorpusError,
                "(?i:caller|ownership|transaction)",
            ):
                self.corpus.propose_treatment(
                    **self._proposal_kwargs(snapshot["snapshot_id"])
                )
            self.assertTrue(self.corpus.conn.in_transaction)
            self.assertEqual(
                "caller-owned",
                self.corpus.conn.execute(
                    "SELECT created_at FROM seeds WHERE seed_id=?",
                    (seed["seed_id"],),
                ).fetchone()[0],
            )
            self.assertEqual(0, self._count("treatments"))
        finally:
            self.corpus.conn.rollback()
        restored = self.corpus.conn.execute(
            "SELECT created_at FROM seeds WHERE seed_id=?",
            (seed["seed_id"],),
        ).fetchone()[0]
        self.assertEqual(original_created_at, restored)

    def test_review_refuses_caller_owned_transaction_without_ending_it(self):
        _, _, candidate = self._candidate()
        seed = self.corpus.conn.execute(
            "SELECT seed_id, created_at FROM seeds LIMIT 1"
        ).fetchone()
        original_created_at = str(seed["created_at"])
        self.corpus.conn.execute("BEGIN")
        self.corpus.conn.execute(
            "UPDATE seeds SET created_at='caller-owned' WHERE seed_id=?",
            (seed["seed_id"],),
        )
        try:
            with self.assertRaisesRegex(
                PublicCorpusError,
                "(?i:caller|ownership|transaction)",
            ):
                self.corpus.review_treatment(
                    candidate["treatment_id"],
                    **self._review_kwargs(),
                )
            self.assertTrue(self.corpus.conn.in_transaction)
            self.assertEqual(
                "caller-owned",
                self.corpus.conn.execute(
                    "SELECT created_at FROM seeds WHERE seed_id=?",
                    (seed["seed_id"],),
                ).fetchone()[0],
            )
            self.assertEqual("candidate", self._status(candidate["treatment_id"]))
            self.assertEqual(
                1,
                self._count(
                    "treatment_review_history",
                    treatment_id=candidate["treatment_id"],
                ),
            )
        finally:
            self.corpus.conn.rollback()
        restored = self.corpus.conn.execute(
            "SELECT created_at FROM seeds WHERE seed_id=?",
            (seed["seed_id"],),
        ).fetchone()[0]
        self.assertEqual(original_created_at, restored)


if __name__ == "__main__":
    unittest.main()
