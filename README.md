# Barbershop SaaS — Backend

Backend multi-tenant para um SaaS de gestão de barbearias, construído com
Django 5, Django REST Framework e autenticação via JWT.

## Stack

- Python 3.12+
- Django 5.x
- Django REST Framework
- djangorestframework-simplejwt (autenticação JWT, com blacklist no logout)
- PostgreSQL (via Docker)
- django-cors-headers (CORS para o frontend React)
- django-filter (filtros na API)

## Estrutura dos apps

| App | Responsabilidade |
|---|---|
| `config` | Código compartilhado: permissões, mixin de multi-tenant, paginação |
| `accounts` | Usuário customizado (`admin` / `barbeiro` / `cliente`) e autenticação |
| `barbershops` | Barbearia (o tenant) e barbeiros |
| `services` | Serviços oferecidos por cada barbearia |
| `appointments` | Agendamentos |

## Arquitetura multi-tenant

Cada barbearia é um tenant isolado dentro do mesmo banco de dados
(estratégia *shared database, shared schema*). O isolamento é feito por
convenção de código, em três camadas:

1. Todo usuário (`accounts.User`) tem um campo `barbershop`.
2. Todo modelo "de negócio" (`Barber`, `Service`, `Appointment`) também
   tem um campo `barbershop` direto, evitando joins desnecessários para
   filtrar.
3. O mixin `config.mixins.TenantScopedQuerysetMixin`, usado pelos ViewSets,
   filtra automaticamente o queryset pela barbearia do usuário autenticado
   (`request.user.barbershop_id`) e preenche esse campo ao criar registros
   — o cliente da API nunca informa `barbershop` manualmente.

Isso foi validado na prática (não só na teoria): rodei requisições HTTP
reais simulando dois tenants diferentes e confirmei que um usuário de uma
barbearia não enxerga dados da outra.

> **Importante:** esse isolamento é aplicado na camada de aplicação, não
> no banco (não há Row Level Security do Postgres, por exemplo). Para a
> maioria dos SaaS nesse estágio é suficiente, mas vale ter em mente ao
> evoluir o projeto.

## Decisões e suposições assumidas

Como o pedido original não detalhava tudo, assumi os seguintes padrões
(fáceis de trocar depois):

- `LANGUAGE_CODE = 'pt-br'` e `TIME_ZONE = 'America/Sao_Paulo'`, dado o
  contexto (barbearia, comentários em português).
- Autenticação por **e-mail**, não por username (removi o campo
  `username` padrão do Django).
- `on_delete=models.CASCADE` em praticamente todas as FKs, pela
  simplicidade nesta fase inicial — revisite isso (ex.: `PROTECT` ou
  soft-delete) quando as regras de negócio de exclusão ficarem claras.
- Paginação padrão de 20 itens por página em toda a API.

## Como rodar o projeto

### 1. Pré-requisitos

- Python 3.12+
- Docker e Docker Compose

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# a SECRET_KEY de exemplo já funciona em dev; troque para produção
```

### 3. Subir o PostgreSQL

```bash
docker-compose up -d
```

### 4. Criar o ambiente virtual e instalar as dependências

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Rodar as migrações

```bash
python manage.py migrate
```

(As migrations iniciais já estão neste repositório — inclusive a divisão
entre `accounts` e `barbershops` que o próprio Django gera automaticamente
por causa da referência circular entre `User.barbershop` e
`Barber.user`.)

### 6. Criar um superusuário (admin da plataforma)

```bash
python manage.py createsuperuser
```

### 7. Rodar o servidor de desenvolvimento

```bash
python manage.py runserver
```

API em `http://localhost:8000/api/v1/`, admin em `http://localhost:8000/admin/`.

## Principais endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/auth/login/` | Login (retorna `access` e `refresh`) |
| POST | `/api/v1/auth/refresh/` | Renova o token de acesso |
| POST | `/api/v1/auth/logout/` | Invalida o refresh token (blacklist) |
| GET | `/api/v1/users/me/` | Dados do usuário autenticado |
| GET/POST | `/api/v1/users/` | Usuários (listar é restrito a admin) |
| GET/POST | `/api/v1/barbershops/` | Barbearias |
| GET/POST | `/api/v1/barbers/` | Barbeiros |
| GET/POST | `/api/v1/services/` | Serviços |
| GET/POST | `/api/v1/appointments/` | Agendamentos |

Todas as rotas (exceto login/refresh) exigem o header
`Authorization: Bearer <access_token>`.

## O que NÃO está incluso (próximos passos sugeridos)

- Testes automatizados (pytest-django) — a estrutura foi validada
  manualmente durante o desenvolvimento, mas ainda não há uma suite.
- Regra de conflito de horário (impedir dois agendamentos sobrepostos
  para o mesmo barbeiro).
- Documentação interativa da API (drf-spectacular / Swagger).
- Notificações de confirmação de agendamento (e-mail/SMS).
- Dockerizar a própria aplicação Django (o `docker-compose.yml` atual
  sobe só o PostgreSQL, conforme pedido).
