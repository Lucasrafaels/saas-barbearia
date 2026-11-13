import { Link } from 'react-router-dom'
import { listActiveBarbers } from '../api/endpoints'
import { Avatar } from '../components/Controls'
import { EmptyState, ErrorState, SkeletonBlock } from '../components/Feedback'

import { PageHeader } from '../components/PageHeader'
import { useAsyncData } from '../hooks/useAsyncData'
import { firstName } from '../utils/format'
import client from '../styles/client.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

/** Equipe da barbearia, com atalho para agendar com cada profissional. */
export function BarbersPage() {
  const { data, isLoading, error, reload } = useAsyncData(listActiveBarbers, [])
  const barbers = [...(data ?? [])].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))

  return (
    <div className={page.page}>
      <PageHeader title="Equipe" description="Escolha com quem você prefere ser atendido." />

      {isLoading ? (
        <div className={client.teamGrid}>{[0, 1, 2].map((key) => <SkeletonBlock key={key} height={190} />)}</div>
      ) : error && !data ? (
        <div className={ui.panel}><ErrorState error={error} fallback="Não foi possível carregar a equipe." onRetry={() => void reload()} /></div>
      ) : barbers.length === 0 ? (
        <div className={ui.panel}><EmptyState art="navalha" title="Nenhum barbeiro disponível" description="A barbearia ainda não tem profissionais recebendo agendamentos." /></div>
      ) : (
        <ul className={client.teamGrid}>
          {barbers.map((barber) => (
            <li key={barber.id} className={client.teamCard}>
              <Avatar name={barber.nome} size="lg" />
              <div>
                <h2>{barber.nome}</h2>
                <p>{barber.especialidade || 'Barbeiro'}</p>
              </div>
              <Link to={`/appointments/new?barbeiro=${barber.id}`} className={`${ui.secondaryButton} ${ui.sm}`}>
                Agendar com {firstName(barber.nome)}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
