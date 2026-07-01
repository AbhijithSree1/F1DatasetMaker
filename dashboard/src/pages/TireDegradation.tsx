import { useMemo, useState } from 'react'
import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { useData } from '../lib/useData'
import { Card } from '../components/Card'
import { Loading, ErrorBanner } from '../components/Loading'
import { compoundColor, formatDelta } from '../lib/format'
import type { TireDegradationRow } from '../lib/types'

const COMPOUNDS = ['SOFT', 'MEDIUM', 'HARD'] as const

export default function TireDegradation() {
  const { data, loading, error } = useData<TireDegradationRow[]>('tire_degradation.json')
  const [activeCompounds, setActiveCompounds] = useState<Set<string>>(new Set(COMPOUNDS))

  const byCompound = useMemo(() => {
    const groups = new Map<string, TireDegradationRow[]>()
    for (const c of COMPOUNDS) groups.set(c, [])
    for (const row of data ?? []) groups.get(row.compound)?.push(row)
    return groups
  }, [data])

  function toggleCompound(c: string) {
    const next = new Set(activeCompounds)
    if (next.has(c)) next.delete(c)
    else next.add(c)
    setActiveCompounds(next)
  }

  if (loading) return <Loading label="Loading tire degradation…" />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  return (
    <div className="space-y-6">
      <Card
        title="Tire Degradation"
        subtitle="Lap-time delta vs. that stint's best lap, by tire age. Steeper slope = faster degradation."
      >
        <div className="flex gap-2 mb-4">
          {COMPOUNDS.map((c) => (
            <button
              key={c}
              onClick={() => toggleCompound(c)}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-colors ${
                activeCompounds.has(c) ? 'text-black' : 'border-border text-gray-500'
              }`}
              style={activeCompounds.has(c) ? { background: compoundColor(c), borderColor: compoundColor(c) } : undefined}
            >
              {c}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={440}>
          <ScatterChart margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" />
            <XAxis
              type="number"
              dataKey="tyre_age_laps"
              name="Tire age"
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              label={{ value: 'Tire age (laps)', position: 'insideBottom', offset: -4, fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="delta_to_stint_best_s"
              name="Delta"
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              width={40}
              label={{ value: 'Δ to stint best (s)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }}
            />
            <ZAxis range={[24, 24]} />
            <Tooltip
              contentStyle={{ background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }}
              formatter={(value: any, name: any) => [name === 'Delta' ? formatDelta(Number(value)) : value, name]}
              labelFormatter={() => ''}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {COMPOUNDS.filter((c) => activeCompounds.has(c)).map((c) => (
              <Scatter key={c} name={c} data={byCompound.get(c)} fill={compoundColor(c)} fillOpacity={0.6} isAnimationActive={false} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Best Lap per Stint" subtitle="One row per driver/stint">
        <StintSummaryTable rows={data} />
      </Card>
    </div>
  )
}

function StintSummaryTable({ rows }: { rows: TireDegradationRow[] }) {
  const stints = useMemo(() => {
    const byStint = new Map<string, { row: TireDegradationRow; laps: number; maxDelta: number }>()
    for (const r of rows) {
      const key = `${r.session_id}_${r.driver_id}_${r.stint_number}`
      const existing = byStint.get(key)
      if (!existing) byStint.set(key, { row: r, laps: 1, maxDelta: r.delta_to_stint_best_s })
      else {
        existing.laps += 1
        existing.maxDelta = Math.max(existing.maxDelta, r.delta_to_stint_best_s)
      }
    }
    return [...byStint.values()].sort((a, b) => a.row.full_name.localeCompare(b.row.full_name) || a.row.stint_number - b.row.stint_number)
  }, [rows])

  return (
    <div className="overflow-x-auto -mx-5 px-5">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-border">
            <th className="py-2 pr-4 font-medium">Driver</th>
            <th className="py-2 pr-4 font-medium">Stint</th>
            <th className="py-2 pr-4 font-medium">Compound</th>
            <th className="py-2 pr-4 font-medium text-right">Laps</th>
            <th className="py-2 pr-4 font-medium text-right">Best lap</th>
            <th className="py-2 pr-4 font-medium text-right">Max drop-off</th>
          </tr>
        </thead>
        <tbody>
          {stints.map(({ row, laps, maxDelta }) => (
            <tr key={`${row.driver_id}_${row.stint_number}`} className="border-b border-border/60 last:border-0 hover:bg-surface-hover">
              <td className="py-1.5 pr-4">{row.full_name}</td>
              <td className="py-1.5 pr-4 tabular-nums text-gray-400">{row.stint_number}</td>
              <td className="py-1.5 pr-4">
                <span className="inline-flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-sm inline-block" style={{ background: compoundColor(row.compound) }} />
                  {row.compound}
                </span>
              </td>
              <td className="py-1.5 pr-4 tabular-nums text-right">{laps}</td>
              <td className="py-1.5 pr-4 tabular-nums text-right">{row.stint_best_lap_s.toFixed(3)}s</td>
              <td className="py-1.5 pr-4 tabular-nums text-right">{formatDelta(maxDelta)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
