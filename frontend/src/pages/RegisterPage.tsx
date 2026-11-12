import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { AuthLayout } from '../components/AuthLayout'
import { ButtonSpinner, Field, fieldA11y, PasswordInput } from '../components/Controls'
import { AlertCircleIcon, InfoIcon } from '../components/Icons'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage, fieldErrors } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

const registerSchema = z.object({
  nome: z.string().trim().min(3, 'Informe seu nome completo.').max(150, 'Use no máximo 150 caracteres.'),
  email: z.string().trim().email('Informe um e-mail válido.'),
  password: z.string().min(8, 'A senha precisa ter pelo menos 8 caracteres.'),
  confirmPassword: z.string().min(1, 'Repita a senha.'),
}).refine((values) => values.password === values.confirmPassword, {
  message: 'As senhas não coincidem.',
  path: ['confirmPassword'],
})

type RegisterForm = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { register: registerAccount, login } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { nome: '', email: '', password: '', confirmPassword: '' },
  })

  const onSubmit = async (values: RegisterForm) => {
    setFormError(null)
    const credentials = { email: values.email.trim(), password: values.password }
    try {
      await registerAccount({ nome: values.nome.trim(), ...credentials })
    } catch (error) {
      const fields = fieldErrors(error)
      for (const key of ['nome', 'email', 'password'] as const) {
        if (fields[key]) setError(key, { message: fields[key] })
      }
      if (!fields.nome && !fields.email && !fields.password) setFormError(errorMessage(error, 'Não foi possível criar a conta.'))
      return
    }
    // Conta criada: entra direto para seguir ao cadastro da barbearia
    try {
      await login(credentials)
      showToast('Conta criada. Agora cadastre sua barbearia.', 'success')
      navigate('/onboarding', { replace: true })
    } catch {
      showToast('Conta criada. Entre com seu e-mail e senha.', 'success')
      navigate('/login', { replace: true })
    }
  }

  return (
    <AuthLayout title="Criar conta" description="Para donos de barbearia que querem organizar a agenda no BarberPro.">
      <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
        {formError && (
          <div className={`${ui.alert} ${ui.alertDanger}`} role="alert"><AlertCircleIcon size={18} /><p>{formError}</p></div>
        )}
        <Field label="Nome completo" htmlFor="register-nome" error={errors.nome?.message}>
          <input {...fieldA11y('register-nome', errors.nome?.message)} autoComplete="name" autoFocus {...register('nome')} />
        </Field>
        <Field label="E-mail" htmlFor="register-email" error={errors.email?.message}>
          <input {...fieldA11y('register-email', errors.email?.message)} type="email" autoComplete="email" inputMode="email" {...register('email')} />
        </Field>
        <Field label="Senha" htmlFor="register-password" error={errors.password?.message} hint="Mínimo de 8 caracteres, sem ser apenas números nem parecida com seu nome ou e-mail.">
          <PasswordInput {...fieldA11y('register-password', errors.password?.message, true)} autoComplete="new-password" {...register('password')} />
        </Field>
        <Field label="Repita a senha" htmlFor="register-confirm" error={errors.confirmPassword?.message}>
          <PasswordInput {...fieldA11y('register-confirm', errors.confirmPassword?.message)} autoComplete="new-password" {...register('confirmPassword')} />
        </Field>
        <button className={`${ui.button} ${ui.block}`} disabled={isSubmitting} type="submit">
          {isSubmitting && <ButtonSpinner />} Criar conta
        </button>
      </form>
      <p className={`${ui.alert} ${ui.alertInfo}`}>
        <InfoIcon size={18} />
        <span>É cliente de uma barbearia? Peça ao administrador para criar seu acesso; com ele você já entra e agenda.</span>
      </p>
      <p className={styles.switch}>Já tem conta? <Link to="/login">Entrar</Link></p>
    </AuthLayout>
  )
}
