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
