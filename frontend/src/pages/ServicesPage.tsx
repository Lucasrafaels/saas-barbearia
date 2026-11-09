import { useEffect, useState } from 'react'
import { serviceApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { Pagination } from '../components/Pagination'
import { ScissorsIcon, ClockIcon } from '../components/Icons'
import { formatCurrency } from '../utils/format'
import styles from '../styles/page.module.css'

interface Service {
  id: number
  nome: string
  descricao: string
  preco: string
  duracao: number
}

export function ServicesPage() {
  const [services, setServices] = useState<Service[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    let active = true
    setIsLoading(true)
    serviceApi.list({ ativo: 'true', page })
      .then((response) => {
        if (active) {
          setServices(response.data.results)
          setTotalCount(response.data.count)
        }
      })
      .catch(() => {
        if (active) setError('Não foi possível carregar os serviços.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => { active = false }
  }, [page])

  if (isLoading) return <PageLoader label="Carregando serviços..." />

  if (error) {
    return (
      <div className={`${styles.page} ${styles.narrowPage}`}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.eyebrow}>Nossos Serviços</p>
            <h1>Serviços disponíveis</h1>
          </div>
        </header>
        <p className={styles.errorBox}>{error}</p>
      </div>
    )
  }

  if (!services.length) {
    return (
      <div className={`${styles.page} ${styles.narrowPage}`}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.eyebrow}>Nossos Serviços</p>
            <h1>Serviços disponíveis</h1>
          </div>
        </header>
        <EmptyState
          title="Nenhum serviço disponível"
          description="No momento não há serviços cadastrados. Volte em breve!"
        />
      </div>
    )
  }

  return (
    <div className={`${styles.page} ${styles.narrowPage}`}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Nossos Serviços</p>
          <h1>Escolha o serviço ideal</h1>
        </div>
        <p>Selecione um serviço para ver detalhes e agendar</p>
      </header>

      <div className={styles.cardGrid}>
        {services.map((service) => (
          <article
            key={service.id}
            className={styles.serviceCard}
          >
            <div className={styles.serviceIcon} aria-hidden="true"><ScissorsIcon size={30} /></div>
            <div>
              <h2>{service.nome}</h2>
              {service.descricao && <p>{service.descricao}</p>}
            </div>
            <footer>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}><ClockIcon size={16} /> {service.duracao} min</span>
              </div>
              <strong>{formatCurrency(service.preco)}</strong>
            </footer>
          </article>
        ))}
      </div>

      <Pagination page={page} count={totalCount} onChange={setPage} />
    </div>
  )
}
