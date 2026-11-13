import api from './client'
import type {
  Appointment,
  AvailableSlots,
  Barber,
  Barbershop,
  CreateAppointmentInput,
  CreateBarberInput,
  CreateServiceInput,
  CreateUserInput,
  LoginInput,
  Paginated,
  PasswordChangeInput,
  PasswordResetConfirmInput,
  PasswordResetRequestInput,
  RegisterInput,
  RevenueReport,
  Service,
  UpdateBarbershopInput,
  UpdateUserInput,
  User,
  UserRole,
} from '../types'

type ActiveFilter = 'true' | 'false' | 'all'

export const authApi = {
  login: (payload: LoginInput) => api.post<{ access: string }>('/auth/login/', payload),
  register: (payload: RegisterInput) => api.post<User>('/auth/register/', payload),
  logout: () => api.post('/auth/logout/'),
  me: () => api.get<User>('/users/me/'),
  changePassword: (payload: PasswordChangeInput) => api.post('/auth/password/change/', payload),
  requestPasswordReset: (payload: PasswordResetRequestInput) => api.post('/auth/password/reset/', payload),
  confirmPasswordReset: (payload: PasswordResetConfirmInput) => api.post('/auth/password/reset/confirm/', payload),
}

export const barbershopApi = {
  list: () => api.get<Paginated<Barbershop>>('/barbershops/'),
  /** A API devolve somente a barbearia do usuário autenticado. */
  current: async (): Promise<Barbershop | null> => {
    const { data } = await api.get<Paginated<Barbershop>>('/barbershops/')
    return data.results[0] ?? null
  },
  create: (payload: Omit<Barbershop, 'id' | 'logo' | 'ativo' | 'created_at' | 'dias_funcionamento'> & { ativo?: boolean; dias_funcionamento?: number[] }) =>
    api.post<Barbershop>('/barbershops/', payload),
  update: (id: number, payload: UpdateBarbershopInput) => api.patch<Barbershop>(`/barbershops/${id}/`, payload),
}

export const barberApi = {
  list: (params?: { page?: number; ativo?: ActiveFilter }) => api.get<Paginated<Barber>>('/barbers/', { params }),
  create: (payload: CreateBarberInput) => api.post<Barber>('/barbers/', payload),
  update: (id: number, payload: Partial<CreateBarberInput>) => api.patch<Barber>(`/barbers/${id}/`, payload),
  /** No backend, DELETE desativa o perfil (soft delete) e preserva o histórico. */
  remove: (id: number) => api.delete(`/barbers/${id}/`),
}

export const serviceApi = {
  list: (params?: { page?: number; ativo?: ActiveFilter }) => api.get<Paginated<Service>>('/services/', { params }),
  create: (payload: CreateServiceInput) => api.post<Service>('/services/', payload),
  /**
   * `ativo=all` também na escrita: sem ele o queryset do backend filtra só
   * serviços ativos e a edição/reativação de um serviço inativo retorna 404.
   */
  update: (id: number, payload: Partial<CreateServiceInput>) =>
    api.patch<Service>(`/services/${id}/`, payload, { params: { ativo: 'all' } }),
  /** No backend, DELETE desativa o serviço (soft delete) e preserva o histórico. */
  remove: (id: number) => api.delete(`/services/${id}/`),
}

export const userApi = {
  list: (params?: { tipo_perfil?: UserRole }) => api.get<Paginated<User>>('/users/', { params }),
  create: (payload: CreateUserInput) => api.post<User>('/users/', payload),
  update: (id: number, payload: Partial<UpdateUserInput>) => api.patch<User>(`/users/${id}/`, payload),
  /** No backend, DELETE desativa a conta e preserva os agendamentos vinculados. */
  remove: (id: number) => api.delete(`/users/${id}/`),
}

export const appointmentApi = {
  list: (params?: Record<string, string | number>) => api.get<Paginated<Appointment>>('/appointments/', { params }),
  get: (id: number) => api.get<Appointment>(`/appointments/${id}/`),
  create: (payload: CreateAppointmentInput) => api.post<Appointment>('/appointments/', payload),
  update: (id: number, payload: Partial<CreateAppointmentInput> & { status?: Appointment['status'] }) =>
    api.patch<Appointment>(`/appointments/${id}/`, payload),
  remove: (id: number) => api.delete(`/appointments/${id}/`),
  availableSlots: (barbeiro: number, servico: number, data: string, excludeAppointmentId?: number) =>
    api.get<AvailableSlots>('/appointments/available-slots/', {
      params: { barbeiro, servico, data, ...(excludeAppointmentId && { exclude_appointment_id: excludeAppointmentId }) },
    }),
  /** Faturamento por preço histórico dos atendimentos realizados (padrão: últimos 30 dias). */
  revenueReport: (params?: { start?: string; end?: string; barbeiro?: number }) =>
    api.get<RevenueReport>('/appointments/revenue-report/', { params }),
}

/** Percorre todas as páginas de uma listagem paginada do DRF. */
async function collectPages<T>(url: string, params?: Record<string, string | number>): Promise<T[]> {
  const items: T[] = []
  let next: string | null = url
  let isFirst = true
  while (next) {
    const response: { data: Paginated<T> } = await api.get<Paginated<T>>(next, isFirst ? { params } : undefined)
    items.push(...response.data.results)
    next = response.data.next
    isFirst = false
  }
  return items
}

/** Todos os agendamentos visíveis ao usuário (o escopo é aplicado pelo backend). */
export function listAllAppointments(): Promise<Appointment[]> {
  return collectPages<Appointment>('/appointments/')
}

/** Usuários do tenant. A API não filtra por papel, então o filtro é aplicado aqui. */
export async function listAllUsers(tipoPerfil?: UserRole): Promise<User[]> {
  const users = await collectPages<User>('/users/')
  return tipoPerfil ? users.filter((user) => user.tipo_perfil === tipoPerfil) : users
}

/** Todos os serviços do tenant, ativos e inativos (admin). */
export function listAllServices(): Promise<Service[]> {
  return collectPages<Service>('/services/', { ativo: 'all' })
}

/** Todos os barbeiros do tenant, ativos e inativos (admin). */
export function listAllBarbers(): Promise<Barber[]> {
  return collectPages<Barber>('/barbers/', { ativo: 'all' })
}

/** Serviços ativos (catálogo visível para qualquer perfil). */
export function listActiveServices(): Promise<Service[]> {
  return collectPages<Service>('/services/', { ativo: 'true' })
}

/** Barbeiros ativos (equipe visível para qualquer perfil). */
export function listActiveBarbers(): Promise<Barber[]> {
  return collectPages<Barber>('/barbers/', { ativo: 'true' })
}

export async function getTotalServices(): Promise<number> {
  const response = await serviceApi.list()
  return response.data.count
}

export async function getTotalBarbers(): Promise<number> {
  const response = await barberApi.list()
  return response.data.count
}
