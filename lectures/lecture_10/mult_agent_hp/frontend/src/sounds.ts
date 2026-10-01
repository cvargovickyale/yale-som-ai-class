/** Synthesized wand sounds (Web Audio, no files).
 *
 * playRequestIn — a bright rising sparkle when an agent receives a task.
 * playReplyOut  — a softer falling chime when an agent sends its result back.
 * Sounds that fire at the same moment are spaced out slightly so seven
 * parallel delegations ripple instead of piling into one blare.
 */

let ctx: AudioContext | null = null
let muted = false
let nextSlot = 0
const SPACING = 0.07 // seconds between overlapping sounds

function getCtx(): AudioContext | null {
  const AC =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AC) return null
  if (!ctx) ctx = new AC()
  return ctx
}

export function setMuted(value: boolean) {
  muted = value
}

/** Call from a click handler so the browser allows later playback. */
export async function unlockAudio() {
  try {
    const c = getCtx()
    if (c && c.state === 'suspended') await c.resume()
  } catch {
    // ignore autoplay quirks
  }
}

function tone(c: AudioContext, freq: number, start: number, dur: number, gain: number, type: OscillatorType, glideTo?: number) {
  const osc = c.createOscillator()
  const g = c.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  if (glideTo) osc.frequency.exponentialRampToValueAtTime(glideTo, start + dur)
  g.gain.setValueAtTime(0.0001, start)
  g.gain.exponentialRampToValueAtTime(gain, start + 0.015)
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur)
  osc.connect(g)
  g.connect(c.destination)
  osc.start(start)
  osc.stop(start + dur + 0.03)
}

function slot(c: AudioContext): number {
  const t = Math.max(c.currentTime + 0.01, nextSlot)
  nextSlot = t + SPACING
  return t
}

/** "Bling!" — a quick upward swish plus sparkles. */
export function playRequestIn(pitch = 1) {
  const c = getCtx()
  if (!c || muted) return
  const t = slot(c)
  tone(c, 880 * pitch, t, 0.12, 0.06, 'sine', 1760 * pitch)
  tone(c, 1318.5 * pitch, t + 0.06, 0.22, 0.07, 'triangle')
  tone(c, 1975.5 * pitch, t + 0.11, 0.25, 0.04, 'sine')
  for (let i = 0; i < 3; i += 1) {
    tone(c, (2400 + Math.random() * 1400) * pitch, t + 0.14 + i * 0.035, 0.1, 0.018, 'sine')
  }
}

/** "Plink-plonk" — a gentle downward two-note chime, rounder and lower. */
export function playReplyOut(pitch = 1) {
  const c = getCtx()
  if (!c || muted) return
  const t = slot(c)
  tone(c, 1174.7 * pitch, t, 0.2, 0.07, 'triangle')
  tone(c, 784 * pitch, t + 0.1, 0.32, 0.08, 'triangle')
  tone(c, 392 * pitch, t + 0.1, 0.3, 0.03, 'sine')
}
