// Mede se o rótulo de status mais longo cabe no cartão da barbearia na barra lateral
// (desktop 1440 px e gaveta do celular 390 px). Build corrigido + API isolada.
import fs from 'node:fs'
import puppeteer from 'puppeteer-core'
const [, , statePath, outFile] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const API = 'http://127.0.0.1:8765/api/v1'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
async function tok(email) { return (await (await fetch(`${API}/auth/login/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: state.creds[email] }) })).json()).access }
async function setDias(dias) { await fetch(`${API}/barbershops/${state.ids.shop_a}/`, { method: 'PATCH', headers: { Authorization: `Bearer ${await tok('admin.a@exemplo.test')}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ dias_funcionamento: dias }) }) }
const hojeIso = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 }[new Intl.DateTimeFormat('en-US', { timeZone: 'America/Sao_Paulo', weekday: 'short' }).format(new Date())]
// Fecha hoje e os dois próximos dias: o rótulo vira "Fechada, abre <dia da semana> às 09:00"
const fechados = [hojeIso, (hojeIso % 7) + 1, ((hojeIso + 1) % 7) + 1]
await setDias([1, 2, 3, 4, 5, 6, 7].filter((d) => !fechados.includes(d)))
const b = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })
const out = []
for (const vp of [{ nome: 'desktop', width: 1440, height: 900 }, { nome: 'celular-gaveta', width: 390, height: 844 }]) {
  const ctx = await b.createBrowserContext(); const p = await ctx.newPage(); await p.setViewport(vp)
  await p.goto('http://127.0.0.1:5173/login'); await p.waitForSelector('#login-email')
  await p.type('#login-email', 'admin.a@exemplo.test'); await p.type('#login-password', state.creds['admin.a@exemplo.test']); await p.click('button[type="submit"]')
  try { await p.waitForNetworkIdle({ idleTime: 400, timeout: 15000 }) } catch {}
  await sleep(600)
  if (vp.nome !== 'desktop') { await p.click('button[aria-label="Abrir menu"]'); await sleep(600) }
  const m = await p.evaluate(() => {
    const meta = document.querySelector('aside [title]')?.parentElement?.lastElementChild
    const card = meta?.parentElement
    const r = meta.getBoundingClientRect(); const c = card.getBoundingClientRect()
    const cs = getComputedStyle(card)
    const limite = c.right - parseFloat(cs.paddingRight)
    const range = document.createRange(); range.selectNodeContents(meta); const t = range.getBoundingClientRect()
    return { rotulo: meta.textContent.trim(), fimDoTexto: Math.round(t.right), limiteInternoDoCartao: Math.round(limite), cabe: t.right <= limite + 0.5 }
  })
  out.push({ tela: vp.nome, ...m })
  await p.screenshot({ path: outFile.replace('.json', `-${vp.nome}.png`) })
  await ctx.close()
}
await setDias([1, 2, 3, 4, 5, 6, 7])
await b.close()
fs.writeFileSync(outFile, JSON.stringify(out, null, 1))
console.log(JSON.stringify(out, null, 1))
