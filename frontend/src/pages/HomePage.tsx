import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { CalendarIcon, ScissorsIcon, ClockIcon, CheckCircleIcon } from '../components/Icons'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const content = {
  cliente: {
    eyebrow: 'Área do cliente',
    title: 'Organize seu próximo horário.',
    description: 'Escolha o serviço, o profissional e um horário disponível em poucos passos.',
    actions: [
      { to: '/appointments/new', label: 'Agendar horário' },
      { to: '/appointments', label: 'Meus agendamentos' },
    ],
    features: [
      { icon: 'calendar', title: 'Agendamento guiado', description: 'Escolha serviço, barbeiro, data e horário.' },
      { icon: 'scissors', title: 'Serviços disponíveis', description: 'Consulte duração e valor antes de confirmar.' },
      { icon: 'clock', title: 'Próximos horários', description: 'Acompanhe ou reagende seus atendimentos.' },
    ],
  },
  barbeiro: {
    eyebrow: 'Área do barbeiro',
    title: 'Sua agenda de trabalho, organizada.',
    description: 'Veja os atendimentos do dia e mantenha o status de cada serviço atualizado.',
    actions: [{ to: '/barber/agenda', label: 'Ver agenda de hoje' }],
    features: [
      { icon: 'calendar', title: 'Agenda do dia', description: 'Consulte seus horários em uma única visualização.' },
      { icon: 'clock', title: 'Ordem de atendimento', description: 'Confira data, hora e detalhes antes do serviço.' },
      { icon: 'check', title: 'Status atualizado', description: 'Registre o andamento direto na agenda.' },
    ],
  },
  admin: {
    eyebrow: 'Painel administrativo',
    title: 'Gestão da barbearia em um só lugar.',
    description: 'Acompanhe a operação, mantenha o catálogo atualizado e organize sua equipe.',
    actions: [
      { to: '/admin/services', label: 'Gerenciar serviços' },
      { to: '/admin/appointments', label: 'Ver agendamentos' },
    ],
    features: [
      { icon: 'calendar', title: 'Agenda geral', description: 'Visualize agendamentos e acompanhe seus status.' },
      { icon: 'scissors', title: 'Catálogo de serviços', description: 'Cadastre e mantenha os serviços atualizados.' },
      { icon: 'check', title: 'Equipe organizada', description: 'Gerencie os profissionais da sua barbearia.' },
    ],
  },
} as const

export function HomePage() {
  const { user } = useAuth()
  if (!user) return null
  const current = content[user.tipo_perfil]
  const featureIcons = { calendar: CalendarIcon, scissors: ScissorsIcon, clock: ClockIcon, check: CheckCircleIcon }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>{current.eyebrow} · Olá, {user.nome.split(' ')[0]}</p>
        <h1>{current.title}</h1>
        <p>{current.description}</p>
        <div className={styles.actionRow}>
          {current.actions.map((action, index) => (
            <Link key={action.to} className={index === 0 ? ui.button : ui.secondaryButton} to={action.to}>{action.label}</Link>
          ))}
        </div>
      </section>
      <section className={styles.featureGrid}>
        {current.features.map((feature, index) => {
          const Icon = featureIcons[feature.icon]
          const tone = index === 1 ? styles.navy : index === 2 ? styles.success : ''
          return <article className={styles.feature} key={feature.title}>
            <div className={`${styles.featureIcon} ${tone}`} aria-hidden="true"><Icon size={28} /></div>
            <h2>{feature.title}</h2>
            <p>{feature.description}</p>
          </article>
        })}
      </section>
    </div>
  )
}
