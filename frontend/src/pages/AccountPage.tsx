import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { authApi, userApi } from '../api/endpoints'
import { Avatar, ButtonSpinner, Field, fieldA11y, PasswordInput } from '../components/Controls'
import { PageHeader } from '../components/PageHeader'
import { roleLabels, useAuth } from '../contexts/AuthContext'
import { useBarbershop } from '../contexts/BarbershopContext'
import { useToast } from '../contexts/ToastContext'
import { dateKey, errorMessage, fieldErrors, formatDayShort } from '../utils/format'
import page from '../styles/page.module.css'
import settings from '../styles/settings.module.css'
import ui from '../styles/ui.module.css'

const profileSchema = z.object({
  nome: z.string().trim().min(3, 'Informe seu nome completo.').max(150, 'Use no máximo 150 caracteres.'),
  email: z.string().trim().email('Informe um e-mail válido.'),
})

const passwordSchema = z.object({
  old_password: z.string().min(1, 'Informe a senha atual.'),
  new_password: z.string().min(8, 'A nova senha precisa ter pelo menos 8 caracteres.'),
  confirm_password: z.string().min(1, 'Repita a nova senha.'),
}).refine((values) => values.new_password === values.confirm_password, {
  message: 'As senhas não coincidem.',
  path: ['confirm_password'],
}).refine((values) => values.new_password !== values.old_password, {
  message: 'A nova senha precisa ser diferente da atual.',
  path: ['new_password'],
})

type ProfileForm = z.infer<typeof profileSchema>
type PasswordForm = z.infer<typeof passwordSchema>

export function AccountPage() {
  const { user, setCurrentUser, endLocalSession } = useAuth()
  const { barbershop } = useBarbershop()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const passwordRef = useRef<HTMLElement>(null)

  const profile = useForm<ProfileForm>({ resolver: zodResolver(profileSchema), defaultValues: { nome: user?.nome ?? '', email: user?.email ?? '' } })
  const password = useForm<PasswordForm>({ resolver: zodResolver(passwordSchema), defaultValues: { old_password: '', new_password: '', confirm_password: '' } })

  // Link antigo /password/change chega aqui com #senha
  useEffect(() => {
    if (location.hash === '#senha') passwordRef.current?.scrollIntoView({ block: 'start' })
  }, [location.hash])

  if (!user) return null

  const saveProfile = async (values: ProfileForm) => {
    try {
      const { data } = await userApi.update(user.id, { nome: values.nome.trim(), email: values.email.trim() })
      setCurrentUser(data)
      profile.reset({ nome: data.nome, email: data.email })
      showToast('Seus dados foram atualizados.', 'success')
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      for (const key of ['nome', 'email'] as const) {
        if (fields[key]) profile.setError(key, { message: fields[key] })
      }
      showToast(errorMessage(requestError, 'Não foi possível salvar seus dados.'), 'error')
    }
  }

  const changePassword = async (values: PasswordForm) => {
    try {
      await authApi.changePassword({ old_password: values.old_password, new_password: values.new_password })
      // O backend revoga as sessões existentes ao trocar a senha: é preciso entrar de novo.
      endLocalSession()
      showToast('Senha alterada. Entre novamente com a nova senha.', 'success')
      navigate('/login', { replace: true })
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      if (fields.old_password) password.setError('old_password', { message: fields.old_password })
      if (fields.new_password) password.setError('new_password', { message: fields.new_password })
      if (!fields.old_password && !fields.new_password) showToast(errorMessage(requestError, 'Não foi possível alterar a senha.'), 'error')
    }
  }

  const pErrors = profile.formState.errors
  const wErrors = password.formState.errors

  return (
    <div className={`${page.page} ${page.medium}`}>
      <PageHeader title="Minha conta" description="Seus dados de acesso ao BarberPro." />

      <section className={settings.section} aria-labelledby="profile-title">
        <div className={settings.intro}>
          <h2 id="profile-title">Dados pessoais</h2>
          <p>O e-mail é usado para entrar no sistema.</p>
          <ul className={settings.facts}>
            <li><Avatar name={user.nome} size="sm" /> {roleLabels[user.tipo_perfil]}{barbershop ? ` em ${barbershop.nome}` : ''}</li>
            <li>Conta criada em {formatDayShort(dateKey(user.created_at))}</li>
          </ul>
        </div>
        <form className={`${ui.panel}`} onSubmit={profile.handleSubmit(saveProfile)} noValidate>
          <div className={`${ui.panelBody} ${ui.form}`}>
            <Field label="Nome completo" htmlFor="account-nome" error={pErrors.nome?.message}>
              <input {...fieldA11y('account-nome', pErrors.nome?.message)} autoComplete="name" {...profile.register('nome')} />
            </Field>
            <Field label="E-mail" htmlFor="account-email" error={pErrors.email?.message}>
              <input {...fieldA11y('account-email', pErrors.email?.message)} type="email" autoComplete="email" {...profile.register('email')} />
            </Field>
          </div>
          <div className={ui.panelFooter}>
            <button type="submit" className={ui.button} disabled={!profile.formState.isDirty || profile.formState.isSubmitting}>
              {profile.formState.isSubmitting && <ButtonSpinner />} Salvar dados
            </button>
          </div>
        </form>
      </section>

      <section className={settings.section} aria-labelledby="password-title" ref={passwordRef} id="senha">
        <div className={settings.intro}>
          <h2 id="password-title">Senha</h2>
          <p>Ao trocar a senha, todas as sessões abertas são encerradas e você entra novamente com a nova senha.</p>
        </div>
        <form className={ui.panel} onSubmit={password.handleSubmit(changePassword)} noValidate>
          <div className={`${ui.panelBody} ${ui.form}`}>
            <Field label="Senha atual" htmlFor="account-old" error={wErrors.old_password?.message}>
              <PasswordInput {...fieldA11y('account-old', wErrors.old_password?.message)} autoComplete="current-password" {...password.register('old_password')} />
            </Field>
            <div className={ui.fieldRow}>
              <Field label="Nova senha" htmlFor="account-new" error={wErrors.new_password?.message} hint="Mínimo de 8 caracteres, sem ser apenas números.">
                <PasswordInput {...fieldA11y('account-new', wErrors.new_password?.message, true)} autoComplete="new-password" {...password.register('new_password')} />
              </Field>
              <Field label="Repita a nova senha" htmlFor="account-confirm" error={wErrors.confirm_password?.message}>
                <PasswordInput {...fieldA11y('account-confirm', wErrors.confirm_password?.message)} autoComplete="new-password" {...password.register('confirm_password')} />
              </Field>
            </div>
          </div>
          <div className={ui.panelFooter}>
            <button type="submit" className={ui.button} disabled={password.formState.isSubmitting}>
              {password.formState.isSubmitting && <ButtonSpinner />} Alterar senha
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
