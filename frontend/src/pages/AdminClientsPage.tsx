import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { listAllAppointments, listAllUsers, userApi } from '../api/endpoints'
import { ActiveBadge, Avatar, ButtonSpinner, Field, fieldA11y, Pagination, PasswordInput, SearchField, SegmentedControl } from '../components/Controls'
import { EmptyState, ErrorState, RefreshBar, SkeletonRows } from '../components/Feedback'
import { EditIcon, PowerIcon, RotateCcwIcon, UserPlusIcon } from '../components/Icons'
import { Modal } from '../components/Modal'
import { PageHeader } from '../components/PageHeader'
import { useConfirm } from '../contexts/ConfirmContext'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import { useLocalPagination } from '../hooks/useUi'
import type { User } from '../types'
import { dateKey, errorMessage, fieldErrors, firstName, formatDayShort, matchesSearch, plural } from '../utils/format'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const baseSchema = z.object({
  nome: z.string().trim().min(3, 'Informe o nome completo.').max(150, 'Use no máximo 150 caracteres.'),
  email: z.string().trim().email('Informe um e-mail válido.'),
})
const createSchema = baseSchema.extend({ password: z.string().min(8, 'A senha precisa ter pelo menos 8 caracteres.') })

type EditForm = z.infer<typeof baseSchema>
type CreateForm = z.infer<typeof createSchema>
type StatusFilter = 'all' | 'active' | 'inactive'

interface ClientStats {
  visits: number
  lastVisit: string | null
  next: string | null
}

export function AdminClientsPage() {
  const { showToast } = useToast()
  const confirm = useConfirm()
  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(async () => {
    const [clients, appointments] = await Promise.all([listAllUsers('cliente'), listAllAppointments()])
    return { clients, appointments }
  }, [])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<StatusFilter>('active')
  const [mode, setMode] = useState<'closed' | 'create' | 'edit'>('closed')
  const [editing, setEditing] = useState<User | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: { nome: '', email: '', password: '' } })
  const editForm = useForm<EditForm>({ resolver: zodResolver(baseSchema), defaultValues: { nome: '', email: '' } })

  const clients = useMemo(() => data?.clients ?? [], [data])

  // Histórico real de cada cliente a partir dos agendamentos do tenant
  const stats = useMemo(() => {
    const map = new Map<number, ClientStats>()
    const now = Date.now()
    for (const item of data?.appointments ?? []) {
      const entry = map.get(item.cliente) ?? { visits: 0, lastVisit: null, next: null }
      if (item.status === 'realizado') {
        entry.visits++
        if (!entry.lastVisit || item.data_hora > entry.lastVisit) entry.lastVisit = item.data_hora
      }
      if ((item.status === 'agendado' || item.status === 'confirmado') && new Date(item.data_hora).getTime() >= now) {
        if (!entry.next || item.data_hora < entry.next) entry.next = item.data_hora
      }
      map.set(item.cliente, entry)
    }
    return map
  }, [data])

  const counts = useMemo(() => ({
    all: clients.length,
    active: clients.filter((item) => item.is_active).length,
    inactive: clients.filter((item) => !item.is_active).length,
  }), [clients])

  const filtered = useMemo(() => clients
    .filter((item) => (status === 'all' || (status === 'active') === item.is_active) && matchesSearch(query, item.nome, item.email))
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')), [clients, status, query])

  const pager = useLocalPagination(filtered, 20, `${status}|${query}`)

  const upsert = (user: User) => setData((current) => current && {
    ...current,
    clients: current.clients.some((item) => item.id === user.id)
      ? current.clients.map((item) => (item.id === user.id ? user : item))
      : [...current.clients, user],
  })

  const openCreate = () => {
    createForm.reset({ nome: '', email: '', password: '' })
    setMode('create')
  }

  const openEdit = (client: User) => {
    editForm.reset({ nome: client.nome, email: client.email })
    setEditing(client)
    setMode('edit')
  }

  const handleCreate = async (values: CreateForm) => {
    try {
      const { data: created } = await userApi.create({ nome: values.nome.trim(), email: values.email.trim(), password: values.password, tipo_perfil: 'cliente' })
      upsert({ ...created, is_active: created.is_active ?? true, created_at: created.created_at ?? new Date().toISOString() })
      showToast(`${firstName(values.nome)} foi cadastrado. Ele já pode entrar com o e-mail e a senha informados.`, 'success')
      setMode('closed')
      void reload()
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      for (const key of ['nome', 'email', 'password'] as const) {
        if (fields[key]) createForm.setError(key, { message: fields[key] })
      }
      showToast(errorMessage(requestError, 'Não foi possível cadastrar o cliente.'), 'error')
    }
  }

  const handleEdit = async (values: EditForm) => {
    if (!editing) return
    try {
      const { data: saved } = await userApi.update(editing.id, { nome: values.nome.trim(), email: values.email.trim() })
      upsert(saved)
      showToast('Dados do cliente atualizados.', 'success')
      setMode('closed')
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      for (const key of ['nome', 'email'] as const) {
        if (fields[key]) editForm.setError(key, { message: fields[key] })
      }
      showToast(errorMessage(requestError, 'Não foi possível atualizar o cliente.'), 'error')
    }
  }

  const toggleActive = async (client: User) => {
    if (client.is_active) {
      const ok = await confirm({
        title: `Desativar a conta de ${client.nome}?`,
        description: 'O cliente deixa de conseguir entrar e agendar. O histórico de atendimentos é mantido, e a conta pode ser reativada depois.',
        confirmLabel: 'Desativar conta',
        tone: 'danger',
      })
      if (!ok) return
    }
    setBusyId(client.id)
    try {
      if (client.is_active) {
        await userApi.remove(client.id)
        upsert({ ...client, is_active: false })
        showToast('Conta desativada.', 'success')
      } else {
        const { data: saved } = await userApi.update(client.id, { is_active: true })
        upsert(saved)
        showToast('Conta reativada.', 'success')
      }
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível alterar a conta.'), 'error')
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
        title="Clientes"
        description="Contas de clientes vinculadas à barbearia. Clientes cadastrados aqui já entram e agendam sem passar pelo cadastro público."
        actions={<button type="button" className={ui.button} onClick={openCreate}><UserPlusIcon size={18} /> Novo cliente</button>}
      />

      <section className={ui.panel}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGrow}>
            <SearchField value={query} onChange={setQuery} placeholder="Buscar por nome ou e-mail" />
          </div>
          <SegmentedControl
            label="Filtrar por situação da conta"
            value={status}
            onChange={setStatus}
            options={[
              { value: 'active', label: 'Ativas', count: counts.active },
              { value: 'inactive', label: 'Inativas', count: counts.inactive },
              { value: 'all', label: 'Todas', count: counts.all },
            ]}
          />
        </div>
        <RefreshBar active={isRefreshing} />

        {isLoading ? (
          <SkeletonRows rows={6} label="Carregando clientes" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar os clientes." onRetry={() => void reload()} />
        ) : clients.length === 0 ? (
          <EmptyState
            art="tesoura"
            title="Nenhum cliente cadastrado"
            description="Cadastre clientes para que eles possam entrar e agendar horários nesta barbearia."
            action={{ label: 'Cadastrar cliente', onClick: openCreate }}
          />
        ) : filtered.length === 0 ? (
          <EmptyState compact title="Nenhum cliente encontrado" description="Ajuste a busca ou o filtro de situação." action={{ label: 'Limpar filtros', onClick: () => { setQuery(''); setStatus('all') } }} />
        ) : (
          <>
            <div className={ui.tableWrap}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Atendimentos</th>
                    <th>Última visita</th>
                    <th>Próximo horário</th>
                    <th>Conta</th>
                    <th><span className="sr-only">Ações</span></th>
                  </tr>
                </thead>
                <tbody>
                  {pager.pageItems.map((client) => {
                    const entry = stats.get(client.id)
                    return (
                      <tr key={client.id} className={client.is_active ? undefined : ui.rowInactive}>
                        <td data-primary>
                          <div className={ui.cellPerson}>
                            <Avatar name={client.nome} muted={!client.is_active} />
                            <div style={{ minWidth: 0 }}>
                              <div className={ui.cellTitle}>{client.nome}</div>
                              <div className={ui.cellMuted}>{client.email}</div>
                            </div>
                          </div>
                        </td>
                        <td data-label="Atendimentos" className={ui.numeric}>{entry?.visits ? plural(entry.visits, 'realizado') : <span className={ui.cellMuted}>Nenhum</span>}</td>
                        <td data-label="Última visita" className={ui.numeric}>{entry?.lastVisit ? formatDayShort(dateKey(entry.lastVisit)) : <span className={ui.cellMuted}>—</span>}</td>
                        <td data-label="Próximo horário" className={ui.numeric}>{entry?.next ? formatDayShort(dateKey(entry.next)) : <span className={ui.cellMuted}>—</span>}</td>
                        <td data-label="Conta"><ActiveBadge active={client.is_active} activeLabel="Ativa" inactiveLabel="Inativa" /></td>
                        <td data-actions>
                          <div className={ui.cellActions}>
                            <button type="button" className={`${ui.ghostButton} ${ui.sm}`} onClick={() => openEdit(client)} aria-label={`Editar ${client.nome}`}>
                              <EditIcon size={16} /> Editar
                            </button>
                            <button
                              type="button"
                              className={`${ui.ghostButton} ${ui.sm}`}
                              onClick={() => void toggleActive(client)}
                              disabled={busyId === client.id}
                              aria-label={`${client.is_active ? 'Desativar' : 'Reativar'} conta de ${client.nome}`}
                            >
                              {busyId === client.id ? <ButtonSpinner /> : client.is_active ? <PowerIcon size={16} /> : <RotateCcwIcon size={16} />}
                              {client.is_active ? 'Desativar' : 'Reativar'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
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
        title="Novo cliente"
        description="A conta é criada já vinculada a esta barbearia. Informe ao cliente o e-mail e a senha inicial."
        footer={
          <>
            <button type="button" className={ui.secondaryButton} onClick={() => setMode('closed')} disabled={submitting}>Cancelar</button>
            <button type="submit" form="client-create" className={ui.button} disabled={submitting}>
              {createForm.formState.isSubmitting && <ButtonSpinner />} Cadastrar cliente
            </button>
          </>
        }
      >
        <form id="client-create" className={ui.form} onSubmit={createForm.handleSubmit(handleCreate)} noValidate>
          <Field label="Nome completo" htmlFor="client-nome" error={createErrors.nome?.message}>
            <input {...fieldA11y('client-nome', createErrors.nome?.message)} autoComplete="off" {...createForm.register('nome')} />
          </Field>
          <Field label="E-mail" htmlFor="client-email" error={createErrors.email?.message}>
            <input {...fieldA11y('client-email', createErrors.email?.message)} type="email" autoComplete="off" {...createForm.register('email')} />
          </Field>
          <Field label="Senha inicial" htmlFor="client-password" error={createErrors.password?.message} hint="Mínimo de 8 caracteres, sem ser apenas números. O cliente pode trocá-la em Minha conta.">
            <PasswordInput {...fieldA11y('client-password', createErrors.password?.message, true)} autoComplete="new-password" {...createForm.register('password')} />
          </Field>
        </form>
      </Modal>

      <Modal
        open={mode === 'edit'}
        onClose={() => setMode('closed')}
        dismissible={!submitting}
        title="Editar cliente"
        footer={
          <>
            <button type="button" className={ui.secondaryButton} onClick={() => setMode('closed')} disabled={submitting}>Cancelar</button>
            <button type="submit" form="client-edit" className={ui.button} disabled={submitting}>
              {editForm.formState.isSubmitting && <ButtonSpinner />} Salvar alterações
            </button>
          </>
        }
      >
        <form id="client-edit" className={ui.form} onSubmit={editForm.handleSubmit(handleEdit)} noValidate>
          <Field label="Nome completo" htmlFor="edit-nome" error={editErrors.nome?.message}>
            <input {...fieldA11y('edit-nome', editErrors.nome?.message)} {...editForm.register('nome')} />
          </Field>
          <Field label="E-mail" htmlFor="edit-email" error={editErrors.email?.message} hint="É o e-mail usado para entrar no sistema.">
            <input {...fieldA11y('edit-email', editErrors.email?.message, true)} type="email" {...editForm.register('email')} />
          </Field>
        </form>
      </Modal>
    </div>
  )
}
