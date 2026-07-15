"""FastAPI-App für Strategy Bank (Solo-Nutzer, kein Mandant/RLS)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg.errors import ForeignKeyViolation, InvalidTextRepresentation

from .routes import extractions as extraction_routes
from .routes import sources as source_routes

app = FastAPI(title="Strategy Bank API", version="0.1.0")


# Eine nicht-UUID Pfad-ID (z. B. /sources/foo) löst beim Postgres-UUID-Cast
# einen InvalidTextRepresentation-Fehler aus → ohne Handler ein 500. Als
# „nicht gefunden" (404) behandeln statt Serverfehler.
@app.exception_handler(InvalidTextRepresentation)
async def _invalid_uuid_handler(request: Request, exc: InvalidTextRepresentation) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Nicht gefunden."})


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
