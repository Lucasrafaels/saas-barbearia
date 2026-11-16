# Evidências da contenção do TEN-01 (14/11/2026)

Contenção emergencial do TEN-01 (P0): a API navegável do DRF expunha, em HTML, clientes, barbeiros, administradores e serviços de todas as barbearias. A análise está na seção 21 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). O diagnóstico original está na seção 20 e em [`../../evidencias-2026-11-13/isolamento-multitenant/`](../../evidencias-2026-11-13/isolamento-multitenant/README.md).

## Como foi verificado

- **Alteração:** só `REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer']` em `config/settings.py`, mais o teste novo `config/test_renderers.py` (`diff/diff-somente-ten01.patch`).
- **"Antes" e "depois":** o código anterior é uma cópia do backend montada fora do projeto, idêntica ao projeto exceto pelo `settings.py`, que é o do HEAD (sem `DEFAULT_RENDERER_CLASSES`). Os mesmos testes, sondagens e roteiros rodaram nas duas versões.
- **Bancos:** SQLite em memória (`config.test_settings`) e um **PostgreSQL 18.3 descartável**, criado com `initdb` no diretório temporário da sessão e acessível só por TCP em `127.0.0.1:55432`. **O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados.** O `config/test_postgres_settings.py`, que aponta para o Docker, também não foi usado.
- **API:** quatro instâncias do `runserver` sobre o banco descartável com o seed fictício da auditoria (`scripts/ten01_servidores.sh`):
  - 8767: código corrigido, `DEBUG=True` (o do `.env`);
  - 8768: código corrigido, `DEBUG=False` também na importação das settings;
  - 8769: código anterior, `DEBUG=True`;
  - 8770: código anterior, `DEBUG=False`.
- **Navegador:** build de produção do frontend (`vite build`, com `VITE_API_URL` apontando para a instância 8767) servido pelo `vite preview` e aberto no Firefox 160 headless, dirigido por WebDriver BiDi com o WebSocket nativo do Node 26. Nenhuma dependência foi instalada.
- **Segredos:** nenhum arquivo desta pasta contém senha, token, `SECRET_KEY` ou string de conexão. As senhas do seed fictício ficaram só no diretório temporário. A cópia anterior recebeu uma `SECRET_KEY` aleatória pelo ambiente, nunca gravada. Os nomes que aparecem são todos fictícios.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-ten01.patch` | Somente as alterações desta contenção: `config/settings.py` e `config/test_renderers.py` |
| `testes/antes-e-depois-por-teste.txt` | Os 10 testes novos, no código anterior e no corrigido, com os motivos das falhas |
| `testes/testes-novos-codigo-anterior-sqlite.txt.gz` | Execução dos testes novos no código anterior (log completo, comprimido) |
| `testes/testes-novos-codigo-corrigido-sqlite.txt` | Execução dos testes novos no código corrigido |
| `testes/suite-completa-sqlite.txt` | Suíte completa do backend, SQLite |
| `testes/suite-completa-postgresql18.txt` | Suíte completa do backend, PostgreSQL 18.3 descartável |
| `testes/suite-completa-postgresql18-debug-false.txt` | Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings |
| `testes/testes-ten01-postgresql18-debug-mode.txt` | Testes do TEN-01 com o executor em `--debug-mode` (`DEBUG=True` em tempo de execução) |
| `testes/django-check-makemigrations.txt` | `check`, `makemigrations --check --dry-run` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test`, `tsc` (app e node), ESLint e build de produção |
| `api/sondagem-ten01-resumo-antes-depois.txt` | Resumo da sondagem HTTP do TEN-01 nas quatro instâncias, com a comparação dos status JSON antes e depois |
| `api/sondagem-ten01-*.json.gz` | Saída bruta da sondagem (1.926 pedidos por instância: status, content-type, HTML, `<option>` de outros tenants e nomes alheios) |
| `api/isolamento-217-verificacoes-pos-ten01.json` / `.txt` | As 217 verificações da auditoria de isolamento, repetidas no código corrigido |
| `api/isolamento-comparacao-com-a-auditoria.txt` | Comparação, verificação por verificação, com a execução da auditoria de 13/11 |
| `api/logs-runserver-4-instancias.tar.gz` | Logs de acesso das quatro instâncias (método, caminho, status) |
| `navegador/navegador-ten01.json` | Login e 16 páginas nos perfis cliente, barbeiro e admin: pedidos à API, status, content-type, textos esperados e erros |
| `scripts/` | Sondagem (`ten01_probe.py`), comparações (`comparar_ten01.py`, `comparar_iso.py`, `resumir_testes.py`), roteiro do navegador (`ten01_navegador.mjs`), subida das instâncias (`ten01_servidores.sh`) e settings do banco descartável |

Os logs de execução usam a extensão `.txt` porque o `.gitignore` da raiz ignora `*.log`. Com `.log`, eles ficariam fora de um commit, como aconteceu com os `.log` das rodadas de 13/11.

A sondagem de 217 verificações é o `iso_probe.py` da auditoria, sem alteração, em [`../../evidencias-2026-11-13/isolamento-multitenant/scripts/`](../../evidencias-2026-11-13/isolamento-multitenant/scripts/).

## Como reproduzir

1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432`, com o usuário `smoke` e autenticação `trust` só local: `initdb -U smoke --auth=trust`; no `postgresql.conf`, `listen_addresses='127.0.0.1'`, `port=55432` e `unix_socket_directories=''`.
2. Testes: `venv/bin/python manage.py test config.test_renderers --settings=config.test_settings`. Para o PostgreSQL, use `scripts/ten01_pg_test_settings.py` pelo `PYTHONPATH`.
3. Sondagem: ajuste os caminhos absolutos de `scripts/ten01_servidores.sh` e de `scripts/iso_settings.py`, rode o script e depois `venv/bin/python -I scripts/ten01_probe.py <estado_seed.json> http://127.0.0.1:8767 <rótulo> <saída.json>`.

Reprodução manual, sem script, com uma conta do cadastro público:

1. `POST /api/v1/auth/register/` e `POST /api/v1/auth/login/`.
2. `GET /api/v1/appointments/` com `Authorization: Bearer <token>` e `Accept: text/html`: agora **406**, corpo JSON `{"detail": …}`. Antes: 200, página HTML com os `<select>` de todas as barbearias.
3. `GET /api/v1/appointments/?format=api` ou `GET /api/v1/appointments.api`: agora **404**, corpo JSON `{"detail": …}`.
4. O mesmo `GET` com `Accept: application/json` continua respondendo 200 em JSON, só com dados da própria barbearia.
