// usage: node render.js <startFrame> <endFrame> <outDir> [times...]
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [a, b, out, ...times] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') console.log('ERR', m.text()); });
  page.on('pageerror', e => console.log('PAGEERR', e.message));
  await page.goto('http://127.0.0.1:8765/index.html');
  await page.waitForFunction('window.READY===true', null, { timeout: 120000 });
  const shot = async (t, name) => {
    await page.evaluate(t => window.renderAt(t), t);
    await page.screenshot({ path: `${out}/${name}`, type: 'jpeg', quality: 96, clip: { x: 0, y: 0, width: 1080, height: 1920 } });
  };
  if (times.length) { for (const t of times) await shot(parseFloat(t), `t${t}.jpg`); }
  else {
    const t0 = Date.now();
    for (let i = +a; i < +b; i++) { await shot(i / 30, `f${String(i).padStart(5, '0')}.jpg`); if (i % 50 === 0) console.log(i, ((Date.now() - t0) / 1000).toFixed(0) + 's'); }
  }
  await browser.close();
})();
