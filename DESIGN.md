---
name: BarberPro
description: Gestão de barbearia com a voz da placa esmaltada americana dos anos 30 e 40, em forma de ferramenta.
colors:
  marinho-900: "#102143"
  marinho-800: "#192f57"
  marinho-700: "#284273"
  marinho-600: "#3a5488"
  marinho-300: "#9fb0cf"
  marinho-200: "#c9d4e8"
  marinho-100: "#e7edf8"
  marinho-50: "#f3f6fb"
  vermelho-600: "#c12d2e"
  vermelho-700: "#a32224"
  vermelho-200: "#edc1bc"
  vermelho-100: "#fbe7e4"
  marfim: "#f8f4eb"
  marfim-2: "#ece6d8"
  marfim-claro: "#fbf9f4"
  branco: "#ffffff"
  tinta: "#0e1727"
  tinta-2: "#535d6e"
  tinta-3: "#666e7e"
  linha: "#e4dfd4"
  linha-forte: "#d2cbbe"
  linha-campo: "#8f8878"
  verde: "#29734e"
  verde-100: "#e3efe8"
typography:
  display:
    fontFamily: "'League Gothic', 'Arial Narrow', 'Roboto Condensed', sans-serif"
    fontSize: "3.25rem"
    fontWeight: 400
    lineHeight: 0.92
    letterSpacing: "0.012em"
  headline:
    fontFamily: "'League Gothic', 'Arial Narrow', 'Roboto Condensed', sans-serif"
    fontSize: "2rem"
    fontWeight: 400
    lineHeight: 0.95
    letterSpacing: "0.02em"
  title:
    fontFamily: "'Public Sans', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  body:
    fontFamily: "'Public Sans', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: "'Public Sans', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.3
  numeric:
    fontFamily: "'Public Sans', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
    fontFeature: "'tnum'"
  label:
    fontFamily: "'Public Sans', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.06em"
rounded:
  radius-sm: "6px"
  radius-md: "8px"
  radius-lg: "12px"
  radius-xl: "18px"
  radius-pill: "999px"
spacing:
  space-1: "0.25rem"
  space-2: "0.5rem"
  space-3: "0.75rem"
  space-4: "1rem"
  space-5: "1.25rem"
  space-6: "1.5rem"
  space-8: "2rem"
  space-10: "2.5rem"
  space-12: "3rem"
  space-16: "4rem"
components:
  button:
    backgroundColor: "{colors.marinho-900}"
    textColor: "{colors.marfim}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.radius-md}"
    padding: "0 1rem"
    height: "2.75rem"
  button-hover:
    backgroundColor: "{colors.marinho-800}"
    textColor: "{colors.branco}"
  secondaryButton:
    backgroundColor: "{colors.branco}"
    textColor: "{colors.marinho-900}"
    rounded: "{rounded.radius-md}"
    padding: "0 1rem"
    height: "2.75rem"
  secondaryButton-hover:
    backgroundColor: "{colors.marinho-50}"
  ghostButton:
    textColor: "{colors.marinho-900}"
    rounded: "{rounded.radius-md}"
    padding: "0 0.75rem"
    height: "2.75rem"
  dangerButton:
    backgroundColor: "{colors.branco}"
    textColor: "{colors.vermelho-700}"
    rounded: "{rounded.radius-md}"
    padding: "0 1rem"
    height: "2.75rem"
  dangerSolidButton:
    backgroundColor: "{colors.vermelho-600}"
    textColor: "{colors.branco}"
    rounded: "{rounded.radius-md}"
    padding: "0 1rem"
    height: "2.75rem"
  input:
    backgroundColor: "{colors.branco}"
    textColor: "{colors.tinta}"
    typography: "{typography.body}"
    rounded: "{rounded.radius-md}"
    padding: "0 0.75rem"
    height: "2.75rem"
  panel:
    backgroundColor: "{colors.branco}"
    rounded: "{rounded.radius-lg}"
    padding: "1.25rem"
  navLink:
    textColor: "{colors.marfim}"
    rounded: "{rounded.radius-md}"
    padding: "0 0.75rem"
    height: "2.625rem"
  navLinkActive:
    backgroundColor: "{colors.marfim}"
    textColor: "{colors.marinho-900}"
  status_agendado:
    backgroundColor: "{colors.branco}"
    textColor: "{colors.marinho-900}"
    rounded: "{rounded.radius-pill}"
    height: "1.5rem"
  status_confirmado:
    backgroundColor: "{colors.marinho-900}"
    textColor: "{colors.marfim}"
    rounded: "{rounded.radius-pill}"
    height: "1.5rem"
  status_realizado:
    backgroundColor: "{colors.verde-100}"
    textColor: "{colors.verde}"
    rounded: "{rounded.radius-pill}"
    height: "1.5rem"
  status_cancelado:
    backgroundColor: "{colors.vermelho-100}"
    textColor: "{colors.vermelho-700}"
    rounded: "{rounded.radius-pill}"
    height: "1.5rem"
  s_confirmado:
    backgroundColor: "{colors.marinho-900}"
    textColor: "{colors.marfim}"
    rounded: "{rounded.radius-sm}"
    padding: "4px 8px"
  s_realizado:
    backgroundColor: "{colors.marfim-2}"
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.radius-sm}"
    padding: "4px 1.5rem 4px 8px"
  slotSelected:
    backgroundColor: "{colors.marinho-900}"
    textColor: "{colors.marfim}"
    rounded: "{rounded.radius-md}"
    height: "2.75rem"
  toast:
    backgroundColor: "{colors.marinho-900}"
    textColor: "{colors.marfim}"
    rounded: "{rounded.radius-md}"
    padding: "0.75rem 0.75rem 0.75rem 1rem"
---

# Design System: BarberPro

## Overview

**Creative North Star: "Esmalte & Navalha"**

O BarberPro é a placa esmaltada da barbearia americana dos anos 30 e 40 transformada em ferramenta. O marinho é a estrutura (trilho lateral, ação principal, títulos, o status confirmado), o vermelho de poste aparece só para "agora, atenção, ação", e o marfim é o papel sobre o qual as superfícies de porcelana branca descansam. Os títulos e os numerais de letreiro falam com a letra de letreiro (League Gothic em caixa-alta); a interface é Public Sans, sóbria e legível, com algarismos tabulares onde há hora ou dinheiro.

Na área autenticada (modo Operate) o mundo empresta só tipografia, paleta, densidade e uma assinatura: layout, navegação e controles seguem o padrão da web. A densidade é de ferramenta de trabalho: painéis divididos por filetes de 1px, tabelas que viram listas no celular, quadro do dia como protagonista. Na página pública (`/conheca`, modo Persuade) o mesmo mundo aparece por inteiro: campo marinho, títulos enormes de letreiro e ilustrações em traço de gravura.

O sistema recusa dois desvios na mesma medida: o back-office genérico (cards iguais, blocos de KPI, roxo de tecnologia) e a caricatura vintage (bigodes, "EST. 19XX", desgaste falso, grão). A época vem da letra, da cor e do filete, nunca de textura envelhecida.

**Key Characteristics:**
- Marinho estrutural, vermelho raro e com significado, marfim como papel, branco como superfície.
- O vermelho nunca toca o marinho sem branco entre os dois.
- League Gothic em caixa-alta só nos títulos; Public Sans com algarismos tabulares na interface.
- Assinatura única: as listras do poste (`--listras-poste`) querem dizer "aberta/agora" na área autenticada; nas superfícies de marca (tela de entrada e página pública) são a placa da casa.
- Status lido pela forma, não só pela cor.
- Plano por padrão; sombra só no que flutua ou responde ao toque.

## Colors

Placa esmaltada: um azul-marinho profundo carregando quase tudo, um vermelho de poste usado com parcimônia, e papel marfim quente por baixo.

### Primary
- **Marinho Placa** (`--marinho-900`, #102143): estrutura. Trilho lateral, botão principal, títulos (`--color-heading`), avatar, toast, bloco e selo "confirmado", horário escolhido, item de data selecionado, primeiro indicador da faixa de caixa.
- **Marinho Fundo de Trilho** (`--marinho-800`): hover do botão principal e dos itens do trilho; cartão da barbearia dentro do trilho.
- **Marinho Tinta de Link** (`--marinho-700`): links e botões de texto (`--color-accent-text`), anel e contorno de foco (`--color-focus`), cursor de digitação.
- **Marinho Médio** (`--marinho-600`): hover de borda em campos e opções; contorno tracejado do bloco "agendado".
- **Escala clara** (`--marinho-300`, `--marinho-200`, `--marinho-100`, `--marinho-50`): texto secundário sobre marinho (300/200), sublinhado de link (200), selo de destaque e opção selecionada (100), hover de linha de tabela e de botão secundário (50).

### Secondary
- **Vermelho Poste** (`--vermelho-600`, #c12d2e): "agora, atenção, ação". Rótulo da hora atual no quadro e na agenda, contorno das pendências "a confirmar", marcador da aba ativa no celular, dia de hoje no seletor de datas e no gráfico, passo atual no fluxo de agendamento, carimbo "Horário reservado", CTA da página pública, ação destrutiva sólida.
- **Vermelho Texto** (`--vermelho-700`, #a32224): o vermelho quando é texto sobre claro (erros, status cancelado, ações destrutivas discretas) e o hover do vermelho sólido.
- **Vermelho Claro** (`--vermelho-200`, `--vermelho-100`): bordas e fundos de erro, hachura do cancelado.

### Tertiary
- **Verde Realizado** (`--verde`, #29734e; fundo `--verde-100`): só sucesso e "realizado" (visto do bloco realizado, alertas de sucesso, interruptor ligado).

### Neutral
- **Marfim** (`--marfim`, #f8f4eb): o papel. Fundo da aplicação (`--color-bg`), texto sobre marinho (`--color-text-inverse`), item ativo do trilho.
- **Marfim Fundo** (`--marfim-2`): trilho do controle segmentado, bloco "realizado" recuado, avatar apagado.
- **Marfim Claro** (`--marfim-claro`): faixas internas de painel (`--color-surface-muted`): cabeçalho de tabela, barra de ferramentas, rodapé de painel e de modal.
- **Branco Porcelana** (`--branco`): superfícies de trabalho (`--color-surface`) e a separação obrigatória entre vermelho e marinho.
- **Tinta** (`--tinta`, #0e1727): texto corrido (`--color-text`).
- **Tinta Suave** (`--tinta-2`): texto secundário (`--color-text-muted`), rótulos de dado. **Tinta Placeholder** (`--tinta-3`): placeholder e ícones apagados.
- **Linhas** (`--linha`, `--linha-forte`, `--linha-campo`): divisória de painel (`--color-border`), divisória forte e borda de opção (`--color-border-strong`), borda de campo de formulário (3,4:1 sobre branco).

Os nomes antigos (`--ink-*`, `--paper`, `--stone-*`, `--copper*`, `--brass`, `--success`, `--danger*`) são aliases de compatibilidade que apontam para a paleta acima. Não usar em código novo.

### Named Rules
**The Branco no Meio Rule.** O vermelho nunca encosta no marinho (contraste de só 2,8:1). Entre os dois há sempre branco: listras do poste, anel do emblema, contorno branco interno do CTA sobre o campo marinho, anel branco das pendências.

**The Vermelho Significa Agora Rule.** O vermelho de poste só marca "agora, atenção, ação". Nunca decora, nunca é cor de marca em área grande, nunca é a ação principal da área autenticada (essa é marinho).

**The Verde Só Sucesso Rule.** O verde aparece apenas para sucesso e "realizado".

## Typography

**Display Font:** League Gothic (com 'Arial Narrow', 'Roboto Condensed', sans-serif), hospedada em `assets/fonts/league-gothic-latin.woff2`
**Body Font:** Public Sans (com ui-sans-serif, system-ui), hospedada em `assets/fonts/public-sans-latin.woff2`, eixo de peso 100 a 900

**Character:** A League Gothic (revival da Alternate Gothic, 1903) é a letra do letreiro pintado: estreita, alta, sempre em caixa-alta. A Public Sans, descendente da Franklin Gothic, é da mesma família de época, mas trabalha calada em tamanhos de interface.

### Hierarchy
- **Display** (League Gothic 400, 2.5rem no celular e 3.25rem a partir de 900px, altura de linha 0.92, caixa-alta): título de página ("PAINEL"). Nas telas de entrada vai a 3rem; na página pública o título principal vai de 4.25rem a 10rem (`clamp`) com altura de linha 0.84.
- **Headline** (League Gothic 400, 1.75rem a 2.25rem, altura de linha 0.95, espaçamento 0.015em a 0.02em, caixa-alta): títulos de bloco com voz de marca ("CAIXA", cartão da barbearia, etapa do agendamento, resumo da reserva).
- **Title** (Public Sans 700, `--fs-18` / `--fs-16`, `--lh-tight`): títulos de painel ("Quadro do dia", "A seguir"). Os `h1` a `h4` base vão de `--fs-24` a `--fs-14` em marinho.
- **Body** (Public Sans 400, `--fs-16`, `--lh-body` 1.55): texto corrido; descrições limitadas a 62ch. `--fs-14` com `--lh-snug` para texto secundário, células de tabela, botões.
- **Numeric** (Public Sans 700, algarismos tabulares): valores da faixa de caixa (1.875rem, -0.02em), horários de "A seguir" (`--fs-18`), preços (`--fs-21`), régua de horas e horários dos blocos (`--fs-12`).
- **Label** (Public Sans 700, `--fs-12`, espaçamento 0.06em, caixa-alta, `--tinta-2`): rótulo de dado preso ao valor (cabeçalho de tabela, rótulo de indicador, `dt` da comanda e do caixa, grupo do trilho).

Escala de interface: `--fs-12` · `--fs-14` · `--fs-16` · `--fs-18` · `--fs-21` · `--fs-24` · `--fs-36` · `--fs-48`. Pesos: `--fw-regular`, `--fw-medium`, `--fw-semibold`, `--fw-bold`. Campos de formulário usam sempre `--fs-16` (evita zoom no iOS).

### Named Rules
**The Letreiro Rule.** League Gothic em títulos e nos numerais de letreiro (hora grande da comanda, número do dia no seletor de datas, números dos passos da página pública, carimbo da reserva), sempre em caixa-alta e peso 400. Texto corrido, botões, rótulos, campos e dados de tabela ficam em Public Sans.

**The Algarismo Tabular Rule.** Todo horário, valor em reais, contagem e eixo de gráfico usa `font-variant-numeric: tabular-nums`, para as colunas não dançarem.

## Layout

Grade de aplicação: trilho lateral marinho de `--sidebar-w` (16rem; recolhido em `--sidebar-w-collapsed`, 4.75rem) e conteúdo sobre marfim limitado a `--content-max` (80rem). Páginas estreitas (58rem e 68rem) mantêm a mesma borda esquerda das largas, para o título não pular ao navegar. Barra superior branca de `--topbar-h` com data, pendências "a confirmar" e conta.

Abaixo de 1024px o trilho vira gaveta e aparece a barra inferior branca (`--tabbar-h`, 4.25rem) com a aba ativa marcada por um filete vermelho no topo; toasts e ações fixas de etapa sobem acima dela, respeitando `safe-area-inset-bottom`. Abaixo de 760px as tabelas viram listas empilhadas com rótulo por célula. Abaixo de 640px o modal vira folha inferior, os filtros segmentados rolam de lado e o quadro do dia mostra um barbeiro por vez, com seletor.

Painel do dono: faixa única de caixa (um painel dividido em quatro, nunca quatro cards) e, a partir de 1180px, quadro do dia ocupando a largura com a coluna "A seguir" (21rem) fixa ao lado. O fluxo de agendamento usa a mesma proporção com resumo lateral de 21rem.

Ritmo de espaço em base 4px (`--space-1` a `--space-16`). Entre blocos de página, `--space-6`; padding interno de painel, `--space-5`; linhas de tabela, `--space-4` por `--space-5`. Controles têm `--control-h` (2.75rem) e `--control-h-sm` (2.25rem).

## Elevation & Depth

Plano por padrão: a profundidade vem de porcelana branca sobre papel marfim, filetes de 1px (`--linha`) e faixas internas em marfim claro. Sombra existe só no que flutua (menus, gavetas, modal, toast) ou como resposta ao toque (bloco do quadro, opção selecionável, comanda), sempre tingida de marinho, nunca preta na área autenticada.

### Shadow Vocabulary
- **Raise** (`--shadow-raise`: `0 1px 2px rgb(16 33 67 / 0.06), 0 8px 18px -10px rgb(16 33 67 / 0.22)`): hover de bloco do quadro e de opção, comanda do próximo horário.
- **Overlay** (`--shadow-overlay`: `0 1px 2px rgb(16 33 67 / 0.08), 0 22px 44px -16px rgb(16 33 67 / 0.38)`): modal, toast, menu da conta, gaveta.
- **Foco** (`--ring-focus`: `0 0 0 3px rgb(40 66 115 / 0.24)`): anel de foco de campos. Demais elementos usam contorno de 2px `--marinho-700` com afastamento de 2px.

### Named Rules
**The Plano em Repouso Rule.** Painéis em repouso não têm sombra (no máximo `0 1px 0` a 3% de marinho). Sombra é estado ou camada, nunca enfeite.

## Shapes

Os raios crescem com o tamanho do objeto, como os cantos de uma placa esmaltada: `--radius-sm` (6px) em blocos do quadro, segmentos e etiquetas pequenas; `--radius-md` (8px) em botões, campos, horários, alertas e toasts; `--radius-lg` (12px) em painéis, comanda e opções; `--radius-xl` (18px) em modal e grandes placas da página pública; `--radius-pill` em selos de status, poste e contadores.

O filete duplo da placa (uma linha fina por dentro da borda, afastada alguns pixels) é o ornamento do mundo, e é reservado: as duas placas marinho grandes (trilho lateral e painel da tela de entrada), selos (avatar como medalha, emblema, carimbo), a comanda do próximo horário (canhoto marinho com filete interno e picote) e a tabela de preços (contorno interno afastado 6px; na página pública, a tabela pintada dos perfis). Pontilhado guia (`dotted --marinho-300`) liga nome e preço nas tabelas de preço. Linhas tracejadas (`dashed --linha-forte`) separam os fatos da comanda e marcam a grade do gráfico.

### Named Rules
**The Filete Reservado Rule.** O filete duplo aparece só nas duas placas marinho grandes (trilho lateral e painel da tela de entrada), em selos, na comanda e na tabela de preços. Painel comum tem uma borda de 1px e mais nada.

## Components

### Buttons
Firmes e quietos: a hierarquia é marinho cheio > contorno > fantasma > texto.
- **Shape:** cantos suaves (`--radius-md`), altura `--control-h` (2.75rem) ou `--control-h-sm` (2.25rem) na variante pequena; Public Sans 600 em `--fs-14`.
- **Primário:** marinho cheio com letra marfim e uma sombra de 1px; é a ação principal de cada tela.
- **Hover / Focus:** primário escurece para `--marinho-800` com sombra marinho difusa; secundário ganha borda marinho e fundo `--marinho-50`; fantasma ganha fundo marinho a 6%. Ao pressionar, `scale(0.97)`. Foco: contorno 2px `--marinho-700`. Desabilitado: 45% de opacidade.
- **Secundário:** branco com borda `--linha-campo` e letra marinho (ex.: "Confirmar" na linha de "A seguir").
- **Destrutivos:** `dangerButton` branco com letra `--vermelho-700` e borda `--vermelho-200`; `dangerSolidButton` vermelho cheio só para confirmar destruição; `ghostDanger` para "Cancelar" ao lado de "Confirmar".
- **Página pública:** o CTA é vermelho com contorno branco interno de 2px, para nunca tocar o campo marinho; ao lado, botão fantasma de borda marfim.

### Status de agendamento
O vocabulário é por forma, nunca só por cor, e sempre com rótulo:
- **Agendado:** contorno tracejado marinho (`1.5px dashed --marinho-600`) sobre branco.
- **Confirmado:** marinho cheio, letra marfim.
- **Realizado:** marfim recuado (`--marfim-2`, texto `--tinta-2`) com visto verde desenhado em CSS.
- **Cancelado:** hachura vermelha a 135° (branco e `--vermelho-100`), borda tracejada `--vermelho-200`, nome e hora riscados em `--vermelho-600`.

O quadro do dia (`board.module.css`) e sua legenda implementam esse vocabulário integralmente. Os selos em pílula (`status_*`, 1.5rem de altura, `--fs-12` 700) acompanham com um marcador: anel vazio no agendado, ponto marfim no confirmado, ícone de visto ou xis nos demais.

### Cards / Containers
- **Corner Style:** `--radius-lg`.
- **Background:** branco porcelana sobre marfim.
- **Shadow Strategy:** plano em repouso (ver Elevation & Depth).
- **Border:** 1px `--color-border`; cabeçalho e rodapé separados por filete, rodapé e barra de ferramentas em `--color-surface-muted`.
- **Internal Padding:** `--space-4` por `--space-5` no cabeçalho, `--space-5` no corpo.
- A faixa de caixa é um único painel dividido por filetes verticais; o primeiro indicador (o dia de hoje) fica em placa marinho.

### Inputs / Fields
- **Style:** branco, borda 1px `--linha-campo`, `--radius-md`, altura `--control-h`, texto `--fs-16`. Select com seta marinho desenhada em SVG.
- **Focus:** borda `--marinho-700` com `--ring-focus`; hover em `--marinho-600`.
- **Error / Disabled:** erro com borda `--vermelho-600` e anel vermelho a 18%, mensagem em `--vermelho-700` com ícone; desabilitado em `--color-surface-muted` com texto suave.
- **Controle segmentado:** trilho `--marfim-2`, segmento escolhido vira plaqueta branca com contador marinho cheio.
- **Horários e datas:** botões de horário brancos com borda `--linha-forte`, marinho cheio quando escolhidos; o dia de hoje tem contorno vermelho de 1.5px.

### Navigation
- **Trilho (desktop):** marinho, logo horizontal fundo escuro no topo, cartão da barbearia com o poste e "Aberta até HH:MM", grupos com rótulo `--marinho-300` em caixa-alta. Itens em Public Sans 500 `--fs-14`, marfim a 82%; hover em `--marinho-800`; o item ativo vira uma plaqueta marfim com letra marinho em 700.
- **Barra inferior (celular, abaixo de 1024px):** branca, ícone e rótulo de 0.6875rem; a aba ativa fica marinho em 700 com filete vermelho de 3px no topo.
- **Pendências:** pílula com contorno vermelho de 1.5px e contador vermelho cheio ("N a confirmar").

### Poste de barbearia (assinatura)
As listras do poste (`--listras-poste`: vermelho, branco, marinho, branco a -45°) significam "aberta/agora" na área autenticada, e só isso:
- **Indicador de barbearia aberta:** poste vertical de 7 a 8px de largura que gira enquanto ela está aberta; parado, em cinza e a 55-60% quando fecha.
- **Linha do agora:** poste deitado de 5 a 6px atravessando o quadro do dia (atrás dos blocos) e a agenda em lista, com o rótulo da hora em vermelho cheio e algarismos tabulares.
- **Loader:** poste em pílula de 0.875 por 1.75rem com anel branco e anel marinho, girando.
Com `prefers-reduced-motion`, o poste fica parado.

Nas superfícies de marca o poste é a placa da casa, o mesmo papel do poste na porta da barbearia: faixa listrada na base do painel da tela de entrada e poste lateral fixo da página pública, que gira com a rolagem. Fora dessas duas superfícies não há listra decorativa.

### Quadro do dia
Barbeiros em colunas, horas em linhas; a altura de cada bloco é a duração real do serviço (`--minute` 1.6px). Cabeçalho e régua de horas fixos; faixa fora do expediente em hachura marfim muito leve. No celular, um barbeiro por vez com seletor, sem rolagem interna.

### Comanda e carimbo
A comanda do próximo horário tem canhoto marinho com filete interno, hora em League Gothic grande e picote de furos até o corpo branco, onde os fatos ficam entre linhas tracejadas. Ao concluir uma reserva, um carimbo circular vermelho em SVG ("Horário reservado"), girado -8°, entra com um único movimento.

### Feedback
Toast marinho com letra marfim e `--shadow-overlay`, no canto inferior direito (acima da barra inferior no celular). Modal branco em `--radius-xl`; no celular vira folha inferior com alça. Estados vazios centralizados com ilustração em traço de gravura (navalha ou tesoura) ou ícone em círculo `--marinho-50`.

### Marca
Logo: a navalha aberta formando o B (lâmina como haste, pino e cabo no pé) + BARBERPRO, nas variações horizontal, emblema, símbolo e favicon, fundo claro, fundo escuro e mono, em `assets/brand/`. Use a versão certa para o fundo; nunca recolorir fora da paleta, distorcer ou acrescentar data de fundação.

## Do's and Don'ts

### Do:
- **Do** usar `--marinho-900` como estrutura e ação principal, e `--marfim` como fundo de página com superfícies `--branco` por cima.
- **Do** separar vermelho e marinho com branco sempre que se encontrarem.
- **Do** reservar `--vermelho-600` para "agora, atenção, ação": hora atual, pendências, dia de hoje, passo atual, destruição confirmada.
- **Do** escrever títulos em League Gothic 400 em caixa-alta e todo o resto em Public Sans.
- **Do** usar algarismos tabulares em todo horário e valor.
- **Do** distinguir status pela forma, nunca só pela cor: no quadro do dia, agendado tracejado, confirmado marinho cheio, realizado marfim recuado com visto, cancelado hachurado e riscado; nos selos em pílula, rótulo com marcador (anel, ponto, visto, xis).
- **Do** usar `--listras-poste` só para "aberta/agora" (indicador de aberta, linha do agora, loader) e, nas superfícies de marca, como a placa da casa (faixa da tela de entrada, poste lateral da página pública).
- **Do** parar toda animação do poste com `prefers-reduced-motion`.

### Don't:
- **Don't** usar cards iguais repetidos, blocos de KPI genéricos ou roxo de tecnologia.
- **Don't** usar caricatura vintage: bigodes, "EST. 19XX", desgaste falso, grão.
- **Don't** pôr faixas laterais coloridas em cards ou linhas; status vem de preenchimento e forma.
- **Don't** usar o filete duplo fora das placas marinho, dos selos, da comanda e da tabela de preços.
- **Don't** comunicar status só por cor.
- **Don't** usar League Gothic em texto corrido, botões ou rótulos.
- **Don't** usar o vermelho como cor de destaque decorativa ou como ação principal da área autenticada.
- **Don't** usar os aliases de compatibilidade (`--ink-*`, `--stone-*`, `--copper*`, `--danger*`) em código novo.
