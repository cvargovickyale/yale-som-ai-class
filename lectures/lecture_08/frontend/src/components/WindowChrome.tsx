import type { ReactNode } from "react"

interface WindowChromeProps {
  title: string
  icon?: string
  className?: string
  bodyClassName?: string
  onMinimize?: () => void
  onClose?: () => void
  statusBarText?: string
  children: ReactNode
}

export default function WindowChrome({
  title,
  icon = "🗂",
  className = "",
  bodyClassName = "",
  onMinimize,
  onClose,
  statusBarText,
  children,
}: WindowChromeProps) {
  return (
    <section className={`gw-window ${className}`}>
      <header className="gw-titlebar">
        <span className="gw-titlebar-icon" aria-hidden>
          {icon}
        </span>
        <span className="gw-titlebar-text">{title}</span>
        <div className="gw-titlebar-buttons">
          {onMinimize && (
            <button className="gw-title-btn" onClick={onMinimize} aria-label="Minimize">
              _
            </button>
          )}
          {onClose && (
            <button className="gw-title-btn" onClick={onClose} aria-label="Close">
              ×
            </button>
          )}
        </div>
      </header>
      <div className={`gw-window-body ${bodyClassName}`}>{children}</div>
      {statusBarText && <footer className="gw-statusbar">{statusBarText}</footer>}
    </section>
  )
}
