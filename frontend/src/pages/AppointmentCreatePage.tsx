import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { appointmentApi, barberApi, serviceApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import { errorMessage, formatCurrency, todayISO } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const schema = z.object({
  servico: z.string().min(1, 'Escolha um serviço.'),
  barbeiro: z.string().min(1, 'Escolha um barbeiro.'),
  data: z.string().min(1, 'Escolha uma data.'),
  horario: z.string().min(1, 'Escolha um horário disponível.'),
  observacoes: z.string().max(500, 'Use no máximo 500 caracteres.').optional(),
})
type AppointmentForm = z.infer<typeof schema>

type Step = 'service' | 'barber' | 'datetime' | 'confirm'

const stepOrder: Step[] = ['service', 'barber', 'datetime', 'confirm']
const stepLabels: Record<Step, string> = {
  service: 'Serviço',
  barber: 'Barbeiro',
  datetime: 'Data e Horário',
  confirm: 'Confirmar',
}

export function AppointmentCreatePage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [slots, setSlots] = useState<string[]>([])
  const [isLoadingSlots, setIsLoadingSlots] = useState(false)
  const [slotsError, setSlotsError] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState<string>(todayISO())
  const [weekStart, setWeekStart] = useState<string>(todayISO())

  const { data, isLoading, error } = useAsyncData(async () => {
    const [services, barbers] = await Promise.all([
      serviceApi.list(true),
      barberApi.list()
    ])
    return {
      services: services.data.results,
      barbers: barbers.data.results.filter((barber) => barber.ativo)
    }
  }, [])

  const {
    register,
    watch,
    setValue,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AppointmentForm>({
    resolver: zodResolver(schema),
    defaultValues: { data: todayISO(), observacoes: '', horario: '' },
  })

  const serviceId = watch('servico')
  const barberId = watch('barbeiro')
  const horario = watch('horario')

  const currentStep = stepOrder[currentStepIndex]
  const canGoNext = () => {
    switch (currentStep) {
      case 'service':
        return Boolean(serviceId)
      case 'barber':
        return Boolean(barberId)
      case 'datetime':
        return Boolean(selectedDate && horario)
      case 'confirm':
        return true
    }
  }

  const goNext = () => {
    if (currentStepIndex < stepOrder.length - 1 && canGoNext()) {
      setCurrentStepIndex(currentStepIndex + 1)
    }
  }

  const goPrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1)
    }
  }

  // Fetch slots when service, barber, or date changes
  useEffect(() => {
    if (!serviceId || !barberId || !selectedDate) {
      setSlots([])
      setSlotsError(null)
      setValue('horario', '')
      return
    }
    let active = true
    setIsLoadingSlots(true)
    setSlotsError(null)
    setValue('horario', '')
    appointmentApi.availableSlots(Number(barberId), Number(serviceId), selectedDate)
      .then((response) => {
        if (active) setSlots(response.data.slots)
      })
      .catch((requestError) => {
        if (active) setSlotsError(errorMessage(requestError, 'Não foi possível consultar os horários.'))
      })
      .finally(() => {
        if (active) setIsLoadingSlots(false)
      })
    return () => { active = false }
  }, [serviceId, barberId, selectedDate, setValue])

  const onSubmit = async (values: AppointmentForm) => {
    if (!user) return
    try {
      await appointmentApi.create({
        cliente: user.id,
        barbeiro: Number(values.barbeiro),
        servico: Number(values.servico),
        data_hora: `${values.data}T${values.horario}:00`,
        observacoes: values.observacoes?.trim(),
      })
      showToast('Agendamento criado com sucesso!', 'success')
      navigate('/appointments')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível criar o agendamento.'), 'error')
    }
  }

  // Generate week dates for date picker
  const getWeekDates = (startDate: string) => {
    const start = new Date(startDate + 'T00:00:00')
    const dates: string[] = []
    for (let i = 0; i < 7; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      dates.push(d.toISOString().split('T')[0])
    }
    return dates
  }

  const weekDates = getWeekDates(weekStart)
  const prevWeek = () => {
    const d = new Date(weekStart + 'T00:00:00')
    d.setDate(d.getDate() - 7)
    setWeekStart(d.toISOString().split('T')[0])
  }
  const nextWeek = () => {
    const d = new Date(weekStart + 'T00:00:00')
    d.setDate(d.getDate() + 7)
    setWeekStart(d.toISOString().split('T')[0])
  }

  const getDayNumber = (dateStr: string) => {
    const d = new Date(dateStr + 'T00:00:00')
    return d.getDate()
  }

  const isToday = (dateStr: string) => dateStr === todayISO()
  const isPast = (dateStr: string) => dateStr < todayISO()
  const isSelected = (dateStr: string) => dateStr === selectedDate

  const handleDateClick = (dateStr: string) => {
    if (isPast(dateStr)) return
    setSelectedDate(dateStr)
    setValue('data', dateStr)
    setValue('horario', '')
    // Auto-advance to next step if we have slots
    setTimeout(() => {
      if (slots.length > 0 && currentStep === 'datetime') {
        goNext()
      }
    }, 300)
  }

  if (isLoading) return <PageLoader label="Preparando o agendamento..." />
  if (error) return <p className={ui.errorBox}>Não foi possível preparar o agendamento.</p>
  if (!data?.services.length || !data.barbers.length) {
    return (
      <div className={`${styles.page} ${styles.narrowPage}`}>
        <header className={styles.pageHeader}>
          <div><p className={styles.eyebrow}>Reserve seu horário</p><h1>Novo agendamento</h1></div>
        </header>
        <EmptyState title="Agendamento indisponível" description="A barbearia precisa ter ao menos um serviço e um barbeiro ativos." />
      </div>
    )
  }

  const selectedService = data.services.find(s => s.id === Number(serviceId))
  const selectedBarber = data.barbers.find(b => b.id === Number(barberId))

  return (
    <div className={`${styles.page} ${styles.narrowPage}`}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Reserve seu horário</p>
          <h1>Novo agendamento</h1>
        </div>
      </header>

      {/* Stepper */}
      <nav className={ui.stepper} aria-label="Progresso do agendamento">
        {stepOrder.map((step, index) => (
          <div
            key={step}
            className={`${ui.stepperItem} ${
              index < currentStepIndex ? ui.stepperItemCompleted :
              index === currentStepIndex ? ui.stepperItemActive : ''
            }`}
          >
            <div className={ui.stepperStep}>
              {index < currentStepIndex ? '' : index + 1}
            </div>
            <span className={ui.stepperLabel}>{stepLabels[step]}</span>
          </div>
        ))}
      </nav>

      <form className={ui.formCard} onSubmit={handleSubmit(onSubmit)} noValidate>
        {/* Step 1: Service Selection */}
        {currentStep === 'service' && (
          <>
            <h2 style={{ marginBottom: 'var(--space-6)', color: 'var(--color-text-primary)', fontSize: 'var(--text-xl)' }}>
              Qual serviço você deseja?
            </h2>
            <div className={styles.cardGrid}>
              {data.services.map((service) => (
                <button
                  key={service.id}
                  type="button"
                  className={`${ui.serviceCardEnhanced} ${
                    serviceId === String(service.id) ? ui.serviceCardEnhancedSelected : ''
                  }`}
                  onClick={() => {
                    setValue('servico', String(service.id))
                    setTimeout(goNext, 200)
                  }}
                  aria-pressed={serviceId === String(service.id)}
                >
                  <div className={ui.serviceCardHeader}>
                    <div className={ui.serviceCardTitle}>
                      <div className={ui.serviceCardIcon} aria-hidden="true">✂</div>
                      <div className={ui.serviceCardInfo}>
                        <h3>{service.nome}</h3>
                        {service.descricao && <p>{service.descricao}</p>}
                      </div>
                    </div>
                    <div className={ui.serviceCardMeta}>
                      <span className={ui.serviceCardPrice}>{formatCurrency(service.preco)}</span>
                      <span className={ui.serviceCardDuration}>{service.duracao} min</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <div className={ui.buttonRow} style={{ marginTop: 'var(--space-6)', justifyContent: 'flex-end' }}>
              <button type="button" className={ui.secondaryButton} disabled onClick={goPrev}>Voltar</button>
              <button type="button" className={ui.button} disabled={!serviceId} onClick={goNext}>Próximo</button>
            </div>
          </>
        )}

        {/* Step 2: Barber Selection */}
        {currentStep === 'barber' && (
          <>
            <h2 style={{ marginBottom: 'var(--space-6)', color: 'var(--color-text-primary)', fontSize: 'var(--text-xl)' }}>
              Com qual barbeiro?
            </h2>
            <div className={styles.cardGrid}>
              {data.barbers.map((barber) => (
                <button
                  key={barber.id}
                  type="button"
                  className={`${ui.barberCardEnhanced} ${
                    barberId === String(barber.id) ? ui.barberCardEnhancedSelected : ''
                  }`}
                  onClick={() => {
                    setValue('barbeiro', String(barber.id))
                    setTimeout(goNext, 200)
                  }}
                  aria-pressed={barberId === String(barber.id)}
                >
                  <div className={ui.barberCardAvatar} aria-hidden="true">
                    {barber.nome.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                  </div>
                  <h3>{barber.nome}</h3>
                  {barber.especialidade && <p className={ui.barberCardSpecialty}>{barber.especialidade}</p>}
                  <div className={ui.barberCardMeta}>
                    <span className={ui.barberCardMetaItem}>
                      <span aria-hidden="true">✓</span> Ativo
                    </span>
                  </div>
                </button>
              ))}
            </div>
            <div className={ui.buttonRow} style={{ marginTop: 'var(--space-6)' }}>
              <button type="button" className={ui.secondaryButton} onClick={goPrev}>Voltar</button>
              <button type="button" className={ui.button} disabled={!barberId} onClick={goNext}>Próximo</button>
            </div>
          </>
        )}

        {/* Step 3: Date & Time Selection */}
        {currentStep === 'datetime' && (
          <>
            <h2 style={{ marginBottom: 'var(--space-6)', color: 'var(--color-text-primary)', fontSize: 'var(--text-xl)' }}>
              Escolha a data e o horário
            </h2>

            {/* Week navigation */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
              <button type="button" className={ui.ghostButton} onClick={prevWeek} aria-label="Semana anterior">‹</button>
              <span style={{ fontWeight: 'var(--font-weight-semibold)', color: 'var(--color-text-primary)' }}>
                {new Date(weekStart + 'T00:00:00').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}
              </span>
              <button type="button" className={ui.ghostButton} onClick={nextWeek} aria-label="Próxima semana">›</button>
            </div>

            {/* Date grid */}
            <div className={ui.dateGrid} role="grid" aria-label="Selecione a data">
              {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((day) => (
                <div key={day} className={`${ui.dateGridDay} ${ui.dateGridWeekday}`} role="columnheader">{day}</div>
              ))}
              {weekDates.map((date) => (
                <button
                  key={date}
                  type="button"
                  className={`${ui.dateGridDay} ${
                    isSelected(date) ? ui.dateGridDaySelected : ''
                  } ${isToday(date) ? ui.dateGridDayToday : ''} ${isPast(date) ? ui.dateGridDayDisabled : ''}`}
                  onClick={() => handleDateClick(date)}
                  disabled={isPast(date)}
                  aria-selected={isSelected(date)}
                  aria-disabled={isPast(date)}
                  aria-label={new Date(date + 'T00:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                >
                  {getDayNumber(date)}
                </button>
              ))}
            </div>

            {/* Time slots */}
            {!serviceId || !barberId ? (
              <p className={ui.hint} style={{ marginTop: 'var(--space-4)', textAlign: 'center' }}>
                Escolha serviço e barbeiro para ver os horários.
              </p>
            ) : isLoadingSlots ? (
              <div className={ui.loaderWrap} style={{ marginTop: 'var(--space-4)' }}>
                <div className={ui.spinner} />
                <span>Calculando horários disponíveis...</span>
              </div>
            ) : slotsError ? (
              <p className={ui.error} style={{ marginTop: 'var(--space-4)', textAlign: 'center' }}>{slotsError}</p>
            ) : slots.length === 0 ? (
              <p className={ui.hint} style={{ marginTop: 'var(--space-4)', textAlign: 'center' }}>
                Não há horários disponíveis nesta data. Escolha outra data.
              </p>
            ) : (
              <div className={ui.slotGrid} style={{ marginTop: 'var(--space-4)' }} role="listbox" aria-label="Horários disponíveis">
                {slots.map((slot) => (
                  <button
                    key={slot}
                    type="button"
                    role="option"
                    aria-selected={horario === slot}
                    className={`${ui.slot} ${horario === slot ? ui.slotSelected : ''}`}
                    onClick={() => setValue('horario', slot, { shouldValidate: true })}
                  >
                    {slot}
                  </button>
                ))}
              </div>
            )}

            <div className={ui.buttonRow} style={{ marginTop: 'var(--space-6)' }}>
              <button type="button" className={ui.secondaryButton} onClick={goPrev}>Voltar</button>
              <button type="button" className={ui.button} disabled={!horario} onClick={goNext}>Próximo</button>
            </div>
          </>
        )}

        {/* Step 4: Confirmation */}
        {currentStep === 'confirm' && (
          <>
            <h2 style={{ marginBottom: 'var(--space-6)', color: 'var(--color-text-primary)', fontSize: 'var(--text-xl)' }}>
              Confirme seu agendamento
            </h2>

            <div className={ui.confirmSummary}>
              <div className={ui.confirmSummaryItem}>
                <span className={ui.confirmSummaryLabel}>Serviço</span>
                <span className={ui.confirmSummaryValue}>
                  {selectedService?.nome}
                  <br />
                  <small style={{ color: 'var(--color-text-muted)', fontWeight: 'var(--font-weight-normal)' }}>
                    {selectedService?.duracao} min · {formatCurrency(selectedService?.preco ?? 0)}
                  </small>
                </span>
              </div>
              <div className={ui.confirmSummaryItem}>
                <span className={ui.confirmSummaryLabel}>Barbeiro</span>
                <span className={ui.confirmSummaryValue}>{selectedBarber?.nome}</span>
              </div>
              <div className={ui.confirmSummaryItem}>
                <span className={ui.confirmSummaryLabel}>Data</span>
                <span className={ui.confirmSummaryValue}>
                  {new Date(selectedDate + 'T00:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
                </span>
              </div>
              <div className={ui.confirmSummaryItem}>
                <span className={ui.confirmSummaryLabel}>Horário</span>
                <span className={ui.confirmSummaryValue}>{horario}</span>
              </div>
              <div className={ui.confirmSummaryItem}>
                <span className={ui.confirmSummaryLabel}>Total</span>
                <span className={ui.confirmSummaryValue}>
                  <strong>{formatCurrency(selectedService?.preco ?? 0)}</strong>
                </span>
              </div>
            </div>

            <label className={ui.field} style={{ marginTop: 'var(--space-2)' }}>
              Observações (opcional)
              <textarea rows={3} placeholder="Ex.: preferência de corte, alergias, etc." {...register('observacoes')} />
              {errors.observacoes && <small className={ui.error}>{errors.observacoes.message}</small>}
            </label>

            <div className={ui.buttonRow} style={{ marginTop: 'var(--space-4)' }}>
              <button type="button" className={ui.secondaryButton} onClick={goPrev}>Voltar</button>
              <button type="submit" className={ui.button} disabled={isSubmitting}>
                {isSubmitting ? 'Confirmando...' : 'Confirmar agendamento'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  )
}