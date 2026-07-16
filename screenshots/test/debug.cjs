const { chromium } = require('/home/dev/.local/lib/node_modules/playwright');

const OUT = '/home/dev/projects/crypto/strategy_bank/screenshots/test';

(async () => {
  const b = await chromium.launch({ headless: true });

  // Debug entwurf detail page
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    p.on('console', m => console.log('[console]', m.type(), m.text()));
    
    await p.goto('http://localhost:3000/entwuerfe/a6ad8c73-48c0-4898-9e26-581322c38e44', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(2000);
    
    // Check what's rendered
    const bodyText = await p.evaluate(() => document.body.innerText.substring(0, 500));
    console.log('Body text:', bodyText);
    
    // Find all elements with data-active attribute
    const activeEls = await p.evaluate(() => {
      const els = document.querySelectorAll('[data-active]');
      return Array.from(els).map(e => ({
        tag: e.tagName,
        active: e.getAttribute('data-active'),
        text: e.textContent?.trim().substring(0, 50),
        classes: e.className?.substring(0, 200)
      }));
    });
    console.log('Active elements:', JSON.stringify(activeEls, null, 2));
    
    // Check sidebar menu items
    const menuItems = await p.evaluate(() => {
      const items = document.querySelectorAll('[data-slot="sidebar-menu-item"]');
      return Array.from(items).map(li => {
        const btn = li.querySelector('button, a');
        const isActive = btn?.getAttribute('data-active');
        return {
          text: li.textContent?.trim().substring(0, 50),
          tagName: btn?.tagName,
          active: isActive,
        };
      });
    });
    console.log('Menu items:', JSON.stringify(menuItems, null, 2));
    
    await p.screenshot({ path: `${OUT}/debug-entwurf.png`, fullPage: true });
    await ctx.close();
  }

  // Test runs/[id]/audit page
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto('http://localhost:3000/runs/some-id/audit', { waitUntil: 'networkidle', timeout: 15000 });
    await p.waitForTimeout(2000);
    
    const activeEls = await p.evaluate(() => {
      const els = document.querySelectorAll('[data-active]');
      return Array.from(els).map(e => ({
        tag: e.tagName,
        active: e.getAttribute('data-active'),
        text: e.textContent?.trim().substring(0, 50),
      }));
    });
    console.log('Runs audit active elements:', JSON.stringify(activeEls, null, 2));
    
    await p.screenshot({ path: `${OUT}/debug-runs-audit.png`, fullPage: true });
    await ctx.close();
  }

  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
