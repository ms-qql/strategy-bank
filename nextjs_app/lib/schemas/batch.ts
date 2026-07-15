import { z } from "zod";

export const DIRECTION_MODES = ["kombiniert", "long-only", "short-only"] as const;

export const instrumentSchema = z.object({
  provider_symbol: z.string().min(1),
  label: z.string().nullable().optional(),
});
export type Instrument = z.infer<typeof instrumentSchema>;

export const backtestProfileWriteSchema = z.object({
  name: z.string().min(1),
  timezone_session: z.string().min(1),
  signal_timing: z.string().min(1),
  fill_timing: z.string().min(1),
  order_type: z.string().min(1),
  fee_pct: z.number(),
  slippage_ticks: z.number(),
  starting_capital: z.number(),
  quote_currency: z.string().min(1),
  position_sizing: z.string().min(1),
  compounding_rule: z.string().min(1),
  leverage: z.number(),
  pyramiding: z.boolean(),
  max_open_positions: z.number().int(),
  missing_bars_handling: z.string().min(1),
  corporate_actions_handling: z.string().min(1),
});
export type BacktestProfileWrite = z.infer<typeof backtestProfileWriteSchema>;

export const backtestProfileSchema = backtestProfileWriteSchema.extend({
  id: z.string(),
  family_id: z.string(),
  version_number: z.number().int(),
  created_at: z.string(),
});
export type BacktestProfile = z.infer<typeof backtestProfileSchema>;

export const versionSummarySchema = z.object({
  id: z.string(),
  family_id: z.string(),
  version_number: z.number().int(),
  name: z.string().nullable(),
  frozen_at: z.string(),
});
export type VersionSummary = z.infer<typeof versionSummarySchema>;

export const batchSchema = z.object({
  id: z.string(),
  backtest_profile_id: z.string(),
  timeframe: z.string(),
  period_start: z.string(),
  period_end: z.string().nullable(),
  run_kind: z.enum(["standard", "holdout", "forward_test"]),
  status: z.enum(["entwurf", "bestätigt"]),
  confirmed_at: z.string().nullable(),
  created_at: z.string(),
  strategy_version_ids: z.array(z.string()),
  instruments: z.array(instrumentSchema),
  direction_modes: z.array(z.string()),
});
export type Batch = z.infer<typeof batchSchema>;

export const previewRunSchema = z.object({
  strategy_version_id: z.string(),
  provider_symbol: z.string(),
  direction_mode: z.string(),
});
export type PreviewRun = z.infer<typeof previewRunSchema>;

export const holdoutStatusSchema = z.object({
  family_id: z.string(),
  consumed: z.boolean(),
  consumed_at: z.string().nullable(),
});
export type HoldoutStatus = z.infer<typeof holdoutStatusSchema>;
