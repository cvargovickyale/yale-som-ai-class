// Catalogue photos come three ways (measured in P10/P11):
//   1. on white: shown as-is
//   2. a light photo boxed inside black side bars (5-29% per side): the bars
//      are measured from a 64px copy and clipped off with CSS `clip-path`
//      (cheap: the browser just doesn't paint those edges)
//   3. a dark garment shot on a black background: no edge to trim (navy
//      fabric reads as "dark" all the way to the middle), so the photo gets a
//      black frame instead (`dark-bg` on its container)
// Results are cached per URL.

const SAMPLE = 64
type Fit = { inset: string | null; darkBackground: boolean }
const cache = new Map<string, Fit>()

const isDark = (d: Uint8ClampedArray, i: number) => d[i] + d[i + 1] + d[i + 2] < 120

function measure(img: HTMLImageElement): Fit {
  if (cache.has(img.src)) return cache.get(img.src)!
  let fit: Fit = { inset: null, darkBackground: false }
  try {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = SAMPLE
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!
    ctx.drawImage(img, 0, 0, SAMPLE, SAMPLE)
    const px = ctx.getImageData(0, 0, SAMPLE, SAMPLE).data
    const at = (x: number, y: number) => (y * SAMPLE + x) * 4
    const mid = SAMPLE >> 1
    // Count dark pixels inward from each edge along the middle row/column.
    const run = (step: (k: number) => number) => {
      let k = 0
      while (k < SAMPLE / 2 && isDark(px, step(k))) k++
      return k
    }
    const left = run((k) => at(k, mid))
    const right = run((k) => at(SAMPLE - 1 - k, mid))
    const top = run((k) => at(mid, k))
    const bottom = run((k) => at(mid, SAMPLE - 1 - k))
    const pct = (n: number) => (n === 0 ? 0 : Math.min(45, (n / SAMPLE) * 100 + 2.5)) // +2.5% clears the soft edge
    const corners = [at(0, 0), at(SAMPLE - 1, 0), at(0, SAMPLE - 1), at(SAMPLE - 1, SAMPLE - 1)].every((i) => isDark(px, i))
    if (corners && left + right >= SAMPLE * 0.75) {
      // Dark all the way in from both sides: a dark garment on black, not bars.
      fit = { inset: null, darkBackground: true }
    } else if ((left > 1 && right > 1) || (top > 1 && bottom > 1)) {
      // Real borders on opposite sides (a dark garment touching one edge isn't a border).
      fit = { inset: `inset(${pct(top)}% ${pct(right)}% ${pct(bottom)}% ${pct(left)}%)`, darkBackground: false }
    }
  } catch {
    // e.g. a cross-origin image: show it as-is
  }
  cache.set(img.src, fit)
  return fit
}

/** onLoad handler: trims black bars off a photo, or frames a black-background shot in black. */
export function matchFrameToPhoto(e: React.SyntheticEvent<HTMLImageElement>) {
  const img = e.currentTarget
  const { inset, darkBackground } = measure(img)
  img.style.clipPath = inset ?? ''
  img.classList.toggle('trimmed', inset !== null)
  img.parentElement?.classList.toggle('dark-bg', darkBackground)
}
