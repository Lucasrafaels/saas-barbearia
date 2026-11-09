import type { Appointment, AppointmentStatus } from '../types'
import { formatDateTime, statusLabels } from '../utils/format'
import { StatusBadge } from './StatusBadge'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

interface AppointmentCardProps {
  appointment: Appointment
  showClient?: boolean
  actions?: React.ReactNode
  onStatusChange?: (status: AppointmentStatus) => void
  isUpdating?: boolean
}

export function AppointmentCard({ appointment, showClient = false, actions, onStatusChange, isUpdating }: AppointmentCardProps) {
  return (
    <article className={styles.appointmentCard}>
      <div className={styles.appointmentTime}>{formatDateTime(appointment.data_hora)}</div>
      <div className={styles.appointmentMain}>
        <div className={styles.appointmentTitle}><h2>{appointment.servico_nome}</h2><StatusBadge status={appointment.status} /></div>
        <p>Com <strong>{appointment.barbeiro_nome}</strong>{showClient ? <> · Cliente: <strong>{appointment.cliente_nome}</strong></> : null}</p>
        {appointment.observacoes && <p className={styles.note}>“{appointment.observacoes}”</p>}
      </div>
      {(actions || onStatusChange) && <div className={styles.appointmentActions}>
        {onStatusChange && (
          <label className={ui.statusSelect}>Status
            <select disabled={isUpdating} value={appointment.status} onChange={(event) => onStatusChange(event.target.value as AppointmentStatus)}>
              {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        )}
        {actions}
      </div>}
    </article>
  )
}
