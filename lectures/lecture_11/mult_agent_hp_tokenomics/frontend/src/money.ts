/** Format small dollar amounts so luna's fractions of a cent stay readable. */
export function usd(value: number | undefined | null): string {
  const v = value ?? 0
  if (v === 0) return '$0'
  if (v < 0.01) return `$${v.toFixed(5)}`
  if (v < 1) return `$${v.toFixed(4)}`
  return `$${v.toFixed(2)}`
}

/** Round up to a "nice" scale (1, 2, 5 × 10ⁿ) so the tube doesn't max out instantly. */
export function niceScale(value: number): number {
  if (value <= 0) return 0.001
  const exp = Math.floor(Math.log10(value * 1.25))
  for (const step of [1, 2, 5, 10]) {
    const candidate = step * 10 ** exp
    if (candidate >= value * 1.25) return candidate
  }
  return 10 ** (exp + 1)
}
