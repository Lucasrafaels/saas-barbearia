# Evidências da correção do TEN-02 (14/11/2026)

Correção do TEN-02: uma conta sem barbearia sondava a agenda de outras barbearias, porque era recusada só depois da validação, e a validação consultava a agenda do barbeiro. A análise está na seção 23 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md).

## Como foi verificado

- **Alteração:** `diff/diff-somente-ten02.patch` traz só esta etapa, comparada com a árvore anterior. A anterior já tinha a contenção e a correção estrutural do TEN-01.
- **Três versões do código:**

  | Versão | O que é | Para que serve |
  |---|---|---|
  | **auditoria** | HEAD, o código auditado em 13/11 | Referência do defeito original |
  | **anterior** | A árvore antes desta etapa | Comparação direta |
  | **corrigido** | O projeto | O que está sendo validado |

  As duas primeiras são cópias montadas fora do projeto, com `git archive` e `cp`, sem comandos destrutivos.
- **Simulação de "escopo amplo".** Substitui `config.tenancy.barbearia_do_pedido` por "todas as barbearias", como faria uma mudança futura que liberasse os campos relacionais para quem não tem barbearia, por exemplo um catálogo público ligado ao PROD-01. Ela mostra se a proteção depende só desse escopo. Roda só em memória, nos testes e no rastreamento.
- **Bancos:** SQLite em memória e um **PostgreSQL 18.3 descartável**, criado com `initdb` no diretório temporário da sessão e acessível só por TCP em `127.0.0.1:55432`. Ele foi apagado ao final. **O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Nenhuma migração foi criada nem aplicada.**
- **SQL do servidor real.** O banco descartável da sondagem rodou com `log_statement = 'all'`. Antes e depois de cada pedido, a sondagem grava um marcador no log, e depois lê os comandos que o servidor executou entre os dois. O log bruto não foi copiado, porque contém hashes de senha e tokens das contas descartáveis. Nos JSONs, os hashes de senha dos `INSERT` foram substituídos por `<hash de senha removido>`.
- **API:** cinco instâncias do `runserver` sobre o banco descartável, com o seed fictício da auditoria (`scripts/ten02_servidores.sh`):

  | Porta | Código | `DEBUG` |
  |---|---|---|
  | 8773 | auditoria | `True` |
  | 8769 | anterior | `True` |
  | 8770 | anterior | `False`, também na importação |
  | 8767 | corrigido | `True` |
  | 8768 | corrigido | `False`, também na importação |

- **Segredos:** nenhum arquivo desta pasta contém senha, hash de senha, token, `SECRET_KEY` ou string de conexão.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-ten02.patch` | `config/permissions.py`, `appointments/views.py`, `appointments/serializers.py`, o teste novo e o ajuste em `config/test_isolamento_tenant.py` |
| `testes/antes-e-depois-por-teste.txt` | Os 9 testes do TEN-02, no código anterior e no corrigido |
| `testes/testes-novos-codigo-anterior.txt`, `testes-novos-codigo-corrigido.txt` | As duas execuções completas |
| `testes/suite-completa-sqlite.txt`, `suite-completa-postgresql18.txt`, `suite-completa-postgresql18-debug-false.txt` | Suíte completa: SQLite, PG 18.3 e PG com `DEBUG=False` na importação |
| `testes/testes-isolamento-postgresql18-debug-mode.txt` | Os 75 testes de isolamento, inclusive os do TEN-02, com o executor em `--debug-mode` (`DEBUG=True`) |
| `testes/django-check-makemigrations.txt` | `check`, `makemigrations --check --dry-run` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test`, `tsc` (app e node), ESLint e build |
| `sql/rastreamento-sql-*.txt` | Consultas SQL de um `POST /appointments/` da conta sem barbearia (ocupado, livre, barbeiro válido de B, IDs inexistentes), nas três versões e com o escopo amplo simulado |
| `api/ten02-resumo-http-sql.txt` | Resumo da sondagem HTTP com o SQL do servidor, nas cinco instâncias |
| `api/sondagem-http-sql-*.json.gz` | Saída bruta da sondagem, sem os hashes de senha |
| `api/isolamento-217-verificacoes-pos-ten02.json` / `.txt` e `api/isolamento-comparacao-estrutural-x-ten02.txt` | As 217 verificações da auditoria no código corrigido e a comparação com a etapa anterior |
| `api/logs-runserver-5-instancias.tar.gz` | Logs de acesso das cinco instâncias |
| `navegador/navegador-ten02.json` | Firefox headless no build de produção: login e 16 páginas; agendamento, remarcação e confirmação pela interface |
| `scripts/` | `rastrear_sql.py`, `ten02_probe.py`, `ten02_resumo.py`, `ten02_servidores.sh`, o roteiro do navegador e as settings descartáveis |

## Como reproduzir

1. **Testes:** `venv/bin/python manage.py test appointments.test_ten02 --settings=config.test_settings`.
2. **Rastreamento SQL:** de dentro do diretório do código a examinar, rode `DEBUG=True python scripts/rastrear_sql.py <rótulo> [--escopo-amplo]`. Ele usa SQLite em memória.
3. **Sondagem HTTP com SQL:**
   1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`, com o usuário `smoke` e `trust` local.
   2. Ajuste os caminhos absolutos em `scripts/ten02_servidores.sh` e rode o script.
   3. Rode `venv/bin/python -I scripts/ten02_probe.py <estado_seed.json> http://127.0.0.1:8767 <rótulo> <log do PostgreSQL> <saída.json>`.
   4. Com `logging_collector = on`, o padrão desta distribuição, o log fica em `pgdata/log/`.
