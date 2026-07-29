"""PROJ-20: Konvertiert PDF, EPUB, MOBI → Markdown."""

import io
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_CONVERTED_BYTES = 25 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 100 * 1024 * 1024
_TEXT_ENTRY_SUFFIXES = {".htm", ".html", ".ncx", ".opf", ".xhtml", ".xml"}


def _finish(parts: list[str]) -> str:
    text = "\n\n".join(part.strip() for part in parts if part.strip())
    if not text:
        raise ValueError("Das Dokument enthält keinen lesbaren Text.")
    if len(text.encode("utf-8")) > MAX_CONVERTED_BYTES:
        raise ValueError("Das Dokument ist nach der Umwandlung zu groß.")
    return text


def _validate_epub_archive(raw_bytes: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            entries = archive.infolist()
            if sum(entry.file_size for entry in entries) > MAX_ARCHIVE_EXPANDED_BYTES:
                raise ValueError("Das Dokument ist nach dem Entpacken zu groß.")
            if (
                sum(
                    entry.file_size
                    for entry in entries
                    if Path(entry.filename).suffix.lower() in _TEXT_ENTRY_SUFFIXES
                )
                > MAX_CONVERTED_BYTES
            ):
                raise ValueError("Das Dokument ist nach der Umwandlung zu groß.")

            try:
                encryption = archive.read("META-INF/encryption.xml")
            except KeyError:
                return
    except zipfile.BadZipFile:
        raise ValueError("Das Dokument konnte nicht gelesen werden.")

    try:
        root = ElementTree.fromstring(encryption)
    except ElementTree.ParseError:
        raise ValueError("Geschützte Dokumente werden nicht unterstützt.")
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "CipherReference":
            continue
        uri = element.attrib.get("URI", "").split("?", 1)[0]
        if Path(uri).suffix.lower() in _TEXT_ENTRY_SUFFIXES:
            raise ValueError("Geschützte Dokumente werden nicht unterstützt.")


def _convert_pdf(raw_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except PdfReadError:
        raise ValueError("Das Dokument konnte nicht gelesen werden.")

    if reader.is_encrypted:
        raise ValueError("Geschützte Dokumente werden nicht unterstützt.")

    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text.strip())

    if not parts:
        raise ValueError(
            "Die PDF enthält keinen auslesbaren Text. Scan-PDFs werden nicht unterstützt."
        )

    return _finish(parts)


def _convert_epub(raw_bytes: bytes) -> str:
    import ebooklib
    from ebooklib import epub
    from markdownify import markdownify

    _validate_epub_archive(raw_bytes)
    try:
        book = epub.read_epub(io.BytesIO(raw_bytes))
    except Exception:
        raise ValueError("Das Dokument konnte nicht gelesen werden.")

    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        try:
            html = item.get_content().decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            continue
        md = markdownify(html, heading_style="ATX", strip=["img", "script", "style"])
        if md.strip():
            parts.append(md.strip())

    return _finish(parts)


def _convert_html(raw_bytes: bytes) -> str:
    from markdownify import markdownify

    try:
        html = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Das Dokument konnte nicht gelesen werden.")
    return _finish([markdownify(html, heading_style="ATX", strip=["img", "script", "style"])])


def _convert_mobi(raw_bytes: bytes) -> str:
    from mobi import kindleunpack

    with tempfile.TemporaryDirectory(prefix="strategy-bank-mobi-") as temp_dir:
        mobi_path = Path(temp_dir) / "input.mobi"
        mobi_path.write_bytes(raw_bytes)
        try:
            kindleunpack.unpackBook(str(mobi_path), temp_dir, epubver="A")
        except Exception:
            raise ValueError("Das Dokument konnte nicht gelesen werden.")

        epub_path = Path(temp_dir) / "mobi8" / "input.epub"
        html_path = Path(temp_dir) / "mobi7" / "book.html"
        pdf_path = Path(temp_dir) / "input.001.pdf"
        if epub_path.is_file():
            return _convert_epub(epub_path.read_bytes())
        if html_path.is_file():
            return _convert_html(html_path.read_bytes())
        if pdf_path.is_file():
            return _convert_pdf(pdf_path.read_bytes())
        raise ValueError("Das Dokument konnte nicht gelesen werden.")


def convert_to_markdown(raw_bytes: bytes, source_type: str) -> str:
    if source_type == "pdf_file":
        return _convert_pdf(raw_bytes)
    elif source_type == "epub_file":
        return _convert_epub(raw_bytes)
    elif source_type == "mobi_file":
        return _convert_mobi(raw_bytes)
    raise ValueError(f"Unbekannter Quelltyp: {source_type}")
