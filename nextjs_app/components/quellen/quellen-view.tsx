"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Loader } from "lucide-react";
import { z } from "zod";
import { apiGet, apiPostForm, ApiError } from "@/lib/api-client";
import {
  MAX_SOURCE_BYTES,
  sourceListSchema,
  sourceSchema,
  type Source,
} from "@/lib/schemas/source";
import {
  extractionRunDetailSchema,
  extractionRunSchema,
  type ExtractionRun,
  type ExtractionRunDetail,
} from "@/lib/schemas/extraction";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { ExtrahierenButton } from "./extrahieren-button";
import { EntwurfCard } from "./entwurf-card";
import { MarkdownDropzone } from "./markdown-dropzone";

const TYP_LABEL: Record<Source["source_type"], string> = {
  text: "Text",
  markdown_file: "Markdown-Datei",
};

const STATUS_VARIANT: Record<
  Source["extraction_status"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  "noch nicht extrahiert": "outline",
  "wird extrahiert": "secondary",
  extrahiert: "default",
  "extrahiert, keine Treffer": "secondary",
  "Extraktion fehlgeschlagen": "destructive",
};

const POLL_MS = 2000;

type ExtState =
  | { kind: "idle" }
  | { kind: "loading" }
  | {
      kind: "loaded";
      runs: ExtractionRun[];
      details: Map<string, ExtractionRunDetail>;
    }
  | { kind: "error"; message: string };

function formatZeitpunkt(iso: string): string {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString("de-DE");
}

export function QuellenView() {
  const [sources, setSources] = useState<Source[]>([]);
  const [ladeliste, setLadeliste] = useState(true);
  const [listenfehler, setListenfehler] = useState<string | null>(null);

  const [tab, setTab] = useState<Source["source_type"]>("text");
  const [text, setText] = useState("");
  const [datei, setDatei] = useState<File | null>(null);
  const [absenden, setAbsenden] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [extData, setExtData] = useState<Map<string, ExtState>>(new Map());
  const pollHandles = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

  useEffect(() => {
    apiGet<unknown>("/sources")
      .then((data) => setSources(sourceListSchema.parse(data)))
      .catch((e) =>
        setListenfehler(
          e instanceof ApiError ? e.message : "Quellen konnten nicht geladen werden.",
        ),
      )
      .finally(() => setLadeliste(false));
  }, []);

  useEffect(() => {
    const handles = pollHandles.current;
    return () => {
      for (const h of handles.values()) clearTimeout(h);
      handles.clear();
    };
  }, []);

  // ponytail: globaler Datei-Drop-Schutz. Verhindert, dass der Browser die App
  // durch eine außerhalb der Dropzone abgelegte Datei ersetzt. Klicks, Text-
  // auswahl und Drag-Vorgänge ohne Dateien bleiben unberührt.
  useEffect(() => {
    function isFileDrag(e: DragEvent) {
      return Array.from(e.dataTransfer?.types ?? []).includes("Files");
    }
    function onDragOver(e: DragEvent) {
      if (isFileDrag(e)) e.preventDefault();
    }
    function onDrop(e: DragEvent) {
      if (isFileDrag(e)) e.preventDefault();
    }
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("drop", onDrop);
    };
  }, []);

  const updateSourceStatus = useCallback(
    (sourceId: string, status: Source["extraction_status"]) => {
      setSources((prev) =>
        prev.map((s) =>
          s.id === sourceId && s.extraction_status !== status
            ? { ...s, extraction_status: status }
            : s,
        ),
      );
    },
    [],
  );

  const loadRunDetail = useCallback(
    async (runId: string): Promise<ExtractionRunDetail> => {
      const data = await apiGet<unknown>(`/extractions/${runId}`);
      return extractionRunDetailSchema.parse(data);
    },
    [],
  );

  const schedulePoll = useCallback(
    (runId: string, sourceId: string) => {
      const handle = setTimeout(async () => {
        pollHandles.current.delete(runId);
        try {
          const detail = await loadRunDetail(runId);
          setExtData((prev) => {
            const next = new Map(prev);
            const state = next.get(sourceId);
            if (state?.kind === "loaded") {
              const details = new Map(state.details);
              details.set(runId, detail);
              next.set(sourceId, {
                ...state,
                runs: state.runs.map((run) =>
                  run.id === runId
                    ? { ...run, status: detail.status, finished_at: detail.finished_at, error_message: detail.error_message }
                    : run,
                ),
                details,
              });
            }
            return next;
          });
          if (detail.status === "läuft") {
            schedulePoll(runId, sourceId);
          } else {
            updateSourceStatus(
              sourceId,
              detail.status === "abgeschlossen"
                ? "extrahiert"
                : detail.status === "keine Treffer"
                  ? "extrahiert, keine Treffer"
                  : "Extraktion fehlgeschlagen",
            );
          }
        } catch {
          schedulePoll(runId, sourceId);
        }
      }, POLL_MS);
      pollHandles.current.set(runId, handle);
    },
    [loadRunDetail, updateSourceStatus],
  );

  const fetchExtractions = useCallback(
    async (sourceId: string) => {
      setExtData((prev) => new Map(prev).set(sourceId, { kind: "loading" }));
      try {
        const list = z
          .array(extractionRunSchema)
          .parse(await apiGet<unknown>(`/sources/${sourceId}/extractions`));
        if (list.length === 0) {
          setExtData(
            (prev) =>
              new Map(prev).set(sourceId, {
                kind: "loaded",
                runs: [],
                details: new Map(),
              }),
          );
          return;
        }
        const latest = list[0];
        const detail = await loadRunDetail(latest.id);
        const details = new Map<string, ExtractionRunDetail>();
        details.set(latest.id, detail);
        setExtData(
          (prev) =>
            new Map(prev).set(sourceId, {
              kind: "loaded",
              runs: list,
              details,
            }),
        );
        if (latest.status === "läuft") {
          schedulePoll(latest.id, sourceId);
        }
      } catch (e) {
        setExtData(
          (prev) =>
            new Map(prev).set(sourceId, {
              kind: "error",
              message:
                e instanceof ApiError
                  ? e.message
                  : "Extraktionen konnten nicht geladen werden.",
            }),
        );
      }
    },
    [loadRunDetail, schedulePoll],
  );

  function toggleExpand(sourceId: string) {
    setExpandedId((prev) => {
      if (prev === sourceId) return null;
      const state = extData.get(sourceId);
      if (!state || state.kind === "idle") {
        void fetchExtractions(sourceId);
      }
      return sourceId;
    });
  }

  async function handleStarted(sourceId: string, run: ExtractionRun) {
    updateSourceStatus(sourceId, "wird extrahiert");
    setExtData((prev) => {
      const next = new Map(prev);
      const state = next.get(sourceId);
      const runs = [run, ...(state?.kind === "loaded" ? state.runs : [])];
      const details =
        state?.kind === "loaded" ? state.details : new Map<string, ExtractionRunDetail>();
      next.set(sourceId, { kind: "loaded", runs, details });
      return next;
    });
    setExpandedId(sourceId);
    schedulePoll(run.id, sourceId);
  }

  function reset() {
    setText("");
    setDatei(null);
  }

  function handleDateiChange(file: File | null, error: string | null) {
    setDatei(file);
    setFehler(error);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFehler(null);

    const form = new FormData();
    form.set("source_type", tab);

    if (tab === "text") {
      if (text.trim().length === 0) {
        setFehler("Quelle enthält keinen Inhalt.");
        return;
      }
      form.set("content", text);
    } else {
      if (!datei) {
        setFehler("Bitte eine Markdown-Datei (.md) auswählen.");
        return;
      }
      if (!datei.name.toLowerCase().endsWith(".md")) {
        setFehler("Nur .md-Dateien werden als Datei-Upload unterstützt.");
        return;
      }
      if (datei.size === 0) {
        setFehler("Quelle enthält keinen Inhalt.");
        return;
      }
      if (datei.size > MAX_SOURCE_BYTES) {
        setFehler("Datei überschreitet das Größenlimit von 2 MB.");
        return;
      }
      form.set("file", datei);
    }

    setAbsenden(true);
    try {
      const data = await apiPostForm<unknown>("/sources", form);
      const neu = sourceSchema.parse(data);
      setSources((prev) => [neu, ...prev]);
      reset();
    } catch (err) {
      setFehler(
        err instanceof ApiError ? err.message : "Quelle konnte nicht gespeichert werden.",
      );
    } finally {
      setAbsenden(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <Card>
        <CardHeader>
          <CardTitle>Quelle erfassen</CardTitle>
          <CardDescription>
            Genau eine Quelle je Vorgang: eingefügter Klartext oder eine
            hochgeladene <code>.md</code>-Datei.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Tabs
              value={tab}
              onValueChange={(v) => {
                setTab(v as Source["source_type"]);
                setFehler(null);
              }}
            >
              <TabsList>
                <TabsTrigger value="text">Text einfügen</TabsTrigger>
                <TabsTrigger value="markdown_file">Markdown-Datei</TabsTrigger>
              </TabsList>

              <TabsContent value="text" className="pt-2">
                <Label htmlFor="quelle-text" className="sr-only">
                  Strategiebeschreibung
                </Label>
                <Textarea
                  id="quelle-text"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Strategiebeschreibung hier einfügen …"
                  rows={12}
                  className="font-mono"
                />
              </TabsContent>

              <TabsContent value="markdown_file" className="pt-2">
                <MarkdownDropzone datei={datei} onChange={handleDateiChange} />
              </TabsContent>
            </Tabs>

            {fehler && (
              <Alert variant="destructive">
                <AlertDescription>{fehler}</AlertDescription>
              </Alert>
            )}

            <div>
              <Button type="submit" disabled={absenden}>
                {absenden ? "Speichern …" : "Quelle speichern"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Erfasste Quellen</CardTitle>
        </CardHeader>
        <CardContent>
          {ladeliste ? (
            <p className="text-sm text-muted-foreground">Wird geladen …</p>
          ) : listenfehler ? (
            <Alert variant="destructive">
              <AlertDescription>{listenfehler}</AlertDescription>
            </Alert>
          ) : sources.length === 0 ? (
            <p className="text-sm text-muted-foreground">Noch keine Quelle erfasst.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Erfasst am</TableHead>
                  <TableHead>Quell-Hash</TableHead>
                  <TableHead>Typ</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Aktion</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sources.map((s) => {
                  const expanded = expandedId === s.id;
                  const isRunning = s.extraction_status === "wird extrahiert";
                  const showStart =
                    s.extraction_status === "noch nicht extrahiert";
                  const showRetry =
                    s.extraction_status === "Extraktion fehlgeschlagen" ||
                    s.extraction_status === "wird extrahiert";
                  return (
                    <>
                      <TableRow
                        key={s.id}
                        aria-expanded={expanded}
                        className="cursor-pointer"
                        onClick={() => toggleExpand(s.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            toggleExpand(s.id);
                          }
                        }}
                        tabIndex={0}
                      >
                        <TableCell>
                          {expanded ? (
                            <ChevronDown
                              className="size-4 text-muted-foreground"
                              aria-hidden="true"
                            />
                          ) : (
                            <ChevronRight
                              className="size-4 text-muted-foreground"
                              aria-hidden="true"
                            />
                          )}
                        </TableCell>
                        <TableCell>{formatZeitpunkt(s.captured_at)}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {s.source_hash.slice(0, 12)}
                        </TableCell>
                        <TableCell>{TYP_LABEL[s.source_type]}</TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1.5">
                            {isRunning && (
                              <Loader
                                className="size-3 animate-spin"
                                aria-hidden="true"
                              />
                            )}
                            <Badge variant={STATUS_VARIANT[s.extraction_status]}>
                              {s.extraction_status}
                            </Badge>
                          </span>
                        </TableCell>
                        <TableCell
                          className="text-right"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {showStart && (
                            <ExtrahierenButton
                              sourceId={s.id}
                              variant="start"
                              onStarted={(run) => handleStarted(s.id, run)}
                            />
                          )}
                          {showRetry && (
                            <ExtrahierenButton
                              sourceId={s.id}
                              variant="retry"
                              onStarted={(run) => handleStarted(s.id, run)}
                            />
                          )}
                        </TableCell>
                      </TableRow>
                      {expanded && (
                        <TableRow key={`${s.id}-detail`} className="bg-muted/20">
                          <TableCell colSpan={6} className="align-top p-0">
                            <EntwuerfeSection
                              state={extData.get(s.id)}
                              onRetryLatest={() => toggleExpand(s.id)}
                            />
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface SectionProps {
  state: ExtState | undefined;
  onRetryLatest: () => void;
}

function EntwuerfeSection({ state, onRetryLatest }: SectionProps) {
  if (!state || state.kind === "idle" || state.kind === "loading") {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Extraktionen werden geladen …
      </div>
    );
  }
  if (state.kind === "error") {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertDescription>{state.message}</AlertDescription>
        </Alert>
        <Button
          size="sm"
          variant="outline"
          className="mt-2"
          onClick={onRetryLatest}
        >
          Erneut versuchen
        </Button>
      </div>
    );
  }
  if (state.runs.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Noch keine Extraktion gestartet.
      </div>
    );
  }
  const latest = state.runs[0];
  const detail = state.details.get(latest.id);

  if (latest.status === "läuft") {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground">
        <Loader className="size-4 animate-spin" aria-hidden="true" />
        Extraktion läuft (Modell {latest.model}, Prompt {latest.prompt_version}) …
      </div>
    );
  }

  if (latest.status === "fehlgeschlagen") {
    return (
      <div className="p-4">
        <Alert variant="destructive">
          <AlertDescription>
            Extraktion fehlgeschlagen.
            {latest.error_message && ` ${latest.error_message}`}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (latest.status === "keine Treffer") {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Keine Strategie in dieser Quelle erkannt.
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Entwurfsdetails werden geladen …
      </div>
    );
  }

  if (detail.drafts.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Keine Strategie in dieser Quelle erkannt.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      <p className="text-xs text-muted-foreground">
        {detail.drafts.length === 1
          ? "1 Entwurf erkannt"
          : `${detail.drafts.length} Entwürfe erkannt`}{" "}
        · Modell {detail.model} · Prompt {detail.prompt_version}
      </p>
      {detail.drafts.map((d) => (
        <EntwurfCard key={d.id} draft={d} />
      ))}
    </div>
  );
}
