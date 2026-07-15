"use client";

import { FileText } from "lucide-react";
import type { Citation } from "@/lib/schemas/extraction";

interface Props {
  citations: Citation[];
}

export function Quellenbelege({ citations }: Props) {
  if (citations.length === 0) return null;
  return (
    <details className="group text-xs">
      <summary className="inline-flex cursor-pointer items-center gap-1 text-muted-foreground hover:text-foreground">
        <FileText aria-hidden="true" />
        {citations.length === 1
          ? "Quellenbeleg anzeigen"
          : `${citations.length} Quellenbelege anzeigen`}
      </summary>
      <ul className="mt-2 flex flex-col gap-2 pl-1">
        {citations.map((c, i) => (
          <li
            key={i}
            className="rounded-md border border-border bg-muted/30 p-2"
          >
            <p className="font-medium text-foreground">{c.rule_field}</p>
            <blockquote className="mt-1 border-l-2 border-border pl-2 italic text-muted-foreground">
              {c.excerpt}
            </blockquote>
            {c.line_reference && (
              <p className="mt-1 text-muted-foreground">
                Position: <span className="font-mono">{c.line_reference}</span>
              </p>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
