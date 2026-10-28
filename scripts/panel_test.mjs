// Close/reopen the results panel on desktop and phone, with screenshots.
import { chromium } from 'playwright-core';
const out = process.argv[2];
const base = process.env.BASE ?? 'http://localhost:5173';
const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
for (const [w, h] of [[1440, 900], [390, 844]]) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(base + '/presidente-2/sp', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: 'Fechar resultados' }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${out}/painel_fechado_${w}.png` });
  const focused = await page.evaluate(() => document.activeElement?.getAttribute('aria-label'));
  await page.keyboard.press('Enter');
  await page.waitForTimeout(800);
  const reaberto = await page.getByRole('complementary', { name: 'Resultados' }).isVisible();
  console.log(w, '| foco após fechar:', focused, '| reabriu pelo teclado:', reaberto, errors.length ? errors : 'sem erros');
  await page.close();
}
await browser.close();
