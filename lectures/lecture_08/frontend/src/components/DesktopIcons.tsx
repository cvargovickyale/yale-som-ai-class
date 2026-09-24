interface DesktopIconsProps {
  onOpenAbout: () => void
  onFocusCatalog: () => void
}

export default function DesktopIcons({ onOpenAbout, onFocusCatalog }: DesktopIconsProps) {
  return (
    <div className="desktop-icons">
      <button className="desktop-icon" onDoubleClick={onFocusCatalog}>
        <span className="desktop-icon-glyph">📚</span>
        <span className="desktop-icon-label">My Courses</span>
      </button>
      <button className="desktop-icon" onDoubleClick={onOpenAbout}>
        <span className="desktop-icon-glyph">ℹ️</span>
        <span className="desktop-icon-label">About SOM95</span>
      </button>
      <button className="desktop-icon" onDoubleClick={() => undefined}>
        <span className="desktop-icon-glyph">🖧</span>
        <span className="desktop-icon-label">SOM Network</span>
      </button>
      <button className="desktop-icon" onDoubleClick={() => undefined}>
        <span className="desktop-icon-glyph">🗑️</span>
        <span className="desktop-icon-label">Recycle Bin</span>
      </button>
    </div>
  )
}
