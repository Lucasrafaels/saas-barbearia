import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { appointmentApi } from '../api/endpoints'
import { PageLoader } from '../components/PageLoader'
import { StatusBadge } from '../components/StatusBadge'
import { statusLabels, isPast } from '../utils/format'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage } from '../utils/format'
import { CalendarIcon } from '../components/Icons'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

type Appointment = {
  id: number
  data_hora: string
  status: 'agendado' | 'confirmado' | 'realizado' | 'cancelado'
  servico_nome: string
  servico_preco: string
  servico_duracao: number
  barbeiro_nome: string
  barbeiro_especialidade: string | null
  observacoes: string | null
}

export function MyAppointmentsPage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  useEffect(() => {
    if (!user) return
    let active = true
    setIsLoading(true)
    appointmentApi.list({ cliente: user.id })
      .then((response) => {
        if (active) setAppointments(response.data.results)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Não foi possível carregar seus agendamentos.'))
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => { active = false }
  }, [user])

  const handleCancel = async (id: number) => {
    if (!window.confirm('Tem certeza que deseja cancelar este agendamento?')) return
    setUpdatingId(id)
    try {
      await appointmentApi.update(id, { status: 'cancelado' })
      showToast('Agendamento cancelado.', 'success')
      setAppointments(prev => prev.map(a => a.id === id ? { ...a, status: 'cancelado' as const } : a))
    } catch (err) {
      showToast(errorMessage(err, 'Não foi possível cancelar.'), 'error')
    } finally {
      setUpdatingId(null)
    }
  }

  const handleReschedule = (id: number) => {
    navigate(`/appointments/new?reschedule=${id}`)
  }

  if (isLoading) return <PageLoader label="Carregando seus agendamentos..." />

  if (error) {
    return (
      <div className={`${styles.page} ${styles.narrowPage}`}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.eyebrow}>Meus Agendamentos</p>
            <h1>Acompanhe seus horários</h1>
          </div>
        </header>
        <p className={ui.errorBox}>{error}</p>
      </div>
    )
  }

  const upcoming = appointments
    .filter(a => !isPast(a.data_hora) && a.status !== 'cancelado' && a.status !== 'realizado')
    .sort((a, b) => new Date(a.data_hora).getTime() - new Date(b.data_hora).getTime())

  const past = appointments
    .filter(a => isPast(a.data_hora) || a.status === 'cancelado' || a.status === 'realizado')
    .sort((a, b) => new Date(b.data_hora).getTime() - new Date(a.data_hora).getTime())

  return (
    <div className={`${styles.page} ${styles.narrowPage}`}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Meus Agendamentos</p>
          <h1>Acompanhe seus horários</h1>
        </div>
        <a className={ui.button} href="/appointments/new">Novo agendamento</a>
      </header>

      {/* Upcoming appointments */}
      <section className={ui.section}>
        <header className={ui.sectionHeader}>
          <h2 className={ui.sectionTitle}>Próximos</h2>
          <span className={ui.sectionCount}>{upcoming.length} agendamento{upcoming.length !== 1 ? 's' : ''}</span>
        </header>

        {upcoming.length === 0 ? (
          <div className={ui.sectionEmpty}>
            <CalendarIcon size={48} className={ui.emptyIcon} aria-hidden="true" />
            <h3>Nenhum agendamento próximo</h3>
            <p>Você não tem agendamentos futuros. Que tal agendar seu próximo corte?</p>
            <a className={ui.button} href="/appointments/new">Agendar agora</a>
          </div>
        ) : (
          <div className={ui.managementList}>
            {upcoming.map((appointment) => (
              <article key={appointment.id} className={ui.appointmentCardEnhanced}>
                <div className={ui.appointmentTimeEnhanced}>
                  <time dateTime={appointment.data_hora}>
                    {new Date(appointment.data_hora).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                  </time>
                  <span className={ui.appointmentDate}>
                    {new Date(appointment.data_hora).toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' })}
                  </span>
                </div>

                <div className={ui.appointmentMainEnhanced}>
                  <div className={ui.appointmentTitleEnhanced}>
                    <h2>{appointment.servico_nome}</h2>
                    <StatusBadge status={appointment.status} />
                  </div>
                  <p>
                    Com <strong>{appointment.barbeiro_nome}</strong>
                    {appointment.barbeiro_especialidade && <>{' — '}{appointment.barbeiro_especialidade}</>}
                  </p>
                  {appointment.observacoes && (
                    <p style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                      "{appointment.observacoes}"
                    </p>
                  )}
                </div>

                <div className={ui.appointmentActionsEnhanced}>
                  {appointment.status === 'agendado' || appointment.status === 'confirmado' ? (
                    <>
                      <button
                        type="button"
                        className={ui.secondaryButton}
                        onClick={() => handleReschedule(appointment.id)}
                        disabled={updatingId === appointment.id}
                      >
                        Reagendar
                      </button>
                      <button
                        type="button"
                        className={ui.dangerButton}
                        onClick={() => handleCancel(appointment.id)}
                        disabled={updatingId === appointment.id}
                      >
                        {updatingId === appointment.id ? 'Cancelando...' : 'Cancelar'}
                      </button>
                    </>
                  ) : (
                    <span className={ui.hint} style={{ fontSize: 'var(--text-xs)' }}>
                      {statusLabels[appointment.status]}
                    </span>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Past appointments */}
      {past.length > 0 && (
        <section className={ui.section}>
          <header className={ui.sectionHeader}>
            <h2 className={ui.sectionTitle}>Anteriores</h2>
            <span className={ui.sectionCount}>{past.length} agendamento{past.length !== 1 ? 's' : ''}</span>
          </header>

          <div className={ui.managementList}>
            {past.map((appointment) => (
              <article key={appointment.id} className={ui.appointmentCardEnhanced}>
                <div className={ui.appointmentTimeEnhanced}>
                  <time dateTime={appointment.data_hora}>
                    {new Date(appointment.data_hora).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                  </time>
                  <span className={ui.appointmentDate}>
                    {new Date(appointment.data_hora).toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short' })}
                  </span>
                </div>

                <div className={ui.appointmentMainEnhanced}>
                  <div className={ui.appointmentTitleEnhanced}>
                    <h2>{appointment.servico_nome}</h2>
                    <StatusBadge status={appointment.status} />
                  </div>
                  <p>
                    Com <strong>{appointment.barbeiro_nome}</strong>
                    {appointment.barbeiro_especialidade && <>{' — '}{appointment.barbeiro_especialidade}</>}
                  </p>
                  {appointment.observacoes && (
                    <p style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                      "{appointment.observacoes}"
                    </p>
                  )}
                </div>

                <div className={ui.appointmentActionsEnhanced}>
                  <span className={ui.hint} style={{ fontSize: 'var(--text-xs)' }}>
                    {statusLabels[appointment.status]}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {appointments.length === 0 && (
        <div className={ui.sectionEmpty} style={{ marginTop: 'var(--space-6)' }}>
          <CalendarIcon size={48} className={ui.emptyIcon} aria-hidden="true" />
          <h3>Nenhum agendamento ainda</h3>
          <p>Comece agendando seu primeiro horário na barbearia.</p>
          <a className={ui.button} href="/appointments/new">Fazer primeiro agendamento</a>
        </div>
      )}
    </div>
  )
}