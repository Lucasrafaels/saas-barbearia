// Verificação no navegador da 1ª rodada de correções (Firefox headless, build de produção,
// API isolada com banco descartável). Sem tokens ou senhas na saída.
import fs from 'node:fs'
import path from 'node:path'
import puppeteer from 'puppeteer-core'

const [, , statePath, outDir] = process.argv
const state = JSON.parse(fs.readFileSync(statePath, 'utf8'))
const APP = 'http://127.0.0.1:5173'
const shots = path.join(outDir, 'capturas')
fs.mkdirSync(shots, { recursive: true })
const axeSrc = fs.readFileSync(new URL('./node_modules/axe-core/axe.min.js', import.meta.url), 'utf8')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const out = { verificacoes: [], erros: [] }
const check = (id, desc, ok, detalhe = '') => out.verificacoes.push({ id, verificacao: desc, ok: Boolean(ok), detalhe: String(detalhe).slice(0, 220) })

const browser = await puppeteer.launch({ browser: 'firefox', executablePath: '/usr/bin/firefox', headless: true })

async function open(email, viewport) {
  const ctx = await browser.createBrowserContext()
  const page = await ctx.newPage()
  await page.setViewport(viewport)
  const log = { console: [], pageErrors: [], api: [] }
  page.on('console', (m) => { if (['error', 'warn', 'warning'].includes(m.type())) log.console.push(m.text().slice(0, 200)) })
  page.on('pageerror', (e) => log.pageErrors.push(String(e?.message ?? e).slice(0, 200)))
  page.on('response', async (res) => {
    if (!res.url().includes(':8765/') || res.request().method() === 'OPTIONS') return
    const entry = { metodo: res.request().method(), caminho: res.url().replace(/^https?:\/\/[^/]+/, '').split('?')[0], status: res.status() }
    if (['POST', 'PATCH'].includes(entry.metodo) && entry.caminho.includes('/appointments/')) {
      try { entry.statusAgendamento = (await res.json()).status } catch { /* sem corpo */ }
    }
    log.api.push(entry)
  })
  await page.goto(`${APP}/login`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('#login-email')
  await page.type('#login-email', email)
  await page.type('#login-password', state.creds[email])
  await page.click('button[type="submit"]')
  await idle(page)
  return { ctx, page, log }
}
async function idle(page, extra = 500) { try { await page.waitForNetworkIdle({ idleTime: 400, timeout: 15000 }) } catch {} await sleep(extra) }
async function go(page, route) { await page.goto(`${APP}${route}`, { waitUntil: 'domcontentloaded' }); await idle(page) }
async function clickText(page, selector, text) {
  for (const h of await page.$$(selector)) {
    const ok = await h.evaluate((el, t) => { const r = el.getBoundingClientRect(); return r.width > 0 && !el.disabled && el.textContent.includes(t) }, text)
    if (ok) { await h.click(); return true }
  }
  return false
}
// Lê a API com a sessão do próprio navegador (o Firefox BiDi não expõe o corpo das respostas ao script)
const apiGet = (page, p) => page.evaluate(async (url) => {
  const token = JSON.parse(localStorage.getItem('barbearia.auth') || '{}').access
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
  return r.json()
}, `http://127.0.0.1:8765/api/v1${p}`)
const h1 = (page) => page.evaluate(() => document.querySelector('h1')?.textContent?.trim())
const text = (page) => page.evaluate(() => document.body.innerText)
const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
async function axe(page) {
  await page.evaluate(axeSrc)
  return page.evaluate(async () => (await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] } })).violations.map((v) => `${v.id} (${v.nodes.length})`))
}
async function pickServiceAndBarber(page) {
  await (await page.$('[role="radiogroup"][aria-label="Serviços"] [role="radio"]')).click(); await sleep(300)
  await (await page.$('[role="radiogroup"][aria-label="Barbeiros"] [role="radio"]')).click(); await idle(page)
}
async function pickOpenDayAndSlot(page, fromIndex) {
  const chips = await page.$$('[role="radiogroup"][aria-label="Dia"] [role="radio"]')
  for (let i = fromIndex; i < chips.length; i++) {
    if (await chips[i].evaluate((el) => el.disabled)) continue
    await chips[i].click(); await idle(page)
    const slot = await page.$('[role="radiogroup"][aria-label^="Horários"] [role="radio"]')
    if (slot) { await slot.click(); return i }
  }
  return -1
}

try {
  // A. Admin: configurar dias, validações do formulário ------------------------------------------
  {
    const { ctx, page, log } = await open('admin.a@exemplo.test', { width: 1440, height: 900 })
    await go(page, '/admin/barbershop')
    const marcados = await page.$$eval('input[type="checkbox"][name="dias_funcionamento"]', (els) => els.map((e) => `${e.value}:${e.checked}`))
    check('A1', 'Dados da barbearia mostra os 7 dias marcados (padrão)', marcados.length === 7 && marcados.every((m) => m.endsWith('true')), marcados.join(' '))
    // Nenhum dia marcado: bloqueado no formulário, sem requisição
    for (const cb of await page.$$('input[type="checkbox"][name="dias_funcionamento"]')) await cb.click()
    const antes = log.api.length
    await clickText(page, 'button', 'Salvar alterações'); await sleep(600)
    check('A2', 'Sem nenhum dia: mensagem e nenhuma requisição', (await text(page)).includes('Marque ao menos um dia') && !log.api.slice(antes).some((r) => r.metodo === 'PATCH'))
    await clickText(page, 'button', 'Descartar alterações'); await sleep(300)
    // BUS-05 no formulário
    await page.evaluate(() => {
      const f = document.querySelector('#shop-fechamento')
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(f, '08:00')
      f.dispatchEvent(new Event('input', { bubbles: true }))
    })
    const antes2 = log.api.length
    await clickText(page, 'button', 'Salvar alterações'); await sleep(600)
    check('A3', 'Fechamento antes da abertura: bloqueado no formulário', (await text(page)).includes('O fechamento precisa ser depois da abertura') && !log.api.slice(antes2).some((r) => r.metodo === 'PATCH'))
    await clickText(page, 'button', 'Descartar alterações'); await sleep(300)
    // Fechar o domingo
    await page.click('input[type="checkbox"][name="dias_funcionamento"][value="7"]')
    await page.screenshot({ path: path.join(shots, 'r1_admin_dias_de_funcionamento_desktop.png'), fullPage: true })
    await clickText(page, 'button', 'Salvar alterações'); await idle(page)
    const patch = log.api.filter((r) => r.metodo === 'PATCH' && r.caminho.includes('/barbershops/')).pop()
    check('A4', 'Admin fecha o domingo e salva', patch?.status === 200 && (await text(page)).includes('Dados da barbearia salvos'), JSON.stringify(patch))
    await page.reload({ waitUntil: 'domcontentloaded' }); await idle(page)
    const dom = await page.$eval('input[type="checkbox"][name="dias_funcionamento"][value="7"]', (e) => e.checked)
    const preview = await page.evaluate(() => document.body.innerText.match(/Segunda a sábado, das[^\n]*/)?.[0] ?? null)
    check('A5', 'Após recarregar: domingo desmarcado e resumo "Segunda a sábado"', dom === false && preview, preview)
    out.axeConfiguracao = await axe(page)
    await page.setViewport({ width: 390, height: 844 }); await go(page, '/admin/barbershop')
    check('A6', 'Dados da barbearia sem rolagem horizontal a 390 px', (await overflow(page)) <= 0, await overflow(page))
    await page.screenshot({ path: path.join(shots, 'r1_admin_dias_de_funcionamento_celular.png'), fullPage: true })
    // Fluxo do admin no painel
    await page.setViewport({ width: 1440, height: 900 }); await go(page, '/admin')
    const conf = await clickText(page, 'button', 'Confirmar'); await idle(page)
    check('A7', 'Admin confirma em "A seguir"', conf && (await text(page)).includes('Agendamento confirmado'))
    out.admin = { console: log.console, pageErrors: log.pageErrors, falhasApi: log.api.filter((r) => r.status >= 400) }
    await ctx.close()
  }

  // B. Cliente (celular): calendário com domingo fechado, FE-13, clique duplo ---------------------
  {
    const { ctx, page, log } = await open('cliente1@exemplo.test', { width: 390, height: 844 })
    await go(page, '/')
    const horario = await page.evaluate(() => document.body.innerText.match(/(Todos os dias|Segunda a sábado)[^\n]*/)?.[0] ?? null)
    check('B1', 'Início do cliente mostra "Segunda a sábado, das 09:00 às 19:00"', horario?.startsWith('Segunda a sábado'), horario)
    await page.screenshot({ path: path.join(shots, 'r1_cliente_inicio_dias.png') })
    await go(page, '/appointments/new')
    await pickServiceAndBarber(page)
    const chips = await page.$$eval('[role="radiogroup"][aria-label="Dia"] [role="radio"]', (els) => els.map((e) => ({ dia: e.querySelector('span')?.textContent, fechado: e.disabled, rotulo: e.getAttribute('aria-label'), texto: e.innerText.replace(/\n/g, ' ') })))
    const domingos = chips.filter((c) => c.dia === 'dom')
    check('B2', 'Domingos desabilitados e marcados como "fechado" no calendário', domingos.length >= 3 && domingos.every((c) => c.fechado && c.texto.toLowerCase().includes('fechado') && c.rotulo.includes('barbearia fechada')), JSON.stringify(domingos.slice(0, 1)))
    check('B3', 'Demais dias habilitados', chips.filter((c) => c.dia !== 'dom').every((c) => !c.fechado), `${chips.filter((c) => !c.fechado).length} de ${chips.length} habilitados`)
    const domIdx = chips.findIndex((c) => c.dia === 'dom')
    const all = await page.$$('[role="radiogroup"][aria-label="Dia"] [role="radio"]')
    const selBefore = await page.$eval('[role="radiogroup"][aria-label="Dia"] [aria-checked="true"]', (e) => e.innerText)
    await all[domIdx].click({ force: true }).catch(() => {}); await sleep(300)
    const selAfter = await page.$eval('[role="radiogroup"][aria-label="Dia"] [aria-checked="true"]', (e) => e.innerText)
    check('B4', 'Clicar num domingo não o seleciona', selBefore === selAfter, `${selBefore.replace(/\n/g, ' ')} → ${selAfter.replace(/\n/g, ' ')}`)
    await all[domIdx].scrollIntoView()
    await page.screenshot({ path: path.join(shots, 'r1_cliente_calendario_domingo_fechado.png') })
    out.axeAgendamento = await axe(page)
    check('B5', 'Agendamento sem rolagem horizontal a 390 px', (await overflow(page)) <= 0, await overflow(page))
    // 1ª reserva
    await pickOpenDayAndSlot(page, 2)
    await clickText(page, 'button', 'Revisar'); await sleep(300)
    await clickText(page, 'button', 'Confirmar agendamento'); await idle(page)
    check('B6', '1ª reserva concluída', (await h1(page)) === 'Horário reservado', await h1(page))
    // FE-13: tocar em "Agendar" na barra inferior abre um fluxo novo
    await page.click('nav[aria-label="Navegação rápida"] a[href="/appointments/new"]'); await idle(page)
    const step = await page.evaluate(() => document.querySelector('[aria-current="step"]')?.textContent?.trim())
    check('B7', 'FE-13: "Agendar" após reservar abre um agendamento novo (etapa Serviço)', (await h1(page)) === 'Agendar horário' && step === 'Serviço', `${await h1(page)} / etapa ${step}`)
    await page.screenshot({ path: path.join(shots, 'r1_fe13_agendar_depois_de_reservar.png') })
    // 2ª reserva com clique duplo no botão final
    await pickServiceAndBarber(page)
    await pickOpenDayAndSlot(page, 4)
    await clickText(page, 'button', 'Revisar'); await sleep(300)
    const postsAntes = log.api.filter((r) => r.metodo === 'POST' && r.caminho === '/api/v1/appointments/').length
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find((el) => el.textContent.includes('Confirmar agendamento'))
      b.click(); b.click()
    })
    await idle(page)
    const posts = log.api.filter((r) => r.metodo === 'POST' && r.caminho === '/api/v1/appointments/').slice(postsAntes)
    check('B8', 'Clique duplo em "Confirmar agendamento" gera uma única reserva', posts.length === 1 && posts[0].status === 201, JSON.stringify(posts))
    check('B9', '2ª reserva concluída (fluxo repetível)', (await h1(page)) === 'Horário reservado')
    const meus = (await apiGet(page, '/appointments/?page=1')).results ?? []
    const criados = [...meus].sort((a, b) => b.id - a.id).slice(0, 2)
    check('B10', 'As duas reservas do cliente nasceram "agendado"', criados.length === 2 && criados.every((a) => a.status === 'agendado'), JSON.stringify(criados.map((a) => [a.id, a.status])))
    // Também pelo menu lateral (desktop)
    await page.setViewport({ width: 1440, height: 900 }); await sleep(300)
    await page.click('aside a[href="/appointments/new"]'); await idle(page)
    check('B11', 'FE-13: "Agendar horário" no menu lateral também reinicia o fluxo', (await h1(page)) === 'Agendar horário')
    // BUS-03: remarcar um horário confirmado
    await page.setViewport({ width: 390, height: 844 })
    await go(page, '/appointments')
    const alvo = await page.evaluate(() => {
      const art = [...document.querySelectorAll('article')].find((a) => a.innerText.includes('Confirmado') && a.querySelector('a[href*="reschedule"]'))
      return art?.querySelector('a[href*="reschedule"]')?.getAttribute('href') ?? null
    })
    if (alvo) {
      await go(page, alvo)
      await pickOpenDayAndSlot(page, 6)
      await clickText(page, 'button', 'Revisar'); await sleep(300)
      const aviso = (await text(page)).includes('Ao remarcar, o novo horário volta a aguardar a confirmação')
      check('B12', 'Remarcar horário confirmado: aviso de nova confirmação', aviso)
      await page.screenshot({ path: path.join(shots, 'r1_bus03_aviso_remarcar_confirmado.png') })
      await clickText(page, 'button', 'Remarcar horário'); await idle(page)
      const patch = log.api.filter((r) => r.metodo === 'PATCH' && r.caminho.startsWith('/api/v1/appointments/')).pop()
      const id = patch?.caminho.match(/appointments\/(\d+)\//)?.[1]
      const depois = id ? await apiGet(page, `/appointments/${id}/`) : null
      check('B13', 'Remarcação do cliente volta a "agendado"', patch?.status === 200 && depois?.status === 'agendado', JSON.stringify({ patch: patch?.status, id, status: depois?.status }))
      check('B14', 'Tela final informa que aguarda confirmação', (await text(page)).toLowerCase().includes('aguarda a confirmação da barbearia'))
    } else {
      check('B12', 'Remarcar horário confirmado (havia horário confirmado futuro do cliente)', false, 'nenhum horário confirmado encontrado')
    }
    out.cliente = { console: log.console, pageErrors: log.pageErrors, falhasApi: log.api.filter((r) => r.status >= 400) }
    await ctx.close()
  }

  // C. Barbeiro (tablet): confirmar ------------------------------------------------------------------
  {
    const { ctx, page, log } = await open('joao.barbeiro@exemplo.test', { width: 820, height: 1180 })
    await go(page, '/barber/agenda?status=agendado')
    const conf = await clickText(page, 'button', 'Confirmar'); await idle(page)
    check('C1', 'Barbeiro confirma na agenda', conf && (await text(page)).includes('Agendamento confirmado'))
    out.barbeiro = { console: log.console, pageErrors: log.pageErrors, falhasApi: log.api.filter((r) => r.status >= 400) }
    await ctx.close()
  }
} catch (error) {
  out.erros.push(String(error?.stack ?? error).slice(0, 600))
}
await browser.close()
fs.writeFileSync(path.join(outDir, 'rodada1-navegador.json'), JSON.stringify(out, null, 1))
const ok = out.verificacoes.filter((v) => v.ok).length
console.log(`${out.verificacoes.length} verificações; ${ok} conforme; ${out.verificacoes.length - ok} divergentes; erros=${out.erros.length}`)
for (const v of out.verificacoes) console.log(v.ok ? 'OK ' : ' X ', v.id, v.verificacao, v.ok ? '' : `| ${v.detalhe}`)
console.log('axe configuração:', out.axeConfiguracao, '| axe agendamento:', out.axeAgendamento)
for (const p of ['admin', 'cliente', 'barbeiro']) console.log(p, JSON.stringify(out[p]))
if (out.erros.length) console.log(out.erros)
