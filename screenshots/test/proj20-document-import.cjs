// PROJ-20 QA: Dokumentauswahl und Importzustände.
const { chromium } = require("/home/dev/.local/lib/node_modules/playwright");

const URL = "http://127.0.0.1:3120/quellen";
const SCREENSHOT =
  "/home/dev/projects/crypto/strategy_bank/screenshots/test/proj20-source-row-fixed.png";

const results = [];
const expectedFailures = [];
let postCount = 0;
let failSecondUpload = false;

function check(label, condition, detail = "") {
  results.push({ label, pass: Boolean(condition), detail });
}

async function select(page, files) {
  const chooserPromise = page.waitForEvent("filechooser");
  await page.getByLabel("Dokumente hier ablegen oder auswählen").click();
  const chooser = await chooserPromise;
  await chooser.setFiles(files);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.route("**/api/sources", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    postCount += 1;
    await new Promise((resolve) => setTimeout(resolve, 350));
    if (failSecondUpload && postCount === 2) {
      await route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Das Dokument konnte nicht gelesen werden." }),
      });
      return;
    }
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: `00000000-0000-0000-0000-00000000002${postCount}`,
        source_hash: "a".repeat(64),
        source_type: postCount === 1 ? "pdf_file" : "epub_file",
        filename: postCount === 1 ? "first.pdf" : "second.epub",
        captured_at: "2026-07-29T19:00:00Z",
        extraction_status: "noch nicht extrahiert",
        content: "# Test",
      }),
    });
  });

  await page.goto(URL);
  await page.getByRole("tab", { name: "Dokument importieren" }).click();
  const dropzone = page.getByLabel("Dokumente hier ablegen oder auswählen");
  check("Dropzone sichtbar", await dropzone.isVisible());
  check(
    "Formathinweis",
    (await dropzone.innerText()).includes(".md, .pdf, .epub oder .mobi, maximal 25 MB"),
  );

  await select(page, [
    { name: "first.pdf", mimeType: "application/pdf", buffer: Buffer.from("pdf") },
    { name: "second.epub", mimeType: "application/epub+zip", buffer: Buffer.from("epub") },
  ]);
  check("Mehrfachauswahl sichtbar", (await dropzone.innerText()).includes("2 Dokumente ausgewählt"));
  check("PDF erkannt", (await dropzone.innerText()).includes("PDF-Dokument"));
  check("EPUB erkannt", (await dropzone.innerText()).includes("EPUB-E-Book"));

  await select(page, { name: "test.txt", mimeType: "text/plain", buffer: Buffer.from("test") });
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
    "Mehrfach-Drop akzeptiert",
    (await dropzone.innerText()).includes("2 Dokumente ausgewählt"),
  );

  const keyboardChooser = page.waitForEvent("filechooser");
  await dropzone.press("Enter");
  await (await keyboardChooser).setFiles([
    { name: "first.pdf", mimeType: "application/pdf", buffer: Buffer.from("pdf") },
    { name: "second.epub", mimeType: "application/epub+zip", buffer: Buffer.from("epub") },
  ]);
  check("Tastatur öffnet Mehrfachauswahl", (await dropzone.innerText()).includes("2 Dokumente ausgewählt"));

  await page.getByRole("button", { name: "Quelle speichern" }).click();
  check(
    "Umwandlungsstatus sichtbar",
    await page.getByRole("button", { name: "Dokumente werden umgewandelt …" }).isVisible(),
  );
  await page.waitForTimeout(850);
  check("Jedes Dokument gespeichert", postCount === 2, `POSTs: ${postCount}`);

  const tableText = await page.locator("table").innerText();
  check("PDF in Quellenliste", tableText.includes("first.pdf"));
  check("EPUB in Quellenliste", tableText.includes("second.epub"));
  check("Originalformat in Quellenliste", tableText.includes("EPUB-E-Book"));
  check("Originaldateiname in Quellenliste", tableText.includes("book.epub"));
  check(
    "Seitenuntertitel nennt Dokumentformate",
    (
      await page
        .getByRole("heading", { name: "Quellenerfassung" })
        .locator("..")
        .innerText()
    ).includes("PDF, EPUB oder MOBI"),
  );

  postCount = 0;
  failSecondUpload = true;
  await select(page, [
    { name: "first.pdf", mimeType: "application/pdf", buffer: Buffer.from("pdf") },
    { name: "second.epub", mimeType: "application/epub+zip", buffer: Buffer.from("epub") },
  ]);
  await page.getByRole("button", { name: "Quelle speichern" }).click();
  await page.waitForTimeout(850);
  check("Teilfehler meldet Restdatei", (await page.locator('[data-slot="alert"]').innerText()).includes("1 verbleiben"));
  check("Teilfehler behält nur Restdatei", (await dropzone.innerText()).includes("1 Dokument ausgewählt"));
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
