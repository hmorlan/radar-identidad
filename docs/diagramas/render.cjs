// Genera docs/img/{como-funciona,arquitectura}-{claro,oscuro}.png desde estos HTML.
// Uso (desde la raíz del repo, con frontend/node_modules instalado y Playwright):
//   node docs/diagramas/render.cjs
const { chromium } = require('playwright');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

(async () => {
	const out = path.resolve(__dirname, '../img');
	const browser = await chromium.launch();
	const trabajos = [];
	for (const name of ['como-funciona', 'arquitectura']) {
		for (const [modo, clase] of [['claro', ''], ['oscuro', 'oscuro']]) trabajos.push([name, modo, clase, 1600]);
	}
	// Versión vertical de "Cómo funciona" para teléfonos (sitio).
	trabajos.push(['como-funciona', 'movil-claro', 'movil', 720], ['como-funciona', 'movil-oscuro', 'movil oscuro', 720]);
	for (const [name, modo, clase, ancho] of trabajos) {
		{
			const page = await browser.newPage({ viewport: { width: ancho, height: 800 }, deviceScaleFactor: 1.5 });
			await page.goto(pathToFileURL(path.join(__dirname, `${name}.html`)).href);
			if (clase) await page.evaluate((c) => document.documentElement.classList.add(...c.split(' ')), clase);
			await page.evaluate(() => document.fonts.ready);
			await page.waitForTimeout(300);
			await page.screenshot({ path: path.join(out, `${name}-${modo}.png`), fullPage: true });
			await page.close();
		}
	}
	await browser.close();
	console.log('Listo:', out);
})();
