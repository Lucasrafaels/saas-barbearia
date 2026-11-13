# Identidade BarberPro

Direção "Esmalte & Navalha": a barbearia americana dos anos 30 e 40, com acabamento de produto digital. O símbolo é uma **navalha aberta formando o B**. A lâmina é a haste, com a ponta arredondada no alto e o bisel no fio. No pé ficam o pino e o cabo aberto, que desce como uma cauda.

Todos os arquivos são vetoriais (SVG). As letras estão convertidas em curvas, então nenhum arquivo depende de fonte instalada nem de recurso externo.

## Arquivos

| Arquivo | Uso |
|---|---|
| `logo/barberpro-horizontal-fundo-claro.svg` | Assinatura principal sobre branco ou marfim (cabeçalhos, documentos) |
| `logo/barberpro-horizontal-fundo-escuro.svg` | Assinatura sobre marinho (menu lateral, rodapé, capa) |
| `logo/barberpro-horizontal-mono.svg` | Uma cor só (preto por padrão; recolore por CSS quando embutido) |
| `logo/barberpro-simbolo-fundo-claro.svg` | Símbolo isolado sobre fundo claro (avatar, espaços estreitos) |
| `logo/barberpro-simbolo-fundo-escuro.svg` | Símbolo isolado sobre marinho |
| `logo/barberpro-simbolo-mono.svg` | Símbolo em uma cor |
| `logo/barberpro-emblema-fundo-claro.svg` | Selo circular sobre fundo claro (carimbos, impressos, momentos de marca) |
| `logo/barberpro-emblema-fundo-escuro.svg` | Selo circular sobre marinho |
| `logo/barberpro-emblema-mono.svg` | Selo em uma cor (carimbo, gravação, impressão de uma cor) |
| `logo/barberpro-favicon.svg` | Favicon e ícone de app: símbolo simplificado na placa marinho, desenhado para 16 e 32 px |
| `ilustracoes/navalha.svg` | Ilustração em traço de gravura: navalha aberta |
| `ilustracoes/tesoura.svg` | Ilustração em traço de gravura: tesoura de barbeiro |

## Como usar no frontend

```tsx
import { logo, ilustracoes } from '../assets/brand'

<img src={logo.horizontal.fundoClaro} alt="BarberPro" height={32} />
<img src={ilustracoes.navalha} alt="" aria-hidden="true" />
```

- **Texto alternativo:** use `alt="BarberPro"` quando o logo for a única identificação da marca; quando houver o nome em texto ao lado, use `alt=""`. Ilustrações decorativas levam `alt=""`.
- **Recoloração:** as versões mono e as ilustrações usam `currentColor`, então recebem a cor do texto quando o SVG é embutido no HTML. Como `<img>`, ficam pretas (logo mono) ou marinho (ilustrações).
- **Favicon:** `index.html` ainda aponta para o favicon antigo (`public/favicon.svg`). A troca, junto com `theme-color`, acontece na etapa de fundações do redesign.

## Cores

| Papel | Cor |
|---|---|
| Marinho (símbolo, letras) | `#102143` |
| Vermelho poste (anel do emblema) | `#C12D2E` |
| Marfim (versões para fundo escuro, centro do emblema) | `#F8F4EB` |
| Branco (separação entre vermelho e marinho) | `#FFFFFF` |

O vermelho **nunca encosta** no marinho, porque o contraste entre os dois é de apenas 2,8:1. No emblema, há sempre um anel branco entre eles. Marinho sobre marfim tem contraste de 14,5:1.

## Tipografia

- **Assinatura e emblema:** League Gothic, revival da Alternate Gothic No. 1 (Morris Fuller Benton, 1903). Licença SIL Open Font License 1.1, The League of Moveable Type.
- **Texto pequeno do emblema:** Public Sans Bold, que descende da Franklin Gothic. Licença SIL Open Font License 1.1, USWDS.
- As letras foram convertidas em contornos. A licença OFL permite usar as fontes em logotipos.

## Área de proteção e tamanhos mínimos

- **Área de proteção:** deixe livre em volta do logo, no mínimo, ¼ da altura do símbolo.
- **Tamanhos mínimos:**
  - Símbolo: 20 px de altura. Abaixo disso, use o favicon.
  - Horizontal: 24 px de altura (cerca de 115 px de largura).
  - Emblema: 96 px de diâmetro; abaixo disso, o texto circular deixa de ser legível.
  - Favicon: desenhado para 16 e 32 px.

## O que não fazer

- Distorcer, inclinar, girar ou mudar as proporções.
- Recolorir fora da paleta, aplicar degradê, sombra, chanfro ou contorno.
- Pôr o vermelho encostado no marinho.
- Usar a versão de fundo claro sobre fundo escuro, ou o contrário.
- Separar o cabo da lâmina ou remover o pino: eles fazem parte do símbolo.
- Acrescentar ao emblema data de fundação ou qualquer informação que não seja verdadeira.
