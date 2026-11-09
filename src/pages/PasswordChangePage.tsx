import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { authApi } from '../api/endpoints'
import styles from '../styles/auth.module.css'

const passwordChangeSchema = z.object({
  old_password: z.string().min(1, 'Senha atual é obrigatória'),
  new_password: z.string().min(8, 'A nova senha deve ter pelo menos 8 caracteres'),
  confirm_password: z.string().min(1, 'Confirmação de senha é obrigatória'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'As senhas não coincidem',
  path: ['confirm_password'],
})

type PasswordChangeForm = z.infer<typeof passwordChangeSchema>

export function PasswordChangePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { showToast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<PasswordChangeForm>({
    resolver: zodResolver(passwordChangeSchema),
  })

  const onSubmit = async (data: PasswordChangeForm) => {
    setIsSubmitting(true)
    try {
      await authApi.changePassword({
        old_password: data.old_password,
        new_password: data.new_password,
      })
      showToast('Senha alterada com sucesso! Você será redirecionado para o login.', 'success')
      reset()
      setTimeout(() => {
        navigate('/login')
      }, 2000)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Erro ao alterar senha'
      showToast(message, 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!user) {
    return null
  }

  return (
    <main className={styles.authPage}>
      <section className={styles.panel}>
        <a href="/" className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">B</span>
          BarberPro
        </a>
        <div className={styles.panelHeader}>
          <p className={styles.eyebrow}>Configurações</p>
          <h1>Alterar Senha</h1>
          <p className={styles.description}>Digite sua senha atual e a nova senha.</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={styles.field}>
            <label htmlFor="old_password">Senha Atual</label>
            <input
              id="old_password"
              type="password"
              autoComplete="current-password"
              {...register('old_password')}
              className={errors.old_password ? 'error' : ''}
              disabled={isSubmitting}
            />
            {errors.old_password && <span className={styles.errorText}>{errors.old_password.message}</span>}
          </div>
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
            {isSubmitting ? 'Alterando...' : 'Alterar Senha'}
          </button>
        </form>
        <p className={styles.switch}>
          <button type="button" onClick={() => navigate(-1)} className="textButton" disabled={isSubmitting}>
            Voltar
          </button>
        </p>
      </section>
    </main>
  )
}