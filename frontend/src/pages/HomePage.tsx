import { Link } from 'react-router-dom'
import { listAllAppointments } from '../api/endpoints'
import { StatusBadge } from '../components/Controls'
import { EmptyState, ErrorState, SkeletonBlock } from '../components/Feedback'
import { CalendarPlusIcon, ClockIcon, LocationIcon, MailIcon, PhoneIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { useBarbershop } from '../contexts/BarbershopContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Appointment } from '../types'
import {
  dateKey, dayOfMonth, firstName, formatClock, formatCurrency, formatDayCompact, formatDuration, formatTime, monthShort,
  relativeDayLabel,
} from '../utils/format'
import { shopHoursStatus } from '../utils/shop'
import { isOpenStatus } from '../utils/status'
import client from '../styles/client.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

/** Início do cliente: o próximo horário em destaque e os dados da barbearia. */
export function HomePage() {
  const { user } = useAuth()
  const { barbershop } = useBarbershop()
  const { data, isLoading, error, reload } = useAsyncData(listAllAppointments, [])

  if (!user) return null

  const now = Date.now()
  const upcoming = (data ?? [])
    .filter((item) => isOpenStatus(item.status) && new Date(item.data_hora).getTime() >= now)
    .sort((a, b) => a.data_hora.localeCompare(b.data_hora))
  const [next, ...others] = upcoming
  const visits = (data ?? []).filter((item) => item.status === 'realizado').length

  return (
    <div className={page.page}>
      <PageHeader
        title={`Olá, ${firstName(user.nome)}`}
        description="Seus horários e os contatos da barbearia."
        actions={<Link to="/appointments/new" className={ui.button}><CalendarPlusIcon size={18} /> Agendar horário</Link>}
      />

      <div className={page.split}>
        <div className={page.stack}>
          <h2 className="sr-only">Próximo horário</h2>
          {isLoading ? (
            <SkeletonBlock height={200} />
          ) : error && !data ? (
            <div className={ui.panel}><ErrorState error={error} fallback="Não foi possível carregar seus horários." onRetry={() => void reload()} /></div>
          ) : next ? (
            <NextTicket appointment={next} />
          ) : (
            <div className={ui.panel}>
              <EmptyState
                icon={<CalendarPlusIcon size={22} />}
                title="Nenhum horário marcado"
                description={visits > 0 ? 'Que tal já deixar o próximo corte reservado?' : 'Escolha o serviço, o barbeiro e um horário livre em poucos passos.'}
                action={{ label: 'Agendar horário', to: '/appointments/new' }}
                secondaryAction={{ label: 'Ver serviços e preços', to: '/services' }}
              />
            </div>
          )}

          {others.length > 0 && (
            <section className={ui.panel} aria-labelledby="others-title">
              <div className={ui.panelHeader}>
                <h2 id="others-title">Também marcado</h2>
                <Link to="/appointments" className={ui.textButton}>Ver todos</Link>
              </div>
              {others.slice(0, 3).map((item) => (
                <div key={item.id} className={page.apptRow}>
                  <div className={page.apptTime}>
                    <time dateTime={item.data_hora}>{formatClock(item.data_hora)}</time>
                    <span>{formatDayCompact(dateKey(item.data_hora))}</span>
                  </div>
                  <div className={page.apptMain}>
                    <div className={page.apptTitle}><span>{item.servico_nome}</span></div>
                    <p className={page.apptMeta}>com {item.barbeiro_nome}</p>
                  </div>
                  <div className={page.apptAside}><StatusBadge status={item.status} /></div>
                </div>
              ))}
            </section>
          )}
        </div>

        <aside className={`${ui.panel} ${ui.panelBody} ${client.shopCard}`} aria-labelledby="shop-title">
          {barbershop ? <ShopInfo /> : <SkeletonBlock height={180} />}
        </aside>
      </div>
    </div>
  )
}

function NextTicket({ appointment }: { appointment: Appointment }) {
  const key = dateKey(appointment.data_hora)
  return (
    <article className={client.ticket} aria-label="Próximo horário">
      <div className={client.ticketStub}>
        <span className={client.ticketDay}>{relativeDayLabel(key).split(',')[0]}</span>
        <time className={client.ticketTime} dateTime={appointment.data_hora}>{formatClock(appointment.data_hora)}</time>
        <span className={client.ticketDate}>{dayOfMonth(key)} de {monthShort(key)}</span>
      </div>
      <div className={client.ticketBody}>
        <div className={client.ticketTitle}>
          <h2>{appointment.servico_nome}</h2>
          <StatusBadge status={appointment.status} />
        </div>
        <dl className={client.ticketFacts}>
          <div><dt>Barbeiro</dt><dd>{appointment.barbeiro_nome}</dd></div>
          <div><dt>Duração</dt><dd>{formatDuration(appointment.servico_duracao)}</dd></div>
          <div><dt>Valor</dt><dd>{formatCurrency(appointment.preco_historico ?? appointment.servico_preco)}</dd></div>
        </dl>
        {appointment.status === 'agendado' && (
          <p className={ui.hint}>A barbearia ainda vai confirmar este horário.</p>
        )}
        <div className={ui.buttonRow}>
          <Link to={`/appointments/new?reschedule=${appointment.id}`} className={`${ui.secondaryButton} ${ui.sm}`}>Reagendar</Link>
          <Link to="/appointments" className={`${ui.ghostButton} ${ui.sm}`}>Meus agendamentos</Link>
        </div>
      </div>
    </article>
  )
}

function ShopInfo() {
  const { barbershop } = useBarbershop()
  if (!barbershop) return null
  const status = shopHoursStatus(barbershop)
  return (
    <>
      <div>
        <h2 id="shop-title" style={{ fontSize: 'var(--fs-18)', marginBottom: 'var(--space-2)' }}>{barbershop.nome}</h2>
        <span className={client.shopStatus}>
          <span className={status.open ? client.dotOpen : client.dotClosed} aria-hidden="true" />
          {status.label}
        </span>
      </div>
      <ul className={client.contactList}>
        <li><ClockIcon size={16} /><span>Todos os dias, das {formatTime(barbershop.horario_abertura)} às {formatTime(barbershop.horario_fechamento)}</span></li>
        <li><LocationIcon size={16} /><span>{barbershop.endereco}</span></li>
        <li><PhoneIcon size={16} /><a href={`tel:${barbershop.telefone.replace(/[^\d+]/g, '')}`}>{barbershop.telefone}</a></li>
        <li><MailIcon size={16} /><a href={`mailto:${barbershop.email}`}>{barbershop.email}</a></li>
      </ul>
    </>
  )
}
