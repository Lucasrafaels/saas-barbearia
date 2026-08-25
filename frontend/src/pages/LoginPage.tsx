import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

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
        <div className={styles.brand}><span>✂</span> Corte Certo</div>
        <p className={styles.eyebrow}>Gestão simples de horários</p>
        <h1>Entre na sua conta</h1>
        <p className={styles.description}>Acompanhe sua agenda ou administre sua barbearia em um só lugar.</p>
        <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <label className={ui.field}>E-mail
            <input type="email" autoComplete="email" placeholder="voce@exemplo.com" {...register('email')} />
            {errors.email && <small className={ui.error}>{errors.email.message}</small>}
          </label>
          <label className={ui.field}>Senha
            <input type="password" autoComplete="current-password" placeholder="Sua senha" {...register('password')} />
            {errors.password && <small className={ui.error}>{errors.password.message}</small>}
          </label>
          <button className={ui.button} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
        <p className={styles.switch}>Ainda não tem conta? <Link to="/register">Criar conta</Link></p>
      </section>
    </main>
  )
}
