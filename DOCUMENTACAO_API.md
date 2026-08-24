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
| `PATCH`/`PUT /users/{id}/` | Próprio ou admin | Atualiza cadastro — ver restrições de campo abaixo. |
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

### Restrições de campo em `PATCH`/`PUT /users/{id}/`

`tipo_perfil` e `barbershop` são protegidos pelo servidor nesta rota — não é
uma convenção que depende do frontend se comportar bem:

- `barbershop` é sempre somente-leitura aqui. Não existe rota para trocar um
  usuário de tenant; se enviado, o valor é simplesmente ignorado.
- `tipo_perfil`: o próprio usuário nunca consegue alterar o seu (também
  ignorado se enviado). Um admin pode alterar o `tipo_perfil` de outro
  usuário do tenant entre `barbeiro` e `cliente`, mas não pode conceder
  `admin` por esta rota — a tentativa retorna `400` (mesma restrição já
  aplicada em `POST /users/`).

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

Se o usuário autenticado já pertencer a uma barbearia (como admin, barbeiro
ou cliente), a criação retorna `400` em vez de criar um segundo tenant: esta
rota é somente o onboarding inicial, e não é possível existir uma barbearia
sem nenhum admin vinculado a ela.

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
- o agendamento — do início ao fim, considerando a duração do serviço —
  precisa caber dentro do horário de funcionamento da barbearia (início
  igual à abertura e fim igual ao fechamento são aceitos; não pode
  atravessar a virada do dia);
- não é permitido marcar nem remarcar (`data_hora`) um agendamento para uma
  data/hora que já passou; já atualizar outros campos de um agendamento
  cuja data já passou — por exemplo marcar `status` como `realizado` ou
  incluir uma `observacoes` — continua permitido, exatamente para não
  travar o fechamento do atendimento;
- o mesmo barbeiro não pode ter horários sobrepostos;
- cliente sempre agenda para si;
- barbeiro só gerencia a própria agenda;
- cliente não pode transferir um agendamento para outra pessoa.

As comparações de horário de funcionamento e de "não permitir o passado" são
feitas na mesma timezone local do projeto usada em `available-slots`
(`TIME_ZONE`), não em UTC.

Filtros: `?status=agendado`, `?barbeiro=7` e `?servico=4`.

Mesmo quando cliente ou barbeiro têm o valor forçado pelo servidor, envie os
IDs corretos de `cliente` e `barbeiro`, pois esses campos são obrigatórios no
serializer.

### Horários disponíveis

#### `GET /appointments/available-slots/`

Autenticada. Retorna os horários em que um barbeiro ainda pode iniciar um
atendimento do serviço informado na data informada. Os slots começam no
horário de abertura da barbearia e avançam com passo igual à duração do
serviço, enquanto ainda caibam antes do fechamento.

| Parâmetro | Tipo | Descrição |
| --- | --- | --- |
| `barbeiro` | ID | Profissional consultado (obrigatório). |
| `servico` | ID | Serviço cujo `duracao` define o passo dos slots (obrigatório). |
| `data` | Data | Dia consultado no formato `YYYY-MM-DD` (obrigatório). |

```http
GET /api/v1/appointments/available-slots/?barbeiro=7&servico=4&data=2026-08-25
```

Resposta: `200 OK`

```json
{
  "data": "2026-08-25",
  "slots": ["09:00", "10:00", "14:00", "14:30"]
}
```

Regras:

- barbeiro e serviço devem pertencer ao tenant do usuário autenticado;
  caso contrário, `403`;
- agendamentos com status `cancelado` não bloqueiam horários;
- agendamentos de outros barbeiros são ignorados;
- erros: `400` se faltar parâmetro ou a data for inválida, `404` se barbeiro
  ou serviço não existirem, `401` sem autenticação.

Os horários são calculados na timezone local configurada no projeto
(`TIME_ZONE`), a mesma usada nas validações de horário de funcionamento.

---

## Fluxo recomendado para o frontend

1. Criar conta em `POST /auth/register/`.
2. Autenticar em `POST /auth/login/`.
3. Buscar o perfil em `GET /users/me/`.
4. Se `barbershop` for `null`, criar a primeira barbearia.
5. Admin cria usuários barbeiros, perfis de barbeiro e serviços.
6. Cliente lista barbeiros e serviços, cria e acompanha agendamentos.

## Atenção antes de integrar o frontend

`tipo_perfil` e `barbershop` em `PATCH`/`PUT /users/{id}/`, e a exigência de
"usuário sem tenant" em `POST /barbershops/`, são regras aplicadas no
servidor (ver as seções de Usuários e Barbearias acima) — o frontend pode
contar com o `400` do servidor como a defesa real, não precisa reforçar
nada além disso na interface.

A tela de criação de barbearia ainda deve, por UX, oferecer essa ação
apenas quando `GET /users/me/` retornar `barbershop: null` — mas isso agora
é só para não mostrar um botão que sempre falharia, não é a única defesa
contra criar uma barbearia órfã.

## Rotas ainda não implementadas

Esta versão ainda não possui cancelamento com antecedência, recuperação de
senha, dashboard ou relatórios. Não integre essas telas como se as rotas já
existissem.