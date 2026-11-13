# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primário: o dono da barbearia.** Dono de barbearia pequena e independente (1 a 5 barbeiros) que corta e administra ao mesmo tempo. Usa o BarberPro no computador do balcão ou do escritório e no celular, inclusive fora da barbearia. Precisa manter a agenda cheia e sem conflito, gerir equipe, serviços e clientes, e saber quanto a barbearia faturou. Quando uma decisão favorece um perfil em detrimento de outro, o dono vem primeiro.

**Barbeiro.** Usa no celular, entre um atendimento e outro. Consulta a agenda do dia e os intervalos livres e muda o status dos atendimentos (confirmar, concluir, cancelar).

**Cliente da barbearia.** Usa no celular. Agenda um horário (serviço → barbeiro → data/horário → confirmação), acompanha os próximos horários, reagenda e cancela.

**Avaliadores acadêmicos.** Neste momento, a banca e os professores do projeto de extensão avaliam o sistema na apresentação final.

## Product Purpose

O BarberPro é um SaaS multi-tenant de gestão de barbearias: agenda, equipe, serviços, clientes e faturamento num só lugar, com um painel para cada perfil.

Ele nasceu como projeto de extensão da faculdade. Primeiro vem a entrega e a apresentação acadêmica; depois, a intenção é transformá-lo em produto real para barbearias.

- **Sucesso agora:** os fluxos dos três perfis funcionam de ponta a ponta numa demonstração ao vivo, e o que é mostrado corresponde ao que o sistema de fato faz.
- **Sucesso depois:** barbearias pequenas reais usando o sistema no dia a dia.

## Positioning

O BarberPro afirma quatro coisas. Cada uma se apoia em um mecanismo que existe no código:

1. **Agenda sem conflito.** Só são oferecidos horários realmente livres (`/appointments/available-slots/`), e o servidor recusa marcações conflitantes com bloqueio de linha (`select_for_update()`). Dois clientes nunca ficam com o mesmo horário do mesmo barbeiro.
2. **Números confiáveis.** O faturamento é calculado pelo preço praticado no momento do agendamento (`preco_historico`), não pelo preço atual do serviço.
3. **Simples para quem corta.** Feito para o dono que atende e administra ao mesmo tempo, sem curva de aprendizado.
4. **Dados isolados e seguros.** Cada barbearia só enxerga os próprios dados. A auditoria de 11/11/2026 bloqueou 16 de 16 tentativas de acesso cruzado.

Toda afirmação pública precisa continuar verdadeira diante das pendências abertas da auditoria. Por exemplo, os horários livres ainda ignoram dias fechados (BUS-06), então "sem conflito" trata de marcação dupla, não de dias de funcionamento.

## Operating Context

- **No balcão:** o dono alterna entre a cadeira e a tela e é interrompido o tempo todo. As consultas precisam ser rápidas, e a tarefa precisa poder ser retomada.
- **Entre cortes:** o barbeiro olha a agenda e atualiza o status pelo celular, em poucos segundos.
- **Na mão do cliente:** o agendamento acontece no celular, fora da barbearia.
- **Ciclo do atendimento:** agendado → confirmado → realizado, ou cancelado em qualquer ponto. O painel do admin organiza o dia em um quadro por barbeiro. A agenda do barbeiro mostra os intervalos livres e uma visão "a confirmar".
- **Apresentação acadêmica:** demonstração ao vivo com uma barbearia fictícia. Slides fazem parte da entrega (requisito 72).
- **Localidade:** português do Brasil (`pt-br`), fuso `America/Sao_Paulo` e valores em reais (BRL).

## Capabilities and Constraints

**Perfis:** `admin` (o dono, rotulado "Administrador" ou "dono"), `barbeiro` e `cliente`. O superusuário do Django usa o Django Admin, e não existe painel de Super Admin.

**O que funciona hoje:**
- Autenticação: login, cadastro, logout, troca de senha, recuperação de senha e renovação de sessão por cookie HttpOnly.
- Proteção de rotas por perfil.
- Onboarding da barbearia.
- Cliente: início com o próximo horário e os contatos da barbearia, serviços e preços, equipe, agendamento guiado com horários reais, reagendamento e cancelamento.
- Barbeiro: agenda por dia com intervalos livres, visão "a confirmar" e ações de status.
- Admin: quadro do dia por barbeiro, indicadores de 30 dias, agendamentos com busca e filtros, CRUD de serviços, barbeiros e clientes com desativação e reativação, dados e horário da barbearia.
- Todos os perfis: "Minha conta".

**Restrições confirmadas no código e na auditoria (`docs/AUDITORIA_BARBERPRO.md`):**
- A barbearia tem um único horário de funcionamento, que vale para todos os dias. Não existem dias fechados, folgas, feriados nem horário por barbeiro.
- O cadastro público cria um `cliente` sem barbearia, que segue para o onboarding e cria a própria barbearia. Clientes de uma barbearia que já existe são cadastrados pelo admin. O autocadastro de clientes numa barbearia está ausente (PROD-01).
- A recuperação de senha não envia e-mail na configuração atual (AUTH-01).
- O logo da barbearia existe só na API, sem tela (FE-09).
- Não há notificações (e-mail, lembrete ou WhatsApp).
- O sistema não está pronto para produção: a auditoria de 11/11/2026 listou 53 problemas, 2 deles críticos.
- O design precisa ser responsivo e funcionar no celular e no desktop (requisito 33, Must).

**Terminologia da interface:** barbearia, barbeiro, serviço, agendamento, horário, "quadro do dia", "a confirmar", "Minha conta". Os status são agendado, confirmado, realizado e cancelado.

**Ainda não decidido:** planos, preço e cobrança do SaaS; o mecanismo de autocadastro de clientes (página pública, convite ou código); comissões de barbeiros; avaliação de atendimento; estoque (marcado como versão 2.0 nos requisitos); notificações.

## Brand Commitments

- **Nome:** BarberPro.
- **Voz:** português do Brasil, tratando por "você". Direta e cordial, com frases curtas, sem gíria e sem formalidade excessiva. Exemplos atuais: "Olá, {primeiro nome}", "Que tal já deixar o próximo corte reservado?", "Escolha o serviço, o barbeiro e um horário livre em poucos passos."
- **Ativo existente:** o ícone `frontend/public/favicon.svg`.

## Evidence on Hand

**O que existe de verdade:**
- Requisitos com 77 cartões priorizados em MoSCoW: `requisitos_barbearia.docx`.
- Auditoria técnica e funcional de 11/11/2026: `docs/AUDITORIA_BARBERPRO.md`. As capturas de tela estão em `docs/auditoria/evidencias/*.png`, e as sondagens e verificações em `docs/auditoria/evidencias/*.txt`.
- Documentação da API: `docs/arquitetura/DOCUMENTACAO_API.md`.
- 239 testes de backend, incluindo os de isolamento entre barbearias.

**O que não existe:** não há barbearia parceira real, clientes pagantes, depoimentos, métricas de uso, imprensa nem tabela de preços. Nada disso pode ser inventado. Os dados de demonstração são de uma barbearia fictícia e precisam ser apresentados como tal.

O relatório de entrega de 10/11/2026 (`docs/auditorias/RELATORIO_ENTREGA_FINAL.md`) diz que o sistema está "100% pronto" para distribuição profissional. A auditoria de 11/11/2026 substitui essa afirmação, que não deve ser repetida.

## Product Principles

1. **O dono vem primeiro.** Em qualquer conflito, decide-se a favor do dono de barbearia pequena, que corta e administra ao mesmo tempo.
2. **Só prometer o que o sistema garante.** Um horário oferecido está livre, um número exibido vem de dado real e o estado do sistema (sem conexão, fechado, sem dados) é mostrado como ele é. Nenhum dado, cliente ou depoimento é inventado.
3. **Cabe no intervalo entre cortes.** As tarefas frequentes de cada perfil se resolvem em poucos toques no celular, sem treinamento.
4. **Cada barbearia é um mundo fechado.** Nenhum dado atravessa barbearias, e o que cada perfil pode ver ou fazer é regra de produto, não detalhe técnico.
