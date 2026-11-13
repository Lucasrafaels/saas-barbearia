import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { barberApi, listAllBarbers, userApi } from '../api/endpoints'
import { ActiveBadge, Avatar, ButtonSpinner, Field, fieldA11y, Pagination, PasswordInput, SearchField, SegmentedControl } from '../components/Controls'
import { EmptyState, ErrorState, RefreshBar, SkeletonRows } from '../components/Feedback'
import { EditIcon, PowerIcon, RotateCcwIcon, UserPlusIcon } from '../components/Icons'
import { Modal } from '../components/Modal'
import { PageHeader } from '../components/PageHeader'
import { useConfirm } from '../contexts/ConfirmContext'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import { useLocalPagination } from '../hooks/useUi'
import type { Barber } from '../types'
import { errorMessage, fieldErrors, firstName, matchesSearch } from '../utils/format'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const specialtyRule = z.string().trim().min(2, 'Informe a especialidade (ex.: degradê, barba).').max(100, 'Use no máximo 100 caracteres.')

const createSchema = z.object({
  nome: z.string().trim().min(3, 'Informe o nome completo.').max(150, 'Use no máximo 150 caracteres.'),
  email: z.string().trim().email('Informe um e-mail válido.'),
  password: z.string().min(8, 'A senha precisa ter pelo menos 8 caracteres.'),
  especialidade: specialtyRule,
  ativo: z.boolean(),
})
const editSchema = z.object({ especialidade: specialtyRule, ativo: z.boolean() })

type CreateForm = z.infer<typeof createSchema>
type EditForm = z.infer<typeof editSchema>
type StatusFilter = 'all' | 'active' | 'inactive'

const createDefaults: CreateForm = { nome: '', email: '', password: '', especialidade: '', ativo: true }

export function AdminBarbersPage() {
  const { showToast } = useToast()
  const confirm = useConfirm()
  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(listAllBarbers, [])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<StatusFilter>('active')
  const [mode, setMode] = useState<'closed' | 'create' | 'edit'>('closed')
  const [editing, setEditing] = useState<Barber | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: createDefaults })
  const editForm = useForm<EditForm>({ resolver: zodResolver(editSchema), defaultValues: { especialidade: '', ativo: true } })

  const barbers = useMemo(() => data ?? [], [data])
  const counts = useMemo(() => ({
    all: barbers.length,
    active: barbers.filter((item) => item.ativo).length,
    inactive: barbers.filter((item) => !item.ativo).length,
  }), [barbers])

  const filtered = useMemo(() => barbers
    .filter((item) => (status === 'all' || (status === 'active') === item.ativo) && matchesSearch(query, item.nome, item.email, item.especialidade))
    .sort((a, b) => Number(b.ativo) - Number(a.ativo) || a.nome.localeCompare(b.nome, 'pt-BR')), [barbers, status, query])

  const pager = useLocalPagination(filtered, 20, `${status}|${query}`)

  const upsert = (barber: Barber) => setData((current) => {
    const list = current ?? []
    return list.some((item) => item.id === barber.id) ? list.map((item) => (item.id === barber.id ? barber : item)) : [...list, barber]
  })

  const openCreate = () => {
    createForm.reset(createDefaults)
    setEditing(null)
    setMode('create')
  }

  const openEdit = (barber: Barber) => {
    editForm.reset({ especialidade: barber.especialidade, ativo: barber.ativo })
    setEditing(barber)
    setMode('edit')
  }

  const handleCreate = async (values: CreateForm) => {
    try {
      // O endpoint de usuários cria a conta e o perfil de barbeiro na mesma
      // transação; duas chamadas poderiam deixar um usuário órfão se a segunda falhasse.
      await userApi.create({
        email: values.email.trim(),
        nome: values.nome.trim(),
        password: values.password,
        tipo_perfil: 'barbeiro',
        especialidade: values.especialidade.trim(),
        ativo: values.ativo,
      })
      await reload()
      showToast(`${firstName(values.nome)} foi adicionado à equipe.`, 'success')
      setMode('closed')
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      for (const key of ['nome', 'email', 'password', 'especialidade'] as const) {
        if (fields[key]) createForm.setError(key, { message: fields[key] })
      }
      showToast(errorMessage(requestError, 'Não foi possível cadastrar o barbeiro.'), 'error')
    }
  }

  const handleEdit = async (values: EditForm) => {
    if (!editing) return
    try {
      const { data: saved } = await barberApi.update(editing.id, { especialidade: values.especialidade.trim(), ativo: values.ativo })
      upsert(saved)
      showToast('Dados do barbeiro atualizados.', 'success')
      setMode('closed')
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      if (fields.especialidade) editForm.setError('especialidade', { message: fields.especialidade })
      showToast(errorMessage(requestError, 'Não foi possível atualizar o barbeiro.'), 'error')
    }
  }

  const toggleActive = async (barber: Barber) => {
    if (barber.ativo) {
      const ok = await confirm({
        title: `Desativar ${barber.nome}?`,
        description: 'Ele deixa de aparecer para novos agendamentos e a conta passa a ser de cliente. Os horários já marcados e o histórico continuam disponíveis, e você pode reativá-lo depois.',
        confirmLabel: 'Desativar barbeiro',
        tone: 'danger',
      })
      if (!ok) return
    }
    setBusyId(barber.id)
    try {
      if (barber.ativo) {
        await barberApi.remove(barber.id)
        upsert({ ...barber, ativo: false })
        showToast(`${firstName(barber.nome)} foi desativado.`, 'success')
      } else {
        const { data: saved } = await barberApi.update(barber.id, { ativo: true })
        upsert(saved)
        showToast(`${firstName(barber.nome)} foi reativado.`, 'success')
      }
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível alterar o barbeiro.'), 'error')
    } finally {
      setBusyId(null)
    }
  }

  const createErrors = createForm.formState.errors
  const editErrors = editForm.formState.errors
  const submitting = createForm.formState.isSubmitting || editForm.formState.isSubmitting

  return (
    <div className={page.page}>
      <PageHeader
        title="Barbeiros"
        description="A equipe que aparece para os clientes no agendamento. Cada barbeiro tem login próprio para ver a agenda."
        actions={<button type="button" className={ui.button} onClick={openCreate}><UserPlusIcon size={18} /> Novo barbeiro</button>}
      />

      <section className={ui.panel}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGrow}>
            <SearchField value={query} onChange={setQuery} placeholder="Buscar por nome, e-mail ou especialidade" />
          </div>
          <SegmentedControl
            label="Filtrar por situação"
            value={status}
            onChange={setStatus}
            options={[
              { value: 'active', label: 'Ativos', count: counts.active },
              { value: 'inactive', label: 'Inativos', count: counts.inactive },
              { value: 'all', label: 'Todos', count: counts.all },
            ]}
          />
        </div>
        <RefreshBar active={isRefreshing} />

        {isLoading ? (
          <SkeletonRows rows={4} label="Carregando barbeiros" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar os barbeiros." onRetry={() => void reload()} />
        ) : barbers.length === 0 ? (
          <EmptyState
            art="navalha"
            title="Nenhum barbeiro na equipe"
            description="Cadastre o primeiro barbeiro. Ele recebe um login para acompanhar a própria agenda."
            action={{ label: 'Cadastrar barbeiro', onClick: openCreate }}
          />
        ) : filtered.length === 0 ? (
          <EmptyState compact title="Nenhum barbeiro encontrado" description="Ajuste a busca ou o filtro de situação." action={{ label: 'Limpar filtros', onClick: () => { setQuery(''); setStatus('all') } }} />
        ) : (
          <>
            <div className={ui.tableWrap}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Barbeiro</th>
                    <th>Especialidade</th>
                    <th>Situação</th>
                    <th><span className="sr-only">Ações</span></th>
                  </tr>
                </thead>
                <tbody>
                  {pager.pageItems.map((barber) => (
                    <tr key={barber.id} className={barber.ativo ? undefined : ui.rowInactive}>
                      <td data-primary>
                        <div className={ui.cellPerson}>
                          <Avatar name={barber.nome} muted={!barber.ativo} />
                          <div style={{ minWidth: 0 }}>
                            <div className={ui.cellTitle}>{barber.nome}</div>
                            <div className={ui.cellMuted}>{barber.email}</div>
                          </div>
                        </div>
                      </td>
                      <td data-label="Especialidade">{barber.especialidade || <span className={ui.cellMuted}>Não informada</span>}</td>
                      <td data-label="Situação"><ActiveBadge active={barber.ativo} /></td>
                      <td data-actions>
                        <div className={ui.cellActions}>
                          <button type="button" className={`${ui.ghostButton} ${ui.sm}`} onClick={() => openEdit(barber)} aria-label={`Editar ${barber.nome}`}>
                            <EditIcon size={16} /> Editar
                          </button>
                          <button
                            type="button"
                            className={`${ui.ghostButton} ${ui.sm}`}
                            onClick={() => void toggleActive(barber)}
                            disabled={busyId === barber.id}
                            aria-label={`${barber.ativo ? 'Desativar' : 'Reativar'} ${barber.nome}`}
                          >
                            {busyId === barber.id ? <ButtonSpinner /> : barber.ativo ? <PowerIcon size={16} /> : <RotateCcwIcon size={16} />}
                            {barber.ativo ? 'Desativar' : 'Reativar'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={pager.page} count={pager.total} pageSize={pager.pageSize} onChange={pager.setPage} />
          </>
        )}
      </section>

      <Modal
        open={mode === 'create'}
        onClose={() => setMode('closed')}
        dismissible={!submitting}
        title="Novo barbeiro"
        description="Cria o login do barbeiro e o perfil profissional que aparece no agendamento."
        footer={
          <>
            <button type="button" className={ui.secondaryButton} onClick={() => setMode('closed')} disabled={submitting}>Cancelar</button>
            <button type="submit" form="barber-create" className={ui.button} disabled={submitting}>
              {createForm.formState.isSubmitting && <ButtonSpinner />} Cadastrar barbeiro
            </button>
          </>
        }
      >
        <form id="barber-create" className={ui.form} onSubmit={createForm.handleSubmit(handleCreate)} noValidate>
          <Field label="Nome completo" htmlFor="barber-nome" error={createErrors.nome?.message}>
            <input {...fieldA11y('barber-nome', createErrors.nome?.message)} autoComplete="off" placeholder="Rafael Mendes" {...createForm.register('nome')} />
          </Field>
          <Field label="E-mail de acesso" htmlFor="barber-email" error={createErrors.email?.message}>
            <input {...fieldA11y('barber-email', createErrors.email?.message)} type="email" autoComplete="off" placeholder="rafael@suabarbearia.com" {...createForm.register('email')} />
          </Field>
          <Field label="Senha inicial" htmlFor="barber-password" error={createErrors.password?.message} hint="Mínimo de 8 caracteres, sem ser apenas números. Compartilhe com o barbeiro; ele pode trocá-la depois.">
            <PasswordInput {...fieldA11y('barber-password', createErrors.password?.message, true)} autoComplete="new-password" {...createForm.register('password')} />
          </Field>
          <Field label="Especialidade" htmlFor="barber-especialidade" error={createErrors.especialidade?.message} hint="Aparece para o cliente ao escolher o profissional.">
            <input {...fieldA11y('barber-especialidade', createErrors.especialidade?.message, true)} placeholder="Degradê e navalhado" {...createForm.register('especialidade')} />
          </Field>
          <label className={ui.switch}>
            <input type="checkbox" {...createForm.register('ativo')} />
            <span className={ui.switchText}>
              Recebendo agendamentos
              <small>Desligado, o perfil fica salvo, mas a conta funciona como cliente até ser reativado.</small>
            </span>
          </label>
        </form>
      </Modal>

      <Modal
        open={mode === 'edit'}
        onClose={() => setMode('closed')}
        dismissible={!submitting}
        title={editing ? `Editar ${editing.nome}` : 'Editar barbeiro'}
        description={editing?.email}
        footer={
          <>
            <button type="button" className={ui.secondaryButton} onClick={() => setMode('closed')} disabled={submitting}>Cancelar</button>
            <button type="submit" form="barber-edit" className={ui.button} disabled={submitting}>
              {editForm.formState.isSubmitting && <ButtonSpinner />} Salvar alterações
            </button>
          </>
        }
      >
        <form id="barber-edit" className={ui.form} onSubmit={editForm.handleSubmit(handleEdit)} noValidate>
          <Field label="Especialidade" htmlFor="edit-especialidade" error={editErrors.especialidade?.message}>
            <input {...fieldA11y('edit-especialidade', editErrors.especialidade?.message)} {...editForm.register('especialidade')} />
          </Field>
          <label className={ui.switch}>
            <input type="checkbox" {...editForm.register('ativo')} />
            <span className={ui.switchText}>
              Recebendo agendamentos
              <small>Ao desligar, a conta passa a ser de cliente; o histórico é mantido.</small>
            </span>
          </label>
        </form>
      </Modal>
    </div>
  )
}
