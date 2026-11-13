import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'
const [, , statePath, outDir] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const APP = 'http://127.0.0.1:5173'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })
const ctx = await browser.createBrowserContext(); const page = await ctx.newPage(); await page.setViewport({ width: 390, height: 844 })
const idle = async () => { try { await page.waitForNetworkIdle({ idleTime: 500, timeout: 15000 }) } catch {} await sleep(500) }
await page.goto(`${APP}/login`); await page.waitForSelector('#login-email')
await page.type('#login-email', 'cliente2@exemplo.test'); await page.type('#login-password', state.creds['cliente2@exemplo.test']); await page.click('button[type="submit"]'); await idle()
await page.goto(`${APP}/appointments/new`); await idle()
await (await page.$('[role="radiogroup"][aria-label="Serviços"] [role="radio"]')).click(); await sleep(300)
await (await page.$('[role="radiogroup"][aria-label="Barbeiros"] [role="radio"]')).click(); await idle()
const chips = await page.$$('[role="radiogroup"][aria-label="Dia"] [role="radio"]'); await chips[10].click(); await idle()
await (await page.$('[role="radiogroup"][aria-label^="Horários"] [role="radio"]')).click()
for (const b of await page.$$('button')) if ((await b.evaluate(e => e.textContent)).includes('Revisar')) { await b.click(); break }
await sleep(300)
for (const b of await page.$$('button')) if ((await b.evaluate(e => e.textContent)).includes('Confirmar agendamento')) { await b.click(); break }
await idle()
const h1a = await page.evaluate(() => document.querySelector('h1')?.textContent)
// clica na aba "Agendar" da barra inferior (mesma rota /appointments/new)
const tab = await page.$('nav[aria-label="Navegação rápida"] a[href="/appointments/new"]'); await tab.click(); await idle()
const h1b = await page.evaluate(() => document.querySelector('h1')?.textContent)
await page.screenshot({ path: path.join(outDir, 'capturas', 'fe_reagendar_novamente_mantem_confirmacao.png') })
// navega para outra tela e volta
await page.goto(`${APP}/appointments`); await idle(); await page.goto(`${APP}/appointments/new`); await idle()
const h1c = await page.evaluate(() => document.querySelector('h1')?.textContent)
const out = { aposConfirmar: h1a, aposClicarNaAbaAgendar: h1b, aposSairEVoltar: h1c }
console.log(JSON.stringify(out))
fs.writeFileSync(path.join(outDir, 'navegador-novo-agendamento-apos-confirmacao.json'), JSON.stringify(out, null, 1))
await browser.close()
