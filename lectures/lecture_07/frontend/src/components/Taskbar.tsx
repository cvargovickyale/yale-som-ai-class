import { useEffect, useState } from "react"

interface TaskButton {
  id: string
  label: string
  active: boolean
  onClick: () => void
}

interface TaskbarProps {
  taskButtons: TaskButton[]
  startMenuOpen: boolean
  onToggleStartMenu: () => void
  onOpenAbout: () => void
  onToggleAssistant: () => void
}

export default function Taskbar({
  taskButtons,
  startMenuOpen,
  onToggleStartMenu,
  onOpenAbout,
  onToggleAssistant,
}: TaskbarProps) {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })

  return (
    <>
      {startMenuOpen && (
        <div className="start-menu bevel-raised">
          <button
            className="start-menu-item"
            onClick={() => {
              onOpenAbout()
              onToggleStartMenu()
            }}
          >
            ℹ️ About SOM95 Explorer
          </button>
          <button
            className="start-menu-item"
            onClick={() => {
              onToggleAssistant()
              onToggleStartMenu()
            }}
          >
            💬 Toggle Course Assistant
          </button>
          <div className="start-menu-divider" />
          <button
            className="start-menu-item"
            onClick={() => {
              window.alert("Just kidding — this is a course catalog, not a shutdown switch.")
              onToggleStartMenu()
            }}
          >
            ⏻ Shut Down…
          </button>
        </div>
      )}
      <footer className="taskbar bevel-raised">
        <button className={`start-btn bevel-raised ${startMenuOpen ? "chip-active bevel-in" : ""}`} onClick={onToggleStartMenu}>
          🐮 Start
        </button>
        <div className="taskbar-divider" />
        <div className="taskbar-tasks">
          {taskButtons.map((btn) => (
            <button
              key={btn.id}
              className={`taskbar-task ${btn.active ? "bevel-in chip-active" : "bevel-raised"}`}
              onClick={btn.onClick}
            >
              {btn.label}
            </button>
          ))}
        </div>
        <div className="taskbar-clock bevel-in">{time}</div>
      </footer>
    </>
  )
}
