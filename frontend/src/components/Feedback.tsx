import axios from 'axios'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ilustracoes } from '../assets/brand'
import { AlertCircleIcon, RefreshIcon, WifiOffIcon } from './Icons'
import { errorMessage } from '../utils/format'
import ui from '../styles/ui.module.css'

type Action = { label: string; to: string } | { label: string; onClick: () => void }

function ActionButton({ action, primary }: { action: Action; primary?: boolean }) {
  const className = primary ? ui.button : ui.secondaryButton
  return 'to' in action
    ? <Link className={className} to={action.to}>{action.label}</Link>
    : <button type="button" className={className} onClick={action.onClick}>{action.label}</button>
}

interface EmptyStateProps {
  title: string
  description?: ReactNode
  icon?: ReactNode
  /** Ilustração da marca no lugar do ícone (navalha ou tesoura em traço de gravura). */
  art?: keyof typeof ilustracoes
  action?: Action
  secondaryAction?: Action
  compact?: boolean
}

/** Estado vazio: explica o que falta e oferece o próximo passo. */
export function EmptyState({ title, description, icon, art, action, secondaryAction, compact }: EmptyStateProps) {
  return (
    <section className={`${ui.emptyState} ${compact ? ui.compact : ''}`}>
      {art
        ? <img className={ui.emptyArt} src={ilustracoes[art]} alt="" aria-hidden="true" draggable={false} />
        : icon && <div className={ui.emptyIcon} aria-hidden="true">{icon}</div>}
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {(action || secondaryAction) && (
        <div className={ui.buttonRow}>
          {secondaryAction && <ActionButton action={secondaryAction} />}
          {action && <ActionButton action={action} primary />}
        </div>
      )}
    </section>
  )
}

interface ErrorStateProps {
  error: unknown
  title?: string
  fallback?: string
  onRetry?: () => void
  compact?: boolean
}

/** Falha de carregamento com a causa e a opção de tentar novamente. */
export function ErrorState({ error, title, fallback = 'Não foi possível carregar os dados.', onRetry, compact }: ErrorStateProps) {
  const offline = axios.isAxiosError(error) && !error.response
  return (
    <section className={`${ui.errorState} ${compact ? ui.compact : ''}`} role="alert">
      <div className={ui.emptyIcon} aria-hidden="true">
        {offline ? <WifiOffIcon size={22} /> : <AlertCircleIcon size={22} />}
      </div>
      <h2>{title ?? (offline ? 'Sem conexão com o servidor' : 'Algo deu errado')}</h2>
      <p>{errorMessage(error, fallback)}</p>
      {onRetry && (
        <div className={ui.buttonRow}>
          <button type="button" className={ui.secondaryButton} onClick={onRetry}>
            <RefreshIcon size={16} /> Tentar novamente
          </button>
        </div>
      )}
    </section>
  )
}

export function PageLoader({ label = 'Carregando…', full }: { label?: string; full?: boolean }) {
  return (
    <div className={`${ui.loaderWrap} ${full ? ui.loaderFull : ''}`} role="status" aria-live="polite">
      <span className={ui.spinner} aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

/** Esqueleto de linhas para listas e tabelas enquanto os dados chegam. */
export function SkeletonRows({ rows = 5, label = 'Carregando' }: { rows?: number; label?: string }) {
  return (
    <div className={ui.skeletonStack} role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, index) => (
        <div className={ui.skeletonRow} key={index} style={{ opacity: 1 - index * 0.12 }}>
          <span className={ui.skeleton} style={{ width: '2.25rem', height: '2.25rem', borderRadius: '50%' }} />
          <span style={{ display: 'grid', gap: 6 }}>
            <span className={ui.skeleton} style={{ width: `${55 + ((index * 17) % 30)}%`, height: 12 }} />
            <span className={ui.skeleton} style={{ width: `${30 + ((index * 11) % 20)}%`, height: 10 }} />
          </span>
          <span className={ui.skeleton} style={{ height: 24, borderRadius: 999 }} />
        </div>
      ))}
    </div>
  )
}

export function SkeletonBlock({ height = 120, radius = 12 }: { height?: number | string; radius?: number }) {
  return <span className={ui.skeleton} style={{ height, borderRadius: radius }} aria-hidden="true" />
}

/** Barra fina indicando recarga em segundo plano. */
export function RefreshBar({ active }: { active: boolean }) {
  return active ? <div className={ui.refreshBar} role="status" aria-label="Atualizando" /> : null
}

/** Tela inteira para quando a API não responde ao validar a sessão salva. */
export function ConnectionLost({ onRetry }: { onRetry: () => void }) {
  return (
    <div className={ui.loaderFull} style={{ display: 'grid', placeItems: 'center', padding: 'var(--space-6)' }}>
      <section className={ui.errorState} role="alert">
        <div className={ui.emptyIcon} aria-hidden="true"><WifiOffIcon size={22} /></div>
        <h2>Sem conexão com o servidor</h2>
        <p>Não foi possível validar sua sessão. Verifique sua internet ou se a API está em execução. Sua sessão continua salva.</p>
        <div className={ui.buttonRow}>
          <button type="button" className={ui.button} onClick={onRetry}><RefreshIcon size={16} /> Tentar novamente</button>
        </div>
      </section>
    </div>
  )
}
