import { z } from "zod";

export const analysisRunReadSchema = z.object({
  id: z.string(),
  comparison_group: z.string(),
  success_definition: z.record(z.string(), z.number()),
  total_analyzed: z.number().int(),
  total_excluded: z.number().int(),
  excluded_reasons: z.record(z.string(), z.number().int()),
  created_at: z.string(),
});

export const analysisRunRowReadSchema = z.object({
  id: z.string(),
  strategy_name: z.string(),
  strategy_version_id: z.string().nullable(),
  calmar_ratio: z.number().nullable(),
  sortino_ratio: z.number().nullable(),
  trades_per_year: z.number().nullable(),
  is_success: z.boolean(),
  indicators: z.array(z.string()),
  indicator_count: z.number().int(),
  parameter_count: z.number().int(),
  entry_archetype: z.string(),
  exit_archetype: z.string(),
  category: z.string().nullable(),
  direction: z.string().nullable(),
  mts_compatibility: z.string().nullable(),
});

export const cohortRowSchema = z.object({
  value: z.string(),
  success: z.number().int(),
  total: z.number().int(),
  success_quote: z.number().nullable(),
  lift: z.number().nullable(),
  median_calmar: z.number().nullable(),
});

export const analysisRunDetailReadSchema = analysisRunReadSchema.extend({
  rows: z.array(analysisRunRowReadSchema),
  cohort: z.array(cohortRowSchema),
});

export type AnalysisRunRead = z.infer<typeof analysisRunReadSchema>;
export type AnalysisRunRowRead = z.infer<typeof analysisRunRowReadSchema>;
export type CohortRow = z.infer<typeof cohortRowSchema>;
export type AnalysisRunDetailRead = z.infer<typeof analysisRunDetailReadSchema>;

export const AXIS_OPTIONS: { value: string; label: string }[] = [
  { value: "indicator", label: "Indikator" },
  { value: "indicator_count", label: "Indikatorzahl" },
  { value: "parameter_count", label: "Parameterzahl" },
  { value: "entry_archetype", label: "Entry-Archetyp" },
  { value: "exit_archetype", label: "Exit-Archetyp" },
  { value: "category", label: "Kategorie" },
  { value: "direction", label: "Richtung" },
  { value: "mts_compatibility", label: "MTS-Eignung" },
];
