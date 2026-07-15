"use client";

import { useRouter } from "next/navigation";
import { TriangleAlert, BookOpen, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Quellenbelege } from "./quellenbelege";
import type { Citation, Draft } from "@/lib/schemas/extraction";

const STATUS_VARIANT: Record<
  Draft["status"],
  "default" | "secondary" | "destructive"
> = {
  Entwurf: "secondary",
  "nicht testbar": "destructive",
  "gesperrt (unvollständig)": "destructive",
  freigegeben: "default",
};

const DIRECTION_LABEL: Record<Draft["direction"], string> = {
  kombiniert: "kombiniert",
  "long-only": "long only",
  "short-only": "short only",
};

function citationsFor(
  field: string,
  citations: Citation[],
): Citation[] {
  return citations.filter(
    (c) => c.rule_field === field || c.rule_field.startsWith(`${field}.`),
  );
}

interface RuleProps {
  field: "entry_rule" | "exit_rule";
  label: string;
  text: string | null;
  citations: Citation[];
}

function RegelBlock({ field, label, text, citations }: RuleProps) {
  const relevant = citationsFor(field, citations);
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      {text ? (
        <p className="font-mono text-sm">{text}</p>
      ) : (
        <p className="text-sm italic text-muted-foreground">
          (in der Quelle nicht ableitbar)
        </p>
      )}
      {relevant.length > 0 && <Quellenbelege citations={relevant} />}
    </div>
  );
}

interface Props {
  draft: Draft;
}

export function EntwurfCard({ draft }: Props) {
  const router = useRouter();

  return (
    <div className="rounded-lg border border-border bg-card p-4 text-sm">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="text-base font-medium leading-tight">{draft.name} · v{draft.version}</h4>
          {draft.thesis && (
            <p className="mt-1 text-muted-foreground">{draft.thesis}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="outline">{draft.category}</Badge>
          <Badge variant="outline">{DIRECTION_LABEL[draft.direction]}</Badge>
          <Badge variant={STATUS_VARIANT[draft.status]}>{draft.status}</Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push(`/entwuerfe/${draft.id}`)}
          >
            <Pencil className="mr-1 h-3.5 w-3.5" />
            Entwurf bearbeiten
          </Button>
        </div>
      </header>

      {draft.status_reason && (
        <Alert variant="destructive" className="mt-3">
          <TriangleAlert aria-hidden="true" />
          <AlertTitle>Hinweis</AlertTitle>
          <AlertDescription>{draft.status_reason}</AlertDescription>
        </Alert>
      )}

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <RegelBlock
          field="entry_rule"
          label="Entry"
          text={draft.entry_rule}
          citations={draft.citations}
        />
        <RegelBlock
          field="exit_rule"
          label="Exit"
          text={draft.exit_rule}
          citations={draft.citations}
        />
      </div>

      {draft.warmup_requirement && (
        <p className="mt-4 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Warm-up: </span>
          {draft.warmup_requirement}
        </p>
      )}
      {(draft.simultaneous_entry_exit_behavior || draft.reversal_behavior) && (
        <div className="mt-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
          {draft.simultaneous_entry_exit_behavior && (
            <p>
              <span className="font-medium text-foreground">
                Gleichzeitiger Entry/Exit:{" "}
              </span>
              {draft.simultaneous_entry_exit_behavior}
            </p>
          )}
          {draft.reversal_behavior && (
            <p>
              <span className="font-medium text-foreground">Reversal: </span>
              {draft.reversal_behavior}
            </p>
          )}
        </div>
      )}

      {draft.parameters.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Parameter
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Wert</TableHead>
                <TableHead>Einheit</TableHead>
                <TableHead>Bereich</TableHead>
                <TableHead className="text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {draft.parameters.map((p, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell className="font-mono">{p.value}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {p.unit ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {p.allowed_range ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {p.is_proposal && (
                      <Badge variant="secondary">Vorschlag</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {draft.open_questions.length > 0 && (
        <div className="mt-4 rounded-md border border-border bg-muted/30 p-3">
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <BookOpen aria-hidden="true" />
            Offene Unklarheiten
          </p>
          <ul className="mt-2 flex flex-col gap-2">
            {draft.open_questions.map((q, i) => (
              <li key={i} className="text-sm">
                <p className="font-medium">{q.description}</p>
                <p className="text-xs text-muted-foreground">
                  Begründung: {q.reasoning}
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs italic text-muted-foreground">
            Blockiert die Freigabe (PROJ-3).
          </p>
        </div>
      )}
    </div>
  );
}
