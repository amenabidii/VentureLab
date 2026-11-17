"""Real committed history is inspectable without restoring execution authority."""
import hashlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import recordings


@pytest.fixture
def api():
    app = FastAPI()
    app.include_router(recordings.router)
    return TestClient(app)


def test_all_committed_recordings_are_readable_and_read_only(api):
    rows = api.get('/api/recordings').json()
    assert len(rows) >= 9
    for row in rows:
        response = api.get('/api/recordings/' + row['id'])
        assert response.status_code == 200
        data = response.json()
        assert data['run']['readOnly']
        assert data['approvals'] == []
        assert data['decision']['builderAllowed'] is False
        entry = recordings._index()[row['id']]
        gate = json.loads((recordings.ROOT / entry['outputs']['gate']).read_text(encoding='utf-8'))
        assert data['decision']['outcome'] == gate['decision']
        assert data['decision']['trace'] == gate.get('checks', [])
        assert data['decision']['thresholds'] == gate.get('thresholds', {})
        assert data['audit'] == entry['audit']
        assert api.post('/api/recordings/' + row['id'], json={}).status_code == 405


def test_historical_go_does_not_become_current_permission(api):
    records = [api.get('/api/recordings/' + key).json() for key in recordings._index()]
    old_go = [x for x in records if x['decision']['outcome'] == 'GO']
    assert old_go
    for data in old_go:
        assert 'superseded' in data['run']['status']
        assert data['decision']['builderAllowed'] is False
        assert 'superseded' in data['decision']['action']


def test_tampered_or_missing_file_fails_closed(api, monkeypatch, tmp_path):
    key, original = next(iter(recordings._index().items()))
    entry = json.loads(json.dumps(original))
    monkeypatch.setattr(recordings, 'ROOT', tmp_path)
    monkeypatch.setattr(recordings, '_index', lambda: {key: entry})
    assert api.get('/api/recordings/' + key).status_code == 409
    for name in entry['files']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'changed')
    assert api.get('/api/recordings/' + key).status_code == 409
    assert api.get('/api/recordings').json()[0]['status'] == 'Unavailable'


@pytest.mark.parametrize('path', ['../secrets', 'outputs/../../secrets', 'C:/secrets', 'outputs\\secret'])
def test_paths_cannot_escape_archive(path):
    with pytest.raises(ValueError):
        recordings._bytes(path, hashlib.sha256(b'').hexdigest())


def test_bad_index_is_explicit_error(api, monkeypatch, tmp_path):
    path = tmp_path / 'index.json'
    path.write_text('{broken')
    monkeypatch.setattr(recordings, 'INDEX', path)
    assert api.get('/api/recordings').status_code == 409


def test_unknown_execution_is_not_synthesized(api):
    assert api.get('/api/recordings/record-0000000000000000').status_code == 404


def test_replay_preserves_historical_bytes_quotes_and_saved_approval_text(api):
    index = recordings._index()
    paths = {recordings.ROOT / name for entry in index.values() for name in entry["files"]}
    log_path = recordings.ROOT / "decision_log.json"
    paths.add(log_path)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    log = json.loads(log_path.read_text(encoding="utf-8"))
    quote_count = 0
    for key, entry in index.items():
        data = api.get('/api/recordings/' + key).json()
        expected_events = [e for e in log if e.get("run_id") == entry["execution_id"]]
        assert [(e["action"], e.get("outcome")) for e in data["audit"]] == [(e["action"], e.get("outcome")) for e in expected_events]
        if "investigation" not in entry["outputs"]:
            continue
        investigation = json.loads((recordings.ROOT / entry["outputs"]["investigation"]).read_text(encoding="utf-8"))
        for recorded, shown in zip(investigation["findings"], data["findings"]):
            quotes = [q for q in recorded["quotes"] if q["status"] == "verified"]
            assert [(q["text"], q["url"]) for q in quotes] == [(q["text"], q["url"]) for q in shown["quotations"]]
            quote_count += len(quotes)
    assert quote_count == 56
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
