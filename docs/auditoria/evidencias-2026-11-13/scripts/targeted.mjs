// Testes dirigidos no build de PRODUÇÃO (vite preview) ligado à API isolada.
// 1) requisições por tela sem StrictMode; 2) recarga com a API derrubada (FE-03);
// 3) carregamento com a API fora do ar; 4) barbearia desativada vista pelo admin e pelo cliente.
import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const [, , statePath, outDir, resetScript] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const APP = 'http://127.0.0.1:5173'
const API = 'http://127.0.0.1:8765/api/v1'
const shots = path.join(outDir, 'capturas')
const out = { requisicoesProducao: [], fe03: {}, apiForaDoAr: {}, barbeariaDesativada: {}, tempoSemTimeout: {} }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })

async function ctxPage(vp = { width: 1440, height: 900 }) {
  const ctx = await browser.createBrowserContext()
  const page = await ctx.newPage()
  await page.setViewport(vp)
  const api = []
  page.on('response', (res) => { if (res.url().includes(':8765/') && res.request().method() !== 'OPTIONS') api.push(`${res.request().method()} ${res.url().replace(/^https?:\/\/[^/]+/, '').split('?')[0]}`) })
  return { ctx, page, api }
}
async function settle(page, extra = 600) { try { await page.waitForNetworkIdle({ idleTime: 500, timeout: 20000 }) } catch {} await sleep(extra) }
async function login(page, email) {
  await page.goto(`${APP}/login`, { waitUntil: 'domcontentloaded' }); await page.waitForSelector('#login-email')
  await page.type('#login-email', email); await page.type('#login-password', state.creds[email])
  await page.click('button[type="submit"]'); await settle(page, 800)
}
async function clickText(page, sel, text) {
  for (const h of await page.$$(sel)) {
    const ok = await h.evaluate((el, t) => { const r = el.getBoundingClientRect(); return r.width > 0 && !el.disabled && el.textContent.includes(t) }, text)
    if (ok) { await h.click(); return true }
  }
  return false
}
const body = (page) => page.evaluate(() => document.body.innerText)

// 1) Requisições no build de produção
for (const [email, routes] of [['admin.a@exemplo.test', ['/admin', '/admin/appointments', '/admin/clients', '/admin/services', '/admin/barbers']],
  ['joao.barbeiro@exemplo.test', ['/barber/agenda']], ['cliente1@exemplo.test', ['/', '/appointments', '/appointments/new']]]) {
  const { ctx, page, api } = await ctxPage()
  await login(page, email)
  for (const route of routes) {
    api.length = 0
    const t0 = Date.now()
    await page.goto(`${APP}${route}`, { waitUntil: 'domcontentloaded' }); await settle(page)
    const appt = api.filter((x) => x === 'GET /api/v1/appointments/').length
    out.requisicoesProducao.push({ usuario: email.split('@')[0], rota: route, requisicoes: api.length, paginasDeAgendamentos: appt, ms: Date.now() - t0 })
  }
  await ctx.close()
}

// 2) FE-03: recarga falha com dados na tela (API derrubada de fato)
{
  const { ctx, page } = await ctxPage()
  await login(page, 'admin.a@exemplo.test')
  await page.goto(`${APP}/admin/appointments`, { waitUntil: 'domcontentloaded' }); await settle(page, 1000)
  const pid = fs.readFileSync(path.join(path.dirname(statePath), 'api.pid'), 'utf8').trim()
  process.kill(Number(pid), 'SIGTERM'); await sleep(1200)
  const before = await body(page)
  await clickText(page, 'button', 'Atualizar'); await sleep(3000)
  const after = await body(page)
  out.fe03 = {
    textoNovoAposFalha: after.split('\n').filter((l) => !before.includes(l)).slice(0, 8),
    mensagemDeErroVisivel: /não foi possível|sem conexão|erro/i.test(after.replace(before, '')),
  }
  await page.screenshot({ path: path.join(shots, 'fe03_recarga_falhou_sem_aviso.png') })
  // 3) recarregar a página com a API fora do ar
  await page.reload({ waitUntil: 'domcontentloaded' }); await sleep(3000)
  out.apiForaDoAr = { texto: (await body(page)).slice(0, 200) }
  await page.screenshot({ path: path.join(shots, 'api_fora_do_ar_ao_recarregar.png') })
  await ctx.close()
  execSync(resetScript)
}

// 4) Barbearia desativada (pela plataforma) vista pelo admin e pelo cliente
{
  const sup = await (await fetch(`${API}/auth/login/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'plataforma@exemplo.test', password: state.creds['plataforma@exemplo.test'] }) })).json()
  const r = await fetch(`${API}/barbershops/${state.ids.shop_a}/?confirmar=${encodeURIComponent('Barbearia Navalha Fictícia')}`, { method: 'DELETE', headers: { Authorization: `Bearer ${sup.access}` } })
  out.barbeariaDesativada.desativacao = r.status
  const a = await ctxPage()
  await login(a.page, 'admin.a@exemplo.test')
  await a.page.goto(`${APP}/admin`, { waitUntil: 'domcontentloaded' }); await settle(a.page)
  const t = await body(a.page)
  out.barbeariaDesativada.adminVeAviso = /desativada|suspensa|inativa/i.test(t)
  out.barbeariaDesativada.resumoLateral = t.match(/Aberta até \d\d:\d\d|Fechada, abre às \d\d:\d\d/)?.[0] ?? null
  await clickText(a.page, 'button', 'Confirmar'); await sleep(1500)
  out.barbeariaDesativada.adminConfirmar = (await body(a.page)).match(/Esta barbearia está desativada[^\n]*/)?.[0]?.slice(0, 120) ?? 'sem mensagem'
  await a.page.screenshot({ path: path.join(shots, 'barbearia_desativada_painel_admin.png') })
  await a.ctx.close()
  const c = await ctxPage({ width: 390, height: 844 })
  await login(c.page, 'cliente1@exemplo.test')
  await c.page.goto(`${APP}/appointments/new`, { waitUntil: 'domcontentloaded' }); await settle(c.page)
  await (await c.page.$('[role="radiogroup"][aria-label="Serviços"] [role="radio"]')).click(); await sleep(300)
  await (await c.page.$('[role="radiogroup"][aria-label="Barbeiros"] [role="radio"]')).click(); await settle(c.page)
  out.barbeariaDesativada.clienteAoAgendar = (await body(c.page)).match(/[^\n]*desativada[^\n]*/)?.[0]?.slice(0, 160) ?? 'sem mensagem'
  await c.page.screenshot({ path: path.join(shots, 'barbearia_desativada_cliente_agendando.png') })
  await c.ctx.close()
  execSync(resetScript)
}

await browser.close()
fs.writeFileSync(path.join(outDir, 'navegador-testes-dirigidos.json'), JSON.stringify(out, null, 1))
console.log(JSON.stringify(out, null, 1))
