import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

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
        <div className={styles.brand}><span>✂</span> Corte Certo</div>
        <p className={styles.eyebrow}>Comece por aqui</p>
        <h1>Crie sua conta</h1>
        <p className={styles.description}>Depois do login, você pode criar a sua barbearia ou entrar quando for vinculado por um administrador.</p>
        <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <label className={ui.field}>Nome completo
            <input autoComplete="name" placeholder="Seu nome" {...register('nome')} />
            {errors.nome && <small className={ui.error}>{errors.nome.message}</small>}
          </label>
          <label className={ui.field}>E-mail
            <input type="email" autoComplete="email" placeholder="voce@exemplo.com" {...register('email')} />
            {errors.email && <small className={ui.error}>{errors.email.message}</small>}
          </label>
          <label className={ui.field}>Senha
            <input type="password" autoComplete="new-password" placeholder="Mínimo de 8 caracteres" {...register('password')} />
            {errors.password && <small className={ui.error}>{errors.password.message}</small>}
          </label>
          <label className={ui.field}>Confirmar senha
            <input type="password" autoComplete="new-password" placeholder="Repita a senha" {...register('confirmPassword')} />
            {errors.confirmPassword && <small className={ui.error}>{errors.confirmPassword.message}</small>}
          </label>
          <button className={ui.button} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Criando conta...' : 'Criar conta'}
          </button>
        </form>
        <p className={styles.switch}>Já tem conta? <Link to="/login">Entrar</Link></p>
      </section>
    </main>
  )
}
