import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api, { readError, rows } from '../lib/api'
import { Alert, Spinner, StatCard, UsageBar } from '../components/ui'

const money = (value, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value || 0)

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [pools, setPools] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.get('/dashboard/summary/'), api.get('/license-pools/?ordering=-used_seats')])
      .then(([summaryRes, poolsRes]) => {
        setSummary(summaryRes.data)
        setPools(rows(poolsRes.data))
      })
      .catch((err) => setError(readError(err)))
  }, [])

  if (error) return <Alert>{error}</Alert>
  if (!summary) return <Spinner />

  const chartData = pools
    .filter((pool) => pool.total_seats > 0)
    .slice(0, 8)
    .map((pool) => ({
      name: pool.application_name.length > 14
        ? `${pool.application_name.slice(0, 13)}...` : pool.application_name,
      Used: pool.used_seats,
      Unused: Math.max(pool.total_seats - pool.used_seats, 0),
    }))

  const utilTone = summary.utilization_pct >= 90 ? 'danger'
    : summary.utilization_pct >= 80 ? 'warn' : 'good'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Overview</h1>
        <p className="text-sm text-ink-500">Everything your organization holds licences for.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Applications" value={summary.application_count}
          sub={`${summary.pool_count} licence pools`} />
        <StatCard label="Seats in use" value={`${summary.used_seats} / ${summary.total_seats}`}
          sub={`${summary.available_seats} available`} />
        <StatCard label="Utilisation" value={`${summary.utilization_pct}%`} tone={utilTone}
          sub="Across all pools" />
        <StatCard label="Spent on unused seats" value={money(summary.wasted_annual_spend)}
          tone={summary.wasted_annual_spend > 0 ? 'warn' : 'good'} sub="Per year, estimated" />
      </div>

      {chartData.length > 0 && (
        <div className="card p-5">
          <h2 className="mb-4 font-semibold">Seats used vs unused</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eceef2" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="Used" stackId="a" fill="#111827" radius={[0, 0, 0, 0]} />
              <Bar dataKey="Unused" stackId="a" fill="#d5dae2" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-ink-200 px-5 py-4">
          <h2 className="font-semibold">Pools needing attention</h2>
          <Link to="/licenses" className="text-sm font-medium text-ink-600 hover:underline">
            View all licences
          </Link>
        </div>
        {summary.pools_at_risk.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-ink-500">
            Nothing above 85% utilisation. You have headroom everywhere.
          </p>
        ) : (
          <table className="w-full">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr><th className="th">Application</th><th className="th">Pool</th><th className="th">Usage</th></tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {summary.pools_at_risk.map((pool) => (
                <tr key={pool.id}>
                  <td className="td font-medium">{pool.application}</td>
                  <td className="td text-ink-600">{pool.pool}</td>
                  <td className="td"><UsageBar used={pool.used_seats} total={pool.total_seats} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
