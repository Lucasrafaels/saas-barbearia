import { useId, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useDocumentTitle } from '../hooks/useUi'
import { ArrowLeftIcon } from './Icons'
import page from '../styles/page.module.css'

interface PageHeaderProps {
  title: string
  description?: ReactNode
  actions?: ReactNode
  back?: { to: string; label: string }
}

/** Cabeçalho de página: título (h1 único), contexto e ações primárias. */
export function PageHeader({ title, description, actions, back }: PageHeaderProps) {
  useDocumentTitle(title)
  return (
    <header className={page.header}>
      <div className={page.headerText}>
        {back && (
          <Link to={back.to} className={page.backLink}>
            <ArrowLeftIcon size={16} /> {back.label}
          </Link>
        )}
        <h1 className={page.title}>{title}</h1>
        {description && <p className={page.description}>{description}</p>}
      </div>
      {actions && <div className={page.headerActions}>{actions}</div>}
    </header>
  )
}

/** Marca BarberPro: cápsula com faixas diagonais (o poste de barbearia, abstraído). */
export function BrandMark({ size = 32 }: { size?: number }) {
  // id único por instância: a marca aparece mais de uma vez na mesma página
  const clipId = `brand-pole-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="8" fill="#23262C" />
      <clipPath id={clipId}>
        <rect x="11" y="5" width="10" height="22" rx="5" />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        <rect x="11" y="5" width="10" height="22" fill="#3B3F47" />
        <path d="M5 13l22-9v4L5 17zM5 22l22-9v4L5 26z" fill="#C6A16B" />
      </g>
    </svg>
  )
}
