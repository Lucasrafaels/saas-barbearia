import { useEffect, useRef, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import navalhaSvg from '../assets/brand/ilustracoes/navalha.svg?raw'
import tesouraSvg from '../assets/brand/ilustracoes/tesoura.svg?raw'
import { BrandEmblem, BrandLogo } from '../components/Brand'
import { useDocumentTitle } from '../hooks/useUi'
import styles from '../styles/landing.module.css'

/* Demonstração do quadro do dia. Dados fictícios, rotulados como tal na página. */
const demo = [
  { name: 'Rafael', blocks: [{ at: 2, w: 13, time: '09:00', service: 'Barba', kind: 'conf' }, { at: 24, w: 19, time: '10:30', service: 'Corte + barba', kind: 'agen' }, { at: 56, w: 10, time: '14:15', service: 'Pezinho', kind: 'conf' }] },
  { name: 'Thiago', blocks: [{ at: 8, w: 10, time: '09:45', service: 'Corte', kind: 'agen' }, { at: 30, w: 12, time: '11:30', service: 'Corte', kind: 'conf' }, { at: 68, w: 13, time: '16:30', service: 'Reservado', kind: 'novo' }] },
  { name: 'Caio', blocks: [{ at: 14, w: 20, time: '10:00', service: 'Platinado', kind: 'conf' }, { at: 46, w: 9, time: '13:00', service: 'Barba', kind: 'agen' }, { at: 80, w: 10, time: '17:00', service: 'Corte', kind: 'conf' }] },
]

const kindClass: Record<string, string> = { conf: styles.blockConf, agen: styles.blockAgen, novo: styles.blockNovo }

/** Página institucional pública do BarberPro (para donos de barbearia). */
export function LandingPage() {
  useDocumentTitle('Conheça o BarberPro')
  const poleRef = useRef<HTMLDivElement>(null)

  // O poste da lateral gira com a rolagem da página (parado com movimento reduzido)
  useEffect(() => {
    const pole = poleRef.current
    if (!pole || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let frame = 0
    const onScroll = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => { pole.style.backgroundPosition = `0 ${window.scrollY * 0.4}px` })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(frame) }
  }, [])

  return (
    <div className={styles.page}>
      <div className={styles.pole} ref={poleRef} aria-hidden="true" />

      <header className={styles.hero}>
        <nav className={styles.nav} aria-label="Navegação">
          <Link to="/conheca" className={styles.navBrand} aria-label="BarberPro"><BrandLogo fundo="escuro" height={30} label="" /></Link>
          <ul className={styles.navLinks}>
            <li><a href="#como-funciona">Como funciona</a></li>
            <li><a href="#perfis">Perfis</a></li>
            <li><a href="#garantias">Garantias</a></li>
          </ul>
          <div className={styles.navActions}>
            <Link to="/login" className={styles.ghostLight}>Entrar</Link>
            <Link to="/register" className={styles.cta}>Criar minha barbearia</Link>
          </div>
        </nav>

        <div className={styles.heroBody}>
          <h1 className={styles.headline}>
            <span>A agenda da</span>
            <span>barbearia,</span>
            <span>em ordem.</span>
          </h1>
          <div className={styles.heroAside}>
            <div className={styles.heroArt} aria-hidden="true" dangerouslySetInnerHTML={{ __html: navalhaSvg }} />
            <p className={styles.lead}>Horários, equipe, serviços e clientes em um só lugar, para quem administra, atende e agenda.</p>
            <div className={styles.heroActions}>
              <Link to="/register" className={styles.cta}>Criar minha barbearia</Link>
              <Link to="/login" className={styles.ghostLight}>Já tenho conta</Link>
            </div>
          </div>
        </div>

        <section className={styles.demo} aria-label="Demonstração do quadro do dia">
          <div className={styles.demoHead}>
            <strong>Quadro do dia</strong>
            <span>Demonstração com dados fictícios</span>
          </div>
          <div className={styles.demoRows}>
            {demo.map((row) => (
              <div className={styles.demoRow} key={row.name}>
                <span className={styles.demoName}>{row.name}</span>
                <div className={styles.track}>
                  {row.blocks.map((block) => (
                    <span key={block.time} className={`${styles.block} ${kindClass[block.kind]}`} style={{ '--at': `${block.at}%`, '--w': `${block.w}%` } as CSSProperties}>
                      <span>{block.time}</span>
                      <span className={styles.blockService}>{block.service}</span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <span className={styles.now} aria-hidden="true" />
          </div>
          <p className={styles.demoNote}>
            <span className={styles.dot} aria-hidden="true" />
            Um horário reservado sai da lista de horários livres na hora. Ninguém marca o mesmo horário duas vezes.
          </p>
        </section>
      </header>

      <main>
        <section id="como-funciona" className={styles.section}>
          <h2 className={styles.sectionTitle}>Como funciona</h2>
          <ol className={styles.steps}>
            <li>
              <span className={styles.stepNo}>1</span>
              <h3>Cadastre a barbearia</h3>
              <p>Crie sua conta e informe nome, endereço, contato e horário de funcionamento.</p>
            </li>
            <li>
              <span className={styles.stepNo}>2</span>
              <h3>Monte equipe e serviços</h3>
              <p>Cadastre os barbeiros, os serviços com preço e duração e os clientes da casa.</p>
            </li>
            <li>
              <span className={styles.stepNo}>3</span>
              <h3>Agende sem conflito</h3>
              <p>O cliente escolhe serviço, barbeiro e um horário realmente livre. O sistema recusa marcação dupla.</p>
            </li>
          </ol>
        </section>

        <section id="perfis" className={`${styles.section} ${styles.board}`}>
          <div className={styles.boardFrame}>
            <h2 className={styles.sectionTitle}>Um painel para cada perfil</h2>
            <dl className={styles.priceBoard}>
              <div>
                <dt>Dono</dt>
                <span className={styles.leader} aria-hidden="true" />
                <dd>Quadro do dia por barbeiro, caixa dos últimos 30 dias, cadastros e o horário da barbearia.</dd>
              </div>
              <div>
                <dt>Barbeiro</dt>
                <span className={styles.leader} aria-hidden="true" />
                <dd>A agenda do dia no celular, com intervalos livres, o próximo atendimento e as ações de status.</dd>
              </div>
              <div>
                <dt>Cliente</dt>
                <span className={styles.leader} aria-hidden="true" />
                <dd>O próximo horário, serviços e preços, a equipe e o agendamento em quatro passos.</dd>
              </div>
            </dl>
          </div>
          <div className={styles.boardArt} aria-hidden="true" dangerouslySetInnerHTML={{ __html: tesouraSvg }} />
        </section>

        <section id="garantias" className={styles.section}>
          <h2 className={styles.sectionTitle}>O que o BarberPro garante</h2>
          <ul className={styles.guarantees}>
            <li>
              <h3>Agenda sem conflito</h3>
              <p>Só aparecem horários livres. Dois clientes nunca ficam com o mesmo horário do mesmo barbeiro.</p>
            </li>
            <li>
              <h3>Números confiáveis</h3>
              <p>O faturamento usa o preço praticado em cada atendimento, não o preço atual do serviço.</p>
            </li>
            <li>
              <h3>Simples para quem corta</h3>
              <p>Feito para o dono que atende e administra ao mesmo tempo, do balcão ou do celular.</p>
            </li>
            <li>
              <h3>Cada barbearia, um mundo fechado</h3>
              <p>Os dados de uma barbearia nunca aparecem para outra.</p>
            </li>
          </ul>
        </section>

        <section className={styles.closing}>
          <BrandEmblem fundo="escuro" size={148} />
          <div>
            <h2>Sua barbearia em ordem, a partir de hoje.</h2>
            <div className={styles.heroActions}>
              <Link to="/register" className={styles.cta}>Criar minha barbearia</Link>
              <Link to="/login" className={styles.ghostLight}>Entrar</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <BrandLogo fundo="claro" height={22} label="BarberPro" />
        <span>Gestão de agenda, equipe e serviços para barbearias.</span>
      </footer>
    </div>
  )
}
