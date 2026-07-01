import { useMemo } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useData } from '../lib/useData'
import { useMeta } from '../lib/MetaContext'
import { Card } from '../components/Card'
import { StatCard } from '../components/StatCard'
import { DriverBadge, TeamDot } from '../components/DriverBadge'
import { Loading, ErrorBanner } from '../components/Loading'
import { formatDelta, formatLapTime, formatRaceTime } from '../lib/format'
import type { Overview as OverviewData } from '../lib/types'

function pivotPositions(rows: OverviewData['position_by_lap']) {
  const byLap = new Map<number, Record<string, number>>()
  for (const r of rows) {
    if (!byLap.has(r.lap_number)) byLap.set(r.lap_number, { lap_number: r.lap_number })
    byLap.get(r.lap_number)![r.driver_id] = r.position
  }
  return Array.from(byLap.values()).sort((a, b) => a.lap_number - b.lap_number)
}

export default function Overview() {
  const { data, loading, error } = useData<OverviewData>('overview.json')
  const { meta, driversById } = useMeta()

  const chartData = useMemo(() => (data ? pivotPositions(data.position_by_lap) : []), [data])

  if (loading) return <Loading label="Loading race overview…" />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  const winner = data.standings[0]
  const podium = data.standings.slice(0, 3)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Race winner"
          value={winner.full_name}
          hint={winner.team_name}
          accent={winner.color}
        />
        <StatCard
          label="Fastest lap"
          value={formatLapTime(data.fastest_lap.lap_time_s)}
          hint={`${data.fastest_lap.full_name} · lap ${data.fastest_lap.lap_number}`}
          accent={data.fastest_lap.color}
        />
        <StatCard label="Race distance" value={`${data.total_laps} laps`} hint={meta?.circuit} />
        <StatCard
          label="Winning time"
          value={formatRaceTime(winner.total_time_s)}
          hint={`${data.standings.length} classified finishers`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Race Position" subtitle="Position by lap for every driver" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#24242f" vertical={false} />
              <XAxis
                dataKey="lap_number"
                stroke="#6b7280"
                tick={{ fontSize: 11 }}
                label={{ value: 'Lap', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }}
              />
              <YAxis
                reversed
                domain={[1, data.standings.length]}
                allowDecimals={false}
                stroke="#6b7280"
                tick={{ fontSize: 11 }}
                width={28}
              />
              <Tooltip
                contentStyle={{ background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }}
                labelFormatter={(lap) => `Lap ${lap}`}
                formatter={(value: any, driverId: any) => [
                  `P${value}`,
                  driversById.get(driverId)?.full_name ?? driverId,
                ]}
              />
              {[...driversById.values()].map((driver) => (
                <Line
                  key={driver.driver_id}
                  type="monotone"
                  dataKey={driver.driver_id}
                  stroke={driver.color}
                  strokeWidth={driver.driver_id === winner.driver_id ? 3 : 1.25}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Podium">
          <ol className="space-y-3">
            {podium.map((row, i) => (
              <li key={row.driver_id} className="flex items-center gap-3 rounded-xl border border-border p-3">
                <span
                  className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white shrink-0"
                  style={{ background: i === 0 ? '#eab308' : i === 1 ? '#9ca3af' : '#b45309' }}
                >
                  {row.position}
                </span>
                <div className="min-w-0 flex-1">
                  <DriverBadge name={row.full_name} team={row.team_name} color={row.color} />
                </div>
                <span className="text-xs text-gray-500 tabular-nums shrink-0">
                  {i === 0 ? formatRaceTime(row.total_time_s) : formatDelta(row.gap_to_leader_s, 3)}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      <Card title="Full Classification">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-border">
                <th className="py-2 pr-4 font-medium">Pos</th>
                <th className="py-2 pr-4 font-medium">Driver</th>
                <th className="py-2 pr-4 font-medium">Grid</th>
                <th className="py-2 pr-4 font-medium text-right">Gap</th>
                <th className="py-2 pr-4 font-medium text-right">Points</th>
              </tr>
            </thead>
            <tbody>
              {data.standings.map((row) => (
                <tr key={row.driver_id} className="border-b border-border/60 last:border-0 hover:bg-surface-hover">
                  <td className="py-2 pr-4 tabular-nums text-gray-400">{row.position}</td>
                  <td className="py-2 pr-4">
                    <DriverBadge name={row.full_name} team={row.team_name} color={row.color} />
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-gray-400">
                    <span className="inline-flex items-center gap-1">
                      {row.grid_position !== row.position &&
                        (row.grid_position > row.position ? (
                          <span className="text-emerald-400">▲</span>
                        ) : (
                          <span className="text-red-400">▼</span>
                        ))}
                      P{row.grid_position}
                    </span>
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-right text-gray-300">
                    {row.position === 1 ? formatRaceTime(row.total_time_s) : formatDelta(row.gap_to_leader_s, 3)}
                  </td>
                  <td className="py-2 pr-4 tabular-nums text-right font-medium text-gray-100">{row.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {meta && (
        <Card title="Teams">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {meta.teams.map((team) => (
              <span key={team.team_id} className="inline-flex items-center gap-2 text-sm text-gray-300">
                <TeamDot color={team.color} />
                {team.team_name}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
