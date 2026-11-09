import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage } from '../utils/format'
import styles from '../styles/auth.module.css'

const registerSchema = z.object({
  nome: z.string().min(3, 'Informe seu nome completo.'),
  email: z.string().email('Informe um e-mail válido.'),
  password: z.string().min(8, 'A senha deve ter pelo menos 8 caracteres.'),
  confirmPassword: z.string(),
}).refine((values) => values.password === values.confirmPassword, {
  message: 'As senhas não coincidem.',
  path: ['confirmPassword'],
})

type RegisterForm = z.infer<typeof registerSchema>

export function RegisterPage() {
  const { register: registerAccount } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (values: RegisterForm) => {
    try {
      await registerAccount({ nome: values.nome, email: values.email, password: values.password })
      showToast('Conta criada. Agora entre com suas credenciais.', 'success')
      navigate('/login', { replace: true })
    } catch (error) {
      showToast(errorMessage(error, 'Não foi possível criar a conta.'), 'error')
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
          <p className={styles.eyebrow}>Comece por aqui</p>
          <h1>Crie sua conta</h1>
          <p className={styles.description}>Depois do login, você pode criar a sua barbearia ou entrar quando for vinculado por um administrador.</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={styles.field}>
            <label htmlFor="nome">Nome completo</label>
            <input
              id="nome"
              autoComplete="name"
              placeholder="Seu nome"
              {...register('nome')}
              className={errors.nome ? styles.error : ''}
            />
            {errors.nome && <span className={styles.errorText}>{errors.nome.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="voce@exemplo.com"
              {...register('email')}
              className={errors.email ? styles.error : ''}
            />
            {errors.email && <span className={styles.errorText}>{errors.email.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              placeholder="Mínimo de 8 caracteres"
              {...register('password')}
              className={errors.password ? styles.error : ''}
            />
            {errors.password && <span className={styles.errorText}>{errors.password.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="confirmPassword">Confirmar senha</label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              placeholder="Repita a senha"
              {...register('confirmPassword')}
              className={errors.confirmPassword ? styles.error : ''}
            />
            {errors.confirmPassword && <span className={styles.errorText}>{errors.confirmPassword.message}</span>}
          </div>
          <button className={styles.submitButton} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Criando conta...' : 'Criar conta'}
          </button>
        </form>
        <p className={styles.switch}>Já tem conta? <Link to="/login">Entrar</Link></p>
      </section>
    </main>
  )
}
