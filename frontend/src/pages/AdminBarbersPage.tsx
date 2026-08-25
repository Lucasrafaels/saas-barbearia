import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { barberApi, userApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Barber } from '../types'
import { errorMessage } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const newBarberSchema = z.object({
  nome: z.string().min(3, 'Informe o nome completo.'),
  email: z.string().email('Informe um e-mail válido.'),
  password: z.string().min(8, 'A senha precisa ter pelo menos 8 caracteres.'),
  especialidade: z.string().max(150, 'Use no máximo 150 caracteres.'),
  ativo: z.boolean(),
})
const editBarberSchema = z.object({
  especialidade: z.string().max(150, 'Use no máximo 150 caracteres.'),
  ativo: z.boolean(),
})
type NewBarberForm = z.infer<typeof newBarberSchema>
type EditBarberForm = z.infer<typeof editBarberSchema>

function BarberEditor({ barber, onSaved, onCancel }: { barber: Barber; onSaved: () => Promise<void>; onCancel: () => void }) {
  const { showToast } = useToast()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<EditBarberForm>({
    resolver: zodResolver(editBarberSchema), defaultValues: { especialidade: barber.especialidade, ativo: barber.ativo },
  })
  const save = async (values: EditBarberForm) => {
    try {
      await barberApi.update(barber.id, values)
      await onSaved()
      showToast('Barbeiro atualizado.', 'success')
      onCancel()
    } catch (error) { showToast(errorMessage(error, 'Não foi possível atualizar o barbeiro.'), 'error') }
  }
  return <form className={ui.inlineEdit} onSubmit={handleSubmit(save)} noValidate>
    <label className={ui.field}>Especialidade<input {...register('especialidade')} />{errors.especialidade && <small className={ui.error}>{errors.especialidade.message}</small>}</label>
    <label className={ui.checkbox}><input type="checkbox" {...register('ativo')} /> Ativo</label>
    <div className={ui.buttonRow}><button className={ui.button} disabled={isSubmitting} type="submit">Salvar</button><button className={ui.secondaryButton} type="button" onClick={onCancel}>Cancelar</button></div>
  </form>
}

export function AdminBarbersPage() {
  const { showToast } = useToast()
  const [editing, setEditing] = useState<number | null>(null)
  const { data, isLoading, error, reload } = useAsyncData(() => barberApi.list().then((response) => response.data), [])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<NewBarberForm>({
    resolver: zodResolver(newBarberSchema), defaultValues: { nome: '', email: '', password: '', especialidade: '', ativo: true },
  })

  const create = async (values: NewBarberForm) => {
    let createdUserName = ''
    try {
      const { data: user } = await userApi.create({
        nome: values.nome, email: values.email, password: values.password, tipo_perfil: 'barbeiro',
      })
      createdUserName = user.nome
      await barberApi.create({ user: user.id, especialidade: values.especialidade, ativo: values.ativo })
      await reload()
      reset()
      showToast('Barbeiro cadastrado.', 'success')
    } catch (requestError) {
      const extra = createdUserName ? ' O usuário foi criado, mas o perfil profissional não; tente cadastrar novamente com outro e-mail ou revise os dados.' : ''
      showToast(`${errorMessage(requestError, 'Não foi possível cadastrar o barbeiro.')}${extra}`, 'error')
    }
  }

  const remove = async (barber: Barber) => {
    if (!window.confirm(`Excluir o perfil de ${barber.nome}? A conta de usuário não será apagada.`)) return
    try {
      await barberApi.remove(barber.id)
      await reload()
      if (editing === barber.id) setEditing(null)
      showToast('Perfil de barbeiro excluído.', 'success')
    } catch (requestError) { showToast(errorMessage(requestError, 'Não foi possível excluir o barbeiro.'), 'error') }
  }

  if (isLoading) return <PageLoader label="Carregando barbeiros..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar os barbeiros.</p>
  const barbers = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}><div><p className={styles.eyebrow}>Equipe da barbearia</p><h1>Gerenciar barbeiros</h1></div></header>
      <div className={styles.adminSplit}>
        <section className={ui.formCard}>
          <h2>Novo barbeiro</h2>
          <p className={ui.hint}>Cria a conta e o perfil profissional de uma só vez.</p>
          <form className={ui.form} onSubmit={handleSubmit(create)} noValidate>
            <label className={ui.field}>Nome completo<input placeholder="João da Silva" {...register('nome')} />{errors.nome && <small className={ui.error}>{errors.nome.message}</small>}</label>
            <label className={ui.field}>E-mail<input type="email" placeholder="joao@barbearia.com" {...register('email')} />{errors.email && <small className={ui.error}>{errors.email.message}</small>}</label>
            <label className={ui.field}>Senha inicial<input type="password" autoComplete="new-password" {...register('password')} />{errors.password && <small className={ui.error}>{errors.password.message}</small>}</label>
            <label className={ui.field}>Especialidade<input placeholder="Corte e barba" {...register('especialidade')} />{errors.especialidade && <small className={ui.error}>{errors.especialidade.message}</small>}</label>
            <label className={ui.checkbox}><input type="checkbox" {...register('ativo')} /> Disponível para agendamento</label>
            <button className={ui.button} disabled={isSubmitting} type="submit">{isSubmitting ? 'Cadastrando...' : 'Cadastrar barbeiro'}</button>
          </form>
        </section>
        <section>
          <h2 className={styles.sectionTitle}>Barbeiros cadastrados</h2>
          {barbers.length === 0 ? <EmptyState title="Nenhum barbeiro" description="Cadastre o primeiro profissional ao lado." /> : <div className={styles.managementList}>
            {barbers.map((barber) => <article className={styles.managementCard} key={barber.id}>
              <div><h3>{barber.nome} {!barber.ativo && <span className={styles.inactive}>Inativo</span>}</h3><p>{barber.especialidade || 'Sem especialidade informada'}</p><small>{barber.email}</small></div>
              {editing === barber.id ? <BarberEditor barber={barber} onSaved={reload} onCancel={() => setEditing(null)} /> : <div className={styles.cardActions}><button className={ui.secondaryButton} onClick={() => setEditing(barber.id)}>Editar</button><button className={ui.dangerButton} onClick={() => void remove(barber)}>Excluir</button></div>}
            </article>)}
          </div>}
        </section>
      </div>
    </div>
  )
}
