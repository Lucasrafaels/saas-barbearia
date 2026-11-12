import { Fragment, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAllAppointments } from '../api/endpoints'
import { AppointmentActions } from '../components/AppointmentActions'
import { SegmentedControl, StatusBadge } from '../components/Controls'
import { EmptyState, ErrorState, RefreshBar, SkeletonRows } from '../components/Feedback'
import { CalendarCheckIcon, ChevronLeftIcon, ChevronRightIcon, RefreshIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { useBarbershop } from '../contexts/BarbershopContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Appointment } from '../types'
import {
  addDays, dateKey, firstName, formatClock, formatDayCompact, formatDayShort, formatDuration, minutesOfDay, minutesToClock, plural,
  relativeDayLabel, timeToMinutes, todayISO,
} from '../utils/format'
import client from '../styles/client.module.css'
import dash from '../styles/dashboard.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

type View = 'day' | 'pending'

const MIN_GAP = 30

/** Agenda do barbeiro: o dia em ordem, com intervalos livres e ações de status. */
export function BarberAgendaPage() {
  const { user } = useAuth()
  const { barbershop } = useBarbershop()
  const [params, setParams] = useSearchParams()
  const today = todayISO()
  const day = params.get('dia') ?? today
  const view: View = params.get('status') === 'agendado' ? 'pending' : 'day'
  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(listAllAppointments, [])

  const setDay = (key: string) => {
    const next = new URLSearchParams()
    if (key !== today) next.set('dia', key)
    setParams(next, { replace: true })
  }

  const setView = (value: View) => {
    const next = new URLSearchParams(params)
    if (value === 'pending') next.set('status', 'agendado')
    else next.delete('status')
    setParams(next, { replace: true })
  }

  const dayItems = useMemo(
    () => (data ?? []).filter((item) => dateKey(item.data_hora) === day).sort((a, b) => a.data_hora.localeCompare(b.data_hora)),
    [data, day],
  )

  const pending = useMemo(
    () => (data ?? []).filter((item) => item.status === 'agendado').sort((a, b) => a.data_hora.localeCompare(b.data_hora)),
    [data],
  )

  const replace = (updated: Appointment) => setData((current) => current?.map((item) => (item.id === updated.id ? updated : item)) ?? null)

  // Intervalos livres entre atendimentos, dentro do horário de funcionamento
  const timeline = useMemo(() => {
    const active = dayItems.filter((item) => item.status !== 'cancelado')
    const rows: ({ kind: 'item'; item: Appointment } | { kind: 'gap'; from: number; to: number })[] = []
    let cursor = barbershop ? timeToMinutes(barbershop.horario_abertura) : null
    const closes = barbershop ? timeToMinutes(barbershop.horario_fechamento) : null
    for (const item of dayItems) {
      const begin = minutesOfDay(item.data_hora)
      if (item.status !== 'cancelado' && cursor !== null && begin - cursor >= MIN_GAP) rows.push({ kind: 'gap', from: cursor, to: begin })
      rows.push({ kind: 'item', item })
      if (item.status !== 'cancelado') cursor = Math.max(cursor ?? 0, begin + item.servico_duracao)
    }
    if (active.length > 0 && cursor !== null && closes !== null && closes - cursor >= MIN_GAP) rows.push({ kind: 'gap', from: cursor, to: closes })
    return rows
  }, [dayItems, barbershop])

  const summary = useMemo(() => {
    const active = dayItems.filter((item) => item.status !== 'cancelado')
    const done = active.filter((item) => item.status === 'realizado').length
    const now = Date.now()
    const next = active.find((item) => item.status !== 'realizado' && new Date(item.data_hora).getTime() >= now)
    return { total: active.length, done, next }
  }, [dayItems])

  const nowMinutes = minutesOfDay(new Date().toISOString())

  return (
    <div className={`${page.page} ${page.medium}`}>
      <PageHeader
        title="Minha agenda"
        description={user ? `Seus atendimentos, ${firstName(user.nome)}. Confirme, marque como realizado ou cancele cada horário.` : undefined}
        actions={
          <button type="button" className={ui.secondaryButton} onClick={() => void reload()} disabled={isRefreshing}>
            <RefreshIcon size={16} /> Atualizar
          </button>
        }
      />

      <section className={ui.panel}>
        <div className={dash.boardHeader}>
          <SegmentedControl
            label="Visualização"
            value={view}
            onChange={setView}
            options={[
              { value: 'day', label: 'Por dia' },
              { value: 'pending', label: 'A confirmar', count: pending.length },
            ]}
          />
          {view === 'day' && (
            <div className={dash.dayNav}>
              <button type="button" className={ui.iconButton} onClick={() => setDay(addDays(day, -1))} aria-label="Dia anterior"><ChevronLeftIcon /></button>
              <span className={dash.dayLabel} aria-live="polite">{relativeDayLabel(day)}{day === today ? `, ${formatDayShort(day)}` : ''}</span>
              <button type="button" className={ui.iconButton} onClick={() => setDay(addDays(day, 1))} aria-label="Próximo dia"><ChevronRightIcon /></button>
              {day !== today && <button type="button" className={`${ui.secondaryButton} ${ui.sm}`} onClick={() => setDay(today)}>Hoje</button>}
            </div>
          )}
        </div>

        {view === 'day' && !isLoading && !error && summary.total > 0 && (
          <p className={ui.resultMeta}>
            <span>
              {plural(summary.total, 'atendimento')}, {plural(summary.done, 'realizado')}
              {day === today && summary.next ? `. Próximo às ${formatClock(summary.next.data_hora)} com ${summary.next.cliente_nome}.` : '.'}
            </span>
          </p>
        )}
        <RefreshBar active={isRefreshing} />

        {isLoading ? (
          <SkeletonRows rows={5} label="Carregando sua agenda" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar sua agenda." onRetry={() => void reload()} />
        ) : view === 'pending' ? (
          pending.length === 0 ? (
            <EmptyState icon={<CalendarCheckIcon size={22} />} title="Tudo confirmado" description="Nenhum horário aguardando confirmação." action={{ label: 'Ver agenda do dia', onClick: () => setView('day') }} />
          ) : (
            pending.map((item) => <AgendaRow key={item.id} item={item} showDay onUpdated={replace} />)
          )
        ) : dayItems.length === 0 ? (
          <EmptyState
            icon={<CalendarCheckIcon size={22} />}
            title={day === today ? 'Nenhum atendimento hoje' : 'Nenhum atendimento neste dia'}
            description="Quando um cliente agendar com você, o horário aparece aqui."
            action={day !== today ? { label: 'Voltar para hoje', onClick: () => setDay(today) } : undefined}
          />
        ) : (
          timeline.map((row, index) => (
            <Fragment key={row.kind === 'item' ? row.item.id : `gap-${index}`}>
              {row.kind === 'gap' ? (
                <div className={client.gapRow}>
                  <span>{minutesToClock(row.from)}</span>
                  <span>
                    Livre até {minutesToClock(row.to)} ({formatDuration(row.to - row.from)})
                    {day === today && nowMinutes >= row.from && nowMinutes < row.to ? ', agora' : ''}
                  </span>
                </div>
              ) : (
                <AgendaRow item={row.item} onUpdated={replace} />
              )}
            </Fragment>
          ))
        )}
      </section>
    </div>
  )
}

function AgendaRow({ item, showDay, onUpdated }: { item: Appointment; showDay?: boolean; onUpdated: (updated: Appointment) => void }) {
  return (
    <article className={`${page.apptRow} ${item.status === 'cancelado' ? page.apptCancelled : ''}`}>
      <div className={page.apptTime}>
        <time dateTime={item.data_hora}>{formatClock(item.data_hora)}</time>
        <span>{showDay ? formatDayCompact(dateKey(item.data_hora)) : formatDuration(item.servico_duracao)}</span>
      </div>
      <div className={page.apptMain}>
        <div className={page.apptTitle}>
          <span>{item.cliente_nome}</span>
          <StatusBadge status={item.status} />
        </div>
        <p className={page.apptMeta}>{item.servico_nome}{showDay ? `, ${formatDuration(item.servico_duracao)}` : ''}</p>
        {item.observacoes && <p className={page.apptNote}>“{item.observacoes}”</p>}
      </div>
      <div className={page.apptAside}>
        <AppointmentActions appointment={item} onUpdated={onUpdated} />
      </div>
    </article>
  )
}
