import { useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { barberApi, serviceApi, listAllAppointments } from '../api/endpoints'
import { useAsyncData } from '../hooks/useAsyncData'
import type { AppointmentStatus } from '../types'
import { formatCurrency, formatDateTime, todayISO, statusLabels } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

function dateKey(value: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(value))
  const get = (kind: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === kind)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')}`
}

function parseDateForCompare(value: string): Date {
  return new Date(value)
}

export function AdminDashboardPage() {
  useAuth()

  const { data: allAppointments, isLoading: loadingAppointments, error: errorAppointments } = useAsyncData(listAllAppointments, [])
  const { data: servicesData, isLoading: loadingServices } = useAsyncData(() => serviceApi.list().then(r => r.data), [])
  const { data: barbersData, isLoading: loadingBarbers } = useAsyncData(() => barberApi.list().then(r => r.data), [])

  const isLoading = loadingAppointments || loadingServices || loadingBarbers
  const error = errorAppointments

  const today = todayISO()
  const now = useMemo(() => new Date(), [])

  const appointments = useMemo(() => allAppointments ?? [], [allAppointments])
  const services = useMemo(() => servicesData?.results ?? [], [servicesData?.results])
  const barbers = useMemo(() => barbersData?.results ?? [], [barbersData?.results])

  const todayAppointments = useMemo(() =>
    appointments
      .filter(a => dateKey(a.data_hora) === today)
      .sort((a, b) => a.data_hora.localeCompare(b.data_hora)),
    [appointments, today]
  )

  const upcomingAppointments = useMemo(() =>
    appointments
      .filter(a => {
        const appointmentDate = parseDateForCompare(a.data_hora)
        return appointmentDate >= now && a.status !== 'cancelado' && a.status !== 'realizado'
      })
      .sort((a, b) => a.data_hora.localeCompare(b.data_hora))
      .slice(0, 10),
    [appointments, now]
  )

  const statusCounts = useMemo(() => {
    const counts: Record<AppointmentStatus, number> = { agendado: 0, confirmado: 0, realizado: 0, cancelado: 0 }
    appointments.forEach(a => { counts[a.status]++ })
    return counts
  }, [appointments])

  const totalRevenue = useMemo(() =>
    appointments
      .filter(a => a.status === 'realizado')
      .reduce((sum, a) => sum + Number(a.servico_preco), 0),
    [appointments]
  )

  const stats = [
    { label: 'Agendamentos hoje', value: todayAppointments.length, description: 'Horários marcados para hoje' },
    { label: 'Total de agendamentos', value: appointments.length, description: 'Todos os status' },
    { label: 'Serviços cadastrados', value: services.length, description: services.filter(s => s.ativo).length + ' ativos' },
    { label: 'Barbeiros cadastrados', value: barbers.length, description: barbers.filter(b => b.ativo).length + ' ativos' },
  ]

  const statusOrder: AppointmentStatus[] = ['agendado', 'confirmado', 'realizado', 'cancelado']
  const statusColors: Record<AppointmentStatus, string> = {
    agendado: 'var(--color-info)',
    confirmado: 'var(--color-success)',
    realizado: 'var(--color-primary)',
    cancelado: 'var(--color-error)',
  }

  if (isLoading) return <div className={styles.page}><div className={ui.pageLoader}>Carregando dashboard...</div></div>
  if (error) return <div className={styles.page}><p className={ui.errorBox}>Não foi possível carregar o dashboard.</p></div>

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Painel administrativo</p>
          <h1>Dashboard</h1>
        </div>
        <p>{new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>
      </header>

      <section className={styles.statsGrid} aria-label="Indicadores principais">
        {stats.map((stat, i) => (
          <article key={i} className={styles.statCard}>
            <p className={styles.statLabel}>{stat.label}</p>
            <p className={styles.statValue}>{stat.value}</p>
            <p className={styles.statDescription}>{stat.description}</p>
          </article>
        ))}
        <article className={styles.statCard} style={{ gridColumn: 'span 1' }}>
          <p className={styles.statLabel}>Faturamento (realizados)</p>
          <p className={styles.statValue}>{formatCurrency(totalRevenue.toString())}</p>
          <p className={styles.statDescription}>Soma de serviços concluídos</p>
        </article>
      </section>

      <div className={styles.dashboardGrid}>
        <section className={styles.dashboardCard} aria-labelledby="today-title">
          <header className={styles.cardHeader}>
            <h2 id="today-title">Agendamentos de hoje</h2>
            <span className={styles.cardCount}>{todayAppointments.length}</span>
          </header>
          {todayAppointments.length === 0 ? (
            <div className={ui.tableEmpty}>Nenhum agendamento para hoje</div>
          ) : (
            <div className={ui.tableContainer}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Horário</th>
                    <th>Cliente</th>
                    <th>Serviço</th>
                    <th>Barbeiro</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {todayAppointments.map((appointment) => (
                    <tr key={appointment.id}>
                      <td>
                        <time dateTime={appointment.data_hora}>
                          {new Date(appointment.data_hora).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                        </time>
                      </td>
                      <td><strong>{appointment.cliente_nome}</strong></td>
                      <td>{appointment.servico_nome}</td>
                      <td>{appointment.barbeiro_nome}</td>
                      <td>
                        <span className={`${ui.badge} ${ui.badgeDefault}`} style={{ backgroundColor: statusColors[appointment.status], color: 'white' }}>
                          {statusLabels[appointment.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className={styles.dashboardCard} aria-labelledby="upcoming-title">
          <header className={styles.cardHeader}>
            <h2 id="upcoming-title">Próximos atendimentos</h2>
            <span className={styles.cardCount}>{upcomingAppointments.length}</span>
          </header>
          {upcomingAppointments.length === 0 ? (
            <div className={ui.tableEmpty}>Nenhum atendimento futuro</div>
          ) : (
            <div className={ui.tableContainer}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Data e Hora</th>
                    <th>Cliente</th>
                    <th>Serviço</th>
                    <th>Barbeiro</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {upcomingAppointments.map((appointment) => (
                    <tr key={appointment.id}>
                      <td>{formatDateTime(appointment.data_hora)}</td>
                      <td><strong>{appointment.cliente_nome}</strong></td>
                      <td>{appointment.servico_nome}</td>
                      <td>{appointment.barbeiro_nome}</td>
                      <td>
                        <span className={`${ui.badge} ${ui.badgeDefault}`} style={{ backgroundColor: statusColors[appointment.status], color: 'white' }}>
                          {statusLabels[appointment.status]}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className={styles.dashboardCard} aria-labelledby="status-title">
          <header className={styles.cardHeader}>
            <h2 id="status-title">Distribuição por status</h2>
          </header>
          <div className={styles.statusDistribution}>
            {statusOrder.map(status => (
              <div key={status} className={styles.statusItem}>
                <div className={styles.statusItemMain}>
                  <span className={styles.statusDot} style={{ backgroundColor: statusColors[status] }} aria-hidden="true" />
                  <span className={styles.statusName}>{statusLabels[status]}</span>
                </div>
                <div className={styles.statusItemMeta}>
                  <span className={styles.statusCount}>{statusCounts[status]}</span>
                  <span className={styles.statusPercent}>
                    {appointments.length > 0
                      ? Math.round((statusCounts[status] / appointments.length) * 100) + '%'
                      : '0%'}
                  </span>
                </div>
                <div className={styles.statusBar} role="progressbar" aria-valuenow={statusCounts[status]} aria-valuemin={0} aria-valuemax={appointments.length || 1} aria-label={statusLabels[status]}>
                  <div className={styles.statusBarFill} style={{ width: appointments.length > 0 ? (statusCounts[status] / appointments.length) * 100 : 0 + '%', backgroundColor: statusColors[status] }} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.dashboardCard} aria-labelledby="revenue-title">
          <header className={styles.cardHeader}>
            <h2 id="revenue-title">Faturamento por status</h2>
          </header>
          <div className={styles.revenueBreakdown}>
            {statusOrder.map(status => {
              const revenue = appointments
                .filter(a => a.status === status)
                .reduce((sum, a) => sum + Number(a.servico_preco), 0)
              return (
                <div key={status} className={styles.revenueItem}>
                  <span className={styles.statusDot} style={{ backgroundColor: statusColors[status] }} aria-hidden="true" />
                  <span>{statusLabels[status]}</span>
                  <strong>{formatCurrency(revenue.toString())}</strong>
                </div>
              )
            })}
            <div className={styles.revenueTotal}>
              <span>Total (realizados)</span>
              <strong>{formatCurrency(totalRevenue.toString())}</strong>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}