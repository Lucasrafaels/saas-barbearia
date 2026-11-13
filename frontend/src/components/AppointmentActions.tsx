import { useState } from 'react'
import { useNow } from '../hooks/useUi'
import { appointmentApi } from '../api/endpoints'
import { useConfirm } from '../contexts/ConfirmContext'
import { useToast } from '../contexts/ToastContext'
import type { Appointment, AppointmentStatus } from '../types'
import { errorMessage, formatClock, formatDayLong, dateKey, minutesOfDay, minutesToClock } from '../utils/format'
import { notifyAppointmentsChanged, statusTransitions, transitionActionLabel, transitionSuccessMessage } from '../utils/status'
import { CheckIcon, XIcon } from './Icons'
import { ButtonSpinner } from './Controls'
import ui from '../styles/ui.module.css'

interface AppointmentActionsProps {
  appointment: Appointment
  onUpdated: (updated: Appointment) => void
  /** Rótulo curto para listas densas. */
  size?: 'sm' | 'md'
  /** Restringe as ações exibidas (ex.: só "Confirmar" numa lista compacta). */
  only?: AppointmentStatus[]
}

/**
 * Ações de status do agendamento. Mostra somente as transições aceitas pelo
 * backend (agendado → confirmado/cancelado, confirmado → realizado/cancelado)
 * e pede confirmação antes de cancelar.
 */
export function AppointmentActions({ appointment, onUpdated, size = 'sm', only }: AppointmentActionsProps) {
  const { showToast } = useToast()
  const confirm = useConfirm()
  const [pending, setPending] = useState<AppointmentStatus | null>(null)
  const now = useNow(30_000)
  const transitions = statusTransitions[appointment.status].filter((status) => !only || only.includes(status))
  // Mesma regra do backend: "realizado" só a partir do término previsto do horário
  const endsAt = new Date(appointment.data_hora).getTime() + appointment.servico_duracao * 60_000
  const canComplete = now.getTime() >= endsAt
  const endLabel = minutesToClock(minutesOfDay(appointment.data_hora) + appointment.servico_duracao)

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
      {transitions.filter((status) => status !== 'cancelado').map((status) => {
        const early = status === 'realizado' && !canComplete
        return (
          <button
            key={status}
            type="button"
            className={`${ui.secondaryButton} ${sizeClass}`}
            disabled={pending !== null || early}
            title={early ? `O atendimento só pode ser marcado como realizado depois do término previsto, às ${endLabel}.` : undefined}
            onClick={() => void run(status)}
          >
            {pending === status ? <ButtonSpinner /> : <CheckIcon size={16} />}
            {early ? `Concluir às ${endLabel}` : transitionActionLabel[status]}
            <span className="sr-only">: {appointment.cliente_nome}, {formatClock(appointment.data_hora)}</span>
          </button>
        )
      })}
      {transitions.includes('cancelado') && (
        <button
          type="button"
          className={`${ui.ghostButton} ${ui.ghostDanger} ${sizeClass}`}
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
