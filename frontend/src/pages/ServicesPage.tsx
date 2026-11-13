import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { listActiveServices } from '../api/endpoints'
import { SearchField } from '../components/Controls'
import { EmptyState, ErrorState, SkeletonRows } from '../components/Feedback'
import { ClockIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useAsyncData } from '../hooks/useAsyncData'
import { formatCurrency, formatDuration, matchesSearch } from '../utils/format'
import client from '../styles/client.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

type SortKey = 'nome' | 'menor' | 'maior' | 'duracao'

const sortLabels: Record<SortKey, string> = {
  nome: 'Nome',
  menor: 'Menor preço',
  maior: 'Maior preço',
  duracao: 'Duração',
}

/** Tabela de preços do cliente, com atalho para agendar cada serviço. */
export function ServicesPage() {
  const { data, isLoading, error, reload } = useAsyncData(listActiveServices, [])
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<SortKey>('nome')

  const services = useMemo(() => {
    const list = (data ?? []).filter((item) => matchesSearch(query, item.nome, item.descricao))
    return list.sort((a, b) => {
      if (sort === 'menor') return Number(a.preco) - Number(b.preco)
      if (sort === 'maior') return Number(b.preco) - Number(a.preco)
      if (sort === 'duracao') return a.duracao - b.duracao
      return a.nome.localeCompare(b.nome, 'pt-BR')
    })
  }, [data, query, sort])

  return (
    <div className={`${page.page} ${page.medium}`}>
      <PageHeader title="Serviços e preços" description="Valores praticados pela barbearia. Escolha um serviço para ver os horários livres." />

      <section className={`${ui.panel} ${client.priceBoard}`}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGrow}>
            <SearchField value={query} onChange={setQuery} placeholder="Buscar serviço" />
          </div>
          <label className={ui.toolbarField}>
            <span>Ordenar por</span>
            <select value={sort} onChange={(event) => setSort(event.target.value as SortKey)}>
              {(Object.keys(sortLabels) as SortKey[]).map((key) => <option key={key} value={key}>{sortLabels[key]}</option>)}
            </select>
          </label>
        </div>

        {isLoading ? (
          <SkeletonRows rows={5} label="Carregando serviços" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar os serviços." onRetry={() => void reload()} />
        ) : !data?.length ? (
          <EmptyState art="tesoura" title="Nenhum serviço disponível" description="A barbearia ainda não publicou serviços para agendamento." />
        ) : services.length === 0 ? (
          <EmptyState compact title="Nenhum serviço encontrado" description={`Nada corresponde a “${query}”.`} action={{ label: 'Limpar busca', onClick: () => setQuery('') }} />
        ) : (
          <ul className={client.priceList}>
            {services.map((service) => (
              <li key={service.id} className={client.priceRow}>
                <div style={{ minWidth: 0 }}>
                  <div className={client.priceHead}>
                    <span className={client.priceName}>{service.nome}</span>
                    <span className={client.priceLeader} aria-hidden="true" />
                    <span className={client.priceValue}>{formatCurrency(service.preco)}</span>
                  </div>
                  {service.descricao && <p className={client.priceDesc}>{service.descricao}</p>}
                  <span className={client.priceMeta}><ClockIcon size={14} /> {formatDuration(service.duracao)}</span>
                </div>
                <Link to={`/appointments/new?servico=${service.id}`} className={`${ui.secondaryButton} ${ui.sm}`} aria-label={`Agendar ${service.nome}`}>
                  Agendar
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
