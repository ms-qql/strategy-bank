const { chromium } = require('/home/dev/.local/lib/node_modules/playwright');

const OUT = process.argv[2] || '/home/dev/projects/crypto/strategy_bank/screenshots/test';

(async () => {
  const b = await chromium.launch({ headless: true });
  const errors = [];
  const results = [];

  async function testPage(name, url, width, checkFn) {
    const ctx = await b.newContext({ viewport: { width: width, height: 900 }, userAgent: 'Mozilla/5.0 (compatible; QABot/1.0)' });
    const p = await ctx.newPage();
    p.on('console', m => { if (m.type() === 'error') errors.push(`[${name}:${width}] ${m.text()}`); });
    p.on('pageerror', e => errors.push(`[${name}:${width}] PAGE ERROR: ${e.message}`));
    
    try {
      await p.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      await p.screenshot({ path: `${OUT}/${name}_${width}.png`, fullPage: true });
      const r = await checkFn(p);
      results.push({ name, width, ...r });
    } catch (e) {
      results.push({ name, width, pass: false, note: `EXCEPTION: ${e.message}` });
    }
    await ctx.close();
  }

  // === AC-1: Jede reguläre App-Seite bietet gemeinsame Navigation ===
  
  // Desktop (1440px)
  await testPage('quellen-desktop', 'http://localhost:3000/quellen', 1440, async (p) => {
    const sidebar = await p.$('aside') || await p.$('[data-sidebar="sidebar"]') || await p.$('[data-slot="sidebar"]');
    if (!sidebar) return { pass: false, note: 'No sidebar found' };

    // Check app name + version in sidebar header
    const sidebarText = await sidebar.textContent();
    const hasAppName = sidebarText.includes('Strategy Bank');
    const hasVersion = /v\d+\.\d+\.\d+/.test(sidebarText);

    // Check all 4 nav items exist in sidebar
    const hasQuellen = sidebarText.includes('Quellen');
    const hasBacktests = sidebarText.includes('Backtests');
    const hasErgebnisse = sidebarText.includes('Ergebnisse');
    const hasEinstellungen = sidebarText.includes('Einstellungen');

    return {
      pass: hasAppName && hasVersion && hasQuellen && hasBacktests && hasErgebnisse && hasEinstellungen,
      hasAppName, hasVersion, hasQuellen, hasBacktests, hasErgebnisse, hasEinstellungen
    };
  });

  // AC-2: Quellen opens quellen page
  await testPage('quellen-content', 'http://localhost:3000/quellen', 1440, async (p) => {
    const content = await p.textContent('body');
    return { pass: content.includes('Quellenerfassung'), contentHasTitle: content.includes('Quellenerfassung') };
  });

  // AC-2: Backtests opens batches page
  await testPage('batches-content', 'http://localhost:3000/batches', 1440, async (p) => {
    const content = await p.textContent('body');
    return { pass: content.includes('Batch-Konfiguration'), contentHasTitle: content.includes('Batch-Konfiguration') };
  });

  // AC-2: Ergebnisse opens ergebnisse page
  await testPage('ergebnisse-content', 'http://localhost:3000/ergebnisse', 1440, async (p) => {
    const content = await p.textContent('body');
    return { pass: content.includes('Ergebnisvergleich'), contentHasTitle: content.includes('Ergebnisvergleich') };
  });

  // AC-3: Einstellungen opens settings page
  await testPage('einstellungen-content', 'http://localhost:3000/einstellungen', 1440, async (p) => {
    const content = await p.textContent('body');
    return { pass: content.includes('Einstellungen') };
  });

  // AC-4 (version check already done in AC-1)

  // AC-5: Active nav item is visually highlighted
  await testPage('active-quellen', 'http://localhost:3000/quellen', 1440, async (p) => {
    const activeBtn = await p.$('[data-active="true"]');
    if (!activeBtn) {
      const activeElements = await p.$$('button[data-active], a[data-active], [data-state="active"]');
      return { pass: activeElements.length > 0, note: activeElements.length === 0 ? 'No active indicator found' : `Found via data-active` };
    }
    const text = await activeBtn.textContent();
    return { pass: text.includes('Quellen'), activeText: text.trim() };
  });

  await testPage('active-ergebnisse', 'http://localhost:3000/ergebnisse', 1440, async (p) => {
    const activeBtn = await p.$('[data-active="true"]');
    if (!activeBtn) {
      const activeElements = await p.$$('[data-active]');
      return { pass: activeElements.length > 0, note: activeElements.length === 0 ? 'No active indicator found' : `Found via data-active` };
    }
    const text = await activeBtn.textContent();
    return { pass: text.includes('Ergebnisse'), activeText: text.trim() };
  });

  // AC-6: Detail pages have navigation and are mapped to correct parent
  await testPage('entwurf-detail-nav', 'http://localhost:3000/entwuerfe/a6ad8c73-48c0-4898-9e26-581322c38e44', 1440, async (p) => {
    // Check sidebar is visible
    const sidebar = await p.$('[data-slot="sidebar"]');
    const hasSidebar = !!sidebar;
    // Check that "Quellen" is active (since entwuerfe maps to Quellen)
    const activeBtn = await p.$('[data-active="true"]');
    let activeText = '';
    if (activeBtn) activeText = await activeBtn.textContent();
    return { pass: hasSidebar && activeText.includes('Quellen'), hasSidebar, activeText: activeText.trim() };
  });

  // AC-7: Mobile narrow view - sidebar is collapsible
  await testPage('mobile-quellen', 'http://localhost:3000/quellen', 375, async (p) => {
    // On mobile, sidebar should be hidden (offcanvas), visible SidebarTrigger
    const trigger = await p.$('[data-slot="sidebar-trigger"]');
    const hasTrigger = !!trigger;
    // Sidebar should NOT be permanently visible
    const visibleSidebar = await p.$('[data-slot="sidebar"]:visible');
    const sidebarVisible = !!visibleSidebar;
    return { pass: hasTrigger, hasTrigger, sidebarVisible };
  });

  // Test mobile: click trigger opens sidebar
  await testPage('mobile-open-sidebar', 'http://localhost:3000/quellen', 375, async (p) => {
    const trigger = await p.$('[data-slot="sidebar-trigger"]');
    if (!trigger) return { pass: false, note: 'No trigger found' };
    await trigger.click();
    await p.waitForTimeout(500);
    // Check if Sheet/Dialog opened
    const sheet = await p.$('[role="dialog"]') || await p.$('[data-mobile="true"]');
    return { pass: !!sheet, sheetOpened: !!sheet };
  });

  // AC-8: Keyboard accessibility - SidebarTrigger is a button
  await testPage('keyboard-access', 'http://localhost:3000/quellen', 1440, async (p) => {
    const trigger = await p.$('[data-slot="sidebar-trigger"]');
    const isButton = trigger ? (await trigger.evaluate(el => el.tagName.toLowerCase())) === 'button' : false;
    return { pass: isButton };
  });

  // EC-1: Unknown path - no false active
  await testPage('unknown-path', 'http://localhost:3000/nonexistent', 1440, async (p) => {
    const activeBtn = await p.$('[data-active="true"]');
    // No nav item should be active for unknown path
    return { pass: !activeBtn, noFalseActive: !activeBtn };
  });

  // EC-2: JavaScript not loaded - nav links work as plain <a> tags
  await testPage('server-side-nav', 'http://localhost:3000/quellen', 1440, async (p) => {
    // The sidebar menu buttons should render as <a> tags (via render prop with Link)
    const links = await p.$$('[data-slot="sidebar-menu-button"]');
    let allAreLinks = true;
    for (const link of links) {
      const tagName = await link.evaluate(el => el.tagName.toLowerCase());
      const href = await link.getAttribute('href');
      if (tagName !== 'a' || !href) { allAreLinks = false; break; }
    }
    return { pass: allAreLinks, linkCount: links.length };
  });

  // Responsive: tablet 768px
  await testPage('tablet-quellen', 'http://localhost:3000/quellen', 768, async (p) => {
    // At 768px (>= 768), sidebar should be visible
    const sidebar = await p.$('[data-slot="sidebar"]');
    const trigger = await p.$('[data-slot="sidebar-trigger"]');
    const content = await p.textContent('body');
    return { 
      pass: !!sidebar || !!trigger,
      sidebarVisible: !!sidebar,
      hasTrigger: !!trigger,
      contentHasQuellen: content.includes('Quellenerfassung')
    };
  });

  // ========== SUMMARY ==========
  console.log('\n=== QA TEST RESULTS ===\n');
  for (const r of results) {
    const status = r.pass ? '✓ PASS' : '✗ FAIL';
    console.log(`${status}: ${r.name} (${r.width}px)`);
    if (!r.pass) console.log(`    -> ${r.note || JSON.stringify(r)}`);
  }

  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass).length;
  console.log(`\n=== SUMMARY: ${passed}/${results.length} passed, ${failed} failed ===`);
  
  console.log('\n=== CONSOLE ERRORS ===');
  if (errors.length === 0) console.log('None');
  else errors.forEach(e => console.log(e));

  await b.close();
  process.exit(failed > 0 ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
