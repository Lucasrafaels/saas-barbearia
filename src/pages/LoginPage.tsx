import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage } from '../utils/format'
import styles from '../styles/auth.module.css'

const loginSchema = z.object({
  email: z.string().email('Informe um e-mail válido.'),
  password: z.string().min(1, 'Informe sua senha.'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const { login } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (values: LoginForm) => {
    try {
      const user = await login(values)
      showToast(`Bem-vindo(a), ${user.nome.split(' ')[0]}!`, 'success')
      navigate(user.barbershop ? '/' : '/onboarding', { replace: true })
    } catch (error) {
      showToast(errorMessage(error, 'E-mail ou senha inválidos.'), 'error')
    }
  }

  return (
    <main className={styles.authPage}>
      <section className={styles.panel}>
        <a href="/" className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">B</span>
          BarberPro
        </a>
        <div className={styles.panelHeader}>
          <p className={styles.eyebrow}>Área do cliente</p>
          <h1>Entre na sua conta</h1>
          <p className={styles.description}>Acompanhe sua agenda ou administre sua barbearia em um só lugar.</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={styles.field}>
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="voce@exemplo.com"
              {...register('email')}
              className={errors.email ? 'error' : ''}
            />
            {errors.email && <span className={styles.errorText}>{errors.email.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="Sua senha"
              {...register('password')}
              className={errors.password ? 'error' : ''}
            />
            {errors.password && <span className={styles.errorText}>{errors.password.message}</span>}
          </div>
          <button className={styles.submitButton} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
        <p className={styles.switch}>Ainda não tem conta? <Link to="/register">Criar conta</Link></p>
        <p className={styles.switch}><Link to="/password/reset">Esqueci minha senha</Link></p>
      </section>
    </main>
  )
}
