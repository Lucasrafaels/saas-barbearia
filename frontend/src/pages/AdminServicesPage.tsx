import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { serviceApi } from '../api/endpoints'
import { EmptyState } from '../components/EmptyState'
import { PageLoader } from '../components/PageLoader'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Service } from '../types'
import { errorMessage, formatCurrency } from '../utils/format'
import styles from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const serviceSchema = z.object({
  nome: z.string().min(2, 'Informe o nome do serviço.'),
  descricao: z.string().max(500, 'Use no máximo 500 caracteres.'),
  preco: z.string().refine((value) => !Number.isNaN(Number(value)) && Number(value) >= 0, 'Informe um preço válido.'),
  duracao: z.coerce.number().int().min(1, 'A duração mínima é de 1 minuto.'),
  ativo: z.boolean(),
})
type ServiceForm = z.infer<typeof serviceSchema>

const defaults: ServiceForm = { nome: '', descricao: '', preco: '', duracao: 30, ativo: true }

export function AdminServicesPage() {
  const { showToast } = useToast()
  const [showModal, setShowModal] = useState(false)
  const [editingService, setEditingService] = useState<Service | null>(null)
  const { data, isLoading, error, reload } = useAsyncData(() => serviceApi.list().then((response) => response.data), [])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ServiceForm>({
    resolver: zodResolver(serviceSchema), defaultValues: defaults,
  })

  const openCreateModal = () => {
    setEditingService(null)
    reset(defaults)
    setShowModal(true)
  }

  const openEditModal = (service: Service) => {
    setEditingService(service)
    reset({ nome: service.nome, descricao: service.descricao, preco: service.preco, duracao: service.duracao, ativo: service.ativo })
    setShowModal(true)
  }

  const closeModal = () => {
    setShowModal(false)
    setEditingService(null)
    reset(defaults)
  }

  const save = async (values: ServiceForm) => {
    try {
      if (editingService) await serviceApi.update(editingService.id, values)
      else await serviceApi.create(values)
      await reload()
      showToast(editingService ? 'Serviço atualizado.' : 'Serviço cadastrado.', 'success')
      closeModal()
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível salvar o serviço.'), 'error')
    }
  }

  const remove = async (service: Service) => {
    if (!window.confirm(`Excluir o serviço "${service.nome}"?`)) return
    try {
      await serviceApi.remove(service.id)
      await reload()
      showToast('Serviço excluído.', 'success')
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível excluir o serviço.'), 'error')
    }
  }

  if (isLoading) return <PageLoader label="Carregando serviços..." />
  if (error) return <p className={ui.errorBox}>Não foi possível carregar os serviços.</p>
  const services = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Catálogo da barbearia</p>
          <h1>Gerenciar serviços</h1>
        </div>
        <button className={ui.button} onClick={openCreateModal}>Novo serviço</button>
      </header>

      <div className={ui.dataTable}>
        {services.length === 0 ? (
          <EmptyState title="Nenhum serviço cadastrado" description="Cadastre o primeiro serviço para começar." />
        ) : (
          <>
            <div className={ui.tableContainer}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    <th>Serviço</th>
                    <th>Preço</th>
                    <th>Duração</th>
                    <th>Status</th>
                    <th style={{ width: '120px' }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {services.map((service) => (
                    <tr key={service.id}>
                      <td>
                        <strong>{service.nome}</strong>
                        {service.descricao && <p className={ui.cellMuted}>{service.descricao}</p>}
                      </td>
                      <td className={ui.cellPrice}>{formatCurrency(service.preco)}</td>
                      <td>{service.duracao} min</td>
                      <td>
                        <span className={`ui.badge ${service.ativo ? 'badgeSuccess' : 'badgeWarning'}`}>
                          {service.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>
                      <td>
                        <div className={ui.actionButtons}>
                          <button className={ui.secondaryButton} onClick={() => openEditModal(service)}>Editar</button>
                          <button className={ui.dangerButton} onClick={() => void remove(service)}>Excluir</button>
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
              <h2 id="modal-title">{editingService ? 'Editar serviço' : 'Novo serviço'}</h2>
              <button className={ui.modalClose} onClick={closeModal} aria-label="Fechar">✕</button>
            </div>
            <form className={ui.modalBody} onSubmit={handleSubmit(save)} noValidate>
              <label className={ui.field}>Nome
                <input placeholder="Corte masculino" {...register('nome')} />
                {errors.nome && <small className={ui.error}>{errors.nome.message}</small>}
              </label>
              <label className={ui.field}>Descrição
                <textarea rows={3} placeholder="Descreva o serviço" {...register('descricao')} />
                {errors.descricao && <small className={ui.error}>{errors.descricao.message}</small>}
              </label>
              <div className={ui.inlineFields}>
                <label className={ui.field}>Preço (R$)
                  <input inputMode="decimal" type="number" min="0" step="0.01" placeholder="50,00" {...register('preco')} />
                  {errors.preco && <small className={ui.error}>{errors.preco.message}</small>}
                </label>
                <label className={ui.field}>Duração (min)
                  <input type="number" min="1" {...register('duracao')} />
                  {errors.duracao && <small className={ui.error}>{errors.duracao.message}</small>}
                </label>
              </div>
              <label className={ui.checkbox}><input type="checkbox" {...register('ativo')} /> Serviço ativo</label>
            </form>
            <div className={ui.modalFooter}>
              <button type="button" className={ui.secondaryButton} onClick={closeModal}>Cancelar</button>
              <button type="submit" className={ui.button} disabled={isSubmitting}>
                {isSubmitting ? 'Salvando...' : editingService ? 'Salvar alterações' : 'Cadastrar serviço'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}