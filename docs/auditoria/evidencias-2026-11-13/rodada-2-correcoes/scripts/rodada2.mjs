// Verificação no navegador da 2ª rodada (FE-14, FE-21, FE-22). Roda igual contra o build
// anterior e o corrigido (servidos em 127.0.0.1:5173) e registra o comportamento de cada um.
// API isolada com banco descartável. Sem tokens ou senhas na saída.
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const [, , statePath, outDir, versao] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const APP = 'http://127.0.0.1:5173'
const API = 'http://127.0.0.1:8765/api/v1'
const shots = path.join(outDir, 'capturas')
fs.mkdirSync(shots, { recursive: true })
const axeSrc = fs.readFileSync(new URL('./node_modules/axe-core/axe.min.js', import.meta.url), 'utf8')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const out = { versao, verificacoes: [], observado: {}, erros: [], console: {} }
const check = (id, desc, ok, detalhe = '') => out.verificacoes.push({ id, verificacao: desc, ok: Boolean(ok), detalhe: String(detalhe).slice(0, 300) })
const WEEKDAY = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado']

// ---------- API (para preparar cenários; a interface é o que se verifica) ----------
async function token(email) {
  const r = await fetch(`${API}/auth/login/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: state.creds[email] }) })
  return (await r.json()).access
}
async function api(email, method, p, body) {
  const r = await fetch(`${API}${p}`, { method, headers: { Authorization: `Bearer ${await token(email)}`, 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  return r.status
}
const setDias = (dias) => api('admin.a@exemplo.test', 'PATCH', `/barbershops/${state.ids.shop_a}/`, { dias_funcionamento: dias })

// ---------- relógio da barbearia ----------
function agoraSP() {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: 'America/Sao_Paulo', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date()).map((p) => [p.type, p.value]))
  const iso = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 }[parts.weekday]
  return { iso, minutos: Number(parts.hour) % 24 * 60 + Number(parts.minute) }
}
const nomeDoIso = (iso) => WEEKDAY[iso % 7]
// Regra esperada (independente do código do app): 09:00–19:00, dias configurados
function statusEsperado(dias, ativo = true) {
  if (!ativo) return 'Barbearia desativada'
  const { iso, minutos } = agoraSP()
  if (dias.includes(iso) && minutos >= 540 && minutos < 1140) return 'Aberta até 19:00'
  if (dias.includes(iso) && minutos < 540) return 'Fechada, abre às 09:00'
  for (let k = 1; k <= 7; k++) {
    const d = ((iso - 1 + k) % 7) + 1
    if (dias.includes(d)) return `Fechada, abre ${k === 1 ? 'amanhã' : nomeDoIso(d)} às 09:00`
  }
  return 'Fechada'
}

// ---------- navegador ----------
const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })
async function open(email, viewport, nome) {
  const ctx = await browser.createBrowserContext()
  const page = await ctx.newPage()
  await page.setViewport(viewport)
  const log = { console: [], pageErrors: [], falhasApi: [] }
  out.console[nome] = log
  page.on('console', (m) => { if (['error', 'warn', 'warning'].includes(m.type())) log.console.push(m.text().slice(0, 200)) })
  page.on('pageerror', (e) => log.pageErrors.push(String(e?.message ?? e).slice(0, 200)))
  page.on('response', (res) => {
    if (res.url().includes(':8765/') && res.request().method() !== 'OPTIONS' && res.status() >= 400) log.falhasApi.push(`${res.request().method()} ${res.url().replace(/^https?:\/\/[^/]+/, '').split('?')[0]} ${res.status()}`)
  })
  await page.goto(`${APP}/login`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('#login-email')
  await page.type('#login-email', email)
  await page.type('#login-password', state.creds[email])
  await page.click('button[type="submit"]')
  await idle(page)
  return { ctx, page }
}
async function idle(page, extra = 500) { try { await page.waitForNetworkIdle({ idleTime: 400, timeout: 15000 }) } catch {} await sleep(extra) }
async function go(page, route) { await page.goto(`${APP}${route}`, { waitUntil: 'domcontentloaded' }); await idle(page) }
const sidebarStatus = (page) => page.evaluate(() => {
  const name = document.querySelector('aside [title]')
  return name?.parentElement?.querySelector('span:last-child')?.textContent?.trim() ?? null
})
const homeStatus = (page) => page.evaluate(() => document.querySelector('#shop-title')?.parentElement?.querySelector('span')?.textContent?.trim() ?? null)
const banner = (page) => page.evaluate(() => [...document.querySelectorAll('main [role="status"]')].map((e) => e.innerText).find((t) => t.includes('Barbearia desativada')) ?? null)
const tabState = (page) => page.evaluate(() => {
  const nav = document.querySelector('nav[aria-label="Navegação rápida"]')
  if (!nav) return { tabbar: false, ativas: [] }
  return { tabbar: true, ativas: [...nav.querySelectorAll('a[aria-current="page"]')].map((a) => a.textContent.trim()) }
})
const sideActive = (page) => page.evaluate(() => [...document.querySelectorAll('nav[aria-label="Navegação principal"] a[aria-current="page"]')].map((a) => a.textContent.trim()))

try {
  await setDias([1, 2, 3, 4, 5, 6, 7])
  // =========================== FE-22 ===========================
  const rotas = {
    admin: [['/admin', 'Painel'], ['/admin/appointments', 'Agenda'], ['/admin/appointments?status=agendado', 'Agenda'], ['/admin/services', 'Serviços'], ['/admin/barbers', 'Barbeiros'], ['/admin/clients', 'Clientes'], ['/admin/barbershop', null], ['/account', null]],
    barbeiro: [['/barber/agenda', 'Agenda'], ['/barber/agenda?status=agendado', 'A confirmar'], ['/account', 'Conta']],
    cliente: [['/', 'Início'], ['/appointments/new', 'Agendar'], ['/appointments', 'Horários'], ['/services', 'Serviços'], ['/barbers', 'Equipe'], ['/account', null]],
  }
  const emails = { admin: 'admin.a@exemplo.test', barbeiro: 'joao.barbeiro@exemplo.test', cliente: 'cliente2@exemplo.test' }
  out.observado.abas = {}
  for (const [perfil, lista] of Object.entries(rotas)) {
    for (const vp of [{ nome: 'celular', width: 390, height: 844 }, { nome: 'tablet', width: 820, height: 1180 }]) {
      const { ctx, page } = await open(emails[perfil], vp, `abas-${perfil}-${vp.nome}`)
      for (const [rota, esperado] of lista) {
        await go(page, rota)
        const st = await tabState(page)
        out.observado.abas[`${perfil} ${vp.nome} ${rota}`] = st.ativas
        const ok = st.tabbar && st.ativas.length === (esperado ? 1 : 0) && (esperado ? st.ativas[0] === esperado : true)
        check(`FE22 ${perfil} ${vp.nome} ${rota}`, `aba ativa = ${esperado ?? 'nenhuma'}`, ok, JSON.stringify(st.ativas))
        if (perfil === 'admin' && rota === '/admin/barbershop' && vp.nome === 'celular') await page.screenshot({ path: path.join(shots, `${versao}_fe22_dados_da_barbearia_celular.png`) })
      }
      // Tocar em cada aba leva à tela e marca só ela
      if (vp.nome === 'celular') {
        const tabs = await page.$$eval('nav[aria-label="Navegação rápida"] a', (as) => as.map((a) => a.getAttribute('href')))
        for (const href of tabs) {
          await page.click(`nav[aria-label="Navegação rápida"] a[href="${href}"]`); await idle(page, 300)
          const st = await tabState(page)
          const label = await page.$eval(`nav[aria-label="Navegação rápida"] a[href="${href}"]`, (a) => a.textContent.trim())
          check(`FE22 ${perfil} toque ${href}`, `tocar em "${label}" marca só ela`, st.ativas.length === 1 && st.ativas[0] === label, JSON.stringify(st.ativas))
        }
      }
      await ctx.close()
    }
  }
  // Desktop: menu lateral inalterado, sem barra inferior
  {
    const { ctx, page } = await open('admin.a@exemplo.test', { width: 1440, height: 900 }, 'desktop-admin')
    for (const [rota, esperado] of [['/admin/barbershop', 'Dados da barbearia'], ['/admin/barbers', 'Barbeiros'], ['/admin', 'Painel']]) {
      await go(page, rota)
      const ativos = await sideActive(page)
      const st = await tabState(page)
      check(`FE22 desktop ${rota}`, `menu lateral marca "${esperado}" e não há barra inferior`, ativos.length === 1 && ativos[0] === esperado && !st.tabbar, JSON.stringify({ ativos, tabbar: st.tabbar }))
    }
    await ctx.close()
  }

  // =========================== FE-21 ===========================
  await setDias([1, 2, 3, 4, 5, 6])
  {
    const { ctx, page } = await open('cliente2@exemplo.test', { width: 390, height: 844 }, 'calendario-cliente')
    await go(page, '/appointments/new')
    await (await page.$('[role="radiogroup"][aria-label="Serviços"] [role="radio"]')).click(); await idle(page, 300)
    await (await page.$('[role="radiogroup"][aria-label="Barbeiros"] [role="radio"]')).click(); await idle(page)
    const chips = await page.$$eval('[role="radiogroup"][aria-label="Dia"] [role="radio"]', (els) => els.map((e) => ({ rotulo: e.getAttribute('aria-label'), visivel: e.innerText.replace(/\s+/g, ' ').trim(), desabilitado: e.disabled, marcado: e.getAttribute('aria-checked') })))
    out.observado.rotulos = chips.map((c) => c.rotulo)
    out.observado.textosVisiveis = chips.map((c) => c.visivel)
    const repetidos = chips.filter((c) => { const m = c.rotulo.match(/(\d{1,2}) de (\w+)/g) || []; return m.length !== 1 })
    check('FE21 data uma vez', 'cada rótulo traz a data uma única vez', repetidos.length === 0, JSON.stringify(repetidos.slice(0, 2).map((c) => c.rotulo)))
    check('FE21 únicos', 'os 21 rótulos são distintos', new Set(chips.map((c) => c.rotulo)).size === chips.length, `${new Set(chips.map((c) => c.rotulo)).size}/${chips.length}`)
    check('FE21 hoje/amanhã', 'primeiro "Hoje, …", segundo "Amanhã, …"', chips[0].rotulo.startsWith('Hoje, ') && chips[1].rotulo.startsWith('Amanhã, '), `${chips[0].rotulo} | ${chips[1].rotulo}`)
    const fechados = chips.filter((c) => c.desabilitado)
    check('FE21 fechados', 'dias fechados: desabilitados e terminando em ", barbearia fechada"', fechados.length >= 3 && fechados.every((c) => c.rotulo.endsWith(', barbearia fechada')) && chips.filter((c) => !c.desabilitado).every((c) => !c.rotulo.includes('fechada')), `${fechados.length} fechados; ex.: ${fechados[0]?.rotulo}`)
    check('FE21 selecionado', 'exatamente um dia marcado (aria-checked) e ele está aberto', chips.filter((c) => c.marcado === 'true').length === 1 && !chips.find((c) => c.marcado === 'true').desabilitado)
    const strip = await page.$('[role="radiogroup"][aria-label="Dia"]')
    const png = await strip.screenshot({ path: path.join(shots, `${versao}_fe21_faixa_de_dias.png`) })
    out.observado.hashFaixaDeDias = crypto.createHash('sha256').update(png).digest('hex')
    await page.evaluate(axeSrc)
    out.observado.axeCalendario = await page.evaluate(async () => (await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] } })).violations.map((v) => `${v.id} (${v.nodes.length})`))
    check('FE21 axe', 'axe sem violações no calendário', out.observado.axeCalendario.length === 0, out.observado.axeCalendario.join(', '))
    // O calendário continua funcionando: escolher um dia aberto mostra horários
    const abertos = await page.$$('[role="radiogroup"][aria-label="Dia"] [role="radio"]:not([disabled])')
    await abertos[3].click(); await idle(page)
    const slots = await page.$$eval('[role="radiogroup"][aria-label^="Horários"] [role="radio"]', (els) => els.length)
    check('FE21 calendário funciona', 'escolher um dia aberto mostra horários', slots > 0, `${slots} horários`)
    await ctx.close()
  }

  // =========================== FE-14 ===========================
  await setDias([1, 2, 3, 4, 5, 6, 7])
  {
    const hoje = agoraSP().iso
    const amanha = (hoje % 7) + 1
    const depois = (amanha % 7) + 1
    const adm = await open('admin.a@exemplo.test', { width: 1440, height: 900 }, 'fe14-admin')
    const cli = await open('cliente2@exemplo.test', { width: 1440, height: 900 }, 'fe14-cliente')
    const brb = await open('joao.barbeiro@exemplo.test', { width: 1440, height: 900 }, 'fe14-barbeiro')
    const todos = [1, 2, 3, 4, 5, 6, 7]
    let st = await sidebarStatus(adm.page)
    check('FE14 padrão', `padrão (todos os dias): "${statusEsperado(todos)}"`, st === statusEsperado(todos), st)
    // Admin fecha o dia de hoje pela tela e salva: a lateral muda sem recarregar
    await go(adm.page, '/admin/barbershop')
    const caixaHoje = `input[type="checkbox"][name="dias_funcionamento"][value="${hoje}"]`
    await adm.page.waitForSelector(caixaHoje, { timeout: 20000 })
    await adm.page.click(caixaHoje)
    for (const b of await adm.page.$$('button')) if ((await b.evaluate((e) => e.textContent)).includes('Salvar alterações')) { await b.click(); break }
    await idle(adm.page)
    const semHoje = todos.filter((d) => d !== hoje)
    st = await sidebarStatus(adm.page)
    check('FE14 hoje fechado (admin, sem recarregar)', `"${statusEsperado(semHoje)}"`, st === statusEsperado(semHoje), st)
    await adm.page.screenshot({ path: path.join(shots, `${versao}_fe14_admin_hoje_fechado.png`) })
    // Outra sessão (cliente): navegar atualiza a lateral; o início e o calendário concordam
    // Navegação interna (clique no menu), sem recarregar a página
    await cli.page.click('aside a[href="/services"]'); await idle(cli.page)
    st = await sidebarStatus(cli.page)
    check('FE14 outra sessão ao navegar (cliente)', `"${statusEsperado(semHoje)}"`, st === statusEsperado(semHoje), st)
    await cli.page.click('aside a[href="/"]'); await idle(cli.page)
    const home = await homeStatus(cli.page)
    check('FE14 início do cliente', 'mesmo status da lateral', home === statusEsperado(semHoje), home)
    await cli.page.click('aside a[href="/appointments/new"]'); await idle(cli.page)
    await cli.page.waitForSelector('[role="radiogroup"][aria-label="Serviços"] [role="radio"]', { timeout: 20000 })
    await (await cli.page.$('[role="radiogroup"][aria-label="Serviços"] [role="radio"]')).click(); await idle(cli.page, 300)
    await (await cli.page.$('[role="radiogroup"][aria-label="Barbeiros"] [role="radio"]')).click(); await idle(cli.page)
    const primeiro = await cli.page.$eval('[role="radiogroup"][aria-label="Dia"] [role="radio"]', (e) => ({ desabilitado: e.disabled, texto: e.innerText.replace(/\s+/g, ' ') }))
    check('FE14 calendário concorda', 'o dia de hoje aparece fechado no calendário', primeiro.desabilitado && /fechado/i.test(primeiro.texto), JSON.stringify(primeiro))
    await cli.page.screenshot({ path: path.join(shots, `${versao}_fe14_cliente_calendario_hoje_fechado.png`) })
    // Hoje, amanhã e depois de amanhã fechados (pela API, em outra sessão); o cliente volta à aba
    const restantes = todos.filter((d) => ![hoje, amanha, depois].includes(d))
    await adm.page.bringToFront(); await sleep(300)
    out.observado.visibilidadeClienteEmSegundoPlano = await cli.page.evaluate(() => document.visibilityState)
    await setDias(restantes)
    await cli.page.bringToFront(); await idle(cli.page)
    out.observado.visibilidadeClienteNaFrente = await cli.page.evaluate(() => document.visibilityState)
    st = await sidebarStatus(cli.page)
    check('FE14 outra sessão ao voltar à aba (cliente)', `"${statusEsperado(restantes)}"`, st === statusEsperado(restantes), st)
    await go(brb.page, '/barber/agenda')
    st = await sidebarStatus(brb.page)
    check('FE14 barbeiro', `"${statusEsperado(restantes)}"`, st === statusEsperado(restantes), st)
    // Desativação pela plataforma
    await setDias(todos)
    const d = await api('plataforma@exemplo.test', 'DELETE', `/barbershops/${state.ids.shop_a}/?confirmar=${encodeURIComponent('Barbearia Navalha Fictícia')}`)
    out.observado.desativacao = d
    await go(adm.page, '/admin')
    st = await sidebarStatus(adm.page)
    const bAdm = await banner(adm.page)
    check('FE14 desativada (admin)', 'lateral "Barbearia desativada" e aviso no topo', st === 'Barbearia desativada' && Boolean(bAdm), JSON.stringify({ st, aviso: bAdm }))
    await adm.page.screenshot({ path: path.join(shots, `${versao}_fe14_admin_barbearia_desativada.png`) })
    await cli.page.click('aside a[href="/"]'); await idle(cli.page)
    const homeD = await homeStatus(cli.page)
    const bCli = await banner(cli.page)
    check('FE14 desativada (cliente)', 'início "Barbearia desativada" e aviso no topo', homeD === 'Barbearia desativada' && Boolean(bCli), JSON.stringify({ homeD, aviso: bCli }))
    await cli.page.setViewport({ width: 390, height: 844 }); await go(cli.page, '/')
    await cli.page.screenshot({ path: path.join(shots, `${versao}_fe14_cliente_desativada_celular.png`) })
    // Reativação: o aviso some ao navegar, sem recarregar
    const r = await api('plataforma@exemplo.test', 'PATCH', `/barbershops/${state.ids.shop_a}/`, { ativo: true })
    out.observado.reativacao = r
    await adm.page.click('aside a[href="/admin/services"]'); await idle(adm.page)
    st = await sidebarStatus(adm.page)
    check('FE14 reativada', `aviso some e status volta a "${statusEsperado(todos)}"`, !(await banner(adm.page)) && st === statusEsperado(todos), st)
    for (const s of [adm, cli, brb]) await s.ctx.close()
  }

  // ====================== Plataforma (superusuário) ======================
  {
    const { ctx, page } = await open('plataforma@exemplo.test', { width: 1440, height: 900 }, 'plataforma')
    check('Plataforma', 'superusuário vai ao onboarding (sem painel próprio, comportamento anterior)', page.url().endsWith('/onboarding'), page.url().replace(APP, ''))
    await ctx.close()
  }
} catch (error) {
  out.erros.push(String(error?.stack ?? error).slice(0, 800))
}
await setDias([1, 2, 3, 4, 5, 6, 7]).catch(() => {})
await browser.close()
fs.writeFileSync(path.join(outDir, `rodada2-navegador-${versao}.json`), JSON.stringify(out, null, 1))
const ok = out.verificacoes.filter((v) => v.ok).length
console.log(`[${versao}] ${out.verificacoes.length} verificações; ${ok} conforme; ${out.verificacoes.length - ok} divergentes; erros=${out.erros.length}`)
for (const v of out.verificacoes) if (!v.ok) console.log(' X', v.id, '|', v.detalhe)
const problemas = Object.entries(out.console).filter(([, l]) => l.console.length || l.pageErrors.length || l.falhasApi.length)
console.log('console/página/API com ocorrências:', JSON.stringify(problemas).slice(0, 800))
if (out.erros.length) console.log(out.erros)
