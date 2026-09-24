import { useEffect, useState } from "react"
import "./App.css"
import { clearToken, fetchChatHistory, fetchMe, getToken, setToken } from "./api"
import ChatPanel from "./components/ChatPanel"
import CourseCatalog from "./components/CourseCatalog"
import DesktopIcons from "./components/DesktopIcons"
import LoginScreen from "./components/LoginScreen"
import Taskbar from "./components/Taskbar"
import WindowChrome from "./components/WindowChrome"
import type { ChatMessage } from "./types"

function App() {
  const [authChecked, setAuthChecked] = useState(false)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])

  const [chatOpen, setChatOpen] = useState(true)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [startMenuOpen, setStartMenuOpen] = useState(false)
  const [catalogFlash, setCatalogFlash] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setAuthChecked(true)
      return
    }
    fetchMe()
      .then(async (me) => {
        setUserEmail(me.email)
        try {
          setChatHistory(await fetchChatHistory())
        } catch {
          setChatHistory([])
        }
      })
      .catch(() => {
        clearToken()
      })
      .finally(() => setAuthChecked(true))
  }, [])

  function handleAuthenticated(token: string, email: string) {
    setToken(token)
    setUserEmail(email)
    fetchChatHistory()
      .then(setChatHistory)
      .catch(() => setChatHistory([]))
  }

  function handleLogout() {
    clearToken()
    setUserEmail(null)
    setChatHistory([])
  }

  function flashCatalog() {
    setCatalogFlash(true)
    window.setTimeout(() => setCatalogFlash(false), 400)
  }

  if (!authChecked) {
    return <div className="desktop" />
  }

  if (!userEmail) {
    return <LoginScreen onAuthenticated={handleAuthenticated} />
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
          statusBarText="Yale SOM · Fall 2026 · data/yale_som.db"
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
            statusBarText={`agent desk · ready · ${userEmail}`}
          >
            <ChatPanel initialMessages={chatHistory} />
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
              <p>Now backed by a real database, with accounts and saved chat history.</p>
              <p>Built for Lecture 08 — Yale SOM AI Class.</p>
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
        onLogout={handleLogout}
        userEmail={userEmail}
      />
    </div>
  )
}

export default App
