import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { useData } from '../lib/useData'
import { useMeta } from '../lib/MetaContext'
import { Card } from '../components/Card'
import { Loading, ErrorBanner } from '../components/Loading'
import { compoundColor, formatLapTime, formatSeconds } from '../lib/format'
import type { LapTimeRow, Strategy } from '../lib/types'

function pivotLapTimes(rows: LapTimeRow[], selected: Set<string>) {
  const byLap = new Map<number, Record<string, number>>()
  for (const r of rows) {
    if (!selected.has(r.driver_id)) continue
    if (!byLap.has(r.lap_number)) byLap.set(r.lap_number, { lap_number: r.lap_number })
    byLap.get(r.lap_number)![r.driver_id] = r.lap_time_s
  }
  return Array.from(byLap.values()).sort((a, b) => a.lap_number - b.lap_number)
}

function safetyCarWindows(rows: LapTimeRow[]): [number, number][] {
  const scLaps = [...new Set(rows.filter((r) => r.track_status === 'SC').map((r) => r.lap_number))].sort(
    (a, b) => a - b,
  )
  const windows: [number, number][] = []
  for (const lap of scLaps) {
    const last = windows[windows.length - 1]
    if (last && lap === last[1] + 1) last[1] = lap
    else windows.push([lap, lap])
  }
  return windows
}

function buildStrategyRows(strategy: Strategy) {
  const byDriver = new Map<string, { full_name: string; color: string; stints: Strategy['stints'] }>()
  for (const s of strategy.stints) {
    if (!byDriver.has(s.driver_id)) byDriver.set(s.driver_id, { full_name: s.full_name, color: s.color, stints: [] })
    byDriver.get(s.driver_id)!.stints.push(s)
  }
  return [...byDriver.values()].map((d) => {
    const sorted = [...d.stints].sort((a, b) => a.stint_number - b.stint_number)
    const row: Record<string, unknown> = { full_name: d.full_name, color: d.color }
    sorted.forEach((s, i) => {
      row[`s${i + 1}_len`] = s.lap_end - s.lap_start + 1
      row[`s${i + 1}_compound`] = s.compound
    })
    return row
  })
}

export default function LapTimes() {
  const { data: laps, loading: lapsLoading, error: lapsError } = useData<LapTimeRow[]>('lap_times.json')
  const { data: strategy, loading: stratLoading, error: stratError } = useData<Strategy>('strategy.json')
  const { driversById } = useMeta()

  const [selected, setSelected] = useState<Set<string> | null>(null)

  const driverOrder = useMemo(() => {
    if (!laps) return []
    const seen = new Map<string, LapTimeRow>()
    for (const r of laps) if (!seen.has(r.driver_id)) seen.set(r.driver_id, r)
    return [...seen.values()]
  }, [laps])

  const effectiveSelected = useMemo(() => {
    if (selected) return selected
    return new Set(driverOrder.slice(0, 6).map((d) => d.driver_id))
  }, [selected, driverOrder])

  const chartData = useMemo(() => (laps ? pivotLapTimes(laps, effectiveSelected) : []), [laps, effectiveSelected])
  const scWindows = useMemo(() => (laps ? safetyCarWindows(laps) : []), [laps])
  const strategyRows = useMemo(() => (strategy ? buildStrategyRows(strategy) : []), [strategy])
  const maxStints = strategyRows.reduce((m, r) => Math.max(m, Object.keys(r).filter((k) => k.endsWith('_len')).length), 0)

  function toggleDriver(id: string) {
    const next = new Set(effectiveSelected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  if (lapsLoading || stratLoading) return <Loading label="Loading lap times & strategy…" />
  if (lapsError || stratError) return <ErrorBanner message={lapsError || stratError || 'unknown error'} />
  if (!laps || !strategy) return null

  return (
    <div className="space-y-6">
      <Card
        title="Lap Time Evolution"
        subtitle="Click a driver below to toggle it on the chart. Shaded bands mark Safety Car periods."
      >
        <div className="flex flex-wrap gap-2 mb-4">
          {driverOrder.map((d) => (
            <button
              key={d.driver_id}
              onClick={() => toggleDriver(d.driver_id)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                effectiveSelected.has(d.driver_id)
                  ? 'border-transparent text-white'
                  : 'border-border text-gray-500 hover:text-gray-300'
              }`}
              style={effectiveSelected.has(d.driver_id) ? { background: d.color } : undefined}
            >
              {driversById.get(d.driver_id)?.abbreviation ?? d.driver_id}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={380}>
          <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
            <XAxis
              dataKey="lap_number"
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              label={{ value: 'Lap', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis
              stroke="#6b7280"
              tick={{ fontSize: 11 }}
              width={64}
              tickFormatter={(v) => formatLapTime(v)}
              domain={['dataMin - 2', 'dataMax + 2']}
            />
            {scWindows.map(([start, end]) => (
              <ReferenceArea key={start} x1={start} x2={end} fill="#eab308" fillOpacity={0.08} strokeOpacity={0} />
            ))}
            <Tooltip
              contentStyle={{ background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }}
              labelFormatter={(lap) => `Lap ${lap}`}
              formatter={(value: any, driverId: any) => [
                formatLapTime(value),
                driversById.get(driverId)?.full_name ?? driverId,
              ]}
            />
            {[...effectiveSelected].map((id) => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                stroke={driversById.get(id)?.color ?? '#888'}
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Tire Strategy" subtitle="Stint length and compound per driver">
        <ResponsiveContainer width="100%" height={Math.max(320, strategyRows.length * 26)}>
          <BarChart data={strategyRows} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" horizontal={false} />
            <XAxis type="number" stroke="#6b7280" tick={{ fontSize: 11 }} label={{ value: 'Lap', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }} />
            <YAxis type="category" dataKey="full_name" stroke="#6b7280" tick={{ fontSize: 11 }} width={120} />
            <Tooltip
              contentStyle={{ background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }}
              formatter={(value: any, key: any, item: any) => [`${value} laps`, String(item.payload[`${String(key).replace('_len', '')}_compound`] ?? '')]}
            />
            {Array.from({ length: maxStints }, (_, i) => i + 1).map((n) => (
              <Bar key={n} dataKey={`s${n}_len`} stackId="stint" isAnimationActive={false} radius={0}>
                {strategyRows.map((row, i) => (
                  <Cell key={i} fill={compoundColor(String(row[`s${n}_compound`] ?? ''))} />
                ))}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-3 text-xs text-gray-400">
          {['SOFT', 'MEDIUM', 'HARD'].map((c) => (
            <span key={c} className="inline-flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm inline-block" style={{ background: compoundColor(c) }} />
              {c}
            </span>
          ))}
        </div>
      </Card>

      <Card title="Pit Stops">
        <PitStopScatter strategy={strategy} />
      </Card>
    </div>
  )
}

function PitStopScatter({ strategy }: { strategy: Strategy }) {
  const points = strategy.pit_stops.map((p) => ({ ...p, y: 1 }))
  return (
    <div>
      <ResponsiveContainer width="100%" height={140}>
        <ScatterChart margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#24242f" />
          <XAxis type="number" dataKey="lap_number" stroke="#6b7280" tick={{ fontSize: 11 }} name="Lap" />
          <YAxis type="number" dataKey="y" hide domain={[0, 2]} />
          <ZAxis type="number" dataKey="pit_duration_s" range={[60, 400]} name="Duration" />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            contentStyle={{ background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }}
            formatter={(value: any, name: any) => (name === 'Duration' ? formatSeconds(Number(value)) : value)}
            labelFormatter={() => ''}
          />
          <Scatter data={points} fill="#38bdf8" />
        </ScatterChart>
      </ResponsiveContainer>
      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-border">
              <th className="py-2 pr-4 font-medium">Driver</th>
              <th className="py-2 pr-4 font-medium">Lap</th>
              <th className="py-2 pr-4 font-medium text-right">Duration</th>
            </tr>
          </thead>
          <tbody>
            {[...strategy.pit_stops]
              .sort((a, b) => a.lap_number - b.lap_number)
              .map((p, i) => (
                <tr key={i} className="border-b border-border/60 last:border-0 hover:bg-surface-hover">
                  <td className="py-1.5 pr-4">{p.full_name}</td>
                  <td className="py-1.5 pr-4 tabular-nums text-gray-400">{p.lap_number}</td>
                  <td className="py-1.5 pr-4 tabular-nums text-right">{formatSeconds(p.pit_duration_s)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
