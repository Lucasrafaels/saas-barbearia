# Evidências da 2ª rodada de correções (13/11/2026) — somente frontend

Correções de FE-14, FE-21 e FE-22. Acompanhamento na seção 19 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md).

## Como foi verificado

- **Testes automatizados de frontend:** `npm test` (executor nativo do Node 26, sem dependências novas). Os mesmos testes rodaram também numa cópia do frontend no estado do início da rodada, montada fora do projeto.
- **Navegador:** Firefox headless contra dois builds de produção, o do início da rodada ("antes") e o corrigido ("depois"). O roteiro é o mesmo nos dois. A API isolada usa um PostgreSQL 16 descartável, já removido, com os dados fictícios da auditoria. O banco real não foi usado.
- **Escopo:** nada fora do frontend mudou (`testes/escopo-backend-config-dependencias.txt`).
- **Segredos:** nenhum arquivo contém senha, token ou `SECRET_KEY`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `testes/testes-frontend-codigo-corrigido.log` | `npm test`: 45/45 (13 FE-14, 6 FE-21, 26 FE-22) |
| `testes/testes-frontend-codigo-anterior.log` | Os mesmos testes no código do início da rodada: 7 de 13 do FE-14 falham; os arquivos de FE-21 e FE-22 não carregam (as funções não existiam) |
| `testes/frontend-tipos-lint-build.log` | `tsc` (app e node), ESLint e build de produção |
| `testes/suite-backend-sqlite.log` | Suíte do backend (inalterado): 391 testes OK |
| `testes/escopo-backend-config-dependencias.txt` | SHA-256 dos `.py`, de `.env`, `requirements.txt` e `docker-compose.yml`, número de migrações e `package-lock.json` |
| `navegador/navegador-build-antes.json` | Roteiro da rodada no build anterior: 57 de 68 conformes |
| `navegador/navegador-build-depois.json` | Roteiro da rodada no build corrigido: 68 de 68 conformes, 0 erros de console, página ou API |
| `navegador/rotulo-mais-longo-lateral.json` | Largura do rótulo mais longo da lateral (desktop e gaveta do celular) |
| `navegador/reexecucao-rodada1.json` | Roteiro da rodada 1 repetido no build corrigido |
| `navegador/varredura-completa.json` | Varredura da auditoria repetida no build corrigido (21 rotas × 5 larguras) |
| `navegador/capturas/` | `antes_*` e `depois_*`: aviso de desativação (desktop e celular), hoje fechado (admin e calendário do cliente), faixa de dias (imagens idênticas), "Dados da barbearia" no celular; rótulo mais longo |
| `diff/diff-somente-correcoes.patch` | Somente as alterações desta rodada |
| `scripts/` | `rodada2.mjs` (roteiro antes/depois) e `medir_rotulo.mjs` |
