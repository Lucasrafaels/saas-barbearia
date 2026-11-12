import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { Modal } from '../components/Modal'
import ui from '../styles/ui.module.css'

interface ConfirmOptions {
  title: string
  description?: ReactNode
  confirmLabel: string
  cancelLabel?: string
  tone?: 'danger' | 'default'
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>

const ConfirmContext = createContext<ConfirmFn | undefined>(undefined)

/** Substitui window.confirm por um diálogo acessível e consistente com a interface. */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null)
  const [open, setOpen] = useState(false)
  const resolver = useRef<((value: boolean) => void) | null>(null)

  const confirm = useCallback<ConfirmFn>((next) => {
    resolver.current?.(false)
    setOptions(next)
    setOpen(true)
    return new Promise<boolean>((resolve) => { resolver.current = resolve })
  }, [])

  const settle = (value: boolean) => {
    resolver.current?.(value)
    resolver.current = null
    setOpen(false)
  }

  const value = useMemo(() => confirm, [confirm])

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      <Modal
        open={open}
        onClose={() => settle(false)}
        title={options?.title ?? ''}
        description={options?.description}
        size="sm"
        footer={
          <>
            <button type="button" className={ui.secondaryButton} onClick={() => settle(false)} data-autofocus={options?.tone === 'danger' ? true : undefined}>
              {options?.cancelLabel ?? 'Voltar'}
            </button>
            <button
              type="button"
              data-autofocus={options?.tone === 'danger' ? undefined : true}
              className={options?.tone === 'danger' ? ui.dangerSolidButton : ui.button}
              onClick={() => settle(true)}
            >
              {options?.confirmLabel}
            </button>
          </>
        }
      />
    </ConfirmContext.Provider>
  )
}

export function useConfirm(): ConfirmFn {
  const context = useContext(ConfirmContext)
  if (!context) throw new Error('useConfirm deve ser usado dentro de ConfirmProvider.')
  return context
}
