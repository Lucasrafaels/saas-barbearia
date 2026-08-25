import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const content = {
  cliente: {
    title: 'Seu próximo corte começa aqui.',
    description: 'Consulte serviços, escolha o barbeiro e reserve o melhor horário para você.',
    actions: [
      { to: '/appointments/new', label: 'Agendar horário' },
      { to: '/appointments', label: 'Meus agendamentos' },
    ],
  },
  barbeiro: {
    title: 'Sua agenda, no ritmo do dia.',
    description: 'Veja os atendimentos de hoje e mantenha cada serviço atualizado.',
    actions: [{ to: '/barber/agenda', label: 'Ver agenda de hoje' }],
  },
  admin: {
    title: 'Sua barbearia sob controle.',
    description: 'Cadastre serviços, organize o time de barbeiros e acompanhe os agendamentos.',
    actions: [
      { to: '/admin/services', label: 'Gerenciar serviços' },
      { to: '/admin/appointments', label: 'Ver agendamentos' },
    ],
  },
} as const

export function HomePage() {
  const { user } = useAuth()
  if (!user) return null
  const current = content[user.tipo_perfil]

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>Olá, {user.nome.split(' ')[0]}</p>
        <h1>{current.title}</h1>
        <p>{current.description}</p>
        <div className={styles.actionRow}>
          {current.actions.map((action, index) => (
            <Link key={action.to} className={index === 0 ? ui.button : ui.secondaryButton} to={action.to}>{action.label}</Link>
          ))}
        </div>
      </section>
      <section className={styles.featureGrid}>
        <article className={styles.feature}><span>◷</span><h2>Horários reais</h2><p>A reserva usa a disponibilidade calculada pela agenda e duração do serviço.</p></article>
        <article className={styles.feature}><span>✓</span><h2>Fluxo direto</h2><p>Tudo o que importa fica no mesmo painel, sem etapas desnecessárias.</p></article>
        <article className={styles.feature}><span>⌁</span><h2>Perfil seguro</h2><p>As permissões do painel seguem o papel validado pela API.</p></article>
      </section>
    </div>
  )
}
