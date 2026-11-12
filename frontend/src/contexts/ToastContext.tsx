import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react'
import { AlertCircleIcon, CheckCircleIcon, InfoIcon, XIcon } from '../components/Icons'
import styles from '../styles/ui.module.css'

type ToastKind = 'success' | 'error' | 'info'

interface Toast {
  id: number
  message: string
  kind: ToastKind
  leaving: boolean
}

interface ToastContextValue {
  showToast: (message: string, kind?: ToastKind) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

const DURATION: Record<ToastKind, number> = { success: 4000, info: 5000, error: 7000 }
const EXIT_MS = 180
const MAX_TOASTS = 4

const icons: Record<ToastKind, typeof CheckCircleIcon> = {
  success: CheckCircleIcon,
  error: AlertCircleIcon,
  info: InfoIcon,
}

const kindClass: Record<ToastKind, string> = {
  success: styles.toastSuccess,
  error: styles.toastError,
  info: styles.toastInfo,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.map((toast) => (toast.id === id ? { ...toast, leaving: true } : toast)))
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), EXIT_MS)
  }, [])

  const showToast = useCallback((message: string, kind: ToastKind = 'info') => {
    const id = nextId.current++
    setToasts((current) => [...current.slice(-(MAX_TOASTS - 1)), { id, message, kind, leaving: false }])
    window.setTimeout(() => dismiss(id), DURATION[kind])
  }, [dismiss])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={styles.toastRegion} aria-live="polite" aria-relevant="additions">
        {toasts.map((toast) => {
          const Icon = icons[toast.kind]
          return (
            <div
              key={toast.id}
              role={toast.kind === 'error' ? 'alert' : 'status'}
              className={`${styles.toast} ${kindClass[toast.kind]} ${toast.leaving ? styles.toastLeaving : ''}`}
            >
              <Icon size={18} className={styles.toastIcon} />
              <span className={styles.toastMessage}>{toast.message}</span>
              <button type="button" className={styles.toastClose} onClick={() => dismiss(toast.id)} aria-label="Fechar aviso">
                <XIcon size={16} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast deve ser usado dentro de ToastProvider.')
  return context
}
