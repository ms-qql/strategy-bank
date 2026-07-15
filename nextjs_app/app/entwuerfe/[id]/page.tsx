"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  Check,
  Loader,
  Plus,
  TriangleAlert,
  X,
} from "lucide-react";
import { apiGet, apiPatch, apiPostJson, apiDelete, ApiError } from "@/lib/api-client";
import { draftSchema, type Draft, type Parameter } from "@/lib/schemas/extraction";
import {
  versionListItemSchema,
  versionReadSchema,
  type VersionListItem,
  type VersionRead,
} from "@/lib/schemas/draft";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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

const CATEGORIES = [
  "Trendfolge",
  "Mean Reversion",
  "Breakout",
  "Volatilität",
  "Momentum",
  "Saison/Zeit",
  "Preis-/Candlestick-Muster",
  "Hybrid",
  "Sonstige",
];

const DIRECTIONS = [
  { value: "kombiniert", label: "kombiniert" },
  { value: "long-only", label: "long only" },
  { value: "short-only", label: "short only" },
];

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  Entwurf: "secondary",
  "nicht testbar": "destructive",
  "gesperrt (unvollständig)": "destructive",
  freigegeben: "default",
};

function SelectField({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function EntwurfEditPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const draftId = params.id;

  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [thesis, setThesis] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [direction, setDirection] = useState("kombiniert");
  const [entryRule, setEntryRule] = useState("");
  const [exitRule, setExitRule] = useState("");
  const [warmup, setWarmup] = useState("");
  const [simulBehavior, setSimulBehavior] = useState("");
  const [reversalBehavior, setReversalBehavior] = useState("");
  const [parameters, setParameters] = useState<
    { name: string; value: string; unit: string; allowed_range: string; is_proposal: boolean }[]
  >([]);

  // Versions
  const [versions, setVersions] = useState<VersionListItem[]>([]);
  const [viewingVersion, setViewingVersion] = useState<VersionRead | null>(null);

  // Freeze / mark-untestable
  const [freezeLoading, setFreezeLoading] = useState(false);
  const [freezeError, setFreezeError] = useState<string | null>(null);
  const [markReason, setMarkReason] = useState("");
  const [markLoading, setMarkLoading] = useState(false);

  // Gate conditions
  const openQuestionCount = draft?.open_questions.length ?? 0;
  const hasEntry = (entryRule ?? "").trim().length > 0;
  const hasExit = (exitRule ?? "").trim().length > 0;
  const hasWarmup = warmup !== null && warmup !== undefined;
  const canFreeze =
    draft?.status === "Entwurf" &&
    openQuestionCount === 0 &&
    hasEntry &&
    hasExit &&
    hasWarmup;

  const loadDraft = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = draftSchema.parse(await apiGet<Draft>(`/drafts/${draftId}`));
      setDraft(d);
      setName(d.name);
      setThesis(d.thesis);
      setCategory(d.category);
      setDirection(d.direction);
      setEntryRule(d.entry_rule ?? "");
      setExitRule(d.exit_rule ?? "");
      setWarmup(d.warmup_requirement ?? "");
      setSimulBehavior(d.simultaneous_entry_exit_behavior ?? "");
      setReversalBehavior(d.reversal_behavior ?? "");
      setParameters(
        d.parameters.map((p) => ({ ...p })),
      );

      try {
        const v = z
          .array(versionListItemSchema)
          .parse(await apiGet<VersionListItem[]>(`/drafts/${draftId}/versions`));
        setVersions(v);
      } catch {
        setVersions([]);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Entwurf konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [draftId]);

  useEffect(() => {
    loadDraft();
  }, [loadDraft]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const body: Record<string, unknown> = {};

      if (name !== draft?.name) body.name = name;
      if (thesis !== draft?.thesis) body.thesis = thesis;
      if (category !== draft?.category) body.category = category;
      if (direction !== draft?.direction) body.direction = direction;
      if ((entryRule ?? "") !== (draft?.entry_rule ?? "")) body.entry_rule = entryRule || null;
      if ((exitRule ?? "") !== (draft?.exit_rule ?? "")) body.exit_rule = exitRule || null;
      if ((warmup ?? "") !== (draft?.warmup_requirement ?? "")) body.warmup_requirement = warmup || null;
      if ((simulBehavior ?? "") !== (draft?.simultaneous_entry_exit_behavior ?? ""))
        body.simultaneous_entry_exit_behavior = simulBehavior || null;
      if ((reversalBehavior ?? "") !== (draft?.reversal_behavior ?? ""))
        body.reversal_behavior = reversalBehavior || null;

      const paramsChanged =
        JSON.stringify(parameters) !== JSON.stringify(draft?.parameters);
      if (paramsChanged) {
        body.parameters = parameters.map((p) => ({
          name: p.name,
          value: p.value,
          unit: p.unit || null,
          allowed_range: p.allowed_range || null,
        }));
      }

      if (Object.keys(body).length === 0) {
        setSuccess("Keine Änderungen.");
        return;
      }

      await apiPatch(`/drafts/${draftId}`, body);
      setSuccess("Gespeichert.");
      await loadDraft();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  };

  const handleCloseOpenQuestion = async (qid: string) => {
    try {
      await apiDelete(`/drafts/${draftId}/open-questions/${qid}`);
      await loadDraft();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Schließen der Unklarheit fehlgeschlagen.");
    }
  };

  const handleFreeze = async () => {
    setFreezeLoading(true);
    setFreezeError(null);
    try {
      await apiPostJson(`/drafts/${draftId}/freeze`, {});
      await loadDraft();
      setSuccess("Version freigegeben.");
    } catch (e) {
      setFreezeError(e instanceof ApiError ? e.message : "Freigabe fehlgeschlagen.");
    } finally {
      setFreezeLoading(false);
    }
  };

  const handleMarkUntestable = async () => {
    if (!markReason.trim()) return;
    setMarkLoading(true);
    try {
      await apiPostJson(`/drafts/${draftId}/mark-untestable`, { reason: markReason });
      await loadDraft();
      setMarkReason("");
      setSuccess("Als nicht testbar markiert.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Markierung fehlgeschlagen.");
    } finally {
      setMarkLoading(false);
    }
  };

  const handleNewDraftFromVersion = async (versionId: string) => {
    try {
      const data = await apiPostJson<Record<string, unknown>>(`/versions/${versionId}/new-draft`, {});
      router.push(`/entwuerfe/${data.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Neuer Entwurf konnte nicht erstellt werden.");
    }
  };

  const handleViewVersion = async (versionId: string) => {
    try {
      const v = versionReadSchema.parse(await apiGet<VersionRead>(`/versions/${versionId}`));
      setViewingVersion(v);
    } catch {
      setError("Version konnte nicht geladen werden.");
    }
  };

  const addParameter = () => {
    setParameters([
      ...parameters,
      { name: "", value: "", unit: "", allowed_range: "", is_proposal: false },
    ]);
  };

  const removeParameter = (idx: number) => {
    setParameters(parameters.filter((_, i) => i !== idx));
  };

  const updateParameter = (
    idx: number,
    field: string,
    val: string,
  ) => {
    setParameters(
      parameters.map((p, i) => (i === idx ? { ...p, [field]: val } : p)),
    );
  };

  const isReadOnly = draft?.status === "freigegeben";

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <Alert variant="destructive">
          <TriangleAlert aria-hidden="true" />
          <AlertTitle>Fehler</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="mt-4">
          <Button variant="outline" onClick={() => router.push("/quellen")}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            Zurück zu Quellen
          </Button>
        </div>
      </div>
    );
  }

  if (!draft) return null;

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      {/* Navigation */}
      <Button variant="ghost" size="sm" className="mb-4" onClick={() => router.push("/quellen")}>
        <ArrowLeft className="mr-1 h-4 w-4" />
        Zurück zu Quellen
      </Button>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{draft.name}</h1>
          {draft.parent_version_id && (
            <p className="mt-1 text-sm text-muted-foreground">
              Entwurf erstellt aus einer freigegebenen Version
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{draft.category}</Badge>
          <Badge variant="outline">
            {DIRECTIONS.find((d) => d.value === draft.direction)?.label ?? draft.direction}
          </Badge>
          <Badge variant={STATUS_VARIANT[draft.status]}>{draft.status}</Badge>
        </div>
      </div>

      {draft.status_reason && (
        <Alert variant="destructive" className="mb-6">
          <TriangleAlert aria-hidden="true" />
          <AlertTitle>Hinweis</AlertTitle>
          <AlertDescription>{draft.status_reason}</AlertDescription>
        </Alert>
      )}

      {/* Messages */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <TriangleAlert aria-hidden="true" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="mb-4 border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
          <Check aria-hidden="true" />
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Bearbeitungsformular */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Stammdaten & Regeln</CardTitle>
          <CardDescription>
            Bearbeite die von der KI extrahierten oder aus einer Version übernommenen Daten.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {/* These */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="thesis">These</Label>
            <Textarea
              id="thesis"
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              disabled={isReadOnly}
              rows={2}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Kategorie"
              value={category}
              options={CATEGORIES.map((c) => ({ value: c, label: c }))}
              onChange={setCategory}
              disabled={isReadOnly}
            />
            <SelectField
              label="Richtung"
              value={direction}
              options={DIRECTIONS}
              onChange={setDirection}
              disabled={isReadOnly}
            />
          </div>

          {/* Regeln */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="entry_rule">Entry-Regel</Label>
              <Textarea
                id="entry_rule"
                value={entryRule}
                onChange={(e) => setEntryRule(e.target.value)}
                disabled={isReadOnly}
                rows={3}
                placeholder="z. B. RSI(14) < 30"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="exit_rule">Exit-Regel</Label>
              <Textarea
                id="exit_rule"
                value={exitRule}
                onChange={(e) => setExitRule(e.target.value)}
                disabled={isReadOnly}
                rows={3}
                placeholder="z. B. RSI(14) > 70"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="warmup">Warm-up</Label>
              <Input
                id="warmup"
                value={warmup}
                onChange={(e) => setWarmup(e.target.value)}
                disabled={isReadOnly}
                placeholder="z. B. 0 bars"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="simul">Gleichzeitiger Entry/Exit</Label>
              <Input
                id="simul"
                value={simulBehavior}
                onChange={(e) => setSimulBehavior(e.target.value)}
                disabled={isReadOnly}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="reversal">Reversal-Verhalten</Label>
              <Input
                id="reversal"
                value={reversalBehavior}
                onChange={(e) => setReversalBehavior(e.target.value)}
                disabled={isReadOnly}
              />
            </div>
          </div>

          {!isReadOnly && (
            <div className="flex justify-end">
              <Button onClick={handleSave} disabled={saving}>
                {saving && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                Speichern
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Parameter */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Parameter</CardTitle>
            <CardDescription>
              Bearbeite Parameterwerte — bestätigte Werte gelten nicht mehr als KI-Vorschlag.
            </CardDescription>
          </div>
          {!isReadOnly && (
            <Button variant="outline" size="sm" onClick={addParameter}>
              <Plus className="mr-1 h-4 w-4" />
              Hinzufügen
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {parameters.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Keine Parameter vorhanden.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Wert</TableHead>
                  <TableHead>Einheit</TableHead>
                  <TableHead>Bereich</TableHead>
                  <TableHead className="text-right">Status</TableHead>
                  {!isReadOnly && <TableHead className="w-10" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {parameters.map((p, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      {isReadOnly ? (
                        <span className="font-medium">{p.name}</span>
                      ) : (
                        <Input
                          value={p.name}
                          onChange={(e) => updateParameter(idx, "name", e.target.value)}
                          className="h-8 text-sm"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {isReadOnly ? (
                        <span className="font-mono">{p.value}</span>
                      ) : (
                        <Input
                          value={p.value}
                          onChange={(e) => updateParameter(idx, "value", e.target.value)}
                          className="h-8 font-mono text-sm"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {isReadOnly ? (
                        <span className="text-muted-foreground">{p.unit || "—"}</span>
                      ) : (
                        <Input
                          value={p.unit}
                          onChange={(e) => updateParameter(idx, "unit", e.target.value)}
                          className="h-8 text-sm"
                          placeholder="—"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {isReadOnly ? (
                        <span className="text-muted-foreground">{p.allowed_range || "—"}</span>
                      ) : (
                        <Input
                          value={p.allowed_range}
                          onChange={(e) => updateParameter(idx, "allowed_range", e.target.value)}
                          className="h-8 text-sm"
                          placeholder="—"
                        />
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {p.is_proposal ? (
                        <Badge variant="secondary">Vorschlag</Badge>
                      ) : (
                        <Badge variant="outline">Bestätigt</Badge>
                      )}
                    </TableCell>
                    {!isReadOnly && (
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => removeParameter(idx)}
                          aria-label="Parameter entfernen"
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {!isReadOnly && parameters.length > 0 && (
            <div className="mt-4 flex justify-end">
              <Button onClick={handleSave} disabled={saving}>
                {saving && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                Speichern
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Offene Unklarheiten */}
      {draft.open_questions.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Offene Unklarheiten ({draft.open_questions.length})
            </CardTitle>
            <CardDescription>
              Diese müssen vor der Freigabe geschlossen werden.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              {draft.open_questions.map((q, i) => (
                <div
                  key={i}
                  className="flex items-start justify-between gap-3 rounded-md border border-border p-3"
                >
                  <div>
                    <p className="text-sm font-medium">{q.description}</p>
                    <p className="text-xs text-muted-foreground">
                      Begründung: {q.reasoning}
                    </p>
                  </div>
                  {!isReadOnly && (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handleCloseOpenQuestion(q.id)}
                      aria-label="Unklarheit schließen"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Versionshistorie */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Versionshistorie</CardTitle>
          <CardDescription>
            Freigegebene Versionen dieser Strategie-Familie.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Noch keine freigegebenen Versionen.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Version</TableHead>
                  <TableHead>Freigegeben am</TableHead>
                  <TableHead className="text-right">Aktionen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((v) => (
                  <TableRow key={v.id}>
                    <TableCell className="font-mono">v{v.version_number}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(v.frozen_at).toLocaleString("de-DE")}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => handleViewVersion(v.id)}>
                          Ansehen
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleNewDraftFromVersion(v.id)}
                        >
                          Neuer Entwurf
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Version detail modal */}
      {viewingVersion && (
        <Card className="mb-6 border-2 border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Version v{viewingVersion.version_number}</CardTitle>
              <CardDescription>
                Freigegeben am {new Date(viewingVersion.frozen_at).toLocaleString("de-DE")}
              </CardDescription>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setViewingVersion(null)}>
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid gap-2 text-sm">
              {Object.entries(viewingVersion.snapshot).map(([key, val]) => {
                if (key === "parameters" || val === null || val === "") return null;
                return (
                  <div key={key} className="flex gap-2">
                    <span className="w-40 shrink-0 font-medium text-muted-foreground">{key}:</span>
                    <span>{String(val)}</span>
                  </div>
                );
              })}
            </div>

            {viewingVersion.parameters.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium">Parameter</p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Wert</TableHead>
                      <TableHead>Einheit</TableHead>
                      <TableHead>Bereich</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {viewingVersion.parameters.map((p, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{p.name}</TableCell>
                        <TableCell className="font-mono">{p.value}</TableCell>
                        <TableCell className="text-muted-foreground">{p.unit ?? "—"}</TableCell>
                        <TableCell className="text-muted-foreground">{p.allowed_range ?? "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            {viewingVersion.user_diff.length > 0 && (
              <div>
                <p className="mb-2 text-sm font-medium">Nutzer-Änderungen gegenüber KI-Vorschlag</p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Feld</TableHead>
                      <TableHead>KI-Vorschlag</TableHead>
                      <TableHead>Nutzer-Wert</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {viewingVersion.user_diff.map((diff, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{diff.field}</TableCell>
                        <TableCell className="text-muted-foreground text-xs">
                          {diff.from === null || diff.from === undefined
                            ? "—"
                            : typeof diff.from === "string"
                              ? diff.from
                              : JSON.stringify(diff.from)}
                        </TableCell>
                        <TableCell className="text-xs">
                          {diff.to === null || diff.to === undefined
                            ? "—"
                            : typeof diff.to === "string"
                              ? diff.to
                              : JSON.stringify(diff.to)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}

            <div className="flex justify-end">
              <Button onClick={() => handleNewDraftFromVersion(viewingVersion.id)}>
                Aus dieser Version neuen Entwurf erstellen
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Herkunft */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Herkunft</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <span className="font-medium text-muted-foreground">Extraktionslauf: </span>
              <span className="font-mono text-xs">{draft.extraction_run_id}</span>
            </div>
            <div>
              <span className="font-medium text-muted-foreground">Quell-Hash: </span>
              <span className="font-mono text-xs">{draft.source_hash}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Aktionsleiste */}
      {!isReadOnly && (
        <Card className="mb-6 border-2 border-border">
          <CardHeader>
            <CardTitle>Freigabe & Status</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {/* Gate conditions */}
            <div className="rounded-md bg-muted/50 p-4">
              <p className="mb-2 text-sm font-medium">Freigabe-Bedingungen:</p>
              <ul className="flex flex-col gap-1 text-sm">
                <li className="flex items-center gap-2">
                  {draft.status === "Entwurf" ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <X className="h-4 w-4 text-destructive" />
                  )}
                  Status ist &quot;Entwurf&quot;
                </li>
                <li className="flex items-center gap-2">
                  {openQuestionCount === 0 ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <X className="h-4 w-4 text-destructive" />
                  )}
                  Keine offenen Unklarheiten ({openQuestionCount} vorhanden)
                </li>
                <li className="flex items-center gap-2">
                  {hasEntry ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <X className="h-4 w-4 text-destructive" />
                  )}
                  Entry-Regel vorhanden
                </li>
                <li className="flex items-center gap-2">
                  {hasExit ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <X className="h-4 w-4 text-destructive" />
                  )}
                  Exit-Regel vorhanden
                </li>
                <li className="flex items-center gap-2">
                  {hasWarmup ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <X className="h-4 w-4 text-destructive" />
                  )}
                  Warm-up gesetzt
                </li>
              </ul>
            </div>

            {freezeError && (
              <Alert variant="destructive">
                <TriangleAlert aria-hidden="true" />
                <AlertDescription>{freezeError}</AlertDescription>
              </Alert>
            )}

            <div className="flex flex-wrap gap-3">
              <Button onClick={handleFreeze} disabled={!canFreeze || freezeLoading}>
                {freezeLoading && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                Version freigeben
              </Button>

              {/* Mark untestable */}
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Begründung für nicht testbar"
                  value={markReason}
                  onChange={(e) => setMarkReason(e.target.value)}
                  className="w-64"
                />
                <Button
                  variant="destructive"
                  onClick={handleMarkUntestable}
                  disabled={!markReason.trim() || markLoading}
                >
                  {markLoading && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                  Als nicht testbar markieren
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
