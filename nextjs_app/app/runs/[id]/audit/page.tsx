"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, ApiError } from "@/lib/api-client";
import { auditTrailReadSchema, type AuditTrailRead } from "@/lib/schemas/audit";
import {
  ArrowLeft,
  Loader,
  TriangleAlert,
  ExternalLink,
  FileText,
  Check,
  Circle,
  CalendarClock,
  Globe,
  Cpu,
  Database,
  Link2,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";

const RUN_KIND_LABELS: Record<string, string> = {
  standard: "Research",
  holdout: "Historisches Holdout",
  forward_test: "Echter Forward-Test",
};

const DIRECTION_MODE_LABELS: Record<string, string> = {
  kombiniert: "Kombiniert",
  "long-only": "Long-only",
  "short-only": "Short-only",
};

function formatDate(d: string | null): string {
  if (!d) return "–";
  return new Date(d).toLocaleString("de-DE");
}

function JsonBlock({ data }: { data: unknown }) {
  return (
    <pre className="overflow-auto rounded-md border border-border bg-muted/50 p-4 font-mono text-xs leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function FeldZeile({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border py-2 text-sm">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className={mono ? "font-mono text-right" : "text-right"}>
        {value ?? "–"}
      </span>
    </div>
  );
}

export default function RunAuditPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const runId = params.id;

  const [audit, setAudit] = useState<AuditTrailRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = auditTrailReadSchema.parse(
          await apiGet<AuditTrailRead>(`/runs/${runId}/audit`),
        );
        if (!cancelled) setAudit(data);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.message === "Audit-Trail nicht gefunden.") {
          setNotFound(true);
        } else {
          setError(e instanceof ApiError ? e.message : "Audit-Trail konnte nicht geladen werden.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [runId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-8">
        <div className="flex items-center justify-center py-16">
          <Loader className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </main>
    );
  }

  if (notFound) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-8">
        <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-6">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Zurück
        </Button>
        <Alert variant="destructive">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>
            Audit-Trail für diesen Run nicht gefunden. Der Run existiert möglicherweise
            noch nicht oder wurde noch nicht ausgeführt.
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  if (error || !audit) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-8">
        <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-6">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Zurück
        </Button>
        <Alert variant="destructive">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error ?? "Audit-Trail nicht verfügbar."}</AlertDescription>
        </Alert>
      </main>
    );
  }

  const finalized = audit.finalized_at != null;
  const periodEnd = audit.period_end ?? "Offen";

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-6">
        <ArrowLeft className="mr-1 h-4 w-4" />
        Zurück
      </Button>

      <h1 className="mb-6 font-heading text-2xl font-semibold tracking-tight">
        Audit-Trail
      </h1>

      {/* RunKopf */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarClock className="h-5 w-5 text-muted-foreground" />
            Run-Identität
          </CardTitle>
          <CardDescription>
            {finalized ? (
              <Badge variant="secondary" className="inline-flex items-center gap-1">
                <Check className="h-3 w-3" />
                Finalisiert
              </Badge>
            ) : (
              <Badge variant="outline" className="inline-flex items-center gap-1">
                <Circle className="h-3 w-3" />
                Nicht finalisiert
              </Badge>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-border">
            <FeldZeile
              label="Auswertungsart"
              value={RUN_KIND_LABELS[audit.run_kind] ?? audit.run_kind}
            />
            <FeldZeile label="Instrument" value={audit.provider_symbol} mono />
            <FeldZeile
              label="Richtung"
              value={DIRECTION_MODE_LABELS[audit.direction_mode] ?? audit.direction_mode}
            />
            <FeldZeile label="Timeframe" value={audit.timeframe} mono />
            <FeldZeile label="Erstellt" value={formatDate(audit.created_at)} mono />
            <FeldZeile label="Gestartet" value={formatDate(audit.started_at)} mono />
            <FeldZeile label="Beendet" value={formatDate(audit.ended_at)} mono />
            <FeldZeile label="Finalisiert" value={formatDate(audit.finalized_at)} mono />
          </div>
        </CardContent>
      </Card>

      {/* StrategieSnapshot */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-muted-foreground" />
            Strategie-Snapshot
          </CardTitle>
          <CardDescription>
            Eingefrorene Regelversion, Parameter und (sofern PROJ-10) Positionsmodus,
            Exit-Herkunft und Crypto-MTS-Eignung.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <JsonBlock data={audit.strategy_snapshot} />
        </CardContent>
      </Card>

      {/* BacktestKonfiguration */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-muted-foreground" />
            Backtest-Konfiguration
          </CardTitle>
          <CardDescription>
            Vollständiges Profil, Timeframe{periodEnd !== "Offen" ? " und Zeitraum" : ""}.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="divide-y divide-border">
            <FeldZeile label="Timeframe" value={audit.timeframe} mono />
            <FeldZeile label="Start" value={formatDate(audit.period_start)} mono />
            <FeldZeile label="Ende" value={periodEnd === "Offen" ? "Offen" : formatDate(periodEnd)} mono />
          </div>
          <JsonBlock data={audit.profile_snapshot} />
        </CardContent>
      </Card>

      {/* Ausfuehrungsdetails */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-muted-foreground" />
            Ausführungsdetails
          </CardTitle>
          <CardDescription>
            Agent-Runtime, Modell, Prompt, Executor und MCP-Aktion.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-border">
            <FeldZeile label="Agent-Runtime" value={audit.agent_runtime} mono />
            <FeldZeile label="Modell" value={audit.model} mono />
            <FeldZeile label="Prompt-Version" value={audit.prompt_version} mono />
            <FeldZeile label="Executor-Version" value={audit.executor_version} mono />
            <FeldZeile label="MCP-Aktion" value={audit.mcp_action} mono />
            <FeldZeile label="Externe Job-ID" value={audit.external_job_id} mono />
            <FeldZeile label="Externe Ergebnis-ID" value={audit.external_result_id} mono />
          </div>

          {/* Credit-Snapshot */}
          <h3 className="mb-3 mt-6 text-sm font-medium">Credit-Snapshot (bei Bestätigung)</h3>
          <div className="divide-y divide-border">
            <FeldZeile
              label="Max"
              value={audit.credit_max != null ? String(audit.credit_max) : null}
              mono
            />
            <FeldZeile
              label="Guthaben"
              value={audit.credit_balance != null ? String(audit.credit_balance) : null}
              mono
            />
            <FeldZeile
              label="Verbleibend"
              value={audit.credit_remaining != null ? String(audit.credit_remaining) : null}
              mono
            />
            <FeldZeile label="Tarif" value={audit.credit_tier} />
            <FeldZeile label="Reset" value={audit.credit_reset} />
            <FeldZeile label="Geprüft" value={formatDate(audit.credit_checked_at)} mono />
          </div>
        </CardContent>
      </Card>

      {/* ProviderMetadaten */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-muted-foreground" />
            Provider-Metadaten
          </CardTitle>
          <CardDescription>
            Engine- und Datenstand-Angaben, sofern von trader.dev geliefert.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-border">
            <FeldZeile label="Engine-Info" value={audit.engine_info} />
            <FeldZeile label="Datenstand" value={audit.data_freshness} />
          </div>
        </CardContent>
      </Card>

      {/* ExterneArtefakte */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-muted-foreground" />
            Externe Artefakte
          </CardTitle>
          <CardDescription>
            trader.dev-Report-Link und rohe strukturierte Antwort.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div>
            <h3 className="mb-2 text-sm font-medium">Report-Link</h3>
            {audit.report_available && audit.report_link ? (
              <a
                href={audit.report_link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-md bg-muted/50 px-3 py-2 font-mono text-sm text-primary hover:underline"
              >
                <ExternalLink className="h-4 w-4" />
                {audit.report_link}
              </a>
            ) : (
              <span className="text-sm text-muted-foreground">
                Report-Link nicht verfügbar
              </span>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-medium">Rohantwort</h3>
            {audit.raw_response_available && audit.raw_response ? (
              <JsonBlock data={audit.raw_response} />
            ) : (
              <span className="text-sm text-muted-foreground">
                Rohantwort nicht verfügbar
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
