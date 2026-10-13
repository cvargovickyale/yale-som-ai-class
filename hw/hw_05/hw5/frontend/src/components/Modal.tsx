import { useEffect, useRef, type ReactNode } from 'react'
import { Icon } from './Icon'

/** A calm popup: Esc or the backdrop closes it, focus moves in and returns when it closes. */
export function Modal({ title, eyebrow, onClose, children, footer, wide }: {
  title: string; eyebrow?: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean
}) {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null
    box.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      before?.focus()
    }
  }, [onClose])

  return (
    <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className={`modal${wide ? ' modal-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby="modal-title"
        tabIndex={-1} ref={box}>
        <header className="modal-head">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <h2 id="modal-title">{title}</h2>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="x" /></button>
        </header>
        <div className="modal-body">{children}</div>
        {footer && <footer className="modal-foot">{footer}</footer>}
      </div>
    </div>
  )
}
