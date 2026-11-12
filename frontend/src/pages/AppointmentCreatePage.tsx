import axios from 'axios'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { appointmentApi, listActiveBarbers, listActiveServices } from '../api/endpoints'
import { Avatar, ButtonSpinner } from '../components/Controls'
import { EmptyState, ErrorState, PageLoader } from '../components/Feedback'
import { AlertCircleIcon, ArrowLeftIcon, CheckIcon, ClockIcon, InfoIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Appointment, Barber, Service } from '../types'
import {
  addDays, dateKey, dayOfMonth, errorMessage, formatClock, formatCurrency, formatDayLong, formatDuration, monthShort,
  relativeDayLabel, todayISO, weekdayShort,
} from '../utils/format'
import { isOpenStatus, notifyAppointmentsChanged } from '../utils/status'
import client from '../styles/client.module.css'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

type Step = 'service' | 'barber' | 'datetime' | 'confirm'
const steps: Step[] = ['service', 'barber', 'datetime', 'confirm']
const stepLabels: Record<Step, string> = { service: 'Serviço', barber: 'Barbeiro', datetime: 'Data e horário', confirm: 'Confirmação' }
const DAYS_AHEAD = 21
const NOTE_LIMIT = 500

function groupSlots(slots: string[]) {
  const groups = [
    { label: 'Manhã', items: slots.filter((slot) => slot < '12:00') },
    { label: 'Tarde', items: slots.filter((slot) => slot >= '12:00' && slot < '18:00') },
    { label: 'Noite', items: slots.filter((slot) => slot >= '18:00') },
  ]
  return groups.filter((group) => group.items.length > 0)
}

export function AppointmentCreatePage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const rescheduleId = params.get('reschedule')
  const presetService = params.get('servico')
  const presetBarber = params.get('barbeiro')

  const catalog = useAsyncData(async () => {
    const [services, barbers] = await Promise.all([listActiveServices(), listActiveBarbers()])
    return { services, barbers }
  }, [])

  const original = useAsyncData<Appointment | null>(
    () => (rescheduleId ? appointmentApi.get(Number(rescheduleId)).then((response) => response.data) : Promise.resolve(null)),
    [rescheduleId],
  )

  const [serviceId, setServiceId] = useState<number | null>(presetService ? Number(presetService) : null)
  const [barberId, setBarberId] = useState<number | null>(presetBarber ? Number(presetBarber) : null)
  const [day, setDay] = useState(todayISO())
  const [slot, setSlot] = useState('')
  const [notes, setNotes] = useState('')
  const [step, setStep] = useState<Step>(presetService ? (presetBarber ? 'datetime' : 'barber') : 'service')
  const [slots, setSlots] = useState<string[]>([])
  const [slotsLoading, setSlotsLoading] = useState(false)
  const [slotsError, setSlotsError] = useState<unknown>(null)
  const [slotsVersion, setSlotsVersion] = useState(0)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Reagendamento: pré-preenche com o agendamento original
  const [prefilledFrom, setPrefilledFrom] = useState<number | null>(null)
  if (original.data && prefilledFrom !== original.data.id) {
    setPrefilledFrom(original.data.id)
    setServiceId(original.data.servico)
    setBarberId(original.data.barbeiro)
    const originalDay = dateKey(original.data.data_hora)
    setDay(originalDay < todayISO() ? todayISO() : originalDay)
    setNotes(original.data.observacoes ?? '')
    setStep('datetime')
  }

  const isRescheduling = Boolean(rescheduleId && original.data)

  // Horários livres reais para serviço + barbeiro + dia
  useEffect(() => {
    if (!serviceId || !barberId) {
      setSlots([])
      return
    }
    let active = true
    setSlotsLoading(true)
    setSlotsError(null)
    appointmentApi.availableSlots(barberId, serviceId, day, isRescheduling && original.data ? original.data.id : undefined)
      .then((response) => { if (active) setSlots(response.data.slots) })
      .catch((requestError) => { if (active) { setSlots([]); setSlotsError(requestError) } })
      .finally(() => { if (active) setSlotsLoading(false) })
    return () => { active = false }
  }, [serviceId, barberId, day, isRescheduling, original.data, slotsVersion])

  // Horário escolhido deixa de valer se não estiver mais na lista
  useEffect(() => {
    if (slot && !slotsLoading && !slots.includes(slot)) setSlot('')
  }, [slots, slot, slotsLoading])

  const days = useMemo(() => Array.from({ length: DAYS_AHEAD }, (_, index) => addDays(todayISO(), index)), [])

  if (catalog.isLoading || original.isLoading) return <PageLoader label="Preparando o agendamento…" />

  if (catalog.error && !catalog.data) {
    return (
      <div className={`${page.page} ${page.medium}`}>
        <PageHeader title="Agendar horário" />
        <div className={ui.panel}><ErrorState error={catalog.error} fallback="Não foi possível carregar serviços e barbeiros." onRetry={() => void catalog.reload()} /></div>
      </div>
    )
  }

  if (rescheduleId && (original.error || (original.data && !isOpenStatus(original.data.status)))) {
    return (
      <div className={`${page.page} ${page.medium}`}>
        <PageHeader title="Reagendar horário" back={{ to: '/appointments', label: 'Meus agendamentos' }} />
        <div className={ui.panel}>
          {original.error
            ? <ErrorState error={original.error} fallback="Não foi possível carregar o agendamento." onRetry={() => void original.reload()} />
            : <EmptyState title="Este horário não pode ser reagendado" description="Somente horários agendados ou confirmados podem ser alterados." action={{ label: 'Voltar para meus agendamentos', to: '/appointments' }} />}
        </div>
      </div>
    )
  }

  const services = catalog.data?.services ?? []
  const barbers = catalog.data?.barbers ?? []

  if (!services.length || !barbers.length) {
    return (
      <div className={`${page.page} ${page.medium}`}>
        <PageHeader title="Agendar horário" />
        <div className={ui.panel}>
          <EmptyState title="Agendamento indisponível no momento" description="A barbearia ainda não tem serviços e barbeiros ativos para agendamento. Fale com a barbearia pelos contatos da página inicial." action={{ label: 'Voltar ao início', to: '/' }} />
        </div>
      </div>
    )
  }

  const service = services.find((item) => item.id === serviceId) ?? null
  const barber = barbers.find((item) => item.id === barberId) ?? null

  // Pré-seleção inválida (ex.: link para serviço desativado): volta para a etapa certa
  if (serviceId !== null && !service) {
    setServiceId(null)
    setStep('service')
  } else if (barberId !== null && !barber) {
    setBarberId(null)
    if (step === 'datetime' || step === 'confirm') setStep('barber')
  }
  const stepIndex = steps.indexOf(step)

  const nextIncomplete = (selected: { service?: Service | null; barber?: Barber | null }): Step => {
    const s = selected.service !== undefined ? selected.service : service
    const b = selected.barber !== undefined ? selected.barber : barber
    if (!s) return 'service'
    if (!b) return 'barber'
    return 'datetime'
  }

  const chooseService = (item: Service) => {
    setServiceId(item.id)
    setSlot('')
    setStep(nextIncomplete({ service: item }))
  }

  const chooseBarber = (item: Barber) => {
    setBarberId(item.id)
    setSlot('')
    setStep('datetime')
  }

  const canOpen = (target: Step) => {
    if (target === 'service') return true
    if (target === 'barber') return Boolean(service)
    if (target === 'datetime') return Boolean(service && barber)
    return Boolean(service && barber && slot)
  }

  const submit = async () => {
    if (!user || !service || !barber || !slot) return
    if (notes.length > NOTE_LIMIT) return
    setSubmitting(true)
    setSubmitError(null)
    const payload = { barbeiro: barber.id, servico: service.id, data_hora: `${day}T${slot}:00`, observacoes: notes.trim() }
    try {
      if (isRescheduling && original.data) {
        await appointmentApi.update(original.data.id, payload)
        showToast(`Horário remarcado para ${relativeDayLabel(day).toLowerCase()} às ${slot}.`, 'success')
      } else {
        await appointmentApi.create({ cliente: user.id, ...payload })
        showToast(`Horário agendado para ${relativeDayLabel(day).toLowerCase()} às ${slot}.`, 'success')
      }
      notifyAppointmentsChanged()
      navigate('/appointments')
    } catch (requestError) {
      const message = errorMessage(requestError, isRescheduling ? 'Não foi possível reagendar.' : 'Não foi possível concluir o agendamento.')
      const conflict = axios.isAxiosError(requestError) && requestError.response?.status === 400
        && Boolean((requestError.response.data as Record<string, unknown> | undefined)?.data_hora)
      setSubmitError(message)
      if (conflict) {
        // O horário foi ocupado enquanto o cliente decidia: volta para escolher outro
        setSlot('')
        setSlotsVersion((value) => value + 1)
        setStep('datetime')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={`${page.page} ${page.medium}`}>
      <PageHeader
        title={isRescheduling ? 'Reagendar horário' : 'Agendar horário'}
        description={isRescheduling && original.data
          ? `Horário atual: ${formatDayLong(dateKey(original.data.data_hora))} às ${formatClock(original.data.data_hora)}. Ele só muda quando você confirmar o novo.`
          : 'Escolha o serviço, o barbeiro e um horário livre.'}
        back={isRescheduling ? { to: '/appointments', label: 'Meus agendamentos' } : undefined}
      />

      <ol className={client.steps} aria-label="Etapas do agendamento">
        {steps.map((item, index) => {
          const state = index < stepIndex ? client.stepDone : index === stepIndex ? client.stepCurrent : ''
          return (
            <li key={item} className={`${client.step} ${state}`} aria-current={item === step ? 'step' : undefined}>
              <span className={client.stepBar} />
              <span className={client.stepLabel}>
                {index < stepIndex && canOpen(item)
                  ? <button type="button" className={client.stepButton} onClick={() => setStep(item)}>{stepLabels[item]}</button>
                  : stepLabels[item]}
              </span>
            </li>
          )
        })}
      </ol>

      <div className={client.bookingLayout}>
        <section className={`${ui.panel} ${ui.panelBody}`}>
          {step === 'service' && (
            <div className={client.stepPanel} key="service">
              <h2>Qual serviço?</h2>
              <p className={client.stepIntro}>O preço e a duração ficam registrados no agendamento.</p>
              <div className={client.optionGrid} role="radiogroup" aria-label="Serviços">
                {services.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="radio"
                    aria-checked={item.id === serviceId}
                    className={`${client.option} ${item.id === serviceId ? client.optionSelected : ''}`}
                    onClick={() => chooseService(item)}
                  >
                    <span className={client.optionCheck} aria-hidden="true"><CheckIcon size={12} strokeWidth={3} /></span>
                    <span className={client.optionTitle}>{item.nome}</span>
                    {item.descricao && <span className={client.optionDesc}>{item.descricao}</span>}
                    <span className={client.optionMeta}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><ClockIcon size={14} /> {formatDuration(item.duracao)}</span>
                      <strong>{formatCurrency(item.preco)}</strong>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 'barber' && (
            <div className={client.stepPanel} key="barber">
              <h2>Com quem?</h2>
              <p className={client.stepIntro}>Os horários livres dependem da agenda de cada barbeiro.</p>
              <div className={client.optionGrid} role="radiogroup" aria-label="Barbeiros">
                {barbers.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="radio"
                    aria-checked={item.id === barberId}
                    className={`${client.option} ${item.id === barberId ? client.optionSelected : ''}`}
                    onClick={() => chooseBarber(item)}
                  >
                    <span className={client.optionCheck} aria-hidden="true"><CheckIcon size={12} strokeWidth={3} /></span>
                    <span className={client.optionPerson}>
                      <Avatar name={item.nome} />
                      <span style={{ display: 'grid' }}>
                        <span className={client.optionTitle}>{item.nome}</span>
                        <span className={client.optionDesc}>{item.especialidade || 'Barbeiro'}</span>
                      </span>
                    </span>
                  </button>
                ))}
              </div>
              <StepActions onBack={() => setStep('service')} />
            </div>
          )}

          {step === 'datetime' && (
            <div className={client.stepPanel} key="datetime">
              <h2>Quando?</h2>
              <p className={client.stepIntro}>Horários livres de {barber?.nome.split(' ')[0]} para {service?.nome.toLowerCase()} ({formatDuration(service?.duracao ?? 0)}).</p>
              {submitError && (
                <div className={`${ui.alert} ${ui.alertDanger}`} role="alert" style={{ marginBottom: 'var(--space-4)' }}>
                  <AlertCircleIcon size={18} />
                  <div><strong>Esse horário não está mais disponível.</strong><p>{submitError} Escolha outro horário abaixo.</p></div>
                </div>
              )}
              <div className={client.dateStrip} role="radiogroup" aria-label="Dia">
                {days.map((key) => (
                  <button
                    key={key}
                    type="button"
                    role="radio"
                    aria-checked={key === day}
                    aria-label={relativeDayLabel(key) === formatDayLong(key) ? formatDayLong(key) : `${relativeDayLabel(key)}, ${formatDayLong(key)}`}
                    className={`${client.dateChip} ${key === day ? client.dateChipSelected : ''} ${key === todayISO() ? client.dateChipToday : ''}`}
                    onClick={() => { setDay(key); setSlot(''); setSubmitError(null) }}
                  >
                    <span>{key === todayISO() ? 'hoje' : weekdayShort(key)}</span>
                    <strong>{dayOfMonth(key)}</strong>
                    <span>{monthShort(key)}</span>
                  </button>
                ))}
              </div>

              <div aria-live="polite">
                {slotsLoading ? (
                  <div className={ui.loaderWrap} style={{ minHeight: '8rem' }}><span className={ui.spinner} aria-hidden="true" /> Consultando horários livres…</div>
                ) : slotsError ? (
                  <ErrorState compact error={slotsError} fallback="Não foi possível consultar os horários." onRetry={() => setSlotsVersion((value) => value + 1)} />
                ) : slots.length === 0 ? (
                  <EmptyState
                    compact
                    title={`Sem horários livres ${day === todayISO() ? 'hoje' : 'neste dia'}`}
                    description="A agenda deste barbeiro está cheia ou o horário de funcionamento já terminou."
                    action={{ label: 'Ver o próximo dia', onClick: () => { setDay(addDays(day, 1)); setSlot('') } }}
                  />
                ) : (
                  <div className={client.slotGroups}>
                    {groupSlots(slots).map((group) => (
                      <div className={client.slotGroup} key={group.label}>
                        <h3>{group.label}</h3>
                        <div className={client.slotGrid} role="radiogroup" aria-label={`Horários da ${group.label.toLowerCase()}`}>
                          {group.items.map((item) => (
                            <button
                              key={item}
                              type="button"
                              role="radio"
                              aria-checked={item === slot}
                              className={`${client.slot} ${item === slot ? client.slotSelected : ''}`}
                              onClick={() => { setSlot(item); setSubmitError(null) }}
                            >
                              {item}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <StepActions onBack={() => setStep('barber')} onNext={() => setStep('confirm')} nextDisabled={!slot} nextLabel="Revisar" />
            </div>
          )}

          {step === 'confirm' && service && barber && (
            <div className={client.stepPanel} key="confirm">
              <h2>Tudo certo?</h2>
              <p className={client.stepIntro}>Revise os dados antes de {isRescheduling ? 'remarcar' : 'confirmar'}.</p>
              {submitError && (
                <div className={`${ui.alert} ${ui.alertDanger}`} role="alert" style={{ marginBottom: 'var(--space-4)' }}>
                  <AlertCircleIcon size={18} /><p>{submitError}</p>
                </div>
              )}
              <dl className={ui.summaryList} style={{ marginBottom: 'var(--space-5)' }}>
                <div className={ui.summaryItem}><dt>Quando</dt><dd>{relativeDayLabel(day)}{day === todayISO() || day === addDays(todayISO(), 1) ? `, ${formatDayLong(day)}` : ''}, às {slot}</dd></div>
                <div className={ui.summaryItem}><dt>Serviço</dt><dd>{service.nome}</dd></div>
                <div className={ui.summaryItem}><dt>Barbeiro</dt><dd>{barber.nome}</dd></div>
                <div className={ui.summaryItem}><dt>Duração</dt><dd>{formatDuration(service.duracao)}</dd></div>
              </dl>
              <div className={ui.field}>
                <label className={ui.label} htmlFor="booking-notes">Observações <span className={ui.optional}>(opcional)</span></label>
                <textarea
                  id="booking-notes"
                  rows={3}
                  value={notes}
                  maxLength={NOTE_LIMIT + 50}
                  aria-invalid={notes.length > NOTE_LIMIT ? true : undefined}
                  aria-describedby="booking-notes-hint"
                  placeholder="Ex.: prefiro máquina baixa nas laterais."
                  onChange={(event) => setNotes(event.target.value)}
                />
                <p id="booking-notes-hint" className={notes.length > NOTE_LIMIT ? ui.error : ui.hint}>
                  {notes.length > NOTE_LIMIT ? `Use no máximo ${NOTE_LIMIT} caracteres (${notes.length} agora).` : 'O barbeiro vê esta observação na agenda.'}
                </p>
              </div>
              {!isRescheduling && (
                <p className={`${ui.alert} ${ui.alertInfo}`} style={{ marginTop: 'var(--space-4)' }}>
                  <InfoIcon size={18} /> O horário fica como agendado até a barbearia confirmar. Você pode reagendar ou cancelar em Meus agendamentos.
                </p>
              )}
              <div className={client.stepActions}>
                <button type="button" className={ui.secondaryButton} onClick={() => setStep('datetime')} disabled={submitting}>
                  <ArrowLeftIcon size={16} /> Voltar
                </button>
                <button type="button" className={ui.button} onClick={() => void submit()} disabled={submitting || notes.length > NOTE_LIMIT}>
                  {submitting && <ButtonSpinner />} {isRescheduling ? 'Remarcar horário' : 'Confirmar agendamento'}
                </button>
              </div>
            </div>
          )}
        </section>

        <aside className={`${ui.panel} ${ui.panelBody} ${client.summary}`} aria-label="Resumo do agendamento">
          <h2 className={client.summaryTitle}>Resumo</h2>
          <dl className={ui.summaryList}>
            <div className={ui.summaryItem}><dt>Serviço</dt><dd className={service ? undefined : client.summaryEmpty}>{service?.nome ?? 'A escolher'}</dd></div>
            <div className={ui.summaryItem}><dt>Barbeiro</dt><dd className={barber ? undefined : client.summaryEmpty}>{barber?.nome ?? 'A escolher'}</dd></div>
            <div className={ui.summaryItem}>
              <dt>Horário</dt>
              <dd className={slot ? undefined : client.summaryEmpty}>{slot ? `${relativeDayLabel(day)}, ${slot}` : 'A escolher'}</dd>
            </div>
          </dl>
          <div className={client.summaryTotal}>
            <span>Total</span>
            <strong>{service ? formatCurrency(service.preco) : '—'}</strong>
          </div>
          {isRescheduling && <Link to="/appointments" className={ui.textButton} style={{ marginTop: 'var(--space-3)' }}>Desistir e manter o horário atual</Link>}
        </aside>
      </div>
    </div>
  )
}

function StepActions({ onBack, onNext, nextDisabled, nextLabel = 'Continuar' }: { onBack: () => void; onNext?: () => void; nextDisabled?: boolean; nextLabel?: string }) {
  return (
    <div className={client.stepActions}>
      <button type="button" className={ui.secondaryButton} onClick={onBack}><ArrowLeftIcon size={16} /> Voltar</button>
      {onNext && <button type="button" className={ui.button} onClick={onNext} disabled={nextDisabled}>{nextLabel}</button>}
    </div>
  )
}
