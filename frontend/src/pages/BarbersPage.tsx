import { barberApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { useAsyncData } from '../hooks/useAsyncData'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

export function BarbersPage() {
  const { data, isLoading, error } = useAsyncData(() => barberApi.list().then((response) => response.data), [])
  if (isLoading) return <PageLoader label="Buscando barbeiros..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar os barbeiros agora.</p>
  const barbers = (data?.results ?? []).filter((barber) => barber.ativo)

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div><p className={styles.eyebrow}>Profissionais</p><h1>Barbeiros</h1></div>
        <p>Escolha quem vai cuidar do seu próximo atendimento.</p>
      </header>
      {barbers.length === 0 ? <EmptyState title="Nenhum barbeiro disponível" description="A equipe ainda não possui barbeiros ativos." /> : (
        <section className={styles.cardGrid}>
          {barbers.map((barber) => (
            <article className={styles.barberCard} key={barber.id}>
              <div className={styles.avatar}>{barber.nome.charAt(0).toUpperCase()}</div>
              <h2>{barber.nome}</h2>
              <p>{barber.especialidade || 'Barbeiro profissional'}</p>
              <small>{barber.email}</small>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}
