# Evidências da correção estrutural do TEN-01 (14/11/2026)

Correção da causa raiz do TEN-01: os campos relacionais e os filtros que listavam ou aceitavam registros de todas as barbearias. A análise está na seção 22 de [`docs/AUDITORIA_BARBERPRO.md`](../../../AUDITORIA_BARBERPRO.md). A contenção anterior (só `JSONRenderer`) está em [`../ten-01-contencao/`](../ten-01-contencao/README.md) e continua ativa.

## Como foi verificado

- **Alteração:** `diff/diff-somente-ten01-estrutural.patch` traz só esta etapa, sem o `settings.py` da contenção.
- **"Antes" e "depois":** o código anterior é uma cópia do backend no estado HEAD + contenção, montada fora do projeto. Os mesmos testes, sondagens e roteiros rodaram nas duas versões. Para os testes poderem ser importados, a cópia recebeu também o `config/tenancy.py`, que nenhuma view nem serializer dela usa.
- **Bancos:** SQLite em memória e um **PostgreSQL 18.3 descartável**, criado com `initdb` no diretório temporário da sessão e acessível só por TCP em `127.0.0.1:55432`. Ele foi apagado ao final. **O banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Nenhuma migração foi criada nem aplicada.**
- **API:** seis instâncias do `runserver` sobre o banco descartável, com o seed fictício da auditoria (`scripts/ten01e_servidores.sh`):

  | Porta | Código | Configuração |
  |---|---|---|
  | 8767 | corrigido | `DEBUG=True` (o do `.env`) |
  | 8768 | corrigido | `DEBUG=False`, também na importação das settings |
  | 8769 | anterior | `DEBUG=True` |
  | 8770 | anterior | `DEBUG=False`, também na importação |
  | 8771 | corrigido | **laboratório** (ver abaixo) |
  | 8772 | anterior | **laboratório** (ver abaixo) |

- **Laboratório (8771 e 8772).** Estas duas instâncias rodaram com `scripts/iso_html_settings.py`, um módulo de settings descartável, fora do projeto, que religa a API navegável **só nelas**. O objetivo é medir o que os formulários HTML listariam se ela voltasse a ser ativada, que é exatamente o que a correção estrutural precisa impedir.
  - O `config/settings.py` do projeto não foi alterado e continua só com `JSONRenderer`.
- **Navegador:**
  - o build de produção do frontend, servido pelo `vite preview` e apontado para a instância 8767;
  - Firefox 160 headless, dirigido por WebDriver BiDi com o WebSocket nativo do Node 26, sem dependências instaladas.
- **Segredos:** nenhum arquivo desta pasta contém senha, token, `SECRET_KEY` ou string de conexão. Os nomes são fictícios.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `diff/diff-somente-ten01-estrutural.patch` | Alterações desta etapa: `config/tenancy.py`, `appointments/filters.py`, `appointments/views.py`, os dois serializers, o teste novo e os três testes antigos atualizados |
| `testes/antes-e-depois-por-teste.txt` | Os 22 testes novos, no código anterior e no corrigido |
| `testes/testes-novos-codigo-anterior-sqlite.txt.gz` | Execução dos testes novos no código anterior (log completo, comprimido) |
| `testes/testes-novos-codigo-corrigido-sqlite.txt` | Execução dos testes novos no código corrigido |
| `testes/suite-completa-sqlite.txt` | Suíte completa, SQLite |
| `testes/suite-completa-postgresql18.txt` | Suíte completa, PostgreSQL 18.3 descartável |
| `testes/suite-completa-postgresql18-debug-false.txt` | Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings |
| `testes/testes-isolamento-postgresql18-debug-mode.txt` | Os 66 testes de isolamento, inclusive os da contenção, com o executor em `--debug-mode` |
| `testes/django-check-makemigrations.txt` | `check`, `makemigrations --check --dry-run` e `check --deploy` |
| `testes/frontend-testes-tipos-lint-build.txt` | `npm test`, `tsc` (app e node), ESLint e build |
| `api/referencias-resumo-antes-depois.txt` | Sondagem de referências entre barbearias. São 288 pedidos por instância, cada um comparado com um ID inexistente: oráculos, referências aceitas, nomes alheios, erros 500 e md5 de todas as linhas |
| `api/referencias-*.json.gz` | Saída bruta dessa sondagem, nas quatro instâncias |
| `api/ten01-matriz-resumo-estrutural.txt` | Matriz HTML/JSON da contenção (1.926 pedidos por instância) nas seis instâncias, inclusive o laboratório |
| `api/matriz-html-json-*.json.gz` | Saída bruta da matriz |
| `api/isolamento-217-verificacoes-pos-estrutural.json` / `.txt` | As 217 verificações da auditoria no código corrigido |
| `api/isolamento-comparacao-contencao-x-estrutural.txt` | Comparação, verificação por verificação, com a execução feita após a contenção |
| `api/logs-runserver-6-instancias.tar.gz` | Logs de acesso das seis instâncias |
| `navegador/navegador-estrutural.json` | Login e 16 páginas dos três perfis; agendamento, remarcação e confirmação pela interface |
| `scripts/` | Sondagens (`ten01e_probe.py`, `ten01_probe.py` com as portas do laboratório), comparação, quadro dos testes, roteiro do navegador, subida das instâncias e settings descartáveis |

O `iso_probe.py` das 217 verificações é o da auditoria, sem alteração: [`../../evidencias-2026-11-13/isolamento-multitenant/scripts/`](../../evidencias-2026-11-13/isolamento-multitenant/scripts/).

## Como reproduzir

1. Crie um PostgreSQL 18 descartável em `127.0.0.1:55432` com o usuário `smoke` e `trust` local. No `postgresql.conf`, use `listen_addresses='127.0.0.1'`, `port=55432` e `unix_socket_directories=''`.
2. Testes:
   - `venv/bin/python manage.py test config.test_isolamento_tenant --settings=config.test_settings`;
   - para o PostgreSQL, `scripts/ten01_pg_test_settings.py` pelo `PYTHONPATH`.
3. Sondagens:
   - ajuste os caminhos absolutos em `scripts/ten01e_servidores.sh` e `scripts/iso_settings.py` e rode o script;
   - depois, `venv/bin/python -I scripts/ten01e_probe.py <estado_seed.json> http://127.0.0.1:8767 <rótulo> <saída.json>`.

Reprodução manual, com o admin da barbearia A:

1. `POST /api/v1/appointments/` com o `barbeiro` de B e, depois, com `barbeiro: 999999`.
   - **Agora:** as duas respostas são 400 `{"barbeiro": ["Pk inválido … - objeto não existe."]}`.
   - **Antes:** "Este barbeiro não pertence à sua barbearia." para o de B.
2. `GET /api/v1/appointments/?barbeiro=<barbeiro de B>` e `?barbeiro=999999`.
   - **Agora:** as duas respostas são 400 "Faça uma escolha válida".
   - **Antes:** 200 com lista vazia para o de B.
3. `POST /api/v1/barbers/` com o `user` do admin de B.
   - **Agora:** 400 "objeto não existe", igual ao de um ID inexistente.
   - **Antes:** "Usuários administradores não podem ser convertidos em barbeiros.", o que revelava o papel do usuário na outra barbearia.
