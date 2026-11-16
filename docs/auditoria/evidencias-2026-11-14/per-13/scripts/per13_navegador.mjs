// PER-13 — verificação no navegador (conta pelo /users/me/, agendamento, remarcação e confirmação). Base: roteiro do TEN-01 estrutural do build de produção contra a API corrigida.
// Firefox headless por WebDriver BiDi com o WebSocket nativo do Node (sem dependências).
// Cobre: login e 16 páginas dos três perfis; agendamento e remarcação reais pelo cliente (POST e PATCH com
// cliente, barbeiro e serviço, os campos que agora têm escopo de tenant); confirmação pela agenda.
// Alvo: frontend em http://127.0.0.1:4181 (vite preview) -> API isolada 127.0.0.1:8767 -> banco DESCARTÁVEL.
// Uso: node ten01e_navegador.mjs <estado_seed.json> <saida.json>   (senhas lidas do seed; nunca impressas)
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'

const [, , seedPath, saida] = process.argv
const CREDS = JSON.parse(fs.readFileSync(seedPath, 'utf8')).creds
const FRONT = 'http://127.0.0.1:4181'
const API = 'http://127.0.0.1:8767/api/v1'

// Leitura no banco descartável, só para conferir o resultado dos fluxos (somente leitura).
const sql = (consulta) => execFileSync('psql', ['-X', '-w', '-h', '127.0.0.1', '-p', '55432', '-U', 'smoke', '-d', 'iso_db', '-Atc',
  `set default_transaction_read_only = on; ${consulta}`], { env: { PATH: '/usr/bin:/bin' } }).toString().trim().split('\n').pop()

const ws = new WebSocket('ws://127.0.0.1:9222/session')
await new Promise((ok, erro) => { ws.onopen = ok; ws.onerror = erro })
let seq = 0
const pendentes = new Map()
const eventos = []
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data)
  if (msg.id && pendentes.has(msg.id)) {
    const { ok, erro } = pendentes.get(msg.id)
    pendentes.delete(msg.id)
    msg.type === 'error' ? erro(new Error(`${msg.error}: ${msg.message}`)) : ok(msg.result)
  } else if (msg.type === 'event') {
    eventos.push(msg)
  }
}
const cmd = (method, params = {}) => new Promise((ok, erro) => {
  const id = ++seq
  pendentes.set(id, { ok, erro })
  ws.send(JSON.stringify({ id, method, params }))
})
const espera = (ms) => new Promise((r) => setTimeout(r, ms))

await cmd('session.new', { capabilities: {} })
await cmd('session.subscribe', { events: ['network.responseCompleted', 'log.entryAdded'] })

const avaliar = async (ctx, expression) => (await cmd('script.evaluate', { expression, target: { context: ctx }, awaitPromise: true })).result?.value

async function ocioso(ms = 1500) {
  let ultimo = eventos.length
  const fim = Date.now() + 8000
  await espera(400)
  while (Date.now() < fim) {
    await espera(700)
    if (eventos.length === ultimo) break
    ultimo = eventos.length
  }
  await espera(Math.max(0, ms - 1500))
}

async function ate(ctx, expressao, tentativas = 40) {
  for (let i = 0; i < tentativas; i++) {
    if (await avaliar(ctx, expressao)) return true
    await espera(250)
  }
  return false
}

const chamadasApi = (ctx, desde) => eventos.slice(desde)
  .filter((e) => e.method === 'network.responseCompleted' && e.params.context === ctx && e.params.request.url.startsWith(API))
  .map((e) => ({
    metodo: e.params.request.method,
    caminho: e.params.request.url.slice(API.length).split('?')[0].replace(/\d+/g, '{id}'),
    com_exclude: e.params.request.url.includes('exclude_appointment_id='),
    status: e.params.response.status,
    content_type: (e.params.response.headers.find((h) => h.name.toLowerCase() === 'content-type')?.value?.value || '').split(';')[0],
  }))
const errosConsole = (ctx, desde) => eventos.slice(desde)
  .filter((e) => e.method === 'log.entryAdded' && e.params.level === 'error' && e.params.source?.context === ctx).map((e) => e.params.text)

async function entrar(email) {
  const { userContext } = await cmd('browser.createUserContext')
  const { context: ctx } = await cmd('browsingContext.create', { type: 'tab', userContext })
  await cmd('browsingContext.navigate', { context: ctx, url: `${FRONT}/login`, wait: 'complete' })
  await ocioso()
  await avaliar(ctx, `(() => {
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    for (const [nome, valor] of [['email', ${JSON.stringify(email)}], ['password', ${JSON.stringify(CREDS[email])}]]) {
      const el = document.querySelector('input[name="' + nome + '"]')
      set.call(el, valor)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    document.querySelector('form button[type="submit"]').click()
    return true
  })()`)
  const saiu = await ate(ctx, 'location.pathname !== "/login"')
  await ocioso()
  return { ctx, userContext, saiu, destino: await avaliar(ctx, 'location.pathname') }
}

const clicarTexto = (ctx, inicio) => avaliar(ctx, `(() => {
  const b = [...document.querySelectorAll('button')].find((x) => !x.disabled && x.textContent.trim().startsWith(${JSON.stringify(inicio)}))
  if (!b) return false
  b.click(); return true
})()`)
const clicarRadio = (ctx, seletorGrupo, indice = 0) => avaliar(ctx, `(() => {
  const r = [...document.querySelectorAll(${JSON.stringify(seletorGrupo)} + ' [role=radio]:not([disabled])')]
  if (r.length <= ${indice}) return false
  r[${indice}].click(); return true
})()`)

const PERFIS = [
  { papel: 'cliente', email: 'cliente1@exemplo.test', paginas: [['/', null], ['/services', 'Corte'], ['/barbers', 'João Navalha'], ['/appointments', null], ['/appointments/new', 'Corte'], ['/account', 'cliente1@exemplo.test']] },
  { papel: 'barbeiro', email: 'joao.barbeiro@exemplo.test', paginas: [['/', null], ['/barber/agenda', null], ['/account', 'joao.barbeiro@exemplo.test']] },
  { papel: 'admin', email: 'admin.a@exemplo.test', paginas: [['/admin', null], ['/admin/appointments', null], ['/admin/services', 'Pigmentação'], ['/admin/barbers', 'Pedro Tesoura'], ['/admin/clients', 'Carla Cliente'], ['/admin/barbershop', 'Barbearia Navalha Fictícia'], ['/account', 'admin.a@exemplo.test']] },
]
const NOMES_DE_B = ['Clara Cliente B', 'Bento Barbeiro B', 'Beatriz Proprietária B', 'Corte B', 'Barbearia Outra Fictícia']
const resultado = { frontend: FRONT, api: API, perfis: [], fluxos: [] }

for (const perfil of PERFIS) {
  const inicio = eventos.length
  const s = await entrar(perfil.email)
  const reg = { papel: perfil.papel, login: { saiu_do_login: s.saiu, destino: s.destino }, paginas: [] }
  for (const [pagina, esperado] of perfil.paginas) {
    const antes = eventos.length
    await cmd('browsingContext.navigate', { context: s.ctx, url: FRONT + pagina, wait: 'complete' })
    await ocioso(2000)
    const texto = await avaliar(s.ctx, "document.body.innerText + '\\n' + [...document.querySelectorAll('input')].map((i) => i.value).join('\\n')")
    const api = chamadasApi(s.ctx, antes)
    reg.paginas.push({
      pagina, final: await avaliar(s.ctx, 'location.pathname'), pedidos_api: api.length,
      nao_json: api.filter((x) => x.metodo !== 'OPTIONS' && x.status !== 204 && x.content_type !== 'application/json').length,
      erros_api: api.filter((x) => x.status >= 400 && !(x.caminho === '/auth/refresh/' && x.status === 401)),
      texto_esperado: esperado, texto_encontrado: esperado ? texto.includes(esperado) : null,
      nomes_de_B: NOMES_DE_B.filter((n) => texto.includes(n)), erros_console: errosConsole(s.ctx, antes).slice(0, 5),
    })
  }
  reg.total_pedidos_api = chamadasApi(s.ctx, inicio).length
  resultado.perfis.push(reg)
  await cmd('browsingContext.close', { context: s.ctx })
  await cmd('browser.removeUserContext', { userContext: s.userContext })
}

// Fluxo do cliente: agendar e remarcar pela interface.
{
  const s = await entrar('cliente1@exemplo.test')
  const idCliente = sql("select id from accounts_user where email='cliente1@exemplo.test'")
  const ultimoAntes = Number(sql(`select coalesce(max(id), 0) from appointments_appointment where cliente_id=${idCliente}`))
  const passos = {}
  let desde = eventos.length
  await cmd('browsingContext.navigate', { context: s.ctx, url: `${FRONT}/appointments/new`, wait: 'complete' })
  await ocioso()
  passos.servico = await clicarRadio(s.ctx, '[role=radiogroup][aria-label="Serviços"]', 0)
  passos.barbeiro = await ate(s.ctx, '!!document.querySelector(\'[role=radiogroup][aria-label="Barbeiros"] [role=radio]\')') && await clicarRadio(s.ctx, '[role=radiogroup][aria-label="Barbeiros"]', 0)
  passos.dia = await ate(s.ctx, '!!document.querySelector(\'[role=radiogroup][aria-label="Dia"] [role=radio]\')') && await clicarRadio(s.ctx, '[role=radiogroup][aria-label="Dia"]', 5)
  passos.horario = await ate(s.ctx, '!!document.querySelector(\'[role=radiogroup][aria-label^="Horários"] [role=radio]:not([disabled])\')') && await clicarRadio(s.ctx, '[role=radiogroup][aria-label^="Horários"]', 0)
  passos.revisar = await clicarTexto(s.ctx, 'Revisar')
  passos.confirmar = await ate(s.ctx, '[...document.querySelectorAll("button")].some((b) => b.textContent.includes("Confirmar agendamento"))') && await clicarTexto(s.ctx, 'Confirmar agendamento')
  passos.marcado = await ate(s.ctx, 'document.body.textContent.includes("Está marcado.")')
  await ocioso()
  const criacao = chamadasApi(s.ctx, desde).filter((x) => x.metodo === 'POST' && x.caminho === '/appointments/')
  const novo = Number(sql(`select coalesce(max(id), 0) from appointments_appointment where cliente_id=${idCliente}`))
  const linhaNova = novo > ultimoAntes ? sql(`select a.barbershop_id = b.barbershop_id and a.barbershop_id = s.barbershop_id and a.barbershop_id = c.barbershop_id from appointments_appointment a join barbershops_barber b on b.id=a.barbeiro_id join services_service s on s.id=a.servico_id join accounts_user c on c.id=a.cliente_id where a.id=${novo}`) : null
  resultado.fluxos.push({ fluxo: 'cliente agenda pela interface', passos, post: criacao, criado: novo > ultimoAntes, mesmo_tenant_em_todos_os_vinculos: linhaNova === 't', erros_console: errosConsole(s.ctx, desde) })

  if (novo > ultimoAntes) {
    const horaAntes = sql(`select data_hora from appointments_appointment where id=${novo}`)
    desde = eventos.length
    const p2 = {}
    await cmd('browsingContext.navigate', { context: s.ctx, url: `${FRONT}/appointments/new?reschedule=${novo}`, wait: 'complete' })
    await ocioso()
    p2.dia = await ate(s.ctx, '!!document.querySelector(\'[role=radiogroup][aria-label="Dia"] [role=radio]\')') && await clicarRadio(s.ctx, '[role=radiogroup][aria-label="Dia"]', 6)
    p2.horario = await ate(s.ctx, '!!document.querySelector(\'[role=radiogroup][aria-label^="Horários"] [role=radio]:not([disabled])\')') && await clicarRadio(s.ctx, '[role=radiogroup][aria-label^="Horários"]', 1)
    p2.revisar = await clicarTexto(s.ctx, 'Revisar')
    p2.remarcar = await ate(s.ctx, '[...document.querySelectorAll("button")].some((b) => b.textContent.includes("Remarcar horário"))') && await clicarTexto(s.ctx, 'Remarcar horário')
    await ocioso(2500)
    const patch = chamadasApi(s.ctx, desde).filter((x) => x.metodo === 'PATCH')
    const horaDepois = sql(`select data_hora from appointments_appointment where id=${novo}`)
    const horariosComExclusao = chamadasApi(s.ctx, desde).filter((x) => x.caminho === '/appointments/available-slots/' && x.com_exclude)
    resultado.fluxos.push({ fluxo: 'cliente remarca pela interface', passos: p2, horarios_com_exclude_appointment_id: horariosComExclusao.map((x) => x.status), patch, horario_mudou: horaAntes !== horaDepois, erros_console: errosConsole(s.ctx, desde) })
  }
  await cmd('browsingContext.close', { context: s.ctx })
  await cmd('browser.removeUserContext', { userContext: s.userContext })
}

// Fluxo da barbearia: o admin confirma um horário "agendado" de Bruno Cliente (cliente1) pela tela de agendamentos.
// (Os horários de clientes promovidos a barbeiro pela sondagem MT-BA não podem ser confirmados, antes e depois.)
{
  const s = await entrar('admin.a@exemplo.test')
  const desde = eventos.length
  await cmd('browsingContext.navigate', { context: s.ctx, url: `${FRONT}/admin/appointments`, wait: 'complete' })
  await ocioso(2000)
  const alvo = await avaliar(s.ctx, `(() => {
    const b = [...document.querySelectorAll('button')].find((x) => !x.disabled && x.textContent.trim().startsWith('Confirmar') && x.textContent.includes('Bruno Cliente'))
    if (!b) return null
    const texto = b.textContent.trim(); b.click(); return texto
  })()`)
  await ocioso(2000)
  const patch = chamadasApi(s.ctx, desde).filter((x) => x.metodo === 'PATCH')
  resultado.fluxos.push({ fluxo: 'admin confirma horário em /admin/appointments', botao: alvo, patch, erros_console: errosConsole(s.ctx, desde) })
  await cmd('browsingContext.close', { context: s.ctx })
  await cmd('browser.removeUserContext', { userContext: s.userContext })
}

const paginas = resultado.perfis.flatMap((p) => p.paginas)
resultado.resumo = {
  logins_ok: resultado.perfis.filter((p) => p.login.saiu_do_login).length,
  paginas: paginas.length,
  pedidos_api: resultado.perfis.reduce((a, p) => a + p.total_pedidos_api, 0),
  respostas_nao_json: paginas.reduce((a, p) => a + p.nao_json, 0),
  erros_api: paginas.reduce((a, p) => a + p.erros_api.length, 0),
  paginas_com_texto_esperado: `${paginas.filter((p) => p.texto_encontrado === true).length}/${paginas.filter((p) => p.texto_esperado).length}`,
  paginas_com_nomes_de_B: paginas.filter((p) => p.nomes_de_B.length).length,
  erros_console: paginas.reduce((a, p) => a + p.erros_console.length, 0) + resultado.fluxos.reduce((a, f) => a + f.erros_console.length, 0),
  fluxos: resultado.fluxos.map((f) => `${f.fluxo}: ${JSON.stringify((f.post || f.patch || []).map((x) => `${x.metodo} ${x.caminho} ${x.status}`))}`),
}
fs.writeFileSync(saida, JSON.stringify(resultado, null, 1))
console.log(JSON.stringify(resultado.resumo, null, 1))
for (const f of resultado.fluxos) console.log(JSON.stringify(f))
await cmd('session.end').catch(() => {})
ws.close()
