# Auditoria técnica e funcional — BarberPro

| | |
|---|---|
| **Data** | 11/11/2026 |
| **Branch auditada** | `desenvolvimento` — commit `ed5e39f` + alterações não commitadas do redesign do frontend |
| **Escopo** | Backend Django/DRF, frontend React, banco de dados, segurança, testes, documentação e repositório |
| **Natureza** | Somente diagnóstico. Nenhum código, configuração ou dado foi alterado |
| **Evidências** | [`docs/auditoria/evidencias/`](auditoria/evidencias/README.md) |

> **Confidencialidade.** Este relatório não contém a `SECRET_KEY`, senhas ou tokens: apenas comprimentos, contagens e códigos HTTP. Ele descreve, porém, uma fragilidade da chave local (SEC-01). **Gere uma nova chave antes de commitar ou publicar este documento** em repositório acessível a terceiros.

---

## Sumário

1. [Resumo executivo](#1-resumo-executivo)
2. [Metodologia](#2-metodologia)
3. [Arquitetura identificada](#3-arquitetura-identificada)
4. [Funcionalidades existentes e estado real](#4-funcionalidades-existentes-e-estado-real)
5. [Funcionalidades ausentes](#5-funcionalidades-ausentes)
6. [Índice dos 53 problemas](#6-índice-dos-53-problemas)
7. [Problemas P0 — Crítico (2)](#7-problemas-p0--crítico-2)
8. [Problemas P1 — Alto (9)](#8-problemas-p1--alto-9)
9. [Problemas P2 — Médio (21)](#9-problemas-p2--médio-21)
10. [Problemas P3 — Baixo (21)](#10-problemas-p3--baixo-21)
11. [Itens não verificados (5)](#11-itens-não-verificados-5)
12. [Resultados dos testes executados](#12-resultados-dos-testes-executados)
13. [Evidências visuais](#13-evidências-visuais)
14. [Plano de correção por prioridade](#14-plano-de-correção-por-prioridade)
15. [Respostas objetivas](#15-respostas-objetivas)
16. [Correções em relação a comunicações anteriores](#16-correções-em-relação-a-comunicações-anteriores)

---

## 1. Resumo executivo

O BarberPro tem uma **base técnica sólida**:

- o isolamento entre barbearias resistiu às **16 tentativas** de acesso cruzado, inclusive com manipulação de IDs;
- a escalada de privilégio foi bloqueada em todos os testes;
- o ciclo de sessão funciona (renovação por cookie HttpOnly, revogação na troca de senha, blacklist no logout, recuperação de senha sem revelar contas);
- o backend é eficiente (2 a 4 consultas SQL por endpoint, sem N+1);
- as migrações estão íntegras e aplicadas;
- os 239 testes do backend passam;
- o frontend compila sem erros de tipo, sem avisos de lint, e os fluxos principais funcionam de ponta a ponta nos três perfis.

O sistema **não está pronto para produção**:

- **Dois problemas críticos de segurança.** A chave secreta efetivamente carregada tem 3 caracteres (SEC-01), e clientes e barbeiros leem o faturamento completo da barbearia (SEC-02).
- **Regras de negócio incorretas e confirmadas.** Admin pode se autodesativar e deixar a barbearia sem administrador; barbearia "excluída" continua operando; reagendamento mantém "confirmado"; atendimento pode terminar depois do fechamento; a API aceita fechamento antes da abertura; atendimento futuro pode ser marcado como realizado.
- **Lacunas de produto que impedem o uso real.** Clientes não conseguem se cadastrar numa barbearia; não há dias de funcionamento (domingos recebem horários); a recuperação de senha não envia e-mail na configuração atual.

| Prioridade | Quantidade |
|---|---|
| P0 — Crítico | 2 |
| P1 — Alto | 9 |
| P2 — Médio | 21 |
| P3 — Baixo | 21 |
| **Total de problemas** | **53** |
| Itens não verificados | 5 |

| Tipo | Quantidade | IDs |
|---|---|---|
| Bug confirmado | 14 | SEC-01, SEC-02, BUS-01, BUS-02, BUS-03, BUS-04, BUS-05, BUS-07, AUTH-02, SEC-03, BUS-10, BUS-12, FE-03, FE-04 |
| Funcionalidade ausente | 13 | BUS-06, PROD-01, BUS-08, BUS-13, API-01, OBS-01, OPS-01, FE-01, FE-02, SA-01, SAAS-01, SEC-08, FE-06 |
| Funcionalidade incompleta | 4 | AUTH-01, BUS-11, BUS-14, FE-09 |
| Risco potencial | 8 | SEC-04, SEC-05, SEC-07, BUS-09, DATA-01, SEC-06, DATA-03, FE-11 |
| Dívida técnica | 8 | REPO-01, API-02, DATA-02, FE-05, FE-07, DOC-03, REPO-02, REPO-03 |
| Documentação incorreta/desatualizada | 2 | DOC-01, DOC-02 |
| Lacuna de testes | 2 | TEST-01, TEST-02 |
| Melhoria opcional | 2 | FE-08, FE-12 |
| **Total** | **53** | |

---

## 2. Metodologia

### 2.1 Regras seguidas

- Branch `desenvolvimento` confirmada; `git status` com as 63 alterações do redesign preservadas; nenhum commit, push ou merge; branch `release/barberpro-academica-v1` intocada.
- **Nenhuma escrita no Postgres real.** Lá foram feitas apenas consultas: `showmigrations` e contagens de integridade pelo ORM.
- Todos os testes dinâmicos (segurança, regras de negócio, interface) rodaram numa **cópia isolada da API**: Django com as mesmas configurações do projeto, mas com banco SQLite descartável fora do repositório, populado com uma barbearia fictícia. Para os testes de isolamento foram criadas uma segunda e uma terceira barbearia **apenas nesse banco descartável**.
- No ambiente isolado o *throttling* foi desligado para permitir as sondagens; por isso o rate limiting real ficou como "não verificado".
- Nenhum ataque contra serviços externos. A força bruta da chave não foi executada; o teste de forja de token usou a chave apenas em memória, sem exibi-la.

### 2.2 Métodos

| Método | O que cobriu |
|---|---|
| Leitura de código | Todos os models, serializers, views, permissões, mixins, settings, URLs, migrações, admin, managers e o frontend completo |
| Sondagem 1 da API isolada | 42 verificações: isolamento entre barbearias (16), perfis e permissões (13), regras de negócio e recursos da API (13). Resultado: 27 OK, 15 falhas |
| Sondagem 2 da API isolada | 12 observações de sessão (login, refresh por cookie, troca de senha, logout, recuperação) e administração do próprio tenant |
| Sondagem 3 da API isolada | Geração de horários num domingo e passo entre horários |
| Teste de forja de JWT | Impacto real da chave curta, com e sem acesso aos hashes de senha |
| Contagem de consultas SQL | 7 endpoints com `CaptureQueriesContext` |
| Navegador real | Firefox headless via `puppeteer-core`: fluxos de admin, cliente e barbeiro; teclado; queda real da API; desktop 1440 px e celular 390 px |
| Banco real (somente leitura) | Migrações aplicadas e 17 contagens de integridade |
| Ferramentas | 239 testes do backend (2 execuções), `tsc -b`, ESLint, build Vite, `makemigrations --check`, `check --deploy`, `git` (histórico, branches, arquivos versionados) |

### 2.3 Classificação

- **Gravidade:** P0 (segurança, perda/corrupção de dados, funcionalidade essencial inutilizável), P1 (funcionalidade principal quebrada ou regra de negócio incorreta), P2 (incompleta, usabilidade, inconsistência), P3 (qualidade, organização, performance, refinamento).
- **Tipo:** bug confirmado, funcionalidade ausente, funcionalidade incompleta, risco potencial, dívida técnica, melhoria opcional, não verificado.
- **"Bug confirmado"** exige reprodução dinâmica ou evidência inequívoca no código. Quando a confirmação veio só da leitura do código, isso está indicado no campo Evidência.

---

## 3. Arquitetura identificada

| Camada | Detalhes |
|---|---|
| Backend | Django 5.0.14, DRF 3.15.2, djangorestframework-simplejwt 5.3.1, django-filter 24.3, django-cors-headers 4.9.0, Pillow 10.4.0, gunicorn 22.0.0 |
| Autenticação | Access token JWT no header `Authorization` (15 min) guardado pelo frontend em `localStorage`; refresh em cookie HttpOnly no caminho `/api/v1/auth/`, `SameSite=Lax`, rotação e blacklist; `CHECK_REVOKE_TOKEN` ativo |
| Banco | PostgreSQL 16 via `docker-compose.yml` (porta 5433); testes também podem usar SQLite (`config.test_settings`) |
| Apps | `accounts` (usuário com `email` como login e `tipo_perfil`), `barbershops` (barbearia = tenant, barbeiros), `services`, `appointments`, `config` (permissões, mixin de tenant, paginação) |
| Multi-tenant | Banco e schema compartilhados. Isolamento na aplicação por `TenantScopedQuerysetMixin` (filtra por `barbershop_id`) e checagens em serializers e models. Superusuário vê todos os tenants |
| Perfis | `admin`, `barbeiro`, `cliente`; "Super Admin" = `is_superuser`/`is_staff` do Django, usando o Django Admin |
| Exclusão | Lógica (desativação) para usuários, barbeiros e serviços; FKs com `PROTECT` |
| Frontend | React 19, TypeScript 5.8, Vite 6, React Router 7, Axios, React Hook Form + Zod, CSS Modules, telas carregadas sob demanda |
| Infra | Apenas o banco em Docker; sem Dockerfile da aplicação, CI, cache compartilhado, logging ou monitoramento |

---

## 4. Funcionalidades existentes e estado real

| Módulo | Funcionalidade | Estado | Evidência / problema |
|---|---|---|---|
| Autenticação | Login | ✅ Funciona | Sondagem 2 (HTTP 200) e fluxos de interface |
| Autenticação | Renovação de sessão por cookie | ✅ Funciona | Refresh 200; recusa do servidor encerra a sessão; queda de rede não desloga |
| Autenticação | Logout | ✅ Funciona | 204; refresh posterior 401 |
| Autenticação | Troca de senha | ✅ Funciona | 204; access e refresh antigos passam a 401 |
| Autenticação | Recuperação de senha | ⚠️ Incompleta | API correta e sem enumeração, mas sem envio de e-mail configurado (AUTH-01) |
| Autenticação | Cadastro público | ⚠️ Incompleto | Só serve a donos de barbearia (PROD-01); e-mails duplicados por maiúsculas (AUTH-02) |
| Usuários | Gestão pelo admin | ⚠️ Bug | Admin pode se rebaixar ou se desativar (BUS-01) |
| Permissões | Controle por perfil | ⚠️ Bug | Correto em 10 de 13 verificações de perfil (e 16 de 16 de isolamento); `revenue-report` aberto a todos (SEC-02); e-mail de barbeiros exposto (SEC-03) |
| Barbearias | Onboarding | ✅ Funciona | Usuário já vinculado recebe 400 |
| Barbearias | Edição | ⚠️ Bug | Fechamento antes da abertura aceito (BUS-05) |
| Barbearias | Desativação/exclusão | ❌ Sem efeito | Barbearia inativa continua operando (BUS-02) |
| Barbearias | Logo | ⚠️ Só API | Sem tela; mídia servida só com `DEBUG` (FE-09, OPS-01) |
| Barbearias | Isolamento | ✅ Funciona | 16/16 tentativas bloqueadas |
| Barbeiros | Cadastro, edição, desativação, reativação | ✅ Funciona | Fluxos testados |
| Barbeiros | Disponibilidade própria | ❌ Ausente | BUS-06 |
| Barbeiros | Efeito da desativação nos agendamentos | ❌ Ausente | BUS-13 |
| Clientes | Cadastro, edição, desativação e histórico pelo admin | ✅ Funciona | Tela "Clientes" e `POST/PATCH/DELETE /users/` |
| Clientes | Autocadastro numa barbearia | ❌ Ausente | PROD-01 |
| Clientes | Pesquisa | ⚠️ Só no navegador | API sem busca (API-01) |
| Serviços | Cadastro, edição, preço, duração, ativo | ✅ Funciona | Edição de inativo corrigida no frontend com `?ativo=all` |
| Serviços | Integridade da duração | ⚠️ Risco | Duração 0 possível fora da API (SEC-07); duração não histórica (BUS-09) |
| Agendamentos | Criação e prevenção de conflitos | ✅ Funciona | Conflitos rejeitados; horários livres excluem ocupados |
| Agendamentos | Horários livres | ⚠️ Incompleto | Ignora dias fechados (BUS-06); passo = duração (BUS-11); devolve datas passadas (BUS-10) |
| Agendamentos | Reagendamento | ⚠️ Bug | Mantém "confirmado" (BUS-03); troca de serviço ignora o horário de funcionamento (BUS-04) |
| Agendamentos | Confirmação e conclusão | ⚠️ Bug | Futuro pode virar "realizado" (BUS-07) |
| Agendamentos | Cancelamento | ✅ Funciona | Cliente, admin e barbeiro (inconsistência em BUS-12) |
| Agendamentos | Desfecho de horários passados | ❌ Ausente | BUS-08 |
| Dashboard | Indicadores e gráficos | ✅ Dados reais | Calculados no navegador a partir dos agendamentos reais com `preco_historico` (FE-11, API-01) |
| Relatórios | `revenue-report` | ❌ Permissão errada | SEC-02; agrupamento por UTC (API-02) |
| Super Admin | Painel global | ❌ Ausente | SA-01 |

---

## 5. Funcionalidades ausentes

| # | Funcionalidade | Problema |
|---|---|---|
| 1 | Autocadastro de clientes numa barbearia (página pública, convite ou código) | PROD-01 |
| 2 | Dias de funcionamento, folgas, feriados, bloqueios e horário por barbeiro | BUS-06 |
| 3 | Envio real de e-mail (recuperação de senha) | AUTH-01 |
| 4 | Status "não compareceu" e desfecho de horários vencidos | BUS-08 |
| 5 | Tratamento de agendamentos futuros ao desativar barbeiro ou cliente | BUS-13 |
| 6 | Agendamento pelo admin para cliente existente ou avulso | BUS-14 |
| 7 | Busca, ordenação, filtro por período e tamanho de página na API | API-01 |
| 8 | Observabilidade: logs, rastreamento de erros, trilha de auditoria, health check | OBS-01 |
| 9 | Infra de produção: Dockerfile, CI, estáticos/mídia, limpeza de tokens, backup | OPS-01 |
| 10 | Tratamento de erros de renderização no frontend | FE-01 |
| 11 | Testes de frontend | FE-02 |
| 12 | Painel de Super Admin | SA-01 |
| 13 | Notificações, LGPD, planos e cobrança | SAAS-01 |
| 14 | Verificação de e-mail no cadastro | SEC-08 |
| 15 | Página 404 | FE-06 |

---

## 6. Índice dos 53 problemas

| # | ID | Prioridade | Tipo | Módulo | Título |
|---|---|---|---|---|---|
| 1 | SEC-01 | P0 | Bug confirmado (configuração) | Segurança / Autenticação | Chave secreta efetiva com 3 caracteres |
| 2 | SEC-02 | P0 | Bug confirmado | Agendamentos / Relatórios | Faturamento exposto a clientes e barbeiros |
| 3 | BUS-01 | P1 | Bug confirmado | Usuários / Permissões | Admin pode se rebaixar ou se desativar |
| 4 | BUS-02 | P1 | Bug confirmado | Barbearias / Super Admin | Barbearia desativada continua operando |
| 5 | BUS-03 | P1 | Bug confirmado | Agendamentos | Reagendamento mantém "confirmado" |
| 6 | BUS-04 | P1 | Bug confirmado | Agendamentos | Troca de serviço ignora horário de funcionamento |
| 7 | BUS-05 | P1 | Bug confirmado | Barbearias | Fechamento anterior à abertura é aceito |
| 8 | BUS-06 | P1 | Funcionalidade ausente | Agendamentos / Barbeiros | Sem dias de funcionamento, folgas e disponibilidade |
| 9 | PROD-01 | P1 | Funcionalidade ausente | Autenticação / Clientes | Cliente não consegue se cadastrar numa barbearia |
| 10 | AUTH-01 | P1 | Funcionalidade incompleta | Autenticação | Recuperação de senha sem envio de e-mail |
| 11 | BUS-07 | P1 | Bug confirmado | Agendamentos / Dashboard | Atendimento futuro pode ser marcado como realizado |
| 12 | AUTH-02 | P2 | Bug confirmado | Usuários / Banco | E-mails duplicados por maiúsculas |
| 13 | SEC-03 | P2 | Bug confirmado | Barbeiros / Privacidade | E-mail de login dos barbeiros exposto a clientes |
| 14 | SEC-04 | P2 | Risco potencial | Frontend / Segurança | Access token em `localStorage` sem CSP |
| 15 | SEC-05 | P2 | Risco potencial | Infra / Segurança | Rate limiting em cache local por processo |
| 16 | SEC-07 | P2 | Risco potencial | Serviços / Agendamentos | Duração 0 trava a geração de horários |
| 17 | BUS-08 | P2 | Funcionalidade ausente | Agendamentos | Sem "não compareceu" nem desfecho de horários vencidos |
| 18 | BUS-09 | P2 | Risco potencial | Banco / Agendamentos | Duração do atendimento não é histórica |
| 19 | BUS-11 | P2 | Funcionalidade incompleta | Agendamentos | Passo entre horários igual à duração |
| 20 | BUS-13 | P2 | Funcionalidade ausente | Barbeiros / Clientes | Desativação não trata agendamentos futuros |
| 21 | BUS-14 | P2 | Funcionalidade incompleta | Agendamentos | Admin não agenda pela interface; sem cliente avulso |
| 22 | API-01 | P2 | Funcionalidade ausente | API / Integração | Sem busca, ordenação, período e page_size |
| 23 | DATA-01 | P2 | Risco potencial | Banco | Reverso da migração 0008 apaga preços históricos |
| 24 | OBS-01 | P2 | Funcionalidade ausente | Backend | Sem logs, monitoramento, auditoria e health check |
| 25 | OPS-01 | P2 | Funcionalidade ausente | Infraestrutura | Sem Dockerfile, CI, estáticos/mídia, rotinas e backup |
| 26 | FE-01 | P2 | Funcionalidade ausente | Frontend | Sem error boundary |
| 27 | FE-02 | P2 | Funcionalidade ausente | Testes / Frontend | Nenhum teste de frontend |
| 28 | TEST-01 | P2 | Lacuna de testes | Testes / Backend | Nenhum teste cobre os bugs confirmados |
| 29 | DOC-01 | P2 | Documentação desatualizada | Documentação / Integração | Documentação da API contradiz o comportamento |
| 30 | REPO-01 | P2 | Dívida técnica | Repositório | Virtualenv versionado (96% dos arquivos) |
| 31 | SA-01 | P2 | Funcionalidade ausente | Super Admin | Sem painel de Super Admin |
| 32 | SAAS-01 | P2 | Funcionalidade ausente | Produto | Sem notificações, LGPD e cobrança |
| 33 | SEC-06 | P3 | Risco potencial | Repositório | Chave secreta antiga no histórico do git |
| 34 | SEC-08 | P3 | Funcionalidade ausente | Autenticação | Sem verificação de e-mail no cadastro |
| 35 | BUS-10 | P3 | Bug confirmado | Agendamentos | Horários livres devolvidos para datas passadas |
| 36 | BUS-12 | P3 | Bug confirmado (inconsistência) | Agendamentos | Regras de cancelamento e edição do barbeiro inconsistentes |
| 37 | API-02 | P3 | Dívida técnica | Relatórios | `revenue_report` com `.extra()` e dia em UTC |
| 38 | DATA-02 | P3 | Dívida técnica | Banco | Preços históricos antigos estimados |
| 39 | DATA-03 | P3 | Risco potencial | Banco | Divergência de versão de collation no Postgres |
| 40 | FE-03 | P3 | Bug confirmado (código) | Frontend | Falha de recarga sem feedback |
| 41 | FE-04 | P3 | Bug confirmado (inconsistência) | Frontend | Contador "a confirmar" inclui horários vencidos |
| 42 | FE-05 | P3 | Dívida técnica | Integração | Fuso horário fixo no frontend |
| 43 | FE-06 | P3 | Funcionalidade ausente | Frontend | Sem página 404 |
| 44 | FE-07 | P3 | Dívida técnica | Frontend | Código morto |
| 45 | FE-08 | P3 | Melhoria opcional | Frontend | Fonte carregada do Google Fonts |
| 46 | FE-09 | P3 | Funcionalidade incompleta | Frontend | Sem tela de logo; barbeiro não reagenda |
| 47 | FE-11 | P3 | Risco potencial | Integração | Duas fontes de cálculo de faturamento |
| 48 | DOC-02 | P3 | Documentação incorreta | Documentação | README: testes não usam SQLite por padrão |
| 49 | DOC-03 | P3 | Dívida técnica | Backend | Comentários obsoletos sobre o app `core` |
| 50 | REPO-02 | P3 | Dívida técnica | Repositório | Arquivos soltos e rascunhos |
| 51 | REPO-03 | P3 | Dívida técnica | Repositório | Branches dessincronizadas |
| 52 | TEST-02 | P3 | Lacuna de testes | Testes | Cobertura de código não medida |
| 53 | FE-12 | P3 | Melhoria opcional | Apresentação | Banco real quase vazio para demonstração |

---

## 7. Problemas P0 — Crítico (2)

### SEC-01 — Chave secreta efetiva com 3 caracteres

| Campo | Valor |
|---|---|
| Gravidade | **P0 — Crítico** |
| Tipo | Bug confirmado (configuração) |
| Módulo | Segurança / Autenticação |
| Arquivos | `.env` (local, **não** versionado); `config/settings.py` (leitura da `SECRET_KEY` e verificação de produção) |

**Descrição.** A `SECRET_KEY` efetivamente carregada pelo Django tem **3 caracteres**. A linha `SECRET_KEY=` do `.env` tem 50 caracteres, mas o valor contém um `#` sem aspas, que o `django-environ` interpreta como início de comentário; o restante é descartado. Como o `SIMPLE_JWT` não define `SIGNING_KEY`, a mesma chave assina os tokens JWT (HS256). A verificação existente em `settings.py` só bloqueia a chave padrão de desenvolvimento quando `DEBUG=False`; não verifica o tamanho.

**Evidência.**
- `len(settings.SECRET_KEY) == 3` e `len(SIMPLE_JWT SIGNING_KEY) == 3`; a linha no `.env` tem 50 caracteres e contém `#` e `$` sem aspas. Valores não exibidos.
- Toda execução dos testes emite `InsecureKeyLengthWarning: The HMAC key is 3 bytes long`.
- Teste de forja (evidência `forja-de-token-jwt.txt`):
  - token assinado com a chave efetiva, **sem** o claim de hash de senha → **HTTP 401**;
  - **com** o claim `hash_password` (MD5 do hash de senha armazenado, simulando vazamento do banco) → **HTTP 200**;
  - controle com outra chave → HTTP 401.

**Impacto.**
- A chave-raiz da aplicação pode ser descoberta por força bruta a partir de qualquer JWT legítimo (3 caracteres).
- A forja de tokens aceitos hoje é contida apenas pelo `CHECK_REVOKE_TOKEN`, que exige um claim derivado do hash da senha.
- Se os hashes de senha vazarem (backup, cópia do banco, acesso indevido ao Django Admin), um atacante gera tokens válidos para **qualquer usuário de qualquer barbearia sem quebrar nenhuma senha**, anulando o isolamento multi-tenant.
- Hoje afeta o ambiente local e a demonstração; seria grave se esse `.env` ou um com o mesmo problema fosse para um servidor.
- Classificado como P0 por ser o segredo-raiz da aplicação, com uma única barreira restante e correção trivial.

**Como reproduzir.**
1. Na raiz do projeto, verifique o comprimento sem exibir o valor:
   ```bash
   venv312/bin/python -c "import os,django;os.environ['DJANGO_SETTINGS_MODULE']='config.settings';django.setup();from django.conf import settings;print(len(settings.SECRET_KEY))"
   ```
2. Resultado atual: `3`.
3. Rode `python manage.py test` e observe o `InsecureKeyLengthWarning`.

**Solução recomendada.**
1. Gerar nova chave sem `#`, `$` e aspas, por exemplo `python -c "import secrets;print(secrets.token_urlsafe(64))"`, ou envolver o valor em aspas no `.env`.
2. Em `settings.py`, falhar na inicialização se `len(SECRET_KEY) < 50` com `DEBUG=False`, e emitir aviso em desenvolvimento.
3. Documentar no `.env.example` que valores com `#` ou `$` precisam de aspas.
4. Esperado: trocar a chave encerra as sessões atuais e invalida tokens de recuperação de senha já emitidos.

**Critério de aceitação.**
- [ ] `len(settings.SECRET_KEY) >= 50` no ambiente local.
- [ ] Nenhum `InsecureKeyLengthWarning` ao rodar os testes.
- [ ] Iniciar com chave curta e `DEBUG=False` falha com mensagem clara.
- [ ] `.env.example` orienta sobre caracteres especiais.

---

### SEC-02 — Faturamento exposto a clientes e barbeiros

| Campo | Valor |
|---|---|
| Gravidade | **P0 — Crítico** |
| Tipo | Bug confirmado |
| Módulo | Agendamentos / Relatórios |
| Arquivos | `appointments/views.py` (action `revenue_report`, método `get_permissions`) |

**Descrição.** O endpoint `GET /api/v1/appointments/revenue-report/` não restringe o perfil do usuário. Qualquer usuário autenticado do tenant (inclusive cliente) recebe o faturamento total, por barbeiro, por serviço e diário. A action não declara `permission_classes`, e `get_permissions` só trata `update`, `partial_update` e `destroy`, caindo em `IsAuthenticated` para todo o resto.

**Evidência.** Sondagem 1 (`sondagem-permissoes-e-regras.txt`): cliente → **HTTP 200**, com o total da barbearia exposto; barbeiro → **HTTP 200**, com o faturamento dos 3 barbeiros. Nenhum teste automatizado cobre o endpoint (busca por `revenue` nos arquivos de teste: zero ocorrências).

**Impacto.** Vazamento de informação financeira da empresa para clientes e de desempenho individual entre funcionários. Risco comercial e de privacidade.

**Como reproduzir.**
1. Entrar como cliente: `POST /api/v1/auth/login/` com e-mail e senha de um cliente; guardar o `access`.
2. `GET /api/v1/appointments/revenue-report/` com `Authorization: Bearer <ACCESS_DO_CLIENTE>`.
3. Resultado atual: HTTP 200 com `total_revenue`, `by_barber`, `by_service` e `daily`.

**Solução recomendada.** Declarar `permission_classes=[IsAuthenticated, IsAdminRole]` na action, ou tratá-la em `get_permissions`. Se o barbeiro precisar ver os próprios números, filtrar pelo `perfil_barbeiro` dele numa action separada. Documentar o endpoint (ver DOC-01).

**Critério de aceitação.**
- [ ] Cliente → 403; barbeiro → 403 (ou apenas os próprios números, se essa for a regra definida); admin → 200.
- [ ] Testes automatizados para os três perfis.
- [ ] Endpoint documentado em `DOCUMENTACAO_API.md`.

---

## 8. Problemas P1 — Alto (9)

### BUS-01 — Admin pode se rebaixar ou se desativar, deixando a barbearia sem administrador

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Bug confirmado |
| Módulo | Usuários / Permissões |
| Arquivos | `accounts/serializers.py` (`UserSerializer.validate` e `update`); `accounts/views.py` (`UserViewSet.perform_destroy`) |

**Descrição.** O admin consegue alterar o próprio `tipo_perfil` para `cliente` com `PATCH /users/{seu_id}/`, porque `UserSerializer.validate` só bloqueia a conversão de admin para barbeiro. Ele também consegue desativar a própria conta com `DELETE /users/{seu_id}/`, porque `perform_destroy` não verifica se o alvo é o próprio usuário ou o último admin do tenant. Nos dois casos a barbearia fica sem nenhum administrador ativo, e a aplicação não oferece caminho de recuperação: só um superusuário, pelo Django Admin.

**Evidência.**
- Sondagem 1: `PATCH tipo_perfil=cliente` no próprio usuário → **HTTP 200**, com `tipo_perfil=cliente`. Em seguida, o ex-admin recebeu **HTTP 403** ao tentar criar usuários.
- Sondagem 2: `DELETE /users/{próprio id}/` → **HTTP 204**; login posterior → **HTTP 401**.

**Impacto.** A barbearia fica bloqueada: ninguém mais cadastra serviços, barbeiros ou clientes, edita dados da barbearia ou administra a agenda. Basta um clique equivocado, ou uma automação, para causar a interrupção.

**Como reproduzir.**
1. Entrar como admin e obter o próprio `id` em `GET /api/v1/users/me/`.
2. `PATCH /api/v1/users/<ID>/` com `{"tipo_perfil": "cliente"}` → 200.
3. Tentar `POST /api/v1/users/` → 403.
4. Alternativa: `DELETE /api/v1/users/<ID>/` → 204; novo login → 401.

**Solução recomendada.**
- No serializer e na view, impedir que o usuário altere o próprio `tipo_perfil` e o próprio `is_active`.
- Impedir rebaixar ou desativar o **último admin ativo** do tenant.
- Responder 400 com mensagem explicando o motivo.

**Critério de aceitação.**
- [ ] Autorrebaixamento e autodesativação do admin retornam 400 com mensagem clara.
- [ ] Rebaixar ou desativar o último admin ativo do tenant retorna 400.
- [ ] Testes cobrindo próprio usuário, último admin e o caso permitido (outro admin, quando houver mais de um).

---

### BUS-02 — Barbearia desativada continua operando normalmente

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Bug confirmado |
| Módulo | Barbearias / Super Admin |
| Arquivos | `barbershops/views.py` (`BarbershopViewSet.perform_destroy`); `barbershops/serializers.py` (`BarbershopSerializer`, campo `ativo` gravável); `config/mixins.py`; `config/permissions.py` |

**Descrição.** O campo `Barbershop.ativo` não é consultado por nenhuma regra de negócio, permissão ou queryset. A "exclusão" de barbearia (`DELETE /barbershops/{id}/?confirmar=<nome>`, restrita ao staff) apenas marca `ativo=False`, e isso não tem nenhum efeito: usuários continuam entrando, agendando e administrando. Além disso, `ativo` é gravável pelo serializer, então o próprio admin do tenant pode alterá-lo via `PATCH`.

**Evidência.** Sondagem 1: `PATCH ativo=false` pelo admin do tenant → **HTTP 200**; em seguida, novo agendamento na mesma barbearia → **HTTP 201**. A busca no código por usos de `barbershop.ativo` em regras não encontrou nenhuma ocorrência (só aparece em filtros do Django Admin).

**Impacto.** A plataforma não consegue suspender uma barbearia (inadimplência, abuso, encerramento de contrato). A operação de exclusão transmite uma falsa sensação de efeito.

**Como reproduzir.**
1. Como admin de uma barbearia, `PATCH /api/v1/barbershops/<ID>/` com `{"ativo": false}` → 200.
2. Criar um agendamento nessa barbearia (`POST /api/v1/appointments/`) → 201.
3. Entrar como cliente dessa barbearia → login normal.

**Solução recomendada.**
- Tornar `ativo` somente-leitura no `BarbershopSerializer` para usuários que não são staff.
- Criar uma verificação central (permissão global ou no `TenantScopedQuerysetMixin` e na autenticação) que recuse requisições de usuários vinculados a barbearia inativa, com mensagem própria ("Barbearia suspensa").
- Manter acesso de leitura ao staff.

**Critério de aceitação.**
- [ ] Usuários de barbearia inativa recebem 403 com mensagem específica em qualquer endpoint de negócio.
- [ ] O admin do tenant não consegue alterar `ativo`.
- [ ] O staff consegue suspender e reativar.
- [ ] Testes cobrindo suspensão, reativação e a tentativa do admin.

---

### BUS-03 — Reagendamento pelo cliente mantém o status "confirmado"

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Bug confirmado |
| Módulo | Agendamentos |
| Arquivos | `appointments/serializers.py` (`AppointmentSerializer.update`); `appointments/views.py` (`perform_update`) |

**Descrição.** Quando um cliente reagenda (altera `data_hora`, `barbeiro` ou `servico`) um agendamento que estava **confirmado**, o status permanece "confirmado". A barbearia confirmou o horário antigo, não o novo, mas a agenda passa a exibir o novo horário como confirmado, sem que ninguém o tenha aprovado.

**Evidência.** Sondagem 1: agendamento criado pelo cliente, confirmado pelo admin e depois reagendado pelo cliente com `PATCH data_hora` → `status = confirmado` na resposta.

**Impacto.** O barbeiro e o admin confiam numa confirmação que não existe. O status perde o significado operacional e o fluxo de confirmação é contornado.

**Como reproduzir.**
1. Cliente cria agendamento (`POST /api/v1/appointments/`).
2. Admin confirma: `PATCH /api/v1/appointments/<ID>/` com `{"status": "confirmado"}`.
3. Cliente reagenda: `PATCH /api/v1/appointments/<ID>/` com `{"data_hora": "<nova data>T09:00:00"}`.
4. Resultado atual: `status = "confirmado"`.

**Solução recomendada.** Quando o cliente alterar `data_hora`, `barbeiro` ou `servico`, redefinir `status` para `agendado` na mesma transação. Decidir e documentar se a mesma regra vale para alterações feitas pelo barbeiro.

**Critério de aceitação.**
- [ ] Reagendamento pelo cliente resulta em `status = agendado`.
- [ ] Alterar apenas `observacoes` não muda o status.
- [ ] Testes cobrindo os dois casos.

---

### BUS-04 — Troca de serviço ignora o horário de funcionamento

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Bug confirmado |
| Módulo | Agendamentos |
| Arquivos | `appointments/models.py` (`Appointment._validar_horario_funcionamento`) |

**Descrição.** A validação de horário de funcionamento retorna antecipadamente quando o agendamento já existe e `data_hora` não mudou. A comparação considera apenas `data_hora`, não o serviço. Se o horário for mantido e o serviço trocado por um mais longo, o fim do atendimento pode ultrapassar o fechamento, e a validação não é executada.

**Evidência.** Sondagem 1: agendamento às 18:30 numa barbearia que fecha às 19:00, trocado de um serviço de 30 min para um de 60 min → **HTTP 200**. O atendimento passa a terminar às 19:30.

**Impacto.** A agenda passa a ter atendimentos fora do horário da barbearia, e o barbeiro fica com compromisso depois do expediente.

**Como reproduzir.**
1. Barbearia com fechamento às 19:00.
2. Criar agendamento às 18:30 com um serviço de 30 min.
3. `PATCH /api/v1/appointments/<ID>/` com `{"servico": <id de serviço de 60 min>}`.
4. Resultado atual: HTTP 200.

**Solução recomendada.** Revalidar o horário de funcionamento quando `data_hora` **ou** `servico_id` mudarem, comparando com o valor persistido. Calcular o fim com a duração do novo serviço.

**Critério de aceitação.**
- [ ] O cenário acima retorna 400 com a mensagem de fechamento.
- [ ] Trocar para um serviço que cabe no horário continua permitido.
- [ ] Testes para os dois casos.

---

### BUS-05 — Fechamento anterior à abertura é aceito

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Bug confirmado |
| Módulo | Barbearias |
| Arquivos | `barbershops/models.py` (`Barbershop`, sem `clean`); `barbershops/serializers.py` (`BarbershopSerializer.validate`) |

**Descrição.** A API aceita `horario_fechamento` anterior ou igual a `horario_abertura`. Não há validação no model nem no serializer, que só verifica se o usuário já pertence a outra barbearia na criação. Com esses valores, a geração de horários livres não produz nenhum horário e toda tentativa de agendamento é recusada, sem explicação.

**Evidência.** Sondagem 1: `PATCH horario_abertura=18:00, horario_fechamento=08:00` → **HTTP 200**. O frontend redesenhado valida esse caso nos formulários, mas o backend é a defesa real.

**Impacto.** A barbearia "desaparece" da agenda: clientes não encontram horários e o admin não entende o motivo.

**Como reproduzir.**
1. Como admin, `PATCH /api/v1/barbershops/<ID>/` com `{"horario_abertura": "18:00:00", "horario_fechamento": "08:00:00"}` → 200.
2. `GET /api/v1/appointments/available-slots/?barbeiro=<id>&servico=<id>&data=<amanhã>` → lista vazia.

**Solução recomendada.** Implementar `Barbershop.clean()` exigindo `fechamento > abertura` e chamar a mesma validação no serializer, na criação e na edição, inclusive em `PATCH` parcial que altere só um dos campos.

**Critério de aceitação.**
- [ ] Criação e edição com fechamento ≤ abertura retornam 400, inclusive quando só um dos campos é enviado.
- [ ] Testes cobrindo criação, edição completa e edição parcial.

---

### BUS-06 — Sem dias de funcionamento, folgas e disponibilidade por barbeiro

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Funcionalidade ausente |
| Módulo | Agendamentos / Barbeiros |
| Arquivos | `barbershops/models.py` (`Barbershop` só tem abertura e fechamento); `appointments/views.py` (`available_slots`); `appointments/models.py` (validações de horário) |

**Descrição.** O sistema não modela dias da semana de funcionamento, feriados, bloqueios de agenda nem horário de trabalho, folga ou intervalo de cada barbeiro. A geração de horários livres e a validação de agendamentos consideram apenas `horario_abertura` e `horario_fechamento` da barbearia, aplicados a **todos os dias**, e a disponibilidade de todos os barbeiros ativos é igual a esse horário.

**Evidência.** Sondagem 3 (`sondagem-agenda.txt`): domingo 15/11/2026 → **10 horários oferecidos** para um serviço de 60 min. Leitura de `available_slots`: os slots começam em `horario_abertura` e terminam em `horario_fechamento`, sem nenhuma consulta a dia da semana ou disponibilidade.

**Impacto.** Em uso real, clientes agendam em dias em que a barbearia está fechada e com barbeiros de folga, gerando faltas, retrabalho e perda de confiança.

**Como reproduzir.**
1. `GET /api/v1/appointments/available-slots/?barbeiro=<id>&servico=<id>&data=<próximo domingo>`.
2. Resultado atual: lista de horários preenchida.
3. Um `POST /api/v1/appointments/` nesse domingo é aceito.

**Solução recomendada.**
- Modelar a grade semanal da barbearia (dia × abertura/fechamento, com intervalos).
- Modelar exceções por data (feriados, fechamentos) e a disponibilidade e folgas por barbeiro.
- Aplicar essas regras em `available_slots` e em `Appointment.clean`.
- Expor no frontend as telas de configuração correspondentes.

**Critério de aceitação.**
- [ ] Dias fechados e folgas não oferecem horários.
- [ ] A API recusa agendamento nesses dias e horários com mensagem clara.
- [ ] Testes para dia fechado, feriado, folga de barbeiro e intervalo.

---

### PROD-01 — Cliente não consegue se cadastrar numa barbearia existente

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Funcionalidade ausente |
| Módulo | Autenticação / Clientes |
| Arquivos | `accounts/serializers.py` (`PublicRegistrationSerializer`); `accounts/views.py` (`RegistrationView`); frontend `src/pages/RegisterPage.tsx` e `src/pages/OnboardingPage.tsx` |

**Descrição.** O cadastro público (`POST /auth/register/`) cria sempre um usuário `cliente` **sem barbearia**, que é encaminhado ao onboarding para **criar a própria barbearia** e virar admin. Não há página pública por barbearia, link de convite, código de acesso nem seleção de barbearia. Hoje a única forma de um cliente usar o sistema é o admin cadastrá-lo manualmente na tela "Clientes", criada no redesign, informando uma senha inicial.

**Evidência.** `PublicRegistrationSerializer.create` não define `barbershop`. O `README.md` do frontend documenta a limitação. Nos fluxos de interface, uma conta criada pelo cadastro público vai para o onboarding de dono.

**Impacto.** Inviabiliza a aquisição de clientes num SaaS real: a barbearia não consegue divulgar um link para seus clientes se cadastrarem e agendarem. Quem se cadastra pelo site acaba criando uma barbearia sem querer, gerando tenants vazios.

**Como reproduzir.**
1. Acessar `/register` e criar uma conta.
2. O sistema entra e mostra "Vamos cadastrar sua barbearia". Não há como escolher uma barbearia existente.

**Solução recomendada.**
- Página pública por barbearia (ex.: `/b/<slug>`) com serviços, equipe e cadastro/agendamento vinculados ao tenant.
- Ou convite por link/código gerado pelo admin.
- Separar explicitamente "criar conta de dono" de "criar conta de cliente".

**Critério de aceitação.**
- [ ] Um cliente novo consegue se cadastrar e agendar numa barbearia específica sem intervenção do admin.
- [ ] A conta fica vinculada ao tenant correto e não passa pelo onboarding de dono.
- [ ] Testes de API para o cadastro vinculado e tentativa de vínculo a tenant inexistente/inativo.

---

### AUTH-01 — Recuperação de senha sem envio de e-mail

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Funcionalidade incompleta |
| Módulo | Autenticação |
| Arquivos | `config/settings.py` (sem `EMAIL_BACKEND`/`EMAIL_HOST`); `accounts/serializers.py` (`PasswordResetRequestSerializer.save`); frontend `src/pages/PasswordResetRequestPage.tsx` e `PasswordResetConfirmPage.tsx` |

**Descrição.** Os endpoints de recuperação de senha existem e são seguros (resposta idêntica para e-mails existentes e inexistentes), mas o envio de e-mail não está configurado:
- Não há `EMAIL_BACKEND`, `EMAIL_HOST` ou credenciais nas configurações. O Django usa o padrão: SMTP em `localhost:25`.
- O envio é feito com `fail_silently=True`, então qualquer falha é engolida sem log.
- A mensagem traz o `uid` e o `token` em texto, sem link para o frontend; o usuário precisa copiá-los manualmente (a tela de confirmação do redesign aceita digitação).
- Para e-mails inexistentes, o código envia uma mensagem para o próprio `DEFAULT_FROM_EMAIL`, para manter tempo de resposta constante.

**Evidência.** Busca em `config/settings.py`: nenhuma configuração `EMAIL_*`. Código de `PasswordResetRequestSerializer.save`. A entrega real **não pôde ser verificada** por falta de SMTP (ver seção 11).

**Impacto.** Quem esqueceu a senha não recebe nada e não há registro do erro. Na prática, o usuário fica sem acesso até um admin intervir.

**Como reproduzir.**
1. Em `/password/reset`, informar o e-mail de uma conta existente → a tela confirma o envio.
2. Nenhum e-mail chega, salvo se houver um servidor SMTP escutando em `localhost:25`, e nenhuma falha é registrada.

**Solução recomendada.**
- Configurar o e-mail por variáveis de ambiente (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`) e documentá-las no `.env.example`.
- Usar o backend de console em desenvolvimento.
- Montar um link `FRONTEND_URL/password/reset/confirm?uid=<uid>&token=<token>` na mensagem.
- Registrar falhas de envio em log em vez de silenciá-las.
- Avaliar envio assíncrono.

**Critério de aceitação.**
- [ ] Com SMTP configurado, o e-mail chega com um link funcional que leva à tela de nova senha já preenchida.
- [ ] Em desenvolvimento, a mensagem aparece no console.
- [ ] Falhas de envio aparecem no log.
- [ ] `.env.example` documenta as variáveis.

---

### BUS-07 — Atendimento futuro pode ser marcado como "realizado"

| Campo | Valor |
|---|---|
| Gravidade | **P1 — Alto** |
| Tipo | Bug confirmado |
| Módulo | Agendamentos / Dashboard |
| Arquivos | `appointments/models.py` (`Appointment._validar_transicao_status`) |

**Descrição.** A máquina de estados permite `confirmado → realizado` sem verificar se o atendimento já começou. Um agendamento com data futura pode ser marcado como realizado.

**Evidência.** Sondagem 1: agendamento 13 dias à frente, confirmado e depois `PATCH status=realizado` → **HTTP 200**.

**Impacto.** Faturamento, ticket médio, rankings de equipe e serviços (painel e `revenue-report`) passam a contar receita que não aconteceu. O horário também deixa de poder ser cancelado ou reagendado, porque "realizado" é estado final.

**Como reproduzir.**
1. Criar um agendamento para daqui a alguns dias.
2. `PATCH {"status": "confirmado"}`.
3. `PATCH {"status": "realizado"}` → 200.

**Solução recomendada.** Em `_validar_transicao_status`, permitir a transição para `realizado` somente se `data_hora <= agora` (opcionalmente com tolerância configurável). No frontend, ocultar "Marcar realizado" para horários futuros.

**Critério de aceitação.**
- [ ] A transição para "realizado" em horário futuro retorna 400 com mensagem clara.
- [ ] A transição em horário iniciado ou passado continua permitida.
- [ ] Testes para os dois casos.

---

## 9. Problemas P2 — Médio (21)

### AUTH-02 — E-mails duplicados por diferença de maiúsculas

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Bug confirmado |
| Módulo | Usuários / Banco |
| Arquivos | `accounts/managers.py` (`UserManager.create_user`); `accounts/models.py` (`email` com `unique=True`) |

**Descrição.** `normalize_email` só converte o domínio para minúsculas, e a restrição de unicidade de `email` diferencia maiúsculas. É possível criar `Fulano@dominio.com` e `fulano@dominio.com` como contas distintas, e o login exige a mesma grafia do cadastro.

**Evidência.** Sondagem 1: cadastro de um e-mail já existente com letras maiúsculas na parte local → **HTTP 201**. No Postgres real não há duplicados hoje (`integridade-banco-real.txt`).

**Impacto.**
- Contas duplicadas para a mesma pessoa.
- Falha de login quando o usuário digita com outra capitalização.
- A recuperação de senha (`email__iexact().first()`) pode escolher a conta errada.

**Como reproduzir.**
1. Com uma conta `exemplo@dominio.com` existente, `POST /api/v1/auth/register/` com `EXEMPLO@dominio.com` → 201.
2. Tentar entrar com `Exemplo@dominio.com` → 401.

**Solução recomendada.**
- Normalizar todo o e-mail para minúsculas no manager, nos serializers de cadastro/edição e no login.
- Criar `UniqueConstraint(Lower('email'))` precedida de uma migração que detecte duplicados existentes.

**Critério de aceitação.**
- [ ] O cadastro do exemplo retorna 400 ("e-mail já cadastrado").
- [ ] O login aceita qualquer capitalização.
- [ ] O banco impede duplicados por maiúsculas.
- [ ] Testes de cadastro, login e edição.

---

### SEC-03 — E-mail de login dos barbeiros exposto a clientes

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Bug confirmado (privacidade) |
| Módulo | Barbeiros |
| Arquivos | `barbershops/serializers.py` (`BarberSerializer`, campo `email`) |

**Descrição.** `GET /api/v1/barbers/` é acessível a clientes (necessário para agendar) e devolve o campo `email` (e-mail de login do barbeiro) de cada profissional.

**Evidência.** Sondagem 1: verificação "cliente vê e-mail de login dos barbeiros" → falha (e-mails presentes na resposta).

**Impacto.** Exposição de dados pessoais de funcionários a qualquer cliente. Facilita phishing e tentativas de acesso à conta do barbeiro.

**Como reproduzir.** Entrar como cliente e chamar `GET /api/v1/barbers/`; o campo `email` aparece em cada item.

**Solução recomendada.** Serializer público sem `email` para cliente e barbeiro; manter o campo apenas para admin (via `get_serializer_class` ou `to_representation` conforme o perfil).

**Critério de aceitação.**
- [ ] Cliente e barbeiro não recebem `email` em `/barbers/`.
- [ ] Admin continua recebendo.
- [ ] Teste por perfil.

---

### SEC-04 — Access token em `localStorage` sem Content-Security-Policy

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Risco potencial |
| Módulo | Frontend / Segurança |
| Arquivos | `frontend/src/utils/storage.ts`; `frontend/src/api/client.ts`; configuração do servidor web (inexistente) |

**Descrição.** O access token (15 min) é salvo em `localStorage` (chave `barbearia.auth`) e não há cabeçalho Content-Security-Policy. O refresh está corretamente em cookie HttpOnly.

**Evidência.** `storage.ts` usa `localStorage.setItem`; não há configuração de CSP no Django nem servidor web configurado no projeto.

**Impacto.** Qualquer XSS (por exemplo, numa futura dependência comprometida) consegue ler o token e agir como o usuário por até 15 minutos. O impacto é limitado pelo tempo de vida curto e por não ser possível obter o refresh.

**Como reproduzir.** Entrar no sistema e, no console do navegador, executar `localStorage.getItem('barbearia.auth')`: o token aparece.

**Solução recomendada.**
- Manter o access token apenas em memória e obter um novo pelo cookie de refresh ao carregar a página.
- Configurar CSP restritiva (scripts apenas da própria origem) no servidor web ou com `django-csp`.

**Critério de aceitação.**
- [ ] O token não é persistido no armazenamento do navegador.
- [ ] O app continua logado após recarregar (via refresh).
- [ ] O cabeçalho CSP está presente em produção.

---

### SEC-05 — Rate limiting em cache local por processo

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Risco potencial |
| Módulo | Infra / Segurança |
| Arquivos | `config/settings.py` (sem `CACHES`; `DEFAULT_THROTTLE_*`) |

**Descrição.** O throttling do DRF (login 5/min, cadastro 10/h, recuperação 5/h etc.) usa o cache padrão do Django, que, sem `CACHES` configurado, é memória local de cada processo.

**Evidência.** Nenhuma configuração `CACHES` em `settings.py`. A limitação real não foi exercitada (ver seção 11).

**Impacto.** Em produção com N workers do gunicorn, cada um conta separadamente: o limite efetivo de tentativas de login vira 5×N por minuto e zera a cada reinício. Isso reduz a proteção contra força bruta de senhas.

**Como reproduzir.** Inspecionar `settings.py` (sem `CACHES`). Em ambiente com vários workers, tentativas de login distribuídas entre eles excedem 5/min sem bloqueio.

**Solução recomendada.** Configurar cache compartilhado (Redis) para o throttling em produção e documentar a variável.

**Critério de aceitação.**
- [ ] Com vários workers, a 6ª tentativa de login no mesmo minuto retorna 429, independentemente do worker.

---

### SEC-07 — Serviço com duração 0 trava a geração de horários

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Risco potencial |
| Módulo | Serviços / Agendamentos |
| Arquivos | `services/models.py` (`duracao = PositiveIntegerField`); `services/serializers.py` (`min_value=1`); `appointments/views.py` (`available_slots`) |

**Descrição.** O model aceita `duracao = 0` (`PositiveIntegerField` permite zero); só o serializer da API exige ≥ 1. Um serviço com duração 0, gravado pelo Django Admin ou direto no banco, faz o laço de `available_slots` (`while slot_atual <= limite: … slot_atual += duracao`) nunca avançar.

**Evidência.** Leitura de código. **Não executado**, para não travar o servidor de teste. No Postgres real não há serviços com duração 0 (`integridade-banco-real.txt`).

**Impacto.** Cada consulta de horários para esse serviço prende um worker indefinidamente, com CPU a 100%; poucas requisições derrubam a API.

**Como reproduzir (não executado).**
1. No Django Admin, editar um serviço e salvar `duração = 0`.
2. Consultar `available-slots` para esse serviço: a requisição não retorna.

**Solução recomendada.**
- `MinValueValidator(1)` no campo e `CheckConstraint(duracao__gt=0)` no model, com migração.
- Guarda no laço (`if duracao <= timedelta(0): return erro`).

**Critério de aceitação.**
- [ ] Banco e Django Admin recusam duração 0.
- [ ] O endpoint responde com erro em vez de entrar em laço, caso exista dado legado inválido.
- [ ] Teste do caso.

---

### BUS-08 — Sem "não compareceu" e sem desfecho de horários vencidos

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Agendamentos |
| Arquivos | `appointments/models.py` (`Appointment.Status`) |

**Descrição.** Os status são `agendado`, `confirmado`, `realizado` e `cancelado`. Não existe "não compareceu" nem rotina ou indicador para horários cujo horário já passou e não tiveram desfecho; eles permanecem "agendado" ou "confirmado" indefinidamente.

**Evidência.** `Appointment.Status` tem 4 valores; não há tarefas agendadas no projeto. O contador "a confirmar" do frontend inclui esses horários (FE-04).

**Impacto.** Agenda poluída com pendências antigas; impossível medir taxa de comparecimento; métricas de cancelamento incompletas.

**Como reproduzir.** Criar um agendamento, deixá-lo passar sem alterar o status e consultar `/appointments/?status=agendado`: ele continua listado como pendente.

**Solução recomendada.** Adicionar o status `nao_compareceu` (transições a partir de agendado/confirmado após o horário) e um indicador de "vencidos sem desfecho" no painel, ou uma rotina que os sinalize.

**Critério de aceitação.**
- [ ] Horários passados podem ser marcados como não comparecidos.
- [ ] Horários vencidos aparecem separados dos "a confirmar".
- [ ] Métricas de comparecimento no painel.
- [ ] Testes de transição.

---

### BUS-09 — Duração do atendimento não é histórica

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Risco potencial |
| Módulo | Banco / Agendamentos |
| Arquivos | `appointments/models.py` (`_validar_conflito_horario`, `_validar_horario_funcionamento`); `appointments/views.py` (`available_slots`) |

**Descrição.** O agendamento guarda o preço histórico, mas não a duração. Conflitos, horários livres e o fim de cada atendimento são calculados com `servico.duracao` **atual**.

**Evidência.** Leitura de código: `agendamento.servico.duracao` em `_validar_conflito_horario` e na lista de ocupados de `available_slots`; não há campo de duração em `Appointment`.

**Impacto.** Alterar a duração de um serviço muda retroativamente a ocupação de agendas já marcadas: aumentar pode criar sobreposições "invisíveis"; reduzir libera horários que estavam ocupados.

**Como reproduzir.**
1. Dois agendamentos seguidos (10:00 e 10:30) com um serviço de 30 min.
2. Alterar a duração do serviço para 60 min.
3. Os dois passam a se sobrepor sem nenhum aviso, e novas validações consideram a nova duração.

**Solução recomendada.** Adicionar `duracao_historica` ao agendamento (preenchida na criação e na troca de serviço, como `preco_historico`), com migração de dados, e usá-la em todos os cálculos.

**Critério de aceitação.**
- [ ] Alterar a duração de um serviço não muda horários nem conflitos de agendamentos existentes.
- [ ] Testes do cenário.

---

### BUS-11 — Passo entre horários igual à duração do serviço

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade incompleta |
| Módulo | Agendamentos |
| Arquivos | `appointments/views.py` (`available_slots`: `slot_atual += duracao`) |

**Descrição.** Os horários livres avançam de acordo com a duração do serviço. Um serviço de 60 min só oferece horas cheias (09:00, 10:00…), mesmo quando 09:30 estaria livre.

**Evidência.** Sondagem 3: serviço de 60 min → `['09:00', '10:00', '11:00', '12:00', '13:00', …]`.

**Impacto.** Perda de encaixes: após um atendimento de 30 min às 09:00, um serviço de 60 min só pode começar às 10:00, deixando 30 min ociosos. A ocupação da barbearia diminui.

**Como reproduzir.** `GET /api/v1/appointments/available-slots/` para um serviço de 60 min; observar que todos os horários são horas cheias.

**Solução recomendada.** Passo configurável por barbearia (ex.: 15 min), independente da duração, mantendo a verificação de que o serviço inteiro cabe e não conflita.

**Critério de aceitação.**
- [ ] Todos os inícios possíveis no passo configurado aparecem quando livres.
- [ ] Testes com serviços de durações diferentes.

---

### BUS-13 — Desativar barbeiro ou cliente não trata agendamentos futuros

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Barbeiros / Clientes |
| Arquivos | `barbershops/views.py` (`BarberViewSet.perform_destroy`, `perform_update`); `accounts/views.py` (`UserViewSet.perform_destroy`); `accounts/serializers.py` (`UserSerializer.update`) |

**Descrição.** Ao desativar um barbeiro (ou rebaixá-lo) ou desativar a conta de um cliente, os agendamentos futuros dessa pessoa permanecem "agendado/confirmado", sem aviso, cancelamento ou reatribuição.

**Evidência.** Leitura de código: as rotinas de desativação alteram apenas o perfil, a conta e o `deleted_at/by`. No Postgres real, hoje há 0 casos (`integridade-banco-real.txt`).

**Impacto.** Clientes podem comparecer para atendimento com um barbeiro desligado; a agenda mantém compromissos de clientes inativos; o painel conta horários que não vão acontecer.

**Como reproduzir.**
1. Barbeiro com agendamento futuro.
2. Desativá-lo (`DELETE /api/v1/barbers/<id>/`).
3. O agendamento continua "agendado/confirmado" em `/appointments/`.

**Solução recomendada.** Antes de desativar, listar os horários futuros afetados e exigir uma decisão (cancelar com aviso ou reatribuir a outro barbeiro). No mínimo, retornar a lista para o frontend exibir.

**Critério de aceitação.**
- [ ] A desativação não deixa horários futuros sem decisão explícita.
- [ ] Testes para barbeiro e cliente.

---

### BUS-14 — Admin não agenda pela interface; sem atendimento avulso

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade incompleta |
| Módulo | Agendamentos |
| Arquivos | `appointments/views.py` (`perform_create` aceita `cliente` informado pelo admin); `appointments/models.py` (`cliente` precisa ter perfil cliente); frontend `src/App.tsx` (`/appointments/new` restrito a clientes) |

**Descrição.** A API permite ao admin criar agendamento para um cliente existente, mas não há tela para isso. Também não existe "cliente avulso" (sem conta): todo agendamento exige um usuário com perfil cliente.

**Evidência.** Leitura de código e de rotas. A rota de agendamento do frontend tem `allowedRoles={['cliente']}`.

**Impacto.** Agendamentos por telefone ou no balcão não podem ser registrados pela interface; a agenda real fica incompleta.

**Como reproduzir.** Entrar como admin e procurar uma ação "Novo agendamento": não existe. Acessar `/appointments/new` como admin redireciona para o painel.

**Solução recomendada.** Tela de agendamento pelo admin, com busca de cliente e cadastro rápido. Avaliar um modelo de cliente sem login (nome e telefone) para atendimentos avulsos.

**Critério de aceitação.**
- [ ] O admin agenda para um cliente existente ou recém-criado pela interface, com as mesmas validações de horário.
- [ ] Testes de API e de interface.

---

### API-01 — Sem busca, ordenação, filtro por período e `page_size`

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | API / Integração |
| Arquivos | `appointments/views.py`, `accounts/views.py`, `services/views.py`, `barbershops/views.py`; `config/pagination.py`; frontend `src/api/endpoints.ts` (`collectPages`) |

**Descrição.**
- A API não oferece `SearchFilter`, `OrderingFilter`, filtro por intervalo de datas, `page_size` nem filtro `tipo_perfil` em `/users/`.
- A paginação é fixa em 20 itens.
- Para oferecer busca e filtros, o frontend baixa todas as páginas em sequência e filtra no navegador.

**Evidência.**
- Sondagem 1: `page_size=100` ignorado (sempre 20); `?ordering`, `?search` e `?tipo_perfil` sem efeito.
- `consultas-sql-por-endpoint.txt`: o painel percorre 12 páginas para 228 agendamentos.
- No backend, cada página custa só 2 consultas; o gargalo é o número de requisições.

**Impacto.** O tempo de carregamento do painel, dos agendamentos e dos clientes cresce linearmente com o histórico. Com milhares de registros, essas telas ficam lentas ou inviáveis, e o tráfego aumenta.

**Como reproduzir.**
1. `GET /api/v1/appointments/?page_size=100` → 20 itens.
2. `GET /api/v1/users/?search=x` → resultado igual à listagem completa.
3. No navegador, abrir o painel e contar as requisições a `/appointments/`.

**Solução recomendada.**
- Habilitar `SearchFilter` e `OrderingFilter` com campos explícitos.
- Criar filtros `data_inicio/data_fim` em agendamentos e `tipo_perfil` em usuários.
- `page_size_query_param` com `max_page_size`.
- Endpoint de métricas agregadas para o painel.
- No frontend, usar paginação e filtros do servidor.

**Critério de aceitação.**
- [ ] As telas fazem um número fixo de requisições independentemente do volume.
- [ ] Busca, ordenação e filtros são resolvidos pela API.
- [ ] Testes dos filtros.

---

### DATA-01 — Reverso da migração 0008 apaga todos os preços históricos

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Risco potencial |
| Módulo | Banco |
| Arquivos | `appointments/migrations/0008_populate_preco_historico.py` |

**Descrição.** A função reversa `reverse_populate_preco_historico` executa `Appointment.objects.all().update(preco_historico=None)`, apagando **todos** os preços históricos, inclusive os gravados pela aplicação depois da migração.

**Evidência.** Leitura do arquivo de migração.

**Impacto.** Um rollback de migração (ex.: `migrate appointments 0007`) destrói dados financeiros irrecuperáveis.

**Como reproduzir (não executado; destrutivo).** `python manage.py migrate appointments 0007` em um banco com agendamentos zera `preco_historico` de todos eles.

**Solução recomendada.** Tornar o reverso um no-op (`migrations.RunPython.noop`), já que a migração 0007 remove o campo ao ser desfeita, ou restringi-lo aos registros que a própria migração preencheu.

**Critério de aceitação.**
- [ ] Desfazer até a 0007 e reaplicar não altera preços gravados pela aplicação, em teste com banco descartável.

---

### OBS-01 — Sem logs, monitoramento, trilha de auditoria e health check

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Backend |
| Arquivos | `config/settings.py` (sem `LOGGING`); `config/urls.py` (sem rota de saúde); `appointments/models.py` (sem histórico de alterações) |

**Descrição.**
- Não há configuração de logging, integração com rastreamento de erros (ex.: Sentry) nem endpoint de health check.
- Não há trilha de auditoria: não se registra quem confirmou, cancelou ou alterou um agendamento (existem apenas `deleted_at/deleted_by` nas exclusões lógicas).
- Falhas de envio de e-mail são silenciadas (AUTH-01).

**Evidência.** Busca nas configurações e rotas (`verificacoes-backend-e-build.txt`).

**Impacto.** Erros em produção passam despercebidos. Não é possível responder "quem cancelou este horário?" numa disputa com cliente, nem monitorar a disponibilidade do serviço.

**Como reproduzir.** Provocar um erro 500 e verificar que não há registro estruturado. Consultar um agendamento cancelado e verificar que não há autor nem data da mudança de status.

**Solução recomendada.** `LOGGING` com formato estruturado, Sentry (ou similar) por variável de ambiente, `/health/` verificando o banco, e tabela de histórico de agendamento (autor, status anterior/novo, data).

**Critério de aceitação.**
- [ ] Erros chegam a um painel.
- [ ] Cada mudança de status registra autor e horário, visíveis ao admin.
- [ ] `/health/` responde 200 com o banco disponível e 503 sem ele.

---

### OPS-01 — Sem infraestrutura de implantação

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Infraestrutura |
| Arquivos | Raiz do projeto; `docker-compose.yml` (só o banco); `config/urls.py` (mídia apenas com `DEBUG`); `config/settings.py` (`STATIC_ROOT` sem servidor) |

**Descrição.** Faltam:
- Dockerfile da aplicação;
- pipeline de CI (testes, lint, build);
- serviço de arquivos estáticos em produção (whitenoise ou servidor web; com `DEBUG=False` o Django Admin fica sem CSS);
- serviço de mídia (logos só são servidos com `DEBUG`);
- rotina `flushexpiredtokens` (a tabela de tokens do blacklist cresce indefinidamente);
- backup documentado.

**Evidência.** `verificacoes-backend-e-build.txt`: sem `.github`, Dockerfile, Procfile, Makefile, pre-commit, whitenoise ou health check; trecho `if settings.DEBUG: urlpatterns += static(...)` em `config/urls.py`.

**Impacto.** Implantação manual e propensa a erro; regressões chegam sem verificação automática; mídia quebrada em produção; crescimento contínuo do banco.

**Como reproduzir.** Tentar subir a aplicação com `DEBUG=False`: o Django Admin aparece sem estilos e as URLs de mídia retornam 404.

**Solução recomendada.**
- Dockerfile multi-stage e compose de produção (app + banco + servidor web).
- CI rodando `manage.py test`, `npm run lint`, `tsc` e `npm run build`.
- Whitenoise ou nginx para estáticos, e armazenamento de mídia (volume ou S3).
- Rotina agendada de limpeza de tokens e backup documentado.

**Critério de aceitação.**
- [ ] Um commit dispara o CI.
- [ ] A aplicação sobe em produção por um procedimento documentado, com estáticos e mídia funcionando.
- [ ] Rotina de limpeza e backup descritas.

---

### FE-01 — Sem error boundary no frontend

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Frontend |
| Arquivos | `frontend/src/App.tsx`; `frontend/src/components/AppLayout.tsx` |

**Descrição.** Não há componente de fronteira de erro. Uma exceção durante a renderização de qualquer tela desmonta a árvore inteira do React e deixa a página em branco.

**Evidência.** Busca por `ErrorBoundary`/`componentDidCatch` em `frontend/src`: zero ocorrências.

**Impacto.** Um dado inesperado vindo da API (ou um bug) derruba a interface inteira, sem mensagem nem forma de recuperação além de recarregar.

**Como reproduzir.** Forçar um erro de renderização numa tela (ex.: lançar exceção num componente em desenvolvimento): a aplicação inteira fica em branco.

**Solução recomendada.** Error boundary no layout e por rota, com mensagem, botão "Recarregar" e registro do erro (integrar ao OBS-01).

**Critério de aceitação.**
- [ ] Um erro forçado numa tela mostra a mensagem de falha e mantém menu e navegação funcionando.

---

### FE-02 — Nenhum teste de frontend

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Testes / Frontend |
| Arquivos | `frontend/package.json` (sem script `test`); `frontend/src` (sem arquivos de teste) |

**Descrição.** O frontend não tem testes unitários, de componente ou de ponta a ponta. A verificação desta auditoria foi feita com scripts externos ao projeto.

**Evidência.** `verificacoes-backend-e-build.txt`.

**Impacto.** Regressões de interface (como os bugs corrigidos no redesign: dias desalinhados, 404 ao editar serviço inativo) só são percebidas manualmente.

**Como reproduzir.** `npm test` não existe; não há arquivos `*.test.*` ou `*.spec.*`.

**Solução recomendada.**
- Vitest + Testing Library para utilitários (`format.ts`, `status.ts`) e componentes críticos (ações de status, modal, agendamento).
- Playwright para login, agendamento, reagendamento, cancelamento e ações do admin.
- Rodar tudo no CI.

**Critério de aceitação.**
- [ ] O CI executa os testes de frontend.
- [ ] Os fluxos de login, agendamento e ações de status têm teste automatizado.

---

### TEST-01 — Nenhum teste cobre os bugs confirmados

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Lacuna de testes |
| Módulo | Testes / Backend |
| Arquivos | `*/tests*.py` e `*/test_*.py` (14 arquivos, 239 testes) |

**Descrição.** A suíte é extensa e passa, mas nenhum teste exercita os comportamentos que falharam na sondagem:
- permissão do `revenue-report`;
- status após reagendamento;
- troca de serviço no fim do expediente;
- fechamento antes da abertura;
- barbearia inativa;
- e-mail com maiúsculas;
- autorrebaixamento e autodesativação do admin;
- "realizado" no futuro;
- horários para data passada;
- exposição de e-mail de barbeiros.

**Evidência.** Busca por `revenue` nos arquivos de teste: zero. Os demais cenários falharam na sondagem com a suíte verde. Distribuição: accounts 82, appointments 98, barbershops 40, services 19.

**Impacto.** A suíte transmite uma segurança que não cobre essas regras; correções futuras podem regredir sem aviso.

**Como reproduzir.** Rodar `python manage.py test` (239 OK) e, em seguida, as requisições descritas em SEC-02, BUS-01, BUS-02, BUS-03, BUS-04, BUS-05, BUS-07, BUS-10, AUTH-02 e SEC-03.

**Solução recomendada.** Criar um teste de regressão para cada item corrigido, escrito antes da correção, que falhe no código atual.

**Critério de aceitação.**
- [ ] Cada bug confirmado desta auditoria tem teste que falha antes e passa depois da correção.

---

### DOC-01 — Documentação da API contradiz o comportamento

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Documentação desatualizada |
| Módulo | Documentação / Integração |
| Arquivos | `docs/arquitetura/DOCUMENTACAO_API.md` |

**Descrição.** O documento diverge da API em vários pontos:

| Linha | Documentação diz | Comportamento real |
|---|---|---|
| 82 | Access expira em 60 minutos | 15 minutos |
| 77, 91, 99 | Refresh retornado e enviado no corpo | Refresh apenas em cookie HttpOnly; o corpo é ignorado |
| 96 | Logout responde 205 | Responde 204 |
| 126 | `DELETE /users/{id}/` remove usuário | Desativa a conta; barbeiros e serviços também são apenas desativados; barbearia exige `?confirmar=<nome>` e só marca inativa |
| 141–142 | Após criar usuário barbeiro, criar perfil em `POST /barbers/` | `POST /users/` com `especialidade` cria o perfil na mesma transação; `especialidade` é obrigatória para barbeiro |
| 399–402 | Recuperação de senha e relatórios não implementados | Existem `/auth/password/change/`, `/auth/password/reset/`, `/auth/password/reset/confirm/` e `revenue-report` |
| — | — | Não documentados: `revenue-report`, `exclude_appointment_id`, `preco_historico`, `?ativo=all\|false` (inclusive a necessidade de `?ativo=all` para editar serviço inativo) |

A branch `release/barberpro-academica-v1` tem parte dessas correções (commit `67ef6e3`), que não voltaram para `desenvolvimento`.

**Evidência.** Comparação linha a linha com as sondagens e o código.

**Impacto.** Quem integrar pela documentação implementa errado. Foi o que aconteceu com o frontend antigo, que tratava desativação como exclusão e recebia 404 ao editar serviço inativo.

**Como reproduzir.** Seguir a documentação para fazer logout com refresh no corpo → a API ignora o corpo e responde 204 usando o cookie.

**Solução recomendada.** Gerar a documentação a partir do código com OpenAPI (drf-spectacular) ou revisar o documento contra os testes; trazer as correções da `release`.

**Critério de aceitação.**
- [ ] Cada endpoint documentado corresponde ao comportamento testado.
- [ ] Os endpoints e parâmetros listados acima estão documentados.

---

### REPO-01 — Virtualenv versionado no git

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Dívida técnica |
| Módulo | Repositório |
| Arquivos | `venv312/` (4.875 arquivos versionados); `.gitignore` |

**Descrição.** O ambiente virtual `venv312/` foi commitado (commit `2a8047f`) e representa **96% dos arquivos versionados**, incluindo binários `.so` compilados para Linux x86_64. A entrada `venv312/` foi adicionada ao `.gitignore` depois, sem efeito sobre arquivos já rastreados.

**Evidência.** `git ls-files | wc -l` = 5076; `git ls-files | grep -c '^venv312/'` = 4875.

**Impacto.** Repositório pesado; diffs e buscas poluídos; binários incompatíveis com outras plataformas; atualizações de dependências geram milhares de arquivos alterados.

**Como reproduzir.** Executar os dois comandos acima.

**Solução recomendada.** Em um commit dedicado: `git rm -r --cached venv312` (a pasta local permanece) e confirmar que o `.gitignore` cobre todos os ambientes virtuais.

**Critério de aceitação.**
- [ ] `git ls-files | grep -c '^venv312/'` retorna 0.
- [ ] O ambiente local continua funcionando.

---

### SA-01 — Sem painel de Super Admin

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Super Admin |
| Arquivos | `accounts/admin.py`, `barbershops/admin.py`, `services/admin.py`, `appointments/admin.py`; branch `feature/painel-super-admin` |

**Descrição.**
- **O que existe:** o Django Admin, com os models registrados (listas, filtros e buscas básicos); o superusuário enxerga todos os tenants pela API, segundo o código do `TenantScopedQuerysetMixin`; a exclusão de barbearia é restrita a `is_staff`.
- **O que está incompleto ou ausente:** painel próprio, lista de barbearias com indicadores, suspensão efetiva (ver BUS-02), métricas da plataforma, gestão de planos, acesso de suporte auditado.
- A branch `feature/painel-super-admin` aponta **para o mesmo commit** de `desenvolvimento`, sem nenhum trabalho.
- **Isolamento verificado:** um admin de barbearia **não** acessa dados de outra (16/16 tentativas bloqueadas). O acesso global do superusuário foi verificado só por leitura de código.

**Evidência.** `git rev-list --count desenvolvimento..feature/painel-super-admin` = 0 e vice-versa; leitura dos `admin.py` e do mixin.

**Impacto.** Operar a plataforma (suporte, suspensão, acompanhamento de clientes) exige acesso direto ao Django Admin, sem regras de negócio e com risco de edição indevida de dados.

**Como reproduzir.** Entrar como superusuário: não há tela da plataforma no frontend; a gestão é feita apenas em `/admin/` do Django.

**Solução recomendada.**
- Definir o escopo do Super Admin: barbearias, suspensão/reativação, métricas, usuários, auditoria.
- Implementar endpoints restritos a staff, uma área no frontend e registro das ações de suporte.

**Critério de aceitação.**
- [ ] O operador da plataforma lista, suspende e reativa barbearias e consulta métricas sem usar o Django Admin.
- [ ] As ações ficam registradas.

---

### SAAS-01 — Sem notificações, LGPD e cobrança

| Campo | Valor |
|---|---|
| Gravidade | P2 — Médio |
| Tipo | Funcionalidade ausente |
| Módulo | Produto |
| Arquivos | — (inexistentes no projeto) |

**Descrição.** Faltam elementos de um SaaS comercial:
- **notificações:** confirmação e lembrete de agendamento por e-mail ou WhatsApp;
- **LGPD:** registro de consentimento, exportação dos dados do titular e exclusão/anonimização real (hoje "excluir" só desativa e mantém todos os dados pessoais);
- **planos, assinatura e cobrança das barbearias.**

**Evidência.** Ausência de models, endpoints, configurações e telas correspondentes.

**Impacto.** Impede a comercialização. A falta de lembretes aumenta faltas, e o tratamento de dados pessoais fica exposto a riscos legais.

**Como reproduzir.** Verificar que não há configuração de mensageria, tela de privacidade ou exportação de dados, nem cadastro de planos.

**Solução recomendada.** Tratar como épicos separados, nesta ordem sugerida: notificações (depende de AUTH-01) → LGPD (anonimização e exportação) → planos e cobrança (depende de SA-01 e BUS-02).

**Critério de aceitação.**
- [ ] Cada épico tem requisitos escritos e critérios próprios.
- [ ] Lembretes são enviados; o titular consegue exportar e solicitar exclusão; a barbearia tem um plano associado.

---

## 10. Problemas P3 — Baixo (21)

### SEC-06 — Chave secreta antiga no histórico do git

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Risco potencial |
| Módulo | Repositório |
| Arquivos | `core/settings.py` no histórico (commits `22575b0` e `3f46df2`) |

**Descrição.** Uma `SECRET_KEY` fixa existia num arquivo de configurações antigo e permanece no histórico do git. O arquivo atual lê a chave do ambiente.

**Evidência.** `git grep` no histórico encontrou a atribuição; o valor não foi exibido nem copiado.

**Impacto.** Nenhum, se essa chave nunca foi nem for reutilizada. Se o repositório for público e a chave tiver sido usada em algum ambiente, ela deve ser considerada comprometida.

**Como reproduzir.** `git log --all --oneline -- core/settings.py` lista os commits; `git grep -c "SECRET_KEY = '" 22575b0 -- core/settings.py` conta a ocorrência sem exibir o valor.

**Solução recomendada.** Confirmar que a chave não é usada em nenhum ambiente. Se o repositório for público, considerar a limpeza do histórico (`git filter-repo`), avaliando o impacto em clones existentes.

**Critério de aceitação.**
- [ ] Declaração de que a chave não é usada em nenhum ambiente, ou histórico limpo.

---

### SEC-08 — Sem verificação de e-mail no cadastro

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Funcionalidade ausente |
| Módulo | Autenticação |
| Arquivos | `accounts/views.py` (`RegistrationView`); `barbershops/views.py` (`perform_create`) |

**Descrição.** Qualquer pessoa cria uma conta sem confirmar o e-mail e, em seguida, uma barbearia (um tenant por conta), limitado apenas pelo throttling de cadastro (10/h por IP).

**Evidência.** Leitura de código; fluxo de cadastro e onboarding testado na interface.

**Impacto.** Contas com e-mail digitado errado ficam inacessíveis na recuperação de senha; criação de tenants de spam.

**Como reproduzir.** Cadastrar uma conta com e-mail inexistente: o sistema entra imediatamente e permite criar barbearia.

**Solução recomendada.** Confirmação de e-mail (link com token) antes de liberar o onboarding (depende de AUTH-01).

**Critério de aceitação.**
- [ ] Contas não confirmadas não conseguem criar barbearia.
- [ ] O link de confirmação expira.

---

### BUS-10 — Horários livres devolvidos para datas passadas

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Bug confirmado |
| Módulo | Agendamentos |
| Arquivos | `appointments/views.py` (`available_slots`) |

**Descrição.** O endpoint só descarta horários já passados quando a data consultada é **hoje**. Para datas anteriores, devolve todos os horários do expediente, embora a criação seja recusada depois.

**Evidência.** Sondagem 1: data de ontem → HTTP 200 com **18 horários**.

**Impacto.** Inconsistência da API; um cliente de integração pode exibir horários impossíveis. O frontend atual não oferece datas passadas, então o usuário final não é afetado hoje.

**Como reproduzir.** `GET /api/v1/appointments/available-slots/?barbeiro=<id>&servico=<id>&data=<ontem>` → lista preenchida.

**Solução recomendada.** Para `data < hoje`, retornar lista vazia (ou 400 com mensagem).

**Critério de aceitação.**
- [ ] Consulta para data passada retorna lista vazia ou 400.
- [ ] Teste do caso.

---

### BUS-12 — Regras de cancelamento e edição do barbeiro inconsistentes

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Bug confirmado (inconsistência) |
| Módulo | Agendamentos |
| Arquivos | `appointments/views.py` (`get_permissions`); `appointments/serializers.py` (`validate`) |

**Descrição.**
- O comentário em `get_permissions` afirma que barbeiros não podem cancelar horários de clientes, e `DELETE` é de fato proibido a eles (403). Porém `PATCH status=cancelado` é aceito.
- Por leitura de código, o serializer só impede que o **cliente** troque o campo `cliente`; o barbeiro pode reatribuir o próprio agendamento a outro cliente do tenant.

**Evidência.** Sondagem 1: barbeiro `PATCH status=cancelado` → HTTP 200. A troca de `cliente` pelo barbeiro foi constatada apenas na leitura de `AppointmentSerializer.validate`, sem execução.

**Impacto.** A regra de negócio fica ambígua: o mesmo resultado é proibido por um caminho e permitido por outro.

**Como reproduzir.** Como barbeiro, `DELETE /api/v1/appointments/<id próprio>/` → 403; `PATCH /api/v1/appointments/<id próprio>/` com `{"status": "cancelado"}` → 200.

**Solução recomendada.** Definir se o barbeiro pode cancelar e trocar o cliente, aplicar a mesma regra nos dois caminhos e atualizar o comentário.

**Critério de aceitação.**
- [ ] `DELETE` e `PATCH` têm o mesmo resultado para o barbeiro.
- [ ] A troca de cliente segue a regra definida.
- [ ] Testes de ambos.

---

### API-02 — `revenue_report` com `.extra()` e dia calculado em UTC

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica |
| Módulo | Relatórios |
| Arquivos | `appointments/views.py` (`revenue_report`, trecho `daily`) |

**Descrição.** O agrupamento diário usa `qs.extra(select={'date': 'DATE(data_hora)'})`. `.extra()` é desaconselhado pelo Django. Com `USE_TZ=True` a conexão trabalha em UTC, então `DATE()` agrupa pelo dia em UTC: atendimentos realizados depois das 21:00 (horário de Brasília) entram no dia seguinte.

**Evidência.** Leitura de código. O efeito do fuso **não foi reproduzido** porque a API não permite criar atendimentos no passado e os dados de teste foram gerados em horário comercial.

**Impacto.** Faturamento diário deslocado para atendimentos noturnos; dependência de SQL específico de banco.

**Como reproduzir (não executado).** Pelo Django Admin, registrar um atendimento realizado às 22:00 de um dia X e consultar `revenue-report`: ele aparece em X+1.

**Solução recomendada.** `TruncDate('data_hora', tzinfo=<fuso local>)` com `values().annotate()`, sem `.extra()`.

**Critério de aceitação.**
- [ ] Atendimento às 22:00 aparece no dia correto.
- [ ] Teste com horário noturno.
- [ ] Nenhum uso de `.extra()`.

---

### DATA-02 — Preços históricos antigos estimados

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica (limitação documentada) |
| Módulo | Banco |
| Arquivos | `appointments/migrations/0008_populate_preco_historico.py` |

**Descrição.** Agendamentos anteriores à criação de `preco_historico` (migração 0007) receberam o preço vigente do serviço no momento da migração, não o preço praticado à época. O próprio arquivo de migração documenta isso como estimativa.

**Evidência.** Comentário e código da migração 0008.

**Impacto.** Relatórios financeiros de períodos anteriores à migração podem não refletir os valores cobrados.

**Como reproduzir.** Ler o cabeçalho do arquivo de migração.

**Solução recomendada.** Registrar a limitação na documentação e, se necessário, sinalizar nos relatórios os períodos estimados.

**Critério de aceitação.**
- [ ] Documentação de relatórios menciona a estimativa e o período afetado.

---

### DATA-03 — Divergência de versão de collation no Postgres

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Risco potencial (operacional) |
| Módulo | Banco |
| Arquivos | — (configuração do servidor Postgres no container `barbershop_db`) |

**Descrição.** O Postgres avisa, a cada conexão, que o banco foi criado com a versão de collation 2.43 e o sistema operacional fornece 2.44.

**Evidência.** Aviso exibido em `manage.py test`, `showmigrations` e consultas (`integridade-banco-real.txt`).

**Impacto.** Índices sobre texto (como o de unicidade de `email`) podem ficar com ordenação inconsistente, em casos raros causando buscas incorretas ou violações de unicidade não detectadas.

**Como reproduzir.** Executar qualquer comando Django contra o Postgres e observar o aviso.

**Solução recomendada.** Em janela de manutenção, com backup: `REINDEX DATABASE barbershop_db;` e `ALTER DATABASE barbershop_db REFRESH COLLATION VERSION;`.

**Critério de aceitação.**
- [ ] O aviso deixa de aparecer.

---

### FE-03 — Falha de recarga sem feedback

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Bug confirmado (por leitura de código) |
| Módulo | Frontend |
| Arquivos | `frontend/src/hooks/useAsyncData.ts`; telas com botão "Atualizar" (`AdminAppointmentsPage.tsx`, `BarberAgendaPage.tsx`) e demais que usam `error && !data` |

**Descrição.** As telas exibem o estado de erro apenas quando não há dados (`error && !data`). Se uma recarga falhar com dados já na tela (ex.: botão "Atualizar" com a API fora do ar), a barra de atualização some e nenhuma mensagem aparece; o usuário vê dados antigos sem saber.

**Evidência.** Leitura de código. A queda da API foi testada apenas no carregamento inicial da sessão, onde há tratamento (tela "Sem conexão").

**Impacto.** O usuário pode tomar decisões com informações desatualizadas.

**Como reproduzir.** Abrir "Agendamentos", desligar a API e clicar em "Atualizar": nada indica a falha.

**Solução recomendada.** Exibir aviso ou toast quando houver `error` com dados presentes, por exemplo "Não foi possível atualizar; mostrando dados de HH:MM".

**Critério de aceitação.**
- [ ] Falha de recarga com dados na tela gera mensagem visível.

---

### FE-04 — Contador "a confirmar" inclui horários vencidos

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Bug confirmado (inconsistência, por leitura de código) |
| Módulo | Frontend |
| Arquivos | `frontend/src/components/AppLayout.tsx` (`PendingIndicator`) |

**Descrição.** O indicador do topo conta `GET /appointments/?status=agendado` sem filtro de data, então inclui horários passados nunca confirmados.

**Evidência.** Leitura de código. No banco de teste não havia vencidos "agendado", então não foi observado na tela.

**Impacto.** O número pode ser maior do que as confirmações realmente pendentes.

**Como reproduzir.** Ter um agendamento passado com status "agendado": ele é contado em "a confirmar".

**Solução recomendada.** Contar apenas horários futuros e mostrar os vencidos separadamente (depende de BUS-08 e do filtro de data em API-01).

**Critério de aceitação.**
- [ ] O contador considera apenas horários futuros.

---

### FE-05 — Fuso horário fixo no frontend

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica |
| Módulo | Integração |
| Arquivos | `frontend/src/utils/format.ts` (`SHOP_TZ = 'America/Sao_Paulo'`); `config/settings.py` (`TIME_ZONE`) |

**Descrição.** O frontend exibe datas no fuso `America/Sao_Paulo`, fixo no código, enquanto o backend lê `TIME_ZONE` das configurações.

**Evidência.** Leitura de código.

**Impacto.** Se o backend operar em outro fuso, a interface mostra horários diferentes dos validados pelo servidor.

**Como reproduzir.** Alterar `TIME_ZONE` no backend: o frontend continua exibindo em horário de Brasília.

**Solução recomendada.** Expor o fuso da barbearia na API (por exemplo em `/barbershops/`) e usá-lo no frontend.

**Critério de aceitação.**
- [ ] O fuso exibido vem da API.

---

### FE-06 — Sem página 404

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Funcionalidade ausente |
| Módulo | Frontend |
| Arquivos | `frontend/src/App.tsx` (rota `*`) |

**Descrição.** Qualquer rota inexistente redireciona silenciosamente para o início.

**Evidência.** `<Route path="*" element={<Navigate to="/" replace />} />`.

**Impacto.** Links quebrados não são percebidos; o usuário não entende por que caiu no início.

**Como reproduzir.** Acessar `/qualquer-coisa`: a página inicial é exibida sem aviso.

**Solução recomendada.** Página "não encontrada" com link para o início.

**Critério de aceitação.**
- [ ] Rota inexistente exibe a página 404.

---

### FE-07 — Código morto no frontend

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica |
| Módulo | Frontend |
| Arquivos | `frontend/src/api/endpoints.ts`; `frontend/src/utils/format.ts`; `frontend/src/components/Icons.tsx` |

**Descrição.** Exportações sem nenhum uso:
- `getTotalServices`, `getTotalBarbers`, `isPast`, `formatDateTime`;
- 14 ícones: `StarIcon`, `BadgeIcon`, `BuildingIcon`, `RazorIcon`, `ChairIcon`, `BellIcon`, `LockIcon`, `KeyIcon`, `TrendingUpIcon`, `ReceiptIcon`, `AnalyticsIcon`, `FilterIcon`, `TrashIcon`, `MinusIcon`.

**Evidência.** Busca de referências em `src` (`verificacoes-backend-e-build.txt`).

**Impacto.** Ruído de manutenção.

**Como reproduzir.** Buscar cada símbolo em `frontend/src`: só aparece na própria declaração.

**Solução recomendada.** Remover as exportações não utilizadas.

**Critério de aceitação.**
- [ ] Nenhuma exportação sem uso, verificável com ferramenta como `ts-prune` ou `knip`.

---

### FE-08 — Fonte carregada do Google Fonts

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Melhoria opcional |
| Módulo | Frontend |
| Arquivos | `frontend/index.html` |

**Descrição.** A fonte Archivo é baixada de `fonts.googleapis.com` a cada visita.

**Evidência.** `<link href="https://fonts.googleapis.com/css2?family=Archivo…">` no `index.html`.

**Impacto.** Dependência de serviço externo (fonte alternativa se o serviço falhar) e envio do IP do usuário a terceiros, um ponto de atenção para a LGPD.

**Como reproduzir.** Abrir a aba Rede do navegador: há requisições a `fonts.googleapis.com` e `fonts.gstatic.com`.

**Solução recomendada.** Hospedar a fonte junto com o app (ex.: pacote `@fontsource-variable/archivo`).

**Critério de aceitação.**
- [ ] Nenhuma requisição a domínios do Google ao carregar o app.

---

### FE-09 — Sem tela de logo; barbeiro não reagenda pela interface

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Funcionalidade incompleta |
| Módulo | Frontend |
| Arquivos | `frontend/src/pages/AdminBarbershopPage.tsx`; `frontend/src/pages/BarberAgendaPage.tsx` |

**Descrição.** A API aceita upload de logo da barbearia (`multipart/form-data`), mas não há campo na tela. O barbeiro pode remarcar horários pela API, mas a agenda dele só oferece ações de status.

**Evidência.** Leitura das telas e do serializer.

**Impacto.** Funcionalidades disponíveis na API ficam inacessíveis ao usuário.

**Como reproduzir.** Abrir "Dados da barbearia": não há campo de logo. Abrir "Minha agenda" como barbeiro: não há "Reagendar".

**Solução recomendada.** Campo de upload com pré-visualização e limite de tamanho, que depende da solução de mídia em OPS-01. Avaliar com o negócio se o barbeiro deve reagendar.

**Critério de aceitação.**
- [ ] Logo enviado e exibido na interface.
- [ ] Reagendamento pelo barbeiro implementado ou explicitamente fora do escopo.

---

### FE-11 — Duas fontes de cálculo de faturamento

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Risco potencial |
| Módulo | Integração |
| Arquivos | `frontend/src/pages/AdminDashboardPage.tsx`; `appointments/views.py` (`revenue_report`) |

**Descrição.** O painel calcula faturamento, ticket médio e rankings no navegador, a partir da lista completa de agendamentos e no fuso da barbearia. O backend tem outro cálculo em `revenue-report`, com o dia agrupado em UTC (API-02).

**Evidência.** Leitura de código.

**Impacto.** Os números do painel e do relatório da API podem divergir para atendimentos noturnos, minando a confiança nos indicadores.

**Como reproduzir (não executado).** Com atendimentos realizados após as 21:00, comparar o faturamento diário do painel com `daily` do `revenue-report`.

**Solução recomendada.** Uma única fonte: endpoint de métricas no backend (corrigido para o fuso local), consumido pelo painel.

**Critério de aceitação.**
- [ ] Painel e API retornam os mesmos números para o mesmo período.

---

### DOC-02 — README: testes não usam SQLite por padrão

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Documentação incorreta |
| Módulo | Documentação |
| Arquivos | `README.md` (seção "Testes") |

**Descrição.** O README afirma que `python manage.py test` usa SQLite em memória. Na prática, sem `--settings`, o runner usa `config.settings` (Postgres), criando e destruindo um banco de teste próprio. SQLite exige `--settings=config.test_settings`.

**Evidência.** A execução de `python manage.py test` nesta auditoria emitiu avisos do Postgres ao destruir o banco de teste (`verificacoes-backend-e-build.txt`); `config/test_settings.py` é o único arquivo que configura SQLite.

**Impacto.** Quem segue o README sem o Postgres rodando vê os testes falharem por conexão; quem tem o Postgres rodando testa nele sem saber.

**Como reproduzir.** Com o container do banco parado, `python manage.py test` falha ao conectar.

**Solução recomendada.** Corrigir o README com os dois comandos e quando usar cada um.

**Critério de aceitação.**
- [ ] README descreve corretamente o banco usado por cada comando.

---

### DOC-03 — Comentários obsoletos sobre o app `core`

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica |
| Módulo | Backend |
| Arquivos | `accounts/models.py` (linha 7: `core.mixins`); `config/settings.py` (linha 54: `"core" vem primeiro`) |

**Descrição.** Comentários referenciam o antigo app `core`, substituído por `config`.

**Evidência.** Leitura dos arquivos.

**Impacto.** Confunde quem lê o código pela primeira vez.

**Como reproduzir.** `grep -rn "core" accounts/models.py config/settings.py`.

**Solução recomendada.** Atualizar os comentários para `config.mixins` e a lista atual de apps.

**Critério de aceitação.**
- [ ] Nenhuma referência ao app `core` em comentários.

---

### REPO-02 — Arquivos soltos e rascunhos no repositório

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica |
| Módulo | Repositório |
| Arquivos | `gerar_zip.py`; `requisitos_barbearia.docx`; `docs/auditorias/historico/` (21 arquivos); locais não versionados: `db.sqlite3` (217 KB), `test.db` (vazio), `outputs/` e `work/` (vazios), `frontend/.pytest_cache` |

**Descrição.** O repositório e a pasta de trabalho acumulam:
- **versionados:** utilitários e rascunhos — um script de geração de zip; 21 arquivos de respostas e verificações anteriores em `docs/auditorias/historico/`, incluindo `debug_test.py` e um segundo `requirements.txt`;
- **na pasta local:** bancos SQLite soltos e pastas vazias.

**Evidência.** Listagens da raiz e de `docs/auditorias/historico/` (`verificacoes-backend-e-build.txt`).

**Impacto.** Dificulta a navegação e a avaliação do projeto; o segundo `requirements.txt` pode ser confundido com o oficial.

**Como reproduzir.** `ls` na raiz e em `docs/auditorias/historico/`.

**Solução recomendada.** Mover os rascunhos para fora do repositório ou consolidá-los num único relatório histórico; remover os arquivos locais desnecessários.

**Critério de aceitação.**
- [ ] A raiz contém apenas arquivos do projeto.
- [ ] `docs/` tem uma estrutura clara, sem rascunhos.

---

### REPO-03 — Branches dessincronizadas

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Dívida técnica |
| Módulo | Repositório |
| Arquivos | Branches `master`, `feature/painel-super-admin`, `release/barberpro-academica-v1` |

**Descrição.**
- `master` está 30 commits atrás de `desenvolvimento`.
- `feature/painel-super-admin` está no mesmo commit de `desenvolvimento`.
- `release/barberpro-academica-v1` tem 1 commit próprio (`67ef6e3`, documentação e comentários), que não voltou para `desenvolvimento`.

**Evidência.** `git rev-list --count` entre as branches.

**Impacto.** Não fica claro qual branch é a referência; correções de documentação ficam presas na `release`.

**Como reproduzir.** `git rev-list --count desenvolvimento..master` (0) e `master..desenvolvimento` (30); `desenvolvimento..release/barberpro-academica-v1` (1).

**Solução recomendada.** Definir o fluxo de branches (ex.: `master` = produção), sincronizar a documentação da `release` e remover a branch vazia ou iniciar o trabalho nela.

**Critério de aceitação.**
- [ ] Fluxo documentado no README.
- [ ] Nenhuma correção existe só na `release`.

---

### TEST-02 — Cobertura de código não medida

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Lacuna de testes |
| Módulo | Testes |
| Arquivos | `requirements.txt` (sem `coverage`) |

**Descrição.** Não há medição de cobertura; não é possível dizer quais linhas e ramificações os 239 testes exercitam.

**Evidência.** `coverage` não está instalado nem configurado.

**Impacto.** Lacunas como as do TEST-01 passam despercebidas.

**Como reproduzir.** `coverage run manage.py test` não está disponível no ambiente.

**Solução recomendada.** Adicionar `coverage` como dependência de desenvolvimento e publicar o relatório no CI, com meta mínima.

**Critério de aceitação.**
- [ ] Relatório de cobertura gerado no CI, com meta definida.

---

### FE-12 — Banco real quase vazio para a demonstração

| Campo | Valor |
|---|---|
| Gravidade | P3 — Baixo |
| Tipo | Melhoria opcional |
| Módulo | Apresentação |
| Arquivos | — (dados do Postgres local) |

**Descrição.** O banco real tem 2 barbearias, 6 usuários, **1 serviço e 1 agendamento**. Não é bug, mas o painel, os gráficos e o quadro do dia vão aparecer praticamente vazios numa apresentação.

**Evidência.** `integridade-banco-real.txt`.

**Impacto.** A apresentação não demonstra os indicadores, gráficos e agenda.

**Como reproduzir.** Entrar como admin da barbearia existente e abrir o painel.

**Solução recomendada.** Comando de gerenciamento `seed_demo` que cria, num tenant separado, registros **reais** (persistidos e manipuláveis pela aplicação, não números fixos na interface): serviços, equipe, clientes e histórico de agendamentos.

**Critério de aceitação.**
- [ ] O comando cria o tenant de demonstração de forma idempotente.
- [ ] O painel exibe dados significativos sem alterar os tenants existentes.

---

## 11. Itens não verificados (5)

| # | Item | Por que não foi verificado | Como verificar |
|---|---|---|---|
| NV-1 | Entrega real de e-mail (recuperação de senha) | Não há servidor SMTP configurado; enviar e-mails a terceiros estaria fora do escopo | Configurar o backend de console ou um SMTP de teste (ex.: Mailpit) e solicitar a recuperação |
| NV-2 | Concorrência de agendamentos no Postgres | O código usa `select_for_update` nos barbeiros e há testes específicos (`config/test_postgres_settings.py`), mas não foi executada carga concorrente | `python manage.py test --settings=config.test_postgres_settings` e um teste de carga com requisições simultâneas para o mesmo horário |
| NV-3 | Leitor de tela (NVDA, VoiceOver) | Validados apenas teclado, foco visível, rótulos ARIA e contraste calculado | Percorrer login, agendamento e painel com NVDA (Windows) e VoiceOver (macOS/iOS) |
| NV-4 | Tablet (~820 px) e navegadores Chrome e Safari | Capturas feitas apenas em 1440 px e 390 px, no Firefox | Repetir os fluxos de interface nesses tamanhos e navegadores |
| NV-5 | Rate limiting real | O ambiente isolado desliga o throttling para permitir as sondagens; só a configuração foi revisada (ver SEC-05) | Com as configurações reais, enviar 6 tentativas de login em 1 minuto e esperar HTTP 429 na 6ª |

---

## 12. Resultados dos testes executados

Todos os registros brutos estão em [`docs/auditoria/evidencias/`](auditoria/evidencias/README.md).

### 12.1 Backend

| Verificação | Resultado |
|---|---|
| `python manage.py test` (2 execuções) | **239 testes, OK** (126 s); aviso `InsecureKeyLengthWarning` (SEC-01). Rodou no Postgres, criando um banco de teste próprio (DOC-02) |
| Distribuição dos testes | accounts 82 · appointments 98 · barbershops 40 · services 19 |
| `makemigrations --check --dry-run` | `No changes detected` |
| `showmigrations` no Postgres real (leitura) | Todas aplicadas |
| `check --deploy` (DEBUG=False, chave temporária) | 1 aviso: `security.W021` (HSTS preload, opcional) |
| Consultas SQL por endpoint | 2 a 4 consultas; sem N+1 |

### 12.2 Sondagens da API isolada

| Sondagem | Verificações | OK | Falhas | Problemas associados |
|---|---|---|---|---|
| Isolamento entre barbearias | 16 | 16 | 0 | — |
| Perfis e permissões | 13 | 10 | 3 | SEC-02 (2), SEC-03 |
| Regras de negócio e recursos da API | 13 | 1 | 12 | BUS-01, BUS-02, BUS-03, BUS-04, BUS-05, BUS-07, BUS-10, AUTH-02, API-01 (4); BUS-12 registrado como inconsistência |
| **Total da sondagem 1** | **42** | **27** | **15** | |
| Sessão e administração (sondagem 2) | 12 observações | 10 conforme esperado | 2 | BUS-01 (autodesativação e login bloqueado) |
| Agenda (sondagem 3) | 1 | — | 1 | BUS-06, BUS-11 |
| Forja de JWT | 3 | — | — | SEC-01 (impacto detalhado) |

### 12.3 Frontend

| Verificação | Resultado |
|---|---|
| `tsc -b` | Sem erros |
| ESLint (`--max-warnings=0`) | 0 erros, 0 avisos |
| `npm run build` | OK. JS inicial 424,02 kB (134,96 kB gzip); CSS 44,91 kB |
| Testes automatizados de frontend | Inexistentes (FE-02) |
| Fluxos no navegador — admin | Login, detalhes no quadro, Esc fecha modal, confirmar, cancelar com diálogo, validação, criar serviço com "35,50", reativar serviço inativo — sem erros de console ou API |
| Fluxos no navegador — cliente | Agendar (serviço → barbeiro → dia → horário → confirmar), reagendar, cancelar, editar perfil — sem erros |
| Fluxos no navegador — barbeiro | Visão "a confirmar", confirmar, marcar realizado — sem erros |
| Teclado | Tab inicia em "Pular para o conteúdo"; menu do usuário com Enter/setas/Esc devolvendo o foco; menu lateral no celular com foco e Esc |
| Queda real da API | Tela "Sem conexão com o servidor", sessão preservada e restaurada sem novo login |
| Responsividade | 1440 px e 390 px verificados; tablet e outros navegadores não verificados (NV-4) |

### 12.4 Banco real (somente leitura)

Nenhuma inconsistência encontrada nas 17 contagens de integridade: tenants coerentes, perfis sincronizados, preços históricos preenchidos, nenhum agendamento órfão ou vencido sem desfecho. Volume mínimo de dados (FE-12) e aviso de collation (DATA-03).

### 12.5 Repositório

5.076 arquivos versionados, 4.875 do `venv312/` (REPO-01). `.env` nunca commitado. Chave antiga no histórico (SEC-06). Branches dessincronizadas (REPO-03). Sem CI, Dockerfile, health check, cache, logging ou e-mail configurados (OPS-01, OBS-01, SEC-05, AUTH-01).

---

## 13. Evidências visuais

Capturas feitas no ambiente isolado com dados **fictícios**. Telas que exibiam e-mails e estados visuais já corrigidos foram excluídas.

| Arquivo | O que mostra |
|---|---|
| [`01-painel-admin-desktop.png`](auditoria/evidencias/01-painel-admin-desktop.png) | Painel: indicadores de 30 dias, quadro do dia, faturamento diário, próximos atendimentos e rankings |
| [`02-quadro-do-dia.png`](auditoria/evidencias/02-quadro-do-dia.png) | Quadro por barbeiro com blocos pela duração real e status com forma e texto |
| [`03-agendamentos-admin.png`](auditoria/evidencias/03-agendamentos-admin.png) | Agendamentos agrupados por dia, filtros e ações de status válidas |
| [`04-dialogo-cancelamento.png`](auditoria/evidencias/04-dialogo-cancelamento.png) | Confirmação antes de cancelar |
| [`05-validacao-formulario-servico.png`](auditoria/evidencias/05-validacao-formulario-servico.png) | Mensagens de validação no formulário |
| [`06-agenda-barbeiro.png`](auditoria/evidencias/06-agenda-barbeiro.png) | Agenda do barbeiro com intervalos livres |
| [`07-agendamento-horarios.png`](auditoria/evidencias/07-agendamento-horarios.png) | Escolha de data e horários reais |
| [`08-api-fora-do-ar.png`](auditoria/evidencias/08-api-fora-do-ar.png) | Estado de queda da API com sessão preservada |
| [`09-menu-celular.png`](auditoria/evidencias/09-menu-celular.png) | Menu lateral no celular |
| [`10-servicos-celular.png`](auditoria/evidencias/10-servicos-celular.png) | Tabela convertida em cartões no celular (capturada antes da correção do ícone da marca no topo) |

---

## 14. Plano de correção por prioridade

### Fase 0 — Antes da apresentação

Alterações pequenas no backend, cada uma com teste de regressão. **Exigem autorização para alterar o código.**

| Ordem | Problema | Esforço estimado | Observação |
|---|---|---|---|
| 1 | SEC-01 | Baixo | Gerar nova chave; validação de tamanho em `settings.py`. Encerra sessões existentes |
| 2 | SEC-02 | Baixo | Permissão de admin na action |
| 3 | BUS-01 | Baixo | Bloquear autorrebaixamento/autodesativação e último admin |
| 4 | BUS-03 | Baixo | Voltar para "agendado" no reagendamento pelo cliente |
| 5 | BUS-04 | Baixo | Revalidar horário na troca de serviço |
| 6 | BUS-05 | Baixo | Validar fechamento > abertura |
| 7 | BUS-07 | Baixo | "Realizado" só após o início |
| 8 | TEST-01 | Baixo/médio | Testes de regressão dos itens 2 a 7 |
| 9 | FE-12 | Baixo (opcional) | `seed_demo` com dados reais num tenant próprio |

### Fase 1 — Antes de qualquer uso real

| Problema | Tema |
|---|---|
| BUS-02 | Suspensão efetiva de barbearia |
| AUTH-01 | E-mail transacional e link de recuperação |
| AUTH-02 | E-mail sem diferenciar maiúsculas |
| SEC-03 | Ocultar e-mail de barbeiros |
| SEC-07 | Duração mínima no model |
| DATA-01 | Reverso seguro da migração 0008 |
| API-01 | Busca, ordenação, filtros, `page_size`; frontend usando o servidor |
| FE-01 | Error boundary |
| OBS-01 | Logs, monitoramento, auditoria, health check |
| OPS-01 | Dockerfile, CI, estáticos/mídia, rotinas, backup |
| SEC-05 | Cache compartilhado para throttling |
| DOC-01, DOC-02 | Documentação fiel ao comportamento |
| REPO-01 | Remover `venv312/` do versionamento |
| FE-02 | Testes de frontend |

### Fase 2 — Produto

| Problema | Tema |
|---|---|
| PROD-01 | Página pública da barbearia / convite de clientes |
| BUS-06 | Grade de funcionamento, folgas e disponibilidade |
| BUS-08 | "Não compareceu" e desfecho de vencidos |
| BUS-09 | Duração histórica |
| BUS-11 | Passo de horários configurável |
| BUS-13 | Tratamento de agendamentos na desativação |
| BUS-14 | Agendamento pelo admin e cliente avulso |
| SA-01 | Painel de Super Admin |
| SAAS-01 | Notificações, LGPD, cobrança |
| SEC-04 | Token só em memória + CSP |
| SEC-08 | Verificação de e-mail |

### Fase 3 — Acabamento

SEC-06, BUS-10, BUS-12, API-02, DATA-02, DATA-03, FE-03, FE-04, FE-05, FE-06, FE-07, FE-08, FE-09, FE-11, DOC-03, REPO-02, REPO-03, TEST-02 e os itens não verificados NV-1 a NV-5.

---

## 15. Respostas objetivas

**O que impede o BarberPro de ser utilizado atualmente?**
- Para demonstração acadêmica, nada bloqueia: os fluxos funcionam de ponta a ponta quando o admin cadastra os clientes.
- Para uma barbearia real:
  - clientes não conseguem se cadastrar sozinhos (PROD-01);
  - dias fechados recebem agendamentos (BUS-06);
  - a recuperação de senha não envia e-mail (AUTH-01);
  - clientes e barbeiros veem o faturamento (SEC-02).

**O que impede de ser considerado pronto para produção?**
- Os dois P0: chave secreta truncada e vazamento de faturamento.
- As regras de negócio P1 confirmadas.
- A ausência de logs, monitoramento, CI e infraestrutura de implantação (OBS-01, OPS-01).
- Rate limiting que não funciona com vários processos (SEC-05).
- A falta de testes para as regras corrigidas e para o frontend (TEST-01, FE-02).

**Quais funcionalidades ainda precisam ser implementadas?**
Autocadastro ou página pública por barbearia; grade de funcionamento, folgas e disponibilidade por barbeiro; e-mail transacional; "não compareceu"; agendamento pelo admin e atendimento avulso; busca, ordenação e filtros na API; tratamento de agendamentos ao desativar pessoas; painel de Super Admin com suspensão efetiva; notificações, LGPD e cobrança; error boundary, página 404 e testes de frontend.

**Quais são os riscos mais graves?**
1. Chave-raiz com 3 caracteres: com qualquer vazamento dos hashes de senha, permite forjar acesso a qualquer conta de qualquer barbearia (SEC-01).
2. Exposição do faturamento a clientes e barbeiros (SEC-02).
3. Barbearia sem administrador por autorrebaixamento ou autodesativação (BUS-01).
4. Suspensão de barbearia sem efeito (BUS-02).
5. Métricas financeiras distorcidas por "realizado" no futuro (BUS-07).

**O que deve ser corrigido primeiro?**
SEC-01 e SEC-02; depois BUS-01, BUS-03, BUS-04, BUS-05 e BUS-07, cada um com teste de regressão (Fase 0).

**O que pode ficar para versões futuras?**
Cobrança e planos, notificações, painel de Super Admin completo, LGPD avançada, passo de horários configurável, duração histórica, hospedagem própria de fontes e os demais itens P3.

---

## 16. Correções em relação a comunicações anteriores

Para manter a rastreabilidade, registro onde este relatório corrige o que foi dito antes nesta auditoria:

| Afirmação anterior | Correção |
|---|---|
| "A `SECRET_KEY` do `.env` tem só 3 caracteres" (entrega do redesign) | A linha no `.env` tem 50 caracteres; o `django-environ` a trunca para 3 por causa de um `#` sem aspas |
| A chave curta permitiria "forjar tokens de qualquer usuário" | O `CHECK_REVOKE_TOKEN` exige um claim derivado do hash da senha: só com a chave, o token forjado é recusado (401). Com acesso aos hashes, é aceito (200). Ver SEC-01 e `forja-de-token-jwt.txt` |
| "14 falhas confirmadas" na sondagem | Foram **15 falhas** em 42 verificações (27 OK) |
| Metodologia com "40 cenários" e divisão 16/6/12/8/4 | Sondagem 1: 42 verificações (16 isolamento, 13 perfis, 13 regras/recursos); sondagem 2: 12 observações de sessão/administração; sondagem 3: 1 verificação de agenda |
| Relatório em `docs/auditorias/AUDITORIA_TECNICA_2026-11-11.md` | Substituído por este documento, que é a versão completa e corrigida. O arquivo anterior não foi removido |
