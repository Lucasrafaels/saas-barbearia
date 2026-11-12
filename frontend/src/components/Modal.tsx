import { useEffect, useId, useRef, useState, type ReactNode, type RefObject } from 'react'
import { createPortal } from 'react-dom'
import { XIcon } from './Icons'
import ui from '../styles/ui.module.css'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg'
  /** Quando falso, Esc e clique fora não fecham (ex.: durante um envio). */
  dismissible?: boolean
  initialFocusRef?: RefObject<HTMLElement | null>
}

const EXIT_MS = 180
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Diálogo modal acessível: foco preso dentro do diálogo, Esc para fechar,
 * foco devolvido ao elemento que o abriu e rolagem da página bloqueada.
 * Mantém o conteúdo montado durante a animação de saída.
 */
export function Modal({ open, onClose, title, description, children, footer, size = 'md', dismissible = true, initialFocusRef }: ModalProps) {
  const [rendered, setRendered] = useState(open)
  const [closing, setClosing] = useState(false)
  const dialogRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const pointerDownOnBackdrop = useRef(false)
  const titleId = useId()
  const descriptionId = useId()

  // Ajuste de estado durante a renderização (padrão recomendado pelo React)
  if (open && (!rendered || closing)) {
    setRendered(true)
    setClosing(false)
  } else if (!open && rendered && !closing) {
    setClosing(true)
  }

  useEffect(() => {
    if (!closing) return
    const timer = window.setTimeout(() => {
      setRendered(false)
      setClosing(false)
    }, EXIT_MS)
    return () => window.clearTimeout(timer)
  }, [closing])

  // Foco inicial, bloqueio de rolagem e devolução de foco
  useEffect(() => {
    if (!rendered) return
    const previouslyFocused = document.activeElement as HTMLElement | null
    const { overflow } = document.body.style
    document.body.style.overflow = 'hidden'

    const frame = window.requestAnimationFrame(() => {
      const target = initialFocusRef?.current
        ?? dialogRef.current?.querySelector<HTMLElement>('[data-autofocus]')
        ?? bodyRef.current?.querySelector<HTMLElement>(FOCUSABLE)
        ?? dialogRef.current
      target?.focus()
    })

    return () => {
      window.cancelAnimationFrame(frame)
      document.body.style.overflow = overflow
      if (previouslyFocused && document.contains(previouslyFocused)) previouslyFocused.focus()
    }
  }, [rendered, initialFocusRef])

  if (!rendered) return null

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape' && dismissible) {
      event.stopPropagation()
      onClose()
      return
    }
    if (event.key !== 'Tab' || !dialogRef.current) return
    const focusables = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => el.offsetParent !== null)
    if (!focusables.length) return
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  const sizeClass = size === 'sm' ? ui.modalSm : size === 'lg' ? ui.modalLg : ''

  return createPortal(
    <div
      className={`${ui.modalBackdrop} ${closing ? ui.modalClosing : ''}`}
      onMouseDown={(event) => { pointerDownOnBackdrop.current = event.target === event.currentTarget }}
      onMouseUp={(event) => {
        if (dismissible && pointerDownOnBackdrop.current && event.target === event.currentTarget) onClose()
        pointerDownOnBackdrop.current = false
      }}
    >
      <div
        ref={dialogRef}
        className={`${ui.modal} ${sizeClass}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
      >
        <div className={ui.modalHeader}>
          <div>
            <h2 id={titleId}>{title}</h2>
            {description && <div id={descriptionId} className={ui.modalDescription}>{description}</div>}
          </div>
          <button type="button" className={ui.iconButton} onClick={onClose} aria-label="Fechar" disabled={!dismissible}>
            <XIcon size={20} />
          </button>
        </div>
        {children && <div ref={bodyRef} className={ui.modalBody}>{children}</div>}
        {footer && <div className={ui.modalFooter}>{footer}</div>}
      </div>
    </div>,
    document.body,
  )
}
