"""FastAPI-App für Strategy Bank (Solo-Nutzer, kein Mandant/RLS)."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.errors import ForeignKeyViolation, InvalidTextRepresentation

from .config import settings
from .db import run_command, run_query
from .routes import audit as audit_routes
from .routes import batches as batch_routes
from .routes import drafts as draft_routes
from .routes import execution as execution_routes
from .routes import export as export_routes
from .routes import extractions as extraction_routes
from .routes import results as result_routes
from .routes import runs as run_routes
from .routes import sources as source_routes


def _recover_stuck_extractions() -> None:
    stale = run_query(
        """
        SELECT s.id AS source_id, er.id AS run_id
        FROM sources s
        JOIN extraction_runs er ON er.source_id = s.id
        WHERE s.extraction_status = 'wird extrahiert'
          AND er.status = 'läuft'
          AND er.started_at < now() - INTERVAL '30 minutes'
        """,
    )
    if not stale:
        return
    now = datetime.now(timezone.utc)
    for row in stale:
        run_command(
            "UPDATE extraction_runs SET status = 'fehlgeschlagen', finished_at = %s, "
            "error_message = 'Extraktion durch Server-Neustart abgebrochen.' WHERE id = %s",
            [now, row["run_id"]],
        )
        run_command(
            "UPDATE sources SET extraction_status = 'Extraktion fehlgeschlagen' WHERE id = %s",
            [row["source_id"]],
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _recover_stuck_extractions()
    yield


app = FastAPI(title="Strategy Bank API", version="0.1.0", lifespan=lifespan)

# CORS: Next.js-Frontend (Port 3000) spricht cross-origin mit FastAPI
# (Port 8000). Ohne Middleware blockt der Browser jeden POST (multipart
# triggert Preflight). Origins kommen aus settings — Prod via .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["content-type"],
    allow_credentials=False,
)


# Nicht-UUID Pfad-IDs (z. B. /sources/foo) lösen Pydantic-Path-Validation
# (422 mit englischem Trace) ODER — falls Pydantic durchrutscht — DB-Cast-
# Fehler aus. Beide Fälle als 404 „Nicht gefunden." behandeln statt 500/422.
@app.exception_handler(InvalidTextRepresentation)
async def _invalid_uuid_handler(request: Request, exc: InvalidTextRepresentation) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Nicht gefunden."})


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    for err in exc.errors():
        if err.get("type") == "uuid_parsing" and err.get("loc", [None])[0] == "path":
            return JSONResponse(status_code=404, content={"detail": "Nicht gefunden."})
    # Pydantic steckt rohe Exception-Instanzen in ctx (z. B. ValueError aus
    # benutzerdefinierten Validatoren). jsonable_encoder macht sie JSON-tauglich.
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


@app.exception_handler(ForeignKeyViolation)
async def _foreign_key_handler(request: Request, exc: ForeignKeyViolation) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Ein verknüpfter Datensatz existiert nicht."},
    )


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(source_routes.router)
app.include_router(extraction_routes.router)
app.include_router(draft_routes.router)
app.include_router(export_routes.router)
app.include_router(batch_routes.router)
app.include_router(audit_routes.router)
app.include_router(result_routes.router)
app.include_router(run_routes.router)
app.include_router(execution_routes.router)
