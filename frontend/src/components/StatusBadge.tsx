import type { AppointmentStatus } from '../types'
import { statusLabels } from '../utils/format'
import styles from '../styles/ui.module.css'

const statusClassMap: Record<AppointmentStatus, string> = {
  agendado: 'statusAgendado',
  confirmado: 'statusConfirmado',
  realizado: 'statusRealizado',
  cancelado: 'statusCancelado',
}

export function StatusBadge({ status }: { status: AppointmentStatus }) {
  return <span className={`${styles.status} ${styles[statusClassMap[status]]}`}>{statusLabels[status]}</span>
}
