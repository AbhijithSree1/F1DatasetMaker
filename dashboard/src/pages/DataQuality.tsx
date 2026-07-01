import { useMemo } from 'react'
import { useData } from '../lib/useData'
import { Card } from '../components/Card'
import { StatCard } from '../components/StatCard'
import { Loading, ErrorBanner } from '../components/Loading'
import type { DataQuality as DataQualityData } from '../lib/types'

function PassBadge({ passed }: { passed: boolean | null }) {
  if (passed === null)
    return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400 border border-gray-700">N/A</span>
  if (passed)
    return (
      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950/50 text-emerald-400 border border-emerald-800/50">
        Passed
      </span>
    )
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-red-950/50 text-red-400 border border-red-800/50">Failed</span>
  )
}

export default function DataQuality() {
  const { data, loading, error } = useData<DataQualityData>('data_quality.json')

  const stats = useMemo(() => {
    if (!data) return null
    const schemaPassed = data.schema_report.filter((r) => r.passed === true).length
    const schemaFailed = data.schema_report.filter((r) => r.passed === false).length
    const sanityPassed = data.sanity_checks.filter((r) => r.passed === true).length
    const sanityFailed = data.sanity_checks.filter((r) => r.passed === false).length
    return { schemaPassed, schemaFailed, sanityPassed, sanityFailed }
  }, [data])

  if (loading) return <Loading label="Loading data quality report…" />
  if (error) return <ErrorBanner message={error} />
  if (!data || !stats) return null

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Tables schema-checked" value={data.schema_report.length} />
        <StatCard
          label="Schema conformance"
          value={`${stats.schemaPassed}/${stats.schemaPassed + stats.schemaFailed}`}
          accent={stats.schemaFailed === 0 ? '#22c55e' : '#ef4444'}
        />
        <StatCard label="Sanity checks run" value={data.sanity_checks.length} />
        <StatCard
          label="Sanity checks passed"
          value={`${stats.sanityPassed}/${stats.sanityPassed + stats.sanityFailed}`}
          accent={stats.sanityFailed === 0 ? '#22c55e' : '#ef4444'}
        />
      </div>

      <Card title="Schema Conformance" subtitle="Each table's columns checked against the canonical data dictionary">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-border">
                <th className="py-2 pr-4 font-medium">Table</th>
                <th className="py-2 pr-4 font-medium text-right">Rows</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Missing columns</th>
                <th className="py-2 pr-4 font-medium">Max null rate</th>
              </tr>
            </thead>
            <tbody>
              {data.schema_report.map((row) => {
                const nullRates = Object.values(row.null_rates ?? {}).filter((v) => v !== null) as number[]
                const maxNull = nullRates.length ? Math.max(...nullRates) : null
                return (
                  <tr key={row.table} className="border-b border-border/60 last:border-0 hover:bg-surface-hover">
                    <td className="py-2 pr-4 font-mono text-gray-200">{row.table}</td>
                    <td className="py-2 pr-4 tabular-nums text-right text-gray-400">{row.row_count.toLocaleString()}</td>
                    <td className="py-2 pr-4">
                      <PassBadge passed={row.passed} />
                    </td>
                    <td className="py-2 pr-4 text-xs text-gray-500">
                      {row.missing_columns.length ? row.missing_columns.join(', ') : '—'}
                    </td>
                    <td className="py-2 pr-4 tabular-nums text-xs text-gray-400">
                      {maxNull === null ? '—' : `${(maxNull * 100).toFixed(1)}%`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Sanity Checks" subtitle="Range and consistency checks (e.g. positive lap times, plausible speeds)">
        <div className="overflow-x-auto -mx-5 px-5">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-border">
                <th className="py-2 pr-4 font-medium">Check</th>
                <th className="py-2 pr-4 font-medium">Table</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {data.sanity_checks.map((row) => (
                <tr key={row.check} className="border-b border-border/60 last:border-0 hover:bg-surface-hover">
                  <td className="py-2 pr-4 font-mono text-gray-200">{row.check}</td>
                  <td className="py-2 pr-4 text-gray-400">{row.table}</td>
                  <td className="py-2 pr-4">
                    <PassBadge passed={row.passed} />
                  </td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
