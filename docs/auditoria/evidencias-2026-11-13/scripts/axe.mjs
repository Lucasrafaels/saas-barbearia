// axe-core (WCAG 2.0/2.1/2.2 A e AA) nas telas principais, desktop e celular, no build de produção.
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'
const [, , statePath, outDir] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const APP = 'http://127.0.0.1:5173'
const axeSrc = fs.readFileSync(new URL('./node_modules/axe-core/axe.min.js', import.meta.url), 'utf8')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })
const plan = [
  [null, ['/login', '/register', '/password/reset', '/conheca']],
  ['admin.a@exemplo.test', ['/admin', '/admin/appointments', '/admin/services', '/admin/barbers', '/admin/clients', '/admin/barbershop', '/account']],
  ['joao.barbeiro@exemplo.test', ['/barber/agenda', '/barber/agenda?status=agendado']],
  ['cliente1@exemplo.test', ['/', '/appointments/new', '/appointments', '/services', '/barbers']],
]
const out = []
for (const [email, routes] of plan) {
  for (const vp of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'celular', width: 390, height: 844 }]) {
    const ctx = await browser.createBrowserContext(); const page = await ctx.newPage(); await page.setViewport(vp)
    if (email) {
      await page.goto(`${APP}/login`, { waitUntil: 'domcontentloaded' }); await page.waitForSelector('#login-email')
      await page.type('#login-email', email); await page.type('#login-password', state.creds[email]); await page.click('button[type="submit"]')
      try { await page.waitForNetworkIdle({ idleTime: 500, timeout: 15000 }) } catch {}
    }
    for (const route of routes) {
      await page.goto(`${APP}${route}`, { waitUntil: 'domcontentloaded' })
      try { await page.waitForNetworkIdle({ idleTime: 500, timeout: 15000 }) } catch {}
      await sleep(900)
      await page.evaluate(axeSrc)
      const res = await page.evaluate(async () => {
        const r = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] }, resultTypes: ['violations'] })
        return r.violations.map((v) => ({ id: v.id, impacto: v.impact, ajuda: v.help, nos: v.nodes.length, exemplo: v.nodes.slice(0, 2).map((n) => n.target.join(' ') + ' :: ' + (n.failureSummary || '').split('\n').slice(1, 2).join(' ').slice(0, 160)) }))
      })
      out.push({ perfil: email ? email.split('@')[0] : 'publico', tela: vp.name, rota: route, violacoes: res })
    }
    await ctx.close()
  }
}
await browser.close()
fs.writeFileSync(path.join(outDir, 'acessibilidade-axe.json'), JSON.stringify(out, null, 1))
const agg = {}
for (const p of out) for (const v of p.violacoes) { agg[v.id] ??= { impacto: v.impacto, ajuda: v.ajuda, paginas: 0, nos: 0, exemplo: v.exemplo[0] }; agg[v.id].paginas++; agg[v.id].nos += v.nos }
console.log(`${out.length} páginas analisadas`)
console.log(JSON.stringify(agg, null, 1))
