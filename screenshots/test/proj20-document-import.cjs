// PROJ-20 QA: Dokumentauswahl und Importzustände.
const { chromium } = require("/home/dev/.local/lib/node_modules/playwright");

const URL = "http://127.0.0.1:3120/quellen";
const SCREENSHOT =
  "/home/dev/projects/crypto/strategy_bank/screenshots/test/proj20-source-row-no-filename.png";

const results = [];
const expectedFailures = [];

function check(label, condition, detail = "") {
  results.push({ label, pass: Boolean(condition), detail });
}

async function select(page, name, mimeType = "application/octet-stream") {
  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByLabel("Dokument hier ablegen oder auswählen").click();
  const chooser = await chooserPromise;
  await chooser.setFiles({ name, mimeType, buffer: Buffer.from("test") });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.route("**/api/sources", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000020",
        source_hash: "a".repeat(64),
        source_type: "epub_file",
        filename: "book.epub",
        captured_at: "2026-07-29T19:00:00Z",
        extraction_status: "noch nicht extrahiert",
        content: "# Test",
      }),
    });
  });

  await page.goto(URL);
  await page.getByRole("tab", { name: "Dokument importieren" }).click();
  const dropzone = page.getByLabel("Dokument hier ablegen oder auswählen");
  check("Dropzone sichtbar", await dropzone.isVisible());
  check(
    "Formathinweis",
    (await dropzone.innerText()).includes(".md, .pdf, .epub oder .mobi, maximal 25 MB"),
  );

  for (const [name, label] of [
    ["test.md", "Markdown-Datei"],
    ["test.pdf", "PDF-Dokument"],
    ["test.epub", "EPUB-E-Book"],
    ["test.mobi", "MOBI-E-Book"],
    ["TEST.PDF", "PDF-Dokument"],
  ]) {
    await select(page, name);
    check(`${name} erkannt`, (await dropzone.innerText()).includes(label));
  }

  await select(page, "test.txt", "text/plain");
  check(
    "Falsche Endung abgelehnt",
    (await page.locator('[data-slot="alert"]').innerText()).includes(
      "Nur .md-, .pdf-, .epub- und .mobi-Dateien werden unterstützt.",
    ),
  );

  const transfer = await page.evaluateHandle(() => {
    const data = new DataTransfer();
    data.items.add(new File(["a"], "a.pdf", { type: "application/pdf" }));
    data.items.add(new File(["b"], "b.epub", { type: "application/epub+zip" }));
    return data;
  });
  await dropzone.dispatchEvent("drop", { dataTransfer: transfer });
  check(
    "Mehrfach-Drop abgelehnt",
    (await page.locator('[data-slot="alert"]').innerText()).includes(
      "Bitte genau eine Datei ablegen.",
    ),
  );

  const keyboardChooser = page.waitForEvent("filechooser");
  await dropzone.press("Enter");
  await (await keyboardChooser).setFiles({
    name: "book.epub",
    mimeType: "application/epub+zip",
    buffer: Buffer.from("epub"),
  });
  check("Tastatur öffnet Dateiauswahl", (await dropzone.innerText()).includes("book.epub"));

  await page.getByRole("button", { name: "Quelle speichern" }).click();
  check(
    "Umwandlungsstatus sichtbar",
    await page.getByRole("button", { name: "Dokument wird umgewandelt …" }).isVisible(),
  );
  await page.waitForResponse(
    (response) =>
      response.url().includes("/api/sources") &&
      response.request().method() === "POST",
  );
  await page.waitForTimeout(50);

  const tableText = await page.locator("table").innerText();
  check("Originalformat in Quellenliste", tableText.includes("EPUB-E-Book"));
  if (!tableText.includes("book.epub")) {
    expectedFailures.push({
      label: "BUG-2: Originaldateiname fehlt in der Quellenliste",
      detail: "API liefert filename=book.epub, die Tabelle rendert ihn nicht.",
    });
  }
  await page.screenshot({ path: SCREENSHOT, fullPage: true });

  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    check(`Responsive ${width}px`, await dropzone.isVisible());
  }

  await browser.close();
  const failed = results.filter((result) => !result.pass);
  console.log(JSON.stringify({ results, expectedFailures }, null, 2));
  process.exitCode = failed.length ? 1 : 0;
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
