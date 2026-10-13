const PATHS: Record<string, string> = {
  shirt: 'M8 4l4 2 4-2 4 3-2 4h-2v9H8v-9H6L4 7z',
  key: 'M14 10a4 4 0 1 0-3.5 4L9 15.5V18h2.5v2H14v-2.5l1.5-1.5A4 4 0 0 0 14 10zm1-1h.01',
  tag: 'M3 12V4h8l9 9-8 8zM7.5 7.5h.01',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  x: 'M6 6l12 12M18 6L6 18',
  info: 'M12 8h.01M11 12h1v5h1M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  refresh: 'M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5',
  play: 'M8 5v14l11-7z',
  mail: 'M4 6h16v12H4zM4 7l8 6 8-6',
  coins: 'M12 7c4 0 7-1.1 7-2.5S16 2 12 2 5 3.1 5 4.5 8 7 12 7zM5 4.5v5C5 10.9 8 12 12 12s7-1.1 7-2.5v-5M5 9.5v5c0 1.4 3 2.5 7 2.5s7-1.1 7-2.5v-5',
  alert: 'M12 9v4M12 17h.01M10.3 3.9L2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  box: 'M3 7l9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10',
}

export function Icon({ name, size = 18, label }: { name: keyof typeof PATHS | string; size?: number; label?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" role={label ? 'img' : undefined} aria-label={label}
      aria-hidden={label ? undefined : true} style={{ flex: 'none' }}>
      <path d={PATHS[name] ?? PATHS.info} />
    </svg>
  )
}
