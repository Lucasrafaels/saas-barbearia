import { Suspense, useCallback, useEffect, useRef, useState, type ComponentType } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { appointmentApi } from '../api/endpoints'
import { roleLabels, useAuth } from '../contexts/AuthContext'
import { BarbershopProvider, useBarbershop } from '../contexts/BarbershopContext'
import { useMediaQuery, useNow } from '../hooks/useUi'
import type { User, UserRole } from '../types'
import { formatDayLong, todayISO } from '../utils/format'
import { activeTab, TAB_ROUTES } from '../utils/navigation'
import { shopHoursStatus } from '../utils/shop'
import { APPOINTMENTS_CHANGED } from '../utils/status'
import { Avatar } from './Controls'
import { PageLoader } from './Feedback'
import {
  AlertCircleIcon,
  CalendarCheckIcon,
  CalendarIcon,
  CalendarPlusIcon,
  ChevronDownIcon,
  ClockIcon,
  ContactIcon,
  DashboardIcon,
  HomeIcon,
  LogoutIcon,
  MenuIcon,
  PanelLeftIcon,
  ScissorsIcon,
  StoreIcon,
  UserIcon,
  UsersIcon,
  XIcon,
} from './Icons'
import { BrandLogo, BrandMark } from './Brand'
import styles from '../styles/layout.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

interface NavItem {
  to: string
  label: string
  icon: ComponentType<{ size?: number }>
  end?: boolean
}

interface NavGroup {
  label?: string
  items: NavItem[]
}

const navigation: Record<UserRole, NavGroup[]> = {
  admin: [
    {
      label: 'Operação',
      items: [
        { to: '/admin', label: 'Painel', icon: DashboardIcon, end: true },
        { to: '/admin/appointments', label: 'Agendamentos', icon: CalendarIcon },
      ],
    },
    {
      label: 'Cadastros',
      items: [
        { to: '/admin/services', label: 'Serviços', icon: ScissorsIcon },
        { to: '/admin/barbers', label: 'Barbeiros', icon: UsersIcon },
        { to: '/admin/clients', label: 'Clientes', icon: ContactIcon },
      ],
    },
    {
      label: 'Barbearia',
      items: [{ to: '/admin/barbershop', label: 'Dados da barbearia', icon: StoreIcon }],
    },
  ],
  barbeiro: [
    { items: [{ to: '/barber/agenda', label: 'Minha agenda', icon: CalendarCheckIcon }] },
  ],
  cliente: [
    {
      items: [
        { to: '/', label: 'Início', icon: HomeIcon, end: true },
        { to: '/appointments/new', label: 'Agendar horário', icon: CalendarPlusIcon },
        { to: '/appointments', label: 'Meus agendamentos', icon: CalendarIcon, end: true },
      ],
    },
    {
      label: 'Barbearia',
      items: [
        { to: '/services', label: 'Serviços e preços', icon: ScissorsIcon },
        { to: '/barbers', label: 'Equipe', icon: UsersIcon },
      ],
    },
  ],
}

const COLLAPSE_KEY = 'barberpro.sidebar.collapsed'

function readCollapsed(): boolean {
  try { return localStorage.getItem(COLLAPSE_KEY) === '1' } catch { return false }
}

export function AppLayout() {
  return (
    <BarbershopProvider>
      <Shell />
    </BarbershopProvider>
  )
}

function Shell() {
  const { user } = useAuth()
  const location = useLocation()
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const drawerRef = useRef<HTMLElement>(null)
  const menuButtonRef = useRef<HTMLButtonElement>(null)

  // Fecha a gaveta ao navegar
  const [lastPath, setLastPath] = useState(location.pathname)
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname)
    setDrawerOpen(false)
  }

  useEffect(() => {
    try { localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0') } catch { /* armazenamento indisponível */ }
  }, [collapsed])

  // Gaveta móvel: Esc fecha, foco entra na gaveta e volta ao botão de menu
  useEffect(() => {
    if (!drawerOpen || isDesktop) return
    const previous = document.activeElement as HTMLElement | null
    const menuButton = menuButtonRef.current
    drawerRef.current?.querySelector<HTMLElement>('a, button')?.focus()
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setDrawerOpen(false) }
    document.addEventListener('keydown', onKey)
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
      ;(previous ?? menuButton)?.focus()
    }
  }, [drawerOpen, isDesktop])

  if (!user) return null

  const groups = navigation[user.tipo_perfil] ?? []
  const isCollapsed = collapsed && isDesktop
  const drawerHidden = !isDesktop && !drawerOpen

  return (
    <div className={`${styles.shell} ${isCollapsed ? styles.shellCollapsed : ''}`}>
      <a className={styles.skipLink} href="#conteudo">Pular para o conteúdo</a>

      {!isDesktop && drawerOpen && <div className={styles.overlay} onClick={() => setDrawerOpen(false)} aria-hidden="true" />}

      <aside
        ref={drawerRef}
        id="menu-principal"
        className={`${styles.sidebar} ${drawerOpen ? styles.sidebarOpen : ''}`}
        aria-label="Menu principal"
        aria-hidden={drawerHidden ? true : undefined}
        inert={drawerHidden ? true : undefined}
      >
        <div className={styles.sidebarHeader}>
          <Link to="/" className={styles.brand} aria-label="BarberPro, página inicial">
            <span className={styles.brandFull}><BrandLogo fundo="escuro" height={30} label="" /></span>
            <span className={styles.brandIcon}><BrandMark size={36} /></span>
          </Link>
          <button type="button" className={`${ui.iconButton} ${styles.closeDrawer}`} onClick={() => setDrawerOpen(false)} aria-label="Fechar menu">
            <XIcon size={20} />
          </button>
        </div>

        <ShopSummary />

        <nav className={styles.nav} aria-label="Navegação principal">
          {groups.map((group, index) => (
            <div className={styles.navGroup} key={group.label ?? index}>
              {group.label && <span className={styles.navGroupLabel}>{group.label}</span>}
              {group.items.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  title={isCollapsed ? label : undefined}
                  aria-label={isCollapsed ? label : undefined}
                  className={({ isActive }) => `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`}
                >
                  <Icon size={20} />
                  <span className={styles.navText}>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <button
            type="button"
            className={styles.collapseButton}
            onClick={() => setCollapsed((value) => !value)}
            aria-expanded={!collapsed}
            aria-controls="menu-principal"
            title={collapsed ? 'Expandir menu' : undefined}
          >
            <PanelLeftIcon size={20} />
            <span className={styles.collapseText}>Recolher menu</span>
            <span className="sr-only">{collapsed ? 'Expandir menu' : ''}</span>
          </button>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <button
            ref={menuButtonRef}
            type="button"
            className={`${ui.iconButton} ${styles.menuButton}`}
            onClick={() => setDrawerOpen(true)}
            aria-label="Abrir menu"
            aria-expanded={drawerOpen}
            aria-controls="menu-principal"
          >
            <MenuIcon size={22} />
          </button>
          <Link to="/" className={styles.mobileBrand} aria-label="BarberPro, página inicial">
            <BrandLogo fundo="claro" height={24} label="" />
          </Link>
          <span className={styles.topbarDate}>{formatDayLong(todayISO(), true)}</span>
          <span className={styles.topbarSpacer} />
          {(user.tipo_perfil === 'admin' || user.tipo_perfil === 'barbeiro') && <PendingIndicator role={user.tipo_perfil} />}
          <UserMenu user={user} />
        </header>

        <main id="conteudo" className={styles.content} tabIndex={-1}>
          <ShopInactiveNotice />
          <Suspense fallback={<PageLoader label="Carregando…" />}>
            <div key={location.pathname} className={page.routeEnter}>
              <Outlet />
            </div>
          </Suspense>
        </main>
      </div>

      {!isDesktop && <TabBar role={user.tipo_perfil} />}
    </div>
  )
}

/** Ícone de cada aba da barra inferior; destino, rótulo e regra de aba ativa ficam em `utils/navigation`. */
const tabIcons: Record<string, ComponentType<{ size?: number }>> = {
  '/admin': DashboardIcon,
  '/admin/appointments': CalendarIcon,
  '/admin/services': ScissorsIcon,
  '/admin/barbers': UsersIcon,
  '/admin/clients': ContactIcon,
  '/barber/agenda': CalendarCheckIcon,
  '/barber/agenda?status=agendado': ClockIcon,
  '/account': UserIcon,
  '/': HomeIcon,
  '/appointments/new': CalendarPlusIcon,
  '/appointments': CalendarIcon,
  '/services': ScissorsIcon,
  '/barbers': UsersIcon,
}

/** Navegação principal ao alcance do polegar (celular e tablet). O menu completo segue no botão do topo. */
function TabBar({ role }: { role: UserRole }) {
  const location = useLocation()
  const items = TAB_ROUTES[role] ?? []
  if (items.length === 0) return null
  const current = activeTab(role, location.pathname, location.search)
  return (
    <nav className={styles.tabbar} aria-label="Navegação rápida">
      {items.map(({ to, label }) => {
        const Icon = tabIcons[to]
        const active = to === current
        return (
          <Link key={to} to={to} className={`${styles.tab} ${active ? styles.tabActive : ''}`} aria-current={active ? 'page' : undefined}>
            {Icon && <Icon size={22} />}
            <span>{label}</span>
          </Link>
        )
      })}
    </nav>
  )
}

/** Barbearia desativada: aviso em todas as telas, com a mesma mensagem da API (FE-14). */
function ShopInactiveNotice() {
  const { barbershop } = useBarbershop()
  if (!barbershop || barbershop.ativo !== false) return null
  return (
    <div className={`${page.page} ${styles.shopNotice}`}>
      <p className={`${ui.alert} ${ui.alertDanger}`} role="status">
        <AlertCircleIcon size={18} />
        <span>
          <strong>Barbearia desativada.</strong>
          Não é possível criar, remarcar, confirmar ou concluir agendamentos. Consultas e cancelamentos continuam disponíveis.
        </span>
      </p>
    </div>
  )
}

function ShopSummary() {
  const { barbershop } = useBarbershop()
  useNow(60_000)
  if (!barbershop) return null
  const status = shopHoursStatus(barbershop)
  return (
    <div className={styles.shop}>
      <span className={styles.shopName} title={barbershop.nome}>{barbershop.nome}</span>
      <span className={styles.shopMeta}>
        <span className={`${styles.pole} ${status.open ? '' : styles.poleStopped}`} aria-hidden="true" />
        {status.label}
      </span>
    </div>
  )
}

/**
 * Agendamentos com status "agendado" aguardando confirmação (dado real da API).
 * Atualiza ao navegar e quando qualquer tela altera um agendamento.
 */
function PendingIndicator({ role }: { role: 'admin' | 'barbeiro' }) {
  const location = useLocation()
  const [count, setCount] = useState<number | null>(null)

  const load = useCallback(() => {
    appointmentApi.list({ status: 'agendado' })
      .then(({ data }) => setCount(data.count))
      .catch(() => setCount(null))
  }, [])

  useEffect(() => { load() }, [load, location.pathname])

  useEffect(() => {
    window.addEventListener(APPOINTMENTS_CHANGED, load)
    return () => window.removeEventListener(APPOINTMENTS_CHANGED, load)
  }, [load])

  if (!count) return null
  const target = role === 'admin' ? '/admin/appointments?status=agendado' : '/barber/agenda?status=agendado'
  return (
    <Link
      to={target}
      className={styles.pendingLink}
      aria-label={`${count} agendamentos aguardando confirmação, em todas as datas`}
      title="Aguardando confirmação, em todas as datas"
    >
      <span className={styles.pendingCount}>{count}</span>
      <span className={styles.pendingText}>a confirmar<span className={styles.pendingScope}> no total</span></span>
    </Link>
  )
}

function UserMenu({ user }: { user: User }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    containerRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus()
    const onPointer = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    return () => document.removeEventListener('pointerdown', onPointer)
  }, [open])

  const onMenuKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(containerRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
    const index = items.indexOf(document.activeElement as HTMLElement)
    if (event.key === 'Escape') {
      setOpen(false)
      buttonRef.current?.focus()
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      items[(index + 1) % items.length]?.focus()
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      items[(index - 1 + items.length) % items.length]?.focus()
    } else if (event.key === 'Tab') {
      setOpen(false)
    }
  }

  const handleLogout = async () => {
    setOpen(false)
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className={styles.userMenu} ref={containerRef}>
      <button
        ref={buttonRef}
        type="button"
        className={styles.userButton}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Avatar name={user.nome} />
        <span className={styles.userButtonText}>
          <strong>{user.nome.split(' ')[0]}</strong>
          <span>{roleLabels[user.tipo_perfil]}</span>
        </span>
        <ChevronDownIcon size={16} />
        <span className="sr-only">Menu da conta</span>
      </button>

      {open && (
        <div className={styles.menu} role="menu" aria-label="Conta" onKeyDown={onMenuKeyDown}>
          <div className={styles.menuHeader}>
            <strong>{user.nome}</strong>
            <span>{user.email}</span>
            <span className={styles.menuRole}>{roleLabels[user.tipo_perfil]}</span>
          </div>
          <Link to="/account" role="menuitem" className={styles.menuItem} onClick={() => setOpen(false)}>
            <UserIcon size={18} /> Minha conta
          </Link>
          <button type="button" role="menuitem" className={`${styles.menuItem} ${styles.menuItemDanger}`} onClick={() => void handleLogout()}>
            <LogoutIcon size={18} /> Sair
          </button>
        </div>
      )}
    </div>
  )
}
