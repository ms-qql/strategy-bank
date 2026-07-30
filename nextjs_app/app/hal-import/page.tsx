"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { apiGet, apiPostForm, apiPostJson, ApiError } from "@/lib/api-client";
import {
  halImportResponseSchema,
  halImportRunRowSchema,
  halImportedFileRowSchema,
  halUnassignedSchema,
  versionSummarySchema,
  STATUS_LABELS,
  STATUS_BADGE_VARIANT,
  type HalImportResponse,
  type HalImportRunRow,
  type HalImportedFileRow,
  type HalUnassigned,
  type VersionSummary,
} from "@/lib/schemas/hal-import";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Upload,
  Loader,
  FileText,
  TriangleAlert,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  Link2,
  Link2Off,
  History,
} from "lucide-react";

export default function HalImportPage() {
  return (
    <div className="w-full px-4 py-6">
      <h1 className="text-xl font-semibold mb-1">HAL-Import</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Backtestergebnisse aus dem Hal-Vault hochladen, zuordnen und in der
        Ergebnisansicht vergleichen.
      </p>

      <Tabs defaultValue="import" className="w-full">
        <TabsList>
          <TabsTrigger value="import">Import</TabsTrigger>
          <TabsTrigger value="zuordnung">Zuordnung</TabsTrigger>
          <TabsTrigger value="historie">Historie</TabsTrigger>
        </TabsList>
        <TabsContent value="import" className="mt-4">
          <ImportTab />
        </TabsContent>
        <TabsContent value="zuordnung" className="mt-4">
          <AssignmentTab />
        </TabsContent>
        <TabsContent value="historie" className="mt-4">
          <ImportHistoryTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ImportTab() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<HalImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    setResult(null);

    const form = new FormData();
    for (const f of files) form.append("files", f);

    try {
      const data = halImportResponseSchema.parse(
        await apiPostForm("/hal-results/import", form),
      );
      setResult(data);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Import fehlgeschlagen.",
      );
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  return (
    <div className="space-y-6">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
        className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-muted-foreground/25 p-12 transition-colors hover:border-muted-foreground/50"
      >
        {uploading ? (
          <Loader className="h-8 w-8 animate-spin text-muted-foreground" />
        ) : (
          <Upload className="h-8 w-8 text-muted-foreground" />
        )}
        <div className="text-center">
          <p className="font-medium">
            {uploading ? "Import läuft..." : "Dateien zum Hochladen hier ablegen"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Mehrere .md-Dateien oder genau eine .zip-Datei mit Markdown-Dateien
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".md,.zip"
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <ImportBericht result={result} />
      )}
    </div>
  );
}

function ImportBericht({ result }: { result: HalImportResponse }) {
  const counts = {
    importiert: result.files.filter((f) => f.status === "importiert").length,
    unverändert: result.files.filter((f) => f.status === "unverändert").length,
    aktualisiert: result.files.filter((f) => f.status === "aktualisiert").length,
    fehlerhaft: result.files.filter((f) => f.status === "fehlerhaft").length,
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Import-Ergebnis</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="mb-4 flex flex-wrap gap-3 text-sm">
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            Importiert: {counts.importiert}
          </span>
          <span className="flex items-center gap-1">
            <RefreshCw className="h-4 w-4 text-blue-600" />
            Aktualisiert: {counts.aktualisiert}
          </span>
          <span className="flex items-center gap-1 text-muted-foreground">
            Unverändert: {counts.unverändert}
          </span>
          <span className="flex items-center gap-1">
            <XCircle className="h-4 w-4 text-destructive" />
            Fehlerhaft: {counts.fehlerhaft}
          </span>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Datei</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {result.files.map((f, i) => (
              <TableRow key={`${f.origin_path}-${i}`}>
                <TableCell className="font-mono text-xs max-w-[300px] truncate">
                  {f.origin_path}
                </TableCell>
                <TableCell>
                  <Badge variant={STATUS_BADGE_VARIANT[f.status] ?? "outline"}>
                    {STATUS_LABELS[f.status] ?? f.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {f.status === "importiert" && f.strategy_name && (
                    <span>Strategie: {f.strategy_name}</span>
                  )}
                  {f.status === "fehlerhaft" && f.error_message && (
                    <span className="text-destructive">{f.error_message}</span>
                  )}
                  {f.status === "unverändert" && (
                    <span>Bereits vorhanden</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function AssignmentTab() {
  const [unassigned, setUnassigned] = useState<HalUnassigned[]>([]);
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [assigningId, setAssigningId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [u, v] = await Promise.all([
          apiGet<HalUnassigned[]>("/hal-results/unassigned").then((d) =>
            z.array(halUnassignedSchema).parse(d),
          ),
          apiGet<VersionSummary[]>("/versions").then((d) =>
            z.array(versionSummarySchema).parse(d),
          ),
        ]);
        setUnassigned(u);
        setVersions(v);
      } catch (e) {
        setError(
          e instanceof ApiError ? e.message : "Daten konnten nicht geladen werden.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleAssign = async (resultId: string, versionId: string | null) => {
    setAssigningId(resultId);
    try {
      await apiPostJson(`/hal-results/${resultId}/assign`, {
        strategy_version_id: versionId,
      });
      setUnassigned((prev) => prev.filter((r) => r.id !== resultId));
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Zuordnung fehlgeschlagen.",
      );
    } finally {
      setAssigningId(null);
    }
  };

  const filteredVersions = versions.filter(
    (v) =>
      !searchQuery ||
      (v.name ?? "").toLowerCase().includes(searchQuery.toLowerCase()),
  );

  if (loading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center">
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

      {unassigned.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12">
            <CheckCircle2 className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              Keine unzugeordneten Ergebnisse. Alle HAL-Importe sind
              Strategieversionen zugewiesen.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {unassigned.map((item) => (
            <Card key={item.id}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    {item.strategy_name}
                    <Badge variant="outline" className="text-xs">
                      HAL-Import
                    </Badge>
                  </span>
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  {item.asset} · {item.timeframe} ·{" "}
                  {new Date(item.period_start).toLocaleDateString("de-DE")}
                  {item.period_end
                    ? ` – ${new Date(item.period_end).toLocaleDateString("de-DE")}`
                    : ""}{" "}
                  · Net: {item.net_return_pct.toFixed(1)}% · DD:{" "}
                  {item.max_drawdown_pct.toFixed(1)}% · Trades:{" "}
                  {item.trade_count}
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-3">
                  {item.suggested_version_id && (
                    <div className="flex-1 min-w-0">
                      <Label className="text-xs">Vorschlag</Label>
                      <p className="font-mono text-sm truncate">
                        {item.suggested_version_name ?? item.suggested_version_id}
                      </p>
                    </div>
                  )}
                  {item.suggested_version_id && (
                    <Button
                      size="sm"
                      onClick={() =>
                        handleAssign(item.id, item.suggested_version_id!)
                      }
                      disabled={assigningId === item.id}
                    >
                      {assigningId === item.id ? (
                        <Loader className="mr-1 h-3 w-3 animate-spin" />
                      ) : (
                        <Link2 className="mr-1 h-3 w-3" />
                      )}
                      Vorschlag übernehmen
                    </Button>
                  )}
                  <ZuordnungsSuche
                    versions={filteredVersions}
                    searchQuery={searchQuery}
                    onSearchChange={setSearchQuery}
                    onAssign={(versionId) => handleAssign(item.id, versionId)}
                    assigning={assigningId === item.id}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleAssign(item.id, null)}
                    disabled={assigningId === item.id}
                  >
                    <Link2Off className="mr-1 h-3 w-3" />
                    Unzugeordnet lassen
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ZuordnungsSuche({
  versions,
  searchQuery,
  onSearchChange,
  onAssign,
  assigning,
}: {
  versions: VersionSummary[];
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onAssign: (versionId: string) => void;
  assigning: boolean;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(!open)}
        disabled={assigning}
      >
        <Search className="mr-1 h-3 w-3" />
        Manuell zuweisen
      </Button>
      {open && (
        <div className="absolute top-full left-0 z-50 mt-1 w-72 rounded-md border bg-popover p-2 shadow-md">
          <Input
            placeholder="Strategie suchen..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="mb-2 h-8 text-sm"
          />
          <div className="max-h-48 overflow-y-auto">
            {versions.slice(0, 30).map((v) => (
              <button
                key={v.id}
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                onClick={() => {
                  onAssign(v.id);
                  setOpen(false);
                }}
              >
                <span className="font-mono text-xs">v{v.version_number}</span>
                <span className="truncate">{v.name ?? v.id}</span>
              </button>
            ))}
            {versions.length === 0 && (
              <p className="px-2 py-1.5 text-sm text-muted-foreground">
                Keine Strategien gefunden
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ImportHistoryTab() {
  const [runs, setRuns] = useState<HalImportRunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [runFiles, setRunFiles] = useState<HalImportedFileRow[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = z
          .array(halImportRunRowSchema)
          .parse(await apiGet<HalImportRunRow[]>("/hal-results/imports"));
        setRuns(data);
      } catch (e) {
        setError(
          e instanceof ApiError ? e.message : "Historie konnte nicht geladen werden.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const toggleExpand = async (runId: string) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null);
      setRunFiles([]);
      return;
    }
    setExpandedRunId(runId);
    setFilesLoading(true);
    try {
      const data = z
        .array(halImportedFileRowSchema)
        .parse(
          await apiGet<HalImportedFileRow[]>(
            `/hal-results/imports/${runId}/files`,
          ),
        );
      setRunFiles(data);
    } catch {
      setRunFiles([]);
    } finally {
      setFilesLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <TriangleAlert aria-hidden="true" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (runs.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-12">
          <History className="h-10 w-10 text-muted-foreground" />
          <p className="text-muted-foreground">
            Keine früheren Importläufe vorhanden.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {runs.map((run) => (
        <Card key={run.id}>
          <CardHeader
            className="cursor-pointer pb-2"
            onClick={() => toggleExpand(run.id)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-mono">
                {new Date(run.created_at).toLocaleString("de-DE")}
              </CardTitle>
              <div className="flex gap-3 text-xs text-muted-foreground">
                <span>
                  Importiert:{" "}
                  <strong className="text-foreground">
                    {run.status_imported}
                  </strong>
                </span>
                <span>
                  Aktualisiert:{" "}
                  <strong className="text-foreground">
                    {run.status_updated}
                  </strong>
                </span>
                <span>
                  Unverändert:{" "}
                  <strong className="text-foreground">
                    {run.status_unchanged}
                  </strong>
                </span>
                <span>
                  Fehlerhaft:{" "}
                  <strong className="text-foreground">
                    {run.status_failed}
                  </strong>
                </span>
              </div>
            </div>
          </CardHeader>
          {expandedRunId === run.id && (
            <CardContent>
              {filesLoading ? (
                <Loader className="h-4 w-4 animate-spin" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Datei</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Fehlermeldung</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runFiles.map((f) => (
                      <TableRow key={f.id}>
                        <TableCell className="font-mono text-xs max-w-[300px] truncate">
                          {f.origin_path}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              STATUS_BADGE_VARIANT[f.processing_status] ??
                              "outline"
                            }
                          >
                            {STATUS_LABELS[f.processing_status] ??
                              f.processing_status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {f.error_message ?? "–"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}
