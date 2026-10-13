import { useEffect, useRef, useState } from 'react'

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Counts smoothly from the old value to the new one, so a payment visibly lands. */
export function useAnimatedNumber(target: number | null, ms = 1100): number | null {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target === null) { setShown(null); return }
    const start = from.current ?? target
    from.current = target
    if (start === target || prefersReducedMotion()) { setShown(target); return }
    let raf = 0
    const t0 = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / ms)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(start + (target - start) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return shown
}

export function useLocalStorage(key: string, initial: string) {
  const [value, setValue] = useState(() => localStorage.getItem(key) ?? initial)
  useEffect(() => { localStorage.setItem(key, value) }, [key, value])
  return [value, setValue] as const
}
