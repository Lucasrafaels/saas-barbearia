# Documentação da API — SaaS Barbearia

Base URL local: `http://127.0.0.1:8000/api/v1`

As requisições e respostas usam JSON, exceto o envio de `logo`, que deve usar
`multipart/form-data`.

## Convenções

### Autenticação

As rotas protegidas exigem:

```http
Authorization: Bearer <access_token>
```

Perfis: `cliente`, `barbeiro` e `admin`. Dados de negócio são isolados por
barbearia (tenant).

### Paginação e erros

Listagens são paginadas em 20 itens e retornam `count`, `next`, `previous` e
`results`. Use `?page=2` para consultar outra página.

- `400`: dados ausentes ou inválidos.
- `401`: token ausente, inválido ou expirado.
- `403`: perfil sem permissão.
- `404`: recurso inexistente ou fora do escopo do usuário.

## Matriz de acesso

| Recurso | Cliente | Barbeiro | Admin |
| --- | --- | --- | --- |
| Usuários | próprio cadastro | próprio cadastro | usuários do tenant |
| Barbearia | consulta | consulta | consulta e edição |
| Barbeiros e serviços | consulta | consulta | CRUD |
| Agendamentos | próprios | própria agenda | todos do tenant |

> A exclusão de uma barbearia exige `is_staff=True`, isto é, é reservada à
> equipe da plataforma.

---

## Autenticação

### `POST /auth/register/`

Pública. Cria uma conta inicial com perfil `cliente` e sem barbearia.

```json
{
  "email": "ana@example.com",
  "nome": "Ana Silva",
  "password": "UmaSenhaForte-2026"
}
```

Resposta: `201 Created`. As regras de senha do Django são aplicadas: tamanho
mínimo, senha comum, senha numérica e similaridade com nome/e-mail.

### `POST /auth/login/`

Pública.

```json
{
  "email": "ana@example.com",
  "password": "UmaSenhaForte-2026"
}
```

Resposta:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

O access token expira em 60 minutos e o refresh em 7 dias. Os claims do token
incluem `nome`, `tipo_perfil` e `barbershop_id`, mas o backend revalida as
permissões no banco.

### `POST /auth/refresh/`

Pública. Envie o refresh token:

```json
{"refresh": "<refresh_token>"}
```

### `POST /auth/logout/`

Protegida. Invalida o refresh token enviado e responde `205 Reset Content`.

```json
{"refresh": "<refresh_token>"}
```

---

## Usuários

Objeto retornado:

```json
{
  "id": 12,
  "email": "ana@example.com",
  "nome": "Ana Silva",
  "tipo_perfil": "cliente",
  "barbershop": 3,
  "is_active": true,
  "created_at": "2026-08-21T12:00:00-03:00"
}
```

| Rota | Permissão | Descrição |
| --- | --- | --- |
| `GET /users/` | Admin | Lista usuários do tenant. |
| `POST /users/` | Admin | Cria cliente ou barbeiro no tenant do admin. |
| `GET /users/{id}/` | Próprio ou admin | Consulta usuário. |
| `PATCH`/`PUT /users/{id}/` | Próprio ou admin | Atualiza cadastro. |
| `DELETE /users/{id}/` | Admin | Remove usuário. |
| `GET /users/me/` | Autenticado | Dados do usuário logado. |

Criação interna de cliente/barbeiro:

```json
{
  "email": "joao.barbeiro@example.com",
  "nome": "João Barbeiro",
  "password": "OutraSenhaForte-2026",
  "tipo_perfil": "barbeiro"
}
```

Não envie `barbershop`: ela é obtida da sessão do admin. Não é permitido criar
outro `admin` por essa rota. Após criar um usuário barbeiro, crie também seu
perfil profissional em `POST /barbers/`.

Para alterações de perfil no frontend, envie somente campos pessoais, por
exemplo:

```json
{"nome": "Ana Souza", "email": "ana.souza@example.com"}
```

---

## Barbearias

Campos de criação: `nome`, `endereco`, `telefone`, `email`,
`horario_abertura` e `horario_fechamento`. `logo` é opcional e `ativo` é
booleano.

| Rota | Permissão | Descrição |
| --- | --- | --- |
| `GET /barbershops/` | Autenticado | Lista a própria barbearia. |
| `GET /barbershops/{id}/` | Autenticado | Consulta a própria barbearia. |
| `POST /barbershops/` | Autenticado sem tenant | Cria a primeira barbearia e promove o criador a admin. |
| `PATCH`/`PUT /barbershops/{id}/` | Admin | Atualiza dados da barbearia. |
| `DELETE /barbershops/{id}/` | Staff | Exclui a barbearia. |

Exemplo:

```json
{
  "nome": "Barbearia Central",
  "endereco": "Rua Principal, 100",
  "telefone": "11999999999",
  "email": "contato@central.com",
  "horario_abertura": "08:00:00",
  "horario_fechamento": "18:00:00"
}
```

Para enviar `logo`, use `multipart/form-data`.

---

## Barbeiros

Objeto retornado:

```json
{
  "id": 7,
  "user": 15,
  "nome": "João Barbeiro",
  "email": "joao.barbeiro@example.com",
  "barbershop": 3,
  "especialidade": "Corte e barba",
  "ativo": true,
  "created_at": "2026-08-21T12:00:00-03:00"
}
```

| Rota | Permissão |
| --- | --- |
| `GET /barbers/`, `GET /barbers/{id}/` | Qualquer autenticado do tenant |
| `POST /barbers/` | Admin |
| `PATCH`, `PUT`, `DELETE /barbers/{id}/` | Admin |

Criação:

```json
{
  "user": 15,
  "especialidade": "Corte e barba",
  "ativo": true
}
```

O usuário indicado precisa ter perfil `barbeiro` e pertencer ao mesmo tenant.
A barbearia é definida pelo servidor.

---

## Serviços

Campos: `nome`, `descricao`, `preco`, `duracao` (minutos) e `ativo`.

| Rota | Permissão |
| --- | --- |
| `GET /services/`, `GET /services/{id}/` | Qualquer autenticado do tenant |
| `POST /services/` | Admin |
| `PATCH`, `PUT`, `DELETE /services/{id}/` | Admin |

Exemplo:

```json
{
  "nome": "Corte masculino",
  "descricao": "Corte tradicional",
  "preco": "50.00",
  "duracao": 30,
  "ativo": true
}
```

Filtro disponível: `GET /services/?ativo=true`.

---

## Agendamentos

Objeto retornado:

```json
{
  "id": 31,
  "barbershop": 3,
  "cliente": 12,
  "cliente_nome": "Ana Silva",
  "barbeiro": 7,
  "barbeiro_nome": "João Barbeiro",
  "servico": 4,
  "servico_nome": "Corte masculino",
  "data_hora": "2026-08-25T10:00:00-03:00",
  "status": "agendado",
  "observacoes": "Preferência por máquina baixa",
  "created_at": "2026-08-21T12:00:00-03:00"
}
```

Status: `agendado`, `confirmado`, `realizado` e `cancelado`.

| Rota | Permissão |
| --- | --- |
| `GET /appointments/`, `GET /appointments/{id}/` | Cliente: próprios; barbeiro: própria agenda; admin: tenant inteiro |
| `POST /appointments/` | Autenticado, dentro do escopo do perfil |
| `PATCH`, `PUT`, `DELETE /appointments/{id}/` | Mesmo escopo da consulta |

Criação:

```json
{
  "cliente": 12,
  "barbeiro": 7,
  "servico": 4,
  "data_hora": "2026-08-25T10:00:00-03:00",
  "observacoes": "Preferência por máquina baixa"
}
```

Regras aplicadas:

- cliente deve ter perfil `cliente` e pertencer ao tenant;
- barbeiro e serviço devem pertencer ao tenant;
- o mesmo barbeiro não pode ter horários sobrepostos;
- cliente sempre agenda para si;
- barbeiro só gerencia a própria agenda;
- cliente não pode transferir um agendamento para outra pessoa.

Filtros: `?status=agendado`, `?barbeiro=7` e `?servico=4`.

Mesmo quando cliente ou barbeiro têm o valor forçado pelo servidor, envie os
IDs corretos de `cliente` e `barbeiro`, pois esses campos são obrigatórios no
serializer.

---

## Fluxo recomendado para o frontend

1. Criar conta em `POST /auth/register/`.
2. Autenticar em `POST /auth/login/`.
3. Buscar o perfil em `GET /users/me/`.
4. Se `barbershop` for `null`, criar a primeira barbearia.
5. Admin cria usuários barbeiros, perfis de barbeiro e serviços.
6. Cliente lista barbeiros e serviços, cria e acompanha agendamentos.

## Atenção antes de integrar o frontend

O contrato acima trata `tipo_perfil` e `barbershop` como dados controlados
pelo servidor. O frontend não deve enviá-los em edições de usuário. Antes do
deploy, vale fazer uma última revisão para garantir que o serializer de
atualização também marque esses campos como somente leitura.

Da mesma forma, o fluxo de criação de barbearia é destinado a contas sem
tenant. A tela deve oferecer essa ação apenas quando `GET /users/me/` retornar
`barbershop: null`; uma validação explícita no backend para esse cenário é uma
boa melhoria de endurecimento antes da produção.

## Rotas ainda não implementadas

Esta versão ainda não possui endpoint de horários disponíveis, cancelamento
com antecedência, recuperação de senha, dashboard ou relatórios. Não integre
essas telas como se as rotas já existissem. O próximo endpoint recomendado é
uma rota de disponibilidade, por exemplo `GET /appointments/available-slots/`.
