# BarberPro — Frontend

Frontend React para a API Django de barbearia BarberPro. O projeto usa TypeScript, Vite, React Router, Axios, Context API, CSS Modules, React Hook Form e Zod.

## Pré-requisitos

- Node.js 20 ou superior
- Backend Django em execução em `http://127.0.0.1:8000`

## Instalação e execução

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

O Vite sobe em `http://localhost:5173`, porta já liberada pela configuração CORS padrão do backend. Para criar uma versão de produção:

```bash
npm run build
npm run preview
```

Verificação de código:

```bash
npm run lint
```

## Variáveis de ambiente

| Variável | Exemplo | Descrição |
| --- | --- | --- |
| `VITE_API_URL` | `http://127.0.0.1:8000/api/v1` | URL base da API, sem barra no final. |

Se o frontend usar outra origem, inclua essa origem em `CORS_ALLOWED_ORIGINS` no `.env` do Django.

## Fluxos incluídos

- Login, registro, logout e proteção de rotas por perfil.
- Renovação automática do access token com refresh token; falhas `401` encerram a sessão e levam o usuário ao login.
- Cliente: catálogo de serviços, equipe, busca de slots reais, criação e cancelamento de agendamentos.
- Barbeiro: agenda do dia e atualização de status.
- Administrador: cadastro, edição e exclusão de serviços e perfis de barbeiro; visualização de todos os agendamentos.
- Tela de onboarding: uma conta sem barbearia pode criar a primeira barbearia e torna-se administradora, conforme a regra do backend.

## Observação sobre o cadastro público

`POST /auth/register/` do backend sempre cria um usuário `cliente` **sem** barbearia. Por isso, depois de entrar, essa conta é direcionada para o onboarding para criar sua própria barbearia. Para usar a aplicação como cliente de uma barbearia já existente, o administrador precisa criar a conta pelo fluxo de usuários do backend e vinculá-la ao tenant; essa regra é do servidor e o frontend a respeita.

## Principais rotas da interface

| Perfil | Rotas |
| --- | --- |
| Cliente | `/services`, `/barbers`, `/appointments/new`, `/appointments` |
| Barbeiro | `/barber/agenda` |
| Admin | `/admin/services`, `/admin/barbers`, `/admin/appointments` |

As chamadas foram implementadas contra as rotas reais do ZIP: `/auth/*`, `/users/me/`, `/services/`, `/barbers/`, `/appointments/` e `/appointments/available-slots/`.