"""UI delivery tests; no Ollama or workflow backend required."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_workspace_starts_without_model():
    response = client.get('/workspace')
    assert response.status_code == 200
    assert 'Founder workspace' in response.text
    assert 'STUBBED' in response.text
    assert 'default-src' in response.headers['content-security-policy']
    assert response.headers['x-content-type-options'] == 'nosniff'

def test_ui_assets_and_no_file_exposure():
    for name in ['app.js', 'styles.css', 'views.js', 'service.js', 'contracts.js', 'fixtures.js']:
        response = client.get('/workspace/assets/' + name)
        assert response.status_code == 200
        assert 'no-store' in response.headers['cache-control']
    for name in ['.env', 'router.py', 'CLAUDE.md', 'index.html']:
        assert client.get('/workspace/assets/' + name).status_code == 404

def test_workspace_is_read_only():
    assert client.post('/workspace', json={'approve': True}).status_code == 405
