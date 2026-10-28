// Screenshot the dev site with the installed Edge (no browser download).
// usage: node scripts/shots.mjs <outdir> <width>x<height> <path> [<path> ...]
import { chromium } from 'playwright-core';

const [outdir, size, ...paths] = process.argv.slice(2);
const [width, height] = size.split('x').map(Number);
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('console', (m) => m.type() === 'error' && errors.push('console: ' + m.text()));
for (const p of paths) {
  await page.goto((process.env.BASE ?? 'http://localhost:5173') + p, { waitUntil: 'networkidle', timeout: 90000 }).catch((e) => errors.push('goto: ' + e.message));
  await page.waitForTimeout(2500);
  const name = (p.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home') + `_${width}.png`;
  await page.screenshot({ path: `${outdir}/${name}` });
  console.log('saved', name);
}
console.log(errors.length ? errors.join('\n') : 'sem erros no console');
await browser.close();
