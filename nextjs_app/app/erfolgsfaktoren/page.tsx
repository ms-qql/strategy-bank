"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { apiDelete, apiGet, apiPost, ApiError } from "@/lib/api-client";
import {
  analysisRunReadSchema,
  analysisRunDetailReadSchema,
  cohortRowSchema,
  AXIS_OPTIONS,
  type AnalysisRunRead,
  type AnalysisRunDetailRead,
  type CohortRow,
} from "@/lib/schemas/analysis";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Loader,
  TriangleAlert,
  SearchX,
  Play,
  Trash2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

type SortField = "success_quote" | "lift" | "total" | "median_calmar";
type SortDir = "asc" | "desc";

interface SortState {
  field: SortField;
  dir: SortDir;
}

function SortIcon({ field, sort }: { field: SortField; sort: SortState | null }) {
  if (!sort || sort.field !== field) {
    return <ArrowUpDown className="ml-1 inline-block h-3 w-3 opacity-30" />;
  }
  return sort.dir === "asc" ? (
    <ArrowUp className="ml-1 inline-block h-3 w-3" />
  ) : (
    <ArrowDown className="ml-1 inline-block h-3 w-3" />
  );
}

function SortableHead({
  field,
  label,
  sort,
  onSort,
}: {
  field: SortField;
  label: string;
  sort: SortState | null;
  onSort: (field: SortField) => void;
}) {
  return (
    <TableHead
      className="cursor-pointer select-none whitespace-nowrap"
      onClick={() => onSort(field)}
    >
      {label}
      <SortIcon field={field} sort={sort} />
    </TableHead>
  );
}

export default function ErfolgsfaktorenPage() {
  const [runs, setRuns] = useState<AnalysisRunRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AnalysisRunDetailRead | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [axis, setAxis] = useState("indicator");
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);

  const [cohortSort, setCohortSort] = useState<SortState>({
    field: "success_quote",
    dir: "desc",
  });

  const [directionMatrix, setDirectionMatrix] = useState(false);
  const [expandedStrategies, setExpandedStrategies] = useState(false);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = z
        .array(analysisRunReadSchema)
        .parse(await apiGet<AnalysisRunRead[]>("/analysis/runs"));
      setRuns(data);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Analyseläufe konnten nicht geladen werden.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const loadDetail = useCallback(
    async (runId: string, selectedAxis: string) => {
      setDetailLoading(true);
      setDetail(null);
      try {
        const data = analysisRunDetailReadSchema.parse(
          await apiGet<AnalysisRunDetailRead>(
            `/analysis/runs/${runId}?axis=${selectedAxis}`,
          ),
        );
        setDetail(data);
      } catch (e) {
        setError(
          e instanceof ApiError
            ? e.message
            : "Laufdetails konnten nicht geladen werden.",
        );
      } finally {
        setDetailLoading(false);
      }
    },
    [],
  );

  const handleSelectRun = (runId: string) => {
    if (selectedRunId === runId) {
      setSelectedRunId(null);
      setDetail(null);
      return;
    }
    setSelectedRunId(runId);
    setExpandedStrategies(false);
    loadDetail(runId, axis);
  };

  const handleAxisChange = (newAxis: string) => {
    setAxis(newAxis);
    if (selectedRunId) {
      loadDetail(selectedRunId, newAxis);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const data = analysisRunReadSchema.parse(
        await apiPost<AnalysisRunRead>("/analysis/runs"),
      );
      setRuns((prev) => [data, ...prev]);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Analyselauf konnte nicht gestartet werden.",
      );
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (runId: string) => {
    if (!window.confirm("Diesen Analyselauf endgültig löschen?")) return;
    setDeletingRunId(runId);
    try {
      await apiDelete(`/analysis/runs/${runId}`);
      setRuns((prev) => prev.filter((r) => r.id !== runId));
      if (selectedRunId === runId) {
        setSelectedRunId(null);
        setDetail(null);
      }
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Lauf konnte nicht gelöscht werden.",
      );
    } finally {
      setDeletingRunId(null);
    }
  };

  const handleCohortSort = (field: SortField) => {
    setCohortSort((prev) => {
      if (prev.field !== field) return { field, dir: "desc" };
      return { field, dir: prev.dir === "desc" ? "asc" : "desc" };
    });
  };

  const sortedCohort = useMemo(() => {
    if (!detail) return [];
    const rows = z.array(cohortRowSchema).parse(detail.cohort);
    const dir = cohortSort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const aVal = a[cohortSort.field];
      const bVal = b[cohortSort.field];
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1;
      if (bVal === null) return -1;
      return ((aVal as number) - (bVal as number)) * dir;
    });
  }, [detail, cohortSort]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="w-full px-4 py-6">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Erfolgsfaktoren</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Gelegentliche Momentaufnahme: Welche Merkmale treten in der
            Erfolgsgruppe häufiger auf?
          </p>
        </div>
        <Button onClick={handleCreate} disabled={creating}>
          {creating ? (
            <Loader className="mr-1 h-4 w-4 animate-spin" />
          ) : (
            <Play className="mr-1 h-4 w-4" />
          )}
          Analyse jetzt fahren
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {runs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <SearchX className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              Keine Analyseläufe vorhanden. Starte den ersten Lauf über den
              Button oben.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {runs.map((run) => (
            <Card key={run.id}>
              <CardHeader
                className="cursor-pointer pb-2"
                onClick={() => handleSelectRun(run.id)}
              >
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-mono">
                    {new Date(run.created_at).toLocaleString("de-DE")}
                  </CardTitle>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>
                      Einbezogen:{" "}
                      <strong className="text-foreground">
                        {run.total_analyzed}
                      </strong>
                    </span>
                    <span>
                      Ausgeschlossen:{" "}
                      <strong className="text-foreground">
                        {run.total_excluded}
                      </strong>
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(run.id);
                      }}
                      disabled={deletingRunId === run.id}
                    >
                      {deletingRunId === run.id ? (
                        <Loader className="h-3 w-3 animate-spin" />
                      ) : (
                        <Trash2 className="h-3 w-3 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>

              {selectedRunId === run.id && detailLoading && (
                <CardContent>
                  <div className="flex items-center justify-center py-6">
                    <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                </CardContent>
              )}

              {selectedRunId === run.id && detail && (
                <CardContent>
                  <LaufDetail
                    detail={detail}
                    axis={axis}
                    onAxisChange={handleAxisChange}
                    cohortSort={cohortSort}
                    onCohortSort={handleCohortSort}
                    sortedCohort={sortedCohort}
                    directionMatrix={directionMatrix}
                    onDirectionMatrixToggle={() =>
                      setDirectionMatrix(!directionMatrix)
                    }
                    expandedStrategies={expandedStrategies}
                    onToggleStrategies={() =>
                      setExpandedStrategies(!expandedStrategies)
                    }
                  />
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function LaufDetail({
  detail,
  axis,
  onAxisChange,
  cohortSort,
  onCohortSort,
  sortedCohort,
  directionMatrix,
  onDirectionMatrixToggle,
  expandedStrategies,
  onToggleStrategies,
}: {
  detail: AnalysisRunDetailRead;
  axis: string;
  onAxisChange: (a: string) => void;
  cohortSort: SortState;
  onCohortSort: (f: SortField) => void;
  sortedCohort: CohortRow[];
  directionMatrix: boolean;
  onDirectionMatrixToggle: () => void;
  expandedStrategies: boolean;
  onToggleStrategies: () => void;
}) {
  const def = detail.success_definition;
  const reasons = detail.excluded_reasons;

  const directionRows = useMemo(() => {
    if (axis !== "direction" || !directionMatrix) return null;
    const rows = detail.rows;
    const directions = ["long-only", "short-only", "kombiniert"];

    const totalAll = rows.length;
    const totalSuccess = rows.filter((r) => r.is_success).length;

    return directions.map((dir) => {
      const subset = rows.filter((r) => r.direction === dir);
      const success = subset.filter((r) => r.is_success).length;
      const total = subset.length;
      const quote = total > 0 ? success / total : null;
      const calmarValues = subset
        .map((r) => r.calmar_ratio)
        .filter((c): c is number => c !== null);

      let lift = null;
      if (totalSuccess > 0 && totalAll > 0 && total > 0) {
        const successShare = success / totalSuccess;
        const totalShare = total / totalAll;
        if (totalShare > 0) lift = successShare / totalShare;
      }

      const medianCalmar =
        calmarValues.length > 0
          ? calmarValues.sort((a, b) => a - b)[
              Math.floor(calmarValues.length / 2)
            ]
          : null;

      return {
        value: dir,
        success,
        total,
        success_quote: quote,
        lift,
        median_calmar: medianCalmar,
      } as CohortRow;
    });
  }, [axis, directionMatrix, detail.rows]);

  return (
    <div className="space-y-6">
      <div className="grid gap-2 text-sm">
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <span className="text-muted-foreground">Vergleichsgruppe:</span>
          <span className="font-mono text-xs">{detail.comparison_group}</span>
        </div>
        {def && (
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            <span className="text-muted-foreground">Erfolgsdefinition:</span>
            <span className="font-mono text-xs">
              Calmar &ge; {def.calmar_min}, Sortino &ge; {def.sortino_min},
              &ge; {def.min_trades_per_year} Trades/Jahr
            </span>
          </div>
        )}
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <span className="text-muted-foreground">Einbezogen:</span>
          <span className="font-semibold text-emerald-600">
            {detail.total_analyzed}
          </span>
          <span className="text-muted-foreground">Ausgeschlossen:</span>
          <span className="font-semibold text-destructive">
            {detail.total_excluded}
          </span>
        </div>
        {Object.keys(reasons).length > 0 && (
          <div className="flex flex-wrap gap-2 mt-1">
            {Object.entries(reasons).map(([reason, count]) => (
              <Badge key={reason} variant="outline" className="text-xs">
                {reason}: {count}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Achse
          </label>
          <select
            value={axis}
            onChange={(e) => onAxisChange(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {AXIS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {axis === "direction" && (
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Matrix
            </label>
            <label className="flex items-center gap-2 h-9 cursor-pointer">
              <input
                type="checkbox"
                checked={directionMatrix}
                onChange={onDirectionMatrixToggle}
                className="h-4 w-4 rounded border-input"
              />
              <span className="text-sm">
                {directionMatrix
                  ? "Long-only / Short-only / Kombiniert"
                  : "Alle Richtungen"}
              </span>
            </label>
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Merkmal</TableHead>
              <SortableHead
                field="success_quote"
                label="Erfolgsquote"
                sort={cohortSort}
                onSort={onCohortSort}
              />
              <SortableHead
                field="lift"
                label="Lift"
                sort={cohortSort}
                onSort={onCohortSort}
              />
              <SortableHead
                field="total"
                label="Stichprobe"
                sort={cohortSort}
                onSort={onCohortSort}
              />
              <SortableHead
                field="median_calmar"
                label="Median Calmar"
                sort={cohortSort}
                onSort={onCohortSort}
              />
            </TableRow>
          </TableHeader>
          <TableBody>
            {(directionMatrix && directionRows ? directionRows : sortedCohort)
              .filter((row) => row.success > 0 || row.total > 0)
              .map((row) => (
                <CohortZeile key={row.value} row={row} />
              ))}
          </TableBody>
        </Table>
      </div>

      <div>
        <button
          onClick={onToggleStrategies}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          {expandedStrategies ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          Beteiligte Strategien ({detail.rows.length})
        </button>

        {expandedStrategies && (
          <div className="mt-3 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Strategie</TableHead>
                  <TableHead>Erfolg</TableHead>
                  <TableHead>Calmar</TableHead>
                  <TableHead>Sortino</TableHead>
                  <TableHead>Trd/J</TableHead>
                  <TableHead>Indikatoren</TableHead>
                  <TableHead>#Ind</TableHead>
                  <TableHead>#Par</TableHead>
                  <TableHead>Entry</TableHead>
                  <TableHead>Exit</TableHead>
                  <TableHead>Kat</TableHead>
                  <TableHead>Richtung</TableHead>
                  <TableHead>MTS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium max-w-[160px] truncate">
                      {r.strategy_name}
                    </TableCell>
                    <TableCell>
                      {r.is_success ? (
                        <Badge
                          variant="default"
                          className="bg-emerald-600 text-xs"
                        >
                          Ja
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">
                          Nein
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {r.calmar_ratio !== null
                        ? r.calmar_ratio.toFixed(2)
                        : "–"}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {r.sortino_ratio !== null
                        ? r.sortino_ratio.toFixed(2)
                        : "–"}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums">
                      {r.trades_per_year !== null
                        ? r.trades_per_year.toFixed(1)
                        : "–"}
                    </TableCell>
                    <TableCell className="text-xs max-w-[200px] truncate">
                      {r.indicators.length > 0
                        ? r.indicators.join(", ")
                        : "–"}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-center">
                      {r.indicator_count}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-center">
                      {r.parameter_count}
                    </TableCell>
                    <TableCell className="text-xs">
                      <Badge variant="outline" className="text-xs">
                        {r.entry_archetype}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      <Badge variant="outline" className="text-xs">
                        {r.exit_archetype}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      {r.category ?? "–"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {r.direction ?? "–"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {r.mts_compatibility ?? "–"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}

function CohortZeile({ row }: { row: CohortRow }) {
  const quotePct = row.success_quote !== null ? row.success_quote * 100 : 0;

  return (
    <TableRow>
      <TableCell className="font-medium">{row.value}</TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-1">
              <span className="font-mono text-xs tabular-nums">
                {row.success_quote !== null
                  ? `${quotePct.toFixed(0)}%`
                  : "nicht verfügbar"}
              </span>
              <span className="text-xs text-muted-foreground">
                ({row.success}/{row.total})
              </span>
            </div>
            <div className="mt-0.5 h-1.5 w-full rounded-full bg-muted">
              <div
                className="h-1.5 rounded-full bg-emerald-500"
                style={{ width: `${Math.min(quotePct, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </TableCell>
      <TableCell className="font-mono text-xs tabular-nums">
        {row.lift !== null ? row.lift.toFixed(2) : "nicht verfügbar"}
      </TableCell>
      <TableCell className="font-mono text-xs tabular-nums">
        {row.total}
      </TableCell>
      <TableCell className="font-mono text-xs tabular-nums">
        {row.median_calmar !== null
          ? row.median_calmar.toFixed(2)
          : "nicht verfügbar"}
      </TableCell>
    </TableRow>
  );
}
