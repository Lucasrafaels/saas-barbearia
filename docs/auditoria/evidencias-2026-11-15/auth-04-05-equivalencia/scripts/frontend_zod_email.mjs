// AUTH-04/05 — o que o esquema de e-mail dos formulários do frontend aceita (z.string().trim().email(), o mesmo das
// telas de cadastro, login, conta, clientes, barbeiros e recuperação), e o que o String.prototype.trim() remove.
// Uso (de dentro de frontend/): node <este arquivo> <saída.json>
import { z } from 'zod'
import { writeFileSync } from 'node:fs'
const schema = z.string().trim().email('Informe um e-mail válido.')
const casos = {
  'minúsculas': 'cliente.b@beta.test', 'maiúsculas': 'Cliente.B@BETA.TEST', 'espaços nas pontas': '  cliente.b@beta.test  ',
  'NBSP nas pontas': ' cliente.b@beta.test ', 'BOM no fim': 'cliente.b@beta.test﻿',
  'domínio com acento': 'cliente@álfa.test', 'İ no domínio': 'x@İ.test', 'parte local com acento': 'joão@exemplo.test',
  'ZWSP no domínio': 'x@exem​plo.test', 'soft hyphen no domínio': 'x@exem­plo.test',
  'letra do Unicode 16 (U+A7CB)': 'x@aꟋb.test', 'punycode': 'x@xn--lfa-1la.test',
  'caracteres especiais ASCII': "a!#$%&'*+/=?^_`{|}~-b@exemplo.test",
}
const resultado = {}
for (const [nome, valor] of Object.entries(casos)) {
  const r = schema.safeParse(valor)
  resultado[nome] = { aceito: r.success, valor_depois: r.success ? r.data : null }
}
const removidos = []
for (let c = 1; c <= 0x10ffff; c++) {
  if (c >= 0xd800 && c <= 0xdfff) continue
  const ch = String.fromCodePoint(c)
  if ((ch + 'a' + ch).trim() === 'a') removidos.push('U+' + c.toString(16).toUpperCase().padStart(4, '0'))
}
const saida = { zod_email: resultado, js_trim_remove: removidos }
writeFileSync(process.argv[2], JSON.stringify(saida, null, 1))
console.log(JSON.stringify(resultado, null, 1))
console.log('js trim remove', removidos.length, 'pontos:', removidos.join(' '))
