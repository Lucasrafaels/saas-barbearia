import type { AppointmentStatus } from '../types'
import { statusLabels } from '../utils/format'
import styles from '../styles/ui.module.css'

export function StatusBadge({ status }: { status: AppointmentStatus }) {
  return <span className={`${styles.status} ${styles[`status${status}`]}`}>{statusLabels[status]}</span>
}
