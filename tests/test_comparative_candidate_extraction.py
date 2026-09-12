import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/constitutional-comparative-research/scripts/extract_argument_candidates.py'
spec = importlib.util.spec_from_file_location('comparative_candidate_extraction', SCRIPT)
miner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = miner
spec.loader.exec_module(miner)


def document(**changes):
    data = {'id': 'xx-cc:synthetic', 'court': 'xx-cc', 'text': 'Синтетический пример. ' * 12 + 'Vertrauensschutz' + ' x' * 150,
            'source_role': 'decision', 'source_url': 'https://example.org/synthetic', 'raw_sha256': 'a' * 64}
    data.update(changes)
    return data


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))


def test_exact_unicode_offsets_do_not_assert_court_adoption():
    doc = document()
    row = list(miner.candidates(doc, 'b'*64))[0]
    assert row['quote_original'] == doc['text'][row['char_start']:row['char_end']]
    assert row['text_sha256'] == miner.sha(doc['text'])
    assert row['speaker'] == row['court_adoption'] == 'unverified'
    assert row['holding'] is None and row['legal_support_verified'] is False
    assert row['raw_hash_verified_by_extractor'] is False


def test_repeat_and_changed_source_preserve_versions(tmp_path):
    source = tmp_path/'input.jsonl'; output=tmp_path/'queue'
    jsonl(source,[document()])
    first=miner.run(output,jsonl=source)
    second=miner.run(output,jsonl=source)
    assert first['processed']==first['candidates_added']==1
    assert second['processed']==second['candidates_added']==0
    jsonl(source,[document(raw_sha256='c'*64)])
    third=miner.run(output,jsonl=source)
    assert third['processed']==third['candidates_added']==1
    assert miner.report(output)['processed_versions']==2


def test_budget_continues_without_skipping_unprocessed_documents(tmp_path):
    source=tmp_path/'input.jsonl';output=tmp_path/'queue'
    jsonl(source,[document(id=f'xx-cc:{i}') for i in range(3)])
    assert miner.run(output,jsonl=source,limit=2)['processed']==2
    assert miner.run(output,jsonl=source,limit=2)['processed']==1
    assert miner.report(output)['candidates']==3


def test_summary_is_rejected_but_other_documents_continue(tmp_path):
    source=tmp_path/'input.jsonl';output=tmp_path/'queue'
    jsonl(source,[document(id='summary',source_role='editorial_summary'),document()])
    result=miner.run(output,jsonl=source)
    assert result['rejected']==1 and result['processed']==1
    assert result['status']=='discovery_only'


def test_no_marker_is_not_evidence_of_absent_argument(tmp_path):
    source=tmp_path/'input.jsonl';output=tmp_path/'queue'
    jsonl(source,[document(text='A different argument without dictionary vocabulary. '*4)])
    result=miner.run(output,jsonl=source)
    assert result['processed']==1 and result['queue_total']==0
    assert result['full_corpus_semantic_review'] is False


def test_foreign_library_read_does_not_modify_source(tmp_path):
    source=tmp_path/'library.sqlite3';doc=document()
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE documents(id TEXT,court TEXT,date TEXT,number TEXT,title TEXT,text TEXT,language TEXT,data TEXT,content_hash TEXT)')
        for name in ('versions','imports','documents_fts'):db.execute(f'CREATE TABLE {name}(id TEXT)')
        db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)',(doc['id'],doc['court'],'','','',doc['text'],'de',json.dumps(doc),miner.source_version(doc)))
    before=source.read_bytes()
    result=miner.run(tmp_path/'queue',foreign_library=source)
    assert result['processed']==1
    assert source.read_bytes()==before
    assert miner.run(tmp_path/'queue',foreign_library=source)['processed']==0


def test_hudoc_path_is_rejected_before_opening(tmp_path,monkeypatch):
    source=tmp_path/'hudoc'/'library.sqlite3';source.parent.mkdir();source.write_text('must not open')
    monkeypatch.setattr(miner,'_read_only',lambda *_: pytest.fail('HUDOC must not be opened'))
    with pytest.raises(ValueError,match='HUDOC'):
        list(miner.foreign_documents(source,set(),'b'*64))


def test_bad_source_format_is_not_treated_as_empty_corpus(tmp_path):
    source=tmp_path/'library.sqlite3'
    with sqlite3.connect(source) as db:db.execute('CREATE TABLE unrelated(id TEXT)')
    with pytest.raises(ValueError,match='формату'):
        list(miner.foreign_documents(source,set(),'b'*64))


@pytest.mark.parametrize('alias', ['symlink', 'hardlink', 'same_path', 'output_root_symlink'])
def test_input_alias_is_rejected_before_any_write(tmp_path, alias):
    source = tmp_path / 'library.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE sentinel(value TEXT)')
        db.execute("INSERT INTO sentinel VALUES('untouched')")
    output = tmp_path / 'queue'
    output.mkdir()
    queue = output / 'argument-candidates.sqlite3'
    if alias == 'symlink':
        queue.symlink_to(source)
    elif alias == 'hardlink':
        os.link(source, queue)
    elif alias == 'same_path':
        source.rename(queue)
        source = queue
    else:
        linked = tmp_path / 'linked-queue'
        linked.symlink_to(output, target_is_directory=True)
        output = linked
    before = source.read_bytes()
    with pytest.raises(ValueError):
        miner.run(output, foreign_library=source)
    assert source.read_bytes() == before
    if alias == 'output_root_symlink':
        assert not queue.exists()
    with sqlite3.connect(source) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [('sentinel',)]


def test_rejection_receipt_allows_bounded_resume_and_corrected_version(tmp_path):
    source = tmp_path / 'input.jsonl'
    output = tmp_path / 'queue'
    rejected = document(id='bad', source_role='editorial_summary')
    jsonl(source, [rejected, document()])
    first = miner.run(output, jsonl=source, limit=1)
    second = miner.run(output, jsonl=source, limit=1)
    assert first['rejected'] == 1 and first['processed'] == 0
    assert second['rejected'] == 0 and second['rejected_skipped'] == 1
    assert second['processed'] == second['candidates_added'] == 1
    with sqlite3.connect(output / 'argument-candidates.sqlite3') as db:
        receipt = db.execute('SELECT document_id,source_version,status,reason FROM rejected').fetchone()
        assert receipt[:3] == ('bad', miner.source_version(rejected), 'rejected')
        assert receipt[3]
        assert db.execute('SELECT document_id FROM processed').fetchall() == [(document()['id'],)]
    jsonl(source, [document(id='bad'), document()])
    fixed = miner.run(output, jsonl=source, limit=1)
    assert fixed['processed'] == fixed['candidates_added'] == 1
    assert fixed['rejected_versions_total'] == 1
    report = miner.report(output)
    assert report['processed_versions'] == 2 and report['rejected_versions'] == 1


def test_provenance_change_retains_both_candidate_versions(tmp_path):
    source = tmp_path / 'input.jsonl'
    output = tmp_path / 'queue'
    original = document(source_provider='third_party', source_url='https://example.org/copy')
    corrected = dict(original, source_provider='official_court', source_url='https://example.org/court')
    jsonl(source, [original])
    assert miner.run(output, jsonl=source)['candidates_added'] == 1
    jsonl(source, [corrected])
    changed = miner.run(output, jsonl=source)
    assert changed['processed'] == changed['candidates_added'] == 1
    with sqlite3.connect(output / 'argument-candidates.sqlite3') as db:
        rows = [json.loads(row[0]) for row in db.execute('SELECT data FROM candidates')]
    assert len({row['candidate_id'] for row in rows}) == 2
    assert {row['source_version'] for row in rows} == {miner.source_version(original), miner.source_version(corrected)}
    assert {(row['source_provider'], row['source_url']) for row in rows} == {
        ('third_party', original['source_url']), ('official_court', corrected['source_url'])}
    assert len({row['text_sha256'] for row in rows}) == len({row['raw_sha256'] for row in rows}) == 1
    report = miner.report(output)
    assert report['candidate_versions'] == report['candidates'] == 2
    assert report['unique_passage_candidates'] == 1


def test_extractor_replay_counts_versions_separately_from_passages(tmp_path, monkeypatch):
    source = tmp_path / 'input.jsonl'
    output = tmp_path / 'queue'
    jsonl(source, [document()])
    miner.run(output, jsonl=source)
    changed_extractor = tmp_path / 'new-extractor-version.py'
    changed_extractor.write_text('# synthetic code revision for checkpoint identity')
    monkeypatch.setattr(miner, '__file__', str(changed_extractor))
    second = miner.run(output, jsonl=source)
    assert second['processed'] == second['candidates_added'] == 1
    assert second['candidate_versions'] == second['queue_total'] == 2
    assert second['unique_passage_candidates'] == 1
    jsonl(source, [document(text='Changed text version. ' + document()['text'])])
    third = miner.run(output, jsonl=source)
    assert third['candidate_versions'] == 3 and third['unique_passage_candidates'] == 2
