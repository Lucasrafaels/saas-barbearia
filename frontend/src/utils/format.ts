import axios from 'axios'
import type { AppointmentStatus } from '../types'

/**
 * Fuso da barbearia. O backend usa TIME_ZONE = America/Sao_Paulo para validar
 * horário de funcionamento e gerar slots; o frontend exibe tudo nesse fuso
 * para que a agenda mostrada seja a mesma que o servidor valida.
 */
export const SHOP_TZ = 'America/Sao_Paulo'

export const statusLabels: Record<AppointmentStatus, string> = {
  agendado: 'Agendado',
  confirmado: 'Confirmado',
  realizado: 'Realizado',
  cancelado: 'Cancelado',
}

const currencyFormatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function formatCurrency(value: string | number | null | undefined): string {
  return currencyFormatter.format(Number(value ?? 0))
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: SHOP_TZ }).format(new Date(value))
}

/** "09:00:00" → "09:00" (campos TimeField da API). */
export function formatTime(value: string | null | undefined): string {
  return value ? value.slice(0, 5) : ''
}

/** Hora (HH:MM) de um datetime ISO, no fuso da barbearia. */
export function formatClock(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: SHOP_TZ }).format(new Date(iso))
}

const dateKeyFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: SHOP_TZ, year: 'numeric', month: '2-digit', day: '2-digit' })

/** Chave de dia (YYYY-MM-DD) de um instante, no fuso da barbearia. */
export function dateKey(value: string | Date): string {
  return dateKeyFormatter.format(typeof value === 'string' ? new Date(value) : value)
}

/** Dia de hoje (YYYY-MM-DD) no fuso da barbearia. */
export function todayISO(): string {
  return dateKey(new Date())
}

/** Soma dias a uma chave YYYY-MM-DD sem depender do fuso do navegador. */
export function addDays(key: string, amount: number): string {
  const [y, m, d] = key.split('-').map(Number)
  const date = new Date(Date.UTC(y, m - 1, d + amount, 12))
  return date.toISOString().slice(0, 10)
}

function keyToUTCNoon(key: string): Date {
  const [y, m, d] = key.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d, 12))
}

/** Dia da semana ISO (1 = segunda … 7 = domingo) de uma chave YYYY-MM-DD, sem depender do fuso do navegador. */
export function isoWeekday(key: string): number {
  const day = keyToUTCNoon(key).getUTCDay()
  return day === 0 ? 7 : day
}

/** "quarta-feira, 11 de novembro" a partir de uma chave YYYY-MM-DD. */
export function formatDayLong(key: string, withYear = false): string {
  return new Intl.DateTimeFormat('pt-BR', {
    weekday: 'long', day: 'numeric', month: 'long', ...(withYear ? { year: 'numeric' } : {}), timeZone: 'UTC',
  }).format(keyToUTCNoon(key))
}

/** "qua., 11 nov." */
export function formatDayShort(key: string): string {
  return new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' }).format(keyToUTCNoon(key))
}

/** "sex 20/11": cabe em colunas estreitas de horário. */
export function formatDayCompact(key: string): string {
  return `${weekdayShort(key)} ${key.slice(8, 10)}/${key.slice(5, 7)}`
}

export function weekdayShort(key: string): string {
  return new Intl.DateTimeFormat('pt-BR', { weekday: 'short', timeZone: 'UTC' }).format(keyToUTCNoon(key)).replace('.', '')
}

export function dayOfMonth(key: string): number {
  return Number(key.slice(8, 10))
}

export function monthShort(key: string): string {
  return new Intl.DateTimeFormat('pt-BR', { month: 'short', timeZone: 'UTC' }).format(keyToUTCNoon(key)).replace('.', '')
}

/** Rótulo relativo para chaves de dia: "Hoje", "Amanhã", "Ontem" ou a data. */
export function relativeDayLabel(key: string): string {
  const today = todayISO()
  if (key === today) return 'Hoje'
  if (key === addDays(today, 1)) return 'Amanhã'
  if (key === addDays(today, -1)) return 'Ontem'
  return capitalize(formatDayLong(key))
}

/**
 * Rótulo acessível de um dia do calendário de agendamento (FE-21). A data
 * aparece uma única vez: "Hoje, sexta-feira, 13 de novembro", "Amanhã,
 * sábado, 14 de novembro" ou "Domingo, 15 de novembro". Dia em que a
 * barbearia não abre termina com ", barbearia fechada".
 */
export function dateChipLabel(key: string, options: { closed?: boolean; today?: string } = {}): string {
  const { closed = false, today = todayISO() } = options
  const date = formatDayLong(key)
  const relative = key === today ? 'Hoje' : key === addDays(today, 1) ? 'Amanhã' : null
  const label = relative ? `${relative}, ${date}` : capitalize(date)
  return closed ? `${label}, barbearia fechada` : label
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Minutos desde 00:00 de um datetime ISO, no fuso da barbearia. */
export function minutesOfDay(iso: string): number {
  const [h, m] = formatClock(iso).split(':').map(Number)
  return h * 60 + m
}

/** "09:30:00" → 570 */
export function timeToMinutes(value: string): number {
  const [h, m] = value.split(':').map(Number)
  return h * 60 + (m || 0)
}

export function minutesToClock(total: number): string {
  const h = Math.floor(total / 60)
  const m = total % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

/** Horário atual em minutos do dia, no fuso da barbearia. */
export function nowMinutes(): number {
  return minutesOfDay(new Date().toISOString())
}

export function isBeforeNow(iso: string): boolean {
  return new Date(iso).getTime() < Date.now()
}

/** Compatibilidade: verdadeiro se a data (ou datetime) é anterior a hoje. */
export function isPast(value: string): boolean {
  return value.slice(0, 10) < todayISO()
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} h ${m} min` : `${h} h`
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '?'
  const first = parts[0][0] ?? ''
  const last = parts.length > 1 ? parts[parts.length - 1][0] ?? '' : ''
  return (first + last).toUpperCase()
}

export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name
}

/** Normaliza texto para busca: minúsculas e sem acentos. */
export function normalize(text: string | null | undefined): string {
  return (text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

export function matchesSearch(query: string, ...fields: (string | null | undefined)[]): boolean {
  const q = normalize(query)
  if (!q) return true
  return fields.some((field) => normalize(field).includes(q))
}

export function plural(count: number, singular: string, pluralForm = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : pluralForm}`
}

/** Aceita "50", "50,5", "1.250,00" ou "50.00" e devolve o decimal da API ("50.00"). */
export function parseMoneyInput(value: string): string | null {
  const cleaned = value.trim().replace(/\s|R\$/g, '')
  if (!cleaned) return null
  const normalized = cleaned.includes(',') ? cleaned.replace(/\./g, '').replace(',', '.') : cleaned
  const number = Number(normalized)
  if (!Number.isFinite(number) || number < 0) return null
  return number.toFixed(2)
}

/** "50.00" → "50,00" para exibir em campos editáveis. */
export function moneyToInput(value: string | number): string {
  return Number(value).toFixed(2).replace('.', ',')
}

const FIELD_LABELS: Record<string, string> = {
  email: 'E-mail',
  nome: 'Nome',
  password: 'Senha',
  new_password: 'Nova senha',
  old_password: 'Senha atual',
  especialidade: 'Especialidade',
  data_hora: 'Horário',
  barbeiro: 'Barbeiro',
  servico: 'Serviço',
  cliente: 'Cliente',
  preco: 'Preço',
  duracao: 'Duração',
  telefone: 'Telefone',
  endereco: 'Endereço',
  token: 'Código',
  uid: 'Identificador',
}

function firstMessage(value: unknown): string | null {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstMessage(item)
      if (message) return message
    }
  }
  if (value && typeof value === 'object') {
    for (const item of Object.values(value)) {
      const message = firstMessage(item)
      if (message) return message
    }
  }
  return null
}

/** Mensagem legível a partir de um erro da API (DRF), sem expor detalhes técnicos. */
export function errorMessage(error: unknown, fallback = 'Não foi possível concluir a operação.'): string {
  if (!axios.isAxiosError(error)) return fallback
  if (!error.response) {
    return 'Sem conexão com o servidor. Verifique sua internet ou se a API está em execução e tente novamente.'
  }
  const { status, data } = error.response
  if (status === 429) return 'Muitas tentativas em pouco tempo. Aguarde um instante e tente novamente.'
  if (status >= 500) return 'O servidor encontrou um erro. Tente novamente em alguns instantes.'
  if (status === 403 && !data) return 'Você não tem permissão para esta ação.'
  if (!data || typeof data !== 'object') return fallback
  const record = data as Record<string, unknown>
  if (typeof record.detail === 'string') return record.detail

  for (const [field, value] of Object.entries(record)) {
    const message = firstMessage(value)
    if (!message) continue
    const label = FIELD_LABELS[field]
    if (field === 'non_field_errors' || field === 'detail' || !label) return message
    return `${label}: ${message}`
  }
  return fallback
}

/** Erros por campo vindos da API (para exibir junto ao campo correspondente). */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError(error) || !error.response?.data || typeof error.response.data !== 'object') return {}
  const result: Record<string, string> = {}
  for (const [field, value] of Object.entries(error.response.data as Record<string, unknown>)) {
    const message = firstMessage(value)
    if (message) result[field] = message
  }
  return result
}
