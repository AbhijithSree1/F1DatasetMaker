import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { useData } from '../lib/useData'
import { useMeta } from '../lib/MetaContext'
import { Card } from '../components/Card'
import { Loading, ErrorBanner } from '../components/Loading'
import { DriverBadge } from '../components/DriverBadge'
import { formatDelta, formatLapTime, formatSeconds } from '../lib/format'
import type { DriverBehaviorRow } from '../lib/types'

export default function DriverBehavior() {
  const { data, loading, error } = useData<DriverBehaviorRow[]>('driver_behavior.json')
  const { teamsById } = useMeta()

  const raceRows = useMemo(() => (data ? data.filter((r) => r.session_id.endsWith('_R')) : []), [data])
  const teamColor = (row: DriverBehaviorRow | undefined): string => (row && teamsById.get(row.team_id)?.color) || '#888'
  const byConsistency = useMemo(() => [...raceRows].sort((a, b) => a.consistency_std_s - b.consistency_std_s), [raceRows])
  const byTeammateDelta = useMemo(
    () => [...raceRows].filter((r) => r.teammate_delta_s !== null).sort((a, b) => (a.teammate_delta_s ?? 0) - (b.teammate_delta_s ?? 0)),
    [raceRows],
  )

  if (loading) return <Loading label="Loading driver behavior…" />
  if (error) return <ErrorBanner message={error} />
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Consistency" subtitle="Std. dev. of clean lap times — lower means more consistent">
          <ResponsiveContainer width="100%" height={Math.max(320, byConsistency.length * 24)}>
            <BarChart data={byConsistency} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#24242f" horizontal={false} />
              <XAxis type="number" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(2)}s`} />
              <YAxis type="category" dataKey="full_name" stroke="#6b7280" tick={{ fontSize: 11 }} width={110} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v: any) => [`${Number(v).toFixed(3)}s`, 'Consistency (std dev)']}
              />
              <Bar dataKey="consistency_std_s" isAnimationActive={false} radius={[0, 4, 4, 0]}>
                {byConsistency.map((r) => (
                  <Cell key={r.driver_id} fill={teamColor(r)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Pace vs. Consistency" subtitle="Median clean lap time vs. lap-time variance">
          <ResponsiveContainer width="100%" height={360}>
            <ScatterChart margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#24242f" />
              <XAxis
                type="number"
                dataKey="median_clean_lap_s"
                name="Pace"
                stroke="#6b7280"
                tick={{ fontSize: 11 }}
                tickFormatter={(v) => formatLapTime(v)}
                domain={['dataMin - 0.3', 'dataMax + 0.3']}
                label={{ value: 'Median clean lap', position: 'insideBottom', offset: -4, fill: '#6b7280', fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="consistency_std_s"
                name="Consistency"
                stroke="#6b7280"
                tick={{ fontSize: 11 }}
                width={40}
                label={{ value: 'Std dev (s)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }}
              />
              <ZAxis type="number" range={[80, 80]} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value: any, name: any) => [name === 'Pace' ? formatLapTime(Number(value)) : Number(value).toFixed(3), name]}
                labelFormatter={() => ''}
              />
              <Scatter data={raceRows} isAnimationActive={false}>
                {raceRows.map((r) => (
                  <Cell key={r.driver_id} fill={teamColor(r)} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Teammate Delta" subtitle="Median clean lap time vs. teammate — negative means faster">
        <ResponsiveContainer width="100%" height={Math.max(280, byTeammateDelta.length * 24)}>
          <BarChart data={byTeammateDelta} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#24242f" horizontal={false} />
            <XAxis type="number" stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(2)}s`} />
            <YAxis type="category" dataKey="full_name" stroke="#6b7280" tick={{ fontSize: 11 }} width={110} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => [formatDelta(Number(v)), 'vs. teammate']} />
            <Bar dataKey="teammate_delta_s" isAnimationActive={false} radius={4}>
              {byTeammateDelta.map((r) => (
                <Cell key={r.driver_id} fill={(r.teammate_delta_s ?? 0) <= 0 ? '#22c55e' : '#ef4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Full Driver Behavior Table">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-border">
                <th className="py-2 pr-4 font-medium">Rank</th>
                <th className="py-2 pr-4 font-medium">Driver</th>
                <th className="py-2 pr-4 font-medium text-right">Median lap</th>
                <th className="py-2 pr-4 font-medium text-right">Consistency</th>
                <th className="py-2 pr-4 font-medium text-right">Teammate Δ</th>
                <th className="py-2 pr-4 font-medium text-right">Top speed</th>
                <th className="py-2 pr-4 font-medium text-right">Full throttle</th>
                <th className="py-2 pr-4 font-medium text-right">Brake events/lap</th>
              </tr>
            </thead>
            <tbody>
              {[...raceRows]
                .sort((a, b) => a.pace_rank - b.pace_rank)
                .map((r) => (
                  <tr key={r.driver_id} className="border-b border-border/60 last:border-0 hover:bg-surface-hover">
                    <td className="py-2 pr-4 tabular-nums text-gray-400">{r.pace_rank}</td>
                    <td className="py-2 pr-4">
                      <DriverBadge name={r.full_name} color={teamColor(r)} />
                    </td>
                    <td className="py-2 pr-4 tabular-nums text-right">{formatLapTime(r.median_clean_lap_s)}</td>
                    <td className="py-2 pr-4 tabular-nums text-right">{formatSeconds(r.consistency_std_s, 3)}</td>
                    <td className="py-2 pr-4 tabular-nums text-right">{formatDelta(r.teammate_delta_s)}</td>
                    <td className="py-2 pr-4 tabular-nums text-right">{r.avg_top_speed_kph.toFixed(0)} km/h</td>
                    <td className="py-2 pr-4 tabular-nums text-right">{r.avg_full_throttle_pct_of_lap.toFixed(0)}%</td>
                    <td className="py-2 pr-4 tabular-nums text-right">{r.avg_brake_events_per_lap.toFixed(1)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

const tooltipStyle = { background: '#131319', border: '1px solid #24242f', borderRadius: 8, fontSize: 12 }
