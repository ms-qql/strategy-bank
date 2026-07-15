"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPostForm, ApiError } from "@/lib/api-client";
import {
  MAX_SOURCE_BYTES,
  sourceListSchema,
  sourceSchema,
  type Source,
} from "@/lib/schemas/source";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

const TYP_LABEL: Record<Source["source_type"], string> = {
  text: "Text",
  markdown_file: "Markdown-Datei",
};

function formatZeitpunkt(iso: string): string {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString("de-DE");
}

export function QuellenView() {
  const [sources, setSources] = useState<Source[]>([]);
  const [ladeliste, setLadeliste] = useState(true);
  const [listenfehler, setListenfehler] = useState<string | null>(null);

  const [tab, setTab] = useState<Source["source_type"]>("text");
  const [text, setText] = useState("");
  const [datei, setDatei] = useState<File | null>(null);
  const [absenden, setAbsenden] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);
  const dateiInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiGet<unknown>("/sources")
      .then((data) => setSources(sourceListSchema.parse(data)))
      .catch((e) =>
        setListenfehler(
          e instanceof ApiError ? e.message : "Quellen konnten nicht geladen werden.",
        ),
      )
      .finally(() => setLadeliste(false));
  }, []);

  function reset() {
    setText("");
    setDatei(null);
    if (dateiInput.current) dateiInput.current.value = "";
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFehler(null);

    const form = new FormData();
    form.set("source_type", tab);

    if (tab === "text") {
      if (text.trim().length === 0) {
        setFehler("Quelle enthält keinen Inhalt.");
        return;
      }
      form.set("content", text);
    } else {
      if (!datei) {
        setFehler("Bitte eine Markdown-Datei (.md) auswählen.");
        return;
      }
      if (!datei.name.toLowerCase().endsWith(".md")) {
        setFehler("Nur .md-Dateien werden als Datei-Upload unterstützt.");
        return;
      }
      if (datei.size === 0) {
        setFehler("Quelle enthält keinen Inhalt.");
        return;
      }
      if (datei.size > MAX_SOURCE_BYTES) {
        setFehler("Datei überschreitet das Größenlimit von 2 MB.");
        return;
      }
      form.set("file", datei);
    }

    setAbsenden(true);
    try {
      const data = await apiPostForm<unknown>("/sources", form);
      const neu = sourceSchema.parse(data);
      setSources((prev) => [neu, ...prev]);
      reset();
    } catch (err) {
      setFehler(
        err instanceof ApiError ? err.message : "Quelle konnte nicht gespeichert werden.",
      );
    } finally {
      setAbsenden(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <Card>
        <CardHeader>
          <CardTitle>Quelle erfassen</CardTitle>
          <CardDescription>
            Genau eine Quelle je Vorgang: eingefügter Klartext oder eine
            hochgeladene <code>.md</code>-Datei.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Tabs
              value={tab}
              onValueChange={(v) => {
                setTab(v as Source["source_type"]);
                setFehler(null);
              }}
            >
              <TabsList>
                <TabsTrigger value="text">Text einfügen</TabsTrigger>
                <TabsTrigger value="markdown_file">Markdown-Datei</TabsTrigger>
              </TabsList>

              <TabsContent value="text" className="pt-2">
                <Label htmlFor="quelle-text" className="sr-only">
                  Strategiebeschreibung
                </Label>
                <Textarea
                  id="quelle-text"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Strategiebeschreibung hier einfügen …"
                  rows={12}
                  className="font-mono"
                />
              </TabsContent>

              <TabsContent value="markdown_file" className="pt-2">
                <Label htmlFor="quelle-datei">Markdown-Datei (.md)</Label>
                <Input
                  id="quelle-datei"
                  ref={dateiInput}
                  type="file"
                  accept=".md,text/markdown"
                  onChange={(e) => setDatei(e.target.files?.[0] ?? null)}
                  className="mt-2"
                />
                {datei && (
                  <p className="mt-2 text-sm text-muted-foreground">
                    Ausgewählt: {datei.name} ({Math.ceil(datei.size / 1024)} KB)
                  </p>
                )}
              </TabsContent>
            </Tabs>

            {fehler && (
              <Alert variant="destructive">
                <AlertDescription>{fehler}</AlertDescription>
              </Alert>
            )}

            <div>
              <Button type="submit" disabled={absenden}>
                {absenden ? "Speichern …" : "Quelle speichern"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Erfasste Quellen</CardTitle>
        </CardHeader>
        <CardContent>
          {ladeliste ? (
            <p className="text-sm text-muted-foreground">Wird geladen …</p>
          ) : listenfehler ? (
            <Alert variant="destructive">
              <AlertDescription>{listenfehler}</AlertDescription>
            </Alert>
          ) : sources.length === 0 ? (
            <p className="text-sm text-muted-foreground">Noch keine Quelle erfasst.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Erfasst am</TableHead>
                  <TableHead>Quell-Hash</TableHead>
                  <TableHead>Typ</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sources.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>{formatZeitpunkt(s.captured_at)}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {s.source_hash.slice(0, 12)}
                    </TableCell>
                    <TableCell>{TYP_LABEL[s.source_type]}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{s.extraction_status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
