import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useDocumentTitle } from '../hooks/useUi'
import { BrandMark } from './PageHeader'
import styles from '../styles/auth.module.css'

interface AuthLayoutProps {
  title: string
  description?: ReactNode
  children: ReactNode
  wide?: boolean
}

/** Moldura das telas públicas: marca à esquerda, formulário à direita. */
export function AuthLayout({ title, description, children, wide }: AuthLayoutProps) {
  useDocumentTitle(title)
  return (
    <div className={styles.layout}>
      <aside className={styles.aside} aria-hidden="true">
        <span className={styles.brand}><BrandMark /> BarberPro</span>
        <div className={styles.statement}>
          <h2>A agenda da barbearia, em ordem.</h2>
          <p>Horários, equipe, serviços e clientes em um só lugar, para quem administra, atende e agenda.</p>
        </div>
        <span className={styles.pole} />
      </aside>
      <main className={styles.main}>
        <section className={`${styles.panel} ${wide ? styles.wide : ''}`}>
          <Link to="/login" className={styles.mobileBrand}><BrandMark size={28} /> BarberPro</Link>
          <header className={styles.header}>
            <h1>{title}</h1>
            {description && <p>{description}</p>}
          </header>
          {children}
        </section>
      </main>
    </div>
  )
}
