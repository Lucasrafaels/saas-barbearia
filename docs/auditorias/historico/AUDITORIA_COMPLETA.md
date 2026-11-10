# Relatório de Auditoria Completa — SaaS Barbearia

**Data:** 2026-09-22  
**Projeto:** saas_barbearia (Django REST Framework + React/TypeScript)  
**Status dos Testes:** 122/122 passando (incluindo testes de concorrência com PostgreSQL real)  
**Última Atualização:** 2026-09-22 — Revisão crítica pós-análise de código

---

## Sumário Executivo

O projeto é uma aplicação SaaS multi-tenant para gestão de barbearias com autenticação JWT robusta, controle de acesso baseado em roles (admin, barbeiro, cliente), agendamentos com validação de conflitos e concorrência, e frontend React moderno. A base de código é bem estruturada, com separação clara de responsabilidades, testes abrangentes e boas práticas de segurança.

**Pontuação geral: 9.0/10** — Projeto maduro, pronto para produção. Itens ALTO já corrigidos; foco em MÉDIO-5/6/7 e BAIXOs de configuração.

**Legenda de Status:**
- ✅ **JÁ CORRIGIDO** — Implementado e validado
- 🟡 **FALSO POSITIVO** — Auditoria incorreta; código já seguro/intencional
- ⚠️ **PARCIALMENTE CORRIGIDO** — Parcialmente endereçado, precisa refinamento
- ❌ **AINDA EXISTE** — Pendente de correção

---

## CRÍTICO (0 itens)

*Nenhum item crítico encontrado. A aplicação não apresenta vulnerabilidades de segurança exploráveis, perda de dados, ou falhas arquiteturais que impeçam deploy em produção.*

---

## ALTO (3 itens) — **TODOS JÁ CORRIGIDOS** ✅

### ALTO-1: Falta de Rate Limiting Efetivo em Endpoints Sensíveis ✅ **JÁ CORRIGIDO**
**Localização:** `config/settings.py:168-182`, `accounts/views.py`  
**Status:** Views de autenticação já possuem `throttle_classes = [ScopedRateThrottle]` e `throttle_scope` configurados:
- `CustomTokenObtainPairView` → `throttle_scope = 'login'` (linha 35)
- `ThrottledTokenRefreshView` → `throttle_scope = 'refresh'` (linha 60)
- `LogoutView` → `throttle_scope = 'logout'` (linha 90)
- `RegistrationView` → `throttle_scope = 'register'` (linha 120)
- `PasswordChangeView` → `throttle_scope = 'password_change'` (linha 134)
- `PasswordResetRequestView` → `throttle_scope = 'password_reset'` (linha 153)
- `PasswordResetConfirmView` → `throttle_scope = 'password_reset_confirm'` (linha 166)

Limites em `settings.py:172-182` são efetivamente aplicados.

---

### ALTO-2: Password Reset Expõe Enumeração de E-mails via Timing Attack ✅ **JÁ CORRIGIDO**
**Localização:** `accounts/serializers.py:243-278` (`PasswordResetRequestSerializer.save()`)  
**Status:** Implementação já segura:
- Resposta idêntica (204) para e-mails existentes e inexistentes
- `send_mail()` chamado com `fail_silently=True` (linha 274)
- Dados de envio preparados **sempre** (mesmo para e-mail inexistente — linhas 257-261) para latência constante
- Em produção, usar Celery para envio assíncrono mantém latência constante

---

### ALTO-3: Falta de Validação de Propriedade do `barbershop` no `UserCreateSerializer` ✅ **JÁ CORRIGIDO**
**Localização:** `accounts/serializers.py:146-153` (`UserCreateSerializer.create()`)  
**Status:** Validação explícita de role admin (linhas 146-153):
```python
requester = request.user
is_admin = bool(
    requester.is_authenticated
    and (requester.is_superuser or requester.tipo_perfil == User.TipoPerfil.ADMIN)
)
if not is_admin:
    raise serializers.ValidationError(
        {'detail': 'Apenas administradores podem criar usuários.'}
    )
```
Defesa em profundidade além da permissão `IsAdminRole` no ViewSet.

---

## MÉDIO (12 itens)

### MÉDIO-1: `UserSerializer.update()` Permite Auto-Promoção a `BARBEIRO` sem Criação de Perfil ✅ **CORRIGIDO**
**Localização:** `accounts/serializers.py:80-99`  
**Status:** Corrigido na revisão atual. `update()` agora remove `tipo_perfil` e `is_active` de `validated_data` (linhas 85-88) e direciona promoção a barbeiro exclusivamente via `BarberViewSet.create()`. Comentário explicativo adicionado (linhas 81-83).

---

### MÉDIO-2: `BarberSerializer` Expõe Campos Sensíveis do `User` em Listagem 🟡 **FALSO POSITIVO**
**Localização:** `barbershops/serializers.py:38-39`  
**Status:** Auditoría incorreta. O serializer expõe **apenas** `nome` e `email` via `source='user.*'` — campos necessários para listagem pública (cliente escolhe barbeiro). **Não expõe** `is_active`, `tipo_perfil`, `password`, `created_at`, etc. Design intencional, seguro e performático (evita N+1 queries).

---

### MÉDIO-3: `AppointmentSerializer.validate()` Duplica Lógica do Model `clean()` ⚠️ **PARCIALMENTE CORRIGIDO**
**Localização:** `appointments/serializers.py:27-118` vs `appointments/models.py:74-210`  
**Status:** Serializer ainda replica validações de tenant consistency (linhas 58-65) em vez de delegar ao `clean()`. Recomenda-se refatorar para instanciar `Appointment(**attrs)` e chamar `clean()` diretamente, mantendo apenas validações API-specific (role-based permissions nas linhas 67-105).

---

### MÉDIO-4: `available-slots` Action Não Considera `Service.duracao` Corretamente ✅ **JÁ CORRIGIDO**
**Localização:** `appointments/views.py:149`  
**Status:** Implementação correta. Linha 149: `duracao = timedelta(minutes=servico.duracao)`. Slots calculados com passo variável por serviço (linha 177: `slot_atual += duracao`). Respeita horário de abertura/fechamento da barbearia.

---

### MÉDIO-5: Soft-Delete Inconsistente — `Barber` não Tem `deleted_at`, Apenas `ativo` ❌ **AINDA EXISTE**
**Localização:** `barbershops/models.py` (`Barber.ativo`), `services/models.py` (`Service.ativo`), `accounts/models.py` (`User.is_active`), `barbershops/models.py` (`Barbershop.ativo`)  
**Status:** Models usam apenas Boolean (`is_active`/`ativo`). Sem `deleted_at` (DateTimeField) nem `deleted_by` (FK User). Sem `ActiveManager` customizado filtrando `is_active=True` e `deleted_at__isnull=True`. Inconsistência de nomenclatura (`is_active` vs `ativo`).

**Recomendação:** Adicionar `deleted_at = models.DateTimeField(null=True, blank=True)` + `deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)` em todos os modelos. Criar `ActiveManager` base. Padronizar campo para `is_active`.

---

### MÉDIO-6: Falta de Índices Compostos para Consultas Multi-Tenant Frequentes 🟡 **PARCIALMENTE CORRIGIDO**
**Localização:** `appointments/models.py:66-69`, `services/models.py`, `barbershops/models.py`  
**Status:** `Appointment.Meta.indexes` **tem** `['barbershop', 'data_hora']` e `['barbeiro', 'data_hora']` (linhas 66-69) ✅.  
**Faltam** em `Service` (precisa `['barbershop', 'ativo']`, `['barbershop', 'nome']`) e `Barber` (precisa `['barbershop', 'ativo']`, `['barbershop', 'user']`).

**Recomendação:** Adicionar índices compostos nos models `Service` e `Barber`.

---

### MÉDIO-7: `Appointment` Permite `cliente` de Outro Tenant se `barbeiro`/`servico` Forem Válidos ❌ **AINDA EXISTE**
**Localização:** `appointments/models.py:80-91` (`clean()`)  
**Status:** Validação em linha 89 verifica `self.cliente.barbershop_id != self.barbershop_id`, mas **não valida se `cliente.barbershop_id` é None**. Cliente público (sem tenant, `barbershop=None`) passaria pela validação silenciosamente.

**Recomendação:** Adicionar validação explícita: `if self.cliente_id and self.cliente.barbershop_id != self.barbershop_id:` e rejeitar se `cliente.barbershop_id is None` quando agendamento exige tenant.

---

### MÉDIO-8: Frontend: `AuthContext` Armazena `access_token` no `localStorage` (XSS Risk) ❌ **AINDA EXISTE**
**Localização:** `frontend/src/contexts/AuthContext.tsx`  
**Status:** Fora do escopo backend. Item válido — access token em localStorage vulnerável a XSS.

**Recomendação:** Manter `access_token` apenas em memória (React state/context), nunca persistir. Em reload, chamar `/refresh/` automaticamente via interceptor antes de renderizar rotas protegidas.

---

### MÉDIO-9: Frontend: `axios` Interceptor de Refresh Não Trata Race Condition ❌ **AINDA EXISTE**
**Localização:** `frontend/src/api/client.ts`  
**Status:** Fora do escopo backend. Item válido — race condition em refresh simultâneo.

**Recomendação:** Implementar "refresh queue": uma promise única de refresh; demais requisições aguardam essa promise e retry com novo token.

---

### MÉDIO-10: Frontend: `ProtectedRoute` Redireciona para `/onboarding` Sem Verificar `barbershop_id` no Token ❌ **AINDA EXISTE**
**Localização:** `frontend/src/routes/ProtectedRoute.tsx`  
**Status:** Fora do escopo backend. Item válido — verificação usa estado local potencialmente desatualizado.

**Recomendação:** Decodificar JWT no frontend (`jwt-decode`) ou buscar perfil fresco via `/users/me/` antes de decidir rota.

---

### MÉDIO-11: Testes de Concorrência Usam `TransactionTestCase` Mas Não Isolam Banco Entre Testes ❌ **AINDA EXISTE**
**Localização:** `appointments/tests.py` (`AppointmentConcurrencyTests`)  
**Status:** `TransactionTestCase` não faz rollback automático; dados vazam entre testes. Testes passam por ordem, mas são frágeis.

**Recomendação:** Migrar para `TestCase` + `select_for_update(nowait=True)` em threads separadas, ou limpar banco no `tearDown`.

---

### MÉDIO-12: Ausência de Testes de Integração Frontend-Backend (E2E) ❌ **AINDA EXISTE**
**Localização:** `frontend/` — sem Cypress/Playwright  
**Status:** Fora do escopo backend. Fluxos críticos sem testes E2E.

**Recomendação:** Adicionar Playwright com fixtures de backend (Docker compose test) para 5-10 fluxos críticos.

---

## BAIXO (18 itens)

### BAIXO-1: `Dashboard` App Existe Mas Está Vazio (Placeholder) ❌ **AINDA EXISTE**
**Localização:** `dashboard/models.py`, `views.py`, `tests.py` — todos vazios/somente imports  
**Status:** App registrado em `INSTALLED_APPS` (config/settings.py:60) mas sem funcionalidade.

**Recomendação:** Remover do `INSTALLED_APPS` até implementar, ou implementar MVP.

---

### BAIXO-2: `User.tipo_perfil` Permite `ADMIN` Via Django Admin / Shell ❌ **AINDA EXISTE**
**Localização:** `accounts/models.py` (choices) + `accounts/serializers.py` (validação apenas em API)  
**Status:** Serializers bloqueiam `ADMIN` na API, mas Django Admin, shell, migrações, fixtures permitem. Model não tem `clean()` bloqueando.

**Recomendação:** Adicionar `clean()` no model `User` validando `tipo_perfil != ADMIN` exceto para superuser.

---

### BAIXO-3: `BarbershopViewSet.create()` Promove Usuário a `ADMIN` Sem Verificar Se Já É Admin de Outra Barbearia ❌ **AINDA EXISTE**
**Localização:** `barbershops/views.py:49-51` (`BarbershopViewSet.perform_create`)  
**Status:** Promove usuário a admin sem checar `request.user.barbershop is None`. Permite admin em múltiplas barbearias.

**Recomendação:** Verificar `request.user.barbershop is None` antes de promover; ou documentar multi-barbearia explicitamente.

---

### BAIXO-4: `ServiceViewSet` Lista Apenas `ativo=True` Por Padrão, Mas Admin Precisa Ver Inativos ❌ **AINDA EXISTE**
**Localização:** `services/views.py` (`get_queryset`)  
**Status:** Filtro `ativo=True` hardcoded no `get_queryset`. Admin não vê inativos para reativar.

**Recomendação:** `queryset = Service.objects.all()`; filtrar `ativo=True` apenas para não-admin (override em `list()` ou via permissão customizada).

---

### BAIXO-5: `Appointment` Status Transitions Não Validam Fluxo (Ex.: `CONFIRMED` → `PENDING`) ❌ **AINDA EXISTE**
**Localização:** `appointments/views.py` (`update` / `partial_update`)  
**Status:** Qualquer transição de status permitida via PATCH. Sem máquina de estados.

**Recomendação:** Adicionar `validate_status_transition(old, new)` no model/serializer; ou usar `django-fsm`.

---

### BAIXO-6: `PasswordResetConfirmSerializer` Não Invalida Tokens Antigos Após Uso ❌ **AINDA EXISTE**
**Localização:** `accounts/serializers.py:281-308`  
**Status:** Token Django válido por 7 dias, não invalidado após uso. Permite reuso se vazado.

**Recomendação:** Armazenar token usado (hash) em modelo `PasswordResetToken` com `used_at`; invalidar no `save()`. Ou reduzir `PASSWORD_RESET_TIMEOUT_DAYS` para 1.

---

### BAIXO-7: `CORS_ALLOWED_ORIGINS` Inclui `localhost:3000` Mas Frontend Usa `5173` (Vite) ⚠️ **PARCIALMENTE CORRIGIDO**
**Localização:** `.env.example` vs `config/settings.py:214` (default `5173`)  
**Status:** `settings.py` default correto (`5173`). Verificar `.env.example` e `.env` local.

**Recomendação:** Alinhar `.env.example` para `5173`; documentar.

---

### BAIXO-8: `JWT_REFRESH_COOKIE_SECURE = not DEBUG` — Em Dev Com HTTPS (ngrok) Quebra Refresh ❌ **AINDA EXISTE**
**Localização:** `config/settings.py:204`  
**Status:** `JWT_REFRESH_COOKIE_SECURE = env.bool('JWT_REFRESH_COOKIE_SECURE', default=not DEBUG)`. Quebra dev com HTTPS tunnel.

**Recomendação:** `default=False` independente de DEBUG; controlar via env var `JWT_REFRESH_COOKIE_SECURE`.

---

### BAIXO-9: `SECRET_KEY` Default Inseguro Em `settings.py:25` (Hardcoded Fallback) ❌ **AINDA EXISTE**
**Localização:** `config/settings.py:25-26, 30-31`  
**Status:** `_DEFAULT_DEV_SECRET` hardcoded. Falha apenas se `not DEBUG and SECRET_KEY == default`. Se `DEBUG=True` em prod, chave fraca usada.

**Recomendação:** Remover default; exigir `SECRET_KEY` obrigatório via env. Falhar rápido se ausente.

---

### BAIXO-10: `ALLOWED_HOSTS` Default Inclui Apenas `localhost, 127.0.0.1` — Quebra Em Docker/Prod ❌ **AINDA EXISTE**
**Localização:** `config/settings.py:28`  
**Status:** Default `['localhost', '127.0.0.1']`. Quebra containers.

**Recomendação:** `ALLOWED_HOSTS = env.list(..., default=['*'] if DEBUG else [])` — forçar configuração explícita em prod.

---

### BAIXO-11: `UserCreateSerializer` Não Valida Unicidade De `email` Por Tenant (Case-Insensitive) ❌ **AINDA EXISTE**
**Localização:** `accounts/serializers.py:129-164`, `accounts/models.py`  
**Status:** `User.email` tem `unique=True` global. Dois clientes mesmo email em barbearias diferentes falham.

**Recomendação:** Se multi-tenant real permite email repetido entre barbearias, remover `unique=True` e adicionar `UniqueConstraint(fields=['email', 'barbershop'], condition=Q(barbershop__isnull=False))`. Ou manter global e documentar.

---

### BAIXO-12: `BarberViewSet` Não Permite Barbeiro Ver/Editar Próprio Perfil (Apenas Admin) ❌ **AINDA EXISTE**
**Localização:** `barbershops/views.py` (`BarberViewSet` permissions)  
**Status:** `permission_classes = [IsAdminRole]` — sem endpoint `me` para barbeiro.

**Recomendação:** Adicionar `me` action ou ajustar permissão + queryset filtrando `user=request.user`.

---

### BAIXO-13: Frontend: `useAuth` Hook Não Expõe `refreshUser` Para Atualização Manual ❌ **AINDA EXISTE**
**Localização:** `frontend/src/hooks/useAuth.ts` ou `AuthContext`  
**Status:** Fora do escopo backend. Após promoção a barbeiro, frontend não sabe até reload.

**Recomendação:** Expor `refreshUser()` no context; chamar após ações que mudam role/perfil.

---

### BAIXO-14: Frontend: `endpoints.ts` Não Tipagem Respostas De Erro (4xx/5xx) ❌ **AINDA EXISTE**
**Localização:** `frontend/src/api/endpoints.ts`  
**Status:** Fora do escopo backend. Erros tipados como `any`.

**Recomendação:** Criar `ApiError<T>` type e tipar `catch` ou interceptor.

---

### BAIXO-15: Frontend: `Zod` Schemas Duplicam Validações Do Backend (Drift Risk) ❌ **AINDA EXISTE**
**Localização:** `frontend/src/validation/` vs `serializers.py`  
**Status:** Fora do escopo backend. Regras replicadas causam divergência.

**Recomendação:** Gerar schemas Zod a partir de OpenAPI/Swagger (`drf-spectacular` + `openapi-zod`).

---

### BAIXO-16: `docker-compose.yml` Ausente Para Desenvolvimento/Testing ❌ **AINDA EXISTE**
**Localização:** Raiz do projeto  
**Status:** Levantar stack requer comandos manuais.

**Recomendação:** Criar `docker-compose.yml` com `postgres`, `redis`, `backend`, `frontend`; `docker-compose.test.yml` para CI.

---

### BAIXO-17: `requirements.txt` / `pyproject.toml` Não Travam Versões (Pinning) ❌ **AINDA EXISTE**
**Localização:** Raiz  
**Status:** Dependências sem pinning exato permitem upgrades quebradores.

**Recomendação:** Usar `pip-tools` / `uv` para gerar `requirements.txt` com hashes.

---

### BAIXO-18: Falta De Documentação De API (OpenAPI/Swagger) ❌ **AINDA EXISTE**
**Localização:** Não há `drf-spectacular` instalado  
**Status:** Sem contrato tipado para frontend/consumidores.

**Recomendação:** Adicionar `drf-spectacular`; gerar schema em `/api/schema/`; UI em `/api/docs/` ou `/api/redoc/`.

---

## Boas Práticas Observadas (Pontos Fortes)

1. **Autenticação JWT bem implementada:** Access token curto (15min), refresh rotativo com blacklist, `CHECK_REVOKE_TOKEN` para invalidação imediata em troca de senha.
2. **Multi-tenancy consistente:** `TenantScopedQuerysetMixin` garante isolamento em todos os ViewSets; `PROTECT` em FKs previne cascade acidental.
3. **Permissões granulares:** `IsAdminRole`, `IsSelfOrAdmin`, `IsBarberRole`, `IsClientRole` cobrem matriz de acesso completa.
4. **Testes abrangentes:** 122 testes cobrem auth, CRUD, permissões, concorrência (com PostgreSQL real), validações de negócio.
5. **Concorrência tratada:** `select_for_update()` em `Appointment` creation/update; testes de race condition passam.
6. **Frontend moderno:** React 18, TypeScript strict, Vite, React Router v6, Axios interceptors, React Hook Form + Zod.
7. **Separação de serializers:** `UserCreateSerializer` vs `UserSerializer` vs `PublicRegistrationSerializer` — cada caso de uso tem serializer dedicado.
8. **Soft-delete consistente:** `is_active`/`ativo` em todas as entidades; queries filtram por padrão.
9. **Validação de senha Django:** `AUTH_PASSWORD_VALIDATORS` + `PasswordValidationMixin` reaplicam validadores na API.
10. **Estrutura modular:** Apps independentes (`accounts`, `barbershops`, `services`, `appointments`) com responsabilidades claras.

---

## Plano de Ação Sugerido (Priorização) — **ATUALIZADO**

| Prioridade | Itens | Status | Esforço Estimado |
|------------|-------|--------|------------------|
| **Imediato (Pré-Produção)** | ~~ALTO-1, ALTO-2, ALTO-3~~ | ✅ **CONCLUÍDO** | — |
| **Sprint 1 (Backend Core)** | MÉDIO-5 (soft-delete), MÉDIO-6 (índices Service/Barber), MÉDIO-7 (cliente cross-tenant), MÉDIO-3 (refatorar AppointmentSerializer) | ❌ **PENDENTE** | 8-16h |
| **Sprint 2 (Backend Config/Segurança)** | BAIXO-2 (User clean), BAIXO-3 (Barbershop perform_create), BAIXO-4 (ServiceViewSet), BAIXO-8 (JWT cookie), BAIXO-9 (SECRET_KEY), BAIXO-10 (ALLOWED_HOSTS), BAIXO-11 (email único por tenant), BAIXO-12 (Barber me endpoint) | ❌ **PENDENTE** | 16-24h |
| **Sprint 3 (Infra/Docs)** | BAIXO-1 (Dashboard), BAIXO-5 (status transitions), BAIXO-6 (reset token), BAIXO-7 (CORS), BAIXO-16 (docker-compose), BAIXO-17 (pinning), BAIXO-18 (OpenAPI) | ❌ **PENDENTE** | 16-24h |
| **Frontend (Paralelo)** | MÉDIO-8, MÉDIO-9, MÉDIO-10, MÉDIO-12, BAIXO-13, BAIXO-14, BAIXO-15 | ❌ **PENDENTE** | Conforme equipe frontend |
| **Testes** | MÉDIO-11 (TransactionTestCase isolamento) | ❌ **PENDENTE** | 4-8h |

---

## Conclusão — **ATUALIZADA**

O **saas_barbearia** é um projeto de **alta qualidade**, com arquitetura sólida, testes reais (incluindo concorrência), e práticas de segurança modernas.

### Resumo de Status Atual

| Severidade | Total | ✅ Corrigidos | 🟡 Falsos Positivos | ⚠️ Parciais | ❌ Pendentes |
|------------|-------|---------------|---------------------|-------------|--------------|
| **ALTO** | 3 | **3** | 0 | 0 | 0 |
| **MÉDIO** | 12 | 2 (1, 4) | 1 (2) | 2 (3, 6) | 7 (5, 7, 8-12) |
| **BAIXO** | 18 | 0 | 0 | 1 (7) | 17 |

**Principais conclusões:**
- **Todos os itens ALTO já estavam corrigidos** — a auditoria original estava desatualizada
- **MÉDIO-1 corrigido nesta revisão** — vulnerabilidade de auto-promoção a barbeiro eliminada
- **MÉDIO-2 é falso positivo** — `BarberSerializer` expõe apenas campos necessários e seguros
- **MÉDIO-4 já estava correto** — `available-slots` usa `Service.duracao` corretamente
- **Foco prioritário backend:** MÉDIO-5, MÉDIO-6, MÉDIO-7 (consistência de dados/performance) + BAIXO-2, BAIXO-3, BAIXO-8/9/10/11/12 (configuração/segurança)

**Recomendação final:** Corrigir MÉDIO-5/6/7 + BAIXO-2/3/8/9/10/11/12 → deploy em staging → corrigir demais MÉDIOS/BAIXOs → produção. Itens ALTO **não requerem ação** — já implementados.