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


# --- PROJ-20: Dokumentimport-Typen ---

CONVERTED_MD = "# Konvertiert\n\nInhalt aus dem Dokument."


def _patch_converter(monkeypatch, text=CONVERTED_MD):
    monkeypatch.setattr(
        "app.routes.sources.convert_to_markdown",
        lambda raw, st: text,
    )


def test_create_source_pdf_success(client, monkeypatch):
    _patch_converter(monkeypatch)
    resp = client.post(
        "/sources", files={"file": ("doku.pdf", b"%PDF-1.4 fake", "application/pdf")}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "pdf_file"
    assert body["filename"] == "doku.pdf"
    assert body["content"] == CONVERTED_MD


def test_create_source_epub_success(client, monkeypatch):
    _patch_converter(monkeypatch)
    resp = client.post(
        "/sources", files={"file": ("buch.epub", b"fake epub", "application/epub+zip")}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "epub_file"
    assert body["filename"] == "buch.epub"


def test_create_source_mobi_success(client, monkeypatch):
    _patch_converter(monkeypatch)
    resp = client.post(
        "/sources",
        files={"file": ("kindle.mobi", b"fake mobi", "application/x-mobipocket-ebook")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source_type"] == "mobi_file"
    assert body["filename"] == "kindle.mobi"


def test_create_source_empty_conversion_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.sources.convert_to_markdown",
        lambda raw, st: "   ",
    )
    resp = client.post(
        "/sources", files={"file": ("leer.pdf", b"%PDF-1.4 empty", "application/pdf")}
    )
    assert resp.status_code == 400
    assert "keinen Inhalt" in resp.json()["detail"]


def test_create_source_no_text_layer_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.sources.convert_to_markdown",
        lambda raw, st: (_ for _ in ()).throw(
            ValueError(
                "Die PDF enthält keinen auslesbaren Text. Scan-PDFs werden nicht unterstützt."
            )
        ),
    )
    resp = client.post(
        "/sources", files={"file": ("scan.pdf", b"%PDF-1.4 scan", "application/pdf")}
    )
    assert resp.status_code == 400
    assert "Scan-PDF" in resp.json()["detail"]


def test_create_source_pdf_encrypted_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.sources.convert_to_markdown",
        lambda raw, st: (_ for _ in ()).throw(
            ValueError("Geschützte Dokumente werden nicht unterstützt.")
        ),
    )
    resp = client.post(
        "/sources", files={"file": ("drm.pdf", b"%PDF-1.4 drm", "application/pdf")}
    )
    assert resp.status_code == 400
    assert "Geschützte" in resp.json()["detail"]


def test_create_source_broken_document_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.sources.convert_to_markdown",
        lambda raw, st: (_ for _ in ()).throw(
            ValueError("Das Dokument konnte nicht gelesen werden.")
        ),
    )
    resp = client.post(
        "/sources", files={"file": ("broken.epub", b"garbage", "application/epub+zip")}
    )
    assert resp.status_code == 400
    assert "nicht gelesen" in resp.json()["detail"]


def test_create_source_hash_over_original_bytes(client, monkeypatch):
    """SHA-256 hash must be computed over raw upload bytes, not converted Markdown."""
    original = b"%PDF-1.4 original content"
    monkeypatch.setattr(
        "app.routes.sources.convert_to_markdown",
        lambda raw, st: "anderer Text",
    )
    resp = client.post(
        "/sources", files={"file": ("orig.pdf", original, "application/pdf")}
    )
    assert resp.status_code == 201
    body = resp.json()
    import hashlib
    expected_hash = hashlib.sha256(original).hexdigest()
    assert body["source_hash"] == expected_hash


def test_extension_case_insensitive(client, monkeypatch):
    _patch_converter(monkeypatch)
    resp = client.post(
        "/sources", files={"file": ("Doc.PDF", b"%PDF-1.4 uc", "application/pdf")}
    )
    assert resp.status_code == 201
    assert resp.json()["source_type"] == "pdf_file"


def test_no_extension_rejected(client):
    resp = client.post(
        "/sources", files={"file": ("noext", b"blob", "application/octet-stream")}
    )
    assert resp.status_code == 400
    assert "unterstützt" in resp.json()["detail"]
