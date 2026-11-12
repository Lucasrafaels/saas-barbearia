# Auditoria técnica e funcional — BarberPro

**Data:** 11/11/2026 · **Branch auditada:** `desenvolvimento` (commit `ed5e39f` + alterações não commitadas do redesign do frontend) · **Escopo:** backend Django/DRF, frontend React, banco, segurança, testes, documentação e repositório.

> Somente diagnóstico. Nenhuma correção foi aplicada. Nenhum dado do Postgres foi alterado: as checagens no banco real foram consultas de leitura (contagens). Todos os testes dinâmicos (segurança, regras de negócio, fluxos de tela) rodaram contra uma **cópia isolada da API com SQLite descartável** fora do repositório.

## Como a auditoria foi feita

| Método | O que cobriu |
|---|---|
| Leitura de código | Todos os models, serializers, views, permissões, mixins, settings, migrações, admin, frontend completo |
| Sondagem dinâmica da API isolada | 40 cenários: isolamento entre barbearias (16), escalada de privilégio (6), regras de negócio (12), sessão/autenticação (8), recursos de API (4) — com uma segunda e terceira barbearia criadas só no banco descartável |
| Navegador real (Firefox headless) | Fluxos de admin, barbeiro e cliente; desktop 1440 px e celular 390 px; teclado; queda da API |
| Banco real (Postgres) | Migrações aplicadas e contagens de integridade, somente leitura |
| Ferramentas | 239 testes do backend, `tsc`, ESLint, build Vite, `makemigrations --check`, `check --deploy`, contagem de queries SQL por endpoint |

**Legenda de tipo:** Bug confirmado · Funcionalidade ausente · Funcionalidade incompleta · Risco potencial · Dívida técnica · Melhoria opcional · Não verificado.

---

## 1. Resumo executivo

O BarberPro tem uma **base técnica sólida**: o isolamento entre barbearias resistiu a todas as 16 tentativas de acesso cruzado, a escalada de privilégio foi bloqueada, o ciclo de sessão (refresh por cookie HttpOnly, revogação na troca de senha, blacklist no logout) funciona, as consultas são eficientes (2 a 4 queries por endpoint) e as migrações estão íntegras. O frontend compila sem erros e os fluxos principais funcionam de ponta a ponta.

Ele **não está pronto para produção** e tem dois problemas críticos de segurança:

1. **A chave secreta efetiva do ambiente atual tem 3 caracteres** (um `#` no `.env` trunca o valor). Ela assina os JWT; com uma chave assim, tokens de qualquer usuário podem ser forjados.
2. **Clientes e barbeiros conseguem ler o faturamento completo da barbearia** pelo endpoint `revenue-report`.

Além disso, há **regras de negócio incorretas confirmadas** (admin pode se autodesativar e deixar a barbearia sem administrador; barbearia "excluída" continua operando; reagendamento mantém "confirmado"; atendimento futuro pode ser marcado como realizado; agendamento pode terminar depois do fechamento) e **lacunas de produto** que impedem o uso real por uma barbearia (clientes não conseguem se cadastrar numa barbearia; não há dias de funcionamento, então domingos recebem horários; recuperação de senha não envia e-mail na configuração atual).

**Contagem:** 2 P0 · 9 P1 · 21 P2 · 21 P3 (53 itens) + 5 itens não verificados.

---

## 2. Arquitetura identificada

- **Backend:** Django 5.0.14 + DRF 3.15.2, JWT (simplejwt 5.3.1) com access no header e refresh em cookie HttpOnly (`/api/v1/auth/`, SameSite=Lax), blacklist de refresh. PostgreSQL 16 via Docker (porta 5433). Apps: `accounts`, `barbershops`, `services`, `appointments`, `config` (permissões, mixin de tenant, paginação).
- **Multi-tenant:** banco e schema compartilhados; isolamento na aplicação via `TenantScopedQuerysetMixin` (filtra por `barbershop_id` do usuário) e checagens nos serializers/models. Superusuário enxerga todos os tenants.
- **Perfis:** `admin`, `barbeiro`, `cliente` (campo `tipo_perfil`), mais `is_superuser`/`is_staff` do Django como "super admin".
- **Exclusões lógicas:** usuários, barbeiros e serviços são desativados, não apagados; FKs com `PROTECT`.
- **Frontend:** React 19 + TypeScript + Vite 6, React Router 7, Axios, React Hook Form + Zod, CSS Modules. Sem biblioteca de UI. Telas carregadas sob demanda.
- **Infra:** somente `docker-compose.yml` do banco. Sem Dockerfile da aplicação, CI, cache compartilhado, logging ou monitoramento.

---

## 3. Funcionalidades existentes e estado real

| Módulo | Funcionalidade | Estado | Evidência |
|---|---|---|---|
| Autenticação | Login / refresh por cookie / logout | ✅ Funciona | Sondagem: login 200, refresh 200, logout 204, refresh pós-logout 401 |
| Autenticação | Troca de senha com revogação das sessões | ✅ Funciona | Access antigo 401 e refresh 401 após a troca |
| Autenticação | Recuperação de senha | ⚠️ Incompleta | API responde 204 sem revelar contas, mas não há SMTP configurado e o e-mail não traz link (ver AUTH-01) |
| Autenticação | Cadastro público | ⚠️ Incompleta | Cria conta sem barbearia (só serve a donos); e-mails duplicados por maiúsculas (AUTH-02) |
| Barbearias | Onboarding (criar a 1ª barbearia) | ✅ Funciona | Teste de fluxo; usuário já vinculado recebe 400 |
| Barbearias | Edição pelo admin | ⚠️ Aceita dados inválidos | Fechamento antes da abertura aceito (BUS-05) |
| Barbearias | Desativação / "exclusão" | ❌ Sem efeito | Barbearia inativa continua aceitando agendamentos (BUS-02) |
| Barbearias | Logo | ⚠️ Só API | Upload aceito pela API; sem tela; mídia servida só com `DEBUG` |
| Barbeiros | Cadastro, edição, desativação, reativação | ✅ Funciona | CRUD testado; perfil e papel sincronizados |
| Barbeiros | Disponibilidade própria (folgas, horários) | ❌ Ausente | Só existe o horário da barbearia (BUS-06) |
| Clientes | Cadastro/edição/desativação pelo admin | ✅ Funciona | `POST/PATCH/DELETE /users/` testados |
| Clientes | Autocadastro numa barbearia | ❌ Ausente | PROD-01 |
| Clientes | Histórico | ✅ Funciona | Tela de clientes calcula visitas reais |
| Serviços | CRUD, preço, duração, ativo | ✅ Funciona | Edição de inativo corrigida no frontend (`?ativo=all`) |
| Agendamentos | Criar, slots livres, conflito | ✅ Funciona | Conflitos rejeitados; slots excluem ocupados |
| Agendamentos | Máquina de status | ⚠️ Regras faltando | Futuro pode virar "realizado" (BUS-07); sem "não compareceu" (BUS-08) |
| Agendamentos | Reagendar | ⚠️ Bug | Mantém "confirmado" (BUS-03); troca de serviço ignora horário (BUS-04) |
| Agendamentos | Cancelar | ✅ Funciona | Cliente e admin; diálogo de confirmação no front |
| Dashboard | Indicadores e gráficos | ✅ Dados reais | Calculados dos agendamentos reais com `preco_historico` |
| Relatório | `revenue-report` | ❌ Permissão errada | Cliente e barbeiro leem tudo (SEC-02) |
| Super Admin | Painel global | ❌ Ausente | Só o Django Admin; branch `feature/painel-super-admin` está vazia (SA-01) |
| Isolamento | Entre barbearias | ✅ Resistiu a 16/16 tentativas | Ver seção 6 |

---

## 4. Funcionalidades ausentes (resumo)

1. Autocadastro de clientes numa barbearia / página pública de agendamento / convite (PROD-01).
2. Dias de funcionamento, folgas, feriados, bloqueios e horário por barbeiro (BUS-06).
3. Envio real de e-mail (recuperação de senha, confirmações, lembretes) (AUTH-01, SAAS-01).
4. Status "não compareceu" e fechamento automático de horários passados (BUS-08).
5. Agendamento pelo admin para cliente sem conta (atendimento avulso) e tela de agendar pelo admin (BUS-14).
6. Busca, ordenação, filtro por período e tamanho de página na API (API-01).
7. Painel de Super Admin: gestão global de barbearias, suspensão efetiva, métricas da plataforma (SA-01).
8. Observabilidade: logs estruturados, rastreamento de erros, trilha de auditoria, health check (OBS-01).
9. Infra de produção: Dockerfile, CI, arquivos estáticos e mídia, rotina de limpeza de tokens, backup (OPS-01).
10. Produto SaaS: planos/cobrança, LGPD (consentimento, exportação e exclusão real de dados), notificações (SAAS-01).

---

## 5–13. Problemas por área

Os itens estão detalhados na seção 14. Índice por área:

- **Segurança (5):** SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, SEC-07, SEC-08
- **Banco e integridade (6):** DATA-01, DATA-02, DATA-03, BUS-09, AUTH-02
- **Frontend (7):** FE-01 a FE-09, FE-11, FE-12, SEC-04
- **Backend e regras de negócio (8):** BUS-01 a BUS-14, AUTH-01, API-01, API-02
- **Integração (9):** API-01 (frontend percorre todas as páginas), FE-05 (fuso duplicado), FE-11 (duas fontes para faturamento), DOC-01 (documentação contradiz a API)
- **Testes (10):** TEST-01, TEST-02, FE-02
- **Documentação (11):** DOC-01, DOC-02, DOC-03
- **Dívidas técnicas (12):** API-02, FE-07, REPO-01, REPO-02, REPO-03, DATA-02

---

## 14. Lista completa de problemas, por prioridade

### P0 — Crítico

#### SEC-01 · P0 · Bug confirmado (configuração) · Segurança/Autenticação
- **Descrição:** a `SECRET_KEY` efetivamente carregada pelo Django tem **3 caracteres**. A linha no `.env` tem 50, mas um `#` na 4ª posição é interpretado pelo `django-environ` como início de comentário. A mesma chave assina os JWT (`SIGNING_KEY` padrão = `SECRET_KEY`).
- **Evidência:** `len(settings.SECRET_KEY) == 3` e `len(SIMPLE_JWT SIGNING_KEY) == 3`; caractere `#` na posição 3 da linha `SECRET_KEY=` (valores não exibidos); aviso `InsecureKeyLengthWarning: The HMAC key is 3 bytes long` em toda execução dos testes. A verificação existente em `settings.py` só barra a chave padrão de desenvolvimento, não chaves curtas.
- **Arquivos:** `.env` (local, não versionado), `config/settings.py`.
- **Impacto:** com uma chave de 3 caracteres, um atacante descobre a chave por força bruta a partir de qualquer JWT e forja tokens de qualquer usuário — inclusive admin de outra barbearia ou superusuário —, anulando todo o isolamento multi-tenant. Hoje afeta o ambiente local/demonstração; seria catastrófico se esse `.env` fosse usado num servidor.
- **Reproduzir:** `venv312/bin/python -c "import django,os;os.environ['DJANGO_SETTINGS_MODULE']='config.settings';django.setup();from django.conf import settings;print(len(settings.SECRET_KEY))"`.
- **Solução:** gerar nova chave sem `#`/`$` (ou colocá-la entre aspas) e adicionar em `settings.py` uma validação de tamanho mínimo (ex.: erro se `len < 50` fora do DEBUG e aviso no DEBUG). Trocar a chave invalida as sessões atuais (esperado).
- **Resolvido quando:** `len(settings.SECRET_KEY) >= 50`, nenhum `InsecureKeyLengthWarning` nos testes e um teste/checagem impede chave curta.

#### SEC-02 · P0 · Bug confirmado · Agendamentos/Relatórios
- **Descrição:** `GET /appointments/revenue-report/` não restringe perfil: qualquer usuário autenticado do tenant recebe o faturamento total, por barbeiro, por serviço e diário.
- **Evidência:** sondagem — cliente recebeu **HTTP 200** com o total da barbearia; barbeiro recebeu **HTTP 200** com o faturamento dos 3 barbeiros. A action não declara `permission_classes`; `get_permissions` só trata `update/partial_update/destroy`.
- **Arquivos:** `appointments/views.py` (`revenue_report`, `get_permissions`).
- **Impacto:** vazamento de informação financeira e de desempenho individual para clientes e funcionários.
- **Reproduzir:** autenticar como cliente e chamar `GET /api/v1/appointments/revenue-report/`.
- **Solução:** exigir `IsAdminRole` na action (ou, se desejado, limitar o barbeiro aos próprios números). Documentar o endpoint.
- **Resolvido quando:** cliente e barbeiro recebem 403, admin 200, com testes automatizados para os três perfis.

### P1 — Alto

#### BUS-01 · P1 · Bug confirmado · Usuários/Permissões
- **Descrição:** o admin pode **se rebaixar a cliente** (`PATCH /users/{id}/ tipo_perfil=cliente`) ou **se desativar** (`DELETE /users/{id}/`), deixando a barbearia sem administrador. Não existe recuperação pela aplicação.
- **Evidência:** sondagem — rebaixamento HTTP 200 (`tipo_perfil=cliente`), e o ex-admin passou a receber 403 ao administrar; autodesativação HTTP 204 seguida de login 401.
- **Arquivos:** `accounts/serializers.py` (`UserSerializer.validate/update`), `accounts/views.py` (`perform_destroy`).
- **Impacto:** barbearia bloqueada; só o superusuário consegue corrigir pelo Django Admin.
- **Reproduzir:** como admin, `PATCH /users/<seu id>/ {"tipo_perfil": "cliente"}`.
- **Solução:** impedir alterar o próprio papel/ativo e impedir remover o último admin ativo do tenant.
- **Resolvido quando:** as duas operações retornam 400 com mensagem clara e há testes cobrindo próprio usuário e último admin.

#### BUS-02 · P1 · Bug confirmado · Barbearias/Super Admin
- **Descrição:** `Barbershop.ativo` não é usado em nenhuma regra. A "exclusão" da barbearia (DELETE pelo staff, que só marca `ativo=False`) não tem efeito, e o próprio admin pode alterar `ativo` via PATCH.
- **Evidência:** sondagem — `PATCH ativo=false` HTTP 200 e, em seguida, novo agendamento HTTP 201; busca no código não encontrou nenhum uso de `barbershop.ativo` fora de filtros do admin.
- **Arquivos:** `barbershops/views.py` (`perform_destroy`), `barbershops/serializers.py` (`ativo` gravável), `config/mixins.py`, `config/permissions.py`.
- **Impacto:** a plataforma não consegue suspender um cliente (inadimplência, abuso); a "exclusão" é ilusória.
- **Reproduzir:** desativar a barbearia e criar um agendamento nela.
- **Solução:** tornar `ativo` somente-leitura para o admin do tenant e bloquear acesso/operações de tenants inativos (permissão global ou no mixin), com mensagem própria.
- **Resolvido quando:** usuários de barbearia inativa recebem 403 com explicação, admin do tenant não altera `ativo`, testes cobrem os dois casos.

#### BUS-03 · P1 · Bug confirmado · Agendamentos
- **Descrição:** quando o cliente reagenda um horário **confirmado**, o status continua "confirmado", embora a barbearia nunca tenha confirmado o novo horário.
- **Evidência:** sondagem — após `PATCH data_hora` pelo cliente, `status = confirmado`.
- **Arquivos:** `appointments/serializers.py` (`update`), `appointments/views.py` (`perform_update`).
- **Impacto:** a agenda mostra como confirmado algo que ninguém confirmou; o barbeiro pode não se preparar.
- **Reproduzir:** confirmar um agendamento como admin e reagendá-lo como cliente.
- **Solução:** ao alterar `data_hora`, `barbeiro` ou `servico` pelo cliente, voltar o status para `agendado`.
- **Resolvido quando:** reagendamento pelo cliente resulta em `agendado`, com teste.

#### BUS-04 · P1 · Bug confirmado · Agendamentos
- **Descrição:** a validação de horário de funcionamento é pulada quando `data_hora` não muda. Trocar só o **serviço** por um mais longo gera um atendimento que termina depois do fechamento.
- **Evidência:** sondagem — agendamento às 18:30 (fechamento 19:00) alterado para serviço de 60 min: **HTTP 200**. Em `_validar_horario_funcionamento`, o retorno antecipado compara apenas `data_hora`.
- **Arquivos:** `appointments/models.py` (`_validar_horario_funcionamento`).
- **Impacto:** agenda inconsistente com o horário da barbearia.
- **Solução:** revalidar também quando `servico_id` mudar (calcular o fim com a nova duração).
- **Resolvido quando:** a troca do exemplo retorna 400, com teste.

#### BUS-05 · P1 · Bug confirmado · Barbearias
- **Descrição:** a API aceita horário de fechamento anterior ao de abertura.
- **Evidência:** sondagem — `PATCH abertura=18:00, fechamento=08:00` HTTP 200. Não há `clean()` em `Barbershop` nem validação no serializer.
- **Arquivos:** `barbershops/models.py`, `barbershops/serializers.py`.
- **Impacto:** a barbearia passa a não oferecer nenhum horário, sem aviso. O frontend novo valida, mas o backend é a defesa real.
- **Solução:** validar `fechamento > abertura` no model e no serializer (criação e edição).
- **Resolvido quando:** a requisição retorna 400 em criação e edição, com testes.

#### BUS-06 · P1 · Funcionalidade ausente · Agendamentos/Barbeiros
- **Descrição:** não existem dias de funcionamento, folgas, feriados, bloqueios de agenda nem horário por barbeiro. Os horários livres dependem apenas de abertura/fechamento da barbearia, todos os dias.
- **Evidência:** sondagem — domingo 15/11 com **10 horários oferecidos**; `available_slots` usa só `horario_abertura/horario_fechamento`.
- **Arquivos:** `barbershops/models.py`, `appointments/views.py` (`available_slots`), `appointments/models.py`.
- **Impacto:** em uso real, clientes agendam em dias fechados e com barbeiros de folga.
- **Solução:** modelar grade semanal da barbearia, exceções por data e disponibilidade por barbeiro; aplicar nos slots e na validação.
- **Resolvido quando:** dias fechados e folgas não oferecem horários e a API recusa agendamentos neles, com testes.

#### PROD-01 · P1 · Funcionalidade ausente · Autenticação/Clientes
- **Descrição:** um cliente não consegue entrar numa barbearia existente por conta própria. O cadastro público cria conta sem barbearia e leva ao onboarding de dono. Não há página pública da barbearia, link de convite nem código de acesso.
- **Evidência:** `PublicRegistrationSerializer` cria usuário sem `barbershop`; o próprio README documenta a limitação. A tela "Clientes" (admin) contorna, mas exige cadastro manual de cada cliente.
- **Arquivos:** `accounts/serializers.py`, `accounts/views.py`, frontend `RegisterPage`/`OnboardingPage`.
- **Impacto:** inviabiliza a aquisição de clientes num SaaS real; quem se cadastra pelo site vira "dono" sem querer.
- **Solução:** página pública por barbearia (slug) com cadastro/agendamento vinculados ao tenant, ou convite por link/código.
- **Resolvido quando:** um cliente novo consegue se cadastrar e agendar numa barbearia específica sem intervenção do admin.

#### AUTH-01 · P1 · Funcionalidade incompleta · Autenticação
- **Descrição:** recuperação de senha não funciona na configuração atual. Não há `EMAIL_BACKEND`/SMTP definidos (padrão do Django: SMTP em `localhost:25`), o envio usa `fail_silently=True` e a mensagem traz `uid` e `token` em texto, sem link para o frontend.
- **Evidência:** `config/settings.py` sem `EMAIL_*`; `PasswordResetRequestSerializer.save`. Entrega real **não verificada** (não há SMTP para testar).
- **Arquivos:** `config/settings.py`, `accounts/serializers.py`, frontend `PasswordReset*Page`.
- **Impacto:** usuário que esqueceu a senha não tem como recuperá-la; o erro é silencioso.
- **Solução:** configurar e documentar e-mail por variáveis de ambiente, montar link `FRONTEND_URL/password/reset/confirm?uid=&token=`, registrar falhas de envio em log.
- **Resolvido quando:** com SMTP configurado, o e-mail chega com link funcional e falhas aparecem no log.

#### BUS-07 · P1 · Bug confirmado · Agendamentos/Dashboard
- **Descrição:** um atendimento **futuro** pode ser marcado como "realizado".
- **Evidência:** sondagem — `PATCH status=realizado` em horário daqui a 13 dias: HTTP 200.
- **Arquivos:** `appointments/models.py` (`_validar_transicao_status`).
- **Impacto:** infla faturamento, ticket médio e rankings; distorce o painel.
- **Solução:** permitir "realizado" somente a partir do início do atendimento.
- **Resolvido quando:** a tentativa retorna 400, com teste.

### P2 — Médio

#### AUTH-02 · P2 · Bug confirmado · Usuários/Banco
- **Descrição:** e-mails diferentes só por maiúsculas geram contas distintas. O login diferencia maiúsculas.
- **Evidência:** sondagem — cadastro de `ADMIN@demo.com` com `admin@demo.com` existente: **HTTP 201**. `normalize_email` só baixa o domínio; a unicidade é sensível a maiúsculas. No Postgres real, hoje há 0 duplicados.
- **Arquivos:** `accounts/managers.py`, `accounts/models.py`.
- **Impacto:** contas duplicadas e falhas de login ("João@…" ≠ "joão@…"); a recuperação de senha escolhe uma das contas.
- **Solução:** normalizar o e-mail para minúsculas, criar restrição única por `Lower(email)` e autenticar sem diferenciar maiúsculas.
- **Resolvido quando:** o cadastro do exemplo retorna 400 e o login aceita qualquer combinação de maiúsculas.

#### SEC-03 · P2 · Bug confirmado (privacidade) · Barbeiros
- **Descrição:** `GET /barbers/` devolve o e-mail de login de cada barbeiro para clientes.
- **Evidência:** sondagem — e-mails presentes na resposta para um cliente.
- **Arquivos:** `barbershops/serializers.py` (`BarberSerializer`).
- **Impacto:** exposição de dados pessoais de funcionários; facilita phishing e ataques de senha.
- **Solução:** serializer público sem e-mail para cliente/barbeiro; e-mail só para admin.
- **Resolvido quando:** cliente não recebe `email`; admin continua recebendo.

#### SEC-04 · P2 · Risco potencial · Frontend/Segurança
- **Descrição:** o access token fica em `localStorage` e não há Content-Security-Policy.
- **Evidência:** `frontend/src/utils/storage.ts`; nenhum cabeçalho CSP configurado.
- **Impacto:** qualquer XSS lê o token (válido por 15 min). Mitigado pelo refresh em cookie HttpOnly.
- **Solução:** manter o access só em memória (renovando pelo cookie no carregamento) e configurar CSP no servidor web.
- **Resolvido quando:** o token não persiste no armazenamento do navegador e a CSP bloqueia scripts externos não autorizados.

#### SEC-05 · P2 · Risco potencial · Infra/Segurança
- **Descrição:** sem `CACHES` configurado, o rate limiting usa cache em memória de cada processo.
- **Evidência:** `config/settings.py` sem `CACHES`.
- **Impacto:** em produção com vários workers, o limite de login (5/min) se multiplica pelo número de processos e zera a cada reinício.
- **Solução:** cache compartilhado (Redis) para throttling.
- **Resolvido quando:** os limites valem para o conjunto de workers.

#### SEC-07 · P2 · Risco potencial · Serviços/Agendamentos
- **Descrição:** `Service.duracao` aceita 0 no banco (`PositiveIntegerField`); só o serializer exige ≥ 1. Com duração 0, o laço de `available_slots` (`slot_atual += duracao`) nunca termina.
- **Evidência:** `services/models.py`; `appointments/views.py`, laço `while slot_atual <= limite`. Não executado para não travar o servidor; conclusão por leitura de código.
- **Impacto:** um serviço salvo com duração 0 pelo Django Admin ou direto no banco trava workers a cada consulta de horários.
- **Solução:** `MinValueValidator(1)` e `CheckConstraint(duracao > 0)` no model; guarda no laço.
- **Resolvido quando:** o banco recusa duração 0 e o endpoint não entra em laço.

#### BUS-08 · P2 · Funcionalidade ausente · Agendamentos
- **Descrição:** não há status "não compareceu" nem fechamento de horários vencidos; agendamentos passados ficam "agendado/confirmado" indefinidamente.
- **Evidência:** `Appointment.Status` tem 4 valores; nenhuma rotina agendada.
- **Impacto:** a lista "a confirmar" acumula horários passados; métricas de comparecimento são impossíveis.
- **Solução:** status de não comparecimento e rotina/indicador para horários vencidos sem desfecho.
- **Resolvido quando:** horários passados sem desfecho têm destino definido e aparecem separados.

#### BUS-09 · P2 · Risco potencial · Banco/Agendamentos
- **Descrição:** a duração do atendimento não é histórica. Conflitos e fim de agendamentos já existentes usam `servico.duracao` atual.
- **Evidência:** `_validar_conflito_horario` e `available_slots` usam `agendamento.servico.duracao`; só o preço tem cópia histórica.
- **Impacto:** alterar a duração de um serviço muda retroativamente agendas já marcadas e pode gerar sobreposição ou falsos conflitos.
- **Solução:** guardar `duracao_historica` no agendamento (como o preço) e usá-la nos cálculos.
- **Resolvido quando:** mudar a duração de um serviço não altera horários já agendados.

#### BUS-11 · P2 · Funcionalidade incompleta · Agendamentos
- **Descrição:** o passo entre horários é igual à duração do serviço; um serviço de 60 min só oferece horas cheias.
- **Evidência:** sondagem — serviço de 60 min: 09:00, 10:00, 11:00…
- **Impacto:** perde encaixes (ex.: 09:30 livre não é oferecido), reduzindo ocupação.
- **Solução:** passo configurável (ex.: 15 min) independente da duração.
- **Resolvido quando:** todos os inícios possíveis no passo configurado aparecem quando livres.

#### BUS-13 · P2 · Funcionalidade ausente · Barbeiros/Clientes
- **Descrição:** desativar um barbeiro ou um cliente não trata os agendamentos futuros deles; continuam ativos, sem aviso nem reatribuição.
- **Evidência:** `perform_destroy` de barbeiros e usuários altera só o perfil/conta.
- **Impacto:** clientes podem ir a um horário com um barbeiro desligado; agendas com clientes inativos.
- **Solução:** ao desativar, listar os horários futuros afetados e exigir decisão (cancelar, reatribuir).
- **Resolvido quando:** a desativação não deixa horários futuros órfãos sem decisão.

#### BUS-14 · P2 · Funcionalidade incompleta · Agendamentos
- **Descrição:** a API permite ao admin agendar para um cliente, mas não há tela para isso e não existe cliente avulso (sem conta).
- **Evidência:** `perform_create` aceita `cliente` do admin; rota `/appointments/new` só para clientes; `Appointment.cliente` exige usuário com perfil cliente.
- **Impacto:** agendamentos por telefone ou balcão não podem ser registrados pela interface.
- **Solução:** tela de agendamento pelo admin, com busca de cliente e cadastro rápido.
- **Resolvido quando:** o admin agenda para um cliente existente ou novo pela interface.

#### API-01 · P2 · Funcionalidade ausente · API/Integração
- **Descrição:** a API não oferece busca, ordenação, filtro por período, `page_size` nem filtro `tipo_perfil` em `/users/`. O frontend compensa baixando todas as páginas e filtrando no navegador.
- **Evidência:** sondagem — `page_size` ignorado (sempre 20), `?ordering`, `?search` e `?tipo_perfil` sem efeito. Painel: 12 requisições sequenciais para 228 agendamentos.
- **Arquivos:** `appointments/views.py`, `accounts/views.py`, `config/pagination.py`; frontend `api/endpoints.ts` (`collectPages`).
- **Impacto:** tempo de carregamento cresce linearmente com o histórico; inviável com milhares de registros.
- **Solução:** `SearchFilter`, `OrderingFilter`, filtros de data, `page_size_query_param` com limite; frontend passa a usar paginação e filtros do servidor.
- **Resolvido quando:** as telas carregam um número fixo de requisições independentemente do volume.

#### DATA-01 · P2 · Risco potencial · Banco
- **Descrição:** o reverso da migração `0008_populate_preco_historico` zera **todos** os preços históricos, inclusive os reais gravados depois.
- **Evidência:** `reverse_populate_preco_historico` faz `Appointment.objects.all().update(preco_historico=None)`.
- **Impacto:** um rollback de migração apaga dados financeiros irrecuperáveis.
- **Solução:** reverso como no-op, ou restrito aos registros preenchidos pela própria migração.
- **Resolvido quando:** desfazer a migração não altera preços gravados pela aplicação.

#### OBS-01 · P2 · Funcionalidade ausente · Backend
- **Descrição:** sem configuração de `LOGGING`, rastreamento de erros, trilha de auditoria (quem confirmou/cancelou/alterou) nem endpoint de saúde.
- **Evidência:** `config/settings.py`, `config/urls.py`; somente `deleted_by` em exclusões lógicas.
- **Impacto:** falhas em produção passam despercebidas; impossível responder "quem cancelou este horário".
- **Solução:** logging estruturado, Sentry (ou similar), histórico de alterações do agendamento, `/health/`.
- **Resolvido quando:** erros chegam a um painel e cada mudança de status registra autor e horário.

#### OPS-01 · P2 · Funcionalidade ausente · Infraestrutura
- **Descrição:** não há Dockerfile da aplicação, pipeline de CI, serviço de arquivos estáticos/mídia em produção (logo só com `DEBUG`), rotina `flushexpiredtokens` nem backup documentado.
- **Evidência:** raiz do projeto e `config/urls.py` (mídia apenas com `DEBUG`).
- **Impacto:** implantação manual e propensa a erro; tabela de tokens cresce indefinidamente.
- **Solução:** Dockerfile + compose de produção, CI rodando testes/lint/build, whitenoise ou servidor web, rotinas agendadas e backup.
- **Resolvido quando:** um commit roda o CI e a aplicação sobe em produção por um procedimento documentado.

#### FE-01 · P2 · Funcionalidade ausente · Frontend
- **Descrição:** não há error boundary; um erro de renderização deixa a tela em branco.
- **Evidência:** nenhum `ErrorBoundary`/`componentDidCatch` em `src`.
- **Impacto:** qualquer falha inesperada derruba a interface inteira, sem mensagem.
- **Solução:** error boundary no layout e por rota, com opção de recarregar.
- **Resolvido quando:** um erro forçado numa tela mostra mensagem e mantém o restante do app.

#### FE-02 · P2 · Funcionalidade ausente · Testes/Frontend
- **Descrição:** o frontend não tem nenhum teste (unitário, componente ou ponta a ponta).
- **Evidência:** sem arquivos de teste e sem script `test` no `package.json`. A verificação desta auditoria foi manual/automatizada fora do projeto.
- **Impacto:** regressões de interface só são percebidas manualmente.
- **Solução:** Vitest + Testing Library para utilitários e componentes críticos; Playwright para os fluxos principais.
- **Resolvido quando:** CI executa testes de frontend cobrindo login, agendamento e ações de status.

#### TEST-01 · P2 · Lacuna de testes · Backend
- **Descrição:** os 239 testes passam, mas nenhum cobre os comportamentos com falha confirmada: permissão do `revenue-report`, status após reagendamento, troca de serviço no fim do expediente, fechamento antes da abertura, barbearia inativa, e-mail com maiúsculas, autorrebaixamento/autodesativação do admin, "realizado" no futuro, slots em data passada.
- **Evidência:** busca nos arquivos de teste; nenhum teste menciona `revenue`; os demais cenários falharam na sondagem com a suíte verde.
- **Impacto:** a suíte transmite uma segurança que não cobre essas regras.
- **Solução:** um teste de regressão para cada item corrigido.
- **Resolvido quando:** cada bug desta lista tem teste que falha antes e passa depois da correção.

#### DOC-01 · P2 · Documentação desatualizada · Documentação/Integração
- **Descrição:** `docs/arquitetura/DOCUMENTACAO_API.md` contradiz o comportamento real em vários pontos.
- **Evidência (linha → realidade):**
  - L82 "access expira em 60 minutos" → 15 minutos.
  - L77, L91, L99 refresh no corpo da resposta/requisição → refresh só em cookie HttpOnly.
  - L96 logout "205 Reset Content" → 204.
  - L126 "DELETE remove usuário" → desativa a conta (o mesmo para barbeiros e serviços; barbearia exige `?confirmar=<nome>` e só desativa).
  - L141 "crie também o perfil em POST /barbers/" → `POST /users/` com `especialidade` cria o perfil na mesma transação, e `especialidade` é obrigatória.
  - L399–402 "recuperação de senha e relatórios não implementados" → existem `/auth/password/*` e `revenue-report`.
  - Não documentados: `revenue-report`, `exclude_appointment_id`, `preco_historico`, `?ativo=all|false`.
  - A branch `release/barberpro-academica-v1` tem parte dessas correções que não voltou para `desenvolvimento`.
- **Impacto:** quem integrar pela documentação implementa errado (como o frontend antigo, que tratou exclusão como remoção).
- **Solução:** atualizar a documentação (ou gerar via OpenAPI com drf-spectacular) e trazer as correções da `release`.
- **Resolvido quando:** cada endpoint documentado corresponde ao comportamento testado.

#### REPO-01 · P2 · Dívida técnica · Repositório
- **Descrição:** o virtualenv `venv312/` está versionado: **4.875 de 5.076 arquivos (96%)**, incluindo binários `.so` específicos de Linux. O `.gitignore` foi atualizado depois do commit, então não tem efeito sobre o que já foi adicionado.
- **Evidência:** `git ls-files | grep -c '^venv312/'` = 4875.
- **Impacto:** repositório pesado, diffs poluídos, binários de plataforma incompatíveis em outras máquinas.
- **Solução:** `git rm -r --cached venv312` (mantendo a pasta local) em um commit dedicado.
- **Resolvido quando:** `git ls-files` não lista nada de `venv312/`.

#### SA-01 · P2 · Funcionalidade ausente · Super Admin
- **Descrição:** não há painel de Super Admin. A gestão global depende do Django Admin (`is_staff`/`is_superuser`); a branch `feature/painel-super-admin` aponta para o mesmo commit de `desenvolvimento`, sem nenhum trabalho próprio. Não há métricas da plataforma, suspensão efetiva de barbearias (ver BUS-02), acesso de suporte auditado nem gestão de planos.
- **Evidência:** `git rev-list` (0 commits de diferença); `*/admin.py` registram os models com listas e filtros básicos.
- **Isolamento verificado:** um admin de barbearia **não** acessa outra (16/16 tentativas bloqueadas); o superusuário enxerga todos os tenants por desenho.
- **Impacto:** operar a plataforma exige acesso direto ao Django Admin.
- **Solução:** definir escopo do Super Admin (lista de barbearias, suspender/reativar, métricas, auditoria) e implementar sobre endpoints restritos a staff.
- **Resolvido quando:** o operador da plataforma gerencia barbearias sem usar o Django Admin.

#### SAAS-01 · P2 · Funcionalidade ausente · Produto
- **Descrição:** faltam elementos de SaaS comercial: notificações (confirmação/lembrete por e-mail ou WhatsApp), planos e cobrança, conformidade com a LGPD (consentimento, exportação e exclusão real de dados pessoais — hoje "excluir" só desativa).
- **Evidência:** ausência de modelos, endpoints e configurações correspondentes.
- **Impacto:** impede a comercialização e expõe a riscos legais no tratamento de dados.
- **Solução:** planejar como épicos separados (notificações → LGPD → cobrança).
- **Resolvido quando:** cada épico tiver requisitos definidos e entregues.

### P3 — Baixo

| ID | Tipo | Módulo | Descrição e evidência | Solução / critério |
|---|---|---|---|---|
| SEC-06 | Risco potencial | Repositório | Uma `SECRET_KEY` fixa existe no histórico (`core/settings.py`, commits `22575b0`, `3f46df2`); valor não exibido. Inofensiva se nunca for reutilizada. | Confirmar que não é usada em lugar nenhum; considerar limpeza de histórico se o repositório for público. |
| SEC-08 | Funcionalidade ausente | Autenticação | Sem verificação de e-mail no cadastro; qualquer pessoa cria uma barbearia por conta. | Confirmação de e-mail antes do onboarding. |
| BUS-10 | Bug confirmado | Agendamentos | `available-slots` devolve horários para datas passadas (18 horários para "ontem"); a criação depois é recusada. | Retornar lista vazia ou 400 para datas passadas; teste. |
| BUS-12 | Inconsistência | Agendamentos | Barbeiro não pode cancelar via DELETE (403), mas pode via PATCH `status=cancelado` (200); também pode trocar o `cliente` do próprio agendamento. | Definir a regra de negócio e aplicá-la igualmente nos dois caminhos. |
| API-02 | Dívida técnica | Relatórios | `revenue_report` usa `.extra()` (obsoleto) e agrupa o diário por `DATE()` em UTC: atendimentos após 21h caem no dia seguinte. | `TruncDate` com fuso local; teste com horário noturno. |
| DATA-02 | Limitação | Banco | Preços históricos anteriores à migração 0007 foram estimados com o preço vigente na época da migração (documentado no arquivo). | Apenas registrar a limitação em relatórios antigos. |
| DATA-03 | Operacional | Banco | O Postgres avisa divergência de versão de *collation* (2.43 × 2.44). Índices de texto podem ficar inconsistentes. | `REINDEX` e `ALTER DATABASE … REFRESH COLLATION VERSION` numa janela de manutenção. |
| FE-03 | Bug confirmado (código) | Frontend | Se a recarga ("Atualizar") falhar quando já há dados na tela, nenhuma mensagem aparece (`error && !data`). | Toast ou aviso em linha para falha de recarga. |
| FE-04 | Inconsistência | Frontend | O contador "a confirmar" inclui agendamentos passados nunca confirmados. | Separar "vencidos" de "a confirmar" (depende de BUS-08). |
| FE-05 | Dívida técnica | Integração | Fuso `America/Sao_Paulo` fixo no frontend, enquanto o backend lê `TIME_ZONE` das configurações. | Expor o fuso da barbearia pela API. |
| FE-06 | Funcionalidade ausente | Frontend | Rota inexistente redireciona silenciosamente para o início; não há página 404. | Página "não encontrada" com link de volta. |
| FE-07 | Código morto | Frontend | Sem uso: `getTotalServices`, `getTotalBarbers`, `isPast`, `formatDateTime` e 14 ícones legados. | Remover. |
| FE-08 | Melhoria opcional | Frontend | Fonte carregada do Google Fonts (dependência externa e envio de IP a terceiros). | Hospedar a fonte junto com o app. |
| FE-09 | Funcionalidade incompleta | Frontend | Sem tela para upload de logo (API suporta); barbeiro não reagenda pela interface (API permite). | Implementar se fizer parte do escopo. |
| FE-11 | Risco potencial | Integração | O painel calcula faturamento no navegador; o `revenue-report` calcula no servidor com agrupamento diferente (ver API-02). Os números podem divergir. | Uma única fonte: endpoint de métricas corrigido. |
| DOC-02 | Documentação incorreta | README | O README diz que `python manage.py test` usa SQLite em memória; na verdade usa o Postgres das configurações (cria e destrói um banco de teste). SQLite exige `--settings=config.test_settings`. | Corrigir o README. |
| DOC-03 | Comentário obsoleto | Backend | Referências ao antigo app `core` (`accounts/models.py:7`, `config/settings.py:54`). | Atualizar os comentários. |
| REPO-02 | Organização | Repositório | Arquivos soltos: `db.sqlite3` (217 KB, ignorado), `test.db` vazio, `gerar_zip.py`, `requisitos_barbearia.docx`, pastas vazias `outputs/` e `work/`, `frontend/.pytest_cache`, 21 rascunhos em `docs/auditorias/historico` (inclui `debug_test.py` e um segundo `requirements.txt`). | Mover para fora do repositório ou consolidar. |
| REPO-03 | Organização | Repositório | `master` está 30 commits atrás de `desenvolvimento`; `feature/painel-super-admin` está vazia; a `release` tem 1 commit (documentação) que não voltou para `desenvolvimento`. | Definir o fluxo de branches e sincronizar a documentação. |
| TEST-02 | Não verificado | Testes | Cobertura de código não medida (`coverage` não está instalado). | Adicionar `coverage` ao CI com meta mínima. |
| FE-12 | Melhoria opcional | Apresentação | O banco real tem 1 serviço e 1 agendamento: o painel aparece praticamente vazio. Não é bug. | Comando `seed_demo` que cria registros reais de demonstração num tenant separado. |

### Não verificado

| Item | Motivo |
|---|---|
| Entrega real de e-mail | Não há SMTP configurado (ver AUTH-01). |
| Concorrência de agendamentos no Postgres | O bloqueio `select_for_update` existe e há testes específicos (`config/test_postgres_settings.py`), mas não executei carga concorrente. |
| Leitor de tela (NVDA/VoiceOver) | Validados apenas teclado, foco, rótulos e contraste calculado. |
| Tablet (≈820 px) e Safari/Chrome | Telas conferidas só em 1440 px e 390 px, no Firefox. |
| Rate limiting real | O ambiente isolado desliga o throttling; só a configuração foi revisada. |

---

## 15. Plano de correção recomendado

**Fase 0 — antes da apresentação (alterações pequenas, com testes, exigem autorização para mexer no backend):**
1. SEC-01: gerar nova `SECRET_KEY` sem `#` e adicionar a validação de tamanho.
2. SEC-02: restringir `revenue-report` ao admin.
3. BUS-01, BUS-03, BUS-04, BUS-05, BUS-07: regras de negócio pontuais.
4. TEST-01: um teste de regressão por item acima.
5. FE-12 (opcional): dados de demonstração reais num tenant próprio.

**Fase 1 — antes de qualquer uso real:**
BUS-02 (suspensão de barbearia), AUTH-01 (e-mail), AUTH-02 (e-mail sem diferenciar maiúsculas), SEC-03, SEC-07, DATA-01, API-01 (+ frontend usando paginação do servidor), FE-01, OBS-01, OPS-01, SEC-05, DOC-01/DOC-02, REPO-01.

**Fase 2 — produto:**
PROD-01 (autocadastro/página pública), BUS-06 (dias e disponibilidade), BUS-08, BUS-09, BUS-11, BUS-13, BUS-14, SA-01, SAAS-01, SEC-04, SEC-08.

**Fase 3 — acabamento:** itens P3 restantes.

---

## Respostas objetivas

**O que impede o BarberPro de ser utilizado atualmente?**
Para demonstração acadêmica, nada bloqueia: os fluxos funcionam de ponta a ponta quando o admin cadastra os clientes. Para uma barbearia real: clientes não conseguem se cadastrar sozinhos (PROD-01), dias fechados recebem agendamentos (BUS-06), a recuperação de senha não envia e-mail (AUTH-01) e clientes veem o faturamento (SEC-02).

**O que impede de ser considerado pronto para produção?**
Os dois P0 (chave secreta truncada e vazamento de faturamento), as regras de negócio P1 confirmadas, a ausência de logs/monitoramento/CI/infra de implantação, e a falta de testes para as regras corrigidas e para o frontend.

**Quais funcionalidades ainda precisam ser implementadas?**
Autocadastro/página pública por barbearia; grade de funcionamento, folgas e disponibilidade por barbeiro; e-mail transacional; "não compareceu"; agendamento pelo admin e atendimento avulso; busca/ordenação/filtros na API; painel de Super Admin com suspensão efetiva; notificações, LGPD e cobrança.

**Quais são os riscos mais graves?**
1. Forja de tokens pela chave de 3 caracteres (comprometimento total, inclusive entre barbearias).
2. Exposição do faturamento a clientes e barbeiros.
3. Barbearia sem administrador por autodesativação.
4. Barbearia suspensa que continua operando.
5. Métricas financeiras distorcidas por "realizado" no futuro.

**O que deve ser corrigido primeiro?**
SEC-01 e SEC-02, depois BUS-01, BUS-03, BUS-04, BUS-05 e BUS-07, cada um com teste de regressão.

**O que pode ficar para versões futuras?**
Cobrança e planos, notificações, painel de Super Admin completo, LGPD avançada, passo de horários configurável, histórico de duração, hospedagem própria de fontes e os demais P3.
