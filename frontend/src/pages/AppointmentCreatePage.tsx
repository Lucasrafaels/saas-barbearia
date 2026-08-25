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

export function AppointmentCreatePage() {
  const { user } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [slots, setSlots] = useState<string[]>([])
  const [isLoadingSlots, setIsLoadingSlots] = useState(false)
  const [slotsError, setSlotsError] = useState<string | null>(null)
  const { data, isLoading, error } = useAsyncData(async () => {
    const [services, barbers] = await Promise.all([serviceApi.list(true), barberApi.list()])
    return { services: services.data.results, barbers: barbers.data.results.filter((barber) => barber.ativo) }
  }, [])
  const { register, watch, setValue, handleSubmit, formState: { errors, isSubmitting } } = useForm<AppointmentForm>({
    resolver: zodResolver(schema),
    defaultValues: { data: todayISO(), observacoes: '', horario: '' },
  })
  const serviceId = watch('servico')
  const barberId = watch('barbeiro')
  const date = watch('data')
  const selectedTime = watch('horario')

  useEffect(() => {
    if (!serviceId || !barberId || !date) {
      setSlots([])
      setSlotsError(null)
      return
    }
    let active = true
    setIsLoadingSlots(true)
    setSlotsError(null)
    setValue('horario', '')
    appointmentApi.availableSlots(Number(barberId), Number(serviceId), date)
      .then((response) => { if (active) setSlots(response.data.slots) })
      .catch((requestError) => { if (active) setSlotsError(errorMessage(requestError, 'Não foi possível consultar os horários.')) })
      .finally(() => { if (active) setIsLoadingSlots(false) })
    return () => { active = false }
  }, [barberId, date, serviceId, setValue])

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

  if (isLoading) return <PageLoader label="Preparando o agendamento..." />
  if (error) return <p className={ui.errorBox}>Não foi possível preparar o agendamento.</p>
  if (!data?.services.length || !data.barbers.length) {
    return <EmptyState title="Agendamento indisponível" description="A barbearia precisa ter ao menos um serviço e um barbeiro ativos." />
  }

  return (
    <div className={`${styles.page} ${styles.narrowPage}`}>
      <header className={styles.pageHeader}><div><p className={styles.eyebrow}>Reserve seu horário</p><h1>Novo agendamento</h1></div></header>
      <form className={ui.formCard} onSubmit={handleSubmit(onSubmit)} noValidate>
        <label className={ui.field}>1. Serviço
          <select {...register('servico')}>
            <option value="">Selecione um serviço</option>
            {data.services.map((service) => <option key={service.id} value={service.id}>{service.nome} — {formatCurrency(service.preco)} ({service.duracao} min)</option>)}
          </select>
          {errors.servico && <small className={ui.error}>{errors.servico.message}</small>}
        </label>
        <label className={ui.field}>2. Barbeiro
          <select {...register('barbeiro')}>
            <option value="">Selecione um barbeiro</option>
            {data.barbers.map((barber) => <option key={barber.id} value={barber.id}>{barber.nome}{barber.especialidade ? ` — ${barber.especialidade}` : ''}</option>)}
          </select>
          {errors.barbeiro && <small className={ui.error}>{errors.barbeiro.message}</small>}
        </label>
        <label className={ui.field}>3. Data
          <input type="date" min={todayISO()} {...register('data')} />
          {errors.data && <small className={ui.error}>{errors.data.message}</small>}
        </label>
        <fieldset className={ui.fieldset}>
          <legend>4. Horário disponível</legend>
          {!serviceId || !barberId || !date ? <p className={ui.hint}>Escolha serviço, barbeiro e data para ver os horários.</p> : null}
          {isLoadingSlots && <p className={ui.hint}>Calculando horários...</p>}
          {slotsError && <p className={ui.error}>{slotsError}</p>}
          {!isLoadingSlots && serviceId && barberId && date && !slotsError && (
            slots.length ? <div className={styles.slotGrid}>
              {slots.map((slot) => <button className={selectedTime === slot ? `${styles.slot} ${styles.slotSelected}` : styles.slot} type="button" key={slot} onClick={() => setValue('horario', slot, { shouldValidate: true })}>{slot}</button>)}
            </div> : <p className={ui.hint}>Não há horários disponíveis nesta data.</p>
          )}
          {errors.horario && <small className={ui.error}>{errors.horario.message}</small>}
        </fieldset>
        <label className={ui.field}>Observações (opcional)
          <textarea rows={3} placeholder="Ex.: preferência de corte" {...register('observacoes')} />
          {errors.observacoes && <small className={ui.error}>{errors.observacoes.message}</small>}
        </label>
        <button className={ui.button} disabled={isSubmitting || !selectedTime} type="submit">{isSubmitting ? 'Confirmando...' : 'Confirmar agendamento'}</button>
      </form>
    </div>
  )
}
