# TEN-03 — matriz dos cenários reproduzidos (15/11/2026)

API de laboratório com o código atual, sem alteração, `DEBUG=False`, sobre o PostgreSQL 18.3 descartável `t3_db` (127.0.0.1:55432). Dados fictícios. A barbearia A tem `id=1`; a B, `id=2`.

Colunas: **Consulta de existência** = o servidor executou `SELECT 1 AS "a" FROM "accounts_user" WHERE "accounts_user"."email" = … LIMIT 1` (o `UniqueValidator` do DRF), com ou sem filtro de barbearia. **Conta com o e-mail** = a barbearia da conta que já tinha o e-mail antes do pedido. **Fora do alcance** = essa conta não poderia ser listada pelo solicitante na API (admin A lista só A; cliente e barbeiro, só a si; superusuário, todas).


## POST /auth/register/ (cadastro público)

| ID | Cenário | Papel (tenant) | Pedido | Status | Resposta integral | Criou conta | Alterou alvo | Consulta de existência | Conta com o e-mail | Fora do alcance | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R01 | e-mail nunca utilizado, senha válida | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 201 | `{"id": 11, "email": "novo.r01@exemplo.test", "nome": "Rita Nova", "tipo_perfil": "cliente", "barbershop": null, "is_active": true, "created_at": "2026-11-15T16:25:33.744334-03:00"}` | 1 | — | sim, sem filtro de barbearia | nenhuma | não | 265.7 |
| R02 | e-mail de outra conta sem barbearia (mesmo "espaço" do cadastro público) | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | (sem barbearia) | **sim** | 20.5 |
| R03 | e-mail de cliente da barbearia B | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 12.9 |
| R04 | e-mail de cliente de B + senha que falha nos validadores (sem efeito colateral) | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 13.5 |
| R05 | e-mail nunca utilizado + a mesma senha fraca (par do R04) | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"password": ["Esta senha é muito comum.", "Esta senha é inteiramente numérica."]}` | 0 | — | sim, sem filtro de barbearia | nenhuma | não | 18.6 |
| R06 | e-mail de cliente de B com maiúsculas na parte local (Cliente.B@...) | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 201 | `{"id": 12, "email": "Cliente.B@beta.test", "nome": "Rita Nova", "tipo_perfil": "cliente", "barbershop": null, "is_active": true, "created_at": "2026-11-15T16:25:36.509634-03:00"}` | 1 | — | sim, sem filtro de barbearia | nenhuma exata; B com outra caixa | **sim** | 243.7 |
| R07 | e-mail de cliente de B com maiúsculas no domínio (...@BETA.TEST) | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 500 | `HTML "Server Error (500)"` | 0 | — | sim, sem filtro de barbearia | nenhuma exata; B com outra caixa | **sim** | 331.6 |
| R08 | e-mail nunca utilizado com maiúsculas no domínio (par do R07) | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 201 | `{"id": 14, "email": "novo.r08@exemplo.test", "nome": "Rita Nova", "tipo_perfil": "cliente", "barbershop": null, "is_active": true, "created_at": "2026-11-15T16:25:38.042374-03:00"}` | 1 | — | sim, sem filtro de barbearia | nenhuma | não | 244.0 |
| R09 | e-mail de cliente de B com espaços antes e depois | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 12.6 |
| R10 | e-mail de conta INATIVA de B | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 13.7 |
| R11 | e-mail do superusuário da plataforma | anônimo ((anônimo)) | `POST /api/v1/auth/register/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | (sem barbearia) | **sim** | 13.3 |

## POST /users/ (criação de usuário)

| ID | Cenário | Papel (tenant) | Pedido | Status | Resposta integral | Criou conta | Alterou alvo | Consulta de existência | Conta com o e-mail | Fora do alcance | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C01 | admin A cria cliente com e-mail nunca utilizado | admin_a (A) | `POST /api/v1/users/` | 201 | `{"id": 15, "email": "novo.c01@exemplo.test", "nome": "Caio Novo", "tipo_perfil": "cliente", "barbershop": 1}` | 1 | — | sim, sem filtro de barbearia | nenhuma | não | 253.1 |
| C02 | admin A cria cliente com e-mail de cliente A2 (mesma barbearia) | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | A | não | 15.9 |
| C03 | admin A cria cliente com e-mail de cliente de B (outra barbearia) | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 14.3 |
| C04 | admin A: e-mail de cliente de B + senha fraca (sem efeito colateral) | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 17.4 |
| C05 | admin A: e-mail nunca utilizado + a mesma senha fraca (par do C04) | admin_a (A) | `POST /api/v1/users/` | 400 | `{"password": ["Esta senha é muito comum.", "Esta senha é inteiramente numérica."]}` | 0 | — | sim, sem filtro de barbearia | nenhuma | não | 15.6 |
| C06 | admin A cria barbeiro com e-mail de barbeiro de B | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 15.3 |
| C07 | admin A cria cliente com e-mail do admin de B | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 17.1 |
| C08 | admin A: e-mail de cliente de B com maiúsculas na parte local | admin_a (A) | `POST /api/v1/users/` | 201 | `{"id": 16, "email": "Cliente.B@beta.test", "nome": "Caio Novo", "tipo_perfil": "cliente", "barbershop": 1}` | 1 | — | sim, sem filtro de barbearia | nenhuma exata; B com outra caixa | **sim** | 248.5 |
| C09 | admin A: e-mail de cliente de B com maiúsculas no domínio | admin_a (A) | `POST /api/v1/users/` | 500 | `HTML "Server Error (500)"` | 0 | — | sim, sem filtro de barbearia | nenhuma exata; B com outra caixa | **sim** | 276.5 |
| C10 | admin A: e-mail de cliente de B com espaços | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 15.8 |
| C11 | admin A: e-mail de conta INATIVA de B | admin_a (A) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | **sim** | 15.4 |
| C12 | cliente A1 tenta criar usuário com e-mail de B | cliente_a1 (A) | `POST /api/v1/users/` | 403 | `{"detail": "Você não tem permissão para executar essa ação."}` | 0 | — | não | B | **sim** | 11.8 |
| C13 | barbeiro A tenta criar usuário com e-mail de B | barbeiro_a (A) | `POST /api/v1/users/` | 403 | `{"detail": "Você não tem permissão para executar essa ação."}` | 0 | — | não | B | **sim** | 12.1 |
| C14 | conta sem barbearia tenta criar usuário com e-mail de B | sem_barbearia ((sem barbearia)) | `POST /api/v1/users/` | 403 | `{"detail": "Você não tem permissão para executar essa ação."}` | 0 | — | não | B | **sim** | 13.5 |
| C15 | superusuário (sem barbearia) cria com e-mail de B | superuser ((plataforma)) | `POST /api/v1/users/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | — | sim, sem filtro de barbearia | B | não | 15.0 |
| C16 | superusuário (sem barbearia) cria com e-mail nunca utilizado | superuser ((plataforma)) | `POST /api/v1/users/` | 400 | `{"barbershop": "O administrador precisa pertencer a uma barbearia."}` | 0 | — | sim, sem filtro de barbearia | nenhuma | não | 17.4 |

## PATCH/PUT /users/{id}/ (edição)

| ID | Cenário | Papel (tenant) | Pedido | Status | Resposta integral | Criou conta | Alterou alvo | Consulta de existência | Conta com o e-mail | Fora do alcance | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | cliente A1 troca o próprio e-mail por um nunca utilizado | cliente_a1 (A) | `PATCH /api/v1/users/3/` | 200 | `{"id": 3, "email": "novo.p01@exemplo.test", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | sim | sim, sem filtro de barbearia | nenhuma | não | 23.5 |
| P02 | cliente A1 reenvia o próprio e-mail | cliente_a1 (A) | `PATCH /api/v1/users/3/` | 200 | `{"id": 3, "email": "cliente.a1@alfa.test", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | não | sim, sem filtro de barbearia | A | não | 23.8 |
| P03 | cliente A1 tenta usar o e-mail de cliente A2 (mesma barbearia) | cliente_a1 (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | A | **sim** | 17.9 |
| P04 | cliente A1 tenta usar o e-mail de cliente de B (outra barbearia) | cliente_a1 (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 17.1 |
| P05 | cliente A1: e-mail de B + nome vazio (sem efeito colateral) | cliente_a1 (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."], "nome": ["Este campo não pode ser em branco."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 17.0 |
| P06 | cliente A1: e-mail nunca utilizado + nome vazio (par do P05) | cliente_a1 (A) | `PATCH /api/v1/users/3/` | 400 | `{"nome": ["Este campo não pode ser em branco."]}` | 0 | não | sim, sem filtro de barbearia | nenhuma | não | 18.6 |
| P07 | barbeiro A tenta usar o e-mail de cliente de B na própria conta | barbeiro_a (A) | `PATCH /api/v1/users/2/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 17.6 |
| P08 | admin A tenta usar o e-mail do admin de B na própria conta | admin_a (A) | `PATCH /api/v1/users/1/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 21.0 |
| P09 | admin A dá ao cliente A1 um e-mail nunca utilizado | admin_a (A) | `PATCH /api/v1/users/3/` | 200 | `{"id": 3, "email": "novo.p09@exemplo.test", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | sim | sim, sem filtro de barbearia | nenhuma | não | 21.8 |
| P10 | admin A dá ao cliente A1 o e-mail do cliente A2 (mesma barbearia) | admin_a (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | A | não | 19.0 |
| P11 | admin A dá ao cliente A1 o e-mail de cliente de B | admin_a (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 16.9 |
| P12 | admin A reenvia o e-mail atual do cliente A1 | admin_a (A) | `PATCH /api/v1/users/3/` | 200 | `{"id": 3, "email": "cliente.a1@alfa.test", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | não | sim, sem filtro de barbearia | A | não | 22.2 |
| P13 | admin A tenta editar o e-mail de um cliente de B | admin_a (A) | `PATCH /api/v1/users/7/` | 404 | `{"detail": "No User matches the given query."}` | 0 | não | não | nenhuma | não | 13.9 |
| P14 | cliente A1 tenta editar o e-mail do cliente A2 (SEC-12: 403, não alterado) | cliente_a1 (A) | `PATCH /api/v1/users/4/` | 403 | `{"detail": "Você não tem permissão para executar essa ação."}` | 0 | não | não | B | **sim** | 16.5 |
| P15 | admin A: cliente A1 com e-mail de B em maiúsculas na parte local | admin_a (A) | `PATCH /api/v1/users/3/` | 200 | `{"id": 3, "email": "Cliente.B@beta.test", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | sim | sim, sem filtro de barbearia | nenhuma exata; B com outra caixa | **sim** | 21.9 |
| P16 | admin A: cliente A1 com e-mail de B em maiúsculas no domínio | admin_a (A) | `PATCH /api/v1/users/3/` | 200 | `{"id": 3, "email": "cliente.b@BETA.TEST", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | sim | sim, sem filtro de barbearia | nenhuma exata; B com outra caixa | **sim** | 21.7 |
| P17 | admin A: cliente A1 com e-mail de B com espaços | admin_a (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 17.8 |
| P18 | admin A: cliente A1 com e-mail de conta INATIVA de B | admin_a (A) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 17.0 |
| P19 | conta sem barbearia tenta trocar o próprio e-mail | sem_barbearia ((sem barbearia)) | `PATCH /api/v1/users/9/` | 404 | `{"detail": "No User matches the given query."}` | 0 | não | não | B | **sim** | 13.3 |
| P20 | superusuário dá ao cliente A1 o e-mail de cliente de B | superuser ((plataforma)) | `PATCH /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | não | 16.3 |
| P21 | PUT: admin A envia o cadastro do cliente A1 com e-mail de B | admin_a (A) | `PUT /api/v1/users/3/` | 400 | `{"email": ["usuário com este e-mail já existe."]}` | 0 | não | sim, sem filtro de barbearia | B | **sim** | 17.8 |
| P22 | PUT: admin A envia o cadastro do cliente A1 com e-mail nunca utilizado | admin_a (A) | `PUT /api/v1/users/3/` | 200 | `{"id": 3, "email": "novo.p22@exemplo.test", "nome": "Carlos Cliente A1", "tipo_perfil": "cliente", "barbershop": 1, "is_active": true, "created_at": "2026-11-15T16:23:10.443312-03:00"}` | 0 | sim | sim, sem filtro de barbearia | nenhuma | não | 20.8 |

## login e recuperação de senha (comparação)

| ID | Cenário | Papel (tenant) | Pedido | Status | Resposta integral | Criou conta | Alterou alvo | Consulta de existência | Conta com o e-mail | Fora do alcance | ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L01 | login: e-mail existente (cliente de B), senha errada | anônimo ((anônimo)) | `POST /api/v1/auth/login/` | 401 | `{"detail": "Usuário e/ou senha incorreto(s)"}` | 0 | — | não | B | **sim** | 247.8 |
| L02 | login: e-mail nunca utilizado | anônimo ((anônimo)) | `POST /api/v1/auth/login/` | 401 | `{"detail": "Usuário e/ou senha incorreto(s)"}` | 0 | — | não | nenhuma | não | 238.8 |
| L03 | login: conta inativa com a senha correta | anônimo ((anônimo)) | `POST /api/v1/auth/login/` | 401 | `{"detail": "Usuário e/ou senha incorreto(s)"}` | 0 | — | não | B | **sim** | 248.7 |
| L04 | login: cliente A1 com a senha correta e maiúsculas na parte local | anônimo ((anônimo)) | `POST /api/v1/auth/login/` | 401 | `{"detail": "Usuário e/ou senha incorreto(s)"}` | 0 | — | não | nenhuma exata; A com outra caixa | **sim** | 256.0 |
| L05 | login: cliente A1 com a senha correta e maiúsculas no domínio | anônimo ((anônimo)) | `POST /api/v1/auth/login/` | 401 | `{"detail": "Usuário e/ou senha incorreto(s)"}` | 0 | — | não | nenhuma exata; A com outra caixa | **sim** | 238.1 |
| L06 | login: cliente A1 com a senha correta e espaços | anônimo ((anônimo)) | `POST /api/v1/auth/login/` | 200 | `{"access": "<token removido>"}` | 0 | — | não | A | **sim** | 259.6 |
| L07 | recuperação: e-mail existente | anônimo ((anônimo)) | `POST /api/v1/auth/password/reset/` | 204 | `(sem corpo)` | 0 | — | não | B | **sim** | 17.0 |
| L08 | recuperação: e-mail nunca utilizado | anônimo ((anônimo)) | `POST /api/v1/auth/password/reset/` | 204 | `(sem corpo)` | 0 | — | não | nenhuma | não | 14.3 |
| L09 | recuperação do cliente de B depois que um terceiro cadastrou "Cliente.B@beta.test" (nome "Aaron Variante") | anônimo ((anônimo)) | `POST /api/v1/auth/password/reset/` | 204 | `(sem corpo)` | 0 | — | não | B | **sim** | 14.1 |
