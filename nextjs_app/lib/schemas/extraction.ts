import { z } from "zod";

const statusSchema = z.enum([
  "läuft",
  "abgeschlossen",
  "keine Treffer",
  "fehlgeschlagen",
]);
export type ExtractionStatus = z.infer<typeof statusSchema>;

const draftStatusSchema = z.enum([
  "Entwurf",
  "nicht testbar",
  "gesperrt (unvollständig)",
]);
export type DraftStatus = z.infer<typeof draftStatusSchema>;

const directionSchema = z.enum(["kombiniert", "long-only", "short-only"]);
export type Direction = z.infer<typeof directionSchema>;

export const extractionRunSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  status: statusSchema,
  model: z.string(),
  prompt_version: z.string(),
  started_at: z.string(),
  finished_at: z.string().nullable(),
  error_message: z.string().nullable(),
});
export type ExtractionRun = z.infer<typeof extractionRunSchema>;

export const parameterSchema = z.object({
  name: z.string(),
  value: z.string(),
  unit: z.string().nullable(),
  allowed_range: z.string().nullable(),
  is_proposal: z.boolean(),
});
export type Parameter = z.infer<typeof parameterSchema>;

export const citationSchema = z.object({
  rule_field: z.string(),
  excerpt: z.string(),
  line_reference: z.string().nullable(),
});
export type Citation = z.infer<typeof citationSchema>;

export const openQuestionSchema = z.object({
  description: z.string(),
  reasoning: z.string(),
});
export type OpenQuestion = z.infer<typeof openQuestionSchema>;

export const draftSchema = z.object({
  id: z.string(),
  extraction_run_id: z.string(),
  source_hash: z.string(),
  name: z.string(),
  thesis: z.string(),
  category: z.string(),
  direction: directionSchema,
  entry_rule: z.string().nullable(),
  exit_rule: z.string().nullable(),
  warmup_requirement: z.string().nullable(),
  simultaneous_entry_exit_behavior: z.string().nullable(),
  reversal_behavior: z.string().nullable(),
  status: draftStatusSchema,
  status_reason: z.string().nullable(),
  created_at: z.string(),
  parameters: z.array(parameterSchema),
  citations: z.array(citationSchema),
  open_questions: z.array(openQuestionSchema),
});
export type Draft = z.infer<typeof draftSchema>;

export const extractionRunDetailSchema = extractionRunSchema.extend({
  drafts: z.array(draftSchema),
});
export type ExtractionRunDetail = z.infer<typeof extractionRunDetailSchema>;
