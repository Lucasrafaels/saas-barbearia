import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useToast } from '../contexts/ToastContext'
import { authApi } from '../api/endpoints'
import styles from '../styles/auth.module.css'

const resetConfirmSchema = z.object({
  new_password: z.string().min(8, 'A nova senha deve ter pelo menos 8 caracteres'),
  confirm_password: z.string().min(1, 'Confirmação de senha é obrigatória'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'As senhas não coincidem',
  path: ['confirm_password'],
})

type ResetConfirmForm = z.infer<typeof resetConfirmSchema>

export function PasswordResetConfirmPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { showToast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isTokenValid, setIsTokenValid] = useState(true)
  const [uid, setUid] = useState('')
  const [token, setToken] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ResetConfirmForm>({
    resolver: zodResolver(resetConfirmSchema),
  })

  useEffect(() => {
    const uidParam = searchParams.get('uid')
    const tokenParam = searchParams.get('token')

    if (!uidParam || !tokenParam) {
      setIsTokenValid(false)
      return
    }

    setUid(uidParam)
    setToken(tokenParam)
  }, [searchParams])

  const onSubmit = async (data: ResetConfirmForm) => {
    setIsSubmitting(true)
    try {
      await authApi.confirmPasswordReset({
        uid,
        token,
        new_password: data.new_password,
      })
      showToast('Senha redefinida com sucesso! Você será redirecionado para o login.', 'success')
      reset()
      setTimeout(() => {
        navigate('/login')
      }, 2000)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Erro ao redefinir senha'
      showToast(message, 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isTokenValid) {
    return (
      <main className={styles.authPage}>
        <section className={styles.panel}>
          <a href="/" className={styles.brand}>
            <span className={styles.brandMark} aria-hidden="true">B</span>
            BarberPro
          </a>
          <div className={styles.panelHeader}>
            <h1>Link Inválido</h1>
            <p className={styles.description}>Este link de recuperação é inválido ou expirou.</p>
          </div>
          <p className={styles.switch}>
            <button
              type="button"
              onClick={() => navigate('/password/reset')}
              className="textButton"
            >
              Solicitar Novo Link
            </button>
          </p>
        </section>
      </main>
    )
  }

  return (
    <main className={styles.authPage}>
      <section className={styles.panel}>
        <a href="/" className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">B</span>
          BarberPro
        </a>
        <div className={styles.panelHeader}>
          <p className={styles.eyebrow}>Redefinir Senha</p>
          <h1>Nova Senha</h1>
          <p className={styles.description}>Digite sua nova senha</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={styles.field}>
            <label htmlFor="new_password">Nova Senha</label>
            <input
              id="new_password"
              type="password"
              autoComplete="new-password"
              {...register('new_password')}
              className={errors.new_password ? 'error' : ''}
              disabled={isSubmitting}
            />
            {errors.new_password && <span className={styles.errorText}>{errors.new_password.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="confirm_password">Confirmar Nova Senha</label>
            <input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              {...register('confirm_password')}
              className={errors.confirm_password ? 'error' : ''}
              disabled={isSubmitting}
            />
            {errors.confirm_password && <span className={styles.errorText}>{errors.confirm_password.message}</span>}
          </div>
          <button className={styles.submitButton} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Redefinindo...' : 'Redefinir Senha'}
          </button>
        </form>
        <p className={styles.switch}>
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="textButton"
            disabled={isSubmitting}
          >
            Voltar para o Login
          </button>
        </p>
      </section>
    </main>
  )
}