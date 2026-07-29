from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse
from uuid import UUID

from ..services.hal_sync import build_all_steckbriefe_zip, build_steckbrief_export

router = APIRouter(prefix="/hal", tags=["hal"])


@router.get("/export-all")
def hal_export_all() -> Response:
    content = build_all_steckbriefe_zip()
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=hal-steckbriefe.zip"},
    )


@router.get("/drafts/{draft_id}/export")
def hal_export_draft(draft_id: UUID) -> PlainTextResponse:
    export = build_steckbrief_export(draft_id)
    if not export:
        raise HTTPException(404, "Entwurf nicht gefunden.")
    filename, content = export
    return PlainTextResponse(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
