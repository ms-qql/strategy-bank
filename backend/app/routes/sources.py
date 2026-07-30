import hashlib
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import settings
from ..db import run_command, run_query, run_query_one
from ..schemas.sources import SourceDetail, SourceListItem
from ..services.document_converter import convert_to_markdown

router = APIRouter(prefix="/sources", tags=["sources"])

ALLOWED_EXTENSIONS = {".md", ".pdf", ".epub", ".mobi"}

EXT_TO_SOURCE_TYPE = {
    ".md": "markdown_file",
    ".pdf": "pdf_file",
    ".epub": "epub_file",
    ".mobi": "mobi_file",
}

DOCUMENT_TYPES = {"pdf_file", "epub_file", "mobi_file"}


def _ext_lower(filename: str) -> str:
    dot = filename.rfind(".")
    if dot == -1:
        return ""
    return filename[dot:].lower()


@router.post("", response_model=SourceDetail, status_code=201)
async def create_source(
    content: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> dict:
    has_content = content is not None and content.strip() != ""
    has_file = file is not None and bool(file.filename)

    if has_content and has_file:
        raise HTTPException(400, "Es kann nur Text ODER eine Datei angegeben werden, nicht beides.")
    if not has_content and not has_file:
        raise HTTPException(400, "Quelle enthält keinen Inhalt.")

    if has_file:
        assert file is not None
        ext = _ext_lower(file.filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, "Nur .md-, .pdf-, .epub- und .mobi-Dateien werden unterstützt.")
        raw_bytes = await file.read()
        source_type = EXT_TO_SOURCE_TYPE[ext]
        file_name = file.filename
    else:
        assert content is not None
        raw_bytes = content.encode("utf-8")
        source_type = "text"
        file_name = None

    if len(raw_bytes) > settings.source_max_bytes:
        limit_mb = settings.source_max_bytes // (1024 * 1024)
        raise HTTPException(400, f"Datei überschreitet das Größenlimit von {limit_mb} MB.")

    if source_type in DOCUMENT_TYPES:
        try:
            text = convert_to_markdown(raw_bytes, source_type)
        except ValueError as e:
            raise HTTPException(400, str(e))
    elif source_type == "markdown_file":
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "Datei konnte nicht als Text gelesen werden.")
    else:
        text = raw_bytes.decode("utf-8")

    if not text.strip():
        raise HTTPException(400, "Quelle enthält keinen Inhalt.")

    source_hash = hashlib.sha256(raw_bytes).hexdigest()

    row = run_command(
        """
        INSERT INTO sources (content, source_hash, source_type, file_name)
        VALUES (%s, %s, %s, %s)
        RETURNING id, content, source_hash, source_type, file_name AS filename,
                  extraction_status, created_at AS captured_at
        """,
        [text, source_hash, source_type, file_name],
        returning=True,
    )
    return row  # type: ignore[return-value]


@router.get("", response_model=list[SourceListItem])
def list_sources(limit: int = 50, offset: int = 0) -> list[dict]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    return run_query(
        """
        SELECT id, source_hash, source_type, file_name AS filename,
               extraction_status, created_at AS captured_at
        FROM sources ORDER BY created_at DESC LIMIT %s OFFSET %s
        """,
        [limit, offset],
    )


@router.get("/{source_id}", response_model=SourceDetail)
def get_source(source_id: UUID) -> dict:
    row = run_query_one(
        """
        SELECT id, content, source_hash, source_type, file_name AS filename,
               extraction_status, created_at AS captured_at
        FROM sources WHERE id = %s
        """,
        [source_id],
    )
    if not row:
        raise HTTPException(404, "Quelle nicht gefunden.")
    return row
