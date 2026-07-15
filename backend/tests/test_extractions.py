from app.routes import extractions as extractions_routes


def test_start_extraction_creates_run_and_updates_source_status(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        extractions_routes, "execute_extraction", lambda *args: calls.append(args)
    )

    source = client.post("/sources", data={"content": "Kaufe wenn RSI < 30."}).json()
    resp = client.post(f"/sources/{source['id']}/extractions")

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "läuft"
    assert body["source_id"] == source["id"]
    assert calls  # Background-Task wurde eingeplant und (im TestClient synchron) ausgeführt.

    updated_source = client.get(f"/sources/{source['id']}").json()
    assert updated_source["extraction_status"] == "wird extrahiert"


def test_start_extraction_404_for_missing_source(client):
    resp = client.post("/sources/00000000-0000-0000-0000-000000000000/extractions")
    assert resp.status_code == 404


def test_list_extractions_for_source(client, monkeypatch):
    monkeypatch.setattr(extractions_routes, "execute_extraction", lambda *args: None)
    source = client.post("/sources", data={"content": "Quelle für Liste"}).json()
    client.post(f"/sources/{source['id']}/extractions")
    resp = client.get(f"/sources/{source['id']}/extractions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_extraction_404(client):
    resp = client.get("/extractions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_draft_404(client):
    resp = client.get("/drafts/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_categories(client):
    resp = client.get("/categories")
    assert resp.status_code == 200
    categories = resp.json()["categories"]
    assert "Sonstige" in categories
    assert "Mean Reversion" in categories
