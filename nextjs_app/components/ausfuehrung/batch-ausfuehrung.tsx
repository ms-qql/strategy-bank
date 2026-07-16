"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { apiDelete, apiGet, apiPost, apiPostJson, ApiError } from "@/lib/api-client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  batchRunsResponseSchema,
  runReadSchema,
  RUN_STATUSES,
  type BatchRunsResponse,
  type RunRead,
  type RunStatus,
  type VersionSummary,
} from "@/lib/schemas/batch";
import { useRouter } from "next/navigation";
import {
  Check,
  Circle,
  FileSearch,
  Loader,
  Play,
  RotateCcw,
  Trash2,
  TriangleAlert,
  X,
} from "lucide-react";

const DIRECTION_MODE_LABELS: Record<string, string> = {
  kombiniert: "Kombiniert",
  "long-only": "Long-only",
  "short-only": "Short-only",
};

const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  geplant: "Geplant",
  bestätigt: "Bestätigt",
  in_queue: "In Queue",
  läuft: "Läuft",
  erfolgreich: "Erfolgreich",
  fehlgeschlagen: "Fehlgeschlagen",
  abgebrochen: "Abgebrochen",
};

function statusVariant(status: RunStatus): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "erfolgreich":
      return "default";
    case "fehlgeschlagen":
      return "destructive";
    case "läuft":
    case "in_queue":
      return "default";
    case "abgebrochen":
      return "secondary";
    default:
      return "outline";
  }
}

const POLL_INTERVAL_MS = 10_000;

function getPendingStatuses(): string {
  return RUN_STATUSES.filter((s) => !["erfolgreich", "fehlgeschlagen", "abgebrochen"].includes(s)).join(",");
}

interface BatchAusfuehrungProps {
  batchId: string;
  versions: VersionSummary[];
  creditMax: number;
  creditBalance: number | null | undefined;
  creditRemaining: number | null | undefined;
  creditTier: string | null | undefined;
  creditReset: string | null | undefined;
  creditCheckedAt: string | null | undefined;
  onClose: () => void;
}

export default function BatchAusfuehrung({
  batchId,
  versions,
  creditMax,
  creditBalance,
  creditRemaining,
  creditTier,
  creditReset,
  creditCheckedAt,
}: BatchAusfuehrungProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [data, setData] = useState<BatchRunsResponse | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      const pending = getPendingStatuses();
      const result = batchRunsResponseSchema.parse(
        await apiGet<BatchRunsResponse>(`/batches/${batchId}/runs?pending=${encodeURIComponent(pending)}`),
      );
      setData(result);
      const hasPending = result.runs.some(
        (r) => !["erfolgreich", "fehlgeschlagen", "abgebrochen"].includes(r.status),
      );
      setStarted(result.batch_status === "in_ausfuehrung");
      return hasPending;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Runs konnten nicht geladen werden.");
      return false;
    }
  }, [batchId]);

  const ensurePolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const hasPending = await fetchRuns();
      if (!hasPending && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, POLL_INTERVAL_MS);
  }, [fetchRuns]);

  useEffect(() => {
    fetchRuns().then((hasPending) => {
      if (hasPending) ensurePolling();
    });
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchRuns, ensurePolling]);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      await apiPost(`/batches/${batchId}/start`);
      setStarted(true);
      await fetchRuns().then((hasPending) => {
        if (hasPending) ensurePolling();
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Batch-Start fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (runId: string) => {
    setActionLoading(runId);
    setError(null);
    try {
      const updated = runReadSchema.parse(await apiPostJson(`/runs/${runId}/cancel`, {}));
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          runs: prev.runs.map((r) => (r.id === runId ? updated : r)),
        };
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Abbrechen fehlgeschlagen.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetryCheck = async (runId: string) => {
    setActionLoading(`credit-${runId}`);
    setError(null);
    try {
      const result = await apiGet(`/runs/${runId}/retry-credit-check`);
      return z.object({ ok: z.boolean(), reason: z.string().nullable().optional() }).parse(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Credit-Prüfung fehlgeschlagen.");
      return null;
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetry = async (runId: string) => {
    const check = await handleRetryCheck(runId);
    if (!check || !check.ok) {
      if (check?.reason) setError(check.reason);
      return;
    }
    setActionLoading(runId);
    setError(null);
    try {
      await apiPost(`/runs/${runId}/retry`);
      await fetchRuns().then((hasPending) => {
        if (hasPending) ensurePolling();
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Retry fehlgeschlagen.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (runId: string) => {
    if (!window.confirm("Diesen abgeschlossenen Run inklusive Audit und Ergebnis löschen?")) return;
    setActionLoading(runId);
    setError(null);
    try {
      await apiDelete(`/runs/${runId}`);
      await fetchRuns();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Run konnte nicht gelöscht werden.");
    } finally {
      setActionLoading(null);
    }
  };

  if (!started) {
    return (
      <Card className="mb-6 border-2 border-border">
        <CardHeader>
          <CardTitle>Batch-Ausführung</CardTitle>
          <CardDescription>
            Bestätigte Runs können jetzt gestartet werden. Die Ausführung läuft
            im Hintergrund — das Browser-Fenster muss nicht offen bleiben.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {error && (
            <Alert variant="destructive">
              <TriangleAlert aria-hidden="true" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="flex justify-end">
            <Button onClick={handleStart} disabled={loading}>
              {loading && <Loader className="mr-1 h-4 w-4 animate-spin" />}
              <Play className="mr-1 h-4 w-4" />
              Batch starten
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const { summary } = data;
  const allDone = summary.offen === 0;

  return (
    <Card className="mb-6 border-2 border-border">
      <CardHeader>
        <CardTitle>Batch-Ausführung</CardTitle>
        <CardDescription>
          {allDone
            ? "Alle Runs abgeschlossen."
            : `${summary.offen} Run(s) noch in Bearbeitung — andere Runs laufen auch bei Einzelfehlern weiter.`}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {error && (
          <Alert variant="destructive">
            <TriangleAlert aria-hidden="true" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <Badge variant="default">
              <Check className="h-3 w-3" />
              {summary.erfolgreich}
            </Badge>
            <span className="text-muted-foreground">Erfolgreich</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="destructive">
              <X className="h-3 w-3" />
              {summary.fehlgeschlagen}
            </Badge>
            <span className="text-muted-foreground">Fehlgeschlagen</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="secondary">
              <Circle className="h-3 w-3" />
              {summary.abgebrochen}
            </Badge>
            <span className="text-muted-foreground">Abgebrochen</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Badge variant="outline">
              <Loader className="h-3 w-3 animate-spin" />
              {summary.offen}
            </Badge>
            <span className="text-muted-foreground">Offen</span>
          </div>
          <div className="ml-auto text-xs text-muted-foreground">
            {summary.erfolgreich + summary.fehlgeschlagen + summary.abgebrochen} / {summary.total}{" "}
            abgeschlossen
          </div>
        </div>

        <div className="rounded-md border border-border p-4">
          <p className="mb-2 text-sm font-medium">Credit-Snapshot (bei Bestätigung)</p>
          <div className="grid gap-2 text-sm">
            <div className="flex flex-wrap gap-4">
              <span>
                <span className="text-muted-foreground">Max:</span>{" "}
                <span className="font-mono">{creditMax}</span>
              </span>
              <span>
                <span className="text-muted-foreground">Guthaben:</span>{" "}
                <span className="font-mono">{creditBalance ?? "-"}</span>
              </span>
              <span>
                <span className="text-muted-foreground">Verbleibend:</span>{" "}
                <span className="font-mono">{creditRemaining ?? "-"}</span>
              </span>
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>Tarif: {creditTier ?? "-"}</span>
              <span>Reset: {creditReset ?? "-"}</span>
              <span>
                Geprüft:{" "}
                {creditCheckedAt
                  ? new Date(creditCheckedAt).toLocaleString("de-DE")
                  : "-"}
              </span>
            </div>
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium">Runs ({data.runs.length})</p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Strategieversion</TableHead>
                <TableHead>Instrument</TableHead>
                <TableHead>Richtung</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ergebnis</TableHead>
                <TableHead className="text-right">Aktion</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.runs.map((r) => (
                <RunZeile
                  key={r.id}
                  run={r}
                  versions={versions}
                  actionLoading={actionLoading}
                  onCancel={handleCancel}
                  onRetry={handleRetry}
                  onDelete={handleDelete}
                />
              ))}
            </TableBody>
          </Table>
        </div>

        {!allDone && (
          <p className="text-xs text-muted-foreground">
            Runs werden im Hintergrund verarbeitet — diese Seite aktualisiert sich
            automatisch.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function RunZeile({
  run,
  versions,
  actionLoading,
  onCancel,
  onRetry,
  onDelete,
}: {
  run: RunRead;
  versions: VersionSummary[];
  actionLoading: string | null;
  onCancel: (runId: string) => void;
  onRetry: (runId: string) => void;
  onDelete: (runId: string) => void;
}) {
  const router = useRouter();
  const versionName =
    versions.find((v) => v.id === run.strategy_version_id)?.name ??
    run.strategy_version_id.slice(0, 8);

  const metrics = run.backtest_metrics;
  const isCompleted = ["erfolgreich", "fehlgeschlagen", "abgebrochen"].includes(run.status);

  return (
    <TableRow>
      <TableCell className="font-mono text-xs">{versionName}</TableCell>
      <TableCell className="font-mono">{run.provider_symbol}</TableCell>
      <TableCell>
        {DIRECTION_MODE_LABELS[run.direction_mode] ?? run.direction_mode}
      </TableCell>
      <TableCell>
        <span className="inline-flex items-center gap-1">
          {run.status === "läuft" && (
            <Loader className="h-3 w-3 animate-spin text-muted-foreground" />
          )}
          {run.status === "in_queue" && (
            <Loader className="h-3 w-3 animate-spin text-muted-foreground" />
          )}
          {run.status === "erfolgreich" && (
            <Check className="h-3 w-3 text-green-600" />
          )}
          {run.status === "fehlgeschlagen" && (
            <TriangleAlert className="h-3 w-3 text-destructive" />
          )}
          {run.status === "abgebrochen" && (
            <X className="h-3 w-3 text-muted-foreground" />
          )}
          <Badge variant={statusVariant(run.status)}>
            {RUN_STATUS_LABELS[run.status]}
          </Badge>
        </span>
        {run.error_message && (
          <p className="mt-1 max-w-64 truncate text-xs text-destructive" title={run.error_message}>
            {run.error_message}
          </p>
        )}
      </TableCell>
      <TableCell className="text-right font-mono text-xs">
        {metrics ? (
          <div className="flex flex-col gap-0.5">
            {metrics.tradeCount != null && (
              <span>
                Trades: <span className="font-medium">{metrics.tradeCount}</span>
              </span>
            )}
            {metrics.netProfitPct != null && (
              <span
                className={
                  metrics.netProfitPct >= 0
                    ? "text-green-600"
                    : "text-red-600"
                }
              >
                Net: {metrics.netProfitPct.toFixed(1)}%
              </span>
            )}
            {metrics.maxDrawdownPct != null && (
              <span className="text-red-600">
                DD: {metrics.maxDrawdownPct.toFixed(1)}%
              </span>
            )}
            {metrics.sharpeRatio != null && (
              <span>Sharpe: {metrics.sharpeRatio.toFixed(2)}</span>
            )}
            {metrics.tradeCount === 0 && (
              <span className="text-muted-foreground">Keine Trades</span>
            )}
          </div>
        ) : (
          <span className="text-muted-foreground">–</span>
        )}
      </TableCell>
      <TableCell className="text-right">
        {(run.status === "geplant" || run.status === "bestätigt") && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCancel(run.id)}
            disabled={actionLoading === run.id}
          >
            {actionLoading === run.id && (
              <Loader className="mr-1 h-3 w-3 animate-spin" />
            )}
            Abbrechen
          </Button>
        )}
        {run.status === "fehlgeschlagen" && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onRetry(run.id)}
            disabled={actionLoading === run.id}
          >
            {actionLoading === run.id && (
              <Loader className="mr-1 h-3 w-3 animate-spin" />
            )}
            <RotateCcw className="mr-1 h-3 w-3" />
            Wiederholen
          </Button>
        )}
        {run.status !== "läuft" && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(run.id)}
            disabled={actionLoading === run.id}
            className="ml-1"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        )}
        {isCompleted && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/runs/${run.id}/audit`)}
            className="ml-1"
          >
            <FileSearch className="mr-1 h-3 w-3" />
            Audit
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
