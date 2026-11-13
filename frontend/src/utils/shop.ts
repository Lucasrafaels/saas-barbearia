import type { Barbershop } from '../types'
import { addDays, formatTime, isoWeekday, nowMinutes, timeToMinutes, todayISO } from './format'

export interface ShopHoursStatus {
  open: boolean
  label: string
}

/** Dias da semana no padrão da API (ISO: 1 = segunda … 7 = domingo). */
export const WEEKDAYS = [
  { iso: 1, short: 'Seg', name: 'segunda' },
  { iso: 2, short: 'Ter', name: 'terça' },
  { iso: 3, short: 'Qua', name: 'quarta' },
  { iso: 4, short: 'Qui', name: 'quinta' },
  { iso: 5, short: 'Sex', name: 'sexta' },
  { iso: 6, short: 'Sáb', name: 'sábado' },
  { iso: 7, short: 'Dom', name: 'domingo' },
] as const

const ALL_DAYS = WEEKDAYS.map((day) => day.iso)

type ShopDays = Partial<Pick<Barbershop, 'dias_funcionamento'>>

/** Dias em que a barbearia atende. Sem a informação, vale o padrão da API: todos os dias. */
export function openDays(shop: ShopDays): number[] {
  return shop.dias_funcionamento?.length ? shop.dias_funcionamento : ALL_DAYS
}

/** Verdadeiro se a barbearia atende no dia (chave YYYY-MM-DD). */
export function isOpenOn(shop: ShopDays, key: string): boolean {
  return openDays(shop).includes(isoWeekday(key))
}

/** "Todos os dias", "Segunda a sábado" ou "Segunda, quarta e sexta". */
export function formatOpenDays(days: number[]): string {
  const sorted = [...new Set(days)].sort((a, b) => a - b)
  if (sorted.length === 0 || sorted.length === 7) return 'Todos os dias'
  const name = (iso: number) => WEEKDAYS.find((day) => day.iso === iso)?.name ?? ''
  const contiguous = sorted.every((iso, index) => index === 0 || iso === sorted[index - 1] + 1)
  const text = contiguous && sorted.length >= 3
    ? `${name(sorted[0])} a ${name(sorted[sorted.length - 1])}`
    : sorted.length === 1
      ? name(sorted[0])
      : `${sorted.slice(0, -1).map(name).join(', ')} e ${name(sorted[sorted.length - 1])}`
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/**
 * Situação atual da barbearia a partir de dados que já existem no produto:
 * o campo `ativo`, os dias de funcionamento e o horário de abertura e
 * fechamento (o mesmo para todos os dias em que ela abre). É a mesma regra
 * que o calendário de agendamento e a API usam, para os três nunca se
 * contradizerem (FE-14).
 *
 * - Desativada: a API recusa agendar, remarcar, confirmar e concluir.
 * - Aberta: hoje é dia de funcionamento e o horário está entre a abertura e o fechamento.
 * - Fechada: informa quando abre — hoje mais tarde, amanhã ou no próximo dia
 *   de funcionamento (pulando os dias em que ela não abre).
 */
export function shopHoursStatus(
  shop: Pick<Barbershop, 'horario_abertura' | 'horario_fechamento'> & ShopDays & Partial<Pick<Barbershop, 'ativo'>>,
  minutes = nowMinutes(),
  today = todayISO(),
): ShopHoursStatus {
  if (shop.ativo === false) return { open: false, label: 'Barbearia desativada' }
  const opens = timeToMinutes(shop.horario_abertura)
  const closes = timeToMinutes(shop.horario_fechamento)
  const opensAt = formatTime(shop.horario_abertura)
  const openToday = isOpenOn(shop, today)
  if (openToday && minutes >= opens && minutes < closes) {
    return { open: true, label: `Aberta até ${formatTime(shop.horario_fechamento)}` }
  }
  if (openToday && minutes < opens) return { open: false, label: `Fechada, abre às ${opensAt}` }
  // Já fechou hoje, ou hoje não é dia de funcionamento: o próximo dia em que ela abre
  for (let offset = 1; offset <= 7; offset++) {
    const key = addDays(today, offset)
    if (isOpenOn(shop, key)) {
      const when = offset === 1 ? 'amanhã' : WEEKDAYS[isoWeekday(key) - 1].name
      return { open: false, label: `Fechada, abre ${when} às ${opensAt}` }
    }
  }
  return { open: false, label: 'Fechada' }
}
