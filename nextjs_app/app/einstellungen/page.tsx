import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function EinstellungenPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Einstellungen</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Allgemeine Einstellungen und Konfigurationen werden in einem
          separaten Feature umgesetzt.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Allgemein</CardTitle>
          <CardDescription>
            Einstellungen folgen in einem eigenen Feature. Hier wird dann die
            Konfiguration von Backend-URL, Theme, Sprache und weiteren Optionen
            bereitgestellt.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="rounded-md border border-border p-8 text-center">
            <p className="text-sm text-muted-foreground">
              Einstellungen werden mit einem separaten Feature-Spec
              umgesetzt und erscheinen dann auf dieser Seite.
            </p>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
