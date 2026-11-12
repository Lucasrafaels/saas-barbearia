import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { barbershopApi } from '../api/endpoints'
import { AuthLayout } from '../components/AuthLayout'
import { ButtonSpinner, Field, fieldA11y } from '../components/Controls'
import { AlertCircleIcon, InfoIcon } from '../components/Icons'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage, fieldErrors, firstName, timeToMinutes } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

const schema = z.object({
  nome: z.string().trim().min(2, 'Informe o nome da barbearia.').max(150, 'Use no máximo 150 caracteres.'),
  endereco: z.string().trim().min(5, 'Informe o endereço completo.').max(255, 'Use no máximo 255 caracteres.'),
  telefone: z.string().trim().min(8, 'Informe um telefone com DDD.').max(20, 'Use no máximo 20 caracteres.'),
  email: z.string().trim().email('Informe um e-mail válido.'),
  horario_abertura: z.string().regex(/^\d{2}:\d{2}$/, 'Informe o horário de abertura.'),
  horario_fechamento: z.string().regex(/^\d{2}:\d{2}$/, 'Informe o horário de fechamento.'),
}).refine((values) => timeToMinutes(values.horario_fechamento) > timeToMinutes(values.horario_abertura), {
  message: 'O fechamento precisa ser depois da abertura.',
  path: ['horario_fechamento'],
})
type Form = z.infer<typeof schema>

export function OnboardingPage() {
  const { user, refreshUser, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { nome: '', endereco: '', telefone: '', email: user?.email ?? '', horario_abertura: '09:00', horario_fechamento: '19:00' },
  })

  const onSubmit = async (values: Form) => {
    setFormError(null)
    try {
      await barbershopApi.create({
        ...values,
        horario_abertura: `${values.horario_abertura}:00`,
        horario_fechamento: `${values.horario_fechamento}:00`,
      })
      await refreshUser()
      showToast(`${values.nome} está pronta. Cadastre serviços e equipe para liberar a agenda.`, 'success')
      navigate('/', { replace: true })
    } catch (error) {
      const fields = fieldErrors(error)
      let mapped = false
      for (const key of ['nome', 'endereco', 'telefone', 'email', 'horario_abertura', 'horario_fechamento'] as const) {
        if (fields[key]) { setError(key, { message: fields[key] }); mapped = true }
      }
      if (!mapped) setFormError(errorMessage(error, 'Não foi possível cadastrar a barbearia.'))
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <AuthLayout
      wide
      title={user ? `Vamos cadastrar sua barbearia, ${firstName(user.nome)}` : 'Cadastre sua barbearia'}
      description="Você será o administrador. Depois, cadastre serviços, barbeiros e clientes pelo painel."
    >
      <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
        {formError && <div className={`${ui.alert} ${ui.alertDanger}`} role="alert"><AlertCircleIcon size={18} /><p>{formError}</p></div>}
        <Field label="Nome da barbearia" htmlFor="onb-nome" error={errors.nome?.message}>
          <input {...fieldA11y('onb-nome', errors.nome?.message)} autoComplete="organization" autoFocus {...register('nome')} />
        </Field>
        <Field label="Endereço" htmlFor="onb-endereco" error={errors.endereco?.message}>
          <input {...fieldA11y('onb-endereco', errors.endereco?.message)} autoComplete="street-address" placeholder="Rua, número, bairro e cidade" {...register('endereco')} />
        </Field>
        <div className={ui.fieldRow}>
          <Field label="Telefone" htmlFor="onb-telefone" error={errors.telefone?.message}>
            <input {...fieldA11y('onb-telefone', errors.telefone?.message)} type="tel" inputMode="tel" autoComplete="tel" placeholder="(11) 99999-9999" {...register('telefone')} />
          </Field>
          <Field label="E-mail de contato" htmlFor="onb-email" error={errors.email?.message}>
            <input {...fieldA11y('onb-email', errors.email?.message)} type="email" {...register('email')} />
          </Field>
        </div>
        <div className={ui.fieldRow}>
          <Field label="Abre às" htmlFor="onb-abre" error={errors.horario_abertura?.message}>
            <input {...fieldA11y('onb-abre', errors.horario_abertura?.message)} type="time" step={900} {...register('horario_abertura')} />
          </Field>
          <Field label="Fecha às" htmlFor="onb-fecha" error={errors.horario_fechamento?.message}>
            <input {...fieldA11y('onb-fecha', errors.horario_fechamento?.message)} type="time" step={900} {...register('horario_fechamento')} />
          </Field>
        </div>
        <p className={ui.hint}>O horário de funcionamento define os horários livres oferecidos aos clientes e pode ser alterado depois.</p>
        <button className={`${ui.button} ${ui.block}`} disabled={isSubmitting} type="submit">
          {isSubmitting && <ButtonSpinner />} Cadastrar barbearia
        </button>
      </form>
      <p className={`${ui.alert} ${ui.alertInfo}`}>
        <InfoIcon size={18} />
        <span>Veio para agendar como cliente? Peça ao administrador da barbearia para criar seu acesso e use a conta que ele informar.</span>
      </p>
      <p className={styles.switch}>
        <button type="button" onClick={() => void handleLogout()} className={ui.textButton}>Sair da conta</button>
      </p>
    </AuthLayout>
  )
}
