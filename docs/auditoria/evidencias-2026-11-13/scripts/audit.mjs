// Auditoria de interface: Firefox headless via puppeteer-core contra o frontend
// (Vite, 127.0.0.1:5173) ligado à API isolada (127.0.0.1:8765, banco descartável).
// Saída: JSON com métricas por página/tamanho de tela e capturas em <out>/capturas.
// Nunca grava tokens ou senhas na saída.
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const [, , statePath, outDir] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const APP = 'http://127.0.0.1:5173'
const shotDir = path.join(outDir, 'capturas')
fs.mkdirSync(shotDir, { recursive: true })

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  notebook: { width: 1280, height: 720 },
  tablet: { width: 820, height: 1180 },
  celular: { width: 390, height: 844 },
  'celular-pequeno': { width: 360, height: 740 },
}
const ROUTES = {
  publico: ['/login', '/register', '/password/reset', '/password/reset/confirm', '/conheca'],
  admin: ['/admin', '/admin/appointments', '/admin/services', '/admin/barbers', '/admin/clients', '/admin/barbershop', '/account'],
  barbeiro: ['/barber/agenda', '/barber/agenda?status=agendado', '/account'],
  cliente: ['/', '/appointments/new', '/appointments', '/services', '/barbers', '/account'],
}
const USERS = { admin: 'admin.a@exemplo.test', barbeiro: 'joao.barbeiro@exemplo.test', cliente: 'cliente1@exemplo.test' }
const SHOTS = new Set(['desktop', 'celular', 'tablet'])

const results = { paginas: [], fluxos: [], teclado: [], observacoes: [] }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await puppeteer.launch({
  browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true,
  args: ['--width=1440', '--height=900'],
})

function attach(page, bucket) {
  page.on('console', (msg) => {
    if (['error', 'warn', 'warning'].includes(msg.type())) bucket.console.push(`${msg.type()}: ${msg.text().slice(0, 220)}`)
  })
  page.on('pageerror', (err) => bucket.pageErrors.push(String(err?.message ?? err).slice(0, 220)))
  page.on('response', (res) => {
    const url = res.url()
    if (url.includes(':8765/')) {
      bucket.api.push(`${res.request().method()} ${url.replace(/^https?:\/\/[^/]+/, '').split('?')[0]} ${res.status()}`)
      if (res.status() >= 400) bucket.failed.push(`${res.request().method()} ${url.replace(/^https?:\/\/[^/]+/, '')} → ${res.status()}`)
    }
  })
}

async function newPage() {
  const ctx = await browser.createBrowserContext()
  const page = await ctx.newPage()
  page.__ctx = ctx
  const bucket = { console: [], pageErrors: [], api: [], failed: [] }
  attach(page, bucket)
  return { page, bucket }
}

async function settle(page, extra = 600) {
  try { await page.waitForNetworkIdle({ idleTime: 500, timeout: 15000 }) } catch { /* segue */ }
  await sleep(extra)
}

async function login(page, email) {
  await page.goto(`${APP}/login`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('#login-email', { timeout: 15000 })
  await page.type('#login-email', email)
  await page.type('#login-password', state.creds[email])
  await Promise.all([page.click('button[type="submit"]'), sleep(400)])
  await settle(page, 800)
}

async function measure(page) {
  return page.evaluate(() => {
    const vw = window.innerWidth
    const doc = document.documentElement
    const over = []
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      const style = getComputedStyle(el)
      if (style.position === 'fixed' && r.right <= vw + 1) continue
      if (r.right > vw + 1 || r.left < -1) {
        // ignora filhos de contêineres com rolagem horizontal própria
        let p = el.parentElement, scrolled = false
        while (p && p !== document.body) {
          const s = getComputedStyle(p)
          if ((s.overflowX === 'auto' || s.overflowX === 'scroll' || s.overflowX === 'hidden' || s.overflowX === 'clip') && p.getBoundingClientRect().right <= vw + 1) { scrolled = true; break }
          p = p.parentElement
        }
        if (!scrolled) over.push(`${el.tagName.toLowerCase()}.${(el.className && typeof el.className === 'string' ? el.className.split(' ')[0] : '')} [${Math.round(r.left)}..${Math.round(r.right)}]`)
      }
    }
    const small = []
    for (const el of document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=radio], [role=tab], [role=menuitem]')) {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      const s = getComputedStyle(el)
      if (s.visibility === 'hidden') continue
      if (r.width < 24 || r.height < 24) small.push(`${el.tagName.toLowerCase()} "${(el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 30)}" ${Math.round(r.width)}x${Math.round(r.height)}`)
    }
    const h1 = document.querySelector('h1')?.textContent?.trim() ?? null
    const fonts = [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family)
    return {
      scrollWidth: doc.scrollWidth, innerWidth: vw, overflowX: doc.scrollWidth - vw,
      overflowing: [...new Set(over)].slice(0, 6), smallTargets: small.length, smallSample: small.slice(0, 5),
      h1, title: document.title, fontsLoaded: [...new Set(fonts)],
    }
  })
}

async function audit(profile, routes) {
  const { page, bucket } = await newPage()
  if (profile !== 'publico') {
    await page.setViewport(VIEWPORTS.desktop)
    await login(page, USERS[profile])
  }
  for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
    await page.setViewport(vp)
    for (const route of routes) {
      bucket.console.length = 0; bucket.pageErrors.length = 0; bucket.api.length = 0; bucket.failed.length = 0
      const t0 = Date.now()
      try {
        await page.goto(`${APP}${route}`, { waitUntil: 'domcontentloaded', timeout: 20000 })
        await settle(page)
        const m = await measure(page)
        const finalUrl = page.url().replace(APP, '')
        let shot = null
        if (SHOTS.has(vpName)) {
          shot = `${profile}_${vpName}_${route.replace(/[/?=&]+/g, '_').replace(/^_|_$/g, '') || 'inicio'}.png`
          await page.screenshot({ path: path.join(shotDir, shot), fullPage: vpName !== 'desktop' ? false : true })
        }
        results.paginas.push({
          perfil: profile, tela: vpName, rota: route, urlFinal: finalUrl, ms: Date.now() - t0,
          requisicoesApi: bucket.api.length, chamadasApi: summarize(bucket.api),
          errosConsole: [...bucket.console], errosPagina: [...bucket.pageErrors], falhasApi: [...bucket.failed], ...m, captura: shot,
        })
      } catch (error) {
        results.paginas.push({ perfil: profile, tela: vpName, rota: route, erro: String(error).slice(0, 200) })
      }
    }
  }
  await page.__ctx.close()
}

function summarize(list) {
  const counts = {}
  for (const item of list) counts[item] = (counts[item] ?? 0) + 1
  return counts
}

async function textOf(page) {
  return page.evaluate(() => document.body.innerText)
}

async function clickByText(page, selector, text) {
  const handles = await page.$$(selector)
  for (const h of handles) {
    const t = await h.evaluate((el) => el.textContent?.trim() ?? '')
    const visible = await h.evaluate((el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.disabled })
    if (visible && t.includes(text)) { await h.click(); return true }
  }
  return false
}

async function flowCliente() {
  const { page, bucket } = await newPage()
  await page.setViewport(VIEWPORTS.celular)
  await login(page, USERS.cliente)
  const steps = []
  await page.goto(`${APP}/appointments/new`, { waitUntil: 'domcontentloaded' }); await settle(page)
  const svc = await page.$('[role="radiogroup"][aria-label="Serviços"] [role="radio"]'); await svc.click(); await sleep(400)
  steps.push('serviço escolhido')
  const bar = await page.$('[role="radiogroup"][aria-label="Barbeiros"] [role="radio"]'); await bar.click(); await settle(page)
  steps.push('barbeiro escolhido')
  // domingo visível no seletor de dias e com horários?
  const sunday = await page.$$eval('[role="radiogroup"][aria-label="Dia"] [role="radio"]', (els) => els.findIndex((e) => e.textContent.toLowerCase().startsWith('dom')))
  if (sunday >= 0) {
    const chips = await page.$$('[role="radiogroup"][aria-label="Dia"] [role="radio"]'); await chips[sunday].click(); await settle(page)
    const n = await page.$$eval('[role="radiogroup"][aria-label^="Horários"] [role="radio"]', (els) => els.length)
    results.observacoes.push({ id: 'BUS-06-ui', texto: `Seletor de dias do cliente oferece domingo com ${n} horários livres.` })
    await page.screenshot({ path: path.join(shotDir, 'fluxo_cliente_domingo_com_horarios.png') })
  }
  const chips = await page.$$('[role="radiogroup"][aria-label="Dia"] [role="radio"]'); await chips[9].click(); await settle(page)
  const slot = await page.$('[role="radiogroup"][aria-label^="Horários"] [role="radio"]'); await slot.click()
  steps.push('dia e horário escolhidos')
  await clickByText(page, 'button', 'Revisar'); await sleep(400)
  await clickByText(page, 'button', 'Confirmar agendamento'); await settle(page)
  const done = (await textOf(page)).includes('Está marcado')
  steps.push(`confirmação exibida=${done}`)
  await page.screenshot({ path: path.join(shotDir, 'fluxo_cliente_agendamento_concluido.png') })
  await page.goto(`${APP}/appointments`, { waitUntil: 'domcontentloaded' }); await settle(page)
  const okCancel = await clickByText(page, 'button', 'Cancelar'); await sleep(500)
  await page.screenshot({ path: path.join(shotDir, 'fluxo_cliente_dialogo_cancelar.png') })
  const confirmed = await clickByText(page, '[role="dialog"] button, dialog button', 'Cancelar horário'); await settle(page)
  const txt = await textOf(page)
  steps.push(`cancelar: botão=${okCancel} diálogo=${confirmed} toast=${txt.includes('Horário cancelado')}`)
  results.fluxos.push({ fluxo: 'Cliente agenda (celular 390 px) e cancela', passos: steps, errosConsole: bucket.console, falhasApi: bucket.failed, errosPagina: bucket.pageErrors })
  await page.__ctx.close()
}

async function flowAdmin() {
  const { page, bucket } = await newPage()
  await page.setViewport(VIEWPORTS.desktop)
  await login(page, USERS.admin)
  const steps = []
  bucket.api.length = 0
  await page.goto(`${APP}/admin`, { waitUntil: 'domcontentloaded' }); await settle(page, 1500)
  const apptPages = bucket.api.filter((x) => x.startsWith('GET /api/v1/appointments/ ')).length
  steps.push(`painel: ${bucket.api.length} requisições à API, ${apptPages} delas para páginas de /appointments/`)
  await page.screenshot({ path: path.join(shotDir, 'admin_desktop_painel_completo.png'), fullPage: true })
  const pending = await page.evaluate(() => document.querySelector('a[href*="status=agendado"]')?.textContent?.trim() ?? null)
  steps.push(`indicador do topo: "${pending}"`)
  const conf = await clickByText(page, 'button', 'Confirmar'); await settle(page)
  steps.push(`confirmar em "A seguir": clique=${conf} toast=${(await textOf(page)).includes('confirmado')}`)
  // Dados da barbearia: fechamento antes da abertura (validação do frontend)
  await page.goto(`${APP}/admin/barbershop`, { waitUntil: 'domcontentloaded' }); await settle(page)
  const inputs = await page.$$('input[type="time"]')
  if (inputs.length >= 2) {
    await inputs[0].evaluate((el) => { el.focus() })
    await page.evaluate(() => {
      const [a, f] = document.querySelectorAll('input[type="time"]')
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      set.call(a, '18:00'); a.dispatchEvent(new Event('input', { bubbles: true }))
      set.call(f, '08:00'); f.dispatchEvent(new Event('input', { bubbles: true }))
    })
    await clickByText(page, 'button', 'Salvar'); await settle(page)
    const t = await textOf(page)
    const blocked = !bucket.failed.length && !bucket.api.some((x) => x.startsWith('PATCH /api/v1/barbershops/'))
    steps.push(`horário inválido no formulário: bloqueado no frontend=${blocked}; mensagem=${/fechamento|abertura/i.test(t)}`)
    await page.screenshot({ path: path.join(shotDir, 'admin_desktop_validacao_horario.png') })
  }
  // FE-03: recarga falha com dados já na tela
  await page.goto(`${APP}/admin/appointments`, { waitUntil: 'domcontentloaded' }); await settle(page, 1200)
  const pid = fs.readFileSync(path.join(path.dirname(statePath), 'api.pid'), 'utf8').trim()
  process.kill(Number(pid), 'SIGSTOP')
  await clickByText(page, 'button', 'Atualizar'); await sleep(2500)
  process.kill(Number(pid), 'SIGCONT')
  await sleep(200)
  // com o processo parado a requisição fica pendente; a interface não deve fingir sucesso
  steps.push('recarga com API pausada: ver captura admin_desktop_recarga_com_api_pausada.png')
  await page.screenshot({ path: path.join(shotDir, 'admin_desktop_recarga_com_api_pausada.png') })
  results.fluxos.push({ fluxo: 'Admin: painel, confirmar, validação de horário, recarga', passos: steps, errosConsole: bucket.console, falhasApi: bucket.failed, errosPagina: bucket.pageErrors })
  await page.__ctx.close()
}

async function flowBarbeiro() {
  const { page, bucket } = await newPage()
  await page.setViewport(VIEWPORTS.tablet)
  await login(page, USERS.barbeiro)
  const steps = []
  await page.goto(`${APP}/barber/agenda?status=agendado`, { waitUntil: 'domcontentloaded' }); await settle(page)
  const conf = await clickByText(page, 'button', 'Confirmar'); await settle(page)
  steps.push(`confirmar: clique=${conf} toast=${(await textOf(page)).includes('confirmado')}`)
  const early = await page.$$eval('button', (els) => els.filter((e) => /Concluir às/.test(e.textContent)).length)
  steps.push(`botões "Concluir às HH:MM" desabilitados (antes do término): ${early}`)
  await page.screenshot({ path: path.join(shotDir, 'fluxo_barbeiro_tablet_a_confirmar.png') })
  results.fluxos.push({ fluxo: 'Barbeiro confirma horário (tablet 820 px)', passos: steps, errosConsole: bucket.console, falhasApi: bucket.failed, errosPagina: bucket.pageErrors })
  await page.__ctx.close()
}

async function keyboard() {
  const { page } = await newPage()
  await page.setViewport(VIEWPORTS.desktop)
  await page.goto(`${APP}/login`, { waitUntil: 'domcontentloaded' }); await settle(page)
  const seq = []
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press('Tab'); await sleep(120)
    seq.push(await page.evaluate(() => {
      const el = document.activeElement
      const s = getComputedStyle(el)
      const visible = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || (s.boxShadow && s.boxShadow !== 'none')
      return `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''} "${(el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || '').trim().slice(0, 28)}" foco-visível=${visible}`
    }))
  }
  results.teclado.push({ pagina: '/login', sequenciaTab: seq })
  await login(page, USERS.admin)
  await page.goto(`${APP}/admin`, { waitUntil: 'domcontentloaded' }); await settle(page)
  await page.keyboard.press('Tab'); await sleep(150)
  const first = await page.evaluate(() => document.activeElement?.textContent?.trim())
  results.teclado.push({ pagina: '/admin', primeiroTab: first })
  await page.__ctx.close()
}

async function notFound() {
  const { page } = await newPage()
  await page.setViewport(VIEWPORTS.desktop)
  await page.goto(`${APP}/pagina-que-nao-existe`, { waitUntil: 'domcontentloaded' }); await settle(page)
  results.observacoes.push({ id: 'FE-06', texto: `/pagina-que-nao-existe (deslogado) termina em ${page.url().replace(APP, '')}` })
  await page.__ctx.close()
}

try { await audit('publico', ROUTES.publico) } catch (e) { results.observacoes.push({ id: 'erro', texto: String(e) }) }
for (const p of ['admin', 'barbeiro', 'cliente']) {
  try { await audit(p, ROUTES[p]) } catch (e) { results.observacoes.push({ id: 'erro', texto: `${p}: ${e}` }) }
}
for (const f of [flowCliente, flowBarbeiro, flowAdmin, keyboard, notFound]) {
  try { await f() } catch (e) { results.observacoes.push({ id: 'erro-fluxo', texto: `${f.name}: ${String(e).slice(0, 300)}` }) }
}
await browser.close()
fs.writeFileSync(path.join(outDir, 'navegador-resultados.json'), JSON.stringify(results, null, 1))
console.log(`páginas=${results.paginas.length} fluxos=${results.fluxos.length} obs=${results.observacoes.length}`)
