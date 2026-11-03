import { useEffect, useState } from 'react'
import { serviceApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
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

  useEffect(() => {
    let active = true
    setIsLoading(true)
    serviceApi.list(true)
      .then((response) => {
        if (active) setServices(response.data.results)
      })
      .catch(() => {
        if (active) setError('Não foi possível carregar os serviços.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => { active = false }
  }, [])

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
            <div className={styles.serviceIcon} aria-hidden="true">✂</div>
            <div>
              <h2>{service.nome}</h2>
              {service.descricao && <p>{service.descricao}</p>}
            </div>
            <footer>
              <span>{service.duracao} min</span>
              <strong>{formatCurrency(service.preco)}</strong>
            </footer>
          </article>
        ))}
      </div>
    </div>
  )
}