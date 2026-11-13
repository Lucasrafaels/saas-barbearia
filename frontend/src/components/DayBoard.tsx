import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import type { Appointment, Barber } from '../types'
import { useMediaQuery, useNow } from '../hooks/useUi'
import { dateKey, formatClock, minutesOfDay, minutesToClock, statusLabels, todayISO } from '../utils/format'
import { statusOrder } from '../utils/status'
import { Avatar, SegmentedControl } from './Controls'
import styles from '../styles/board.module.css'

interface DayBoardProps {
  day: string
  appointments: Appointment[]
  barbers: Barber[]
  /** Horário de funcionamento em minutos do dia. */
  opens: number
  closes: number
  onSelect: (appointment: Appointment) => void
}

const MINUTE_PX = 1.6
/** No celular a escala é menor: uma coluna só, sem horas vazias empurrando o resto da página. */
const MOBILE_MINUTE_PX = 1.2

const statusClass = {
  agendado: styles.s_agendado,
  confirmado: styles.s_confirmado,
  realizado: styles.s_realizado,
  cancelado: styles.s_cancelado,
}

/**
 * Quadro do dia: uma coluna por barbeiro, blocos posicionados pelo horário e
 * pela duração real do serviço. Cada bloco abre os detalhes e ações.
 */
export function DayBoard({ day, appointments, barbers, opens, closes, onSelect }: DayBoardProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const now = useNow(60_000)
  const isToday = day === todayISO()
  const nowMin = minutesOfDay(now.toISOString())
  // Celular: um barbeiro por vez, em largura total, escolhido no seletor acima do quadro
  const single = useMediaQuery('(max-width: 640px)')
  const [focusId, setFocusId] = useState<number | null>(null)
  const minutePx = single ? MOBILE_MINUTE_PX : MINUTE_PX

  const dayAppointments = useMemo(
    () => appointments.filter((item) => dateKey(item.data_hora) === day),
    [appointments, day],
  )

  // Colunas: barbeiros ativos + quem tiver horário no dia (mesmo se desativado depois)
  const columns = useMemo(() => {
    const ids = new Set(dayAppointments.map((item) => item.barbeiro))
    return barbers
      .filter((barber) => barber.ativo || ids.has(barber.id))
      .map((barber) => ({
        barber,
        items: dayAppointments
          .filter((item) => item.barbeiro === barber.id)
          .sort((a, b) => a.data_hora.localeCompare(b.data_hora)),
      }))
  }, [barbers, dayAppointments])

  // Janela visível: horário de funcionamento, ampliada se houver horários fora dele
  const [start, end] = useMemo(() => {
    let first = opens
    let last = closes
    for (const item of dayAppointments) {
      const begin = minutesOfDay(item.data_hora)
      first = Math.min(first, begin)
      last = Math.max(last, begin + item.servico_duracao)
    }
    return [Math.floor(first / 60) * 60, Math.ceil(last / 60) * 60]
  }, [dayAppointments, opens, closes])

  const hours = useMemo(() => {
    const list: number[] = []
    for (let minute = start; minute < end; minute += 60) list.push(minute)
    return list
  }, [start, end])

  const height = (end - start) * minutePx
  const showNow = isToday && nowMin >= start && nowMin <= end

  // Leva a rolagem para o agora (hoje) ou para o primeiro horário do dia
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return
    const firstItem = dayAppointments.reduce<number | null>((min, item) => {
      const value = minutesOfDay(item.data_hora)
      return min === null || value < min ? value : min
    }, null)
    const focus = showNow ? nowMin - 60 : firstItem !== null ? firstItem - 30 : start
    element.scrollTop = Math.max(0, (focus - start) * minutePx)
  // Só ao trocar de dia: não deve brigar com a rolagem do usuário.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day])

  const focused = single ? columns.find((column) => column.barber.id === focusId) ?? columns[0] : undefined
  const visible = focused ? [focused] : columns
  const showPicker = focused !== undefined && columns.length > 1
  const firstNames = columns.map(({ barber }) => barber.nome.split(' ')[0])
  const emptyText = dayAppointments.length === 0
    ? 'Nenhum agendamento neste dia.'
    : focused && focused.items.length === 0
      ? `Nenhum agendamento de ${focused.barber.nome.split(' ')[0]} neste dia.`
      : null

  const gridStyle = { '--cols': Math.max(visible.length, 1) } as CSSProperties

  return (
    <>
      {showPicker && focused && (
        <div className={styles.picker}>
          <SegmentedControl
            label="Barbeiro exibido no quadro"
            value={String(focused.barber.id)}
            options={columns.map(({ barber, items }, index) => ({
              value: String(barber.id),
              // Primeiro nome; o nome inteiro só quando dois barbeiros dividem o mesmo
              label: firstNames.filter((name) => name === firstNames[index]).length > 1 ? barber.nome : firstNames[index],
              count: items.filter((item) => item.status !== 'cancelado').length,
            }))}
            onChange={(value) => setFocusId(Number(value))}
          />
        </div>
      )}
    <div className={styles.board} ref={scrollRef} style={{ '--minute': `${minutePx}px` } as CSSProperties}>
      <div className={styles.grid} style={gridStyle}>
        {!showPicker && <div className={styles.corner} style={{ gridColumn: 1, gridRow: 1 }} aria-hidden="true" />}
        {!showPicker && visible.map(({ barber, items }, columnIndex) => {
          const active = items.filter((item) => item.status !== 'cancelado').length
          return (
            <div className={styles.colHeader} key={barber.id} style={{ gridColumn: columnIndex + 2, gridRow: 1 }}>
              <Avatar name={barber.nome} size="sm" muted={!barber.ativo} />
              <span className={styles.colName}>
                <strong title={barber.nome}>{barber.nome}</strong>
                <span>{active === 0 ? 'Livre' : active === 1 ? '1 horário' : `${active} horários`}</span>
              </span>
            </div>
          )
        })}

        <div className={styles.gutter} style={{ height, gridColumn: 1, gridRow: 2 }} aria-hidden="true">
          {hours.map((minute) => (
            <span key={minute} className={styles.hourLabel} style={{ top: (minute - start) * minutePx }}>
              {minutesToClock(minute)}
            </span>
          ))}
          {showNow && <span className={styles.nowLabel} style={{ top: (nowMin - start) * minutePx }}>{minutesToClock(nowMin)}</span>}
        </div>

        {visible.map(({ barber, items }, columnIndex) => (
          <div
            className={styles.column}
            key={barber.id}
            style={{ height, gridColumn: columnIndex + 2, gridRow: 2 }}
            role="list"
            aria-label={`Agenda de ${barber.nome}`}
          >
            {opens > start && <div className={styles.closed} style={{ top: 0, height: (opens - start) * minutePx }} />}
            {closes < end && <div className={styles.closed} style={{ top: (closes - start) * minutePx, bottom: 0 }} />}
            {items.map((item, index) => {
              const begin = minutesOfDay(item.data_hora)
              const top = (begin - start) * minutePx
              const blockHeight = Math.max(item.servico_duracao * minutePx - 3, 16)
              // Blocos curtos: uma linha (horário + cliente); médios escondem o serviço
              // Abaixo de 40px não cabem duas linhas: horário e cliente vão lado a lado
              const tiny = blockHeight < 40
              const compact = !tiny && blockHeight < 60
              const finish = minutesToClock(begin + item.servico_duracao)
              return (
                <div role="listitem" key={item.id}>
                  <button
                    type="button"
                    className={`${styles.block} ${statusClass[item.status]} ${tiny ? styles.blockTiny : ''} ${compact ? styles.blockCompact : ''}`}
                    style={{ top: top + 1, height: blockHeight, '--delay': `${Math.min(columnIndex * 40 + index * 25, 400)}ms` } as CSSProperties}
                    onClick={() => onSelect(item)}
                    aria-label={`${formatClock(item.data_hora)} a ${finish}, ${item.cliente_nome}, ${item.servico_nome}, ${statusLabels[item.status]}`}
                  >
                    <span className={styles.blockTime}>{formatClock(item.data_hora)}</span>
                    <span className={styles.blockClient}>{item.cliente_nome}</span>
                    <span className={styles.blockService}>{item.servico_nome}</span>
                  </button>
                </div>
              )
            })}
          </div>
        ))}

        <div className={styles.overlayLayer} style={{ gridColumn: '2 / -1', gridRow: 2, height }} aria-hidden={emptyText ? undefined : true}>
          {showNow && <div className={styles.nowLine} style={{ top: (nowMin - start) * minutePx }} />}
          {emptyText && <div className={styles.emptyOverlay}><p>{emptyText}</p></div>}
        </div>
      </div>
    </div>
    </>
  )
}

export function BoardLegend() {
  return (
    <div className={styles.legend} aria-label="Legenda de status">
      {statusOrder.map((status) => (
        <span className={styles.legendItem} key={status}>
          <span className={`${styles.legendSwatch} ${statusClass[status]}`} aria-hidden="true" />
          {statusLabels[status]}
        </span>
      ))}
    </div>
  )
}
