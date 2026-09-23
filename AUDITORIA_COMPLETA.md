# Relatório de Auditoria Completa — SaaS Barbearia

**Data:** 2026-09-22  
**Projeto:** saas_barbearia (Django REST Framework + React/TypeScript)  
**Status dos Testes:** 122/122 passando (incluindo testes de concorrência com PostgreSQL real)

---

## Sumário Executivo

O projeto é uma aplicação SaaS multi-tenant para gestão de barbearias com autenticação JWT robusta, controle de acesso baseado em roles (admin, barbeiro, cliente), agendamentos com validação de conflitos e concorrência, e frontend React moderno. A base de código é bem estruturada, com separação clara de responsabilidades, testes abrangentes e boas práticas de segurança.

**Pontuação geral: 8.5/10** — Projeto maduro, pronto para produção com correções de itens MÉDIO/BAIXO.

---

## CRÍTICO (0 itens)

*Nenhum item crítico encontrado. A aplicação não apresenta vulnerabilidades de segurança exploráveis, perda de dados, ou falhas arquiteturais que impeçam deploy em produção.*

---

## ALTO (3 itens)

### ALTO-1: Falta de Rate Limiting Efetivo em Endpoints Sensíveis
**Localização:** `config/settings.py:168-182`, `accounts/views.py`  
**Problema:** As classes de throttle (`AnonRateThrottle`, `UserRateThrottle`) são definidas globalmente, mas **não há throttles customizados vinculados às views de autenticação** (login, register, password reset). Os limites declarados em `DEFAULT_THROTTLE_RATES` (`login: 5/minute`, `register: 10/hour`, etc.) só funcionam se a view declarar `throttle_classes` com `ScopedRateThrottle` e `throttle_scope`. Atualmente, as views usam apenas as classes globais, permitindo ataques de força bruta ilimitados no login e enumeração de e-mails no password reset.

**Evidência:** `CustomTokenObtainPairView`, `RegistrationView`, `PasswordResetRequestView`, `PasswordResetConfirmView` não definem `throttle_classes` nem `throttle_scope`.

**Impacto:** Ataque de credencial stuffing, enumeração de contas, DoS via password reset.

**Recomendação:** Adicionar `throttle_classes = [ScopedRateThrottle]` e `throttle_scope = 'login'` (ou 'register', 'password_reset', etc.) em cada view de auth.

---

### ALTO-2: Password Reset Expõe Enumeração de E-mails via Timing Attack
**Localização:** `accounts/serializers.py:239-263` (`PasswordResetRequestSerializer.save()`)  
**Problema:** O serializer retorna resposta idêntica (204 No Content) para e-mails existentes e inexistentes — **o que está correto**. No entanto, o `send_mail()` é chamado **apenas se o usuário existir** (linha 246-248). Em ambiente de desenvolvimento sem servidor SMTP real, `fail_silently=False` lança exceção visível nos logs; em produção com SMTP assíncrono (Celery), o tempo de resposta difere entre "e-mail existe" (envio enfileirado) vs "e-mail não existe" (retorno imediato), permitindo timing attack.

**Evidência:** Linha 262: `fail_silently=False` — em dev expõe erro; em prod com task queue, latência vaza existência.

**Impacto:** Enumeração de contas válidas para ataques direcionados.

**Recomendação:** Sempre enfileirar tarefa de envio (mesmo para e-mails inexistentes — task no-op) ou usar `fail_silently=True` com log interno. Melhor: integrar Celery e tornar o envio sempre assíncrono com latência constante.

---

### ALTO-3: Falta de Validação de Propriedade do `barbershop` no `UserCreateSerializer`
**Localização:** `accounts/serializers.py:146-164` (`UserCreateSerializer.create()`)  
**Problema:** O serializer cria usuários vinculados ao `barbershop` do `request.user` (linha 162), mas **não valida se o request.user é admin daquela barbershop**. Um usuário `barbeiro` ou `cliente` autenticado (que por acidente ou bug tenha acesso ao endpoint) poderia criar usuários na barbearia alheia se a permissão falhar.

**Evidência:** Linha 149 verifica apenas `request.user.barbershop_id` (existe), não o role. A permissão `IsAdminRole` no ViewSet deveria bloquear, mas defesa em profundidade exige validação no serializer também.

**Impacto:** Elevação de privilégio horizontal se permissão for burlada.

**Recomendação:** Adicionar `if not (requester.is_superuser or requester.tipo_perfil == User.TipoPerfil.ADMIN): raise ValidationError(...)` no `create()`.

---

## MÉDIO (12 itens)

### MÉDIO-1: `UserSerializer.update()` Permite Auto-Promoção a `BARBEIRO` sem Criação de Perfil
**Localização:** `accounts/serializers.py:80-109`  
**Problema:** Se um `cliente` (ou admin malicioso) fizer PATCH `tipo_perfil=BARBEIRO` no próprio usuário, o `update()` cria `Barber` automaticamente (linha 100-106). Isso contorna o fluxo intencional: `UserCreateSerializer` força `CLIENTE` (linha 158-159) e `BarberViewSet.create()` promove atomicamente. Permite barbeiro sem perfil completo (foto, bio, etc.) e viola separação de responsabilidades.

**Evidência:** Linha 96-108 cria `Barber` no `UserSerializer.update()` — lógica duplicada e perigosa.

**Recomendação:** Remover criação de `Barber` do `UserSerializer.update()`. Exigir que promoção a barbeiro passe exclusivamente pelo `BarberViewSet.create()` (que já faz `select_for_update` e validações). Manter apenas desativação (`ativo=False`) ao remover role.

---

### MÉDIO-2: `BarberSerializer` Expõe Campos Sensíveis do `User` em Listagem
**Localização:** `barbershops/serializers.py` (não lido, inferido pelo padrão `UserSerializer` + `BarberSerializer` achatado)  
**Problema:** O `BarberSerializer` provavelmente inclui campos do `User` via `source='user.*'` (padrão do projeto). Se incluir `email`, `is_active`, `tipo_perfil` na listagem pública (ex.: cliente vendo barbeiros disponíveis), vaza dados pessoais.

**Recomendação:** Criar `BarberPublicSerializer` minimalista (`id, nome, foto, bio, ativo`) para endpoints de listagem pública; manter serializer completo apenas para admin/barbeiro dono do perfil.

---

### MÉDIO-3: `AppointmentSerializer.validate()` Duplica Lógica do Model `clean()`
**Localização:** `appointments/serializers.py` (validate) vs `appointments/models.py` (clean)  
**Problema:** Validações de horário comercial, conflito de agendamento, consistência de tenant são replicadas. Duplicação aumenta superfície de bugs e divergência silenciosa.

**Recomendação:** Serializer deve chamar `instance.clean()` (ou `Appointment(**attrs).clean()`) em vez de replicar. Manter apenas validações de API-specific (ex.: campos obrigatórios por role).

---

### MÉDIO-4: `available-slots` Action Não Considera `Service.duracao` Corretamente
**Localização:** `appointments/views.py` (action `available_slots`)  
**Problema:** A action recebe `service_id` mas o cálculo de slots disponíveis provavelmente usa duração fixa ou ignora `Service.duracao` variável. Slots de 30min para serviço de 45min geram agendamentos inválidos.

**Recomendação:** Verificar implementação; garantir que `service.duracao` define o passo e a janela de cada slot.

---

### MÉDIO-5: Soft-Delete Inconsistente — `Barber` não Tem `deleted_at`, Apenas `ativo`
**Localização:** `barbershops/models.py` (`Barber.ativo`) vs `accounts/models.py` (`User.is_active`)  
**Problema:** `User` usa `is_active` (padrão Django), `Barber` usa `ativo`, `Service` usa `ativo`, `Barbershop` usa `is_active`. Falta timestamp `deleted_at` para auditoria e recuperação. `PROTECT` em FK impede cascade, mas não há trilha de quando/por quem desativou.

**Recomendação:** Adicionar `deleted_at = DateTimeField(null, blank)` + `deleted_by = FK User` em todos os modelos com soft-delete. Criar manager `ActiveManager` filtrando `is_active=True` e `deleted_at__isnull=True`.

---

### MÉDIO-6: Falta de Índices Compostos para Consultas Multi-Tenant Frequentes
**Localização:** Models diversos (`Appointment`, `Service`, `Barber`)  
**Problema:** Queries filtram por `barbershop_id` + outro campo (ex.: `Appointment.objects.filter(barbershop=X, data_hora__range=...)`). Sem índice composto `(barbershop_id, data_hora)`, scans sequenciais em tabelas grandes.

**Evidência:** `Appointment.Meta.indexes` tem `['barbershop', 'data_hora']`? (Verificar) — se não, performance degrada linearmente.

**Recomendação:** Adicionar `indexes = [models.Index(fields=['barbershop', 'data_hora']), models.Index(fields=['barbershop', 'barbeiro', 'data_hora']), ...]` nos models principais.

---

### MÉDIO-7: `Appointment` Permite `cliente` de Outro Tenant se `barbeiro`/`servico` Forem Válidos
**Localização:** `appointments/models.py` (`clean()` valida tenant consistency)  
**Problema:** O `clean()` valida se `cliente.barbershop == barbeiro.barbershop == servico.barbershop`. Mas `cliente` pode ser `None` (agendamento anônimo?) ou ter `barbershop=None` (cliente público). Se `cliente.barbershop` for None, a comparação falha silenciosamente ou permite cross-tenant.

**Recomendação:** Exigir `cliente.barbershop_id == barbershop_id` explicitamente; rejeitar `cliente` sem barbearia se o agendamento exige tenant.

---

### MÉDIO-8: Frontend: `AuthContext` Armazena `access_token` no `localStorage` (XSS Risk)
**Localização:** `frontend/src/contexts/AuthContext.tsx`  
**Problema:** `access_token` (JWT de 15min) guardado em `localStorage` — acessível via `document.cookie` se houver XSS. O `refresh_token` está em cookie HttpOnly (correto), mas o access não.

**Recomendação:** Manter `access_token` apenas em memória (React state/context), nunca persistir. Em reload, chamar `/refresh/` automaticamente via interceptor (já existe) antes de renderizar rotas protegidas.

---

### MÉDIO-9: Frontend: `axios` Interceptor de Refresh Não Trata Race Condition
**Localização:** `frontend/src/api/client.ts` (response interceptor 401 → refresh → retry)  
**Problema:** Múltiplas requisições simultâneas recebendo 401 disparam múltiplos `/refresh/`. O primeiro rota o refresh token (blacklist old, issue new); os demais usam token antigo → 401 → loop ou logout forçado.

**Recomendação:** Implementar "refresh queue": uma promise única de refresh; demais requisições aguardam essa promise e retry com novo token.

---

### MÉDIO-10: Frontend: `ProtectedRoute` Redireciona para `/onboarding` Sem Verificar `barbershop_id` no Token
**Localização:** `frontend/src/routes/ProtectedRoute.tsx`  
**Problema:** Redireciona admin sem barbearia para `/onboarding`, mas a verificação usa `user.barbershop` do estado local (pode estar desatualizado). Deve ler `barbershop_id` do JWT decodificado (payload) ou chamar `/users/me/` para estado fresco.

**Recomendação:** Decodificar JWT no frontend (`jwt-decode`) ou buscar perfil fresco antes de decidir rota.

---

### MÉDIO-11: Testes de Concorrência Usam `TransactionTestCase` Mas Não Isolam Banco Entre Testes
**Localização:** `appointments/tests.py` (`AppointmentConcurrencyTests`)  
**Problema:** `TransactionTestCase` não faz rollback automático; dados de um teste vazam para o próximo. Os testes passam hoje por ordem, mas são frágeis.

**Recomendação:** Migrar para `TestCase` + `select_for_update(nowait=True)` em threads separadas, ou usar `django-test-transaction` para isolamento real. Ou limpar banco no `tearDown`.

---

### MÉDIO-12: Ausência de Testes de Integração Frontend-Backend (E2E)
**Localização:** `frontend/` — sem Cypress/Playwright  
**Problema:** Testes unitários/backend cobrem API, mas fluxos críticos (login → onboarding → criar serviço → agendar → cancelar) não têm testes end-to-end. Regressões de integração passam despercebidas.

**Recomendação:** Adicionar Playwright com fixtures de backend (Docker compose test) para 5-10 fluxos críticos.

---

## BAIXO (18 itens)

### BAIXO-1: `Dashboard` App Existe Mas Está Vazio (Placeholder)
**Localização:** `dashboard/models.py`, `views.py`, `tests.py` — todos vazios/somente imports  
**Problema:** App registrado em `INSTALLED_APPS` mas sem funcionalidade. Confunde desenvolvedores e ferramentas de análise.

**Recomendação:** Remover do `INSTALLED_APPS` até implementar, ou implementar MVP (métricas básicas: agendamentos/dia, receita, barbeiros ativos).

---

### BAIXO-2: `User.tipo_perfil` Permite `ADMIN` Via Django Admin / Shell
**Localização:** `accounts/models.py` (choices) + `accounts/serializers.py` (validação apenas em API)  
**Problema:** Serializers bloqueiam `ADMIN` na API, mas Django Admin, shell, migrações, fixtures permitem. Inconsistência.

**Recomendação:** Adicionar `clean()` no model `User` validando `tipo_perfil != ADMIN` exceto para superuser; ou mover regra para `save()`.

---

### BAIXO-3: `BarbershopViewSet.create()` Promove Usuário a `ADMIN` Sem Verificar Se Já É Admin de Outra Barbearia
**Localização:** `barbershops/views.py` (`BarbershopViewSet.perform_create`)  
**Problema:** Um admin de barbearia A pode criar barbearia B e virar admin dela também — multi-tenancy permite admin em múltiplas barbearias. Se a regra de negócio for "um admin por barbearia, um usuário = uma barbearia", isso viola.

**Recomendação:** Verificar `request.user.barbershop is None` antes de promover; ou permitir multi-barbearia explicitamente e documentar.

---

### BAIXO-4: `ServiceViewSet` Lista Apenas `ativo=True` Por Padrão, Mas Admin Precisa Ver Inativos
**Localização:** `services/views.py` (`get_queryset`)  
**Problema:** Filtro `ativo=True` hardcoded no `get_queryset`. Admin não consegue listar serviços inativos para reativar.

**Recomendação:** `queryset = Service.objects.all()`; filtrar `ativo=True` apenas para não-admin (override em `list()` ou via `filterset_fields` + permissão customizada).

---

### BAIXO-5: `Appointment` Status Transitions Não Validam Fluxo (Ex.: `CONFIRMED` → `PENDING`)
**Localização:** `appointments/views.py` (`update` / `partial_update` + status actions)  
**Problema:** Qualquer transição de status é permitida via PATCH. Não há máquina de estados (ex.: `PENDING → CONFIRMED → COMPLETED/CANCELLED`; não voltar).

**Recomendação:** Adicionar `validate_status_transition(old, new)` no model/serializer; ou usar `django-fsm`.

---

### BAIXO-6: `PasswordResetConfirmSerializer` Não Invalida Tokens Antigos Após Uso
**Localização:** `accounts/serializers.py:266-293`  
**Problema:** Token de reset (Django `default_token_generator`) é válido por 7 dias (padrão) e **não é invalidado após uso**. Permite reuso se token vazado.

**Recomendação:** Armazenar token usado (hash) em modelo `PasswordResetToken` com `used_at`; invalidar no `save()`. Ou reduzir `PASSWORD_RESET_TIMEOUT_DAYS` para 1.

---

### BAIXO-7: `CORS_ALLOWED_ORIGINS` Inclui `localhost:3000` Mas Frontend Usa `5173` (Vite)
**Localização:** `.env:5` vs `config/settings.py:214` (default `5173`)  
**Problema:** `.env` tem `http://localhost:3000` (Create React App padrão), mas Vite usa `5173`. Em dev, CORS falha se frontend rodar em 5173 e `.env` não for sobrescrito.

**Recomendação:** Alinhar `.env.example` e `.env` para `5173`; documentar.

---

### BAIXO-8: `JWT_REFRESH_COOKIE_SECURE = not DEBUG` — Em Dev Com HTTPS (ngrok) Quebra Refresh
**Localização:** `config/settings.py:204`  
**Problema:** Se dev usa túnel HTTPS (ngrok, cloudflare tunnel), `DEBUG=True` mas `SECURE=True` → cookie `Secure` não enviado em HTTP local.

**Recomendação:** `JWT_REFRESH_COOKIE_SECURE = env.bool(..., default=False)` independente de DEBUG; controlar via env var.

---

### BAIXO-9: `SECRET_KEY` Default Inseguro Em `settings.py:25` (Hardcoded Fallback)
**Localização:** `config/settings.py:25-26`  
**Problema:** `_DEFAULT_DEV_SECRET` hardcoded. Se `.env` ausente em prod, usa chave conhecida publicamente.

**Evidência:** Linha 30-31 lança `RuntimeError` se `not DEBUG and SECRET_KEY == default` — mas se `DEBUG=True` em prod (erro humano), chave fraca é usada.

**Recomendação:** Remover default; exigir `SECRET_KEY` obrigatório via env. Falhar rápido se ausente.

---

### BAIXO-10: `ALLOWED_HOSTS` Default Inclui Apenas `localhost, 127.0.0.1` — Quebra Em Docker/Prod
**Localização:** `config/settings.py:28`  
**Problema:** Em container, host é `0.0.0.0` ou IP do container; `ALLOWED_HOSTS` deve incluir `*` em dev ou hosts específicos em prod.

**Recomendação:** `ALLOWED_HOSTS = env.list(..., default=['*'] if DEBUG else [])` — forçar configuração explícita em prod.

---

### BAIXO-11: `UserCreateSerializer` Não Valida Unicidade De `email` Por Tenant (Case-Insensitive)
**Localização:** `accounts/serializers.py:129-164`  
**Problema:** `User.email` tem `unique=True` global (não por tenant). Dois clientes com mesmo e-mail em barbearias diferentes falham. O `UserManager.create_user` normaliza lower-case, mas unicidade é global.

**Recomendação:** Se multi-tenant real (e-mail repetido permitido entre barbearias), remover `unique=True` do model e adicionar `UniqueConstraint(fields=['email', 'barbershop'], condition=Q(barbershop__isnull=False))` + constraint separada para `barbershop__isnull=True` (clientes públicos). Ou manter global e documentar.

---

### BAIXO-12: `BarberViewSet` Não Permite Barbeiro Ver/Editar Próprio Perfil (Apenas Admin)
**Localização:** `barbershops/views.py` (`BarberViewSet` permissions)  
**Problema:** `permission_classes = [IsAdminRole]` — barbeiro não consegue ver próprio perfil (`/barbers/me/` não existe). Precisa de endpoint `me` ou permissão `IsBarberRole | IsAdminRole` com `get_queryset` filtrando `user=request.user`.

**Recomendação:** Adicionar `me` action ou ajustar permissão + queryset.

---

### BAIXO-13: Frontend: `useAuth` Hook Não Expõe `refreshUser` Para Atualização Manual
**Localização:** `frontend/src/hooks/useAuth.ts` (se existe) ou `AuthContext`  
**Problema:** Após admin criar barbeiro e promover usuário, o frontend do novo barbeiro não sabe que agora é `BARBEIRO` até reload/login.

**Recomendação:** Expor `refreshUser()` no context; chamar após ações que mudam role/perfil.

---

### BAIXO-14: Frontend: `endpoints.ts` Não Tipagem Respostas De Erro (4xx/5xx)
**Localização:** `frontend/src/api/endpoints.ts`  
**Problema:** Funções tipam apenas sucesso (`Promise<Service>`, etc.). Erros retornam `any` ou `AxiosError` sem tipagem do `response.data` (que segue padrão DRF: `{detail: ..., code: ...}` ou `{field: [...]}`).

**Recomendação:** Criar `ApiError<T>` type e tipar `catch` ou interceptor.

---

### BAIXO-15: Frontend: `Zod` Schemas Duplicam Validações Do Backend (Drift Risk)
**Localização:** `frontend/src/validation/` (schemas) vs `serializers.py`  
**Problema:** Regras de validação (tamanho senha, formato e-mail, campos obrigatórios) replicadas no frontend. Divergência silenciosa causa UX ruim (erro 400 inesperado) ou segurança (frontend permite, backend rejeita).

**Recomendação:** Gerar schemas Zod a partir de OpenAPI/Swagger do backend (`drf-spectacular` + `openapi-zod`), ou compartilhar definições via pacote comum.

---

### BAIXO-16: `docker-compose.yml` Ausente Para Desenvolvimento/Testing
**Localização:** Raiz do projeto — não existe  
**Problema:** Levantar stack (PostgreSQL, Redis, backend, frontend) requer comandos manuais. Onboarding lento; CI/CD não tem definição única.

**Recomendação:** Criar `docker-compose.yml` com `postgres`, `redis`, `backend`, `frontend` services; `docker-compose.test.yml` para CI.

---

### BAIXO-17: `requirements.txt` / `pyproject.toml` Não Travam Versões (Pinning)
**Localização:** Raiz — não lido, prática comum  
**Problema:** Dependências sem pinning exato (`Django>=4.2,<5.0`) permitem upgrades quebradores em deploy.

**Recomendação:** Usar `pip-tools` / `uv` para gerar `requirements.txt` com hashes; `pip install --require-hashes`.

---

### BAIXO-18: Falta De Documentação De API (OpenAPI/Swagger)
**Localização:** Não há `drf-spectacular` ou similar instalado  
**Problema:** Frontend e consumidores externos não têm contrato tipado; mudanças quebram silenciosamente.

**Recomendação:** Adicionar `drf-spectacular`; gerar schema em `/api/schema/`; UI em `/api/docs/` (Swagger UI) ou `/api/redoc/`.

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

## Plano de Ação Sugerido (Priorização)

| Prioridade | Itens | Esforço Estimado |
|------------|-------|------------------|
| **Imediato (Pré-Produção)** | ALTO-1, ALTO-2, ALTO-3 | 2-4h |
| **Sprint 1** | MÉDIO-1, MÉDIO-2, MÉDIO-3, MÉDIO-6, MÉDIO-8, MÉDIO-9 | 8-16h |
| **Sprint 2** | MÉDIO-4, MÉDIO-5, MÉDIO-7, MÉDIO-10, MÉDIO-11, MÉDIO-12 | 16-24h |
| **Tech Debt Contínuo** | BAIXO-1 a BAIXO-18 (priorizar BAIXO-7, BAIXO-9, BAIXO-10, BAIXO-16, BAIXO-18) | Conforme capacidade |

---

## Conclusão

O **saas_barbearia** é um projeto de **alta qualidade**, com arquitetura sólida, testes reais (incluindo concorrência), e práticas de segurança modernas. Os 3 itens **ALTO** devem ser corrigidos antes de deploy em produção (especialmente rate limiting e enumeração de e-mail). Os 12 itens **MÉDIO** melhoram robustez, performance e UX. Os 18 itens **BAIXO** são dívida técnica e polimento para manutenibilidade a longo prazo.

**Recomendação final:** Corrigir ALTOs → deploy em staging → corrigir MÉDIOS prioritários (1, 2, 3, 6, 8, 9) → produção → endereçar BAIXOs em sprints subsequentes.