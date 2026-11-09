import { useState } from 'react'
import { appointmentApi, listAllAppointments } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { StatusBadge } from '../components/StatusBadge'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { AppointmentStatus } from '../types'
import { errorMessage, todayISO, statusLabels } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

function dateKey(value: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(value))
  const get = (kind: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === kind)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')}`
}

export function BarberAgendaPage() {
  const { showToast } = useToast()
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const { data, isLoading, error, reload } = useAsyncData(listAllAppointments, [])
  const today = todayISO()
  const appointments = (data ?? []).filter((appointment) => dateKey(appointment.data_hora) === today)
    .sort((a, b) => a.data_hora.localeCompare(b.data_hora))

  const updateStatus = async (id: number, status: AppointmentStatus) => {
    try {
      setUpdatingId(id)
      await appointmentApi.update(id, { status })
      await reload()
      showToast('Status atualizado.', 'success')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível atualizar o status.'), 'error')
    } finally {
      setUpdatingId(null)
    }
  }

  // Valid status transitions for barbers based on backend rules
  // Barbers can only advance the flow: agendado -> confirmado/cancelado, confirmado -> realizado/cancelado
  // They CANNOT reopen terminal states (realizado, cancelado)
  const validTransitions: Record<AppointmentStatus, AppointmentStatus[]> = {
    agendado: ['confirmado', 'cancelado'],
    confirmado: ['realizado', 'cancelado'],
    realizado: [], // Terminal state - cannot transition further
    cancelado: [], // Terminal state - cannot transition further
  }

  if (isLoading) return <PageLoader label="Carregando sua agenda..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar a agenda.</p>

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Sua agenda</p>
          <h1>Agendamentos de hoje</h1>
        </div>
        <p>
          {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </header>

      <div className={ui.dataTable}>
        {appointments.length === 0 ? (
          <EmptyState
            title="Nenhum agendamento hoje"
            description="Aproveite o tempo livre! Nenhum horário marcado para hoje."
          />
        ) : (
          <>
            <div className={ui.tableContainer}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Horário</th>
                    <th>Cliente</th>
                    <th>Serviço</th>
                    <th>Duração</th>
                    <th>Status</th>
                    <th style={{ width: '140px' }}>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appointment) => (
                    <tr key={appointment.id}>
                      <td>
                        <time dateTime={appointment.data_hora}>
                          {new Date(appointment.data_hora).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                        </time>
                      </td>
                      <td>
                        <strong>{appointment.cliente_nome}</strong>
                      </td>
                      <td>{appointment.servico_nome}</td>
                      <td>{appointment.servico_duracao} min</td>
                      <td>
                        <StatusBadge status={appointment.status} />
                      </td>
                      <td>
                        <div className={ui.statusSelect}>
                          <select
                            value={appointment.status}
                            onChange={(e) => updateStatus(appointment.id, e.target.value as AppointmentStatus)}
                            disabled={updatingId === appointment.id}
                          >
                            {['agendado', 'confirmado', 'realizado', 'cancelado'].map((statusValue) => {
                              const isCurrent = appointment.status === statusValue
                              const canTransition = validTransitions[appointment.status]?.includes(statusValue as AppointmentStatus) ?? false
                              // Disable if currently updating this appointment (prevents double submission)
                              // OR if it's not the current status AND not a valid transition
                              const disabled = updatingId === appointment.id || (!isCurrent && !canTransition)
                              return (
                                <option
                                  key={statusValue}
                                  value={statusValue}
                                  disabled={disabled}
                                >
                                  {statusLabels[statusValue as AppointmentStatus]}
                                </option>
                              )
                            })}
                          </select>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}