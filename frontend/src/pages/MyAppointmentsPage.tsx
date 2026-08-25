import { useState } from 'react'
import { appointmentApi } from '../api/endpoints'
import { AppointmentCard } from '../components/AppointmentCard'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { Pagination } from '../components/Pagination'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import { errorMessage } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

export function MyAppointmentsPage() {
  const [page, setPage] = useState(1)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const { showToast } = useToast()
  const { data, isLoading, error, reload } = useAsyncData(() => appointmentApi.list({ page }).then((response) => response.data), [page])

  const cancel = async (id: number) => {
    if (!window.confirm('Deseja cancelar este agendamento?')) return
    try {
      setUpdatingId(id)
      await appointmentApi.update(id, { status: 'cancelado' })
      await reload()
      showToast('Agendamento cancelado.', 'success')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível cancelar o agendamento.'), 'error')
    } finally {
      setUpdatingId(null)
    }
  }

  if (isLoading) return <PageLoader label="Buscando seus agendamentos..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar seus agendamentos.</p>
  const appointments = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}><div><p className={styles.eyebrow}>Seu histórico</p><h1>Meus agendamentos</h1></div></header>
      {appointments.length === 0 ? <EmptyState title="Sem agendamentos por enquanto" description="Quando você reservar um horário, ele aparecerá aqui." action={{ to: '/appointments/new', label: 'Agendar agora' }} /> : (
        <section className={styles.appointmentList}>
          {appointments.map((appointment) => (
            <AppointmentCard
              key={appointment.id}
              appointment={appointment}
              actions={appointment.status !== 'cancelado' && appointment.status !== 'realizado' ? (
                <button className={ui.dangerButton} disabled={updatingId === appointment.id} onClick={() => void cancel(appointment.id)}>
                  {updatingId === appointment.id ? 'Cancelando...' : 'Cancelar'}
                </button>
              ) : null}
            />
          ))}
        </section>
      )}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}
