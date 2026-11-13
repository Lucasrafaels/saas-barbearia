import { logo } from '../assets/brand'

type Fundo = 'claro' | 'escuro'

/** Ícone da marca: o símbolo simplificado na placa marinho (o mesmo do favicon). */
export function BrandMark({ size = 32 }: { size?: number }) {
  return <img src={logo.favicon} width={size} height={size} alt="" aria-hidden="true" draggable={false} />
}

/**
 * Assinatura principal: navalha aberta formando o B + BARBERPRO.
 * `height` é a altura total da arte; a largura acompanha a proporção do arquivo.
 */
export function BrandLogo({ fundo = 'claro', height = 28, label = 'BarberPro' }: { fundo?: Fundo; height?: number; label?: string }) {
  const src = fundo === 'escuro' ? logo.horizontal.fundoEscuro : logo.horizontal.fundoClaro
  return <img src={src} height={height} style={{ height, width: 'auto' }} alt={label} draggable={false} />
}

/** Selo circular, para momentos de marca (login, confirmação de reserva). */
export function BrandEmblem({ fundo = 'claro', size = 120 }: { fundo?: Fundo; size?: number }) {
  const src = fundo === 'escuro' ? logo.emblema.fundoEscuro : logo.emblema.fundoClaro
  return <img src={src} width={size} height={size} alt="" aria-hidden="true" draggable={false} />
}
