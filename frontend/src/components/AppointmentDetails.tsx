import type { Appointment } from '../types'
import { dateKey, formatClock, formatCurrency, formatDayLong, formatDuration, minutesOfDay, minutesToClock } from '../utils/format'
import { AppointmentActions } from './AppointmentActions'
import { StatusBadge } from './Controls'
import { Modal } from './Modal'
import ui from '../styles/ui.module.css'

interface AppointmentDetailsProps {
  appointment: Appointment | null
  onClose: () => void
  onUpdated: (updated: Appointment) => void
}

/** Detalhes de um agendamento com as ações de status permitidas. */
export function AppointmentDetails({ appointment, onClose, onUpdated }: AppointmentDetailsProps) {
  const item = appointment
  const end = item ? minutesToClock(minutesOfDay(item.data_hora) + item.servico_duracao) : ''
  const price = item ? item.preco_historico ?? item.servico_preco : 0

  return (
    <Modal
      open={item !== null}
      onClose={onClose}
      title={item ? `${item.servico_nome}` : ''}
      description={item ? <>{formatDayLong(dateKey(item.data_hora))}, {formatClock(item.data_hora)} às {end}</> : null}
      footer={item && <AppointmentActions appointment={item} onUpdated={(updated) => { onUpdated(updated); onClose() }} size="md" />}
    >
      {item && (
        <dl className={ui.summaryList}>
          <div className={ui.summaryItem}><dt>Status</dt><dd><StatusBadge status={item.status} /></dd></div>
          <div className={ui.summaryItem}><dt>Cliente</dt><dd>{item.cliente_nome}</dd></div>
          <div className={ui.summaryItem}><dt>Barbeiro</dt><dd>{item.barbeiro_nome}</dd></div>
          <div className={ui.summaryItem}><dt>Duração</dt><dd>{formatDuration(item.servico_duracao)}</dd></div>
          <div className={ui.summaryItem}><dt>Valor</dt><dd>{formatCurrency(price)}</dd></div>
          {item.observacoes && <div className={ui.summaryItem}><dt>Observações</dt><dd style={{ fontWeight: 400 }}>{item.observacoes}</dd></div>}
        </dl>
      )}
    </Modal>
  )
}
