import styles from '../styles/ui.module.css'

interface PaginationProps {
  page: number
  count: number
  pageSize?: number
  onChange: (page: number) => void
}

export function Pagination({ page, count, pageSize = 20, onChange }: PaginationProps) {
  const totalPages = Math.ceil(count / pageSize)
  if (totalPages <= 1) return null

  return (
    <nav className={styles.pagination} aria-label="Paginação">
      <button className={styles.secondaryButton} disabled={page <= 1} onClick={() => onChange(page - 1)}>Anterior</button>
      <span>Página {page} de {totalPages}</span>
      <button className={styles.secondaryButton} disabled={page >= totalPages} onClick={() => onChange(page + 1)}>Próxima</button>
    </nav>
  )
}
