import fs from 'node:fs'
import puppeteer from 'puppeteer-core'
const axeSrc = fs.readFileSync(new URL('./node_modules/axe-core/axe.min.js', import.meta.url), 'utf8')
const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })
const page = await browser.newPage(); await page.setViewport({ width: 1440, height: 900 })
await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle0' })
await page.evaluate(axeSrc)
const base = await page.evaluate(async () => { const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] } }); return { regrasAprovadas: r.passes.length, violacoes: r.violations.map(v => v.id), incompletas: r.incomplete.map(v => v.id) } })
await page.evaluate(() => { const i = document.createElement('input'); i.type = 'text'; document.body.appendChild(i); const p = document.createElement('p'); p.textContent = 'baixo contraste'; p.style.color = '#ccc'; p.style.background = '#fff'; document.body.appendChild(p); const img = document.createElement('img'); img.src = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='; document.body.appendChild(img) })
const ctl = await page.evaluate(async () => { const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] } }); return r.violations.map(v => v.id) })
console.log(JSON.stringify({ login: base, controleComViolacoesPlantadas: ctl }, null, 1))
await browser.close()
