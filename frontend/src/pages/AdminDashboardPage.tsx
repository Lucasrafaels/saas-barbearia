import { useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { listAllAppointments, listAllServices, listAllBarbers } from '../api/endpoints'
import { PageLoader } from '../components/PageLoader'
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
  const { data: services, isLoading: loadingServices, error: errorServices } = useAsyncData(listAllServices, [])
  const { data: barbers, isLoading: loadingBarbers, error: errorBarbers } = useAsyncData(listAllBarbers, [])

  const isLoading = loadingAppointments || loadingServices || loadingBarbers
  const hasError = errorAppointments || errorServices || errorBarbers

  const today = todayISO()
  const now = useMemo(() => new Date(), [])

  const appointments = useMemo(() => allAppointments ?? [], [allAppointments])
  const servicesArray = useMemo(() => services ?? [], [services])
  const barbersArray = useMemo(() => barbers ?? [], [barbers])

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
    { label: 'Serviços ativos', value: errorServices ? '—' : servicesArray.filter(s => s.ativo).length, description: errorServices ? 'Erro ao carregar' : `${servicesArray.filter(s => s.ativo).length} de ${servicesArray.length} ativos` },
    { label: 'Barbeiros ativos', value: errorBarbers ? '—' : barbersArray.filter(b => b.ativo).length, description: errorBarbers ? 'Erro ao carregar' : `${barbersArray.filter(b => b.ativo).length} de ${barbersArray.length} ativos` },
  ]

  const statusOrder: AppointmentStatus[] = ['agendado', 'confirmado', 'realizado', 'cancelado']
  // Use design tokens directly for status colors - matching badge classes
  const statusColors: Record<AppointmentStatus, string> = {
    agendado: 'var(--color-primary-navy)',    // --color-primary-navy (matches badgeInfo)
    confirmado: 'var(--color-success)',       // --color-success (matches badgeSuccess)
    realizado: 'var(--color-error)',          // --color-error (--color-primary-red, matches badgeError)
    cancelado: 'var(--color-warning)',        // --color-warning (matches badgeWarning)
  }

  // Badge classes mapping - using design token colors
  // Note: ui.badgeInfo = primary-navy, ui.badgeSuccess = green, ui.badgeError = red, ui.badgeWarning = yellow
  const statusBadgeClass: Record<AppointmentStatus, string> = {
    agendado: ui.badgeInfo,      // --color-info (--color-primary-navy)
    confirmado: ui.badgeSuccess, // --color-success (green)
    realizado: ui.badgeError,    // --color-error (--color-primary-red)
    cancelado: ui.badgeWarning,  // --color-warning (yellow)
  }

  if (isLoading) return <PageLoader label="Carregando dashboard..." />
  const formatError = (err: unknown): string => {
    if (err instanceof Error) return err.message
    if (typeof err === 'string') return err
    return 'Erro desconhecido'
  }

  const errorMessages = [
    errorAppointments ? `Agendamentos: ${formatError(errorAppointments)}` : null,
    errorServices ? `Serviços: ${formatError(errorServices)}` : null,
    errorBarbers ? `Barbeiros: ${formatError(errorBarbers)}` : null,
  ].filter(Boolean) as string[]

  if (hasError) return (
    <div className={styles.page}>
      <div className={ui.errorBox}>
        <p>Não foi possível carregar alguns dados do dashboard.</p>
        {errorMessages.map((msg, i) => (
          <p key={i}>{msg}</p>
        ))}
      </div>
    </div>
  )

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
          <p className={styles.statLabel}>Valor dos serviços concluídos</p>
          <p className={styles.statValue}>{formatCurrency(totalRevenue.toString())}</p>
          <p className={styles.statDescription}>Soma dos preços dos serviços com status "realizado" — não reflete pagamentos confirmados</p>
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
                        <span className={`${ui.badge} ${statusBadgeClass[appointment.status]}`}>
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
                        <span className={`${ui.badge} ${statusBadgeClass[appointment.status]}`}>
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
                  <div className={styles.statusBarFill} style={{ width: appointments.length > 0 ? `${(statusCounts[status] / appointments.length) * 100}%` : '0%', backgroundColor: statusColors[status] }} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.dashboardCard} aria-labelledby="revenue-title">
          <header className={styles.cardHeader}>
            <h2 id="revenue-title">Valor dos serviços por status</h2>
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
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-3)' }}>
              Valores baseados nos preços cadastrados dos serviços — não reflete pagamentos confirmados
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}