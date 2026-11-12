import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listAllAppointments, listAllBarbers } from '../api/endpoints'
import { AppointmentActions } from '../components/AppointmentActions'
import { SearchField, SegmentedControl, StatusBadge } from '../components/Controls'
import { EmptyState, ErrorState, RefreshBar, SkeletonRows } from '../components/Feedback'
import { CalendarIcon, RefreshIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Appointment, AppointmentStatus } from '../types'
import {
  dateKey, formatClock, formatCurrency, formatDuration, matchesSearch, plural, relativeDayLabel, todayISO,
} from '../utils/format'
import { statusOrder } from '../utils/status'
import { statusLabels } from '../utils/format'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

type Period = 'today' | 'upcoming' | 'past' | 'all'
type StatusFilter = AppointmentStatus | 'all'

const periodLabels: Record<Period, string> = {
  today: 'Hoje',
  upcoming: 'Próximos',
  past: 'Anteriores',
  all: 'Todo o período',
}

const PAGE_STEP = 60

export function AdminAppointmentsPage() {
  const [params, setParams] = useSearchParams()
  const status = (params.get('status') as StatusFilter | null) ?? 'all'
  const period = (params.get('periodo') as Period | null) ?? (params.get('status') ? 'all' : 'upcoming')
  const barber = params.get('barbeiro') ?? 'all'
  const query = params.get('q') ?? ''
  const [visible, setVisible] = useState(PAGE_STEP)

  const update = (key: string, value: string, fallback: string) => {
    const next = new URLSearchParams(params)
    if (value === fallback) next.delete(key)
    else next.set(key, value)
    // Mantém o período visível estável ao trocar o status (o padrão depende do status)
    if (key === 'status' && !params.has('periodo') && period !== 'upcoming') next.set('periodo', period)
    setParams(next, { replace: true })
    setVisible(PAGE_STEP)
  }

  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(async () => {
    const [appointments, barbers] = await Promise.all([listAllAppointments(), listAllBarbers()])
    return { appointments, barbers }
  }, [])

  const today = todayISO()

  // Filtros que não são de status (para contar por status dentro do recorte)
  const scoped = useMemo(() => {
    const now = Date.now()
    return (data?.appointments ?? []).filter((item) => {
      const key = dateKey(item.data_hora)
      const time = new Date(item.data_hora).getTime()
      if (period === 'today' && key !== today) return false
      if (period === 'upcoming' && time < now) return false
      if (period === 'past' && time >= now) return false
      if (barber !== 'all' && String(item.barbeiro) !== barber) return false
      return matchesSearch(query, item.cliente_nome, item.servico_nome, item.barbeiro_nome)
    })
  }, [data, period, barber, query, today])

  const counts = useMemo(() => {
    const result: Record<StatusFilter, number> = { all: scoped.length, agendado: 0, confirmado: 0, realizado: 0, cancelado: 0 }
    for (const item of scoped) result[item.status]++
    return result
  }, [scoped])

  const filtered = useMemo(() => {
    const list = status === 'all' ? scoped : scoped.filter((item) => item.status === status)
    const ascending = period === 'today' || period === 'upcoming'
    return [...list].sort((a, b) => (ascending ? a.data_hora.localeCompare(b.data_hora) : b.data_hora.localeCompare(a.data_hora)))
  }, [scoped, status, period])

  const groups = useMemo(() => {
    const result: { key: string; items: Appointment[] }[] = []
    for (const item of filtered.slice(0, visible)) {
      const key = dateKey(item.data_hora)
      const last = result[result.length - 1]
      if (last && last.key === key) last.items.push(item)
      else result.push({ key, items: [item] })
    }
    return result
  }, [filtered, visible])

  const replaceAppointment = (updated: Appointment) => {
    setData((current) => current && {
      ...current,
      appointments: current.appointments.map((item) => (item.id === updated.id ? updated : item)),
    })
  }

  const hasFilters = status !== 'all' || barber !== 'all' || query !== '' || period !== 'upcoming'

  return (
    <div className={page.page}>
      <PageHeader
        title="Agendamentos"
        description="Todos os horários da barbearia. Confirme, marque como realizado ou cancele direto na lista."
        actions={
          <button type="button" className={ui.secondaryButton} onClick={() => void reload()} disabled={isRefreshing}>
            <RefreshIcon size={16} /> Atualizar
          </button>
        }
      />

      <section className={ui.panel}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGrow}>
            <SearchField value={query} onChange={(value) => update('q', value, '')} placeholder="Buscar por cliente, serviço ou barbeiro" />
          </div>
          <label className={ui.toolbarField}>
            <span>Período</span>
            <select value={period} onChange={(event) => update('periodo', event.target.value, 'upcoming')}>
              {(Object.keys(periodLabels) as Period[]).map((key) => <option key={key} value={key}>{periodLabels[key]}</option>)}
            </select>
          </label>
          <label className={ui.toolbarField}>
            <span>Barbeiro</span>
            <select value={barber} onChange={(event) => update('barbeiro', event.target.value, 'all')}>
              <option value="all">Todos</option>
              {(data?.barbers ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.nome}{item.ativo ? '' : ' (inativo)'}</option>
              ))}
            </select>
          </label>
        </div>

        <div className={ui.resultMeta} style={{ flexWrap: 'wrap' }}>
          <SegmentedControl
            label="Filtrar por status"
            value={status}
            onChange={(value) => update('status', value, 'all')}
            options={[{ value: 'all', label: 'Todos', count: counts.all }, ...statusOrder.map((key) => ({ value: key, label: statusLabels[key], count: counts[key] }))]}
          />
          {hasFilters && (
            <button type="button" className={ui.textButton} onClick={() => { setParams(new URLSearchParams(), { replace: true }); setVisible(PAGE_STEP) }}>
              Limpar filtros
            </button>
          )}
        </div>

        <RefreshBar active={isRefreshing} />

        {isLoading ? (
          <SkeletonRows rows={6} label="Carregando agendamentos" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar os agendamentos." onRetry={() => void reload()} />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<CalendarIcon size={22} />}
            title={hasFilters ? 'Nenhum agendamento com esses filtros' : 'Nenhum agendamento pela frente'}
            description={hasFilters ? 'Ajuste o período, o status ou a busca para ver outros horários.' : 'Os horários marcados pelos clientes aparecem aqui.'}
            action={hasFilters ? { label: 'Limpar filtros', onClick: () => setParams(new URLSearchParams(), { replace: true }) } : undefined}
          />
        ) : (
          <>
            <p className="sr-only" aria-live="polite">{plural(filtered.length, 'agendamento encontrado', 'agendamentos encontrados')}</p>
            {groups.map((group) => (
              <section key={group.key} className={page.dayGroup} aria-label={relativeDayLabel(group.key)}>
                <h2 className={page.dayHeading}>
                  <strong>{relativeDayLabel(group.key)}</strong>
                  <span>{plural(group.items.length, 'horário')}</span>
                </h2>
                {group.items.map((item) => (
                  <AppointmentRow key={item.id} item={item} onUpdated={replaceAppointment} />
                ))}
              </section>
            ))}
            {filtered.length > visible && (
              <div className={page.loadMore}>
                <button type="button" className={ui.secondaryButton} onClick={() => setVisible((value) => value + PAGE_STEP)}>
                  Mostrar mais ({filtered.length - visible} restantes)
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}

function AppointmentRow({ item, onUpdated }: { item: Appointment; onUpdated: (updated: Appointment) => void }) {
  return (
    <article className={`${page.apptRow} ${item.status === 'cancelado' ? page.apptCancelled : ''}`}>
      <div className={page.apptTime}>
        <time dateTime={item.data_hora}>{formatClock(item.data_hora)}</time>
        <span>{formatDuration(item.servico_duracao)}</span>
      </div>
      <div className={page.apptMain}>
        <div className={page.apptTitle}>
          <span>{item.cliente_nome}</span>
          <StatusBadge status={item.status} />
        </div>
        <p className={page.apptMeta}>{item.servico_nome} com <strong>{item.barbeiro_nome}</strong></p>
        {item.observacoes && <p className={page.apptNote}>“{item.observacoes}”</p>}
      </div>
      <div className={page.apptAside}>
        <span className={page.apptPrice}>{formatCurrency(item.preco_historico ?? item.servico_preco)}</span>
        <AppointmentActions appointment={item} onUpdated={onUpdated} />
      </div>
    </article>
  )
}
