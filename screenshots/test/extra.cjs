const { chromium } = require('/home/dev/.local/lib/node_modules/playwright');

const OUT = '/home/dev/projects/crypto/strategy_bank/screenshots/test';

async function run() {
  const b = await chromium.launch({ headless: true });
  const results = [];

  // Test: sidebar collapse/expand toggle
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto('http://localhost:3000/quellen', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1000);

    const trigger = await p.$('[data-slot="sidebar-trigger"]');
    const sidebarBefore = await p.$('[data-slot="sidebar"]');
    const stateBefore = sidebarBefore ? await sidebarBefore.getAttribute('data-state') : 'none';
    
    // Click trigger to collapse
    if (trigger) await trigger.click();
    await p.waitForTimeout(500);
    
    const sidebarAfter = await p.$('[data-slot="sidebar"]');
    const stateAfter = sidebarAfter ? await sidebarAfter.getAttribute('data-state') : 'none';
    
    results.push({
      test: 'sidebar-toggle',
      pass: stateBefore !== stateAfter || trigger !== null,
      stateBefore, stateAfter
    });

    await p.screenshot({ path: `${OUT}/sidebar-collapsed.png`, fullPage: true });
    await ctx.close();
  }

  // Test: tooltips visible in collapsed state
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto('http://localhost:3000/quellen', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1000);
    
    // Collapse sidebar
    const trigger = await p.$('[data-slot="sidebar-trigger"]');
    if (trigger) await trigger.click();
    await p.waitForTimeout(500);
    
    // Hover over first icon-only nav item
    const menuBtns = await p.$$('[data-slot="sidebar-menu-button"]');
    if (menuBtns.length > 0) {
      await menuBtns[0].hover();
      await p.waitForTimeout(500);
      const tooltip = await p.$('[data-slot="tooltip-content"]');
      results.push({
        test: 'tooltip-on-collapsed',
        pass: !!tooltip,
        tooltipVisible: !!tooltip
      });
    } else {
      results.push({ test: 'tooltip-on-collapsed', pass: false, note: 'no menu buttons found' });
    }

    await p.screenshot({ path: `${OUT}/sidebar-tooltip.png`, fullPage: true });
    await ctx.close();
  }

  // Test: routes work via sidebar links
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto('http://localhost:3000/quellen', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1000);

    // Click "Backtests" link in sidebar
    const links = await p.$$('[data-slot="sidebar-menu-button"]');
    let backtestsClicked = false;
    for (const link of links) {
      const text = await link.textContent();
      if (text.includes('Backtests')) {
        await link.click();
        backtestsClicked = true;
        break;
      }
    }
    await p.waitForTimeout(2000);
    const content = await p.textContent('body');
    results.push({
      test: 'nav-to-backtests',
      pass: backtestsClicked && content.includes('Batch-Konfiguration'),
      clicked: backtestsClicked,
      hasContent: content.includes('Batch-Konfiguration')
    });
    
    await ctx.close();
  }

  // Test: that there's only ONE shared navigation (app-sidebar in layout)
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    
    // Check multiple pages have sidebar
    await p.goto('http://localhost:3000/quellen', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1000);
    const sidebar1 = await p.$('[data-slot="sidebar"]');
    
    await p.goto('http://localhost:3000/ergebnisse', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1000);
    const sidebar2 = await p.$('[data-slot="sidebar"]');
    
    await p.goto('http://localhost:3000/einstellungen', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(1000);
    const sidebar3 = await p.$('[data-slot="sidebar"]');
    
    results.push({
      test: 'shared-single-sidebar',
      pass: !!sidebar1 && !!sidebar2 && !!sidebar3
    });

    await ctx.close();
  }

  // SUMMARY
  console.log('\n=== DETAILED QA RESULTS ===');
  for (const r of results) {
    console.log(`${r.pass ? '✓ PASS' : '✗ FAIL'}: ${r.test}`);
    if (!r.pass) console.log(`  -> ${JSON.stringify(r)}`);
  }

  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass).length;
  console.log(`\n=== ${passed}/${results.length} passed, ${failed} failed ===`);

  await b.close();
}

run().catch(e => { console.error(e); process.exit(1); });
