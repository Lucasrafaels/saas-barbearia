/**
 * Kit de identidade do BarberPro.
 *
 * Cada import devolve a URL do arquivo, processada pelo Vite: pronta para
 * `<img src>`, `background-image` ou `<link rel="icon">`. Arquivos pequenos
 * podem ser embutidos como data URI no build, sem mudar o uso.
 *
 * Exemplo:
 *   import { logo } from '../assets/brand'
 *   <img src={logo.horizontal.fundoClaro} alt="BarberPro" height={32} />
 *
 * Guia completo (cores, área de proteção, tamanhos mínimos): ./README.md
 */
import emblemaFundoClaro from './logo/barberpro-emblema-fundo-claro.svg'
import emblemaFundoEscuro from './logo/barberpro-emblema-fundo-escuro.svg'
import emblemaMono from './logo/barberpro-emblema-mono.svg'
import favicon from './logo/barberpro-favicon.svg'
import horizontalFundoClaro from './logo/barberpro-horizontal-fundo-claro.svg'
import horizontalFundoEscuro from './logo/barberpro-horizontal-fundo-escuro.svg'
import horizontalMono from './logo/barberpro-horizontal-mono.svg'
import simboloFundoClaro from './logo/barberpro-simbolo-fundo-claro.svg'
import simboloFundoEscuro from './logo/barberpro-simbolo-fundo-escuro.svg'
import simboloMono from './logo/barberpro-simbolo-mono.svg'
import navalha from './ilustracoes/navalha.svg'
import tesoura from './ilustracoes/tesoura.svg'

export const logo = {
  /** Só o símbolo (navalha aberta formando o B). */
  simbolo: { fundoClaro: simboloFundoClaro, fundoEscuro: simboloFundoEscuro, mono: simboloMono },
  /** Símbolo + BARBERPRO: a assinatura principal. */
  horizontal: { fundoClaro: horizontalFundoClaro, fundoEscuro: horizontalFundoEscuro, mono: horizontalMono },
  /** Selo circular para carimbos, materiais impressos e momentos de marca. */
  emblema: { fundoClaro: emblemaFundoClaro, fundoEscuro: emblemaFundoEscuro, mono: emblemaMono },
  /** Ícone simplificado na placa marinho, desenhado na grade de 32 px. */
  favicon,
} as const

/** Ilustrações em traço de gravura. Sem cor fixa no traço: marinho por padrão. */
export const ilustracoes = { navalha, tesoura } as const
