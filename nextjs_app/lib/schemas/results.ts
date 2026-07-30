import { z } from "zod";

export const resultRowSchema = z.object({
  run_id: z.string(),
  strategy_id: z.string().nullable(),
  strategy_name: z.string(),
  strategy_version_number: z.number().int().nullable(),
  strategy_family_id: z.string().nullable(),
  category: z.string().nullable(),
  instrument: z.string(),
  direction: z.string().nullable(),
  result_type: z.string(),
  status: z.string().nullable(),
  error_message: z.string().nullable(),

  profile_id: z.string().nullable(),
  profile_name: z.string().nullable(),
  profile_version_number: z.number().int().nullable(),
  profile_family_id: z.string().nullable(),

  timeframe: z.string(),
  period_start: z.string(),
  period_end: z.string().nullable(),

  net_profit_pct: z.number().nullable(),
  cagr_pct: z.number().nullable(),
  trade_count: z.number().int().nullable(),
  max_drawdown_pct: z.number().nullable(),
  sharpe_ratio: z.number().nullable(),
  sortino_ratio: z.number().nullable(),
  profit_factor: z.number().nullable(),
  calmar_ratio: z.number().nullable(),

  trades_per_year: z.number().nullable(),
  is_comparable: z.boolean(),
  success_group: z.boolean(),
  shortlisted: z.boolean(),

  report_link: z.string().nullable(),
  incomplete: z.boolean(),
  low_activity: z.boolean(),

  import_origin_path: z.string().nullable(),
  import_hash: z.string().nullable(),
  import_version: z.number().int().nullable(),
  import_created_at: z.string().nullable(),
  strategy_version_status: z.string().nullable(),
  source_name: z.string().nullable(),
  mts_compatibility: z.string().nullable(),
  robustness_status: z.string().nullable(),

  created_at: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
});

export type ResultRow = z.infer<typeof resultRowSchema>;

export const RESULT_TYPE_LABELS: Record<string, string> = {
  standard: "Research",
  holdout: "Historisches Holdout",
  forward_test: "Echter Forward-Test",
  "HAL-Import": "HAL-Import",
};

export const DIRECTION_MODE_LABELS: Record<string, string> = {
  kombiniert: "Kombiniert",
  "long-only": "Long-only",
  "short-only": "Short-only",
};

export const STATUS_LABELS: Record<string, string> = {
  geplant: "Geplant",
  bestätigt: "Bestätigt",
  in_queue: "In Queue",
  läuft: "Läuft",
  erfolgreich: "Erfolgreich",
  fehlgeschlagen: "Fehlgeschlagen",
  abgebrochen: "Abgebrochen",
};

export const CATEGORIES = [
  "Trendfolge",
  "Mean Reversion",
  "Breakout",
  "Volatilität",
  "Momentum",
  "Saison/Zeit",
  "Preis-/Candlestick-Muster",
  "Hybrid",
  "Sonstige",
] as const;
