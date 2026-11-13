import type { UserRole } from '../types'

/**
 * Verdadeiro se `pathname` é a seção `base` ou uma subpágina dela. Compara
 * por segmento de caminho, não por prefixo de texto: "/admin/barbershop" não
 * pertence à seção "/admin/barbers" (FE-22).
 */
export function isSectionPath(pathname: string, base: string): boolean {
  return pathname === base || pathname.startsWith(`${base}/`)
}

export interface TabRoute {
  to: string
  label: string
  isActive: (pathname: string, search: string) => boolean
}

/** Abas da barra inferior (celular e tablet) de cada perfil e a tela que cada uma representa. */
export const TAB_ROUTES: Record<UserRole, TabRoute[]> = {
  admin: [
    { to: '/admin', label: 'Painel', isActive: (path) => path === '/admin' },
    { to: '/admin/appointments', label: 'Agenda', isActive: (path) => isSectionPath(path, '/admin/appointments') },
    { to: '/admin/services', label: 'Serviços', isActive: (path) => isSectionPath(path, '/admin/services') },
    { to: '/admin/barbers', label: 'Barbeiros', isActive: (path) => isSectionPath(path, '/admin/barbers') },
    { to: '/admin/clients', label: 'Clientes', isActive: (path) => isSectionPath(path, '/admin/clients') },
  ],
  barbeiro: [
    { to: '/barber/agenda', label: 'Agenda', isActive: (path, search) => path === '/barber/agenda' && !search.includes('status=agendado') },
    { to: '/barber/agenda?status=agendado', label: 'A confirmar', isActive: (path, search) => path === '/barber/agenda' && search.includes('status=agendado') },
    { to: '/account', label: 'Conta', isActive: (path) => path === '/account' },
  ],
  cliente: [
    { to: '/', label: 'Início', isActive: (path) => path === '/' },
    { to: '/appointments/new', label: 'Agendar', isActive: (path) => path === '/appointments/new' },
    { to: '/appointments', label: 'Horários', isActive: (path) => path === '/appointments' },
    { to: '/services', label: 'Serviços', isActive: (path) => path === '/services' },
    { to: '/barbers', label: 'Equipe', isActive: (path) => path === '/barbers' },
  ],
}

/** Destino da aba ativa para a tela atual, ou `null` quando a tela não tem aba (ex.: "Dados da barbearia"). */
export function activeTab(role: UserRole, pathname: string, search = ''): string | null {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname
  return TAB_ROUTES[role]?.find((tab) => tab.isActive(path, search))?.to ?? null
}
