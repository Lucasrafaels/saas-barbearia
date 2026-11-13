import type { ReactNode } from 'react'
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

/** Marca BarberPro (navalha aberta formando o B). Reexportada para os imports antigos. */
export { BrandMark } from './Brand'
