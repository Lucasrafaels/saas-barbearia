// TEN-01 (contenção) — verificação no navegador: o build de produção do frontend consome a API só-JSON.
// Firefox headless dirigido por WebDriver BiDi com o WebSocket nativo do Node (sem dependências).
// Alvo: frontend em http://127.0.0.1:4181 (vite preview) -> API isolada 127.0.0.1:8767 -> banco DESCARTÁVEL.
// Uso: node ten01_navegador.mjs <estado_seed.json> <saida.json>   (senhas lidas do seed; nunca impressas)
import fs from 'node:fs'

const [, , seedPath, saida] = process.argv
const CREDS = JSON.parse(fs.readFileSync(seedPath, 'utf8')).creds
const FRONT = 'http://127.0.0.1:4181'
const API = 'http://127.0.0.1:8767/api/v1'

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

async function avaliar(ctx, expression) {
  const r = await cmd('script.evaluate', { expression, target: { context: ctx }, awaitPromise: true })
  return r.result?.value
}

async function ocioso(ctx, ms = 1500) {
  // Espera a rede da API ficar quieta por 700 ms (máximo `ms` extra).
  let ultimo = eventos.length
  const fim = Date.now() + 8000
  await espera(400)
  while (Date.now() < fim) {
    await espera(700)
    if (eventos.length === ultimo) break
    ultimo = eventos.length
  }
  await espera(Math.max(0, ms - 1500))
  return avaliar(ctx, 'location.pathname')
}

const PERFIS = [
  { papel: 'cliente', email: 'cliente1@exemplo.test', paginas: [['/', null], ['/services', 'Corte'], ['/barbers', 'João Navalha'], ['/appointments', null], ['/appointments/new', 'Corte'], ['/account', 'cliente1@exemplo.test']] },
  { papel: 'barbeiro', email: 'joao.barbeiro@exemplo.test', paginas: [['/', null], ['/barber/agenda', null], ['/account', 'joao.barbeiro@exemplo.test']] },
  { papel: 'admin', email: 'admin.a@exemplo.test', paginas: [['/admin', null], ['/admin/appointments', null], ['/admin/services', 'Pigmentação'], ['/admin/barbers', 'Pedro Tesoura'], ['/admin/clients', 'Carla Cliente'], ['/admin/barbershop', 'Barbearia Navalha Fictícia'], ['/account', 'admin.a@exemplo.test']] },
]
const NOMES_DE_B = ['Clara Cliente B', 'Bento Barbeiro B', 'Beatriz Proprietária B', 'Corte B', 'Barbearia Outra Fictícia']

const resultado = { frontend: FRONT, api: API, perfis: [] }
for (const perfil of PERFIS) {
  const { userContext } = await cmd('browser.createUserContext')
  const { context: ctx } = await cmd('browsingContext.create', { type: 'tab', userContext })
  const inicio = eventos.length
  const reg = { papel: perfil.papel, login: null, paginas: [] }

  await cmd('browsingContext.navigate', { context: ctx, url: `${FRONT}/login`, wait: 'complete' })
  await ocioso(ctx)
  const senha = CREDS[perfil.email]
  await avaliar(ctx, `(() => {
    const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
    for (const [nome, valor] of [['email', ${JSON.stringify(perfil.email)}], ['password', ${JSON.stringify(senha)}]]) {
      const el = document.querySelector('input[name="' + nome + '"]')
      set.call(el, valor)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }
    document.querySelector('form button[type="submit"]').click()
    return true
  })()`)
  let caminho = '/login'
  for (let i = 0; i < 20 && caminho === '/login'; i++) { await espera(300); caminho = await avaliar(ctx, 'location.pathname') }
  reg.login = { saiu_do_login: caminho !== '/login', destino: caminho }
  await ocioso(ctx)

  for (const [pagina, esperado] of perfil.paginas) {
    const antes = eventos.length
    // Carga completa da página: refaz a sessão pelo cookie de refresh e busca os dados de novo.
    await cmd('browsingContext.navigate', { context: ctx, url: FRONT + pagina, wait: 'complete' })
    const final = await ocioso(ctx, 2000)
    const texto = await avaliar(ctx, "document.body.innerText + '\\n' + [...document.querySelectorAll('input')].map((i) => i.value).join('\\n')")
    const api = eventos.slice(antes).filter((e) => e.method === 'network.responseCompleted' && e.params.context === ctx && e.params.request.url.startsWith(API))
      .map((e) => {
        const ct = (e.params.response.headers.find((h) => h.name.toLowerCase() === 'content-type')?.value?.value || '').split(';')[0]
        return { metodo: e.params.request.method, caminho: e.params.request.url.slice(API.length).split('?')[0], status: e.params.response.status, content_type: ct }
      })
    const consoleErros = eventos.slice(antes).filter((e) => e.method === 'log.entryAdded' && e.params.level === 'error' && e.params.source?.context === ctx).map((e) => e.params.text)
    reg.paginas.push({
      pagina, final, pedidos_api: api.length,
      status: Object.fromEntries(Object.entries(api.reduce((a, x) => ({ ...a, [x.status]: (a[x.status] || 0) + 1 }), {}))),
      nao_json: api.filter((x) => x.metodo !== 'OPTIONS' && x.status !== 204 && x.content_type !== 'application/json'),
      erros_api: api.filter((x) => x.status >= 400 && !(x.caminho === '/auth/refresh/' && x.status === 401)),
      status_406: api.filter((x) => x.status === 406).length,
      texto_esperado: esperado, texto_encontrado: esperado ? texto.includes(esperado) : null,
      nomes_de_B: NOMES_DE_B.filter((n) => texto.includes(n)),
      erros_console: consoleErros.slice(0, 5),
    })
  }
  reg.total_pedidos_api = eventos.slice(inicio).filter((e) => e.method === 'network.responseCompleted' && e.params.context === ctx && e.params.request.url.startsWith(API)).length
  resultado.perfis.push(reg)
  await cmd('browsingContext.close', { context: ctx })
  await cmd('browser.removeUserContext', { userContext })
}

const paginas = resultado.perfis.flatMap((p) => p.paginas)
resultado.resumo = {
  logins_ok: resultado.perfis.filter((p) => p.login.saiu_do_login).length,
  paginas: paginas.length,
  pedidos_api: resultado.perfis.reduce((a, p) => a + p.total_pedidos_api, 0),
  respostas_nao_json: paginas.reduce((a, p) => a + p.nao_json.length, 0),
  respostas_406: paginas.reduce((a, p) => a + p.status_406, 0),
  erros_api: paginas.reduce((a, p) => a + p.erros_api.length, 0),
  paginas_com_texto_esperado: paginas.filter((p) => p.texto_encontrado === true).length + '/' + paginas.filter((p) => p.texto_esperado).length,
  paginas_com_nomes_de_B: paginas.filter((p) => p.nomes_de_B.length).length,
  erros_console: paginas.reduce((a, p) => a + p.erros_console.length, 0),
}
fs.writeFileSync(saida, JSON.stringify(resultado, null, 1))
console.log(JSON.stringify(resultado.resumo))
for (const p of resultado.perfis) {
  console.log(`${p.papel}: login -> ${p.login.destino}`)
  for (const g of p.paginas) console.log(`  ${g.pagina} -> ${g.final} | API ${g.pedidos_api} ${JSON.stringify(g.status)} | texto ${g.texto_encontrado} | não-JSON ${g.nao_json.length} | erros ${g.erros_api.length} | console ${g.erros_console.length}`)
}
await cmd('session.end').catch(() => {})
ws.close()
