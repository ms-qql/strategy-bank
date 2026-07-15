import { QuellenView } from "@/components/quellen/quellen-view";

export default function QuellenPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Quellenerfassung</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Strategiebeschreibungen als Text oder Markdown-Datei erfassen.
        </p>
      </header>
      <QuellenView />
    </main>
  );
}
