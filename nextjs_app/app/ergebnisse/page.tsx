"use client";

import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { apiDelete, apiGet, apiPost, apiPostJson, apiUrl, ApiError } from "@/lib/api-client";
import {
  resultRowSchema,
  RESULT_TYPE_LABELS,
  DIRECTION_MODE_LABELS,
  STATUS_LABELS,
  CATEGORIES,
  type ResultRow,
} from "@/lib/schemas/results";
import {
  regimeEvaluationReadSchema,
  resultTradeReadSchema,
  fetchTradesResponseSchema,
  REGIME_LABELS,
  REGIME_BADGE_VARIANT,
  type RegimeEvaluationRead,
  type ResultTradeRead,
} from "@/lib/schemas/regime";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Card,
  CardContent,
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
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  Loader,
  TriangleAlert,
  SearchX,
  RotateCcw,
  SlidersHorizontal,
  Trash2,
  Star,
  Info,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";

type SortDir = "asc" | "desc" | null;

interface SortState {
  field: string;
  dir: Exclude<SortDir, null>;
}

const METRIC_FIELDS = [
  "net_profit_pct",
  "cagr_pct",
  "trade_count",
  "trades_per_year",
  "max_drawdown_pct",
  "sharpe_ratio",
  "sortino_ratio",
  "profit_factor",
  "calmar_ratio",
] as const;

const STATUS_BADGE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  erfolgreich: "default",
  fehlgeschlagen: "destructive",
  abgebrochen: "outline",
  geplant: "secondary",
  bestätigt: "secondary",
  in_queue: "secondary",
  läuft: "secondary",
};

function SortIcon({ field, sort }: { field: string; sort: SortState | null }) {
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
  field: string;
  label: string;
  sort: SortState | null;
  onSort: (field: string) => void;
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

export default function ErgebnissePage() {
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);
  const [retryingRunId, setRetryingRunId] = useState<string | null>(null);

  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterStrategy, setFilterStrategy] = useState("");
  const [filterInstrument, setFilterInstrument] = useState("");
  const [filterVersion, setFilterVersion] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterTimeframe, setFilterTimeframe] = useState("");
  const [filterDirection, setFilterDirection] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterResultType, setFilterResultType] = useState("");
  const [filterMtsCompatibility, setFilterMtsCompatibility] = useState("");
  const [filterRobustnessStatus, setFilterRobustnessStatus] = useState("");
  const [filterSuccessGroup, setFilterSuccessGroup] = useState(false);
  const [filterShortlisted, setFilterShortlisted] = useState(false);

  const [sort, setSort] = useState<SortState>({ field: "calmar_ratio", dir: "desc" });

  const [togglingStar, setTogglingStar] = useState<string | null>(null);

  const [regimePanelResultId, setRegimePanelResultId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = z
          .array(resultRowSchema)
          .parse(await apiGet<ResultRow[]>("/results"));
        setRows(data);
      } catch (e) {
        setError(
          e instanceof ApiError ? e.message : "Ergebnisse konnten nicht geladen werden.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const uniqueValues = useMemo(() => {
    const strategies = new Set<string>();
    const versions = new Set<number>();
    const instruments = new Set<string>();
    const directions = new Set<string>();
    const statuses = new Set<string>();
    const resultTypes = new Set<string>();
    const timeframes = new Set<string>();
    const mtsCompatibilities = new Set<string>();
    const robustnessStatuses = new Set<string>();
    for (const r of rows) {
      strategies.add(r.strategy_name);
      if (r.strategy_version_number !== null)
        versions.add(r.strategy_version_number);
      instruments.add(r.instrument);
      if (r.direction) directions.add(r.direction);
      if (r.status) statuses.add(r.status);
      resultTypes.add(r.result_type);
      if (r.timeframe) timeframes.add(r.timeframe);
      if (r.mts_compatibility) mtsCompatibilities.add(r.mts_compatibility);
      if (r.robustness_status) robustnessStatuses.add(r.robustness_status);
    }
    return {
      strategies, versions, instruments, directions, statuses, resultTypes,
      timeframes, mtsCompatibilities, robustnessStatuses,
    };
  }, [rows]);

  const filtered = useMemo(() => {
    let result = rows;
    if (filterStrategy)
      result = result.filter((r) => r.strategy_name === filterStrategy);
    if (filterVersion)
      result = result.filter((r) => r.strategy_version_number === Number(filterVersion));
    if (filterInstrument)
      result = result.filter((r) => r.instrument === filterInstrument);
    if (filterCategory)
      result = result.filter((r) => r.category === filterCategory);
    if (filterDirection)
      result = result.filter((r) => r.direction === filterDirection);
    if (filterStatus)
      result = result.filter((r) => r.status === filterStatus);
    if (filterResultType)
      result = result.filter((r) => r.result_type === filterResultType);
    if (filterTimeframe)
      result = result.filter((r) => r.timeframe === filterTimeframe);
    if (filterMtsCompatibility)
      result = result.filter((r) => r.mts_compatibility === filterMtsCompatibility);
    if (filterRobustnessStatus)
      result = result.filter((r) => r.robustness_status === filterRobustnessStatus);
    if (filterSuccessGroup)
      result = result.filter((r) => r.success_group);
    if (filterShortlisted)
      result = result.filter((r) => r.shortlisted);
    return result;
  }, [
    rows, filterStrategy, filterVersion, filterInstrument, filterCategory,
    filterDirection, filterStatus, filterResultType, filterTimeframe,
    filterMtsCompatibility, filterRobustnessStatus, filterSuccessGroup, filterShortlisted,
  ]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sort.field];
      const bVal = (b as Record<string, unknown>)[sort.field];
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1;
      if (bVal === null) return -1;
      return ((aVal as number) - (bVal as number)) * dir;
    });
  }, [filtered, sort]);

  const profileFamilies = useMemo(() => {
    const families = new Map<string, ResultRow[]>();
    for (const r of sorted) {
      if (r.result_type === "HAL-Import") {
        const key = `hal-${r.profile_name ?? "nicht-vergleichbar"}`;
        if (!families.has(key)) families.set(key, []);
        families.get(key)!.push(r);
      } else {
        const key = r.profile_family_id ?? `unknown-${r.run_id}`;
        if (!families.has(key)) families.set(key, []);
        families.get(key)!.push(r);
      }
    }
    return [...families.entries()];
  }, [sorted]);

  const hasMultipleProfiles = profileFamilies.length > 1;

  const handleSort = (field: string) => {
    setSort((prev) => {
      if (!prev || prev.field !== field) return { field, dir: "desc" };
      if (prev.dir === "desc") return { field, dir: "asc" };
      return { field, dir: "desc" };
    });
  };

  const clearFilters = () => {
    setFilterStrategy("");
    setFilterVersion("");
    setFilterInstrument("");
    setFilterCategory("");
    setFilterDirection("");
    setFilterStatus("");
    setFilterResultType("");
    setFilterTimeframe("");
    setFilterMtsCompatibility("");
    setFilterRobustnessStatus("");
    setFilterSuccessGroup(false);
    setFilterShortlisted(false);
  };

  const handleDelete = async (runId: string) => {
    if (!window.confirm("Diesen Run endgültig löschen?")) return;
    setDeletingRunId(runId);
    try {
      await apiDelete(`/runs/${runId}`);
      setRows((prev) => prev.filter((row) => row.run_id !== runId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Run konnte nicht gelöscht werden.");
    } finally {
      setDeletingRunId(null);
    }
  };

  const handleRetry = async (runId: string) => {
    setRetryingRunId(runId);
    setError(null);
    try {
      const check = z
        .object({ ok: z.boolean(), reason: z.string().nullable().optional() })
        .parse(await apiGet(`/runs/${runId}/retry-credit-check`));
      if (!check.ok) {
        setError(check.reason ?? "Wiederholung ist nicht möglich.");
        return;
      }
      await apiPost(`/runs/${runId}/retry`);
      setRows(
        z.array(resultRowSchema).parse(await apiGet<ResultRow[]>("/results")),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Run konnte nicht wiederholt werden.");
    } finally {
      setRetryingRunId(null);
    }
  };

  const handleStarToggle = async (strategyId: string, currentlyShortlisted: boolean) => {
    setTogglingStar(strategyId);
    try {
      if (currentlyShortlisted) {
        await fetch(apiUrl(`/shortlist/${strategyId}`), { method: "DELETE" });
      } else {
        await fetch(apiUrl(`/shortlist/${strategyId}`), { method: "PUT" });
      }
      setRows(
        z.array(resultRowSchema).parse(await apiGet<ResultRow[]>("/results")),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Shortlist-Änderung fehlgeschlagen.");
    } finally {
      setTogglingStar(null);
    }
  };

  const hasFilters =
    filterStrategy || filterVersion || filterInstrument || filterCategory ||
    filterDirection || filterStatus || filterResultType || filterTimeframe ||
    filterMtsCompatibility || filterRobustnessStatus || filterSuccessGroup || filterShortlisted;

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
          <h1 className="text-xl font-semibold">Ergebnisvergleich</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {sorted.length} Ergebnis{sorted.length !== 1 ? "se" : ""} gefunden
            {sort && ` — sortiert nach ${_metricLabel(sort.field)} ${sort.dir === "asc" ? "▲" : "▼"}`}
          </p>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filterleiste */}
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setFiltersOpen(!filtersOpen)}
        >
          <SlidersHorizontal className="mr-1 h-4 w-4" />
          Filter {hasFilters ? `(${filtered.length})` : ""}
          {filtersOpen ? "▲" : "▼"}
        </Button>

        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Filter zurücksetzen
          </Button>
        )}
      </div>

      {/* Filter-Bereich */}
      {filtersOpen && (
        <Card className="mb-6">
          <CardContent className="grid gap-4 pt-6 sm:grid-cols-2 lg:grid-cols-3">
            <SelectFilter
              label="Strategie"
              value={filterStrategy}
              options={[...uniqueValues.strategies].sort()}
              onChange={setFilterStrategy}
              placeholder="Alle Strategien"
            />
            <SelectFilter
              label="Version"
              value={filterVersion}
              options={[...uniqueValues.versions].sort((a, b) => a - b).map(String)}
              onChange={setFilterVersion}
              placeholder="Alle Versionen"
              renderOption={(v) => `v${v}`}
            />
            <SelectFilter
              label="Instrument"
              value={filterInstrument}
              options={[...uniqueValues.instruments].sort()}
              onChange={setFilterInstrument}
              placeholder="Alle Instrumente"
            />
            <SelectFilter
              label="Kategorie"
              value={filterCategory}
              options={[...CATEGORIES]}
              onChange={setFilterCategory}
              placeholder="Alle Kategorien"
            />
            <SelectFilter
              label="Richtung"
              value={filterDirection}
              options={[...uniqueValues.directions].sort()}
              onChange={setFilterDirection}
              placeholder="Alle Richtungen"
              renderOption={(v) => DIRECTION_MODE_LABELS[v] ?? v}
            />
            <SelectFilter
              label="Status"
              value={filterStatus}
              options={[...uniqueValues.statuses].sort()}
              onChange={setFilterStatus}
              placeholder="Alle Status"
              renderOption={(v) => STATUS_LABELS[v] ?? v}
            />
            <SelectFilter
              label="Ergebnisart"
              value={filterResultType}
              options={[...uniqueValues.resultTypes].sort()}
              onChange={setFilterResultType}
              placeholder="Alle Ergebnisarten"
              renderOption={(v) => RESULT_TYPE_LABELS[v] ?? v}
            />
            <SelectFilter
              label="Timeframe"
              value={filterTimeframe}
              options={[...uniqueValues.timeframes].sort()}
              onChange={setFilterTimeframe}
              placeholder="Alle Timeframes"
            />
            <SelectFilter
              label="MTS-Eignung"
              value={filterMtsCompatibility}
              options={[...uniqueValues.mtsCompatibilities].sort()}
              onChange={setFilterMtsCompatibility}
              placeholder="Alle MTS-Eignungen"
            />
            <SelectFilter
              label="Robustheitsstatus"
              value={filterRobustnessStatus}
              options={[...uniqueValues.robustnessStatuses].sort()}
              onChange={setFilterRobustnessStatus}
              placeholder="Alle Robustheitsstatus"
            />
            <CheckboxFilter
              label="Erfolgsgruppe"
              checked={filterSuccessGroup}
              onChange={setFilterSuccessGroup}
            />
            <CheckboxFilter
              label="Shortlist"
              checked={filterShortlisted}
              onChange={setFilterShortlisted}
            />
          </CardContent>
        </Card>
      )}

      {/* Profil-Warnung */}
      {hasMultipleProfiles && (
        <Alert className="mb-6">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>
            Mehrere Backtest-Profilversionen oder HAL-Importe vorhanden. Jede
            Gruppe wird separat dargestellt. Ergebnisse mit unterschiedlichen
            Gebühren-, Slippage- oder Sizing-Profilen sind nicht direkt
            vergleichbar.
          </AlertDescription>
        </Alert>
      )}

      {/* Leerer Zustand */}
      {profileFamilies.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <SearchX className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              {rows.length === 0
                ? "Keine Ergebnisse vorhanden. Bestätige einen Batch oder importiere HAL-Dateien."
                : "Keine Ergebnisse für diese Filterkombination."}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Ergebnisgruppen */}
      {profileFamilies.map(([familyId, group]) => (
        <ErgebnisGruppe
          key={familyId}
          rows={group}
          groupLabel={
            familyId.startsWith("hal-")
              ? `HAL-Importe · ${group[0].profile_name ?? "Nicht vergleichbar"}`
              : `Profil: ${group[0].profile_name ?? "Unbekannt"} (v${group[0].profile_version_number ?? "?"})`
          }
          sort={sort}
          onSort={handleSort}
          isHighlighted={hasMultipleProfiles}
          deletingRunId={deletingRunId}
          retryingRunId={retryingRunId}
          togglingStar={togglingStar}
          onDelete={handleDelete}
          onRetry={handleRetry}
          onStarToggle={handleStarToggle}
          onOpenRegimePanel={setRegimePanelResultId}
        />
      ))}

      <RegimePanel
        resultId={regimePanelResultId}
        onClose={() => setRegimePanelResultId(null)}
      />
    </div>
  );
}

function SelectFilter({
  label,
  value,
  options,
  onChange,
  placeholder,
  renderOption,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  placeholder: string;
  renderOption?: (v: string) => string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs font-medium">{label}</Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {renderOption ? renderOption(opt) : opt}
          </option>
        ))}
      </select>
    </div>
  );
}

function CheckboxFilter({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs font-medium">{label}</Label>
      <label className="flex items-center gap-2 h-9 cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-input"
        />
        <span className="text-sm">{checked ? "Aktiv" : "Inaktiv"}</span>
      </label>
    </div>
  );
}

function ErgebnisGruppe({
  rows,
  groupLabel,
  sort,
  onSort,
  isHighlighted,
  deletingRunId,
  retryingRunId,
  togglingStar,
  onDelete,
  onRetry,
  onStarToggle,
  onOpenRegimePanel,
}: {
  rows: ResultRow[];
  groupLabel: string;
  sort: SortState | null;
  onSort: (field: string) => void;
  isHighlighted: boolean;
  deletingRunId: string | null;
  retryingRunId: string | null;
  togglingStar: string | null;
  onDelete: (runId: string) => void;
  onRetry: (runId: string) => void;
  onStarToggle: (strategyId: string, currentlyShortlisted: boolean) => void;
  onOpenRegimePanel: (resultId: string) => void;
}) {
  const isHalGroup = rows[0]?.result_type === "HAL-Import";

  return (
    <Card className={`mb-6 ${isHighlighted ? "border-amber-200 dark:border-amber-800" : ""}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{groupLabel}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>Strategie</TableHead>
              <TableHead>Version</TableHead>
              <TableHead className="hidden sm:table-cell">Kategorie</TableHead>
              <TableHead>Instrument</TableHead>
              <TableHead className="hidden md:table-cell">Richtung</TableHead>
              <TableHead className="hidden md:table-cell">Art</TableHead>
              {!isHalGroup && <TableHead>Status</TableHead>}
              <TableHead className="hidden lg:table-cell">Zeitraum</TableHead>
              <SortableHead field="net_profit_pct" label="Net Return" sort={sort} onSort={onSort} />
              <SortableHead field="cagr_pct" label="CAGR" sort={sort} onSort={onSort} />
              <SortableHead field="trade_count" label="Trades" sort={sort} onSort={onSort} />
              <SortableHead field="trades_per_year" label="Trd/J" sort={sort} onSort={onSort} />
              <SortableHead field="max_drawdown_pct" label="Max DD" sort={sort} onSort={onSort} />
              <SortableHead field="sharpe_ratio" label="Sharpe" sort={sort} onSort={onSort} />
              <SortableHead field="sortino_ratio" label="Sortino" sort={sort} onSort={onSort} />
              <SortableHead field="profit_factor" label="PF" sort={sort} onSort={onSort} />
              <SortableHead field="calmar_ratio" label="Calmar" sort={sort} onSort={onSort} />
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <ErgebnisZeile
                key={r.run_id}
                row={r}
                isHalGroup={isHalGroup}
                deletingRunId={deletingRunId}
                retryingRunId={retryingRunId}
                togglingStar={togglingStar}
                onDelete={onDelete}
                onRetry={onRetry}
                onStarToggle={onStarToggle}
                onOpenRegimePanel={onOpenRegimePanel}
              />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ErgebnisZeile({
  row,
  isHalGroup,
  deletingRunId,
  retryingRunId,
  togglingStar,
  onDelete,
  onRetry,
  onStarToggle,
  onOpenRegimePanel,
}: {
  row: ResultRow;
  isHalGroup: boolean;
  deletingRunId: string | null;
  retryingRunId: string | null;
  togglingStar: string | null;
  onDelete: (runId: string) => void;
  onRetry: (runId: string) => void;
  onStarToggle: (strategyId: string, currentlyShortlisted: boolean) => void;
  onOpenRegimePanel: (resultId: string) => void;
}) {
  const hasReport = !!row.report_link;
  const canStar = !!row.strategy_id;
  const isHalImport = row.result_type === "HAL-Import";

  return (
    <TableRow>
      <TableCell>
        {canStar ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => onStarToggle(row.strategy_id!, row.shortlisted)}
            disabled={togglingStar === row.strategy_id}
          >
            {togglingStar === row.strategy_id ? (
              <Loader className="h-3 w-3 animate-spin" />
            ) : (
              <Star
                className={`h-4 w-4 ${
                  row.shortlisted
                    ? "fill-amber-400 text-amber-400"
                    : "text-muted-foreground/30"
                }`}
              />
            )}
          </Button>
        ) : (
          <Star className="h-4 w-4 text-muted-foreground/20" />
        )}
      </TableCell>
      <TableCell className="font-medium">
        <div className="max-w-[160px] truncate">{row.strategy_name}</div>
      </TableCell>
      <TableCell className="font-mono text-xs">
        {row.strategy_version_number !== null ? `v${row.strategy_version_number}` : "–"}
      </TableCell>
      <TableCell className="hidden sm:table-cell">
        {row.category ? (
          <Badge variant="outline" className="text-xs">{row.category}</Badge>
        ) : (
          <span className="text-xs text-muted-foreground">–</span>
        )}
      </TableCell>
      <TableCell className="font-mono text-xs">{row.instrument}</TableCell>
      <TableCell className="hidden md:table-cell">
        {row.direction ? (DIRECTION_MODE_LABELS[row.direction] ?? row.direction) : "–"}
      </TableCell>
      <TableCell className="hidden md:table-cell">
        <Badge variant="secondary" className="text-xs">
          {RESULT_TYPE_LABELS[row.result_type] ?? row.result_type}
        </Badge>
      </TableCell>
      {!isHalGroup && (
        <TableCell>
          {row.status ? (
            <Badge
              variant={STATUS_BADGE_VARIANT[row.status] ?? "outline"}
              className="text-xs"
            >
              {STATUS_LABELS[row.status] ?? row.status}
            </Badge>
          ) : "–"}
        </TableCell>
      )}
      <TableCell className="hidden lg:table-cell text-xs text-muted-foreground">
        {row.period_start}
        {row.period_end ? ` – ${row.period_end}` : " – offen"}
      </TableCell>

      {METRIC_FIELDS.map((field) => {
        const val = row[field] as number | null;
        const isNull = val === null || val === undefined;
        let display: string;
        if (isNull) {
          display = "–";
        } else if (["net_profit_pct", "cagr_pct", "max_drawdown_pct"].includes(field)) {
          display = val.toFixed(1) + "%";
        } else if (["trade_count"].includes(field)) {
          display = val.toFixed(0);
        } else if (["trades_per_year"].includes(field)) {
          display = val.toFixed(1);
        } else {
          display = val.toFixed(2);
        }
        const isCalmar = field === "calmar_ratio";
        return (
          <TableCell
            key={field}
            className={`font-mono text-xs tabular-nums ${isNull ? "text-muted-foreground italic" : ""} ${isCalmar && !isNull ? "font-semibold" : ""}`}
          >
            {display}
          </TableCell>
        );
      })}

      <TableCell>
        <div className="flex items-center gap-1 flex-wrap">
          {row.result_type === "HAL-Import" && row.import_origin_path && (
            <HerkunftsPopover row={row} />
          )}
          {row.result_type === "HAL-Import" && row.strategy_version_status && (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Badge variant="destructive" className="text-xs">
                  Version nicht verfügbar
                  </Badge>
                }
              />
              <TooltipContent>
                {row.strategy_version_status}
              </TooltipContent>
            </Tooltip>
          )}
          {row.low_activity && (
            <Badge variant="outline" className="text-xs text-amber-600 border-amber-300">
              Niedrige Aktivität
            </Badge>
          )}
          {row.incomplete && (
            <Badge variant="outline" className="text-xs text-orange-600 border-orange-300">
              Unvollständig
            </Badge>
          )}
          {!row.is_comparable && (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Badge variant="outline" className="text-xs text-gray-500 border-gray-300">
                  Nicht vergleichbar
                  </Badge>
                }
              />
              <TooltipContent>
                Gebühren, Slippage oder Sizing-Modell fehlen oder weichen ab.
              </TooltipContent>
            </Tooltip>
          )}
          {row.success_group && (
            <Badge variant="default" className="text-xs bg-emerald-600">
              Erfolgsgruppe
            </Badge>
          )}
          {isHalImport && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenRegimePanel(row.run_id)}
            >
              <TrendingUp className="mr-1 h-3 w-3" />
              Regime
            </Button>
          )}
          {hasReport && (
            <a
              href={row.report_link!}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-1 inline-flex items-center text-muted-foreground hover:text-foreground"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          {!isHalGroup && row.status === "fehlgeschlagen" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRetry(row.run_id)}
              disabled={retryingRunId === row.run_id || deletingRunId === row.run_id}
            >
              {retryingRunId === row.run_id ? (
                <Loader className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <RotateCcw className="mr-1 h-3 w-3" />
              )}
              Wiederholen
            </Button>
          )}
          {!isHalGroup && row.status !== "läuft" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(row.run_id)}
              disabled={deletingRunId === row.run_id || retryingRunId === row.run_id}
            >
              {deletingRunId === row.run_id ? <Loader className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}

function HerkunftsPopover({ row }: { row: ResultRow }) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
          <Info className="h-3 w-3 text-muted-foreground" />
          </Button>
        }
      />
      <TooltipContent side="left" className="max-w-[300px] text-xs">
        <div className="space-y-1">
          <p>
            <strong>Herkunft:</strong> {row.import_origin_path}
          </p>
          <p className="font-mono text-[10px] text-muted-foreground">
            Hash: {row.import_hash?.slice(0, 12)}...
          </p>
          {row.import_version !== null && (
            <p>
              <strong>Version:</strong> {row.import_version}
            </p>
          )}
          {row.import_created_at && (
            <p>
              <strong>Importiert:</strong>{" "}
              {new Date(row.import_created_at).toLocaleString("de-DE")}
            </p>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function RegimePanel({
  resultId,
  onClose,
}: {
  resultId: string | null;
  onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<RegimeEvaluationRead | null>(null);
  const [trades, setTrades] = useState<ResultTradeRead[]>([]);
  const [tradesLoading, setTradesLoading] = useState(false);
  const [fetchingTrades, setFetchingTrades] = useState(false);

  useEffect(() => {
    if (!resultId) return;
    setLoading(true);
    setError(null);
    setEvaluation(null);
    setTrades([]);

    (async () => {
      try {
        const t = z
          .array(resultTradeReadSchema)
          .parse(await apiGet<ResultTradeRead[]>(`/regime/hal-results/${resultId}/trades`));
        setTrades(t);

        if (t.length === 0) {
          setLoading(false);
          return;
        }

        try {
          const ev = regimeEvaluationReadSchema.parse(
            await apiGet<RegimeEvaluationRead>(`/regime/hal-results/${resultId}/regime`),
          );
          setEvaluation(ev);
        } catch (e) {
          setError(
            e instanceof ApiError ? e.message : "Regime-Auswertung nicht möglich.",
          );
        }
      } catch (e) {
        setError(
          e instanceof ApiError ? e.message : "Trades konnten nicht geladen werden.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [resultId]);

  const handleFetchTrades = async () => {
    if (!resultId) return;
    setFetchingTrades(true);
    setError(null);
    try {
      const resp = fetchTradesResponseSchema.parse(
        await apiPostJson(`/regime/hal-results/${resultId}/trades/fetch`, {}),
      );

      const t = z
        .array(resultTradeReadSchema)
        .parse(await apiGet<ResultTradeRead[]>(`/regime/hal-results/${resultId}/trades`));
      setTrades(t);

      if (t.length > 0 && resp.trades_count > 0) {
        try {
          const ev = regimeEvaluationReadSchema.parse(
            await apiGet<RegimeEvaluationRead>(`/regime/hal-results/${resultId}/regime`),
          );
          setEvaluation(ev);
        } catch {
          // evaluation will load or show an error
        }
      }
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Trades konnten nicht geladen werden.",
      );
    } finally {
      setFetchingTrades(false);
    }
  };

  return (
    <Sheet open={resultId !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="sm:max-w-xl w-full overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Regime-Auswertung</SheetTitle>
          <SheetDescription>
            Performance je Marktregime (Bullish, Bearish, Seitwärts)
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <TriangleAlert aria-hidden="true" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!loading && trades.length === 0 && !error && (
            <div className="space-y-4">
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Regime-Auswertung nicht möglich: Zeitgestempelte Ergebnisdaten fehlen.
                  Lade zuerst die Trades vom trader.dev-Report.
                </AlertDescription>
              </Alert>
              <Button
                variant="default"
                onClick={handleFetchTrades}
                disabled={fetchingTrades}
                className="w-full"
              >
                {fetchingTrades && <Loader className="mr-1 h-3 w-3 animate-spin" />}
                Trades vom trader.dev laden
              </Button>
            </div>
          )}

          {!loading && trades.length > 0 && !evaluation && !error && (
            <div className="flex items-center justify-center py-8">
              <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {evaluation && (
            <div className="space-y-4">
              <Card>
                <CardContent className="pt-4 space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Modellversion:</span>
                    <Badge variant="outline">{evaluation.model_version_name ?? "–"}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Zuordnungsregel:</span>
                    <span className="font-mono text-xs">{evaluation.assignment_rule}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Abdeckung:</span>
                    <span>{evaluation.coverage_pct.toFixed(1)}%</span>
                    {evaluation.is_incomplete && (
                      <Badge variant="destructive" className="text-xs">Unvollständig</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">Gesamt-P&L:</span>
                    <span className="font-mono text-xs">
                      {evaluation.total_result_pnl.toFixed(2)}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {evaluation.regime_dominance && (
                <Alert>
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <AlertDescription>
                    Regime-Dominanz: <strong>{REGIME_LABELS[evaluation.regime_dominance] ?? evaluation.regime_dominance}</strong> liefert
                    mehr als 70 % der positiven Beiträge. Der Gesamterfolg hängt stark
                    von dieser einen Marktphase ab.
                  </AlertDescription>
                </Alert>
              )}

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Regime</TableHead>
                    <TableHead>Trades</TableHead>
                    <TableHead>Netto-P&L</TableHead>
                    <TableHead>Max DD</TableHead>
                    <TableHead>Anteil</TableHead>
                    <TableHead>Calmar</TableHead>
                    <TableHead>Sortino</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {evaluation.regime_details.map((d) => (
                    <TableRow key={d.regime}>
                      <TableCell>
                        <Badge variant={REGIME_BADGE_VARIANT[d.regime] ?? "outline"} className="text-xs">
                          {REGIME_LABELS[d.regime] ?? d.regime}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {d.trade_count}
                        {d.small_sample && (
                          <Badge variant="outline" className="ml-1 text-xs text-amber-600 border-amber-300">
                            Kleine Stichprobe
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className={`font-mono text-xs ${d.net_pnl >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                        {d.net_pnl.toFixed(2)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {d.max_drawdown_pct !== null ? `${d.max_drawdown_pct.toFixed(1)}%` : "–"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {d.pnl_share_pct.toFixed(1)}%
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {d.calmar_ratio !== null ? d.calmar_ratio.toFixed(2) : "–"}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {d.sortino_ratio !== null ? d.sortino_ratio.toFixed(2) : "–"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <Button
                variant="outline"
                size="sm"
                onClick={handleFetchTrades}
                disabled={fetchingTrades}
              >
                {fetchingTrades && <Loader className="mr-1 h-3 w-3 animate-spin" />}
                Trades neu laden
              </Button>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function _metricLabel(field: string): string {
  const labels: Record<string, string> = {
    net_profit_pct: "Net Return",
    cagr_pct: "CAGR",
    trade_count: "Trades",
    trades_per_year: "Trades/Jahr",
    max_drawdown_pct: "Max DD",
    sharpe_ratio: "Sharpe",
    sortino_ratio: "Sortino",
    profit_factor: "PF",
    calmar_ratio: "Calmar",
  };
  return labels[field] ?? field;
}
