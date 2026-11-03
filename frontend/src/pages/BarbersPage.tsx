import { useEffect, useState } from 'react'
import { barberApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import styles from '../styles/page.module.css'

interface Barber {
  id: number
  nome: string
  especialidade: string | null
  ativo: boolean
}

export function BarbersPage() {
  const [barbers, setBarbers] = useState<Barber[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setIsLoading(true)
    barberApi.list()
      .then((response) => {
        if (active) {
          setBarbers(response.data.results.filter((barber) => barber.ativo))
        }
      })
      .catch(() => {
        if (active) setError('Não foi possível carregar os barbeiros.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => { active = false }
  }, [])

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  if (isLoading) return <PageLoader label="Carregando barbeiros..." />

  if (error) {
    return (
      <div className={`${styles.page} ${styles.narrowPage}`}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.eyebrow}>Nossa Equipe</p>
            <h1>Barbeiros disponíveis</h1>
          </div>
        </header>
        <p className={styles.errorBox}>{error}</p>
      </div>
    )
  }

  if (!barbers.length) {
    return (
      <div className={`${styles.page} ${styles.narrowPage}`}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.eyebrow}>Nossa Equipe</p>
            <h1>Barbeiros disponíveis</h1>
          </div>
        </header>
        <EmptyState
          title="Nenhum barbeiro disponível"
          description="No momento não há barbeiros ativos. Volte em breve!"
        />
      </div>
    )
  }

  return (
    <div className={`${styles.page} ${styles.narrowPage}`}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Nossa Equipe</p>
          <h1>Conheça nossos barbeiros</h1>
        </div>
        <p>Profissionais especializados prontos para te atender</p>
      </header>

      <div className={styles.cardGrid}>
        {barbers.map((barber) => (
          <article
            key={barber.id}
            className={styles.barberCard}
          >
            <div className={styles.serviceIcon} aria-hidden="true">{getInitials(barber.nome)}</div>
            <h2>{barber.nome}</h2>
            {barber.especialidade && <p>{barber.especialidade}</p>}
            <small>Barbeiro ativo</small>
          </article>
        ))}
      </div>
    </div>
  )
}