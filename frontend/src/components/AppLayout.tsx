import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from '../styles/layout.module.css'

interface MenuItem {
  to: string
  label: string
  end?: boolean
}

const menuByRole: Record<string, MenuItem[]> = {
  cliente: [
    { to: '/', label: 'Início', end: true },
    { to: '/services', label: 'Serviços' },
    { to: '/barbers', label: 'Barbeiros' },
    { to: '/appointments/new', label: 'Agendar' },
    { to: '/appointments', label: 'Meus horários' },
  ],
  barbeiro: [
    { to: '/', label: 'Início', end: true },
    { to: '/barber/agenda', label: 'Agenda de hoje' },
  ],
  admin: [
    { to: '/', label: 'Início', end: true },
    { to: '/admin/services', label: 'Serviços' },
    { to: '/admin/barbers', label: 'Barbeiros' },
    { to: '/admin/appointments', label: 'Agendamentos' },
  ],
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <NavLink to="/" className={styles.brand}>
          <span aria-hidden="true">✂</span> Corte Certo
        </NavLink>
        <div className={styles.userArea}>
          <div>
            <strong>{user.nome}</strong>
            <span>{user.tipo_perfil}</span>
          </div>
          <button className={styles.logout} onClick={handleLogout}>Sair</button>
        </div>
      </header>
      <nav className={styles.nav} aria-label="Navegação principal">
        {menuByRole[user.tipo_perfil].map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className={styles.main}><Outlet /></main>
    </div>
  )
}
