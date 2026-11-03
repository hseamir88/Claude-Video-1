// Render src/index.html frame-by-frame with Playwright (deterministic timeline via window.renderAt).
// Usage: node src/render.js <outDir> [fps=30] [workers=4]   |   node src/render.js --still <t> <out.png>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const PAGE = 'file://' + path.resolve(__dirname, 'index.html');
const TOTAL = 177;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto(PAGE);
  await page.evaluate(() => document.fonts.ready);
  return page;
}

async function main() {
  const args = process.argv.slice(2);
  const browser = await chromium.launch();
  if (args[0] === '--still') {
    const page = await openPage(browser);
    await page.evaluate(t => window.renderAt(t), parseFloat(args[1]));
    await page.screenshot({ path: args[2] });
    await browser.close();
    return;
  }
  const outDir = args[0];
  const fps = parseInt(args[1] || '30', 10);
  const workers = parseInt(args[2] || '4', 10);
  fs.mkdirSync(outDir, { recursive: true });
  const nFrames = Math.round(TOTAL * fps);
  const per = Math.ceil(nFrames / workers);
  let done = 0;
  await Promise.all([...Array(workers).keys()].map(async w => {
    const page = await openPage(browser);
    for (let f = w * per; f < Math.min(nFrames, (w + 1) * per); f++) {
      await page.evaluate(t => window.renderAt(t), f / fps);
      await page.screenshot({ path: path.join(outDir, `f${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 92 });
      if (++done % 300 === 0) console.log(`${done}/${nFrames}`);
    }
  }));
  await browser.close();
  console.log('done', nFrames);
}
main().catch(e => { console.error(e); process.exit(1); });
