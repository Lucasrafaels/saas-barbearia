import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { barbershopApi } from '../api/endpoints'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { errorMessage } from '../utils/format'
import styles from '../styles/auth.module.css'
import ui from '../styles/ui.module.css'

const schema = z.object({
  nome: z.string().min(2, 'Informe o nome da barbearia.'),
  endereco: z.string().min(5, 'Informe um endereço.'),
  telefone: z.string().min(8, 'Informe um telefone.'),
  email: z.string().email('Informe um e-mail válido.'),
  horario_abertura: z.string().regex(/^\d{2}:\d{2}$/, 'Informe a abertura.'),
  horario_fechamento: z.string().regex(/^\d{2}:\d{2}$/, 'Informe o fechamento.'),
})
type Form = z.infer<typeof schema>

export function OnboardingPage() {
  const { refreshUser, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { horario_abertura: '08:00', horario_fechamento: '18:00' },
  })

  const onSubmit = async (values: Form) => {
    try {
      await barbershopApi.create(values)
      await refreshUser()
      showToast('Barbearia criada. Você agora é o administrador.', 'success')
      navigate('/', { replace: true })
    } catch (error) {
      showToast(errorMessage(error, 'Não foi possível criar a barbearia.'), 'error')
    }
  }

  return (
    <main className={styles.authPage}>
      <section className={`${styles.panel} ${styles.widePanel}`}>
        <a href="/" className={styles.brand}>
          <span className={styles.brandMark} aria-hidden="true">B</span>
          BarberPro
        </a>
        <div className={styles.panelHeader}>
          <p className={styles.eyebrow}>Primeiro acesso</p>
          <h1>Cadastre sua barbearia</h1>
          <p className={styles.description}>A API cria a barbearia e promove sua conta a administrador. Se você foi convidado por uma barbearia, peça ao administrador para vincular sua conta.</p>
        </div>
        <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={styles.field}>
            <label htmlFor="nome">Nome</label>
            <input
              id="nome"
              placeholder="Barbearia Central"
              {...register('nome')}
              className={errors.nome ? styles.error : ''}
            />
            {errors.nome && <span className={styles.errorText}>{errors.nome.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="email">E-mail comercial</label>
            <input
              id="email"
              type="email"
              placeholder="contato@barbearia.com"
              {...register('email')}
              className={errors.email ? styles.error : ''}
            />
            {errors.email && <span className={styles.errorText}>{errors.email.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="endereco">Endereço</label>
            <input
              id="endereco"
              placeholder="Rua Exemplo, 100"
              {...register('endereco')}
              className={errors.endereco ? styles.error : ''}
            />
            {errors.endereco && <span className={styles.errorText}>{errors.endereco.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="telefone">Telefone</label>
            <input
              id="telefone"
              inputMode="tel"
              placeholder="(11) 99999-9999"
              {...register('telefone')}
              className={errors.telefone ? styles.error : ''}
            />
            {errors.telefone && <span className={styles.errorText}>{errors.telefone.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="horario_abertura">Abre às</label>
            <input
              id="horario_abertura"
              type="time"
              {...register('horario_abertura')}
              className={errors.horario_abertura ? styles.error : ''}
            />
            {errors.horario_abertura && <span className={styles.errorText}>{errors.horario_abertura.message}</span>}
          </div>
          <div className={styles.field}>
            <label htmlFor="horario_fechamento">Fecha às</label>
            <input
              id="horario_fechamento"
              type="time"
              {...register('horario_fechamento')}
              className={errors.horario_fechamento ? styles.error : ''}
            />
            {errors.horario_fechamento && <span className={styles.errorText}>{errors.horario_fechamento.message}</span>}
          </div>
          <button className={styles.submitButton} disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Criando...' : 'Criar minha barbearia'}
          </button>
        </form>
        <p className={styles.switch}>
          <button type="button" onClick={() => void logout()} className={ui.textButton}>
            Sair da conta
          </button>
        </p>
      </section>
    </main>
  )
}