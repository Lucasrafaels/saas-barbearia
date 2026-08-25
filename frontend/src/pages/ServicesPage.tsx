import { useAsyncData } from '../hooks/useAsyncData'
import { serviceApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { formatCurrency } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

export function ServicesPage() {
  const { data, isLoading, error } = useAsyncData(() => serviceApi.list(true).then((response) => response.data), [])
  if (isLoading) return <PageLoader label="Buscando serviços..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar os serviços agora.</p>
  const services = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div><p className={styles.eyebrow}>Escolha seu estilo</p><h1>Serviços</h1></div>
        <p>Selecione um serviço antes de escolher seu horário.</p>
      </header>
      {services.length === 0 ? <EmptyState title="Nenhum serviço disponível" description="Esta barbearia ainda não publicou serviços." /> : (
        <section className={styles.cardGrid}>
          {services.map((service) => (
            <article className={styles.serviceCard} key={service.id}>
              <div className={styles.serviceIcon}>✂</div>
              <div><h2>{service.nome}</h2><p>{service.descricao || 'Sem descrição adicional.'}</p></div>
              <footer><strong>{formatCurrency(service.preco)}</strong><span>{service.duracao} min</span></footer>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}
