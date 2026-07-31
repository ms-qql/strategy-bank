import { z } from "zod";

export const regimeModelVersionCreateSchema = z.object({
  name: z.string().min(1),
  course_source: z.string().default("close"),
  zscore_length: z.number().int().min(2).default(75),
  hma_length: z.number().int().min(1).default(2),
  confirmation_candles: z.number().int().min(1).default(2),
  upper_threshold: z.number(),
  lower_threshold: z.number(),
});

export const regimeModelVersionReadSchema = z.object({
  id: z.string(),
  name: z.string(),
  course_source: z.string(),
  zscore_length: z.number().int(),
  hma_length: z.number().int(),
  confirmation_candles: z.number().int(),
  upper_threshold: z.number(),
  lower_threshold: z.number(),
  created_at: z.string(),
});

export const regimeSeriesReadSchema = z.object({
  id: z.string(),
  provider_symbol: z.string(),
  asset: z.string(),
  timeframe: z.string(),
  model_version_id: z.string(),
  model_version_name: z.string().nullable(),
  period_start: z.string().nullable(),
  period_end: z.string().nullable(),
  bar_count: z.number().int(),
  unavailable_count: z.number().int(),
  last_refreshed_at: z.string().nullable(),
});

export const regimeCoverageIssueSchema = z.object({
  issue_type: z.string(),
  detail: z.string(),
});

export const regimeBarReadSchema = z.object({
  bar_time: z.string(),
  regime: z.string(),
});

export const regimeSeriesDetailReadSchema = regimeSeriesReadSchema.extend({
  bars: z.array(regimeBarReadSchema).nullable(),
  coverage_issues: z.array(regimeCoverageIssueSchema),
});

export const resultTradeReadSchema = z.object({
  id: z.string(),
  hal_result_id: z.string(),
  direction: z.string(),
  entry_time: z.string(),
  exit_time: z.string(),
  net_pnl: z.number(),
  data_source: z.string(),
  created_at: z.string(),
});

export const fetchTradesResponseSchema = z.object({
  hal_result_id: z.string(),
  trades_count: z.number().int(),
});

export const regimeDetailRowSchema = z.object({
  regime: z.string(),
  trade_count: z.number().int(),
  net_pnl: z.number(),
  max_drawdown_pct: z.number().nullable(),
  pnl_share_pct: z.number(),
  calmar_ratio: z.number().nullable(),
  sortino_ratio: z.number().nullable(),
  small_sample: z.boolean(),
});

export const regimeEvaluationReadSchema = z.object({
  id: z.string(),
  hal_result_id: z.string(),
  series_id: z.string(),
  model_version_id: z.string(),
  model_version_name: z.string().nullable(),
  coverage_pct: z.number(),
  assignment_rule: z.string(),
  is_incomplete: z.boolean(),
  total_result_pnl: z.number(),
  regime_details: z.array(regimeDetailRowSchema),
  regime_dominance: z.string().nullable(),
  created_at: z.string(),
});

export const regimeImportResponseSchema = z.object({
  series_id: z.string(),
  bars_inserted: z.number().int(),
  bars_skipped: z.number().int(),
});

export type RegimeModelVersionCreate = z.infer<typeof regimeModelVersionCreateSchema>;
export type RegimeModelVersionRead = z.infer<typeof regimeModelVersionReadSchema>;
export type RegimeSeriesRead = z.infer<typeof regimeSeriesReadSchema>;
export type RegimeSeriesDetailRead = z.infer<typeof regimeSeriesDetailReadSchema>;
export type RegimeCoverageIssue = z.infer<typeof regimeCoverageIssueSchema>;
export type RegimeBarRead = z.infer<typeof regimeBarReadSchema>;
export type ResultTradeRead = z.infer<typeof resultTradeReadSchema>;
export type FetchTradesResponse = z.infer<typeof fetchTradesResponseSchema>;
export type RegimeDetailRow = z.infer<typeof regimeDetailRowSchema>;
export type RegimeEvaluationRead = z.infer<typeof regimeEvaluationReadSchema>;
export type RegimeImportResponse = z.infer<typeof regimeImportResponseSchema>;

export const REGIME_LABELS: Record<string, string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  sideways: "Seitwärts",
  "ohne Regimezuordnung": "Ohne Regimezuordnung",
};

export const REGIME_BADGE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  bullish: "default",
  bearish: "destructive",
  sideways: "secondary",
  "ohne Regimezuordnung": "outline",
};

export const ISSUE_TYPE_LABELS: Record<string, string> = {
  gap: "Lücke",
  overlapping_version: "Überlappende Version",
  timeframe_mismatch: "Timeframe-Fehlanpassung",
};
