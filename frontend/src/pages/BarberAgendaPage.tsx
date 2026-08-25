import { useState } from 'react'
import { appointmentApi, listAllAppointments } from '../api/endpoints'
import { AppointmentCard } from '../components/AppointmentCard'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { AppointmentStatus } from '../types'
import { errorMessage, todayISO } from '../utils/format'
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
  const appointments = (data ?? []).filter((appointment) => dateKey(appointment.data_hora) === todayISO())
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

  if (isLoading) return <PageLoader label="Carregando sua agenda..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar a agenda de hoje.</p>

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}><div><p className={styles.eyebrow}>{new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(new Date())}</p><h1>Agenda de hoje</h1></div><p>{appointments.length} atendimento(s) hoje</p></header>
      {appointments.length === 0 ? <EmptyState title="Agenda livre hoje" description="Quando houver atendimentos atribuídos a você, eles aparecerão aqui." /> : (
        <section className={styles.appointmentList}>
          {appointments.map((appointment) => <AppointmentCard key={appointment.id} appointment={appointment} showClient onStatusChange={(status) => void updateStatus(appointment.id, status)} isUpdating={updatingId === appointment.id} />)}
        </section>
      )}
    </div>
  )
}
