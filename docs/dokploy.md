# Dokploy: Strategy Bank

## Compose-App

1. In Dokploy ein **Compose**-Projekt aus `ms-qql/strategy-bank`, Branch `main`, Compose Path `docker-compose.dokploy.yml` anlegen.
2. Vor dem ersten Build diese Umgebungsvariablen setzen:
   - `POSTGRES_PASSWORD`: neues langes Passwort.
   - `DATABASE_URL`: `postgresql://strategy_bank:<URL-kodiertes Passwort>@strategy-bank-db:5432/strategy_bank`
   - `OPENCODE_GO_API_KEY`: vorhandener OpenCode-Go-Key als Secret.
3. Die öffentliche Domain ausschließlich dem Service `strategy-bank-web` auf Container-Port `3000` zuordnen und TLS aktivieren. Datenbank und API erhalten keine Domain.
4. Auto Deploy aktivieren und den ersten Build starten.

Das Frontend leitet `/api/*` intern an FastAPI weiter. Dadurch werden weder eine öffentliche API-URL noch CORS-Origins für die Produktionsdomain benötigt. Beim Start führt das Backend die vorhandenen idempotenten SQL-Dateien aus `backend/sql/` aus. Der Extraktions-Default ist `opencode-go/kimi-k2.7-code`; ein anderes Go-Modell kann über `EXTRACTION_MODEL` gesetzt werden.
