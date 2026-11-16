# Auditoria técnica e funcional — BarberPro

| | |
|---|---|
| **Data** | 13/11/2026 |
| **Branch auditada** | `desenvolvimento`, commit `3e0949e` + 43 arquivos modificados e 16 entradas não versionadas (backend do dono e redesign "Esmalte & Navalha") |
| **Escopo** | Backend Django/DRF, frontend React/TypeScript/Vite, banco de dados, segurança, regras de negócio, integração ponta a ponta, três perfis, responsividade, acessibilidade, testes, dependências, documentação e repositório |
| **Natureza** | Somente diagnóstico. Nenhum código, configuração, dependência, migração ou dado real foi alterado |
| **Evidências** | [`docs/auditoria/evidencias-2026-11-13/`](auditoria/evidencias-2026-11-13/README.md) |
| **Correções** | Rodada 1 em 13/11/2026: BUS-15, BUS-03, BUS-05, BUS-04 e FE-13 resolvidos e verificados; BUS-06 parcialmente resolvido. Acompanhamento na [seção 18](#18-acompanhamento-das-correções). Rodada 2 em 13/11/2026 (somente frontend): FE-14, FE-21 e FE-22 resolvidos e verificados, na [seção 19](#19-rodada-2--13112026-fe-14-fe-21-e-fe-22-somente-frontend). As seções 1 a 17 descrevem o estado no momento da auditoria e foram preservadas |
| **Isolamento multi-tenant** | Auditoria de 13/11/2026, somente diagnóstico, na [seção 20](#20-auditoria-de-isolamento-multi-tenant--13112026). **Achou 1 P0 novo (TEN-01): a API navegável do DRF expõe dados de todas as barbearias.** Com isso, a afirmação "nenhum P0 aberto" do resumo executivo deixou de valer. Também achou TEN-02 (P2), TEN-03 e TEN-04 (P3) e ampliou o SEC-10 |
| **Contenção do TEN-01** | 14/11/2026, na [seção 21](#21-contenção-do-ten-01--14112026). A API passou a responder só em JSON (`DEFAULT_RENDERER_CLASSES`). **A exposição deixou de ser reproduzível** nas 21 rotas da API, com 9 papéis, todas as formas de pedir HTML e `DEBUG` True ou False. **TEN-01 está contido, não resolvido:** a correção estrutural (querysets limitados ao tenant) continua pendente. Registrados também API-03 e AUTH-03 (P3), que já existiam |
| **Correção estrutural do TEN-01** | 14/11/2026, na [seção 22](#22-correção-estrutural-do-ten-01--14112026). Os campos relacionais (`cliente`, `barbeiro`, `servico` e `user`) e os filtros de agendamentos passaram a aceitar e listar só registros da barbearia do usuário. **TEN-01 resolvido e verificado** no ambiente de testes; a contenção continua ativa. SEC-10 parcialmente resolvido (filtros e corpo das requisições; falta o `exclude_appointment_id`). O sintoma do TEN-02 deixou de se reproduzir, mas o item segue aberto. Registrada a observação BUS-20 (P3) |
| **Correção do TEN-02** | 14/11/2026, na [seção 23](#23-correção-do-ten-02--14112026). A conta sem barbearia passou a ser recusada antes de qualquer validação, com uma resposta única (403 "Usuário sem barbearia vinculada."), e o `validate()` deixou de pular as checagens de barbearia. A proteção não depende mais do escopo dos campos do TEN-01. **TEN-02 resolvido e verificado** no ambiente de testes |
| **Correção do SEC-10 (`exclude_appointment_id`)** | 14/11/2026, na [seção 24](#24-correção-do-sec-10-exclude_appointment_id--14112026). O agendamento a excluir passou a ser buscado com a barbearia do usuário na própria consulta: o de outra barbearia responde exatamente como um ID inexistente e nunca é lido. **Os caminhos do SEC-10 entre barbearias estão fechados.** O SEC-10 continua parcial por um ponto dentro da própria barbearia, que já constava da definição original (PER-13: 403 em vez de 404 ao consultar outro usuário pelo ID), não autorizado nesta etapa |
| **Correção do PER-13 e conclusão do SEC-10** | 14/11/2026, na [seção 25](#25-correção-do-per-13-e-conclusão-do-sec-10--14112026). Na leitura de detalhe de `/users/{id}/` (GET e HEAD), cliente e barbeiro só enxergam o próprio cadastro, já na consulta: outro usuário da mesma barbearia recebe o mesmo 404 de um ID inexistente. **SEC-10 resolvido e verificado** no ambiente de testes, com os três pontos da definição original cobertos por evidências. A mesma diferença 403 × 404 nas escritas (PATCH e PUT de `/users/{{id}}/`) e no `exclude_appointment_id`, dentro da própria barbearia, foi registrada à parte como **SEC-12 (P3)**, sem correção |
| **Investigação do TEN-03** | 15/11/2026, somente investigação, na [seção 26](#26-investigação-do-ten-03--15112026). **Causa confirmada:** o e-mail é único em toda a plataforma (model e banco) e é o login, e o `UniqueValidator` do DRF consulta todas as barbearias. O alcance é maior que o registrado em 13/11: além do admin e do cadastro público, também qualquer cliente que troca o próprio e-mail, com variantes sem efeito colateral e um caminho por erro 500. Uma simulação mostrou que trocar a mensagem, ou padronizar status e corpo, não fecha o oráculo. Registrados AUTH-04 (P2) e AUTH-05 (P3). **TEN-03 continua aberto; a regra de unicidade aguarda a decisão do dono** |
| **Mitigação D do TEN-03** | 15/11/2026, na [seção 27](#27-mitigação-d-do-ten-03-limite-de-tentativas--15112026). O dono decidiu: e-mail único em toda a plataforma (A), limite de tentativas como mitigação temporária (D), confirmação por e-mail e convites (C3) depois da apresentação, e AUTH-04 e AUTH-05 numa etapa prioritária separada. Implementados limites próprios, por conta ou por origem e nunca pelo e-mail-alvo, no cadastro público (+20/dia), na criação de usuários (30/hora e 100/dia) e na troca de e-mail (10/hora e 30/dia, só quando o e-mail muda). Esgotado o limite, a resposta é 429 antes da validação. Login e recuperação não mudaram. **TEN-03 continua aberto, com mitigação parcial.** Registrado o SEC-13 (P2): os limites por origem aceitam `X-Forwarded-For` forjado sem `NUM_PROXIES` |
| **Investigação do AUTH-04 e do AUTH-05** | 15/11/2026, somente diagnóstico e plano, na [seção 28](#28-investigação-e-plano-do-auth-04-e-do-auth-05--15112026). **Causas confirmadas.** A recuperação procura sem diferenciar caixa e escolhe uma conta pelo nome; o token vai sempre para o e-mail da própria conta, mas a recuperação é desviada para a conta do terceiro. A validação, o manager, a edição, o login e a recuperação tratam a caixa de quatro jeitos diferentes. Medidos: duplicatas, 500 com o domínio em maiúsculas, o login após o cadastro falhando, e 500 em 15 de 15 pedidos simultâneos. Plano: normalização única para minúsculas e `UNIQUE (LOWER(email))`. **Exige migração (não criada).** A consulta de colisões no banco real está pronta e **não foi executada**. AUTH-04 e AUTH-05 continuam abertos |
| **Verificação de colisões no banco real** | 15/11/2026, somente leitura, na [seção 29](#29-verificação-de-colisões-no-banco-real-somente-leitura--15112026). Banco `barbershop_db` (PostgreSQL 18.3, porta 5432), transação `READ ONLY` terminada em `ROLLBACK`, sem a consulta que mostra nomes e e-mails. **8 contas, 0 a normalizar, 0 fora do ASCII, 0 grupos de colisão.** A migração planejada não exige decisões por grupo. Isso não autoriza a migração nem a implementação |
| **AUTH-04 e AUTH-05: equivalência e parada** | 15/11/2026, na [seção 30](#30-auth-04-e-auth-05-equivalência-python--postgresql-e-parada-antes-da-implementação--15112026). Antes de implementar, a equivalência entre a normalização em Python e as funções do PostgreSQL foi medida em `pt_BR.UTF-8`, nos 1.112.063 pontos de código. **Ela não se sustenta** para o que o backend aceita hoje: 56 caracteres têm `lower()` divergente, 55 entradas aceitas violariam o `CHECK`, e invisíveis aceitos não são normalizados. **A implementação parou antes de alterar qualquer código**, como o escopo exigia. Alternativa proposta: e-mail normalizado só em ASCII imprimível (o frontend já só aceita ASCII), com equivalência medida e garantida. Aguarda autorização |
| **Correção do AUTH-04 e do AUTH-05** | 15/11/2026, na [seção 31](#31-correção-do-auth-04-e-do-auth-05-com-e-mail-normalizado-em-ascii--15112026). Uma regra única de e-mail (`accounts/emails.py`) foi aplicada a cadastro, criação, edição, Django Admin, login e recuperação: espaços externos removidos, só ASCII imprimível, minúsculas. A recuperação busca o e-mail normalizado com igualdade exata, e a migração `accounts.0006` cria o `CHECK` e o `UNIQUE (LOWER(email))`. Validado em PostgreSQL 18.3 `pt_BR.UTF-8` descartável: 521 testes OK; antes × depois, 7 → 0 duplicatas, 500 → 400 em 15 de 15 pedidos simultâneos, login com outra caixa 401 → 200. **AUTH-04 e AUTH-05 resolvidos e verificados no ambiente de testes. A migração não foi aplicada no banco real** |
| **Revisão final e plano de implantação** | 15/11/2026, só leitura e planejamento, na [seção 32](#32-revisão-final-do-auth-04-e-do-auth-05-e-plano-de-implantação-da-accounts0006--15112026). A revisão independente confirmou a implementação e a migração, sem nenhum critério de parada. Há oito observações não bloqueantes, incorporadas ao plano; a principal é que a verificação da seção 29 não cobriu espaço interno, controles ASCII nem e-mail vazio (a migração se interromperia sem alterar nada). Plano P0 a P12: backup novo, ensaio numa cópia restaurada em PG 18.3 pt_BR, aplicação com `lock_timeout`, pós-verificação, fumaça, critérios de interrupção e recuperação. **Nada foi executado no banco real.** PROD-01 continua aberto |
| **Execução de P0 a P7** | 15/11/2026, na [seção 33](#33-execução-de-p0-a-p7-do-plano-da-accounts0006--15112026). Identidade do banco real confirmada (`barbershop_db`, 18.3, `::1:5432`, pt_BR, libc). Leitura: 8 contas, todas já canônicas, 0 fora da regra, 0 colisões, restrição `accounts_user_email_key`, e o `migrate --plan` só com a `accounts.0006`. Backup novo de 63.004 bytes (SHA-256 `5eb831d6…21af95`), validado. A cópia restaurada em PG 18.3 pt_BR descartável é idêntica ao banco real. A `accounts.0006` foi aplicada, revertida e reaplicada **só na cópia**, e os 40 testes de fumaça passaram, sem 500. **Banco real sem nenhuma escrita; P8 não executada** |
| **Aplicação no banco real (P8 a P12)** | 15/11/2026, na [seção 34](#34-aplicação-da-accounts0006-no-banco-real-p8-e-etapas-p9-a-p12--15112026). **P8:** pré-verificações idênticas ao ensaio; backup imediato de 63.004 bytes (SHA-256 `5a4c028b…513279`), validado; **`accounts.0006` aplicada às 22:56:22**, com `lock_timeout=5s` e nada além dela. **P9:** `CHECK` validado, índice único em `lower(email)` válido, `accounts_user_email_key` preservada e 8 contas canônicas. **P10:** backend e frontend no ar com o código conferido, sem escrita na inicialização. **P11:** 26 testes só de leitura OK, 0 respostas 500 e contadores de escrita inalterados. Testes com escrita ficam pendentes de autorização. **AUTH-04/05 resolvidos também no banco real** |
| **Auditoria anterior** | Cópia integral em [`docs/auditorias/historico/AUDITORIA_BARBERPRO_2026-11-11.md`](auditorias/historico/AUDITORIA_BARBERPRO_2026-11-11.md); evidências antigas preservadas em [`docs/auditoria/evidencias/`](auditoria/evidencias/README.md) |

> **Confidencialidade.** Este relatório não contém a `SECRET_KEY`, senhas, tokens nem a string de conexão do banco: só comprimentos, contagens, códigos HTTP e nomes de campos. Todos os dados de teste citados são fictícios.

---

## Sumário

1. [Resumo executivo](#1-resumo-executivo)
2. [Estado geral do projeto](#2-estado-geral-do-projeto)
3. [Escopo e metodologia](#3-escopo-e-metodologia)
4. [Ambiente e ferramentas](#4-ambiente-e-ferramentas)
5. [Auditoria de segurança](#5-auditoria-de-segurança)
6. [Auditoria do backend](#6-auditoria-do-backend)
7. [Auditoria do frontend](#7-auditoria-do-frontend)
8. [Auditoria do banco de dados](#8-auditoria-do-banco-de-dados)
9. [Integração ponta a ponta](#9-integração-ponta-a-ponta)
10. [Testes dos três perfis](#10-testes-dos-três-perfis)
11. [Responsividade e acessibilidade](#11-responsividade-e-acessibilidade)
12. [Comparação com a auditoria anterior](#12-comparação-com-a-auditoria-anterior)
13. [Lista completa de problemas](#13-lista-completa-de-problemas)
14. [Problemas não verificáveis e limitações](#14-problemas-não-verificáveis-e-limitações)
15. [Matriz de prioridades](#15-matriz-de-prioridades)
16. [Plano recomendado de correção](#16-plano-recomendado-de-correção)
17. [Prontidão para a demonstração](#17-prontidão-para-a-demonstração)
18. [Acompanhamento das correções](#18-acompanhamento-das-correções)
19. [Rodada 2: FE-14, FE-21 e FE-22](#19-rodada-2--13112026-fe-14-fe-21-e-fe-22-somente-frontend)
20. [Auditoria de isolamento multi-tenant](#20-auditoria-de-isolamento-multi-tenant--13112026)
21. [Contenção do TEN-01](#21-contenção-do-ten-01--14112026)
22. [Correção estrutural do TEN-01](#22-correção-estrutural-do-ten-01--14112026)
23. [Correção do TEN-02](#23-correção-do-ten-02--14112026)
24. [Correção do SEC-10: `exclude_appointment_id`](#24-correção-do-sec-10-exclude_appointment_id--14112026)
25. [Correção do PER-13 e conclusão do SEC-10](#25-correção-do-per-13-e-conclusão-do-sec-10--14112026)
26. [Investigação do TEN-03](#26-investigação-do-ten-03--15112026)
27. [Mitigação D do TEN-03: limite de tentativas](#27-mitigação-d-do-ten-03-limite-de-tentativas--15112026)
28. [Investigação e plano do AUTH-04 e do AUTH-05](#28-investigação-e-plano-do-auth-04-e-do-auth-05--15112026)
29. [Verificação de colisões no banco real](#29-verificação-de-colisões-no-banco-real-somente-leitura--15112026)
30. [AUTH-04 e AUTH-05: equivalência Python × PostgreSQL e parada](#30-auth-04-e-auth-05-equivalência-python--postgresql-e-parada-antes-da-implementação--15112026)
31. [Correção do AUTH-04 e do AUTH-05](#31-correção-do-auth-04-e-do-auth-05-com-e-mail-normalizado-em-ascii--15112026)
32. [Revisão final do AUTH-04 e do AUTH-05 e plano de implantação](#32-revisão-final-do-auth-04-e-do-auth-05-e-plano-de-implantação-da-accounts0006--15112026)
33. [Execução de P0 a P7 do plano da `accounts.0006`](#33-execução-de-p0-a-p7-do-plano-da-accounts0006--15112026)
34. [Aplicação da `accounts.0006` no banco real (P8) e etapas P9 a P12](#34-aplicação-da-accounts0006-no-banco-real-p8-e-etapas-p9-a-p12--15112026)

---

## 1. Resumo executivo

O BarberPro melhorou desde 11/11. **Os dois problemas críticos da auditoria anterior foram corrigidos e comprovados**:

- a `SECRET_KEY` efetiva agora tem 86 caracteres, e o `settings.py` recusa chaves curtas (SEC-01);
- o faturamento deixou de vazar para clientes e barbeiros (SEC-02).

Também foram corrigidos e verificados:

- o admin que se rebaixava ou se desativava (BUS-01), inclusive sob concorrência;
- o "realizado" em horário futuro (BUS-07);
- a fonte vinda do Google Fonts (FE-08).

A base continua sólida:

- **isolamento entre barbearias:** 21 de 21 tentativas de acesso cruzado foram bloqueadas;
- **concorrência:** 20 pedidos simultâneos para o mesmo horário geraram exatamente 1 agendamento (PostgreSQL 16);
- **testes:** 327 testes passam em SQLite e em PostgreSQL, com 91% de cobertura de linhas e ramificações;
- **frontend:** sem erros de tipo, lint ou build;
- **navegador:** nenhuma das 105 combinações de tela × tamanho tem erro de console ou rolagem horizontal;
- **acessibilidade:** nenhuma violação automática (axe-core) em 36 páginas.

**Não há nenhum problema P0 aberto.** O sistema, porém, **não está pronto para produção** e tem pontos que podem aparecer numa demonstração:

- **O fluxo de confirmação da barbearia pode ser contornado pelo cliente.**
  - O cliente cria o agendamento já como "confirmado" (BUS-15, novo).
  - Ao reagendar um horário confirmado, ele continua "confirmado" (BUS-03).
- **O horário de funcionamento não é garantido pela API.**
  - A troca de serviço ultrapassa o fechamento (BUS-04).
  - A API aceita fechamento antes da abertura (BUS-05).
  - Domingos e dias fechados recebem horários. A interface reservou um domingo durante esta auditoria (BUS-06).
- **Lacunas de produto continuam:**
  - o cliente não se cadastra numa barbearia (PROD-01);
  - a recuperação de senha não envia e-mail (AUTH-01).
- **Suspensão de barbearia só parcial.** A agenda congela, mas o próprio admin reativa a barbearia que a plataforma desativou, e a interface não avisa nada (BUS-02, FE-14).
- **Dependências do backend com 91 vulnerabilidades conhecidas.** O Django 5.0 está fora de suporte (DEP-01).
- **Dois bancos de desenvolvimento diferentes.** O app usa o PostgreSQL 18 do host. O banco do `docker-compose` indicado no README está com duas migrações pendentes e falharia nos agendamentos (DB-01).
- **Uma regressão do redesign.** Depois de reservar, o botão "Agendar" continua mostrando "Horário reservado" (FE-13).

### Números

| Prioridade | Quantidade |
|---|---|
| P0 — Crítico | **0** |
| P1 — Alto | **7** |
| P2 — Médio | **28** |
| P3 — Baixo | **35** |
| **Total de problemas abertos** | **70** |

| Situação dos 53 problemas da auditoria anterior | Quantidade | IDs |
|---|---|---|
| Resolvido e verificado | 5 | SEC-01, SEC-02, BUS-01, BUS-07, FE-08 |
| Parcialmente resolvido | 3 | BUS-02, TEST-01, FE-04 |
| Continua presente | 45 | ver seção 12 |
| Regressão (voltou a ocorrer) | 0 | — |
| Não reproduzido / obsoleto / não verificável | 0 | — |

| Problemas novos | Quantidade |
|---|---|
| Encontrados nesta auditoria | 22 (1 P1, 5 P2, 16 P3) |
| Dos quais regressão introduzida pelo redesign | 1 (FE-13) |

### Os cinco problemas mais importantes

| # | ID | Prioridade | Por que |
|---|---|---|---|
| 1 | BUS-15 | P1 | O cliente se autoconfirma ao criar o horário: a confirmação da barbearia perde o sentido. Correção de poucas linhas |
| 2 | BUS-03 | P1 | Reagendar mantém "confirmado": a barbearia passa a ter um horário confirmado que nunca aprovou |
| 3 | BUS-06 | P1 | Domingos e dias fechados recebem agendamentos, inclusive pela interface. É o mais visível numa demonstração |
| 4 | BUS-05 | P1 | A API aceita fechamento antes da abertura, e a barbearia "desaparece" da agenda |
| 5 | BUS-04 | P1 | A troca de serviço gera atendimento depois do fechamento |

Para a operação real também pesam PROD-01, AUTH-01, DEP-01 e DB-01.

**Veredito.** O BarberPro **pode ser apresentado** como protótipo acadêmico. Os fluxos dos três perfis funcionam de ponta a ponta, sem erros na interface, em todos os tamanhos de tela testados. É preciso garantir o banco usado e os dados de demonstração e evitar os fluxos listados na seção 17. **Não está pronto para uso real nem para produção.**

---

## 2. Estado geral do projeto

| Área | Situação | Resumo |
|---|---|---|
| Autenticação e sessão | ✅ Funciona | Login, refresh por cookie HttpOnly com rotação e blacklist, logout, troca de senha, bloqueio imediato de conta desativada. Pendentes: SEC-04, SEC-05, AUTH-01 e AUTH-02 |
| Isolamento multi-tenant | ✅ Funciona | 21/21 tentativas de acesso cruzado bloqueadas; há só um oráculo de existência de IDs (SEC-10) |
| Permissões por perfil | ⚠️ Quase | Faturamento protegido (SEC-02 resolvido). O cliente cria horário já confirmado (BUS-15) e o barbeiro troca o cliente de um horário (BUS-12) |
| Regras de agenda | ❌ Incompletas | Conflito por barbeiro garantido, inclusive sob concorrência. Abertos: horário de funcionamento (BUS-04, BUS-05), dias fechados (BUS-06), confirmação (BUS-03, BUS-15), vencidos (BUS-08), duração histórica (BUS-09) e sobreposição do próprio cliente (BUS-17) |
| Barbearia desativada | ⚠️ Parcial | A agenda congela, mas o admin reativa a barbearia por conta própria e a interface não sinaliza (BUS-02, FE-14) |
| Financeiro | ⚠️ Quase | Usa o preço histórico. O dia é agrupado em UTC (API-02), o painel e a API usam janelas diferentes (FE-11), e o reverso de uma migração apaga preços (DATA-01) |
| Banco de dados | ⚠️ | Migrações coerentes no banco que o app usa; sem constraints de negócio (DB-02); dois bancos de desenvolvimento divergentes (DB-01) |
| Frontend (funcionamento) | ✅ Funciona | `tsc`, ESLint e build sem erros; 0 erros de console em 105 cargas; fluxos concluídos nos três perfis. Pendentes: FE-03, FE-13, FE-15 e a carga integral de listas (API-01) |
| Redesign e identidade | ✅ Consistente | Paleta, League Gothic e Public Sans locais, logo e componentes coerentes entre as telas. Pequenos desvios: 45 estilos inline e cores literais (MAINT-01) |
| Responsividade | ✅ Funciona | 0 rolagem horizontal em 5 larguras (1440, 1280, 820, 390 e 360 px) e fluxos completos no celular e no tablet. Detalhes em FE-19 e FE-20 |
| Acessibilidade | ✅ Bom | 0 violações automáticas WCAG A/AA em 36 páginas, link "Pular para o conteúdo", foco visível. Leitor de tela não testado (NV-3) |
| Testes | ⚠️ | 327 testes no backend, 91% de cobertura, mas as regras quebradas não têm teste (TEST-01). Nenhum teste de frontend (FE-02) |
| Dependências | ❌ | Backend com 91 vulnerabilidades conhecidas e Django fora de suporte (DEP-01); frontend com 14 (DEP-02) |
| Infra e operação | ❌ Ausente | Sem Dockerfile, CI, logs, monitoramento, cache compartilhado e e-mail (OPS-01, OBS-01, SEC-05, AUTH-01) |
| Documentação | ❌ Desatualizada | Documentação da API, README e índice de `docs/` divergem do comportamento (DOC-01 a DOC-04) |

### Funcionalidades e estado real

| Módulo | Funcionalidade | Estado | Evidência / problema |
|---|---|---|---|
| Autenticação | Login, renovação, logout, troca de senha | ✅ | SES-01 a SES-06 (`api/sondagem-api.json`) |
| Autenticação | Recuperação de senha | ⚠️ Incompleta | Sem envio de e-mail (AUTH-01); confirmação sem teste (TEST-01) |
| Autenticação | Cadastro público | ⚠️ Incompleto | Só serve a donos de barbearia (PROD-01); e-mail duplicado por maiúsculas (AUTH-02) |
| Usuários | Gestão pelo admin | ✅ | BUS-01 resolvido. Sem segundo admin nem transferência de titularidade (BUS-19) |
| Barbearias | Edição dos dados | ⚠️ | Fechamento antes da abertura aceito pela API (BUS-05); telefone sem validação (BUS-18) |
| Barbearias | Desativação/suspensão | ⚠️ Parcial | BUS-02, FE-14 |
| Barbearias | Logo | ❌ Só API | Sem tela (FE-09); upload sem limite (SEC-09) |
| Barbeiros | Cadastro, edição, desativação, reativação | ✅ | Fluxos no navegador; desativação não trata a agenda (BUS-13) |
| Clientes | Cadastro e gestão pelo admin | ✅ | Tela "Clientes"; lista carrega todos os agendamentos (API-01) |
| Serviços | Cadastro, preço, duração, ativo | ✅ | Validações fracas (BUS-18); "1.000" vira R$ 1,00 (FE-16) |
| Agendamentos | Criação sem conflito | ✅ | CON-01: 1 de 20 pedidos simultâneos |
| Agendamentos | Horários livres | ⚠️ | Dias fechados (BUS-06), passo (BUS-11), datas passadas (BUS-10) |
| Agendamentos | Confirmação | ❌ Contornável | BUS-15, BUS-03 |
| Agendamentos | Conclusão ("realizado") | ✅ | BUS-07 resolvido; botão "Concluir às HH:MM" desabilitado antes do término |
| Agendamentos | Cancelamento | ⚠️ | Funciona; o cliente cancela até horário já passado (BUS-16); regra do barbeiro incoerente (BUS-12) |
| Painel / Caixa | Indicadores, quadro do dia, faturamento | ✅ Dados reais | Calculados no navegador a partir de todas as páginas (API-01, FE-11) |
| Relatórios | `revenue-report` | ✅ Protegido | Só admin (SEC-02 resolvido); dia em UTC (API-02); não é usado pela interface |
| Página institucional | `/conheca` | ✅ | Nova; sem rolagem horizontal; promessas coerentes com o sistema |
| Super Admin | Painel global | ❌ Ausente | SA-01 |

---

## 3. Escopo e metodologia

### 3.1 Regras seguidas

- Trabalho na branch `desenvolvimento`. Nenhum commit, push, merge, `reset`, `checkout` ou limpeza.
- **Nenhum arquivo de código, configuração, dependência, migração ou `.env` foi alterado.** Ao final, `git diff --stat` continuava idêntico ao do início: 43 arquivos, +2065/−830. Só foram criados:
  - este relatório;
  - a cópia histórica, idêntica byte a byte ao original (mesmo SHA-256);
  - a pasta de evidências nova.
- **O banco real não sofreu nenhuma escrita.**
  - Nele rodaram só consultas numa sessão `BEGIN READ ONLY` e `showmigrations`, que apenas lê a tabela de migrações.
  - Nenhuma migração foi executada nele.
- Todos os testes com escrita usaram um **PostgreSQL 16.15 descartável**:
  - num container próprio, com dados em `tmpfs`, removido ao final;
  - populado com dados fictícios: 2 barbearias, 14 usuários, 419 agendamentos.
- A migração reversa (DATA-01) rodou numa segunda cópia descartável desse banco.
- Ferramentas auxiliares foram instaladas **fora do projeto**, no diretório temporário da sessão: `coverage`, `pip-audit`, `puppeteer-core` e `axe-core`. Nada foi instalado no `venv312` nem no `node_modules` do projeto.
- O build de produção do frontend foi gerado fora do projeto, sem sobrescrever `frontend/dist`.
- Nenhum valor de segredo foi exibido ou gravado. O teste de `SECRET_KEY` mediu só o comprimento.

### 3.2 Métodos

| Método | O que cobriu |
|---|---|
| Leitura integral de código | Todos os models, serializers, views, permissões, mixins, settings, URLs, migrações, admin e managers. No frontend: rotas, cliente HTTP, autenticação, hooks, telas e componentes alterados pelo redesign e o diff completo desde `3e0949e` |
| Suíte do backend | 327 testes em SQLite (`config.test_settings`) e em PostgreSQL 16 descartável, com medição de cobertura |
| Sondagem 1 da API isolada | 91 verificações por HTTP real: isolamento (23; 21 conforme), perfis (23; 20 conforme), regras de negócio (23; 4 conforme), barbearia desativada (6; 3 conforme), sessão e segurança HTTP (15; 13 conforme), concorrência (1; conforme). Total: 62 conforme o esperado, 29 divergentes. Duas observações de transparência: PER-23 divergiu da expectativa, mas o comportamento é adequado (recusa com 400), e não virou problema; o primeiro teste de BUS-12 ficou inválido (o agendamento de partida não foi criado) e foi refeito na sondagem 2 |
| Sondagem 2 | 13 verificações: BUS-12 refeito, BUS-09, upload de logo, validações, oráculo de tempo, contrato |
| Testes dirigidos | Laço com duração 0 (com `timeout`), consultas SQL por endpoint, rate limit real com 3 workers do gunicorn, reverso da migração 0008, painel × relatório |
| Navegador real | Firefox 160 headless via `puppeteer-core`, com um contexto isolado por perfil. Foram 105 cargas: 21 rotas em 5 larguras (1440, 1280, 820, 390 e 360 px). Também fluxos de cliente (celular), barbeiro (tablet) e admin (desktop), teclado e rota inexistente. No build de produção: requisições por tela, API derrubada, API travada e barbearia desativada |
| Acessibilidade | axe-core 4.10.3 (WCAG 2.0/2.1/2.2 A e AA) em 36 páginas, com teste de controle que confirmou a detecção de 3 violações plantadas |
| Banco real (somente leitura) | Migrações aplicadas e 26 contagens de integridade |
| Ferramentas estáticas | `tsc`, ESLint, build Vite, `makemigrations --check`, `check --deploy`, `pip-audit`, `npm audit`, `npm outdated` e `git` (arquivos versionados, branches, histórico) |

### 3.3 Classificação

- **Severidade:**
  - **P0:** comprometimento grave de segurança, perda de dados ou quebra do isolamento;
  - **P1:** autorização importante, regra de negócio crítica ou funcionalidade essencial;
  - **P2:** problema funcional relevante, integração, usabilidade que prejudica a operação, dependência vulnerável ou lacuna de infraestrutura;
  - **P3:** visual, pequena inconsistência, acessibilidade, manutenção.
- **Confiança:**
  - **Confirmado:** reproduzido dinamicamente ou inequívoco no código, com a fonte indicada no campo Evidência;
  - **Provável:** forte indício sem reprodução;
  - **Não verificado:** depende de condição que não pôde ser criada.
- **Estado em relação à auditoria anterior:** Novo, Continua presente, Parcialmente resolvido, Reclassificado.

---

## 4. Ambiente e ferramentas

| Item | Versão / detalhe |
|---|---|
| Sistema | Fedora Linux 45, kernel 7.3.3 |
| Python / Django / DRF | 3.12.16 / 5.0.14 / 3.15.2 (djangorestframework-simplejwt 5.3.1, Pillow 10.4.0) |
| Node / npm | 26.13.0 / 11.20.0 |
| Frontend | React 19.2.8, React Router 7.18.2, Vite 6.4.3, TypeScript 5.8.3, axios 1.19.0, zod 3.25.76 |
| Banco que o app usa (`.env`) | PostgreSQL **18.3** no host, porta 5432 (somente leitura nesta auditoria) |
| Banco do `docker-compose.yml` | PostgreSQL 16.15, container `barbershop_db`, porta 5433: **não é o banco que o app usa** (DB-01) |
| Banco descartável da auditoria | PostgreSQL 16.15 (`postgres:16-alpine`), container próprio em `tmpfs` |
| Navegador | Firefox 160.0 headless + puppeteer-core 24.10.0 |
| Acessibilidade | axe-core 4.10.3 |
| Cobertura / dependências | coverage 7.17.3, pip-audit 2.10.1, `npm audit` |
| Servidores de teste | `runserver` (sondagens) e gunicorn com 3 workers (rate limit) |

---

## 5. Auditoria de segurança

### 5.1 Verificações e resultados

| Tema | Resultado | Evidência |
|---|---|---|
| `SECRET_KEY` | ✅ 86 caracteres, 47 distintos; `settings.py` recusa chaves curtas também com `DEBUG=True`; nenhum `InsecureKeyLengthWarning` na suíte | `config/settings.py:40-49`, `config/test_secret_key.py` |
| Faturamento por perfil | ✅ Cliente 403, barbeiro 403 (inclusive filtrando o próprio id), admin 200 | PER-08 a PER-11 |
| Isolamento entre barbearias | ✅ 21/21 bloqueadas: leitura, alteração e exclusão de barbearia, usuários, serviços, barbeiros e agendamentos de outra barbearia; uso de barbeiro, serviço ou cliente alheios; horários livres; `exclude_appointment_id`; listas | ISO-01 a ISO-21 |
| Oráculo de IDs | ⚠️ Mensagens distintas revelam que um ID existe em outra barbearia | ISO-22, ISO-23 → SEC-10 |
| Escalada de privilégio | ✅ Cliente não se promove nem se reativa; barbeiro e cliente não gerenciam usuários, serviços ou barbearia; não é possível criar admin pela API | PER-01 a PER-07, PER-14, PER-15 |
| Regras de autorização de negócio | ❌ Cliente cria horário confirmado (BUS-15); barbeiro troca o cliente de um horário e cancela por PATCH (BUS-12); admin reativa a barbearia suspensa pela plataforma (BUS-02) | NEW-STATUS, BUS-12, BUS-02f |
| Sessão JWT | ✅ Refresh só em cookie HttpOnly, `SameSite=Lax`, caminho restrito; rotação e blacklist funcionam; logout revoga; conta desativada perde acesso imediatamente | SES-01 a SES-06 |
| Armazenamento do access token | ⚠️ `localStorage`, sem CSP; o token traz `nome` e `hash_password` | SES-03, SES-09 → SEC-04 |
| Rate limiting | ❌ Por processo: com 3 workers, 10 de 15 tentativas de login no mesmo minuto foram aceitas | `api/rate-limit-gunicorn-3-workers.txt` → SEC-05 |
| Recuperação de senha | ✅ Mesma resposta e tempo equivalente para e-mail existente e inexistente (mediana de 16 ms e 15 ms em 12 amostras); ❌ não envia e-mail | SES-10, SES-10b → AUTH-01 |
| CORS | ✅ Origem não autorizada não recebe `Access-Control-Allow-Origin`. O `.env` local libera também `localhost:3000`, que não é usado | SES-07, SES-08 → SEC-11 |
| Cabeçalhos | ✅ `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `COOP`; ❌ sem CSP | SES-09 |
| CSRF | ✅ API autenticada por header `Authorization`; o refresh por cookie depende de `SameSite=Lax`, que bloqueia POST de outro site | Leitura de código |
| Entradas malformadas | ✅ 400/404, sem erro 500, em agendamento, horários e relatório | SES-13 a SES-15 |
| SQL injection | ✅ Só ORM; o único `.extra()` usa SQL fixo | `appointments/views.py:351` |
| XSS | ✅ React escapa os dados; os três `dangerouslySetInnerHTML` recebem SVGs estáticos do projeto | `AuthLayout.tsx:22`, `LandingPage.tsx:61,141` |
| Uploads | ❌ Logo de 14,5 MB aceito; Pillow com 69 vulnerabilidades; SVG recusado | UPL-01, UPL-02 → SEC-09, DEP-01 |
| Negação de serviço | ❌ Serviço com duração 0 trava a requisição (gravável pelo Django Admin) | `api/sec07-duracao-zero.txt` → SEC-07 |
| Configuração de produção | ✅ `check --deploy` só com W021 (HSTS preload, opcional); ⚠️ `.env` local com `DEBUG=True` exibe a página técnica de rotas, e há credenciais padrão de desenvolvimento no código | SES-12 → SEC-11 |
| Dependências | ❌ 91 vulnerabilidades no backend e 14 no frontend | DEP-01, DEP-02 |
| Histórico do git | ⚠️ Chave antiga no commit `3f46df2`; o repositório tem remoto no GitHub (visibilidade não verificada) | SEC-06 |
| Logs | ⚠️ Não há configuração de logging, então não há vazamento em logs, mas também não há rastreio (OBS-01). O log do `runserver` registra só método, caminho e status | `config/settings.py` |

### 5.2 Problemas de segurança

BUS-15 (P1); BUS-02, BUS-12, AUTH-02, SEC-03, SEC-04, SEC-05, SEC-07, SEC-09 e DEP-01 (P2); SEC-06, SEC-08, SEC-10, SEC-11 e DEP-02 (P3). **Nenhum P0.**

---

## 6. Auditoria do backend

### 6.1 O que funciona

- **Estrutura:** a regra de tenant está centralizada em `TenantScopedQuerysetMixin` e reforçada nos serializers e em `Appointment.clean()`.
- **Concorrência:**
  - `select_for_update` nos barbeiros ao criar e alterar agendamentos;
  - trava dos admins ativos ao rebaixar ou desativar (BUS-01);
  - os testes de concorrência passam em PostgreSQL 16 (0 pulados).
- **Transações:** `transaction.atomic` nas operações compostas (usuário + perfil de barbeiro, promoção, desativação).
- **Exclusão lógica:** usuários, barbeiros e serviços são desativados, com `deleted_at` e `deleted_by` nos dois últimos. FKs com `PROTECT` preservam o histórico.
- **Eficiência:** 2 consultas por listagem e 4 no relatório e nos horários livres, sem N+1 (`api/consultas-sql-por-endpoint.txt`).
- **Correções novas do dono, verificadas:**
  - SEC-01: `config/settings.py:40-49`;
  - SEC-02: `appointments/views.py:52-57`;
  - BUS-01: `accounts/admin_integrity.py`, `User.save/delete`, `UserQuerySet`, Django Admin;
  - BUS-02 parcial: `Appointment._validar_barbearia_ativa`, `available_slots`;
  - BUS-07: `Appointment._validar_conclusao_apos_termino`.

### 6.2 O que falha

| Tema | Problemas |
|---|---|
| Criação e status de agendamentos | BUS-15, BUS-03, BUS-12, BUS-16 |
| Horário de funcionamento e dias | BUS-04, BUS-05, BUS-06, BUS-10, BUS-11 |
| Integridade de agenda | BUS-09, BUS-13, BUS-17, SEC-07 |
| Usuários e tenant | AUTH-02, PROD-01, BUS-19, BUS-02 |
| Relatórios | API-02, FE-11 |
| API | API-01, SEC-10, FE-17 (contrato) |
| Operação | AUTH-01, OBS-01, OPS-01, SEC-05, DEP-01 |
| Código | MAINT-01: código morto `_validar_campos_cliente_nao_autorizados` e `IsClientRole`; filtro `ativo` duplicado em dois ViewSets; comentários obsoletos (DOC-03) |

### 6.3 Testes do backend

| Execução | Resultado |
|---|---|
| SQLite (`--settings=config.test_settings`) | **327 testes, OK** (9 pulados: exigem PostgreSQL), 3,6 s |
| PostgreSQL 16 descartável | **327 testes, OK, 0 pulados**, 8,9 s |
| Distribuição | accounts 124 · appointments 123 · barbershops 51 · services 19 · config 10 (eram 239 em 11/11) |
| Cobertura (linhas + ramificações) | **91%** no total. Menores: `config/permissions.py` 74%; `accounts/managers.py`, `accounts/serializers.py` e `appointments/models.py` entre 85% e 86%. **A confirmação de recuperação de senha não tem nenhum teste** (`accounts/serializers.py:427-449`) |
| Testes sem asserção | 2, do tipo "não deve lançar erro", aceitáveis (`accounts/test_admin_integrity_paths.py:317,326`) |
| `makemigrations --check` | Sem alterações pendentes |
| `check --deploy` | 1 aviso (W021, HSTS preload) |

---

## 7. Auditoria do frontend

### 7.1 Qualidade de build

| Verificação | Resultado |
|---|---|
| `tsc` (app e `vite.config`) | 0 erros |
| ESLint `--max-warnings=0` | 0 erros, 0 avisos |
| Build de produção | OK. JS inicial 433,7 kB (138,1 kB gzip); CSS 53,6 kB (10,8 kB gzip); fontes locais de 18,7 kB e 26,8 kB; telas carregadas sob demanda |
| Testes automatizados | Inexistentes (FE-02) |

### 7.2 Funcionamento e integração

| Verificação | Resultado |
|---|---|
| Erros de console, erros de página e respostas ≥ 400 | **0** em 105 cargas e nos fluxos |
| Rotas e redirecionamentos por perfil | Corretos: cada perfil vai à própria página inicial; rota de outro perfil devolve à inicial; rota inexistente devolve ao início ou ao login, sem página 404 (FE-06) |
| Fluxo do cliente (celular 390 px) | Agendar (serviço → barbeiro → dia → horário → revisar → confirmar) → "Está marcado". Cancelar → diálogo → toast. **Reservou um domingo** (BUS-06) |
| Fluxo do barbeiro (tablet 820 px) | "A confirmar" → Confirmar → toast; "Concluir às HH:MM" desabilitado antes do término |
| Fluxo do admin (desktop) | Painel → Confirmar em "A seguir" → toast; horário inválido barrado no formulário; falha de recarga sem aviso (FE-03) |
| API fora do ar ao abrir | Tela "Sem conexão com o servidor", sessão preservada |
| API travada | Carregamento sem limite de tempo (FE-15) |
| Barbearia desativada | O admin só descobre ao agir; a lateral diz "Aberta até 19:00" (FE-14) |
| Novo agendamento após reservar | Continua na tela "Horário reservado" (FE-13, regressão) |
| Volume de requisições (build de produção) | Painel do admin, Agendamentos e Clientes: 25 requisições cada, 22 delas para páginas de `/appointments/` com 419 agendamentos. Cresce linearmente com o histórico (API-01). Em modo dev o `StrictMode` dobra o número |
| Contratos | Campo `barbeiro_especialidade` inexistente na API; filtro `tipo_perfil` ignorado; `cliente` obrigatório no POST do próprio cliente (FE-17) |
| Tratamento de erros HTTP | 400 com mensagem por campo; 401 renova a sessão uma vez e só desloga se o servidor recusar; 403 e 404 com mensagem; 429 e ≥ 500 com mensagens próprias (`utils/format.ts:222-243`) |

### 7.3 Redesign e identidade visual

- A identidade aprovada é aplicada de forma consistente em todas as telas auditadas:
  - **paleta "Placa esmaltada":** marinho, vermelho só para "agora", pendências, destrutivo e CTA, marfim e branco;
  - **tipografia:** League Gothic nos títulos e Public Sans na interface, as duas **servidas pelo próprio app**, sem Google Fonts;
  - **marca:** logo "Navalha aberta" e o poste como indicador de "aberta/agora";
  - **componentes:** os mesmos em admin, barbeiro, cliente e páginas públicas.
- Estados de carregamento (skeleton e barra de recarga), vazio (ilustrações), erro (com "Tentar novamente") e sucesso (toast, carimbo de reserva) existem em todas as telas de lista.
- Desvios pequenos (MAINT-01):
  - 45 estilos inline (`style={{…}}`);
  - cores literais em `ui.module.css` (ícones de toast) e `layout.module.css`, fora de `design-tokens.css`;
  - `ui.module.css` com 1.096 linhas;
  - 17 ícones e 3 funções sem uso (FE-07).
- Textos da interface que prometem o que o sistema não faz (FE-18).

---

## 8. Auditoria do banco de dados

| Tema | Resultado |
|---|---|
| Migrações (banco que o app usa) | Todas aplicadas (22 dos apps do projeto) |
| Migrações (banco do `docker-compose`) | **0007 e 0008 de `appointments` pendentes**: a coluna `preco_historico` não existe ali (DB-01) |
| Integridade do banco real (somente leitura) | Sem inconsistências em 26 contagens. Volume mínimo: 2 barbearias, 8 usuários, 2 serviços, **2 agendamentos** (FE-12); 1 conta sem barbearia criada pelo cadastro público (PROD-01) |
| Relacionamentos | FKs com `PROTECT` (histórico preservado); `deleted_by` com `SET_NULL`; `Barber.user` `OneToOne` |
| Constraints | Só PK, FK, `unique(email)` e `OneToOne`. **Nenhuma** constraint para: duração > 0, preço ≥ 0, fechamento > abertura, status válido, e-mail sem diferenciar maiúsculas, não sobreposição por barbeiro (DB-02) |
| Índices | Adequados ao uso: `(barbeiro, data_hora)`, `(barbershop, data_hora)`, `(barbershop, ativo)` em barbeiros e serviços |
| Concorrência | ✅ Comprovada em PostgreSQL 16: 20 pedidos simultâneos → 1 criado e 19 recusados |
| Migração reversa | ❌ Desfazer a 0008 zera os 419 preços históricos; refazer grava o preço atual e o faturamento realizado passa de R$ 15.215 para R$ 16.565 (DATA-01) |
| Fuso nos relatórios | ❌ Atendimento às 22:30 de 12/11 aparece no dia 13/11 do relatório (API-02) |
| Collation | ⚠️ Banco do app criado com glibc 2.43; o sistema tem 2.44 (DATA-03) |
| Consultas ineficientes | Nenhuma no backend; o gargalo é o frontend percorrer todas as páginas (API-01) |
| Crescimento | Tabela de tokens sem rotina de limpeza (`flushexpiredtokens`, OPS-01); hoje 13 tokens, nenhum expirado |

---

## 9. Integração ponta a ponta

Caminho de cada fluxo: Frontend → API → Backend → Banco → Resposta → Atualização da interface.

| Fluxo | Resultado | Camada da falha |
|---|---|---|
| Login e logout | ✅ Cookie definido, `/users/me/`, redirecionamento por perfil; logout revoga o refresh | — |
| Sessão expirada / renovação | ✅ 401 → refresh → repetição da chamada; recusa do servidor → toast e login | — |
| Cadastro público | ⚠️ Cria conta sem barbearia → onboarding de dono | Produto (PROD-01) |
| Onboarding (criar barbearia) | ✅ No frontend, com validação de horário; ⚠️ a API aceita horário inválido | Backend (BUS-05) |
| Recuperação de senha | ⚠️ Tela e API respondem; nenhum e-mail é enviado | Backend/configuração (AUTH-01) |
| Gestão de barbeiros | ✅ Criar, editar, desativar e reativar; ⚠️ a agenda futura do barbeiro desativado continua ativa | Backend (BUS-13) |
| Gestão de clientes | ✅; ⚠️ a tela baixa todos os agendamentos | Frontend/API (API-01) |
| Gestão de serviços | ✅; ⚠️ "1.000" vira R$ 1,00; validações fracas | Frontend (FE-16), Backend (BUS-18) |
| Dados da barbearia | ✅ Edição; ❌ sem logo | Frontend (FE-09) |
| Criar agendamento (cliente) | ✅ Conflito impedido e horários reais; ❌ domingos; ⚠️ "Agendar" de novo não reinicia a tela | Backend (BUS-06), Frontend (FE-13) |
| Criar agendamento (admin) | ❌ Sem tela (a API aceita: 201) | Frontend (BUS-14) |
| Reagendar (cliente) | ✅ Muda horário, barbeiro e serviço; ❌ mantém "confirmado" | Backend (BUS-03) |
| Cancelar (cliente) | ✅ Diálogo + toast; ⚠️ a API aceita cancelar horário que já passou | Backend (BUS-16) |
| Confirmar (admin/barbeiro) | ✅ Em "A seguir", na lista e na agenda | — |
| Concluir ("realizado") | ✅ Só após o término previsto (frontend e backend) | — |
| Agenda do barbeiro | ✅ Por dia e "a confirmar"; ⚠️ a contagem inclui vencidos | Frontend/produto (FE-04, BUS-08) |
| Caixa (painel) | ✅ Números reais pelo preço histórico; ⚠️ diverge do relatório da API em R$ 570 | Integração (FE-11) |
| Relatórios (`revenue-report`) | ✅ Protegido; ⚠️ dia em UTC; não é consumido pela interface | Backend (API-02) |
| Barbearia desativada | ⚠️ A API bloqueia a agenda; a interface não sinaliza; o admin reativa | Backend + Frontend (BUS-02, FE-14) |
| Experiência pública de agendamento | ❌ Não existe página pública por barbearia | Produto (PROD-01) |

---

## 10. Testes dos três perfis

Permissões testadas **pela API**, não só pela interface. Os códigos vêm de `api/sondagem-api.json` e `api/sondagem-api-complementar.json`.

### 10.1 Proprietário (admin)

| Item | Resultado |
|---|---|
| Telas acessíveis | Painel, Agendamentos, Serviços, Barbeiros, Clientes, Dados da barbearia, Minha conta. Rotas de cliente e barbeiro devolvem ao painel |
| Pode | Ver faturamento (200); gerenciar serviços, barbeiros e clientes; confirmar, concluir e cancelar qualquer horário do tenant; editar a barbearia; agendar para cliente pela API (201) |
| Bloqueado corretamente | Rebaixar ou desativar a própria conta (400 e 400); acessar outra barbearia (404 em 11 operações); usar barbeiro, serviço ou cliente de outra barbearia (400) |
| Problemas | Reativa a barbearia desativada pela plataforma (BUS-02f: 200); aceita fechamento antes da abertura (BUS-05); não agenda pela interface (BUS-14); não envia logo (FE-09); não sabe que a barbearia está desativada (FE-14); não cria um segundo admin (BUS-19) |

### 10.2 Barbeiro

| Item | Resultado |
|---|---|
| Telas acessíveis | Minha agenda (por dia e "a confirmar"), Minha conta |
| Pode | Ver só a própria agenda (140 itens, todos dele); confirmar; concluir após o término; agendar para si mesmo |
| Bloqueado corretamente | Faturamento (403, inclusive filtrando o próprio id); usuários (403); serviços (403); horário de outro barbeiro (404); agendar em nome de outro barbeiro (400); DELETE (cancelamento) de horário (403) |
| Problemas | Cancela por PATCH (200) embora o DELETE seja proibido, e **troca o cliente** de um horário (200) (BUS-12); cria horário já "cancelado" (BUS-15); recebe o e-mail de login dos colegas (SEC-03) |

### 10.3 Cliente

| Item | Resultado |
|---|---|
| Telas acessíveis | Início, Agendar horário, Meus agendamentos, Serviços e preços, Equipe, Minha conta |
| Pode | Agendar, reagendar e cancelar os próprios horários; ver serviços e equipe |
| Bloqueado corretamente | Faturamento (403); usuários (403); serviços, barbeiros e barbearia (403); confirmar o próprio horário por PATCH (403); horário de outro cliente (404); agendar em nome de outro cliente (gravado para ele mesmo); autopromoção (ignorada) |
| Problemas | **Cria horário já "confirmado"** (BUS-15: 201); reagendar mantém "confirmado" (BUS-03); cancela horário que já passou (BUS-16); marca dois horários simultâneos (BUS-17); vê o e-mail de login dos barbeiros (SEC-03); recebe 403 em vez de 404 ao consultar outro cliente por id (SEC-10); não consegue se cadastrar sozinho numa barbearia (PROD-01) |

### 10.4 Plataforma (superusuário)

Lê todos os tenants (419 agendamentos) e não cria recursos sem contexto de barbearia (403). Desativa uma barbearia por DELETE com confirmação, mas a desativação é revertida pelo admin do tenant (BUS-02). Não há painel próprio: no frontend, o superusuário cai no onboarding de dono (SA-01).

---

## 11. Responsividade e acessibilidade

### 11.1 Responsividade

| Largura | Rotas | Rolagem horizontal | Erros | Observações |
|---|---|---|---|---|
| Desktop 1440 px | 21 | 0 | 0 | — |
| Notebook 1280 × 720 | 21 | 0 | 0 | — |
| Tablet 820 px | 21 | 0 | 0 | Fluxo do barbeiro concluído |
| Celular 390 px | 21 | 0 | 0 | Fluxo do cliente concluído; menu inferior por perfil; diálogo de cancelamento |
| Celular 360 px | 21 | 0 | 0 | — |

Com 390 px, as funções continuam utilizáveis: barra de navegação inferior, quadro do dia e "A seguir" reordenados para o celular, ações de status nas listas e agendamento em quatro passos.

Detalhes a corrigir:

- filtro de status cortado sem sinal de rolagem e placeholder da busca truncado (FE-20);
- links de texto nas telas públicas com 16 a 22 px de altura (FE-19).

### 11.2 Acessibilidade

| Verificação | Resultado |
|---|---|
| axe-core, WCAG A/AA (36 páginas, desktop e celular) | **0 violações** (controle: 3 violações plantadas foram detectadas) |
| Contraste | Aprovado pelo axe em todas as páginas |
| Teclado | Primeiro Tab no app: "Pular para o conteúdo"; no login, ordem lógica e foco visível em todos os controles; menus e diálogos com Esc (código e auditoria anterior) |
| Rótulos e ARIA | Campos com rótulo; grupos de opção com `role="radiogroup"`; botões de ícone com `aria-label`; gráfico com tabela alternativa para leitor de tela; `aria-live` em horários e confirmação |
| Áreas clicáveis | Botões e controles ≥ 24 px; exceção: links de texto públicos (FE-19) |
| Leitor de tela | Não testado (NV-3) |

---

## 12. Comparação com a auditoria anterior

### 12.1 Situação dos 53 problemas

| ID | Antes | Estado atual | Agora | Verificação nesta auditoria |
|---|---|---|---|---|
| SEC-01 | P0 | ✅ Resolvido e verificado | — | Chave com 86 caracteres; validação em `settings.py`; 10 testes; sem aviso de chave curta |
| SEC-02 | P0 | ✅ Resolvido e verificado | — | PER-08 a PER-11; 13 testes |
| BUS-01 | P1 | ✅ Resolvido e verificado | — | BUS-01 e BUS-01b: 400; testes de concorrência em PostgreSQL. Efeito colateral em BUS-19 |
| BUS-02 | P1 | ◐ Parcialmente resolvido | P2 | Agenda congela (BUS-02c: 400). O admin reativa (02f: 200), os cadastros continuam (02d e 02e: 201) e a interface não sinaliza |
| BUS-03 | P1 | Continua presente | P1 | 200 com status `confirmado` |
| BUS-04 | P1 | Continua presente | P1 | 200 |
| BUS-05 | P1 | Continua presente | P1 | 200 e 200 (completo e parcial) |
| BUS-06 | P1 | Continua presente | P1 | API: 10 horários num domingo; interface: reserva concluída num domingo |
| PROD-01 | P1 | Continua presente | P1 | `barbershop=None` |
| AUTH-01 | P1 | Continua presente | P1 | Sem `EMAIL_*`; `fail_silently=True` |
| BUS-07 | P1 | ✅ Resolvido e verificado | — | 400 com mensagem; 13 testes; botão desabilitado na interface |
| AUTH-02 | P2 | Continua presente (ampliado) | P2 | Cadastro 201, login 401 e também troca do próprio e-mail (200) |
| SEC-03 | P2 | Continua presente | P2 | 3 de 3 barbeiros com e-mail |
| SEC-04 | P2 | Continua presente | P2 | `localStorage`, sem CSP; comentário do settings contradiz |
| SEC-05 | P2 | Continua presente (agora reproduzido) | P2 | 10 de 15 logins aceitos com 3 workers |
| SEC-07 | P2 | Continua presente (agora reproduzido) | P2 | Sem resposta em 10 s |
| BUS-08 | P2 | Continua presente | P2 | 22 vencidos como "agendado" na base de teste |
| BUS-09 | P2 | Continua presente (agora reproduzido) | P2 | Horário das 10:00 passou a terminar às 11:00, sobrepondo o das 10:30 |
| BUS-11 | P2 | Continua presente | P2 | Só horas cheias para 60 min |
| BUS-13 | P2 | Continua presente | P2 | Os 20 horários futuros verificados continuam ativos, por DELETE e por rebaixamento |
| BUS-14 | P2 | Continua presente | P2 | API 201; sem tela |
| API-01 | P2 | Continua presente | P2 | `page_size`, `search`, `ordering` e `tipo_perfil` ignorados; 22 páginas por carga do painel |
| DATA-01 | P2 | Continua presente (agora reproduzido) | P2 | 419 → 0 preços; R$ 15.215 → R$ 16.565 |
| OBS-01 | P2 | Continua presente | P2 | Sem `LOGGING`, monitoramento, auditoria ou health check |
| OPS-01 | P2 | Continua presente | P2 | Sem Dockerfile, CI, estáticos ou mídia em produção |
| FE-01 | P2 | Continua presente | P2 | Nenhum error boundary |
| FE-02 | P2 | Continua presente | P2 | Nenhum teste de frontend |
| TEST-01 | P2 | ◐ Parcialmente resolvido | P2 | +88 testes (SEC-01, SEC-02, BUS-01, BUS-02, BUS-07); continuam sem teste BUS-03, 04, 05, 10, 12, 15, 16, 17, AUTH-02, SEC-03 e a confirmação de recuperação de senha |
| DOC-01 | P2 | Continua presente | P2 | Linhas 82, 77-99, 96, 126, 142 e 399 do documento da API |
| REPO-01 | P2 | Continua presente | P2 | 4.875 de 5.112 arquivos versionados são do `venv312/` |
| SA-01 | P2 | Continua presente | P2 | Branch `feature/painel-super-admin` sem commits próprios |
| SAAS-01 | P2 | Continua presente | P2 | — |
| SEC-06 | P3 | Continua presente | P3 | Commit `3f46df2`; remoto no GitHub |
| SEC-08 | P3 | Continua presente | P3 | — |
| BUS-10 | P3 | Continua presente | P3 | 14 horários para ontem |
| BUS-12 | P3 | Continua presente (**reclassificado**) | **P2** | Agora reproduzido também a troca de cliente pelo barbeiro (200), o que é mais grave que uma inconsistência |
| API-02 | P3 | Continua presente (agora reproduzido) | P3 | 22:30 de 12/11 contado em 13/11 |
| DATA-02 | P3 | Continua presente | P3 | Limitação documentada na migração |
| DATA-03 | P3 | Continua presente | P3 | Collation 2.43 × 2.44 |
| FE-03 | P3 | Continua presente (agora reproduzido) | P3 | API derrubada + "Atualizar": nenhuma mensagem |
| FE-04 | P3 | ◐ Parcialmente resolvido | P3 | O rótulo diz "no total / em todas as datas", mas ainda conta vencidos (40, dos quais 22 vencidos) |
| FE-05 | P3 | Continua presente | P3 | `SHOP_TZ` fixo |
| FE-06 | P3 | Continua presente | P3 | Rota inexistente → início/login |
| FE-07 | P3 | Continua presente (ampliado) | P3 | 17 ícones (eram 14), `getTotalServices`, `getTotalBarbers`, `isPast`, `formatDateTime` e `revenueReport` sem uso |
| FE-08 | P3 | ✅ Resolvido e verificado | — | Fontes `woff2` locais; `index.html` sem Google Fonts |
| FE-09 | P3 | Continua presente | P3 | Sem logo na tela; barbeiro não reagenda |
| FE-11 | P3 | Continua presente (agora reproduzido) | P3 | R$ 570 de diferença |
| DOC-02 | P3 | Continua presente | P3 | README: SQLite por padrão e proxy do Vite inexistente |
| DOC-03 | P3 | Continua presente | P3 | `accounts/models.py:7`, `config/settings.py:72` |
| REPO-02 | P3 | Continua presente (ampliado) | P3 | Também `.codex/`, `.impeccable/`, `references/` (HTML de sites de terceiros) e `media/` fora do `.gitignore` |
| REPO-03 | P3 | Continua presente | P3 | `master` 31 commits atrás; `feature` 1 atrás e sem commits próprios; `release` com 1 commit próprio |
| TEST-02 | P3 | Continua presente | P3 | Cobertura medida só pela auditoria (91%); o projeto não tem a ferramenta |
| FE-12 | P3 | Continua presente | P3 | 2 agendamentos no banco real |

### 12.2 Itens não verificados da auditoria anterior

| ID | Antes | Agora |
|---|---|---|
| NV-1 | Entrega de e-mail | **Continua não verificável**: sem SMTP configurado |
| NV-2 | Concorrência em PostgreSQL | **Verificado**: CON-01 e testes de concorrência em PostgreSQL 16 |
| NV-3 | Leitor de tela | Continua não verificado; checagens automáticas aprovadas |
| NV-4 | Tablet e outros navegadores | Tablet (820 px) **verificado**; Chrome e Safari continuam não verificados |
| NV-5 | Rate limiting real | **Verificado**: funciona num processo e falha com vários (SEC-05) |

### 12.3 Correções ao que a auditoria anterior afirmou

| Afirmação de 11/11 | Correção |
|---|---|
| "Banco PostgreSQL 16 via `docker-compose.yml` (porta 5433)" e "migrações íntegras e aplicadas" | O `.env` aponta para o PostgreSQL **18** do host (porta 5432), onde as migrações estão aplicadas. O banco do `docker-compose` é outro e está com duas migrações pendentes (DB-01) |
| "Isolamento resistiu às 16 tentativas" | Confirmado e ampliado para 21 tentativas; foram encontrados dois oráculos de existência de IDs (SEC-10) |
| SEC-07 e DATA-01 "não executados" | Agora reproduzidos em ambiente descartável |

---

## 13. Lista completa de problemas

### 13.1 Índice dos 70 problemas abertos

| # | ID | Sev. | Camada | Título | Estado | Confiança |
|---|---|---|---|---|---|---|
| 1 | BUS-15 | P1 | Backend | Cliente cria agendamento já "confirmado" | Novo | Confirmado |
| 2 | BUS-03 | P1 | Backend | Reagendamento mantém "confirmado" | Continua | Confirmado |
| 3 | BUS-06 | P1 | Backend + Frontend | Domingos e dias fechados recebem agendamentos | Continua | Confirmado |
| 4 | BUS-05 | P1 | Backend | Fechamento anterior à abertura é aceito | Continua | Confirmado |
| 5 | BUS-04 | P1 | Backend | Troca de serviço ignora o horário de funcionamento | Continua | Confirmado |
| 6 | PROD-01 | P1 | Produto | Cliente não se cadastra numa barbearia | Continua | Confirmado |
| 7 | AUTH-01 | P1 | Backend / Config. | Recuperação de senha não envia e-mail | Continua | Confirmado (código) |
| 8 | BUS-02 | P2 | Backend + Frontend | Suspensão de barbearia parcial e reversível pelo próprio admin | Parcial | Confirmado |
| 9 | BUS-12 | P2 | Backend | Barbeiro troca o cliente e cancela por PATCH, mas não por DELETE | Continua (reclass.) | Confirmado |
| 10 | BUS-16 | P2 | Backend | Cliente cancela horário que já passou | Novo | Confirmado |
| 11 | BUS-17 | P2 | Backend | Mesmo cliente com horários simultâneos, sem limite de reservas | Novo | Confirmado |
| 12 | AUTH-02 | P2 | Backend / Banco | E-mails duplicados por maiúsculas (cadastro e edição) | Continua | Confirmado |
| 13 | SEC-03 | P2 | Backend | E-mail de login dos barbeiros exposto a clientes | Continua | Confirmado |
| 14 | SEC-04 | P2 | Frontend / Infra | Access token em `localStorage`, sem CSP | Continua | Confirmado |
| 15 | SEC-05 | P2 | Infra | Rate limiting por processo | Continua | Confirmado |
| 16 | SEC-07 | P2 | Backend / Banco | Serviço com duração 0 trava a requisição | Continua | Confirmado |
| 17 | SEC-09 | P2 | Backend / Infra | Upload de logo sem limite de tamanho | Novo | Confirmado |
| 18 | DEP-01 | P2 | Dependências | Backend com 91 vulnerabilidades conhecidas; Django fora de suporte | Novo | Confirmado |
| 19 | DB-01 | P2 | Banco / Config. | Dois bancos de desenvolvimento divergentes | Novo | Confirmado |
| 20 | DATA-01 | P2 | Banco | Reverso da migração 0008 apaga e altera preços | Continua | Confirmado |
| 21 | BUS-08 | P2 | Backend / Produto | Sem "não compareceu" nem desfecho de vencidos | Continua | Confirmado |
| 22 | BUS-09 | P2 | Backend / Banco | Duração do atendimento não é histórica | Continua | Confirmado |
| 23 | BUS-11 | P2 | Backend | Passo entre horários igual à duração | Continua | Confirmado |
| 24 | BUS-13 | P2 | Backend | Desativar ou rebaixar barbeiro não trata a agenda | Continua | Confirmado |
| 25 | BUS-14 | P2 | Frontend | Admin não agenda pela interface | Continua | Confirmado |
| 26 | API-01 | P2 | API + Frontend | Sem filtros, busca e `page_size`; telas baixam todo o histórico | Continua | Confirmado |
| 27 | FE-01 | P2 | Frontend | Sem error boundary | Continua | Confirmado (código) |
| 28 | FE-02 | P2 | Frontend / Testes | Nenhum teste de frontend | Continua | Confirmado |
| 29 | TEST-01 | P2 | Testes | Regras quebradas sem teste de regressão | Parcial | Confirmado |
| 30 | OBS-01 | P2 | Backend / Infra | Sem logs, monitoramento, trilha de auditoria e health check | Continua | Confirmado (código) |
| 31 | OPS-01 | P2 | Infra | Sem infraestrutura de implantação | Continua | Confirmado |
| 32 | DOC-01 | P2 | Documentação | Documentação da API contradiz o comportamento | Continua | Confirmado |
| 33 | REPO-01 | P2 | Repositório | Virtualenv versionado | Continua | Confirmado |
| 34 | SA-01 | P2 | Produto | Sem painel de Super Admin | Continua | Confirmado |
| 35 | SAAS-01 | P2 | Produto | Sem notificações, LGPD e cobrança | Continua | Confirmado |
| 36 | FE-13 | P3 | Frontend | "Agendar" após reservar continua mostrando "Horário reservado" | **Novo (regressão)** | Confirmado |
| 37 | FE-14 | P3 | Frontend | Barbearia desativada e dia da semana ignorados no status "Aberta" | Novo | Confirmado |
| 38 | FE-03 | P3 | Frontend | Falha de recarga sem aviso | Continua | Confirmado |
| 39 | FE-15 | P3 | Frontend | Requisições sem tempo limite | Novo | Confirmado |
| 40 | FE-16 | P3 | Frontend | "1.000" no preço vira R$ 1,00 | Novo | Confirmado |
| 41 | FE-04 | P3 | Frontend | Contador "a confirmar" inclui vencidos | Parcial | Confirmado |
| 42 | FE-17 | P3 | Integração | Contratos de API e tipos divergentes | Novo | Confirmado |
| 43 | FE-18 | P3 | Frontend | Textos que prometem o que o sistema não faz | Novo | Confirmado |
| 44 | FE-19 | P3 | Frontend / A11y | Links de texto pequenos para toque nas telas públicas | Novo | Confirmado |
| 45 | FE-20 | P3 | Frontend | Filtro de status cortado e busca truncada no celular | Novo | Confirmado |
| 46 | FE-05 | P3 | Integração | Fuso horário fixo no frontend | Continua | Confirmado (código) |
| 47 | FE-06 | P3 | Frontend | Sem página 404 | Continua | Confirmado |
| 48 | FE-07 | P3 | Frontend | Código morto | Continua (ampliado) | Confirmado |
| 49 | FE-09 | P3 | Frontend | Sem tela de logo; barbeiro não reagenda | Continua | Confirmado |
| 50 | FE-11 | P3 | Integração | Painel e relatório da API calculam o faturamento de formas diferentes | Continua | Confirmado |
| 51 | API-02 | P3 | Backend | Relatório agrupa o dia em UTC | Continua | Confirmado |
| 52 | BUS-10 | P3 | Backend | Horários livres para datas passadas | Continua | Confirmado |
| 53 | BUS-18 | P3 | Backend | Validações de cadastro fracas | Novo | Confirmado |
| 54 | BUS-19 | P3 | Backend / Produto | Sem segundo admin nem transferência de titularidade | Novo | Confirmado (código) |
| 55 | SEC-06 | P3 | Repositório | Chave antiga no histórico do git | Continua | Confirmado |
| 56 | SEC-08 | P3 | Backend | Sem verificação de e-mail no cadastro | Continua | Confirmado (código) |
| 57 | SEC-10 | P3 | Backend | Oráculo de existência de IDs | Novo | Confirmado |
| 58 | SEC-11 | P3 | Configuração | Configurações de desenvolvimento inseguras se reaproveitadas | Novo | Confirmado |
| 59 | DEP-02 | P3 | Dependências | Frontend com 14 vulnerabilidades conhecidas | Novo | Confirmado |
| 60 | DATA-02 | P3 | Banco | Preços históricos antigos estimados | Continua | Confirmado |
| 61 | DATA-03 | P3 | Banco | Divergência de collation | Continua | Confirmado |
| 62 | DB-02 | P3 | Banco | Regras de negócio sem constraints no banco | Novo | Confirmado |
| 63 | MAINT-01 | P3 | Código | Componentes grandes, estilos inline, duplicação e código morto no backend | Novo | Confirmado |
| 64 | DOC-02 | P3 | Documentação | README com instruções incorretas | Continua (ampliado) | Confirmado |
| 65 | DOC-03 | P3 | Documentação | Comentários obsoletos sobre o app `core` | Continua | Confirmado |
| 66 | DOC-04 | P3 | Documentação | Índice de `docs/` e comentários desatualizados | Novo | Confirmado |
| 67 | REPO-02 | P3 | Repositório | Arquivos soltos e pastas fora do `.gitignore` | Continua (ampliado) | Confirmado |
| 68 | REPO-03 | P3 | Repositório | Branches dessincronizadas | Continua | Confirmado |
| 69 | TEST-02 | P3 | Testes | Cobertura não medida pelo projeto | Continua | Confirmado |
| 70 | FE-12 | P3 | Dados / Apresentação | Banco real quase vazio para a demonstração | Continua | Confirmado |

Os detalhes abaixo seguem esta ordem. Referências do tipo "BUS-03 (sondagem)" apontam para `api/sondagem-api.json` ou `api/sondagem-api-complementar.json` da pasta de evidências.

---

### 13.2 Problemas P1 — Alto (7)

#### BUS-15 — Cliente cria agendamento já "confirmado"

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend (serializer e view) | `appointments/serializers.py:34,37`; `appointments/views.py:87-105`; `appointments/models.py:345-347` | Confirmado | **Novo** |

- **Descrição.**
  - O campo `status` do `AppointmentSerializer` é gravável também na criação.
  - `perform_create` não fixa o status inicial.
  - A máquina de estados (`_validar_transicao_status`) retorna cedo quando o registro ainda não existe.
  - Resultado: qualquer perfil escolhe o status de um agendamento novo. Só "realizado" é barrado, pela regra do BUS-07.
- **Evidência.**
  - NEW-STATUS: cliente → **201, status `confirmado`**.
  - NEW-STATUS-2: barbeiro → **201, status `cancelado`**.
  - Nenhum teste cobre a criação com `status`.
- **Reprodução.**
  1. Entrar como cliente.
  2. `POST /api/v1/appointments/` com `cliente` (o próprio id), `barbeiro`, `servico`, `data_hora` futura e `"status": "confirmado"`.
- **Resultado atual.** 201 com `status: confirmado`.
- **Resultado esperado.** Todo agendamento novo nasce `agendado`: o campo é ignorado ou a API responde 400.
- **Impacto.**
  - O cliente contorna a confirmação da barbearia.
  - O horário não entra na fila "a confirmar" do admin nem do barbeiro.
  - A agenda mostra uma confirmação que ninguém deu.
- **Recomendação.**
  1. Tornar `status` somente leitura quando `self.instance is None`, ou chamar `serializer.save(status=AGENDADO)` em `perform_create`.
  2. No model, recusar registro novo com status diferente de `agendado`, salvo origem administrativa explícita.
  3. Teste para os três perfis.

#### BUS-03 — Reagendamento pelo cliente mantém "confirmado"

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend | `appointments/serializers.py:228-255` (`update`), `:128-170` | Confirmado | Continua presente |

- **Descrição.** Quando o cliente altera `data_hora`, `barbeiro` ou `servico` de um horário confirmado, o status continua "confirmado". A barbearia confirmou o horário antigo, não o novo.
- **Evidência.**
  - Sondagem BUS-03: criar → admin confirma → cliente reagenda → **200 com `status: confirmado`**.
  - A tela de sucesso do reagendamento diz "O novo horário já está na sua agenda" (`AppointmentCreatePage.tsx`).
- **Reprodução.**
  1. Cliente cria um horário.
  2. Admin aplica `PATCH {"status": "confirmado"}`.
  3. Cliente aplica `PATCH {"data_hora": "<outro horário>"}`.
- **Resultado atual.** `confirmado`.
- **Resultado esperado.** Volta a `agendado` quando horário, barbeiro ou serviço mudam; alterar só `observacoes` não muda o status.
- **Impacto.** Barbeiro e admin confiam numa confirmação que não existe. Somado ao BUS-15, o fluxo de confirmação fica sem garantia.
- **Recomendação.** Em `update`, redefinir `status = AGENDADO` na mesma transação quando esses campos mudarem; decidir se a regra vale para alterações do admin e do barbeiro; testes.

#### BUS-06 — Domingos e dias fechados recebem agendamentos

> **Rodada 1 de correções (13/11/2026): Parcialmente resolvido (dias da semana configuráveis; feriados, folgas e disponibilidade por barbeiro continuam ausentes).** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend + Banco + Frontend | `appointments/views.py:236-268`; `barbershops/models.py:22-23`; `frontend/src/pages/AppointmentCreatePage.tsx:25,104` | Confirmado | Continua presente |

- **Descrição.**
  - O sistema não modela dias de funcionamento, feriados, bloqueios nem folgas e horário de cada barbeiro.
  - O mesmo horário de abertura e fechamento vale para todos os dias e todos os barbeiros.
  - O frontend oferece os próximos 21 dias sem distinção.
- **Evidência.**
  - API: domingo 15/11 → **10 horários** para um serviço de 60 min.
  - Navegador: domingo com **16 horários**, e uma reserva concluída para **domingo, 22/11** (capturas `fluxo_cliente_domingo_com_horarios.png` e `fluxo_cliente_agendamento_concluido.png`).
- **Reprodução.** `GET /api/v1/appointments/available-slots/?barbeiro=<id>&servico=<id>&data=<próximo domingo>`, ou agendar pela tela escolhendo "Dom".
- **Resultado atual.** Horários oferecidos e reserva aceita.
- **Resultado esperado.** Dias fechados e folgas sem horários; a API recusa a criação com mensagem clara.
- **Impacto.** Clientes reservam com a barbearia fechada. É o problema mais visível numa demonstração com o calendário.
- **Recomendação.**
  1. Grade semanal da barbearia (dia × abertura e fechamento, com intervalos).
  2. Exceções por data e disponibilidade por barbeiro.
  3. Aplicar em `available_slots` e em `Appointment.clean()`.
  4. Tela de configuração.
  5. Como medida mínima imediata: um campo "dias de funcionamento" na barbearia.

#### BUS-05 — Fechamento anterior à abertura é aceito

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend (model e serializer) | `barbershops/models.py:12-35` (sem `clean`); `barbershops/serializers.py:20-32` | Confirmado | Continua presente |

- **Descrição.** A API aceita `horario_fechamento` ≤ `horario_abertura`, na edição completa e na parcial. O frontend valida, mas a API é a defesa real.
- **Evidência.**
  - Sondagem BUS-05: completo **200**, parcial **200**.
  - Navegador: o formulário bloqueou o mesmo caso (`admin_desktop_validacao_horario.png`).
- **Reprodução.** `PATCH /api/v1/barbershops/<id>/` com `{"horario_abertura": "18:00:00", "horario_fechamento": "08:00:00"}`, ou só `{"horario_fechamento": "08:30:00"}`.
- **Resultado atual.** 200.
- **Resultado esperado.** 400, inclusive quando só um dos campos é enviado.
- **Impacto.** Nenhum horário é gerado e todos os agendamentos são recusados sem explicação: a barbearia "some" da agenda.
- **Recomendação.** `Barbershop.clean()` com `fechamento > abertura`; `validate()` do serializer comparando com o valor persistido no PATCH parcial; `CheckConstraint` (DB-02); testes.

#### BUS-04 — Troca de serviço ignora o horário de funcionamento

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend (model) | `appointments/models.py:238-248` | Confirmado | Continua presente |

- **Descrição.** `_validar_horario_funcionamento` retorna cedo se `data_hora` não mudou e não considera a troca de serviço, então um serviço mais longo ultrapassa o fechamento.
- **Evidência.** Sondagem BUS-04: horário às 18:30 (fechamento às 19:00), serviço trocado de 30 para 60 min → **200**.
- **Reprodução.** Criar às 18:30 com serviço de 30 min; `PATCH {"servico": <id do serviço de 60 min>}`.
- **Resultado atual.** 200; o atendimento termina às 19:30.
- **Resultado esperado.** 400 com a mensagem de fechamento.
- **Impacto.** Atendimentos fora do expediente.
- **Recomendação.** Revalidar quando `data_hora` **ou** `servico_id` mudarem; testes para os dois casos.

#### PROD-01 — Cliente não se cadastra numa barbearia

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Produto (backend + frontend) | `accounts/serializers.py:309-321`; `accounts/views.py:119-130`; `frontend/src/pages/RegisterPage.tsx`, `OnboardingPage.tsx` | Confirmado | Continua presente |

- **Descrição.** O cadastro público cria um cliente sem barbearia, que é levado a criar a própria barbearia. Não há página pública, convite nem código por barbearia.
- **Evidência.**
  - Sondagem PROD-01: **201, `barbershop=None`**.
  - No banco real há 1 conta sem barbearia criada pelo cadastro.
- **Reprodução.** `/register` → a conta entra em "Vamos cadastrar sua barbearia".
- **Resultado atual.** Só o admin cadastra clientes, informando uma senha inicial que ele mesmo conhece.
- **Resultado esperado.** Cliente se cadastra e agenda numa barbearia específica.
- **Impacto.** Inviabiliza a aquisição de clientes; cria tenants vazios.
- **Recomendação.** Página pública por barbearia (`/b/<slug>`) ou convite por link, e separação entre conta de dono e conta de cliente.

#### AUTH-01 — Recuperação de senha não envia e-mail

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P1** | Backend / Configuração | `config/settings.py` (sem `EMAIL_*`); `accounts/serializers.py:381-419` | Confirmado por código; entrega não verificável (NV-1) | Continua presente |

- **Descrição.**
  - Sem `EMAIL_BACKEND` nem SMTP configurados: o Django tenta `localhost:25`.
  - `fail_silently=True` engole a falha sem log.
  - A mensagem traz `uid` e `token` em texto, sem link.
  - A confirmação não tem nenhum teste (`accounts/serializers.py:427-449` sem cobertura).
- **Evidência.** Busca em `settings.py`; respostas 204 para e-mail existente e inexistente (SES-10); relatório de cobertura.
- **Reprodução.** `/password/reset` com uma conta existente → a tela confirma, mas nenhum e-mail chega.
- **Resultado atual.** O usuário fica sem acesso até alguém intervir.
- **Resultado esperado.** E-mail com link para a tela de nova senha; falhas registradas em log.
- **Impacto.** Recuperação de acesso inexistente na prática.
- **Recomendação.** Variáveis `EMAIL_*` no `.env.example`; backend de console em desenvolvimento; link `FRONTEND_URL/password/reset/confirm?uid=…&token=…`; log de falhas; testes da confirmação.

---

### 13.3 Problemas P2 — Médio (28)

#### BUS-02 — Suspensão de barbearia parcial e reversível pelo próprio admin

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 (era P1) | Backend + Frontend | `barbershops/serializers.py:15,18` (`ativo` gravável); `barbershops/views.py:38`; `appointments/models.py:145-175`; `frontend/src/components/AppLayout.tsx:296-310` | Confirmado | **Parcialmente resolvido** |

- **Descrição.**
  - **O que foi corrigido:** com `ativo=False`, ninguém cria, remarca, confirma ou conclui agendamentos, e os horários livres são recusados. Os testes do dono cobrem isso.
  - **O que continua:**
    - o campo `ativo` continua gravável pelo admin do tenant, que **desfaz a desativação feita pela plataforma** (o DELETE é restrito ao staff, mas o PATCH não);
    - login, cadastro de clientes e serviços e edição da barbearia seguem normalmente;
    - a interface não mostra que a barbearia está desativada (FE-14).
- **Evidência.** Sondagem BUS-02:
  - plataforma desativa → 204;
  - cliente agenda → **400**, como esperado;
  - admin cria serviço → **201** e cadastra cliente → **201**;
  - admin aplica `PATCH {"ativo": true}` → **200** e a barbearia volta a operar.
  - O teste do dono `test_admin_desativa_e_reativa_a_barbearia` assume essa reativação como regra.
- **Reprodução.**
  1. Superusuário: `DELETE /api/v1/barbershops/<id>/?confirmar=<nome>`.
  2. Admin do tenant: `PATCH /api/v1/barbershops/<id>/` com `{"ativo": true}`.
- **Resultado atual.** Reativada pelo próprio tenant.
- **Resultado esperado.** Distinguir "pausa pelo dono" de "suspensão pela plataforma". A suspensão só pode ser revertida pelo staff.
- **Impacto.** A plataforma não consegue suspender uma barbearia (inadimplência, abuso). Vira P1 se houver cobrança.
- **Recomendação.**
  1. `ativo` somente leitura para não-staff, ou um campo separado `suspensa_pela_plataforma`.
  2. Verificação central que bloqueie a escrita em todo o tenant suspenso.
  3. Aviso na interface.
  4. Testes.

#### BUS-12 — Barbeiro troca o cliente e cancela por PATCH, mas não por DELETE

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 (era P3) | Backend | `appointments/serializers.py:99-126`; `appointments/views.py:40-51` | Confirmado | Continua presente — **reclassificado** |

- **Descrição.**
  - O DELETE (cancelamento) é proibido ao barbeiro, mas `PATCH {"status": "cancelado"}` é aceito.
  - O serializer só impede o **cliente** de trocar o campo `cliente`, então o barbeiro reatribui o horário a outra pessoa.
- **Evidência.** Sondagem complementar BUS-12, no horário do próprio barbeiro:
  - DELETE **403**;
  - `PATCH {"cliente": <outro>}` **200**, e o horário passou ao outro cliente;
  - `PATCH {"status": "cancelado"}` **200**.
- **Reprodução.** Como barbeiro, nos próprios horários, executar as três chamadas acima.
- **Resultado atual.** Regras contraditórias, e o cliente original perde o horário sem consentimento.
- **Resultado esperado.** Mesma regra nos dois caminhos; troca de cliente só pelo admin, ou proibida.
- **Impacto.** Integridade da agenda e dos dados do cliente; a reclassificação para P2 decorre da troca de cliente agora reproduzida.
- **Recomendação.** Definir a regra, aplicá-la no serializer e no `get_permissions`, e testar.

#### BUS-16 — Cliente cancela horário que já passou

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/serializers.py:108-145`; `appointments/views.py:115-131` | Confirmado | **Novo** |

- **Descrição.** Não há prazo para cancelamento: o cliente cancela um horário que já começou ou terminou, inclusive um confirmado que ainda não foi marcado como realizado.
- **Evidência.** Sondagem NEW-PASTCANCEL: horário das 14:00 de hoje, cancelado depois das 15:40 → **204**.
- **Reprodução.** `DELETE /api/v1/appointments/<id>/`, ou `PATCH {"status": "cancelado"}`, num horário próprio com `data_hora` no passado.
- **Resultado atual.** Cancelado.
- **Resultado esperado.** Recusado depois do início (ou de uma antecedência mínima configurável). Horários passados viram "realizado" ou "não compareceu" (BUS-08).
- **Impacto.**
  - Um atendimento feito pode sair do faturamento por iniciativa do cliente, antes de o barbeiro marcar "realizado".
  - Não comparecimentos viram "cancelamentos".
- **Recomendação.** Bloquear o cancelamento pelo cliente após `data_hora`, com antecedência mínima configurável; teste.

#### BUS-17 — Mesmo cliente com horários simultâneos, sem limite de reservas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/models.py:304-332` (conflito só por barbeiro) | Confirmado | **Novo** |

- **Descrição.**
  - A checagem de conflito considera só o barbeiro: o mesmo cliente reserva o mesmo horário com dois barbeiros.
  - Não há limite de reservas futuras por cliente.
  - O único freio é o throttling de 1.000 requisições por hora.
- **Evidência.** Sondagem NEW-OVERLAP: duas reservas às 16:00 do mesmo dia, com barbeiros diferentes → **201 / 201**.
- **Reprodução.** Dois `POST /appointments/` do mesmo cliente, mesmo horário, barbeiros diferentes.
- **Resultado atual.** Os dois são aceitos.
- **Resultado esperado.** O segundo é recusado; limite de reservas ativas por cliente.
- **Impacto.** Agenda inflada e horários bloqueados para outros clientes. Um cliente mal-intencionado ocupa a agenda inteira.
- **Recomendação.** Validar a sobreposição por cliente em `clean()`, sob a mesma trava; limite configurável de reservas futuras; testes.

#### AUTH-02 — E-mails duplicados por maiúsculas (cadastro e edição)

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Banco | `accounts/managers.py:43`; `accounts/models.py:29`; `accounts/serializers.py:46-57` | Confirmado | Continua presente (ampliado) |

- **Descrição.** `normalize_email` só converte o domínio para minúsculas, e a unicidade de `email` diferencia maiúsculas. Além do cadastro, o próprio usuário troca o e-mail para uma variação do e-mail de outra pessoa.
- **Evidência.** Sondagem:
  - AUTH-02 (cadastro de `CLIENTE1@…` existente) **201**;
  - AUTH-02b (login com outra grafia) **401**;
  - AUTH-02c (troca do próprio e-mail para `CLIENTE2@…`) **200**.
  - No banco real há 0 duplicados.
- **Reprodução.** `POST /auth/register/` com um e-mail existente em maiúsculas; `PATCH /users/<seu id>/` com `{"email": "<e-mail de outro em maiúsculas>"}`.
- **Resultado atual.** Contas duplicadas; login sensível à grafia.
- **Resultado esperado.** 400 "e-mail já cadastrado"; login aceita qualquer grafia.
- **Impacto.** Contas duplicadas; a recuperação (`email__iexact().first()`) pode escolher a conta errada.
- **Recomendação.** Normalizar para minúsculas no manager, nos serializers e no login; `UniqueConstraint(Lower('email'))` após checar duplicados; testes.

#### SEC-03 — E-mail de login dos barbeiros exposto a clientes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `barbershops/serializers.py:39` | Confirmado | Continua presente |

- **Descrição.** `GET /barbers/`, necessário para agendar, devolve o `email` de login de cada barbeiro a qualquer cliente e barbeiro.
- **Evidência.** Sondagem PER-12: **3 de 3** itens com e-mail.
- **Reprodução.** Como cliente, `GET /api/v1/barbers/`.
- **Resultado atual.** E-mail presente.
- **Resultado esperado.** Só o admin recebe `email`.
- **Impacto.** Dados pessoais de funcionários expostos; facilita phishing e ataques às contas.
- **Recomendação.** Serializer público sem `email`, escolhido por perfil; teste.

#### SEC-04 — Access token em `localStorage`, sem CSP

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend / Infra | `frontend/src/utils/storage.ts:13`; `config/settings.py:219` | Confirmado | Continua presente |

- **Descrição.** O access token (15 min) fica em `localStorage`, não há CSP, e o comentário do `settings.py` afirma que ele "é mantido apenas em memória". O token traz `nome`, `tipo_perfil`, `barbershop_id` e `hash_password` (derivado do hash da senha).
- **Evidência.** Código; SES-03 (claims); SES-09 (sem `Content-Security-Policy`).
- **Reprodução.** Entrar e executar `localStorage.getItem('barbearia.auth')` no console.
- **Resultado atual.** Token legível por qualquer script da página.
- **Resultado esperado.** Token só em memória, renovado pelo cookie ao recarregar; CSP restritiva.
- **Impacto.** Um XSS futuro (por exemplo, por dependência comprometida) age como o usuário por até 15 minutos.
- **Recomendação.** Manter o access em memória; adicionar CSP no servidor web ou com `django-csp`; corrigir o comentário.

#### SEC-05 — Rate limiting por processo

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Infra / Configuração | `config/settings.py:186-200` (sem `CACHES`) | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.**
  - O throttling usa o cache padrão em memória de cada processo.
  - Com N workers, o limite efetivo vira N vezes maior e zera a cada reinício.
  - Sem `NUM_PROXIES`, atrás de um proxy todos os usuários compartilham o mesmo IP e o limite.
- **Evidência.** `api/rate-limit-gunicorn-3-workers.txt`: 15 logins errados no mesmo minuto e mesmo IP → **10 aceitos (401) e 5 bloqueados (429)**, contra o limite configurado de 5/min. Num único processo, o 6º login recebeu 429.
- **Reprodução.** gunicorn com 3 workers e 15 `POST /auth/login/` com senha errada.
- **Resultado atual.** 10 tentativas aceitas.
- **Resultado esperado.** A partir da 6ª, 429 em qualquer worker.
- **Impacto.** Proteção contra força bruta reduzida em produção.
- **Recomendação.** Cache compartilhado (Redis) e `NUM_PROXIES` conforme a infraestrutura.

#### SEC-07 — Serviço com duração 0 trava a requisição

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Banco | `services/models.py:20`; `appointments/views.py:262-268` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** O model aceita `duracao = 0`; só o serializer exige ≥ 1. Com 0, o laço `while slot_atual <= limite: slot_atual += duracao` não avança.
- **Evidência.** `api/sec07-duracao-zero.txt`: serviço criado pelo ORM (como faria o Django Admin) e `available-slots` **sem resposta em 10 s** (processo encerrado pelo `timeout`, código 124).
- **Reprodução.** Django Admin → serviço com duração 0 → consultar horários desse serviço.
- **Resultado atual.** O worker fica preso com CPU em 100%.
- **Resultado esperado.** O banco recusa duração 0 e o endpoint responde com erro.
- **Impacto.** Negação de serviço com poucas requisições; exige acesso ao Django Admin ou ao banco.
- **Recomendação.** `MinValueValidator(1)` + `CheckConstraint(duracao__gt=0)` com migração; guarda no laço; teste.

#### SEC-09 — Upload de logo sem limite de tamanho

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Infra | `barbershops/models.py:24-26`; `config/settings.py:163`; `.gitignore` | Confirmado | **Novo** |

- **Descrição.**
  - O `ImageField` da logo não tem limite de tamanho nem de dimensões.
  - O processamento usa Pillow 10.4.0, com 69 vulnerabilidades conhecidas (DEP-01).
  - Os arquivos vão para `media/` dentro do projeto, pasta que não está no `.gitignore`.
- **Evidência.**
  - Sondagem complementar UPL-01: PNG de **14,5 MB → 200**, e o arquivo foi gravado.
  - UPL-02: SVG com script → 400, corretamente.
- **Reprodução.** `PATCH /api/v1/barbershops/<id>/` multipart com uma logo grande.
- **Resultado atual.** Aceito.
- **Resultado esperado.** Limite (por exemplo, 2 MB e 1.024 px), com redimensionamento.
- **Impacto.** Consumo de disco e memória; superfície de ataque do Pillow; risco de versionar uploads de usuários.
- **Recomendação.** Validador de tamanho e dimensões; `FILE_UPLOAD_MAX_MEMORY_SIZE` e `DATA_UPLOAD_MAX_MEMORY_SIZE` explícitos; `media/` no `.gitignore`; atualizar o Pillow.

#### DEP-01 — Backend com 91 vulnerabilidades conhecidas; Django fora de suporte

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Dependências | `requirements.txt` | Confirmado | **Novo** |

- **Descrição.** As 91 vulnerabilidades conhecidas estão em 5 pacotes:

  | Pacote | Versão | Avisos | Observação |
  |---|---|---|---|
  | Django | 5.0.14 | 13 | Série 5.0 sem correções de segurança desde abril de 2025 |
  | Pillow | 10.4.0 | 69 | Processa as logos enviadas |
  | djangorestframework | 3.15.2 | 5 | — |
  | PyJWT | 2.14.0 | 2 | — |
  | djangorestframework-simplejwt | 5.3.1 | 2 | — |

- **Evidência.** `dependencias/backend-pip-audit.txt`.
- **Reprodução.** `pip-audit -r requirements.txt`.
- **Resultado atual.** 91 avisos.
- **Resultado esperado.** Versões com suporte e sem avisos conhecidos.
- **Impacto.** Exposição a falhas públicas, especialmente no upload de imagens e nos componentes de autenticação.
- **Recomendação.** Migrar para Django 5.2 LTS e versões atuais de DRF, simplejwt, PyJWT e Pillow, rodando a suíte (327 testes) a cada passo; adicionar `pip-audit` ao CI.

#### DB-01 — Dois bancos de desenvolvimento divergentes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Banco / Configuração | `.env` (`DATABASE_URL` → porta 5432); `docker-compose.yml`; `config/settings.py:127`; `config/test_postgres_settings.py`; `README.md` | Confirmado | **Novo** |

- **Descrição.**
  - O app usa o **PostgreSQL 18 do host** (porta 5432), conforme o `.env`.
  - O `README` ("PostgreSQL via Docker"), o `docker-compose.yml`, o valor padrão do `settings.py` e o `test_postgres_settings.py` apontam para o **container PostgreSQL 16** na porta 5433.
  - O container está **com as migrações `appointments.0007` e `0008` pendentes**, sem a coluna `preco_historico` e com dados diferentes (6 agendamentos, contra 2 no banco do app).
- **Evidência.**
  - `showmigrations` no banco do app: todas aplicadas.
  - Consulta somente leitura no container: a coluna `preco_historico` não existe, e `django_migrations` vai só até `0005`.
  - `banco/integridade-banco-real-somente-leitura.txt`.
- **Reprodução.** Seguir o README (`docker-compose up`) e apontar o `.env` para a porta 5433: as telas de agendamento falham por coluna inexistente até um `migrate`.
- **Resultado atual.** Duas fontes de verdade, com versões e dados diferentes.
- **Resultado esperado.** Um único banco de desenvolvimento, documentado e migrado.
- **Impacto.** Risco concreto na demonstração (subir o banco errado gera erros 500) e confusão sobre "o banco real".
- **Recomendação.** Escolher um banco, alinhar `.env.example`, README e `docker-compose.yml` (inclusive a versão do PostgreSQL) e migrar o outro ou removê-lo do fluxo.

#### DATA-01 — Reverso da migração 0008 apaga e altera preços

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Banco | `appointments/migrations/0008_populate_preco_historico.py:20` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** O reverso executa `Appointment.objects.all().update(preco_historico=None)`. Reaplicar a migração preenche com o preço **atual** do serviço.
- **Evidência.** `banco/data01-reverso-migracao-0008.txt`, numa cópia descartável:
  - desfazer: **419 → 0** preços;
  - depois de o "Corte" subir de R$ 45 para R$ 60, desfazer e refazer muda o faturamento realizado de **R$ 15.215 para R$ 16.565**.
- **Reprodução.** `migrate appointments 0007` e depois `migrate appointments`, num banco **descartável**.
- **Resultado atual.** Dados financeiros perdidos ou alterados.
- **Resultado esperado.** Reverso sem efeito sobre preços gravados pela aplicação.
- **Impacto.** Um rollback operacional corrompe o histórico financeiro.
- **Recomendação.** `migrations.RunPython.noop` como reverso; teste de ida e volta.

#### BUS-08 — Sem "não compareceu" nem desfecho de vencidos

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Produto | `appointments/models.py:28-32` | Confirmado | Continua presente |

- **Descrição.** Só há 4 status. Horários que passaram sem desfecho continuam "agendado" ou "confirmado" para sempre e entram em "a confirmar" (FE-04).
- **Evidência.** Sondagem BUS-08: **22 vencidos como "agendado"** na base de teste; no banco real, 0.
- **Reprodução.** Deixar um horário passar sem alterar o status.
- **Resultado atual.** Continua pendente.
- **Resultado esperado.** Status `nao_compareceu` e separação dos vencidos.
- **Impacto.** Agenda poluída; não há como medir comparecimento.
- **Recomendação.** Novo status com transições a partir de agendado ou confirmado após o horário; indicador de vencidos; testes.

#### BUS-09 — Duração do atendimento não é histórica

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Banco | `appointments/models.py:207,251,314`; `appointments/views.py:250-257` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** Conflitos, horários livres, fim do atendimento e a regra do "realizado" usam a duração **atual** do serviço.
- **Evidência.** Sondagem complementar BUS-09: horários às 10:00 e 10:30 com um serviço de 30 min. Depois de mudar a duração para 60 min, o das 10:00 passa a terminar às 11:00, **sobrepondo** o das 10:30, que continua ativo.
- **Reprodução.** Alterar a duração de um serviço com horários seguidos.
- **Resultado atual.** Sobreposição criada retroativamente.
- **Resultado esperado.** Agendamentos existentes mantêm a duração com que foram marcados.
- **Impacto.** Agenda inconsistente; a promessa "agenda sem conflito" da página institucional deixa de valer.
- **Recomendação.** Campo `duracao_historica`, preenchido como `preco_historico`, com migração de dados e uso em todos os cálculos.

#### BUS-11 — Passo entre horários igual à duração

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/views.py:268` | Confirmado | Continua presente |

- **Descrição.** Os horários livres avançam pela duração do serviço.
- **Evidência.** Sondagem BUS-11: serviço de 60 min → 09:00, 10:00, 11:00…
- **Reprodução.** Consultar `available-slots` para um serviço de 60 min.
- **Resultado atual.** Só horas cheias.
- **Resultado esperado.** Passo configurável, por exemplo 15 min.
- **Impacto.** Encaixes perdidos e menor ocupação.
- **Recomendação.** Passo configurável por barbearia, mantendo a checagem de que o serviço inteiro cabe.

#### BUS-13 — Desativar ou rebaixar barbeiro não trata a agenda

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `barbershops/views.py:160-171,177-195`; `accounts/serializers.py:148-172` | Confirmado | Continua presente |

- **Descrição.** Os horários futuros continuam "agendado" ou "confirmado" com um barbeiro desativado.
- **Evidência.** Sondagem:
  - BUS-13: DELETE do barbeiro → os **20** horários futuros verificados (primeira página da lista) continuam ativos;
  - BUS-13b: rebaixamento a cliente por `/users/` → os **20** verificados continuam ativos.
- **Reprodução.** Desativar um barbeiro com horários futuros e consultar `/appointments/?barbeiro=<id>`.
- **Resultado atual.** Horários órfãos.
- **Resultado esperado.** Decisão explícita (cancelar com aviso ou reatribuir) antes de desativar.
- **Impacto.** Clientes comparecem para atendimento com quem saiu.
- **Recomendação.** Listar os afetados e exigir a decisão; testes.

#### BUS-14 — Admin não agenda pela interface

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend | `frontend/src/App.tsx:55` (rota só para cliente) | Confirmado | Continua presente |

- **Descrição.** A API permite ao admin agendar para um cliente, mas não há tela para isso, nem cliente avulso.
- **Evidência.** Sondagem complementar BUS-14-api: **201**; o painel não tem "Novo agendamento".
- **Reprodução.** Como admin, procurar a ação na interface.
- **Resultado atual.** Inexistente.
- **Resultado esperado.** Agendamento pelo balcão, com busca de cliente.
- **Impacto.** Agendamentos por telefone ou presenciais ficam fora do sistema.
- **Recomendação.** Tela de agendamento do admin reutilizando o fluxo do cliente.

#### API-01 — Sem filtros, busca e `page_size`; telas baixam todo o histórico

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | API + Frontend | `config/pagination.py:4`; `appointments/views.py:34`; `frontend/src/api/endpoints.ts:95-117`; `AdminDashboardPage.tsx:34`; `AdminClientsPage.tsx:40` | Confirmado | Continua presente |

- **Descrição.**
  - A paginação é fixa em 20 itens.
  - `search`, `ordering`, filtro por período e `tipo_perfil` não existem.
  - Painel, Agendamentos e Clientes percorrem todas as páginas de agendamentos, em sequência, e filtram no navegador.
- **Evidência.**
  - Sondagem API-01: `page_size=100` → 20 itens; `search`, `tipo_perfil` e `ordering` sem efeito.
  - Build de produção (`navegador/navegador-testes-dirigidos.json`): **25 requisições por carga, 22 delas para `/appointments/`**, com 419 agendamentos e cerca de 3,2 s locais.
  - O backend é eficiente (2 consultas por página); o gargalo é o número de requisições.
- **Reprodução.** Abrir o painel com o histórico de teste e contar as chamadas.
- **Resultado atual.** Tempo e tráfego crescem linearmente com o histórico.
- **Resultado esperado.** Número fixo de requisições; filtros e agregações no servidor.
- **Impacto.** Com alguns milhares de agendamentos, painel e listas ficam lentos.
- **Recomendação.** `SearchFilter`, `OrderingFilter`, filtros `data_inicio`/`data_fim` e `tipo_perfil`, `page_size_query_param` com máximo, endpoint de métricas para o painel e paginação no servidor.

#### FE-01 — Sem error boundary

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend | `frontend/src/App.tsx`; `frontend/src/components/AppLayout.tsx` | Confirmado (código) | Continua presente |

- **Descrição.** Não há fronteira de erro: uma exceção de renderização desmonta toda a interface.
- **Evidência.** Nenhuma ocorrência de `ErrorBoundary` ou `componentDidCatch` em `frontend/src`.
- **Reprodução.** Forçar uma exceção numa tela em modo de desenvolvimento.
- **Resultado atual.** Página em branco.
- **Resultado esperado.** Mensagem com "Recarregar", com menu e navegação preservados.
- **Impacto.** Um dado inesperado derruba a aplicação inteira.
- **Recomendação.** Error boundary no layout e por rota, com registro do erro (OBS-01).

#### FE-02 — Nenhum teste de frontend

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Frontend / Testes | `frontend/package.json` (sem `test`) | Confirmado | Continua presente |

- **Descrição.** Não há testes unitários, de componente nem de ponta a ponta. A verificação desta auditoria usou scripts externos (`scripts/*.mjs`).
- **Evidência.** Nenhum `*.test.*` ou `*.spec.*`; sem script `test`.
- **Reprodução.** `npm test` não existe.
- **Resultado atual.** Regressões só são percebidas manualmente: a FE-13 passou pela revisão do redesign.
- **Resultado esperado.** Testes dos fluxos críticos no CI.
- **Impacto.** Regressões silenciosas.
- **Recomendação.** Vitest + Testing Library para `format.ts`, `status.ts`, ações de status e agendamento; Playwright para login, agendar, reagendar e cancelar e para as ações do admin. Os scripts desta auditoria servem de ponto de partida.

#### TEST-01 — Regras quebradas sem teste de regressão

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Testes | `*/test*.py` | Confirmado | **Parcialmente resolvido** |

- **Descrição.**
  - **Melhorou:** +88 testes, com regressão para SEC-01, SEC-02, BUS-01 (incluindo concorrência), BUS-02 e BUS-07.
  - **Continua sem teste:** BUS-03, BUS-04, BUS-05, BUS-10, BUS-12, BUS-15, BUS-16, BUS-17, AUTH-02, SEC-03 e a **confirmação da recuperação de senha**, que não tem nenhum teste funcional.
- **Evidência.** Suíte verde (327) com as sondagens falhando nesses pontos; `testes/cobertura-backend.txt` (linhas 427-449 de `accounts/serializers.py` sem cobertura).
- **Reprodução.** Rodar a suíte e depois as requisições das sondagens.
- **Resultado atual.** A suíte passa com as regras quebradas.
- **Resultado esperado.** Cada bug confirmado com um teste que falhe antes da correção.
- **Impacto.** Falsa sensação de segurança; risco de regressão.
- **Recomendação.** Escrever primeiro o teste de cada item corrigido.

#### OBS-01 — Sem logs, monitoramento, trilha de auditoria e health check

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend / Infra | `config/settings.py` (sem `LOGGING`); `config/urls.py` | Confirmado (código) | Continua presente |

- **Descrição.** Faltam:
  - configuração de logging e rastreamento de erros;
  - endpoint de saúde;
  - registro de quem confirmou, cancelou ou alterou um agendamento.
- **Evidência.** Busca em settings e URLs.
- **Reprodução.** Provocar um erro 500 e procurar o registro; consultar um cancelamento e procurar autor e data.
- **Resultado atual.** Inexistentes.
- **Resultado esperado.** Logs estruturados, Sentry ou similar, `/health/` e histórico de status.
- **Impacto.** Erros passam despercebidos; não há como resolver disputas ("quem cancelou?").
- **Recomendação.** `LOGGING`, integração de erros por variável de ambiente, `/health/` e tabela de histórico de agendamento.

#### OPS-01 — Sem infraestrutura de implantação

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Infra | Raiz; `docker-compose.yml`; `config/urls.py:40` | Confirmado | Continua presente |

- **Descrição.** Faltam:
  - Dockerfile e CI;
  - serviço de estáticos e mídia em produção (a mídia só é servida com `DEBUG`);
  - rotina `flushexpiredtokens`;
  - backup documentado.
- **Evidência.** Nenhum Dockerfile, `.github`, Procfile, Makefile, whitenoise ou rotina.
- **Reprodução.** Subir com `DEBUG=False`: o Django Admin fica sem CSS e a mídia retorna 404.
- **Resultado atual.** Implantação manual.
- **Resultado esperado.** Procedimento reproduzível com CI.
- **Impacto.** Erro humano e regressões sem verificação.
- **Recomendação.** Dockerfile multi-stage, CI (testes, lint, `tsc`, build, `pip-audit`, `npm audit`), whitenoise ou nginx, armazenamento de mídia e rotinas.

#### DOC-01 — Documentação da API contradiz o comportamento

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Documentação | `docs/arquitetura/DOCUMENTACAO_API.md:77-99,126,142,399` | Confirmado | Continua presente |

- **Descrição.** O documento diverge do comportamento em vários pontos:

  | Documento diz | Comportamento real |
  |---|---|
  | Access de 60 min | 15 min |
  | Refresh no corpo da requisição | Só em cookie |
  | Logout responde 205 | 204 |
  | `DELETE /users/{id}/` remove o usuário | Desativa a conta |
  | Perfil de barbeiro criado depois, em `POST /barbers/` | Criado junto, em `POST /users/` |
  | Recuperação e relatórios "não implementados" | Existem |

  Também faltam `revenue-report`, `exclude_appointment_id`, `?ativo=all` e o campo `cliente` obrigatório no POST.
- **Evidência.** Comparação com o código e as sondagens.
- **Reprodução.** Seguir o documento para o logout com refresh no corpo.
- **Resultado atual.** A integração pelo documento falha.
- **Resultado esperado.** Documento fiel, de preferência gerado do código.
- **Impacto.** Integrações erradas.
- **Recomendação.** OpenAPI com drf-spectacular, ou revisão contra os testes; trazer as correções da branch `release`.

#### REPO-01 — Virtualenv versionado

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Repositório | `venv312/` | Confirmado | Continua presente |

- **Descrição.** O `venv312/` versionado responde por **4.875 dos 5.112 arquivos** versionados, inclusive binários Linux.
- **Evidência.** `repositorio/repositorio.txt`.
- **Reprodução.** `git ls-files | grep -c '^venv312/'`.
- **Resultado atual.** 4.875.
- **Resultado esperado.** 0.
- **Impacto.** Repositório pesado e não portável.
- **Recomendação.** `git rm -r --cached venv312` num commit dedicado.

#### SA-01 — Sem painel de Super Admin

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Produto | Branch `feature/painel-super-admin` | Confirmado | Continua presente |

- **Descrição.**
  - A operação da plataforma depende do Django Admin.
  - No frontend, o superusuário cai no onboarding de dono.
  - A branch dedicada não tem commits próprios.
- **Evidência.** `git rev-list` (0 commits à frente); superusuário sem barbearia → `/onboarding`.
- **Reprodução.** Entrar como superusuário no frontend.
- **Resultado atual.** Sem tela da plataforma.
- **Resultado esperado.** Listar, suspender e reativar barbearias e ver métricas, com as ações registradas.
- **Impacto.** Suporte e suspensão só por acesso direto aos dados.
- **Recomendação.** Definir o escopo e implementar endpoints restritos ao staff e uma área no frontend.

#### SAAS-01 — Sem notificações, LGPD e cobrança

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Produto | — | Confirmado | Continua presente |

- **Descrição.** Faltam:
  - confirmação e lembrete de agendamento;
  - consentimento, exportação e anonimização de dados (hoje "excluir" só desativa e mantém tudo);
  - planos e cobrança.
- **Evidência.** Ausência de models, endpoints e telas.
- **Reprodução.** —
- **Resultado atual.** Inexistentes.
- **Resultado esperado.** Épicos com requisitos próprios.
- **Impacto.** Impede a comercialização e expõe a riscos legais.
- **Recomendação.** Implementar, nesta ordem: notificações (depende de AUTH-01) → LGPD → planos (depende de SA-01 e BUS-02).

---

### 13.4 Problemas P3 — Baixo (35)

#### FE-13 — "Agendar" após reservar continua mostrando "Horário reservado"

> **Rodada 1 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 18](#18-acompanhamento-das-correções). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/pages/AppointmentCreatePage.tsx:67,106`; `frontend/src/components/AppLayout.tsx:235` | Confirmado | **Novo — regressão do redesign** |

- **Descrição.**
  - O redesign trocou o "toast + ir para Meus agendamentos" pela tela "Horário reservado", guardada no estado `booked`.
  - A rota continua `/appointments/new` e o layout só remonta a tela quando o caminho muda.
  - Por isso, clicar em "Agendar" (aba inferior ou menu) **mantém a confirmação** em vez de abrir um novo agendamento.
- **Evidência.** `navegador/navegador-novo-agendamento-apos-confirmacao.json`:
  - após confirmar: "Horário reservado";
  - após clicar na aba "Agendar": **"Horário reservado"**;
  - só depois de sair e voltar: "Agendar horário".
  - Captura `fe_reagendar_novamente_mantem_confirmacao.png`.
- **Reprodução.** Como cliente, concluir um agendamento e tocar em "Agendar" na barra inferior.
- **Resultado atual.** A mesma tela de confirmação.
- **Resultado esperado.** Um novo fluxo de agendamento.
- **Impacto.** Confunde quem quer marcar outro horário; o contorno é ir a outra tela.
- **Recomendação.** Limpar `booked` quando a navegação ocorrer (por exemplo, usando `location.key` como `key` do layout ou observando a localização), ou navegar para uma rota própria de confirmação.

#### FE-14 — Barbearia desativada e dia da semana ignorados no status "Aberta"

> **Rodada 2 de correções (13/11/2026): Resolvido e verificado.** Detalhes e testes na [seção 19](#19-rodada-2--13112026-fe-14-fe-21-e-fe-22-somente-frontend). A descrição abaixo é a original da auditoria.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/components/AppLayout.tsx:296-310`; `frontend/src/utils/shop.ts:13` | Confirmado | **Novo** |

- **Descrição.** O resumo lateral calcula "Aberta até HH:MM" só pelo horário. Ignora o campo `ativo` da barbearia e o dia da semana. Nenhuma tela usa `barbershop.ativo`.
- **Evidência.** `navegador/navegador-testes-dirigidos.json`: com a barbearia desativada, `adminVeAviso=false` e lateral "**Aberta até 19:00**". Só ao clicar em "Confirmar" aparece o toast do backend (`barbearia_desativada_painel_admin.png`).
- **Reprodução.** Desativar a barbearia pela plataforma e abrir o painel.
- **Resultado atual.** A barbearia aparece "Aberta".
- **Resultado esperado.** Faixa de aviso "Barbearia desativada" e status coerente.
- **Impacto.** O admin descobre a desativação por tentativa e erro.
- **Recomendação.** Ler `ativo` no `BarbershopContext` e exibir um aviso global; incluir os dias de funcionamento quando BUS-06 for resolvido.

#### FE-03 — Falha de recarga sem aviso

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/hooks/useAsyncData.ts`; telas com `error && !data` (por exemplo, `AdminAppointmentsPage.tsx:154`) | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** As telas só mostram erro quando não há dados. Uma recarga que falha com dados na tela não avisa nada.
- **Evidência.** API derrubada e clique em "Atualizar" → nenhum texto novo nem mensagem (`mensagemDeErroVisivel=false`; `fe03_recarga_falhou_sem_aviso.png`).
- **Reprodução.** Abrir "Agendamentos", parar a API e clicar em "Atualizar".
- **Resultado atual.** Dados antigos, sem indicação.
- **Resultado esperado.** "Não foi possível atualizar; mostrando dados de HH:MM".
- **Impacto.** Decisões tomadas com dados desatualizados.
- **Recomendação.** Exibir toast ou faixa quando houver `error` com dados presentes.

#### FE-15 — Requisições sem tempo limite

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/api/client.ts:10-14` | Confirmado | **Novo** |

- **Descrição.** O cliente axios não define `timeout`. Com a API travada, sem cair, as telas ficam carregando indefinidamente.
- **Evidência.** API pausada (`SIGSTOP`): "Atualizar" desabilitado e barra de progresso sem fim (`admin_desktop_recarga_com_api_pausada.png`).
- **Reprodução.** Pausar o processo da API e recarregar uma lista.
- **Resultado atual.** Espera sem limite.
- **Resultado esperado.** Erro após um prazo (por exemplo, 15 s), com "Tentar novamente".
- **Impacto.** Interface aparentemente congelada.
- **Recomendação.** `timeout` no `axios.create` e tratamento de `ECONNABORTED` em `errorMessage`.

#### FE-16 — "1.000" no preço vira R$ 1,00

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/utils/format.ts:171-178`; `AdminServicesPage.tsx:23,88` | Confirmado (função reproduzida isoladamente) | **Novo** |

- **Descrição.** Sem vírgula, o ponto é tratado como separador decimal, então o ponto de milhar brasileiro é lido errado.
- **Evidência.** `"1.250"` → `1.25`; `"1.000"` → `1.00`; `"1.250,00"` → `1250.00`, correto.
- **Reprodução.** Cadastrar um serviço com preço "1.000".
- **Resultado atual.** Gravado como R$ 1,00, sem aviso.
- **Resultado esperado.** R$ 1.000,00, ou um pedido de confirmação quando a entrada for ambígua.
- **Impacto.** Preço errado entra no histórico financeiro. É raro em barbearias, mas silencioso.
- **Recomendação.** Tratar `\d{1,3}(\.\d{3})+` sem vírgula como milhar; mostrar o valor interpretado ao lado do campo.

#### FE-04 — Contador "a confirmar" inclui vencidos

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend / Produto | `frontend/src/components/AppLayout.tsx:316-346` | Confirmado | **Parcialmente resolvido** |

- **Descrição.** O rótulo agora diz "a confirmar no total" ("em todas as datas"), mas a contagem continua incluindo horários que já passaram.
- **Evidência.** Painel com "**40 a confirmar no total**", dos quais 22 vencidos (`admin_desktop_painel_completo.png`, sondagem BUS-08).
- **Reprodução.** Ter horários passados com status "agendado".
- **Resultado atual.** Contados como pendentes.
- **Resultado esperado.** Só futuros; vencidos em indicador separado.
- **Impacto.** Número inflado.
- **Recomendação.** Filtro de data na API (API-01) e status de desfecho (BUS-08).

#### FE-17 — Contratos de API e tipos divergentes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Integração | `frontend/src/types/index.ts:61`; `MyAppointmentsPage.tsx:114`; `frontend/src/api/endpoints.ts:71,114-117`; `appointments/serializers.py:31-36` | Confirmado | **Novo** |

- **Descrição.**
  - O tipo `Appointment.barbeiro_especialidade` não existe na API: é sempre `undefined`, e o trecho que o exibe nunca aparece.
  - `userApi.list({tipo_perfil})` envia um filtro que a API ignora.
  - A API exige `cliente` no POST mesmo quando quem agenda é o próprio cliente, e depois sobrescreve o valor. O contrato não está documentado.
- **Evidência.** CTR-02: POST sem `cliente` → 400 "Este campo é obrigatório"; leitura do serializer e dos tipos.
- **Reprodução.** `POST /appointments/` como cliente sem o campo `cliente`.
- **Resultado atual.** 400; o frontend contorna enviando `user.id`.
- **Resultado esperado.** Tipos gerados a partir do esquema da API; `cliente` opcional e ignorado para clientes.
- **Impacto.** Erros de integração em novos clientes da API; código que nunca executa.
- **Recomendação.** Esquema OpenAPI (DOC-01) com tipos gerados; `cliente` como `required=False` e preenchido em `perform_create`.

#### FE-18 — Textos que prometem o que o sistema não faz

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `AppointmentCreatePage.tsx:248,308` | Confirmado | **Novo** |

- **Descrição.**
  - "O preço e a duração ficam registrados no agendamento": a duração não é registrada (BUS-09).
  - O alerta da etapa de horário sempre começa com "Esse horário não está mais disponível.", mesmo quando o erro é outro (barbearia desativada, barbeiro inativo) e o usuário volta a essa etapa.
- **Evidência.** Leitura do código e a sondagem BUS-09.
- **Reprodução.** Comparar o texto com o comportamento descrito em BUS-09.
- **Resultado atual.** Promessas imprecisas.
- **Resultado esperado.** Textos fiéis ao que o sistema faz.
- **Impacto.** Expectativa errada do usuário.
- **Recomendação.** Ajustar os textos ou corrigir BUS-09; usar o título do alerta só para erros de conflito (`data_hora`).

#### FE-19 — Links de texto pequenos para toque nas telas públicas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend / Acessibilidade | `LoginPage.tsx`, `RegisterPage.tsx`, `PasswordReset*Page.tsx`, `AuthLayout.tsx` | Confirmado | **Novo** |

- **Descrição.** No celular, links como "Criar conta" (73×16 px), "Entrar" (41×16), "Voltar para o login" (120×16), "Esqueci minha senha" e "Conheça o BarberPro" (22 px de altura) ficam abaixo de 24 px de altura. Os contatos clicáveis da página inicial do cliente têm 22 px.
- **Evidência.** `navegador/navegador-resultados.json` (`smallTargets` nas telas públicas e na inicial do cliente). Os botões e controles do app têm todos ≥ 24 px.
- **Reprodução.** Abrir `/login` com 390 px de largura e medir.
- **Resultado atual.** Alvos estreitos.
- **Resultado esperado.** Altura de toque ≥ 24 px (WCAG 2.5.8), de preferência 44 px.
- **Impacto.** Toques errados em telas pequenas. Links dentro de frases têm exceção na norma.
- **Recomendação.** `padding-block` e `display: inline-block` nos links isolados.

#### FE-20 — Filtro de status cortado e busca truncada no celular

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend (visual) | `AdminAppointmentsPage.tsx:117`; `ui.module.css` (controle segmentado) | Confirmado | **Novo** |

- **Descrição.** Com 390 px, o controle segmentado de status corta "Confi…" sem sinal de rolagem horizontal, e o placeholder da busca aparece truncado ("…ou barbei").
- **Evidência.** `admin_celular_admin_appointments.png`.
- **Reprodução.** Abrir Agendamentos (admin) com 390 px.
- **Resultado atual.** O último filtro fica oculto.
- **Resultado esperado.** Indicação de rolagem (degradê ou seta) ou quebra em duas linhas; placeholder curto.
- **Impacto.** Os filtros "Realizado" e "Cancelado" ficam menos visíveis.
- **Recomendação.** Máscara de degradê nas bordas ou `flex-wrap`; placeholder "Buscar".

#### FE-05 — Fuso horário fixo no frontend

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Integração | `frontend/src/utils/format.ts:9` | Confirmado (código) | Continua presente |

- **Descrição.** `SHOP_TZ = 'America/Sao_Paulo'` está fixo no código; o backend usa `TIME_ZONE`.
- **Evidência.** Código.
- **Reprodução.** Alterar `TIME_ZONE` no backend.
- **Resultado atual.** A interface continua no horário de Brasília.
- **Resultado esperado.** Fuso vindo da API, por barbearia.
- **Impacto.** Divergência se a barbearia estiver em outro fuso.
- **Recomendação.** Expor o fuso em `/barbershops/` e usá-lo.

#### FE-06 — Sem página 404

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/App.tsx:65` | Confirmado | Continua presente |

- **Descrição.** Rota inexistente redireciona silenciosamente.
- **Evidência.** `/pagina-que-nao-existe` (deslogado) → `/login`; logado → início do perfil.
- **Reprodução.** Acessar uma URL inválida.
- **Resultado atual.** Redireciona sem aviso.
- **Resultado esperado.** Página "não encontrada".
- **Impacto.** Links quebrados passam despercebidos.
- **Recomendação.** Rota `*` com página 404 na identidade visual.

#### FE-07 — Código morto

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `frontend/src/components/Icons.tsx`; `api/endpoints.ts:90,139-147`; `utils/format.ts:24,132`; `assets/brand/index.ts` | Confirmado | Continua presente (ampliado) |

- **Descrição.** Sem uso:
  - **17 ícones:** Razor, Chair, Minus, Filter, Trash, Settings, Key, Lock, Bell, XCircle, AlertTriangle, TrendingUp, Receipt, Analytics, Star, Badge, Building;
  - **funções:** `getTotalServices`, `getTotalBarbers`, `formatDateTime`, `isPast` e `appointmentApi.revenueReport` (a interface não usa o relatório da API);
  - **logos:** o objeto `logo` importa as variantes "emblema", que entram no build (cerca de 30 kB de SVG) sem uso.
- **Evidência.** Busca de referências.
- **Reprodução.** Buscar cada símbolo em `frontend/src`.
- **Resultado atual.** Código sem uso.
- **Resultado esperado.** Nenhuma exportação sem uso.
- **Impacto.** Ruído e bytes extras.
- **Recomendação.** Remover; adotar `knip` ou `ts-prune`.

#### FE-09 — Sem tela de logo; barbeiro não reagenda

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Frontend | `AdminBarbershopPage.tsx`; `BarberAgendaPage.tsx` | Confirmado | Continua presente |

- **Descrição.** A API aceita a logo e o reagendamento pelo barbeiro, mas as telas não oferecem essas ações.
- **Evidência.** Nenhuma ocorrência de "logo" ou "Reagendar" nessas telas.
- **Reprodução.** Abrir "Dados da barbearia" e "Minha agenda".
- **Resultado atual.** Funcionalidades inacessíveis.
- **Resultado esperado.** Upload com prévia (depois de SEC-09); decisão sobre o reagendamento pelo barbeiro.
- **Impacto.** Funções da API sem uso.
- **Recomendação.** Implementar as telas ou declará-las fora do escopo.

#### FE-11 — Painel e relatório da API calculam o faturamento de formas diferentes

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Integração | `AdminDashboardPage.tsx:47-118`; `appointments/views.py:272-383` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** O painel soma no navegador os últimos **30 dias**, de hoje−29 até hoje. O `revenue-report` usa **31 dias**, de hoje−30 até hoje, e agrupa o dia em UTC.
- **Evidência.** `api/fe11-duas-fontes-de-faturamento.txt`: painel **R$ 14.645** (293 atendimentos) contra API **R$ 15.215** (305): **R$ 570** de diferença.
- **Reprodução.** Comparar o "Faturamento, 30 dias" do painel com `GET /appointments/revenue-report/`.
- **Resultado atual.** Números diferentes para o "mesmo" período.
- **Resultado esperado.** Uma única fonte, com período idêntico.
- **Impacto.** Desconfiança nos números se a API for exposta a outro consumidor.
- **Recomendação.** Endpoint de métricas no backend (no fuso local), consumido pelo painel.

#### API-02 — Relatório agrupa o dia em UTC

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/views.py:351-356` | Confirmado | Continua presente (**agora reproduzido**) |

- **Descrição.** `qs.extra(select={'date': 'DATE(data_hora)'})` agrupa pelo dia em UTC. O filtro do período usa o dia local, então o relatório chega a listar uma data fora do período pedido.
- **Evidência.** Sondagem API-02: relatório com `start=end=2026-11-12` devolve `daily` com **2026-11-13** (o atendimento de 12/11 às 22:30).
- **Reprodução.** Um realizado depois das 21:00 locais; `revenue-report?start=<dia>&end=<dia>`.
- **Resultado atual.** Dia seguinte.
- **Resultado esperado.** Dia local.
- **Impacto.** Faturamento diário deslocado.
- **Recomendação.** `TruncDate('data_hora', tzinfo=ZoneInfo(TIME_ZONE))` com `values().annotate()`, sem `.extra()`; teste noturno.

#### BUS-10 — Horários livres para datas passadas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/views.py:266` | Confirmado | Continua presente |

- **Descrição.** Os horários já passados só são descartados quando a data consultada é hoje.
- **Evidência.** Sondagem BUS-10: ontem → **14 horários**.
- **Reprodução.** `available-slots?data=<ontem>`.
- **Resultado atual.** Lista preenchida.
- **Resultado esperado.** Lista vazia ou 400.
- **Impacto.** Inconsistência da API; o frontend não oferece datas passadas.
- **Recomendação.** Retornar vazio para `data < hoje`; teste.

#### BUS-18 — Validações de cadastro fracas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `barbershops/models.py:20`; `services/models.py:17-23`; `services/serializers.py:13-21`; `appointments/models.py:86` | Confirmado | **Novo** |

- **Descrição.** A API aceita:
  - telefone com qualquer texto;
  - serviços com nome duplicado no mesmo tenant;
  - duração de 100.000 min e preço de 999.999,99;
  - observações de agendamento sem limite de tamanho (o frontend limita a 500).
- **Evidência.** Sondagem complementar: VAL-01, VAL-02 e VAL-03 → **200, 201 e 201**.
- **Reprodução.** As requisições de VAL-01 a VAL-03.
- **Resultado atual.** Dados inválidos aceitos.
- **Resultado esperado.** 400 com mensagens.
- **Impacto.** Dados ruins no cadastro; serviços que nunca cabem na agenda.
- **Recomendação.** Validadores de formato e de faixa; unicidade de nome por barbearia; `max_length` nas observações.

#### BUS-19 — Sem segundo admin nem transferência de titularidade

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend / Produto | `accounts/serializers.py:76-84,235-240`; `accounts/admin_integrity.py` | Confirmado (código) | **Novo** (efeito colateral do BUS-01) |

- **Descrição.**
  - Nenhum endpoint cria um admin ou promove alguém a admin.
  - Com a regra do BUS-01, o único admin não pode ser rebaixado nem desativado.
  - A titularidade só muda pelo Django Admin, com ação do superusuário.
- **Evidência.** `validate_tipo_perfil` recusa `admin` na criação e na edição; testes `test_recuperacao_*` usam o Django Admin.
- **Reprodução.** Tentar criar ou promover um admin pela API → 400.
- **Resultado atual.** Uma barbearia tem sempre um único admin, insubstituível pela aplicação.
- **Resultado esperado.** Convite de coadministrador e transferência auditada.
- **Impacto.** Venda da barbearia, saída do dono ou LGPD exigem suporte manual.
- **Recomendação.** Fluxo de convite de admin com confirmação e registro.

#### SEC-06 — Chave antiga no histórico do git

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Repositório | `core/settings.py` no commit `3f46df2` | Confirmado | Continua presente |

- **Descrição.** Uma `SECRET_KEY` fixa permanece no histórico. O repositório tem remoto no GitHub (`origin`); a visibilidade não foi verificada.
- **Evidência.** `git grep -c` no commit (1 ocorrência; valor não exibido).
- **Reprodução.** `git log --all -- core/settings.py`.
- **Resultado atual.** Chave no histórico.
- **Resultado esperado.** Chave comprovadamente não usada, ou histórico limpo.
- **Impacto.** Nenhum, se a chave nunca foi nem for usada; a chave atual é outra (SEC-01).
- **Recomendação.** Declarar que a chave antiga não é usada; se o repositório for público, avaliar `git filter-repo`.

#### SEC-08 — Sem verificação de e-mail no cadastro

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `accounts/views.py:119-130`; `barbershops/views.py` (`perform_create`) | Confirmado (código) | Continua presente |

- **Descrição.** Qualquer pessoa cria uma conta e uma barbearia sem confirmar o e-mail.
- **Evidência.** Código; sondagem PROD-01 (conta criada e já ativa).
- **Reprodução.** Cadastrar com um e-mail inexistente.
- **Resultado atual.** Entra direto.
- **Resultado esperado.** Confirmação por link antes do onboarding.
- **Impacto.** Tenants de spam; contas inacessíveis por e-mail digitado errado.
- **Recomendação.** Verificação por token (depende de AUTH-01).

#### SEC-10 — Oráculo de existência de IDs

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/serializers.py:82-97`; `appointments/views.py:203-213`; `config/permissions.py` (`IsSelfOrAdmin`) | Confirmado | **Novo** |

> **Atualização de 14/11/2026:** dos três pontos abaixo, os dois primeiros (corpo das requisições e `exclude_appointment_id`) foram corrigidos (seções 22 e 24). O terceiro (403 em vez de 404 em `/users/{id}/`, PER-13) continua presente ([seção 24](#24-correção-do-sec-10-exclude_appointment_id--14112026)).
>
> **Atualização de 14/11/2026, PER-13:** o terceiro ponto foi corrigido na leitura de detalhe (GET e HEAD). Os três pontos estão cobertos, e o SEC-10 está resolvido ([seção 25](#25-correção-do-per-13-e-conclusão-do-sec-10--14112026)). A variante nas escritas virou o SEC-12.

- **Descrição.**
  - Para IDs de outra barbearia, a API responde "Este barbeiro não pertence à sua barbearia"; para IDs inexistentes, "Pk inválido".
  - `exclude_appointment_id` distingue "não pertence" de "não encontrado".
  - Um cliente que consulta outro cliente por id recebe 403, que revela a existência, em vez de 404.
- **Evidência.** Sondagem ISO-22, ISO-23 e PER-13.
- **Reprodução.** POST de agendamento com `barbeiro` de outra barbearia e com um ID inexistente; comparar as mensagens.
- **Resultado atual.** Mensagens distintas.
- **Resultado esperado.** A mesma resposta 400/404 genérica.
- **Impacto.** Permite mapear IDs de outras barbearias. Os dados não vazam: o isolamento continua.
- **Recomendação.** Querysets dos campos relacionados filtrados pelo tenant; 404 para objetos alheios.

#### SEC-11 — Configurações de desenvolvimento inseguras se reaproveitadas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Configuração | `.env` local (`DEBUG=True`, `CORS_ALLOWED_ORIGINS` com `localhost:3000`); `config/settings.py:127`; `config/test_postgres_settings.py:12`; `docker-compose.yml:10` | Confirmado | **Novo** |

- **Descrição.**
  - Com o `.env` atual, rotas inexistentes exibem a página técnica do Django com a lista de URLs.
  - O CORS libera uma origem que não é usada.
  - Usuário e senha padrão de desenvolvimento do banco estão escritos no código e no compose (valores não reproduzidos aqui).
- **Evidência.** Sondagem SES-12 ("Django tried these URL patterns") e SES-08.
- **Reprodução.** `GET /api/v1/rota-inexistente/` com o `.env` atual.
- **Resultado atual.** Página de debug.
- **Resultado esperado.** Em qualquer ambiente acessível por terceiros, `DEBUG=False`, sem credenciais padrão e CORS mínimo.
- **Impacto.** Baixo em uso local; alto se esse `.env` ou essas credenciais forem usados num servidor.
- **Recomendação.** Remover os valores padrão com credenciais (exigir `DATABASE_URL`); revisar `CORS_ALLOWED_ORIGINS`; checklist de implantação.

#### DEP-02 — Frontend com 14 vulnerabilidades conhecidas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Dependências | `frontend/package-lock.json` | Confirmado | **Novo** |

- **Descrição.**
  - São 7 vulnerabilidades altas e 7 moderadas.
  - Em tempo de execução: axios 1.19.0 (12 avisos, a maioria nos adaptadores de Node) e zod 3.25 (consumo de memória).
  - O restante está em ferramentas de build e de desenvolvimento: vite 6.4.3, brace-expansion, js-yaml, source-map-js, minimatch, typescript-eslint.
- **Evidência.** `dependencias/frontend-npm-audit-outdated.txt`.
- **Reprodução.** `npm audit`.
- **Resultado atual.** 14 avisos; correção disponível por `npm audit fix` (o zod exige versão maior).
- **Resultado esperado.** 0 altas.
- **Impacto.** Baixo no navegador; o servidor de desenvolvimento do Vite tem avisos de leitura de arquivos.
- **Recomendação.** `npm audit fix` e atualização de axios e vite; avaliar zod 4 com testes.

#### DATA-02 — Preços históricos antigos estimados

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Banco | `appointments/migrations/0008_populate_preco_historico.py` | Confirmado | Continua presente |

- **Descrição.** Agendamentos anteriores à 0007 receberam o preço vigente na migração, o que a própria migração documenta como estimativa.
- **Evidência.** Cabeçalho da migração.
- **Reprodução.** Ler o arquivo.
- **Resultado atual.** Valores estimados.
- **Resultado esperado.** Limitação declarada nos relatórios.
- **Impacto.** Relatórios antigos podem não refletir o valor cobrado.
- **Recomendação.** Documentar o período afetado.

#### DATA-03 — Divergência de collation

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Banco | Servidor PostgreSQL do host (banco do app) | Confirmado | Continua presente |

- **Descrição.** O banco foi criado com collation 2.43 e o sistema operacional fornece 2.44.
- **Evidência.** Aviso a cada conexão; `banco/integridade-banco-real-somente-leitura.txt`.
- **Reprodução.** Qualquer comando Django contra o banco do app.
- **Resultado atual.** Aviso constante.
- **Resultado esperado.** Sem aviso.
- **Impacto.** Índices de texto, como o `unique` de e-mail, podem ficar inconsistentes em casos raros.
- **Recomendação.** Com backup: `REINDEX DATABASE` e `ALTER DATABASE … REFRESH COLLATION VERSION`.

#### DB-02 — Regras de negócio sem constraints no banco

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Banco | `services/models.py`; `barbershops/models.py`; `appointments/models.py`; `accounts/models.py` | Confirmado | **Novo** |

- **Descrição.** O banco não impede:
  - duração ≤ 0;
  - preço negativo;
  - fechamento ≤ abertura;
  - status fora da lista;
  - e-mail duplicado por maiúsculas;
  - sobreposição de agendamentos do mesmo barbeiro.

  Toda a integridade depende da aplicação, e caminhos fora da API (Django Admin, shell, SQL) a contornam, como mostra o SEC-07.
- **Evidência.** Migrações e models: só PK, FK, `unique(email)` e `OneToOne`.
- **Reprodução.** Inserir um serviço com `duracao=0` pelo ORM (SEC-07).
- **Resultado atual.** Aceito.
- **Resultado esperado.** `CheckConstraint` e `UniqueConstraint(Lower('email'))`; opcionalmente uma constraint de exclusão (`btree_gist`) por barbeiro e intervalo.
- **Impacto.** Dados inválidos possíveis fora da API.
- **Recomendação.** Adicionar as constraints com migração, depois de checar os dados existentes.

#### MAINT-01 — Componentes grandes, estilos inline, duplicação e código morto no backend

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Código | `AppointmentCreatePage.tsx` (508 linhas), `AppLayout.tsx` (424), `AdminDashboardPage.tsx` (397), `ui.module.css` (1.096); `barbershops/views.py:83-135` e `services/views.py:30-75`; `appointments/models.py:370-381`; `config/permissions.py:39` | Confirmado | **Novo** |

- **Descrição.**
  - Componentes com várias responsabilidades.
  - 45 usos de `style={{…}}` e algumas cores literais fora de `design-tokens.css` (por exemplo, `ui.module.css:897-898`).
  - Lógica do filtro `ativo` duplicada entre os ViewSets de barbeiros e serviços.
  - Código morto: `_validar_campos_cliente_nao_autorizados` (método incompleto, nunca chamado) e `IsClientRole` (nunca usada).
  - Comentário com erro de digitação em `appointments/views.py:47`.
- **Evidência.** Contagens e buscas.
- **Reprodução.** —
- **Resultado atual.** Manutenção mais cara.
- **Resultado esperado.** Componentes menores, tokens em vez de literais, filtro compartilhado.
- **Impacto.** Baixo, mas acumulativo.
- **Recomendação.** Extrair os passos do agendamento e as seções do painel; mixin para o filtro `ativo`; remover o código morto.

#### DOC-02 — README com instruções incorretas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Documentação | `README.md` | Confirmado | Continua presente (ampliado) |

- **Descrição.** O README diz que:
  - `python manage.py test` usa SQLite em memória, mas usa o banco do `.env`, criando um banco de teste no servidor;
  - existe um proxy do Vite para a porta 8000, mas `vite.config.ts` não tem proxy;
  - o banco roda "via Docker", mas o app usa o PostgreSQL do host (DB-01).
- **Evidência.** `README.md`; `vite.config.ts`; `config/test_settings.py`.
- **Reprodução.** Seguir o README.
- **Resultado atual.** Instruções divergentes.
- **Resultado esperado.** README fiel ao ambiente.
- **Impacto.** Quem segue o README testa ou executa em outro banco.
- **Recomendação.** Reescrever as seções de execução e testes.

#### DOC-03 — Comentários obsoletos sobre o app `core`

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Documentação | `accounts/models.py:7`; `config/settings.py:72` | Confirmado | Continua presente |

- **Descrição.** Comentários citam o antigo app `core`.
- **Evidência.** Busca.
- **Reprodução.** `grep -n core accounts/models.py config/settings.py`.
- **Resultado atual.** Referências obsoletas.
- **Resultado esperado.** `config.mixins` e a lista atual de apps.
- **Impacto.** Confusão.
- **Recomendação.** Atualizar os comentários.

#### DOC-04 — Índice de `docs/` e comentários desatualizados

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Documentação | `docs/README.md`; `config/settings.py:218-219` | Confirmado | **Novo** |

- **Descrição.**
  - O índice de `docs/` aponta `RELATORIO_ENTREGA_FINAL.md` como documento principal e não cita a auditoria oficial nem as pastas de evidências.
  - O comentário do `settings.py` afirma que o access token é mantido só em memória (SEC-04).
- **Evidência.** Leitura dos arquivos.
- **Reprodução.** —
- **Resultado atual.** Índice e comentário desatualizados.
- **Resultado esperado.** Índice com a auditoria oficial e o histórico; comentário fiel.
- **Impacto.** Avaliadores encontram primeiro um relatório antigo.
- **Recomendação.** Atualizar `docs/README.md` e o comentário.

#### REPO-02 — Arquivos soltos e pastas fora do `.gitignore`

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Repositório | Raiz; `.gitignore` | Confirmado | Continua presente (ampliado) |

- **Descrição.**
  - Continuam na raiz: `gerar_zip.py`, `db.sqlite3`, `test.db` vazio, `outputs/`, `work/`, 21 rascunhos em `docs/auditorias/historico/`.
  - Novos e **fora do `.gitignore`**:
    - `.codex/` (hooks de ferramenta);
    - `.impeccable/`;
    - `references/`, com cópias de HTML de sites de terceiros (direitos autorais);
    - `media/` (uploads) e `staticfiles/`.
- **Evidência.** `repositorio/repositorio.txt`; `.gitignore`.
- **Reprodução.** `git status`.
- **Resultado atual.** Risco de versionar material de terceiros e uploads.
- **Resultado esperado.** Raiz limpa e `.gitignore` cobrindo as ferramentas locais.
- **Impacto.** Repositório confuso e risco legal.
- **Recomendação.** Atualizar o `.gitignore` e mover os rascunhos.

#### REPO-03 — Branches dessincronizadas

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Repositório | Branches | Confirmado | Continua presente |

- **Descrição.**
  - `master` está 31 commits atrás de `desenvolvimento`.
  - `feature/painel-super-admin` está 1 atrás, sem commits próprios.
  - `release/barberpro-academica-v1` tem 1 commit próprio (`67ef6e3`).
- **Evidência.** `git rev-list --count` (`repositorio/repositorio.txt`).
- **Reprodução.** Os mesmos comandos.
- **Resultado atual.** Sem branch de referência clara.
- **Resultado esperado.** Fluxo de branches documentado.
- **Impacto.** Correções presas na `release`.
- **Recomendação.** Definir o fluxo e sincronizar.

#### TEST-02 — Cobertura não medida pelo projeto

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Testes | `requirements.txt` | Confirmado | Continua presente |

- **Descrição.** O projeto não tem `coverage`. Esta auditoria mediu 91% com a ferramenta instalada fora do projeto.
- **Evidência.** `testes/cobertura-backend.txt`.
- **Reprodução.** `coverage run manage.py test` não está disponível no ambiente do projeto.
- **Resultado atual.** Sem medição contínua.
- **Resultado esperado.** Cobertura no CI, com meta.
- **Impacto.** Lacunas como a da confirmação de senha passam despercebidas.
- **Recomendação.** `coverage` como dependência de desenvolvimento, com meta mínima no CI.

#### FE-12 — Banco real quase vazio para a demonstração

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Dados / Apresentação | Banco do app (somente leitura) | Confirmado | Continua presente |

- **Descrição.** O banco do app tem 2 barbearias, 8 usuários, 2 serviços e **2 agendamentos**.
- **Evidência.** `banco/integridade-banco-real-somente-leitura.txt`.
- **Reprodução.** Entrar como admin e abrir o painel.
- **Resultado atual.** Painel, gráficos e quadro do dia quase vazios.
- **Resultado esperado.** Tenant de demonstração com histórico real, manipulável pela aplicação.
- **Impacto.** A demonstração não mostra os indicadores. As capturas desta auditoria mostram como fica com dados.
- **Recomendação.** Comando `seed_demo` idempotente num tenant separado. `scripts/seed.py` serve de base, adaptado para não fixar senhas.

---

## 14. Problemas não verificáveis e limitações

| # | Item | Por que não foi verificado | Risco que permanece | Como verificar |
|---|---|---|---|---|
| NV-1 | Entrega real de e-mail | Não há SMTP configurado; enviar a terceiros está fora do escopo | A recuperação de senha pode falhar mesmo com o SMTP configurado | Backend de console ou Mailpit e solicitar a recuperação |
| NV-3 | Leitor de tela (NVDA, VoiceOver, TalkBack) | Indisponível no ambiente; validados axe-core, teclado e ARIA | Problemas de anúncio e ordem de leitura | Percorrer login, agendamento e painel com leitores reais |
| NV-4 | Chrome, Safari, Edge e aparelhos físicos | Só o Firefox estava disponível; tamanhos simulados | Diferenças de renderização (por exemplo, `inert`, controles de data e hora) | Repetir `scripts/audit.mjs` com Chromium e WebKit e testar em celulares reais |
| NV-6 | Visibilidade do repositório no GitHub | Exigiria consulta autenticada a serviço externo | Se for público, a chave antiga (SEC-06) e a auditoria anterior estão expostas | Conferir no GitHub |
| NV-7 | Carga e desempenho em volume real | Base de teste com 419 agendamentos; sem teste de carga | O crescimento linear (API-01) foi demonstrado, mas o limite prático não foi medido | Popular 10 mil agendamentos e medir o painel |
| NV-8 | Implantação em produção (HTTPS, proxy, `DEBUG=False`) | Não há infraestrutura de produção (OPS-01); só `check --deploy` | Comportamento real de cookies `Secure`, CSP e estáticos | Ambiente de homologação |

Limitações de método:

- Revisão manual de layout feita por amostragem de capturas, em 3 das 5 larguras.
- As métricas automáticas (rolagem, alvos de toque, erros) cobriram todas as 105 combinações.
- As telas do frontend que **não** mudaram desde a auditoria anterior foram lidas por diff e testadas no navegador, mas não relidas linha a linha: Onboarding, Register, PasswordReset, Account.
- NV-2 e NV-5 da auditoria anterior foram resolvidos como verificações nesta (seção 12.2).

---

## 15. Matriz de prioridades

Esforço estimado:

- **baixo:** até meio dia, com teste;
- **médio:** de 1 a 3 dias;
- **alto:** uma semana ou mais, ou decisão de produto.

| Severidade \ Esforço | Baixo | Médio | Alto |
|---|---|---|---|
| **P1** | BUS-15, BUS-03, BUS-04, BUS-05 | AUTH-01 | BUS-06, PROD-01 |
| **P2** | BUS-12, BUS-16, SEC-03, SEC-07, SEC-09, DATA-01, DB-01, FE-01 | BUS-02, BUS-17, AUTH-02, SEC-04, SEC-05, DEP-01, BUS-08, BUS-09, BUS-11, BUS-13, BUS-14, API-01, FE-02, TEST-01, OBS-01, DOC-01, REPO-01 | OPS-01, SA-01, SAAS-01 |
| **P3** | FE-13, FE-14, FE-03, FE-15, FE-16, FE-17, FE-18, FE-19, FE-20, FE-06, FE-07, API-02, BUS-10, SEC-10, SEC-11, DEP-02, DOC-02, DOC-03, DOC-04, REPO-02 | FE-04, FE-05, FE-09, FE-11, BUS-18, BUS-19, DATA-03, DB-02, MAINT-01, REPO-03, TEST-02, FE-12 | SEC-08, SEC-06 (se o histórico precisar ser limpo), DATA-02 (documentar) |

Leitura sugerida:

- **canto superior esquerdo:** P1 de baixo esforço, o maior ganho por hora;
- **diagonal P2 baixo:** riscos operacionais baratos;
- **coluna "alto":** decisões de produto que não cabem antes da apresentação.

---

## 16. Plano recomendado de correção

A ordem é sugestão; a decisão é do dono do projeto. Cada correção deve vir com um teste de regressão escrito antes, que falhe no código atual.

### Fase 0 — Antes da apresentação de 17/11

Alterações pequenas, de baixo risco:

| Ordem | Item | Esforço | Por que agora |
|---|---|---|---|
| 1 | DB-01 | Baixo | Garantir que a demonstração rode no banco migrado (o do `.env`) e alinhar README e compose, ou migrar o container |
| 2 | FE-12 | Baixo | Tenant de demonstração com histórico, para mostrar painel, caixa e quadro do dia |
| 3 | BUS-15 | Baixo | Status inicial sempre "agendado" |
| 4 | BUS-03 | Baixo | Reagendar volta a "agendado" |
| 5 | BUS-05 | Baixo | Validação de fechamento > abertura na API |
| 6 | BUS-04 | Baixo | Revalidar o horário na troca de serviço |
| 7 | FE-13 | Baixo | Reiniciar o fluxo de agendamento (regressão visível) |
| 8 | SEC-03 | Baixo | Ocultar o e-mail dos barbeiros para clientes |
| 9 | BUS-12 | Baixo | Unificar a regra de cancelamento e troca de cliente do barbeiro |
| 10 | TEST-01 (parcial) | Baixo | Testes dos itens 3 a 9 |

Se não houver tempo para BUS-06, **evitar demonstrar domingos** (seção 17).

### Fase 1 — Antes de qualquer uso real

| Tema | Itens |
|---|---|
| Agenda e regras | BUS-16, BUS-17, BUS-10, BUS-02 (suspensão pela plataforma), FE-14 |
| Segurança e dependências | DEP-01 (Django 5.2 LTS, Pillow), DEP-02, SEC-05 (Redis), SEC-07, SEC-09, SEC-04 (CSP), SEC-11, SEC-10 |
| Contas | AUTH-01 (e-mail), AUTH-02 |
| Dados | DATA-01, DB-02, API-02 |
| Desempenho e integração | API-01, FE-11, FE-17, FE-15, FE-03, FE-01 |
| Operação | OBS-01, OPS-01, REPO-01, REPO-02 |
| Qualidade | FE-02, TEST-01 (restante), TEST-02 |
| Documentação | DOC-01, DOC-02, DOC-04 |

### Fase 2 — Produto

PROD-01 (página pública e convite), BUS-06 (grade de funcionamento, folgas e feriados), BUS-08 (não compareceu), BUS-09 (duração histórica), BUS-11 (passo configurável), BUS-13 (agenda ao desativar), BUS-14 (agendamento pelo balcão), BUS-19 (coadministradores), SA-01, SAAS-01, SEC-08, FE-09.

### Fase 3 — Acabamento

FE-04, FE-05, FE-06, FE-07, FE-16, FE-18, FE-19, FE-20, MAINT-01, DATA-02, DATA-03, DOC-03, REPO-03, SEC-06, e os itens não verificados NV-1, NV-3, NV-4, NV-6, NV-7 e NV-8.

---

## 17. Prontidão para a demonstração

### 17.1 Conclusão

**O BarberPro está em condições de ser apresentado como protótipo acadêmico. Não está em condições de uso real nem de produção.**

A favor:

- Nenhum P0. Os dois críticos anteriores foram corrigidos e testados.
- O isolamento entre barbearias resistiu a todas as tentativas.
- As permissões principais dos três perfis valem na API, não só na interface.
- Os fluxos centrais funcionam de ponta a ponta, sem erros de console ou de API, do desktop ao celular de 360 px: login, cadastro de serviços e equipe, agendamento, reagendamento, cancelamento, confirmação, conclusão, painel e caixa.
- O redesign é consistente e acessível nas verificações automáticas.
- 327 testes passam, inclusive concorrência em PostgreSQL.

Contra:

- Sete problemas P1 de regra de negócio e de produto.
- Dependências vulneráveis.
- Ausência de infraestrutura, e-mail, observabilidade e testes de frontend.
- A demonstração depende do banco certo (DB-01) e de dados preparados (FE-12).

### 17.2 Recomendações para o roteiro da apresentação

| Fazer | Evitar (enquanto não corrigido) |
|---|---|
| Rodar no banco do `.env` (migrado) e conferir `showmigrations` antes | Subir o banco do `docker-compose` sem migrar (DB-01) |
| Usar um tenant de demonstração com histórico (FE-12) | Mostrar o painel com o banco atual: 2 agendamentos |
| Demonstrar login dos três perfis, agendamento em dia útil, confirmação pelo barbeiro, conclusão após o término, cancelamento, painel e caixa | Agendar num domingo (BUS-06) |
| Mostrar a recusa de horário ocupado e o isolamento entre barbearias | Reagendar um horário já confirmado (BUS-03) |
| Mostrar a interface no celular | Tocar em "Agendar" logo após reservar (FE-13) |
| Explicar as limitações declaradas: e-mail, cadastro de cliente, dias de funcionamento | Recuperação de senha (AUTH-01) e cadastro público como cliente (PROD-01) |

### 17.3 Respostas objetivas

- **Quantidade total de problemas:** 70 (P0 0, P1 7, P2 28, P3 35).
- **Problemas antigos resolvidos:** 5 resolvidos e verificados, 3 parcialmente.
- **Problemas antigos que continuam presentes:** 45.
- **Regressões:** nenhum problema antigo voltou. O redesign introduziu 1 regressão nova (FE-13).
- **Cinco problemas mais importantes:** BUS-15, BUS-03, BUS-06, BUS-05 e BUS-04 (seção 1).
- **Pode ser apresentado?** Sim, como protótipo acadêmico, com as precauções da tabela acima. Não está pronto para produção.

---

## 18. Acompanhamento das correções

### 18.1 Rodada 1 — 13/11/2026: integridade dos agendamentos

**Escopo autorizado:** BUS-15, BUS-03, BUS-06, BUS-05, BUS-04 e a regressão FE-13. Nenhum outro problema foi tratado. Ficaram fora, por instrução, PROD-01, AUTH-01 e todos os P2 e P3.

**Restrições cumpridas:**
- sem commit, push ou merge, na branch `desenvolvimento`;
- sem alteração de `.env`, `SECRET_KEY`, settings, dependências ou infraestrutura;
- sem migração no banco real;
- alterações já existentes (redesign e backend do dono) preservadas.

Evidências em [`docs/auditoria/evidencias-2026-11-13/rodada-1-correcoes/`](auditoria/evidencias-2026-11-13/rodada-1-correcoes/README.md).

#### Resumo

| ID | Sev. | Situação após a rodada | Prova de falha antes / correção depois |
|---|---|---|---|
| BUS-15 | P1 | ✅ **Resolvido e verificado** | 6 testes falham no código anterior; 14 de 14 passam depois |
| BUS-03 | P1 | ✅ **Resolvido e verificado** | 5 falham antes; 14 de 14 passam depois |
| BUS-06 | P1 | ◐ **Parcialmente resolvido** | 15 falham antes; 16 de 16 passam depois |
| BUS-05 | P1 | ✅ **Resolvido e verificado** | 7 falham antes; 10 de 10 passam depois |
| BUS-04 | P1 | ✅ **Resolvido e verificado** | 5 falham antes; 10 de 10 passam depois |
| FE-13 | P3 | ✅ **Resolvido e verificado** | Reproduzido na auditoria; corrigido e verificado no navegador (B6, B7, B9, B11) |

Os testes que passam nos dois estados (26 no total) protegem os fluxos legítimos que precisavam continuar funcionando: admin e barbeiro registrando horário confirmado, remarcação pelo lado da barbearia, limites exatos de horário, edição de outros campos. Detalhe por teste em `testes/antes-e-depois-por-teste.txt`.

#### BUS-15 — Cliente cria agendamento já "confirmado"

| Campo | Registro |
|---|---|
| Arquivos modificados | `appointments/serializers.py` (`validate`); `appointments/models.py` (`clean`, novo `_validar_status_inicial`) |
| Solução implementada | **Na API:** o cliente só cria horários `agendado`. Mandar outro `status` na criação (JSON ou formulário) responde **403** e não grava nada. **No modelo** (vale também para Django Admin e shell): todo registro novo nasce `agendado` ou `confirmado`, e ninguém cria um agendamento já cancelado (400). Admin e barbeiro continuam podendo registrar um horário já confirmado (por exemplo, agendamento por telefone). "Realizado" na criação continua recusado pela regra do BUS-07 |
| Testes executados | `appointments/test_status_inicial.py` (14): status `confirmado`, `cancelado` e `realizado` pelo cliente; envio por formulário; combinação com outro `cliente`; status inválido sem erro 500; fluxo normal do cliente; entrada na fila "a confirmar"; admin e barbeiro com e sem status; modelo fora da API. Sondagem HTTP `BUS-15/*` (6) |
| Resultado | 14/14 no código corrigido (6 falhavam antes). Sondagem: cliente `confirmado`, `cancelado` e `realizado` → 403; sem status → 201 `agendado`; admin `confirmado` → 201; barbeiro `cancelado` → 400. Na repetição da sondagem da auditoria, NEW-STATUS passou de 201 `confirmado` para 403 |
| Situação | **Resolvido e verificado** |

#### BUS-03 — Reagendamento pelo cliente mantém "confirmado"

| Campo | Registro |
|---|---|
| Arquivos modificados | `appointments/serializers.py` (`validate`, novo `_altera_agenda`); `appointments/models.py` (`_validar_transicao_status`); `frontend/src/pages/AppointmentCreatePage.tsx` (aviso e texto da tela final) |
| Solução implementada | **Regra na API:** quando o **cliente** muda de fato o horário, o barbeiro ou o serviço de um horário `confirmado`, o status volta a `agendado` na mesma gravação e a barbearia precisa confirmar de novo. Mandar `status: confirmado` junto não impede a volta. **No modelo:** `confirmado → agendado` só é aceito quando há remarcação; reabrir sem remarcar continua proibido. **Preservado:** remarcação feita pelo admin ou pelo barbeiro, que já são o lado da barbearia, mantém o status; editar só as observações também. **Na interface:** ao remarcar um horário confirmado, um aviso informa que ele volta a aguardar confirmação, e a tela final diz que o novo horário aguarda a barbearia |
| Testes executados | `appointments/test_remarcacao_status.py` (14): mudança de horário, barbeiro e serviço; status enviado junto; status final junto (403); preço histórico preservado; nova confirmação; só observações; reenvio dos mesmos dados; horário ainda agendado; admin e barbeiro mantendo `confirmado`; reabertura sem remarcar; modelo. Sondagem `BUS-03/*` (3). Navegador B12–B14 |
| Resultado | 14/14 (5 falhavam antes). Sondagem: cliente → `agendado`; só observações → `confirmado`; admin → `confirmado`. No navegador, o horário 401 (confirmado, qua 18/11 15:00) foi remarcado pelo cliente para qui 19/11 09:00 e ficou `agendado`; o aviso e o texto final aparecem |
| Situação | **Resolvido e verificado** |

#### BUS-06 — Domingos e dias fechados recebem agendamentos

| Campo | Registro |
|---|---|
| Arquivos modificados | **Backend:** `barbershops/models.py` (campo `dias_funcionamento`, `clean`, `abre_no_dia`); `barbershops/migrations/0006_barbershop_dias_funcionamento.py` (nova); `barbershops/serializers.py`; `appointments/models.py` (`_validar_horario_funcionamento`); `appointments/views.py` (`available_slots`). **Frontend:** `types/index.ts`, `api/endpoints.ts`, `utils/format.ts` (`isoWeekday`), `utils/shop.ts`, `pages/AdminBarbershopPage.tsx`, `pages/AppointmentCreatePage.tsx`, `pages/HomePage.tsx`, `styles/client.module.css`, `styles/settings.module.css` |
| Solução implementada | **Configuração:** o projeto não tinha nenhuma configuração de dias, então foi criado o mínimo necessário, `Barbershop.dias_funcionamento`: lista de dias ISO, 1 = segunda … 7 = domingo. Ela é validada (pelo menos um dia, valores de 1 a 7, sem repetição) e editável só pelo admin. **Padrão:** todos os dias. Assim nenhuma barbearia existente perde dias, e domingos não são bloqueados de forma indiscriminada: cada barbearia escolhe os seus em "Dados da barbearia". **API:** dia fechado devolve lista de horários vazia, e criação ou remarcação para esse dia recebe 400 ("A barbearia não abre aos domingos"), pelos três perfis. O dia da semana é o do horário local da barbearia, não o de UTC. Fechar um dia **não** trava horários que já estavam marcados nele: confirmar, editar observações e cancelar continuam possíveis. **Interface:** seletor de dias em "Dados da barbearia"; no agendamento, dias fechados aparecem desabilitados com "fechado", e o dia inicial pula para o próximo dia aberto; a tela inicial do cliente mostra os dias ("Segunda a sábado, das 09:00 às 19:00"); o status lateral considera o dia. **Fora, por instrução:** feriados, exceções por data, folgas e disponibilidade por barbeiro |
| Testes executados | `barbershops/test_dias_funcionamento.py` (16): padrão; onboarding; normalização; valores inválidos (vazio, 0, 8, booleano, texto, nulo, decimal); permissão de cliente e barbeiro (403); modelo fora da API; agendamento em dia fechado pelos três perfis; horários vazios; domingo aberto continua aceitando; barbearia que fecha na segunda; remarcação para dia fechado; horário existente num dia que depois fechou; fuso (sábado 22:00 local = domingo em UTC); isolamento entre barbearias. Migração 0006 aplicada, desfeita e reaplicada num banco com 419 agendamentos. Sondagem `BUS-06/*` (11). Navegador A1–A6, B1–B5 |
| Resultado | 16/16 (15 falhavam antes). Sondagem: no padrão, domingo com 20 horários; com o domingo fechado, 0 horários no domingo e 20 no sábado; agendar no domingo → 400 para cliente, admin e barbeiro; cliente e barbeiro não alteram os dias (403). Navegador: domingos desabilitados e rotulados "barbearia fechada"; formulário recusa nenhum dia marcado; sem rolagem horizontal a 390 px; axe sem violações |
| Situação | **Parcialmente resolvido.** Os dias de funcionamento da semana estão resolvidos e verificados. Continuam ausentes feriados, exceções por data, folgas e horário por barbeiro, que a recomendação original incluía. Até o dono desmarcar o domingo, ele continua aberto (padrão "todos os dias"). A parte restante tem impacto menor; sugere-se reavaliá-la como P2 |

#### BUS-05 — Fechamento anterior à abertura é aceito

| Campo | Registro |
|---|---|
| Arquivos modificados | `barbershops/models.py` (`clean`, mensagem `HORARIO_INVALIDO_MENSAGEM`); `barbershops/serializers.py` (`validate`) |
| Solução implementada | **Verificação prévia:** o projeto não suporta horário que atravesse a meia-noite. `Appointment` recusa atendimento que termina em outro dia, e os horários livres vão da abertura ao fechamento do mesmo dia. **Validação:** fechamento ≤ abertura é sempre inválido, na criação (onboarding), na edição completa e no PATCH parcial, que compara com o valor gravado, também no modelo (Django Admin). A mensagem: "O horário de fechamento precisa ser depois do horário de abertura. A agenda não atravessa a meia-noite: abertura e fechamento são do mesmo dia." O frontend já validava; nada mudou nele |
| Testes executados | `barbershops/test_horario_funcionamento.py` (10): antes, igual, PATCH parcial só do fechamento e só da abertura, meia-noite (22:00–02:00 e fechamento 00:00), limite de 1 minuto aceito, edição válida, edição de outros campos, onboarding inválido sem criar barbearia nem promover o usuário, modelo. Sondagem `BUS-05/*` (5). Navegador A3 |
| Resultado | 10/10 (7 falhavam antes). Sondagem: completo, parcial, igual e meia-noite → 400, e o horário gravado permanece 09:00–19:00. Na repetição da sondagem da auditoria, BUS-05 passou de 200/200 para 400/400 |
| Situação | **Resolvido e verificado** |

#### BUS-04 — Troca de serviço ignora o horário de funcionamento

| Campo | Registro |
|---|---|
| Arquivos modificados | `appointments/models.py` (`_validar_horario_funcionamento`) |
| Solução implementada | A validação de horário de funcionamento passa a rodar quando muda o horário **ou o serviço**. O término é calculado com a duração do novo serviço e comparado ao fechamento no fuso local. Terminar exatamente no fechamento continua permitido. O preço histórico só muda numa troca aceita, como antes; numa troca recusada nada é gravado. Mudar só o status ou as observações continua sem revalidar (a duração não histórica é o BUS-09, fora do escopo) |
| Testes executados | `appointments/test_troca_servico_fechamento.py` (10): cenário da auditoria pelos três perfis; horário fora da grade (18:15); limite exato (18:00 + 60 min); troca por serviço de mesma duração; troca de serviço com antecipação do horário; horário enviado em UTC; mudança só de status; modelo. Sondagem `BUS-04/*` (3) |
| Resultado | 10/10 (5 falhavam antes). Sondagem: troca 30 → 60 min às 18:30 → 400 para admin e cliente; às 18:00 → 200. Na repetição da sondagem da auditoria, BUS-04 passou de 200 para 400 |
| Situação | **Resolvido e verificado** |

#### FE-13 — "Agendar" após reservar continua mostrando "Horário reservado"

| Campo | Registro |
|---|---|
| Arquivos modificados | `frontend/src/pages/AppointmentCreatePage.tsx` |
| Solução implementada | A página virou um invólucro que remonta o fluxo a cada navegação (`key={location.key}`). Tocar em "Agendar", na barra inferior ou no menu lateral, estando na tela de horário reservado começa um agendamento novo, sem o estado da reserva anterior. Uma trava (`useRef`) impede que um segundo clique em "Confirmar agendamento" antes da resposta gere outra reserva |
| Testes executados | Navegador, build de produção (`navegador/navegador-rodada1.json`): B6 (1ª reserva), B7 (aba "Agendar" → etapa Serviço), B8 (clique duplo → um único POST, 201), B9 (2ª reserva concluída), B10 (as duas nascem `agendado`), B11 (menu lateral). O projeto não tem infraestrutura de testes de frontend (FE-02, P2, fora do escopo), por isso a verificação é por navegador |
| Resultado | Todas conformes. Antes, a aba mantinha "Horário reservado" (`navegador-novo-agendamento-apos-confirmacao.json` da auditoria) |
| Situação | **Resolvido e verificado** |

#### Verificação geral da rodada

| Verificação | Resultado |
|---|---|
| Suíte completa do backend, SQLite | **391 testes, OK** (9 pulados, exigem PostgreSQL). Eram 327; +64 novos |
| Suíte completa do backend, PostgreSQL 16 descartável | **391 testes, OK**, 0 pulados |
| Testes novos no código anterior | 38 de 64 falham (reproduzem os defeitos) e 26 passam (fluxos legítimos) |
| `makemigrations --check` | Sem alterações pendentes depois da `0006` |
| Migração `0006` | Aditiva, padrão "todos os dias"; aplicada, desfeita e reaplicada sem perda (419 agendamentos) |
| Cobertura dos módulos alterados | 92% (linhas + ramificações); o que ficou de fora são guardas defensivas e código morto anterior |
| Frontend | `tsc` 0 erros, ESLint 0 avisos, build OK (JS inicial 434,7 kB, 138,5 kB gzip) |
| Sondagem HTTP da rodada | 28/28 conforme |
| Sondagem da auditoria repetida (91 verificações) | 66 conforme, contra 62 antes. 4 passaram a conforme (NEW-STATUS, BUS-03, BUS-04, BUS-05) e **nenhuma regrediu**. NEW-STATUS-2 continua marcado só porque o script antigo esperava `agendado` no corpo: agora a API recusa com 400, o comportamento correto. BUS-06 continua com horários no domingo porque o seed está no padrão "todos os dias" |
| Navegador da rodada (três perfis) | 22/22 conforme; 0 erros de console ou de página; 0 respostas ≥ 400; axe sem violações em "Dados da barbearia" e no agendamento (a tela inicial do cliente não passou pelo axe nesta rodada) |
| Varredura completa repetida | 105 cargas (21 rotas × 5 larguras): 0 rolagem horizontal, 0 erros |
| Diff | Só os 15 arquivos listados acima, mais 5 arquivos de teste novos e este documento (`diff/diff-somente-correcoes.patch`) |

#### Ação necessária antes de usar o código corrigido

A rodada criou a migração `barbershops.0006_barbershop_dias_funcionamento`. Ela **não foi aplicada no banco real**, por restrição da tarefa. Antes de rodar o app com este código, é preciso aplicá-la no banco que o `.env` usa:

```bash
python manage.py migrate
```

Sem isso, toda tela que lê a barbearia falha, porque a coluna não existe. A migração só adiciona a coluna, com o padrão "todos os dias", e pode ser desfeita (`migrate barbershops 0005`). O banco do `docker-compose` (DB-01) já estava com outras migrações pendentes.

#### Observações encontradas durante a rodada (não corrigidas, fora do escopo)

| ID | Sev. | Observação |
|---|---|---|
| FE-21 | P3 | No agendamento, o `aria-label` dos dias que não são "hoje", "amanhã" ou "ontem" sai repetido ("Domingo, 15 de novembro, domingo, 15 de novembro"). A comparação entre `relativeDayLabel` e `formatDayLong` diferencia maiúsculas. Defeito anterior à rodada |
| FE-22 | P3 | Na barra inferior do celular, a aba "Barbeiros" fica ativa em "Dados da barbearia": `'/admin/barbershop'.startsWith('/admin/barbers')` é verdadeiro. Defeito anterior à rodada |
| FE-14 | P3 | Para manter a interface coerente com o BUS-06, o status lateral passou a mostrar "Fechada hoje" em dia fechado. Essa parte não tem teste dedicado, e a parte de barbearia desativada continua aberta. **FE-14 continua aberto** |
| TEST-01 | P2 | Os itens desta rodada agora têm testes de regressão. TEST-01 continua **parcialmente resolvido** pelos demais itens (BUS-10, BUS-12, BUS-16, BUS-17, AUTH-02, SEC-03, confirmação de recuperação de senha) |

**Correção de comunicação:** durante a execução foi informado que "48 de 63" testes novos falhavam no código anterior. O número correto era **37 de 63** (leitura errada da saída). Com o teste acrescentado depois, são **38 de 64**.

#### Contagem após a rodada 1

| | Na auditoria | Após a rodada 1 |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 7 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 28 |
| P3 | 35 | 34, mais 2 observações novas (FE-21, FE-22) |
| **Abertos** | **70** | **65 dos 70 originais** (BUS-06 entre eles, parcial), mais 2 observações novas |

---

## 19. Rodada 2 — 13/11/2026: FE-14, FE-21 e FE-22 (somente frontend)

**Escopo autorizado:** FE-14 (indicador de barbearia aberta ou fechada), FE-21 (rótulos acessíveis do calendário) e FE-22 (aba ativa no celular). Nenhum outro item foi tratado.

**Restrições cumpridas:**
- Nenhum arquivo do backend, API, banco, migração, autenticação, `.env` ou configuração foi alterado. Os 93 arquivos `.py` têm o mesmo SHA-256 do início da rodada, e não há migração nova.
- **Dependências:** nenhuma adicionada. O `package-lock.json` é idêntico ao HEAD. O `package.json` ganhou só o script `"test"`. **Justificativa:** o projeto não tinha como rodar testes de frontend (FE-02). Os testes usam o executor nativo do Node 26 (`node --test`, que já remove os tipos do TypeScript), com um gancho de resolução de imports, sem Vitest nem Jest.
- Sem commit, push ou merge. Branch `desenvolvimento`. Alterações já existentes preservadas.
- **Sem redesign.** O aviso de barbearia desativada reaproveita o alerta existente (`ui.alert` / `alertDanger`). Nenhuma cor, fonte ou componente novo, e a faixa de dias do calendário ficou idêntica pixel a pixel.

Evidências em [`docs/auditoria/evidencias-2026-11-13/rodada-2-correcoes/`](auditoria/evidencias-2026-11-13/rodada-2-correcoes/README.md).

#### Resumo

| ID | Situação | Causa técnica |
|---|---|---|
| FE-14 | ✅ **Resolvido e verificado** | O status ignorava `ativo` e, depois de fechar, presumia que a barbearia abria no dia seguinte. A barbearia era carregada uma vez por sessão, então outras sessões ficavam com dados velhos: o calendário do cliente oferecia hoje como dia aberto e a lateral dizia "Aberta" depois de o dono fechar o dia |
| FE-21 | ✅ **Resolvido e verificado** | `relativeDayLabel` devolve a data com inicial maiúscula ("Domingo, 15 de novembro") e `formatDayLong`, com minúscula. A comparação entre os dois diferenciava maiúsculas, falhava e juntava as duas formas |
| FE-22 | ✅ **Resolvido e verificado** | A aba "Barbeiros" usava `path.startsWith('/admin/barbers')`, e `/admin/barbershop` começa com esse texto |

#### FE-14 — Indicador de barbearia aberta ou fechada

| Campo | Registro |
|---|---|
| Arquivos alterados | `frontend/src/utils/shop.ts` (`shopHoursStatus`); `frontend/src/contexts/BarbershopContext.tsx`; `frontend/src/components/AppLayout.tsx` (aviso `ShopInactiveNotice`); `frontend/src/styles/layout.module.css` (espaçamento do aviso) |
| Comportamento esperado (auditoria) | Status coerente com a barbearia desativada e com o dia da semana, e um aviso de barbearia desativada |
| Solução | **1. Status calculado só com dados que já existem** (`ativo`, `dias_funcionamento`, abertura e fechamento), com a mesma função `isOpenOn` que o calendário usa: <br>• "Barbearia desativada"; <br>• "Aberta até 19:00"; <br>• "Fechada, abre às 09:00" (hoje, mais tarde); <br>• "Fechada, abre amanhã às 09:00"; <br>• "Fechada, abre segunda às 09:00", que pula os dias em que ela não abre. <br>Antes, depois do fechamento de sábado, a lateral prometia "abre às 09:00" mesmo com o domingo fechado. <br>**2. Aviso "Barbearia desativada"** no topo de todas as telas, para os três perfis, com a mesma mensagem que a API devolve. <br>**3. Dados atualizados entre sessões:** a barbearia é conferida de novo a cada navegação interna e quando a aba volta a ficar visível. Uma mudança feita pelo dono (dias, horário, desativação) chega à lateral, ao início do cliente, ao calendário e ao aviso sem recarregar. Se nada mudou, o estado não é trocado, e uma falha de rede mantém os dados atuais |
| Testes automatizados | `frontend/tests/shop-status.test.ts`, 13 testes: <br>• dia ISO; <br>• aberta e limites de horário; <br>• antes de abrir; <br>• hoje fechado; <br>• fim de semana fechado; <br>• sábado à noite com domingo fechado; <br>• um dia por semana; <br>• sem configuração de dias; <br>• desativada e reativada; <br>• mudança de configuração; <br>• **teste de coerência com o calendário**: 7 configurações × 14 dias × 7 horários (686 casos), que confere que "aberta" só aparece em dia de funcionamento e dentro do horário, e que o dia prometido é aberto e é o primeiro aberto. <br>No código anterior, 7 dos 13 falham |
| Navegador (build de produção) | Roteiro `scripts/rodada2.mjs`, igual nos dois builds: <br>• **padrão:** status conforme o relógio; <br>• **admin:** fecha hoje em "Dados da barbearia" e a lateral muda **sem recarregar**; <br>• **cliente em outra sessão:** a lateral se atualiza ao navegar pelo menu; o início do cliente mostra o mesmo status; o calendário mostra hoje como fechado; <br>• **API muda os dias em outra sessão:** a lateral do cliente se atualiza quando a aba volta à frente (`hidden` → `visible`); <br>• **barbeiro:** mesmo status; <br>• **desativação pela plataforma:** aviso e "Barbearia desativada" para admin e cliente, inclusive no celular; <br>• **reativação:** o aviso some ao navegar. <br>No build anterior, 8 dessas 11 verificações falham. Por exemplo, a sessão do cliente continuava "Aberta até 19:00", com hoje habilitado no calendário, depois de o dono fechar o dia. No build corrigido, todas conformes |
| Largura | O rótulo mais longo ("Fechada, abre segunda às 09:00") cabe no cartão da lateral: termina em 223 px, com limite em 232 px no desktop e 264 px na gaveta do celular (`navegador/rotulo-mais-longo-lateral.json`) |
| Limitações | <br>• Outra sessão vê a mudança ao navegar ou ao voltar para a aba, não em tempo real: se a pessoa fica parada na mesma tela com a aba à frente, a atualização vem na próxima navegação. Não há consulta periódica. <br>• Cada navegação faz uma requisição a mais (`GET /barbershops/`, 2 consultas SQL), no mesmo padrão do contador "a confirmar". <br>• No celular, o status da lateral fica dentro do menu (gaveta), como antes; o aviso de desativação aparece no topo em todos os tamanhos |
| Situação | **Resolvido e verificado** |

#### FE-21 — Rótulos acessíveis do calendário

| Campo | Registro |
|---|---|
| Arquivos alterados | `frontend/src/utils/format.ts` (nova `dateChipLabel`); `frontend/src/pages/AppointmentCreatePage.tsx` (usa a função) |
| Solução | Uma única função monta o rótulo, e a data aparece uma vez: <br>• "Hoje, sexta-feira, 13 de novembro"; <br>• "Amanhã, sábado, 14 de novembro"; <br>• "Domingo, 15 de novembro"; <br>• dia fechado: "…, barbearia fechada". <br>A semântica não mudou: dias abertos e fechados são botões com `role="radio"`, os fechados ficam `disabled`, e o dia escolhido tem `aria-checked="true"`. A aparência é a mesma: a imagem da faixa de dias tem o mesmo SHA-256 nos dois builds, e os textos visíveis são idênticos |
| Testes automatizados | `frontend/tests/calendar-labels.test.ts`, 6 testes: hoje, amanhã, demais dias, dia fechado, virada de ano, e os 21 dias do agendamento (rótulos únicos, data e dia da semana uma vez só, sufixo de fechado só nos fechados), com e sem dias fechados |
| Navegador | Os 21 rótulos são distintos e cada um tem a data uma única vez; os 3 domingos aparecem desabilitados e terminam em ", barbearia fechada"; há um único dia marcado, e ele é aberto; o axe-core não acusa violações; escolher um dia aberto mostra os horários. No build anterior: "Domingo, 15 de novembro, domingo, 15 de novembro, barbearia fechada" |
| Limitações | Não foi testado com leitor de tela real (NV-3); a verificação foi pelos rótulos expostos e pelo axe-core |
| Situação | **Resolvido e verificado** |

#### FE-22 — Aba ativa incorreta no celular

| Campo | Registro |
|---|---|
| Arquivos alterados | `frontend/src/utils/navigation.ts` (novo: `isSectionPath`, `TAB_ROUTES`, `activeTab`); `frontend/src/components/AppLayout.tsx` (a barra inferior usa o módulo; os ícones ficam mapeados por destino) |
| Solução | A aba ativa compara por **segmento de caminho**: uma seção é a própria rota ou uma subpágina dela (`/admin/barbers` ou `/admin/barbers/...`), não qualquer texto que comece igual. As abas e as regras de cada perfil ficaram num módulo puro e testável; a barra inferior marca no máximo uma aba. Telas sem aba, como "Dados da barbearia" e "Minha conta" do admin, não marcam nenhuma. O menu lateral do desktop (`NavLink`) não mudou |
| Testes automatizados | `frontend/tests/navigation.test.ts`, 26 testes: <br>• seção por segmento (incluindo o caso da auditoria); <br>• todas as rotas autenticadas de `App.tsx` nos três perfis (admin, barbeiro e cliente), com parâmetros de busca e barra final; <br>• no máximo uma aba ativa por rota; <br>• cada aba fica ativa na própria tela |
| Navegador | Celular (390 px) e tablet (820 px): <br>• admin: 8 rotas; <br>• barbeiro: 3 rotas; <br>• cliente: 6 rotas; <br>• tocar em cada aba marca só ela; <br>• desktop: o menu lateral marca o item certo e não há barra inferior. <br>No build anterior, "Dados da barbearia" marcava "Barbeiros" no celular e no tablet |
| Situação | **Resolvido e verificado** |

#### Perfis verificados

| Perfil | O que foi verificado |
|---|---|
| Administrador da plataforma (superusuário) | Comportamento anterior mantido: entra no onboarding (não há painel de plataforma, SA-01). Desativa e reativa a barbearia pela API para o teste do aviso |
| Administrador da barbearia | Abas no celular e no tablet, menu lateral no desktop, mudança de dias com atualização imediata da lateral, aviso de desativação |
| Barbeiro | Abas (Agenda, A confirmar, Conta) e status da lateral coerente com a configuração |
| Cliente | Abas, calendário (rótulos, dias fechados, horários), status no início e na lateral, aviso de desativação no celular |

#### Testes executados nesta rodada

| Tipo | Resultado |
|---|---|
| Typecheck (`tsc`, app e node) | 0 erros |
| Lint (ESLint, `--max-warnings=0`) | 0 erros, 0 avisos |
| Build de produção | OK (JS inicial 436,3 kB, 139,0 kB gzip; antes, 434,7 kB) |
| Testes automatizados de frontend (`npm test`, novos) | **45/45** (13 FE-14, 6 FE-21, 26 FE-22). No código do início da rodada, 7 de 13 do FE-14 falham; os arquivos de FE-21 e FE-22 não carregam, porque a lógica antiga estava embutida nos componentes |
| Suíte do backend (SQLite, sem alteração de backend) | 391 testes, OK (9 pulados, exigem PostgreSQL) |
| Navegador, roteiro da rodada (build anterior × corrigido) | Anterior: 57/68. Corrigido: **68/68**. 11 itens passaram a conformes, nenhum regrediu, 0 erros de console, de página ou de API |
| Reexecução do roteiro da rodada 1 no build corrigido | **22/22**: as correções da rodada 1 continuam funcionando (dias de funcionamento, calendário, FE-13, clique duplo, remarcação), com 0 erros de console, página ou API e axe sem violações |
| Varredura completa da auditoria no build corrigido | **105 cargas** (21 rotas × 5 larguras, de 1440 a 360 px): 0 erros de carga, 0 rolagem horizontal, 0 erros de console, página ou API; os 3 fluxos (cliente no celular, barbeiro no tablet, admin no desktop) concluídos sem erros |

**Verificações manuais:** inspeção visual das capturas (aviso de desativação no desktop e no celular, lateral com o rótulo mais longo, "Dados da barbearia" sem aba marcada, calendário). **Não testados:** leitor de tela real; Chrome e Safari (só Firefox disponível); celular físico.

#### Fora do escopo, apenas registrado

- **`PRODUCT.md`** ainda diz que "não existem dias fechados" e que os horários livres ignoram dias fechados (BUS-06). Isso deixou de ser verdade na rodada 1 para os dias da semana. É documentação, não foi alterada.
- **Leitura de dados por sessão:** a atualização entre sessões resolve a barbearia. Outras listas (por exemplo, serviços e barbeiros no agendamento) continuam carregadas ao abrir cada tela, como antes.

#### Contagem após a rodada 2

| | Após a rodada 1 | Após a rodada 2 |
|---|---|---|
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 28 |
| P3 | 34, mais 2 observações (FE-21, FE-22) | 33 (FE-14 resolvido), sem observações pendentes (FE-21 e FE-22 resolvidos) |
| **Abertos** | 65 dos 70 originais, mais 2 observações | **64 dos 70 originais** |

---

## 20. Auditoria de isolamento multi-tenant — 13/11/2026

**Escopo.** Descobrir se usuários de uma barbearia conseguem acessar, consultar, alterar ou excluir dados de outra. A auditoria cobriu:

- todos os recursos da API;
- os endpoints secundários;
- os filtros;
- o Django Admin;
- a mídia;
- as respostas que não são JSON.

Somente diagnóstico.

**Restrições cumpridas:**

- **Código:** nenhum arquivo de código, configuração, migração ou `.env` foi alterado.
- **Dependências:** nada foi instalado no projeto. A sondagem usa a biblioteca padrão do Python e o `psycopg2` que já está no `venv`.
- **Arquivos criados:** esta seção, a linha 20 do sumário, uma linha no quadro inicial e a pasta de evidências.
- **Bancos:** o banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Todos os testes com escrita rodaram num **PostgreSQL 18.3 descartável** (`127.0.0.1:55432`), com dados fictícios, já apagado.
- **Repositório:** sem commit, push ou merge. Branch `desenvolvimento`, HEAD `051b00a`, árvore limpa no início.

**Contexto.** A migração `barbershops.0006` foi aplicada no banco real em 13/11/2026 às 22:06, depois de um backup validado. O smoke test seguinte passou:

- 391 de 391 testes do backend em PostgreSQL 18.3;
- 45 de 45 testes do frontend;
- 26 de 26 verificações no navegador.

Evidências em [`docs/auditoria/evidencias-2026-11-13/isolamento-multitenant/`](auditoria/evidencias-2026-11-13/isolamento-multitenant/README.md). A matriz completa, com as 217 verificações, está em [`MATRIZ.md`](auditoria/evidencias-2026-11-13/isolamento-multitenant/MATRIZ.md).

### 20.1 Veredito

**O isolamento multi-tenant não pode ser declarado seguro.**

- **A API em JSON isola corretamente.** Foram 203 verificações conformes, que cobrem:
  - leitura, criação, edição e exclusão;
  - IDs de outra barbearia na URL e no corpo;
  - filtros e endpoints secundários;
  - tentativa de trocar o próprio papel ou a barbearia;
  - os três papéis, nos dois sentidos (A → B e B → A).

  A fotografia de todas as linhas das barbearias A e B não mudou.
- **A API navegável do DRF vaza dados.** É a mesma URL respondendo em HTML. Ela expõe nomes de clientes, barbeiros, administradores, serviços e barbearias de **todos os tenants** a qualquer usuário autenticado, inclusive a uma conta criada no cadastro público. Também acontece com `DEBUG=False` (**TEN-01, P0**).
- **Uma conta sem barbearia sonda a agenda de barbeiros de outras barbearias** (TEN-02, P2).
- **Há três problemas menores:**
  - o e-mail de outra barbearia é revelado (TEN-03);
  - o oráculo de IDs também aparece nos filtros (SEC-10, ampliado);
  - a mídia é pública por URL (TEN-04).
- **Afirmação pública.** O `PRODUCT.md` afirma "Dados isolados e seguros" (posicionamento 4). Pelo princípio "Só prometer o que o sistema garante", essa frase não deve ser usada enquanto TEN-01 e TEN-02 estiverem abertos. O `PRODUCT.md` não foi alterado.

### 20.2 Método

| Item | Como |
|---|---|
| Leitura de código | Models, serializers, ViewSets, permissões, `TenantScopedQuerysetMixin`, rotas, admin, managers e settings. Foram cobertas as 21 rotas da API (incluindo a raiz `/api/v1/`) e `/media/`. Não há signals, tarefas assíncronas nem notificações. O único envio de e-mail é síncrono, na recuperação de senha |
| Testes existentes | Cerca de 50 testes de isolamento, pelo nome. Todos verificam respostas JSON; nenhum cobre HTML, `OPTIONS` ou o oráculo dos filtros |
| Barbearias | A ("Navalha Fictícia", origem dos ataques), B ("Outra Fictícia", alvo) e C, criada durante o teste pelo onboarding de uma conta do cadastro público |
| Papéis | Admin, barbeiro e cliente de A; admin, barbeiro e cliente de B, no sentido inverso; conta sem barbearia; admin de C; superusuário; anônimo |
| Ataques | IDs de B na URL e no corpo; filtros apontando para B; endpoints secundários (horários livres, `exclude_appointment_id`, faturamento); criação vinculada a B; edição e exclusão de B; troca do próprio papel e da barbearia; JWT adulterado; logout com cookie alheio; upload; Django Admin; HTML e `OPTIONS` |
| Conferência dos dados | Além do status HTTP, cada tentativa de escrita é conferida na linha-alvo do banco. Também foi calculado o md5 de todas as linhas de B antes e depois dos ataques de A, e de A antes e depois dos ataques de B |
| Confirmação em "produção" | Uma segunda instância com `DEBUG=False` reproduziu o TEN-01 |

**Transparência.**

- **Falsos positivos corrigidos.** A primeira execução completa teve três falsos positivos do próprio roteiro (MT-BA-14, MT-AP-22d e MT-AP-23c). O PATCH respondeu 200 ignorando os campos `barbershop` e `user`, e só o `updated_at` mudou. O roteiro passou a comparar as colunas de tenant.
- **Execuções descartadas.** Duas execuções anteriores foram interrompidas por erros do próprio roteiro: um campo obrigatório faltando e uma variável sobrescrita.
- **Números finais.** Todos os números abaixo vêm da execução final, feita do zero num banco recriado com migrações e seed.

### 20.3 Vulnerabilidades confirmadas

#### TEN-01 — API navegável do DRF expõe dados de todas as barbearias

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| **P0** | Backend | `config/settings.py:171` (sem `DEFAULT_RENDERER_CLASSES`); `appointments/serializers.py:29-37`; `barbershops/serializers.py:54-68`; `appointments/views.py:34` | Confirmado | **Novo** |

> **Atualização de 14/11/2026:** contenção aplicada e verificada na [seção 21](#21-contenção-do-ten-01--14112026). O texto abaixo descreve o estado em 13/11 e foi preservado.
>
> **Atualização de 14/11/2026, correção estrutural:** campos relacionais e filtros limitados à barbearia do usuário. TEN-01 resolvido e verificado na [seção 22](#22-correção-estrutural-do-ten-01--14112026).

- **Descrição.** O DRF ativa o `BrowsableAPIRenderer` por padrão. Quando a requisição pede HTML (`Accept: text/html` ou `?format=api`), a página traz os formulários de criação e edição e o formulário de filtros. Os `<select>` desses formulários são preenchidos com o queryset dos campos relacionados, que é `Model.objects.all()`. O filtro de tenant só existe no `get_queryset()` da view e no `validate()` do serializer, e nenhum dos dois é usado para montar o formulário.
  - **`/appointments/`**, para qualquer papel que pode criar (cliente e conta sem barbearia inclusive):
    - `cliente` lista os clientes de todas as barbearias (o `limit_choices_to` só filtra o papel);
    - `barbeiro` e `servico` listam os de todas as barbearias, inclusive inativos, com o nome da barbearia.
  - **`/barbers/`**, para admins, inclusive o de uma barbearia recém-criada no onboarding: `user` lista **todos os usuários da plataforma**, com o papel. Aparecem até os admins de outras barbearias e o superusuário.
  - **Formulário de filtros (`django-filter`):** repete `barbeiro` e `servico` de todos os tenants.
- **Evidência.**
  - Verificações MT-HT-01 a 05, 07, 08 e 12.
  - Texto exposto, em dados fictícios:
    - `Clara Cliente B (Cliente)`;
    - `Bento Barbeiro B - Barbearia Outra Fictícia`;
    - `Corte B (Barbearia Outra Fictícia)`;
    - `Beatriz Proprietária B (Administrador)`;
    - `Operador Plataforma (Administrador)`.
  - A conta do cadastro público viu 22 registros distintos das barbearias A e B, que aparecem como 37 opções porque o formulário de criação e o de filtros se repetem (MT-HT-07).
  - Também reproduzido com `DEBUG=False` (`resultados/html-debug-false.txt`).
  - O anônimo recebe 401, sem formulários (`resultados/html-anonimo.txt`).
  - O `OPTIONS` em JSON não vaza (MT-HT-13).
- **Reprodução.**
  1. Fazer o cadastro público.
  2. Fazer login.
  3. Pedir `GET /api/v1/appointments/` com `Authorization: Bearer <token>` e `Accept: text/html`.
  4. Ler os `<option>` dos `<select>`.
- **Resultado atual.** IDs, nomes e papéis de usuários de todas as barbearias; barbeiros e serviços acompanhados do nome da barbearia.
- **Resultado esperado.** Nenhum registro de outra barbearia, em qualquer formato de resposta.
- **Impacto.**
  - **É uma quebra do isolamento em leitura.** Qualquer pessoa cria uma conta em segundos e obtém a lista de clientes, barbeiros e donos de todas as barbearias, com até 1.000 registros por campo (limite padrão do DRF).
  - **Expõe dados pessoais.** São clientes de outras empresas, o que é relevante para a LGPD.
  - **Limites.** Não expõe e-mail, telefone nem senha. Não permite escrita: as fotografias de A e B não mudaram (MT-IN-01 e MT-IN-03).
- **Recomendação.**
  1. **Contenção imediata:** `DEFAULT_RENDERER_CLASSES = ['rest_framework.renderers.JSONRenderer']`. O frontend só usa JSON.
  2. **Correção estrutural:**
     - limitar ao tenant do usuário o queryset dos campos relacionados (`cliente`, `barbeiro`, `servico` e `user`);
     - criar um `FilterSet` explícito com o queryset do tenant. Isso também fecha o oráculo do SEC-10.
  3. **Testes de regressão:** pedir HTML como cada papel e verificar que nenhum nome de outra barbearia aparece.

#### TEN-02 — Conta sem barbearia sonda a agenda de outras barbearias

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `appointments/serializers.py:76-97` e `:199`; `appointments/views.py:87-89` | Confirmado | **Novo** |

> **Atualização de 14/11/2026:** com a correção estrutural do TEN-01 ([seção 22](#22-correção-estrutural-do-ten-01--14112026)), a conta sem barbearia não referencia nenhum registro, e o MT-AP-27 deixou de se reproduzir. O TEN-02 não foi tratado como item: as checagens condicionais do `validate()` e o 403 tardio do `perform_create` continuam no código, e o item segue aberto até a etapa própria.
>
> **Atualização de 14/11/2026, correção do TEN-02:** recusa antecipada e `validate()` sem checagens condicionais. TEN-02 resolvido e verificado na [seção 23](#23-correção-do-ten-02--14112026).

- **Descrição.**
  - As checagens de tenant do `AppointmentSerializer.validate()` só rodam quando existe `barbershop_id` (`if barbeiro and barbershop_id and ...`).
  - Para uma conta do cadastro público, sem barbearia, elas são puladas.
  - Em seguida, o `full_clean()` do modelo checa conflito de horário contra a agenda do barbeiro da outra barbearia.
  - O 403 de `perform_create` só viria depois da validação.
- **Evidência.** MT-AP-27 compara duas respostas:
  - **horário ocupado de B:** `400 {"barbershop": ["Este campo não pode ser nulo."], "data_hora": ["Este barbeiro já possui um agendamento neste horário."]}`;
  - **horário livre:** só `{"barbershop": [...]}`.

  Nenhum agendamento é criado (MT-AP-24).
- **Reprodução.** Com uma conta do cadastro público, enviar `POST /api/v1/appointments/` com `barbeiro` e `servico` de B e um `data_hora`. Repetir variando o horário.
- **Resultado esperado.** A mesma recusa genérica, antes de qualquer validação.
- **Impacto.**
  - Revela quando cada barbeiro de outra barbearia está ocupado, o que é informação de negócio.
  - Com os IDs obtidos pelo TEN-01, permite mapear a agenda de qualquer barbearia.
  - Não revela nomes de clientes.
- **Recomendação.**
  - **Na view:** recusar com 403 criação, edição e horários livres de quem não tem barbearia, **antes** da validação.
  - **No serializer:** tratar `barbershop_id` ausente como erro, em vez de pular as checagens.
  - **Teste** de regressão.

#### TEN-03 — E-mail de outra barbearia revelado ao cadastrar ou editar usuários

> **Atualização de 15/11/2026:** investigado na [seção 26](#26-investigação-do-ten-03--15112026). A causa foi confirmada. O alcance inclui também o cadastro público sem efeito colateral, a troca do próprio e-mail por qualquer cliente ou barbeiro e um caminho por erro 500. Uma mensagem genérica não fecha o oráculo. Ficaram registrados o AUTH-04 e o AUTH-05. **Continua aberto**, aguardando a decisão de produto.
>
> **Atualização de 15/11/2026, mitigação D:** o dono manteve o e-mail único em toda a plataforma. Foram implementados limites de tentativas específicos ([seção 27](#27-mitigação-d-do-ten-03-limite-de-tentativas--15112026)). **Continua aberto**, com mitigação parcial: abaixo do limite, o oráculo é o mesmo. A correção definitiva planejada é a C3.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `accounts/models.py:29` (`email` único em toda a plataforma) | Confirmado | **Novo** |

- **Descrição.**
  - O e-mail é único em toda a plataforma, porque é o login.
  - O admin de A que cadastra ou edita um cliente com o e-mail de um cliente de B recebe "usuário com este e-mail já existe".
  - O cadastro público se comporta do mesmo jeito.
- **Evidência.** MT-US-16 e MT-US-27.
- **Impacto.** Confirma que uma pessoa usa o sistema, sem dizer em qual barbearia. Não expõe nenhum dado.
- **Recomendação.** É uma decisão de produto:
  - aceitar, porque é inerente ao login global por e-mail; ou
  - responder com uma mensagem genérica e limitar as tentativas.

#### SEC-10 — Oráculo de existência de IDs (continua presente, ampliado)

> **Atualização de 14/11/2026:** o caminho pelos filtros (MT-FI-01) e um caminho novo, pelo corpo das requisições, foram fechados pela correção estrutural do TEN-01 ([seção 22](#22-correção-estrutural-do-ten-01--14112026)). O `exclude_appointment_id` (MT-AV-02) continua presente.
>
> **Atualização de 14/11/2026, `exclude_appointment_id`:** corrigido; o MT-AV-02 ficou conforme ([seção 24](#24-correção-do-sec-10-exclude_appointment_id--14112026)). Segue aberto o ponto dentro da própria barbearia (PER-13).
>
> **Atualização de 14/11/2026, PER-13:** corrigido; SEC-10 resolvido ([seção 25](#25-correção-do-per-13-e-conclusão-do-sec-10--14112026)).

- **Continua:** o `exclude_appointment_id` distingue "não pertence à sua barbearia" de "não encontrado" (MT-AV-02).
- **Novo caminho, pelo filtro:**
  - o filtro `?barbeiro=` ou `?servico=` de `/appointments/` responde 200, com lista vazia, para um ID de outra barbearia;
  - para um ID inexistente, responde 400 "Faça uma escolha válida" (MT-FI-01);
  - a causa é que o `filterset_fields` gera um `ModelChoiceFilter` com os registros de todas as barbearias.
- **Isolamento preservado:** os dados não vazam, porque as listas continuam vazias (MT-AP-02a a d). A severidade continua P3.
- **Correção:** a recomendação estrutural do TEN-01 (querysets limitados ao tenant) fecha os dois caminhos.

#### TEN-04 — Mídia pública por URL, com o nome original do arquivo

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend / infraestrutura | `barbershops/models.py:68` (`upload_to='barbershops/logos/'`); `config/urls.py:41` | Confirmado | **Novo** |

- **Descrição.**
  - O logo fica em `/media/barbershops/logos/<nome original>` e é servido sem autenticação: em desenvolvimento pelo Django, em produção pelo servidor web.
  - O nome é previsível, por exemplo `logo.png`.
- **Evidência.**
  - Sem token, a resposta é 200 (MT-UP-01).
  - Um nome de arquivo com `../` foi saneado para dentro de `barbershops/logos/` (MT-UP-02).
- **Impacto.** Baixo, porque logos costumam ser públicos. Vira problema se outros documentos forem guardados com o mesmo esquema.
- **Recomendação.**
  - Gerar um nome aleatório (`uuid`) no `upload_to`.
  - Decidir explicitamente que a mídia é pública, ou servi-la por URL assinada.

### 20.4 Matriz

A matriz completa, com as 217 linhas, está em [`MATRIZ.md`](auditoria/evidencias-2026-11-13/isolamento-multitenant/MATRIZ.md). Ela traz, para cada verificação, o ID, o recurso, o papel, a origem e o destino, a operação, os resultados esperado e observado, a evidência reproduzível e a severidade.

**Resumo por área:**

| Área | Verificações | Conformes | Divergentes |
|---|---|---|---|
| Autenticação e sessão | 6 | 6 | 0 |
| Barbearia e configurações | 20 | 20 | 0 |
| Usuários | 45 | 43 | 2 (MT-US-16, MT-US-27) |
| Barbeiros | 25 | 25 | 0 |
| Serviços e preços | 24 | 24 | 0 |
| Agendamentos e histórico | 38 | 37 | 1 (MT-AP-27) |
| Relatórios, buscas e filtros | 5 | 4 | 1 (MT-FI-01) |
| Disponibilidade e horários | 12 | 11 | 1 (MT-AV-02) |
| Dashboards e relatórios | 6 | 6 | 0 |
| Uploads e imagens | 2 | 1 | 1 (MT-UP-01) |
| API navegável (HTML) e metadados | 13 | 5 | 8 (MT-HT-01, MT-HT-02, MT-HT-03, MT-HT-04, MT-HT-05, MT-HT-07, MT-HT-08, MT-HT-12) |
| Django Admin | 5 | 5 | 0 |
| Superusuário (plataforma) | 1 | 1 | 0 |
| Integridade dos dados | 3 | 3 | 0 |
| Sentido inverso (B → A) | 12 | 12 | 0 |
| **Total** | **217** | **203** | **14** |

**Todas as divergências:**

| ID | Problema | Recurso | Papel | Origem → destino | Operação | Esperado | Observado | Evidência reproduzível | Sev. |
|---|---|---|---|---|---|---|---|---|---|
| MT-US-16 | TEN-03 | POST /users/ | admin | A → B | criar usuário com o e-mail de um cliente de B | recusa sem revelar que o e-mail existe em outra barbearia | 400 {"email": ["usuário com este e-mail já existe."]} \| e-mail livre (senha inválida): 400 {"password": ["Certifique-se de que este campo tenha mais de 8 caracteres."]} | POST /api/v1/users/ {email:<e-mail do cliente B>} e comparar com e-mail inexistente | P3 |
| MT-US-27 | TEN-03 | PATCH /users/{id}/ | admin | A → B | dar a um cliente de A o e-mail de um cliente de B | recusa sem revelar a existência do e-mail | 400 {"email": ["usuário com este e-mail já existe."]} | PATCH /api/v1/users/<cliente A>/ {email:<e-mail do cliente B>} | P3 |
| MT-FI-01 | SEC-10 | GET /appointments/?barbeiro=… | admin | A → B | comparar filtro com barbeiro de B e com ID inexistente | mesma resposta (sem oráculo) | B: 200 \| inexistente: 400 {"barbeiro": ["Faça uma escolha válida. Sua escolha não é uma das disponíveis."]} | GET /api/v1/appointments/?barbeiro=<barbeiro B> vs ?barbeiro=999999 | P3 |
| MT-AP-27 | TEN-02 | POST /appointments/ (validação) | sem barbearia | — → B | tentar marcar com o barbeiro de B num horário ocupado e num livre | mesma recusa genérica nos dois (sem revelar a agenda de B) | ocupado: 400 {"barbershop": ["Este campo não pode ser nulo."], "data_hora": ["Este barbeiro já possui um agendamento neste horário."]} \| livre: 400 {"barbershop": ["Este campo não pode ser nulo."]}; criados=0 | POST /api/v1/appointments/ {cliente:<próprio>, barbeiro:<barbeiro B>, servico:<serviço B>, data_hora:<horário ocupado de B>} e o mesmo num horário livre | P2 |
| MT-AV-02 | SEC-10 | GET /appointments/available-slots/?exclude_appointment_id=… | cliente | A → B | excluir agendamento de B da ocupação | 404 igual ao de ID inexistente | B: 404 {"detail": "Agendamento a excluir não pertence à sua barbearia."} \| inexistente: 404 {"detail": "Agendamento a excluir não encontrado."} | GET …available-slots/?…&exclude_appointment_id=<agendamento B> vs 999999 | P3 |
| MT-UP-01 | TEN-04 | GET /media/barbershops/logos/… | anônimo | — → B | baixar o logo de B sem autenticação | documentar: arquivos de mídia são públicos por URL | 200 (/media/barbershops/logos/logo-b.png) | GET /media/barbershops/logos/logo-b.png sem Authorization | P3 |
| MT-HT-01 | TEN-01 | GET /api/v1/appointments/ (Accept: text/html) | cliente | A → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 10 opções de outros tenants {'cliente:B': 1, 'cliente:sem barbearia': 1, 'barbeiro:B': 2, 'servico:B': 6}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Corte B', 'Barba B', 'Inativo B', 'Barbearia Out | GET /api/v1/appointments/ com Authorization: Bearer <token de cliente> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-02 | TEN-01 | GET /api/v1/appointments/ (Accept: text/html) | barbeiro | A → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 10 opções de outros tenants {'cliente:B': 1, 'cliente:sem barbearia': 1, 'barbeiro:B': 2, 'servico:B': 6}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Corte B', 'Barba B', 'Inativo B', 'Barbearia Out | GET /api/v1/appointments/ com Authorization: Bearer <token de barbeiro> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-03 | TEN-01 | GET /api/v1/appointments/ (Accept: text/html) | admin | A → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 10 opções de outros tenants {'cliente:B': 1, 'cliente:sem barbearia': 1, 'barbeiro:B': 2, 'servico:B': 6}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Corte B', 'Barba B', 'Inativo B', 'Barbearia Out | GET /api/v1/appointments/ com Authorization: Bearer <token de admin> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-04 | TEN-01 | GET /api/v1/appointments/422/ (Accept: text/html) | admin | A → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 6 opções de outros tenants {'cliente:B': 1, 'cliente:sem barbearia': 1, 'barbeiro:B': 1, 'servico:B': 3}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Corte B', 'Barba B', 'Inativo B', 'Barbearia Outr | GET /api/v1/appointments/422/ com Authorization: Bearer <token de admin> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-05 | TEN-01 | GET /api/v1/barbers/ (Accept: text/html) | admin | A → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 6 opções de outros tenants {'user:B': 3, 'user:C': 1, 'user:sem barbearia': 2}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Beatriz Proprietária B', 'Operador Plataforma'] | GET /api/v1/barbers/ com Authorization: Bearer <token de admin> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-07 | TEN-01 | GET /api/v1/appointments/ (Accept: text/html) | sem barbearia | — → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 37 opções de outros tenants {'cliente:A': 6, 'cliente:B': 1, 'barbeiro:B': 2, 'barbeiro:A': 10, 'servico:A': 12, 'servico:B': 6}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Corte B', 'Barba B', 'Ina | GET /api/v1/appointments/ com Authorization: Bearer <token de sem barbearia> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-08 | TEN-01 | GET /api/v1/barbers/ (Accept: text/html) | admin (barbearia C, criada no onboarding) | C → todas | abrir a API navegável do DRF | nenhum registro de outra barbearia no HTML | 200; 17 opções de outros tenants {'user:A': 12, 'user:B': 3, 'user:sem barbearia': 2}; nomes de B no HTML=['Clara Cliente B', 'Bento Barbeiro B', 'Beatriz Proprietária B', 'Operador Plataforma'] | GET /api/v1/barbers/ com Authorization: Bearer <token de admin (barbearia C, criada no onboarding)> e Accept: text/html; ler <select>/<option> | P0 |
| MT-HT-12 | TEN-01 | GET /api/v1/appointments/?format=api | cliente | A → todas | mesma página via ?format=api (sem cabeçalho Accept) | nenhum nome de B | 200; nomes de B=['Clara Cliente B', 'Bento Barbeiro B', 'Corte B', 'Barba B', 'Inativo B', 'Barbearia Outra Fictícia'] | GET /api/v1/appointments/?format=api | P0 |

### 20.5 Testes que passaram

| Área | O que ficou comprovado | IDs |
|---|---|---|
| Barbearia e configurações | A, como admin, barbeiro e cliente, não lê, renomeia, substitui (PUT), desativa, muda os dias nem troca o logo de B; o DELETE com a confirmação correta é recusado. O cliente de A não cria outra barbearia para trocar de tenant. `id` de B no corpo e logo apontando para o arquivo de B são recusados. O onboarding cria sempre uma barbearia nova (C), mesmo com `id` de B no corpo, e o admin de C só vê a si mesmo | MT-BS-01 a 16 |
| Usuários | Listas só com A, inclusive com filtros forjados. As contas de B, do superusuário e do cadastro público retornam 404 para os três papéis. PATCH, PUT e DELETE em contas de B são recusados e as contas ficam inalteradas. `barbershop=B` no corpo de um cadastro é ignorado e o usuário nasce em A. Ninguém muda o próprio papel, a barbearia nem `is_staff` ou `is_superuser`; o admin não cria outro admin nem move um cliente para B. O cadastro público ignora `barbershop`, `tipo_perfil=admin` e `is_staff` | MT-US-01 a 29 (exceto 16 e 27), MT-AU-01 |
| Barbeiros | Listas sem B, inclusive com `ativo=all`, `ativo=false` e `barbershop=B`. Leitura, edição, desativação e PUT do barbeiro de B são recusados. Não é possível promover a barbeiro de A o cliente de B, o barbeiro de B, a conta sem barbearia nem o superusuário. `barbershop=B` no corpo é ignorado | MT-BA-01 a 15 |
| Serviços e preços | Listas sem B. Os serviços ativos e inativos de B retornam 404. Preço, PUT, desativação e reativação de B são recusados. `barbershop=B` é ignorado na criação e na edição. A conta sem barbearia não lista nem cria serviços | MT-SV-01 a 11 |
| Agendamentos e histórico | As listas de cada papel batem exatamente com o escopo do banco (admin: a barbearia; barbeiro: a própria agenda; cliente: os próprios horários). Leitura, edição, confirmação, remarcação, PUT e cancelamento (PATCH e DELETE) de B são recusados. Não é possível criar agendamento com barbeiro, serviço ou cliente de B, nem mover um agendamento próprio para B. O cliente não marca horário em nome de outra pessoa. Também na mesma barbearia, cliente e barbeiro não leem nem editam horários de outros clientes ou barbeiros | MT-AP-01 a 26 |
| Disponibilidade | Horários livres com barbeiro ou serviço de B retornam 404 para os três papéis, com a mesma resposta dada a um ID inexistente. Para a conta sem barbearia, 403 | MT-AV-01, 03, 04 |
| API navegável (sem campos relacionados) | As páginas HTML de serviços, usuários, barbearias e do detalhe de um barbeiro não têm `<select>` de outros tenants. O `OPTIONS` em JSON não lista registros | MT-HT-06, 09, 10, 11, 13 |
| Uploads | Um nome de arquivo com `../` é saneado para dentro de `barbershops/logos/` | MT-UP-02 |
| Dashboards e relatórios | O faturamento do admin bate com a soma de A no banco, mesmo com `barbershop=B` na URL, e não traz nomes de B. Filtrar pelo barbeiro de B dá 0. Barbeiro, cliente e conta sem barbearia recebem 403. A contagem do painel bate com o banco | MT-RR-01 a 04 |
| Autenticação e sessão | Logout com o cookie de refresh de B é recusado e nada é revogado. JWT com `user_id` ou `barbershop_id` adulterados dá 401: a autorização vem do banco, não das claims. Todos os endpoints dão 401 sem token. Redefinir a senha de B com token inventado é recusado | MT-AU-02 a 06 |
| Django Admin | Sem sessão, redireciona para o login. Admin, barbeiro e cliente não entram, porque não são staff. O `autocomplete` do admin não aceita o token da API | MT-DA-01 a 05 |
| Integridade | O md5 de todas as linhas de B é idêntico antes e depois de todos os ataques de A. O mesmo vale para A nos ataques de B. A conta do cadastro público ficou inalterada depois das tentativas de promoção | MT-IN-01 a 03 |
| Sentido inverso | Admin, barbeiro e cliente de B não leem, alteram, desativam nem cancelam objetos de A, e não criam agendamento nem barbeiro com dados de A | MT-RV-01 a 12 |

A sondagem da auditoria anterior (ISO-01 a ISO-21) está toda contida nestes testes e continua conforme.

### 20.6 Áreas que não puderam ser testadas ou não existem

| Área | Situação |
|---|---|
| Notificações e operações assíncronas | **Não existem** no código: não há signals, Celery, filas, webhooks nem WhatsApp. O e-mail da recuperação de senha é síncrono e não é entregue (AUTH-01) |
| Redefinição de senha com token válido de outra pessoa | Não testada: obter o token exige receber o e-mail. Só o token inventado foi testado |
| Django Admin com staff que não é superusuário | Não existe esse perfil hoje. O admin não tem escopo por tenant, então um staff com permissões de modelo veria todas as barbearias. Isso é por desenho, mas precisa ser considerado antes de criar contas staff |
| Superusuário | Vê todas as barbearias (MT-SU-01), o que é intencional para o operador da plataforma. Não há "contexto de barbearia" para ele (SA-01) |
| Produção real (nginx, gunicorn, CDN) | Não disponível. O comportamento foi verificado com `runserver`, com `DEBUG=True` e com `DEBUG=False`. A publicação de `/media/` em produção depende do servidor |
| Frontend | Não foi testado separadamente nesta auditoria: ele só consome a API JSON, que foi testada |
| Corridas entre tenants (concorrência) | Não testadas |
| Banco real | Não usado, por restrição |

**Atenção:** o isolamento só poderá ser declarado seguro depois de corrigidos TEN-01 e TEN-02 e de cobertas as linhas acima que se aplicarem ao ambiente de produção.

### 20.7 Causas prováveis

1. **Escopo do tenant aplicado tarde demais.** Os campos relacionados dos serializers (`PrimaryKeyRelatedField`) usam `Model.objects.all()`. O tenant só é imposto depois, no `get_queryset()` e no `validate()`. Isso basta para o JSON, mas não para quem enumera o queryset do campo: o formulário HTML e o filtro.
2. **Renderizador HTML ativo por padrão.** As settings não definem `DEFAULT_RENDERER_CLASSES`, e o `DEBUG` não desliga a API navegável.
3. **Checagens de tenant condicionais.** O `validate()` pula as checagens quando não há barbearia, e a permissão de "ter barbearia" só é verificada em `perform_create`, depois da validação.
4. **Mensagens diferentes conforme a existência do objeto.** Por isso o SEC-10 aparece em vários caminhos.
5. **E-mail único em toda a plataforma**, inerente ao login por e-mail (TEN-03).
6. **Testes só em JSON.** Nenhum teste pede HTML, `OPTIONS` ou compara as respostas de filtros.

### 20.8 Plano de correção priorizado

| Ordem | Item | Sev. | Esforço | Observação |
|---|---|---|---|---|
| 1 | TEN-01, contenção: só `JSONRenderer` em `REST_FRAMEWORK`, com teste que pede HTML como cliente, barbeiro, admin e conta sem barbearia | P0 | Baixo | Uma linha de settings. Fecha o vazamento imediatamente. Recomendado antes da apresentação de 17/11 |
| 2 | TEN-02: recusar antes da validação quem não tem barbearia (criação, edição e horários livres); no `validate()`, tratar `barbershop_id` ausente como erro | P2 | Baixo | Teste: a mesma resposta para horário ocupado e livre |
| 3 | TEN-01, estrutural: campos relacionados (`cliente`, `barbeiro`, `servico`, `user`) com queryset do tenant; `FilterSet` de agendamentos com queryset do tenant | P0 | Médio | Defesa em profundidade, caso o HTML volte a ser ativado. Fecha também o SEC-10 dos filtros (MT-FI-01) |
| 4 | SEC-10: a mesma resposta 404 para `exclude_appointment_id` de outra barbearia e inexistente | P3 | Baixo | — |
| 5 | Suíte de regressão de isolamento: transformar o `iso_probe.py` em testes Django (HTML, `OPTIONS`, filtros, fotografia de B) | — | Médio | Evita que o problema volte |
| 6 | TEN-03 e TEN-04: decisão de produto (aceitar, ou mensagem genérica e limite); nome aleatório no `upload_to` | P3 | Baixo | O TEN-04 gera uma migração (`AlterField`) |

### 20.9 Arquivos que provavelmente precisarão de alteração

| Arquivo | Para quê |
|---|---|
| `config/settings.py` | `DEFAULT_RENDERER_CLASSES` (TEN-01) |
| `config/` (módulo novo, por exemplo `config/fields.py`) | Campo relacionado limitado ao tenant, reutilizável (TEN-01, SEC-10) |
| `appointments/serializers.py` | Campos `cliente`, `barbeiro` e `servico` limitados ao tenant; `barbershop_id` ausente tratado como erro (TEN-01, TEN-02) |
| `barbershops/serializers.py` | Campo `user` do `BarberSerializer` limitado ao tenant (TEN-01) |
| `appointments/views.py` | `filterset_class` limitado ao tenant; permissão "precisa ter barbearia" antes da validação; mensagem única do `exclude_appointment_id` (TEN-01, TEN-02, SEC-10) |
| `appointments/filters.py` (novo) | `FilterSet` de agendamentos (SEC-10, TEN-01) |
| `barbershops/models.py` e uma migração nova | `upload_to` com nome aleatório (TEN-04) |
| `accounts/serializers.py` | Mensagem de e-mail, se a decisão for ocultar (TEN-03) |
| Testes: `appointments/test_multitenant_isolation.py`, `accounts/test_multitenant_isolation.py` e um teste novo da API navegável (por exemplo `config/test_renderers.py`) | Regressão de TEN-01, TEN-02 e SEC-10 |

### 20.10 Fora do escopo, apenas registrado

Duas observações do smoke test pós-migração. Ficam registradas aqui para não se perderem, mas **não entram na contagem**:

- **ENV-01 (P3).** O banco real tem a migração `token_blacklist.0013` aplicada (em 09/11), mas o `venv` do projeto, com simplejwt 5.3.1, não tem esse arquivo. Ela veio de um Python 3.14 com simplejwt 5.5.1 instalado no `~/.local` do usuário. A migração só altera metadados (`AlterModelOptions`), e o esquema do banco real é idêntico ao gerado pelas migrações do código. O risco é haver dois ambientes Python com versões diferentes de bibliotecas.
- **DB-02 (P3).** O banco real avisa que a versão de ordenação gravada (collation 2.43) não confere com a do sistema (2.44). Índices de texto, como o e-mail único, podem precisar ser reconstruídos numa etapa autorizada, com backup.

### 20.11 Contagem após a auditoria de isolamento

| | Após a rodada 2 | Após a auditoria de isolamento |
|---|---|---|
| P0 | 0 | **1** (TEN-01) |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 29 (+TEN-02) |
| P3 | 33 | 35 (+TEN-03, +TEN-04; SEC-10 ampliado, já contado) |
| **Abertos** | 64 dos 70 originais | **64 dos 70 originais + 4 novos = 68** |

---

## 21. Contenção do TEN-01 — 14/11/2026

> **Atualização:** a correção estrutural foi feita na sequência, na [seção 22](#22-correção-estrutural-do-ten-01--14112026). Com ela, o TEN-01 passou a resolvido e verificado. Esta seção registra o estado após a contenção e foi preservada.

**Escopo autorizado:** somente a contenção emergencial do TEN-01, que é a exposição de dados pela API navegável do DRF. Ficaram de fora, por instrução, TEN-02, TEN-03, TEN-04, SEC-10 e a correção estrutural do TEN-01 (item 3 do plano da seção 20.8).

**Restrições cumpridas:**

- **Código:** uma chave nova em `config/settings.py` e um arquivo de teste novo, `config/test_renderers.py`. Serializers, models, views, permissões, regras de negócio, frontend e dependências não foram alterados. Não há migração nova (`makemigrations --check`: "No changes detected"). O `.env` não foi alterado.
- **Bancos:** o banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Os testes com escrita rodaram em SQLite em memória e num **PostgreSQL 18.3 descartável**, criado com `initdb` no diretório temporário da sessão e acessível só por TCP em `127.0.0.1:55432`, com dados fictícios.
- **Repositório:** sem commit, push ou merge. Branch `desenvolvimento`. As alterações locais anteriores foram preservadas: a seção 20 deste relatório e a pasta de evidências do isolamento.
- **Segredos:** nenhum arquivo de evidência contém senha, token, `SECRET_KEY` ou string de conexão.

Evidências em [`docs/auditoria/evidencias-2026-11-14/ten-01-contencao/`](auditoria/evidencias-2026-11-14/ten-01-contencao/README.md).

### 21.1 Resumo

| ID | Situação | O que mudou |
|---|---|---|
| TEN-01 | 🟡 **Contido e verificado; correção estrutural pendente** | Nenhuma rota da API entrega mais HTML. A exposição deixou de ser reproduzível nas 21 rotas da API, com 9 papéis, as 5 formas de pedir HTML, o `Accept` de navegador e `DEBUG` True ou False. As 8 verificações do TEN-01 na matriz passaram a conformes, e nenhuma outra mudou. A causa de fundo continua no código: os campos relacionados e os filtros enumeram registros de todas as barbearias (seção 21.7) |

### 21.2 Causa

Três fatores juntos:

1. **Renderizador HTML ativo por padrão.** Sem `DEFAULT_RENDERER_CLASSES`, o DRF usa `JSONRenderer` e `BrowsableAPIRenderer`. O `DEBUG` não muda isso. A negociação de conteúdo escolhe o HTML quando o pedido traz:
   - `Accept: text/html`, inclusive o `Accept` padrão dos navegadores, que prefere `text/html`;
   - `?format=api`;
   - o sufixo `.api`, que o `DefaultRouter` registra para todas as rotas, como `/api/v1/appointments.api`.
2. **Formulários montados com querysets globais.** A página HTML traz os formulários de criação e edição e o formulário de filtros do `django-filter`. Os `<select>` desses formulários listam o queryset do campo relacionado, e esse queryset é `Model.objects.all()`:
   - `cliente`, `barbeiro` e `servico` no `AppointmentSerializer`;
   - `user` no `BarberSerializer`;
   - `barbeiro` e `servico` no `filterset_fields` de agendamentos.

   O escopo do tenant só existe no `get_queryset()` das views e no `validate()` dos serializers, e nenhum dos dois é usado para montar os formulários.
3. **Os formulários aparecem também em respostas de erro.** A sondagem desta etapa mostrou que uma página 404, de um objeto de outra barbearia, também desenhava os formulários. Por exemplo, o admin de B, ao abrir o detalhe de um barbeiro de A, recebia 404 com um `<select>` de todos os usuários da plataforma.

### 21.3 Contenção implementada

`config/settings.py`, dentro de `REST_FRAMEWORK` (linhas 178 a 187):

```python
    # Somente JSON (TEN-01). Sem esta chave, o DRF também ativa a API
    # navegável (BrowsableAPIRenderer), que responde em HTML a
    # "Accept: text/html", "?format=api" ou ao sufixo ".api". [...]
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
```

**Por que dessa forma:**

- **Global e sem depender do `DEBUG`.** O `.env` local usa `DEBUG=True`. Uma regra condicionada ao `DEBUG` deixaria o ambiente de desenvolvimento exposto e reabriria o problema num deploy mal configurado.
- **Nenhuma view reativa o HTML.** Nenhuma view nem `@action` define `renderer_classes`. Isso foi conferido por busca no código e por um teste que percorre as 41 rotas do DRF (13 classes de view).
- **Parsers inalterados.** Continuam JSON, formulário e multipart, então o upload do logo segue funcionando.
- **O frontend negocia JSON como antes.** O axios envia `Accept: application/json, text/plain, */*`.

**Comportamento efetivo, medido e não presumido.** A sondagem HTTP rodou nas quatro instâncias, com 1.926 pedidos em cada uma:

| Pedido | Antes | Depois |
|---|---|---|
| `Accept: text/html` ou `text/html,application/xhtml+xml` | HTML com os formulários: 200, 401, 403, 404, 405 ou 500 | **406**, JSON `{"detail": …}` |
| `?format=api`, com ou sem `Accept: text/html` | HTML | **404**, JSON `{"detail": …}` |
| Sufixo `.api` (`/appointments.api`, `/users/me.api`…) | HTML, ou 500 nas `@action` (API-03) | **404**, JSON `{"detail": …}` |
| `Accept` de navegador (`text/html,…,*/*;q=0.8`) | HTML | JSON, com o mesmo status de antes |
| JSON: `Accept: application/json`, `Accept` do axios, sem `Accept`, `?format=json` e sufixo `.json` | JSON | JSON, com status idênticos nos 855 pedidos |
| `OPTIONS` | `renders: ["application/json", "text/html"]` | `renders: ["application/json"]` |

- **Corpo das respostas.** Nos 882 pedidos de HTML, o corpo é só `{"detail": …}`.
- **O anônimo também recebe 406 ou 404, e não 401.** O DRF negocia o formato antes de autenticar.
- **`DEBUG` não muda nada.** `DEBUG=True` e `DEBUG=False` deram os mesmos status, content-types e formatos, antes e depois.

### 21.4 Testes de regressão

O arquivo `config/test_renderers.py` tem 10 testes e cerca de 2.200 subtestes.

**Cenário:**

- barbearias A e B, com barbeiro e serviço inativos em B;
- superusuário;
- uma conta criada pelo cadastro público, pela própria API;
- uma barbearia C criada no onboarding, também pela API.

Todos os papéis entram com **JWT real**, emitido pelo endpoint de login. Os nomes fictícios de cada grupo servem de marca para detectar vazamento.

| Teste | O que comprova | Código anterior | Corrigido |
|---|---|---|---|
| `test_pedidos_de_html_nao_recebem_html_nem_dados` (`DEBUG=False`) e `…_com_debug` (`DEBUG=True`) | **21 rotas × 7 papéis** (anônimo, cliente, barbeiro e admin de A, conta sem barbearia, admin de C e superusuário) × **5 formas de pedir HTML** (686 casos por modo). Confere que a resposta não é `text/html`, não contém `<`, traz só `detail` e não tem nome, e-mail ou papel de nenhum grupo. Fixa o status observado: 406 ou 404 | 666 falhas e 20 erros em cada modo | ✅ |
| `test_casos_reproduzidos_na_auditoria` | MT-HT-01 a 05, 07, 08 e 12, um a um, sem `<select>`, `<option>` nem nomes | 8 falhas | ✅ |
| `test_options_continua_em_json_e_so_anuncia_json` | `OPTIONS` em JSON, `renders` só com JSON, sem nomes | 6 falhas | ✅ |
| `test_nenhuma_view_registrada_reativa_renderizador_html` | Configuração efetiva igual a `[JSONRenderer]`. Percorre as 41 rotas do DRF, inclusive os `initkwargs` das `@action`, e confere que todas usam só `JSONRenderer`. **Protege contra uma reativação futura em uma view** | 1 falha | ✅ |
| `test_json_mantem_status_e_isolamento_de_cada_papel` | 812 casos. Mantém o status de antes para cada rota e papel nas formas JSON (`Accept` JSON, do axios, de navegador, sem `Accept`, `?format=json`, `.json`) e confere que não há dados de outro grupo | 146 falhas e 1 erro (o `Accept` de navegador recebia HTML) | ✅ |
| `test_listas_json_trazem_os_dados_do_proprio_tenant` | As listas JSON não estão vazias e trazem exatamente os registros do próprio tenant | ✅ | ✅ |
| `test_fluxo_do_frontend_com_axios_continua_funcionando` | Fluxo com os cabeçalhos do axios: login, cookie de refresh, `/users/me/`, refresh, horários livres, criação (201), erro de validação em JSON (400), cancelamento e logout (204) | ✅ | ✅ |
| `test_escritas_do_admin_e_do_barbeiro_continuam_em_json` | PATCH de serviço (admin), confirmação de horário (barbeiro) e faturamento (admin) | ✅ | ✅ |
| `test_token_invalido_continua_recusado` | Token inválido recebe 401 em JSON | ✅ | ✅ |

- **Código anterior.** É uma cópia do backend idêntica ao projeto, exceto pelo `settings.py`, que é o do HEAD. Resultado: **1.493 falhas e 41 erros**. Os 4 testes de fluxo legítimo passam nas duas versões.
- **Código corrigido.** **10 de 10.**
- **Os 41 erros** são 500s da própria API navegável: o sufixo `.api` em `@action` (API-03) e o HTML pedido pelo anônimo no detalhe de um agendamento (AUTH-03).

### 21.5 Evidências e testes executados

| Verificação | Resultado |
|---|---|
| Testes novos, SQLite | Código anterior: 1.493 falhas e 41 erros. Corrigido: **10/10** |
| Suíte completa do backend, SQLite (`config.test_settings`) | **401 testes, OK** (9 pulados, que exigem PostgreSQL). Eram 391, mais os 10 novos |
| Suíte completa, PostgreSQL 18.3 descartável | **401 testes, OK**, 0 pulados |
| Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings | **401 testes, OK** |
| Testes do TEN-01 com o executor em `--debug-mode` (`DEBUG=True`) | **10/10** |
| Sondagem HTTP do TEN-01 (`runserver` real; anterior e corrigido × `DEBUG` True e False; 21 rotas × 9 papéis × 11 formas de pedido; 1.926 pedidos por instância) | **Anterior:** 1.071 respostas HTML, 114 com dados de outro tenant, 26 erros 500 (iguais com `DEBUG` True e False). **Corrigido:** 0 HTML, 0 com dados de outro tenant, 0 erros 500. JSON: 855 de 855 pedidos com o mesmo status antes e depois. `Accept` de navegador: 188 de 189 iguais; o restante passou de 500 (AUTH-03, em HTML) para 401 em JSON |
| As 217 verificações da auditoria de isolamento (`iso_probe.py`, sem alteração) no código corrigido | De 203 para **211 conformes**. Só as 8 do TEN-01 mudaram (MT-HT-01 a 05, 07, 08 e 12); nenhuma regrediu. As 6 divergentes que continuam são TEN-02, TEN-03 (duas), SEC-10 (duas) e TEN-04, todas fora do escopo |
| Navegador: build de produção, Firefox 160 headless, API só-JSON | 3 perfis (cliente, barbeiro e admin), login e 16 páginas com carga completa (o que refaz a sessão pelo cookie de refresh). **291 respostas da API, todas 200 e em JSON**; 0 respostas 406; 0 erros de API ou de console; 10 de 10 textos esperados; nenhum nome de B nas telas de A |
| Frontend | `npm test`: **45/45**; `tsc` (app e node): 0 erros; ESLint (`--max-warnings=0`): 0; build de produção OK (JS inicial 436,3 kB, 139,0 kB gzip, igual ao da rodada 2). Nenhum arquivo do frontend foi alterado |
| Django | `check`: sem problemas. `makemigrations --check --dry-run`: "No changes detected". `check --deploy` com `DEBUG=False`: só o W021 (HSTS preload, opcional), como na auditoria |

**Alcance do vazamento antes da contenção.** A sondagem desta etapa foi mais ampla que a matriz da seção 20 e confirmou três pontos:

- **Sentido inverso.** O vazamento ocorria também de B para A. O cliente e o admin de B viam clientes, barbeiros e serviços de A nos formulários de `/appointments/`.
- **Páginas 404.** As páginas de detalhe de objetos de outra barbearia também traziam os formulários:
  - o admin de B e o admin de C viam **todos os usuários da plataforma** no `<select name="user">` do detalhe de um barbeiro de A;
  - o cliente de B, a conta sem barbearia e o admin de C viam os `<select>` completos no detalhe de um agendamento de A.
- **Tamanho.** Foram 19 combinações de rota e papel com dados de outro tenant, com até 44 `<option>` de outras barbearias numa única página (admin de C em `/appointments/`).

Todas essas combinações deixaram de expor dados.

### 21.6 Perfis verificados

| Perfil | Onde |
|---|---|
| Anônimo | Testes, sondagem |
| Cliente, barbeiro e admin da barbearia A | Testes, sondagem, navegador |
| Cliente e admin da barbearia B (sentido inverso) | Sondagem |
| Conta do cadastro público, sem barbearia | Testes, sondagem |
| Admin de uma barbearia criada no onboarding (C) | Testes, sondagem |
| Superusuário (operador da plataforma) | Testes, sondagem |

### 21.7 Limitações e o que continua aberto

1. **Isto é uma contenção, não a correção estrutural.**
   - **O que continua no código:** os campos relacionados (`cliente`, `barbeiro`, `servico` e `user`) e os filtros de `/appointments/` continuam com querysets de todas as barbearias.
   - **Quando o vazamento volta:**
     - se um renderizador HTML for reativado nas settings, numa view ou numa `@action`. O teste `test_nenhuma_view_registrada_reativa_renderizador_html` falha nesse caso;
     - se algum componente novo enumerar esses querysets, como um formulário HTML, uma classe de metadados que liste `choices` de campos relacionados ou uma tela que desenhe o formulário do `django-filter`.
   - **O que fica pendente:** a correção estrutural, item 3 do plano da seção 20.8. Ela também fecha o oráculo do SEC-10 nos filtros (MT-FI-01), que continua presente.
2. **Os demais itens do isolamento não foram tocados.** TEN-02 (P2), TEN-03, TEN-04 e SEC-10 (P3) seguem divergentes na repetição das 217 verificações. O isolamento ainda **não** pode ser declarado seguro (seção 20.6), e o "Dados isolados e seguros" do `PRODUCT.md` continua sem respaldo.
3. **A API navegável deixou de existir também em desenvolvimento.** É intencional. Para inspecionar a API, use JSON: `curl`, as ferramentas do navegador ou o próprio frontend.
4. **Ainda existem páginas HTML fora do DRF.** O Django continua respondendo em HTML em três casos, mas nenhum deles monta querysets de tenant:
   - o Django Admin, só para staff, conforme MT-DA-01 a 05;
   - o 404 de URLs que não existem;
   - a página de erro 500.

   Com `DEBUG=True`, o 404 técnico lista as rotas e o 500 mostra o traceback. Por isso o `DEBUG=True` nunca pode ir para produção (SEC-11).
5. **Clientes que pedem só HTML recebem 406.** Quem envia `Accept: text/html` sem `*/*` recebe 406, e quem envia `?format=api` recebe 404. Nenhum consumidor legítimo faz isso: o frontend usa o axios, e os navegadores incluem `*/*`.
6. **Não testados:**
   - a pilha de produção (nginx, gunicorn, CDN);
   - o banco real, por restrição;
   - Chrome e Safari, porque só o Firefox está disponível;
   - outros clientes da API, que não existem hoje além do frontend.

### 21.8 Fora do escopo, apenas registrado

Dois defeitos **já existentes**, encontrados pelos testes desta etapa. Não foram corrigidos e se comportam igual antes e depois da contenção.

#### API-03 — Sufixo `.json` nas `@action` responde 500

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `accounts/views.py:254` (`me`); `appointments/views.py:134` (`available_slots`) e `:279` (`revenue_report`) | Confirmado | **Novo** |

- **Descrição.** O `DefaultRouter` registra rotas com sufixo de formato também para as `@action`: `/users/me.json`, `/appointments/available-slots.json` e `/appointments/revenue-report.json`. Os três métodos não aceitam o argumento `format` e quebram com `TypeError: … got an unexpected keyword argument 'format'`.
- **Resultado.** Um usuário autenticado recebe 500. Com `DEBUG=False`, é a página genérica "Server Error (500)", sem dados. O anônimo recebe 401 antes.
- **Antes da contenção.** O sufixo `.api` também levava a esse 500. Agora a negociação devolve 404 antes de chamar o método.
- **Impacto.** Baixo. O frontend não usa sufixos, e não há exposição de dados. Mas qualquer usuário consegue provocar erros 500.
- **Recomendação.** Aceitar `*args, **kwargs` nos três métodos, ou desligar os sufixos (`include_format_suffixes = False` no router), com teste de regressão.

#### AUTH-03 — Escrita anônima em `/appointments/{id}/` responde 500 em vez de 401

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `appointments/views.py:41` e `:49` (`get_permissions`) | Confirmado | **Novo** |

- **Descrição.** Para `update`, `partial_update` e `destroy`, o `get_permissions()` lê `request.user.is_cliente` antes de qualquer checagem de autenticação. O `AnonymousUser` não tem esse atributo, e o resultado é um `AttributeError`.
- **Resultado.** PUT, PATCH e DELETE sem token recebem 500 (com `DEBUG=False`, a página genérica). Nada é alterado no banco.
- **Antes da contenção.** O mesmo erro aparecia ao pedir o HTML do detalhe de um agendamento sem token.
- **Por que a auditoria não pegou.** A auditoria testou o anônimo só com GET (MT-AU-04 e 05).
- **Impacto.** Baixo. Não expõe dados nem permite escrita, mas gera 500 sob demanda e polui os logs.
- **Recomendação.** Checar a autenticação antes, por exemplo com `getattr(user, 'is_cliente', False)` ou devolvendo `[IsAuthenticated()]` para o anônimo, com teste de regressão.

### 21.9 Contagem após a contenção

| | Após a auditoria de isolamento | Após a contenção do TEN-01 |
|---|---|---|
| P0 | **1** (TEN-01) | 1, **contido**: TEN-01 sem exposição reproduzível. Continua aberto até a correção estrutural; a reclassificação fica para o dono decidir depois dela |
| P1 | 3 (BUS-06 parcial, PROD-01, AUTH-01) | 3 |
| P2 | 29 | 29 |
| P3 | 35 | 37 (+API-03, +AUTH-03) |
| **Abertos** | 64 dos 70 originais + 4 novos = 68 | **64 dos 70 originais + 6 novos = 70**, com o TEN-01 contido |

**Próximo passo sugerido, não iniciado:** a ordem fica com o dono. Pelo plano da seção 20.8, os candidatos são o item 2 (TEN-02) e o item 3 (TEN-01 estrutural, que também fecha o SEC-10 dos filtros).

---

## 22. Correção estrutural do TEN-01 — 14/11/2026

> **Atualização:** o TEN-02, que aqui aparece como "sintoma não reproduzível; item aberto", foi corrigido na sequência, na [seção 23](#23-correção-do-ten-02--14112026). Esta seção foi preservada.

**Escopo autorizado:**

- **Corrigido nesta etapa:**
  - a causa raiz do TEN-01: campos relacionais, querysets, filtros e validações que permitiam selecionar ou referenciar registros de outra barbearia;
  - os oráculos do SEC-10 que fazem parte da mesma implementação.
- **Fora do escopo, por instrução:**
  - o TEN-02, que não foi iniciado;
  - o `exclude_appointment_id` (SEC-10), que fica para a próxima etapa;
  - o TEN-03 e o TEN-04.

**Restrições cumpridas:**

- **Código:**
  - **Alterado:** `config/tenancy.py` (novo), `appointments/filters.py` (novo), `appointments/serializers.py`, `barbershops/serializers.py` e `appointments/views.py`.
  - **Testes:** um arquivo de teste novo e três testes existentes atualizados (seção 22.4).
  - **Intacto:** models, permissões, `settings.py`, `.env`, frontend e dependências não foram alterados.
- **Migrações:** nenhuma. Nenhum model mudou, e o `makemigrations --check` responde "No changes detected".
- **Contenção mantida.** O `DEFAULT_RENDERER_CLASSES` continua só com `JSONRenderer`, e o `BrowsableAPIRenderer` não foi reativado no projeto. Ele só foi religado em duas instâncias de laboratório, por um módulo de settings descartável fora do projeto, para medir o que os formulários HTML listariam (seção 22.5).
- **Bancos:** o banco real (`barbershop_db`) e o PostgreSQL do Docker (porta 5433) não foram usados. Os testes com escrita rodaram em SQLite em memória e num **PostgreSQL 18.3 descartável** (`initdb` no diretório temporário, só TCP em `127.0.0.1:55432`), já apagado.
- **Repositório:** sem commit, push ou merge. As alterações locais anteriores foram preservadas: as seções 20 e 21 e as duas pastas de evidências.

Evidências em [`docs/auditoria/evidencias-2026-11-14/ten-01-estrutural/`](auditoria/evidencias-2026-11-14/ten-01-estrutural/README.md).

### 22.1 Resumo

| ID | Situação | Base |
|---|---|---|
| TEN-01 | ✅ **Resolvido e verificado** no ambiente de testes | Contenção ativa. Os 4 campos relacionais graváveis e os 2 filtros relacionais da API passaram a ter escopo de tenant, e testes estruturais impedem que um novo campo ou filtro escape disso. No laboratório, com a API navegável religada, as páginas com dados de outra barbearia caíram de 114 para 0 |
| SEC-10 | ◐ **Parcialmente resolvido** | Fechados o filtro (MT-FI-01) e um caminho novo, o corpo das requisições: 288 de 288 pedidos davam resposta diferente da de um ID inexistente, e agora nenhum dá. Continua o `exclude_appointment_id` (MT-AV-02) |
| TEN-02 | Sintoma não reproduzível; **item aberto** | A conta sem barbearia não referencia mais nenhum registro, e o MT-AP-27 ficou conforme. As correções próprias do TEN-02 não foram feitas (seção 22.8) |
| BUS-20 | Novo, P3, apenas registrado | Seção 22.8 |

### 22.2 Causa raiz encontrada

A inspeção do código atual confirmou estas superfícies:

| Superfície | Antes | Situação |
|---|---|---|
| `AppointmentSerializer.cliente` | Gerado pelo `ModelSerializer` com `User.objects.filter(tipo_perfil='cliente')`: os clientes de **todas** as barbearias | Corrigido |
| `AppointmentSerializer.barbeiro` e `.servico` | `Barber.objects` e `Service.objects`, todas as barbearias, inclusive inativos | Corrigido |
| `BarberSerializer.user` (criação) | `User.objects`: **todos os usuários da plataforma**, inclusive admins, superusuário e contas sem barbearia | Corrigido |
| Filtros `barbeiro` e `servico` de `/appointments/` (`filterset_fields`) | `ModelChoiceFilter` com `Barber.objects` e `Service.objects`, todas as barbearias | Corrigido |
| `barbershop` (agendamentos, barbeiros, serviços, usuários); `UserSerializer`, `UserCreateSerializer`, `BarbershopSerializer`, `ServiceSerializer` | Somente leitura, ou sem campo relacional gravável | Já estava correto |
| `available-slots` (`barbeiro`, `servico`) e `revenue-report` (`barbeiro`) | Consultas já filtradas pela barbearia do usuário: o ID de outra barbearia recebe a mesma resposta de um inexistente | Já estava correto; agora há teste |
| `available-slots` (`exclude_appointment_id`) | Busca global e mensagem diferente (SEC-10) | Fora do escopo |

**Causa raiz.** O `ModelSerializer` e o `django-filter` geram os campos relacionais a partir do model, com o manager padrão, ou seja, todas as barbearias. O escopo do tenant só era aplicado depois, no `get_queryset()` da view, no `validate()` do serializer e no `clean()` do model. Isso tinha quatro consequências:

1. **Vazamento em formulários.** Qualquer formulário montado a partir desses campos, como o da API navegável, listava as outras barbearias. Era o TEN-01 original.
2. **Oráculo de existência pelo corpo da requisição.** Para um ID de outra barbearia, a resposta era "Este barbeiro não pertence à sua barbearia."; para um inexistente, "objeto não existe". No cadastro de barbeiro, a mensagem chegava a revelar o **papel** do usuário na outra barbearia: "Usuários administradores não podem ser convertidos em barbeiros.".
3. **Oráculo pelos filtros.** O ID de outra barbearia recebia 200 com lista vazia, e o inexistente, 400 (MT-FI-01).
4. **Leitura do registro alheio.** O registro de outra barbearia era lido do banco antes da recusa. Para a conta sem barbearia, o `validate()` pulava as checagens de tenant, e a validação de conflito de horário rodava contra a agenda da outra barbearia (MT-AP-27).

### 22.3 Estratégia de isolamento implementada

**`config/tenancy.py` (novo):**

- **`barbearia_do_pedido(request, instancia=None)`.** Decide de quais barbearias o pedido pode referenciar registros. O escopo vem sempre do usuário autenticado, nunca de IDs enviados no corpo ou na URL:

  | Quem | Escopo |
  |---|---|
  | Anônimo, ou sem requisição no contexto | Nenhum registro (falha fechado) |
  | Usuário comum | A própria barbearia |
  | Usuário sem barbearia (por exemplo, cadastro público) | **Nenhum registro.** A falta de contexto não amplia o acesso |
  | Superusuário (exceção explícita, decidida por `is_superuser`, como no `TenantScopedQuerysetMixin`) | Ao editar, a barbearia do registro, que a view já autorizou. Ao criar, a própria barbearia, se houver; senão, todas. A criação sem contexto continua barrada pelas views |

- **`limitar_a_barbearia(queryset, escopo)`** aplica o escopo na própria consulta.
- **`campo_de_tenant(model)`** falha fechado (`ImproperlyConfigured`) para um model sem barbearia.
- **`TenantScopedPrimaryKeyRelatedField`** é o `PrimaryKeyRelatedField` com o queryset limitado. Ele exige um queryset quando é gravável, porque o DRF dispensa essa checagem em subclasses.

**Onde foi aplicado:**

- **`AppointmentSerializer` e `BarberSerializer`** recebem `serializer_related_field = TenantScopedPrimaryKeyRelatedField`. Os campos continuam gerados pelo model, com o mesmo rótulo, os mesmos validadores (o `UniqueValidator` de `Barber.user`) e o mesmo `limit_choices_to` (o perfil de cliente). Só ganham o escopo.
- **`appointments/filters.py` (novo)** define o `AppointmentFilter`, com os filtros `status`, `barbeiro` e `servico`. Os querysets de `barbeiro` e `servico` são calculados a cada pedido pela mesma regra. O `AppointmentViewSet` passou de `filterset_fields` para `filterset_class`.
- **As checagens que já existiam continuam,** como defesa em profundidade: `get_queryset()`, `validate()`, `clean()` e `perform_create`.

**Efeito:**

- um ID de outra barbearia recebe **exatamente a mesma resposta** de um ID inexistente;
- o registro alheio **nunca é lido**, porque a condição de barbearia está na mesma consulta SQL;
- formulários e opções só listam o próprio tenant;
- a conta sem barbearia não referencia nada.

### 22.4 Testes adicionados e atualizados

**`config/test_isolamento_tenant.py` (novo, 22 testes).** O cenário tem:

- as barbearias A e B, cada uma com admin, dois clientes, dois barbeiros ativos, um barbeiro inativo, um serviço ativo, um serviço inativo e um agendamento;
- uma conta sem barbearia e o superusuário;
- nos testes de cadastro e onboarding, contas criadas pela API, com login JWT real.

| Classe | O que comprova |
|---|---|
| `EscopoEstruturalTests` | **Varredura de todos os serializers do projeto:** os campos relacionais graváveis são exatamente 4, e todos têm escopo de tenant. **Varredura de todas as rotas:** os filtros relacionais são exatamente 2, e os dois têm escopo. Também confere as opções de cada campo e as do formulário de filtros, por papel, nas duas barbearias: sem barbearia, nada; anônimo ou sem requisição, nada; superusuário editando um registro de B, só B |
| `ReferenciasCruzadasTests` | IDs de outra barbearia (ativos e inativos) em `cliente`, `barbeiro` e `servico`, no POST, PATCH e PUT de agendamentos; e em `user`, no POST de barbeiros: cliente, admin e barbeiro da outra barbearia, conta sem barbearia e superusuário. Cobre os três papéis, **A → B e B → A**. Para cada caso confere: <br>• 400; <br>• resposta idêntica à de um ID inexistente; <br>• nenhum nome da outra barbearia; <br>• **nenhuma consulta SQL que leia o registro alheio sem condição de barbearia**; <br>• nada criado nem alterado; <br>• fotografia da outra barbearia inalterada; <br>• nenhum vínculo entre barbearias. <br>`barbershop` no corpo continua ignorado |
| `FiltrosDeAgendamentoTests` | Os filtros `barbeiro` e `servico` com IDs da outra barbearia (ativos e inativos) e com um inexistente, para os seis papéis e a conta sem barbearia: mesma resposta e nenhum dado alheio. O filtro com ID próprio continua retornando só os registros do tenant. Horários livres e faturamento continuam sem oráculo. A listagem traz só o próprio tenant |
| `FluxosLegitimosTests` | Na própria barbearia: <br>• o cliente agenda e remarca (inclusive trocando de barbeiro); <br>• o barbeiro registra e confirma; <br>• o admin registra e troca o barbeiro; <br>• o admin promove um cliente. <br>As mensagens de validação dentro do tenant ficaram iguais: barbeiro inativo, serviço inativo, admin como barbeiro e "Barbeiros só podem gerenciar a própria agenda" |
| `CadastroPublicoEOnboardingTests` | **Conta do cadastro público** (API e JWT): não referencia nenhuma barbearia, e o MT-AP-27 mostra horário ocupado e livre de B com a mesma resposta de IDs inexistentes. <br>**Onboarding de uma barbearia nova (Gama)**, com o fluxo completo: serviço, dois clientes, barbeiro e agendamento. A barbearia nova também não alcança A nem B, nem pelo corpo nem pelos filtros |
| `SuperusuarioTests` | O superusuário lê e filtra qualquer barbearia; edita dentro da barbearia do registro e recebe 400 ao apontar para outra; e, sem barbearia, continua sem criar barbeiros (403) nem agendamentos |

**Testes existentes atualizados.** Os três abaixo protegiam a propriedade de segurança certa (nenhum dado de B, nenhum vínculo criado), mas fixavam a resposta antiga, que era o próprio oráculo. As asserções de segurança foram mantidas e ficaram mais estritas. Nenhuma permissão foi enfraquecida.

| Teste | Antes | Agora |
|---|---|---|
| `appointments/test_multitenant_isolation.py:254` (`test_filtros_com_ids_de_outro_tenant_nao_contornam_a_queryset`) | Exigia 200 para `?barbeiro=` e `?servico=` com ID de B | Exige 400, igual ao de um ID inexistente, e sem `results`. Os filtros `ativo` continuam com 200 |
| `barbershops/tests.py:476` (`test_barber_from_other_tenant_cannot_be_associated_via_api`) | Exigia o erro em `barbershop` (que revelava a outra barbearia) | Exige `user` com o código `does_not_exist`, e nenhum barbeiro criado |
| `accounts/tests_multitenant_comprehensive_final.py:397` (`test_filter_search_isolation`) | Exigia 200 com lista vazia | Exige 400, igual ao de um ID inexistente, e sem `results` |

### 22.5 Resultados

| Verificação | Resultado |
|---|---|
| Testes novos, SQLite | **Código anterior** (HEAD + contenção): 11 de 22 testes falham, com 188 subtestes. Entre as falhas estão 6 leituras de registros de outra barbearia sem condição de tenant. **Corrigido: 22/22.** Os 11 que passam nas duas versões protegem fluxos legítimos e o superusuário |
| Suíte completa, SQLite | **423 testes, OK** (9 pulados, que exigem PostgreSQL). Eram 401, mais os 22 novos |
| Suíte completa, PostgreSQL 18.3 descartável | **423, OK**, 0 pulados |
| Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings | **423, OK** |
| 66 testes de isolamento (novos, contenção e isolamento existentes) com `--debug-mode` (`DEBUG=True`) | **66, OK** |
| Django | `check` limpo. `makemigrations --check`: "No changes detected". `check --deploy` com `DEBUG=False`: só o W021, como antes |
| As 217 verificações da auditoria (`iso_probe.py`, sem alteração) | De 211 para **213 conformes**. Mudaram só MT-FI-01 (SEC-10) e MT-AP-27 (TEN-02), as duas para conforme; nenhuma regrediu. As 4 divergentes restantes são TEN-03 (duas), TEN-04 e `exclude_appointment_id` |
| Referências entre barbearias: `runserver` real, 288 pedidos por instância (seis papéis nos dois sentidos, conta sem barbearia e admin do onboarding), cada um comparado com um ID inexistente | **Anterior:** 288 oráculos, iguais com `DEBUG` True e False. **Corrigido:** 0 oráculos. Nos dois: 0 referências aceitas, 0 respostas com nomes de outra barbearia, 0 erros 500, banco inalterado (md5 de todas as linhas) e 0 vínculos entre barbearias |
| Matriz HTML/JSON da contenção (21 rotas × 9 papéis × 11 formas de pedido) | Corrigido: 0 respostas HTML com `DEBUG` True e False. Os 1.926 pedidos tiveram status e content-type iguais aos do código só com a contenção. A API continua respondendo só em JSON |
| **Laboratório:** API navegável religada só em duas instâncias descartáveis | Com 1.071 páginas HTML e 653 formulários nas duas versões: <br>• **anterior:** 114 respostas com dados de outra barbearia, em 19 combinações de rota e papel, com até 47 `<option>` alheios numa página; <br>• **corrigido: 0, 0 e 0.** <br>Os formulários continuam sendo desenhados, com o mesmo status e o mesmo número de `<select>` (1.926/1.926), mas só com o próprio tenant. Os 26 erros 500 das duas versões são o API-03 e o AUTH-03, que já existiam |
| Navegador: build de produção contra a API corrigida, Firefox headless | 3 logins e 16 páginas: 317 respostas da API, todas em JSON, 0 erros de API ou de console, 10/10 textos esperados, nenhum nome de B. **Fluxos pela interface:** <br>• o cliente agenda (POST 201, "Está marcado.", e no banco todos os vínculos na mesma barbearia); <br>• o cliente remarca (PATCH 200, horário alterado no banco); <br>• o admin confirma um horário (PATCH 200) |
| Frontend | `npm test` 45/45; `tsc` (app e node), 0 erros; ESLint, 0; build igual ao anterior (mesmo hash do JS). O frontend não foi alterado |

### 22.6 Perfis e sentidos verificados

| Perfil | Testes | HTTP | Navegador |
|---|---|---|---|
| Cliente, barbeiro e admin de A (A → B) | ✅ | ✅ | ✅ |
| Cliente, barbeiro e admin de B (B → A) | ✅ | ✅ | — |
| Conta do cadastro público, sem barbearia | ✅ | ✅ | — |
| Admin de uma barbearia criada no onboarding | ✅ | ✅ | — |
| Superusuário | ✅ | ✅ (matriz HTML/JSON) | — |
| Anônimo | ✅ (sem escopo) | ✅ (matriz HTML/JSON) | — |

### 22.7 Verificações que não puderam ser realizadas

- **Pilha de produção** (nginx, gunicorn, CDN) e **banco real**: não disponíveis ou não permitidos. Tudo rodou com `runserver` e banco descartável.
- **Canal de tempo:** o ID de outra barbearia e o inexistente agora geram a mesma consulta, sem linha encontrada, mas a diferença de tempo de resposta não foi medida.
- **Django Admin com staff que não é superusuário:** esse perfil não existe. O admin não tem escopo por tenant, por desenho (seção 20.6).
- **Corridas entre tenants** (concorrência): não testadas.
- **Navegadores:** Chrome e Safari não estão disponíveis; só o Firefox foi usado. Os papéis de B e a conta sem barbearia foram verificados por HTTP e testes, não pela interface.

### 22.8 Riscos ainda existentes

1. **Código novo precisa usar o escopo.**
   - **O que os testes estruturais pegam:** um campo relacional gravável ou um filtro relacional novo sem escopo, inclusive um `PrimaryKeyRelatedField` declarado à mão. Um model sem barbearia usado com o escopo falha com `ImproperlyConfigured`.
   - **O que não pegam:** consultas manuais nas views que busquem por ID sem filtrar a barbearia, como o `exclude_appointment_id`.
2. **O superusuário enxerga todas as barbearias**, por desenho. Comprometer essa conta expõe a plataforma inteira.
3. **A contenção deve continuar.** A correção estrutural não justifica religar a API navegável. Para o superusuário ela listaria todas as barbearias, e há os 500 do API-03 e do AUTH-03.
4. **Itens abertos relacionados:**
   - **SEC-10:** falta o `exclude_appointment_id`.
   - **TEN-02:** as checagens condicionais do `validate()` (`if barbeiro and barbershop_id`) e o 403 tardio do `perform_create` continuam no código. O sintoma deixou de se reproduzir porque os campos não aceitam nada para quem não tem barbearia. Se uma mudança futura afrouxar esse escopo, o TEN-02 volta.
5. **BUS-20 (P3, novo, apenas registrado): cliente promovido a barbeiro deixa os próprios horários sem confirmação.**
   - **Achado:** na verificação pelo navegador, o admin não conseguiu confirmar um horário: 400 `{"cliente": ["A instância de usuário com id 8 não existe.", "O usuário selecionado deve ter perfil de cliente."]}`.
   - **Causa:** a sondagem da auditoria tinha promovido esse cliente a barbeiro, de forma legítima (MT-BA), e ele já tinha horários futuros como cliente.
   - **Não é efeito desta correção:** a resposta é idêntica no código anterior e no corrigido.
   - **O que falta verificar:** outras edições e o cancelamento desses horários não foram testados.
   - **Decisão de produto:** o que fazer com os horários de um cliente promovido.

### 22.9 Situação atual

- **TEN-01: ✅ resolvido e verificado** no ambiente de testes. A conclusão se apoia em:
  - a contenção, que continua ativa;
  - a correção da causa raiz em todas as superfícies identificadas (seção 22.2);
  - testes estruturais que enumeram todos os campos e filtros relacionais;
  - testes de isolamento por papel, nos dois sentidos;
  - as 217 verificações da auditoria, sem regressão;
  - a sondagem de referências, com 0 oráculos;
  - o laboratório com a API navegável religada, com 0 dados alheios;
  - o navegador.

  Não foi verificado em produção nem no banco real.
- **SEC-10: ◐ parcialmente resolvido** (P3, continua aberto). Falta o `exclude_appointment_id`.
- **TEN-02:** sintoma não reproduzível; segue aberto (P2) até a etapa própria.

| | Após a contenção | Após a correção estrutural |
|---|---|---|
| P0 | 1 (TEN-01 contido) | **0** (TEN-01 resolvido) |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 29 | 29 (TEN-02 continua contado) |
| P3 | 37 | 38 (+BUS-20; SEC-10 parcial, continua contado) |
| **Abertos** | 64 dos 70 originais + 6 novos = 70 | **64 dos 70 originais + 6 novos = 70** (saiu o TEN-01, entrou o BUS-20) |

**Próximo passo:** aguarda a revisão do dono. O TEN-02 não foi iniciado.

---

## 23. Correção do TEN-02 — 14/11/2026

> **Atualização:** o `exclude_appointment_id`, citado aqui como risco aberto do SEC-10, foi corrigido na [seção 24](#24-correção-do-sec-10-exclude_appointment_id--14112026). Esta seção foi preservada.

**Escopo autorizado:** garantir que um usuário sem barbearia seja recusado antes de qualquer validação de negócio que consulte agendamentos, barbeiros ou disponibilidade de outras barbearias, com uma resposta que não dependa do horário nem da existência dos registros. O SEC-10 (`exclude_appointment_id`) ficou de fora, por instrução, e não foi iniciado.

**Restrições cumpridas:**

- **Código:**
  - **Alterado:** `config/permissions.py`, com a classe nova `HasBarbershop`; `appointments/views.py`; e `appointments/serializers.py`.
  - **Testes:** um arquivo de teste novo e uma asserção ajustada num teste da etapa anterior.
  - **Intacto:** models, `settings.py`, `.env`, frontend e dependências.
- **Migrações:** nenhuma. O `makemigrations --check` responde "No changes detected".
- **Etapas anteriores preservadas:** a contenção (só `JSONRenderer`) e a correção estrutural do TEN-01 continuam iguais.
- **Bancos:** o banco real e o PostgreSQL do Docker não foram usados. Os testes com escrita rodaram em SQLite em memória e num **PostgreSQL 18.3 descartável** (`127.0.0.1:55432`), já apagado.
- **Repositório:** sem commit, push ou merge. As alterações e as evidências anteriores foram preservadas.

Evidências em [`docs/auditoria/evidencias-2026-11-14/ten-02/`](auditoria/evidencias-2026-11-14/ten-02/README.md).

### 23.1 Resumo

| ID | Situação | Base |
|---|---|---|
| TEN-02 | ✅ **Resolvido e verificado** no ambiente de testes | Recusa antes de qualquer validação, com uma resposta única para qualquer corpo. Na conta sem barbearia, nenhuma consulta à agenda e nenhuma leitura de tabela de tenant, medidas no SQL do servidor com `DEBUG` True e False. A proteção é independente do escopo dos campos do TEN-01: com esse escopo afrouxado de propósito, o oráculo **voltava** no código anterior e não volta no corrigido |

### 23.2 Causa raiz e investigação

**Onde a conta sem barbearia era recusada, e onde estava a primeira consulta de disponibilidade.** Num `POST /appointments/`, o DRF executa nesta ordem:

1. autenticação;
2. permissões (`get_permissions`);
3. validação do serializer, campo a campo;
4. `validate()`, que chama o `full_clean()`, e o `clean()` do model chama `_validar_conflito_horario`, a **consulta à agenda do barbeiro**;
5. `perform_create`, que tinha o único `PermissionDenied('Usuário sem barbearia vinculada.')`.

| Versão | Onde a conta sem barbearia parava | Consultas (rastreamento SQL) | Ocupado × livre |
|---|---|---|---|
| Auditoria (HEAD) | Passo 4: o `validate()` pulava as checagens de barbearia (`if barbeiro and barbershop_id and …`), e o `full_clean()` rodava | 7 por pedido: lia o cliente, o barbeiro e o serviço de B pelo ID e **consultava a agenda do barbeiro de B** | Respostas diferentes (oráculo) |
| Anterior (com o TEN-01 estrutural) | Passo 3: os campos relacionais ficam vazios para quem não tem barbearia | 0 | Mesma resposta, ecoando os IDs enviados |
| Anterior, com o escopo dos campos afrouxado (simulação de uma mudança futura, por exemplo um catálogo público ligado ao PROD-01) | Passo 4, como na auditoria | As mesmas 7, **agenda de B incluída** | **Respostas diferentes: o oráculo voltava** |

**Conclusão da investigação: o TEN-02 não estava protegido de forma independente.**

- O defeito original continuava no código: a recusa só existia em `perform_create`, depois da validação, e o `validate()` pulava as checagens quando `barbershop_id` era vazio.
- O sintoma tinha sumido só porque o escopo dos campos do TEN-01 barrava antes. A proteção dependia de uma única camada, e uma alteração era necessária.

**As demais operações já recusavam antes de qualquer consulta** e não precisaram mudar:

- **PATCH, PUT e DELETE:** 404 pelo `get_queryset()` vazio, sem SQL;
- **horários livres:** 403 na primeira linha;
- **listagem filtrada:** 400, com as opções do filtro vazias.

### 23.3 Alteração implementada

**Duas camadas independentes, com a resposta que o projeto já usa:** 403 `{"detail": "Usuário sem barbearia vinculada."}`, igual à de `perform_create` e de `available-slots`.

1. **Recusa antes da validação.**
   - **Permissão:** `config.permissions.HasBarbershop` (`config/permissions.py:44`).
   - **Onde se aplica:** à criação, em `AppointmentViewSet.get_permissions` (`appointments/views.py:40-46`).
   - **Quando roda:** nas permissões do DRF, antes do serializer. A única consulta é a da autenticação, a linha do próprio usuário.
   - **Superusuário:** vale também para o superusuário sem barbearia, que o `perform_create` já recusava, só que depois da validação.
2. **O serializer falha fechado.**
   - **No `AppointmentSerializer.validate()`** (`appointments/serializers.py:93`): sem barbearia, é `PermissionDenied`, antes das checagens de tenant e do `full_clean()`.
   - **As três checagens de barbearia,** de barbeiro, serviço e cliente, deixaram de ser condicionais: não há mais caminho que as pule em silêncio.
   - **Independência:** esta camada vale para qualquer caminho que use o serializer, mesmo sem a view e mesmo com o escopo dos campos afrouxado.

**Sem alteração:**

- **PATCH, PUT e DELETE:** já recusam antes de qualquer consulta. O superusuário precisa continuar editando.
- **`available-slots`:** já recusa na primeira linha.
- **Listagem:** já vazia para quem não tem barbearia.
- **Recusa do `perform_create`:** mantida, como terceira camada.

**Teste ajustado.** Em `config/test_isolamento_tenant.py`, a regressão MT-AP-27 da etapa anterior fixava o 400 da recusa pelos campos. Agora ela exige o 403 com a resposta única e continua exigindo a mesma resposta de um ID inexistente.

### 23.4 Testes de regressão

**`appointments/test_ten02.py` (novo, 9 testes).** A autenticação é JWT real, e o cenário tem as barbearias A e B com agendamentos, uma conta sem barbearia e o superusuário.

| Teste | Caso do pedido | O que comprova |
|---|---|---|
| `test_criacao_recusada_antes_da_validacao_com_resposta_unica` e `…_debug` | 1 a 4, com `DEBUG=False` e `DEBUG=True` | Valem para o horário ocupado e o livre de B, o barbeiro válido de B, os IDs inexistentes, o corpo vazio e a data inválida: <br>• o mesmo 403 com o mesmo corpo, sem `data_hora`; <br>• **no SQL capturado, só a autenticação**: a linha do próprio usuário, sem agenda, barbeiro, serviço ou barbearia; <br>• nenhum agendamento criado ou alterado |
| `test_recusa_nao_depende_do_escopo_dos_campos` | Defesa em profundidade | Com o escopo dos campos afrouxado: <br>• ocupado e livre recebem o mesmo 403; <br>• a agenda de B não é consultada |
| `test_validate_recusa_sem_barbearia_antes_das_regras_de_negocio` | Segunda camada | O serializer, chamado diretamente com o escopo afrouxado, levanta `PermissionDenied` sem consultar a agenda |
| `test_demais_operacoes_sem_barbearia_nao_revelam_nada` | Demais operações | PATCH, PUT, DELETE, horários livres e listagem filtrada: a mesma resposta para um registro de B e para um inexistente (e para um dia ocupado e um livre), sem leitura de dados de tenant e sem alteração |
| `test_usuario_de_a_nao_sonda_a_agenda_de_b` | 5 | Cliente, barbeiro e admin de A com o barbeiro de B, em horário ocupado, horário livre e com ID inexistente: <br>• a mesma resposta; <br>• **a agenda não é consultada**; <br>• nada criado |
| `test_usuario_legitimo_agenda_na_propria_barbearia` | 6 | Na própria barbearia, cliente, admin e barbeiro agendam (201). O conflito continua detectado ("Este barbeiro já possui um agendamento neste horário."), e a consulta à agenda usa só o barbeiro de A |
| `test_cadastro_publico_e_onboarding` | 7 | Cadastro público e login: o agendamento é recusado com a resposta única. Depois do onboarding, o mesmo token cria serviço, clientes, barbeiro e agendamento (201): a barbearia vem do banco, não do token |
| `test_superusuario` | Superusuário | Sem barbearia, não cria agendamento (403, igual). Continua editando e filtrando qualquer barbearia |

**Antes e depois:**

- **Código anterior:** 6 dos 9 testes falham, com 18 subtestes. Entre as falhas estão a reprodução do oráculo com o escopo afrouxado e o serializer que não recusava.
- **Corrigido:** 9/9.
- **Os 3 que passam nas duas versões** protegem as demais operações, o caso 5 e o fluxo legítimo.

### 23.5 Resultados

| Verificação | Resultado |
|---|---|
| Testes do TEN-02 | Código anterior: 6 de 9 falham. **Corrigido: 9/9** |
| Suíte completa, SQLite | **432, OK** (9 pulados, que exigem PostgreSQL). Eram 423, mais os 9 novos |
| Suíte completa, PostgreSQL 18.3 descartável | **432, OK**, 0 pulados |
| Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings | **432, OK** |
| 75 testes de isolamento (TEN-02, TEN-01 estrutural e contenção, isolamento existentes) com `--debug-mode` (`DEBUG=True`) | **75, OK** |
| Django | `check` limpo. `makemigrations --check`: "No changes detected". `check --deploy` com `DEBUG=False`: só o W021, como antes |
| As 217 verificações da auditoria | **213 conformes**, as mesmas da etapa anterior; nenhuma regrediu. O MT-AP-27 agora responde 403 igual para ocupado e livre. As 4 divergentes são TEN-03 (duas), TEN-04 e `exclude_appointment_id` |
| Sondagem HTTP com o SQL do servidor, em cinco instâncias (seção 23.6) | Corrigido, com `DEBUG` True e False: resposta única e 0 consultas à agenda |
| Navegador: build de produção, Firefox headless | 3 logins e 16 páginas: 311 respostas da API, todas em JSON, 0 erros. Pela interface: <br>• o cliente agenda (201); <br>• o cliente remarca (200); <br>• o admin confirma (200) |
| Frontend | `npm test` 45/45; `tsc` (app e node), 0 erros; ESLint, 0; build igual ao anterior (o frontend não mudou) |

### 23.6 Evidências de que não há mais oráculo de disponibilidade

A sondagem HTTP rodou com o `runserver` real e o PostgreSQL descartável com `log_statement = 'all'`. Cada pedido foi isolado entre marcadores no log do banco.

**Casos 1 a 4 da conta sem barbearia (ocupado, livre, barbeiro válido de B, inexistente):**

| Instância | Status | Respostas distintas | Consultas à agenda | Leituras de tabelas de tenant sem escopo de barbearia |
|---|---|---|---|---|
| Auditoria (HEAD) | 400 | 3 | **3** | **14** |
| Anterior, `DEBUG` True e False | 400 | 3 (1 sem os números ecoados) | 0 | 0 |
| **Corrigido, `DEBUG=True`** | **403** | **1** | **0** | **0** |
| **Corrigido, `DEBUG=False`** | **403** | **1** | **0** | **0** |

**Nas instâncias corrigidas:**

- **demais operações da conta sem barbearia:**
  - PATCH e DELETE: 404 igual para o agendamento de B e para um inexistente;
  - horários livres: 403 igual para o dia ocupado, o dia livre e IDs inexistentes;
  - listagem: 400 igual para o barbeiro de B e para um inexistente;
  - em todos, 0 consultas;
- **usuários de A contra a agenda de B:** a mesma resposta, sem contar os números ecoados, e 0 consultas à agenda;
- **cliente de A na própria barbearia:** 201 e 400 por conflito, com a agenda de A consultada;
- **onboarding:** completo, com 201 em cada passo.

### 23.7 Consultas SQL relevantes

Comandos que o servidor executou para "conta sem barbearia, horário ocupado de B", lidos do log do PostgreSQL. A lista de colunas foi abreviada como `…`.

```sql
-- Código da auditoria: 400 {"barbershop": [...], "data_hora": ["Este barbeiro já possui um agendamento neste horário."]}
SELECT … FROM "accounts_user" WHERE "accounts_user"."id" = 35                                   -- autenticação (o próprio usuário)
SELECT … FROM "accounts_user" WHERE ("accounts_user"."tipo_perfil" = 'cliente' AND "accounts_user"."id" = 13)   -- cliente de B
SELECT … FROM "barbershops_barber" WHERE "barbershops_barber"."id" = 4                          -- barbeiro de B
SELECT … FROM "services_service" WHERE "services_service"."id" = 6                              -- serviço de B
-- (as três leituras se repetem no full_clean)
SELECT … FROM "appointments_appointment" INNER JOIN "services_service" ON (…)
  WHERE ("appointments_appointment"."barbeiro_id" = 4 AND "appointments_appointment"."data_hora" >= '…' …)   -- AGENDA DE B

-- Código corrigido (DEBUG True e False): 403 {"detail": "Usuário sem barbearia vinculada."}
SELECT … FROM "accounts_user" WHERE "accounts_user"."id" = 47                                   -- só a autenticação
```

**Usuário de A com o barbeiro de B.** A busca já vem com a condição de barbearia, e a linha de B nunca é carregada:

```sql
SELECT … FROM "barbershops_barber" WHERE ("barbershops_barber"."barbershop_id" = 1 AND "barbershops_barber"."id" = 4)
```

**Validação legítima na própria barbearia** (conflito do cliente de A):

```sql
SELECT … FROM "appointments_appointment" INNER JOIN "services_service" ON (…)
  WHERE ("appointments_appointment"."barbeiro_id" = 1 …)
```

O `barbeiro_id = 1` é o barbeiro de A escolhido pelo próprio cliente.

### 23.8 Riscos que continuam abertos

1. **SEC-10 (`exclude_appointment_id`):** a busca é global, com mensagem diferente para o agendamento de outra barbearia. Fica para a próxima etapa, que não foi iniciada.
2. **Respostas diferentes por desenho.** A conta sem barbearia recebe 403 na criação e nos horários livres, e 404 em PATCH, PUT e DELETE.
   - **Por que são diferentes:** na criação, não há objeto; na edição, o objeto está fora do escopo.
   - **Por que não há oráculo:** cada resposta é sempre a mesma, seja qual for o corpo ou o ID.
3. **Outros caminhos que validem agendamentos.** Um endpoint ou uma ação nova que valide agendamentos deve usar `HasBarbershop` ou o `AppointmentSerializer`. O `validate()` do serializer cobre qualquer caminho que o use, mas código que chame `Appointment.full_clean()` diretamente não teria essa proteção.
4. **Canal de tempo:** não medido. A recusa acontece antes de qualquer consulta, o que tende a uniformizar o tempo.
5. **Fora do escopo, continuam abertos:** TEN-03, TEN-04, API-03, AUTH-03 e BUS-20.

### 23.9 Situação final

**TEN-02: ✅ resolvido e verificado** no ambiente de testes. A conclusão se apoia em:

- a investigação do caminho de validação nas três versões;
- os testes de regressão, inclusive com o escopo dos campos afrouxado de propósito;
- o SQL do servidor real com `DEBUG` True e False;
- as 217 verificações sem regressão;
- o navegador.

Não foi verificado em produção nem no banco real.

| | Após a correção estrutural do TEN-01 | Após a correção do TEN-02 |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 29 | **28** (TEN-02 resolvido) |
| P3 | 38 | 38 (SEC-10 parcial continua contado) |
| **Abertos** | 64 dos 70 originais + 6 novos = 70 | **64 dos 70 originais + 5 novos = 69** |

**Próximo passo:** aguarda a revisão do dono. O SEC-10 (`exclude_appointment_id`) não foi iniciado.

---

## 24. Correção do SEC-10: `exclude_appointment_id` — 14/11/2026

> **Atualização:** o PER-13, que aqui aparece como aberto, foi corrigido na [seção 25](#25-correção-do-per-13-e-conclusão-do-sec-10--14112026), e o SEC-10 foi concluído. Esta seção foi preservada.

**Escopo autorizado:** investigar e corrigir qualquer diferença de resposta que permitisse descobrir, pelo parâmetro `exclude_appointment_id`, se um agendamento pertence a outra barbearia. TEN-03 e as demais correções não foram iniciadas, por instrução.

**Restrições cumpridas:**

- **Código:** só `appointments/views.py` mudou (a busca do agendamento a excluir e a docstring), mais um arquivo de teste novo.
- **Intacto:** serializers, models, permissões, `settings.py`, `.env`, frontend e dependências.
- **Migrações:** nenhuma. O `makemigrations --check` responde "No changes detected".
- **Etapas anteriores preservadas:** a contenção (só `JSONRenderer`) e as correções do TEN-01 e do TEN-02 continuam iguais, e os testes delas continuam passando.
- **Bancos:** o banco real e o PostgreSQL do Docker não foram usados. Os testes com escrita rodaram em SQLite em memória e num **PostgreSQL 18.3 descartável** (`127.0.0.1:55432`), já apagado.
- **Repositório:** sem commit, push ou merge. As alterações e as evidências anteriores foram preservadas.

Evidências em [`docs/auditoria/evidencias-2026-11-14/sec-10/`](auditoria/evidencias-2026-11-14/sec-10/README.md).

### 24.1 Resumo

| Item | Situação |
|---|---|
| `exclude_appointment_id` (MT-AV-02) | ✅ **Corrigido e verificado.** O ID de outra barbearia tem o mesmo status, o mesmo corpo, as mesmas consultas SQL (só muda o número) e a mesma ausência de horários de um ID inexistente, e o registro alheio não é lido. Vale com `DEBUG` True e False, para os seis papéis, nos dois sentidos |
| SEC-10, considerando todos os pontos conhecidos | ◐ **Continua parcial.** Os caminhos entre barbearias estão todos fechados: corpo das requisições (seção 22), filtros (seção 22) e `exclude_appointment_id` (esta seção). Segue presente o terceiro ponto da definição original, que acontece dentro da própria barbearia (PER-13, seção 24.8) e não foi autorizado nesta etapa |

### 24.2 Causa raiz

A inspeção do código atual (`appointments/views.py`, ação `available_slots`) mostrou:

1. **Onde o parâmetro chega.** `request.query_params.get('exclude_appointment_id')` (linha 179). Uma string vazia equivale a omitir o parâmetro (`if exclude_appointment_id:`, linha 215).
2. **Onde é convertido e validado.** Na própria busca: o Django converte o valor para inteiro. Valores não numéricos (`abc`, `1.5`, `1e3`, espaço) levantam `ValueError`, que é tratado como "não encontrado". Valores fora da faixa do banco também caem em "não encontrado", sem erro 500 em SQLite nem em PostgreSQL.
3. **Onde o agendamento era consultado.** `Appointment.objects.select_related('cliente', 'barbeiro', 'servico', 'barbershop').get(pk=…)`, **sem condição de barbearia.**
4. **Se a busca respeitava a barbearia.** **Não.** O registro de outra barbearia era lido, com o cliente, o barbeiro, o serviço e a barbearia carregados por JOIN, e só **depois** comparado com a barbearia do usuário.
5. **Diferença entre ID inexistente e ID de outra barbearia.** O status era o mesmo (404), mas a mensagem não:
   - outra barbearia: "Agendamento a excluir **não pertence à sua barbearia**.";
   - inexistente: "Agendamento a excluir **não encontrado**."

   Disponibilidade e SQL eram iguais. A correção estrutural do TEN-01 não cobria este caminho, porque é uma consulta manual na view, fora dos campos relacionais e dos filtros.

### 24.3 Comportamento anterior e posterior

**A alteração,** em `appointments/views.py:215-225`:

- **Busca:** passou a ser `Appointment.objects.filter(barbershop_id=user.barbershop_id).get(pk=…)`.
- **Ramo removido:** "não pertence à sua barbearia" ficou inalcançável e saiu.
- **`select_related` removido:** nenhum campo relacionado era usado depois. Agora o agendamento a excluir não carrega o cliente nem os demais registros.

As regras que vêm depois não mudaram: o cliente só exclui o próprio horário, o barbeiro só a própria agenda, o status precisa permitir remarcação, e o agendamento de outro barbeiro é ignorado.

| Caso | Antes | Depois |
|---|---|---|
| Agendamento da própria barbearia, permitido ao papel | 200; o horário é liberado | Igual |
| Agendamento de **outra barbearia** | 404 "**não pertence à sua barbearia**", depois de ler o registro com JOINs | 404 "**não encontrado**", idêntico ao inexistente; o registro não é lido |
| ID inexistente | 404 "não encontrado" | Igual |
| Omitido ou vazio | 200, sem exclusão | Igual |
| Malformado (`abc`, `1.5`, `-1`, `0`, `1e3`, espaço, valor enorme) | 404 "não encontrado" | Igual, sem erro 500 |
| Usuário sem barbearia (TEN-02) | 403 "Usuário sem barbearia vinculada." antes de qualquer consulta | Igual |
| Superusuário sem barbearia | 403 (a ação usa a barbearia do usuário) | Igual |
| Superusuário com barbearia | Escopo da própria barbearia; o de outra recebia "não pertence" | Escopo da própria barbearia; o de outra é igual ao inexistente |
| Dentro da própria barbearia: cliente com o horário de outro cliente; barbeiro com o de outro barbeiro | 403 | Igual (regra atual, preservada; seção 24.8) |

### 24.4 Testes adicionados

**`appointments/test_sec10.py` (novo, 11 testes).** O cenário tem as barbearias A e B, cada uma com dois clientes, dois barbeiros, um serviço de 30 minutos e um combo de 60, e horários às 10:00 e às 11:00. Também há uma conta sem barbearia e o superusuário.

| Teste | Casos do pedido | O que comprova |
|---|---|---|
| `test_id_de_outra_barbearia_igual_a_inexistente` e `…_debug` | 2, 3, 6, 7 e 8, com `DEBUG=False` e `DEBUG=True` | Para cliente, barbeiro e admin, **A → B e B → A**: <br>• o mesmo status e o **mesmo corpo**; <br>• nenhum horário retornado; <br>• nenhum dado da outra barbearia; <br>• **as mesmas consultas SQL**, só mudando o número; <br>• nenhuma busca do agendamento alheio sem a condição de barbearia do usuário; <br>• nenhum agendamento alterado |
| `test_consulta_do_excluido_ja_tem_condicao_de_barbearia` | Leitura | Há uma única busca, com `barbershop_id = <A>` na própria consulta e **sem JOIN**: o registro alheio não é carregado antes da recusa |
| `test_proprio_agendamento_e_excluido_da_ocupacao` | 1 e 8 | Para os três papéis nas duas barbearias, o próprio horário (10:00) é liberado, e o de outro cliente (11:00) continua ocupado |
| `test_parametro_omitido_ou_vazio_mantem_a_ocupacao` | 4 | Omitido e vazio dão a mesma resposta, sem exclusão |
| `test_valor_malformado_responde_como_inexistente` | 5 | `abc`, `1.5`, `-1`, `0`, `1e3`, espaço e um valor enorme dão a mesma resposta que um ID inexistente |
| `test_usuario_sem_barbearia_continua_recusado_antes_de_tudo` | 9 | 403 único, com **zero consultas**, para o agendamento de A, o de B, o inexistente e o omitido |
| `test_superusuario_mantem_as_regras_atuais` | 10 | Sem barbearia, 403. Com barbearia, exclui o próprio, e o de B é igual ao inexistente, sem ler o de B |
| `test_regras_atuais_dentro_da_propria_barbearia` | Regras preservadas | O cliente com o horário de outro cliente recebe 403, e o barbeiro com o de outro barbeiro também. O admin exclui qualquer horário da barbearia, e um cancelado recebe 400 |
| `test_remarcacao_legitima_com_horario_que_so_aparece_ao_excluir_o_proprio` | 11 | O combo de 60 minutos às 10:00 só aparece excluindo o próprio horário, e a remarcação (PATCH) é aceita e gravada |
| `test_conflitos_da_mesma_barbearia_continuam_valendo` | 12 | Excluir o próprio não libera o horário de outro cliente. Remarcar para cima dele dá 400 "Este barbeiro já possui um agendamento neste horário.". Para outro barbeiro, o próprio horário é ignorado |

**Antes e depois:**

- **Código anterior:** 4 dos 11 testes falham, com 14 subtestes. São a diferença de mensagem, a busca sem condição de barbearia e o superusuário com barbearia.
- **Corrigido:** 11/11.
- **Os 7 que passam nas duas versões** protegem as regras atuais e os fluxos legítimos.
- **Testes antigos:** os 8 de `exclude_appointment_id` em `appointments/tests.py` (`AvailableSlotsExcludeAppointmentTests`) e os de `test_cancelamento_reagendamento.py` continuam passando sem alteração. Eles verificavam só o status.

### 24.5 Resultados

| Verificação | Resultado |
|---|---|
| Testes do SEC-10 | Código anterior: 4 de 11 falham. **Corrigido: 11/11** |
| Suíte completa, SQLite | **443, OK** (9 pulados, que exigem PostgreSQL). Eram 432, mais os 11 novos |
| Suíte completa, PostgreSQL 18.3 descartável | **443, OK**, 0 pulados |
| Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings | **443, OK** |
| 105 testes de isolamento e de `exclude_appointment_id` com `--debug-mode` (`DEBUG=True`) | **105, OK**. Inclui os do SEC-10, do TEN-02, do TEN-01 (estrutural e contenção), os de isolamento existentes e os de remarcação |
| Django | `check` limpo. `makemigrations --check`: "No changes detected". `check --deploy` com `DEBUG=False`: só o W021, como antes |
| As 217 verificações da auditoria | De 213 para **214 conformes**. Só o MT-AV-02 mudou, para conforme; nenhuma regrediu. As 3 divergentes restantes são TEN-03 (duas) e TEN-04 |
| Contenção JSON (matriz HTML/JSON, 1.926 pedidos por instância) | Corrigido, com `DEBUG` True e False: 0 respostas HTML, 0 com dados de outro tenant, `OPTIONS` anuncia só JSON |
| TEN-01 e TEN-02 | Os testes deles (22 e 9) passam. As verificações MT-HT-01 a 12, MT-FI-01 e MT-AP-27 continuam conformes |
| Navegador: build de produção, Firefox headless | 3 logins e 16 páginas: 288 respostas da API, todas em JSON, 0 erros. **A remarcação pela interface,** que chama `available-slots` com `exclude_appointment_id`, fez 4 chamadas, todas 200, e gravou a nova data (PATCH 200). O agendamento (201) e a confirmação (200) também funcionaram |
| Frontend | `npm test` 45/45; `tsc` (app e node), 0 erros; ESLint, 0; build igual ao anterior (o frontend não mudou) |

### 24.6 Evidências de equivalência entre ID alheio e inexistente

Sondagem no servidor real: seis papéis (cliente, barbeiro e admin de A e de B), nos dois sentidos. O SQL foi lido do log do PostgreSQL descartável:

| Instância | Comparações | Corpo diferente | Status diferente | SQL diferente (só o número muda) | Buscas do agendamento alheio sem condição de barbearia | Buscas com JOIN |
|---|---|---|---|---|---|---|
| Anterior, `DEBUG` True e False | 6 | **6** | 0 | 0 | **6** | **6** |
| **Corrigido, `DEBUG=True`** | 6 | **0** | 0 | 0 | **0** | **0** |
| **Corrigido, `DEBUG=False`** | 6 | **0** | 0 | 0 | **0** | **0** |

**Nas instâncias corrigidas:**

- valores malformados dão a mesma resposta que o inexistente, e o vazio, a mesma que o omitido;
- o próprio agendamento libera o horário nos seis papéis;
- a conta sem barbearia recebe 403 único, sem consultar agendamentos;
- 0 erros 500, inclusive com o valor enorme no PostgreSQL;
- o md5 de todos os agendamentos ficou igual antes e depois.

### 24.7 Consultas SQL relevantes

Lidas do log do PostgreSQL, para o cliente de A, com a lista de colunas abreviada como `…`:

```sql
-- Anterior, agendamento de B (419): 404 "Agendamento a excluir não pertence à sua barbearia."
SELECT … FROM "appointments_appointment"
  INNER JOIN "barbershops_barbershop" ON (…) INNER JOIN "accounts_user" ON (…)
  INNER JOIN "barbershops_barber" ON (…) INNER JOIN "services_service" ON (…)
  WHERE "appointments_appointment"."id" = 419 LIMIT 21          -- lê o agendamento de B e o cliente dele

-- Corrigido, agendamento de B (419): 404 "Agendamento a excluir não encontrado."
SELECT … FROM "appointments_appointment"
  WHERE ("appointments_appointment"."barbershop_id" = 1 AND "appointments_appointment"."id" = 419) LIMIT 21

-- Corrigido, inexistente (999999): a mesma consulta e a mesma resposta
SELECT … FROM "appointments_appointment"
  WHERE ("appointments_appointment"."barbershop_id" = 1 AND "appointments_appointment"."id" = 999999) LIMIT 21
```

### 24.8 Riscos ainda abertos

1. **PER-13, o terceiro ponto da definição original do SEC-10 (seção 13), continua presente.** Ele acontece dentro da própria barbearia.
   - **Comportamento:** o cliente (ou o barbeiro) que pede `GET /users/{id}/` de outro usuário da mesma barbearia recebe **403**. Para um usuário de outra barbearia ou inexistente, recebe **404**. A causa é a permissão de objeto `IsSelfOrAdmin` (`config/permissions.py:12`), aplicada depois do queryset da barbearia (`accounts/views.py:204-205`). Verificado nesta etapa, antes e depois da alteração: `sql/rastreamento-sql-*.txt`.
   - **Mesmo padrão no `exclude_appointment_id`:** o cliente com o horário de outro cliente, ou o barbeiro com o de outro barbeiro, da mesma barbearia, recebe 403, contra 404 para o inexistente. São "regras atuais", fixadas por testes existentes, e foram preservadas por instrução.
   - **Impacto:** baixo. Revela só que um ID existe **na própria barbearia** e não expõe dados.
   - **Correção possível, que depende de autorização:** limitar o queryset de cliente e barbeiro ao que eles podem ver (o próprio cadastro; os próprios horários), devolvendo 404 para o resto. Isso muda respostas que hoje são 403 e os testes que as fixam.
2. **Consultas manuais por ID.** Este era o último caso conhecido de busca por ID sem condição de barbearia nas views de agendamento:
   - `available-slots` (barbeiro e serviço) e faturamento já filtram pela barbearia;
   - os campos relacionais e os filtros usam o escopo do TEN-01.

   Código novo com buscas manuais precisa seguir o mesmo padrão. Os testes estruturais do TEN-01 não cobrem consultas manuais.
3. **Canal de tempo:** não medido. As duas buscas são a mesma consulta e não encontram linha.
4. **Fora do escopo, continuam abertos:** TEN-03, TEN-04, API-03, AUTH-03 e BUS-20.

### 24.9 Situação final

- **`exclude_appointment_id`: ✅ corrigido e verificado** no ambiente de testes, com `DEBUG` True e False.
- **SEC-10: ◐ continua parcial,** e não foi declarado resolvido:

  | Ponto | Situação |
  |---|---|
  | Corpo das requisições, entre barbearias | Fechado (seção 22) |
  | Filtros, entre barbearias | Fechado (seção 22) |
  | `exclude_appointment_id`, entre barbearias | Fechado (esta seção) |
  | **PER-13**, dentro da própria barbearia | **Aberto, aguardando decisão** |

  Para encerrar o SEC-10, falta decidir e corrigir o PER-13, ou aceitá-lo formalmente como comportamento intencional.

| | Após a correção do TEN-02 | Após a correção do `exclude_appointment_id` |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 28 |
| P3 | 38 | 38 (SEC-10 parcial, só com o PER-13, continua contado) |
| **Abertos** | 64 dos 70 originais + 5 novos = 69 | **69** |

**Próximo passo:** aguarda a revisão do dono. Nem o TEN-03 nem o PER-13 foram iniciados.

---

## 25. Correção do PER-13 e conclusão do SEC-10 — 14/11/2026

**Escopo autorizado:** corrigir o PER-13, o terceiro ponto da definição original do SEC-10 (seção 13), só na leitura de detalhe de `/users/{id}/` (GET e HEAD), e concluir a validação do SEC-10. O TEN-03 não foi iniciado. As escritas não foram alteradas, por instrução; o mesmo problema nelas foi registrado à parte (SEC-12, seção 25.8).

**Restrições cumpridas:**

- **Código:**
  - **Alterado:** só `accounts/views.py`, no `UserViewSet.get_queryset()`.
  - **Testes:** um arquivo de teste novo e quatro asserções de GET atualizadas em testes existentes.
  - **Intacto:** permissões, serializers, models, `settings.py`, `.env`, frontend e dependências.
- **Migrações:** nenhuma. O `makemigrations --check` responde "No changes detected".
- **Etapas anteriores preservadas:** a contenção (só `JSONRenderer`), o TEN-01, o TEN-02 e o `exclude_appointment_id`, com os testes de todos eles passando.
- **Bancos:** o banco real e o PostgreSQL do Docker não foram usados. Os testes com escrita rodaram em SQLite em memória e num **PostgreSQL 18.3 descartável** (`127.0.0.1:55432`), já apagado.
- **Repositório:** sem commit, push ou merge, e sem comandos destrutivos. As alterações locais e as evidências anteriores foram preservadas. As desta etapa estão numa pasta nova.

Evidências em [`docs/auditoria/evidencias-2026-11-14/per-13/`](auditoria/evidencias-2026-11-14/per-13/README.md).

### 25.1 Resumo

| Item | Situação |
|---|---|
| PER-13 (GET e HEAD em `/users/{id}/`) | ✅ **Corrigido e verificado.** Para cliente e barbeiro, outro usuário da mesma barbearia, um usuário de outra barbearia e um ID inexistente recebem o mesmo 404, com o mesmo corpo e a mesma forma de SQL. O registro do usuário consultado não é carregado. Vale com `DEBUG` True e False, nas duas barbearias |
| **SEC-10** | ✅ **Resolvido e verificado** no ambiente de testes. Os três pontos da definição original estão cobertos por evidências (seção 25.9) |
| SEC-12 (novo, P3) | **Registrado, não corrigido.** É a mesma diferença 403 × 404 dentro da própria barbearia em PATCH e PUT de `/users/{id}/` e no `exclude_appointment_id` (seção 25.8) |

### 25.2 Causa raiz

A rota é `/api/v1/users/{id}/`, registrada pelo `DefaultRouter` em `accounts/urls.py` e atendida pelo `UserViewSet` (`accounts/views.py`). O caminho da leitura de detalhe era:

1. **Permissões:** `get_permissions()` aplica `IsAuthenticated` e `IsSelfOrAdmin` em `retrieve`, `update` e `partial_update` (linha 204).
2. **Busca:** `get_queryset()` limitava à barbearia do usuário. O superusuário via todos, e o usuário sem barbearia, nenhum. Mas a busca **não** levava em conta o que cada papel pode ver.
3. **Carga do registro:** `get_object()` buscava o registro com `WHERE barbershop_id = <A> AND id = <alvo>` e **o carregava**.
4. **Recusa tardia:** só então `IsSelfOrAdmin.has_object_permission` (`config/permissions.py:12`) recusava, com 403, quem não é o próprio usuário, admin ou superusuário.

**Resultado:** um usuário da mesma barbearia era lido e recebia 403, enquanto um de outra barbearia ou inexistente nem era encontrado e recebia 404. Cliente e barbeiro descobriam quais IDs existem na própria barbearia.

O PATCH e o PUT passam pelo mesmo caminho e têm a mesma diferença. O DELETE recusa antes da busca, com `IsAdminRole`, e dá 403 uniforme. O HEAD segue o `retrieve`.

### 25.3 Estratégia e alteração

Em `UserViewSet.get_queryset()` (`accounts/views.py:216-224`), quando a ação é `retrieve` (GET e HEAD) e o solicitante não é admin, a consulta ganha `filter(pk=user.pk)`. A autorização entra na própria consulta, antes de recuperar o registro.

| Solicitante | Escopo na leitura de detalhe |
|---|---|
| Cliente e barbeiro | Só o próprio cadastro |
| Admin | Todos os usuários da própria barbearia (inalterado) |
| Superusuário | Todos (inalterado; tratado antes, em `get_queryset()`) |
| Usuário sem barbearia | Nenhum (inalterado; queryset vazio, falha fechado, sem SQL de busca) |

**O que fica igual:**

- **`IsSelfOrAdmin`** continua como segunda camada.
- **Listagem, criação, PATCH, PUT, DELETE e `/users/me/`** não mudaram: a condição se aplica só à ação `retrieve`.

**O que muda por consequência:**

- **Mensagem:** o 404 é o mesmo do DRF para objeto não encontrado (`{"detail":"No User matches the given query."}`), para todos os casos não autorizados e para o inexistente.
- **Usuário sem barbearia:** na própria conta por ID, já recebia 404. Continua assim; o caminho suportado é `/users/me/`.

### 25.4 Comportamento antes e depois: matriz por papel

GET e HEAD em `/users/{id}/`, nas barbearias A e B:

| Solicitante | Própria conta | Outro cliente da barbearia | Barbeiro da barbearia | Admin da barbearia | Usuário de outra barbearia | Inexistente |
|---|---|---|---|---|---|---|
| Cliente | 200 → 200 | **403 → 404** | **403 → 404** | **403 → 404** | 404 → 404 | 404 → 404 |
| Barbeiro | 200 → 200 | **403 → 404** | **403 → 404** (outro barbeiro) | **403 → 404** | 404 → 404 | 404 → 404 |
| Admin | 200 → 200 | 200 → 200 | 200 → 200 | 200 → 200 | 404 → 404 | 404 → 404 |
| Superusuário | 200 → 200 | 200 → 200 | 200 → 200 | 200 → 200 | 200 → 200 | 404 → 404 |
| Sem barbearia | 404 → 404 | 404 → 404 | 404 → 404 | 404 → 404 | 404 → 404 | 404 → 404 |

**Sem mudança:**

| Operação | Comportamento |
|---|---|
| PATCH e PUT em outro usuário da barbearia, por cliente ou barbeiro | 403, contra 404 do inexistente (SEC-12) |
| DELETE por cliente ou barbeiro | 403 para qualquer ID |
| `/users/` | Admin vê a própria barbearia; cliente, barbeiro e sem barbearia recebem 403; superusuário vê todos |
| `/users/me/` | 200 para todos |

As linhas de admin, sem barbearia e superusuário do rastreamento ficaram idênticas antes e depois (`sql/rastreamento-respostas-sql-*.txt`).

### 25.5 Testes

**`accounts/test_per13.py` (novo, 9 testes).** O cenário tem as barbearias A e B, cada uma com dois admins, dois clientes e dois barbeiros com perfil, além de uma conta sem barbearia e do superusuário. A autenticação é JWT real.

| Teste | Casos do pedido | O que comprova |
|---|---|---|
| `test_nao_autorizado_igual_a_inexistente` e `…_debug` | 2, 3, 4, 6, 7, 9, 10, 11 e 12, com `DEBUG=False` e `DEBUG=True` | Para cliente, barbeiro e admin de A e de B, cada ID não autorizado (da mesma barbearia e de outra) tem: <br>• o **mesmo status e corpo integral** do inexistente; <br>• nenhum nome nem e-mail do usuário consultado; <br>• **as mesmas consultas SQL**, só mudando o número; <br>• a busca com `barbershop_id` **e** com o ID do próprio solicitante no WHERE, no caso de cliente e barbeiro; <br>• o mesmo status também no HEAD |
| `test_cada_um_consulta_a_propria_conta` | 1 e 5 | Cliente, barbeiro e admin: 200 com os próprios dados (GET e HEAD) |
| `test_admin_consulta_usuarios_da_propria_barbearia` | 8 | O admin lê o outro admin, os clientes e os barbeiros da barbearia |
| `test_usuario_sem_barbearia_continua_sem_acesso` | 13 | 404 único para o próprio ID, A, B e o inexistente. Só a autenticação lê o banco. `/users/me/` continua 200 |
| `test_superusuario_mantem_o_comportamento` | 14 | 200 para usuários de A e de B; 404 para o inexistente |
| `test_listagem_users_sem_regressao` | `/users/` | Admin: exatamente os usuários da barbearia. Cliente, barbeiro e sem barbearia: 403. Superusuário: todos |
| `test_users_me_continua` | `/users/me/` | 200 para todos os papéis |
| `test_escritas_mantem_as_permissoes_anteriores` | Escritas | As recusas de antes continuam, sem alterar dados: <br>• PATCH e PUT em outro usuário da barbearia (403); <br>• PATCH em outra barbearia (404); <br>• DELETE e POST pelo cliente (403). <br>As escritas legítimas também: <br>• PATCH na própria conta; <br>• PATCH, POST e DELETE do admin |

- **Antes e depois:** no código anterior, 2 dos 9 testes falham (48 subtestes); no corrigido, 9/9. Os 7 que passam nas duas versões protegem o acesso legítimo, a listagem, o `/users/me/` e as escritas.
- **Testes existentes atualizados:** quatro asserções exigiam **403 no GET** de detalhe de outro usuário da mesma barbearia, que era o próprio oráculo. Agora exigem 404. As asserções de escrita desses mesmos testes não mudaram.
  - `accounts/test_multitenant_isolation.py`: `test_barber_cannot_manage_users` e `test_client_cannot_manage_users`, só a linha do GET;
  - `accounts/test_permissions.py`: `test_beireiro_can_only_access_own_user` e `test_cliente_can_only_access_own_user`;
  - `config/test_renderers.py`: na matriz JSON da contenção, a linha "usuário" passou de 403 para 404 para cliente e barbeiro.

### 25.6 Resultados

| Verificação | Resultado |
|---|---|
| Testes do PER-13 | Código anterior: 2 de 9 falham. **Corrigido: 9/9** |
| Suíte completa, SQLite | **452, OK** (9 pulados, que exigem PostgreSQL). Eram 443, mais os 9 novos |
| Suíte completa, PostgreSQL 18.3 descartável | **452, OK**, 0 pulados |
| Suíte completa, PostgreSQL 18.3, com `DEBUG=False` também na importação das settings | **452, OK** |
| 123 testes com `--debug-mode` (`DEBUG=True`) | **123, OK**. Incluem PER-13, SEC-10 (`exclude_appointment_id` e os 8 testes antigos dele), TEN-02, TEN-01 (estrutural e contenção), isolamento, permissões de usuários e remarcação |
| Django | `check` limpo. `makemigrations --check`: "No changes detected". `check --deploy` com `DEBUG=False`: só o W021, como antes |
| As 217 verificações da auditoria | **214 conformes**, sem nenhum veredito alterado em relação à etapa anterior. Elas cobrem o acesso entre barbearias; o PER-13 é coberto pelos testes e pela sondagem desta etapa |
| Contenção JSON (matriz HTML/JSON, 1.926 pedidos por instância) | Corrigido, com `DEBUG` True e False: 0 respostas HTML, 0 com dados de outro tenant, `OPTIONS` só JSON |
| Navegador: build de produção, Firefox headless | 3 logins e 16 páginas, inclusive "Minha conta" (pelo `/users/me/`): 285 respostas da API, todas em JSON, 0 erros, 10/10 textos esperados. **Agendamento** (201), **remarcação** (4 chamadas a horários livres com `exclude_appointment_id`, todas 200; PATCH 200) e **confirmação** (200) pela interface |
| Frontend | `npm test` 45/45; `tsc` (app e node), 0 erros; ESLint, 0; build igual ao anterior (o frontend não mudou) |

### 25.7 Indistinguibilidade e SQL

**Sondagem no servidor real,** com o SQL lido do log do PostgreSQL descartável (`log_statement = 'all'`). São 130 pedidos por instância: cliente, barbeiro e admin de A e de B, superusuário e conta sem barbearia, contra o próprio usuário, usuários da mesma barbearia e de outra, e um inexistente.

| Instância | Não autorizados com resposta diferente da do inexistente | HEAD diferente | SQL diferente (só o número muda) | Buscas sem o solicitante no WHERE (cliente e barbeiro) | Dados do consultado na resposta |
|---|---|---|---|---|---|
| Anterior, `DEBUG` True e False | **10** (3 por cliente e barbeiro de A, 2 por cliente e barbeiro de B) | **10** | 0 | **26** | 0 |
| **Corrigido, `DEBUG` True e False** | **0** | **0** | 0 | **0** | 0 |

Em todas as instâncias: 0 erros 500, os usuários ficaram inalterados (md5) e admins e superusuário mantiveram os 200.

**SQL do servidor** (cliente de A, id 5, consultando o barbeiro da barbearia, id 2, e um inexistente):

```sql
-- Anterior: carrega a linha do barbeiro e recusa com 403
SELECT … FROM "accounts_user" WHERE "accounts_user"."id" = 5                                     -- autenticação
SELECT … FROM "accounts_user" WHERE ("accounts_user"."barbershop_id" = 1 AND "accounts_user"."id" = 2)
-- Corrigido: a busca já exige o próprio solicitante; não encontra nada e dá 404, igual ao inexistente
SELECT … FROM "accounts_user" WHERE "accounts_user"."id" = 5                                     -- autenticação
SELECT … FROM "accounts_user" WHERE ("accounts_user"."barbershop_id" = 1 AND "accounts_user"."id" = 5 AND "accounts_user"."id" = 2)
SELECT … FROM "accounts_user" WHERE ("accounts_user"."barbershop_id" = 1 AND "accounts_user"."id" = 5 AND "accounts_user"."id" = 999999)
```

### 25.8 Limitações e riscos

1. **SEC-12 (P3, novo, registrado e não corrigido): a mesma diferença 403 × 404 dentro da própria barbearia, em outras operações.**
   - **Onde aparece:**
     - PATCH e PUT de `/users/{id}/` por cliente ou barbeiro em outro usuário da barbearia dão 403, contra 404 para um usuário de outra barbearia ou inexistente. A causa é a mesma do PER-13, no `update` e no `partial_update`. Medido na sondagem: `api/per13-resumo-http-sql.txt`, bloco SEC-12.
     - No `exclude_appointment_id` (seção 24), o cliente com o horário de outro cliente, ou o barbeiro com o de outro barbeiro, recebe 403, contra 404 para o inexistente.
   - **Impacto:** baixo. Revela só que um ID existe na própria barbearia, sem dados.
   - **Correção possível, com autorização:** estender o escopo do PER-13 a `update` e `partial_update` (e, no `exclude_appointment_id`, buscar pelo queryset que cada papel enxerga). Isso troca esses 403 por 404 e exige atualizar os testes que os fixam.
2. **Mensagem do 404 em inglês.** "No User matches the given query." vem do Django, é igual em todos os casos e revela só o nome do model.
3. **Canal de tempo:** não medido. As buscas não autorizadas e a inexistente são a mesma consulta e não encontram linha.
4. **Fora do escopo, continuam abertos:** TEN-03, TEN-04, API-03, AUTH-03 e BUS-20.
5. **Não verificado:** produção e banco real. Este relatório **não declara o projeto pronto para produção.**

### 25.9 Situação final do SEC-10

**SEC-10: ✅ resolvido e verificado** no ambiente de testes. A definição original (seção 13) tem três pontos, e os três estão corrigidos e cobertos por evidências:

| Ponto da definição original | Correção | Evidência |
|---|---|---|
| 1. Para IDs de outra barbearia, "não pertence à sua barbearia" × "Pk inválido" para inexistentes, nos campos do corpo | Seção 22: campos relacionais com escopo de tenant | 288 de 288 pedidos sem oráculo, por instância, com `DEBUG` True e False; testes `ReferenciasCruzadasTests`; nenhuma leitura sem escopo |
| 2. O `exclude_appointment_id` distingue "não pertence" de "não encontrado" | Seção 24: busca com a barbearia na própria consulta | MT-AV-02 conforme; 6 de 6 comparações iguais; `appointments/test_sec10.py` |
| 3. Um cliente que consulta outro cliente por ID recebe 403, que revela a existência, em vez de 404 (PER-13) | Esta seção: a leitura de detalhe limitada ao próprio cadastro na consulta | 0 diferenças em 130 pedidos por instância, com `DEBUG` True e False; `accounts/test_per13.py`; SQL com o solicitante no WHERE |

Também ficou fechada a ampliação registrada na auditoria de isolamento, os filtros (MT-FI-01, seção 22). A variante nas escritas e no `exclude_appointment_id`, dentro da própria barbearia, não faz parte desses três pontos e foi registrada como SEC-12.

| | Após o `exclude_appointment_id` | Após o PER-13 |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 28 |
| P3 | 38 | 38 (−SEC-10, resolvido; +SEC-12, novo) |
| **Abertos** | 64 dos 70 originais + 5 novos = 69 | **63 dos 70 originais + 6 novos = 69** |

**Próximo passo:** aguarda a revisão do dono. Nem o TEN-03 nem o SEC-12 foram iniciados.

---

## 26. Investigação do TEN-03 — 15/11/2026

**Escopo autorizado:** só investigar o TEN-03, a exposição da existência de e-mails usados em outras barbearias. Nada foi corrigido. A regra de unicidade é uma decisão de produto e fica com o dono. TEN-04 e SEC-12 não foram iniciados.

**Restrições cumpridas:**

- **Código:** nenhum arquivo de produção, teste, permissão, serializer, model, view, settings, `.env` ou frontend foi alterado. Nenhuma dependência foi atualizada.
- **Migrações:** nenhuma criada nem aplicada. O `makemigrations --check` responde "No changes detected".
- **Etapas anteriores preservadas:** a contenção (só `JSONRenderer`), o TEN-01, o TEN-02, o `exclude_appointment_id` e o PER-13. A suíte completa passou sem alteração.
- **Bancos:** o `barbershop_db` real e o PostgreSQL do Docker (porta 5433) não foram usados. Os testes com escrita rodaram num **PostgreSQL 18.3 descartável** (`initdb` no diretório temporário, só TCP em `127.0.0.1:55432`), já apagado.
- **Dados:** só fictícios, em domínios reservados `.test`.
- **Repositório:** sem commit, push ou merge, e sem comandos destrutivos. As alterações locais e as evidências anteriores foram preservadas.

Evidências em [`docs/auditoria/evidencias-2026-11-15/ten-03/`](auditoria/evidencias-2026-11-15/ten-03/README.md).

### 26.1 Resumo

| Item | Situação |
|---|---|
| **Causa raiz** | **Confirmada.** O e-mail é único em toda a plataforma no model (`accounts/models.py:29`, `unique=True`) e no banco (`UNIQUE (email)`, restrição `accounts_user_email_key`). Ele é o `USERNAME_FIELD`. O DRF gera desse campo um `UniqueValidator` sobre **todos** os usuários, sem filtro de barbearia, nos três serializers que gravam e-mail. Esse validador responde 400 "usuário com este e-mail já existe." só quando o e-mail está em uso |
| **Alcance** | Maior do que o registrado em 13/11. Além do admin e do cadastro público, **qualquer cliente ou barbeiro** com barbearia consegue sondar trocando o próprio e-mail. Existem variantes **sem efeito colateral** para anônimo, admin e cliente. Há ainda um caminho por **erro 500**, ao variar a caixa do domínio |
| **O que revela** | Só a existência do e-mail na plataforma, inclusive de contas inativas e do superusuário. Não revela barbearia, nome nem papel. O admin de A distingue, além disso, "está na minha barbearia" (porque pode listá-la) de "está em outra" |
| **Achados novos** | **AUTH-04 (P2):** a recuperação de senha pode mandar o token de **outra conta** quando existe uma variação de caixa do e-mail. **AUTH-05 (P3):** o e-mail não tem normalização de caixa coerente: aceita duplicatas por caixa, dá 500 no cadastro e o login diferencia caixa. Registrados, não corrigidos (26.6) |
| **Alternativas** | A (único global), B (único por barbearia), C (manter e mudar o fluxo, em três níveis), D (aceitar o risco com mitigação) e E (identidade global com vínculos). Comparadas em 26.7 |
| **Recomendação técnica** | Manter o e-mail único global (A). Corrigir a normalização de caixa (AUTH-04 e AUTH-05). Para o TEN-03, escolher entre aceitar o risco residual com mitigação (D) ou o fluxo de confirmação por e-mail e convites (C3), depois da apresentação. **A decisão de produto continua pendente** (26.8) |
| **TEN-03** | **Continua aberto (P3).** Não foi marcado como resolvido |

### 26.2 Arquitetura atual de unicidade e autenticação

| # | Pergunta | Resposta confirmada no código atual |
|---|---|---|
| 1 | O e-mail é único no model ou só no serializer? | **No model**, e daí em diante em tudo. `email = models.EmailField('e-mail', unique=True)` (`accounts/models.py:29`). Não há `Meta.constraints` nem `unique_together`. Os serializers não definem validação própria: herdam do model o `UniqueValidator` (`arquitetura/validadores-por-serializer.txt`) |
| 2 | Existe `UNIQUE` no banco? | **Sim, global e sensível à caixa.** A `accounts.0001_initial` cria `"email" varchar(254) NOT NULL UNIQUE` (restrição `accounts_user_email_key`, btree) e o índice `accounts_user_email_b2644a56_like` (`varchar_pattern_ops`). Nenhuma migração posterior altera o campo. Verificado no banco descartável criado pelas migrações (`sql/esquema-accounts_user.txt`). O esquema do banco real já tinha sido conferido como idêntico (seção 20) e não foi consultado agora |
| 3 | O e-mail é o identificador de login? | **Sim.** `POST /api/v1/auth/login/` (`CustomTokenObtainPairView`, simplejwt) chama o `authenticate()` do Django. O `ModelBackend` busca com `get_by_natural_key`, um `get(email=<valor>)` **exato** (SQL: `WHERE "accounts_user"."email" = '…' LIMIT 21`) |
| 4 | `USERNAME_FIELD` | `'email'` (`accounts/models.py:49`); `REQUIRED_FIELDS = ['nome']`; `AUTH_USER_MODEL = 'accounts.User'`; `AUTHENTICATION_BACKENDS` é o padrão (`ModelBackend`) |
| 5 | Como a barbearia é identificada na autenticação? | **Não é informada no login.** Só e-mail e senha. A barbearia vem da linha encontrada (`User.barbershop`, FK única). A cada pedido, o `JWTAuthentication` carrega o usuário pelo claim `user_id`, e o escopo sai de `request.user.barbershop_id` (`config/tenancy.py`, `barbearia_do_pedido`). O claim `barbershop_id` do token (`accounts/serializers.py:336`) não é lido nem pelo backend nem pelo frontend, que usa `/users/me/`. Não existe slug, subdomínio nem cabeçalho de barbearia |
| 6 | Uma pessoa pode ter contas em barbearias diferentes? | **Só com e-mails diferentes.** Com o mesmo endereço, não. A exceção é acidental: variações de caixa passam, como mostra o AUTH-05 |
| 7 | Um usuário pode pertencer a mais de uma barbearia? | **Não.** `barbershop` é uma FK única e anulável (`accounts/models.py:40`). Não há tabela de vínculos, e o `tipo_perfil` é por conta. O superusuário é a exceção explícita entre barbearias, por flag, não por vínculo. O onboarding (`BarbershopViewSet.perform_create`) move uma conta sem barbearia para a barbearia que ela cria, uma única vez |
| 8 | Quais serializers validam unicidade? | `PublicRegistrationSerializer`, `UserCreateSerializer` e `UserSerializer`. Os três têm `UniqueValidator(queryset=User._default_manager, lookup='exact')`, sem filtro de barbearia e com a mensagem "usuário com este e-mail já existe.". No Django Admin, só para a equipe, os formulários `CustomUserCreationForm` e `CustomUserChangeForm` fazem o `validate_unique` do ModelForm. `CustomTokenObtainPairSerializer` e `PasswordResetRequestSerializer` não validam unicidade. O `email` do `BarberSerializer` é só leitura, e o de `Barbershop` é contato, sem unicidade |
| 9 | Quais endpoints cadastram ou alteram e-mail? | `POST /api/v1/auth/register/`, `POST /api/v1/users/`, `PATCH` e `PUT` `/api/v1/users/{id}/`, e o Django Admin (`/admin/accounts/user/`, equipe). Nenhum outro |
| 10 | A validação muda conforme o papel? | **O validador é o mesmo para todos.** Muda só se o pedido chega à validação, conforme a tabela 26.3. A ordem do DRF importa: os validadores de campo (`UniqueValidator`) rodam antes do `validate()`, onde ficam os validadores de senha, e o `validate()` não roda se algum campo já falhou. Por isso o pedido com senha fraca devolve só o erro de e-mail quando o e-mail existe, e só o de senha quando ele está livre |

**Normalização atual do e-mail:**

| Variação | Validação (DRF) | Gravação | Login | Recuperação de senha |
|---|---|---|---|---|
| Espaços antes ou depois | O `EmailField` corta os espaços (`trim_whitespace`) **antes** do `UniqueValidator`; dá o mesmo 400 do e-mail exato | Sem espaços | Corta os espaços (`CharField`): entra (L06) | Corta os espaços |
| Maiúsculas na parte local | `lookup='exact'`: **não** encontra o existente | Grava como digitado: **conta duplicada** (R06, C08, P15) | **Diferencia caixa**: senha correta com outra caixa dá 401 (L04) | `email__iexact` + `.first()` ordenado por `nome` (AUTH-04) |
| Maiúsculas no domínio | Não encontra o existente | No cadastro e na criação, o `create_user` aplica `normalize_email`, que só põe o **domínio** em minúsculas, **depois** da validação: o `INSERT` colide e dá **500** (R07, C09). Na edição não há normalização: grava `…@BETA.TEST`, outra duplicata (P16) | Diferencia caixa: 401 (L05) | Como acima |

### 26.3 Endpoints afetados e quem chega à validação

| Endpoint | Papel | Chega ao `UniqueValidator`? | Oráculo | Limite de taxa atual |
|---|---|---|---|---|
| `POST /api/v1/auth/register/` | Anônimo | Sim | **Sim**, inclusive sem efeito colateral (R04 × R05) e por 500 (R07 × R08) | `register`: 10/hora por IP. Só `ScopedRateThrottle`; o `anon` não se aplica |
| `POST /api/v1/users/` | Admin | Sim | **Sim**, inclusive sem efeito colateral (C04 × C05) e por 500 (C09) | Só o padrão `user`: 1000/hora por conta |
| `POST /api/v1/users/` | Cliente, barbeiro ou conta sem barbearia | Não: 403 (`IsAdminRole`) antes da validação | Não (C12 a C14) | — |
| `POST /api/v1/users/` | Superusuário sem barbearia | Sim, e depois falha em "O administrador precisa pertencer a uma barbearia." | Irrelevante: o superusuário lista todos os usuários | — |
| `PATCH`/`PUT` `/api/v1/users/{próprio}/` | Cliente, barbeiro, admin | Sim | **Sim**, inclusive sem efeito colateral (P05 × P06) | `user`: 1000/hora por conta |
| `PATCH`/`PUT` `/api/v1/users/{id}/`, usuário da própria barbearia | Admin | Sim | **Sim** (P11, P21) | `user`: 1000/hora |
| `PATCH` `/api/v1/users/{id}/`, outro usuário da mesma barbearia | Cliente ou barbeiro | Não: 403 antes (SEC-12, mantido) | Não (P14) | — |
| `PATCH` `/api/v1/users/{id}/`, usuário de outra barbearia | Admin | Não: 404 (queryset) | Não (P13) | — |
| `PATCH` `/api/v1/users/{próprio}/` | Conta sem barbearia | Não: 404 (`queryset.none()`, `accounts/views.py:214`) | Não (P19), mas tem o cadastro público | — |
| `POST /api/v1/auth/login/` e `/auth/password/reset/` | Anônimo | Não há validação de unicidade | **Não**: 401 e 204 idênticos (L01 a L03, L07 e L08). A falha é outra, o AUTH-04 | `login` 5/min; `password_reset` 5/hora |

### 26.4 Comportamento reproduzido

**Montagem:**

- A API de laboratório roda o código atual, sem alteração, com `DEBUG=False` e só JSON, sobre o PG 18.3 descartável.
- Barbearias A (`id=1`) e B (`id=2`).
- Contas:
  - de A: admin, barbeiro e dois clientes;
  - de B: admin, barbeiro, um cliente e um cliente inativo;
  - uma conta sem barbearia e um superusuário.
- **58 cenários:** 11 de cadastro público, 16 de criação, 22 de edição e 9 de login e recuperação.
- Cada cenário parte do seed restaurado, com fotografia do banco antes e depois e o SQL do servidor entre marcadores.

A matriz completa, com o corpo integral de cada resposta, está em `MATRIZ-TEN-03.md`. Os cenários pedidos:

| Cenário pedido | IDs | Status | Resposta | Criou ou alterou | Consulta de existência |
|---|---|---|---|---|---|
| E-mail nunca utilizado | R01, C01, P01, P09, P22 | 201 / 200 | O registro criado ou alterado | Sim | Sim, sem filtro de barbearia |
| E-mail de outro usuário da **mesma** barbearia | C02 (admin), P03 (cliente), P10 (admin) | 400 | `{"email":["usuário com este e-mail já existe."]}` | Não | Sim, sem filtro. No P03, o cliente descobre que outro cliente da barbearia usa o e-mail, algo que ele não conseguiria listar |
| E-mail de usuário de **outra** barbearia | R03, C03, C06, C07, P04, P07, P08, P11, P21 | 400 | **Idêntica** à da mesma barbearia | Não | **Sim, sem filtro; encontrou a conta de B** |
| O próprio e-mail na edição | P02, P12 | 200 | O registro, sem mudança | Não | Sim, com `AND NOT (id = <próprio>)` |
| E-mail de outro usuário na edição | P03, P04, P10, P11, P18, P20, P21 | 400 | `{"email":[…já existe.]}` | Não | Sim |
| Maiúsculas e minúsculas | R06, R07, R08, C08, C09, P15, P16, L04, L05, L09 | 201 / **500** / 200 / 401 | Parte local: cria duplicata (201/200). Domínio: **500** quando o e-mail existe e 201 quando está livre. Login: 401 | Duplicata em R06, C08, P15 e P16 | Sim, exata: não encontra a variação |
| Espaços antes ou depois | R09, C10, P17, L06 | 400 / 200 | Iguais ao e-mail exato; o login com espaços entra | Não | Sim, com o valor já sem espaços |
| Conta inativa | R10, C11, P18, L03 | 400 / 401 | A conta inativa também é revelada pelo 400; no login, 401 igual | Não | Sim |

**Pares que revelam a existência sem criar nem alterar nada:**

| Par | E-mail de B (existe) | E-mail livre |
|---|---|---|
| Cadastro público, senha `12345678` (R04 × R05) | 400 `{"email":["usuário com este e-mail já existe."]}` | 400 `{"password":["Esta senha é muito comum.","Esta senha é inteiramente numérica."]}` |
| Admin A cria cliente, senha `12345678` (C04 × C05) | 400 `{"email":[…]}` | 400 `{"password":[…]}` |
| Cliente A1 troca o e-mail e envia `nome` vazio (P05 × P06) | 400 `{"email":[…],"nome":["Este campo não pode ser em branco."]}` | 400 `{"nome":[…]}` |
| Domínio em maiúsculas, no cadastro público (R07 × R08) | **500** HTML "Server Error (500)" | 201 (cria a conta) |

**Tempo:** o 201 leva cerca de 250 ms, por causa do hash da senha, e o 400 entre 13 e 21 ms. Nos pares sem efeito colateral, os tempos ficam na mesma faixa (13 a 19 ms). Nem é preciso medir: o status e o corpo já revelam.

### 26.5 Consultas SQL relevantes

Registradas pelo próprio PostgreSQL descartável (`sql/sql-por-cenario.txt`):

```sql
-- C03: admin A cria cliente com o e-mail de cliente de B. A consulta não filtra barbearia e encontra a conta de B.
SELECT … FROM "accounts_user" WHERE "accounts_user"."id" = 1 LIMIT 21                        -- autenticação (JWT)
SELECT 1 AS "a" FROM "accounts_user" WHERE "accounts_user"."email" = 'cliente.b@beta.test' LIMIT 1
-- P04: edição do próprio cadastro. Exclui só o próprio id.
SELECT 1 AS "a" FROM "accounts_user" WHERE ("accounts_user"."email" = 'cliente.b@beta.test' AND NOT ("accounts_user"."id" = 3)) LIMIT 1
-- R07: domínio em maiúsculas. A validação exata não encontra; o create_user normaliza o domínio e o INSERT colide.
SELECT 1 AS "a" FROM "accounts_user" WHERE "accounts_user"."email" = 'cliente.b@BETA.TEST' LIMIT 1
INSERT INTO "accounts_user" (…, "email", …) VALUES (…, 'cliente.b@beta.test', …)
ERROR:  duplicate key value violates unique constraint "accounts_user_email_key"
DETAIL:  Key (email)=(cliente.b@beta.test) already exists.
-- L04: o login é exato (diferencia caixa).
SELECT … FROM "accounts_user" WHERE "accounts_user"."email" = 'Cliente.A1@alfa.test' LIMIT 21
-- L07 a L09: a recuperação não diferencia caixa e escolhe UMA conta pela ordem do nome.
SELECT … FROM "accounts_user" WHERE (UPPER("accounts_user"."email"::text) = UPPER('cliente.b@beta.test') AND "accounts_user"."is_active") ORDER BY "accounts_user"."nome" ASC LIMIT 1
```

Em todos os cenários com consulta de existência, ela é **global**: nenhuma tem `barbershop_id` no WHERE.

### 26.6 Achados novos relacionados (registrados, não corrigidos)

#### AUTH-04 — Recuperação de senha pode enviar o token de outra conta

> **Atualização de 15/11/2026:** investigado na [seção 28](#28-investigação-e-plano-do-auth-04-e-do-auth-05--15112026). Uma precisão sobre o título: o token vai sempre para o e-mail gravado na própria conta para a qual foi gerado. O que se desvia é a conta recuperada, que passa a ser a do terceiro. **Continua aberto.**
>
> **Atualização de 15/11/2026:** ✅ resolvido e verificado no ambiente de testes ([seção 31](#31-correção-do-auth-04-e-do-auth-05-com-e-mail-normalizado-em-ascii--15112026)). A recuperação procura a conta pelo e-mail normalizado, com igualdade exata, e uma variação de caixa não pode mais existir. A `accounts.0006` ainda não foi aplicada no banco real.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P2 | Backend | `accounts/serializers.py:391` (`filter(email__iexact=…, is_active=True).first()`), combinado com o AUTH-05 | Confirmado (L09) | **Novo** |

- **Descrição.**
  - Um anônimo cadastra `Cliente.B@beta.test`, uma variação de caixa do e-mail de uma vítima, com um nome que vem antes na ordem alfabética.
  - A partir daí, toda recuperação pedida com `cliente.b@beta.test` escolhe a conta do terceiro.
  - Na sondagem, o e-mail saiu para `Cliente.B@beta.test` com o `uid` da conta 18 (a do terceiro), e não da 7 (a da vítima).
- **Impacto.**
  - A vítima perde a recuperação de senha enquanto a variação existir.
  - Na prática, a mensagem cai na caixa postal da vítima, porque os provedores não diferenciam caixa na parte local. Mas o token é da conta do terceiro.
  - Não há tomada da conta da vítima.
- **Correção possível, com autorização:** a mesma do AUTH-05. Com unicidade sem diferenciar caixa, o `.first()` deixa de ser ambíguo.

#### AUTH-05 — E-mail sem normalização de caixa coerente

> **Atualização de 15/11/2026:** investigado na [seção 28](#28-investigação-e-plano-do-auth-04-e-do-auth-05--15112026). Efeitos novos: o login logo após o cadastro falha quando o domínio foi digitado com maiúscula, e há 500 em 15 de 15 pedidos simultâneos com o mesmo e-mail. O plano prevê migração. **Continua aberto.**
>
> **Atualização de 15/11/2026:** ✅ resolvido e verificado no ambiente de testes ([seção 31](#31-correção-do-auth-04-e-do-auth-05-com-e-mail-normalizado-em-ascii--15112026)). Há uma regra única em todos os caminhos, garantida pelo banco com `CHECK` e `UNIQUE (LOWER(email))`, e sem 500 em pedidos simultâneos. A `accounts.0006` ainda não foi aplicada no banco real.

| Severidade | Camada | Local | Confiança | Estado |
|---|---|---|---|---|
| P3 | Backend | `UniqueValidator` com `lookup='exact'`; `accounts/managers.py:43` (`normalize_email` só no `create_user`, depois da validação); `UserSerializer.update` sem normalização; banco `UNIQUE (email)` sensível à caixa; login exato | Confirmado | **Novo** |

- **Descrição.**
  - A validação, o banco e o login comparam o e-mail exatamente como foi digitado.
  - O `create_user` põe só o domínio em minúsculas, e só depois de validar.
  - A recuperação compara sem diferenciar caixa.
- **Efeitos medidos.**
  - **Contas duplicadas** do mesmo endereço: R06, C08, P15 e P16.
  - **500** com página HTML no cadastro e na criação quando o domínio vem em maiúsculas e o e-mail existe (R07, C09). É um segundo oráculo, que nenhuma troca de mensagem fecha.
  - **Login recusado** com a senha certa e outra caixa (L04, L05). O frontend corta espaços, mas não converte para minúsculas.
- **Correção possível, com autorização:**
  - normalizar (cortar espaços e converter para minúsculas) em todos os caminhos de escrita e no login;
  - usar validação sem diferenciar caixa;
  - criar um índice único funcional `lower(email)`, que exige migração (26.9).

### 26.7 Alternativas avaliadas

#### Alternativa A — E-mail globalmente único (a regra atual)

- **Modelo, banco e autenticação:** já é a regra atual, e compatível com tudo. O `ModelBackend` exige `USERNAME_FIELD` único: o check `auth.E003`, em `django/contrib/auth/checks.py`, é **erro** quando só o `ModelBackend` está configurado. Login, recuperação e JWT continuam inequívocos.
- **Banco:** a `UNIQUE (email)` já existe. Falta a unicidade sem diferenciar caixa (AUTH-05).
- **Cadastro e edição:** nenhum fluxo muda.
- **Privacidade: a regra, sozinha, é o oráculo.** A simulação de laboratório (`simulacoes/simulacao-alternativa-c.txt`) mediu, em cada variante, 6 pares de pedidos (e-mail de B × e-mail livre):

  | Variante | Pares que ainda distinguem | Por quê |
  |---|---|---|
  | Atual | 6 de 6 | Mensagens e campos diferentes |
  | C1: **só a mensagem genérica** ("Não foi possível usar este e-mail.") | **6 de 6** | O campo `email` aparece no erro só quando o e-mail existe, e o sucesso (201/200) só acontece quando está livre |
  | C2: **status e corpo padronizados em todo 400** | **3 de 6** | Fecha os pares sem efeito colateral (senha fraca, nome vazio). Não fecha **400 × 201/200** quando o pedido é válido, nem o **500 × 201** do domínio em maiúsculas |

  Trocar a mensagem **não resolve**. Padronizar status e corpo **não resolve**: enquanto a operação puder dar certo para um e-mail livre e der errado para um ocupado, o próprio sucesso revela a existência.
- **Contas existentes:** nenhum impacto. Com a normalização, os e-mails com maiúsculas precisam ser convertidos, depois de conferir colisões no banco real (consulta em 26.9).
- **Frontend:** nenhum impacto.

#### Alternativa B — E-mail único por barbearia

- **Modelo:** trocar `unique=True` por `UniqueConstraint(Lower('email'), 'barbershop', nulls_distinct=False)`.
  - Sem `unique=True` no `USERNAME_FIELD`, o Django acusa o **`auth.E003` (erro)** com o `ModelBackend` padrão.
  - Seria preciso um backend próprio, e aí o check vira o aviso `auth.W004`.
- **Autenticação: deixa de ser inequívoca.** A simulação de laboratório (`simulacoes/simulacao-alternativa-b.json`) trocou a restrição dentro de uma transação desfeita e criou duas contas com o mesmo e-mail, em A e em B.
  - O `POST /auth/login/` com a senha da conta de A respondeu **500** (`MultipleObjectsReturned: get() returned more than one User -- it returned 2!`).
  - Para funcionar, o login precisaria de um identificador de barbearia, **que hoje não existe**: `Barbershop` não tem slug, e não há subdomínio nem rota por barbearia. Isso exige um campo novo, único e preenchido para as barbearias existentes, rotas ou subdomínios no frontend, e cuidado com `ALLOWED_HOSTS`, CORS e o caminho do cookie de refresh.
  - A outra opção, "e-mail e senha, depois escolher a barbearia", testa a senha contra várias contas: revela em quais a combinação vale e multiplica o custo de hash.
- **Recuperação de senha:** fica ambígua. Na simulação, o token foi para uma só das duas contas, e a outra ficou sem recuperação. O pedido e o link teriam de carregar a barbearia.
- **Tokens:** o JWT continua inequívoco depois do login, porque usa o `user_id`.
- **Cadastro público e contas sem barbearia:**
  - Uma `UNIQUE` comum trata `NULL` como distinto. Na simulação, aceitou duas contas sem barbearia com o mesmo e-mail.
  - O `NULLS NOT DISTINCT` (PG 15+, `nulls_distinct=False` no Django 5.0) resolve isso, mas mantém o oráculo no cadastro público entre contas sem barbearia.
  - Depois do onboarding, o e-mail do dono sai desse espaço, e um novo cadastro público com o mesmo endereço passa. O login volta a ficar ambíguo, entre a conta sem barbearia e a da barbearia.
- **Contas existentes:** os dados atuais já são únicos no global, portanto também por barbearia. A migração passaria nos dados.
- **Oráculo:** só **parcialmente fechado**.
  - Fecha entre barbearias no `POST /users/` e no `PATCH`: o admin de A cria uma conta própria para a pessoa.
  - Continua dentro da barbearia (o cliente que troca o próprio e-mail descobre os e-mails dos outros clientes) e no cadastro público.
- **Produto:** uma pessoa que é cliente de duas barbearias passa a ter duas contas e duas senhas. O e-mail deixa de identificar a pessoa.
- **Frontend:** login, recuperação, cadastro, rotas e `AuthContext`.
- **Risco de regressão:** muito alto.
- **Conclusão:** como o login não fica inequívoco sem um redesenho, esta alternativa **não é recomendada**.

#### Alternativa C — Manter a unicidade global e mudar o fluxo

Três níveis diferentes:

1. **Esconder a mensagem (C1):** não resolve. É a simulação acima.
2. **Padronizar status e corpo (C2):** reduz o oráculo, mas não o impede. Também é a simulação acima.
3. **Impedir a enumeração de fato (C3):** a resposta precisa ser a mesma para e-mail livre e ocupado, **e** o sucesso não pode ser visível para quem pediu. Isso só se consegue levando a confirmação para o dono da caixa postal:
   - **Cadastro público:** sempre 202 "Se o e-mail puder ser usado, enviamos um link para concluir o cadastro". E-mail livre: a conta nasce inativa e recebe um link de confirmação. E-mail ocupado: o dono recebe um aviso ("alguém tentou criar uma conta com seu e-mail; se foi você, recupere a senha"). **O frontend perde o login automático depois do cadastro** e ganha uma página de confirmação.
   - **Troca do próprio e-mail:** a troca fica pendente. A resposta é sempre "enviamos um link para o novo endereço", e só o link efetiva a troca. Se o endereço estiver ocupado, segue um aviso ou nada.
   - **Admin cria cliente ou barbeiro:** vira **convite**. A resposta é sempre 202 "convite enviado".
     - E-mail livre: o convidado define a senha e entra na barbearia.
     - E-mail ocupado: o convidado é avisado de que já tem conta. Como a FK é única, ele não entra na barbearia com aquele e-mail.
     - O admin não distingue "não aceitou" de "ocupado", e a lista de convites mostra os dois do mesmo jeito.
     - **Impacto de produto:** o admin deixa de definir a senha. Um cliente novo só pode ser agendado depois de aceitar o convite. Criar a conta pendente na hora, visível ao admin, recriaria o oráculo.
   - **Admin edita o e-mail de um cliente:** fica pendente até a confirmação pelo novo endereço.
   - **Infraestrutura:** precisa de envio de e-mail real. As settings não configuram `EMAIL_HOST` nem `EMAIL_BACKEND` próprio, então vale o padrão SMTP local. A recuperação de senha atual usa `fail_silently=True`. **A entrega de e-mail em produção não foi verificada.**
   - **Migração:** é opcional. Uma variante usa tokens assinados (`django.core.signing`) e `is_active=False` até a confirmação. Para listar convites, é preciso uma tabela nova.
   - **Testes:** muda o `accounts/tests.py::test_user_registration_duplicate_email`, que espera 400 com `email`, e todos os que esperam 201 com login logo em seguida, além dos testes de frontend.
   - **Esforço** médio a alto, com impacto grande na experiência de uso.

#### Alternativa D (outra) — Aceitar o risco residual com mitigação

- Manter a regra A. Corrigir AUTH-04 e AUTH-05.
- Criar um limite específico para as escritas que trocam ou criam e-mail. Hoje o `PATCH` e o `POST` de `/users/` só têm o limite geral de 1000/hora por conta.
- Registrar em log as recusas repetidas e documentar a aceitação do risco. A mensagem genérica é opcional e cosmética.
- **Não resolve o TEN-03:** só reduz a taxa de sondagem, e o cadastro público continua permitindo 10/hora por IP.
- Esforço e risco baixos. Nenhum impacto no frontend.

#### Alternativa E (outra) — Identidade global com vínculos por barbearia

- Uma conta por e-mail, global, e N barbearias por um vínculo `(user, barbershop, papel, ativo)`.
- O admin "adiciona" um cliente por e-mail com um convite. O vínculo nasce na aceitação, e a resposta é igual para conta existente ou nova.
- **Fecha o oráculo** e permite que uma pessoa seja cliente de várias barbearias, um ganho de produto.
- **Exige refatorar todo o escopo**: `user.barbershop_id` e `tipo_perfil` aparecem em `config/tenancy.py`, nas permissões, nos serializers, nas views e nas regras do BUS-01. Exige também escolher a barbearia ativa por pedido e um seletor no frontend, além de migrar os dados da FK para os vínculos.
- É uma mudança de arquitetura, para depois da apresentação.

#### Comparação

| | A, só a regra atual | A + D (normalização e limites) | B | C3 | E |
|---|---|---|---|---|---|
| Fecha o oráculo entre barbearias | Não | **Não** (só reduz a taxa) | Parcialmente | **Sim** | **Sim** |
| Login inequívoco | Sim | Sim | **Não** sem identificador de barbearia (500 na simulação) | Sim | Sim, com a barbearia ativa escolhida |
| Recuperação de senha | AUTH-04 aberto | Corrigida | Ambígua sem barbearia | Corrigida, se feita junto com A + D | Corrigida |
| Migração | Nenhuma | Índice funcional e dados | Restrição, slug com dados, backend | Opcional (tabela de convites) | Grande (vínculos e dados) |
| Contas existentes | Sem efeito | Conversão para minúsculas, se não houver colisão | Compatíveis | Sem efeito | Migradas para vínculos |
| Frontend | Nenhum | Nenhum | Login, recuperação, cadastro, rotas | Cadastro, conta, clientes, barbeiros, páginas novas | Amplo |
| Esforço / risco de regressão | — | Baixo / baixo | Alto / muito alto | Médio-alto / médio | Muito alto / muito alto |
| Viável antes de 17/11 | — | Sim, com autorização para a migração | Não | Não recomendado | Não |

### 26.8 Recomendação técnica (a decisão é do dono)

1. **Manter o e-mail único em toda a plataforma (A).** É a única regra coerente com a autenticação atual sem redesenhá-la: login só por e-mail, FK única de barbearia e `ModelBackend`. A alternativa B quebra a unicidade do login, como a simulação demonstrou, e fecha o oráculo só em parte.
2. **Corrigir o AUTH-04 e o AUTH-05** quando autorizado. Esforço e risco baixos, sem impacto no frontend, e pode ser feito antes de 17/11. Fecha o oráculo por 500, as duplicatas e o desvio da recuperação de senha. **Não fecha o TEN-03.** Exige uma migração e, no banco real, backup e a checagem de colisões antes.
3. **Para o próprio TEN-03, duas opções:**
   - **D, agora:** aceitar o risco residual P3, documentado e com limite específico. O que se revela é só a existência do e-mail, sem dados.
   - **C3, depois da apresentação:** a correção definitiva, com confirmação por e-mail e convites. Depende de entrega de e-mail real e muda o cadastro e a criação de clientes.
   - Recomendação técnica: **D antes de 17/11 e C3 planejada para depois**. A E só faz sentido se o produto quiser clientes em várias barbearias.
4. **Não recomendado:** trocar só a mensagem e declarar o TEN-03 resolvido. A simulação mostrou que o oráculo continua.

**Decisão de produto pendente:**

- a regra de unicidade (A, B ou E);
- o tratamento do TEN-03 (D ou C3);
- se o AUTH-04 e o AUTH-05 entram antes da apresentação.

### 26.9 Migrações possíveis (ilustrativas, não criadas nem executadas)

**A + D (AUTH-05).** O `unique=True` continua, porque o `auth.E003` só aceita unicidade no próprio campo ou numa `UniqueConstraint(fields=('email',))`, e uma restrição funcional não conta. Acrescenta-se:

```python
# accounts/migrations/0006_email_unico_sem_diferenciar_caixa.py — ILUSTRATIVO, NÃO CRIADO
from django.db import migrations, models
from django.db.models.functions import Lower

operations = [
    migrations.RunPython(converter_emails_para_minusculas_se_nao_houver_colisao, migrations.RunPython.noop),
    migrations.AddConstraint(
        model_name='user',
        constraint=models.UniqueConstraint(Lower('email'), name='accounts_user_email_sem_caixa_unico'),
    ),
]
```

Antes, no banco real e só com autorização, rodar estas consultas, que são só de leitura:

```sql
SELECT lower(email), count(*) FROM accounts_user GROUP BY 1 HAVING count(*) > 1;  -- colisões: precisa dar zero linhas
SELECT count(*) FROM accounts_user WHERE email <> lower(btrim(email));            -- quantos seriam convertidos
```

O índice sobre `lower(email)` depende da ordenação do banco. Com o aviso do DB-02 (collation 2.43 × 2.44), convém um `REINDEX` numa etapa autorizada.

**B:**

- `AlterField` do `email`, sem `unique` e com `db_index`;
- `AddConstraint(UniqueConstraint(Lower('email'), 'barbershop', nulls_distinct=False, …))`;
- `AddField` do `Barbershop.slug`, mais um `RunPython` que preenche o slug e um `AlterField` para não nulo;
- um backend de autenticação próprio em `AUTHENTICATION_BACKENDS`.

**C3:** nenhuma, com tokens assinados e `is_active=False` até a confirmação. Para listar convites e trocas pendentes: `CreateModel` de convite (barbearia, e-mail, papel, criado por, hash do token, expiração, aceito em) e de troca de e-mail pendente.

**E:** `CreateModel` do vínculo `(user, barbershop, tipo_perfil, ativo)` com unicidade `(user, barbershop)`, mais um `RunPython` que copia `User.barbershop` e `tipo_perfil`. Os campos antigos saem só depois de migrar o código.

### 26.10 Testes e verificações realizados

| Verificação | Resultado |
|---|---|
| Leitura do código: model, manager, serializers, views, rotas, permissões, settings de autenticação, Django Admin, `config/tenancy.py`, simplejwt e `ModelBackend`, frontend (`RegisterPage`, `LoginPage`, `AccountPage`, `AdminClientsPage`, `AdminBarbersPage`, `PasswordResetRequestPage`, `AuthContext`, `api/endpoints.ts`) | As respostas de 26.2 |
| Validadores gerados pelo DRF por serializer (`arquitetura/validadores-por-serializer.txt`) | Três serializers com `UniqueValidator` global e `exact` |
| Esquema criado pelas migrações no PG 18.3 descartável e `sqlmigrate accounts 0001` (`sql/esquema-accounts_user.txt`) | `UNIQUE (email)` global; nenhuma migração posterior mexe no campo |
| Sondagem HTTP: 58 cenários com o SQL do servidor (`MATRIZ-TEN-03.md`, `api/`, `sql/`) | A matriz de 26.4; consulta de existência sempre global |
| Simulação da Alternativa C: 3 variantes × 6 pares × 4 e-mails, numa transação desfeita | Mensagem genérica: 6 de 6 pares distinguem. Status e corpo padronizados: 3 de 6, mais o 500 |
| Simulação da Alternativa B: restrição trocada numa transação desfeita, com rollback conferido nas restrições do banco | Login 500 (`MultipleObjectsReturned`); recuperação ambígua; duas contas sem barbearia aceitas sem `NULLS NOT DISTINCT` |
| Suíte completa, sem alteração: SQLite e PG 18.3 descartável | **452 testes, OK** nos dois (9 pulados no SQLite) |
| `manage.py check` e `makemigrations --check --dry-run` | Sem problemas; "No changes detected" |
| Hash SHA-256 dos arquivos de código do projeto antes e depois da investigação | Idênticos (nenhum arquivo de código alterado) |

**Incidente de laboratório, sem efeito fora dele:** a primeira versão do script da simulação B tinha o `raise` de desfazer fora do bloco transacional. Numa das execuções, a troca de restrição ficou gravada no banco de laboratório `t3_lab`. Esse banco foi apagado e recriado, o script foi corrigido, e a execução registrada termina com `accounts_user_email_key` restaurada e zero usuários. O banco da sondagem, o banco real e o Docker não foram afetados.

### 26.11 Limitações

1. **Banco real não consultado,** por instrução. A existência de e-mails com maiúsculas ou de colisões por caixa no `barbershop_db` não foi verificada. As consultas de 26.9 ficam para uma etapa autorizada.
2. **Entrega de e-mail em produção não verificada.** É pré-requisito da C3.
3. **Os limites de taxa foram relaxados na instância de laboratório** para a matriz caber. Os limites reais (26.3) foram lidos do código, não medidos.
4. **O Django Admin não foi sondado.** Ele é restrito à equipe, que já enxerga todos os usuários.
5. **SEC-12 mantido.** Os 403 dentro da barbearia (P14) seguem como registrado na seção 25.

### 26.12 Situação e contagem

**TEN-03: continua aberto (P3).** A causa foi confirmada, o comportamento foi reproduzido e as alternativas foram avaliadas. Aguarda a decisão de produto e nada foi corrigido.

| | Após o PER-13 | Após a investigação do TEN-03 |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 28 | 29 (+AUTH-04) |
| P3 | 38 | 39 (+AUTH-05; o TEN-03 continua) |
| **Abertos** | 63 dos 70 originais + 6 novos = 69 | **63 dos 70 originais + 8 novos = 71** |

**Próximo passo:** o dono decide a regra de unicidade e o tratamento do TEN-03. TEN-04 e SEC-12 não foram iniciados.

---

## 27. Mitigação D do TEN-03: limite de tentativas — 15/11/2026

**Decisões do dono (15/11/2026):**

- manter o e-mail único em toda a plataforma (A);
- adotar um limite específico de tentativas como mitigação temporária do TEN-03 (D);
- planejar a confirmação por e-mail e os convites (C3) para depois da apresentação;
- tratar AUTH-04 e AUTH-05 antes da apresentação, numa etapa separada e prioritária;
- **não** marcar o TEN-03 como resolvido.

**Escopo autorizado:** só a mitigação D. AUTH-04, AUTH-05, TEN-04 e SEC-12 não foram tocados.

**Restrições cumpridas:**

- **Código:**
  - **Alterado:** `accounts/views.py` e `config/settings.py`.
  - **Novo:** o módulo `accounts/throttles.py`.
  - **Intactos:** serializers, models, managers, permissões, a regra de unicidade, o login, a recuperação de senha, o `.env` e o frontend.
- **Testes:**
  - um arquivo novo;
  - a taxa nova acrescentada às duas settings de teste;
  - uma linha acrescentada a dois testes antigos de throttle (27.6).
- **Migrações:** nenhuma. A solução usa o cache, como os limites que já existiam. O `makemigrations --check` responde "No changes detected".
- **Etapas anteriores preservadas:** a contenção (só `JSONRenderer`), o TEN-01, o TEN-02, o SEC-10 e o PER-13, com os testes de todos eles passando.
- **Bancos:** o banco real e o PostgreSQL do Docker não foram usados. Os testes com escrita rodaram em SQLite em memória e num **PostgreSQL 18.3 descartável** (`127.0.0.1:55432`), já apagado.
- **Repositório:** sem commit, push ou merge, e sem comandos destrutivos. As alterações locais, os documentos e as evidências anteriores foram preservados.

Evidências em [`docs/auditoria/evidencias-2026-11-15/ten-03-mitigacao-d/`](auditoria/evidencias-2026-11-15/ten-03-mitigacao-d/README.md).

### 27.1 Resumo

| Item | Situação |
|---|---|
| **O que foi feito** | Limites próprios, por hora e por dia, nos três fluxos em que a investigação demonstrou o oráculo: cadastro público, criação de usuário e troca de e-mail. Esgotado o limite, a resposta é **429 antes da validação**: igual para e-mail existente e livre, sem consultar a unicidade e sem criar nem alterar nada |
| **Chave do limite** | Sempre **quem pede**: a conta autenticada ou, para o anônimo, a origem. **Nunca o e-mail nem a conta-alvo.** Um terceiro não consegue gastar a cota da vítima |
| **Uso legítimo** | A troca de e-mail só conta quando o e-mail enviado difere do atual. Editar o nome, reenviar o próprio e-mail, como fazem "Minha conta" e "Clientes", ou reativar uma conta não contam |
| **Login e recuperação** | Sem alteração: mesmos limites, mesmas respostas |
| **Efeito medido** | Por conta, a criação caiu de até 1000 para 30 tentativas por hora e 100 por dia. A troca de e-mail caiu de até 1000 para 10 por hora e 30 por dia. No cadastro público, as 10 por hora que já existiam ganharam um teto de 20 por dia por origem |
| **TEN-03** | **Continua aberto (P3), agora com mitigação parcial.** Abaixo do limite, a resposta ainda revela a existência do e-mail |
| **Achado novo** | **SEC-13 (P2):** sem `NUM_PROXIES`, os limites por origem, os novos e os que já existiam (inclusive o de login), aceitam o `X-Forwarded-For` enviado pelo cliente. Isso permite contorná-los e gastar a cota do IP de outra pessoa. Registrado, não corrigido: depende da infraestrutura (27.8) |
| **Testes** | 28 novos. Suíte de 452 para **480 testes, OK** no SQLite, no PG 18.3 e no PG com `DEBUG=False`. Os 132 de isolamento e da mitigação passam com `DEBUG=True` |

### 27.2 Fluxos afetados e limites, antes e depois

Os fluxos são os mapeados na seção 26.3. Eles **não** usam o mesmo mecanismo:

| Fluxo | Quem chega à validação | Limite antes | Limite agora |
|---|---|---|---|
| `POST /api/v1/auth/register/` | Anônimo. A view define `throttle_classes` próprio, então os limites padrão `anon` e `user` **não** se aplicam | `register` (`ScopedRateThrottle`): 10/hora por origem | `register`: 10/hora (**sem mudança**) + **`register_day`: 20/dia** por origem |
| `POST /api/v1/users/` | Admin. A permissão (`IsAdminRole`) vem antes do limite: cliente, barbeiro e conta sem barbearia continuam recebendo 403 e não gastam cota | Só o padrão `user`: 1000/hora por conta | `user` + **`user_create`: 30/hora** + **`user_create_day`: 100/dia**, por conta |
| `PATCH`/`PUT /api/v1/users/{id}/` com outro e-mail | Qualquer papel na própria conta; o admin nas contas da sua barbearia | Só o padrão `user`: 1000/hora por conta | `user` + **`email_change`: 10/hora** + **`email_change_day`: 30/dia**, por conta de quem pede, e só quando o e-mail muda |
| `POST /auth/login/`, `/auth/password/reset/`, `/auth/password/reset/confirm/`, `/auth/refresh/`, `/auth/password/change/`, `/auth/logout/` | Não consultam a unicidade (26.3) | `login` 5/min, `password_reset` 5/hora, `password_reset_confirm` 10/hora, `refresh` 10/min, `password_change` 5/hora, `logout` 30/min | **Sem mudança** (verificado por teste e na sondagem) |
| Django Admin (`/admin/`) | Só a equipe, que já vê todos os usuários | — | Sem mudança |

### 27.3 Estratégia

1. **Usa o mecanismo que o projeto já tinha:** os throttles do DRF (`SimpleRateThrottle`), com as taxas em `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` e o mesmo cache dos limites atuais. Não entrou nenhuma dependência nova.
2. **Classes próprias** (`accounts/throttles.py`). `LimitePorSolicitante` é um `ScopedRateThrottle` com o escopo fixo na classe, o que permite ter um limite por hora e outro por dia na mesma view. A chave é `throttle_<escopo>_<id da conta>` ou `throttle_<escopo>_<origem>`, nunca o e-mail.
3. **Cadastro público:** `RegistrationView.throttle_classes = [ScopedRateThrottle, CadastroPublicoPorDiaThrottle]` (`accounts/views.py:133`).
4. **Criação:** `UserViewSet.get_throttles()` (`accounts/views.py:217`) acrescenta os dois limites só na ação `create`. O DRF os checa depois da permissão e antes da validação.
5. **Troca de e-mail:** o limite precisa saber se o e-mail muda, e isso exige a conta. Por isso fica em `UserViewSet.update()` (`accounts/views.py:227`), igual ao `UpdateModelMixin.update`. A ordem é:
   1. `get_object()`, que mantém o escopo e as respostas atuais: 404 fora do alcance e 403 do SEC-12, sem gastar cota;
   2. `tenta_trocar_email()`, que compara o e-mail enviado, sem os espaços das pontas como faz o `EmailField`, com o atual daquela conta;
   3. se muda, `_aplicar_limites()`, com a mesma regra do `check_throttles` do DRF;
   4. só então a validação.

   A comparação usa só um e-mail que quem pede já pode ver: o próprio, ou o de uma conta da barbearia do admin. Não cria um oráculo novo.
6. **Pedidos recusados continuam contando no outro limite.** É o comportamento padrão do DRF: quando o limite por hora recusa, o diário ainda registra a tentativa. Insistir depois do bloqueio leva ao limite diário, sempre na cota de quem insiste. Na sondagem, o `Retry-After` do cadastro passou de 3600 para 86400 depois da 20ª tentativa.
7. **A mensagem genérica não é a proteção.** O 429 já é igual para todos os e-mails, e o que protege é a validação não rodar. Abaixo do limite, as respostas continuam as de antes.

### 27.4 Limites adotados e justificativa

| Escopo | Taxa | Justificativa |
|---|---|---|
| `register` | 10/hora (já existia) | Mantido |
| `register_day` | 20/dia por origem | O cadastro público é para donos de barbearia: os clientes são criados pelo admin. O uso legítimo é de uma ou duas contas por origem e por dia, então 20 não afeta nem redes compartilhadas (NAT). A sondagem contínua por origem cai de 240 para 20 por dia |
| `user_create` | 30/hora por conta | Comporta cadastrar clientes e barbeiros no balcão e na demonstração. Cai de até 1000 para 30 tentativas por hora |
| `user_create_day` | 100/dia por conta | Limita a sondagem contínua a 100 por dia e por admin. **Pode limitar a importação de uma carteira grande de clientes no primeiro dia.** Nesse caso, a taxa pode ser ajustada em `settings.py`, sem mexer no código |
| `email_change` | 10/hora por conta | Troca de e-mail é rara (correção de digitação), e reenviar o mesmo e-mail não conta. Cai de até 1000 para 10 por hora |
| `email_change_day` | 30/dia por conta | Sondagem contínua de no máximo 30 por dia e por conta. O admin que corrige e-mails de clientes usa a própria cota, não a do cliente |

Os valores são uma escolha técnica. Se o dono quiser outros, mudam só em `config/settings.py` e, para manter os testes coerentes, nas settings de teste.

### 27.5 Arquivos alterados nesta etapa

| Arquivo | Alteração |
|---|---|
| `accounts/throttles.py` (novo) | `LimitePorSolicitante`, as cinco classes de limite e `tenta_trocar_email()` |
| `accounts/views.py` | `RegistrationView.throttle_classes`; `UserViewSet.get_throttles()`, `update()` e `_aplicar_limites()` |
| `config/settings.py` | Cinco taxas novas em `DEFAULT_THROTTLE_RATES`. As existentes não mudaram |
| `config/test_settings.py`, `config/test_postgres_settings.py` | As mesmas cinco taxas. Essas settings substituem o dicionário de taxas, e sem elas o DRF acusa `ImproperlyConfigured` |
| `accounts/test_ten03_limites.py` (novo) | 28 testes |
| `accounts/tests.py`, `accounts/test_correcoes.py` | Nos `ThrottlingTests`, que trocam as taxas por um dicionário próprio, entrou só `'register_day': '1000/day'`, para o bloqueio continuar vindo do `register`, que é o que esses testes verificam. As asserções não mudaram |

O diff só desta etapa está em `diff/diff-somente-mitigacao-d.patch`.

### 27.6 Testes executados

**Os 28 testes novos** (`accounts/test_ten03_limites.py`):

| Grupo | O que verifica |
|---|---|
| Configuração (7) | As taxas novas em produção e nos testes. As que já existiam não mudaram. Login, recuperação, refresh, troca de senha e logout com as mesmas classes e escopos. Cadastro com os dois limites. Os limites da criação só na ação `create`. A chave é de quem pede e nunca o e-mail. O que conta como troca de e-mail (11 casos) |
| Cadastro público (4) | Antes do limite, a validação responde (400). Depois, 429 para e-mail existente, livre e com espaços. Limite diário. Origens independentes: com uma origem esgotada, outra cadastra (201) e entra (200). A janela expira |
| Criação de usuário (5) | 30 validações, depois 429. Limite diário. Cota por admin: outro admin da mesma barbearia e um de outra criam (201) e o criado entra. Cliente e conta sem barbearia continuam com 403 em 35 tentativas, sem 429. A janela expira |
| Troca de e-mail (8) | 10 validações, depois 429, e o e-mail não muda. PUT e PATCH dividem a cota. Limite diário. 25 edições sem troca não contam, e depois do bloqueio continuam funcionando. O admin gasta a própria cota, não a do cliente editado nem a de outro admin. **Um terceiro que sonda o e-mail da vítima não bloqueia a vítima**, que troca o e-mail (200), entra (200) e pede recuperação (204). Fora do alcance (404) e SEC-12 (403) mantêm as respostas e não gastam cota. A janela expira |
| Resposta do limite (1) | Com `DEBUG` True e False, nos três fluxos: 429 idêntico para e-mail existente, livre, da mesma barbearia e inválido. Só a chave `detail`, JSON, `Retry-After: 3600`. Não aparece o e-mail, a barbearia nem HTML. **A unicidade não é consultada** (consultas capturadas) |
| Login e recuperação (3) | Depois de esgotar os três limites novos: o login entra (200), o login errado dá 401 igual para existente e inexistente, a recuperação dá 204 igual. O limite do login segue 5 por minuto (5×401 e depois 429). A troca de senha não é afetada |

**Antes e depois:**

| Execução | Código anterior | Código corrigido |
|---|---|---|
| Testes novos | Falham na importação: `accounts.throttles` não existia (`testes/testes-novos-codigo-anterior.txt`) | **28 OK** |
| Suíte completa, SQLite | 452 OK (9 pulados) | **480 OK** (9 pulados) |
| Suíte completa, PG 18.3 descartável | 452 OK | **480 OK** |
| Suíte completa, PG 18.3, `DEBUG=False` também na importação | — | **480 OK** |
| Novos + isolamento, permissões, PER-13, SEC-10, TEN-02 e renderizadores, `--debug-mode` (`DEBUG=True`), PG 18.3 | — | **132 OK** |
| `check`; `makemigrations --check --dry-run` | — | Sem problemas; "No changes detected" |
| `check --deploy` (`DEBUG=False`) | — | Só o `security.W021` (HSTS preload), que já existia |
| Frontend: `npm test`, `tsc -b`, ESLint, build | — | 45 testes OK; sem erros de tipo ou de lint; build OK. Nenhum arquivo do frontend foi alterado, e ele já trata o 429 ("Muitas tentativas em pouco tempo…") nas telas afetadas: cadastro, "Minha conta", Clientes e Barbeiros |

**Sondagem HTTP com as taxas reais** (`api/resumo-antes-e-depois.txt`): quatro instâncias (corrigido e anterior, cada uma com `DEBUG` True e False), 98 pedidos cada, com o SQL do servidor:

| Etapa | Anterior (`DEBUG` True e False) | Corrigido (`DEBUG` True e False) |
|---|---|---|
| Cadastro público, 25 tentativas | 10×400, 15×429; `Retry-After` até 3600 | 10×400, 15×429; `Retry-After` 3600 e, depois da 20ª, **86400** |
| Criação pelo admin A, 40 tentativas | **40×400** (a unicidade foi consultada 40 vezes) | **30×400, 10×429** (0 consultas nos 429) |
| Criação por outro admin | 201 | 201 |
| Troca do próprio e-mail, 15 tentativas | **15×400** | **10×400, 5×429** (0 consultas nos 429) |
| Edição sem troca, depois do bloqueio | 2×200 | 2×200 |
| Vítima: troca o e-mail, entra, pede recuperação | 200, 200, 204 | 200, 200, 204 |
| Login errado | 4×401, depois 429 (5/min) | Igual |
| Recuperação, existente e livre | 204 e 204 | Igual |

Em todos os 429, o corpo é o mesmo para e-mail existente e livre: `{"detail":"Pedido foi limitado. Expected available in N seconds."}`, com `Content-Type: application/json`. Nenhum consultou a unicidade.

### 27.7 Por que o TEN-03 continua aberto

1. **Abaixo do limite, o oráculo é o mesmo.** As 10 primeiras trocas, as 30 primeiras criações e as 10 primeiras tentativas de cadastro por hora respondem exatamente como na seção 26, inclusive pelas variantes sem efeito colateral e pelo 500 do AUTH-05.
2. **Mais contas multiplicam a cota.** Cada conta nova tem a própria cota de troca de e-mail e, depois do onboarding, de criação. As contas novas só são limitadas pelo cadastro por origem, que pode ser contornado (SEC-13).
3. O limite **reduz a velocidade** de uma enumeração automatizada. Não impede de confirmar um e-mail específico, que pede uma única tentativa.

### 27.8 Limitações e risco residual

1. **SEC-13 (P2, novo, registrado e não corrigido): os limites por origem aceitam o `X-Forwarded-For` enviado pelo cliente.**
   - **Causa:** as settings não definem `NUM_PROXIES`. Nesse caso, o `get_ident` do DRF usa o `X-Forwarded-For` inteiro, quando presente, como identidade da origem.
   - **Contorno do limite:** na sondagem, com a origem já bloqueada no cadastro, cinco pedidos com `X-Forwarded-For: 203.0.113.1` a `.5` foram processados (5×400), na versão anterior e na corrigida.
   - **Bloqueio de terceiros:** um terceiro que envia `X-Forwarded-For: 198.51.100.7` gasta a mesma cota de quem se conecta diretamente desse IP (`laboratorio/xff-identidade.txt`).
   - **Alcance:** vale para **todos** os limites por origem que já existiam, inclusive o `login` (5/min) contra força bruta, e não só para o `register_day` novo.
   - **Correção:** definir `NUM_PROXIES` de acordo com a quantidade real de proxies na frente da aplicação. Não há proxy no repositório, mas o `settings.py` já confia em `X-Forwarded-Proto` em produção, o que indica que existe um. Um valor errado faria todos os usuários dividirem o IP do proxy e se bloquearem mutuamente, inclusive no login.
   - **Por que não foi feito:** por isso, e por a etapa não poder alterar o login, **nenhuma configuração foi inventada**. Fica para uma etapa autorizada, com a topologia de implantação conhecida.
2. **SEC-05 continua:** o cache é o padrão em memória de cada processo. Com N workers do gunicorn, cada limite vale N vezes, e um reinício zera as cotas. O cache compartilhado (Redis, Memcached ou o cache em banco do Django) é uma decisão de infraestrutura e não está disponível no projeto. Os limites novos têm a mesma limitação dos existentes.
3. **A mensagem do 429 sai metade em inglês** ("Pedido foi limitado. Expected available in N seconds."), porque a tradução do DRF está incompleta. O mesmo já acontecia no login. O frontend mostra o próprio texto, "Muitas tentativas em pouco tempo. Aguarde um instante e tente novamente.", que fala em "um instante" mesmo quando a espera é de até uma hora ou um dia. Não foi alterado.
4. **Origem compartilhada:** no cadastro público, quem está atrás do mesmo IP (NAT) divide a cota de 10 por hora, que já existia, e de 20 por dia. Um abusador na mesma rede pode esgotá-la para os demais. O risco é baixo porque o cadastro legítimo é raro, mas existe.
5. **A janela não é atômica:** o throttle do DRF lê e grava o histórico sem trava. Pedidos simultâneos podem ultrapassar o limite em poucas unidades. Isso também já valia para os limites existentes.
6. **AUTH-04 e AUTH-05 não foram tocados.** O caminho do 500 pelo domínio em maiúsculas continua, mas agora conta no limite.

### 27.9 Relação com a C3

A D é **temporária**. A C3 elimina o oráculo: o cadastro responde sempre 202 e confirma por e-mail, a troca de e-mail fica pendente até a confirmação e a criação pelo admin vira convite. Quando a C3 entrar:

- **os limites continuam úteis** como proteção contra abuso dos envios de e-mail (bombardeio de convites e de confirmações). Os escopos `register`, `register_day`, `user_create` e `email_change` podem ser mantidos nos endpoints novos;
- a regra de **contar só a troca de e-mail** passa para o pedido de troca pendente;
- os testes de `accounts/test_ten03_limites.py` que verificam a validação abaixo do limite (400) precisarão ser revistos, porque as respostas passam a ser 202;
- a C3 também resolve o **SEC-08**, a falta de verificação de e-mail no cadastro.

### 27.10 Situação final e contagem

- **TEN-03: continua aberto (P3), com mitigação parcial (D).** Não foi marcado como resolvido.
- **AUTH-04 (P2) e AUTH-05 (P3): continuam abertos**, como registrados na seção 26.6. O código deles (`accounts/serializers.py`, `accounts/managers.py`, `accounts/models.py`) não foi alterado. São a próxima etapa prioritária, quando autorizada.
- **SEC-13 (P2): novo**, registrado e não corrigido.

| | Após a investigação do TEN-03 | Após a mitigação D |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 29 | 30 (+SEC-13) |
| P3 | 39 | 39 (o TEN-03 continua, agora mitigado) |
| **Abertos** | 63 dos 70 originais + 8 novos = 71 | **63 dos 70 originais + 9 novos = 72** |

**Próximo passo:** aguarda autorização para o AUTH-04 e o AUTH-05. TEN-04, SEC-12 e SEC-13 não foram iniciados.

---

## 28. Investigação e plano do AUTH-04 e do AUTH-05 — 15/11/2026

**Decisões do dono que orientam o plano:**

- o e-mail continua único em toda a plataforma;
- o tratamento de caixa deve ser coerente em cadastro, edição, login e recuperação de senha;
- a direção é **normalizar o endereço inteiro para minúsculas**;
- AUTH-04 e AUTH-05 têm prioridade.

**Escopo autorizado:** só diagnóstico e plano. Nada foi corrigido.

**Restrições cumpridas:**

- **Código:** nenhum arquivo de código, teste, migração, settings, `.env` ou frontend foi alterado.
- **Migrações:** nenhuma criada nem executada.
- **Banco real:** não foi consultado nem alterado. A consulta de colisões (28.6) ficou pronta e **não foi executada nele**.
- **Etapas anteriores preservadas:** a mitigação D, o TEN-01, o TEN-02, o SEC-10, o TEN-03, o SEC-13 e o SEC-05 não foram tocados. A contenção (só `JSONRenderer`) continua.
- **Bancos usados:** só um **PostgreSQL 18.3 descartável** (`127.0.0.1:55432`), com dados fictícios, já apagado. O PostgreSQL do Docker não foi usado.
- **Repositório:** sem commit, push ou merge. As alterações locais e as evidências anteriores foram preservadas.

Evidências em [`docs/auditoria/evidencias-2026-11-15/auth-04-05/`](auditoria/evidencias-2026-11-15/auth-04-05/README.md).

### 28.1 Resumo

| Item | Situação |
|---|---|
| **Causa do AUTH-04** | **Confirmada.** A recuperação procura sem diferenciar caixa e escolhe **uma** conta pela ordem do nome: `filter(email__iexact=…, is_active=True).first()` (`accounts/serializers.py:391`). O cadastro deixa existir mais de uma conta com o mesmo endereço em caixas diferentes (AUTH-05) |
| **Precisão sobre o AUTH-04** | O token **nunca** vai para um endereço diferente do gravado na conta para a qual foi gerado (6 de 6 mensagens conferidas). O que se desvia é **a conta recuperada**. A vítima recebe o token da conta do terceiro: ao usá-lo, troca a senha do terceiro, e a dela continua igual. Um terceiro só recebe um token da conta dele mesmo |
| **Causa do AUTH-05** | **Confirmada.** Há quatro tratamentos diferentes para o mesmo dado: (1) a validação compara **exato**; (2) o `create_user` corta os espaços e põe só o **domínio** em minúsculas, **depois** de validar; (3) a edição grava como veio; (4) o login compara **exato**, e a recuperação **sem diferenciar caixa**. O banco tem `UNIQUE (email)` sensível à caixa |
| **Efeitos medidos** | Contas duplicadas por caixa em cadastro, criação, edição e Django Admin. **500** quando o domínio vem em maiúsculas e o e-mail existe. **O login logo após o cadastro falha** quando o domínio foi digitado com maiúscula. **500 em 15 de 15** pedidos simultâneos com o mesmo e-mail |
| **Estratégia** | Uma única função de normalização (cortar espaços e converter tudo para minúsculas), aplicada no campo do serializer, no model, no manager e nas buscas de login e recuperação. Garantia no banco por `UNIQUE (LOWER(email))`. `IntegrityError` convertido no mesmo 400 de hoje |
| **Migração** | **Necessária** (28.5): conversão dos e-mails gravados e restrição no banco. **Não foi criada** |
| **Colisões no banco real** | **Desconhecidas.** Dependem da consulta de 28.6, que aguarda autorização. Se houver colisões, a migração precisa de uma decisão do dono para cada grupo |
| **Situação** | **AUTH-04 (P2) e AUTH-05 (P3) continuam abertos** |

### 28.2 AUTH-04: caminho do token, passo a passo

1. **Cadastro (`POST /auth/register/`):**
   - O `EmailField` do DRF corta os espaços.
   - O `UniqueValidator` (`lookup='exact'`) procura `WHERE email = 'Cliente.B@beta.test'` e não acha a vítima `cliente.b@beta.test`.
   - O `create_user` (`accounts/managers.py:43`) aplica o `normalize_email` do Django, que só põe o domínio em minúsculas, e grava `Cliente.B@beta.test`.
   - Agora existem duas contas para o mesmo endereço.
2. **Pedido de recuperação** (`accounts/serializers.py:391`):
   - A busca é `UPPER(email) = UPPER('cliente.b@beta.test') AND is_active ORDER BY nome LIMIT 1`.
   - Ela casa as duas contas e fica com a de nome menor.
3. **Destinatário:** é `[user.email]` da conta escolhida (`:397`). O token é gerado para essa mesma conta, e o `uid` é o id dela.
4. **Confirmação** (`accounts/serializers.py:430`): procura a conta pelo `uid`, isto é, pelo id. A senha trocada é a da conta para a qual o token foi gerado.

**Demonstração** (`demonstracoes/auth04-demonstracao.json`; vítima "Clara Cliente B", id 5):

| Passo | Resultado |
|---|---|
| A1, controle, sem variação | Token da conta 5 para `cliente.b@beta.test` |
| A2, anônimo cadastra `Cliente.B@beta.test` com o nome "Aaron Variante" | 201, conta 6 |
| A3/A4, a vítima pede a recuperação com `cliente.b@beta.test` ou `CLIENTE.B@BETA.TEST` | Token da **conta 6** para `Cliente.B@beta.test` |
| A5, a vítima usa esse token | 204 |
| A6, efeito | `cliente.b@beta.test` + senha nova: **401**. `cliente.b@beta.test` + senha antiga: 200. `Cliente.B@beta.test` + senha nova: **200**. A senha trocada foi a do terceiro |
| A7, variação com nome que vem **depois** ("Zuleica" > "Celia") | O token vai para a vítima. O resultado depende da ordem alfabética do nome |
| A8, o admin A cria, **na barbearia A**, o cliente `ADMIN.B@beta.test`, com o nome "Abel" | A recuperação do admin da barbearia B gera o token da conta "Abel", um cliente da barbearia A |
| A9, o admin A desativa "Abel" | A recuperação volta para o admin de B (`is_active` filtra) |
| Conferência | Em todas as 6 mensagens, o destinatário é o e-mail gravado na própria conta do token |

**Um terceiro pode receber o token da conta de outra pessoa?** Não pelo código: o token sempre segue para o e-mail da conta a que pertence.

- **O dano real é o desvio da recuperação.** Enquanto a variação existir, a vítima não recupera a própria conta. A mensagem chega à caixa postal da vítima, porque os provedores não diferenciam caixa na parte local, mas o token é de outra conta.
- **Agravante (A8):** quem segue o link define a senha de uma conta **dentro da barbearia do terceiro**. Se entrar com aquela grafia, opera como cliente dessa barbearia, visível ao admin dela.
- **Provedor que diferencia caixa** (raro, mas permitido pelo RFC 5321): o dono da variação recebe o token da conta dele mesmo, sem ganho.

**Outros fluxos com o mesmo problema** (busca por e-mail que pode casar várias contas): **nenhum**.

- **Login, login do Django Admin e `createsuperuser`:** usam `get_by_natural_key`, exato. Cada grafia entra na própria conta, e o defeito ali é outro (28.3).
- **Confirmação da recuperação, refresh e JWT:** procuram pelo id.
- **Unicidade (`UniqueValidator`):** é exata, e é a causa das duplicatas, não um desvio.

### 28.3 AUTH-05: todos os pontos em que o e-mail entra, é comparado ou gravado

| # | Ponto | Espaços | Parte local | Domínio | Comparação |
|---|---|---|---|---|---|
| 1 | Model `email = EmailField(unique=True)` (`accounts/models.py:29`); banco `UNIQUE (email)` + índice `_like` | — | — | — | Banco **sensível à caixa** |
| 2 | `UserManager.create_user` → `normalize_email` do Django (`accounts/managers.py:43`) | Corta | **Mantém** | Minúsculas | — |
| 3 | `User.save()` (`accounts/models.py:73`) | Não trata | Não trata | Não trata | — |
| 4 | `AbstractUser.clean()` do Django → `normalize_email`; `AbstractBaseUser.clean()` → NFKC. Só roda via `full_clean` (Django Admin) | Corta | Mantém | Minúsculas | — |
| 5 | `PublicRegistrationSerializer` (`accounts/serializers.py:309`), `POST /auth/register/` | Corta (`EmailField`) | Mantém | Minúsculas, mas só **depois** da validação, no `create_user` | `UniqueValidator` **exato** |
| 6 | `UserCreateSerializer` (`:222`), `POST /users/` | Corta | Mantém | Minúsculas **depois** da validação | Exato |
| 7 | `UserSerializer` (`:43`), `PATCH`/`PUT /users/{id}/` | Corta | Mantém | **Mantém** (sem normalização) | Exato, excluindo a própria conta |
| 8 | Login: `CustomTokenObtainPairSerializer` (`CharField` do simplejwt) → `authenticate` → `ModelBackend.get_by_natural_key` | Corta | — | — | **Exato** |
| 9 | Pedido de recuperação (`:381-397`) | Corta | — | — | **`iexact` + `.first()` por nome** |
| 10 | Confirmação da recuperação (`:422-430`) | — | — | — | Pelo id |
| 11 | Django Admin: `CustomUserCreationForm`/`CustomUserChangeForm` (`accounts/forms.py`) → `full_clean` (ponto 4) → `validate_unique`; login do Admin → ponto 8 | Corta | Mantém | Minúsculas **antes** de validar | Exato |
| 12 | Mitigação D: `tenta_trocar_email` (`accounts/throttles.py:72`) | Corta | — | — | Exato com o atual |
| 13 | `BarberSerializer.email` (só leitura) e `Barbershop.email` (contato, sem unicidade) | — | — | — | Não identificam ninguém. Fora do escopo |
| 14 | Frontend: cadastro, login, "Minha conta", Clientes (criar e editar), Barbeiros (criar) e recuperação (`*.tsx`, `z.string().trim()` e `.trim()` no envio). O cadastro entra logo depois com o texto digitado | Corta | Mantém | Mantém | — |

**Matriz medida** (`demonstracoes/auth05-matriz.json`; conta existente `cliente.a1@alfa.test`):

| Variação | Cadastro público | Criação pelo admin | Troca do próprio e-mail |
|---|---|---|---|
| Nova, minúsculas | 201, grava igual | 201 | 200 |
| Nova, maiúsculas na parte local | 201, grava `Novo.2@…` | 201, `Novo.12@…` | 200, `Novo.22@…` |
| Nova, maiúsculas no domínio | 201, grava `…@exemplo.test` | 201, idem | 200, grava **`…@EXEMPLO.TEST`** |
| Existente, exato ou com espaços | 400 | 400 | 400 |
| Existente, maiúsculas na parte local | **201, duplicata** | **201, duplicata** | **200, duplicata** |
| Existente, maiúsculas no domínio | **500** (`IntegrityError`) | **500** | **200, duplicata** (`…@ALFA.TEST`) |
| Existente, tudo maiúsculo | **201, duplicata** (`CLIENTE.A1@alfa.test`) | **201, duplicata** | **200, duplicata** |

- **Login com a senha correta:** exato e com espaços dão 200. Maiúsculas na parte local, no domínio ou em tudo dão **401**.
- **Recuperação:** qualquer variação leva à mesma conta, quando não há duplicata gravada.
- **Login logo após o cadastro** (`auth05-login-apos-cadastro.json`): `pessoa.tres@EXEMPLO.TEST` e `Pessoa.Quatro@Exemplo.Test` são gravados com o domínio em minúsculas, e o login com o **mesmo texto digitado** dá **401**. Na tela, a conta é criada, mas o login automático falha, e a pessoa só entra se digitar o domínio em minúsculas.
- **Django Admin** (`auth05-admin-e-unicode.json`): o formulário recusa a variação no domínio, porque o `clean()` normaliza antes do `validate_unique`. Mas aceita `Cliente.B@beta.test` e `CLIENTE.B@BETA.TEST`, este gravado como `CLIENTE.B@beta.test`, e cria duplicatas.

**Diferença entre validação e gravação, e os 500:**

- **Domínio em maiúsculas no cadastro e na criação:** a validação procura o texto como veio (não acha) e o `create_user` grava o domínio em minúsculas. O `INSERT` colide com `accounts_user_email_key`, e a API responde 500.
- **Concorrência** (`auth05-concorrencia.json`): o `UniqueValidator` consulta e só depois o código grava, com o hash da senha, cerca de 250 ms, no meio. Em **15 de 15** pares simultâneos com o mesmo e-mail (5 cadastros, 5 criações por admins de barbearias diferentes e 5 trocas por contas diferentes), um pedido teve sucesso e o outro recebeu **500**. O banco impediu a duplicata, mas a API não trata o erro.
- **A validação no serializer não garante a unicidade:** é uma checagem antes de gravar, sujeita a corrida, que não cobre o ORM, o shell, `update()`, `bulk_create` nem SQL.

**Unicode** (`auth05-admin-e-unicode.json`):

- O `EmailValidator` recusa parte local não ASCII (`joão@…`), mas aceita domínio não ASCII (`cliente@ÁLFA.test`).
- No banco descartável (`C.UTF-8`), o `str.lower()` do Python e o `lower()` do PostgreSQL deram o mesmo resultado em 5 de 6 amostras. A exceção foi `İ`: Python `i̇`, PostgreSQL `i`.
- O `lower()` depende do `LC_CTYPE` do banco. O do banco real não foi consultado (28.6, consulta 0).

### 28.4 Estratégia técnica recomendada

**Princípios:**

- uma única função de normalização, `btrim` + minúsculas no endereço inteiro, usada em **toda** entrada e em **toda** busca;
- o banco como garantia final;
- respostas iguais às de hoje para quem não erra.

| Componente | Precisa mudar? | O que muda e por quê |
|---|---|---|
| Função única | **Sim** | Por exemplo, `UserManager.normalize_email` sobrescrito para `(email or '').strip().lower()`. Como é classmethod, cobre `create_user`, `create_superuser` e o `AbstractUser.clean()` do Django Admin |
| Manager | **Sim** | `create_user` já usa a função. `get_by_natural_key(username)` passa a normalizar e buscar exato. Isso torna sem caixa o login da API, o login do Django Admin e o `createsuperuser`, **sem mexer nas views** nem no simplejwt |
| Model | **Sim** | `User.save()` normaliza antes de gravar. Cobre o ORM, o shell e o Admin; `update()`, `bulk_create` e SQL ficam para o banco |
| Serializers | **Sim** | Um `EmailField` que normaliza no `to_internal_value`, aplicado aos três serializers (por exemplo, via `serializer_field_mapping`), para o `UniqueValidator` já receber o valor normalizado. **Um `validate_email` não basta:** o DRF roda o `UniqueValidator` dentro de `field.run_validation`, antes do `validate_<campo>` (`rest_framework/serializers.py:499-501`). Além disso, capturar `IntegrityError` no `create` e no `update` e responder o **mesmo 400** de hoje. Para não esconder outros erros, conferir se a conta com aquele e-mail existe antes de converter |
| Fluxo de autenticação | **Pelo manager** | Nenhuma view muda. O `ModelBackend` continua igual, inclusive a proteção de tempo para conta inexistente |
| Recuperação de senha | **Sim** | A busca passa a ser exata no valor normalizado, sem `.first()` ambíguo. A resposta continua 204 para qualquer e-mail, e o envio fictício para e-mail inexistente se mantém |
| Mitigação D | **Ajuste mínimo** | `tenta_trocar_email` passa a comparar com a mesma função. Reenviar o próprio e-mail em outra caixa deixa de contar como troca. Exige autorização, porque toca a mitigação D |
| Restrição no banco | **Sim** | `UniqueConstraint(Lower('email'))`: garante que não existam duas contas equivalentes, por qualquer caminho de escrita (28.5) |
| Conversão dos dados | **Sim** | Os e-mails gravados fora do padrão passam para a forma normalizada |
| Frontend | **Não é obrigatório** | O backend normaliza tudo. Converter para minúsculas na tela é só conforto visual |
| TEN-03 | Sem mudança de natureza | As variações de caixa de um e-mail existente passam a receber o mesmo 400 do e-mail exato, sem informação nova. O oráculo pelo 500 desaparece. O TEN-03 continua aberto |

**Restrição no banco, as duas opções medidas em laboratório (`sql/laboratorio-ddl-saida.txt`):**

- **`UNIQUE (LOWER(email))`** (`UniqueConstraint(Lower('email'), …)`): **recomendada.** Impede contas equivalentes, mesmo que algum caminho grave fora do padrão.
- **`CHECK (email = lower(btrim(email)))`**: obriga a gravar já normalizado. Com ela, a `UNIQUE (email)` atual já impede as equivalentes, e as buscas exatas usam o índice existente. A contrapartida é que qualquer escrita fora do padrão, por um caminho esquecido, vira `IntegrityError`. **Recomendada como reforço; a decisão é do dono.**

**Detalhes que afetam a escolha:**

- **O `unique=True` do campo precisa ficar.** O check `auth.E003` só aceita unicidade no próprio campo ou numa `UniqueConstraint(fields=('email',))`, e uma restrição funcional não conta.
- **O DRF 3.15.2 ignora `UniqueConstraint` funcional:** só gera validadores para restrições com mais de um campo. Os serializers não mudam de comportamento por causa dela.
- **O Django 5.0 valida restrições funcionais no `full_clean`:** o Django Admin passa a mostrar erro de formulário, e não 500.

### 28.5 Por que a correção exige migração

1. **O banco não garante hoje a unicidade sem caixa.** O serializer não basta: corrida (15 de 15) e caminhos que não passam por ele. Só uma restrição no banco garante. Isso é uma alteração de esquema, portanto uma migração.
2. **Os dados atuais podem estar fora do padrão:**
   - quem se cadastrou com maiúsculas na parte local;
   - quem trocou o e-mail com o domínio em maiúsculas;
   - possíveis grupos equivalentes.
3. **A restrição não pode ser criada com equivalentes no banco (L1).** E a conversão para minúsculas falha na `UNIQUE (email)` atual se houver colisão (L2). A migração precisa verificar, converter e só então restringir.

**Operações previstas para uma migração `accounts.0006`** (ilustrativas; o arquivo **não foi criado**):

1. **`RunPython` de verificação:** se `lower(btrim(email))` se repetir, **interrompe** e lista os ids dos grupos, nunca os e-mails. A migração é atômica e nada muda.
2. **`RunPython` de conversão:** grava `email.strip().lower()`, com a mesma função da aplicação, só nas contas que mudam.
3. **`AddConstraint(UniqueConstraint(Lower('email'), name='accounts_user_email_normalizado_unico', violation_error_message='usuário com este e-mail já existe.'))`.**
4. **Opcional:** `AddConstraint(CheckConstraint(check=Q(email=Lower(Trim('email'))), name='accounts_user_email_em_minusculas'))`.
5. **Reversão:** retira as restrições. A conversão dos dados não se desfaz, e o backup cobre esse caso.

**Dados afetados:**

- **Contas convertidas:** as que têm `email <> lower(btrim(email))` (consultas 1 e 4 de 28.6). Para elas:
  - o login passa a aceitar qualquer caixa;
  - o e-mail aparece em minúsculas;
  - **os links de recuperação pendentes deixam de valer**, porque o hash do token do Django inclui o e-mail (`django/contrib/auth/tokens.py:120-122`);
  - sessões e JWT continuam valendo, porque usam o id.
- **Contas em grupos de colisão:** exigem **decisão do dono**, conta por conta, antes da migração. Opções:
  - manter o e-mail na conta principal e dar às outras um endereço provisório (como `conflito+<id>@resolver.invalid`), desativando-as ou pedindo um e-mail novo;
  - ou unificar as contas, o que não é recomendado de forma automática, porque mexe em agendamentos e perfis de barbeiro.
- **Bloqueio:** `CREATE UNIQUE INDEX` e `ADD CONSTRAINT … CHECK` travam a tabela `accounts_user` durante a criação. A tabela é pequena, e isso deve levar milissegundos, mas convém uma janela curta.
- **Ordem de implantação:** código e migração **juntos**.
  - Código novo sem a conversão: quem tem e-mail gravado com maiúsculas não entra, porque a busca normalizada é exata.
  - Restrição sem o código novo: as variações recebem 500 em vez de virar duplicata.

### 28.6 Consulta de colisões para o banco real (não executada)

O arquivo é `sql/verificacao-colisoes-somente-leitura.sql`. Ele roda numa transação `READ ONLY` que termina em `ROLLBACK`.

| Consulta | Retorna | Dados pessoais |
|---|---|---|
| 0 | Banco, `datcollate`, `datctype` e versão. O `lower()` depende do `LC_CTYPE` | Não |
| 1 | Totais: contas, quantas mudariam, com espaços, não ASCII, **grupos que colidiriam** e contas nesses grupos | Não |
| 2 | Um registro por grupo de colisão: ids, barbearias, papéis, ativas, superusuário, último login, criação, agendamentos como cliente, perfil de barbeiro e qual já está normalizada | **Não** (só ids) |
| 3 | O detalhe de cada grupo, com e-mail gravado e nome, **para o dono decidir** | **Sim. Não copiar para as evidências** |
| 4 | As contas que a normalização mudaria, só pelo id, com o tipo de mudança | Não |
| 5 | Os ids com caracteres não ASCII, onde o `lower()` do PostgreSQL e o do Python podem divergir | Não |

O núcleo da verificação:

```sql
SELECT min(u.id) AS grupo, count(*) AS contas, array_agg(u.id ORDER BY u.id) AS ids, …
FROM accounts_user u
GROUP BY lower(btrim(u.email))
HAVING count(*) > 1;
```

**O que ela retornou no banco fictício** (`sql/colisoes-saida-banco-ficticio.txt`):

- 14 contas: 7 mudariam, 1 tem espaço na ponta e 1 tem caractere não ASCII.
- **4 grupos de colisão (8 contas):**
  - a variação do AUTH-04, sem barbearia, × a cliente de B, que tem 2 agendamentos;
  - a variação do admin B criada e desativada em A;
  - um barbeiro de A × uma cópia em maiúsculas em B;
  - dois "espaco@" que só diferem por um espaço final, gravável só pelo shell.

No banco real, um resultado com **0 grupos** libera a migração sem decisões. Qualquer grupo exige a decisão de 28.5 antes.

### 28.7 Riscos de compatibilidade

1. **Colisões no banco real:** desconhecidas até a consulta. Se existirem, a migração é interrompida (de propósito), e cada grupo precisa de decisão.
2. **E-mails exibidos em minúsculas** e **links de recuperação pendentes invalidados** para as contas convertidas.
3. **Caixa postal que diferencia caixa na parte local** (permitido pelo RFC 5321, raro na prática): duas pessoas assim deixam de poder ter contas separadas. Foi aceito pela decisão de produto.
4. **Domínios não ASCII:** o `lower()` do PostgreSQL pode divergir do Python (o caso `İ`). A consulta 5 diz se há contas assim. Se não houver, o risco é só teórico. Se houver, uma opção é guardar o domínio em IDNA (ASCII).
5. **DB-02** (versão de ordenação 2.43 × 2.44 no banco real): um índice sobre `lower(email)` depende do `LC_CTYPE`. Recomenda-se um `REINDEX` numa etapa autorizada, com backup.
6. **Implantação:** código e migração na mesma janela, com backup (`pg_dump -Fc`) antes, como foi feito na `barbershops.0006`.
7. **Testes existentes:** só um depende da caixa. É o `accounts/test_ten03_limites.py:195` (`'Cliente.A1@alfa.test'` conta como troca), que passará a ser `False`. Nenhum outro teste usa e-mail com maiúsculas.
8. **Mitigação D:** precisa do ajuste mínimo em `tenta_trocar_email`.
9. **TEN-03:** continua aberto. A mudança não cria oráculo novo e remove o do 500.

### 28.8 Testes que a correção deve trazer

Como nas etapas anteriores, os testes vêm **antes** da correção. Eles falham no código atual e passam no corrigido.

| Teste | Deve verificar | Hoje |
|---|---|---|
| Cadastro com e-mail em minúsculas | 201; gravado igual | 201 |
| Cadastro com maiúsculas (parte local, domínio, tudo) | 201; **gravado em minúsculas** | Grava a parte local como veio |
| Cadastro com variação de caixa de conta existente | **400**, a mesma mensagem do exato; nenhuma conta criada | 201 (duplicata) ou 500 |
| Criação pelo admin com variação de caixa | 400; sem conta na barbearia A; a conta de B intacta | 201 ou 500 |
| Edição do próprio e-mail com maiúsculas, nova ou existente | Nova: 200, gravada em minúsculas. Existente: 400. Reenvio do próprio em outra caixa: 200 sem mudança | Grava como veio; duplicata |
| Login com caixa diferente e com espaços | 200 para a mesma conta. Senha errada: o mesmo 401 | 401 |
| Login logo após o cadastro com domínio em maiúsculas | 200 | 401 |
| Recuperação com caixa diferente | O token vai para a única conta, no endereço normalizado | Funciona sem duplicata |
| Recuperação com registros antigos com variações | Com a migração aplicada, não existem. Teste da migração: interrompe se houver grupo e informa só os ids | `.first()` escolhe pelo nome |
| Ausência de token para endereço incorreto | Para cada envio, o `uid` é da conta cujo e-mail é o destinatário, e só existe uma conta por endereço | Desvio (A3) |
| Tentativa de criar duplicatas por todos os caminhos | Serializers, `create_user`, `User.save()`, formulário do Admin (erro de formulário) e `update()`/SQL (o banco recusa) | Duplicatas |
| Concorrência entre dois cadastros equivalentes | Uma conta só e **nenhum 500**: o segundo recebe o mesmo 400. No PostgreSQL, com threads e barreira (`TransactionTestCase`). No SQLite, simulado deixando o validador passar e forçando o `IntegrityError` | 500 em 15 de 15 |
| Ausência de HTTP 500 | Domínio em maiúsculas, corrida, valor inválido e nulo | 500 |
| Unicidade global preservada | O e-mail de B, em qualquer caixa, é recusado em A, no cadastro e na troca | Parcial |
| Isolamento multi-tenant preservado | Suíte de isolamento inteira; o login normalizado leva à conta e à barbearia certas; a recuperação não cruza barbearias | Já cobertos |
| `get_by_natural_key` e `createsuperuser` | Encontram a conta em qualquer caixa | Exato |
| Migração | Banco com dados antigos fictícios: interrompe com colisão. Sem colisão: converte, cria as restrições, e a reversão as retira | — |
| Mitigação D | `tenta_trocar_email` com o próprio e-mail em outra caixa → `False`; os 28 testes continuam passando | `True` |
| Frontend | Sem mudança obrigatória; `npm test`, `tsc`, ESLint e build | — |

### 28.9 Ordem recomendada

1. **Autorização para a consulta de 28.6 no banco real.** Só leitura e sem backup necessário. Gravar nas evidências só os resultados sem dados pessoais (consultas 0, 1, 2, 4 e 5).
2. **Decisão do dono sobre cada grupo de colisão**, se houver, e sobre o `CHECK` opcional.
3. **Testes de regressão** (28.8), escritos antes e falhando no código atual.
4. **Normalização no código:** função única, manager (`normalize_email` e `get_by_natural_key`), `User.save()`, campo de e-mail dos serializers, `IntegrityError` → 400, recuperação exata e o ajuste mínimo da mitigação D.
5. **Migração `accounts.0006`** (verificação, conversão e restrições), validada no PostgreSQL 18.3 descartável com o conjunto de dados antigos fictícios (`scripts/a45_dados_legados.py`).
6. **Suíte completa** (SQLite, PostgreSQL 18.3, `DEBUG` True e False), isolamento multi-tenant, `check`, frontend e a repetição das demonstrações desta seção, que devem passar a mostrar o comportamento correto.
7. **Banco real:** backup `pg_dump -Fc` validado, as decisões de colisão aplicadas, a migração na mesma janela da implantação do código, um smoke test, e o `REINDEX` do DB-02 se autorizado.

### 28.10 Situação

- **AUTH-04: aberto (P2).** Causa confirmada e plano pronto.
- **AUTH-05: aberto (P3).** Causa confirmada e plano pronto. A investigação acrescentou efeitos ao registro da seção 26.6: o login após o cadastro com domínio em maiúsculas falha, e há 500 em pedidos simultâneos. A severidade não mudou, porque os dois serão corrigidos juntos com o AUTH-04.
- **TEN-03, SEC-13 e SEC-05:** abertos, sem alteração.
- **Contagem:** sem mudança, **72 abertos** (63 dos 70 originais + 9 novos).

**Próximo passo:** aguarda autorização para a consulta no banco real, para a migração e para a implementação. SEC-13, SEC-05, TEN-04 e SEC-12 não foram iniciados.

---

## 29. Verificação de colisões no banco real (somente leitura) — 15/11/2026

**Escopo autorizado:** só rodar, no banco real, a consulta de colisões preparada em 28.6. Não inclui implementação, escrita, migração nem nenhuma outra operação.

**Como foi feito:**

- **O arquivo:** foi lido por inteiro e conferido instrução por instrução. Só tem `SELECT`, comandos do psql (`\set`, `\echo`), `BEGIN TRANSACTION READ ONLY`, `SET LOCAL` e `ROLLBACK`.
- **O bloco 3 não foi executado:** ele só lê, mas mostra nomes e e-mails, e a autorização proíbe expô-los. Rodou uma cópia sem esse bloco, e a diferença está registrada.
- **A sessão:** aberta com `default_transaction_read_only=on`, `statement_timeout=30s` e `lock_timeout=5s`. As credenciais vieram das settings da aplicação, sem serem impressas.
- **Não usados:** o PostgreSQL do Docker (porta 5433) e o banco antigo `barbershop`.

Evidências em [`docs/auditoria/evidencias-2026-11-15/auth-04-05-verificacao-banco-real/`](auditoria/evidencias-2026-11-15/auth-04-05-verificacao-banco-real/README.md).

| Item | Resultado |
|---|---|
| Banco | `barbershop_db`, PostgreSQL 18.3, localhost (`::1`), porta 5432; `datctype` `pt_BR.UTF-8` (libc) |
| Contas verificadas | 8 |
| Contas que seriam normalizadas | 0 |
| Com espaços nas pontas | 0 |
| Com caracteres fora do ASCII | 0 |
| **Grupos de colisão** | **0** |
| Fim da transação | `ROLLBACK`; nenhum dado alterado |

**Conclusão:**

- Pela consulta, o banco real **não tem colisões**, e nenhuma conta precisaria ser convertida. A migração planejada em 28.5 pode avançar para o próximo passo de planejamento **sem decisões por grupo**: a verificação e a conversão não teriam nada a fazer hoje.
- Elas continuam necessárias na migração, porque o banco pode mudar até a implantação.
- Como o banco real usa `pt_BR.UTF-8`, e não o `C.UTF-8` do laboratório, a validação da migração deve repetir esse `LC_CTYPE` no PostgreSQL descartável.
- **Isso não autoriza a migração nem a implementação.**

**AUTH-04 (P2) e AUTH-05 (P3) continuam abertos.** Contagem sem mudança: 72 abertos.

---

## 30. AUTH-04 e AUTH-05: equivalência Python × PostgreSQL e parada antes da implementação — 15/11/2026

**Escopo autorizado:**

- implementar o AUTH-04 e o AUTH-05, com a migração `accounts.0006` validada em PostgreSQL 18.3 descartável;
- com uma condição expressa de parada: se não for possível garantir equivalência entre a normalização em Python e a função SQL **para todos os caracteres aceitos**, parar e apresentar uma alternativa segura antes de criar a restrição.

**O que aconteceu:**

- A verificação de equivalência foi feita **antes de qualquer alteração de código**, como o escopo exigia, num PostgreSQL 18.3 descartável com **`pt_BR.UTF-8`** (libc, glibc 2.44), a mesma ordenação do banco real.
- A equivalência **não se sustenta** para o conjunto de caracteres que o backend aceita hoje. A implementação **foi interrompida**: nenhum código, teste ou migração foi criado ou alterado.
- O banco real não foi acessado nesta etapa.

Evidências em [`docs/auditoria/evidencias-2026-11-15/auth-04-05-equivalencia/`](auditoria/evidencias-2026-11-15/auth-04-05-equivalencia/README.md).

### 30.1 O que foi medido

| Verificação (1.112.063 pontos de código) | Resultado |
|---|---|
| `str.lower()` (Python 3.12, Unicode 15) × `lower()` (PostgreSQL, pt_BR) | **56 divergem**, todos aceitos pelo `EmailValidator` do Django no domínio. Exemplos: `İ` (U+0130: Python `i` + U+0307; PostgreSQL `i`) e letras do Unicode 16 (U+A7CB: Python mantém; PostgreSQL vira U+0264). **No ASCII, nenhuma divergência** |
| Entradas aceitas cujo valor normalizado em Python seria recusado por `CHECK (email = lower(email))` | **55** |
| Espaços externos | O Python e o `trim_whitespace` do DRF removem 29 pontos de código. O `btrim()` remove só o espaço (U+0020). A classe `\s` do PostgreSQL (pt_BR) cobre 21 e não inclui U+001C–U+001F, U+0085, U+00A0, U+2007 e U+202F. O `trim()` do JavaScript (frontend) remove 25 e inclui U+FEFF, que o Python não remove |
| Caracteres invisíveis | O `EmailValidator` aceita, pelo caminho IDNA, U+200B, U+FEFF, U+00AD e outros 7, no meio ou no fim do domínio (20 de 30 posições testadas). Nenhuma normalização os remove: são endereços que parecem iguais e entregam na mesma caixa, mas ficam diferentes no banco |
| Frontend (zod 3.25.76, `z.string().trim().email()`) | **Só aceita e-mails ASCII.** Recusa domínio acentuado, `İ`, invisíveis e Unicode 16. Pela interface, só ASCII chega ao backend; o resto só chega pela API direta |
| Banco real (seção 29) | 0 contas com caractere fora do ASCII |

**Conclusão:** com o conjunto aceito hoje, Python e PostgreSQL discordam sobre o que é "o mesmo e-mail normalizado". Uma restrição `CHECK` baseada em `lower()` recusaria e-mails que a aplicação aceita. E os invisíveis criam endereços equivalentes que nenhuma das duas normalizações une.

### 30.2 Alternativa segura proposta (aguarda autorização)

**Restringir o e-mail normalizado a ASCII imprimível, sem espaços (U+0021 a U+007E).**

| Item | Definição exata |
|---|---|
| Normalização | `str(valor).strip().lower()`. O `strip()` do Python remove os mesmos 29 pontos de código que o DRF, os formulários do Django e o `normalize_email` já removem hoje |
| Validação | Depois de normalizar, recusar qualquer caractere fora de U+0021–U+007E, com o mesmo erro de "e-mail inválido" da API (400 no campo `email`), além do `EmailValidator` atual |
| `CHECK` | `email = lower(email) AND email ~ '^[!-~]+$'` |
| Unicidade | `UNIQUE (LOWER(email))`, como decidido, mais o `unique=True` atual |
| Equivalência | **Garantida e medida:** `lower()` idêntico em todo o ASCII. `chr(c) ~ '^[!-~]$'` coincide exatamente com 33 ≤ c ≤ 126 nos 1.112.063 pontos de código, em pt_BR. Como o valor gravado não tem nenhum espaço, as diferenças entre `strip()`, `btrim()`, `\s` e `trim()` deixam de importar |
| Migração | Além das colisões, a verificação também interrompe se alguma conta tiver, depois de normalizada, caractere fora de U+0021–U+007E, listando só os ids. No banco real seriam 0 |
| Impacto | A API passa a recusar e-mails com acento, IDN Unicode ou invisíveis, que **a interface já recusa hoje**. Domínios internacionais continuam aceitos na forma punycode (`xn--…`), que o frontend também aceita. Não há contas afetadas no banco real |

**Alternativas avaliadas e não recomendadas:**

- **Converter domínios Unicode para punycode na normalização.** Aceitaria IDN pela API. Mas o codec do Python é IDNA2003 (mapeia, por exemplo, `ß` → `ss`), diferente do IDNA2008/UTS46 dos navegadores. Exigiria mais regras e testes, e o frontend já recusa IDN.
- **Manter Unicode e criar só `UNIQUE (LOWER(email))`, sem `CHECK`.** Não atende ao requisito: 56 caracteres divergem, e os invisíveis continuam gerando duplicatas equivalentes.

### 30.3 Situação

- **AUTH-04 (P2) e AUTH-05 (P3): continuam abertos.** Não foram implementados.
- O banco real não foi acessado. Nada foi alterado no código, nos testes, nas migrações, no `.env` ou no frontend.
- A contagem não muda: 72 abertos.

**Próximo passo:** aguarda a autorização do dono para a regra "e-mail normalizado só em ASCII imprimível" (ou outra alternativa). Com ela, a implementação planejada nas seções 28 e 30.2 pode seguir com a equivalência garantida.

---

## 31. Correção do AUTH-04 e do AUTH-05 com e-mail normalizado em ASCII — 15/11/2026

**Escopo autorizado:** implementar a regra da seção 30.2 e a migração necessária, validando tudo em PostgreSQL 18.3 descartável com `pt_BR.UTF-8`.

A regra aprovada:

- espaços externos removidos com `str.strip()`;
- só ASCII imprimível de U+0021 a U+007E, checado **antes** de converter;
- endereço inteiro em minúsculas;
- sintaxe pelo validador do projeto;
- punycode aceito.

**Fora do escopo, como pedido:** aplicar a migração no banco real, REINDEX, deploy, commit e verificação de e-mail.

**Restrições cumpridas:**

- **Banco real:** não foi acessado nesta etapa, nem para leitura. Os bancos usados foram só o SQLite em memória e o PostgreSQL 18.3 descartável (`initdb --locale=pt_BR.UTF-8 --locale-provider=libc`, glibc 2.44, `127.0.0.1:55432`), já apagado. O Docker (porta 5433) e o banco antigo `barbershop` não foram usados.
- **Sem alteração:** `.env`, credenciais, frontend, os limites de taxa, SEC-13, SEC-05, TEN-03, SEC-12 e a contenção (só `JSONRenderer`).
- **Mitigação D:** só o ajuste mínimo previsto na seção 28, justificado em 31.3.
- **Repositório:** sem commit, push ou merge. As alterações locais, os documentos e as evidências anteriores foram preservados.

Evidências em [`docs/auditoria/evidencias-2026-11-15/auth-04-05-implementacao/`](auditoria/evidencias-2026-11-15/auth-04-05-implementacao/README.md).

### 31.1 Resumo

| Item | Situação |
|---|---|
| **AUTH-04** | **Resolvido e verificado no ambiente de testes.** A recuperação procura a conta pelo e-mail normalizado, com igualdade exata (`User.objects.get(email=…, is_active=True)`), sem `iexact` nem `.first()`. Uma variação de caixa não pode mais existir: a API, o manager, o `save()` e o próprio banco a recusam. Na demonstração, o token vai sempre para a conta certa, e usá-lo troca a senha da vítima, não de outra conta |
| **AUTH-05** | **Resolvido e verificado no ambiente de testes.** Cadastro, criação, edição, Django Admin, login e recuperação usam a mesma regra (`accounts/emails.py`). O e-mail gravado está sempre na forma canônica. O banco garante isso com `CHECK` e `UNIQUE (LOWER(email))` (migração `accounts.0006`). Pedidos simultâneos dão 400, não 500 |
| **Condição para a produção** | A `accounts.0006` **não foi aplicada no banco real**. A consulta de 15/11 (seção 29) não achou colisões nem contas a converter, mas a migração verifica tudo de novo e se interrompe se houver problema. A aplicação depende de autorização, de backup e de uma janela de implantação |
| **Testes** | 41 novos. Suíte de 480 para **521**, OK no SQLite, no PG 18.3 pt_BR e no PG com `DEBUG=False`. Os 211 de novos, isolamento, permissões e limites passam com `DEBUG=True`. No PostgreSQL, nenhum teste novo é pulado, inclusive concorrência real e equivalência |
| **Antes × depois (HTTP, PG pt_BR)** | Duplicatas por caixa: 7 → **0**. Respostas 500: 2 na matriz e 15 de 15 na concorrência → **0**. Login com outra caixa: 401 → **200**. Login logo após o cadastro com o domínio em maiúsculas: 401 → **200** |
| **Frontend** | Sem alteração. 45 testes, `tsc`, ESLint e build OK |

### 31.2 Arquivos alterados nesta etapa

| Arquivo | Alteração |
|---|---|
| `accounts/emails.py` (novo) | A regra única: `forma_canonica()` (sem conversão de tipo; `None` fora da regra), `normalizar_email()` (`ValidationError` fora da regra), a faixa `[!-~]` e a expressão SQL, os nomes das restrições e `e_violacao_da_unicidade_do_email()`, que reconhece só as duas restrições de unicidade do e-mail: pelo diagnóstico do driver no PostgreSQL e pelo texto padrão no SQLite |
| `accounts/models.py` | `Meta.constraints` com o `CHECK` e o `UNIQUE (LOWER(email))` (`unique=True` mantido, por causa do `auth.E003`). `clean()` próprio, no lugar dos herdados: o NFKC do `AbstractBaseUser` transformaria caracteres Unicode em ASCII antes da checagem, e o `AbstractUser` só normalizava o domínio. `validate_constraints()` sem repetir as restrições do e-mail (31.5). `save()` normaliza o e-mail sempre que ele é gravado |
| `accounts/managers.py` | `normalize_email()` passa a ser a regra única (`create_user` e `create_superuser`). `get_by_natural_key()` busca pela forma canônica, com igualdade exata. Isso cobre o login da API, o login do Django Admin e o `createsuperuser` sem mexer nas views; um valor fora da regra se comporta como conta inexistente |
| `accounts/serializers.py` | `EmailNormalizadoField`: normaliza no `to_internal_value`, **antes** do `UniqueValidator`, sem converter tipos, com as mesmas respostas de antes para entrada inválida. `EmailCanonicoMixin` aplica esse campo aos três serializers de usuário. `recusar_email_duplicado()` converte só a violação da unicidade do e-mail no mesmo 400 do validador e levanta de novo qualquer outro `IntegrityError`. Cadastro, criação e edição gravam dentro de `transaction.atomic()`, e a transação externa continua íntegra. A recuperação usa o campo normalizado e a busca exata (AUTH-04) |
| `accounts/throttles.py` | O ajuste mínimo da mitigação D (31.3) |
| `accounts/migrations/0006_email_normalizado.py` (nova) | Verificação e conversão (`RunPython`) e as duas restrições (31.4) |
| `accounts/test_auth04_auth05.py` (novo) | 41 testes (31.6) |
| `accounts/test_ten03_limites.py` | O caso `'Cliente.A1@alfa.test'` (o próprio e-mail em outra caixa) passa a **não** contar como troca, e entraram dois casos novos. É a consequência prevista na seção 28 |
| `config/test_isolamento_tenant.py` | A massa de dados gerava `freguês@alfa.test` a partir do rótulo "Freguês". O nome continua "Freguês"; a parte local do e-mail virou `fregues` (31.7) |

O diff só desta etapa está em `diff/diff-somente-auth04-auth05.patch`.

### 31.3 Ajuste mínimo na mitigação D

- **O que mudou:** só `tenta_trocar_email()`. Ela passa a comparar a forma canônica (`forma_canonica`) com o e-mail atual da conta. Um texto fora da regra, que o serializer recusa, continua contando como antes.
- **Por que é indispensável:** com a normalização, reenviar o próprio e-mail em outra caixa não troca nada. Sem o ajuste, esse pedido continuaria gastando a cota de troca de e-mail, e uma edição só de nome com o e-mail em outra caixa chegaria a 429. Isso bloquearia um usuário legítimo.
- **O que não mudou:** taxas, escopos e a identidade que consome a cota.
- **Teste** (`LimitesExistentesTests`, com as taxas reais): 15 edições com o próprio e-mail em maiúsculas dão 15×200. A troca real continua limitada: 10×400 e depois 429. Os 28 testes da mitigação D continuam passando.

### 31.4 Migração `accounts.0006_email_normalizado`

1. **`RunPython`:**
   - Verifica **todas** as contas com a mesma `forma_canonica()` da aplicação.
   - Se houver e-mail fora da regra, ou contas que ficariam com o mesmo e-mail, **interrompe**. A mensagem mostra só os ids, sem e-mails nem nomes, e nada é alterado, porque a migração é atômica. Nenhuma conta é escolhida automaticamente.
   - Se não houver problema, grava a forma canônica onde ela difere.
2. **`CHECK`:** `(email = lower(email) AND email ~ '^[!-~]+$')`. No PostgreSQL, fica `CHECK ((((email)::text = lower((email)::text)) AND ((email)::text ~ '^[!-~]+$'::text)))`.
3. **`UNIQUE (LOWER(email))`:** índice único `accounts_user_email_lower_unico`.
4. **Reversão:** retira as duas restrições. **Não recupera a grafia original** dos e-mails convertidos, porque a conversão para minúsculas não é reversível. Só um backup feito antes da migração recupera os valores anteriores.

**Validação pelo comando real `migrate`, no PG 18.3 pt_BR** (`migracao/validacao-migracao-postgresql18-ptbr.txt`), com dados antigos fictícios gravados pelo código anterior:

| Cenário | Resultado |
|---|---|
| Colisões e e-mail fora da regra | Interrompida: "Contas com e-mail fora da regra (ids): [12]. Grupos que ficariam com o mesmo e-mail após a normalização (ids): [[2, 5], [3, 4], [6, 7], [10, 11]]". A `accounts.0005` continua a última aplicada, sem restrições novas e sem dado alterado |
| Depois da decisão do dono (simulada: e-mails provisórios nas contas em conflito) | Aplicada. 0 contas fora do padrão; as duas restrições criadas |
| Reversão (`migrate accounts 0005`) | Restrições retiradas. Os e-mails continuam em minúsculas: a grafia original não volta |
| Dados antigos válidos (`Pessoa.Dois@…`, `novo.3@EXEMPLO.TEST`, espaço e tabulação nas pontas) | Convertidos para a forma canônica e aplicada |
| Escrita direta no banco depois da migração | Variação de caixa, espaço e não ASCII violam o `CHECK`; a duplicata exata viola `accounts_user_email_key` |

**Efeito sobre links de recuperação pendentes:** o hash do token do Django inclui o e-mail. Os links pendentes das contas **convertidas** deixam de valer, e a pessoa precisa pedir de novo. Pela consulta de 15/11 (seção 29), nenhuma conta do banco real seria convertida, portanto nenhum link seria invalidado. Sessões e JWT continuam valendo, porque usam o id.

### 31.5 Problemas encontrados durante a implementação

1. **A massa de dados do teste de isolamento tinha um e-mail fora da regra.** O `freguês@alfa.test` era gerado a partir do rótulo "Freguês". A API sempre recusou esse endereço, porque o `EmailValidator` não aceita acento na parte local. Ele só existia porque o `create_user` não validava o formato. Ajustada só a parte local (31.2). Os testes do TEN-01 não mudaram.
2. **Django Admin com dois erros para um e-mail duplicado.** Um era o do campo; o outro mostrava o nome interno da restrição ("Restrição "accounts_user_email_lower_unico" foi violada."). Corrigido com `validate_constraints()`. As duas restrições do e-mail já estão garantidas antes, pelo `clean()` (forma canônica) e pelo `unique=True` (duplicata), e o banco continua sendo a garantia final. Agora aparece um erro só (`testes/django-admin-mensagens*.txt`). O teste foi reforçado e as suítes foram executadas de novo com o código final.
3. **O cadastro público não associa a conta a uma barbearia existente.** Esse é o comportamento atual, não uma mudança desta etapa. Hoje o cadastro público é o fluxo do **dono**: conta sem barbearia, login, onboarding (cria a barbearia e vira admin). O cliente que agenda numa barbearia é cadastrado pelo administrador, e uma conta sem barbearia é recusada no agendamento (TEN-02); o frontend a manda para o onboarding. A página pública da barbearia, com convite, é o PROD-01, ainda aberto. Os testes de regressão cobrem os fluxos reais (31.6). Nenhum fluxo novo foi criado.
4. **Ordem das demonstrações.** No código corrigido, a demonstração do AUTH-04 troca a senha da própria vítima, o que é o comportamento certo, e isso revogou o token usado depois na corrida de troca de e-mail. A demonstração foi refeita com a concorrência antes.
5. **SQLite × PostgreSQL no `CHECK`.** No SQLite dos testes, a função `REGEXP` do Django usa o `re` do Python, em que `$` aceita um `\n` final. No PostgreSQL, `$` é o fim do texto. A aplicação nunca grava quebra de linha, porque o `strip()` remove. Os testes de escrita direta com quebra de linha foram validados no PostgreSQL.

### 31.6 Testes executados

**Os 41 testes novos** (`accounts/test_auth04_auth05.py`):

| Grupo | O que verifica |
|---|---|
| Regra única (8) | ASCII válido. Os 29 espaços externos do Python. Espaços internos. Maiúsculas. Acentos. Domínio Unicode. Punycode. U+0130 e os outros divergentes. O Kelvin (U+212A), recusado antes de virar "k". Invisíveis (U+200B, U+FEFF, U+00AD e outros 7). **Nenhum** ponto de código fora do ASCII passa (1.112.063 testados), nem controle ASCII. Entradas que não são texto. O campo da API responde como antes a não texto, `null`, vazio e inválido. Só as duas restrições de unicidade viram "e-mail duplicado" |
| Cadastro público (6) | Formas aceitas, gravadas na forma canônica. Formas recusadas com a mesma resposta do e-mail inválido. Variação de caixa de conta existente: 400 e nenhuma conta criada. **Dono: cadastro com maiúsculas → login com o texto digitado → onboarding → serviço, barbeiro e cliente criados com maiúsculas e espaços → agendamento (201)**. **Cliente cadastrado pelo admin: entra com outra caixa e agenda (201)**. Conta sem barbearia continua com 403 no agendamento (TEN-02) |
| Criação e edição (4) | Criação de cliente e de barbeiro. Duplicidade na mesma barbearia e em outra, em qualquer caixa, com a barbearia B intacta. Troca do próprio e-mail (PATCH e PUT), inclusive o próprio em outra caixa. Admin editando cliente |
| Login e recuperação (6) | Login sem diferenciar caixa e com espaços, levando à conta e à barbearia certas. Login errado com resposta igual para existente, inexistente e fora da regra. Login do Django Admin e `createsuperuser` com a mesma regra. **A recuperação vai para a conta canônica**: o destinatário é o e-mail gravado e o `uid` é dessa conta. Recuperação de inexistente e de inativa responde igual, com o envio fictício de sempre. **AUTH-04: a variação não pode ser criada pela API, pelo manager nem por `update()`, e a recuperação vai para a dona** |
| Admin, model e caminhos diretos (3) | Formulários do Django Admin: grava canônico, e duplicata, Unicode, largura total e invisível dão **um** erro no campo. Manager e `save()`. `update()` e `bulk_create()`, que contornam o `save()`, são recusados pelo banco |
| `IntegrityError` (3) | Corrida simulada (validador desligado): o 400 do validador nos três fluxos, com a transação externa utilizável. Outro `IntegrityError` não vira e-mail duplicado (500 sem a mensagem). Respostas iguais com `DEBUG` True e False |
| Isolamento (1) | O e-mail de B, em qualquer caixa, não entra em A; a lista de A só tem A; o login normalizado leva à barbearia certa |
| Limites existentes (1) | 31.3 |
| **Concorrência real, só PostgreSQL** (3) | Duas threads passam juntas pelo `UniqueValidator` (barreira) e gravam ao mesmo tempo: cadastros públicos, admins de barbearias diferentes e trocas de e-mail. Sempre um sucesso e um 400 com a mensagem de duplicidade, nunca 500, e uma conta só |
| **Equivalência, só PostgreSQL pt_BR** (2) | `lower()` igual em todo o ASCII. A faixa `[!-~]` exata em todos os pontos de código. Toda forma canônica satisfaz o `CHECK` no banco. Se o banco de teste não for pt_BR, o teste é pulado e informa isso; aqui rodou em pt_BR |
| Migração (4) | Dados antigos válidos são convertidos. Colisões interrompem sem alterar nada e mostram só ids. E-mail fora da faixa interrompe. Reversão retira as restrições e não recupera a grafia |

**Resultados com o código final:**

| Execução | Resultado |
|---|---|
| Testes novos, código anterior | Falham na importação: `accounts.emails` não existia |
| Testes novos, SQLite | 41 OK (5 pulados: os 3 de concorrência e os 2 de equivalência exigem PostgreSQL), também com `DEBUG=True` |
| Testes novos, **PG 18.3 pt_BR** | **41 OK, nenhum pulado** |
| Suíte completa, SQLite | **521 OK** (14 pulados: 9 que já existiam e 5 novos) |
| Suíte completa, PG 18.3 pt_BR | **521 OK** |
| Suíte completa, PG 18.3 pt_BR, `DEBUG=False` também na importação | **521 OK** |
| Novos, isolamento, permissões, PER-13, SEC-10, TEN-02, renderizadores, mitigação D e autenticação, `--debug-mode` | **211 OK** |
| `check`; `makemigrations --check`; `check --deploy` | Sem problemas; "No changes detected"; só o W021 (HSTS preload), que já existia |
| Frontend | 45 testes, `tsc -b`, ESLint e build OK; nenhum arquivo alterado |

**Demonstrações HTTP no PG 18.3 pt_BR** (código anterior × corrigido, `DEBUG` True e False; `api/`):

| Demonstração | Anterior | Corrigido |
|---|---|---|
| AUTH-04: terceiro cadastra `Cliente.B@beta.test` | 201; a recuperação da vítima gera o token da **conta do terceiro**; usá-lo troca a senha dele | **400**; a recuperação gera o token da **vítima**; usá-lo troca a senha dela (login com a senha nova: 200) |
| AUTH-04: variação criada por um admin em outra barbearia | 201; desvia a recuperação do admin de B | **400**; não desvia |
| AUTH-05: matriz de 3 fluxos × 10 variações | 7 duplicatas, 2 respostas 500, domínio em maiúsculas gravado na edição | **0 duplicatas, 0 respostas 500**, tudo gravado na forma canônica; idêntico com `DEBUG=True` |
| Login com a senha certa e outra caixa | 401 | **200** |
| Login logo após o cadastro com o domínio em maiúsculas | 401 | **200** |
| 15 pares de pedidos simultâneos (cadastro, criação, troca) | Um sucesso e um **500** em 15 de 15; 17 `IntegrityError` no log | Um sucesso e um **400** em 15 de 15, nas duas instâncias; 0 `IntegrityError` no log |
| Recuperação com qualquer caixa ou espaços | A conta certa, quando não havia variação gravada | A conta certa, sempre |

### 31.7 Riscos restantes

1. **A migração não está no banco real.** Precisa de autorização, de backup (`pg_dump -Fc`) e de uma janela de implantação. Pela seção 29, nada seria convertido, mas a verificação dentro da migração protege contra mudanças desde então.
2. **O código pode ir antes da migração.** Pela seção 29, todos os e-mails reais já estão na forma canônica, então o login e a recuperação funcionam. A corrida dá 400 pela `UNIQUE (email)` que já existe. Só os caminhos que contornam a aplicação ficam sem `CHECK` até a migração. O recomendado continua sendo implantar os dois juntos.
3. **DB-02:** o índice `UNIQUE (LOWER(email))` depende da ordenação do banco, que avisa versão 2.43 × 2.44. Com só ASCII gravado, o `lower()` não depende disso na prática, mas um `REINDEX` (não executado, não autorizado) continua recomendado, junto com o `REFRESH COLLATION VERSION`, numa etapa própria.
4. **Mudança de comportamento da API:** e-mails com acento, domínio Unicode ou invisíveis passam a receber 400. A interface já os recusava, e o banco real não tem nenhum. Domínios internacionais continuam aceitos em punycode.
5. **Sintaxe:** o manager e o `save()` aplicam a regra de forma e de caixa, mas não o `EmailValidator`, como antes. Pela API e pelo Django Admin, a sintaxe continua validada; pelo shell, o banco garante a forma, não a sintaxe.
6. **Fora do escopo, continuam abertos:**
   - **TEN-03:** o oráculo continua abaixo do limite. As variações de caixa agora dão o mesmo 400 do e-mail exato, sem informação nova, e o oráculo pelo 500 acabou.
   - **SEC-13, SEC-05, SEC-12, TEN-04, PROD-01 e SEC-08** (sem verificação de e-mail no cadastro).

### 31.8 Situação e contagem

- **AUTH-04 (P2) e AUTH-05 (P3): ✅ resolvidos e verificados no ambiente de testes** (PostgreSQL 18.3 `pt_BR.UTF-8` descartável e SQLite). A proteção definitiva no banco real depende de aplicar a `accounts.0006`, o que **não** foi autorizado nem feito.
- **Banco real:** não foi acessado nesta etapa. Continua sem a `accounts.0006`.

| | Após a mitigação D | Após o AUTH-04 e o AUTH-05 |
|---|---|---|
| P0 | 0 | 0 |
| P1 | 3 | 3 (BUS-06 parcial, PROD-01, AUTH-01) |
| P2 | 30 | 29 (−AUTH-04) |
| P3 | 39 | 38 (−AUTH-05) |
| **Abertos** | 63 dos 70 originais + 9 novos = 72 | **63 dos 70 originais + 7 novos = 70** |

**Próximo passo:** aguarda autorização para planejar a janela de implantação (backup, aplicação da `accounts.0006` no banco real e smoke test). Nada foi executado no banco real.

---

## 32. Revisão final do AUTH-04 e do AUTH-05 e plano de implantação da `accounts.0006` — 15/11/2026

**Escopo autorizado:** fazer uma revisão técnica independente das alterações da seção 31 e preparar o plano de uma futura implantação da `accounts.0006` no banco real. Era só leitura, análise e planejamento.

**Restrições cumpridas:**

- nenhuma conexão ao banco real, nenhuma consulta nele e nenhuma migração aplicada;
- nenhum código, teste ou migração alterado;
- nenhum dos comandos do plano executado;
- `.env`, PROD-01, TEN-03, SEC-13, SEC-05, SEC-12, TEN-04 e SEC-08 intactos;
- sem commit nem deploy.

Os arquivos do plano (consultas, wrapper de credenciais, settings do ensaio e roteiro de fumaça) estão em [`docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano/`](auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano/README.md) e só passaram por análise de sintaxe.

### 32.1 Resultado da revisão

**Nenhum critério de parada foi atingido.** Não há erro na migração, inconsistência entre modelo e migração, risco de perda de dados, problema de concorrência, teste ausente que comprometa a segurança nem alteração fora do escopo. As observações de 32.2 não bloqueiam e foram incorporadas ao plano.

**Código:**

| # | Ponto revisado | Conclusão |
|---|---|---|
| 1 | Mesma normalização em todos os caminhos de cadastro e edição | **Sim.** Os três serializers de usuário geram o campo como `EmailNormalizadoField` (via `EmailCanonicoMixin`). O manager (`normalize_email`) e o `User.save()` usam `normalizar_email`, e o Django Admin, o `User.clean()`. Todos chamam `accounts.emails.forma_canonica`. Não há outra gravação nem busca por e-mail no código de produção: a única busca é a da recuperação, já na forma canônica |
| 2 | Unicode recusado antes de converter | **Sim.** `forma_canonica` faz `strip()`, checa `[!-~]+` com `fullmatch` e só então chama `lower()`. Teste: nenhum dos 1.112.063 pontos de código fora do ASCII passa, e o Kelvin (U+212A, que viraria "k") é recusado. O NFKC herdado do `AbstractBaseUser.clean()` foi substituído |
| 3 | Valores que não são texto | **Sim.** O campo da API recusa com 'invalid' antes de qualquer conversão; `null` e vazio continuam 'null' e 'blank'. O teste compara com o `EmailField` antigo, entrada por entrada. Manager e `save()`: `ValidationError`. Login: conta inexistente |
| 4 | Login e recuperação com a mesma regra | **Sim.** Login pelo `get_by_natural_key` (forma canônica, igualdade exata); recuperação pelo `EmailNormalizadoField` |
| 5 | A recuperação não seleciona outra conta | **Sim.** `User.objects.get(email=<canônico>, is_active=True)`, sem `iexact` nem `.first()`. A unicidade (`unique=True` e `UNIQUE (LOWER(email))`) impede duas contas candidatas. Demonstrado: o token vai para a vítima, e usá-lo troca a senha dela |
| 6 | `IntegrityError`: só a unicidade pertinente | **Sim.** `e_violacao_da_unicidade_do_email` aceita só `accounts_user_email_key` e `accounts_user_email_lower_unico`, pelo `diag.constraint_name` no PostgreSQL, que independe do idioma das mensagens (validado com o servidor em pt_BR). Qualquer outro, inclusive o `CHECK`, é levantado de novo; há teste de que ele não vira "e-mail duplicado". `AdminIntegrityError` herda de `ValidationError`, não de `IntegrityError`, então a ordem dos `except` não os mistura |
| 7 | Transações íntegras depois do erro | **Sim.** Cadastro, criação e edição gravam dentro de `transaction.atomic()`. Num banco sem transação externa, o erro vem no `INSERT`/`UPDATE`, porque as restrições de unicidade do PostgreSQL não são adiáveis. Teste: a transação externa segue utilizável depois do 400 |
| 8 | Erros do Django Admin | **Sim.** Um erro só no campo, sem nome interno de restrição (ajustado na seção 31), com teste |
| 9 | Limites de requisição | **Sem mudança de comportamento.** `config/settings.py` não mudou nesta frente. A única mudança é em `tenta_trocar_email`: reenviar o próprio e-mail em outra caixa deixa de contar. Os 28 testes da mitigação D passam, e há teste com as taxas reais |
| 10 | Caminhos que contornam o `save()` | **Avaliados.** O projeto não usa `update()`, `bulk_create()`, `bulk_update()`, `get_or_create()` nem `update_or_create()` com e-mail. O `CHECK` e o `UNIQUE (LOWER(email))` recusam esses caminhos (teste com `update()` e `bulk_create()`) |

**Migração `accounts.0006_email_normalizado`:**

| Ponto | Conclusão |
|---|---|
| Detecção de colisões antes de qualquer alteração | **Sim.** Ela monta as listas e levanta a exceção antes do laço de `update()` |
| Problemas identificados só por ids | **Sim.** A mensagem só tem ids; o teste verifica que não há `@` nem nomes |
| Mesma regra do Python | **Sim.** Importa a mesma `forma_canonica` |
| `CHECK` = faixa aprovada | **Sim.** No PostgreSQL: `CHECK ((((email)::text = lower((email)::text)) AND ((email)::text ~ '^[!-~]+$'::text)))` |
| `UNIQUE (LOWER(email))` | **Sim.** `CREATE UNIQUE INDEX accounts_user_email_lower_unico ON accounts_user ((LOWER(email)))` |
| Estado das operações = modelos | **Sim.** `makemigrations --check`: "No changes detected", reconfirmado nesta etapa |
| Reversão retira as restrições | **Sim.** Testado e validado com `migrate accounts 0005` |
| Reversão não promete a grafia original | **Sim.** Está documentado na migração e na seção 31 |
| Perda de dados fora da normalização | **Não há.** Só o campo `email` é atualizado, e só quando a forma canônica difere. Não há `DELETE`. A migração é atômica |

**Aplicação ao estado atual do banco real (sem conectar):**

- A consulta da seção 29 encontrou 8 contas, 0 a normalizar, 0 fora do ASCII e 0 colisões. Com isso, a migração não converteria nada e criaria as duas restrições.
- **Lacuna (32.2, O1):** a consulta da seção 29 não verificou espaço interno, controles ASCII nem e-mail vazio. Se houver algum caso assim, a migração **se interrompe sem alterar nada**. É seguro, mas a migração não seria aplicada.
- A pré-verificação do plano (P2) usa a expressão exata do `CHECK` e resolve isso. O ensaio na cópia restaurada (P6) dá a resposta definitiva antes de tocar o banco real.

### 32.2 Observações (nenhuma bloqueia; todas foram incorporadas ao plano)

1. **O1, verificação da seção 29 incompleta para a regra exata.**
   - Faltaram espaço interno, controles ASCII (`\t`, por exemplo) e e-mail vazio.
   - Risco: só de interrupção, sem perda.
   - Tratamento: a consulta 4 de `01-pre-verificacao` e o ensaio P6.
2. **O2, nome da restrição de unicidade no banco real.**
   - A conversão do `IntegrityError` da duplicata exata depende do nome `accounts_user_email_key`. O PostgreSQL gera esse nome a partir da `accounts.0001`, e ele foi confirmado nos bancos descartáveis.
   - No real, é confirmado só por leitura em P2. Se for diferente, a duplicata simultânea voltaria a dar 500, sem risco de dado. **Nesse caso, interromper.**
3. **O3, a migração importa `forma_canonica` do app.**
   - É o que garante a mesma regra hoje. Mas mudar essa função depois mudaria o comportamento da `0006` em bancos novos.
   - **Uma mudança futura na regra deve vir com uma migração nova, não com edição silenciosa da função.**
4. **O4, travas da migração.**
   - Na mesma transação, o `ALTER TABLE … ADD CONSTRAINT … CHECK` pega `ACCESS EXCLUSIVE`, e o `CREATE UNIQUE INDEX` bloqueia gravações em `accounts_user` até o `COMMIT`, o que inclui o login.
   - Com 8 linhas, a duração é de milissegundos. O risco real é **esperar** na fila atrás de uma transação aberta e enfileirar os outros pedidos.
   - Tratamento: aplicação parada, verificação de sessões e travas (P2 e P8) e `lock_timeout=5s` na sessão do `migrate`.
5. **O5, compatibilidade entre código e migração.**
   - **Código novo sem a `0006`: compatível.** Hoje os e-mails do banco real já estão na forma canônica (seção 29), e a corrida dá 400 pela `UNIQUE (email)` que já existe.
   - **Código antigo com a `0006`: incompatível.** O `create_user` antigo gravaria maiúsculas na parte local, e o `CHECK` responderia 500.
   - Por isso, depois da migração, só o código novo pode rodar. Na reversão, primeiro reverter a `0006`, depois voltar o código.
6. **O6, buscas futuras por e-mail.**
   - Um `filter(email=…)` ou `get_or_create(email=…)` com texto não normalizado não acharia a conta.
   - Não há nenhum hoje. Orientação: sempre `forma_canonica`.
7. **O7, dependências da migração.**
   - O `makemigrations` acrescentou `barbershops.0006` (aplicada no banco real em 13/11) e `auth.0012`.
   - No banco real há a `token_blacklist.0013` aplicada sem arquivo (ENV-01). O Django ignora migração aplicada sem arquivo.
   - P2 confirma que o `migrate --plan` lista **só** a `accounts.0006`.
8. **O8, mensagens.** A API diz "usuário com este e-mail já existe." e o Django Admin, "Usuário com este E-mail já existe.". Já era assim; não é problema novo.

### 32.3 Testes e evidências

- **Reconfirmado nesta etapa** (`testes/reconfirmacao-sqlite.txt`): os arquivos de código e de teste são idênticos aos do fim da seção 31, conferidos por hash. Suíte completa no SQLite: **521 OK** (14 pulados). `makemigrations --check`: "No changes detected". `check`: sem problemas.
- **Evidências da seção 31, que valem para o código atual** (`auth-04-05-implementacao/`):
  - PG 18.3 `pt_BR.UTF-8`: **521 OK**; **521 OK** com `DEBUG=False`; 41 novos sem nenhum pulado, inclusive concorrência real e equivalência; 211 de isolamento e limites com `DEBUG=True`;
  - validação da migração pelo `migrate` real (interrupção com ids, aplicação, reversão e conversão);
  - demonstrações HTTP de antes e depois: 7 → 0 duplicatas; 500 → 400 em 15 de 15 pedidos simultâneos; login com outra caixa 401 → 200.
- **Ausências relevantes:**
  - não há teste automatizado com dados do banco real, que é coberto pelo ensaio P5 a P7;
  - não há teste do nome da restrição no banco real, que é coberto por P2.
  - Nenhuma das duas compromete a segurança, porque o plano as verifica antes da aplicação.

### 32.4 Fluxos de cadastro (situação explícita)

| Fluxo | Situação |
|---|---|
| **Cadastro público do dono** | **Funciona e está coberto.** Cadastro sem barbearia → login com o texto digitado (agora em qualquer caixa) → onboarding (cria a barbearia e vira admin) → serviços, barbeiros, clientes e agendamentos. Teste de regressão `test_dono_cadastra_entra_cria_a_barbearia_e_agenda` |
| **Cadastro administrativo do cliente** | **Funciona e está coberto.** O admin cria o cliente na própria barbearia; o cliente entra (em qualquer caixa) e agenda. Teste `test_cliente_cadastrado_pelo_admin_entra_com_outra_caixa_e_agenda` |
| **Cadastro autônomo do cliente vinculado a uma barbearia** | **Não existe no produto atual, e está fora do escopo.** O cadastro público não associa a conta a uma barbearia existente. A conta sem barbearia é recusada no agendamento (TEN-02), e o frontend a manda para o onboarding. É o **PROD-01 (P1), que continua aberto** e não foi alterado |

### 32.5 Plano de implantação (não executado)

**Princípios:**

- tudo é ensaiado antes numa cópia descartável restaurada do backup novo;
- no banco real, só leitura até o passo P8;
- a aplicação fica parada durante a migração;
- o código novo sobe logo depois;
- qualquer critério de 32.6 interrompe.

**Variáveis do roteiro** (a definir na hora, num shell `bash`):

```bash
PROJ=/home/lucasrafael/arquivos_faculdade/saas_barbearia
EVID=$PROJ/docs/auditoria/evidencias-2026-11-15/auth-04-05-revisao-e-plano
BK=$HOME/backups/barberpro
ENSAIO=<diretório NOVO e vazio no diretório temporário da sessão>   # cluster descartável e cópia restaurada
TS=$(date +%Y%m%d_%H%M%S)
ARQ=$BK/barbershop_db_${TS}_antes_accounts0006.dump                  # nunca sobrescreve o backup de 13/11
```

Na tabela, "Real" é o banco `barbershop_db` (PostgreSQL 18.3 do host, porta 5432); "Descartável" é o cluster do ensaio (`127.0.0.1:55432`); "—" é sem banco.

| Passo | Comando futuro | O que faz | Diretório | Leitura/escrita | Banco |
|---|---|---|---|---|---|
| **P0 Pré-requisitos** | Autorização expressa do dono para: janela, backup, ensaio com cópia de dados reais, aplicação e fumaça no real | — | — | — | — |
| P0 | `pg_dump --version; pg_restore --version; psql --version` | Confirma clientes 18.x, compatíveis com o servidor 18.3 | qualquer | Leitura | — |
| P0 | `locale -a \| grep -x pt_BR.utf8` | Confirma o locale do ensaio | qualquer | Leitura | — |
| P0 | `tar --exclude=./venv --exclude=./venv312 --exclude=./frontend/node_modules --exclude=./frontend/dist --exclude=./.git --exclude=./.env --exclude=./media --exclude='*.sqlite3' --exclude=./test.db -czf $BK/codigo_${TS}.tar.gz .` (antes, `test ! -e $BK/codigo_${TS}.tar.gz`) | Retrato do código atual, para eventual retorno, sem segredos | `$PROJ` | Escrita só do arquivo | — |
| **P1 Disco e disponibilidade** | `df -h $BK $ENSAIO` | Espaço livre: exigir pelo menos 10 vezes o tamanho do banco (P2) e 1 GB | qualquer | Leitura | — |
| P1 | `pg_isready -h localhost -p 5432` | O servidor aceita conexões (sem login) | qualquer | Leitura | Real (sem autenticar) |
| P1 | `pgrep -fa "manage.py runserver\|gunicorn"` | Lista os processos da aplicação, para pará-los na janela | qualquer | Leitura | — |
| **P2 Pré-verificação** | `venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -f $EVID/sql/01-pre-verificacao-somente-leitura.sql` | Identidade, migrações, restrições, regra exata do `CHECK` (só ids), sessões e travas | `$PROJ` | **Leitura** (`READ ONLY`) | **Real** |
| P2 | `venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -f $EVID/sql/03-contagem-de-linhas-somente-leitura.sql` | Contagens, guardadas para comparar com a cópia | `$PROJ` | **Leitura** | **Real** |
| P2 | `PGOPTIONS='-c default_transaction_read_only=on' venv/bin/python manage.py showmigrations accounts barbershops` e `PGOPTIONS='-c default_transaction_read_only=on' venv/bin/python manage.py migrate --plan` | Estado das migrações; o plano deve listar **só** `accounts.0006` | `$PROJ` | **Leitura** (sessão somente leitura) | **Real** |
| **P3 Backup novo** | `mkdir -p $BK && chmod 700 $BK && test ! -e "$ARQ"` | Garante que não sobrescreve nada | qualquer | Escrita local | — |
| P3 | `venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- pg_dump -Fc --no-password -f "$ARQ" && chmod 600 "$ARQ"` | Backup completo em formato custom | `$PROJ` | **Leitura** no banco; escrita só do arquivo | **Real** |
| **P4 Integridade do backup** | `ls -l "$ARQ"; sha256sum "$ARQ" \| tee "$ARQ.sha256"; pg_restore --list "$ARQ" > /dev/null && echo LISTA_OK; pg_restore --list "$ARQ" \| grep -c 'TABLE DATA'; pg_restore --list "$ARQ" \| grep 'TABLE DATA public accounts_user'` | Arquivo não vazio, hash guardado, índice legível, tabelas presentes | qualquer | Leitura do arquivo | — |
| **P5 Restauração de teste** | `initdb -D $ENSAIO/pgdata -U smoke --auth=trust -E UTF8 --locale=pt_BR.UTF-8 --locale-provider=libc`, mais `listen_addresses='127.0.0.1'`, `port=55432` e `unix_socket_directories=''` no `postgresql.conf`; depois `pg_ctl -D $ENSAIO/pgdata -l $ENSAIO/pg.log -w start` | Cluster descartável igual ao real (pt_BR, libc) | qualquer | Escrita | **Descartável** |
| P5 | `psql -X -h 127.0.0.1 -p 55432 -U smoke -d postgres -c "create database ensaio_restaurado template template0"` e `pg_restore --no-owner --no-privileges --exit-on-error -h 127.0.0.1 -p 55432 -U smoke -d ensaio_restaurado "$ARQ"` | Restaura o backup na cópia | qualquer | Escrita | **Descartável** |
| P5 | `psql -X -h 127.0.0.1 -p 55432 -U smoke -d ensaio_restaurado -f $EVID/sql/03-contagem-de-linhas-somente-leitura.sql` e o mesmo com `01-pre-verificacao` | As contagens e a pré-verificação devem ser **idênticas** às de P2 | qualquer | Leitura | **Descartável** |
| **P6 Ensaio da migração** | `K=$(python3 -c 'import secrets;print(secrets.token_urlsafe(64))')`; `SECRET_KEY=$K DEBUG=False PYTHONPATH=$EVID/scripts:. venv/bin/python manage.py migrate --plan --settings=ensaio_settings` | Mesmo plano de P2, agora na cópia. A `SECRET_KEY` aleatória impede que um token do ensaio valha na aplicação real | `$PROJ` | Leitura | **Descartável** |
| P6 | `SECRET_KEY=$K DEBUG=False PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' PYTHONPATH=$EVID/scripts:. venv/bin/python manage.py migrate accounts 0006 --settings=ensaio_settings` | **Aplica a 0006 na cópia** dos dados reais | `$PROJ` | Escrita | **Descartável** |
| P6 | `psql -X -h 127.0.0.1 -p 55432 -U smoke -d ensaio_restaurado -f $EVID/sql/02-pos-verificacao-somente-leitura.sql` | Restrições criadas e válidas; 0 fora da regra | qualquer | Leitura | **Descartável** |
| **P7 Fumaça na cópia** | `SECRET_KEY=$K DEBUG=False PYTHONPATH=$EVID/scripts:. venv/bin/python manage.py runserver 127.0.0.1:8899 --noreload --settings=ensaio_settings` (em segundo plano) e `python3 -I $EVID/scripts/fumaca.py completo http://127.0.0.1:8899` | Cadastro, login, onboarding, agendamento (dono e cliente), recuperação, variação e não ASCII recusados | `$PROJ` | Escrita (dados fictícios) | **Descartável** |
| P7 | Encerrar o `runserver` pelo PID; `pg_ctl -D $ENSAIO/pgdata -m fast -w stop && rm -rf $ENSAIO` | **Apaga a cópia**, que tem dados reais | qualquer | Escrita | **Descartável** |
| **P8 Aplicação** | Parar a aplicação. Repetir as consultas 5 e 6 de `01-pre-verificacao` (como em P2): nenhuma sessão da aplicação e nenhuma trava | Janela limpa | `$PROJ` | Leitura | **Real** |
| P8 | `PGOPTIONS='-c lock_timeout=5s -c statement_timeout=60s' venv/bin/python manage.py migrate accounts 0006` | **Aplica a 0006.** Esperado: "Applying accounts.0006_email_normalizado... OK" | `$PROJ` | **ESCRITA** | **Real** |
| **P9 Pós-verificação** | `venv/bin/python $EVID/scripts/com_credenciais_da_app.py --somente-leitura -- psql -X -v ON_ERROR_STOP=1 -f $EVID/sql/02-pos-verificacao-somente-leitura.sql` | `CHECK` e `UNIQUE (LOWER(email))` presentes e válidos; 0 fora da regra; mesmo número de contas | `$PROJ` | **Leitura** | **Real** |
| P9 | `PGOPTIONS='-c default_transaction_read_only=on' venv/bin/python manage.py showmigrations accounts` e `venv/bin/python manage.py check` | `[X] 0006_email_normalizado`; sem problemas | `$PROJ` | Leitura | **Real** |
| **P10 Subir o código novo** | Iniciar a aplicação pelo mesmo comando de sempre, a partir de `$PROJ` (o código novo já está na árvore) | — | `$PROJ` | Uso normal | **Real** |
| **P11 Fumaça no real** | `FUMACA_EMAIL_EXISTENTE=<e-mail do dono, digitado na hora> python3 -I $EVID/scripts/fumaca.py sem-escrita http://<endereço da API>` | API no ar; login errado 401; não ASCII 400; variação de caixa de e-mail existente 400 (sem criar conta); recuperação de inexistente 204 | qualquer | **Nenhum pedido grava no banco** | **Real** |
| P11 | **Com autorização expressa, pela interface:** login do dono com o e-mail em outra caixa; pedido de recuperação do próprio e-mail; um agendamento de teste com um cliente de teste, cancelado em seguida | Fluxos reais de ponta a ponta | navegador | **ESCRITA** (token de sessão, agendamento) | **Real** |
| **P12 Registro** | Guardar nas evidências só saídas sem dados pessoais (P2 sem as listas de ids, se o dono preferir; P9; P11), o hash do backup e o horário. Atualizar o relatório de forma aditiva | — | `$PROJ/docs` | Escrita de documentos | — |

**Coordenação entre código e migração** (32.2, O5):

- **A ordem é:** parar a aplicação → P8 → P9 → P10 (código novo).
- **O código novo já está na árvore e é compatível com o banco sem a `0006`.** Se a janela não acontecer antes de 17/11, a aplicação pode rodar como está.
- **O código antigo não pode rodar com a `0006` aplicada.**
- **O código não tem commit.** Decidir se faz commit antes da janela é do dono e está fora deste plano. O retrato de P0 serve de referência.

### 32.6 Critérios objetivos de interrupção

Qualquer item abaixo **interrompe** a implantação. Não se tenta de novo às cegas; registra-se e volta-se ao dono.

1. **P0 e P1:**
   - falta de autorização;
   - cliente PostgreSQL abaixo de 18;
   - sem `pt_BR.utf8`;
   - espaço livre menor que 10 vezes o banco ou menor que 1 GB;
   - servidor indisponível.
2. **P2, identidade e migrações:**
   - banco diferente de `barbershop_db`, versão diferente de 18.3 ou porta diferente de 5432;
   - `accounts.0006` já presente;
   - `migrate --plan` com qualquer outra migração além da `accounts.0006`;
   - `barbershops.0006` ou `auth.0012` ausentes.
3. **P2, restrições e dados:**
   - restrição de unicidade do e-mail com nome diferente de `accounts_user_email_key` (O2);
   - `violariam_o_check` > 0, `vazios` > 0 ou grupos > 0. Nesse caso, vai para decisão do dono, como na seção 28.5; não se "migra para ver".
4. **P2 e P8, sessões e travas:**
   - sessão da aplicação ativa;
   - qualquer `idle in transaction`;
   - transação aberta há mais de 60 segundos;
   - trava em `accounts_user`.
5. **P3 e P4, backup:**
   - `pg_dump` com código de saída diferente de 0;
   - arquivo vazio;
   - `pg_restore --list` com erro;
   - `accounts_user` ausente da lista;
   - hash não registrado.
6. **P5, restauração:**
   - erro do `pg_restore`;
   - contagens diferentes das de P2;
   - pré-verificação diferente da de P2.
7. **P6 e P7, ensaio:**
   - a migração falha ou é interrompida na cópia;
   - a pós-verificação falha;
   - qualquer falha no `fumaca.py completo`.
8. **P8, aplicação:**
   - qualquer erro, `lock_timeout` ou `statement_timeout`.

   A migração é atômica: o PostgreSQL desfaz tudo. Seguir R1.
9. **P9, pós-verificação:**
   - restrição ausente;
   - índice com `indisvalid` falso;
   - contas fora da regra;
   - número de contas diferente;
   - `0006` não registrada.

   Seguir R2.
10. **P11, fumaça no real:**
    - qualquer 500;
    - falha de login de conta existente;
    - recuperação diferente de 204;
    - falha de agendamento.

    Seguir R3.

### 32.7 Procedimento de recuperação

| Caso | Procedimento | Leitura/escrita | Banco |
|---|---|---|---|
| **R1. A migração falhou em P8** | Nada a desfazer: a migração é atômica e o PostgreSQL faz o `ROLLBACK`. Confirmar com `01-pre-verificacao` (a `accounts` continua em 0005 e não há restrição nova). A aplicação pode subir com o código novo, que é compatível sem a `0006`. Investigar na cópia (P5 a P7) antes de qualquer nova tentativa | Leitura | Real |
| **R2. Pós-verificação ou comportamento errado com a `0006` aplicada** | `PGOPTIONS='-c lock_timeout=5s' venv/bin/python manage.py migrate accounts 0005`, a partir de `$PROJ`. A reversão retira as duas restrições. Os e-mails convertidos **não** voltam à grafia original; pela seção 29, nenhum seria convertido. Depois, `01-pre-verificacao` e subir o código novo | **Escrita** | Real |
| **R3. O código novo falha na fumaça** | Parar a aplicação. Primeiro **R2** (nunca o código antigo com a `0006`). Depois, se o dono decidir voltar o código, extrair o retrato de P0 **num diretório separado** (`mkdir <novo>; tar -xzf $BK/codigo_${TS}.tar.gz -C <novo>`), sem sobrescrever a árvore de trabalho com as alterações não commitadas, e rodar a aplicação de lá, com o mesmo `.env` (um link simbólico, sem copiar nem alterar). Exige autorização | Escrita local | Real (uso normal) |
| **R4. Dano de dados (último recurso)** | Só com autorização expressa e a aplicação parada. Restaurar o backup de P3: `pg_restore --clean --if-exists --no-owner --single-transaction -d barbershop_db "$ARQ"`, com as credenciais da aplicação. **Perde tudo o que foi gravado depois do backup.** Alternativa menos destrutiva: restaurar num banco novo e trocar o `DATABASE_URL`, o que exige alterar o `.env` e outra autorização, e talvez um papel com `CREATEDB`. O backup de 13/11 continua guardado como segunda linha | **ESCRITA destrutiva** | Real |

### 32.8 Riscos

| Risco | Probabilidade | Mitigação |
|---|---|---|
| A migração se interrompe por dado fora da regra não visto na seção 29 (O1) | Baixa | P2 com a regra exata e o ensaio P6. Interromper não altera nada |
| Fila de travas atrás de uma transação aberta (O4) | Baixa com a aplicação parada | P2 e P8 (sessões e travas); `lock_timeout=5s` |
| Duplicata simultânea voltar a dar 500 por nome de restrição diferente (O2) | Muito baixa | P2 confirma o nome; se for diferente, interromper |
| Código antigo rodando com a `0006` (O5) | Baixa | Ordem de 32.5; R3 começa por R2 |
| Links de recuperação pendentes invalidados | Nula hoje (0 conversões) | — |
| Cópia restaurada com dados reais exposta | Baixa | Fica só no diretório temporário, com e-mail em `locmem`, `SECRET_KEY` aleatória, e é apagada no fim de P7; nenhuma saída com dados pessoais vai para as evidências |
| DB-02 (ordenação 2.43 × 2.44) | Baixa para a `0006` (só ASCII) | `REINDEX` e `REFRESH COLLATION VERSION` numa etapa própria, não incluída aqui |
| Apresentação de 17/11 | — | Se não houver janela segura antes, manter o código novo sem a `0006` (compatível); a garantia do banco fica para depois |

### 32.9 Situação

- **AUTH-04 (P2) e AUTH-05 (P3): ✅ resolvidos e verificados no ambiente de testes** (seção 31). A revisão independente confirmou a implementação. A garantia no banco real depende da `accounts.0006`, **não aplicada**.
- **PROD-01 (P1): aberto.** O cadastro autônomo do cliente vinculado a uma barbearia não existe e não foi alterado.
- **Banco real:** não foi acessado nesta etapa. Sem a `accounts.0006`.
- **Contagem:** sem mudança, **70 abertos**.

**Próximo passo:** aguarda autorização para executar o plano de 32.5, ou parte dele, por exemplo só P0 a P7 (backup e ensaio, sem tocar no esquema do banco real).

---

## 33. Execução de P0 a P7 do plano da `accounts.0006` — 15/11/2026

**Escopo autorizado:** P0 a P7 do plano da seção 32:

- cópia local do código;
- consultas só de leitura no banco real;
- backup novo e sua verificação;
- restauração em PostgreSQL descartável;
- migração e testes de fumaça **só na cópia**.

**Não autorizado e não executado:** P8, P9, P10, P11 e P12, e qualquer escrita no banco real.

Evidências em [`docs/auditoria/evidencias-2026-11-15/auth-04-05-p0-p7/`](auditoria/evidencias-2026-11-15/auth-04-05-p0-p7/README.md).

### 33.1 Resumo

| Etapa | Resultado |
|---|---|
| **P0 Preparação** | Diretório novo e privado (0700) `/home/lucasrafael/backups/barberpro/accounts0006_20261115_224006/`. Cópia isolada do backend (107 arquivos, idênticos ao original por SHA-256), sem `.env`. Retrato do código para eventual retorno (349.115 bytes, 0600, sem `.env*`). O primeiro retrato foi refeito: 33.3. Repositório original e `git status` preservados |
| **P1 Servidor** | 353 GB livres em `/home` e 7,3 GB em `/tmp` (o banco tem 9,4 MB). PostgreSQL do host aceitando conexões em 5432; Docker em 5433, não usado. Clientes 18.3, glibc 2.44, `pt_BR.utf8` disponível. Portas 55432 e 8899 livres. Nenhum processo da aplicação rodando. **Identidade configurada confere** (`barbershop_db`, localhost, 5432, usuário esperado), sem exibir credenciais |
| **P2 Banco real (leitura)** | **Identidade confirmada:** `barbershop_db`, PostgreSQL 18.3, `::1:5432`, usuário esperado, sessão somente leitura, `pt_BR.UTF-8` (libc, versão de ordenação 2.43). `accounts` até a 0005; `barbershops.0006` e `auth.0012` aplicadas. `migrate --plan`: **só a `accounts.0006`**. Restrição de unicidade: **`accounts_user_email_key`**, o nome que o código espera (O2 resolvida). **Regra exata: 8 contas, 8 já canônicas, 0 a normalizar, 0 fora da regra, 0 colisões.** Nenhuma outra sessão, nenhuma trava |
| **P3 e P4 Backup** | `pg_dump -Fc` em sessão somente leitura: `barbershop_db_20261115_224006_antes_accounts0006.dump`, **63.004 bytes**, 0600, SHA-256 **`5eb831d6b973bd82337d3936efd1b8ef707329cb7e2f2f9f2707b31bbc21af95`**. `pg_restore --list`: código 0, 139 itens, 16 tabelas com dados, as 8 principais presentes. Contagens no banco real idênticas antes e depois. Mesma lista de objetos do backup de 13/11, que continua intacto |
| **P5 Restauração descartável** | PostgreSQL 18.3, `pt_BR.UTF-8`, libc, glibc 2.44, escutando só em `127.0.0.1:55432`, com marca de identidade. `pg_restore` com código 0, sem mensagens. Isolamento: só `plpgsql`, nenhum servidor externo, e-mail sem saída de rede. **Contagens idênticas** ao banco real; **estrutura idêntica** ao backup (108 objetos); pré-verificações **idênticas** às da P2 |
| **P6 Ensaio da migração** | Pela própria `forma_canonica` sobre a cópia: 0 fora da regra, 0 a normalizar, 0 colisões. `migrate --plan`: só a `accounts.0006`. **"Applying accounts.0006_email_normalizado... OK".** `CHECK` validado; índice único em `lower(email)` válido e pronto; 0 contas fora da regra; e-mails inalterados. `migrate --check` e `makemigrations --check` sem pendências. **Reversão:** retirou as duas restrições, manteve a `UNIQUE` original e não alterou os e-mails. Reaplicação OK |
| **P7 Fumaça na cópia** | **12 de 12** do roteiro do plano e **28 de 28** do complemento. **0 respostas 500** e 0 tracebacks no log da API do ensaio |
| **Banco real** | **Nenhuma escrita.** A conferência final (só leitura) mostra o banco idêntico à P2: `accounts.0006` ausente, nenhuma restrição nova, mesmas contagens |
| **P8** | **Não executada** |

### 33.2 Detalhes

- **Regra exata em SQL (P2).** O SQL do plano (`01-pre-verificacao`) só verificava se o e-mail **já** estava na forma canônica.
  - Para a regra **exata** da migração, foi gerado um SQL a partir do próprio Python: `btrim` com os 29 pontos de código que o `str.strip()` remove, a faixa `[!-~]` checada antes da conversão, e `lower()` só no ASCII.
  - Antes de ir ao banco real, ele foi comparado com `forma_canonica` no banco descartável pt_BR: **3.336.202 casos** (todos os pontos de código em três posições, mais casos fixos), **0 divergências** (`saidas/prova-equivalencia-sql-python.txt`).
  - Na cópia, a mesma conclusão veio da própria função da migração.
- **Testes de fumaça (P7)**, todos com dados fictícios e só na cópia:
  - **roteiro do plano:** cadastro público do dono com maiúsculas; login logo depois, com o mesmo texto; variação de caixa e e-mail não ASCII recusados; onboarding; serviço, barbeiro e cliente criados pelo admin; agendamento pelo dono; login do cliente com outra caixa e agendamento pelo próprio cliente; recuperação com outra caixa;
  - **complemento:** duas barbearias fictícias. O admin de A só lista contas de A, não lê nem edita o cliente de B (404), só vê a própria barbearia e não cria conta com o e-mail do cliente de B em outra caixa. Edição do próprio e-mail grava a forma canônica, e a edição para o e-mail de outra conta ou para não ASCII dá 400. Cadastro com e-mail inválido (espaço interno, invisível, `İ`, número) dá 400. **Recuperação de senha seguida até o fim, com o e-mail capturado em arquivo local:** destinatário e conta do token conferem; a confirmação troca a senha; login com a senha nova (outra caixa) dá 200 e com a antiga, 401; e-mail inexistente dá 204.
  - **Configuração:** limites de taxa reais; `SECRET_KEY` aleatória; e-mail em arquivo local (`locmem` no `ensaio_settings`).
- **Segurança das credenciais:**
  - as credenciais do banco real só foram lidas pelas settings da aplicação e passadas ao `psql`/`pg_dump` por variáveis de ambiente;
  - não foram impressas, não estiveram na linha de comando, e não houve `set -x`;
  - tudo foi gravado com `umask 077`.

### 33.3 Problemas encontrados

1. **O primeiro retrato do código incluía arquivos que deviam ficar de fora.** A lista de exclusões do plano (seção 32.5, P0) não previa:
   - **`frontend/.env`** (115 bytes; o conteúdo não foi aberto);
   - uma segunda pasta **`.venv`**;
   - pastas de ferramentas (`.claude`, `.agents`).

   O arquivo, com 39,6 MB, foi detectado pela própria verificação do script. Depois de conferir que fora criado minutos antes, nesta execução e no diretório novo, foi **apagado junto com o seu `.sha256`**. Não era o backup do banco, que ainda não existia. Ele foi refeito por **lista de inclusão**: backend e fontes do frontend, sem `.env*` (349.115 bytes). **Para uma janela futura, o P0 do plano deve usar a lista de inclusão desta execução** (`scripts/p0_retrato.sh`), e não a de exclusão da seção 32.5.
2. **Falhas dos scripts desta execução, corrigidas sem efeito em banco:**
   - o `sha256sum` falhou com entradas que são diretórios, e o script parou antes de criar qualquer coisa;
   - o CSV da prova de equivalência tratava o campo vazio como `NULL`;
   - uma limpeza redundante de tabela temporária;
   - uma conferência no zsh sem divisão de palavras, refeita em `bash`.
3. **Diferença de tamanho entre os backups:** 119.639 bytes em 13/11 × 63.004 bytes agora. A estrutura dos dois é idêntica: 143 itens, 16 tabelas com dados, mesma lista de objetos. A diferença vem do volume de dados de cada data; a restauração confere com o banco atual.
4. **Versão de ordenação:** o banco real registra 2.43, e a cópia restaurada nasceu com 2.44 (DB-02, já registrado). Não interfere na `0006`, porque o e-mail fica só em ASCII.

### 33.4 Riscos para a janela de P8

- **Nenhum bloqueio encontrado:**
  - o estado do banco real é o esperado pelo plano;
  - a migração aplica e reverte na cópia fiel;
  - os fluxos funcionam sem 500.
- **Continuam valendo:**
  - os critérios de interrupção da seção 32.6, com a pré-verificação **repetida no momento** da janela, já que os dados podem mudar até lá;
  - a aplicação parada durante a migração;
  - o código antigo nunca roda com a `0006` aplicada.
- **O backup desta execução vale como referência deste momento.** O plano prevê um backup novo **na própria janela**, porque o banco pode receber gravações até lá.

### 33.5 Situação

- **AUTH-04 (P2) e AUTH-05 (P3):** resolvidos e verificados no ambiente de testes. **Ensaio de implantação aprovado na cópia fiel do banco real.** A `accounts.0006` **não** foi aplicada no banco real.
- **PROD-01:** aberto, sem alteração.
- **Banco real:** sem nenhuma escrita. Backup novo preservado.
- **Contagem:** sem mudança, 70 abertos.

**Próximo passo:** aguarda autorização expressa e separada para P8 (aplicação no banco real) e as etapas seguintes.

---

## 34. Aplicação da `accounts.0006` no banco real (P8) e etapas P9 a P12 — 15/11/2026

**Autorizações**, em duas mensagens separadas do dono:

1. **P8:** repetir as pré-verificações, fazer um backup imediato e aplicar **só** a `accounts.0006` no banco real, com `lock_timeout=5s`.
2. **P9 a P12:**
   - P9: pós-verificação somente leitura;
   - P10: subir a aplicação;
   - P11: testes **somente de leitura**, sem POST, PUT, PATCH ou DELETE e sem nada que grave;
   - P12: este registro.

**Não autorizado e não feito:**

- nenhuma escrita além da própria migração;
- nenhuma reversão ou restauração;
- nenhum REINDEX nem tratamento do DB-02;
- nenhuma alteração de código, `.env` ou dependências;
- nenhum deploy, commit, push ou merge;
- PROD-01 não foi implementado.

Evidências em [`docs/auditoria/evidencias-2026-11-15/auth-04-05-p8-p12/`](auditoria/evidencias-2026-11-15/auth-04-05-p8-p12/README.md).

### 34.1 Resumo

| Etapa | Resultado |
|---|---|
| **P8 Pré-verificações (leitura)** | **Sem nenhuma divergência em relação ao ensaio P0–P7.** Identidade: `barbershop_db`, PostgreSQL 18.3, `::1:5432`, usuário esperado, `pt_BR.UTF-8`, libc, versão de ordenação 2.43. Não é o banco antigo `barbershop` nem o Docker (5433). Código: os 107 arquivos do backend, inclusive a migração, idênticos por SHA-256 aos do ensaio. `accounts` até a 0005; o `migrate --plan` lista só a `accounts.0006`. Restrição `accounts_user_email_key`. Regra exata: **8 contas, 8 canônicas, 0 a normalizar, 0 fora da regra, 0 colisões**. Contagens iguais às da P2. Nenhuma outra sessão, nenhuma transação aberta, nenhuma trava e nenhum processo da aplicação |
| **P8 Backup imediato** | `pg_dump -Fc` em sessão somente leitura, às 22:55:52. Arquivo `/home/lucasrafael/backups/barberpro/accounts0006_p8_20261115_225552/barbershop_db_20261115_225552_p8_antes_accounts0006.dump`: **63.004 bytes**, arquivo 0600, diretório novo 0700, SHA-256 **`5a4c028b39b4f2c4274e24042b47e863ca9fd7318a17c376453ab9ceed513279`**. `pg_restore --list`: código 0, 139 itens, 16 tabelas com dados, as 8 principais presentes; o próprio arquivo registra `dbname: barbershop_db` e `Dumped from database version: 18.3`. Mesma lista de objetos do backup do ensaio. Contagens iguais antes e depois |
| **P8 Migração** | Rodou num processo que, **na mesma conexão do `migrate`**, conferiu antes a identidade, o `lock_timeout` de 5 s, a ausência de outras sessões e travas e o plano (só a 0006); qualquer divergência o pararia antes. Das 22:56:21 às 22:56:22: **"Applying accounts.0006_email_normalizado... OK"**, código de saída 0. Nenhum SQL manual, nenhuma outra migração, nenhuma correção em registros. Único aviso: o da versão de ordenação ao conectar (DB-02, não tratado) |
| **P9 Pós-verificação (leitura)** | **Aprovada.** `accounts.0006` registrada às 22:56:22. `CHECK accounts_user_email_normalizado` presente e validado, com a expressão aprovada: `email = lower(email) AND email ~ '^[!-~]+$'`. Índice único `accounts_user_email_lower_unico` em `lower(email)`, válido e pronto. **`accounts_user_email_key` preservada.** 8 contas, 0 fora da regra; pela regra exata, 8 canônicas e 0 colisões. Todas as tabelas com as contagens de antes da P8, exceto `django_migrations` (53 → 54, o registro da 0006). `showmigrations`: `[X] 0006_email_normalizado`; `migrate --plan`: nenhuma operação; `migrate --check`: código 0 |
| **P10 Aplicação** | **Backend e frontend no ar.** Código idêntico ao conferido antes da migração: 199 arquivos do retrato da P0 (lista de inclusão), 0 diferenças, e os 107 do backend. **Inicialização sem escrita automática:** nenhum `ready()`, sinal ou consulta em nível de módulo; cache em memória; sessões gravadas só quando modificadas; `UPDATE_LAST_LOGIN = False`. Pelo procedimento do README, **sem `migrate` e sem `npm install`**: `python manage.py runserver` em `127.0.0.1:8000` (lista de serviços sem login: 401 JSON) e `npm run dev` em `localhost:5173` (Vite 6.4.3: 200). Contadores de escrita iguais aos de antes |
| **P11 Fumaça só leitura** | **26 de 26 OK, 0 respostas 500, 0 tracebacks, nenhuma escrita.** São 19 pedidos HTTP (só GET e OPTIONS, sem login) e 7 verificações internas numa sessão `default_transaction_read_only=on` (34.3) |
| **P12** | Esta seção e a pasta de evidências nova |

### 34.2 Prova de que P10 e P11 não gravaram nada

Os contadores do PostgreSQL de linhas inseridas, atualizadas e excluídas (`n_tup_ins`, `n_tup_upd`, `n_tup_del` e `n_tup_hot_upd` de `pg_stat_user_tables`, 17 tabelas) foram fotografados em quatro momentos, sempre em sessão somente leitura:

1. **S0**, no fim da P9;
2. **S1**, depois de subir a aplicação;
3. **S2**, depois dos testes;
4. **S3**, no fim.

**Os quatro são idênticos.** As verificações internas, além disso, rodaram numa sessão que o próprio PostgreSQL impediria de gravar.

### 34.3 Testes executados na P11

| Grupo | Teste | Resultado |
|---|---|---|
| Backend sem login | Serviços, `users/me`, agendamentos, barbearia e barbeiros (GET) | 401 JSON nos 5 |
| Rotas de escrita | GET em login, cadastro e recuperação | 405 nos 3 (as rotas existem e só aceitam POST) |
| | OPTIONS no cadastro | 200 (metadados, sem gravar) |
| Contenção do TEN-01 | `Accept: text/html` | 406 |
| | `?format=api` | 404 (nunca HTML da API navegável) |
| CORS | Preflight OPTIONS do login vindo de `http://localhost:5173` | 200, com `Access-Control-Allow-Origin` do frontend |
| Django Admin | Página de login (GET, sem enviar o formulário) | 200 |
| Frontend | Página inicial, `/login`, `/register`, `/password/reset` e o módulo principal | 200 nos 5 |
| Regra de e-mail (interno, leitura) | As 8 contas reais na forma canônica | 8/8 |
| | A busca do login (`get_by_natural_key`) acha a mesma conta com o e-mail em MAIÚSCULAS | 8/8 |
| | Idem, com caixa trocada e espaços nas pontas | 8/8 |
| | A busca exata da recuperação acha a própria conta ativa a partir de outra caixa | 8/8 |
| | Conta inativa não é encontrada | 0/0: **não há contas inativas**, então o teste não se aplica |
| | O cadastro, **só validado e sem `save()`**, recusa a variação de caixa de cada e-mail existente como duplicado (`unique`) | 8/8 |
| | O cadastro, também só validado, recusa e-mails fora da regra como inválidos (acento, espaço interno, invisível e `K` Kelvin) | 4/4 |

Nenhum teste imprimiu e-mail, nome ou id: só contagens.

### 34.4 Testes não executados por exigirem escrita ou POST (pendentes de autorização separada)

| Teste | Por que não foi executado |
|---|---|
| **Login real** (API e Django Admin) | POST. O login pela API grava um `OutstandingToken`, e o do Admin grava uma sessão |
| **Qualquer fluxo autenticado**, mesmo só de leitura (`users/me`, listas da barbearia, painéis no navegador) | Exige um token, e obtê-lo exige o login, que grava. **Gerar um token fora do fluxo**, com a chave da aplicação, seria contornar a restrição e mexer num segredo, e por isso não foi feito |
| Renovação de token e logout | Gravam (rotação e lista negra) |
| Cadastro público e criação de conta pelo admin | Gravam contas |
| Edição de e-mail ou senha | Gravam |
| Recuperação de senha e confirmação | POST; a confirmação troca a senha e invalida o token |
| Onboarding, serviços, barbeiros e agendamentos (criar ou cancelar) | Gravam |
| **`fumaca.py sem-escrita` do plano** (seção 32: login errado de conta fictícia, cadastro com e-mail não ASCII, cadastro com variação de caixa e recuperação de e-mail inexistente) | São POSTs, proibidos nesta P11, embora não devessem gravar. **A mesma regra do lado do servidor foi conferida pelas verificações internas sem `save()`** (34.3). A resposta HTTP desses fluxos no banco real continua pendente |

O comportamento completo desses fluxos, inclusive com escrita, já foi verificado na **cópia fiel** do banco real (P7, seção 33: 40 de 40 OK) e nos testes automatizados (seção 31).

### 34.5 Estado e riscos

- **A aplicação continua no ar**, em modo de desenvolvimento, iniciada nesta sessão em segundo plano. A partir de agora, qualquer uso real (login, cadastro, agendamento) **grava no banco real normalmente**. Isso é a operação da aplicação, não uma etapa desta auditoria.
- **O código antigo não pode mais rodar contra o banco real.** Ele gravaria e-mails fora da forma canônica, o `CHECK` recusaria e a resposta seria 500.
  - **Risco novo:** o código corrigido existe **só como alterações não commitadas** na árvore de trabalho (`git status`). Um `git checkout`, `git stash` ou `git restore` faria a aplicação voltar ao código incompatível.
  - Recomenda-se **commitar as alterações da auditoria**, o que depende de autorização. O retrato da P0 (`codigo_20261115_224006.tar.gz`) guarda uma cópia.
- **Caminho de volta,** que depende de nova autorização:
  - a reversão da 0006 (`migrate accounts 0005`) foi ensaiada na cópia (P6) e retira as duas restrições sem alterar os e-mails;
  - o backup da P8 permite restaurar o estado de 22:55:52.
- **DB-02:** o aviso da versão de ordenação (2.43 × 2.44) aparece em cada conexão. Não foi tratado.
- **PROD-01:** aberto, sem alteração.

### 34.6 Situação

- **AUTH-04 (P2) e AUTH-05 (P3): ✅ resolvidos, com a `accounts.0006` aplicada no banco real e pós-verificada.** A proteção agora está no código **e** no banco (`CHECK` e `UNIQUE (LOWER(email))`). Os testes funcionais com escrita no banco real continuam pendentes de autorização (34.4).
- **Banco real:**
  - a única escrita desta etapa foi a `accounts.0006`: duas restrições novas e o registro em `django_migrations`;
  - nenhuma conta precisou de normalização, e as 8 continuam iguais e na forma canônica;
  - os backups foram preservados.
- **Contagem:** sem mudança, **70 abertos**, já sem o AUTH-04 e o AUTH-05 (seção 31).

**Próximo passo:** aguarda nova autorização antes de qualquer operação que escreva no banco real, inclusive os testes da 34.4 e o commit do código.
