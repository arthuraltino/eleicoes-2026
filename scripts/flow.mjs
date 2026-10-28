// End-to-end check of the main navigation flows, with screenshots.
// usage: node scripts/flow.mjs <outdir>
import { chromium } from 'playwright-core';

const out = process.argv[2];
const browser = await chromium.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
page.on('console', (m) => m.type() === 'error' && errors.push('console: ' + m.text()));
const shot = async (name) => { await page.waitForTimeout(2200); await page.screenshot({ path: `${out}/flow_${name}.png` }); console.log('shot', name, page.url()); };

await page.goto((process.env.BASE ?? 'http://localhost:5173') + '/presidente-2', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

// 1. keyboard search for a municipality
await page.keyboard.press('/');
await page.keyboard.type('campinas');
await page.waitForTimeout(300);
await page.keyboard.press('Enter');
await shot('1_busca_campinas');

// 2. "Minha seção"
await page.keyboard.press('Control+k');
await page.getByRole('tab', { name: 'Minha seção' }).click();
await page.getByRole('textbox', { name: 'Município' }).fill('São Paulo');
await page.locator('.sug button', { hasText: 'SP' }).first().click();
await page.getByRole('textbox', { name: 'Zona' }).fill('2');
await page.getByRole('textbox', { name: 'Seção' }).fill('30');
await page.getByRole('button', { name: 'Ver minha urna' }).click();
await shot('2_minha_secao');

// 3. wrong section gives a clear message
await page.keyboard.press('Control+k');
await page.getByRole('tab', { name: 'Minha seção' }).click();
await page.getByRole('textbox', { name: 'Município' }).fill('Campinas');
await page.locator('.sug button').first().click();
await page.getByRole('textbox', { name: 'Zona' }).fill('999');
await page.getByRole('textbox', { name: 'Seção' }).fill('1');
await page.getByRole('button', { name: 'Ver minha urna' }).click();
await page.waitForTimeout(1200);
console.log('erro mostrado:', await page.locator('.erro').textContent().catch(() => null));
await page.keyboard.press('Escape');

// 4. virada map at national level
await page.goto((process.env.BASE ?? 'http://localhost:5173') + '/presidente-2', { waitUntil: 'networkidle' });
await page.getByRole('button', { name: 'Virada desde o 1º turno' }).click();
await shot('4_virada_br');

// 5. click a state on the map (Bahia, roughly) and go back with the browser
await page.getByRole('button', { name: 'Resultado' }).click();
await page.mouse.click(705, 470);
await shot('5_clique_estado');
await page.goBack();
await shot('6_voltar');

// 6. Escape climbs one level
await page.goto((process.env.BASE ?? 'http://localhost:5173') + '/presidente-2/sp/3550308-sao-paulo/local-2-1023', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
await page.keyboard.press('Escape');
await page.waitForTimeout(800);
console.log('depois do Esc:', page.url());

console.log(errors.length ? errors.join('\n') : 'sem erros no console');
await browser.close();
