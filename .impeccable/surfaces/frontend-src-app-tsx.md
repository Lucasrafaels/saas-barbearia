---
version: 1
slug: "frontend-src-app-tsx"
primary_target: "frontend/src/App.tsx"
related_targets: ["frontend/src/components/AppLayout.tsx","frontend/index.html","frontend/src/styles/design-tokens.css"]
---

# Aplicativo BarberPro (área autenticada)

## Escopo e modo
- Telas autenticadas dos três perfis: painel e cadastros do dono, agenda do barbeiro e área do cliente, incluindo o fluxo de agendamento. Também login, cadastro, recuperação de senha e onboarding.
- Modo: Operate. O mundo empresta só tipografia, paleta, densidade e uma assinatura; layout, navegação e controles seguem o padrão da web.
- A página pública institucional (Persuade) terá uma surface brief própria na etapa 7.

## Público, tarefa e prova
- O dono de barbearia pequena, que corta e administra ao mesmo tempo, vê o dia de relance e age sem procurar: confirmar, encaixar, conferir o caixa.
- O barbeiro resolve a agenda no celular entre um corte e outro.
- O cliente agenda em poucos toques.
- Prova: horários livres reais, conflito recusado, caixa calculado pelo preço histórico. Dados de demonstração sempre rotulados como fictícios.

## Restrições
- Backend, API, banco, autenticação, regras de negócio, `.env` e SECRET_KEY ficam intocados.
- Todas as funcionalidades atuais, a responsividade e a acessibilidade são preservadas.
- Sem novas dependências. As fontes ficam hospedadas no próprio projeto.
- Identidade (etapa 1): `frontend/src/assets/brand/`.

## Direction contract
THESIS: O BarberPro é a placa esmaltada da barbearia americana dos anos 30 e 40 transformada em ferramenta: marinho estrutural, vermelho só para "agora, atenção, ação" e letra de letreiro nos títulos. Recusa o back-office genérico (cards iguais, blocos de KPI, roxo de tecnologia) e a caricatura vintage (bigodes, "EST. 19XX", desgaste falso).

OWN-WORLD:
- Marinho: #102143, #192F57, #284273, #E7EDF8.
- Vermelho poste: #C12D2E, e #A32224 para texto.
- Marfim (#F8F4EB, #ECE6D8) como papel; branco porcelana nas superfícies; tinta #0E1727 e #535D6E.
- Verde #29734E só para sucesso.
- O vermelho nunca toca o marinho sem branco entre os dois.
- League Gothic em caixa-alta nos títulos; Public Sans com algarismos tabulares na interface.
- O filete duplo de placa aparece só em selos, comanda e tabela de preços.
- Símbolo: navalha aberta. A lâmina é a haste do B; o pino e o cabo ficam no pé.

STORY: O dono abre o painel e entende o dia: quem está na cadeira, o que vem a seguir e quanto entrou. Confia nos números e age em um toque. Barbeiro e cliente fazem o mesmo no celular.

FIRST VIEWPORT: Painel do dono a 1440 px.
- À esquerda, trilho marinho com o logo, a barbearia com o poste girando ("Aberta até 19:00") e a navegação; o item ativo vira uma plaqueta marfim.
- No topo, faixa branca com a data, "N a confirmar" em vermelho e a conta.
- Título PAINEL em League Gothic.
- Faixa única de caixa: realizado de previsto, 30 dias com histórico, ticket médio e cancelamentos.
- Quadro do dia com uma coluna por barbeiro, ocupando a largura, e a linha do agora listrada passando por trás dos blocos.
- Coluna "A seguir" com Confirmar na própria linha.
- Ação principal em marinho.

FORM: Mundo fixado pelo usuário ("Classic American Barbershop meets Modern Digital Experience"), na forma de placa esmaltada. É o primeiro da lista ordenada da proposta; não houve sorteio porque a direção veio fixada.
- Assinatura: o poste gira quando a barbearia está aberta e marca o "agora"; fica parado quando ela fecha ou com movimento reduzido.
- Pico do cliente: carimbo "Horário reservado".
seed: none (sorteio não executado: direção fixada pelo dono antes do build)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Emendas após o build (2026-11-12)
Registradas na revisão final para alinhar o contrato ao que foi entregue (o DESIGN.md já as descreve):
- O filete duplo também aparece nas duas placas marinho grandes (trilho lateral e painel da tela de entrada): elas são as próprias placas esmaltadas.
- League Gothic também nos numerais de letreiro: hora da comanda, dia no seletor de datas, passos da página pública e carimbo.
- Nas superfícies de marca (tela de entrada e página pública), o poste é a placa da casa: faixa listrada no painel de entrada e poste lateral da página pública. Na área autenticada continua significando só "aberta/agora".

## Decisões em aberto
- Copy final da página pública.
- Fonte das fotografias: sessão numa barbearia parceira ou banco licenciado.
- Vitrine de cada barbearia: só desenho nesta fase, porque depende do backend.
