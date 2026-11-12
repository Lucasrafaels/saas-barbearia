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

- Login, cadastro (com entrada automática e onboarding da barbearia), logout e proteção de rotas por perfil.
- Renovação automática do access token pelo cookie de refresh; recusa do servidor encerra a sessão, falha de rede não (a tela "Sem conexão" permite tentar de novo).
- Recuperação de senha em duas etapas (o e-mail traz `uid` e `token`, que podem ser digitados ou vir na URL).
- **Cliente:** início com o próximo horário e os contatos da barbearia; tabela de serviços e preços; equipe; agendamento guiado com horários reais (`available-slots`), reagendamento e cancelamento com confirmação.
- **Barbeiro:** agenda por dia com intervalos livres, visão "a confirmar" e ações de status.
- **Administrador:** painel com quadro do dia por barbeiro, indicadores de 30 dias e gráficos calculados a partir dos agendamentos reais (preço histórico); agendamentos com busca e filtros na URL; CRUD de serviços, barbeiros e clientes com desativação/reativação; dados e horário da barbearia.
- **Todos:** Minha conta (dados pessoais e troca de senha).

## Observação sobre o cadastro público

`POST /auth/register/` do backend sempre cria um usuário `cliente` **sem** barbearia. Por isso, depois de entrar, essa conta é direcionada para o onboarding para criar sua própria barbearia. Para usar a aplicação como cliente de uma barbearia já existente, o administrador cria a conta na tela **Clientes** (`POST /users/`), já vinculada ao tenant; essa regra é do servidor e o frontend a respeita.

## Principais rotas da interface

| Perfil | Rotas |
| --- | --- |
| Cliente | `/`, `/services`, `/barbers`, `/appointments/new`, `/appointments` |
| Barbeiro | `/barber/agenda` |
| Admin | `/admin`, `/admin/appointments`, `/admin/services`, `/admin/barbers`, `/admin/clients`, `/admin/barbershop` |
| Todos | `/account` (a rota antiga `/password/change` redireciona para cá) |

## Interface

- Identidade e tokens em `src/styles/design-tokens.css`; componentes reutilizáveis em `src/components` (modal acessível, diálogo de confirmação, toasts, estados vazio/erro/carregamento, busca, filtros segmentados, ações de status).
- Fonte Archivo (Google Fonts) carregada no `index.html`.
- As telas são carregadas sob demanda (`React.lazy`) e respeitam `prefers-reduced-motion`.

As chamadas foram implementadas contra as rotas reais do ZIP: `/auth/*`, `/users/me/`, `/services/`, `/barbers/`, `/appointments/` e `/appointments/available-slots/`.