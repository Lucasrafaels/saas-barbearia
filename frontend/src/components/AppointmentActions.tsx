import { useState } from 'react'
import { appointmentApi } from '../api/endpoints'
import { useConfirm } from '../contexts/ConfirmContext'
import { useToast } from '../contexts/ToastContext'
import type { Appointment, AppointmentStatus } from '../types'
import { errorMessage, formatClock, formatDayLong, dateKey } from '../utils/format'
import { notifyAppointmentsChanged, statusTransitions, transitionActionLabel, transitionSuccessMessage } from '../utils/status'
import { CheckIcon, XIcon } from './Icons'
import { ButtonSpinner } from './Controls'
import ui from '../styles/ui.module.css'

interface AppointmentActionsProps {
  appointment: Appointment
  onUpdated: (updated: Appointment) => void
  /** Rótulo curto para listas densas. */
  size?: 'sm' | 'md'
}

/**
 * Ações de status do agendamento. Mostra somente as transições aceitas pelo
 * backend (agendado → confirmado/cancelado, confirmado → realizado/cancelado)
 * e pede confirmação antes de cancelar.
 */
export function AppointmentActions({ appointment, onUpdated, size = 'sm' }: AppointmentActionsProps) {
  const { showToast } = useToast()
  const confirm = useConfirm()
  const [pending, setPending] = useState<AppointmentStatus | null>(null)
  const transitions = statusTransitions[appointment.status]

  if (!transitions.length) return null

  const run = async (status: AppointmentStatus) => {
    if (status === 'cancelado') {
      const ok = await confirm({
        title: 'Cancelar este agendamento?',
        description: `${appointment.servico_nome} de ${appointment.cliente_nome}, ${formatDayLong(dateKey(appointment.data_hora))} às ${formatClock(appointment.data_hora)}. O horário volta a ficar livre na agenda.`,
        confirmLabel: 'Cancelar agendamento',
        cancelLabel: 'Manter',
        tone: 'danger',
      })
      if (!ok) return
    }
    setPending(status)
    try {
      const { data } = await appointmentApi.update(appointment.id, { status })
      onUpdated(data)
      notifyAppointmentsChanged()
      showToast(transitionSuccessMessage[status], 'success')
    } catch (error) {
      showToast(errorMessage(error, 'Não foi possível atualizar o agendamento.'), 'error')
    } finally {
      setPending(null)
    }
  }

  const sizeClass = size === 'sm' ? ui.sm : ''

  return (
    <div className={ui.cellActions}>
      {transitions.filter((status) => status !== 'cancelado').map((status) => (
        <button
          key={status}
          type="button"
          className={`${ui.secondaryButton} ${sizeClass}`}
          disabled={pending !== null}
          onClick={() => void run(status)}
        >
          {pending === status ? <ButtonSpinner /> : <CheckIcon size={16} />}
          {transitionActionLabel[status]}
        </button>
      ))}
      {transitions.includes('cancelado') && (
        <button
          type="button"
          className={`${ui.ghostButton} ${sizeClass}`}
          disabled={pending !== null}
          onClick={() => void run('cancelado')}
          aria-label={`Cancelar agendamento de ${appointment.cliente_nome}`}
        >
          {pending === 'cancelado' ? <ButtonSpinner /> : <XIcon size={16} />}
          Cancelar
        </button>
      )}
    </div>
  )
}
