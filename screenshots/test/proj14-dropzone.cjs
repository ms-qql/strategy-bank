// PROJ-14 QA: Markdown-Drag-and-Drop
// Voraussetzungen: dev-server http://localhost:3120, backend http://localhost:8200

const { chromium } = require('/home/dev/.local/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = '/home/dev/projects/crypto/strategy_bank/screenshots/test';
const URL = 'http://localhost:3120/quellen';
const TMP = '/tmp/proj14-qa';

fs.mkdirSync(TMP, { recursive: true });

const DROPZONE = '[aria-label="Markdown-Datei hier ablegen oder auswählen"]';
const FILE_TAB = '[role="tab"]:has-text("Markdown-Datei")';
const TEXT_TAB = '[role="tab"]:has-text("Text einfügen")';
const HINWEIS = '.bg-destructive, [role="alert"]';
const SUBMIT_BTN = 'button[type="submit"]';

function fail(label, detail) {
  return { label, pass: false, detail };
}
function pass(label, detail) {
  return { label, pass: true, detail };
}

async function switchToFileTab(page) {
  await page.click(FILE_TAB);
  await page.waitForSelector(DROPZONE, { timeout: 5000 });
}

async function switchToTextTab(page) {
  await page.click(TEXT_TAB);
  await page.waitForSelector('textarea#quelle-text', { timeout: 5000 });
}

async function dispatchDrop(page, files) {
  // files: [{ name, mimeType, content }, ...]
  const handle = await page.evaluateHandle((files) => {
    const dt = new DataTransfer();
    for (const f of files) {
      const file = new File([f.content], f.name, { type: f.mimeType });
      dt.items.add(file);
    }
    return dt;
  }, files);
  await page.locator(DROPZONE).dispatchEvent('drop', { dataTransfer: handle });
  return handle;
}

async function dispatchDragOver(page) {
  const handle = await page.evaluateHandle(() => {
    const dt = new DataTransfer();
    const file = new File(['x'], 'a.md', { type: 'text/markdown' });
    dt.items.add(file);
    return dt;
  });
  await page.locator(DROPZONE).dispatchEvent('dragover', { dataTransfer: handle });
  return handle;
}

function readErrorText(page) {
  return page.evaluate(() => {
    const alert = document.querySelector('[role="alert"]');
    return alert ? alert.textContent : null;
  });
}

async function getSelectedFileSummary(page) {
  return page.evaluate(() => {
    const all = document.body.innerText;
    const m = all.match(/Ausgewählt:\s*([^\n]+?)\s*\((\d+)\s*KB\)/);
    return m ? { name: m[1].trim(), kb: parseInt(m[2], 10) } : null;
  });
}

async function getSourceCount(page) {
  return page.evaluate(() => {
    // "Erfasste Quellen" table — count rows except header
    const rows = document.querySelectorAll('[data-slot="card"] table tbody tr');
    // Detail rows are nested inside expand; only count top-level rows
    return rows.length;
  });
}

async function waitNoExtractionStart(page, beforeCount) {
  await page.waitForTimeout(500);
  const after = await getSourceCount(page);
  return after === beforeCount;
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on('console', (m) => {
    if (m.type() === 'error') console.log('[console error]', m.text());
  });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));

  const results = [];

  // -------- Setup: open the page and wait for sources to load --------
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForSelector('h1:has-text("Quellenerfassung")', { timeout: 10000 });
  await page.waitForSelector('table, [data-slot="card"]', { timeout: 10000 });
  await page.waitForTimeout(1500); // wait for initial sources fetch

  const sourcesBefore = await page.evaluate(() => {
    return document.querySelectorAll('[data-slot="card"] table tbody tr').length;
  });

  // -------- AC-1: Dropzone has required text --------
  await switchToFileTab(page);
  const text = await page.locator(DROPZONE).textContent();
  if (text && text.includes('Markdown-Datei hier ablegen oder auswählen')) {
    results.push(pass('AC-1: Dropzone-Text sichtbar', { text: text.slice(0, 80) }));
  } else {
    results.push(fail('AC-1: Dropzone-Text sichtbar', { text }));
  }
  await page.screenshot({ path: `${OUT}/proj14-ac1-dropzone.png`, fullPage: false });

  // -------- AC-2: Valid .md drop selects without auto-save/extract --------
  await dispatchDrop(page, [{ name: 'valid.md', mimeType: 'text/markdown', content: '# Test\nContent' }]);
  await page.waitForTimeout(500);
  const summary = await getSelectedFileSummary(page);
  const noSave = await waitNoExtractionStart(page, sourcesBefore);
  if (summary && summary.name === 'valid.md' && noSave) {
    results.push(pass('AC-2: Drop wählt Datei, kein Auto-Save/Extract', { summary, noSave }));
  } else {
    results.push(fail('AC-2: Drop wählt Datei, kein Auto-Save/Extract', { summary, noSave }));
  }
  await page.screenshot({ path: `${OUT}/proj14-ac2-selected.png`, fullPage: false });

  // -------- AC-3: Click + Enter + Space open file dialog --------
  // ponytail: jeder Pfad in eigenem Kontext, weil das aufeinanderfolgende
  // Schließen des ersten Choosers den zweiten blockieren kann (browser modal).
  async function testTriggerOpensChooser(triggerFn) {
    const ctxLocal = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctxLocal.newPage();
    await p.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
    await p.click(FILE_TAB);
    await p.waitForSelector(DROPZONE, { timeout: 5000 });
    const fcPromise = p.waitForEvent('filechooser', { timeout: 3000 }).catch(() => null);
    await triggerFn(p);
    const fc = await fcPromise;
    if (fc) {
      try { await fc.setFiles([]); } catch {}
    }
    await ctxLocal.close();
    return !!fc;
  }

  const clickOpens = await testTriggerOpensChooser(async (p) => { await p.click(DROPZONE); });
  const enterOpens = await testTriggerOpensChooser(async (p) => {
    await p.locator(DROPZONE).focus();
    await p.keyboard.press('Enter');
  });
  const spaceOpens = await testTriggerOpensChooser(async (p) => {
    await p.locator(DROPZONE).focus();
    await p.keyboard.press(' ');
  });

  if (clickOpens && enterOpens && spaceOpens) {
    results.push(pass('AC-3: Klick/Enter/Space öffnen Dateidialog', { click: clickOpens, enter: enterOpens, space: spaceOpens }));
  } else {
    results.push(fail('AC-3: Klick/Enter/Space öffnen Dateidialog', { click: clickOpens, enter: enterOpens, space: spaceOpens }));
  }

  // -------- AC-4: Drag-Over Aktivzustand --------
  // Reset any previous selection by reloading
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  const beforeDrag = await page.locator(DROPZONE).getAttribute('data-drag-active');
  await dispatchDragOver(page);
  await page.waitForTimeout(200);
  const afterDrag = await page.locator(DROPZONE).getAttribute('data-drag-active');
  // Screenshot im aktiven Zustand BEVOR wir dragleave feuern.
  await page.screenshot({ path: `${OUT}/proj14-ac4-drag-active.png`, fullPage: false, clip: { x: 280, y: 100, width: 1100, height: 400 } });
  // Move pointer away to clear
  await page.mouse.move(0, 0);
  await page.evaluate(() => {
    const dz = document.querySelector('[aria-label="Markdown-Datei hier ablegen oder auswählen"]');
    if (dz) dz.dispatchEvent(new DragEvent('dragleave', { bubbles: true }));
  });
  await page.waitForTimeout(200);
  if (afterDrag === 'true' && beforeDrag === 'false') {
    results.push(pass('AC-4: Drag-Over Aktivzustand (data-drag-active=true)', { before: beforeDrag, after: afterDrag }));
  } else {
    results.push(fail('AC-4: Drag-Over Aktivzustand', { before: beforeDrag, after: afterDrag }));
  }

  // -------- AC-5: Selection shows name+size; new selection replaces --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  await dispatchDrop(page, [{ name: 'first.md', mimeType: 'text/markdown', content: 'AAAA' }]);
  await page.waitForTimeout(400);
  const first = await getSelectedFileSummary(page);
  await dispatchDrop(page, [{ name: 'second.md', mimeType: 'text/markdown', content: 'BBBBBBBBBBBBBBBB' }]);
  await page.waitForTimeout(400);
  const second = await getSelectedFileSummary(page);
  if (first && second && first.name === 'first.md' && second.name === 'second.md' && second.kb >= 1) {
    results.push(pass('AC-5: Name+Größe sichtbar; neue Auswahl ersetzt', { first, second }));
  } else {
    results.push(fail('AC-5: Name+Größe sichtbar; neue Auswahl ersetzt', { first, second }));
  }

  // -------- AC-6: Validation rules (one .md, max 2 MB, not empty) --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);

  // Wrong extension
  await dispatchDrop(page, [{ name: 'foo.txt', mimeType: 'text/plain', content: 'hi' }]);
  await page.waitForTimeout(400);
  const wrongExt = await readErrorText(page);

  // Empty
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  await dispatchDrop(page, [{ name: 'empty.md', mimeType: 'text/markdown', content: '' }]);
  await page.waitForTimeout(400);
  const empty = await readErrorText(page);

  // Too large (>2 MB)
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  const big = 'x'.repeat(3 * 1024 * 1024);
  await dispatchDrop(page, [{ name: 'big.md', mimeType: 'text/markdown', content: big }]);
  await page.waitForTimeout(600);
  const tooBig = await readErrorText(page);

  const validations = {
    wrongExt: wrongExt?.includes('Nur .md-Dateien werden unterstützt.'),
    empty: empty?.includes('Quelle enthält keinen Inhalt.'),
    tooBig: tooBig?.includes('Datei überschreitet das Größenlimit von 2 MB.'),
  };
  const allValid = Object.values(validations).every(Boolean);
  if (allValid) {
    results.push(pass('AC-6: Validierung (Endung/leer/Größe)', validations));
  } else {
    results.push(fail('AC-6: Validierung (Endung/leer/Größe)', { validations, wrongExt, empty, tooBig }));
  }

  // -------- AC-7: Drop outside dropzone does not navigate --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  const urlBefore = page.url();
  // Dispatch drop on body (outside the dropzone)
  const bodyHandle = await page.evaluateHandle(() => {
    const dt = new DataTransfer();
    const file = new File(['x'], 'outside.md', { type: 'text/markdown' });
    dt.items.add(file);
    return dt;
  });
  await page.evaluate(() => {
    // Drop on the body / main area
    const target = document.querySelector('main') || document.body;
    const dt = new DataTransfer();
    const file = new File(['x'], 'outside.md', { type: 'text/markdown' });
    dt.items.add(file);
    target.dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }));
    target.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
  });
  await page.waitForTimeout(500);
  const urlAfter = page.url();
  if (urlBefore === urlAfter && urlAfter.includes('/quellen')) {
    results.push(pass('AC-7: Drop außerhalb navigiert nicht', { urlBefore, urlAfter }));
  } else {
    results.push(fail('AC-7: Drop außerhalb navigiert nicht', { urlBefore, urlAfter }));
  }

  // -------- AC-8: Text mode unchanged; cannot combine with file --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToTextTab(page);
  await page.fill('textarea#quelle-text', 'Some text content for the text mode');
  await switchToFileTab(page);
  const textState1 = await page.evaluate(() => document.querySelector('textarea#quelle-text')?.value || '');
  await switchToTextTab(page);
  const textState2 = await page.evaluate(() => document.querySelector('textarea#quelle-text')?.value || '');
  if (textState1 === '' && textState2 === 'Some text content for the text mode') {
    results.push(pass('AC-8: Text-Modus unabhängig von Datei-Modus', { textState1, textState2 }));
  } else {
    results.push(fail('AC-8: Text-Modus unabhängig von Datei-Modus', { textState1, textState2 }));
  }

  // -------- EC-1: Multiple files → spezielle Meldung --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  await dispatchDrop(page, [
    { name: 'a.md', mimeType: 'text/markdown', content: 'A' },
    { name: 'b.md', mimeType: 'text/markdown', content: 'B' },
  ]);
  await page.waitForTimeout(400);
  const multi = await readErrorText(page);
  const multiSummary = await getSelectedFileSummary(page);
  if (multi?.includes('Bitte genau eine Markdown-Datei ablegen.') && !multiSummary) {
    results.push(pass('EC-1: Mehrfach-Drop abgelehnt, keine Datei ausgewählt', { multi }));
  } else {
    results.push(fail('EC-1: Mehrfach-Drop abgelehnt', { multi, multiSummary }));
  }

  // -------- EC-4: Ordner als Drop → ungültig --------
  // DataTransfer files.length === 0 simulates folder drop (no file API access)
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  await page.evaluate(() => {
    const dz = document.querySelector('[aria-label="Markdown-Datei hier ablegen oder auswählen"]');
    if (!dz) return;
    const dt = new DataTransfer();
    // No items — folder drop has no accessible file
    dz.dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }));
  });
  await page.waitForTimeout(400);
  const folder = await readErrorText(page);
  if (folder?.includes('Nur .md-Dateien werden unterstützt.')) {
    results.push(pass('EC-4: Ordner-Drop wie ungültige Datei behandelt', { folder }));
  } else {
    results.push(fail('EC-4: Ordner-Drop wie ungültige Datei behandelt', { folder }));
  }

  // -------- EC-5: Valid nach invalid → alter Fehler weg, valide Datei aktiv --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  await dispatchDrop(page, [{ name: 'wrong.txt', mimeType: 'text/plain', content: 'x' }]);
  await page.waitForTimeout(400);
  const errAfterWrong = await readErrorText(page);
  await dispatchDrop(page, [{ name: 'good.md', mimeType: 'text/markdown', content: '# Good' }]);
  await page.waitForTimeout(400);
  const errAfterGood = await readErrorText(page);
  const goodSummary = await getSelectedFileSummary(page);
  if (errAfterWrong && !errAfterGood && goodSummary?.name === 'good.md') {
    results.push(pass('EC-5: Valide nach invalide → Fehler weg, Datei gewählt', { errAfterWrong, errAfterGood, goodSummary }));
  } else {
    results.push(fail('EC-5: Valide nach invalide', { errAfterWrong, errAfterGood, goodSummary }));
  }

  // -------- Regression: PROJ-1 Text-Modus Speichern funktioniert weiterhin --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToTextTab(page);
  await page.fill('textarea#quelle-text', 'Regressionstest: einfacher Klartext ohne Inhalt sollte Fehler werfen.');
  await page.click(SUBMIT_BTN);
  await page.waitForTimeout(1500);
  const textSaved = await page.evaluate(() => {
    // Nach Speichern sollte die Textarea leer sein
    return !document.querySelector('textarea#quelle-text')?.value;
  });
  const newSource = await getSourceCount(page);
  if (textSaved && newSource > sourcesBefore) {
    results.push(pass('Regression: Text-Speichern funktioniert (PROJ-1)', { textSaved, newSource, sourcesBefore }));
  } else {
    results.push(fail('Regression: Text-Speichern funktioniert (PROJ-1)', { textSaved, newSource, sourcesBefore }));
  }

  // -------- Sicherheit / XSS: Dateiname wird nicht in HTML gerendert --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  const xssName = '<img src=x onerror=alert(1)>.md';
  await dispatchDrop(page, [{ name: xssName, mimeType: 'text/markdown', content: '# XSS' }]);
  await page.waitForTimeout(400);
  // ponytail: React rendert Dateinamen als Textknoten — textContent enthält
  // die ursprüngliche Zeichenkette, body.innerHTML enthält sie escaped.
  const xss = await page.evaluate((xssName) => {
    const text = document.body.textContent || '';
    const html = document.body.innerHTML || '';
    return {
      hasTextName: text.includes(xssName),
      hasRawHtmlImg: !!document.querySelector('img[onerror]'),
      hasEscapedImg: html.includes('&lt;img') || html.includes('&lt;IMG'),
    };
  }, xssName);
  if (xss.hasTextName && !xss.hasRawHtmlImg && xss.hasEscapedImg) {
    results.push(pass('Sicherheit: Dateiname als Text (kein HTML-Render)', xss));
  } else {
    results.push(fail('Sicherheit: Dateiname als Text', xss));
  }

  // -------- Sicherheit: Tab-Wechsel cleared Fehler --------
  await page.reload({ waitUntil: 'networkidle' });
  await switchToFileTab(page);
  await dispatchDrop(page, [{ name: 'bad.txt', mimeType: 'text/plain', content: 'x' }]);
  await page.waitForTimeout(300);
  const errBeforeTab = await readErrorText(page);
  await switchToTextTab(page);
  await page.waitForTimeout(200);
  const errAfterTab = await readErrorText(page);
  if (errBeforeTab && !errAfterTab) {
    results.push(pass('Sicherheit/UX: Tab-Wechsel räumt Fehler', { errBeforeTab, errAfterTab }));
  } else {
    results.push(fail('Sicherheit/UX: Tab-Wechsel räumt Fehler', { errBeforeTab, errAfterTab }));
  }

  // -------- Responsive: 375px und 768px --------
  for (const vp of [
    { width: 375, height: 800, name: 'mobile' },
    { width: 768, height: 1024, name: 'tablet' },
  ]) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await page.reload({ waitUntil: 'networkidle' });
    await switchToFileTab(page);
    const dropVisible = await page.locator(DROPZONE).isVisible();
    await page.screenshot({ path: `${OUT}/proj14-responsive-${vp.name}.png`, fullPage: false });
    if (dropVisible) {
      results.push(pass(`Responsive ${vp.width}px: Dropzone sichtbar`, {}));
    } else {
      results.push(fail(`Responsive ${vp.width}px: Dropzone sichtbar`, {}));
    }
  }

  // -------- SUMMARY --------
  console.log('\n=== PROJ-14 QA RESULTS ===');
  for (const r of results) {
    console.log(`${r.pass ? '✓' : '✗'} ${r.label}`);
    if (!r.pass) console.log('  detail:', JSON.stringify(r.detail).slice(0, 400));
  }
  const passed = results.filter((r) => r.pass).length;
  const failed = results.length - passed;
  console.log(`\n=== ${passed}/${results.length} passed, ${failed} failed ===`);

  await browser.close();
  process.exit(failed > 0 ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
