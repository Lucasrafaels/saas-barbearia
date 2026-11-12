# Evidências da auditoria técnica — BarberPro (11/11/2026)

Material de apoio ao relatório [`docs/AUDITORIA_BARBERPRO.md`](../../AUDITORIA_BARBERPRO.md).

## Origem dos dados

- Capturas de tela e sondagens foram feitas contra uma **cópia isolada da API** (Django com banco SQLite descartável, fora do repositório) e o frontend em modo de desenvolvimento.
- Todos os nomes, e-mails, telefones e valores exibidos são **fictícios**, criados apenas para teste.
- O único arquivo com dados do Postgres real é `integridade-banco-real.txt`, que contém **apenas contagens**, obtidas em modo somente leitura.
- Nenhum arquivo contém senha, token ou valor de chave secreta.
- Capturas que exibiam e-mails (telas Clientes e Minha conta) ou um estado visual já corrigido foram deixadas de fora.

## Arquivos de texto

| Arquivo | Conteúdo |
|---|---|
| `sondagem-permissoes-e-regras.txt` | 42 verificações de isolamento, perfis e regras de negócio (27 OK, 15 falhas) |
| `sondagem-sessao-e-administracao.txt` | Ciclo de sessão JWT/cookie e autodesativação do admin |
| `sondagem-agenda.txt` | Horários oferecidos no domingo e passo entre horários |
| `forja-de-token-jwt.txt` | Impacto real da chave secreta curta: forja de JWT com e sem acesso aos hashes de senha |
| `consultas-sql-por-endpoint.txt` | Consultas SQL por endpoint (ausência de N+1) e páginas percorridas pelo frontend |
| `verificacoes-backend-e-build.txt` | Testes, migrações, `check --deploy`, build/lint/tipos do frontend, repositório |
| `integridade-banco-real.txt` | Contagens de integridade no Postgres real (somente leitura) |
| `fluxos-de-interface.txt` | Fluxos executados no navegador por perfil, teclado e queda da API |

## Capturas de tela

| Arquivo | O que mostra |
|---|---|
| `01-painel-admin-desktop.png` | Painel do admin com indicadores de 30 dias, quadro do dia, faturamento diário, próximos atendimentos e rankings |
| `02-quadro-do-dia.png` | Detalhe do quadro do dia: colunas por barbeiro, blocos por duração real, status com forma e texto |
| `03-agendamentos-admin.png` | Lista de agendamentos agrupada por dia com filtros e ações de status válidas |
| `04-dialogo-cancelamento.png` | Confirmação antes de cancelar; contador "a confirmar" no topo |
| `05-validacao-formulario-servico.png` | Mensagens de validação no cadastro de serviço |
| `06-agenda-barbeiro.png` | Agenda do barbeiro com intervalos livres e ações |
| `07-agendamento-horarios.png` | Escolha de data e horário com horários reais da API agrupados por período |
| `08-api-fora-do-ar.png` | Estado "Sem conexão com o servidor" com a sessão preservada |
| `09-menu-celular.png` | Menu lateral no celular (390 px) |
| `10-servicos-celular.png` | Tabela de serviços convertida em cartões no celular. Capturada antes da correção do ícone da marca no topo; o restante da tela corresponde ao estado atual |
