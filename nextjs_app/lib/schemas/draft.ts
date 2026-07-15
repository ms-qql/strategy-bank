import { z } from "zod";

export const parameterEditSchema = z.object({
  name: z.string().min(1),
  value: z.string(),
  unit: z.string().nullable().optional(),
  allowed_range: z.string().nullable().optional(),
});
export type ParameterEdit = z.infer<typeof parameterEditSchema>;

export const draftUpdateSchema = z.object({
  name: z.string().optional(),
  thesis: z.string().optional(),
  category: z.string().optional(),
  direction: z.enum(["kombiniert", "long-only", "short-only"]).optional(),
  entry_rule: z.string().nullable().optional(),
  exit_rule: z.string().nullable().optional(),
  warmup_requirement: z.string().nullable().optional(),
  simultaneous_entry_exit_behavior: z.string().nullable().optional(),
  reversal_behavior: z.string().nullable().optional(),
  status_reason: z.string().nullable().optional(),
  parameters: z.array(parameterEditSchema).optional(),
});
export type DraftUpdate = z.infer<typeof draftUpdateSchema>;

export const markUntestableSchema = z.object({
  reason: z.string().min(1),
});
export type MarkUntestableRequest = z.infer<typeof markUntestableSchema>;

export const versionParameterSchema = z.object({
  name: z.string(),
  value: z.string(),
  unit: z.string().nullable(),
  allowed_range: z.string().nullable(),
});
export type VersionParameter = z.infer<typeof versionParameterSchema>;

export const versionListItemSchema = z.object({
  id: z.string(),
  draft_id: z.string(),
  version_number: z.number().int().positive(),
  frozen_at: z.string(),
  created_at: z.string(),
});
export type VersionListItem = z.infer<typeof versionListItemSchema>;

export const userDiffEntrySchema = z.object({
  field: z.string(),
  from: z.unknown().nullable(),
  to: z.unknown().nullable(),
});

export const versionReadSchema = z.object({
  id: z.string(),
  draft_id: z.string(),
  family_id: z.string(),
  version_number: z.number().int().positive(),
  source_id: z.string(),
  source_hash: z.string(),
  extraction_model: z.string(),
  prompt_version: z.string(),
  snapshot: z.record(z.string(), z.unknown()),
  frozen_at: z.string(),
  created_at: z.string(),
  parameters: z.array(versionParameterSchema),
  user_diff: z.array(userDiffEntrySchema),
});
export type VersionRead = z.infer<typeof versionReadSchema>;
