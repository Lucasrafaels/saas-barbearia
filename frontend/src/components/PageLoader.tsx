import styles from '../styles/ui.module.css'

export function PageLoader({ label = 'Carregando...' }: { label?: string }) {
  return (
    <div className={styles.loaderWrap} role="status" aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}
