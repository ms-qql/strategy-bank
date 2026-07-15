"use client";

import { useState } from "react";
import { Loader } from "lucide-react";
import { apiPost, ApiError } from "@/lib/api-client";
import { extractionRunSchema, type ExtractionRun } from "@/lib/schemas/extraction";
import { Button } from "@/components/ui/button";

interface Props {
  sourceId: string;
  variant: "start" | "retry";
  onStarted: (run: ExtractionRun) => void;
}

export function ExtrahierenButton({ sourceId, variant, onStarted }: Props) {
  const [laden, setLaden] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  async function handleClick() {
    setFehler(null);
    setLaden(true);
    try {
      const data = await apiPost<unknown>(`/sources/${sourceId}/extractions`);
      onStarted(extractionRunSchema.parse(data));
    } catch (e) {
      setFehler(
        e instanceof ApiError ? e.message : "Extraktion konnte nicht gestartet werden.",
      );
    } finally {
      setLaden(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        size="sm"
        variant={variant === "retry" ? "outline" : "default"}
        onClick={handleClick}
        disabled={laden}
      >
        {laden && <Loader className="animate-spin" />}
        {variant === "retry" ? "Erneut extrahieren" : "Extrahieren"}
      </Button>
      {fehler && (
        <p className="text-xs text-destructive" role="alert">
          {fehler}
        </p>
      )}
    </div>
  );
}
