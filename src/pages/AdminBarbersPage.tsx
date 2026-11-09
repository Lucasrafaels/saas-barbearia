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
import { XIcon } from '../components/Icons'
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

const newBarberDefaults: NewBarberForm = { nome: '', email: '', password: '', especialidade: '', ativo: true }
const editBarberDefaults: EditBarberForm = { especialidade: '', ativo: true }

export function AdminBarbersPage() {
  const { showToast } = useToast()
  const [showModal, setShowModal] = useState(false)
  const [editingBarber, setEditingBarber] = useState<Barber | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'ativo' | 'inativo'>('all')

  const { data: barbersData, isLoading: loadingBarbers, error: errorBarbers, reload: reloadBarbers } = useAsyncData(
    () => barberApi.list().then((response) => response.data),
    []
  )

  // Create form
  const createForm = useForm<NewBarberForm>({
    resolver: zodResolver(newBarberSchema),
    defaultValues: newBarberDefaults,
  })

  // Edit form
  const editForm = useForm<EditBarberForm>({
    resolver: zodResolver(editBarberSchema),
    defaultValues: editBarberDefaults,
  })

  const isEditMode = Boolean(editingBarber)

  const openCreateModal = () => {
    setEditingBarber(null)
    createForm.reset(newBarberDefaults)
    setShowModal(true)
  }

  const openEditModal = (barber: Barber) => {
    setEditingBarber(barber)
    editForm.reset({ especialidade: barber.especialidade, ativo: barber.ativo })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingBarber(null)
    createForm.reset(newBarberDefaults)
    editForm.reset(editBarberDefaults)
  }

  const handleCreateSubmit = async (values: NewBarberForm) => {
    try {
      const userResponse = await userApi.create({ email: values.email, nome: values.nome, password: values.password, tipo_perfil: 'barbeiro' })
      const createdUser = userResponse.data
      // Create the barber profile linked to the user
      await barberApi.create({ user: createdUser.id, especialidade: values.especialidade, ativo: values.ativo })
      await reloadBarbers()
      showToast('Barbeiro cadastrado.', 'success')
      closeModal()
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível cadastrar o barbeiro.'), 'error')
    }
  }

  const handleEditSubmit = async (values: EditBarberForm) => {
    if (!editingBarber) return
    try {
      await barberApi.update(editingBarber.id, values)
      await reloadBarbers()
      showToast('Barbeiro atualizado.', 'success')
      closeModal()
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível atualizar o barbeiro.'), 'error')
    }
  }

  const remove = async (barber: Barber) => {
    if (!window.confirm(`Excluir o barbeiro "${barber.nome}"?`)) return
    try {
      await barberApi.remove(barber.id)
      await reloadBarbers()
      showToast('Barbeiro excluído.', 'success')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível excluir o barbeiro.'), 'error')
    }
  }

  if (loadingBarbers) return <PageLoader label="Carregando barbeiros..." />
  if (errorBarbers) return <p className={ui.errorBox}>Não foi possível carregar os barbeiros.</p>
  const allBarbers = barbersData?.results ?? []

  // Apply status filter
  const barbers = allBarbers.filter(barber => {
    if (statusFilter === 'all') return true
    if (statusFilter === 'ativo') return barber.ativo
    if (statusFilter === 'inativo') return !barber.ativo
    return true
  })

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Equipe da barbearia</p>
          <h1>Gerenciar barbeiros</h1>
        </div>
        <button className={ui.button} onClick={openCreateModal}>Novo barbeiro</button>
      </header>

      <div className={ui.dataTable}>
        {barbers.length === 0 ? (
          <EmptyState title="Nenhum barbeiro cadastrado" description="Cadastre o primeiro barbeiro para começar." />
        ) : (
          <>
            <div className={ui.filterBar}>
              <div className={ui.filterGroup}>
                <label htmlFor="status-filter">Status</label>
                <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as 'all' | 'ativo' | 'inativo')}>
                  <option value="all">Todos</option>
                  <option value="ativo">Ativos</option>
                  <option value="inativo">Inativos</option>
                </select>
              </div>
            </div>

            <div className={ui.tableContainer}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Barbeiro</th>
                    <th>E-mail</th>
                    <th>Especialidade</th>
                    <th>Status</th>
                    <th style={{ width: '140px' }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {barbers.map((barber) => (
                    <tr key={barber.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                          <span className={ui.avatar} style={{ width: '2.5rem', height: '2.5rem', fontSize: 'var(--text-base)' }}>
                            {barber.nome.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                          </span>
                          <strong>{barber.nome}</strong>
                        </div>
                      </td>
                      <td>{barber.email}</td>
                      <td>{barber.especialidade || <span className={ui.cellMuted}>—</span>}</td>
                      <td>
                        <span className={`ui.badge ${barber.ativo ? 'badgeSuccess' : 'badgeWarning'}`}>
                          {barber.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>
                      <td>
                        <div className={ui.actionButtons}>
                          <button className={ui.secondaryButton} onClick={() => openEditModal(barber)}>Editar</button>
                          <button className={ui.dangerButton} onClick={() => void remove(barber)}>Excluir</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className={ui.modalOverlay} onClick={closeModal} role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className={ui.modal} onClick={(e) => e.stopPropagation()}>
            <div className={ui.modalHeader}>
              <h2 id="modal-title">{isEditMode ? 'Editar barbeiro' : 'Novo barbeiro'}</h2>
              <button className={ui.modalClose} onClick={closeModal} aria-label="Fechar"><XIcon size={20} /></button>
            </div>
            {!isEditMode ? (
              <form className={ui.modalBody} onSubmit={createForm.handleSubmit(handleCreateSubmit)} noValidate>
                <label className={ui.field}>Nome completo
                  <input placeholder="João Silva" {...createForm.register('nome')} />
                  {createForm.formState.errors.nome && <small className={ui.error}>{createForm.formState.errors.nome.message}</small>}
                </label>
                <label className={ui.field}>E-mail
                  <input type="email" placeholder="joao@exemplo.com" {...createForm.register('email')} />
                  {createForm.formState.errors.email && <small className={ui.error}>{createForm.formState.errors.email.message}</small>}
                </label>
                <label className={ui.field}>Senha
                  <input type="password" placeholder="••••••••" {...createForm.register('password')} />
                  {createForm.formState.errors.password && <small className={ui.error}>{createForm.formState.errors.password.message}</small>}
                </label>
                <label className={ui.field}>Especialidade
                  <input placeholder="Ex.: Barba, Corte degradê, Colorimetria" {...createForm.register('especialidade')} />
                  {createForm.formState.errors.especialidade && <small className={ui.error}>{createForm.formState.errors.especialidade.message}</small>}
                </label>
                <label className={ui.checkbox}><input type="checkbox" {...createForm.register('ativo')} /> Barbeiro ativo</label>
                <div className={ui.modalFooter}>
                  <button type="button" className={ui.secondaryButton} onClick={closeModal}>Cancelar</button>
                  <button type="submit" className={ui.button} disabled={createForm.formState.isSubmitting}>
                    {createForm.formState.isSubmitting ? 'Salvando...' : 'Cadastrar barbeiro'}
                  </button>
                </div>
              </form>
            ) : (
              <form className={ui.modalBody} onSubmit={editForm.handleSubmit(handleEditSubmit)} noValidate>
                <label className={ui.field}>Especialidade
                  <input placeholder="Ex.: Barba, Corte degradê, Colorimetria" {...editForm.register('especialidade')} />
                  {editForm.formState.errors.especialidade && <small className={ui.error}>{editForm.formState.errors.especialidade.message}</small>}
                </label>
                <label className={ui.checkbox}><input type="checkbox" {...editForm.register('ativo')} /> Barbeiro ativo</label>
                <div className={ui.modalFooter}>
                  <button type="button" className={ui.secondaryButton} onClick={closeModal}>Cancelar</button>
                  <button type="submit" className={ui.button} disabled={editForm.formState.isSubmitting}>
                    {editForm.formState.isSubmitting ? 'Salvando...' : 'Salvar alterações'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}