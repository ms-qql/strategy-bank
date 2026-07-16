"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { z } from "zod";
import { apiGet, apiPatch, apiPostJson, ApiError } from "@/lib/api-client";
import { ArrowLeft, Check, Loader, Plus, TriangleAlert, X } from "lucide-react";
import {
  backtestProfileSchema,
  batchSchema,
  creditStatusSchema,
  previewRunSchema,
  versionSummarySchema,
  DIRECTION_MODES,
  type BacktestProfile,
  type Batch,
  type CreditStatus,
  type Instrument,
  type PreviewRun,
  type VersionSummary,
} from "@/lib/schemas/batch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import BatchAusfuehrung from "@/components/ausfuehrung/batch-ausfuehrung";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const DEFAULT_INSTRUMENTS: Instrument[] = [
  { provider_symbol: "BYBIT:BTCUSDT.P", label: "BTC" },
];

type EditableInstrument = Instrument & { active: boolean };

const INSTRUMENT_PREFERENCE_KEY = "strategy-bank.instrument-preference-v1";

function readInstrumentPreference(): EditableInstrument[] | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(INSTRUMENT_PREFERENCE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    const seen = new Set<string>();
    const result: EditableInstrument[] = [];
    for (const entry of parsed) {
      if (!entry || typeof entry !== "object") return null;
      const symbol = (entry as { provider_symbol?: unknown }).provider_symbol;
      if (typeof symbol !== "string" || !symbol.trim()) return null;
      const key = symbol.trim();
      if (seen.has(key)) return null;
      seen.add(key);
      const label = (entry as { label?: unknown }).label;
      result.push({
        provider_symbol: key,
        label: typeof label === "string" ? label : null,
        active: (entry as { active?: unknown }).active !== false,
      });
    }
    return result.length > 0 ? result : null;
  } catch {
    return null;
  }
}

function writeInstrumentPreference(items: EditableInstrument[]) {
  if (typeof window === "undefined") return;
  const cleaned = items
    .filter((i) => i.provider_symbol.trim())
    .map((i) => ({
      provider_symbol: i.provider_symbol.trim(),
      label: i.label?.trim() ? i.label.trim() : null,
      active: i.active,
    }));
  window.localStorage.setItem(INSTRUMENT_PREFERENCE_KEY, JSON.stringify(cleaned));
}

const DIRECTION_MODE_LABELS: Record<string, string> = {
  kombiniert: "Kombiniert (Long & Short)",
  "long-only": "Long-only",
  "short-only": "Short-only",
};

const NEW_PROFILE_DEFAULTS = {
  name: "",
  timezone_session: "Exchange-Zeitzone",
  signal_timing: "Schlusskurs",
  fill_timing: "nächster verfügbarer Bar-Open",
  order_type: "Market",
  fee_pct: 0.06,
  slippage_ticks: 2,
  starting_capital: 10000,
  quote_currency: "USD",
  position_sizing: "Fix 100% Kapital",
  compounding_rule: "Kein Compounding",
  leverage: 1,
  pyramiding: false,
  max_open_positions: 1,
  missing_bars_handling: "Bar überspringen",
  corporate_actions_handling: "Ignorieren",
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

export default function BatchesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <BatchesPageInner />
    </Suspense>
  );
}

function BatchesPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectVersion = searchParams.get("version");
  const loadBatchId = searchParams.get("batch");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [profiles, setProfiles] = useState<BacktestProfile[]>([]);
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [existingBatches, setExistingBatches] = useState<Batch[]>([]);

  const [profileMode, setProfileMode] = useState<"existing" | "new">("new");
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [newProfile, setNewProfile] = useState(NEW_PROFILE_DEFAULTS);
  const [creatingProfile, setCreatingProfile] = useState(false);

  const [selectedVersionIds, setSelectedVersionIds] = useState<string[]>(
    preselectVersion ? [preselectVersion] : [],
  );
  const [instruments, setInstruments] = useState<EditableInstrument[]>(
    DEFAULT_INSTRUMENTS.map((i) => ({ ...i, active: true })),
  );
  const [timeframe, setTimeframe] = useState("4h");
  const [periodStart, setPeriodStart] = useState("2021-01-01");
  const [periodEnd, setPeriodEnd] = useState("2024-12-31");
  const [directionMode, setDirectionMode] = useState<string | null>("kombiniert");
  const [legacyDirectionModes, setLegacyDirectionModes] = useState<string[] | null>(null);

  const [batch, setBatch] = useState<Batch | null>(null);
  const [preview, setPreview] = useState<PreviewRun[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [creditMax, setCreditMax] = useState(0);
  const [creditStatus, setCreditStatus] = useState<CreditStatus | null>(null);
  const [creditLoading, setCreditLoading] = useState(false);

  const refreshPreview = useCallback(async (batchId: string) => {
    try {
      const p = z.array(previewRunSchema).parse(await apiGet<PreviewRun[]>(`/batches/${batchId}/preview`));
      setPreview(p);
      if (p.length > 0 && creditMax === 0) {
        setCreditMax(p.length);
      }
    } catch {
      setPreview([]);
    }
  }, [creditMax]);

  const loadInitial = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = z.array(backtestProfileSchema).parse(await apiGet<BacktestProfile[]>("/backtest-profiles"));
      setProfiles(p);
      if (p.length > 0 && !loadBatchId) {
        setSelectedProfileId(p[0].id);
        setProfileMode("existing");
      }
      const v = z.array(versionSummarySchema).parse(await apiGet<VersionSummary[]>("/versions"));
      setVersions(v);
      setExistingBatches(z.array(batchSchema).parse(await apiGet<Batch[]>("/batches")));

      if (loadBatchId) {
        const loaded = batchSchema.parse(await apiGet<Batch>(`/batches/${loadBatchId}`));
        setBatch(loaded);
        setProfileMode("existing");
        setSelectedProfileId(loaded.backtest_profile_id);
        if (!p.some((profile) => profile.id === loaded.backtest_profile_id)) {
          const referenced = backtestProfileSchema.parse(
            await apiGet<BacktestProfile>(`/backtest-profiles/versions/${loaded.backtest_profile_id}`),
          );
          setProfiles((prev) => [...prev, referenced]);
        }
        setSelectedVersionIds(loaded.strategy_version_ids);
        const serverActive: EditableInstrument[] = loaded.instruments.map((i) => ({
          provider_symbol: i.provider_symbol,
          label: i.label ?? null,
          active: true,
        }));
        if (loaded.status === "entwurf") {
          const pref = readInstrumentPreference();
          const serverSymbols = new Set(
            serverActive.map((i) => i.provider_symbol.trim().toUpperCase()),
          );
          const inactiveFromPref: EditableInstrument[] = (pref ?? [])
            .filter(
              (i) => !serverSymbols.has(i.provider_symbol.trim().toUpperCase()),
            )
            .map((i) => ({ ...i, active: false }));
          setInstruments([...serverActive, ...inactiveFromPref]);
        } else {
          setInstruments(serverActive);
        }
        setTimeframe(loaded.timeframe);
        setPeriodStart(loaded.period_start);
        setPeriodEnd(loaded.period_end ?? "");
        setDirectionMode(loaded.direction_modes.length === 1 ? loaded.direction_modes[0] : null);
        setLegacyDirectionModes(
          loaded.status !== "entwurf" && loaded.direction_modes.length !== 1
            ? loaded.direction_modes
            : null,
        );
        await refreshPreview(loaded.id);
      } else {
        const pref = readInstrumentPreference();
        if (pref) {
          setInstruments(pref);
        }
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Daten konnten nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, [loadBatchId, refreshPreview]);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  const isConfirmed = batch != null && batch.status !== "entwurf";
  const isStandardBatch = !batch || batch.run_kind === "standard";

  const toggleVersion = (id: string) => {
    setSelectedVersionIds((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id],
    );
  };

  const updateInstrument = (idx: number, field: keyof Instrument, value: string) => {
    setInstruments((prev) => prev.map((i, n) => (n === idx ? { ...i, [field]: value } : i)));
  };

  const toggleInstrumentActive = (idx: number) => {
    setInstruments((prev) => prev.map((i, n) => (n === idx ? { ...i, active: !i.active } : i)));
  };

  const addInstrument = () => {
    setInstruments((prev) => [...prev, { provider_symbol: "", label: "", active: true }]);
  };

  const removeInstrument = (idx: number) => {
    setInstruments((prev) => prev.filter((_, n) => n !== idx));
  };

  const hasDuplicateProviderSymbol = (rows: EditableInstrument[]) => {
    const seen = new Set<string>();
    for (const row of rows) {
      const key = row.provider_symbol.trim();
      if (!key) continue;
      if (seen.has(key)) return true;
      seen.add(key);
    }
    return false;
  };

  const activeInstruments = instruments.filter((i) => i.active && i.provider_symbol.trim());

  const handleCreateProfile = async () => {
    setCreatingProfile(true);
    setError(null);
    try {
      const created = backtestProfileSchema.parse(
        await apiPostJson<BacktestProfile>("/backtest-profiles", newProfile),
      );
      setProfiles((prev) => [...prev, created]);
      setSelectedProfileId(created.id);
      setProfileMode("existing");
      setSuccess("Profil angelegt.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Profil konnte nicht angelegt werden.");
    } finally {
      setCreatingProfile(false);
    }
  };

  const handleSaveDraft = async () => {
    setError(null);
    setSuccess(null);
    if (!selectedProfileId) {
      setError("Bitte ein Backtest-Profil wählen oder anlegen.");
      return;
    }
    if (selectedVersionIds.length === 0) {
      setError("Bitte mindestens eine Strategieversion wählen.");
      return;
    }
    if (!directionMode || !(DIRECTION_MODES as readonly string[]).includes(directionMode)) {
      setError("Bitte genau einen gültigen Richtungsmodus wählen.");
      return;
    }
    if (hasDuplicateProviderSymbol(instruments)) {
      setError("Provider-Symbol ist bereits vorhanden.");
      return;
    }
    const activeRows = instruments.filter((i) => i.active && i.provider_symbol.trim());
    if (activeRows.length === 0) {
      setError("Bitte mindestens ein Instrument aktivieren.");
      return;
    }
    setSaving(true);
    try {
      const body = {
        backtest_profile_id: selectedProfileId,
        strategy_version_ids: selectedVersionIds,
        instruments: activeRows.map((i) => ({
          provider_symbol: i.provider_symbol.trim(),
          label: i.label?.trim() ? i.label.trim() : null,
        })),
        direction_modes: [directionMode],
        timeframe,
        period_start: periodStart,
        period_end: periodEnd || undefined,
      };
      const saved = batchSchema.parse(
        batch
          ? await apiPatch<Batch>(`/batches/${batch.id}`, body)
          : await apiPostJson<Batch>("/batches", body),
      );
      setBatch(saved);
      writeInstrumentPreference(instruments);
      await refreshPreview(saved.id);
      setSuccess("Entwurf gespeichert.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Speichern fehlgeschlagen.");
    } finally {
      setSaving(false);
    }
  };

  const handleCreditCheck = async () => {
    if (!batch) return;
    setCreditLoading(true);
    setError(null);
    try {
      const result = creditStatusSchema.parse(
        await apiGet<CreditStatus>(`/batches/${batch.id}/credit-check`),
      );
      setCreditStatus(result);
      if (creditMax < result.planned_actions) {
        setCreditMax(result.planned_actions);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Credit-Prüfung fehlgeschlagen.");
    } finally {
      setCreditLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!batch) return;
    setConfirming(true);
    setError(null);
    try {
      const confirmed = batchSchema.parse(
        await apiPostJson<Batch>(`/batches/${batch.id}/confirm`, { credit_max: creditMax }),
      );
      setBatch(confirmed);
      await refreshPreview(confirmed.id);
      setSuccess("Batch bestätigt — Runs sind angelegt.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Bestätigen fehlgeschlagen.");
    } finally {
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <Button variant="ghost" size="sm" className="mb-4" onClick={() => router.push("/quellen")}>
        <ArrowLeft className="mr-1 h-4 w-4" />
        Zurück zu Quellen
      </Button>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Batch-Konfiguration</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Instrumente, Zeitraum, Timeframe und Richtung für einen Vergleich mehrerer
            Strategieversionen festlegen.
          </p>
        </div>
        {batch && (
          <div className="flex gap-2">
            {!isStandardBatch && (
              <Badge variant="outline">
                {batch.run_kind === "holdout" ? "Historischer Holdout" : "Forward-Test"}
              </Badge>
            )}
            <Badge variant={isConfirmed ? "default" : "secondary"}>{batch.status}</Badge>
          </div>
        )}
      </div>

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

      {!loadBatchId && existingBatches.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Vorhandene Batches</CardTitle>
            <CardDescription>Ausführung eines bestehenden Batches wieder öffnen.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {existingBatches.map((existing) => (
              <div key={existing.id} className="flex flex-wrap items-center gap-3 rounded-md border border-border p-3 text-sm">
                <Badge variant={existing.status === "entwurf" ? "secondary" : "default"}>{existing.status}</Badge>
                <span>{existing.run_kind}</span>
                <span className="text-muted-foreground">{new Date(existing.created_at).toLocaleString("de-DE")}</span>
                <Button className="ml-auto" variant="outline" size="sm" onClick={() => router.push(`/batches?batch=${existing.id}`)}>
                  Ausführung öffnen
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Backtest-Profil */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Backtest-Profil</CardTitle>
          <CardDescription>
            Wiederverwendbares Profil — alle Runs dieses Batches nutzen dasselbe Profil.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {profiles.length > 0 && (
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-64">
                <SelectField
                  label="Vorhandenes Profil"
                  value={profileMode === "existing" ? selectedProfileId : ""}
                  options={profiles.map((p) => ({
                    value: p.id,
                    label: `${p.name} (v${p.version_number})`,
                  }))}
                  onChange={(v) => {
                    setSelectedProfileId(v);
                    setProfileMode("existing");
                  }}
                  disabled={isConfirmed}
                />
              </div>
              {!isConfirmed && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setProfileMode(profileMode === "new" ? "existing" : "new")}
                >
                  {profileMode === "new" ? "Vorhandenes nutzen" : "Neues Profil"}
                </Button>
              )}
            </div>
          )}

          {profileMode === "new" && !isConfirmed && (
            <div className="flex flex-col gap-4 rounded-md border border-border p-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label>Name</Label>
                  <Input
                    value={newProfile.name}
                    onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })}
                    placeholder="z. B. Standard"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Zeitzone / Handelssitzung</Label>
                  <Input
                    value={newProfile.timezone_session}
                    onChange={(e) => setNewProfile({ ...newProfile, timezone_session: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Signalzeitpunkt</Label>
                  <Input
                    value={newProfile.signal_timing}
                    onChange={(e) => setNewProfile({ ...newProfile, signal_timing: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Fill-Zeitpunkt</Label>
                  <Input
                    value={newProfile.fill_timing}
                    onChange={(e) => setNewProfile({ ...newProfile, fill_timing: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Ordertyp</Label>
                  <Input
                    value={newProfile.order_type}
                    onChange={(e) => setNewProfile({ ...newProfile, order_type: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Gebühren (%)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={newProfile.fee_pct}
                    onChange={(e) => setNewProfile({ ...newProfile, fee_pct: Number(e.target.value) })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Slippage (Ticks)</Label>
                  <Input
                    type="number"
                    value={newProfile.slippage_ticks}
                    onChange={(e) =>
                      setNewProfile({ ...newProfile, slippage_ticks: Number(e.target.value) })
                    }
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Startkapital</Label>
                  <Input
                    type="number"
                    value={newProfile.starting_capital}
                    onChange={(e) =>
                      setNewProfile({ ...newProfile, starting_capital: Number(e.target.value) })
                    }
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Quote-Währung</Label>
                  <Input
                    value={newProfile.quote_currency}
                    onChange={(e) => setNewProfile({ ...newProfile, quote_currency: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Positionsgröße & Compounding</Label>
                  <Input
                    value={newProfile.position_sizing}
                    onChange={(e) => setNewProfile({ ...newProfile, position_sizing: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Compounding-Regel</Label>
                  <Input
                    value={newProfile.compounding_rule}
                    onChange={(e) => setNewProfile({ ...newProfile, compounding_rule: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Leverage</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={newProfile.leverage}
                    onChange={(e) => setNewProfile({ ...newProfile, leverage: Number(e.target.value) })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Max. gleichzeitig offene Positionen</Label>
                  <Input
                    type="number"
                    value={newProfile.max_open_positions}
                    onChange={(e) =>
                      setNewProfile({ ...newProfile, max_open_positions: Number(e.target.value) })
                    }
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Umgang mit fehlenden Bars</Label>
                  <Input
                    value={newProfile.missing_bars_handling}
                    onChange={(e) =>
                      setNewProfile({ ...newProfile, missing_bars_handling: e.target.value })
                    }
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Umgang mit Corporate Actions</Label>
                  <Input
                    value={newProfile.corporate_actions_handling}
                    onChange={(e) =>
                      setNewProfile({ ...newProfile, corporate_actions_handling: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={newProfile.pyramiding}
                  onCheckedChange={(checked) =>
                    setNewProfile({ ...newProfile, pyramiding: checked === true })
                  }
                />
                <Label>Pyramiding erlaubt</Label>
              </div>
              <div className="flex justify-end">
                <Button
                  onClick={handleCreateProfile}
                  disabled={creatingProfile || !newProfile.name.trim()}
                >
                  {creatingProfile && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                  Profil anlegen
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Strategieversionen */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Strategieversionen</CardTitle>
          <CardDescription>Nur freigegebene Versionen sind wählbar.</CardDescription>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Noch keine freigegebenen Strategieversionen vorhanden.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {versions.map((v) => (
                <label
                  key={v.id}
                  className="flex items-center gap-3 rounded-md border border-border p-3 text-sm"
                >
                  <Checkbox
                    checked={selectedVersionIds.includes(v.id)}
                    onCheckedChange={() => toggleVersion(v.id)}
                    disabled={isConfirmed}
                  />
                  <span className="font-medium">{v.name ?? "Unbenannt"}</span>
                  <span className="text-muted-foreground">v{v.version_number}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    freigegeben {new Date(v.frozen_at).toLocaleDateString("de-DE")}
                  </span>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Instrumente */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Instrumente</CardTitle>
            <CardDescription>
              Provider-Symbole, nicht nur der fachliche Name. Deaktivierte Einträge bleiben
              sichtbar, erzeugen aber keine Runs.
            </CardDescription>
          </div>
          {!isConfirmed && (
            <Button variant="outline" size="sm" onClick={addInstrument}>
              <Plus className="mr-1 h-4 w-4" />
              Hinzufügen
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {activeInstruments.length === 0 && !isConfirmed && (
            <Alert variant="destructive" className="mb-3">
              <TriangleAlert aria-hidden="true" />
              <AlertDescription>Bitte mindestens ein Instrument aktivieren.</AlertDescription>
            </Alert>
          )}
          {hasDuplicateProviderSymbol(instruments) && !isConfirmed && (
            <Alert variant="destructive" className="mb-3">
              <TriangleAlert aria-hidden="true" />
              <AlertDescription>Provider-Symbol ist bereits vorhanden.</AlertDescription>
            </Alert>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                {!isConfirmed && <TableHead className="w-12">Aktiv</TableHead>}
                <TableHead>Provider-Symbol</TableHead>
                <TableHead>Label</TableHead>
                {!isConfirmed && <TableHead className="w-10" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {instruments.map((instr, idx) => (
                <TableRow
                  key={idx}
                  className={!instr.active && !isConfirmed ? "opacity-60" : undefined}
                >
                  {!isConfirmed && (
                    <TableCell>
                      <Checkbox
                        checked={instr.active}
                        onCheckedChange={() => toggleInstrumentActive(idx)}
                        aria-label={`Instrument ${instr.provider_symbol || "neu"} aktiv`}
                      />
                    </TableCell>
                  )}
                  <TableCell>
                    {isConfirmed ? (
                      <span className="font-mono">{instr.provider_symbol}</span>
                    ) : (
                      <div className="flex flex-wrap items-center gap-2">
                        <Input
                          value={instr.provider_symbol}
                          onChange={(e) => updateInstrument(idx, "provider_symbol", e.target.value)}
                          className="h-8 w-56 font-mono text-sm"
                        />
                        {!instr.active && (
                          <Badge variant="secondary">Nicht verwendet</Badge>
                        )}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    {isConfirmed ? (
                      <span>{instr.label}</span>
                    ) : (
                      <Input
                        value={instr.label ?? ""}
                        onChange={(e) => updateInstrument(idx, "label", e.target.value)}
                        className="h-8 max-w-48 text-sm"
                      />
                    )}
                  </TableCell>
                  {!isConfirmed && (
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={() => removeInstrument(idx)}
                        aria-label="Instrument entfernen"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Zeitraum & Timeframe */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Zeitraum & Timeframe</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="flex flex-col gap-1.5">
            <Label>Timeframe</Label>
            <Input value={timeframe} onChange={(e) => setTimeframe(e.target.value)} disabled={isConfirmed} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Von</Label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              disabled={isConfirmed || !isStandardBatch}
              max={isStandardBatch ? "2024-12-31" : undefined}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs disabled:opacity-50"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Bis</Label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              disabled={isConfirmed || !isStandardBatch}
              max={isStandardBatch ? "2024-12-31" : undefined}
              placeholder={!isStandardBatch && batch?.run_kind === "forward_test" ? "offen" : undefined}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs disabled:opacity-50"
            />
          </div>
        </CardContent>
      </Card>

      {/* Richtungsmodus */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Richtungsmodus</CardTitle>
          <CardDescription>
            Genau ein Modus je Batch — gilt für Standard-, Holdout- und Forward-Batches.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div
            role="radiogroup"
            aria-labelledby="direction-mode-legend"
            aria-describedby="direction-mode-help"
            className="flex flex-col gap-2"
          >
            <p id="direction-mode-legend" className="text-sm font-medium">
              Richtung
            </p>
            <p id="direction-mode-help" className="text-xs text-muted-foreground">
              Pro Strategieversion und aktivem Instrument wird genau ein Run angelegt.
            </p>
            <div className="mt-2 flex flex-col gap-2">
              {DIRECTION_MODES.map((mode) => {
                const label =
                  mode === "kombiniert"
                    ? "Long & Short"
                    : mode === "long-only"
                      ? "Nur Long"
                      : "Nur Short";
                return (
                  <label key={mode} className="flex items-center gap-3 text-sm">
                    <input
                      type="radio"
                      name="direction-mode"
                      value={mode}
                      checked={directionMode === mode}
                      onChange={() => {
                        setDirectionMode(mode);
                        setLegacyDirectionModes(null);
                      }}
                      disabled={isConfirmed}
                      className="size-4 cursor-pointer accent-primary disabled:cursor-not-allowed disabled:opacity-50"
                    />
                    {label}
                  </label>
                );
              })}
            </div>
          </div>

          <p className="text-sm text-muted-foreground">
            Aktiver Modus:{" "}
            <span className="font-medium text-foreground">
              {directionMode
                ? DIRECTION_MODE_LABELS[directionMode] ?? directionMode
                : "keiner ausgewählt"}
            </span>
          </p>

          {legacyDirectionModes && legacyDirectionModes.length > 0 && (
            <Alert>
              <TriangleAlert aria-hidden="true" />
              <AlertDescription>
                Historischer Batch mit mehreren Richtungsmodi (
                {legacyDirectionModes
                  .map((m) => DIRECTION_MODE_LABELS[m] ?? m)
                  .join(", ")}
                ) — schreibgeschützt.
              </AlertDescription>
            </Alert>
          )}

          {directionMode && !DIRECTION_MODES.includes(directionMode as (typeof DIRECTION_MODES)[number]) && (
            <Alert variant="destructive">
              <TriangleAlert aria-hidden="true" />
              <AlertDescription>
                Unbekannter Richtungswert &bdquo;{directionMode}&ldquo; — Speichern blockiert.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Aktionsleiste */}
      <Card className="mb-6 border-2 border-border">
        <CardHeader>
          <CardTitle>Vorschau & Bestätigung</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {!isConfirmed && (
            <div className="flex justify-end">
              <Button onClick={handleSaveDraft} disabled={saving}>
                {saving && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                Entwurf speichern
              </Button>
            </div>
          )}

          {batch && (
            <>
              <div>
                <p className="mb-2 text-sm font-medium">
                  Geplante Runs ({preview.length}): Strategieversion × Instrument × Richtungsmodus
                </p>
                {preview.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">
                    Keine Runs vorhanden — Konfiguration unvollständig.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Strategieversion</TableHead>
                        <TableHead>Instrument</TableHead>
                        <TableHead>Richtungsmodus</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {preview.map((r, i) => (
                        <TableRow key={i}>
                          <TableCell className="font-mono text-xs">
                            {versions.find((v) => v.id === r.strategy_version_id)?.name ??
                              r.strategy_version_id}
                          </TableCell>
                          <TableCell className="font-mono">{r.provider_symbol}</TableCell>
                          <TableCell>{DIRECTION_MODE_LABELS[r.direction_mode] ?? r.direction_mode}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>

              {!isConfirmed && (
                <>
                  <div className="rounded-md border border-border p-4">
                    <div className="mb-3 flex items-center justify-between">
                      <p className="text-sm font-medium">Credit-Gate</p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleCreditCheck}
                        disabled={creditLoading}
                      >
                        {creditLoading && <Loader className="mr-1 h-3 w-3 animate-spin" />}
                        Credits prüfen
                      </Button>
                    </div>

                    {creditStatus && (
                      <div className="grid gap-3 text-sm">
                        <div className="flex flex-wrap gap-4">
                          <div>
                            <span className="text-muted-foreground">Geplante Aktionen:</span>{" "}
                            <span className="font-mono font-medium">{creditStatus.planned_actions}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Guthaben:</span>{" "}
                            <span className="font-mono font-medium">{creditStatus.credit_balance}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Verbleibend:</span>{" "}
                            <span
                              className={`font-mono font-medium ${creditStatus.credit_remaining < 0 ? "text-red-600" : ""}`}
                            >
                              {creditStatus.credit_remaining}
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                          <span>Tarif: {creditStatus.tier}</span>
                          <span>Reset: {creditStatus.reset}</span>
                        </div>

                        <div className="flex flex-col gap-1.5">
                          <Label>
                            Max. Credits für diesen Batch
                          </Label>
                          <Input
                            type="number"
                            min={creditStatus.planned_actions}
                            value={creditMax}
                            onChange={(e) => setCreditMax(Number(e.target.value))}
                            className="w-32 font-mono"
                          />
                        </div>

                        {creditStatus.blocked && creditStatus.block_reason && (
                          <Alert variant="destructive">
                            <TriangleAlert aria-hidden="true" />
                            <AlertDescription>{creditStatus.block_reason}</AlertDescription>
                          </Alert>
                        )}
                      </div>
                    )}

                    {!creditStatus && !creditLoading && (
                      <p className="text-sm text-muted-foreground">
                        Credits vor dem Start prüfen, um den Verbrauch abzuschätzen.
                      </p>
                    )}
                  </div>

                  <div className="flex justify-end">
                    <Button
                      variant="default"
                      onClick={handleConfirm}
                      disabled={confirming || preview.length === 0 || creditMax < preview.length}
                    >
                      {confirming && <Loader className="mr-1 h-4 w-4 animate-spin" />}
                      Batch bestätigen
                    </Button>
                  </div>
                </>
              )}
              {isConfirmed && batch.credit_balance != null && (
                <div className="rounded-md border border-border p-4">
                  <p className="mb-2 text-sm font-medium">Credit-Snapshot (bei Bestätigung)</p>
                  <div className="grid gap-2 text-sm">
                    <div className="flex flex-wrap gap-4">
                      <span>
                        <span className="text-muted-foreground">Max:</span>{" "}
                        <span className="font-mono">{batch.credit_max}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Guthaben:</span>{" "}
                        <span className="font-mono">{batch.credit_balance}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Verbleibend:</span>{" "}
                        <span className="font-mono">{batch.credit_remaining}</span>
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                      <span>Tarif: {batch.credit_tier}</span>
                      <span>Reset: {batch.credit_reset}</span>
                      <span>Geprüft: {batch.credit_checked_at ? new Date(batch.credit_checked_at).toLocaleString("de-DE") : "-"}</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {isConfirmed && (
        <BatchAusfuehrung
          batchId={batch!.id}
          versions={versions}
          creditMax={batch!.credit_max ?? 0}
          creditBalance={batch!.credit_balance}
          creditRemaining={batch!.credit_remaining}
          creditTier={batch!.credit_tier}
          creditReset={batch!.credit_reset}
          creditCheckedAt={batch!.credit_checked_at}
          onClose={() => {}}
        />
      )}
    </div>
  );
}
