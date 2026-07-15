"use client";

import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { apiGet, ApiError } from "@/lib/api-client";
import {
  resultRowSchema,
  RESULT_TYPE_LABELS,
  DIRECTION_MODE_LABELS,
  STATUS_LABELS,
  CATEGORIES,
  type ResultRow,
} from "@/lib/schemas/results";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
  ArrowLeft,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  Loader,
  TriangleAlert,
  SearchX,
  SlidersHorizontal,
} from "lucide-react";
import { useRouter } from "next/navigation";

type SortDir = "asc" | "desc" | null;

interface SortState {
  field: string;
  dir: Exclude<SortDir, null>;
}

const METRIC_FIELDS = [
  "net_profit_pct",
  "cagr_pct",
  "trade_count",
  "max_drawdown_pct",
  "sharpe_ratio",
  "profit_factor",
  "calmar_ratio",
] as const;

const METRIC_LABELS: Record<string, string> = {
  net_profit_pct: "Net Return %",
  cagr_pct: "CAGR %",
  trade_count: "Trades",
  max_drawdown_pct: "Max DD %",
  sharpe_ratio: "Sharpe",
  profit_factor: "PF",
  calmar_ratio: "Calmar",
};

const DEFAULT_THRESHOLD = 24;

const STATUS_BADGE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  erfolgreich: "default",
  fehlgeschlagen: "destructive",
  abgebrochen: "outline",
  geplant: "secondary",
  bestätigt: "secondary",
  in_queue: "secondary",
  läuft: "secondary",
};

function SortIcon({
  field,
  sort,
}: {
  field: string;
  sort: SortState | null;
}) {
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
  const router = useRouter();

  const [rows, setRows] = useState<ResultRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterStrategy, setFilterStrategy] = useState("");
  const [filterInstrument, setFilterInstrument] = useState("");
  const [filterVersion, setFilterVersion] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterDirection, setFilterDirection] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterResultType, setFilterResultType] = useState("");

  const [sort, setSort] = useState<SortState | null>(null);
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);

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
    for (const r of rows) {
      strategies.add(r.strategy_name);
      versions.add(r.strategy_version_number);
      instruments.add(r.instrument);
      directions.add(r.direction);
      statuses.add(r.status);
      resultTypes.add(r.result_type);
    }
    return { strategies, versions, instruments, directions, statuses, resultTypes };
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
    return result;
  }, [rows, filterStrategy, filterInstrument, filterCategory, filterDirection, filterStatus, filterResultType]);

  const sorted = useMemo(() => {
    if (!sort) return filtered;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sort.field];
      const bVal = (b as Record<string, unknown>)[sort.field];
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1; // null sorts to end
      if (bVal === null) return -1;
      return ((aVal as number) - (bVal as number)) * dir;
    });
  }, [filtered, sort]);

  const profileFamilies = useMemo(() => {
    const families = new Map<string, ResultRow[]>();
    for (const r of sorted) {
      const key = r.profile_family_id;
      if (!families.has(key)) families.set(key, []);
      families.get(key)!.push(r);
    }
    return [...families.entries()];
  }, [sorted]);

  const hasMultipleProfiles = profileFamilies.length > 1;

  const handleSort = (field: string) => {
    setSort((prev) => {
      if (!prev || prev.field !== field) return { field, dir: "desc" };
      if (prev.dir === "desc") return { field, dir: "asc" };
      return null;
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
  };

  const hasFilters =
    filterStrategy || filterVersion || filterInstrument || filterCategory || filterDirection || filterStatus || filterResultType;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <Button
        variant="ghost"
        size="sm"
        className="mb-4"
        onClick={() => router.push("/batches")}
      >
        <ArrowLeft className="mr-1 h-4 w-4" />
        Zurück zu Batches
      </Button>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Ergebnisvergleich</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {sorted.length} Run{sorted.length !== 1 ? "s" : ""} gefunden — Metriken,
            Report-Links und Aktivitätskennzeichnung.
          </p>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Aktivitätsschwelle */}
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Label htmlFor="threshold" className="text-sm whitespace-nowrap">
            Aktivitätsschwelle (Trades)
          </Label>
          <Input
            id="threshold"
            type="number"
            min={0}
            value={threshold}
            onChange={(e) => setThreshold(Math.max(0, Number(e.target.value) || 0))}
            className="w-20 h-8 font-mono text-sm"
          />
        </div>

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
          </CardContent>
        </Card>
      )}

      {/* Profil-Warnung */}
      {hasMultipleProfiles && (
        <Alert className="mb-6">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>
            Mehrere Backtest-Profilversionen vorhanden. Runs aus unterschiedlichen
            Profilgruppen sind nicht direkt vergleichbar. Jede Profilgruppe wird
            separat dargestellt.
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
                ? "Keine Runs vorhanden. Bestätige einen Batch, um Ergebnisse zu erhalten."
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
          groupLabel={`Profil: ${group[0].profile_name} (v${group[0].profile_version_number})`}
          sort={sort}
          onSort={handleSort}
          threshold={threshold}
          isHighlighted={hasMultipleProfiles}
        />
      ))}
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

function ErgebnisGruppe({
  rows,
  groupLabel,
  sort,
  onSort,
  threshold,
  isHighlighted,
}: {
  rows: ResultRow[];
  groupLabel: string;
  sort: SortState | null;
  onSort: (field: string) => void;
  threshold: number;
  isHighlighted: boolean;
}) {
  const activeThreshold = threshold;

  return (
    <Card className={`mb-6 ${isHighlighted ? "border-amber-200 dark:border-amber-800" : ""}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{groupLabel}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Strategie</TableHead>
              <TableHead>Version</TableHead>
              <TableHead className="hidden sm:table-cell">Kategorie</TableHead>
              <TableHead>Instrument</TableHead>
              <TableHead className="hidden md:table-cell">Richtung</TableHead>
              <TableHead className="hidden md:table-cell">Art</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="hidden lg:table-cell">Zeitraum</TableHead>
              <SortableHead
                field="net_profit_pct"
                label="Net Return"
                sort={sort}
                onSort={onSort}
              />
              <SortableHead
                field="cagr_pct"
                label="CAGR"
                sort={sort}
                onSort={onSort}
              />
              <SortableHead
                field="trade_count"
                label="Trades"
                sort={sort}
                onSort={onSort}
              />
              <SortableHead
                field="max_drawdown_pct"
                label="Max DD"
                sort={sort}
                onSort={onSort}
              />
              <SortableHead
                field="sharpe_ratio"
                label="Sharpe"
                sort={sort}
                onSort={onSort}
              />
              <SortableHead
                field="profit_factor"
                label="PF"
                sort={sort}
                onSort={onSort}
              />
              <SortableHead
                field="calmar_ratio"
                label="Calmar"
                sort={sort}
                onSort={onSort}
              />
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <ErgebnisZeile key={r.run_id} row={r} threshold={activeThreshold} />
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ErgebnisZeile({
  row,
  threshold,
}: {
  row: ResultRow;
  threshold: number;
}) {
  const isLowActivity = row.trade_count !== null && row.trade_count < threshold;
  const hasReport = !!row.report_link;
  const isCompleted = ["erfolgreich", "fehlgeschlagen", "abgebrochen"].includes(
    row.status,
  );
  const hasMetrics =
    row.net_profit_pct !== null || row.trade_count !== null;

  return (
    <TableRow>
      <TableCell className="font-medium">
        <div className="max-w-[160px] truncate">{row.strategy_name}</div>
      </TableCell>
      <TableCell className="font-mono text-xs">
        v{row.strategy_version_number}
      </TableCell>
      <TableCell className="hidden sm:table-cell">
        <Badge variant="outline" className="text-xs">
          {row.category}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-xs">{row.instrument}</TableCell>
      <TableCell className="hidden md:table-cell">
        {DIRECTION_MODE_LABELS[row.direction] ?? row.direction}
      </TableCell>
      <TableCell className="hidden md:table-cell">
        <Badge variant="secondary" className="text-xs">
          {RESULT_TYPE_LABELS[row.result_type] ?? row.result_type}
        </Badge>
      </TableCell>
      <TableCell>
        <Badge
          variant={STATUS_BADGE_VARIANT[row.status] ?? "outline"}
          className="text-xs"
        >
          {STATUS_LABELS[row.status] ?? row.status}
        </Badge>
      </TableCell>
      <TableCell className="hidden lg:table-cell text-xs text-muted-foreground">
        {row.period_start}
        {row.period_end ? ` – ${row.period_end}` : " – offen"}
      </TableCell>

      {METRIC_FIELDS.map((field) => {
        const val = row[field] as number | null;
        const isNull = val === null || val === undefined;
        return (
          <TableCell
            key={field}
            className={`font-mono text-xs tabular-nums ${isNull ? "text-muted-foreground italic" : ""}`}
          >
            {isNull
              ? "–"
              : ["net_profit_pct", "cagr_pct", "max_drawdown_pct"].includes(field)
                ? val.toFixed(1) + "%"
                : field === "trade_count"
                  ? val.toFixed(0)
                  : val.toFixed(2)}
          </TableCell>
        );
      })}

      <TableCell>
        <div className="flex items-center gap-1">
          {isLowActivity && (
            <Badge variant="outline" className="text-xs text-amber-600 border-amber-300">
              &lt;{threshold} Trades
            </Badge>
          )}
          {hasMetrics && row.incomplete && (
            <Badge variant="outline" className="text-xs text-orange-600 border-orange-300">
              Unvollständig
            </Badge>
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
        </div>
      </TableCell>
    </TableRow>
  );
}
