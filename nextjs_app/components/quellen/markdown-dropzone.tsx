"use client";

import { useEffect, useRef, useState } from "react";
import { FileUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { MAX_SOURCE_BYTES, type SourceType } from "@/lib/schemas/source";

const ALLOWED_EXTENSIONS: Record<string, SourceType> = {
  ".md": "markdown_file",
  ".pdf": "pdf_file",
  ".epub": "epub_file",
  ".mobi": "mobi_file",
};

const ACCEPT = ".md,.pdf,.epub,.mobi";

const EXT_LABELS: Record<string, string> = {
  ".md": "Markdown-Datei",
  ".pdf": "PDF-Dokument",
  ".epub": "EPUB-E-Book",
  ".mobi": "MOBI-E-Book",
};

const LIMIT_MB = Math.ceil(MAX_SOURCE_BYTES / (1024 * 1024));

interface DocumentDropzoneProps {
  datei: File | null;
  onChange: (file: File | null, error: string | null) => void;
}

export function MarkdownDropzone({ datei, onChange }: DocumentDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (datei === null && inputRef.current) {
      inputRef.current.value = "";
    }
  }, [datei]);

  function applyFile(file: File | null | undefined) {
    if (!file) return;
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!(ext in ALLOWED_EXTENSIONS)) {
      onChange(null, "Nur .md-, .pdf-, .epub- und .mobi-Dateien werden unterstützt.");
      return;
    }
    if (file.size === 0) {
      onChange(null, "Quelle enthält keinen Inhalt.");
      return;
    }
    if (file.size > MAX_SOURCE_BYTES) {
      onChange(null, `Datei überschreitet das Größenlimit von ${LIMIT_MB} MB.`);
      return;
    }
    onChange(file, null);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    const files = e.dataTransfer.files;
    if (files.length === 0) {
      onChange(null, "Nur .md-, .pdf-, .epub- und .mobi-Dateien werden unterstützt.");
      return;
    }
    if (files.length > 1) {
      onChange(null, "Bitte genau eine Datei ablegen.");
      return;
    }
    applyFile(files[0]);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    if (!dragActive) setDragActive(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setDragActive(false);
  }

  function openDialog() {
    inputRef.current?.click();
  }

  const fileExt = datei
    ? datei.name.slice(datei.name.lastIndexOf(".")).toLowerCase()
    : null;
  const formatLabel = fileExt && fileExt in EXT_LABELS ? EXT_LABELS[fileExt] : null;

  return (
    <div className="flex flex-col gap-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Dokument hier ablegen oder auswählen"
        onClick={openDialog}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openDialog();
          }
        }}
        onDragOver={handleDragOver}
        onDragEnter={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        data-drag-active={dragActive}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-input bg-muted/30 px-6 py-8 text-center transition-colors",
          "hover:bg-muted/50 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 focus:outline-none",
          "data-[drag-active=true]:border-primary data-[drag-active=true]:bg-primary/10",
        )}
      >
        <FileUp className="size-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium">
          Dokument hier ablegen oder auswählen
        </p>
        <p className="text-xs text-muted-foreground">
          .md, .pdf, .epub oder .mobi, maximal {LIMIT_MB} MB.
        </p>
        {datei && formatLabel && (
          <div className="mt-1 text-xs text-muted-foreground">
            <p>
              Ausgewählt: <span className="font-mono">{datei.name}</span>{" "}
              ({Math.ceil(datei.size / 1024)} KB)
            </p>
            <p>
              Erkanntes Format: <span className="font-medium">{formatLabel}</span>
            </p>
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={(e) => {
          applyFile(e.target.files?.[0]);
          e.target.value = "";
        }}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
      />
    </div>
  );
}
