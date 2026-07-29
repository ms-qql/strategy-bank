"""PROJ-20: echte Konverterpfade ohne gemockte Drittanbietergrenzen."""

import io
import os
import zipfile

import pytest
from ebooklib import epub
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services import document_converter as dc


def _epub_bytes() -> bytes:
    book = epub.EpubBook()
    book.set_identifier("proj-20-test")
    book.set_title("Testbuch")
    book.set_language("de")
    chapter = epub.EpubHtml(title="Kapitel", file_name="kapitel.xhtml", lang="de")
    chapter.content = (
        b"<h1>Momentum</h1><p>Kaufe beim Ausbruch.</p><ul><li>Long</li></ul>"
        b"<pre><code>rsi = 14</code></pre>"
        b"<table><tr><th>Parameter</th><th>Wert</th></tr>"
        b"<tr><td>RSI</td><td>14</td></tr></table>"
    )
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    output = io.BytesIO()
    epub.write_epub(output, book)
    return output.getvalue()


def _epub_with_content(content: bytes) -> bytes:
    book = epub.EpubBook()
    book.set_identifier("proj-20-sized-test")
    book.set_title("Testbuch")
    book.set_language("de")
    chapter = epub.EpubHtml(title="Kapitel", file_name="kapitel.xhtml", lang="de")
    chapter.content = content
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]
    output = io.BytesIO()
    epub.write_epub(output, book)
    return output.getvalue()


def _protected_epub_bytes() -> bytes:
    source = zipfile.ZipFile(io.BytesIO(_epub_bytes()))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as protected:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.endswith("kapitel.xhtml"):
                data = b"\xff\xfe\x00encrypted"
            protected.writestr(item, data)
        protected.writestr(
            "META-INF/encryption.xml",
            """<?xml version="1.0"?>
            <encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <EncryptedData>
                <CipherData><CipherReference URI="EPUB/kapitel.xhtml"/></CipherData>
              </EncryptedData>
            </encryption>""",
        )
    return output.getvalue()


def _text_pdf_bytes() -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=100)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 12 Tf 10 50 Td (Momentum strategy) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(content)
    writer.write(output)
    return output.getvalue()


def test_pdf_with_text_layer_is_extracted():
    assert "Momentum strategy" in dc.convert_to_markdown(_text_pdf_bytes(), "pdf_file")


def test_epub_preserves_heading_paragraph_and_list_as_markdown():
    markdown = dc.convert_to_markdown(_epub_bytes(), "epub_file")

    assert "# Momentum" in markdown
    assert "Kaufe beim Ausbruch." in markdown
    assert "* Long" in markdown
    assert "rsi = 14" in markdown
    assert "| Parameter | Wert |" in markdown


def test_source_endpoint_persists_real_epub_as_markdown(client):
    response = client.post(
        "/sources",
        files={"file": ("buch.epub", _epub_bytes(), "application/epub+zip")},
    )

    assert response.status_code == 201
    source = response.json()
    assert source["source_type"] == "epub_file"
    assert source["filename"] == "buch.epub"
    assert "# Momentum" in source["content"]


def test_blank_pdf_is_rejected_as_scan_without_text_layer():
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(output)

    with pytest.raises(ValueError, match="Scan-PDFs werden nicht unterstützt"):
        dc.convert_to_markdown(output.getvalue(), "pdf_file")


def test_encrypted_pdf_is_rejected_as_protected():
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    writer.write(output)

    with pytest.raises(ValueError, match="Geschützte Dokumente"):
        dc.convert_to_markdown(output.getvalue(), "pdf_file")


def test_broken_epub_is_rejected():
    with pytest.raises(ValueError, match="konnte nicht gelesen"):
        dc.convert_to_markdown(b"not-an-epub", "epub_file")


def test_protected_epub_is_rejected():
    with pytest.raises(ValueError, match="Geschützte Dokumente"):
        dc.convert_to_markdown(_protected_epub_bytes(), "epub_file")


def test_epub_expanded_content_is_bounded(monkeypatch):
    monkeypatch.setattr(dc, "MAX_CONVERTED_BYTES", 1024, raising=False)
    raw = _epub_with_content(b"<p>" + b"A" * 2048 + b"</p>")

    with pytest.raises(ValueError, match="zu groß"):
        dc.convert_to_markdown(raw, "epub_file")


def test_mobi_epub_output_is_converted_and_tempdir_removed(monkeypatch):
    extracted_dirs = []

    def fake_unpack(infile, outdir, epubver):
        extracted_dirs.append(outdir)
        epub_dir = os.path.join(outdir, "mobi8")
        os.makedirs(epub_dir)
        stem = os.path.splitext(os.path.basename(infile))[0]
        with open(os.path.join(epub_dir, stem + ".epub"), "wb") as result:
            result.write(_epub_bytes())

    monkeypatch.setattr("mobi.kindleunpack.unpackBook", fake_unpack)

    markdown = dc.convert_to_markdown(b"mobi", "mobi_file")

    assert "# Momentum" in markdown
    assert extracted_dirs and not os.path.exists(extracted_dirs[0])


def test_mobi_html_fallback_is_converted(monkeypatch):
    def fake_unpack(infile, outdir, epubver):
        html_dir = os.path.join(outdir, "mobi7")
        os.makedirs(html_dir)
        with open(os.path.join(html_dir, "book.html"), "w", encoding="utf-8") as result:
            result.write("<h1>Momentum</h1><p>Kaufe beim Ausbruch.</p>")

    monkeypatch.setattr("mobi.kindleunpack.unpackBook", fake_unpack)

    markdown = dc.convert_to_markdown(b"mobi", "mobi_file")

    assert "# Momentum" in markdown


def test_unknown_source_type_is_rejected():
    with pytest.raises(ValueError, match="Unbekannter Quelltyp"):
        dc.convert_to_markdown(b"x", "docx_file")
