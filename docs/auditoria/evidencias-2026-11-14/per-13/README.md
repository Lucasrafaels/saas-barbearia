# Evidências da correção do PER-13 e da conclusão do SEC-10 (14/11/2026)

Correção do PER-13: em `GET /users/{id}/`, cliente e barbeiro recebiam 403 para outro usuário da mesma barbearia e 404 para um de outra barbearia ou inexistente. A análise está na seção 25 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). As pastas das etapas anteriores (`ten-01-contencao/`, `ten-01-estrutural/`, `ten-02/`, `sec-10/`) não foram alteradas.

## Como foi verificado

- **Alteração:** `diff/diff-somente-per13.patch` traz só esta etapa: `accounts/views.py`, o teste novo e as asserções de GET atualizadas em três arquivos de teste. A comparação é com a árvore anterior, que já tinha a contenção, o TEN-01, o TEN-02 e o `exclude_appointment_id`.
- **"Anterior" e "corrigido":** o código anterior é uma cópia dessa árvore, montada fora do projeto, sem comandos destrutivos do Git. Os mesmos testes, rastreamentos e sondagens rodaram nas duas versões.
- **Bancos:** SQLite em memória e um **PostgreSQL 18.3 descartável** (`initdb` no diretório temporário, só TCP em `127.0.0.1:55432`), já apagado. **O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Nenhuma migração foi criada nem aplicada.**
- **SQL do servidor real:** o banco descartável da sondagem rodou com `log_statement = 'all'`, e cada pedido ficou entre dois marcadores no log. O log bruto não foi copiado. Nos JSONs, os hashes de senha foram substituídos por `<hash de senha removido>`.
- **API:** quatro instâncias do `runserver` sobre o banco descartável, com o seed fictício da auditoria (`scripts/per13_servidores.sh`):

  | Porta | Código | `DEBUG` |
  |---|---|---|
  | 8767 | corrigido | `True` |
  | 8768 | corrigido | `False`, também na importação |
  | 8769 | anterior | `True` |
  | 8770 | anterior | `False`, também na importação |

- **Dados:** todos fictícios (`*@alfa.test`, `*@exemplo.test`, …). Nenhum arquivo desta pasta contém senha, hash de senha, token, `SECRET_KEY` ou string de conexão.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-per13.patch` | `accounts/views.py`, `accounts/test_per13.py` (novo) e as asserções de GET de detalhe atualizadas em `accounts/test_multitenant_isolation.py`, `accounts/test_permissions.py` e `config/test_renderers.py` |
| `testes/antes-e-depois-por-teste.txt` | Os 9 testes do PER-13, no código anterior e no corrigido |
| `testes/testes-novos-codigo-anterior.txt`, `testes-novos-codigo-corrigido.txt` | As duas execuções completas |
| `testes/suite-completa-sqlite.txt`, `suite-completa-postgresql18.txt`, `suite-completa-postgresql18-debug-false.txt` | Suíte completa: SQLite, PG 18.3 e PG com `DEBUG=False` na importação |
| `testes/testes-isolamento-postgresql18-debug-mode.txt` | Os 123 testes de isolamento, permissões e remarcação com o executor em `--debug-mode` (`DEBUG=True`) |
| `testes/django-check-makemigrations.txt` | `check`, `makemigrations --check --dry-run` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test`, `tsc` (app e node), ESLint e build |
| `sql/rastreamento-respostas-sql-*.txt` | Matriz de respostas por papel e método (GET, HEAD, PATCH, PUT, DELETE) em `/users/{id}/`, com o WHERE da busca, nas duas versões |
| `api/per13-resumo-http-sql.txt` | Resumo da sondagem HTTP com o SQL do servidor, nas quatro instâncias. Inclui trechos de SQL e o bloco do SEC-12 (PATCH) |
| `api/sondagem-http-sql-*.json.gz` | Saída bruta da sondagem (130 pedidos por instância), sem hashes de senha |
| `api/matriz-html-json-resumo.txt`, `api/matriz-html-json-*.json.gz` | A matriz HTML/JSON da contenção no código corrigido: continua só JSON |
| `api/isolamento-217-verificacoes-pos-per13.json` / `.txt` e `api/isolamento-comparacao-sec10-x-per13.txt` | As 217 verificações da auditoria no código corrigido e a comparação com a etapa anterior |
| `api/logs-runserver-4-instancias.tar.gz` | Logs de acesso das quatro instâncias |
| `navegador/navegador-per13.json` | Firefox headless no build de produção: login e 16 páginas, inclusive "Minha conta"; agendamento, remarcação e confirmação pela interface |
| `scripts/` | `rastrear_per13.py`, `per13_probe.py`, `per13_resumo.py`, `per13_servidores.sh`, `ten01_probe.py`, `comparar_iso.py`, o roteiro do navegador e as settings descartáveis |

## Como reproduzir

1. **Testes:** `venv/bin/python manage.py test accounts.test_per13 --settings=config.test_settings`.
2. **Matriz de respostas e SQL:** de dentro do diretório do código, rode `DEBUG=True python scripts/rastrear_per13.py <rótulo>`. Ele usa SQLite em memória.
3. **Sondagem HTTP com SQL:**
   1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`.
   2. Ajuste os caminhos absolutos em `scripts/per13_servidores.sh` e rode o script.
   3. Rode `venv/bin/python -I scripts/per13_probe.py <estado_seed.json> http://127.0.0.1:8767 <rótulo> <log do PostgreSQL> <saída.json>`.
   4. Com `logging_collector = on`, o log fica em `pgdata/log/`.

Reprodução manual, com um cliente da barbearia A: `GET /api/v1/users/<ID do admin da mesma barbearia>/` e `GET /api/v1/users/999999/`.

| Versão | Admin da mesma barbearia | ID inexistente |
|---|---|---|
| **Agora** | 404 `{"detail":"No User matches the given query."}` | Igual |
| **Antes** | 403 "Você não tem permissão para executar essa ação." | 404 |
