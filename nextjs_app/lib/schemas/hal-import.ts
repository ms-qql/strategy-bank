import { z } from "zod";

export const halImportFileResultSchema = z.object({
  origin_path: z.string(),
  content_hash: z.string(),
  status: z.enum(["importiert", "unverändert", "aktualisiert", "fehlerhaft"]),
  error_message: z.string().nullable().optional(),
  strategy_name: z.string().nullable().optional(),
});

export const halImportResponseSchema = z.object({
  import_run_id: z.string(),
  total: z.number().int(),
  files: z.array(halImportFileResultSchema),
});

export const halImportRunRowSchema = z.object({
  id: z.string(),
  total_files: z.number().int(),
  status_imported: z.number().int(),
  status_unchanged: z.number().int(),
  status_updated: z.number().int(),
  status_failed: z.number().int(),
  created_at: z.string(),
});

export const halImportedFileRowSchema = z.object({
  id: z.string(),
  import_run_id: z.string(),
  origin_path: z.string(),
  content_hash: z.string(),
  import_version: z.number().int(),
  processing_status: z.string(),
  error_message: z.string().nullable(),
  created_at: z.string(),
});

export const halUnassignedSchema = z.object({
  id: z.string(),
  imported_file_id: z.string(),
  strategy_name: z.string(),
  asset: z.string(),
  timeframe: z.string(),
  period_start: z.string(),
  period_end: z.string().nullable(),
  net_return_pct: z.number(),
  max_drawdown_pct: z.number(),
  trade_count: z.number().int(),
  sortino_ratio: z.number().nullable(),
  profit_factor: z.number().nullable(),
  sharpe_ratio: z.number().nullable(),
  import_origin_path: z.string(),
  suggested_version_id: z.string().nullable(),
  suggested_version_name: z.string().nullable(),
  strategy_version_id: z.string().nullable(),
  created_at: z.string(),
});

export const versionSummarySchema = z.object({
  id: z.string(),
  family_id: z.string(),
  version_number: z.number().int(),
  name: z.string().nullable(),
  frozen_at: z.string(),
});

export type HalImportFileResult = z.infer<typeof halImportFileResultSchema>;
export type HalImportResponse = z.infer<typeof halImportResponseSchema>;
export type HalImportRunRow = z.infer<typeof halImportRunRowSchema>;
export type HalImportedFileRow = z.infer<typeof halImportedFileRowSchema>;
export type HalUnassigned = z.infer<typeof halUnassignedSchema>;
export type VersionSummary = z.infer<typeof versionSummarySchema>;

export const STATUS_LABELS: Record<string, string> = {
  importiert: "Importiert",
  unverändert: "Unverändert",
  aktualisiert: "Aktualisiert",
  fehlerhaft: "Fehlerhaft",
};

export const STATUS_BADGE_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  importiert: "default",
  unverändert: "outline",
  aktualisiert: "secondary",
  fehlerhaft: "destructive",
};
