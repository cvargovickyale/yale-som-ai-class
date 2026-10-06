// 73 of the 102 catalogue photos are product shots boxed inside black
// borders (typically 11% per side, 5-29%; measured in P10). When each image
// loads, measure its border widths from a 64px copy and clip them off with
// CSS `clip-path` (cheap: the browser just doesn't paint those edges), so every
// product sits on the same warm-white background. Results are cached per URL.

const SAMPLE = 64
const cache = new Map<string, string | null>()

const isDark = (d: Uint8ClampedArray, i: number) => d[i] + d[i + 1] + d[i + 2] < 120

function borderInset(img: HTMLImageElement): string | null {
  if (cache.has(img.src)) return cache.get(img.src)!
  let inset: string | null = null
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
    const pct = (n: number) => (n === 0 ? 0 : Math.min(45, (n / SAMPLE) * 100 + 1.5)) // +1.5% clears the soft edge
    // Only clip real borders: a dark garment touching the edge isn't a border.
    if ((left > 1 && right > 1) || (top > 1 && bottom > 1)) {
      inset = `inset(${pct(top)}% ${pct(right)}% ${pct(bottom)}% ${pct(left)}%)`
    }
  } catch {
    inset = null // e.g. a cross-origin image: show it as-is
  }
  cache.set(img.src, inset)
  return inset
}

/** onLoad handler: trims black borders off a catalogue photo. */
export function matchFrameToPhoto(e: React.SyntheticEvent<HTMLImageElement>) {
  const img = e.currentTarget
  const inset = borderInset(img)
  img.style.clipPath = inset ?? ''
  img.classList.toggle('trimmed', inset !== null)
}
