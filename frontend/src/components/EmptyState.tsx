import { Link } from 'react-router-dom'
import styles from '../styles/ui.module.css'

interface EmptyStateProps {
  title: string
  description: string
  action?: { to: string; label: string }
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className={styles.emptyState}>
      <p className={styles.emptyIcon} aria-hidden="true">✦</p>
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <Link className={styles.button} to={action.to}>{action.label}</Link>}
    </section>
  )
}
