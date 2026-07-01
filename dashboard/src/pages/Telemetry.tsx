import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useData } from '../lib/useData'
import { useMeta } from '../lib/MetaContext'
import { Card } from '../components/Card'
import { Loading, ErrorBanner } from '../components/Loading'
import { formatLapTime } from '../lib/format'
import type { TelemetryData } from '../lib/types'

export default function Telemetry() {
  const { data, loading, error } = useData<TelemetryData>('telemetry.json')
  const { meta, driversById } = useMeta()

  const driverIds = useMemo(() => (data ? Object.keys(data.fastest_laps_by_driver) : []), [data])
  const sortedByPace = useMemo(
    () =>
      data
        ? [...driverIds].sort(
            (a, b) => data.fastest_laps_by_driver[a].lap_time_s - data.fastest_laps_by_driver[b].lap_time_s,
          )
        : [],
    [data, driverIds],
  )

  const [driverA, setDriverA] = useState<string | null>(null)
  const [driverB, setDriverB] = useState<string | null>(null)

  const a = driverA ?? sortedByPace[0]
  // Default B to the fastest driver on a different team than A, so the two
  // traces aren't the same color by default.
  const defaultB = sortedByPace.find((id) => id !== a && driversById.get(id)?.team_id !== driversById.get(a)?.team_id)
  const b = driverB ?? defaultB ?? sortedByPace.find((id) => id !== a) ?? sortedByPace[1]

  const merged = useMemo(() => {
    if (!data || !a || !b) return []
    const traceA = data.fastest_laps_by_driver[a].trace
    const traceB = new Map(data.fastest_laps_by_driver[b].trace.map((p) => [p.distance_bin_m, p]))
    let cumA = 0
    let cumB = 0
    const rows = []
    for (const pa of traceA) {
      const pb = traceB.get(pa.distance_bin_m)
      const dtA = 20 / (pa.speed_kph / 3.6 || 1)
      cumA += dtA
      let deltaS: number | null = null
      if (pb) {
        const dtB = 20 / (pb.speed_kph / 3.6 || 1)
        cumB += dtB
        deltaS = cumA - cumB
      }
      rows.push({
        distance_m: pa.distance_bin_m,
        [`${a}_speed`]: pa.speed_kph,
        [`${a}_throttle`]: pa.throttle_pct,
        [`${a}_brake`]: pa.brake * 100,
        [`${a}_gear`]: pa.gear,
        ...(pb
          ? {
              [`${b}_speed`]: pb.speed_kph,
              [`${b}_throttle`]: pb.throttle_pct,
              [`${b}_brake`]: pb.brake * 100,
              [`${b}_gear`]: pb.gear,
            }
          : {}),
        delta_s: deltaS,
      })
    }
    return rows
  }, [data, a, b])

  if (loading) return <Loading label="Loading telemetry…" />
  if (error) return <ErrorBanner message={error} />
  if (!data || !a || !b) return null

  const colorA = driversById.get(a)?.color ?? '#e10600'
  const colorB = driversById.get(b)?.color ?? '#38bdf8'
  const drsZones = meta?.track.drs_zones ?? []
  const maxSpeed = Math.max(
    ...merged.map((r) => {
      const row = r as unknown as Record<string, number | undefined>
      return Math.max(row[`${a}_speed`] ?? 0, row[`${b}_speed`] ?? 0)
    }),
  )
  const speedDomain: [number, number] = [0, Math.ceil((maxSpeed + 10) / 10) * 10]

  return (
    <div className="space-y-6">
      <Card title="Telemetry Comparison" subtitle="Fastest race lap for each selected driver, overlaid by distance into the lap">
        <div className="flex flex-wrap items-center gap-4 mb-5">
          <DriverSelect label="Driver A" value={a} onChange={setDriverA} options={sortedByPace} data={data} driversById={driversById} accent={colorA} />
          <DriverSelect label="Driver B" value={b} onChange={setDriverB} options={sortedByPace} data={data} driversById={driversById} accent={colorB} />
        </div>

        <ChartBlock title="Speed" unit="km/h" height={220}>
          <LineChart data={merged} margin={{ top: 4, right: 12, left: 0, bottom: 0 }} syncId="telemetry">
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
            {drsZones.map((z, i) => (
              <ReferenceArea key={i} x1={z.start_m} x2={z.end_m} fill="#22c55e" fillOpacity={0.06} strokeOpacity={0} />
            ))}
            <XAxis dataKey="distance_m" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}m`} />
            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} width={36} domain={speedDomain} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => `${v}m`} />
            <Line type="monotone" dataKey={`${a}_speed`} stroke={colorA} dot={false} strokeWidth={2} isAnimationActive={false} />
            <Line type="monotone" dataKey={`${b}_speed`} stroke={colorB} strokeDasharray="6 3" dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ChartBlock>

        <ChartBlock title="Throttle" unit="%" height={140}>
          <AreaChart data={merged} margin={{ top: 4, right: 12, left: 0, bottom: 0 }} syncId="telemetry">
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
            <XAxis dataKey="distance_m" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}m`} />
            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} width={36} domain={[0, 100]} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => `${v}m`} />
            <Area type="monotone" dataKey={`${a}_throttle`} stroke={colorA} fill={colorA} fillOpacity={0.15} strokeWidth={1.5} isAnimationActive={false} />
            <Area type="monotone" dataKey={`${b}_throttle`} stroke={colorB} strokeDasharray="6 3" fill={colorB} fillOpacity={0.15} strokeWidth={1.5} isAnimationActive={false} />
          </AreaChart>
        </ChartBlock>

        <ChartBlock title="Brake" unit="" height={100}>
          <AreaChart data={merged} margin={{ top: 4, right: 12, left: 0, bottom: 0 }} syncId="telemetry">
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
            <XAxis dataKey="distance_m" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}m`} />
            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} width={36} domain={[0, 100]} hide />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => `${v}m`} />
            <Area type="step" dataKey={`${a}_brake`} stroke={colorA} fill={colorA} fillOpacity={0.25} strokeWidth={1} isAnimationActive={false} />
            <Area type="step" dataKey={`${b}_brake`} stroke={colorB} strokeDasharray="6 3" fill={colorB} fillOpacity={0.25} strokeWidth={1} isAnimationActive={false} />
          </AreaChart>
        </ChartBlock>

        <ChartBlock title="Gear" unit="" height={120}>
          <LineChart data={merged} margin={{ top: 4, right: 12, left: 0, bottom: 0 }} syncId="telemetry">
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
            <XAxis dataKey="distance_m" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}m`} />
            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} width={36} domain={[1, 8]} allowDecimals={false} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => `${v}m`} />
            <Line type="stepAfter" dataKey={`${a}_gear`} stroke={colorA} dot={false} strokeWidth={1.5} isAnimationActive={false} />
            <Line type="stepAfter" dataKey={`${b}_gear`} stroke={colorB} strokeDasharray="6 3" dot={false} strokeWidth={1.5} isAnimationActive={false} />
          </LineChart>
        </ChartBlock>

        <ChartBlock title="Time delta (A − B)" unit="s" height={140}>
          <AreaChart data={merged} margin={{ top: 4, right: 12, left: 0, bottom: 0 }} syncId="telemetry">
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
            <XAxis dataKey="distance_m" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}m`} />
            <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} width={36} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v) => `${v}m`} formatter={(v: any) => Number(v)?.toFixed(3)} />
            <Area type="monotone" dataKey="delta_s" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.2} strokeWidth={1.5} isAnimationActive={false} />
          </AreaChart>
        </ChartBlock>
      </Card>
    </div>
  )
}

function ChartBlock({ title, unit, height, children }: { title: string; unit: string; height: number; children: React.ReactElement }) {
  return (
    <div className="mb-3">
      <p className="text-xs text-gray-500 mb-1">
        {title} {unit && `(${unit})`}
      </p>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  )
}

function DriverSelect({
  label,
  value,
  onChange,
  options,
  data,
  driversById,
  accent,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
  data: TelemetryData
  driversById: ReturnType<typeof useMeta>['driversById']
  accent: string
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-gray-500">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border px-2.5 py-1.5 text-sm bg-surface text-gray-100"
        style={{ borderColor: accent }}
      >
        {options.map((id) => (
          <option key={id} value={id}>
            {driversById.get(id)?.full_name ?? id} · {formatLapTime(data.fastest_laps_by_driver[id].lap_time_s)}
          </option>
        ))}
      </select>
    </label>
  )
}

const tooltipStyle = { background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }
