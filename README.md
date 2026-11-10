# BarberPro — Backend

Backend multi-tenant para o SaaS BarberPro de gestão de barbearias, construído com
Django 5, Django REST Framework e autenticação via JWT.

## Stack

- Python 3.12 (versão oficial suportada)
- Django 5.x
- Django REST Framework
- djangorestframework-simplejwt (autenticação JWT, com blacklist no logout)
- PostgreSQL (via Docker)
- django-cors-headers (CORS para o frontend React)
- django-filter (filtros na API)

## Estrutura dos apps

| App | Responsabilidade |
|---|---|
| `config` | Código compartilhado: permissões, mixin de multi-tenant, paginação, settings |
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
> maioria dos SaaS nesse estágio é suficiente, mas se precisar de
> isolamento mais forte, pode-se considerar o RLS do Postgres no futuro.

## Como executar (Backend)

1. Clone o repositório
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o ambiente: `source venv/bin/activate` (no Windows: `venv\Scripts\activate`)
4. Instale as dependências: `pip install -r requirements.txt`
5. Configure as variáveis de ambiente (copie `.env.example` para `.env` e ajuste)
6. Execute as migrações: `python manage.py migrate`
7. Crie um superusuario: `python manage.py createsuperuser`
8. Execute o servidor: `python manage.py runserver`

A API estará disponível em `http://localhost:8000/api/v1/`

## Como executar (Frontend)

O frontend React/Vite está em `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

O servidor de desenvolvimento roda em `http://localhost:5173` (proxy configurado para `http://localhost:8000`).

## Testes

### SQLite (em memória, rápido)

```bash
python manage.py test --settings=config.test_settings
```

- Usa banco SQLite em memória (`:memory:`)
- Não suporta `select_for_update()` — 4 testes de concorrência são ignorados
- Execução rápida (~3s)

### PostgreSQL (Docker, completo)

```bash
python manage.py test --settings=config.test_postgres_settings
```

- Usa PostgreSQL 16 via Docker (porta 5433)
- Suporta `select_for_update()` — todos os testes de concorrência rodam
- Execução completa (~9s)

> **Diferença:** `config.test_settings` usa SQLite `:memory:` (sem locking de linha). `config.test_postgres_settings` usa PostgreSQL real, permitindo validar isolamento multi-tenant e concorrência com `select_for_update()`. O comando `python manage.py test` sem `--settings` usa o `config.settings` padrão (PostgreSQL) e falhará se o container não estiver rodando.

## Documentação

- [Arquitetura da API](docs/arquitetura/DOCUMENTACAO_API.md)
- [Auditorias e relatórios técnicos](docs/auditorias/historico/)

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.