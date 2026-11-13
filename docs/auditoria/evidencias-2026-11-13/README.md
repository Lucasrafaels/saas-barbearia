# Evidências da auditoria de 13/11/2026 — BarberPro

Material de apoio ao relatório oficial [`docs/AUDITORIA_BARBERPRO.md`](../../AUDITORIA_BARBERPRO.md).
As evidências da auditoria anterior (11/11/2026) continuam em [`../evidencias/`](../evidencias/README.md), sem alteração.

## Origem dos dados

- **Testes de escrita** (sondagens da API, concorrência, rate limit, migração reversa, navegador) rodaram contra uma **cópia isolada**: o mesmo código e as mesmas configurações do projeto, ligados a um PostgreSQL 16.15 descartável num container próprio (`barberpro_auditoria_pg16`, dados em `tmpfs`, porta 55433), já removido.
- O banco descartável foi populado por `scripts/seed.py` com **dados fictícios**: 2 barbearias, 14 usuários, 419 agendamentos (30 dias de histórico e 8 dias à frente). Nomes, e-mails (`@exemplo.test`) e telefones são inventados.
- As senhas dos usuários fictícios foram geradas aleatoriamente e ficaram fora do repositório. Nenhum arquivo desta pasta contém senha, token JWT ou `SECRET_KEY`.
- O **banco real de desenvolvimento** foi acessado apenas em **sessão somente leitura** (`BEGIN READ ONLY`), para contagens de integridade (`banco/integridade-banco-real-somente-leitura.txt`).
- Caminhos locais foram substituídos por `<scratch>` e `~`.

## Arquivos

| Pasta / arquivo | Conteúdo |
|---|---|
| `testes/suite-sqlite.log` | 327 testes do backend em SQLite (`config.test_settings`): OK, 9 pulados (exigem PostgreSQL) |
| `testes/suite-postgresql16.log` | 327 testes do backend em PostgreSQL 16 descartável: OK, 0 pulados |
| `testes/cobertura-backend.txt` | Cobertura de linhas e ramificações do backend (91%) |
| `testes/django-checks-migracoes-e-deploy.txt` | `makemigrations --check` e `check --deploy` |
| `testes/frontend-tipos-lint-build.log` | `tsc` (app e node), ESLint e build de produção do Vite |
| `dependencias/backend-pip-audit.txt` | 91 vulnerabilidades conhecidas em 5 pacotes Python |
| `dependencias/frontend-npm-audit-outdated.txt` | 14 vulnerabilidades (7 altas, 7 moderadas) e pacotes desatualizados |
| `api/sondagem-api.json` | 91 verificações: isolamento, perfis, regras de negócio, barbearia desativada, sessão, concorrência |
| `api/sondagem-api-complementar.json` | 13 verificações: BUS-12, BUS-09, upload de logo, validações, contrato |
| `api/rate-limit-gunicorn-3-workers.txt` | Throttling real de login com 3 workers (SEC-05) |
| `api/sec07-duracao-zero.txt` | Serviço com duração 0: `available-slots` não responde em 10 s (SEC-07) |
| `api/consultas-sql-por-endpoint.txt` | Consultas SQL por endpoint (sem N+1) |
| `api/fe11-duas-fontes-de-faturamento.txt` | Painel x `revenue-report`: R$ 570 de diferença (FE-11) |
| `banco/data01-reverso-migracao-0008.txt` | Desfazer e refazer a migração 0008 apaga e altera preços históricos (DATA-01) |
| `banco/integridade-banco-real-somente-leitura.txt` | Contagens de integridade do banco real (somente leitura) |
| `repositorio/repositorio.txt` | Arquivos versionados, branches, histórico, raiz |
| `navegador/navegador-resultados.json` | 105 combinações de rota × tamanho de tela (5 tamanhos), 3 fluxos, teclado |
| `navegador/navegador-testes-dirigidos.json` | Build de produção: requisições por tela, falha de recarga, API fora do ar, barbearia desativada |
| `navegador/acessibilidade-axe.json` | axe-core 4.10.3 (WCAG 2.0/2.1/2.2 A e AA) em 36 páginas |
| `navegador/navegador-novo-agendamento-apos-confirmacao.json` | Regressão FE-13 |
| `navegador/capturas/` | 36 capturas (desktop 1440 px, tablet 820 px, celular 390 px) |
| `scripts/` | Scripts usados, para reproduzir as verificações (precisam de um banco descartável) |

## Capturas mais relevantes

| Arquivo | O que mostra | Problema |
|---|---|---|
| `fluxo_cliente_domingo_com_horarios.png` | Domingo com 16 horários livres no agendamento do cliente | BUS-06 |
| `fluxo_cliente_agendamento_concluido.png` | Reserva concluída num domingo (22/11) | BUS-06 |
| `fe_reagendar_novamente_mantem_confirmacao.png` | Após reservar, a aba "Agendar" continua mostrando "Horário reservado" | FE-13 |
| `fe03_recarga_falhou_sem_aviso.png` | "Atualizar" com a API derrubada: nenhuma mensagem | FE-03 |
| `barbearia_desativada_painel_admin.png` | Barbearia desativada: lateral diz "Aberta até 19:00"; só o toast avisa | BUS-02, FE-14 |
| `barbearia_desativada_cliente_agendando.png` | Cliente recebe a mensagem de barbearia desativada ao escolher horários | BUS-02 |
| `admin_desktop_recarga_com_api_pausada.png` | API travada: "Atualizar" fica carregando sem limite de tempo | FE-15 |
| `admin_celular_admin_appointments.png` | Filtro de status cortado ("Confi…") e busca truncada no celular | FE-20 |
| `admin_desktop_painel_completo.png` | Painel com dados fictícios; indicador "40 a confirmar no total" inclui vencidos | FE-04 |
| `api_fora_do_ar_ao_recarregar.png` | Estado "Sem conexão com o servidor" com a sessão preservada | — (funciona) |

## Como reproduzir

1. Suba um PostgreSQL descartável (por exemplo, `docker run --rm -p 127.0.0.1:55433:5432 -e POSTGRES_USER=audit -e POSTGRES_PASSWORD=<qualquer> -e POSTGRES_DB=audit_db --tmpfs /var/lib/postgresql/data postgres:16-alpine`).
2. Crie um módulo de settings que importe `config.settings` e aponte `DATABASES` para esse banco. **Nunca** use o banco real.
3. `migrate`, `scripts/seed.py <arquivo-de-credenciais>`, `runserver 127.0.0.1:8765`.
4. Rode `scripts/probe.py` e `scripts/probe2.py` (Python + `requests`) e, para a interface, `scripts/audit.mjs`, `targeted.mjs`, `axe.mjs` e `rebook.mjs` (Node + `puppeteer-core` + Firefox), com o frontend servido em `127.0.0.1:5173` e `VITE_API_URL` apontando para a API isolada.
