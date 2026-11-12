import { useMemo, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { listAllAppointments, listAllBarbers } from '../api/endpoints'
import { AppointmentDetails } from '../components/AppointmentDetails'
import { Avatar, StatusBadge } from '../components/Controls'
import { BoardLegend, DayBoard } from '../components/DayBoard'
import { EmptyState, ErrorState, RefreshBar, SkeletonBlock } from '../components/Feedback'
import { ChevronLeftIcon, ChevronRightIcon, UsersIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useBarbershop } from '../contexts/BarbershopContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Appointment } from '../types'
import {
  addDays, dateKey, formatClock, formatCurrency, formatDayShort, plural, relativeDayLabel, timeToMinutes, todayISO,
} from '../utils/format'
import { isOpenStatus } from '../utils/status'
import dash from '../styles/dashboard.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const PERIOD_DAYS = 30

function priceOf(item: Appointment): number {
  return Number(item.preco_historico ?? item.servico_preco ?? 0)
}

const compactCurrency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

export function AdminDashboardPage() {
  const { barbershop } = useBarbershop()
  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(async () => {
    const [appointments, barbers] = await Promise.all([listAllAppointments(), listAllBarbers()])
    return { appointments, barbers }
  }, [])

  const today = todayISO()
  const [day, setDay] = useState(today)
  const [selected, setSelected] = useState<Appointment | null>(null)

  const appointments = useMemo(() => data?.appointments ?? [], [data])
  const barbers = useMemo(() => data?.barbers ?? [], [data])

  const metrics = useMemo(() => {
    const periodStart = addDays(today, -(PERIOD_DAYS - 1))
    const previousStart = addDays(periodStart, -PERIOD_DAYS)
    let todayTotal = 0
    let todayDone = 0
    let todayPending = 0
    let revenue = 0
    let done = 0
    let inPeriod = 0
    let cancelled = 0
    let previousRevenue = 0
    let previousDone = 0
    const daily = new Map<string, { revenue: number; count: number }>()
    const byBarber = new Map<string, { revenue: number; count: number }>()
    const byService = new Map<string, { revenue: number; count: number }>()

    for (const item of appointments) {
      const key = dateKey(item.data_hora)
      if (key === today && item.status !== 'cancelado') {
        todayTotal++
        if (item.status === 'realizado') todayDone++
        if (item.status === 'agendado') todayPending++
      }
      if (key >= periodStart && key <= today) {
        inPeriod++
        if (item.status === 'cancelado') cancelled++
        if (item.status === 'realizado') {
          const price = priceOf(item)
          revenue += price
          done++
          const bucket = daily.get(key) ?? { revenue: 0, count: 0 }
          daily.set(key, { revenue: bucket.revenue + price, count: bucket.count + 1 })
          const barber = byBarber.get(item.barbeiro_nome) ?? { revenue: 0, count: 0 }
          byBarber.set(item.barbeiro_nome, { revenue: barber.revenue + price, count: barber.count + 1 })
          const service = byService.get(item.servico_nome) ?? { revenue: 0, count: 0 }
          byService.set(item.servico_nome, { revenue: service.revenue + price, count: service.count + 1 })
        }
      } else if (key >= previousStart && key < periodStart && item.status === 'realizado') {
        previousRevenue += priceOf(item)
        previousDone++
      }
    }

    const days = Array.from({ length: PERIOD_DAYS }, (_, index) => {
      const key = addDays(periodStart, index)
      return { key, ...(daily.get(key) ?? { revenue: 0, count: 0 }) }
    })

    return {
      todayTotal, todayDone, todayPending, revenue, done, inPeriod, cancelled, previousRevenue, previousDone, days,
      ticket: done ? revenue / done : 0,
      cancelRate: inPeriod ? cancelled / inPeriod : 0,
      byBarber: [...byBarber.entries()].map(([name, v]) => ({ name, ...v })).sort((a, b) => b.revenue - a.revenue),
      byService: [...byService.entries()].map(([name, v]) => ({ name, ...v })).sort((a, b) => b.count - a.count),
    }
  }, [appointments, today])

  const upcoming = useMemo(() => {
    const now = Date.now()
    return appointments
      .filter((item) => isOpenStatus(item.status) && new Date(item.data_hora).getTime() >= now)
      .sort((a, b) => a.data_hora.localeCompare(b.data_hora))
      .slice(0, 6)
  }, [appointments])

  const replaceAppointment = (updated: Appointment) => {
    setData((current) => current && {
      ...current,
      appointments: current.appointments.map((item) => (item.id === updated.id ? updated : item)),
    })
  }

  const header = (
    <PageHeader
      title="Painel"
      description={`A operação de hoje e o desempenho dos últimos ${PERIOD_DAYS} dias.`}
      actions={<Link to="/admin/appointments" className={ui.secondaryButton}>Ver todos os agendamentos</Link>}
    />
  )

  if (isLoading) {
    return (
      <div className={page.page}>
        {header}
        <SkeletonBlock height={124} />
        <SkeletonBlock height={420} />
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className={page.page}>
        {header}
        <div className={ui.panel}><ErrorState error={error} fallback="Não foi possível carregar o painel." onRetry={() => void reload()} /></div>
      </div>
    )
  }

  // Comparação só com base mínima no período anterior; com poucos dados a variação engana
  const MIN_BASELINE = 20
  const revenueDelta = metrics.previousDone >= MIN_BASELINE && metrics.previousRevenue > 0
    ? (metrics.revenue - metrics.previousRevenue) / metrics.previousRevenue
    : null
  const opens = barbershop ? timeToMinutes(barbershop.horario_abertura) : 8 * 60
  const closes = barbershop ? timeToMinutes(barbershop.horario_fechamento) : 20 * 60
  const activeBarbers = barbers.filter((barber) => barber.ativo)

  return (
    <div className={page.page}>
      {header}

      <section className={dash.ledger} aria-label="Indicadores">
        <div className={dash.metric}>
          <span className={dash.metricLabel}>Hoje</span>
          <span className={dash.metricValue}>{metrics.todayTotal}<small>{metrics.todayTotal === 1 ? ' horário' : ' horários'}</small></span>
          <span className={dash.metricNote}>
            {metrics.todayTotal === 0 ? 'Nenhum horário marcado' : `${plural(metrics.todayDone, 'realizado')}, ${metrics.todayPending} a confirmar`}
          </span>
        </div>
        <div className={dash.metric}>
          <span className={dash.metricLabel}>Faturamento, {PERIOD_DAYS} dias</span>
          <span className={dash.metricValue}>{compactCurrency.format(metrics.revenue)}</span>
          <span className={dash.metricNote}>
            {revenueDelta !== null && (
              <span className={`${dash.delta} ${revenueDelta >= 0 ? dash.deltaUp : dash.deltaDown}`}>
                {revenueDelta >= 0 ? '+' : '−'}{Math.abs(Math.round(revenueDelta * 100))}%
              </span>
            )}{revenueDelta !== null && ' '}
            {revenueDelta !== null ? 'vs. período anterior' : `${plural(metrics.done, 'atendimento realizado', 'atendimentos realizados')}`}
          </span>
        </div>
        <div className={dash.metric}>
          <span className={dash.metricLabel}>Ticket médio</span>
          <span className={dash.metricValue}>{formatCurrency(metrics.ticket)}</span>
          <span className={dash.metricNote}>por atendimento realizado</span>
        </div>
        <div className={dash.metric}>
          <span className={dash.metricLabel}>Cancelamentos</span>
          <span className={dash.metricValue}>{Math.round(metrics.cancelRate * 100)}<small>%</small></span>
          <span className={dash.metricNote}>{metrics.cancelled} de {plural(metrics.inPeriod, 'agendamento')}</span>
        </div>
      </section>

      <section className={ui.panel} aria-labelledby="board-title">
        <div className={dash.boardHeader}>
          <div className={dash.boardTitle}>
            <h2 id="board-title">Agenda do dia</h2>
            <p>Clique em um horário para ver detalhes, confirmar ou cancelar.</p>
          </div>
          <div className={dash.dayNav}>
            <button type="button" className={ui.iconButton} onClick={() => setDay(addDays(day, -1))} aria-label="Dia anterior"><ChevronLeftIcon /></button>
            <span className={dash.dayLabel} aria-live="polite">{relativeDayLabel(day)}{day === today ? `, ${formatDayShort(day)}` : ''}</span>
            <button type="button" className={ui.iconButton} onClick={() => setDay(addDays(day, 1))} aria-label="Próximo dia"><ChevronRightIcon /></button>
            {day !== today && <button type="button" className={`${ui.secondaryButton} ${ui.sm}`} onClick={() => setDay(today)}>Hoje</button>}
          </div>
        </div>
        <RefreshBar active={isRefreshing} />
        {activeBarbers.length === 0 && !appointments.some((item) => dateKey(item.data_hora) === day) ? (
          <EmptyState
            compact
            icon={<UsersIcon size={22} />}
            title="Nenhum barbeiro ativo"
            description="Cadastre a equipe para que os clientes possam agendar e a agenda do dia apareça aqui."
            action={{ label: 'Cadastrar barbeiro', to: '/admin/barbers' }}
          />
        ) : (
          <DayBoard day={day} appointments={appointments} barbers={barbers} opens={opens} closes={closes} onSelect={setSelected} />
        )}
        <div className={dash.boardFooter}><BoardLegend /></div>
      </section>

      <div className={page.split}>
        <section className={ui.panel} aria-labelledby="revenue-title">
          <div className={ui.panelHeader}>
            <div>
              <h2 id="revenue-title">Faturamento diário</h2>
              <p>Atendimentos realizados, pelo preço praticado no agendamento.</p>
            </div>
          </div>
          <DailyRevenueChart days={metrics.days} />
        </section>

        <section className={ui.panel} aria-labelledby="upcoming-title">
          <div className={ui.panelHeader}>
            <h2 id="upcoming-title">Próximos atendimentos</h2>
          </div>
          {upcoming.length === 0 ? (
            <EmptyState compact title="Nada pela frente" description="Novos agendamentos dos clientes aparecem aqui." />
          ) : (
            <div className={dash.upcoming}>
              {upcoming.map((item) => {
                const key = dateKey(item.data_hora)
                return (
                  <button type="button" key={item.id} className={dash.upcomingItem} onClick={() => setSelected(item)}>
                    <span className={dash.upcomingWhen}>
                      <strong>{formatClock(item.data_hora)}</strong>
                      <span>{key === today ? 'Hoje' : key === addDays(today, 1) ? 'Amanhã' : formatDayShort(key)}</span>
                    </span>
                    <span className={dash.upcomingMain}>
                      <strong>{item.cliente_nome}</strong>
                      <span>{item.servico_nome} com {item.barbeiro_nome.split(' ')[0]}</span>
                    </span>
                    <StatusBadge status={item.status} />
                  </button>
                )
              })}
            </div>
          )}
        </section>
      </div>

      <div className={page.twoCols}>
        <RankPanel
          title="Equipe"
          subtitle={`Faturamento por barbeiro, últimos ${PERIOD_DAYS} dias.`}
          rows={metrics.byBarber.map((row) => ({ name: row.name, value: row.revenue, primary: compactCurrency.format(row.revenue), secondary: plural(row.count, 'atendimento') }))}
          withAvatar
        />
        <RankPanel
          title="Serviços mais realizados"
          subtitle={`Quantidade de atendimentos, últimos ${PERIOD_DAYS} dias.`}
          rows={metrics.byService.map((row) => ({ name: row.name, value: row.count, primary: plural(row.count, 'vez', 'vezes'), secondary: compactCurrency.format(row.revenue) }))}
        />
      </div>

      <AppointmentDetails appointment={selected} onClose={() => setSelected(null)} onUpdated={replaceAppointment} />
    </div>
  )
}

function DailyRevenueChart({ days }: { days: { key: string; revenue: number; count: number }[] }) {
  const max = Math.max(...days.map((item) => item.revenue), 0)
  if (max === 0) {
    return <EmptyState compact title="Sem atendimentos realizados" description="O faturamento aparece aqui conforme os atendimentos forem marcados como realizados." />
  }
  const step = max > 1000 ? 500 : max > 400 ? 200 : max > 100 ? 50 : 20
  const top = Math.ceil(max / step) * step
  return (
    <div className={dash.chart}>
      <div className={dash.chartBars}>
        <div className={dash.chartGrid} style={{ top: 0 }}><span className={dash.chartGridLabel}>{compactCurrency.format(top)}</span></div>
        <div className={dash.chartGrid} style={{ top: '50%' }}><span className={dash.chartGridLabel}>{compactCurrency.format(top / 2)}</span></div>
        {days.map((item, index) => (
          <div
            key={item.key}
            className={dash.chartCol}
            tabIndex={0}
            aria-label={`${formatDayShort(item.key)}: ${formatCurrency(item.revenue)}, ${plural(item.count, 'atendimento')}`}
          >
            <div
              className={`${dash.chartBar} ${item.revenue === 0 ? dash.chartBarEmpty : ''}`}
              style={{ height: `${(item.revenue / top) * 100}%`, '--delay': `${index * 12}ms` } as CSSProperties}
            />
            <span className={dash.tooltip} aria-hidden="true">
              {formatDayShort(item.key)}
              <strong>{formatCurrency(item.revenue)}</strong>
              {plural(item.count, 'atendimento')}
            </span>
          </div>
        ))}
      </div>
      <div className={dash.chartAxis} aria-hidden="true">
        <span>{formatDayShort(days[0].key)}</span>
        <span>{formatDayShort(days[Math.floor(days.length / 2)].key)}</span>
        <span>Hoje</span>
      </div>
      <table className="sr-only">
        <caption>Faturamento diário</caption>
        <thead><tr><th>Dia</th><th>Faturamento</th><th>Atendimentos</th></tr></thead>
        <tbody>
          {days.filter((item) => item.count > 0).map((item) => (
            <tr key={item.key}><td>{formatDayShort(item.key)}</td><td>{formatCurrency(item.revenue)}</td><td>{item.count}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface RankRow { name: string; value: number; primary: string; secondary: string }

function RankPanel({ title, subtitle, rows, withAvatar }: { title: string; subtitle: string; rows: RankRow[]; withAvatar?: boolean }) {
  const max = Math.max(...rows.map((row) => row.value), 0)
  return (
    <section className={ui.panel} aria-label={title}>
      <div className={ui.panelHeader}>
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {rows.length === 0 ? (
        <EmptyState compact title="Sem dados no período" description="Os números aparecem quando houver atendimentos realizados." />
      ) : (
        <ul className={dash.rankList}>
          {rows.slice(0, 6).map((row) => (
            <li className={dash.rankRow} key={row.name}>
              <span className={dash.rankName} title={row.name} style={withAvatar ? { display: 'flex', alignItems: 'center', gap: 8 } : undefined}>
                {withAvatar && <Avatar name={row.name} size="sm" />}
                {row.name}
              </span>
              <span className={dash.rankTrack} aria-hidden="true">
                <span className={dash.rankFill} style={{ width: `${max ? (row.value / max) * 100 : 0}%`, display: 'block' }} />
              </span>
              <span className={dash.rankValue}>
                <strong>{row.primary}</strong>
                <span>{row.secondary}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
