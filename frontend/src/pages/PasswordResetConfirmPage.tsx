import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { authApi } from '../api/endpoints'
import { AuthLayout } from '../components/AuthLayout'
import { ButtonSpinner, Field, fieldA11y, PasswordInput } from '../components/Controls'
import { AlertCircleIcon } from '../components/Icons'
import { useToast } from '../contexts/ToastContext'
import { errorMessage, fieldErrors } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

const schema = z.object({
  uid: z.string().trim().min(1, 'Informe o identificador recebido por e-mail.'),
  token: z.string().trim().min(1, 'Informe o token recebido por e-mail.'),
  new_password: z.string().min(8, 'A nova senha precisa ter pelo menos 8 caracteres.'),
  confirm_password: z.string().min(1, 'Repita a nova senha.'),
}).refine((values) => values.new_password === values.confirm_password, {
  message: 'As senhas não coincidem.',
  path: ['confirm_password'],
})
type Form = z.infer<typeof schema>

/**
 * O e-mail do backend envia `uid` e `token` como texto. Se vierem na URL
 * (?uid=&token=), os campos já chegam preenchidos.
 */
export function PasswordResetConfirmPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { showToast } = useToast()
  const [formError, setFormError] = useState<string | null>(null)
  const fromLink = Boolean(params.get('uid') && params.get('token'))
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { uid: params.get('uid') ?? '', token: params.get('token') ?? '', new_password: '', confirm_password: '' },
  })

  const onSubmit = async (values: Form) => {
    setFormError(null)
    try {
      await authApi.confirmPasswordReset({ uid: values.uid.trim(), token: values.token.trim(), new_password: values.new_password })
      showToast('Senha redefinida. Entre com a nova senha.', 'success')
      navigate('/login', { replace: true })
    } catch (error) {
      const fields = fieldErrors(error)
      if (fields.new_password) setError('new_password', { message: fields.new_password })
      if (fields.token) setFormError('Os códigos são inválidos ou expiraram. Solicite uma nova recuperação de senha.')
      else if (!fields.new_password) setFormError(errorMessage(error, 'Não foi possível redefinir a senha.'))
    }
  }

  return (
    <AuthLayout title="Criar nova senha" description={fromLink ? 'Escolha a nova senha da sua conta.' : 'Informe os códigos recebidos por e-mail e escolha a nova senha.'}>
      <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
        {formError && (
          <div className={`${ui.alert} ${ui.alertDanger}`} role="alert">
            <AlertCircleIcon size={18} />
            <p>{formError} {formError.startsWith('Os códigos') && <Link to="/password/reset">Solicitar novamente</Link>}</p>
          </div>
        )}
        {!fromLink && (
          <div className={ui.fieldRow}>
            <Field label="Identificador (uid)" htmlFor="confirm-uid" error={errors.uid?.message}>
              <input {...fieldA11y('confirm-uid', errors.uid?.message)} autoComplete="off" spellCheck={false} autoFocus {...register('uid')} />
            </Field>
            <Field label="Token" htmlFor="confirm-token" error={errors.token?.message}>
              <input {...fieldA11y('confirm-token', errors.token?.message)} autoComplete="one-time-code" spellCheck={false} {...register('token')} />
            </Field>
          </div>
        )}
        <Field label="Nova senha" htmlFor="confirm-new" error={errors.new_password?.message} hint="Mínimo de 8 caracteres, sem ser apenas números.">
          <PasswordInput {...fieldA11y('confirm-new', errors.new_password?.message, true)} autoComplete="new-password" {...register('new_password')} />
        </Field>
        <Field label="Repita a nova senha" htmlFor="confirm-repeat" error={errors.confirm_password?.message}>
          <PasswordInput {...fieldA11y('confirm-repeat', errors.confirm_password?.message)} autoComplete="new-password" {...register('confirm_password')} />
        </Field>
        <button className={`${ui.button} ${ui.block}`} disabled={isSubmitting} type="submit">
          {isSubmitting && <ButtonSpinner />} Salvar nova senha
        </button>
      </form>
      <p className={styles.switch}><Link to="/login">Voltar para o login</Link></p>
    </AuthLayout>
  )
}
