// Carregado com `node --import` antes dos testes. Faz as importações relativas
// sem extensão ("./format", "../types") apontarem para o arquivo .ts/.tsx,
// como o Vite resolve. Assim os testes rodam com o executor nativo do Node
// (que já remove os tipos do TypeScript), sem nenhuma dependência nova.
import { existsSync } from 'node:fs'
import { registerHooks } from 'node:module'
import { fileURLToPath } from 'node:url'

const HAS_EXTENSION = /\.[cm]?[jt]sx?$/

registerHooks({
  resolve(specifier, context, nextResolve) {
    const relative = specifier.startsWith('./') || specifier.startsWith('../')
    if (relative && context.parentURL && !HAS_EXTENSION.test(specifier)) {
      for (const suffix of ['.ts', '.tsx', '/index.ts']) {
        const url = new URL(specifier + suffix, context.parentURL)
        if (existsSync(fileURLToPath(url))) return nextResolve(url.href, context)
      }
    }
    return nextResolve(specifier, context)
  },
})
