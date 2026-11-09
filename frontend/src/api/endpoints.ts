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
  Service,
  UpdateUserInput,
  User,
  UserRole,
} from '../types'

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
  create: (payload: Omit<Barbershop, 'id' | 'logo' | 'ativo' | 'created_at'> & { ativo?: boolean }) =>
    api.post<Barbershop>('/barbershops/', payload),
}

export const barberApi = {
  list: (params?: { page?: number; ativo?: 'true' | 'false' | 'all' }) => api.get<Paginated<Barber>>('/barbers/', { params }),
  create: (payload: CreateBarberInput) => api.post<Barber>('/barbers/', payload),
  update: (id: number, payload: Partial<CreateBarberInput>) => api.patch<Barber>(`/barbers/${id}/`, payload),
  remove: (id: number) => api.delete(`/barbers/${id}/`),
}

export const serviceApi = {
  list: (params?: { page?: number; ativo?: 'true' | 'false' | 'all' }) => api.get<Paginated<Service>>('/services/', { params }),
  create: (payload: CreateServiceInput) => api.post<Service>('/services/', payload),
  update: (id: number, payload: Partial<CreateServiceInput>) => api.patch<Service>(`/services/${id}/`, payload),
  remove: (id: number) => api.delete(`/services/${id}/`),
}

export const userApi = {
  list: (params?: { tipo_perfil?: UserRole }) => api.get<Paginated<User>>('/users/', { params }),
  create: (payload: CreateUserInput) => api.post<User>('/users/', payload),
  update: (id: number, payload: Partial<UpdateUserInput>) => api.patch<User>(`/users/${id}/`, payload),
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
      params: { barbeiro, servico, data, ...(excludeAppointmentId && { exclude_appointment_id: excludeAppointmentId }) }
    }),
}

/** Busca todas as páginas. Usado apenas onde a visão precisa realmente de todos os itens (agenda do dia). */
export async function listAllAppointments(): Promise<Appointment[]> {
  const appointments: Appointment[] = []
  let next: string | null = '/appointments/'
  while (next) {
    const response = await api.get<Paginated<Appointment>>(next)
    const pageData: Paginated<Appointment> = response.data
    appointments.push(...pageData.results)
    next = pageData.next
  }
  return appointments
}

/** Busca todas as páginas de usuários do tenant, opcionalmente filtrando por papel. */
export async function listAllUsers(tipoPerfil?: UserRole): Promise<User[]> {
  const users: User[] = []
  let next: string | null = '/users/'
  let isFirst = true

  while (next) {
    const url: string = next
    const config = isFirst && tipoPerfil ? { params: { tipo_perfil: tipoPerfil } } : {}

    const response = await api.get<Paginated<User>>(url, config)

    isFirst = false
    users.push(...response.data.results)
    next = response.data.next
  }

  return tipoPerfil ? users.filter((u) => u.tipo_perfil === tipoPerfil) : users
}

/** Busca o total de serviços (paginação aware). */
export async function getTotalServices(): Promise<number> {
  const response = await serviceApi.list()
  return response.data.count
}

/** Busca o total de barbeiros (paginação aware). */
export async function getTotalBarbers(): Promise<number> {
  const response = await barberApi.list()
  return response.data.count
}

/** Busca todos os serviços do tenant (traversa todas as páginas). */
export async function listAllServices(): Promise<Service[]> {
  const services: Service[] = []
  let next: string | null = '/services/?ativo=all'
  while (next) {
    const response = await api.get<Paginated<Service>>(next)
    const pageData: Paginated<Service> = response.data
    services.push(...pageData.results)
    next = pageData.next
  }
  return services
}

/** Busca todos os barbeiros do tenant (traversa todas as páginas). */
export async function listAllBarbers(): Promise<Barber[]> {
  const barbers: Barber[] = []
  let next: string | null = '/barbers/?ativo=all'
  while (next) {
    const response = await api.get<Paginated<Barber>>(next)
    const pageData: Paginated<Barber> = response.data
    barbers.push(...pageData.results)
    next = pageData.next
  }
  return barbers
}