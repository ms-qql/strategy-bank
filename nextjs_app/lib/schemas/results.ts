import { z } from "zod";

export const resultRowSchema = z.object({
  run_id: z.string(),
  strategy_id: z.string(),
  strategy_name: z.string(),
  strategy_version_number: z.number().int(),
  strategy_family_id: z.string(),
  category: z.string(),
  instrument: z.string(),
  direction: z.string(),
  result_type: z.string(),
  status: z.string(),
  error_message: z.string().nullable(),

  profile_id: z.string(),
  profile_name: z.string(),
  profile_version_number: z.number().int(),
  profile_family_id: z.string(),

  timeframe: z.string(),
  period_start: z.string(),
  period_end: z.string().nullable(),

  net_profit_pct: z.number().nullable(),
  cagr_pct: z.number().nullable(),
  trade_count: z.number().int().nullable(),
  max_drawdown_pct: z.number().nullable(),
  sharpe_ratio: z.number().nullable(),
  profit_factor: z.number().nullable(),
  calmar_ratio: z.number().nullable(),

  report_link: z.string().nullable(),
  incomplete: z.boolean(),
  low_activity: z.boolean(),

  created_at: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
});

export type ResultRow = z.infer<typeof resultRowSchema>;

export const RESULT_TYPE_LABELS: Record<string, string> = {
  standard: "Research",
  holdout: "Historisches Holdout",
  forward_test: "Echter Forward-Test",
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
