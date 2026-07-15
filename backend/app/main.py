"""FastAPI-App für Strategy Bank (Solo-Nutzer, kein Mandant/RLS)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.errors import ForeignKeyViolation, InvalidTextRepresentation

from .config import settings
from .routes import extractions as extraction_routes
from .routes import sources as source_routes

app = FastAPI(title="Strategy Bank API", version="0.1.0")

# CORS: Next.js-Frontend (Port 3000) spricht cross-origin mit FastAPI
# (Port 8000). Ohne Middleware blockt der Browser jeden POST (multipart
# triggert Preflight). Origins kommen aus settings — Prod via .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["GET", "POST"],
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
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


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
