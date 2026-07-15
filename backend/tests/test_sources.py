from app import config


def test_create_source_text_success(client):
    resp = client.post("/sources", data={"content": "Kaufe wenn RSI < 30."})
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "text"
    assert body["extraction_status"] == "noch nicht extrahiert"
    assert len(body["source_hash"]) == 64


def test_create_source_empty_rejected(client):
    resp = client.post("/sources", data={"content": "   "})
    assert resp.status_code == 400
    assert "keinen Inhalt" in resp.json()["detail"]


def test_create_source_neither_content_nor_file_rejected(client):
    resp = client.post("/sources", data={})
    assert resp.status_code == 400


def test_create_source_both_content_and_file_rejected(client):
    resp = client.post(
        "/sources",
        data={"content": "abc"},
        files={"file": ("test.md", b"# Titel", "text/markdown")},
    )
    assert resp.status_code == 400
    assert "nicht beides" in resp.json()["detail"]


def test_create_source_wrong_extension_rejected(client):
    resp = client.post("/sources", files={"file": ("test.txt", b"hallo", "text/plain")})
    assert resp.status_code == 400
    assert ".md" in resp.json()["detail"]


def test_create_source_markdown_file_success(client):
    resp = client.post(
        "/sources", files={"file": ("strategie.md", b"# Momentum\nKaufe bei Breakout.", "text/markdown")}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "markdown_file"
    assert body["filename"] == "strategie.md"


def test_create_source_too_large_rejected(client, monkeypatch):
    monkeypatch.setattr(config.settings, "source_max_bytes", 10)
    resp = client.post("/sources", data={"content": "das ist länger als zehn bytes"})
    assert resp.status_code == 400
    assert "Größenlimit" in resp.json()["detail"]


def test_create_source_invalid_utf8_rejected(client):
    resp = client.post(
        "/sources", files={"file": ("bad.md", b"\xff\xfe\x00\x01", "text/markdown")}
    )
    assert resp.status_code == 400
    assert "nicht als Text gelesen" in resp.json()["detail"]


def test_list_sources_newest_first(client):
    client.post("/sources", data={"content": "erste Quelle"})
    client.post("/sources", data={"content": "zweite Quelle"})
    resp = client.get("/sources")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["captured_at"] >= body[1]["captured_at"]
    assert len(body[0]["source_hash"]) == 64


def test_get_source_detail_and_404(client):
    created = client.post("/sources", data={"content": "Detail-Test-Quelle"}).json()
    resp = client.get(f"/sources/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "Detail-Test-Quelle"

    missing = client.get("/sources/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
