import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { authApi } from '../api/endpoints'
import { useToast } from '../contexts/ToastContext'
import styles from '../styles/auth.module.css'

const resetRequestSchema = z.object({
  email: z.string().email('E-mail inválido'),
})

type ResetRequestForm = z.infer<typeof resetRequestSchema>

export function PasswordResetRequestPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ResetRequestForm>({
    resolver: zodResolver(resetRequestSchema),
  })

  const onSubmit = async (data: ResetRequestForm) => {
    setIsSubmitting(true)
    try {
      await authApi.requestPasswordReset({ email: data.email })
      showToast('Se o e-mail estiver cadastrado, você receberá instruções para redefinir a senha.', 'success')
      reset()
      setTimeout(() => {
        navigate('/login')
      }, 3000)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Erro ao solicitar recuperação de senha'
      showToast(message, 'error')
    } finally {
      setIsSubmitting(false)
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
          <p className={styles.eyebrow}>Recuperar Senha</p>
          <h1>Esqueceu a senha?</h1>
          <p className={styles.description}>Digite seu e-mail para receber instruções de recuperação</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={styles.field}>
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              {...register('email')}
              className={errors.email ? 'error' : ''}
              disabled={isSubmitting}
            />
            {errors.email && <span className={styles.errorText}>{errors.email.message}</span>}
          </div>
          <button className={styles.submitButton} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Enviando...' : 'Enviar Instruções'}
          </button>
        </form>
        <p className={styles.switch}>
          <button type="button" onClick={() => navigate('/login')} className="textButton" disabled={isSubmitting}>
            Voltar para o Login
          </button>
        </p>
      </section>
    </main>
  )
}