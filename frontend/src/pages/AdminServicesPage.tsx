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
  const [editing, setEditing] = useState<Service | null>(null)
  const { data, isLoading, error, reload } = useAsyncData(() => serviceApi.list().then((response) => response.data), [])
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ServiceForm>({
    resolver: zodResolver(serviceSchema), defaultValues: defaults,
  })

  const beginEdit = (service: Service) => {
    setEditing(service)
    reset({ nome: service.nome, descricao: service.descricao, preco: service.preco, duracao: service.duracao, ativo: service.ativo })
  }

  const clearForm = () => { setEditing(null); reset(defaults) }

  const save = async (values: ServiceForm) => {
    try {
      if (editing) await serviceApi.update(editing.id, values)
      else await serviceApi.create(values)
      await reload()
      showToast(editing ? 'Serviço atualizado.' : 'Serviço cadastrado.', 'success')
      clearForm()
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível salvar o serviço.'), 'error')
    }
  }

  const remove = async (service: Service) => {
    if (!window.confirm(`Excluir o serviço “${service.nome}”?`)) return
    try {
      await serviceApi.remove(service.id)
      await reload()
      if (editing?.id === service.id) clearForm()
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
      <header className={styles.pageHeader}><div><p className={styles.eyebrow}>Catálogo da barbearia</p><h1>Gerenciar serviços</h1></div></header>
      <div className={styles.adminSplit}>
        <section className={ui.formCard}>
          <h2>{editing ? 'Editar serviço' : 'Novo serviço'}</h2>
          <form className={ui.form} onSubmit={handleSubmit(save)} noValidate>
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
            <div className={ui.buttonRow}>
              <button className={ui.button} disabled={isSubmitting} type="submit">{isSubmitting ? 'Salvando...' : editing ? 'Salvar alterações' : 'Cadastrar serviço'}</button>
              {editing && <button className={ui.secondaryButton} type="button" onClick={clearForm}>Cancelar edição</button>}
            </div>
          </form>
        </section>
        <section>
          <h2 className={styles.sectionTitle}>Serviços cadastrados</h2>
          {services.length === 0 ? <EmptyState title="Nenhum serviço" description="Cadastre o primeiro serviço ao lado." /> : <div className={styles.managementList}>
            {services.map((service) => <article className={styles.managementCard} key={service.id}>
              <div><h3>{service.nome} {!service.ativo && <span className={styles.inactive}>Inativo</span>}</h3><p>{service.descricao || 'Sem descrição'}</p><small>{formatCurrency(service.preco)} · {service.duracao} min</small></div>
              <div className={styles.cardActions}><button className={ui.secondaryButton} onClick={() => beginEdit(service)}>Editar</button><button className={ui.dangerButton} onClick={() => void remove(service)}>Excluir</button></div>
            </article>)}
          </div>}
        </section>
      </div>
    </div>
  )
}
