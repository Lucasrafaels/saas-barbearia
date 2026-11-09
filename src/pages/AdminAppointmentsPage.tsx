import { useState } from 'react'
import { appointmentApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { Pagination } from '../components/Pagination'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { AppointmentStatus } from '../types'
import { errorMessage, formatDateTime, statusLabels } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

export function AdminAppointmentsPage() {
  const { showToast } = useToast()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  const { data, isLoading, error, reload } = useAsyncData(
    () => appointmentApi.list({ page, ...(statusFilter === 'all' ? {} : { status: statusFilter }) }).then((response) => response.data),
    [page, statusFilter]
  )

  const updateStatus = async (id: number, status: AppointmentStatus) => {
    try {
      setUpdatingId(id)
      await appointmentApi.update(id, { status })
      await reload()
      showToast('Status atualizado com sucesso.', 'success')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível atualizar o status.'), 'error')
    } finally {
      setUpdatingId(null)
    }
  }

  if (isLoading) return <PageLoader label="Carregando agendamentos..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar os agendamentos.</p>
  const appointments = data?.results ?? []

  const statusOptions: { value: string; label: string }[] = [
    { value: 'all', label: 'Todos' },
    { value: 'agendado', label: 'Agendado' },
    { value: 'confirmado', label: 'Confirmado' },
    { value: 'realizado', label: 'Realizado' },
    { value: 'cancelado', label: 'Cancelado' },
  ]

  const renderStatusOptions = (currentStatus: AppointmentStatus, isUpdating: boolean) =>
    statusOptions
      .filter(opt => opt.value !== 'all')
      .map(opt => {
        // Valid status transitions for admin based on backend rules
        // Admin can: agendado -> confirmado/cancelado, confirmado -> realizado/cancelado
        // realizado and cancelado are terminal states (admin cannot revert)
        const validTransitions: Record<AppointmentStatus, AppointmentStatus[]> = {
          agendado: ['confirmado', 'cancelado'],
          confirmado: ['realizado', 'cancelado'],
          realizado: [],
          cancelado: [],
        }
        const canTransition = validTransitions[currentStatus]?.includes(opt.value as AppointmentStatus) ?? false
        const isCurrentStatus = opt.value === currentStatus
        return (
          <option
            key={opt.value}
            value={opt.value}
            disabled={isUpdating && !isCurrentStatus || !canTransition && !isCurrentStatus}
          >
            {opt.label}
          </option>
        )
      })

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Visão da barbearia</p>
          <h1>Todos os agendamentos</h1>
        </div>
        <p>{data?.count ?? 0} no total</p>
      </header>

      <div className={ui.dataTable}>
        <div className={ui.filterBar}>
          <div className={ui.filterGroup}>
            <label htmlFor="status-filter">Status</label>
            <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {statusOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
            </select>
          </div>
        </div>

        {appointments.length === 0 ? (
          <EmptyState title="Nenhum agendamento encontrado" description={statusFilter !== 'all' ? 'Tente alterar o filtro de status.' : 'Os horários marcados pelos clientes aparecerão aqui.'} />
        ) : (
          <>
            <div className={ui.tableContainer}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Data e Hora</th>
                    <th>Cliente</th>
                    <th>Serviço</th>
                    <th>Barbeiro</th>
                    <th>Status</th>
                    <th style={{ width: '100px' }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.map((appointment) => (
                    <tr key={appointment.id}>
                      <td>{formatDateTime(appointment.data_hora)}</td>
                      <td>{appointment.cliente_nome}</td>
                      <td>
                        <strong>{appointment.servico_nome}</strong>
                        <p className={ui.cellMuted}>{formatDateTime(appointment.data_hora).split(', ')[1] || ''} · {appointment.servico_duracao} min</p>
                      </td>
                      <td>{appointment.barbeiro_nome}</td>
                      <td>
                        <span className={`ui.badge badgeDefault`}>{statusLabels[appointment.status]}</span>
                      </td>
                      <td>
                        <div className={ui.actionButtons}>
                          <div className={ui.statusSelect}>
                            <select
                              value={appointment.status}
                              onChange={(e) => updateStatus(appointment.id, e.target.value as AppointmentStatus)}
                              disabled={updatingId === appointment.id}
                            >
                              {renderStatusOptions(appointment.status, updatingId === appointment.id)}
                            </select>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {data && <Pagination page={page} count={data.count} onChange={setPage} />}
          </>
        )}
      </div>
    </div>
  )
}