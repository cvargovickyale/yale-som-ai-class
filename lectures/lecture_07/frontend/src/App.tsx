import { useState } from "react"
import "./App.css"
import CourseCatalog from "./components/CourseCatalog"
import ChatPanel from "./components/ChatPanel"
import WindowChrome from "./components/WindowChrome"
import Taskbar from "./components/Taskbar"
import DesktopIcons from "./components/DesktopIcons"

function App() {
  const [chatOpen, setChatOpen] = useState(true)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [startMenuOpen, setStartMenuOpen] = useState(false)
  const [catalogFlash, setCatalogFlash] = useState(false)

  function flashCatalog() {
    setCatalogFlash(true)
    window.setTimeout(() => setCatalogFlash(false), 400)
  }

  const taskButtons = [
    {
      id: "catalog",
      label: "📚 Course Catalog",
      active: catalogFlash,
      onClick: flashCatalog,
    },
    {
      id: "assistant",
      label: "💬 SOM Assistant",
      active: chatOpen,
      onClick: () => setChatOpen((v) => !v),
    },
    ...(aboutOpen
      ? [
          {
            id: "about",
            label: "ℹ️ About",
            active: true,
            onClick: () => setAboutOpen(false),
          },
        ]
      : []),
  ]

  return (
    <div className="desktop" onClick={() => startMenuOpen && setStartMenuOpen(false)}>
      <DesktopIcons onOpenAbout={() => setAboutOpen(true)} onFocusCatalog={flashCatalog} />

      <main className="workspace">
        <WindowChrome
          title="Course Catalog Explorer 2000"
          icon="📚"
          className={`catalog-window ${catalogFlash ? "window-flash" : ""}`}
          statusBarText="Yale SOM · Fall 2026 · yale_som_classes.json"
        >
          <CourseCatalog />
        </WindowChrome>

        {chatOpen && (
          <WindowChrome
            title="SOM Course Assistant"
            icon="💬"
            className="chat-window"
            bodyClassName="chat-window-body"
            onMinimize={() => setChatOpen(false)}
            statusBarText="agent desk · ready"
          >
            <ChatPanel />
          </WindowChrome>
        )}
      </main>

      {aboutOpen && (
        <div className="about-overlay">
          <WindowChrome title="About SOM95 Explorer" icon="ℹ️" className="about-window" onClose={() => setAboutOpen(false)}>
            <div className="about-body">
              <p>
                <strong>SOM95 Course Explorer</strong>
              </p>
              <p>Powered by caffeine, FastAPI, and one very organized JSON file.</p>
              <p>Built for Lecture 07 — Yale SOM AI Class.</p>
              <p className="about-footnote">© 2026 · No cows were harmed in the making of this desktop.</p>
            </div>
          </WindowChrome>
        </div>
      )}

      <Taskbar
        taskButtons={taskButtons}
        startMenuOpen={startMenuOpen}
        onToggleStartMenu={() => setStartMenuOpen((v) => !v)}
        onOpenAbout={() => setAboutOpen(true)}
        onToggleAssistant={() => setChatOpen((v) => !v)}
      />
    </div>
  )
}

export default App
