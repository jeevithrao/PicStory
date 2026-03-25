# tests/test_routes.py
# Basic smoke tests for all API routes.
# Run with: pytest tests/test_routes.py -v

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io, zipfile

# --- We mock DB and file services so tests run without MySQL ---
@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    monkeypatch.setattr("app.db.connection.init_db", lambda: None)
    monkeypatch.setattr("app.services.db_service.create_project",   lambda **kw: "test-uuid-1234")
    monkeypatch.setattr("app.services.db_service.get_project",      lambda pid: {"id": pid, "mode": "upload", "language": "hi", "status": "uploaded", "prompt": None} if pid == "test-uuid-1234" else None)
    monkeypatch.setattr("app.services.db_service.update_project_status", lambda *a: None)
    monkeypatch.setattr("app.services.db_service.save_images",      lambda *a: None)
    monkeypatch.setattr("app.services.db_service.get_images",        lambda pid: [{"filename": "test.jpg", "display_order": 0}])
    monkeypatch.setattr("app.services.db_service.get_captions",     lambda pid: [{"caption_en": "A test image.", "caption_translated": "एक परीक्षण छवि।", "image_filename": "test.jpg"}])
    monkeypatch.setattr("app.services.db_service.save_captions",    lambda *a: None)
    monkeypatch.setattr("app.services.db_service.save_narration",   lambda *a: None)
    monkeypatch.setattr("app.services.db_service.get_narration",    lambda pid: {"narration_text": "test script", "narration_path": "outputs/test/narration.mp3"})
    monkeypatch.setattr("app.services.db_service.save_music",       lambda *a: None)
    monkeypatch.setattr("app.services.db_service.save_output",      lambda *a: None)
    monkeypatch.setattr("app.services.db_service.get_output",       lambda pid: None)
    monkeypatch.setattr("app.services.db_service.apply_image_edits",lambda *a, **kw: None)


@pytest.fixture
def client(mock_db):
    from app.main import app
    return TestClient(app)


def make_zip_bytes():
    """Create a minimal in-memory ZIP with one fake image."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.jpg", b"\xff\xd8\xff" + b"\x00" * 100)  # Fake JPEG header
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /upload
# ---------------------------------------------------------------------------
def test_upload_rejects_non_zip(client):
    r = client.post("/upload", files={"file": ("photo.jpg", b"fake", "image/jpeg")}, data={"language": "hi"})
    assert r.status_code == 400

def test_upload_accepts_zip(client, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.file_service.extract_zip", lambda b, pid: [str(tmp_path / "test.jpg")])
    monkeypatch.setattr("app.services.file_service.relative_path", lambda p: p)
    r = client.post("/upload", files={"file": ("photos.zip", make_zip_bytes(), "application/zip")}, data={"language": "hi"})
    assert r.status_code == 200
    assert "project_id" in r.json()


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------
def test_status_valid(client):
    r = client.get("/status/test-uuid-1234")
    assert r.status_code == 200
    assert r.json()["status"] == "uploaded"

def test_status_invalid(client):
    r = client.get("/status/nonexistent-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /caption
# ---------------------------------------------------------------------------
def test_caption(client, monkeypatch):
    monkeypatch.setattr("app.services.file_service.get_project_upload_dir", lambda pid: "/tmp")
    monkeypatch.setattr("app.services.translation_service.translate_batch", lambda texts, lang: texts)
    monkeypatch.setattr("ai.captioning.generate_captions", lambda paths: ["A test image."])
    r = client.post("/caption", json={"project_id": "test-uuid-1234", "language": "hi"})
    assert r.status_code == 200
    assert len(r.json()["captions"]) > 0


# ---------------------------------------------------------------------------
# /edit
# ---------------------------------------------------------------------------
def test_edit(client):
    r = client.post("/edit", json={
        "project_id":     "test-uuid-1234",
        "ordered_images": ["test.jpg"],
        "removed_images": [],
    })
    assert r.status_code == 200
    assert r.json()["final_image_count"] == 1


# ---------------------------------------------------------------------------
# /status — 404 for unknown project
# ---------------------------------------------------------------------------
def test_all_routes_return_404_for_bad_project(client):
    bad = {"project_id": "bad-id", "language": "hi"}
    assert client.post("/caption",   json=bad).status_code == 404
    assert client.post("/narration", json=bad).status_code == 404
    assert client.post("/edit",      json={**bad, "ordered_images": [], "removed_images": []}).status_code == 404
    assert client.post("/video",     json={**bad, "music_path": "x.mp3"}).status_code == 404
    assert client.post("/social",    json={**bad, "platform": "instagram"}).status_code == 404
