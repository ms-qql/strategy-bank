"""PROJ-20: echte Konverterpfade ohne gemockte Drittanbietergrenzen."""

import io

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


@pytest.mark.xfail(
    strict=True,
    reason="BUG-1: mobi.extract liefert (tempdir, dateipfad), der Konverter erwartet einen Pfad",
)
def test_mobi_uses_library_return_contract(monkeypatch, tmp_path):
    extracted_dir = tmp_path / "extracted"
    extracted_dir.mkdir()
    epub_path = extracted_dir / "book.epub"
    epub_path.write_bytes(_epub_bytes())
    monkeypatch.setattr("mobi.extract", lambda _: (str(extracted_dir), str(epub_path)))

    markdown = dc.convert_to_markdown(b"mobi", "mobi_file")

    assert "# Momentum" in markdown


def test_unknown_source_type_is_rejected():
    with pytest.raises(ValueError, match="Unbekannter Quelltyp"):
        dc.convert_to_markdown(b"x", "docx_file")
