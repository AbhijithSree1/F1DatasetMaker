import type { ReactNode } from 'react'

export function StatCard({
  label,
  value,
  hint,
  accent,
  icon,
}: {
  label: string
  value: ReactNode
  hint?: string
  accent?: string
  icon?: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface/80 backdrop-blur-sm p-5 shadow-lg shadow-black/20 relative overflow-hidden">
      {accent && (
        <div
          className="absolute inset-x-0 top-0 h-0.5"
          style={{ background: `linear-gradient(90deg, ${accent}, transparent)` }}
        />
      )}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">{label}</p>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-50 mt-2 tabular-nums">{value}</p>
      {hint && <p className="text-xs text-gray-500 mt-1">{hint}</p>}
    </div>
  )
}
