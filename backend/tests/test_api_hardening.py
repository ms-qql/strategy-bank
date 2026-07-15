"""Tests für die Backend-Härtung (QA-Bugs BUG-1 + BUG-2 aus PROJ-1).

BUG-1: CORS-Middleware muss Cross-Origin-Requests vom Next.js-Frontend erlauben.
BUG-2: Nicht-UUID-Pfad-IDs müssen als 404 „Nicht gefunden." beantwortet werden
        (statt 422 mit Pydantic-Trace oder 500 bei DB-Cast-Fehlern).
"""


def test_cors_preflight_options_returns_cors_headers(client):
    resp = client.options(
        "/sources",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


def test_cors_actual_post_returns_allow_origin_header(client):
    resp = client.post(
        "/sources",
        data={"content": "CORS-Test"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert resp.status_code == 201
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_disallowed_origin_not_echoed(client):
    resp = client.post(
        "/sources",
        data={"content": "x"},
        headers={"Origin": "http://evil.example.com"},
    )
    assert "access-control-allow-origin" not in resp.headers or resp.headers["access-control-allow-origin"] != "http://evil.example.com"


def test_get_source_non_uuid_returns_404(client):
    resp = client.get("/sources/not-a-uuid")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Nicht gefunden."


def test_get_extraction_non_uuid_returns_404(client):
    resp = client.get("/extractions/not-a-uuid")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Nicht gefunden."


def test_get_draft_non_uuid_returns_404(client):
    resp = client.get("/drafts/not-a-uuid")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Nicht gefunden."


def test_post_extraction_non_uuid_source_returns_404(client):
    resp = client.post("/sources/not-a-uuid/extractions")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Nicht gefunden."


def test_get_source_list_non_uuid_returns_404(client):
    # /sources/{id} mit nicht-UUID → 404 (sonst würde die Route fälschlich
    # als Listen-Query interpretiert).
    resp = client.get("/sources/abc")
    assert resp.status_code == 404


def test_validation_error_non_uuid_path_does_not_leak_pydantic_trace(client):
    resp = client.get("/sources/zzz")
    body = resp.json()
    # Vor dem Fix: 422 mit `detail: [{"type": "uuid_parsing", ...}]`.
    # Nach dem Fix: 404 mit flachem `detail: "Nicht gefunden."`.
    assert isinstance(body["detail"], str)
    assert "uuid_parsing" not in resp.text
    assert "Pydantic" not in resp.text
