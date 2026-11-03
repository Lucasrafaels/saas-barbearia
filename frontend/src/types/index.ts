export type UserRole = 'cliente' | 'barbeiro' | 'admin'
export type AppointmentStatus = 'agendado' | 'confirmado' | 'realizado' | 'cancelado'

export interface AuthTokens {
  access: string
  refresh: string
}

export interface User {
  id: number
  email: string
  nome: string
  tipo_perfil: UserRole
  barbershop: number | null
  is_active: boolean
  created_at: string
}

export interface Barbershop {
  id: number
  nome: string
  endereco: string
  telefone: string
  email: string
  horario_abertura: string
  horario_fechamento: string
  logo: string | null
  ativo: boolean
  created_at: string
}

export interface Barber {
  id: number
  user: number
  nome: string
  email: string
  barbershop: number
  especialidade: string
  ativo: boolean
  created_at: string
}

export interface Service {
  id: number
  barbershop: number
  nome: string
  descricao: string
  preco: string
  duracao: number
  ativo: boolean
  created_at: string
}

export interface Appointment {
  id: number
  barbershop: number
  cliente: number
  cliente_nome: string
  barbeiro: number
  barbeiro_nome: string
  barbeiro_especialidade: string | null
  servico: number
  servico_nome: string
  servico_preco: string
  servico_duracao: number
  data_hora: string
  status: AppointmentStatus
  observacoes: string
  created_at: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface AvailableSlots {
  data: string
  slots: string[]
}

export interface LoginInput {
  email: string
  password: string
}

export interface RegisterInput extends LoginInput {
  nome: string
}

export interface CreateServiceInput {
  nome: string
  descricao: string
  preco: string
  duracao: number
  ativo: boolean
}

export interface CreateBarberInput {
  user: number
  especialidade: string
  ativo: boolean
}

export interface CreateUserInput {
  email: string
  nome: string
  password: string
  tipo_perfil: Exclude<UserRole, 'admin'>
}

export interface UpdateUserInput {
  email?: string
  nome?: string
  tipo_perfil?: Exclude<UserRole, 'admin'>
  is_active?: boolean
}

export interface CreateAppointmentInput {
  cliente: number
  barbeiro: number
  servico: number
  data_hora: string
  observacoes?: string
}

export interface PasswordChangeInput {
  old_password: string
  new_password: string
}

export interface PasswordResetRequestInput {
  email: string
}

export interface PasswordResetConfirmInput {
  uid: string
  token: string
  new_password: string
}
