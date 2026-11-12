import { zodResolver } from '@hookform/resolvers/zod'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { listAllServices, serviceApi } from '../api/endpoints'
import { ActiveBadge, ButtonSpinner, Field, fieldA11y, Pagination, SearchField, SegmentedControl } from '../components/Controls'
import { EmptyState, ErrorState, RefreshBar, SkeletonRows } from '../components/Feedback'
import { ChevronDownIcon, ChevronUpIcon, EditIcon, PlusIcon, PowerIcon, RotateCcwIcon, ScissorsIcon, SortIcon } from '../components/Icons'
import { Modal } from '../components/Modal'
import { PageHeader } from '../components/PageHeader'
import { useConfirm } from '../contexts/ConfirmContext'
import { useToast } from '../contexts/ToastContext'
import { useAsyncData } from '../hooks/useAsyncData'
import { useLocalPagination } from '../hooks/useUi'
import type { Service } from '../types'
import { errorMessage, fieldErrors, formatCurrency, formatDuration, matchesSearch, moneyToInput, parseMoneyInput, plural } from '../utils/format'
import page from '../styles/page.module.css'
import ui from '../styles/ui.module.css'

const serviceSchema = z.object({
  nome: z.string().trim().min(2, 'Informe o nome do serviço.').max(150, 'Use no máximo 150 caracteres.'),
  descricao: z.string().max(500, 'Use no máximo 500 caracteres.'),
  preco: z.string().trim().min(1, 'Informe o preço.').refine((value) => parseMoneyInput(value) !== null, 'Use um valor como 45 ou 45,90.'),
  duracao: z.coerce.number({ invalid_type_error: 'Informe a duração em minutos.' }).int('Use minutos inteiros.').min(5, 'A duração mínima é de 5 minutos.').max(600, 'A duração máxima é de 10 horas.'),
  ativo: z.boolean(),
})
type ServiceForm = z.infer<typeof serviceSchema>

const defaults: ServiceForm = { nome: '', descricao: '', preco: '', duracao: 30, ativo: true }

type StatusFilter = 'all' | 'active' | 'inactive'
type SortKey = 'nome' | 'preco' | 'duracao'

export function AdminServicesPage() {
  const { showToast } = useToast()
  const confirm = useConfirm()
  const { data, isLoading, isRefreshing, error, reload, setData } = useAsyncData(listAllServices, [])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<StatusFilter>('all')
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'nome', dir: 'asc' })
  const [editing, setEditing] = useState<Service | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)

  const form = useForm<ServiceForm>({ resolver: zodResolver(serviceSchema), defaultValues: defaults })
  const { register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = form

  const services = useMemo(() => data ?? [], [data])
  const counts = useMemo(() => ({
    all: services.length,
    active: services.filter((item) => item.ativo).length,
    inactive: services.filter((item) => !item.ativo).length,
  }), [services])

  const filtered = useMemo(() => {
    const list = services.filter((item) =>
      (status === 'all' || (status === 'active') === item.ativo) && matchesSearch(query, item.nome, item.descricao))
    const factor = sort.dir === 'asc' ? 1 : -1
    return list.sort((a, b) => {
      if (sort.key === 'nome') return a.nome.localeCompare(b.nome, 'pt-BR') * factor
      if (sort.key === 'preco') return (Number(a.preco) - Number(b.preco)) * factor
      return (a.duracao - b.duracao) * factor
    })
  }, [services, status, query, sort])

  const pager = useLocalPagination(filtered, 20, `${status}|${query}|${sort.key}|${sort.dir}`)

  const openCreate = () => {
    setEditing(null)
    reset(defaults)
    setModalOpen(true)
  }

  const openEdit = (service: Service) => {
    setEditing(service)
    reset({ nome: service.nome, descricao: service.descricao, preco: moneyToInput(service.preco), duracao: service.duracao, ativo: service.ativo })
    setModalOpen(true)
  }

  const upsert = (service: Service) => {
    setData((current) => {
      const list = current ?? []
      return list.some((item) => item.id === service.id) ? list.map((item) => (item.id === service.id ? service : item)) : [...list, service]
    })
  }

  const save = async (values: ServiceForm) => {
    const payload = { ...values, nome: values.nome.trim(), descricao: values.descricao.trim(), preco: parseMoneyInput(values.preco) ?? '0.00' }
    try {
      const { data: saved } = editing ? await serviceApi.update(editing.id, payload) : await serviceApi.create(payload)
      upsert(saved)
      showToast(editing ? 'Serviço atualizado.' : 'Serviço cadastrado.', 'success')
      setModalOpen(false)
    } catch (requestError) {
      const fields = fieldErrors(requestError)
      for (const key of ['nome', 'descricao', 'preco', 'duracao'] as const) {
        if (fields[key]) setError(key, { message: fields[key] })
      }
      showToast(errorMessage(requestError, 'Não foi possível salvar o serviço.'), 'error')
    }
  }

  const toggleActive = async (service: Service) => {
    if (service.ativo) {
      const ok = await confirm({
        title: `Desativar “${service.nome}”?`,
        description: 'O serviço deixa de aparecer para novos agendamentos. Agendamentos existentes e o histórico de faturamento são mantidos, e você pode reativá-lo quando quiser.',
        confirmLabel: 'Desativar serviço',
        tone: 'danger',
      })
      if (!ok) return
    }
    setBusyId(service.id)
    try {
      if (service.ativo) {
        await serviceApi.remove(service.id)
        upsert({ ...service, ativo: false })
        showToast('Serviço desativado.', 'success')
      } else {
        const { data: saved } = await serviceApi.update(service.id, { ativo: true })
        upsert(saved)
        showToast('Serviço reativado.', 'success')
      }
    } catch (requestError) {
      showToast(errorMessage(requestError, 'Não foi possível alterar o serviço.'), 'error')
    } finally {
      setBusyId(null)
    }
  }

  const sortHeader = (key: SortKey, label: string, align?: 'right') => {
    const active = sort.key === key
    return (
      <th aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'} className={align === 'right' ? ui.alignRight : undefined}>
        <button type="button" onClick={() => setSort({ key, dir: active && sort.dir === 'asc' ? 'desc' : 'asc' })}>
          {label}
          {active ? (sort.dir === 'asc' ? <ChevronUpIcon size={14} /> : <ChevronDownIcon size={14} />) : <SortIcon size={14} />}
        </button>
      </th>
    )
  }

  return (
    <div className={page.page}>
      <PageHeader
        title="Serviços"
        description="O catálogo que os clientes veem ao agendar. Preço e duração definem os horários disponíveis."
        actions={<button type="button" className={ui.button} onClick={openCreate}><PlusIcon size={18} /> Novo serviço</button>}
      />

      <section className={ui.panel}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGrow}>
            <SearchField value={query} onChange={setQuery} placeholder="Buscar por nome ou descrição" />
          </div>
          <SegmentedControl
            label="Filtrar por situação"
            value={status}
            onChange={setStatus}
            options={[
              { value: 'all', label: 'Todos', count: counts.all },
              { value: 'active', label: 'Ativos', count: counts.active },
              { value: 'inactive', label: 'Inativos', count: counts.inactive },
            ]}
          />
        </div>
        <RefreshBar active={isRefreshing} />

        {isLoading ? (
          <SkeletonRows rows={5} label="Carregando serviços" />
        ) : error && !data ? (
          <ErrorState error={error} fallback="Não foi possível carregar os serviços." onRetry={() => void reload()} />
        ) : services.length === 0 ? (
          <EmptyState
            icon={<ScissorsIcon size={22} />}
            title="Nenhum serviço cadastrado"
            description="Cadastre o primeiro serviço com preço e duração para liberar os agendamentos."
            action={{ label: 'Cadastrar serviço', onClick: openCreate }}
          />
        ) : filtered.length === 0 ? (
          <EmptyState compact title="Nenhum serviço encontrado" description="Ajuste a busca ou o filtro de situação." action={{ label: 'Limpar filtros', onClick: () => { setQuery(''); setStatus('all') } }} />
        ) : (
          <>
            <div className={ui.tableWrap}>
              <table className={ui.table}>
                <thead>
                  <tr>
                    {sortHeader('nome', 'Serviço')}
                    {sortHeader('preco', 'Preço', 'right')}
                    {sortHeader('duracao', 'Duração')}
                    <th>Situação</th>
                    <th><span className="sr-only">Ações</span></th>
                  </tr>
                </thead>
                <tbody>
                  {pager.pageItems.map((service) => (
                    <tr key={service.id} className={service.ativo ? undefined : ui.rowInactive}>
                      <td data-primary>
                        <div className={ui.cellTitle}>{service.nome}</div>
                        {service.descricao && <div className={`${ui.cellMuted} ${ui.cellClamp}`}>{service.descricao}</div>}
                      </td>
                      <td data-label="Preço" className={`${ui.numeric} ${ui.alignRight}`}>{formatCurrency(service.preco)}</td>
                      <td data-label="Duração" className={ui.numeric}>{formatDuration(service.duracao)}</td>
                      <td data-label="Situação"><ActiveBadge active={service.ativo} /></td>
                      <td data-actions>
                        <div className={ui.cellActions}>
                          <button type="button" className={`${ui.ghostButton} ${ui.sm}`} onClick={() => openEdit(service)} aria-label={`Editar ${service.nome}`}>
                            <EditIcon size={16} /> Editar
                          </button>
                          <button
                            type="button"
                            className={`${ui.ghostButton} ${ui.sm}`}
                            onClick={() => void toggleActive(service)}
                            disabled={busyId === service.id}
                            aria-label={`${service.ativo ? 'Desativar' : 'Reativar'} ${service.nome}`}
                          >
                            {busyId === service.id ? <ButtonSpinner /> : service.ativo ? <PowerIcon size={16} /> : <RotateCcwIcon size={16} />}
                            {service.ativo ? 'Desativar' : 'Reativar'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={pager.page} count={pager.total} pageSize={pager.pageSize} onChange={pager.setPage} />
            {pager.total <= pager.pageSize && <p className={ui.resultMeta} style={{ borderTop: '1px solid var(--color-border)', borderBottom: 0 }}>{plural(filtered.length, 'serviço')}</p>}
          </>
        )}
      </section>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        dismissible={!isSubmitting}
        title={editing ? 'Editar serviço' : 'Novo serviço'}
        description={editing ? 'Mudanças de preço valem para novos agendamentos; os já marcados mantêm o preço original.' : 'Os clientes verão nome, descrição, preço e duração ao agendar.'}
        footer={
          <>
            <button type="button" className={ui.secondaryButton} onClick={() => setModalOpen(false)} disabled={isSubmitting}>Cancelar</button>
            <button type="submit" form="service-form" className={ui.button} disabled={isSubmitting}>
              {isSubmitting && <ButtonSpinner />}
              {editing ? 'Salvar alterações' : 'Cadastrar serviço'}
            </button>
          </>
        }
      >
        <form id="service-form" className={ui.form} onSubmit={handleSubmit(save)} noValidate>
          <Field label="Nome" htmlFor="service-nome" error={errors.nome?.message}>
            <input {...fieldA11y('service-nome', errors.nome?.message)} placeholder="Corte masculino" {...register('nome')} />
          </Field>
          <Field label="Descrição" htmlFor="service-descricao" error={errors.descricao?.message} optional hint="Aparece para o cliente abaixo do nome.">
            <textarea {...fieldA11y('service-descricao', errors.descricao?.message, true)} rows={3} placeholder="Tesoura ou máquina, com lavagem e finalização." {...register('descricao')} />
          </Field>
          <div className={ui.fieldRow}>
            <Field label="Preço" htmlFor="service-preco" error={errors.preco?.message}>
              <div className={`${ui.inputWrap} ${ui.inputWithPrefix}`}>
                <span className={ui.inputPrefix} aria-hidden="true">R$</span>
                <input {...fieldA11y('service-preco', errors.preco?.message)} inputMode="decimal" placeholder="60,00" {...register('preco')} />
              </div>
            </Field>
            <Field label="Duração (minutos)" htmlFor="service-duracao" error={errors.duracao?.message} hint="Define o intervalo dos horários.">
              <input {...fieldA11y('service-duracao', errors.duracao?.message, true)} type="number" inputMode="numeric" min={5} step={5} {...register('duracao')} />
            </Field>
          </div>
          <label className={ui.switch}>
            <input type="checkbox" {...register('ativo')} />
            <span className={ui.switchText}>
              Disponível para agendamento
              <small>Serviços inativos ficam ocultos para os clientes.</small>
            </span>
          </label>
        </form>
      </Modal>
    </div>
  )
}
