import axios from 'axios'
import type { AppointmentStatus } from '../types'

export const statusLabels: Record<AppointmentStatus, string> = {
  agendado: 'Agendado',
  confirmado: 'Confirmado',
  realizado: 'Realizado',
  cancelado: 'Cancelado',
}

export function formatCurrency(value: string | number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(Number(value))
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatTime(value: string): string {
  return value.slice(0, 5)
}

export function todayISO(): string {
  const now = new Date()
  const timezoneOffset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - timezoneOffset).toISOString().slice(0, 10)
}

export function isPast(dateStr: string): boolean {
  const today = todayISO()
  return dateStr < today
}

export function errorMessage(error: unknown, fallback = 'Não foi possível concluir a operação.'): string {
  if (!axios.isAxiosError(error)) return fallback
  const data = error.response?.data
  if (!data) return 'Não foi possível conectar à API. Verifique se o backend está em execução.'
  if (typeof data.detail === 'string') return data.detail

  const messages = Object.values(data)
    .flatMap((value) => (Array.isArray(value) ? value : [value]))
    .filter((value): value is string => typeof value === 'string')

  return messages[0] ?? fallback
}
