# Auditoria técnica e funcional — BarberPro

| | |
|---|---|
| **Data** | 13/11/2026 |
| **Branch auditada** | `desenvolvimento`, commit `3e0949e` + 43 arquivos modificados e 16 entradas não versionadas (backend do dono e redesign "Esmalte & Navalha") |
| **Escopo** | Backend Django/DRF, frontend React/TypeScript/Vite, banco de dados, segurança, regras de negócio, integração ponta a ponta, três perfis, responsividade, acessibilidade, testes, dependências, documentação e repositório |
| **Natureza** | Somente diagnóstico. Nenhum código, configuração, dependência, migração ou dado real foi alterado |
| **Evidências** | [`docs/auditoria/evidencias-2026-11-13/`](auditoria/evidencias-2026-11-13/README.md) |
| **Correções** | Rodada 1 em 13/11/2026: BUS-15, BUS-03, BUS-05, BUS-04 e FE-13 resolvidos e verificados; BUS-06 parcialmente resolvido. Acompanhamento na [seção 18](#18-acompanhamento-das-correções). Rodada 2 em 13/11/2026 (somente frontend): FE-14, FE-21 e FE-22 resolvidos e verificados, na [seção 19](#19-rodada-2--13112026-fe-14-fe-21-e-fe-22-somente-frontend). As seções 1 a 17 descrevem o estado no momento da auditoria e foram preservadas |
| **Auditoria anterior** | Cópia integral em [`docs/auditorias/historico/AUDITORIA_BARBERPRO_2026-11-11.md`](auditorias/historico/AUDITORIA_BARBERPRO_2026-11-11.md); evidências antigas preservadas em [`docs/auditoria/evidencias/`](auditoria/evidencias/README.md) |

> **Confidencialidade.** Este relatório não contém a `SECRET_KEY`, senhas, tokens nem a string de conexão do banco: só comprimentos, contagens, códigos HTTP e nomes de campos. Todos os dados de teste citados são fictícios.

---

## Sumário

1. [Resumo executivo](#1-resumo-executivo)
2. [Estado geral do projeto](#2-estado-geral-do-projeto)
3. [Escopo e metodologia](#3-escopo-e-metodologia)
4. [Ambiente e ferramentas](#4-ambiente-e-ferramentas)
5. [Auditoria de segurança](#5-auditoria-de-segurança)
6. [Auditoria do backend](#6-auditoria-do-backend)
7. [Auditoria do frontend](#7-auditoria-do-frontend)
8. [Auditoria do banco de dados](#8-auditoria-do-banco-de-dados)
9. [Integração ponta a ponta](#9-integração-ponta-a-ponta)
10. [Testes dos três perfis](#10-testes-dos-três-perfis)
11. [Responsividade e acessibilidade](#11-responsividade-e-acessibilidade)
12. [Comparação com a auditoria anterior](#12-comparação-com-a-auditoria-anterior)
13. [Lista completa de problemas](#13-lista-completa-de-problemas)
14. [Problemas não verificáveis e limitações](#14-problemas-não-verificáveis-e-limitações)
15. [Matriz de prioridades](#15-matriz-de-prioridades)
16. [Plano recomendado de correção](#16-plano-recomendado-de-correção)
17. [Prontidão para a demonstração](#17-prontidão-para-a-demonstração)
18. [Acompanhamento das correções](#18-acompanhamento-das-correções)
19. [Rodada 2: FE-14, FE-21 e FE-22](#19-rodada-2--13112026-fe-14-fe-21-e-fe-22-somente-frontend)

---

## 1. Resumo executivo

O BarberPro melhorou desde 11/11. **Os dois problemas críticos da auditoria anterior foram corrigidos e comprovados**:

- a `SECRET_KEY` efetiva agora tem 86 caracteres, e o `settings.py` recusa chaves curtas (SEC-01);
- o faturamento deixou de vazar para clientes e barbeiros (SEC-02).

Também foram corrigidos e verificados:

- o admin que se rebaixava ou se desativava (BUS-01), inclusive sob concorrência;
- o "realizado" em horário futuro (BUS-07);
- a fonte vinda do Google Fonts (FE-08).

A base continua sólida:

- **isolamento entre barbearias:** 21 de 21 tentativas de acesso cruzado foram bloqueadas;
- **concorrência:** 20 pedidos simultâneos para o mesmo horário geraram exatamente 1 agendamento (PostgreSQL 16);
- **testes:** 327 testes passam em SQLite e em PostgreSQL, com 91% de cobertura de linhas e ramificações;
- **frontend:** sem erros de tipo, lint ou build;
- **navegador:** nenhuma das 105 combinações de tela × tamanho tem erro de console ou rolagem horizontal;
- **acessibilidade:** nenhuma violação automática (axe-core) em 36 páginas.

**Não há nenhum problema P0 aberto.** O sistema, porém, **não está pronto para produção** e tem pontos que podem aparecer numa demonstração:

- **O fluxo de confirmação da barbearia pode ser contornado pelo cliente.**
  - O cliente cria o agendamento já como "confirmado" (BUS-15, novo).
  - Ao reagendar um horário confirmado, ele continua "confirmado" (BUS-03).
- **O horário de funcionamento não é garantido pela API.**
  - A troca de serviço ultrapassa o fechamento (BUS-04).
  - A API aceita fechamento antes da abertura (BUS-05).
  - Domingos e dias fechados recebem horários. A interface reservou um domingo durante esta auditoria (BUS-06).
- **Lacunas de produto continuam:**
  - o cliente não se cadastra numa barbearia (PROD-01);
  - a recuperação de senha não envia e-mail (AUTH-01).
- **Suspensão de barbearia só parcial.** A agenda congela, mas o próprio admin reativa a barbearia que a plataforma desativou, e a interface não avisa nada (BUS-02, FE-14).
- **Dependências do backend com 91 vulnerabilidades conhecidas.** O Django 5.0 está fora de suporte (DEP-01).
- **Dois bancos de desenvolvimento diferentes.** O app usa o PostgreSQL 18 do host. O banco do `docker-compose` indicado no README está com duas migrações pendentes e falharia nos agendamentos (DB-01).
- **Uma regressão do redesign.** Depois de reservar, o botão "Agendar" continua mostrando "Horário reservado" (FE-13).

### Números

| Prioridade | Quantidade |
|---|---|
| P0 — Crítico | **0** |
| P1 — Alto | **7** |
| P2 — Médio | **28** |
| P3 — Baixo | **35** |
| **Total de problemas abertos** | **70** |

| Situação dos 53 problemas da auditoria anterior | Quantidade | IDs |
|---|---|---|
| Resolvido e verificado | 5 | SEC-01, SEC-02, BUS-01, BUS-07, FE-08 |
| Parcialmente resolvido | 3 | BUS-02, TEST-01, FE-04 |
| Continua presente | 45 | ver seção 12 |
| Regressão (voltou a ocorrer) | 0 | — |
| Não reproduzido / obsoleto / não verificável | 0 | — |

| Problemas novos | Quantidade |
|---|---|
| Encontrados nesta auditoria | 22 (1 P1, 5 P2, 16 P3) |
| Dos quais regressão introduzida pelo redesign | 1 (FE-13) |

### Os cinco problemas mais importantes

| # | ID | Prioridade | Por que |
|---|---|---|---|
| 1 | BUS-15 | P1 | O cliente se autoconfirma ao criar o horário: a confirmação da barbearia perde o sentido. Correção de poucas linhas |
| 2 | BUS-03 | P1 | Reagendar mantém "confirmado": a barbearia passa a ter um horário confirmado que nunca aprovou |
| 3 | BUS-06 | P1 | Domingos e dias fechados recebem agendamentos, inclusive pela interface. É o mais visível numa demonstração |
| 4 | BUS-05 | P1 | A API aceita fechamento antes da abertura, e a barbearia "desaparece" da agenda |
| 5 | BUS-04 | P1 | A troca de serviço gera atendimento depois do fechamento |

Para a operação real também pesam PROD-01, AUTH-01, DEP-01 e DB-01.

**Veredito.** O BarberPro **pode ser apresentado** como protótipo acadêmico. Os fluxos dos três perfis funcionam de ponta a ponta, sem erros na interface, em todos os tamanhos de tela testados. É preciso garantir o banco usado e os dados de demonstração e evitar os fluxos listados na seção 17. **Não está pronto para uso real nem para produção.**

---

## 2. Estado geral do projeto

| Área | Situação | Resumo |
|---|---|---|
| Autenticação e sessão | ✅ Funciona | Login, refresh por cookie HttpOnly com rotação e blacklist, logout, troca de senha, bloqueio imediato de conta desativada. Pendentes: SEC-04, SEC-05, AUTH-01 e AUTH-02 |
| Isolamento multi-tenant | ✅ Funciona | 21/21 tentativas de acesso cruzado bloqueadas; há só um oráculo de existência de IDs (SEC-10) |
| Permissões por perfil | ⚠️ Quase | Faturamento protegido (SEC-02 resolvido). O cliente cria horário já confirmado (BUS-15) e o barbeiro troca o cliente de um horário (BUS-12) |
| Regras de agenda | ❌ Incompletas | Conflito por barbeiro garantido, inclusive sob concorrência. Abertos: horário de funcionamento (BUS-04, BUS-05), dias fechados (BUS-06), confirmação (BUS-03, BUS-15), vencidos (BUS-08), duração histórica (BUS-09) e sobreposição do próprio cliente (BUS-17) |
| Barbearia desativada | ⚠️ Parcial | A agenda congela, mas o admin reativa a barbearia por conta própria e a interface não sinaliza (BUS-02, FE-14) |
| Financeiro | ⚠️ Quase | Usa o preço histórico. O dia é agrupado em UTC (API-02), o painel e a API usam janelas diferentes (FE-11), e o reverso de uma migração apaga preços (DATA-01) |
| Banco de dados | ⚠️ | Migrações coerentes no banco que o app usa; sem constraints de negócio (DB-02); dois bancos de desenvolvimento divergentes (DB-01) |
| Frontend (funcionamento) | ✅ Funciona | `tsc`, ESLint e build sem erros; 0 erros de console em 105 cargas; fluxos concluídos nos três perfis. Pendentes: FE-03, FE-13, FE-15 e a carga integral de listas (API-01) |
| Redesign e identidade | ✅ Consistente | Paleta, League Gothic e Public Sans locais, logo e componentes coerentes entre as telas. Pequenos desvios: 45 estilos inline e cores literais (MAINT-01) |
| Responsividade | ✅ Funciona | 0 rolagem horizontal em 5 larguras (1440, 1280, 820, 390 e 360 px) e fluxos completos no celular e no tablet. Detalhes em FE-19 e FE-20 |
| Acessibilidade | ✅ Bom | 0 violações automáticas WCAG A/AA em 36 páginas, link "Pular para o conteúdo", foco visível. Leitor de tela não testado (NV-3) |
| Testes | ⚠️ | 327 testes no backend, 91% de cobertura, mas as regras quebradas não têm teste (TEST-01). Nenhum teste de frontend (FE-02) |
| Dependências | ❌ | Backend com 91 vulnerabilidades conhecidas e Django fora de suporte (DEP-01); frontend com 14 (DEP-02) |
| Infra e operação | ❌ Ausente | Sem Dockerfile, CI, logs, monitoramento, cache compartilhado e e-mail (OPS-01, OBS-01, SEC-05, AUTH-01) |
| Documentação | ❌ Desatualizada | Documentação da API, README e índice de `docs/` divergem do comportamento (DOC-01 a DOC-04) |

### Funcionalidades e estado real

| Módulo | Funcionalidade | Estado | Evidência / problema |
|---|---|---|---|
| Autenticação | Login, renovação, logout, troca de senha | ✅ | SES-01 a SES-06 (`api/sondagem-api.json`) |
| Autenticação | Recuperação de senha | ⚠️ Incompleta | Sem envio de e-mail (AUTH-01); confirmação sem teste (TEST-01) |
| Autenticação | Cadastro público | ⚠️ Incompleto | Só serve a donos de barbearia (PROD-01); e-mail duplicado por maiúsculas (AUTH-02) |
| Usuários | Gestão pelo admin | ✅ | BUS-01 resolvido. Sem segundo admin nem transferência de titularidade (BUS-19) |
| Barbearias | Edição dos dados | ⚠️ | Fechamento antes da abertura aceito pela API (BUS-05); telefone sem validação (BUS-18) |
| Barbearias | Desativação/suspensão | ⚠️ Parcial | BUS-02, FE-14 |
| Barbearias | Logo | ❌ Só API | Sem tela (FE-09); upload sem limite (SEC-09) |
| Barbeiros | Cadastro, edição, desativação, reativação | ✅ | Fluxos no navegador; desativação não trata a agenda (BUS-13) |
| Clientes | Cadastro e gestão pelo admin | ✅ | Tela "Clientes"; lista carrega todos os agendamentos (API-01) |
| Serviços | Cadastro, preço, duração, ativo | ✅ | Validações fracas (BUS-18); "1.000" vira R$ 1,00 (FE-16) |
| Agendamentos | Criação sem conflito | ✅ | CON-01: 1 de 20 pedidos simultâneos |
| Agendamentos | Horários livres | ⚠️ | Dias fechados (BUS-06), passo (BUS-11), datas passadas (BUS-10) |
| Agendamentos | Confirmação | ❌ Contornável | BUS-15, BUS-03 |
| Agendamentos | Conclusão ("realizado") | ✅ | BUS-07 resolvido; botão "Concluir às HH:MM" desabilitado antes do término |
| Agendamentos | Cancelamento | ⚠️ | Funciona; o cliente cancela até horário já passado (BUS-16); regra do barbeiro incoerente (BUS-12) |
| Painel / Caixa | Indicadores, quadro do dia, faturamento | ✅ Dados reais | Calculados no navegador a partir de todas as páginas (API-01, FE-11) |
| Relatórios | `revenue-report` | ✅ Protegido | Só admin (SEC-02 resolvido); dia em UTC (API-02); não é usado pela interface |
| Página institucional | `/conheca` | ✅ | Nova; sem rolagem horizontal; promessas coerentes com o sistema |
| Super Admin | Painel global | ❌ Ausente | SA-01 |

---

## 3. Escopo e metodologia

### 3.1 Regras seguidas

- Trabalho na branch `desenvolvimento`. Nenhum commit, push, merge, `reset`, `checkout` ou limpeza.
- **Nenhum arquivo de código, configuração, dependência, migração ou `.env` foi alterado.** Ao final, `git diff --stat` continuava idêntico ao do início: 43 arquivos, +2065/−830. Só foram criados:
  - este relatório;
  - a cópia histórica, idêntica byte a byte ao original (mesmo SHA-256);
  - a pasta de evidências nova.
- **O banco real não sofreu nenhuma escrita.**
  - Nele rodaram só consultas numa sessão `BEGIN READ ONLY` e `showmigrations`, que apenas lê a tabela de migrações.
  - Nenhuma migração foi executada nele.
- Todos os testes com escrita usaram um **PostgreSQL 16.15 descartável**:
  - num container próprio, com dados em `tmpfs`, removido ao final;
  - populado com dados fictícios: 2 barbearias, 14 usuários, 419 agendamentos.
- A migração reversa (DATA-01) rodou numa segunda cópia descartável desse banco.
- Ferramentas auxiliares foram instaladas **fora do projeto**, no diretório temporário da sessão: `coverage`, `pip-audit`, `puppeteer-core` e `axe-core`. Nada foi instalado no `venv312` nem no `node_modules` do projeto.
- O build de produção do frontend foi gerado fora do projeto, sem sobrescrever `frontend/dist`.
- Nenhum valor de segredo foi exibido ou gravado. O teste de `SECRET_KEY` mediu só o comprimento.

### 3.2 Métodos

| Método | O que cobriu |
|---|---|
| Leitura integral de código | Todos os models, serializers, views, permissões, mixins, settings, URLs, migrações, admin e managers. No frontend: rotas, cliente HTTP, autenticação, hooks, telas e componentes alterados pelo redesign e o diff completo desde `3e0949e` |
| Suíte do backend | 327 testes em SQLite (`config.test_settings`) e em PostgreSQL 16 descartável, com medição de cobertura |
| Sondagem 1 da API isolada | 91 verificações por HTTP real: isolamento (23; 21 conforme), perfis (23; 20 conforme), regras de negócio (23; 4 conforme), barbearia desativada (6; 3 conforme), sessão e segurança HTTP (15; 13 conforme), concorrência (1; conforme). Total: 62 conforme o esperado, 29 divergentes. Duas observações de transparência: PER-23 divergiu da expectativa, mas o comportamento é adequado (recusa com 400), e não virou problema; o primeiro teste de BUS-12 ficou inválido (o agendamento de partida não foi criado) e foi refeito na sondagem 2 |
| Sondagem 2 | 13 verificações: BUS-12 refeito, BUS-09, upload de logo, validações, oráculo de tempo, contrato |
| Testes dirigidos | Laço com duração 0 (com `timeout`), consultas SQL por endpoint, rate limit real com 3 workers do gunicorn, reverso da migração 0008, painel × relatório |
| Navegador real | Firefox 160 headless via `puppeteer-core`, com um contexto isolado por perfil. Foram 105 cargas: 21 rotas em 5 larguras (1440, 1280, 820, 390 e 360 px). Também fluxos de cliente (celular), barbeiro (tablet) e admin (desktop), teclado e rota inexistente. No build de produção: requisições por tela, API derrubada, API travada e barbearia desativada |
| Acessibilidade | axe-core 4.10.3 (WCAG 2.0/2.1/2.2 A e AA) em 36 páginas, com teste de controle que confirmou a detecção de 3 violações plantadas |
| Banco real (somente leitura) | Migrações aplicadas e 26 contagens de integridade |
| Ferramentas estáticas | `tsc`, ESLint, build Vite, `makemigrations --check`, `check --deploy`, `pip-audit`, `npm audit`, `npm outdated` e `git` (arquivos versionados, branches, histórico) |

### 3.3 Classificação

- **Severidade:**
  - **P0:** comprometimento grave de segurança, perda de dados ou quebra do isolamento;
  - **P1:** autorização importante, regra de negócio crítica ou funcionalidade essencial;
  - **P2:** problema funcional relevante, integração, usabilidade que prejudica a operação, dependência vulnerável ou lacuna de infraestrutura;
  - **P3:** visual, pequena inconsistência, acessibilidade, manutenção.
- **Confiança:**
  - **Confirmado:** reproduzido dinamicamente ou inequívoco no código, com a fonte indicada no campo Evidência;
  - **Provável:** forte indício sem reprodução;
  - **Não verificado:** depende de condição que não pôde ser criada.
- **Estado em relação à auditoria anterior:** Novo, Continua presente, Parcialmente resolvido, Reclassificado.

---

## 4. Ambiente e ferramentas

| Item | Versão / detalhe |
|---|---|
| Sistema | Fedora Linux 45, kernel 7.3.3 |
| Python / Django / DRF | 3.12.16 / 5.0.14 / 3.15.2 (djangorestframework-simplejwt 5.3.1, Pillow 10.4.0) |
| Node / npm | 26.13.0 / 11.20.0 |
| Frontend | React 19.2.8, React Router 7.18.2, Vite 6.4.3, TypeScript 5.8.3, axios 1.19.0, zod 3.25.76 |
| Banco que o app usa (`.env`) | PostgreSQL **18.3** no host, porta 5432 (somente leitura nesta auditoria) |
| Banco do `docker-compose.yml` | PostgreSQL 16.15, container `barbershop_db`, porta 5433: **não é o banco que o app usa** (DB-01) |
| Banco descartável da auditoria | PostgreSQL 16.15 (`postgres:16-alpine`), container próprio em `tmpfs` |
| Navegador | Firefox 160.0 headless + puppeteer-core 24.10.0 |
| Acessibilidade | axe-core 4.10.3 |
| Cobertura / dependências | coverage 7.17.3, pip-audit 2.10.1, `npm audit` |
| Servidores de teste | `runserver` (sondagens) e gunicorn com 3 workers (rate limit) |

---

## 5. Auditoria de segurança

### 5.1 Verificações e resultados

| Tema | Resultado | Evidência |
|---|---|---|
| `SECRET_KEY` | ✅ 86 caracteres, 47 distintos; `settings.py` recusa chaves curtas também com `DEBUG=True`; nenhum `InsecureKeyLengthWarning` na suíte | `config/settings.py:40-49`, `config/test_secret_key.py` |
| Faturamento por perfil | ✅ Cliente 403, barbeiro 403 (inclusive filtrando o próprio id), admin 200 | PER-08 a PER-11 |
| Isolamento entre barbearias | ✅ 21/21 bloqueadas: leitura, alteração e exclusão de barbearia, usuários, serviços, barbeiros e agendamentos de outra barbearia; uso de barbeiro, serviço ou cliente alheios; horários livres; `exclude_appointment_id`; listas | ISO-01 a ISO-21 |
| Oráculo de IDs | ⚠️ Mensagens distintas revelam que um ID existe em outra barbearia | ISO-22, ISO-23 → SEC-10 |
| Escalada de privilégio | ✅ Cliente não se promove nem se reativa; barbeiro e cliente não gerenciam usuários, serviços ou barbearia; não é possível criar admin pela API | PER-01 a PER-07, PER-14, PER-15 |
| Regras de autorização de negócio | ❌ Cliente cria horário confirmado (BUS-15); barbeiro troca o cliente de um horário e cancela por PATCH (BUS-12); admin reativa a barbearia suspensa pela plataforma (BUS-02) | NEW-STATUS, BUS-12, BUS-02f |
| Sessão JWT | ✅ Refresh só em cookie HttpOnly, `SameSite=Lax`, caminho restrito; rotação e blacklist funcionam; logout revoga; conta desativada perde acesso imediatamente | SES-01 a SES-06 |
| Armazenamento do access token | ⚠️ `localStorage`, sem CSP; o token traz `nome` e `hash_password` | SES-03, SES-09 → SEC-04 |
| Rate limiting | ❌ Por processo: com 3 workers, 10 de 15 tentativas de login no mesmo minuto foram aceitas | `api/rate-limit-gunicorn-3-workers.txt` → SEC-05 |
| Recuperação de senha | ✅ Mesma resposta e tempo equivalente para e-mail existente e inexistente (mediana de 16 ms e 15 ms em 12 amostras); ❌ não envia e-mail | SES-10, SES-10b → AUTH-01 |
| CORS | ✅ Origem não autorizada não recebe `Access-Control-Allow-Origin`. O `.env` local libera também `localhost:3000`, que não é usado | SES-07, SES-08 → SEC-11 |
| Cabeçalhos | ✅ `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `COOP`; ❌ sem CSP | SES-09 |
| CSRF | ✅ API autenticada por header `Authorization`; o refresh por cookie depende de `SameSite=Lax`, que bloqueia POST de outro site | Leitura de código |
| Entradas malformadas | ✅ 400/404, sem erro 500, em agendamento, horários e relatório | SES-13 a SES-15 |
| SQL injection | ✅ Só ORM; o único `.extra()` usa SQL fixo | `appointments/views.py:351` |
| XSS | ✅ React escapa os dados; os três `dangerouslySetInnerHTML` recebem SVGs estáticos do projeto | `AuthLayout.tsx:22`, `LandingPage.tsx:61,141` |
| Uploads | ❌ Logo de 14,5 MB aceito; Pillow com 69 vulnerabilidades; SVG recusado | UPL-01, UPL-02 → SEC-09, DEP-01 |
| Negação de serviço | ❌ Serviço com duração 0 trava a requisição (gravável pelo Django Admin) | `api/sec07-duracao-zero.txt` → SEC-07 |
| Configuração de produção | ✅ `check --deploy` só com W021 (HSTS preload, opcional); ⚠️ `.env` local com `DEBUG=True` exibe a página técnica de rotas, e há credenciais padrão de desenvolvimento no código | SES-12 → SEC-11 |
| Dependências | ❌ 91 vulnerabilidades no backend e 14 no frontend | DEP-01, DEP-02 |
| Histórico do git | ⚠️ Chave antiga no commit `3f46df2`; o repositório tem remoto no GitHub (visibilidade não verificada) | SEC-06 |
| Logs | ⚠️ Não há configuração de logging, então não há vazamento em logs, mas também não há rastreio (OBS-01). O log do `runserver` registra só método, caminho e status | `config/settings.py` |

### 5.2 Problemas de segurança

BUS-15 (P1); BUS-02, BUS-12, AUTH-02, SEC-03, SEC-04, SEC-05, SEC-07, SEC-09 e DEP-01 (P2); SEC-06, SEC-08, SEC-10, SEC-11 e DEP-02 (P3). **Nenhum P0.**

---

## 6. Auditoria do backend

### 6.1 O que funciona

- **Estrutura:** a regra de tenant está centralizada em `TenantScopedQuerysetMixin` e reforçada nos serializers e em `Appointment.clean()`.
- **Concorrência:**
  - `select_for_update` nos barbeiros ao criar e alterar agendamentos;
  - trava dos admins ativos ao rebaixar ou desativar (BUS-01);
  - os testes de concorrência passam em PostgreSQL 16 (0 pulados).
- **Transações:** `transaction.atomic` nas operações compostas (usuário + perfil de barbeiro, promoção, desativação).
- **Exclusão lógica:** usuários, barbeiros e serviços são desativados, com `deleted_at` e `deleted_by` nos dois últimos. FKs com `PROTECT` preservam o histórico.
- **Eficiência:** 2 consultas por listagem e 4 no relatório e nos horários livres, sem N+1 (`api/consultas-sql-por-endpoint.txt`).
- **Correções novas do dono, verificadas:**
  - SEC-01: `config/settings.py:40-49`;
  - SEC-02: `appointments/views.py:52-57`;
  - BUS-01: `accounts/admin_integrity.py`, `User.save/delete`, `UserQuerySet`, Django Admin;
  - BUS-02 parcial: `Appointment._validar_barbearia_ativa`, `available_slots`;
  - BUS-07: `Appointment._validar_conclusao_apos_termino`.

### 6.2 O que falha

| Tema | Problemas |
|---|---|
| Criação e status de agendamentos | BUS-15, BUS-03, BUS-12, BUS-16 |
| Horário de funcionamento e dias | BUS-04, BUS-05, BUS-06, BUS-10, BUS-11 |
| Integridade de agenda | BUS-09, BUS-13, BUS-17, SEC-07 |
| Usuários e tenant | AUTH-02, PROD-01, BUS-19, BUS-02 |
| Relatórios | API-02, FE-11 |
| API | API-01, SEC-10, FE-17 (contrato) |
| Operação | AUTH-01, OBS-01, OPS-01, SEC-05, DEP-01 |
| Código | MAINT-01: código morto `_validar_campos_cliente_nao_autorizados` e `IsClientRole`; filtro `ativo` duplicado em dois ViewSets; comentários obsoletos (DOC-03) |

### 6.3 Testes do backend

| Execução | Resultado |
|---|---|
| SQLite (`--settings=config.test_settings`) | **327 testes, OK** (9 pulados: exigem PostgreSQL), 3,6 s |
| PostgreSQL 16 descartável | **327 testes, OK, 0 pulados**, 8,9 s |
| Distribuição | accounts 124 · appointments 123 · barbershops 51 · services 19 · config 10 (eram 239 em 11/11) |
| Cobertura (linhas + ramificações) | **91%** no total. Menores: `config/permissions.py` 74%; `accounts/managers.py`, `accounts/serializers.py` e `appointments/models.py` entre 85% e 86%. **A confirmação de recuperação de senha não tem nenhum teste** (`accounts/serializers.py:427-449`) |
| Testes sem asserção | 2, do tipo "não deve lançar erro", aceitáveis (`accounts/test_admin_integrity_paths.py:317,326`) |
| `makemigrations --check` | Sem alterações pendentes |
| `check --deploy` | 1 aviso (W021, HSTS preload) |

---

## 7. Auditoria do frontend

### 7.1 Qualidade de build

| Verificação | Resultado |
|---|---|
| `tsc` (app e `vite.config`) | 0 erros |
| ESLint `--max-warnings=0` | 0 erros, 0 avisos |
| Build de produção | OK. JS inicial 433,7 kB (138,1 kB gzip); CSS 53,6 kB (10,8 kB gzip); fontes locais de 18,7 kB e 26,8 kB; telas carregadas sob demanda |
| Testes automatizados | Inexistentes (FE-02) |

### 7.2 Funcionamento e integração

| Verificação | Resultado |
|---|---|
| Erros de console, erros de página e respostas ≥ 400 | **0** em 105 cargas e nos fluxos |
| Rotas e redirecionamentos por perfil | Corretos: cada perfil vai à própria página inicial; rota de outro perfil devolve à inicial; rota inexistente devolve ao início ou ao login, sem página 404 (FE-06) |
| Fluxo do cliente (celular 390 px) | Agendar (serviço → barbeiro → dia → horário → revisar → confirmar) → "Está marcado". Cancelar → diálogo → toast. **Reservou um domingo** (BUS-06) |
| Fluxo do barbeiro (tablet 820 px) | "A confirmar" → Confirmar → toast; "Concluir às HH:MM" desabilitado antes do término |
| Fluxo do admin (desktop) | Painel → Confirmar em "A seguir" → toast; horário inválido barrado no formulário; falha de recarga sem aviso (FE-03) |
| API fora do ar ao abrir | Tela "Sem conexão com o servidor", sessão preservada |
| API travada | Carregamento sem limite de tempo (FE-15) |
| Barbearia desativada | O admin só descobre ao agir; a lateral diz "Aberta até 19:00" (FE-14) |
| Novo agendamento após reservar | Continua na tela "Horário reservado" (FE-13, regressão) |
| Volume de requisições (build de produção) | Painel do admin, Agendamentos e Clientes: 25 requisições cada, 22 delas para páginas de `/appointments/` com 419 agendamentos. Cresce linearmente com o histórico (API-01). Em modo dev o `StrictMode` dobra o número |
| Contratos | Campo `barbeiro_especialidade` inexistente na API; filtro `tipo_perfil` ignorado; `cliente` obrigatório no POST do próprio cliente (FE-17) |
| Tratamento de erros HTTP | 400 com mensagem por campo; 401 renova a sessão uma vez e só desloga se o servidor recusar; 403 e 404 com mensagem; 429 e ≥ 500 com mensagens próprias (`utils/format.ts:222-243`) |

### 7.3 Redesign e identidade visual

- A identidade aprovada é aplicada de forma consistente em todas as telas auditadas:
  - **paleta "Placa esmaltada":** marinho, vermelho só para "agora", pendências, destrutivo e CTA, marfim e branco;
  - **tipografia:** League Gothic nos títulos e Public Sans na interface, as duas **servidas pelo próprio app**, sem Google Fonts;
  - **marca:** logo "Navalha aberta" e o poste como indicador de "aberta/agora";
  - **componentes:** os mesmos em admin, barbeiro, cliente e páginas públicas.
- Estados de carregamento (skeleton e barra de recarga), vazio (ilustrações), erro (com "Tentar novamente") e sucesso (toast, carimbo de reserva) existem em todas as telas de lista.
- Desvios pequenos (MAINT-01):
  - 45 estilos inline (`style={{…}}`);
  - cores literais em `ui.module.css` (ícones de toast) e `layout.module.css`, fora de `design-tokens.css`;
  - `ui.module.css` com 1.096 linhas;
  - 17 ícones e 3 funções sem uso (FE-07).
- Textos da interface que prometem o que o sistema não faz (FE-18).

---

## 8. Auditoria do banco de dados

| Tema | Resultado |
|---|---|
| Migrações (banco que o app usa) | Todas aplicadas (22 dos apps do projeto) |
| Migrações (banco do `docker-compose`) | **0007 e 0008 de `appointments` pendentes**: a coluna `preco_historico` não existe ali (DB-01) |
| Integridade do banco real (somente leitura) | Sem inconsistências em 26 contagens. Volume mínimo: 2 barbearias, 8 usuários, 2 serviços, **2 agendamentos** (FE-12); 1 conta sem barbearia criada pelo cadastro público (PROD-01) |
| Relacionamentos | FKs com `PROTECT` (histórico preservado); `deleted_by` com `SET_NULL`; `Barber.user` `OneToOne` |
| Constraints | Só PK, FK, `unique(email)` e `OneToOne`. **Nenhuma** constraint para: duração > 0, preço ≥ 0, fechamento > abertura, status válido, e-mail sem diferenciar maiúsculas, não sobreposição por barbeiro (DB-02) |
| Índices | Adequados ao uso: `(barbeiro, data_hora)`, `(barbershop, data_hora)`, `(barbershop, ativo)` em barbeiros e serviços |
| Concorrência | ✅ Comprovada em PostgreSQL 16: 20 pedidos simultâneos → 1 criado e 19 recusados |
| Migração reversa | ❌ Desfazer a 0008 zera os 419 preços históricos; refazer grava o preço atual e o faturamento realizado passa de R$ 15.215 para R$ 16.565 (DATA-01) |
| Fuso nos relatórios | ❌ Atendimento às 22:30 de 12/11 aparece no dia 13/11 do relatório (API-02) |
| Collation | ⚠️ Banco do app criado com glibc 2.43; o sistema tem 2.44 (DATA-03) |
| Consultas ineficientes | Nenhuma no backend; o gargalo é o frontend percorrer todas as páginas (API-01) |
| Crescimento | Tabela de tokens sem rotina de limpeza (`flushexpiredtokens`, OPS-01); hoje 13 tokens, nenhum expirado |

---

## 9. Integração ponta a ponta

Caminho de cada fluxo: Frontend → API → Backend → Banco → Resposta → Atualização da interface.

| Fluxo | Resultado | Camada da falha |
|---|---|---|
| Login e logout | ✅ Cookie definido, `/users/me/`, redirecionamento por perfil; logout revoga o refresh | — |
| Sessão expirada / renovação | ✅ 401 → refresh → repetição da chamada; recusa do servidor → toast e login | — |
| Cadastro público | ⚠️ Cria conta sem barbearia → onboarding de dono | Produto (PROD-01) |
| Onboarding (criar barbearia) | ✅ No frontend, com validação de horário; ⚠️ a API aceita horário inválido | Backend (BUS-05) |
| Recuperação de senha | ⚠️ Tela e API respondem; nenhum e-mail é enviado | Backend/configuração (AUTH-01) |
| Gestão de barbeiros | ✅ Criar, editar, desativar e reativar; ⚠️ a agenda futura do barbeiro desativado continua ativa | Backend (BUS-13) |
| Gestão de clientes | ✅; ⚠️ a tela baixa todos os agendamentos | Frontend/API (API-01) |
| Gestão de serviços | ✅; ⚠️ "1.000" vira R$ 1,00; validações fracas | Frontend (FE-16), Backend (BUS-18) |
| Dados da barbearia | ✅ Edição; ❌ sem logo | Frontend (FE-09) |
| Criar agendamento (cliente) | ✅ Conflito impedido e horários reais; ❌ domingos; ⚠️ "Agendar" de novo não reinicia a tela | Backend (BUS-06), Frontend (FE-13) |
| Criar agendamento (admin) | ❌ Sem tela (a API aceita: 201) | Frontend (BUS-14) |
| Reagendar (cliente) | ✅ Muda horário, barbeiro e serviço; ❌ mantém "confirmado" | Backend (BUS-03) |
| Cancelar (cliente) | ✅ Diálogo + toast; ⚠️ a API aceita cancelar horário que já passou | Backend (BUS-16) |
| Confirmar (admin/barbeiro) | ✅ Em "A seguir", na lista e na agenda | — |
| Concluir ("realizado") | ✅ Só após o término previsto (frontend e backend) | — |
| Agenda do barbeiro | ✅ Por dia e "a confirmar"; ⚠️ a contagem inclui vencidos | Frontend/produto (FE-04, BUS-08) |
| Caixa (painel) | ✅ Números reais pelo preço histórico; ⚠️ diverge do relatório da API em R$ 570 | Integração (FE-11) |
| Relatórios (`revenue-report`) | ✅ Protegido; ⚠️ dia em UTC; não é consumido pela interface | Backend (API-02) |
| Barbearia desativada | ⚠️ A API bloqueia a agenda; a interface não sinaliza; o admin reativa | Backend + Frontend (BUS-02, FE-14) |
| Experiência pública de agendamento | ❌ Não existe página pública por barbearia | Produto (PROD-01) |

---

## 10. Testes dos três perfis

Permissões testadas **pela API**, não só pela interface. Os códigos vêm de `api/sondagem-api.json` e `api/sondagem-api-complementar.json`.

### 10.1 Proprietário (admin)

| Item | Resultado |
|---|---|
| Telas acessíveis | Painel, Agendamentos, Serviços, Barbeiros, Clientes, Dados da barbearia, Minha conta. Rotas de cliente e barbeiro devolvem ao painel |
| Pode | Ver faturamento (200); gerenciar serviços, barbeiros e clientes; confirmar, concluir e cancelar qualquer horário do tenant; editar a barbearia; agendar para cliente pela API (201) |
| Bloqueado corretamente | Rebaixar ou desativar a própria conta (400 e 400); acessar outra barbearia (404 em 11 operações); usar barbeiro, serviço ou cliente de outra barbearia (400) |
| Problemas | Reativa a barbearia desativada pela plataforma (BUS-02f: 200); aceita fechamento antes da abertura (BUS-05); não agenda pela interface (BUS-14); não envia logo (FE-09); não sabe que a barbearia está desativada (FE-14); não cria um segundo admin (BUS-19) |

### 10.2 Barbeiro

| Item | Resultado |
|---|---|
| Telas acessíveis | Minha agenda (por dia e "a confirmar"), Minha conta |
| Pode | Ver só a própria agenda (140 itens, todos dele); confirmar; concluir após o término; agendar para si mesmo |
| Bloqueado corretamente | Faturamento (403, inclusive filtrando o próprio id); usuários (403); serviços (403); horário de outro barbeiro (404); agendar em nome de outro barbeiro (400); DELETE (cancelamento) de horário (403) |
| Problemas | Cancela por PATCH (200) embora o DELETE seja proibido, e **troca o cliente** de um horário (200) (BUS-12); cria horário já "cancelado" (BUS-15); recebe o e-mail de login dos colegas (SEC-03) |

### 10.3 Cliente

| Item | Resultado |
|---|---|
| Telas acessíveis | Início, Agendar horário, Meus agendamentos, Serviços e preços, Equipe, Minha conta |
| Pode | Agendar, reagendar e cancelar os próprios horários; ver serviços e equipe |
| Bloqueado corretamente | Faturamento (403); usuários (403); serviços, barbeiros e barbearia (403); confirmar o próprio horário por PATCH (403); horário de outro cliente (404); agendar em nome de outro cliente (gravado para ele mesmo); autopromoção (ignorada) |
| Problemas | **Cria horário já "confirmado"** (BUS-15: 201); reagendar mantém "confirmado" (BUS-03); cancela horário que já passou (BUS-16); marca dois horários simultâneos (BUS-17); vê o e-mail de login dos barbeiros (SEC-03); recebe 403 em vez de 404 ao consultar outro cliente por id (SEC-10); não consegue se cadastrar sozinho numa barbearia (PROD-01) |

### 10.4 Plataforma (superusuário)

Lê todos os tenants (419 agendamentos) e não cria recursos sem contexto de barbearia (403). Desativa uma barbearia por DELETE com confirmação, mas a desativação é revertida pelo admin do tenant (BUS-02). Não há painel próprio: no frontend, o superusuário cai no onboarding de dono (SA-01).

---

## 11. Responsividade e acessibilidade

### 11.1 Responsividade

| Largura | Rotas | Rolagem horizontal | Erros | Observações |
|---|---|---|---|---|
| Desktop 1440 px | 21 | 0 | 0 | — |
| Notebook 1280 × 720 | 21 | 0 | 0 | — |
| Tablet 820 px | 21 | 0 | 0 | Fluxo do barbeiro concluído |
| Celular 390 px | 21 | 0 | 0 | Fluxo do cliente concluído; menu inferior por perfil; diálogo de cancelamento |
| Celular 360 px | 21 | 0 | 0 | — |

Com 390 px, as funções continuam utilizáveis: barra de navegação inferior, quadro do dia e "A seguir" reordenados para o celular, ações de status nas listas e agendamento em quatro passos.

Detalhes a corrigir:

- filtro de status cortado sem sinal de rolagem e placeholder da busca truncado (FE-20);
- links de texto nas telas públicas com 16 a 22 px de altura (FE-19).

### 11.2 Acessibilidade

| Verificação | Resultado |
|---|---|
| axe-core, WCAG A/AA (36 páginas, desktop e celular) | **0 violações** (controle: 3 violações plantadas foram detectadas) |
| Contraste | Aprovado pelo axe em todas as páginas |
| Teclado | Primeiro Tab no app: "Pular para o conteúdo"; no login, ordem lógica e foco visível em todos os controles; menus e diálogos com Esc (código e auditoria anterior) |
| Rótulos e ARIA | Campos com rótulo; grupos de opção com `role="radiogroup"`; botões de ícone com `aria-label`; gráfico com tabela alternativa para leitor de tela; `aria-live` em horários e confirmação |
| Áreas clicáveis | Botões e controles ≥ 24 px; exceção: links de texto públicos (FE-19) |
| Leitor de tela | Não testado (NV-3) |

---

## 12. Comparação com a auditoria anterior

### 12.1 Situação dos 53 problemas

| ID | Antes | Estado atual | Agora | Verificação nesta auditoria |
|---|---|---|---|---|
| SEC-01 | P0 | ✅ Resolvido e verificado | — | Chave com 86 caracteres; validação em `settings.py`; 10 testes; sem aviso de chave curta |
| SEC-02 | P0 | ✅ Resolvido e verificado | — | PER-08 a PER-11; 13 testes |
| BUS-01 | P1 | ✅ Resolvido e verificado | — | BUS-01 e BUS-01b: 400; testes de concorrência em PostgreSQL. Efeito colateral em BUS-19 |
| BUS-02 | P1 | ◐ Parcialmente resolvido | P2 | Agenda congela (BUS-02c: 400). O admin reativa (02f: 200), os cadastros continuam (02d e 02e: 201) e a interface não sinaliza |
| BUS-03 | P1 | Continua presente | P1 | 200 com status `confirmado` |
| BUS-04 | P1 | Continua presente | P1 | 200 |
| BUS-05 | P1 | Continua presente | P1 | 200 e 200 (completo e parcial) |
| BUS-06 | P1 | Continua presente | P1 | API: 10 horários num domingo; interface: reserva concluída num domingo |
| PROD-01 | P1 | Continua presente | P1 | `barbershop=None` |
| AUTH-01 | P1 | Continua presente | P1 | Sem `EMAIL_*`; `fail_silently=True` |
| BUS-07 | P1 | ✅ Resolvido e verificado | — | 400 com mensagem; 13 testes; botão desabilitado na interface |
| AUTH-02 | P2 | Continua presente (ampliado) | P2 | Cadastro 201, login 401 e também troca do próprio e-mail (200) |
| SEC-03 | P2 | Continua presente | P2 | 3 de 3 barbeiros com e-mail |
| SEC-04 | P2 | Continua presente | P2 | `localStorage`, sem CSP; comentário do settings contradiz |
| SEC-05 | P2 | Continua presente (agora reproduzido) | P2 | 10 de 15 logins aceitos com 3 workers |
| SEC-07 | P2 | Continua presente (agora reproduzido) | P2 | Sem resposta em 10 s |
| BUS-08 | P2 | Continua presente | P2 | 22 vencidos como "agendado" na base de teste |
| BUS-09 | P2 | Continua presente (agora reproduzido) | P2 | Horário das 10:00 passou a terminar às 11:00, sobrepondo o das 10:30 |
| BUS-11 | P2 | Continua presente | P2 | Só horas cheias para 60 min |
| BUS-13 | P2 | Continua presente | P2 | Os 20 horários futuros verificados continuam ativos, por DELETE e por rebaixamento |
| BUS-14 | P2 | Continua presente | P2 | API 201; sem tela |
| API-01 | P2 | Continua presente | P2 | `page_size`, `search`, `ordering` e `tipo_perfil` ignorados; 22 páginas por carga do painel |
| DATA-01 | P2 | Continua presente (agora reproduzido) | P2 | 419 → 0 preços; R$ 15.215 → R$ 16.565 |
| OBS-01 | P2 | Continua presente | P2 | Sem `LOGGING`, monitoramento, auditoria ou health check |
| OPS-01 | P2 | Continua presente | P2 | Sem Dockerfile, CI, estáticos ou mídia em produção |
| FE-01 | P2 | Continua presente | P2 | Nenhum error boundary |
| FE-02 | P2 | Continua presente | P2 | Nenhum teste de frontend |
| TEST-01 | P2 | ◐ Parcialmente resolvido | P2 | +88 testes (SEC-01, SEC-02, BUS-01, BUS-02, BUS-07); continuam sem teste BUS-03, 04, 05, 10, 12, 15, 16, 17, AUTH-02, SEC-03 e a confirmação de recuperação de senha |
| DOC-01 | P2 | Continua presente | P2 | Linhas 82, 77-99, 96, 126, 142 e 399 do documento da API |
| REPO-01 | P2 | Continua presente | P2 | 4.875 de 5.112 arquivos versionados são do `venv312/` |
| SA-01 | P2 | Continua presente | P2 | Branch `feature/painel-super-admin` sem commits próprios |
| SAAS-01 | P2 | Continua presente | P2 | — |
| SEC-06 | P3 | Continua presente | P3 | Commit `3f46df2`; remoto no GitHub |
| SEC-08 | P3 | Continua presente | P3 | — |
| BUS-10 | P3 | Continua presente | P3 | 14 horários para ontem |
| BUS-12 | P3 | Continua presente (**reclassificado**) | **P2** | Agora reproduzido também a troca de cliente pelo barbeiro (200), o que é mais grave que uma inconsistência |
| API-02 | P3 | Continua presente (agora reproduzido) | P3 | 22:30 de 12/11 contado em 13/11 |
| DATA-02 | P3 | Continua presente | P3 | Limitação documentada na migração |
| DATA-03 | P3 | Continua presente | P3 | Collation 2.43 × 2.44 |
| FE-03 | P3 | Continua presente (agora reproduzido) | P3 | API derrubada + "Atualizar": nenhuma mensagem |
| FE-04 | P3 | ◐ Parcialmente resolvido | P3 | O rótulo diz "no total / em todas as datas", mas ainda conta vencidos (40, dos quais 22 vencidos) |
| FE-05 | P3 | Continua presente | P3 | `SHOP_TZ` fixo |
| FE-06 | P3 | Continua presente | P3 | Rota inexistente → início/login |
| FE-07 | P3 | Continua presente (ampliado) | P3 | 17 ícones (eram 14), `getTotalServices`, `getTotalBarbers`, `isPast`, `formatDateTime` e `revenueReport` sem uso |
| FE-08 | P3 | ✅ Resolvido e verificado | — | Fontes `woff2` locais; `index.html` sem Google Fonts |
| FE-09 | P3 | Continua presente | P3 | Sem logo na tela; barbeiro não reagenda |
| FE-11 | P3 | Continua presente (agora reproduzido) | P3 | R$ 570 de diferença |
| DOC-02 | P3 | Continua presente | P3 | README: SQLite por padrão e proxy do Vite inexistente |
| DOC-03 | P3 | Continua presente | P3 | `accounts/models.py:7`, `config/settings.py:72` |
| REPO-02 | P3 | Continua presente (ampliado) | P3 | Também `.codex/`, `.impeccable/`, `references/` (HTML de sites de terceiros) e `media/` fora do `.gitignore` |
| REPO-03 | P3 | Continua presente | P3 | `master` 31 commits atrás; `feature` 1 atrás e sem commits próprios; `release` com 1 commit próprio |
| TEST-02 | P3 | Continua presente | P3 | Cobertura medida só pela auditoria (91%); o projeto não tem a ferramenta |
| FE-12 | P3 | Continua presente | P3 | 2 agendamentos no banco real |

### 12.2 Itens não verificados da auditoria anterior

| ID | Antes | Agora |
|---|---|---|
| NV-1 | Entrega de e-mail | **Continua não verificável**: sem SMTP configurado |
| NV-2 | Concorrência em PostgreSQL | **Verificado**: CON-01 e testes de concorrência em PostgreSQL 16 |
| NV-3 | Leitor de tela | Continua não verificado; checagens automáticas aprovadas |
| NV-4 | Tablet e outros navegadores | Tablet (820 px) **verificado**; Chrome e Safari continuam não verificados |
| NV-5 | Rate limiting real | **Verificado**: funciona num processo e falha com vários (SEC-05) |

### 12.3 Correções ao que a auditoria anterior afirmou

| Afirmação de 11/11 | Correção |
|---|---|
| "Banco PostgreSQL 16 via `docker-compose.yml` (porta 5433)" e "migrações íntegras e aplicadas" | O `.env` aponta para o PostgreSQL **18** do host (porta 5432), onde as migrações estão aplicadas. O banco do `docker-compose` é outro e está com duas migrações pendentes (DB-01) |
| "Isolamento resistiu às 16 tentativas" | Confirmado e ampliado para 21 tentativas; foram encontrados dois oráculos de existência de IDs (SEC-10) |
| SEC-07 e DATA-01 "não executados" | Agora reproduzidos em ambiente descartável |

---

## 13. Lista completa de problemas

### 13.1 Índice dos 70 problemas abertos

| # | ID | Sev. | Camada | Título | Estado | Confiança |
|---|---|---|---|---|---|---|
| 1 | BUS-15 | P1 | Backend | Cliente cria agendamento já "confirmado" | Novo | Confirmado |
| 2 | BUS-03 | P1 | Backend | Reagendamento mantém "confirmado" | Continua | Confirmado |
| 3 | BUS-06 | P1 | Backend + Frontend | Domingos e dias fechados recebem agendamentos | Continua | Confirmado |
| 4 | BUS-05 | P1 | Backend | Fechamento anterior à abertura é aceito | Continua | Confirmado |
| 5 | BUS-04 | P1 | Backend | Troca de serviço ignora o horário de funcionamento | Continua | Confirmado |
| 6 | PROD-01 | P1 | Produto | Cliente não se cadastra numa barbearia | Continua | Confirmado |
| 7 | AUTH-01 | P1 | Backend / Config. | Recuperação de senha não envia e-mail | Continua | Confirmado (código) |
| 8 | BUS-02 | P2 | Backend + Frontend | Suspensão de barbearia parcial e reversível pelo próprio admin | Parcial | Confirmado |
| 9 | BUS-12 | P2 | Backend | Barbeiro troca o cliente e cancela por PATCH, mas não por DELETE | Continua (reclass.) | Confirmado |
| 10 | BUS-16 | P2 | Backend | Cliente cancela horário que já passou | Novo | Confirmado |
| 11 | BUS-17 | P2 | Backend | Mesmo cliente com horários simultâneos, sem limite de reservas | Novo | Confirmado |
| 12 | AUTH-02 | P2 | Backend / Banco | E-mails duplicados por maiúsculas (cadastro e edição) | Continua | Confirmado |
| 13 | SEC-03 | P2 | Backend | E-mail de login dos barbeiros exposto a clientes | Continua | Confirmado |
| 14 | SEC-04 | P2 | Frontend / Infra | Access token em `localStorage`, sem CSP | Continua | Confirmado |
| 15 | SEC-05 | P2 | Infra | Rate limiting por processo | Continua | Confirmado |
| 16 | SEC-07 | P2 | Backend / Banco | Serviço com duração 0 trava a requisição | Continua | Confirmado |
| 17 | SEC-09 | P2 | Backend / Infra | Upload de logo sem limite de tamanho | Novo | Confirmado |
| 18 | DEP-01 | P2 | Dependências | Backend com 91 vulnerabilidades conhecidas; Django fora de suporte | Novo | Confirmado |
| 19 | DB-01 | P2 | Banco / Config. | Dois bancos de desenvolvimento divergentes | Novo | Confirmado |
| 20 | DATA-01 | P2 | Banco | Reverso da migração 0008 apaga e altera preços | Continua | Confirmado |
| 21 | BUS-08 | P2 | Backend / Produto | Sem "não compareceu" nem desfecho de vencidos | Continua | Confirmado |
| 22 | BUS-09 | P2 | Backend / Banco | Duração do atendimento não é histórica | Continua | Confirmado |
| 23 | BUS-11 | P2 | Backend | Passo entre horários igual à duração | Continua | Confirmado |
| 24 | BUS-13 | P2 | Backend | Desativar ou rebaixar barbeiro não trata a agenda | Continua | Confirmado |
| 25 | BUS-14 | P2 | Frontend | Admin não agenda pela interface | Continua | Confirmado |
| 26 | API-01 | P2 | API + Frontend | Sem filtros, busca e `page_size`; telas baixam todo o histórico | Continua | Confirmado |
| 27 | FE-01 | P2 | Frontend | Sem error boundary | Continua | Confirmado (código) |
| 28 | FE-02 | P2 | Frontend / Testes | Nenhum teste de frontend | Continua | Confirmado |
| 29 | TEST-01 | P2 | Testes | Regras quebradas sem teste de regressão | Parcial | Confirmado |
| 30 | OBS-01 | P2 | Backend / Infra | Sem logs, monitoramento, trilha de auditoria e health check | Continua | Confirmado (código) |
| 31 | OPS-01 | P2 | Infra | Sem infraestrutura de implantação | Continua | Confirmado |
| 32 | DOC-01 | P2 | Documentação | Documentação da API contradiz o comportamento | Continua | Confirmado |
| 33 | REPO-01 | P2 | Repositório | Virtualenv versionado | Continua | Confirmado |
| 34 | SA-01 | P2 | Produto | Sem painel de Super Admin | Continua | Confirmado |
| 35 | SAAS-01 | P2 | Produto | Sem notificações, LGPD e cobrança | Continua | Confirmado |
| 36 | FE-13 | P3 | Frontend | "Agendar" após reservar continua mostrando "Horário reservado" | **Novo (regressão)** | Confirmado |
| 37 | FE-14 | P3 | Frontend | Barbearia desativada e dia da semana ignorados no status "Aberta" | Novo | Confirmado |
| 38 | FE-03 | P3 | Frontend | Falha de recarga sem aviso | Continua | Confirmado |
| 39 | FE-15 | P3 | Frontend | Requisições sem tempo limite | Novo | Confirmado |
| 40 | FE-16 | P3 | Frontend | "1.000" no preço vira R$ 1,00 | Novo | Confirmado |
| 41 | FE-04 | P3 | Frontend | Contador "a confirmar" inclui vencidos | Parcial | Confirmado |
| 42 | FE-17 | P3 | Integração | Contratos de API e tipos divergentes | Novo | Confirmado |
| 43 | FE-18 | P3 | Frontend | Textos que prometem o que o sistema não faz | Novo | Confirmado |
| 44 | FE-19 | P3 | Frontend / A11y | Links de texto pequenos para toque nas telas públicas | Novo | Confirmado |
| 45 | FE-20 | P3 | Frontend | Filtro de status cortado e busca truncada no celular | Novo | Confirmado |
| 46 | FE-05 | P3 | Integração | Fuso horário fixo no frontend | Continua | Confirmado (código) |
| 47 | FE-06 | P3 | Frontend | Sem página 404 | Continua | Confirmado |
| 48 | FE-07 | P3 | Frontend | Código morto | Continua (ampliado) | Confirmado |
| 49 | FE-09 | P3 | Frontend | Sem tela de logo; barbeiro não reagenda | Continua | Confirmado |
| 50 | FE-11 | P3 | Integração | Painel e relatório da API calculam o faturamento de formas diferentes | Continua | Confirmado |
| 51 | API-02 | P3 | Backend | Relatório agrupa o dia em UTC | Continua | Confirmado |
| 52 | BUS-10 | P3 | Backend | Horários livres para datas passadas | Continua | Confirmado |
| 53 | BUS-18 | P3 | Backend | Validações de cadastro fracas | Novo | Confirmado |
| 54 | BUS-19 | P3 | Backend / Produto | Sem segundo admin nem transferência de titularidade | Novo | Confirmado (código) |
| 55 | SEC-06 | P3 | Repositório | Chave antiga no histórico do git | Continua | Confirmado |
| 56 | SEC-08 | P3 | Backend | Sem verificação de e-mail no cadastro | Continua | Confirmado (código) |
| 57 | SEC-10 | P3 | Backend | Oráculo de existência de IDs | Novo | Confirmado |
| 58 | SEC-11 | P3 | Configuração | Configurações de desenvolvimento inseguras se reaproveitadas | Novo | Confirmado |
| 59 | DEP-02 | P3 | Dependências | Frontend com 14 vulnerabilidades conhecidas | Novo | Confirmado |
| 60 | DATA-02 | P3 | Banco | Preços históricos antigos estimados | Continua | Confirmado |
| 61 | DATA-03 | P3 | Banco | Divergência de collation | Continua | Confirmado |
| 62 | DB-02 | P3 | Banco | Regras de negócio sem constraints no banco | Novo | Confirmado |
| 63 | MAINT-01 | P3 | Código | Componentes grandes, estilos inline, duplicação e código morto no backend | Novo | Confirmado |
| 64 | DOC-02 | P3 | Documentação | README com instruções incorretas | Continua (ampliado) | Confirmado |
| 65 | DOC-03 | P3 | Documentação | Comentários obsoletos sobre o app `core` | Continua | Confirmado |
| 66 | DOC-04 | P3 | Documentação | Índice de `docs/` e comentários desatualizados | Novo | Confirmado |
| 67 | REPO-02 | P3 | Repositório | Arquivos soltos e pastas fora do `.gitignore` | Continua (ampliado) | Confirmado |
| 68 | REPO-03 | P3 | Repositório | Branches dessincronizadas | Continua | Confirmado |
| 69 | TEST-02 | P3 | Testes | Cobertura não medida pelo projeto | Continua | Confirmado |
| 70 | FE-12 | P3 | Dados / Apresentação | Banco real quase vazio para a demonstração | Continua | Confirmado |

Os detalhes abaixo seguem esta ordem. Referências do tipo "BUS-03 (sondagem)" apontam para `api/sondagem-api.json` ou `api/sondagem-api-complementar.json` da pasta de evidências.

---

### 13.2 Problemas P1 — Alto (7)

#### BUS-15 — Cliente cria agendamento já "confirmado"

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend (serializer e view) | `appointments/serializers.py:34,37`; `appointments/views.py:87-105`; `appointments/models.py:345-347` | Confirmado | **Novo** |

- **Descrição.**
  - O campo `status` do `AppointmentSerializer` é gravável também na criação.
  - `perform_create` não fixa o status inicial.
  - A máquina de estados (`_validar_transicao_status`) retorna cedo quando o registro ainda não existe.
  - Resultado: qualquer perfil escolhe o status de um agendamento novo. Só "realizado" é barrado, pela regra do BUS-07.
- **Evidência.**
  - NEW-STATUS: cliente → **201, status `confirmado`**.
  - NEW-STATUS-2: barbeiro → **201, status `cancelado`**.
  - Nenhum teste cobre a criação com `status`.
- **Reprodução.**
  1. Entrar como cliente.
  2. `POST /api/v1/appointments/` com `cliente` (o próprio id), `barbeiro`, `servico`, `data_hora` futura e `"status": "confirmado"`.
- **Resultado atual.** 201 com `status: confirmado`.
- **Resultado esperado.** Todo agendamento novo nasce `agendado`: o campo é ignorado ou a API responde 400.
- **Impacto.**
  - O cliente contorna a confirmação da barbearia.
  - O horário não entra na fila "a confirmar" do admin nem do barbeiro.
  - A agenda mostra uma confirmação que ninguém deu.
- **Recomendação.**
  1. Tornar `status` somente leitura quando `self.instance is None`, ou chamar `serializer.save(status=AGENDADO)` em `perform_create`.
  2. No model, recusar registro novo com status diferente de `agendado`, salvo origem administrativa explícita.
  3. Teste para os três perfis.

#### BUS-03 — Reagendamento pelo cliente mantém "confirmado"

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend | `appointments/serializers.py:228-255` (`update`), `:128-170` | Confirmado | Continua presente |

- **Descrição.** Quando o cliente altera `data_hora`, `barbeiro` ou `servico` de um horário confirmado, o status continua "confirmado". A barbearia confirmou o horário antigo, não o novo.
- **Evidência.**
  - Sondagem BUS-03: criar → admin confirma → cliente reagenda → **200 com `status: confirmado`**.
  - A tela de sucesso do reagendamento diz "O novo horário já está na sua agenda" (`AppointmentCreatePage.tsx`).
- **Reprodução.**
  1. Cliente cria um horário.
  2. Admin aplica `PATCH {"status": "confirmado"}`.
  3. Cliente aplica `PATCH {"data_hora": "<outro horário>"}`.
- **Resultado atual.** `confirmado`.
- **Resultado esperado.** Volta a `agendado` quando horário, barbeiro ou serviço mudam; alterar só `observacoes` não muda o status.
- **Impacto.** Barbeiro e admin confiam numa confirmação que não existe. Somado ao BUS-15, o fluxo de confirmação fica sem garantia.
- **Recomendação.** Em `update`, redefinir `status = AGENDADO` na mesma transação quando esses campos mudarem; decidir se a regra vale para alterações do admin e do barbeiro; testes.

#### BUS-06 — Domingos e dias fechados recebem agendamentos

> **Rodada 1 de correções (13/11/2026): Parcialmente resolvido (dias da semana configuráveis; feriados, folgas e disponibilidade por barbeiro continuam ausentes).** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend + Banco + Frontend | `appointments/views.py:236-268`; `barbershops/models.py:22-23`; `frontend/src/pages/AppointmentCreatePage.tsx:25,104` | Confirmado | Continua presente |

- **Descrição.**
  - O sistema não modela dias de funcionamento, feriados, bloqueios nem folgas e horário de cada barbeiro.
  - O mesmo horário de abertura e fechamento vale para todos os dias e todos os barbeiros.
  - O frontend oferece os próximos 21 dias sem distinção.
- **Evidência.**
  - API: domingo 15/11 → **10 horários** para um serviço de 60 min.
  - Navegador: domingo com **16 horários**, e uma reserva concluída para **domingo, 22/11** (capturas `fluxo_cliente_domingo_com_horarios.png` e `fluxo_cliente_agendamento_concluido.png`).
- **Reprodução.** `GET /api/v1/appointments/available-slots/?barbeiro=<id>&servico=<id>&data=<próximo domingo>`, ou agendar pela tela escolhendo "Dom".
- **Resultado atual.** Horários oferecidos e reserva aceita.
- **Resultado esperado.** Dias fechados e folgas sem horários; a API recusa a criação com mensagem clara.
- **Impacto.** Clientes reservam com a barbearia fechada. É o problema mais visível numa demonstração com o calendário.
- **Recomendação.**
  1. Grade semanal da barbearia (dia × abertura e fechamento, com intervalos).
  2. Exceções por data e disponibilidade por barbeiro.
  3. Aplicar em `available_slots` e em `Appointment.clean()`.
  4. Tela de configuração.
  5. Como medida mínima imediata: um campo "dias de funcionamento" na barbearia.

#### BUS-05 — Fechamento anterior à abertura é aceito

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend (model e serializer) | `barbershops/models.py:12-35` (sem `clean`); `barbershops/serializers.py:20-32` | Confirmado | Continua presente |

- **Descrição.** A API aceita `horario_fechamento` ≤ `horario_abertura`, na edição completa e na parcial. O frontend valida, mas a API é a defesa real.
- **Evidência.**
  - Sondagem BUS-05: completo **200**, parcial **200**.
  - Navegador: o formulário bloqueou o mesmo caso (`admin_desktop_validacao_horario.png`).
- **Reprodução.** `PATCH /api/v1/barbershops/<id>/` com `{"horario_abertura": "18:00:00", "horario_fechamento": "08:00:00"}`, ou só `{"horario_fechamento": "08:30:00"}`.
- **Resultado atual.** 200.
- **Resultado esperado.** 400, inclusive quando só um dos campos é enviado.
- **Impacto.** Nenhum horário é gerado e todos os agendamentos são recusados sem explicação: a barbearia "some" da agenda.
- **Recomendação.** `Barbershop.clean()` com `fechamento > abertura`; `validate()` do serializer comparando com o valor persistido no PATCH parcial; `CheckConstraint` (DB-02); testes.

#### BUS-04 — Troca de serviço ignora o horário de funcionamento

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend (model) | `appointments/models.py:238-248` | Confirmado | Continua presente |

- **Descrição.** `_validar_horario_funcionamento` retorna cedo se `data_hora` não mudou e não considera a troca de serviço, então um serviço mais longo ultrapassa o fechamento.
- **Evidência.** Sondagem BUS-04: horário às 18:30 (fechamento às 19:00), serviço trocado de 30 para 60 min → **200**.
- **Reprodução.** Criar às 18:30 com serviço de 30 min; `PATCH {"servico": <id do serviço de 60 min>}`.
- **Resultado atual.** 200; o atendimento termina às 19:30.
- **Resultado esperado.** 400 com a mensagem de fechamento.
- **Impacto.** Atendimentos fora do expediente.
- **Recomendação.** Revalidar quando `data_hora` **ou** `servico_id` mudarem; testes para os dois casos.

#### PROD-01 — Cliente não se cadastra numa barbearia

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Produto (backend + frontend) | `accounts/serializers.py:309-321`; `accounts/views.py:119-130`; `frontend/src/pages/RegisterPage.tsx`, `OnboardingPage.tsx` | Confirmado | Continua presente |

- **Descrição.** O cadastro público cria um cliente sem barbearia, que é levado a criar a própria barbearia. Não há página pública, convite nem código por barbearia.
- **Evidência.**
  - Sondagem PROD-01: **201, `barbershop=None`**.
  - No banco real há 1 conta sem barbearia criada pelo cadastro.
- **Reprodução.** `/register` → a conta entra em "Vamos cadastrar sua barbearia".
- **Resultado atual.** Só o admin cadastra clientes, informando uma senha inicial que ele mesmo conhece.
- **Resultado esperado.** Cliente se cadastra e agenda numa barbearia específica.
- **Impacto.** Inviabiliza a aquisição de clientes; cria tenants vazios.
- **Recomendação.** Página pública por barbearia (`/b/<slug>`) ou convite por link, e separação entre conta de dono e conta de cliente.

#### AUTH-01 — Recuperação de senha não envia e-mail

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend / Configuração | `config/settings.py` (sem `EMAIL_*`); `accounts/serializers.py:381-419` | Confirmado por código; entrega não verificável (NV-1) | Continua presente |

- **Descrição.**
  - Sem `EMAIL_BACKEND` nem SMTP configurados: o Django tenta `localhost:25`.
  - `fail_silently=True` engole a falha sem log.
  - A mensagem traz `uid` e `token` em texto, sem link.
  - A confirmação não tem nenhum teste (`accounts/serializers.py:427-449` sem cobertura).
- **Evidência.** Busca em `settings.py`; respostas 204 para e-mail existente e inexistente (SES-10); relatório de cobertura.
- **Reprodução.** `/password/reset` com uma conta existente → a tela confirma, mas nenhum e-mail chega.
- **Resultado atual.** O usuário fica sem acesso até alguém intervir.
- **Resultado esperado.** E-mail com link para a tela de nova senha; falhas registradas em log.
- **Impacto.** Recuperação de acesso inexistente na prática.
- **Recomendação.** Variáveis `EMAIL_*` no `.env.example`; backend de console em desenvolvimento; link `FRONTEND_URL/password/reset/confirm?uid=…&token=…`; log de falhas; testes da confirmação.

---

### 13.3 Problemas P2 — Médio (28)

#### BUS-02 — Suspensão de barbearia parcial e reversível pelo próprio admin

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 (era P1) | Backend + Frontend | `barbershops/serializers.py:15,18` (`ativo` gravável); `barbershops/views.py:38`; `appointments/models.py:145-175`; `frontend/src/components/AppLayout.tsx:296-310` | Confirmado | **Parcialmente resolvido** |

- **Descrição.**
  - **O que foi corrigido:** com `ativo=False`, ninguém cria, remarca, confirma ou conclui agendamentos, e os horários livres são recusados. Os testes do dono cobrem isso.
  - **O que continua:**
    - o campo `ativo` continua gravável pelo admin do tenant, que **desfaz a desativação feita pela plataforma** (o DELETE é restrito ao staff, mas o PATCH não);
    - login, cadastro de clientes e serviços e edição da barbearia seguem normalmente;
    - a interface não mostra que a barbearia está desativada (FE-14).
- **Evidência.** Sondagem BUS-02:
  - plataforma desativa → 204;
  - cliente agenda → **400**, como esperado;
  - admin cria serviço → **201** e cadastra cliente → **201**;
  - admin aplica `PATCH {"ativo": true}` → **200** e a barbearia volta a operar.
  - O teste do dono `test_admin_desativa_e_reativa_a_barbearia` assume essa reativação como regra.
- **Reprodução.**
  1. Superusuário: `DELETE /api/v1/barbershops/<id>/?confirmar=<nome>`.
  2. Admin do tenant: `PATCH /api/v1/barbershops/<id>/` com `{"ativo": true}`.
- **Resultado atual.** Reativada pelo próprio tenant.
- **Resultado esperado.** Distinguir "pausa pelo dono" de "suspensão pela plataforma". A suspensão só pode ser revertida pelo staff.
- **Impacto.** A plataforma não consegue suspender uma barbearia (inadimplência, abuso). Vira P1 se houver cobrança.
- **Recomendação.**
  1. `ativo` somente leitura para não-staff, ou um campo separado `suspensa_pela_plataforma`.
  2. Verificação central que bloqueie a escrita em todo o tenant suspenso.
  3. Aviso na interface.
  4. Testes.

#### BUS-12 — Barbeiro troca o cliente e cancela por PATCH, mas não por DELETE

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 (era P3) | Backend | `appointments/serializers.py:99-126`; `appointments/views.py:40-51` | Confirmado | Continua presente — **reclassificado** |

- **Descrição.**
  - O DELETE (cancelamento) é proibido ao barbeiro, mas `PATCH {"status": "cancelado"}` é aceito.
  - O serializer só impede o **cliente** de trocar o campo `cliente`, então o barbeiro reatribui o horário a outra pessoa.
- **Evidência.** Sondagem complementar BUS-12, no horário do próprio barbeiro:
  - DELETE **403**;
  - `PATCH {"cliente": <outro>}` **200**, e o horário passou ao outro cliente;
  - `PATCH {"status": "cancelado"}` **200**.
- **Reprodução.** Como barbeiro, nos próprios horários, executar as três chamadas acima.
- **Resultado atual.** Regras contraditórias, e o cliente original perde o horário sem consentimento.
- **Resultado esperado.** Mesma regra nos dois caminhos; troca de cliente só pelo admin, ou proibida.
- **Impacto.** Integridade da agenda e dos dados do cliente; a reclassificação para P2 decorre da troca de cliente agora reproduzida.
- **Recomendação.** Definir a regra, aplicá-la no serializer e no `get_permissions`, e testar.

#### BUS-16 — Cliente cancela horário que já passou

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/serializers.py:108-145`; `appointments/views.py:115-131` | Confirmado | **Novo** |

- **Descrição.** Não há prazo para cancelamento: o cliente cancela um horário que já começou ou terminou, inclusive um confirmado que ainda não foi marcado como realizado.
- **Evidência.** Sondagem NEW-PASTCANCEL: horário das 14:00 de hoje, cancelado depois das 15:40 → **204**.
- **Reprodução.** `DELETE /api/v1/appointments/<id>/`, ou `PATCH {"status": "cancelado"}`, num horário próprio com `data_hora` no passado.
- **Resultado atual.** Cancelado.
- **Resultado esperado.** Recusado depois do início (ou de uma antecedência mínima configurável). Horários passados viram "realizado" ou "não compareceu" (BUS-08).
- **Impacto.**
  - Um atendimento feito pode sair do faturamento por iniciativa do cliente, antes de o barbeiro marcar "realizado".
  - Não comparecimentos viram "cancelamentos".
- **Recomendação.** Bloquear o cancelamento pelo cliente após `data_hora`, com antecedência mínima configurável; teste.

#### BUS-17 — Mesmo cliente com horários simultâneos, sem limite de reservas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/models.py:304-332` (conflito só por barbeiro) | Confirmado | **Novo** |

- **Descrição.**
  - A checagem de conflito considera só o barbeiro: o mesmo cliente reserva o mesmo horário com dois barbeiros.
  - Não há limite de reservas futuras por cliente.
  - O único freio é o throttling de 1.000 requisições por hora.
- **Evidência.** Sondagem NEW-OVERLAP: duas reservas às 16:00 do mesmo dia, com barbeiros diferentes → **201 / 201**.
- **Reprodução.** Dois `POST /appointments/` do mesmo cliente, mesmo horário, barbeiros diferentes.
- **Resultado atual.** Os dois são aceitos.
- **Resultado esperado.** O segundo é recusado; limite de reservas ativas por cliente.
- **Impacto.** Agenda inflada e horários bloqueados para outros clientes. Um cliente mal-intencionado ocupa a agenda inteira.
- **Recomendação.** Validar a sobreposição por cliente em `clean()`, sob a mesma trava; limite configurável de reservas futuras; testes.

#### AUTH-02 — E-mails duplicados por maiúsculas (cadastro e edição)

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Banco | `accounts/managers.py:43`; `accounts/models.py:29`; `accounts/serializers.py:46-57` | Confirmado | Continua presente (ampliado) |

- **Descrição.** `normalize_email` só converte o domínio para minúsculas, e a unicidade de `email` diferencia maiúsculas. Além do cadastro, o próprio usuário troca o e-mail para uma variação do e-mail de outra pessoa.
- **Evidência.** Sondagem:
  - AUTH-02 (cadastro de `CLIENTE1@…` existente) **201**;
  - AUTH-02b (login com outra grafia) **401**;
  - AUTH-02c (troca do próprio e-mail para `CLIENTE2@…`) **200**.
  - No banco real há 0 duplicados.
- **Reprodução.** `POST /auth/register/` com um e-mail existente em maiúsculas; `PATCH /users/<seu id>/` com `{"email": "<e-mail de outro em maiúsculas>"}`.
- **Resultado atual.** Contas duplicadas; login sensível à grafia.
- **Resultado esperado.** 400 "e-mail já cadastrado"; login aceita qualquer grafia.
- **Impacto.** Contas duplicadas; a recuperação (`email__iexact().first()`) pode escolher a conta errada.
- **Recomendação.** Normalizar para minúsculas no manager, nos serializers e no login; `UniqueConstraint(Lower('email'))` após checar duplicados; testes.

#### SEC-03 — E-mail de login dos barbeiros exposto a clientes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `barbershops/serializers.py:39` | Confirmado | Continua presente |

- **Descrição.** `GET /barbers/`, necessário para agendar, devolve o `email` de login de cada barbeiro a qualquer cliente e barbeiro.
- **Evidência.** Sondagem PER-12: **3 de 3** itens com e-mail.
- **Reprodução.** Como cliente, `GET /api/v1/barbers/`.
- **Resultado atual.** E-mail presente.
- **Resultado esperado.** Só o admin recebe `email`.
- **Impacto.** Dados pessoais de funcionários expostos; facilita phishing e ataques às contas.
- **Recomendação.** Serializer público sem `email`, escolhido por perfil; teste.

#### SEC-04 — Access token em `localStorage`, sem CSP

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend / Infra | `frontend/src/utils/storage.ts:13`; `config/settings.py:219` | Confirmado | Continua presente |

- **Descrição.** O access token (15 min) fica em `localStorage`, não há CSP, e o comentário do `settings.py` afirma que ele "é mantido apenas em memória". O token traz `nome`, `tipo_perfil`, `barbershop_id` e `hash_password` (derivado do hash da senha).
- **Evidência.** Código; SES-03 (claims); SES-09 (sem `Content-Security-Policy`).
- **Reprodução.** Entrar e executar `localStorage.getItem('barbearia.auth')` no console.
- **Resultado atual.** Token legível por qualquer script da página.
- **Resultado esperado.** Token só em memória, renovado pelo cookie ao recarregar; CSP restritiva.
- **Impacto.** Um XSS futuro (por exemplo, por dependência comprometida) age como o usuário por até 15 minutos.
- **Recomendação.** Manter o access em memória; adicionar CSP no servidor web ou com `django-csp`; corrigir o comentário.

#### SEC-05 — Rate limiting por processo

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Infra / Configuração | `config/settings.py:186-200` (sem `CACHES`) | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.**
  - O throttling usa o cache padrão em memória de cada processo.
  - Com N workers, o limite efetivo vira N vezes maior e zera a cada reinício.
  - Sem `NUM_PROXIES`, atrás de um proxy todos os usuários compartilham o mesmo IP e o limite.
- **Evidência.** `api/rate-limit-gunicorn-3-workers.txt`: 15 logins errados no mesmo minuto e mesmo IP → **10 aceitos (401) e 5 bloqueados (429)**, contra o limite configurado de 5/min. Num único processo, o 6º login recebeu 429.
- **Reprodução.** gunicorn com 3 workers e 15 `POST /auth/login/` com senha errada.
- **Resultado atual.** 10 tentativas aceitas.
- **Resultado esperado.** A partir da 6ª, 429 em qualquer worker.
- **Impacto.** Proteção contra força bruta reduzida em produção.
- **Recomendação.** Cache compartilhado (Redis) e `NUM_PROXIES` conforme a infraestrutura.

#### SEC-07 — Serviço com duração 0 trava a requisição

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Banco | `services/models.py:20`; `appointments/views.py:262-268` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** O model aceita `duracao = 0`; só o serializer exige ≥ 1. Com 0, o laço `while slot_atual <= limite: slot_atual += duracao` não avança.
- **Evidência.** `api/sec07-duracao-zero.txt`: serviço criado pelo ORM (como faria o Django Admin) e `available-slots` **sem resposta em 10 s** (processo encerrado pelo `timeout`, código 124).
- **Reprodução.** Django Admin → serviço com duração 0 → consultar horários desse serviço.
- **Resultado atual.** O worker fica preso com CPU em 100%.
- **Resultado esperado.** O banco recusa duração 0 e o endpoint responde com erro.
- **Impacto.** Negação de serviço com poucas requisições; exige acesso ao Django Admin ou ao banco.
- **Recomendação.** `MinValueValidator(1)` + `CheckConstraint(duracao__gt=0)` com migração; guarda no laço; teste.

#### SEC-09 — Upload de logo sem limite de tamanho

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Infra | `barbershops/models.py:24-26`; `config/settings.py:163`; `.gitignore` | Confirmado | **Novo** |

- **Descrição.**
  - O `ImageField` da logo não tem limite de tamanho nem de dimensões.
  - O processamento usa Pillow 10.4.0, com 69 vulnerabilidades conhecidas (DEP-01).
  - Os arquivos vão para `media/` dentro do projeto, pasta que não está no `.gitignore`.
- **Evidência.**
  - Sondagem complementar UPL-01: PNG de **14,5 MB → 200**, e o arquivo foi gravado.
  - UPL-02: SVG com script → 400, corretamente.
- **Reprodução.** `PATCH /api/v1/barbershops/<id>/` multipart com uma logo grande.
- **Resultado atual.** Aceito.
- **Resultado esperado.** Limite (por exemplo, 2 MB e 1.024 px), com redimensionamento.
- **Impacto.** Consumo de disco e memória; superfície de ataque do Pillow; risco de versionar uploads de usuários.
- **Recomendação.** Validador de tamanho e dimensões; `FILE_UPLOAD_MAX_MEMORY_SIZE` e `DATA_UPLOAD_MAX_MEMORY_SIZE` explícitos; `media/` no `.gitignore`; atualizar o Pillow.

#### DEP-01 — Backend com 91 vulnerabilidades conhecidas; Django fora de suporte

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Dependências | `requirements.txt` | Confirmado | **Novo** |

- **Descrição.** As 91 vulnerabilidades conhecidas estão em 5 pacotes:

  | Pacote | Versão | Avisos | Observação |
  |---|---|---|---|
  | Django | 5.0.14 | 13 | Série 5.0 sem correções de segurança desde abril de 2025 |
  | Pillow | 10.4.0 | 69 | Processa as logos enviadas |
  | djangorestframework | 3.15.2 | 5 | — |
  | PyJWT | 2.14.0 | 2 | — |
  | djangorestframework-simplejwt | 5.3.1 | 2 | — |

- **Evidência.** `dependencias/backend-pip-audit.txt`.
- **Reprodução.** `pip-audit -r requirements.txt`.
- **Resultado atual.** 91 avisos.
- **Resultado esperado.** Versões com suporte e sem avisos conhecidos.
- **Impacto.** Exposição a falhas públicas, especialmente no upload de imagens e nos componentes de autenticação.
- **Recomendação.** Migrar para Django 5.2 LTS e versões atuais de DRF, simplejwt, PyJWT e Pillow, rodando a suíte (327 testes) a cada passo; adicionar `pip-audit` ao CI.

#### DB-01 — Dois bancos de desenvolvimento divergentes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Banco / Configuração | `.env` (`DATABASE_URL` → porta 5432); `docker-compose.yml`; `config/settings.py:127`; `config/test_postgres_settings.py`; `README.md` | Confirmado | **Novo** |

- **Descrição.**
  - O app usa o **PostgreSQL 18 do host** (porta 5432), conforme o `.env`.
  - O `README` ("PostgreSQL via Docker"), o `docker-compose.yml`, o valor padrão do `settings.py` e o `test_postgres_settings.py` apontam para o **container PostgreSQL 16** na porta 5433.
  - O container está **com as migrações `appointments.0007` e `0008` pendentes**, sem a coluna `preco_historico` e com dados diferentes (6 agendamentos, contra 2 no banco do app).
- **Evidência.**
  - `showmigrations` no banco do app: todas aplicadas.
  - Consulta somente leitura no container: a coluna `preco_historico` não existe, e `django_migrations` vai só até `0005`.
  - `banco/integridade-banco-real-somente-leitura.txt`.
- **Reprodução.** Seguir o README (`docker-compose up`) e apontar o `.env` para a porta 5433: as telas de agendamento falham por coluna inexistente até um `migrate`.
- **Resultado atual.** Duas fontes de verdade, com versões e dados diferentes.
- **Resultado esperado.** Um único banco de desenvolvimento, documentado e migrado.
- **Impacto.** Risco concreto na demonstração (subir o banco errado gera erros 500) e confusão sobre "o banco real".
- **Recomendação.** Escolher um banco, alinhar `.env.example`, README e `docker-compose.yml` (inclusive a versão do PostgreSQL) e migrar o outro ou removê-lo do fluxo.

#### DATA-01 — Reverso da migração 0008 apaga e altera preços

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Banco | `appointments/migrations/0008_populate_preco_historico.py:20` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** O reverso executa `Appointment.objects.all().update(preco_historico=None)`. Reaplicar a migração preenche com o preço **atual** do serviço.
- **Evidência.** `banco/data01-reverso-migracao-0008.txt`, numa cópia descartável:
  - desfazer: **419 → 0** preços;
  - depois de o "Corte" subir de R$ 45 para R$ 60, desfazer e refazer muda o faturamento realizado de **R$ 15.215 para R$ 16.565**.
- **Reprodução.** `migrate appointments 0007` e depois `migrate appointments`, num banco **descartável**.
- **Resultado atual.** Dados financeiros perdidos ou alterados.
- **Resultado esperado.** Reverso sem efeito sobre preços gravados pela aplicação.
- **Impacto.** Um rollback operacional corrompe o histórico financeiro.
- **Recomendação.** `migrations.RunPython.noop` como reverso; teste de ida e volta.

#### BUS-08 — Sem "não compareceu" nem desfecho de vencidos

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Produto | `appointments/models.py:28-32` | Confirmado | Continua presente |

- **Descrição.** Só há 4 status. Horários que passaram sem desfecho continuam "agendado" ou "confirmado" para sempre e entram em "a confirmar" (FE-04).
- **Evidência.** Sondagem BUS-08: **22 vencidos como "agendado"** na base de teste; no banco real, 0.
- **Reprodução.** Deixar um horário passar sem alterar o status.
- **Resultado atual.** Continua pendente.
- **Resultado esperado.** Status `nao_compareceu` e separação dos vencidos.
- **Impacto.** Agenda poluída; não há como medir comparecimento.
- **Recomendação.** Novo status com transições a partir de agendado ou confirmado após o horário; indicador de vencidos; testes.

#### BUS-09 — Duração do atendimento não é histórica

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Banco | `appointments/models.py:207,251,314`; `appointments/views.py:250-257` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** Conflitos, horários livres, fim do atendimento e a regra do "realizado" usam a duração **atual** do serviço.
- **Evidência.** Sondagem complementar BUS-09: horários às 10:00 e 10:30 com um serviço de 30 min. Depois de mudar a duração para 60 min, o das 10:00 passa a terminar às 11:00, **sobrepondo** o das 10:30, que continua ativo.
- **Reprodução.** Alterar a duração de um serviço com horários seguidos.
- **Resultado atual.** Sobreposição criada retroativamente.
- **Resultado esperado.** Agendamentos existentes mantêm a duração com que foram marcados.
- **Impacto.** Agenda inconsistente; a promessa "agenda sem conflito" da página institucional deixa de valer.
- **Recomendação.** Campo `duracao_historica`, preenchido como `preco_historico`, com migração de dados e uso em todos os cálculos.

#### BUS-11 — Passo entre horários igual à duração

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/views.py:268` | Confirmado | Continua presente |

- **Descrição.** Os horários livres avançam pela duração do serviço.
- **Evidência.** Sondagem BUS-11: serviço de 60 min → 09:00, 10:00, 11:00…
- **Reprodução.** Consultar `available-slots` para um serviço de 60 min.
- **Resultado atual.** Só horas cheias.
- **Resultado esperado.** Passo configurável, por exemplo 15 min.
- **Impacto.** Encaixes perdidos e menor ocupação.
- **Recomendação.** Passo configurável por barbearia, mantendo a checagem de que o serviço inteiro cabe.

#### BUS-13 — Desativar ou rebaixar barbeiro não trata a agenda

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `barbershops/views.py:160-171,177-195`; `accounts/serializers.py:148-172` | Confirmado | Continua presente |

- **Descrição.** Os horários futuros continuam "agendado" ou "confirmado" com um barbeiro desativado.
- **Evidência.** Sondagem:
  - BUS-13: DELETE do barbeiro → os **20** horários futuros verificados (primeira página da lista) continuam ativos;
  - BUS-13b: rebaixamento a cliente por `/users/` → os **20** verificados continuam ativos.
- **Reprodução.** Desativar um barbeiro com horários futuros e consultar `/appointments/?barbeiro=<id>`.
- **Resultado atual.** Horários órfãos.
- **Resultado esperado.** Decisão explícita (cancelar com aviso ou reatribuir) antes de desativar.
- **Impacto.** Clientes comparecem para atendimento com quem saiu.
- **Recomendação.** Listar os afetados e exigir a decisão; testes.

#### BUS-14 — Admin não agenda pela interface

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend | `frontend/src/App.tsx:55` (rota só para cliente) | Confirmado | Continua presente |

- **Descrição.** A API permite ao admin agendar para um cliente, mas não há tela para isso, nem cliente avulso.
- **Evidência.** Sondagem complementar BUS-14-api: **201**; o painel não tem "Novo agendamento".
- **Reprodução.** Como admin, procurar a ação na interface.
- **Resultado atual.** Inexistente.
- **Resultado esperado.** Agendamento pelo balcão, com busca de cliente.
- **Impacto.** Agendamentos por telefone ou presenciais ficam fora do sistema.
- **Recomendação.** Tela de agendamento do admin reutilizando o fluxo do cliente.

#### API-01 — Sem filtros, busca e `page_size`; telas baixam todo o histórico

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | API + Frontend | `config/pagination.py:4`; `appointments/views.py:34`; `frontend/src/api/endpoints.ts:95-117`; `AdminDashboardPage.tsx:34`; `AdminClientsPage.tsx:40` | Confirmado | Continua presente |

- **Descrição.**
  - A paginação é fixa em 20 itens.
  - `search`, `ordering`, filtro por período e `tipo_perfil` não existem.
  - Painel, Agendamentos e Clientes percorrem todas as páginas de agendamentos, em sequência, e filtram no navegador.
- **Evidência.**
  - Sondagem API-01: `page_size=100` → 20 itens; `search`, `tipo_perfil` e `ordering` sem efeito.
  - Build de produção (`navegador/navegador-testes-dirigidos.json`): **25 requisições por carga, 22 delas para `/appointments/`**, com 419 agendamentos e cerca de 3,2 s locais.
  - O backend é eficiente (2 consultas por página); o gargalo é o número de requisições.
- **Reprodução.** Abrir o painel com o histórico de teste e contar as chamadas.
- **Resultado atual.** Tempo e tráfego crescem linearmente com o histórico.
- **Resultado esperado.** Número fixo de requisições; filtros e agregações no servidor.
- **Impacto.** Com alguns milhares de agendamentos, painel e listas ficam lentos.
- **Recomendação.** `SearchFilter`, `OrderingFilter`, filtros `data_inicio`/`data_fim` e `tipo_perfil`, `page_size_query_param` com máximo, endpoint de métricas para o painel e paginação no servidor.

#### FE-01 — Sem error boundary

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend | `frontend/src/App.tsx`; `frontend/src/components/AppLayout.tsx` | Confirmado (código) | Continua presente |

- **Descrição.** Não há fronteira de erro: uma exceção de renderização desmonta toda a interface.
- **Evidência.** Nenhuma ocorrência de `ErrorBoundary` ou `componentDidCatch` em `frontend/src`.
- **Reprodução.** Forçar uma exceção numa tela em modo de desenvolvimento.
- **Resultado atual.** Página em branco.
- **Resultado esperado.** Mensagem com "Recarregar", com menu e navegação preservados.
- **Impacto.** Um dado inesperado derruba a aplicação inteira.
- **Recomendação.** Error boundary no layout e por rota, com registro do erro (OBS-01).

#### FE-02 — Nenhum teste de frontend

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend / Testes | `frontend/package.json` (sem `test`) | Confirmado | Continua presente |

- **Descrição.** Não há testes unitários, de componente nem de ponta a ponta. A verificação desta auditoria usou scripts externos (`scripts/*.mjs`).
- **Evidência.** Nenhum `*.test.*` ou `*.spec.*`; sem script `test`.
- **Reprodução.** `npm test` não existe.
- **Resultado atual.** Regressões só são percebidas manualmente: a FE-13 passou pela revisão do redesign.
- **Resultado esperado.** Testes dos fluxos críticos no CI.
- **Impacto.** Regressões silenciosas.
- **Recomendação.** Vitest + Testing Library para `format.ts`, `status.ts`, ações de status e agendamento; Playwright para login, agendar, reagendar e cancelar e para as ações do admin. Os scripts desta auditoria servem de ponto de partida.

#### TEST-01 — Regras quebradas sem teste de regressão

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Testes | `*/test*.py` | Confirmado | **Parcialmente resolvido** |

- **Descrição.**
  - **Melhorou:** +88 testes, com regressão para SEC-01, SEC-02, BUS-01 (incluindo concorrência), BUS-02 e BUS-07.
  - **Continua sem teste:** BUS-03, BUS-04, BUS-05, BUS-10, BUS-12, BUS-15, BUS-16, BUS-17, AUTH-02, SEC-03 e a **confirmação da recuperação de senha**, que não tem nenhum teste funcional.
- **Evidência.** Suíte verde (327) com as sondagens falhando nesses pontos; `testes/cobertura-backend.txt` (linhas 427-449 de `accounts/serializers.py` sem cobertura).
- **Reprodução.** Rodar a suíte e depois as requisições das sondagens.
- **Resultado atual.** A suíte passa com as regras quebradas.
- **Resultado esperado.** Cada bug confirmado com um teste que falhe antes da correção.
- **Impacto.** Falsa sensação de segurança; risco de regressão.
- **Recomendação.** Escrever primeiro o teste de cada item corrigido.

#### OBS-01 — Sem logs, monitoramento, trilha de auditoria e health check

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Infra | `config/settings.py` (sem `LOGGING`); `config/urls.py` | Confirmado (código) | Continua presente |

- **Descrição.** Faltam:
  - configuração de logging e rastreamento de erros;
  - endpoint de saúde;
  - registro de quem confirmou, cancelou ou alterou um agendamento.
- **Evidência.** Busca em settings e URLs.
- **Reprodução.** Provocar um erro 500 e procurar o registro; consultar um cancelamento e procurar autor e data.
- **Resultado atual.** Inexistentes.
- **Resultado esperado.** Logs estruturados, Sentry ou similar, `/health/` e histórico de status.
- **Impacto.** Erros passam despercebidos; não há como resolver disputas ("quem cancelou?").
- **Recomendação.** `LOGGING`, integração de erros por variável de ambiente, `/health/` e tabela de histórico de agendamento.

#### OPS-01 — Sem infraestrutura de implantação

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Infra | Raiz; `docker-compose.yml`; `config/urls.py:40` | Confirmado | Continua presente |

- **Descrição.** Faltam:
  - Dockerfile e CI;
  - serviço de estáticos e mídia em produção (a mídia só é servida com `DEBUG`);
  - rotina `flushexpiredtokens`;
  - backup documentado.
- **Evidência.** Nenhum Dockerfile, `.github`, Procfile, Makefile, whitenoise ou rotina.
- **Reprodução.** Subir com `DEBUG=False`: o Django Admin fica sem CSS e a mídia retorna 404.
- **Resultado atual.** Implantação manual.
- **Resultado esperado.** Procedimento reproduzível com CI.
- **Impacto.** Erro humano e regressões sem verificação.
- **Recomendação.** Dockerfile multi-stage, CI (testes, lint, `tsc`, build, `pip-audit`, `npm audit`), whitenoise ou nginx, armazenamento de mídia e rotinas.

#### DOC-01 — Documentação da API contradiz o comportamento

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Documentação | `docs/arquitetura/DOCUMENTACAO_API.md:77-99,126,142,399` | Confirmado | Continua presente |

- **Descrição.** O documento diverge do comportamento em vários pontos:

  | Documento diz | Comportamento real |
  |---|---|
  | Access de 60 min | 15 min |
  | Refresh no corpo da requisição | Só em cookie |
  | Logout responde 205 | 204 |
  | `DELETE /users/{id}/` remove o usuário | Desativa a conta |
  | Perfil de barbeiro criado depois, em `POST /barbers/` | Criado junto, em `POST /users/` |
  | Recuperação e relatórios "não implementados" | Existem |

  Também faltam `revenue-report`, `exclude_appointment_id`, `?ativo=all` e o campo `cliente` obrigatório no POST.
- **Evidência.** Comparação com o código e as sondagens.
- **Reprodução.** Seguir o documento para o logout com refresh no corpo.
- **Resultado atual.** A integração pelo documento falha.
- **Resultado esperado.** Documento fiel, de preferência gerado do código.
- **Impacto.** Integrações erradas.
- **Recomendação.** OpenAPI com drf-spectacular, ou revisão contra os testes; trazer as correções da branch `release`.

#### REPO-01 — Virtualenv versionado

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Repositório | `venv312/` | Confirmado | Continua presente |

- **Descrição.** O `venv312/` versionado responde por **4.875 dos 5.112 arquivos** versionados, inclusive binários Linux.
- **Evidência.** `repositorio/repositorio.txt`.
- **Reprodução.** `git ls-files | grep -c '^venv312/'`.
- **Resultado atual.** 4.875.
- **Resultado esperado.** 0.
- **Impacto.** Repositório pesado e não portável.
- **Recomendação.** `git rm -r --cached venv312` num commit dedicado.

#### SA-01 — Sem painel de Super Admin

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Produto | Branch `feature/painel-super-admin` | Confirmado | Continua presente |

- **Descrição.**
  - A operação da plataforma depende do Django Admin.
  - No frontend, o superusuário cai no onboarding de dono.
  - A branch dedicada não tem commits próprios.
- **Evidência.** `git rev-list` (0 commits à frente); superusuário sem barbearia → `/onboarding`.
- **Reprodução.** Entrar como superusuário no frontend.
- **Resultado atual.** Sem tela da plataforma.
- **Resultado esperado.** Listar, suspender e reativar barbearias e ver métricas, com as ações registradas.
- **Impacto.** Suporte e suspensão só por acesso direto aos dados.
- **Recomendação.** Definir o escopo e implementar endpoints restritos ao staff e uma área no frontend.

#### SAAS-01 — Sem notificações, LGPD e cobrança

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Produto | — | Confirmado | Continua presente |

- **Descrição.** Faltam:
  - confirmação e lembrete de agendamento;
  - consentimento, exportação e anonimização de dados (hoje "excluir" só desativa e mantém tudo);
  - planos e cobrança.
- **Evidência.** Ausência de models, endpoints e telas.
- **Reprodução.** —
- **Resultado atual.** Inexistentes.
- **Resultado esperado.** Épicos com requisitos próprios.
- **Impacto.** Impede a comercialização e expõe a riscos legais.
- **Recomendação.** Implementar, nesta ordem: notificações (depende de AUTH-01) → LGPD → planos (depende de SA-01 e BUS-02).

---

### 13.4 Problemas P3 — Baixo (35)

#### FE-13 — "Agendar" após reservar continua mostrando "Horário reservado"

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/pages/AppointmentCreatePage.tsx:67,106`; `frontend/src/components/AppLayout.tsx:235` | Confirmado | **Novo — regressão do redesign** |

- **Descrição.**
  - O redesign trocou o "toast + ir para Meus agendamentos" pela tela "Horário reservado", guardada no estado `booked`.
  - A rota continua `/appointments/new` e o layout só remonta a tela quando o caminho muda.
  - Por isso, clicar em "Agendar" (aba inferior ou menu) **mantém a confirmação** em vez de abrir um novo agendamento.
- **Evidência.** `navegador/navegador-novo-agendamento-apos-confirmacao.json`:
  - após confirmar: "Horário reservado";
  - após clicar na aba "Agendar": **"Horário reservado"**;
  - só depois de sair e voltar: "Agendar horário".
  - Captura `fe_reagendar_novamente_mantem_confirmacao.png`.
- **Reprodução.** Como cliente, concluir um agendamento e tocar em "Agendar" na barra inferior.
- **Resultado atual.** A mesma tela de confirmação.
- **Resultado esperado.** Um novo fluxo de agendamento.
- **Impacto.** Confunde quem quer marcar outro horário; o contorno é ir a outra tela.
- **Recomendação.** Limpar `booked` quando a navegação ocorrer (por exemplo, usando `location.key` como `key` do layout ou observando a localização), ou navegar para uma rota própria de confirmação.

#### FE-14 — Barbearia desativada e dia da semana ignorados no status "Aberta"

> **Rodada 2 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 19](#19-rodada-2--13112026-fe-14-fe-21-e-fe-22-somente-frontend). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/components/AppLayout.tsx:296-310`; `frontend/src/utils/shop.ts:13` | Confirmado | **Novo** |

- **Descrição.** O resumo lateral calcula "Aberta até HH:MM" só pelo horário. Ignora o campo `ativo` da barbearia e o dia da semana. Nenhuma tela usa `barbershop.ativo`.
- **Evidência.** `navegador/navegador-testes-dirigidos.json`: com a barbearia desativada, `adminVeAviso=false` e lateral "**Aberta até 19:00**". Só ao clicar em "Confirmar" aparece o toast do backend (`barbearia_desativada_painel_admin.png`).
- **Reprodução.** Desativar a barbearia pela plataforma e abrir o painel.
- **Resultado atual.** A barbearia aparece "Aberta".
- **Resultado esperado.** Faixa de aviso "Barbearia desativada" e status coerente.
- **Impacto.** O admin descobre a desativação por tentativa e erro.
- **Recomendação.** Ler `ativo` no `BarbershopContext` e exibir um aviso global; incluir os dias de funcionamento quando BUS-06 for resolvido.

#### FE-03 — Falha de recarga sem aviso

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/hooks/useAsyncData.ts`; telas com `error && !data` (por exemplo, `AdminAppointmentsPage.tsx:154`) | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** As telas só mostram erro quando não há dados. Uma recarga que falha com dados na tela não avisa nada.
- **Evidência.** API derrubada e clique em "Atualizar" → nenhum texto novo nem mensagem (`mensagemDeErroVisivel=false`; `fe03_recarga_falhou_sem_aviso.png`).
- **Reprodução.** Abrir "Agendamentos", parar a API e clicar em "Atualizar".
- **Resultado atual.** Dados antigos, sem indicação.
- **Resultado esperado.** "Não foi possível atualizar; mostrando dados de HH:MM".
- **Impacto.** Decisões tomadas com dados desatualizados.
- **Recomendação.** Exibir toast ou faixa quando houver `error` com dados presentes.

#### FE-15 — Requisições sem tempo limite

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/api/client.ts:10-14` | Confirmado | **Novo** |

- **Descrição.** O cliente axios não define `timeout`. Com a API travada, sem cair, as telas ficam carregando indefinidamente.
- **Evidência.** API pausada (`SIGSTOP`): "Atualizar" desabilitado e barra de progresso sem fim (`admin_desktop_recarga_com_api_pausada.png`).
- **Reprodução.** Pausar o processo da API e recarregar uma lista.
- **Resultado atual.** Espera sem limite.
- **Resultado esperado.** Erro após um prazo (por exemplo, 15 s), com "Tentar novamente".
- **Impacto.** Interface aparentemente congelada.
- **Recomendação.** `timeout` no `axios.create` e tratamento de `ECONNABORTED` em `errorMessage`.

#### FE-16 — "1.000" no preço vira R$ 1,00

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/utils/format.ts:171-178`; `AdminServicesPage.tsx:23,88` | Confirmado (função reproduzida isoladamente) | **Novo** |

- **Descrição.** Sem vírgula, o ponto é tratado como separador decimal, então o ponto de milhar brasileiro é lido errado.
- **Evidência.** `"1.250"` → `1.25`; `"1.000"` → `1.00`; `"1.250,00"` → `1250.00`, correto.
- **Reprodução.** Cadastrar um serviço com preço "1.000".
- **Resultado atual.** Gravado como R$ 1,00, sem aviso.
- **Resultado esperado.** R$ 1.000,00, ou um pedido de confirmação quando a entrada for ambígua.
- **Impacto.** Preço errado entra no histórico financeiro. É raro em barbearias, mas silencioso.
- **Recomendação.** Tratar `\d{1,3}(\.\d{3})+` sem vírgula como milhar; mostrar o valor interpretado ao lado do campo.

#### FE-04 — Contador "a confirmar" inclui vencidos

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend / Produto | `frontend/src/components/AppLayout.tsx:316-346` | Confirmado | **Parcialmente resolvido** |

- **Descrição.** O rótulo agora diz "a confirmar no total" ("em todas as datas"), mas a contagem continua incluindo horários que já passaram.
- **Evidência.** Painel com "**40 a confirmar no total**", dos quais 22 vencidos (`admin_desktop_painel_completo.png`, sondagem BUS-08).
- **Reprodução.** Ter horários passados com status "agendado".
- **Resultado atual.** Contados como pendentes.
- **Resultado esperado.** Só futuros; vencidos em indicador separado.
- **Impacto.** Número inflado.
- **Recomendação.** Filtro de data na API (API-01) e status de desfecho (BUS-08).

#### FE-17 — Contratos de API e tipos divergentes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Integração | `frontend/src/types/index.ts:61`; `MyAppointmentsPage.tsx:114`; `frontend/src/api/endpoints.ts:71,114-117`; `appointments/serializers.py:31-36` | Confirmado | **Novo** |

- **Descrição.**
  - O tipo `Appointment.barbeiro_especialidade` não existe na API: é sempre `undefined`, e o trecho que o exibe nunca aparece.
  - `userApi.list({tipo_perfil})` envia um filtro que a API ignora.
  - A API exige `cliente` no POST mesmo quando quem agenda é o próprio cliente, e depois sobrescreve o valor. O contrato não está documentado.
- **Evidência.** CTR-02: POST sem `cliente` → 400 "Este campo é obrigatório"; leitura do serializer e dos tipos.
- **Reprodução.** `POST /appointments/` como cliente sem o campo `cliente`.
- **Resultado atual.** 400; o frontend contorna enviando `user.id`.
- **Resultado esperado.** Tipos gerados a partir do esquema da API; `cliente` opcional e ignorado para clientes.
- **Impacto.** Erros de integração em novos clientes da API; código que nunca executa.
- **Recomendação.** Esquema OpenAPI (DOC-01) com tipos gerados; `cliente` como `required=False` e preenchido em `perform_create`.

#### FE-18 — Textos que prometem o que o sistema não faz

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `AppointmentCreatePage.tsx:248,308` | Confirmado | **Novo** |

- **Descrição.**
  - "O preço e a duração ficam registrados no agendamento": a duração não é registrada (BUS-09).
  - O alerta da etapa de horário sempre começa com "Esse horário não está mais disponível.", mesmo quando o erro é outro (barbearia desativada, barbeiro inativo) e o usuário volta a essa etapa.
- **Evidência.** Leitura do código e a sondagem BUS-09.
- **Reprodução.** Comparar o texto com o comportamento descrito em BUS-09.
- **Resultado atual.** Promessas imprecisas.
- **Resultado esperado.** Textos fiéis ao que o sistema faz.
- **Impacto.** Expectativa errada do usuário.
- **Recomendação.** Ajustar os textos ou corrigir BUS-09; usar o título do alerta só para erros de conflito (`data_hora`).

#### FE-19 — Links de texto pequenos para toque nas telas públicas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend / Acessibilidade | `LoginPage.tsx`, `RegisterPage.tsx`, `PasswordReset*Page.tsx`, `AuthLayout.tsx` | Confirmado | **Novo** |

- **Descrição.** No celular, links como "Criar conta" (73×16 px), "Entrar" (41×16), "Voltar para o login" (120×16), "Esqueci minha senha" e "Conheça o BarberPro" (22 px de altura) ficam abaixo de 24 px de altura. Os contatos clicáveis da página inicial do cliente têm 22 px.
- **Evidência.** `navegador/navegador-resultados.json` (`smallTargets` nas telas públicas e na inicial do cliente). Os botões e controles do app têm todos ≥ 24 px.
- **Reprodução.** Abrir `/login` com 390 px de largura e medir.
- **Resultado atual.** Alvos estreitos.
- **Resultado esperado.** Altura de toque ≥ 24 px (WCAG 2.5.8), de preferência 44 px.
- **Impacto.** Toques errados em telas pequenas. Links dentro de frases têm exceção na norma.
- **Recomendação.** `padding-block` e `display: inline-block` nos links isolados.

#### FE-20 — Filtro de status cortado e busca truncada no celular

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend (visual) | `AdminAppointmentsPage.tsx:117`; `ui.module.css` (controle segmentado) | Confirmado | **Novo** |

- **Descrição.** Com 390 px, o controle segmentado de status corta "Confi…" sem sinal de rolagem horizontal, e o placeholder da busca aparece truncado ("…ou barbei").
- **Evidência.** `admin_celular_admin_appointments.png`.
- **Reprodução.** Abrir Agendamentos (admin) com 390 px.
- **Resultado atual.** O último filtro fica oculto.
- **Resultado esperado.** Indicação de rolagem (degradê ou seta) ou quebra em duas linhas; placeholder curto.
- **Impacto.** Os filtros "Realizado" e "Cancelado" ficam menos visíveis.
- **Recomendação.** Máscara de degradê nas bordas ou `flex-wrap`; placeholder "Buscar".

#### FE-05 — Fuso horário fixo no frontend

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Integração | `frontend/src/utils/format.ts:9` | Confirmado (código) | Continua presente |

- **Descrição.** `SHOP_TZ = 'America/Sao_Paulo'` está fixo no código; o backend usa `TIME_ZONE`.
- **Evidência.** Código.
- **Reprodução.** Alterar `TIME_ZONE` no backend.
- **Resultado atual.** A interface continua no horário de Brasília.
- **Resultado esperado.** Fuso vindo da API, por barbearia.
- **Impacto.** Divergência se a barbearia estiver em outro fuso.
- **Recomendação.** Expor o fuso em `/barbershops/` e usá-lo.

#### FE-06 — Sem página 404

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/App.tsx:65` | Confirmado | Continua presente |

- **Descrição.** Rota inexistente redireciona silenciosamente.
- **Evidência.** `/pagina-que-nao-existe` (deslogado) → `/login`; logado → início do perfil.
- **Reprodução.** Acessar uma URL inválida.
- **Resultado atual.** Redireciona sem aviso.
- **Resultado esperado.** Página "não encontrada".
- **Impacto.** Links quebrados passam despercebidos.
- **Recomendação.** Rota `*` com página 404 na identidade visual.

#### FE-07 — Código morto

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/components/Icons.tsx`; `api/endpoints.ts:90,139-147`; `utils/format.ts:24,132`; `assets/brand/index.ts` | Confirmado | Continua presente (ampliado) |

- **Descrição.** Sem uso:
  - **17 ícones:** Razor, Chair, Minus, Filter, Trash, Settings, Key, Lock, Bell, XCircle, AlertTriangle, TrendingUp, Receipt, Analytics, Star, Badge, Building;
  - **funções:** `getTotalServices`, `getTotalBarbers`, `formatDateTime`, `isPast` e `appointmentApi.revenueReport` (a interface não usa o relatório da API);
  - **logos:** o objeto `logo` importa as variantes "emblema", que entram no build (cerca de 30 kB de SVG) sem uso.
- **Evidência.** Busca de referências.
- **Reprodução.** Buscar cada símbolo em `frontend/src`.
- **Resultado atual.** Código sem uso.
- **Resultado esperado.** Nenhuma exportação sem uso.
- **Impacto.** Ruído e bytes extras.
- **Recomendação.** Remover; adotar `knip` ou `ts-prune`.

#### FE-09 — Sem tela de logo; barbeiro não reagenda

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `AdminBarbershopPage.tsx`; `BarberAgendaPage.tsx` | Confirmado | Continua presente |

- **Descrição.** A API aceita a logo e o reagendamento pelo barbeiro, mas as telas não oferecem essas ações.
- **Evidência.** Nenhuma ocorrência de "logo" ou "Reagendar" nessas telas.
- **Reprodução.** Abrir "Dados da barbearia" e "Minha agenda".
- **Resultado atual.** Funcionalidades inacessíveis.
- **Resultado esperado.** Upload com prévia (depois de SEC-09); decisão sobre o reagendamento pelo barbeiro.
- **Impacto.** Funções da API sem uso.
- **Recomendação.** Implementar as telas ou declará-las fora do escopo.

#### FE-11 — Painel e relatório da API calculam o faturamento de formas diferentes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Integração | `AdminDashboardPage.tsx:47-118`; `appointments/views.py:272-383` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** O painel soma no navegador os últimos **30 dias**, de hoje−29 até hoje. O `revenue-report` usa **31 dias**, de hoje−30 até hoje, e agrupa o dia em UTC.
- **Evidência.** `api/fe11-duas-fontes-de-faturamento.txt`: painel **R$ 14.645** (293 atendimentos) contra API **R$ 15.215** (305): **R$ 570** de diferença.
- **Reprodução.** Comparar o "Faturamento, 30 dias" do painel com `GET /appointments/revenue-report/`.
- **Resultado atual.** Números diferentes para o "mesmo" período.
- **Resultado esperado.** Uma única fonte, com período idêntico.
- **Impacto.** Desconfiança nos números se a API for exposta a outro consumidor.
- **Recomendação.** Endpoint de métricas no backend (no fuso local), consumido pelo painel.

#### API-02 — Relatório agrupa o dia em UTC

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/views.py:351-356` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** `qs.extra(select={'date': 'DATE(data_hora)'})` agrupa pelo dia em UTC. O filtro do período usa o dia local, então o relatório chega a listar uma data fora do período pedido.
- **Evidência.** Sondagem API-02: relatório com `start=end=2026-11-12` devolve `daily` com **2026-11-13** (o atendimento de 12/11 às 22:30).
- **Reprodução.** Um realizado depois das 21:00 locais; `revenue-report?start=<dia>&end=<dia>`.
- **Resultado atual.** Dia seguinte.
- **Resultado esperado.** Dia local.
- **Impacto.** Faturamento diário deslocado.
- **Recomendação.** `TruncDate('data_hora', tzinfo=ZoneInfo(TIME_ZONE))` com `values().annotate()`, sem `.extra()`; teste noturno.

#### BUS-10 — Horários livres para datas passadas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/views.py:266` | Confirmado | Continua presente |

- **Descrição.** Os horários já passados só são descartados quando a data consultada é hoje.
- **Evidência.** Sondagem BUS-10: ontem → **14 horários**.
- **Reprodução.** `available-slots?data=<ontem>`.
- **Resultado atual.** Lista preenchida.
- **Resultado esperado.** Lista vazia ou 400.
- **Impacto.** Inconsistência da API; o frontend não oferece datas passadas.
- **Recomendação.** Retornar vazio para `data < hoje`; teste.

#### BUS-18 — Validações de cadastro fracas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `barbershops/models.py:20`; `services/models.py:17-23`; `services/serializers.py:13-21`; `appointments/models.py:86` | Confirmado | **Novo** |

- **Descrição.** A API aceita:
  - telefone com qualquer texto;
  - serviços com nome duplicado no mesmo tenant;
  - duração de 100.000 min e preço de 999.999,99;
  - observações de agendamento sem limite de tamanho (o frontend limita a 500).
- **Evidência.** Sondagem complementar: VAL-01, VAL-02 e VAL-03 → **200, 201 e 201**.
- **Reprodução.** As requisições de VAL-01 a VAL-03.
- **Resultado atual.** Dados inválidos aceitos.
- **Resultado esperado.** 400 com mensagens.
- **Impacto.** Dados ruins no cadastro; serviços que nunca cabem na agenda.
- **Recomendação.** Validadores de formato e de faixa; unicidade de nome por barbearia; `max_length` nas observações.

#### BUS-19 — Sem segundo admin nem transferência de titularidade

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend / Produto | `accounts/serializers.py:76-84,235-240`; `accounts/admin_integrity.py` | Confirmado (código) | **Novo** (efeito colateral do BUS-01) |

- **Descrição.**
  - Nenhum endpoint cria um admin ou promove alguém a admin.
  - Com a regra do BUS-01, o único admin não pode ser rebaixado nem desativado.
  - A titularidade só muda pelo Django Admin, com ação do superusuário.
- **Evidência.** `validate_tipo_perfil` recusa `admin` na criação e na edição; testes `test_recuperacao_*` usam o Django Admin.
- **Reprodução.** Tentar criar ou promover um admin pela API → 400.
- **Resultado atual.** Uma barbearia tem sempre um único admin, insubstituível pela aplicação.
- **Resultado esperado.** Convite de coadministrador e transferência auditada.
- **Impacto.** Venda da barbearia, saída do dono ou LGPD exigem suporte manual.
- **Recomendação.** Fluxo de convite de admin com confirmação e registro.

#### SEC-06 — Chave antiga no histórico do git

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Repositório | `core/settings.py` no commit `3f46df2` | Confirmado | Continua presente |

- **Descrição.** Uma `SECRET_KEY` fixa permanece no histórico. O repositório tem remoto no GitHub (`origin`); a visibilidade não foi verificada.
- **Evidência.** `git grep -c` no commit (1 ocorrência; valor não exibido).
- **Reprodução.** `git log --all -- core/settings.py`.
- **Resultado atual.** Chave no histórico.
- **Resultado esperado.** Chave comprovadamente não usada, ou histórico limpo.
- **Impacto.** Nenhum, se a chave nunca foi nem for usada; a chave atual é outra (SEC-01).
- **Recomendação.** Declarar que a chave antiga não é usada; se o repositório for público, avaliar `git filter-repo`.

#### SEC-08 — Sem verificação de e-mail no cadastro

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `accounts/views.py:119-130`; `barbershops/views.py` (`perform_create`) | Confirmado (código) | Continua presente |

- **Descrição.** Qualquer pessoa cria uma conta e uma barbearia sem confirmar o e-mail.
- **Evidência.** Código; sondagem PROD-01 (conta criada e já ativa).
- **Reprodução.** Cadastrar com um e-mail inexistente.
- **Resultado atual.** Entra direto.
- **Resultado esperado.** Confirmação por link antes do onboarding.
- **Impacto.** Tenants de spam; contas inacessíveis por e-mail digitado errado.
- **Recomendação.** Verificação por token (depende de AUTH-01).

#### SEC-10 — Oráculo de existência de IDs

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/serializers.py:82-97`; `appointments/views.py:203-213`; `config/permissions.py` (`IsSelfOrAdmin`) | Confirmado | **Novo** |

- **Descrição.**
  - Para IDs de outra barbearia, a API responde "Este barbeiro não pertence à sua barbearia"; para IDs inexistentes, "Pk inválido".
  - `exclude_appointment_id` distingue "não pertence" de "não encontrado".
  - Um cliente que consulta outro cliente por id recebe 403, que revela a existência, em vez de 404.
- **Evidência.** Sondagem ISO-22, ISO-23 e PER-13.
- **Reprodução.** POST de agendamento com `barbeiro` de outra barbearia e com um ID inexistente; comparar as mensagens.
- **Resultado atual.** Mensagens distintas.
- **Resultado esperado.** A mesma resposta 400/404 genérica.
- **Impacto.** Permite mapear IDs de outras barbearias. Os dados não vazam: o isolamento continua.
- **Recomendação.** Querysets dos campos relacionados filtrados pelo tenant; 404 para objetos alheios.

#### SEC-11 — Configurações de desenvolvimento inseguras se reaproveitadas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Configuração | `.env` local (`DEBUG=True`, `CORS_ALLOWED_ORIGINS` com `localhost:3000`); `config/settings.py:127`; `config/test_postgres_settings.py:12`; `docker-compose.yml:10` | Confirmado | **Novo** |

- **Descrição.**
  - Com o `.env` atual, rotas inexistentes exibem a página técnica do Django com a lista de URLs.
  - O CORS libera uma origem que não é usada.
  - Usuário e senha padrão de desenvolvimento do banco estão escritos no código e no compose (valores não reproduzidos aqui).
- **Evidência.** Sondagem SES-12 ("Django tried these URL patterns") e SES-08.
- **Reprodução.** `GET /api/v1/rota-inexistente/` com o `.env` atual.
- **Resultado atual.** Página de debug.
- **Resultado esperado.** Em qualquer ambiente acessível por terceiros, `DEBUG=False`, sem credenciais padrão e CORS mínimo.
- **Impacto.** Baixo em uso local; alto se esse `.env` ou essas credenciais forem usados num servidor.
- **Recomendação.** Remover os valores padrão com credenciais (exigir `DATABASE_URL`); revisar `CORS_ALLOWED_ORIGINS`; checklist de implantação.

#### DEP-02 — Frontend com 14 vulnerabilidades conhecidas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Dependências | `frontend/package-lock.json` | Confirmado | **Novo** |

- **Descrição.**
  - São 7 vulnerabilidades altas e 7 moderadas.
  - Em tempo de execução: axios 1.19.0 (12 avisos, a maioria nos adaptadores de Node) e zod 3.25 (consumo de memória).
  - O restante está em ferramentas de build e de desenvolvimento: vite 6.4.3, brace-expansion, js-yaml, source-map-js, minimatch, typescript-eslint.
- **Evidência.** `dependencias/frontend-npm-audit-outdated.txt`.
- **Reprodução.** `npm audit`.
- **Resultado atual.** 14 avisos; correção disponível por `npm audit fix` (o zod exige versão maior).
- **Resultado esperado.** 0 altas.
- **Impacto.** Baixo no navegador; o servidor de desenvolvimento do Vite tem avisos de leitura de arquivos.
- **Recomendação.** `npm audit fix` e atualização de axios e vite; avaliar zod 4 com testes.

#### DATA-02 — Preços históricos antigos estimados

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Banco | `appointments/migrations/0008_populate_preco_historico.py` | Confirmado | Continua presente |

- **Descrição.** Agendamentos anteriores à 0007 receberam o preço vigente na migração, o que a própria migração documenta como estimativa.
- **Evidência.** Cabeçalho da migração.
- **Reprodução.** Ler o arquivo.
- **Resultado atual.** Valores estimados.
- **Resultado esperado.** Limitação declarada nos relatórios.
- **Impacto.** Relatórios antigos podem não refletir o valor cobrado.
- **Recomendação.** Documentar o período afetado.

#### DATA-03 — Divergência de collation

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Banco | Servidor PostgreSQL do host (banco do app) | Confirmado | Continua presente |

- **Descrição.** O banco foi criado com collation 2.43 e o sistema operacional fornece 2.44.
- **Evidência.** Aviso a cada conexão; `banco/integridade-banco-real-somente-leitura.txt`.
- **Reprodução.** Qualquer comando Django contra o banco do app.
- **Resultado atual.** Aviso constante.
- **Resultado esperado.** Sem aviso.
- **Impacto.** Índices de texto, como o `unique` de e-mail, podem ficar inconsistentes em casos raros.
- **Recomendação.** Com backup: `REINDEX DATABASE` e `ALTER DATABASE … REFRESH COLLATION VERSION`.

#### DB-02 — Regras de negócio sem constraints no banco

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Banco | `services/models.py`; `barbershops/models.py`; `appointments/models.py`; `accounts/models.py` | Confirmado | **Novo** |

- **Descrição.** O banco não impede:
  - duração ≤ 0;
  - preço negativo;
  - fechamento ≤ abertura;
  - status fora da lista;
  - e-mail duplicado por maiúsculas;
  - sobreposição de agendamentos do mesmo barbeiro.

  Toda a integridade depende da aplicação, e caminhos fora da API (Django Admin, shell, SQL) a contornam, como mostra o SEC-07.
- **Evidência.** Migrações e models: só PK, FK, `unique(email)` e `OneToOne`.
- **Reprodução.** Inserir um serviço com `duracao=0` pelo ORM (SEC-07).
- **Resultado atual.** Aceito.
- **Resultado esperado.** `CheckConstraint` e `UniqueConstraint(Lower('email'))`; opcionalmente uma constraint de exclusão (`btree_gist`) por barbeiro e intervalo.
- **Impacto.** Dados inválidos possíveis fora da API.
- **Recomendação.** Adicionar as constraints com migração, depois de checar os dados existentes.

#### MAINT-01 — Componentes grandes, estilos inline, duplicação e código morto no backend

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Código | `AppointmentCreatePage.tsx` (508 linhas), `AppLayout.tsx` (424), `AdminDashboardPage.tsx` (397), `ui.module.css` (1.096); `barbershops/views.py:83-135` e `services/views.py:30-75`; `appointments/models.py:370-381`; `config/permissions.py:39` | Confirmado | **Novo** |

- **Descrição.**
  - Componentes com várias responsabilidades.
  - 45 usos de `style={{…}}` e algumas cores literais fora de `design-tokens.css` (por exemplo, `ui.module.css:897-898`).
  - Lógica do filtro `ativo` duplicada entre os ViewSets de barbeiros e serviços.
  - Código morto: `_validar_campos_cliente_nao_autorizados` (método incompleto, nunca chamado) e `IsClientRole` (nunca usada).
  - Comentário com erro de digitação em `appointments/views.py:47`.
- **Evidência.** Contagens e buscas.
- **Reprodução.** —
- **Resultado atual.** Manutenção mais cara.
- **Resultado esperado.** Componentes menores, tokens em vez de literais, filtro compartilhado.
- **Impacto.** Baixo, mas acumulativo.
- **Recomendação.** Extrair os passos do agendamento e as seções do painel; mixin para o filtro `ativo`; remover o código morto.

#### DOC-02 — README com instruções incorretas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Documentação | `README.md` | Confirmado | Continua presente (ampliado) |

- **Descrição.** O README diz que:
  - `python manage.py test` usa SQLite em memória, mas usa o banco do `.env`, criando um banco de teste no servidor;
  - existe um proxy do Vite para a porta 8000, mas `vite.config.ts` não tem proxy;
  - o banco roda "via Docker", mas o app usa o PostgreSQL do host (DB-01).
- **Evidência.** `README.md`; `vite.config.ts`; `config/test_settings.py`.
- **Reprodução.** Seguir o README.
- **Resultado atual.** Instruções divergentes.
- **Resultado esperado.** README fiel ao ambiente.
- **Impacto.** Quem segue o README testa ou executa em outro banco.
- **Recomendação.** Reescrever as seções de execução e testes.

#### DOC-03 — Comentários obsoletos sobre o app `core`

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Documentação | `accounts/models.py:7`; `config/settings.py:72` | Confirmado | Continua presente |

- **Descrição.** Comentários citam o antigo app `core`.
- **Evidência.** Busca.
- **Reprodução.** `grep -n core accounts/models.py config/settings.py`.
- **Resultado atual.** Referências obsoletas.
- **Resultado esperado.** `config.mixins` e a lista atual de apps.
- **Impacto.** Confusão.
- **Recomendação.** Atualizar os comentários.

#### DOC-04 — Índice de `docs/` e comentários desatualizados

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Documentação | `docs/README.md`; `config/settings.py:218-219` | Confirmado | **Novo** |

- **Descrição.**
  - O índice de `docs/` aponta `RELATORIO_ENTREGA_FINAL.md` como documento principal e não cita a auditoria oficial nem as pastas de evidências.
  - O comentário do `settings.py` afirma que o access token é mantido só em memória (SEC-04).
- **Evidência.** Leitura dos arquivos.
- **Reprodução.** —
- **Resultado atual.** Índice e comentário desatualizados.
- **Resultado esperado.** Índice com a auditoria oficial e o histórico; comentário fiel.
- **Impacto.** Avaliadores encontram primeiro um relatório antigo.
- **Recomendação.** Atualizar `docs/README.md` e o comentário.

#### REPO-02 — Arquivos soltos e pastas fora do `.gitignore`

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Repositório | Raiz; `.gitignore` | Confirmado | Continua presente (ampliado) |

- **Descrição.**
  - Continuam na raiz: `gerar_zip.py`, `db.sqlite3`, `test.db` vazio, `outputs/`, `work/`, 21 rascunhos em `docs/auditorias/historico/`.
  - Novos e **fora do `.gitignore`**:
    - `.codex/` (hooks de ferramenta);
    - `.impeccable/`;
    - `references/`, com cópias de HTML de sites de terceiros (direitos autorais);
    - `media/` (uploads) e `staticfiles/`.
- **Evidência.** `repositorio/repositorio.txt`; `.gitignore`.
- **Reprodução.** `git status`.
- **Resultado atual.** Risco de versionar material de terceiros e uploads.
- **Resultado esperado.** Raiz limpa e `.gitignore` cobrindo as ferramentas locais.
- **Impacto.** Repositório confuso e risco legal.
- **Recomendação.** Atualizar o `.gitignore` e mover os rascunhos.

#### REPO-03 — Branches dessincronizadas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Repositório | Branches | Confirmado | Continua presente |

- **Descrição.**
  - `master` está 31 commits atrás de `desenvolvimento`.
  - `feature/painel-super-admin` está 1 atrás, sem commits próprios.
  - `release/barberpro-academica-v1` tem 1 commit próprio (`67ef6e3`).
- **Evidência.** `git rev-list --count` (`repositorio/repositorio.txt`).
- **Reprodução.** Os mesmos comandos.
- **Resultado atual.** Sem branch de referência clara.
- **Resultado esperado.** Fluxo de branches documentado.
- **Impacto.** Correções presas na `release`.
- **Recomendação.** Definir o fluxo e sincronizar.

#### TEST-02 — Cobertura não medida pelo projeto

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Testes | `requirements.txt` | Confirmado | Continua presente |

- **Descrição.** O projeto não tem `coverage`. Esta auditoria mediu 91% com a ferramenta instalada fora do projeto.
- **Evidência.** `testes/cobertura-backend.txt`.
- **Reprodução.** `coverage run manage.py test` não está disponível no ambiente do projeto.
- **Resultado atual.** Sem medição contínua.
- **Resultado esperado.** Cobertura no CI, com meta.
- **Impacto.** Lacunas como a da confirmação de senha passam despercebidas.
- **Recomendação.** `coverage` como dependência de desenvolvimento, com meta mínima no CI.

#### FE-12 — Banco real quase vazio para a demonstração

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Dados / Apresentação | Banco do app (somente leitura) | Confirmado | Continua presente |

- **Descrição.** O banco do app tem 2 barbearias, 8 usuários, 2 serviços e **2 agendamentos**.
- **Evidência.** `banco/integridade-banco-real-somente-leitura.txt`.
- **Reprodução.** Entrar como admin e abrir o painel.
- **Resultado atual.** Painel, gráficos e quadro do dia quase vazios.
- **Resultado esperado.** Tenant de demonstração com histórico real, manipulável pela aplicação.
- **Impacto.** A demonstração não mostra os indicadores. As capturas desta auditoria mostram como fica com dados.
- **Recomendação.** Comando `seed_demo` idempotente num tenant separado. `scripts/seed.py` serve de base, adaptado para não fixar senhas.

---

## 14. Problemas não verificáveis e limitações

| # | Item | Por que não foi verificado | Risco que permanece | Como verificar |
|---|---|---|---|---|
| NV-1 | Entrega real de e-mail | Não há SMTP configurado; enviar a terceiros está fora do escopo | A recuperação de senha pode falhar mesmo com o SMTP configurado | Backend de console ou Mailpit e solicitar a recuperação |
| NV-3 | Leitor de tela (NVDA, VoiceOver, TalkBack) | Indisponível no ambiente; validados axe-core, teclado e ARIA | Problemas de anúncio e ordem de leitura | Percorrer login, agendamento e painel com leitores reais |
| NV-4 | Chrome, Safari, Edge e aparelhos físicos | Só o Firefox estava disponível; tamanhos simulados | Diferenças de renderização (por exemplo, `inert`, controles de data e hora) | Repetir `scripts/audit.mjs` com Chromium e WebKit e testar em celulares reais |
| NV-6 | Visibilidade do repositório no GitHub | Exigiria consulta autenticada a serviço externo | Se for público, a chave antiga (SEC-06) e a auditoria anterior estão expostas | Conferir no GitHub |
| NV-7 | Carga e desempenho em volume real | Base de teste com 419 agendamentos; sem teste de carga | O crescimento linear (API-01) foi demonstrado, mas o limite prático não foi medido | Popular 10 mil agendamentos e medir o painel |
| NV-8 | Implantação em produção (HTTPS, proxy, `DEBUG=False`) | Não há infraestrutura de produção (OPS-01); só `check --deploy` | Comportamento real de cookies `Secure`, CSP e estáticos | Ambiente de homologação |

Limitações de método:

- Revisão manual de layout feita por amostragem de capturas, em 3 das 5 larguras.
- As métricas automáticas (rolagem, alvos de toque, erros) cobriram todas as 105 combinações.
- As telas do frontend que **não** mudaram desde a auditoria anterior foram lidas por diff e testadas no navegador, mas não relidas linha a linha: Onboarding, Register, PasswordReset, Account.
- NV-2 e NV-5 da auditoria anterior foram resolvidos como verificações nesta (seção 12.2).

---

## 15. Matriz de prioridades

Esforço estimado:

- **baixo:** até meio dia, com teste;
- **médio:** de 1 a 3 dias;
- **alto:** uma semana ou mais, ou decisão de produto.

| Severidade \ Esforço | Baixo | Médio | Alto |
|---|---|---|---|
| **P1** | BUS-15, BUS-03, BUS-04, BUS-05 | AUTH-01 | BUS-06, PROD-01 |
| **P2** | BUS-12, BUS-16, SEC-03, SEC-07, SEC-09, DATA-01, DB-01, FE-01 | BUS-02, BUS-17, AUTH-02, SEC-04, SEC-05, DEP-01, BUS-08, BUS-09, BUS-11, BUS-13, BUS-14, API-01, FE-02, TEST-01, OBS-01, DOC-01, REPO-01 | OPS-01, SA-01, SAAS-01 |
| **P3** | FE-13, FE-14, FE-03, FE-15, FE-16, FE-17, FE-18, FE-19, FE-20, FE-06, FE-07, API-02, BUS-10, SEC-10, SEC-11, DEP-02, DOC-02, DOC-03, DOC-04, REPO-02 | FE-04, FE-05, FE-09, FE-11, BUS-18, BUS-19, DATA-03, DB-02, MAINT-01, REPO-03, TEST-02, FE-12 | SEC-08, SEC-06 (se o histórico precisar ser limpo), DATA-02 (documentar) |

Leitura sugerida:

- **canto superior esquerdo:** P1 de baixo esforço, o maior ganho por hora;
- **diagonal P2 baixo:** riscos operacionais baratos;
- **coluna "alto":** decisões de produto que não cabem antes da apresentação.

---

## 16. Plano recomendado de correção

A ordem é sugestão; a decisão é do dono do projeto. Cada correção deve vir com um teste de regressão escrito antes, que falhe no código atual.

### Fase 0 — Antes da apresentação de 17/11

Alterações pequenas, de baixo risco:

| Ordem | Item | Esforço | Por que agora |
|---|---|---|---|
| 1 | DB-01 | Baixo | Garantir que a demonstração rode no banco migrado (o do `.env`) e alinhar README e compose, ou migrar o container |
| 2 | FE-12 | Baixo | Tenant de demonstração com histórico, para mostrar painel, caixa e quadro do dia |
| 3 | BUS-15 | Baixo | Status inicial sempre "agendado" |
| 4 | BUS-03 | Baixo | Reagendar volta a "agendado" |
| 5 | BUS-05 | Baixo | Validação de fechamento > abertura na API |
| 6 | BUS-04 | Baixo | Revalidar o horário na troca de serviço |
| 7 | FE-13 | Baixo | Reiniciar o fluxo de agendamento (regressão visível) |
| 8 | SEC-03 | Baixo | Ocultar o e-mail dos barbeiros para clientes |
| 9 | BUS-12 | Baixo | Unificar a regra de cancelamento e troca de cliente do barbeiro |
| 10 | TEST-01 (parcial) | Baixo | Testes dos itens 3 a 9 |

Se não houver tempo para BUS-06, **evitar demonstrar domingos** (seção 17).

### Fase 1 — Antes de qualquer uso real

| Tema | Itens |
|---|---|
| Agenda e regras | BUS-16, BUS-17, BUS-10, BUS-02 (suspensão pela plataforma), FE-14 |
| Segurança e dependências | DEP-01 (Django 5.2 LTS, Pillow), DEP-02, SEC-05 (Redis), SEC-07, SEC-09, SEC-04 (CSP), SEC-11, SEC-10 |
| Contas | AUTH-01 (e-mail), AUTH-02 |
| Dados | DATA-01, DB-02, API-02 |
| Desempenho e integração | API-01, FE-11, FE-17, FE-15, FE-03, FE-01 |
| Operação | OBS-01, OPS-01, REPO-01, REPO-02 |
| Qualidade | FE-02, TEST-01 (restante), TEST-02 |
| Documentação | DOC-01, DOC-02, DOC-04 |

### Fase 2 — Produto

PROD-01 (página pública e convite), BUS-06 (grade de funcionamento, folgas e feriados), BUS-08 (não compareceu), BUS-09 (duração histórica), BUS-11 (passo configurável), BUS-13 (agenda ao desativar), BUS-14 (agendamento pelo balcão), BUS-19 (coadministradores), SA-01, SAAS-01, SEC-08, FE-09.

### Fase 3 — Acabamento

FE-04, FE-05, FE-06, FE-07, FE-16, FE-18, FE-19, FE-20, MAINT-01, DATA-02, DATA-03, DOC-03, REPO-03, SEC-06, e os itens não verificados NV-1, NV-3, NV-4, NV-6, NV-7 e NV-8.

---

## 17. Prontidão para a demonstração

### 17.1 Conclusão

**O BarberPro está em condições de ser apresentado como protótipo acadêmico. Não está em condições de uso real nem de produção.**

A favor:

- Nenhum P0. Os dois críticos anteriores foram corrigidos e testados.
- O isolamento entre barbearias resistiu a todas as tentativas.
- As permissões principais dos três perfis valem na API, não só na interface.
- Os fluxos centrais funcionam de ponta a ponta, sem erros de console ou de API, do desktop ao celular de 360 px: login, cadastro de serviços e equipe, agendamento, reagendamento, cancelamento, confirmação, conclusão, painel e caixa.
- O redesign é consistente e acessível nas verificações automáticas.
- 327 testes passam, inclusive concorrência em PostgreSQL.

Contra:

- Sete problemas P1 de regra de negócio e de produto.
- Dependências vulneráveis.
- Ausência de infraestrutura, e-mail, observabilidade e testes de frontend.
- A demonstração depende do banco certo (DB-01) e de dados preparados (FE-12).

### 17.2 Recomendações para o roteiro da apresentação

| Fazer | Evitar (enquanto não corrigido) |
|---|---|
| Rodar no banco do `.env` (migrado) e conferir `showmigrations` antes | Subir o banco do `docker-compose` sem migrar (DB-01) |
| Usar um tenant de demonstração com histórico (FE-12) | Mostrar o painel com o banco atual: 2 agendamentos |
| Demonstrar login dos três perfis, agendamento em dia útil, confirmação pelo barbeiro, conclusão após o término, cancelamento, painel e caixa | Agendar num domingo (BUS-06) |
| Mostrar a recusa de horário ocupado e o isolamento entre barbearias | Reagendar um horário já confirmado (BUS-03) |
| Mostrar a interface no celular | Tocar em "Agendar" logo após reservar (FE-13) |
| Explicar as limitações declaradas: e-mail, cadastro de cliente, dias de funcionamento | Recuperação de senha (AUTH-01) e cadastro público como cliente (PROD-01) |

### 17.3 Respostas objetivas

- **Quantidade total de problemas:** 70 (P0 0, P1 7, P2 28, P3 35).
- **Problemas antigos resolvidos:** 5 resolvidos e verificados, 3 parcialmente.
- **Problemas antigos que continuam presentes:** 45.
- **Regressões:** nenhum problema antigo voltou. O redesign introduziu 1 regressão nova (FE-13).
- **Cinco problemas mais importantes:** BUS-15, BUS-03, BUS-06, BUS-05 e BUS-04 (seção 1).
- **Pode ser apresentado?** Sim, como protótipo acadêmico, com as precauções da tabela acima. Não está pronto para produção.

---

## 18. Acompanhamento das correções

### 18.1 Rodada 1 — 13/11/2026: integridade dos agendamentos

**Escopo autorizado:** BUS-15, BUS-03, BUS-06, BUS-05, BUS-04 e a regressão FE-13. Nenhum outro problema foi tratado. Ficaram fora, por instrução, PROD-01, AUTH-01 e todos os P2 e P3.

**Restrições cumpridas:**
- sem commit, push ou merge, na branch `desenvolvimento`;
- sem alteração de `.env`, `SECRET_KEY`, settings, dependências ou infraestrutura;
- sem migração no banco real;
- alterações já existentes (redesign e backend do dono) preservadas.

Evidências em [`docs/auditoria/evidencias-2026-11-13/rodada-1-correcoes/`](auditoria/evidencias-2026-11-13/rodada-1-correcoes/README.md).

#### Resumo

| ID | Sev. | Situação após a rodada | Prova de falha antes / correção depois |
|---|---|---|---|
| BUS-15 | P1 | ✅ **Resolvido e verificado** | 6 testes falham no código anterior; 14 de 14 passam depois |
| BUS-03 | P1 | ✅ **Resolvido e verificado** | 5 falham antes; 14 de 14 passam depois |
| BUS-06 | P1 | ◐ **Parcialmente resolvido** | 15 falham antes; 16 de 16 passam depois |
| BUS-05 | P1 | ✅ **Resolvido e verificado** | 7 falham antes; 10 de 10 passam depois |
| BUS-04 | P1 | ✅ **Resolvido e verificado** | 5 falham antes; 10 de 10 passam depois |
| FE-13 | P3 | ✅ **Resolvido e verificado** | Reproduzido na auditoria; corrigido e verificado no navegador (B6, B7, B9, B11) |

Os testes que passam nos dois estados (26 no total) protegem os fluxos legítimos que precisavam continuar funcionando: admin e barbeiro registrando horário confirmado, remarcação pelo lado da barbearia, limites exatos de horário, edição de outros campos. Detalhe por teste em `testes/antes-e-depois-por-teste.txt`.

#### BUS-15 — Cliente cria agendamento já "confirmado"

| Campo | Registro |
|---|---|
| Arquivos modificados | `appointments/serializers.py` (`validate`); `appointments/models.py` (`clean`, novo `_validar_status_inicial`) |
| Solução implementada | **Na API:** o cliente só cria horários `agendado`. Mandar outro `status` na criação (JSON ou formulário) responde **403** e não grava nada. **No modelo** (vale também para Django Admin e shell): todo registro novo nasce `agendado` ou `confirmado`, e ninguém cria um agendamento já cancelado (400). Admin e barbeiro continuam podendo registrar um horário já confirmado (por exemplo, agendamento por telefone). "Realizado" na criação continua recusado pela regra do BUS-07 |
| Testes executados | `appointments/test_status_inicial.py` (14): status `confirmado`, `cancelado` e `realizado` pelo cliente; envio por formulário; combinação com outro `cliente`; status inválido sem erro 500; fluxo normal do cliente; entrada na fila "a confirmar"; admin e barbeiro com e sem status; modelo fora da API. Sondagem HTTP `BUS-15/*` (6) |
| Resultado | 14/14 no código corrigido (6 falhavam antes). Sondagem: cliente `confirmado`, `cancelado` e `realizado` → 403; sem status → 201 `agendado`; admin `confirmado` → 201; barbeiro `cancelado` → 400. Na repetição da sondagem da auditoria, NEW-STATUS passou de 201 `confirmado` para 403 |
| Situação | **Resolvido e verificado** |

#### BUS-03 — Reagendamento pelo cliente mantém "confirmado"

| Campo | Registro |
|---|---|
| Arquivos modificados | `appointments/serializers.py` (`validate`, novo `_altera_agenda`); `appointments/models.py` (`_validar_transicao_status`); `frontend/src/pages/AppointmentCreatePage.tsx` (aviso e texto da tela final) |
| Solução implementada | **Regra na API:** quando o **cliente** muda de fato o horário, o barbeiro ou o serviço de um horário `confirmado`, o status volta a `agendado` na mesma gravação e a barbearia precisa confirmar de novo. Mandar `status: confirmado` junto não impede a volta. **No modelo:** `confirmado → agendado` só é aceito quando há remarcação; reabrir sem remarcar continua proibido. **Preservado:** remarcação feita pelo admin ou pelo barbeiro, que já são o lado da barbearia, mantém o status; editar só as observações também. **Na interface:** ao remarcar um horário confirmado, um aviso informa que ele volta a aguardar confirmação, e a tela final diz que o novo horário aguarda a barbearia |
| Testes executados | `appointments/test_remarcacao_status.py` (14): mudança de horário, barbeiro e serviço; status enviado junto; status final junto (403); preço histórico preservado; nova confirmação; só observações; reenvio dos mesmos dados; horário ainda agendado; admin e barbeiro mantendo `confirmado`; reabertura sem remarcar; modelo. Sondagem `BUS-03/*` (3). Navegador B12–B14 |
| Resultado | 14/14 (5 falhavam antes). Sondagem: cliente → `agendado`; só observações → `confirmado`; admin → `confirmado`. No navegador, o horário 401 (confirmado, qua 18/11 15:00) foi remarcado pelo cliente para qui 19/11 09:00 e ficou `agendado`; o aviso e o texto final aparecem |
| Situação | **Resolvido e verificado** |

#### BUS-06 — Domingos e dias fechados recebem agendamentos

| Campo | Registro |
|---|---|
| Arquivos modificados | **Backend:** `barbershops/models.py` (campo `dias_funcionamento`, `clean`, `abre_no_dia`); `barbershops/migrations/0006_barbershop_dias_funcionamento.py` (nova); `barbershops/serializers.py`; `appointments/models.py` (`_validar_horario_funcionamento`); `appointments/views.py` (`available_slots`). **Frontend:** `types/index.ts`, `api/endpoints.ts`, `utils/format.ts` (`isoWeekday`), `utils/shop.ts`, `pages/AdminBarbershopPage.tsx`, `pages/AppointmentCreatePage.tsx`, `pages/HomePage.tsx`, `styles/client.module.css`, `styles/settings.module.css` |
| Solução implementada | **Configuração:** o projeto não tinha nenhuma configuração de dias, então foi criado o mínimo necessário, `Barbershop.dias_funcionamento`: lista de dias ISO, 1 = segunda … 7 = domingo. Ela é validada (pelo menos um dia, valores de 1 a 7, sem repetição) e editável só pelo admin. **Padrão:** todos os dias. Assim nenhuma barbearia existente perde dias, e domingos não são bloqueados de forma indiscriminada: cada barbearia escolhe os seus em "Dados da barbearia". **API:** dia fechado devolve lista de horários vazia, e criação ou remarcação para esse dia recebe 400 ("A barbearia não abre aos domingos"), pelos três perfis. O dia da semana é o do horário local da barbearia, não o de UTC. Fechar um dia **não** trava horários que já estavam marcados nele: confirmar, editar observações e cancelar continuam possíveis. **Interface:** seletor de dias em "Dados da barbearia"; no agendamento, dias fechados aparecem desabilitados com "fechado", e o dia inicial pula para o próximo dia aberto; a tela inicial do cliente mostra os dias ("Segunda a sábado, das 09:00 às 19:00"); o status lateral considera o dia. **Fora, por instrução:** feriados, exceções por data, folgas e disponibilidade por barbeiro |
| Testes executados | `barbershops/test_dias_funcionamento.py` (16): padrão; onboarding; normalização; valores inválidos (vazio, 0, 8, booleano, texto, nulo, decimal); permissão de cliente e barbeiro (403); modelo fora da API; agendamento em dia fechado pelos três perfis; horários vazios; domingo aberto continua aceitando; barbearia que fecha na segunda; remarcação para dia fechado; horário existente num dia que depois fechou; fuso (sábado 22:00 local = domingo em UTC); isolamento entre barbearias. Migração 0006 aplicada, desfeita e reaplicada num banco com 419 agendamentos. Sondagem `BUS-06/*` (11). Navegador A1–A6, B1–B5 |
| Resultado | 16/16 (15 falhavam antes). Sondagem: no padrão, domingo com 20 horários; com o domingo fechado, 0 horários no domingo e 20 no sábado; agendar no domingo → 400 para cliente, admin e barbeiro; cliente e barbeiro não alteram os dias (403). Navegador: domingos desabilitados e rotulados "barbearia fechada"; formulário recusa nenhum dia marcado; sem rolagem horizontal a 390 px; axe sem violações |
| Situação | **Parcialmente resolvido.** Os dias de funcionamento da semana estão resolvidos e verificados. Continuam ausentes feriados, exceções por data, folgas e horário por barbeiro, que a recomendação original incluía. Até o dono desmarcar o domingo, ele continua aberto (padrão "todos os dias"). A parte restante tem impacto menor; sugere-se reavaliá-la como P2 |

#### BUS-05 — Fechamento anterior à abertura é aceito

| Campo | Registro |
|---|---|
| Arquivos modificados | `barbershops/models.py` (`clean`, mensagem `HORARIO_INVALIDO_MENSAGEM`); `barbershops/serializers.py` (`validate`) |
| Solução implementada | **Verificação prévia:** o projeto não suporta horário que atravesse a meia-noite. `Appointment` recusa atendimento que termina em outro dia, e os horários livres vão da abertura ao fechamento do mesmo dia. **Validação:** fechamento ≤ abertura é sempre inválido, na criação (onboarding), na edição completa e no PATCH parcial, que compara com o valor gravado, também no modelo (Django Admin). A mensagem: "O horário de fechamento precisa ser depois do horário de abertura. A agenda não atravessa a meia-noite: abertura e fechamento são do mesmo dia." O frontend já validava; nada mudou nele |
| Testes executados | `barbershops/test_horario_funcionamento.py` (10): antes, igual, PATCH parcial só do fechamento e só da abertura, meia-noite (22:00–02:00 e fechamento 00:00), limite de 1 minuto aceito, edição válida, edição de outros campos, onboarding inválido sem criar barbearia nem promover o usuário, modelo. Sondagem `BUS-05/*` (5). Navegador A3 |
| Resultado | 10/10 (7 falhavam antes). Sondagem: completo, parcial, igual e meia-noite → 400, e o horário gravado permanece 09:00–19:00. Na repetição da sondagem da auditoria, BUS-05 passou de 200/200 para 400/400 |
| Situação | **Resolvido e verificado** |

#### BUS-04 — Troca de serviço ignora o horário de funcionamento

| Campo | Registro |
|---|---|
| Arquivos modificados | `appointments/models.py` (`_validar_horario_funcionamento`) |
| Solução implementada | A validação de horário de funcionamento passa a rodar quando muda o horário **ou o serviço**. O término é calculado com a duração do novo serviço e comparado ao fechamento no fuso local. Terminar exatamente no fechamento continua permitido. O preço histórico só muda numa troca aceita, como antes; numa troca recusada nada é gravado. Mudar só o status ou as observações continua sem revalidar (a duração não histórica é o BUS-09, fora do escopo) |
| Testes executados | `appointments/test_troca_servico_fechamento.py` (10): cenário da auditoria pelos três perfis; horário fora da grade (18:15); limite exato (18:00 + 60 min); troca por serviço de mesma duração; troca de serviço com antecipação do horário; horário enviado em UTC; mudança só de status; modelo. Sondagem `BUS-04/*` (3) |
| Resultado | 10/10 (5 falhavam antes). Sondagem: troca 30 → 60 min às 18:30 → 400 para admin e cliente; às 18:00 → 200. Na repetição da sondagem da auditoria, BUS-04 passou de 200 para 400 |
| Situação | **Resolvido e verificado** |

#### FE-13 — "Agendar" após reservar continua mostrando "Horário reservado"

| Campo | Registro |
|---|---|
| Arquivos modificados | `frontend/src/pages/AppointmentCreatePage.tsx` |
| Solução implementada | A página virou um invólucro que remonta o fluxo a cada navegação (`key={location.key}`). Tocar em "Agendar", na barra inferior ou no menu lateral, estando na tela de horário reservado começa um agendamento novo, sem o estado da reserva anterior. Uma trava (`useRef`) impede que um segundo clique em "Confirmar agendamento" antes da resposta gere outra reserva |
| Testes executados | Navegador, build de produção (`navegador/navegador-rodada1.json`): B6 (1ª reserva), B7 (aba "Agendar" → etapa Serviço), B8 (clique duplo → um único POST, 201), B9 (2ª reserva concluída), B10 (as duas nascem `agendado`), B11 (menu lateral). O projeto não tem infraestrutura de testes de frontend (FE-02, P2, fora do escopo), por isso a verificação é por navegador |
| Resultado | Todas conformes. Antes, a aba mantinha "Horário reservado" (`navegador-novo-agendamento-apos-confirmacao.json` da auditoria) |
| Situação | **Resolvido e verificado** |

#### Verificação geral da rodada

| Verificação | Resultado |
|---|---|
| Suíte completa do backend, SQLite | **391 testes, OK** (9 pulados, exigem PostgreSQL). Eram 327; +64 novos |
| Suíte completa do backend, PostgreSQL 16 descartável | **391 testes, OK**, 0 pulados |
| Testes novos no código anterior | 38 de 64 falham (reproduzem os defeitos) e 26 passam (fluxos legítimos) |
| `makemigrations --check` | Sem alterações pendentes depois da `0006` |
| Migração `0006` | Aditiva, padrão "todos os dias"; aplicada, desfeita e reaplicada sem perda (419 agendamentos) |
| Cobertura dos módulos alterados | 92% (linhas + ramificações); o que ficou de fora são guardas defensivas e código morto anterior |
| Frontend | `tsc` 0 erros, ESLint 0 avisos, build OK (JS inicial 434,7 kB, 138,5 kB gzip) |
| Sondagem HTTP da rodada | 28/28 conforme |
| Sondagem da auditoria repetida (91 verificações) | 66 conforme, contra 62 antes. 4 passaram a conforme (NEW-STATUS, BUS-03, BUS-04, BUS-05) e **nenhuma regrediu**. NEW-STATUS-2 continua marcado só porque o script antigo esperava `agendado` no corpo: agora a API recusa com 400, o comportamento correto. BUS-06 continua com horários no domingo porque o seed está no padrão "todos os dias" |
| Navegador da rodada (três perfis) | 22/22 conforme; 0 erros de console ou de página; 0 respostas ≥ 400; axe sem violações em "Dados da barbearia" e no agendamento (a tela inicial do cliente não passou pelo axe nesta rodada) |
| Varredura completa repetida | 105 cargas (21 rotas × 5 larguras): 0 rolagem horizontal, 0 erros |
| Diff | Só os 15 arquivos listados acima, mais 5 arquivos de teste novos e este documento (`diff/diff-somente-correcoes.patch`) |

#### Ação necessária antes de usar o código corrigido

A rodada criou a migração `barbershops.0006_barbershop_dias_funcionamento`. Ela **não foi aplicada no banco real**, por restrição da tarefa. Antes de rodar o app com este código, é preciso aplicá-la no banco que o `.env` usa:

```bash
python manage.py migrate
```

Sem isso, toda tela que lê a barbearia falha, porque a coluna não existe. A migração só adiciona a coluna, com o padrão "todos os dias", e pode ser desfeita (`migrate barbershops 0005`). O banco do `docker-compose` (DB-01) já estava com outras migrações pendentes.

#### Observações encontradas durante a rodada (não corrigidas, fora do escopo)

| ID | Sev. | Observação |
|---|---|---|
| FE-21 | P3 | No agendamento, o `aria-label` dos dias que não são "hoje", "amanhã" ou "ontem" sai repetido ("Domingo, 15 de novembro, domingo, 15 de novembro"). A comparação entre `relativeDayLabel` e `formatDayLong` diferencia maiúsculas. Defeito anterior à rodada |
| FE-22 | P3 | Na barra inferior do celular, a aba "Barbeiros" fica ativa em "Dados da barbearia": `'/admin/barbershop'.startsWith('/admin/barbers')` é verdadeiro. Defeito anterior à rodada |
| FE-14 | P3 | Para manter a interface coerente com o BUS-06, o status lateral passou a mostrar "Fechada hoje" em dia fechado. Essa parte não tem teste dedicado, e a parte de barbearia desativada continua aberta. **FE-14 continua aberto** |
| TEST-01 | P2 | Os itens desta rodada agora têm testes de regressão. TEST-01 continua **parcialmente resolvido** pelos demais itens (BUS-10, BUS-12, BUS-16, BUS-17, AUTH-02, SEC-03, confirmação de recuperação de senha) |

**Correção de comunicação:** durante a execução foi informado que "48 de 63" testes novos falhavam no código anterior. O número correto era **37 de 63** (leitura errada da saída). Com o teste acrescentado depois, são **38 de 64**.

#### Contagem após a rodada 1

| | Na auditoria | Após a rodada 1 |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 7 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 28 |
| P3 | 35 | 34, mais 2 observações novas (FE-21, FE-22) |
| **Abertos** | **70** | **65 dos 70 originais** (BUS-06 entre eles, parcial), mais 2 observações novas |

---

## 19. Rodada 2 — 13/11/2026: FE-14, FE-21 e FE-22 (somente frontend)

**Escopo autorizado:** FE-14 (indicador de barbearia aberta ou fechada), FE-21 (rótulos acessíveis do calendário) e FE-22 (aba ativa no celular). Nenhum outro item foi tratado.

**Restrições cumpridas:**
- Nenhum arquivo do backend, API, banco, migração, autenticação, `.env` ou configuração foi alterado. Os 93 arquivos `.py` têm o mesmo SHA-256 do início da rodada, e não há migração nova.
- **Dependências:** nenhuma adicionada. O `package-lock.json` é idêntico ao HEAD. O `package.json` ganhou só o script `"test"`. **Justificativa:** o projeto não tinha como rodar testes de frontend (FE-02). Os testes usam o executor nativo do Node 26 (`node --test`, que já remove os tipos do TypeScript), com um gancho de resolução de imports, sem Vitest nem Jest.
- Sem commit, push ou merge. Branch `desenvolvimento`. Alterações já existentes preservadas.
- **Sem redesign.** O aviso de barbearia desativada reaproveita o alerta existente (`ui.alert` / `alertDanger`). Nenhuma cor, fonte ou componente novo, e a faixa de dias do calendário ficou idêntica pixel a pixel.

Evidências em [`docs/auditoria/evidencias-2026-11-13/rodada-2-correcoes/`](auditoria/evidencias-2026-11-13/rodada-2-correcoes/README.md).

#### Resumo

| ID | Situação | Causa técnica |
|---|---|---|
| FE-14 | ✅ **Resolvido e verificado** | O status ignorava `ativo` e, depois de fechar, presumia que a barbearia abria no dia seguinte. A barbearia era carregada uma vez por sessão, então outras sessões ficavam com dados velhos: o calendário do cliente oferecia hoje como dia aberto e a lateral dizia "Aberta" depois de o dono fechar o dia |
| FE-21 | ✅ **Resolvido e verificado** | `relativeDayLabel` devolve a data com inicial maiúscula ("Domingo, 15 de novembro") e `formatDayLong`, com minúscula. A comparação entre os dois diferenciava maiúsculas, falhava e juntava as duas formas |
| FE-22 | ✅ **Resolvido e verificado** | A aba "Barbeiros" usava `path.startsWith('/admin/barbers')`, e `/admin/barbershop` começa com esse texto |

#### FE-14 — Indicador de barbearia aberta ou fechada

| Campo | Registro |
|---|---|
| Arquivos alterados | `frontend/src/utils/shop.ts` (`shopHoursStatus`); `frontend/src/contexts/BarbershopContext.tsx`; `frontend/src/components/AppLayout.tsx` (aviso `ShopInactiveNotice`); `frontend/src/styles/layout.module.css` (espaçamento do aviso) |
| Comportamento esperado (auditoria) | Status coerente com a barbearia desativada e com o dia da semana, e um aviso de barbearia desativada |
| Solução | **1. Status calculado só com dados que já existem** (`ativo`, `dias_funcionamento`, abertura e fechamento), com a mesma função `isOpenOn` que o calendário usa: <br>• "Barbearia desativada"; <br>• "Aberta até 19:00"; <br>• "Fechada, abre às 09:00" (hoje, mais tarde); <br>• "Fechada, abre amanhã às 09:00"; <br>• "Fechada, abre segunda às 09:00", que pula os dias em que ela não abre. <br>Antes, depois do fechamento de sábado, a lateral prometia "abre às 09:00" mesmo com o domingo fechado. <br>**2. Aviso "Barbearia desativada"** no topo de todas as telas, para os três perfis, com a mesma mensagem que a API devolve. <br>**3. Dados atualizados entre sessões:** a barbearia é conferida de novo a cada navegação interna e quando a aba volta a ficar visível. Uma mudança feita pelo dono (dias, horário, desativação) chega à lateral, ao início do cliente, ao calendário e ao aviso sem recarregar. Se nada mudou, o estado não é trocado, e uma falha de rede mantém os dados atuais |
| Testes automatizados | `frontend/tests/shop-status.test.ts`, 13 testes: <br>• dia ISO; <br>• aberta e limites de horário; <br>• antes de abrir; <br>• hoje fechado; <br>• fim de semana fechado; <br>• sábado à noite com domingo fechado; <br>• um dia por semana; <br>• sem configuração de dias; <br>• desativada e reativada; <br>• mudança de configuração; <br>• **teste de coerência com o calendário**: 7 configurações × 14 dias × 7 horários (686 casos), que confere que "aberta" só aparece em dia de funcionamento e dentro do horário, e que o dia prometido é aberto e é o primeiro aberto. <br>No código anterior, 7 dos 13 falham |
| Navegador (build de produção) | Roteiro `scripts/rodada2.mjs`, igual nos dois builds: <br>• **padrão:** status conforme o relógio; <br>• **admin:** fecha hoje em "Dados da barbearia" e a lateral muda **sem recarregar**; <br>• **cliente em outra sessão:** a lateral se atualiza ao navegar pelo menu; o início do cliente mostra o mesmo status; o calendário mostra hoje como fechado; <br>• **API muda os dias em outra sessão:** a lateral do cliente se atualiza quando a aba volta à frente (`hidden` → `visible`); <br>• **barbeiro:** mesmo status; <br>• **desativação pela plataforma:** aviso e "Barbearia desativada" para admin e cliente, inclusive no celular; <br>• **reativação:** o aviso some ao navegar. <br>No build anterior, 8 dessas 11 verificações falham. Por exemplo, a sessão do cliente continuava "Aberta até 19:00", com hoje habilitado no calendário, depois de o dono fechar o dia. No build corrigido, todas conformes |
| Largura | O rótulo mais longo ("Fechada, abre segunda às 09:00") cabe no cartão da lateral: termina em 223 px, com limite em 232 px no desktop e 264 px na gaveta do celular (`navegador/rotulo-mais-longo-lateral.json`) |
| Limitações | <br>• Outra sessão vê a mudança ao navegar ou ao voltar para a aba, não em tempo real: se a pessoa fica parada na mesma tela com a aba à frente, a atualização vem na próxima navegação. Não há consulta periódica. <br>• Cada navegação faz uma requisição a mais (`GET /barbershops/`, 2 consultas SQL), no mesmo padrão do contador "a confirmar". <br>• No celular, o status da lateral fica dentro do menu (gaveta), como antes; o aviso de desativação aparece no topo em todos os tamanhos |
| Situação | **Resolvido e verificado** |

#### FE-21 — Rótulos acessíveis do calendário

| Campo | Registro |
|---|---|
| Arquivos alterados | `frontend/src/utils/format.ts` (nova `dateChipLabel`); `frontend/src/pages/AppointmentCreatePage.tsx` (usa a função) |
| Solução | Uma única função monta o rótulo, e a data aparece uma vez: <br>• "Hoje, sexta-feira, 13 de novembro"; <br>• "Amanhã, sábado, 14 de novembro"; <br>• "Domingo, 15 de novembro"; <br>• dia fechado: "…, barbearia fechada". <br>A semântica não mudou: dias abertos e fechados são botões com `role="radio"`, os fechados ficam `disabled`, e o dia escolhido tem `aria-checked="true"`. A aparência é a mesma: a imagem da faixa de dias tem o mesmo SHA-256 nos dois builds, e os textos visíveis são idênticos |
| Testes automatizados | `frontend/tests/calendar-labels.test.ts`, 6 testes: hoje, amanhã, demais dias, dia fechado, virada de ano, e os 21 dias do agendamento (rótulos únicos, data e dia da semana uma vez só, sufixo de fechado só nos fechados), com e sem dias fechados |
| Navegador | Os 21 rótulos são distintos e cada um tem a data uma única vez; os 3 domingos aparecem desabilitados e terminam em ", barbearia fechada"; há um único dia marcado, e ele é aberto; o axe-core não acusa violações; escolher um dia aberto mostra os horários. No build anterior: "Domingo, 15 de novembro, domingo, 15 de novembro, barbearia fechada" |
| Limitações | Não foi testado com leitor de tela real (NV-3); a verificação foi pelos rótulos expostos e pelo axe-core |
| Situação | **Resolvido e verificado** |

#### FE-22 — Aba ativa incorreta no celular

| Campo | Registro |
|---|---|
| Arquivos alterados | `frontend/src/utils/navigation.ts` (novo: `isSectionPath`, `TAB_ROUTES`, `activeTab`); `frontend/src/components/AppLayout.tsx` (a barra inferior usa o módulo; os ícones ficam mapeados por destino) |
| Solução | A aba ativa compara por **segmento de caminho**: uma seção é a própria rota ou uma subpágina dela (`/admin/barbers` ou `/admin/barbers/...`), não qualquer texto que comece igual. As abas e as regras de cada perfil ficaram num módulo puro e testável; a barra inferior marca no máximo uma aba. Telas sem aba, como "Dados da barbearia" e "Minha conta" do admin, não marcam nenhuma. O menu lateral do desktop (`NavLink`) não mudou |
| Testes automatizados | `frontend/tests/navigation.test.ts`, 26 testes: <br>• seção por segmento (incluindo o caso da auditoria); <br>• todas as rotas autenticadas de `App.tsx` nos três perfis (admin, barbeiro e cliente), com parâmetros de busca e barra final; <br>• no máximo uma aba ativa por rota; <br>• cada aba fica ativa na própria tela |
| Navegador | Celular (390 px) e tablet (820 px): <br>• admin: 8 rotas; <br>• barbeiro: 3 rotas; <br>• cliente: 6 rotas; <br>• tocar em cada aba marca só ela; <br>• desktop: o menu lateral marca o item certo e não há barra inferior. <br>No build anterior, "Dados da barbearia" marcava "Barbeiros" no celular e no tablet |
| Situação | **Resolvido e verificado** |

#### Perfis verificados

| Perfil | O que foi verificado |
|---|---|
| Administrador da plataforma (superusuário) | Comportamento anterior mantido: entra no onboarding (não há painel de plataforma, SA-01). Desativa e reativa a barbearia pela API para o teste do aviso |
| Administrador da barbearia | Abas no celular e no tablet, menu lateral no desktop, mudança de dias com atualização imediata da lateral, aviso de desativação |
| Barbeiro | Abas (Agenda, A confirmar, Conta) e status da lateral coerente com a configuração |
| Cliente | Abas, calendário (rótulos, dias fechados, horários), status no início e na lateral, aviso de desativação no celular |

#### Testes executados nesta rodada

| Tipo | Resultado |
|---|---|
| Typecheck (`tsc`, app e node) | 0 erros |
| Lint (ESLint, `--max-warnings=0`) | 0 erros, 0 avisos |
| Build de produção | OK (JS inicial 436,3 kB, 139,0 kB gzip; antes, 434,7 kB) |
| Testes automatizados de frontend (`npm test`, novos) | **45/45** (13 FE-14, 6 FE-21, 26 FE-22). No código do início da rodada, 7 de 13 do FE-14 falham; os arquivos de FE-21 e FE-22 não carregam, porque a lógica antiga estava embutida nos componentes |
| Suíte do backend (SQLite, sem alteração de backend) | 391 testes, OK (9 pulados, exigem PostgreSQL) |
| Navegador, roteiro da rodada (build anterior × corrigido) | Anterior: 57/68. Corrigido: **68/68**. 11 itens passaram a conformes, nenhum regrediu, 0 erros de console, de página ou de API |
| Reexecução do roteiro da rodada 1 no build corrigido | **22/22**: as correções da rodada 1 continuam funcionando (dias de funcionamento, calendário, FE-13, clique duplo, remarcação), com 0 erros de console, página ou API e axe sem violações |
| Varredura completa da auditoria no build corrigido | **105 cargas** (21 rotas × 5 larguras, de 1440 a 360 px): 0 erros de carga, 0 rolagem horizontal, 0 erros de console, página ou API; os 3 fluxos (cliente no celular, barbeiro no tablet, admin no desktop) concluídos sem erros |

**Verificações manuais:** inspeção visual das capturas (aviso de desativação no desktop e no celular, lateral com o rótulo mais longo, "Dados da barbearia" sem aba marcada, calendário). **Não testados:** leitor de tela real; Chrome e Safari (só Firefox disponível); celular físico.

#### Fora do escopo, apenas registrado

- **`PRODUCT.md`** ainda diz que "não existem dias fechados" e que os horários livres ignoram dias fechados (BUS-06). Isso deixou de ser verdade na rodada 1 para os dias da semana. É documentação, não foi alterada.
- **Leitura de dados por sessão:** a atualização entre sessões resolve a barbearia. Outras listas (por exemplo, serviços e barbeiros no agendamento) continuam carregadas ao abrir cada tela, como antes.

#### Contagem após a rodada 2

| | Após a rodada 1 | Após a rodada 2 |
|---|---|---|
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 28 |
| P3 | 34, mais 2 observações (FE-21, FE-22) | 33 (FE-14 resolvido), sem observações pendentes (FE-21 e FE-22 resolvidos) |
| **Abertos** | 65 dos 70 originais, mais 2 observações | **64 dos 70 originais** |
