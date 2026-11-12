import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { AuthLayout } from '../components/AuthLayout'
import { ButtonSpinner, Field, fieldA11y, PasswordInput } from '../components/Controls'
import { AlertCircleIcon } from '../components/Icons'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage, firstName } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

const loginSchema = z.object({
  email: z.string().trim().email('Informe um e-mail válido.'),
  password: z.string().min(1, 'Informe sua senha.'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const { login } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const onSubmit = async (values: LoginForm) => {
    setFormError(null)
    try {
      const user = await login({ email: values.email.trim(), password: values.password })
      showToast(`Bem-vindo(a), ${firstName(user.nome)}.`, 'success')
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname
      navigate(user.barbershop ? (from && from !== '/login' ? from : '/') : '/onboarding', { replace: true })
    } catch (error) {
      setFormError(errorMessage(error, 'E-mail ou senha incorretos.'))
    }
  }

  return (
    <AuthLayout title="Entrar" description="Acesse a agenda da sua barbearia.">
      <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
        {formError && (
          <div className={`${ui.alert} ${ui.alertDanger}`} role="alert">
            <AlertCircleIcon size={18} />
            <p>{formError}</p>
          </div>
        )}
        <Field label="E-mail" htmlFor="login-email" error={errors.email?.message}>
          <input {...fieldA11y('login-email', errors.email?.message)} type="email" autoComplete="email" inputMode="email" autoFocus {...register('email')} />
        </Field>
        <div className={ui.field}>
          <div className={styles.labelRow}>
            <label className={ui.label} htmlFor="login-password">Senha</label>
            <Link to="/password/reset">Esqueci minha senha</Link>
          </div>
          <PasswordInput {...fieldA11y('login-password', errors.password?.message)} autoComplete="current-password" {...register('password')} />
          {errors.password && <p className={ui.error} id="login-password-error"><AlertCircleIcon size={14} />{errors.password.message}</p>}
        </div>
        <button className={`${ui.button} ${ui.block}`} disabled={isSubmitting} type="submit">
          {isSubmitting && <ButtonSpinner />} Entrar
        </button>
      </form>
      <div className={styles.divider} />
      <p className={styles.switch}>Ainda não tem conta? <Link to="/register">Criar conta</Link></p>
    </AuthLayout>
  )
}
