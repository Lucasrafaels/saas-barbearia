# Evidências da correção do SEC-10: `exclude_appointment_id` (14/11/2026)

Correção do caminho do SEC-10 pelo `exclude_appointment_id` de `GET /appointments/available-slots/` (MT-AV-02). A análise está na seção 24 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md).

## Como foi verificado

- **Alteração:** `diff/diff-somente-sec10.patch` traz só esta etapa: `appointments/views.py` e o teste novo. A comparação é com a árvore anterior, que já tinha a contenção e as correções do TEN-01 e do TEN-02.
- **"Anterior" e "corrigido":** o código anterior é uma cópia da árvore antes desta etapa, montada fora do projeto. Os mesmos testes, rastreamentos e sondagens rodaram nas duas versões.
- **Bancos:** SQLite em memória e um **PostgreSQL 18.3 descartável** (`initdb` no diretório temporário, só TCP em `127.0.0.1:55432`), já apagado. **O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Nenhuma migração foi criada nem aplicada.**
- **SQL do servidor real:** o banco descartável da sondagem rodou com `log_statement = 'all'`, e cada pedido ficou entre dois marcadores no log. O log bruto não foi copiado, porque contém hashes de senha e tokens das contas descartáveis; nos JSONs, os hashes foram substituídos por `<hash de senha removido>`.
- **API:** quatro instâncias do `runserver` sobre o banco descartável, com o seed fictício da auditoria (`scripts/sec10_servidores.sh`):

  | Porta | Código | `DEBUG` |
  |---|---|---|
  | 8767 | corrigido | `True` |
  | 8768 | corrigido | `False`, também na importação |
  | 8769 | anterior | `True` |
  | 8770 | anterior | `False`, também na importação |

- **Segredos:** nenhum arquivo desta pasta contém senha, hash de senha, token, `SECRET_KEY` ou string de conexão.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-sec10.patch` | `appointments/views.py` e `appointments/test_sec10.py` |
| `testes/antes-e-depois-por-teste.txt` | Os 11 testes do SEC-10, no código anterior e no corrigido |
| `testes/testes-novos-codigo-anterior.txt`, `testes-novos-codigo-corrigido.txt` | As duas execuções completas |
| `testes/suite-completa-sqlite.txt`, `suite-completa-postgresql18.txt`, `suite-completa-postgresql18-debug-false.txt` | Suíte completa: SQLite, PG 18.3 e PG com `DEBUG=False` na importação |
| `testes/testes-isolamento-postgresql18-debug-mode.txt` | Os 105 testes de isolamento e de `exclude_appointment_id` com o executor em `--debug-mode` (`DEBUG=True`) |
| `testes/django-check-makemigrations.txt` | `check`, `makemigrations --check --dry-run` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test`, `tsc` (app e node), ESLint e build |
| `sql/rastreamento-sql-anterior.txt`, `rastreamento-sql-corrigido.txt` | Resposta e SQL para o próprio agendamento, o de outra barbearia, um inexistente, o parâmetro omitido e valores malformados, nas duas versões. Inclui a verificação do PER-13 (`GET /users/{id}/`) |
| `api/sec10-resumo-http-sql.txt` | Resumo da sondagem HTTP com o SQL do servidor, nas quatro instâncias, com trechos de SQL |
| `api/sondagem-http-sql-*.json.gz` | Saída bruta da sondagem: seis papéis nos dois sentidos, conta sem barbearia; sem hashes de senha |
| `api/matriz-html-json-resumo.txt`, `api/matriz-html-json-*.json.gz` | A matriz HTML/JSON da contenção no código corrigido: continua só JSON |
| `api/isolamento-217-verificacoes-pos-sec10.json` / `.txt` e `api/isolamento-comparacao-ten02-x-sec10.txt` | As 217 verificações da auditoria no código corrigido e a comparação com a etapa anterior |
| `api/logs-runserver-4-instancias.tar.gz` | Logs de acesso das quatro instâncias |
| `navegador/navegador-sec10.json` | Firefox headless no build de produção: login e 16 páginas; agendamento, **remarcação** (a tela usa `exclude_appointment_id`) e confirmação pela interface |
| `scripts/` | `rastrear_sec10.py`, `sec10_probe.py`, `sec10_servidores.sh`, `ten01_probe.py`, `comparar_iso.py`, o roteiro do navegador e as settings descartáveis |

## Como reproduzir

1. **Testes:** `venv/bin/python manage.py test appointments.test_sec10 --settings=config.test_settings`.
2. **Rastreamento:** de dentro do diretório do código a examinar, rode `DEBUG=True python scripts/rastrear_sec10.py <rótulo>`. Ele usa SQLite em memória.
3. **Sondagem HTTP com SQL:**
   1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`.
   2. Ajuste os caminhos absolutos em `scripts/sec10_servidores.sh` e rode o script.
   3. Rode `venv/bin/python -I scripts/sec10_probe.py <estado_seed.json> http://127.0.0.1:8767 <rótulo> <log do PostgreSQL> <saída.json>`.
   4. Com `logging_collector = on`, o log fica em `pgdata/log/`.

Reprodução manual, com o cliente da barbearia A:

- `GET /api/v1/appointments/available-slots/?barbeiro=<A>&servico=<A>&data=<dia>&exclude_appointment_id=<agendamento de B>`
- o mesmo pedido com `exclude_appointment_id=999999`

| Versão | Agendamento de B | ID inexistente |
|---|---|---|
| **Agora** | 404 `{"detail": "Agendamento a excluir não encontrado."}` | Igual |
| **Antes** | 404 "não pertence à sua barbearia" | 404 "não encontrado" |
