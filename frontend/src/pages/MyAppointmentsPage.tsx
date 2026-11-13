import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { appointmentApi, listAllAppointments } from '../api/endpoints'
import { ButtonSpinner, SegmentedControl, StatusBadge } from '../components/Controls'
import { EmptyState, ErrorState, RefreshBar, SkeletonRows } from '../components/Feedback'
import { CalendarPlusIcon, HistoryIcon, XIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useConfirm } from '../contexts/ConfirmContext'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Appointment } from '../types'
import { dateKey, errorMessage, formatClock, formatCurrency, formatDayLong, formatDuration, plural, relativeDayLabel } from '../utils/format'
import { isOpenStatus } from '../utils/status'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

type Tab = 'upcoming' | 'history'

export function MyAppointmentsPage() {
  const { showToast } = useToast()
  const confirm = useConfirm()
  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(listAllAppointments, [])
  const [tab, setTab] = useState<Tab>('upcoming')
  const [cancellingId, setCancellingId] = useState<number | null>(null)

  const { upcoming, history } = useMemo(() => {
    const now = Date.now()
    const list = data ?? []
    const isUpcoming = (item: Appointment) => isOpenStatus(item.status) && new Date(item.data_hora).getTime() >= now
    return {
      upcoming: list.filter(isUpcoming).sort((a, b) => a.data_hora.localeCompare(b.data_hora)),
      history: list.filter((item) => !isUpcoming(item)).sort((a, b) => b.data_hora.localeCompare(a.data_hora)),
    }
  }, [data])

  const cancel = async (item: Appointment) => {
    const ok = await confirm({
      title: 'Cancelar este horário?',
      description: `${item.servico_nome} com ${item.barbeiro_nome}, ${formatDayLong(dateKey(item.data_hora))} às ${formatClock(item.data_hora)}. O horário fica livre para outros clientes.`,
      confirmLabel: 'Cancelar horário',
      cancelLabel: 'Manter',
      tone: 'danger',
    })
    if (!ok) return
    setCancellingId(item.id)
    try {
      const { data: updated } = await appointmentApi.update(item.id, { status: 'cancelado' })
      setData((current) => current?.map((entry) => (entry.id === updated.id ? updated : entry)) ?? null)
      showToast('Horário cancelado.', 'success')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível cancelar o horário.'), 'error')
    } finally {
      setCancellingId(null)
    }
  }

  const list = tab === 'upcoming' ? upcoming : history

  return (
    <div className={`${page.page} ${page.medium}`}>
      <PageHeader
        title="Meus agendamentos"
        description="Reagende ou cancele horários marcados e consulte seu histórico."
        actions={<Link to="/appointments/new" className={ui.button}><CalendarPlusIcon size={18} /> Agendar horário</Link>}
      />

      <section className={ui.panel}>
        <div className={ui.toolbar}>
          <SegmentedControl
            label="Mostrar"
            value={tab}
            onChange={setTab}
            options={[
              { value: 'upcoming', label: 'Próximos', count: upcoming.length },
              { value: 'history', label: 'Histórico', count: history.length },
            ]}
          />
        </div>
        <RefreshBar active={isRefreshing} />

        {isLoading ? (
          <SkeletonRows rows={4} label="Carregando seus agendamentos" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar seus agendamentos." onRetry={() => void reload()} />
        ) : list.length === 0 ? (
          tab === 'upcoming' ? (
            <EmptyState
              art="navalha"
              title="Nenhum horário marcado"
              description="Escolha o serviço, o barbeiro e um horário livre em poucos passos."
              action={{ label: 'Agendar horário', to: '/appointments/new' }}
            />
          ) : (
            <EmptyState icon={<HistoryIcon size={22} />} title="Sem histórico ainda" description="Atendimentos realizados e cancelados aparecem aqui." />
          )
        ) : (
          <div>
            <p className="sr-only" aria-live="polite">{plural(list.length, 'agendamento')}</p>
            {list.map((item) => {
              const canChange = isOpenStatus(item.status) && new Date(item.data_hora).getTime() >= Date.now()
              return (
                <article key={item.id} className={`${page.apptRow} ${item.status === 'cancelado' ? page.apptCancelled : ''}`}>
                  <div className={page.apptTime}>
                    <time dateTime={item.data_hora}>{formatClock(item.data_hora)}</time>
                    <span>{formatDuration(item.servico_duracao)}</span>
                  </div>
                  <div className={page.apptMain}>
                    <div className={page.apptTitle}>
                      <span>{item.servico_nome}</span>
                      <StatusBadge status={item.status} />
                    </div>
                    <p className={page.apptMeta}>
                      <strong>{relativeDayLabel(dateKey(item.data_hora))}</strong> com {item.barbeiro_nome}
                      {item.barbeiro_especialidade ? `, ${item.barbeiro_especialidade.toLowerCase()}` : ''}
                    </p>
                    {item.observacoes && <p className={page.apptNote}>“{item.observacoes}”</p>}
                  </div>
                  <div className={page.apptAside}>
                    <span className={page.apptPrice}>{formatCurrency(item.preco_historico ?? item.servico_preco)}</span>
                    {canChange && (
                      <div className={ui.cellActions}>
                        <Link to={`/appointments/new?reschedule=${item.id}`} className={`${ui.secondaryButton} ${ui.sm}`}>Reagendar</Link>
                        <button
                          type="button"
                          className={`${ui.ghostButton} ${ui.ghostDanger} ${ui.sm}`}
                          onClick={() => void cancel(item)}
                          disabled={cancellingId === item.id}
                        >
                          {cancellingId === item.id ? <ButtonSpinner /> : <XIcon size={16} />} Cancelar
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
