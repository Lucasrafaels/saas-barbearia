import { forwardRef, useId, useState, type InputHTMLAttributes, type ReactNode } from 'react'
import { AlertCircleIcon, CheckIcon, EyeIcon, EyeOffIcon, SearchIcon, XIcon } from './Icons'
import type { AppointmentStatus } from '../types'
import { initials, statusLabels } from '../utils/format'
import ui from '../styles/ui.module.css'

/* ---------------------------------------------------------------- Field */

interface FieldProps {
  label: string
  htmlFor: string
  error?: string
  hint?: ReactNode
  optional?: boolean
  children: ReactNode
}

/** Rótulo + controle + dica/erro, com associação acessível via id. */
export function Field({ label, htmlFor, error, hint, optional, children }: FieldProps) {
  return (
    <div className={ui.field}>
      <label className={ui.label} htmlFor={htmlFor}>
        {label}
        {optional && <span className={ui.optional}> (opcional)</span>}
      </label>
      {children}
      {error
        ? <p className={ui.error} id={`${htmlFor}-error`}><AlertCircleIcon size={14} />{error}</p>
        : hint ? <p className={ui.hint} id={`${htmlFor}-hint`}>{hint}</p> : null}
    </div>
  )
}

/** Props de acessibilidade para o controle dentro de <Field>. */
export function fieldA11y(id: string, error?: string, hint?: boolean) {
  return {
    id,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': error ? `${id}-error` : hint ? `${id}-hint` : undefined,
  } as const
}

/* -------------------------------------------------------- PasswordInput */

type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>

/** Campo de senha com botão para mostrar/ocultar. */
export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(function PasswordInput(props, ref) {
  const [visible, setVisible] = useState(false)
  return (
    <div className={ui.inputWrap}>
      <input ref={ref} {...props} type={visible ? 'text' : 'password'} />
      <span className={ui.inputAddon}>
        <button
          type="button"
          className={ui.iconButton}
          onClick={() => setVisible((value) => !value)}
          aria-label={visible ? 'Ocultar senha' : 'Mostrar senha'}
          aria-pressed={visible}
        >
          {visible ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
        </button>
      </span>
    </div>
  )
})

/* ---------------------------------------------------------- SearchField */

interface SearchFieldProps {
  value: string
  onChange: (value: string) => void
  placeholder: string
  label?: string
}

export function SearchField({ value, onChange, placeholder, label = 'Buscar' }: SearchFieldProps) {
  const id = useId()
  return (
    <div className={ui.search} role="search">
      <label htmlFor={id} className="sr-only">{label}</label>
      <SearchIcon size={16} />
      <input
        id={id}
        type="search"
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Escape' && value) { event.preventDefault(); onChange('') } }}
      />
      {value && (
        <button type="button" className={ui.searchClear} onClick={() => onChange('')} aria-label="Limpar busca">
          <XIcon size={14} />
        </button>
      )}
    </div>
  )
}

/* ----------------------------------------------------- SegmentedControl */

interface SegmentOption<T extends string> {
  value: T
  label: string
  count?: number
}

interface SegmentedControlProps<T extends string> {
  label: string
  value: T
  options: SegmentOption<T>[]
  onChange: (value: T) => void
}

/** Grupo de rádios nativos: navegação por setas e leitores de tela funcionam sem código extra. */
export function SegmentedControl<T extends string>({ label, value, options, onChange }: SegmentedControlProps<T>) {
  const name = useId()
  return (
    <div className={ui.segmented} role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <label key={option.value} className={ui.segment}>
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          <span>
            {option.label}
            {option.count !== undefined && <span className={ui.segmentCount}>{option.count}</span>}
          </span>
        </label>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------ Badges */

const statusClass: Record<AppointmentStatus, string> = {
  agendado: ui.status_agendado,
  confirmado: ui.status_confirmado,
  realizado: ui.status_realizado,
  cancelado: ui.status_cancelado,
}

/** Status do agendamento: forma + texto, nunca apenas cor. */
export function StatusBadge({ status }: { status: AppointmentStatus }) {
  return (
    <span className={`${ui.badge} ${statusClass[status]}`}>
      {status === 'realizado' ? <CheckIcon size={12} strokeWidth={2.5} />
        : status === 'cancelado' ? <XIcon size={12} strokeWidth={2.5} />
          : <span className={ui.statusMark} aria-hidden="true" />}
      {statusLabels[status]}
    </span>
  )
}

export function ActiveBadge({ active, activeLabel = 'Ativo', inactiveLabel = 'Inativo' }: { active: boolean; activeLabel?: string; inactiveLabel?: string }) {
  return (
    <span className={`${ui.badge} ${active ? ui.badgeSuccess : ui.badgeNeutral}`}>
      {active ? <CheckIcon size={12} strokeWidth={2.5} /> : <span className={ui.statusMark} style={{ border: '1.5px solid currentColor' }} aria-hidden="true" />}
      {active ? activeLabel : inactiveLabel}
    </span>
  )
}

/* ------------------------------------------------------------ Avatar */

export function Avatar({ name, size = 'md', muted }: { name: string; size?: 'sm' | 'md' | 'lg'; muted?: boolean }) {
  const sizeClass = size === 'sm' ? ui.avatarSm : size === 'lg' ? ui.avatarLg : ''
  return <span className={`${ui.avatar} ${sizeClass} ${muted ? ui.avatarMuted : ''}`} aria-hidden="true">{initials(name)}</span>
}

/* ---------------------------------------------------------- Spinner */

export function ButtonSpinner() {
  return <span className={ui.buttonSpinner} aria-hidden="true" />
}

/* -------------------------------------------------------- Pagination */

interface PaginationProps {
  page: number
  count: number
  pageSize?: number
  onChange: (page: number) => void
}

export function Pagination({ page, count, pageSize = 20, onChange }: PaginationProps) {
  const totalPages = Math.ceil(count / pageSize)
  if (totalPages <= 1) return null
  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, count)
  return (
    <nav className={ui.pagination} aria-label="Paginação">
      <span aria-live="polite">{first}–{last} de {count}</span>
      <div className={ui.paginationButtons}>
        <button type="button" className={`${ui.secondaryButton} ${ui.sm}`} disabled={page <= 1} onClick={() => onChange(page - 1)}>Anterior</button>
        <button type="button" className={`${ui.secondaryButton} ${ui.sm}`} disabled={page >= totalPages} onClick={() => onChange(page + 1)}>Próxima</button>
      </div>
    </nav>
  )
}
