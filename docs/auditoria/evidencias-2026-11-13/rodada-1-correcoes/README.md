# Evidências da 1ª rodada de correções (13/11/2026)

Correções de BUS-15, BUS-03, BUS-06, BUS-05, BUS-04 e FE-13. Acompanhamento na seção 18 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md).

## Como foi verificado

- **Testes com escrita:** rodaram em SQLite em memória (`config.test_settings`) e num PostgreSQL 16 descartável, num container próprio em `tmpfs`, já removido. O banco real não foi usado, e nenhuma migração rodou nele.
- **Prova de "falha antes / passa depois":** os 64 testes novos rodaram também numa cópia do backend no estado anterior à rodada, ou seja, HEAD + alterações já existentes do dono, montada fora do projeto.
- **API e navegador:** contra a API isolada (mesmo código, banco descartável com o seed fictício da auditoria) e o build de produção do frontend, no Firefox headless.
- **Segredos:** nenhum arquivo contém senha, token ou `SECRET_KEY`.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `testes/antes-e-depois-por-teste.txt` | Os 64 testes novos: 38 falham no código anterior (reproduzem os defeitos), 26 passam nos dois (protegem fluxos legítimos) e 64 passam no código corrigido |
| `testes/testes-novos-no-codigo-anterior.log` | Execução na cópia anterior às correções |
| `testes/testes-novos-no-codigo-corrigido.log` | Execução no código corrigido |
| `testes/suite-completa-sqlite.log` | 391 testes, OK (9 pulados: exigem PostgreSQL) |
| `testes/suite-completa-postgresql16.log` | 391 testes, OK, 0 pulados |
| `testes/cobertura-modulos-alterados.txt` | Cobertura dos 5 módulos alterados (92%) |
| `testes/migracao-0006-ida-volta.txt` | Migração `barbershops.0006`: aplicar, desfazer e reaplicar num banco descartável com 419 agendamentos, sem perda |
| `testes/frontend-tipos-lint-build.log` | `tsc` (app e node), ESLint e build de produção |
| `api/sondagem-rodada1.json` / `.txt` | 28 verificações HTTP dos cinco itens de backend pelos três perfis: 28 conforme |
| `api/sondagem-auditoria-repetida.json` | As 91 verificações da auditoria repetidas na API corrigida |
| `api/sondagem-auditoria-repetida-comparacao.txt` | 4 itens passaram a conforme e nenhum regrediu |
| `navegador/navegador-rodada1.json` | 22 verificações de interface (admin, cliente e barbeiro), axe-core e erros de console e de API |
| `navegador/varredura-completa-105-cargas.json` | Varredura da auditoria repetida: 21 rotas × 5 larguras, sem rolagem horizontal nem erros |
| `navegador/capturas/` | Dias de funcionamento (desktop e celular), calendário com domingo fechado, início do cliente, FE-13 e aviso de remarcação |
| `diff/diff-somente-correcoes.patch` | Somente as alterações desta rodada, separadas do redesign e do backend já não commitados |
| `scripts/` | `rodada1_probe.py` (API) e `rodada1.mjs` (navegador) |
