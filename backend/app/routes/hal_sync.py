from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from uuid import UUID

from ..services.hal_sync import (
    build_all_steckbriefe_zip,
    build_steckbrief_export,
    build_steckbriefe_zip_for_sources,
)

router = APIRouter(prefix="/hal", tags=["hal"])


class ExportSelectedRequest(BaseModel):
    source_ids: list[UUID]


@router.get("/export-all")
def hal_export_all() -> Response:
    content = build_all_steckbriefe_zip()
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=hal-steckbriefe.zip"},
    )


@router.post("/export-selected")
def hal_export_selected(body: ExportSelectedRequest) -> Response:
    if not body.source_ids:
        raise HTTPException(400, "Keine Quellen ausgewählt.")
    content = build_steckbriefe_zip_for_sources(body.source_ids)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=hal-steckbriefe-auswahl.zip"},
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
