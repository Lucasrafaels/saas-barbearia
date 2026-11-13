import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { barbershopApi } from '../api/endpoints'
import { ButtonSpinner, Field, fieldA11y } from '../components/Controls'
import { ErrorState, SkeletonBlock } from '../components/Feedback'
import { AlertCircleIcon, ClockIcon } from '../components/Icons'
import { PageHeader } from '../components/PageHeader'
import { useBarbershop } from '../contexts/BarbershopContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage, fieldErrors, formatDayShort, formatDuration, dateKey, formatTime, timeToMinutes } from '../utils/format'
import { formatOpenDays, openDays, WEEKDAYS } from '../utils/shop'
import page from '../styles/page.module.css'
import settings from '../styles/settings.module.css'
import ui from '../styles/ui.module.css'

const schema = z.object({
  nome: z.string().trim().min(2, 'Informe o nome da barbearia.').max(150, 'Use no máximo 150 caracteres.'),
  email: z.string().trim().email('Informe um e-mail válido.'),
  telefone: z.string().trim().min(8, 'Informe um telefone com DDD.').max(20, 'Use no máximo 20 caracteres.'),
  endereco: z.string().trim().min(5, 'Informe o endereço completo.').max(255, 'Use no máximo 255 caracteres.'),
  horario_abertura: z.string().regex(/^\d{2}:\d{2}$/, 'Informe o horário de abertura.'),
  horario_fechamento: z.string().regex(/^\d{2}:\d{2}$/, 'Informe o horário de fechamento.'),
  // Caixas de seleção com o mesmo nome: o formulário entrega os valores marcados como texto
  dias_funcionamento: z.array(z.string()).min(1, 'Marque ao menos um dia de funcionamento.'),
}).refine((values) => timeToMinutes(values.horario_fechamento) > timeToMinutes(values.horario_abertura), {
  message: 'O fechamento precisa ser depois da abertura.',
  path: ['horario_fechamento'],
})
type Form = z.infer<typeof schema>

export function AdminBarbershopPage() {
  const { barbershop, isLoading, error, reload, setBarbershop } = useBarbershop()
  const { showToast } = useToast()
  const { register, handleSubmit, reset, watch, setError, formState: { errors, isSubmitting, isDirty } } = useForm<Form>({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (!barbershop) return
    reset({
      nome: barbershop.nome,
      email: barbershop.email,
      telefone: barbershop.telefone,
      endereco: barbershop.endereco,
      horario_abertura: formatTime(barbershop.horario_abertura),
      horario_fechamento: formatTime(barbershop.horario_fechamento),
      dias_funcionamento: openDays(barbershop).map(String),
    })
  }, [barbershop, reset])

  const opens = watch('horario_abertura')
  const closes = watch('horario_fechamento')
  const openMinutes = opens && closes ? timeToMinutes(closes) - timeToMinutes(opens) : 0
  const selectedDays = (watch('dias_funcionamento') ?? []).map(Number)

  const onSubmit = async (values: Form) => {
    if (!barbershop) return
    try {
      const { data } = await barbershopApi.update(barbershop.id, {
        ...values,
        horario_abertura: `${values.horario_abertura}:00`,
        horario_fechamento: `${values.horario_fechamento}:00`,
        dias_funcionamento: values.dias_funcionamento.map(Number).sort((a, b) => a - b),
      })
      setBarbershop(data)
      showToast('Dados da barbearia salvos.', 'success')
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      for (const key of ['nome', 'email', 'telefone', 'endereco', 'horario_abertura', 'horario_fechamento', 'dias_funcionamento'] as const) {
        if (fields[key]) setError(key, { message: fields[key] })
      }
      showToast(errorMessage(requestError, 'Não foi possível salvar os dados.'), 'error')
    }
  }

  return (
    <div className={`${page.page} ${page.medium}`}>
      <PageHeader title="Dados da barbearia" description="Informações exibidas para clientes e equipe, e o horário que define a agenda." />

      {isLoading ? (
        <SkeletonBlock height={420} />
      ) : !barbershop ? (
        <div className={ui.panel}><ErrorState error={error} fallback="Não foi possível carregar a barbearia." onRetry={() => void reload()} /></div>
      ) : (
        <form className={page.stack} onSubmit={handleSubmit(onSubmit)} noValidate>
          <section className={settings.section}>
            <div className={settings.intro}>
              <h2>Identificação e contato</h2>
              <p>Os clientes veem esses dados na tela inicial e ao agendar.</p>
              <ul className={settings.facts}>
                <li>Cadastrada em {formatDayShort(dateKey(barbershop.created_at))}</li>
              </ul>
            </div>
            <div className={`${ui.panel} ${ui.panelBody} ${ui.form}`}>
              <Field label="Nome da barbearia" htmlFor="shop-nome" error={errors.nome?.message}>
                <input {...fieldA11y('shop-nome', errors.nome?.message)} {...register('nome')} />
              </Field>
              <div className={ui.fieldRow}>
                <Field label="E-mail de contato" htmlFor="shop-email" error={errors.email?.message}>
                  <input {...fieldA11y('shop-email', errors.email?.message)} type="email" {...register('email')} />
                </Field>
                <Field label="Telefone" htmlFor="shop-telefone" error={errors.telefone?.message}>
                  <input {...fieldA11y('shop-telefone', errors.telefone?.message)} type="tel" inputMode="tel" {...register('telefone')} />
                </Field>
              </div>
              <Field label="Endereço" htmlFor="shop-endereco" error={errors.endereco?.message}>
                <input {...fieldA11y('shop-endereco', errors.endereco?.message)} autoComplete="street-address" {...register('endereco')} />
              </Field>
            </div>
          </section>

          <section className={settings.section}>
            <div className={settings.intro}>
              <h2>Horário de funcionamento</h2>
              <p>Os horários livres oferecidos aos clientes começam na abertura e terminam quando o serviço ainda cabe antes do fechamento. O mesmo horário vale para todos os dias marcados; nos outros, a barbearia não recebe agendamentos.</p>
            </div>
            <div className={`${ui.panel} ${ui.panelBody} ${ui.form}`}>
              <fieldset className={settings.days} aria-describedby={errors.dias_funcionamento ? 'shop-dias-error' : undefined}>
                <legend className={ui.label}>Dias de funcionamento</legend>
                <div className={settings.dayToggles}>
                  {WEEKDAYS.map((weekday) => (
                    <label key={weekday.iso} className={settings.dayToggle}>
                      <input type="checkbox" value={String(weekday.iso)} {...register('dias_funcionamento')} />
                      <span><abbr title={weekday.name}>{weekday.short}</abbr></span>
                    </label>
                  ))}
                </div>
                {errors.dias_funcionamento && (
                  <p className={ui.error} id="shop-dias-error"><AlertCircleIcon size={14} />{errors.dias_funcionamento.message}</p>
                )}
              </fieldset>
              <div className={ui.fieldRow}>
                <Field label="Abre às" htmlFor="shop-abertura" error={errors.horario_abertura?.message}>
                  <input {...fieldA11y('shop-abertura', errors.horario_abertura?.message)} type="time" step={900} {...register('horario_abertura')} />
                </Field>
                <Field label="Fecha às" htmlFor="shop-fechamento" error={errors.horario_fechamento?.message}>
                  <input {...fieldA11y('shop-fechamento', errors.horario_fechamento?.message)} type="time" step={900} {...register('horario_fechamento')} />
                </Field>
              </div>
              {openMinutes > 0 && (
                <p className={settings.hoursPreview}>
                  <ClockIcon size={18} />
                  <span>{selectedDays.length > 0 ? `${formatOpenDays(selectedDays)}, das ` : 'Aberta das '}<strong>{opens}</strong> às <strong>{closes}</strong>, {formatDuration(openMinutes)} de agenda por dia.</span>
                </p>
              )}
            </div>
          </section>

          <div className={`${ui.buttonRow} ${ui.buttonRowEnd}`}>
            <button type="button" className={ui.secondaryButton} disabled={!isDirty || isSubmitting} onClick={() => reset()}>Descartar alterações</button>
            <button type="submit" className={ui.button} disabled={!isDirty || isSubmitting}>
              {isSubmitting && <ButtonSpinner />} Salvar alterações
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
