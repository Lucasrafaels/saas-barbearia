import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import navalhaSvg from '../assets/brand/ilustracoes/navalha.svg?raw'
import { useDocumentTitle } from '../hooks/useUi'
import { BrandLogo } from './Brand'
import styles from '../styles/auth.module.css'

interface AuthLayoutProps {
  title: string
  description?: ReactNode
  children: ReactNode
  wide?: boolean
}

/** Moldura das telas de entrada: placa marinho com a marca à esquerda, formulário sobre o marfim à direita. */
export function AuthLayout({ title, description, children, wide }: AuthLayoutProps) {
  useDocumentTitle(title)
  return (
    <div className={styles.layout}>
      <aside className={styles.aside} aria-hidden="true">
        <span className={styles.brand}><BrandLogo fundo="escuro" height={34} label="" /></span>
        <div className={styles.art} dangerouslySetInnerHTML={{ __html: navalhaSvg }} />
        <div className={styles.statement}>
          <h2>A agenda da barbearia, em ordem.</h2>
          <p>Horários, equipe, serviços e clientes em um só lugar, para quem administra, atende e agenda.</p>
        </div>
        <span className={styles.pole} />
      </aside>
      <main className={styles.main}>
        <section className={`${styles.panel} ${wide ? styles.wide : ''}`}>
          <Link to="/login" className={styles.mobileBrand} aria-label="BarberPro"><BrandLogo fundo="claro" height={30} label="" /></Link>
          <span className={styles.mobilePole} aria-hidden="true" />
          <header className={styles.header}>
            <h1>{title}</h1>
            {description && <p>{description}</p>}
          </header>
          {children}
          <Link to="/conheca" className={styles.about}>Conheça o BarberPro</Link>
        </section>
      </main>
    </div>
  )
}
