import { useState } from 'react'

// "Find your fit": a flat figure whose clothing zones are clickable category
// filters (P10). Pure SVG + CSS, no images; zones map to the backend's six
// categories (backend/main.py CATEGORIES).
const ZONES = [
  { category: 'Hoodies', label: 'Hood', hint: 'Hoodies' },
  { category: 'Quarter-Zips', label: 'Zip collar', hint: 'Quarter-zips' },
  { category: 'Crewnecks', label: 'Chest', hint: 'Crewnecks' },
  { category: 'T-Shirts', label: 'Short sleeves', hint: 'T-shirts' },
  { category: 'Long Sleeves', label: 'Long sleeves', hint: 'Long sleeves' },
  { category: 'Jackets', label: 'Outer layer', hint: 'Jackets & fleece' },
] as const

type Category = (typeof ZONES)[number]['category']

interface Props {
  counts: Map<string, number>
  active?: string | null
  onPick: (category: string) => void
  compact?: boolean
}

export default function FitPicker({ counts, active, onPick, compact }: Props) {
  const [hover, setHover] = useState<Category | null>(null)
  const lit = hover ?? (active as Category | null)

  // One clickable, keyboard-focusable SVG group per zone.
  const zone = (category: Category, children: React.ReactNode) => {
    const z = ZONES.find((x) => x.category === category)!
    return (
      <g
        className={`fit-zone${lit === category ? ' lit' : ''}`}
        role="button"
        tabIndex={0}
        aria-label={`${z.label}: shop ${z.hint} (${counts.get(category) ?? 0})`}
        onClick={() => onPick(category)}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), onPick(category))}
        onMouseEnter={() => setHover(category)}
        onMouseLeave={() => setHover(null)}
        onFocus={() => setHover(category)}
        onBlur={() => setHover(null)}
      >
        {children}
      </g>
    )
  }

  return (
    <div className={`fit-picker${compact ? ' compact' : ''}`}>
      <svg viewBox="0 0 220 300" className="fit-figure" aria-label="Clothing picker">
        {/* not clickable: head, legs */}
        <path className="fit-base" d="M76 206 h68 l-6 86 h-22 l-6 -60 l-6 60 h-22 z" />
        {zone('Hoodies', <path d="M70 84 C62 30 158 30 150 84 C140 70 80 70 70 84 Z" />)}
        <circle className="fit-skin" cx="110" cy="58" r="22" />
        {zone('Long Sleeves', <>
          <path d="M50 126 L30 196 L45 201 L66 140 Z" />
          <path d="M170 126 L190 196 L175 201 L154 140 Z" />
        </>)}
        {zone('T-Shirts', <>
          <path d="M72 88 L44 104 L50 128 L68 142 Z" />
          <path d="M148 88 L176 104 L170 128 L152 142 Z" />
        </>)}
        {zone('Crewnecks', <path d="M78 86 C92 96 128 96 142 86 L150 120 L146 208 L74 208 L70 120 Z" />)}
        {zone('Jackets', <>
          <path d="M70 88 L84 90 L82 210 L66 210 L64 120 Z" />
          <path d="M150 88 L136 90 L138 210 L154 210 L156 120 Z" />
        </>)}
        {zone('Quarter-Zips', <path d="M101 88 h18 v40 l-9 6 l-9 -6 Z" />)}
        <line className="fit-zipline" x1="110" y1="92" x2="110" y2="128" />
      </svg>

      <ul className="fit-legend">
        {ZONES.map((z) => (
          <li key={z.category}>
            <button
              title={`${z.label}: ${z.hint}`}
              className={lit === z.category ? 'lit' : ''}
              onClick={() => onPick(z.category)}
              onMouseEnter={() => setHover(z.category)}
              onMouseLeave={() => setHover(null)}
            >
              <span>{z.label}</span>
              <span className="fit-hint">
                <span>{z.hint}</span>
                <span className="fit-count">{counts.get(z.category) ?? 0}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
