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
        <div className={styles.brand}><span>✂</span> Corte Certo</div>
        <p className={styles.eyebrow}>Primeiro acesso</p>
        <h1>Cadastre sua barbearia</h1>
        <p className={styles.description}>A API cria a barbearia e promove sua conta a administrador. Se você foi convidado por uma barbearia, peça ao administrador para vincular sua conta.</p>
        <form className={ui.form} onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className={ui.formGrid}>
            <label className={ui.field}>Nome
              <input placeholder="Barbearia Central" {...register('nome')} />
              {errors.nome && <small className={ui.error}>{errors.nome.message}</small>}
            </label>
            <label className={ui.field}>E-mail comercial
              <input type="email" placeholder="contato@barbearia.com" {...register('email')} />
              {errors.email && <small className={ui.error}>{errors.email.message}</small>}
            </label>
            <label className={`${ui.field} ${ui.fullWidth}`}>Endereço
              <input placeholder="Rua Exemplo, 100" {...register('endereco')} />
              {errors.endereco && <small className={ui.error}>{errors.endereco.message}</small>}
            </label>
            <label className={ui.field}>Telefone
              <input inputMode="tel" placeholder="(11) 99999-9999" {...register('telefone')} />
              {errors.telefone && <small className={ui.error}>{errors.telefone.message}</small>}
            </label>
            <div className={ui.inlineFields}>
              <label className={ui.field}>Abre às
                <input type="time" {...register('horario_abertura')} />
              </label>
              <label className={ui.field}>Fecha às
                <input type="time" {...register('horario_fechamento')} />
              </label>
            </div>
          </div>
          <button className={ui.button} disabled={isSubmitting} type="submit">{isSubmitting ? 'Criando...' : 'Criar minha barbearia'}</button>
          <button className={ui.textButton} type="button" onClick={() => void logout()}>Sair da conta</button>
        </form>
      </section>
    </main>
  )
}
