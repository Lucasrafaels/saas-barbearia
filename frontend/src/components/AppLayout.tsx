import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import styles from '../styles/layout.module.css'

interface MenuItem {
  to: string
  label: string
  icon: React.ReactNode
  end?: boolean
  roles?: string[]
}

const menuByRole: Record<string, MenuItem[]> = {
  cliente: [
    { to: '/', label: 'Início', icon: <HomeIcon />, end: true, roles: ['cliente'] },
    { to: '/services', label: 'Serviços', icon: <ScissorsIcon />, roles: ['cliente'] },
    { to: '/barbers', label: 'Barbeiros', icon: <UsersIcon />, roles: ['cliente'] },
    { to: '/appointments/new', label: 'Agendar', icon: <CalendarIcon />, roles: ['cliente'] },
    { to: '/appointments', label: 'Meus horários', icon: <ClockIcon />, roles: ['cliente'] },
  ],
  barbeiro: [
    { to: '/', label: 'Início', icon: <HomeIcon />, end: true, roles: ['barbeiro'] },
    { to: '/barber/agenda', label: 'Agenda de hoje', icon: <CalendarIcon />, roles: ['barbeiro'] },
  ],
  admin: [
    { to: '/admin', label: 'Dashboard', icon: <DashboardIcon />, end: true, roles: ['admin'] },
    { to: '/admin/services', label: 'Serviços', icon: <ScissorsIcon />, roles: ['admin'] },
    { to: '/admin/barbers', label: 'Barbeiros', icon: <UsersIcon />, roles: ['admin'] },
    { to: '/admin/appointments', label: 'Agendamentos', icon: <CalendarIcon />, roles: ['admin'] },
  ],
}

function HomeIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  )
}

function ScissorsIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="5.5" cy="5.5" r="2.5" />
      <circle cx="18.5" cy="5.5" r="2.5" />
      <line x1="5.5" y1="8.5" x2="10" y2="14" />
      <line x1="18.5" y1="8.5" x2="14" y2="14" />
      <line x1="10" y1="14" x2="14" y2="14" />
    </svg>
  )
}

function UsersIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function CalendarIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function DashboardIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  )
}

function ClockIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  )
}

function ChevronLeftIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function ChevronRightIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function MenuIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  )
}

function UserIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

function LogoutIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  )
}

function SettingsIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024)
      if (window.innerWidth >= 1024) {
        setIsMobileMenuOpen(false)
      }
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  if (!user) return null

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  const userMenuItems = menuByRole[user.tipo_perfil] || []

  const getPageTitle = () => {
    const currentItem = userMenuItems.find(item => {
      if (item.end) return location.pathname === item.to
      return location.pathname.startsWith(item.to)
    })
    return currentItem?.label || 'BarberPro'
  }

  const getPageDescription = () => {
    const descriptions: Record<string, string> = {
      '/': 'Visão geral do seu painel',
      '/services': 'Gerencie os serviços disponíveis',
      '/barbers': 'Visualize os barbeiros disponíveis',
      '/appointments/new': 'Agende um novo horário',
      '/appointments': 'Acompanhe seus agendamentos',
      '/barber/agenda': 'Gerencie sua agenda de hoje',
      '/admin': 'Visão geral da barbearia',
      '/admin/services': 'Administre os serviços da barbearia',
      '/admin/barbers': 'Gerencie a equipe de barbeiros',
      '/admin/appointments': 'Visualize todos os agendamentos',
      '/password/change': 'Altere sua senha de acesso',
    }
    return descriptions[location.pathname] || ''
  }

  const toggleSidebar = () => {
    if (isMobile) {
      setIsMobileMenuOpen(!isMobileMenuOpen)
    } else {
      setIsSidebarCollapsed(!isSidebarCollapsed)
    }
  }

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false)
  }

  return (
    <>
      {isMobile && isMobileMenuOpen && (
        <div className={styles.overlay} onClick={closeMobileMenu} aria-hidden="true" />
      )}
      <aside
        className={`${styles.sidebar} ${isSidebarCollapsed ? styles.collapsed : ''} ${isMobile && isMobileMenuOpen ? styles.mobileOpen : ''}`}
        aria-label="Menu principal"
      >
        <div className={styles.sidebarHeader}>
          <NavLink to="/" className={styles.brand} aria-label="BarberPro - Início">
            <span className={styles.brandMark} aria-hidden="true">B</span>
            <span className={isSidebarCollapsed ? styles.brandTextHidden : styles.brandText}>BarberPro</span>
          </NavLink>
          {!isMobile && (
            <button
              className={styles.collapseToggle}
              onClick={toggleSidebar}
              aria-label={isSidebarCollapsed ? 'Expandir menu' : 'Recolher menu'}
              aria-expanded={!isSidebarCollapsed}
            >
              {isSidebarCollapsed ? <ChevronRightIcon size={18} /> : <ChevronLeftIcon size={18} />}
            </button>
          )}
        </div>

        <nav className={styles.nav} aria-label="Navegação principal">
          {userMenuItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.navLinkActive : ''} ${isSidebarCollapsed ? styles.navLinkCollapsed : ''}`
              }
              onClick={closeMobileMenu}
            >
              <span className={styles.navIcon} aria-hidden="true">{item.icon}</span>
              {!isSidebarCollapsed && <span className={styles.navLabel}>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={isSidebarCollapsed ? styles.userInfoCollapsed : styles.userInfo}>
            <div className={styles.userAvatar} aria-hidden="true">
              <UserIcon size={24} />
            </div>
            {!isSidebarCollapsed && (
              <div className={styles.userDetails}>
                <strong className={styles.userName}>{user.nome}</strong>
                <span className={styles.userRole}>{user.tipo_perfil}</span>
              </div>
            )}
          </div>
          {!isSidebarCollapsed && (
            <div className={styles.userActions}>
              <NavLink
                to="/password/change"
                className={styles.userAction}
                onClick={closeMobileMenu}
              >
                <SettingsIcon size={18} />
                <span>Alterar Senha</span>
              </NavLink>
              <button className={styles.logout} onClick={handleLogout}>
                <LogoutIcon size={18} />
                <span>Sair</span>
              </button>
            </div>
          )}
          {isSidebarCollapsed && (
            <div className={styles.collapsedActions}>
              <NavLink
                to="/password/change"
                className={styles.collapsedAction}
                onClick={closeMobileMenu}
                title="Alterar Senha"
              >
                <SettingsIcon size={20} />
              </NavLink>
              <button
                className={styles.collapsedAction}
                onClick={handleLogout}
                title="Sair"
              >
                <LogoutIcon size={20} />
              </button>
            </div>
          )}
        </div>
      </aside>

      <div className={styles.mainWrapper}>
        <header className={styles.header}>
          <button
            className={styles.mobileMenuToggle}
            onClick={toggleSidebar}
            aria-label="Abrir menu"
            aria-expanded={isMobileMenuOpen}
            aria-controls="sidebar"
          >
            <MenuIcon />
          </button>
          <div className={styles.headerContent}>
            <div className={styles.pageTitle}>
              <h1>{getPageTitle()}</h1>
              {getPageDescription() && <p>{getPageDescription()}</p>}
            </div>
            <div className={styles.headerActions}>
              <div className={styles.headerUser}>
                <div className={styles.userAvatar} aria-hidden="true">
                  <UserIcon size={28} />
                </div>
                <div className={styles.userInfo}>
                  <strong>{user.nome.split(' ')[0]}</strong>
                  <span>{user.tipo_perfil}</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className={styles.main} id="main-content" role="main" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </>
  )
}