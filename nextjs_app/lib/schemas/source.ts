import { z } from "zod";

// Max. Quellgröße (PROJ-20: 25 MB für Dokumentimport).
export const MAX_SOURCE_BYTES = 25 * 1024 * 1024;

export const sourceTypeSchema = z.enum([
  "text",
  "markdown_file",
  "pdf_file",
  "epub_file",
  "mobi_file",
]);
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
