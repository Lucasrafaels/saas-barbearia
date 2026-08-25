import { useState } from 'react'
import { appointmentApi } from '../api/endpoints'
import { AppointmentCard } from '../components/AppointmentCard'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { Pagination } from '../components/Pagination'
import { useAsyncData } from '../hooks/useAsyncData'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

export function AdminAppointmentsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error } = useAsyncData(() => appointmentApi.list({ page }).then((response) => response.data), [page])
  if (isLoading) return <PageLoader label="Carregando agendamentos..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar os agendamentos.</p>
  const appointments = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}><div><p className={styles.eyebrow}>Visão da barbearia</p><h1>Todos os agendamentos</h1></div><p>{data?.count ?? 0} no total</p></header>
      {appointments.length === 0 ? <EmptyState title="Nenhum agendamento registrado" description="Os horários marcados pelos clientes aparecerão aqui." /> : <section className={styles.appointmentList}>{appointments.map((appointment) => <AppointmentCard key={appointment.id} appointment={appointment} showClient />)}</section>}
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}
