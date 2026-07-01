export function formatLapTime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '—'
  const mins = Math.floor(seconds / 60)
  const secs = seconds - mins * 60
  return `${mins}:${secs.toFixed(3).padStart(6, '0')}`
}

export function formatDelta(seconds: number | null | undefined, digits = 3): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '—'
  const sign = seconds > 0 ? '+' : seconds < 0 ? '−' : ''
  return `${sign}${Math.abs(seconds).toFixed(digits)}s`
}

export function formatSeconds(seconds: number | null | undefined, digits = 1): string {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return '—'
  return `${seconds.toFixed(digits)}s`
}

export function formatRaceTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = totalSeconds % 60
  const parts = h > 0 ? [h, m.toString().padStart(2, '0')] : [m]
  return `${parts.join(':')}:${s.toFixed(3).padStart(6, '0')}`
}

const TRACK_STATUS_LABEL: Record<string, string> = {
  green: 'Green',
  yellow: 'Yellow',
  SC: 'Safety Car',
  VSC: 'Virtual SC',
  red: 'Red Flag',
  unknown: 'Unknown',
}

export function trackStatusLabel(status: string): string {
  return TRACK_STATUS_LABEL[status] ?? status
}

const COMPOUND_COLOR: Record<string, string> = {
  SOFT: '#ff3b3b',
  MEDIUM: '#ffd43b',
  HARD: '#f4f4f6',
  INTERMEDIATE: '#4caf50',
  WET: '#3b82f6',
}

export function compoundColor(compound: string): string {
  return COMPOUND_COLOR[compound] ?? '#9ca3af'
}
