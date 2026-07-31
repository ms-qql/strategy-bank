"use client";

import { useCallback, useEffect, useState } from "react";
import { z } from "zod";
import { apiGet, apiPostJson, ApiError } from "@/lib/api-client";
import {
  regimeModelVersionReadSchema,
  regimeModelVersionCreateSchema,
  regimeSeriesReadSchema,
  regimeSeriesDetailReadSchema,
  ISSUE_TYPE_LABELS,
  type RegimeModelVersionRead,
  type RegimeSeriesRead,
  type RegimeSeriesDetailRead,
} from "@/lib/schemas/regime";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
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
  Loader,
  TriangleAlert,
  Plus,
  RefreshCw,
  Info,
  SearchX,
} from "lucide-react";

export default function RegimePage() {
  return (
    <div className="w-full px-4 py-6">
      <h1 className="text-xl font-semibold mb-1">Regime-Analyse</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Gemeinsame Marktregime-Zeitreihe für alle Strategien. Modellversionen
        definieren Parameter, Zeitreihen liefern die Daten.
      </p>

      <Tabs defaultValue="modelle" className="w-full">
        <TabsList>
          <TabsTrigger value="modelle">Modellversionen</TabsTrigger>
          <TabsTrigger value="zeitreihen">Zeitreihen</TabsTrigger>
        </TabsList>
        <TabsContent value="modelle" className="mt-4">
          <ModelleTab />
        </TabsContent>
        <TabsContent value="zeitreihen" className="mt-4">
          <ZeitreihenTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ModelleTab() {
  const [models, setModels] = useState<RegimeModelVersionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    name: "zscore-hma-v1",
    zscore_length: 75,
    hma_length: 2,
    confirmation_candles: 2,
    upper_threshold: 0.75,
    lower_threshold: -0.75,
  });

  const loadModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = z
        .array(regimeModelVersionReadSchema)
        .parse(await apiGet<RegimeModelVersionRead[]>("/regime/models"));
      setModels(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Modellversionen konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadModels(); }, [loadModels]);

  const handleCreate = async () => {
    setSaving(true);
    setError(null);
    try {
      const body = regimeModelVersionCreateSchema.parse({
        name: form.name,
        course_source: "close",
        zscore_length: form.zscore_length,
        hma_length: form.hma_length,
        confirmation_candles: form.confirmation_candles,
        upper_threshold: form.upper_threshold,
        lower_threshold: form.lower_threshold,
      });
      await apiPostJson("/regime/models", body);
      setShowForm(false);
      await loadModels();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Modellversion konnte nicht angelegt werden.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {models.length} Modellversion{models.length !== 1 ? "en" : ""}
        </p>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="mr-1 h-4 w-4" />
          Neue Modellversion
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Neue Modellversion</CardTitle>
            <CardDescription>
              Parameteränderung erzeugt neue, unveränderliche Version.
              Bestehende Auswertungen bleiben reproduzierbar.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Name</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="z.B. zscore-hma-v1"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Z-Score-Länge</Label>
                <Input
                  type="number"
                  min={2}
                  value={form.zscore_length}
                  onChange={(e) => setForm({ ...form, zscore_length: Number(e.target.value) })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">HMA-Länge</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.hma_length}
                  onChange={(e) => setForm({ ...form, hma_length: Number(e.target.value) })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Bestätigungskerzen</Label>
                <Input
                  type="number"
                  min={1}
                  value={form.confirmation_candles}
                  onChange={(e) => setForm({ ...form, confirmation_candles: Number(e.target.value) })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Obere Schwelle</Label>
                <Input
                  type="number"
                  step={0.01}
                  value={form.upper_threshold}
                  onChange={(e) => setForm({ ...form, upper_threshold: Number(e.target.value) })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label className="text-xs font-medium">Untere Schwelle</Label>
                <Input
                  type="number"
                  step={0.01}
                  value={form.lower_threshold}
                  onChange={(e) => setForm({ ...form, lower_threshold: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <Button onClick={handleCreate} disabled={saving}>
                {saving && <Loader className="mr-1 h-3 w-3 animate-spin" />}
                Modellversion anlegen
              </Button>
              <Button variant="ghost" onClick={() => setShowForm(false)}>
                Abbrechen
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {models.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <SearchX className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              Keine Modellversionen vorhanden. Lege die erste an, um Zeitreihen zu berechnen.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
        {models.map((m) => (
          <Card key={m.id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                {m.name}
                <Badge variant="outline" className="text-xs font-mono">
                  v{m.created_at ? new Date(m.created_at).toLocaleDateString("de-DE") : "–"}
                </Badge>
              </CardTitle>
              <CardDescription>
                Angelegt am {new Date(m.created_at).toLocaleString("de-DE")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                <span className="text-muted-foreground">Kursquelle:</span>
                <span>{m.course_source}</span>
                <span className="text-muted-foreground">Z-Score-Länge:</span>
                <span>{m.zscore_length}</span>
                <span className="text-muted-foreground">HMA-Länge:</span>
                <span>{m.hma_length}</span>
                <span className="text-muted-foreground">Bestätigungskerzen:</span>
                <span>{m.confirmation_candles}</span>
                <span className="text-muted-foreground">Obere Schwelle:</span>
                <span>{m.upper_threshold}</span>
                <span className="text-muted-foreground">Untere Schwelle:</span>
                <span>{m.lower_threshold}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ZeitreihenTab() {
  const [series, setSeries] = useState<RegimeSeriesRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterAsset, setFilterAsset] = useState("");
  const [filterTimeframe, setFilterTimeframe] = useState("");
  const [selectedSeries, setSelectedSeries] = useState<RegimeSeriesDetailRead | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const loadSeries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let path = "/regime/series";
      const params = new URLSearchParams();
      if (filterAsset) params.set("asset", filterAsset);
      if (filterTimeframe) params.set("timeframe", filterTimeframe);
      const qs = params.toString();
      if (qs) path += "?" + qs;

      const data = z
        .array(regimeSeriesReadSchema)
        .parse(await apiGet<RegimeSeriesRead[]>(path));
      setSeries(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Zeitreihen konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [filterAsset, filterTimeframe]);

  useEffect(() => { loadSeries(); }, [loadSeries]);

  const handleSelect = async (seriesId: string) => {
    setDetailLoading(true);
    setSelectedSeries(null);
    try {
      const data = regimeSeriesDetailReadSchema.parse(
        await apiGet<RegimeSeriesDetailRead>(`/regime/series/${seriesId}`),
      );
      setSelectedSeries(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Details konnten nicht geladen werden.");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleRefresh = async (seriesId: string) => {
    setRefreshingId(seriesId);
    setError(null);
    try {
      const data = regimeSeriesDetailReadSchema.parse(
        await apiPostJson(`/regime/series/${seriesId}/refresh`, {}),
      );
      setSelectedSeries(data);
      await loadSeries();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Refresh fehlgeschlagen.");
    } finally {
      setRefreshingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs font-medium">Asset</Label>
          <select
            value={filterAsset}
            onChange={(e) => setFilterAsset(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Alle</option>
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs font-medium">Timeframe</Label>
          <select
            value={filterTimeframe}
            onChange={(e) => setFilterTimeframe(e.target.value)}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">Alle</option>
            <option value="1h">1h</option>
            <option value="4h">4h</option>
            <option value="1d">1d</option>
          </select>
        </div>
      </div>

      {series.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <SearchX className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              Keine Zeitreihen vorhanden. Lege eine Modellversion an und lade Kursdaten.
            </p>
          </CardContent>
        </Card>
      )}

      {series.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Asset</TableHead>
                  <TableHead>Timeframe</TableHead>
                  <TableHead>Modellversion</TableHead>
                  <TableHead>Zeitraum</TableHead>
                  <TableHead>Bars</TableHead>
                  <TableHead>Nicht verfügbar</TableHead>
                  <TableHead>Letzter Refresh</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {series.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-mono text-xs">{s.asset}</TableCell>
                    <TableCell className="font-mono text-xs">{s.timeframe}</TableCell>
                    <TableCell>{s.model_version_name ?? "–"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {s.period_start
                        ? `${new Date(s.period_start).toLocaleDateString("de-DE")} – ${s.period_end ? new Date(s.period_end).toLocaleDateString("de-DE") : "offen"}`
                        : "–"}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{s.bar_count}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {s.unavailable_count > 0 ? (
                        <Badge variant="outline" className="text-amber-600 border-amber-300">
                          {s.unavailable_count}
                        </Badge>
                      ) : (
                        "0"
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {s.last_refreshed_at
                        ? new Date(s.last_refreshed_at).toLocaleString("de-DE")
                        : "–"}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSelect(s.id)}
                        >
                          <Info className="h-3 w-3 mr-1" />
                          Details
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRefresh(s.id)}
                          disabled={refreshingId === s.id}
                        >
                          {refreshingId === s.id ? (
                            <Loader className="h-3 w-3 animate-spin" />
                          ) : (
                            <RefreshCw className="h-3 w-3 mr-1" />
                          )}
                          Refresh
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {detailLoading && (
        <div className="flex items-center justify-center py-4">
          <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      )}

      {selectedSeries && (
        <Card className="border-primary/30">
          <CardHeader>
            <CardTitle className="text-base">
              Details: {selectedSeries.asset} {selectedSeries.timeframe} ·{" "}
              {selectedSeries.model_version_name}
            </CardTitle>
            <CardDescription>
              {selectedSeries.bar_count} Bars ·{" "}
              {selectedSeries.unavailable_count} nicht verfügbar
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedSeries.coverage_issues.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Datenqualität</h4>
                {selectedSeries.coverage_issues.map((issue, i) => (
                  <Alert key={i} variant="default" className="text-sm">
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      <Badge variant="outline" className="mr-2 text-xs">
                        {ISSUE_TYPE_LABELS[issue.issue_type] ?? issue.issue_type}
                      </Badge>
                      {issue.detail}
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            )}

            {selectedSeries.coverage_issues.length === 0 && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Keine Datenqualitätsprobleme erkannt.
                </AlertDescription>
              </Alert>
            )}

            {selectedSeries.bars && selectedSeries.bars.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">
                  Bars (erste 20 / letzte 20 von {selectedSeries.bars.length})
                </h4>
                <div className="max-h-64 overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Zeitstempel</TableHead>
                        <TableHead>Regime</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...selectedSeries.bars.slice(0, 20), ...(selectedSeries.bars.length > 40
                        ? [{ bar_time: "...", regime: "..." } as never]
                        : []),
                        ...selectedSeries.bars.slice(Math.max(20, selectedSeries.bars.length - 20)),
                      ].map((bar, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-xs font-mono">
                            {bar.bar_time === "..."
                              ? "..."
                              : new Date(bar.bar_time).toLocaleString("de-DE")}
                          </TableCell>
                          <TableCell>
                            <Badge variant={bar.regime === "bullish" ? "default" : bar.regime === "bearish" ? "destructive" : "secondary"}>
                              {bar.regime}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
