import { z } from "zod";

// Max. Quellgröße (Default lt. Spec 2 MB). Client-Vorprüfung; Backend prüft verbindlich.
export const MAX_SOURCE_BYTES = 2 * 1024 * 1024;

export const sourceTypeSchema = z.enum(["text", "markdown_file"]);
export type SourceType = z.infer<typeof sourceTypeSchema>;

// Antwortform von GET /sources und POST /sources.
export const sourceSchema = z.object({
  id: z.string(),
  source_hash: z.string(),
  source_type: sourceTypeSchema,
  filename: z.string().nullable(),
  captured_at: z.string(), // ISO-8601 UTC
  extraction_status: z.string(), // MVP: "noch nicht extrahiert"
});
export type Source = z.infer<typeof sourceSchema>;

export const sourceListSchema = z.array(sourceSchema);
