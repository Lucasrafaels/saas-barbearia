import type { Barbershop } from '../types'
import { formatTime, nowMinutes, timeToMinutes } from './format'

export interface ShopHoursStatus {
  open: boolean
  label: string
}

/**
 * Situação atual da barbearia a partir do horário de funcionamento cadastrado.
 * O backend não modela dias fechados; o mesmo horário vale para todos os dias.
 */
export function shopHoursStatus(shop: Pick<Barbershop, 'horario_abertura' | 'horario_fechamento'>, minutes = nowMinutes()): ShopHoursStatus {
  const opens = timeToMinutes(shop.horario_abertura)
  const closes = timeToMinutes(shop.horario_fechamento)
  const open = minutes >= opens && minutes < closes
  if (open) return { open, label: `Aberta até ${formatTime(shop.horario_fechamento)}` }
  return { open, label: `Fechada, abre às ${formatTime(shop.horario_abertura)}` }
}
