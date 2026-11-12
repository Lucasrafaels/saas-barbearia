import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { authApi } from '../api/endpoints'
import { AuthLayout } from '../components/AuthLayout'
import { ButtonSpinner, Field, fieldA11y } from '../components/Controls'
import { AlertCircleIcon, MailIcon } from '../components/Icons'
import { errorMessage } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

const schema = z.object({ email: z.string().trim().email('Informe um e-mail válido.') })
type Form = z.infer<typeof schema>

export function PasswordResetRequestPage() {
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema), defaultValues: { email: '' } })

  const onSubmit = async (values: Form) => {
    setFormError(null)
    try {
      await authApi.requestPasswordReset({ email: values.email.trim() })
      setSentTo(values.email.trim())
    } catch (error) {
      setFormError(errorMessage(error, 'Não foi possível solicitar a recuperação de senha.'))
    }
  }

  if (sentTo) {
    return (
      <AuthLayout title="Verifique seu e-mail" description={<>Se houver uma conta ativa com <strong>{sentTo}</strong>, enviamos as instruções para criar uma nova senha.</>}>
        <div className={`${ui.alert} ${ui.alertInfo}`}>
          <MailIcon size={18} />
          <span>A mensagem traz dois códigos: o identificador e o token. Use-os na próxima tela junto com a nova senha.</span>
        </div>
        <Link to="/password/reset/confirm" className={`${ui.button} ${ui.block}`}>Já tenho os códigos</Link>
        <p className={styles.switch}>
          Não recebeu? <button type="button" className={ui.textButton} onClick={() => setSentTo(null)}>Tentar outro e-mail</button>
        </p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Recuperar senha" description="Informe o e-mail da sua conta para receber as instruções.">
      <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
        {formError && <div className={`${ui.alert} ${ui.alertDanger}`} role="alert"><AlertCircleIcon size={18} /><p>{formError}</p></div>}
        <Field label="E-mail" htmlFor="reset-email" error={errors.email?.message}>
          <input {...fieldA11y('reset-email', errors.email?.message)} type="email" autoComplete="email" inputMode="email" autoFocus {...register('email')} />
        </Field>
        <button className={`${ui.button} ${ui.block}`} disabled={isSubmitting} type="submit">
          {isSubmitting && <ButtonSpinner />} Enviar instruções
        </button>
      </form>
      <p className={styles.switch}><Link to="/login">Voltar para o login</Link></p>
    </AuthLayout>
  )
}
