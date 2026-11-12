import type { AppointmentStatus } from '../types'

/**
 * Máquina de estados do agendamento — espelha Appointment._validar_transicao_status
 * no backend. A interface só oferece transições que o servidor aceita.
 */
export const statusTransitions: Record<AppointmentStatus, AppointmentStatus[]> = {
  agendado: ['confirmado', 'cancelado'],
  confirmado: ['realizado', 'cancelado'],
  realizado: [],
  cancelado: [],
}

/** Verbo do botão que leva ao status. */
export const transitionActionLabel: Record<AppointmentStatus, string> = {
  agendado: 'Reabrir',
  confirmado: 'Confirmar',
  realizado: 'Marcar realizado',
  cancelado: 'Cancelar',
}

/** Mensagem de sucesso após a transição (mesmo vocabulário do botão). */
export const transitionSuccessMessage: Record<AppointmentStatus, string> = {
  agendado: 'Agendamento reaberto.',
  confirmado: 'Agendamento confirmado.',
  realizado: 'Atendimento marcado como realizado.',
  cancelado: 'Agendamento cancelado.',
}

export const statusOrder: AppointmentStatus[] = ['agendado', 'confirmado', 'realizado', 'cancelado']

export function isOpenStatus(status: AppointmentStatus): boolean {
  return status === 'agendado' || status === 'confirmado'
}

/** Evento global para avisar a interface que agendamentos mudaram. */
export const APPOINTMENTS_CHANGED = 'appointments:changed'

export function notifyAppointmentsChanged(): void {
  window.dispatchEvent(new Event(APPOINTMENTS_CHANGED))
}
