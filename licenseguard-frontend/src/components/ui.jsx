/** Small shared pieces. Keeping them together avoids a dozen one-line files. */
import { AlertTriangle, CheckCircle2, X } from 'lucide-react'

export function StatCard({ label, value, sub, tone = 'default' }) {
  const tones = {
    default: 'text-ink-900',
    warn: 'text-amber-600',
    danger: 'text-red-600',
    good: 'text-emerald-600',
  }
  return (
    <div className="card p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${tones[tone]}`}>{value}</p>
      {sub && <p className="mt-1 text-sm text-ink-500">{sub}</p>}
    </div>
  )
}

export function UsageBar({ used, total }) {
  const pct = total ? Math.min((used / total) * 100, 100) : 0
  const colour = !total ? 'bg-ink-300' : pct >= 95 ? 'bg-red-500' : pct >= 85 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 w-28 overflow-hidden rounded-full bg-ink-100">
        <div className={`h-full rounded-full ${colour}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-28 shrink-0 text-xs tabular-nums text-ink-600">
        {total ? `${used}/${total} (${pct.toFixed(0)}%)` : `${used} used, no cap set`}
      </span>
    </div>
  )
}

export function Badge({ tone = 'gray', children }) {
  const tones = {
    gray: 'bg-ink-100 text-ink-700',
    green: 'bg-emerald-100 text-emerald-800',
    amber: 'bg-amber-100 text-amber-800',
    red: 'bg-red-100 text-red-800',
    blue: 'bg-blue-100 text-blue-800',
  }
  return <span className={`badge ${tones[tone]}`}>{children}</span>
}

export function Alert({ tone = 'error', children, onClose }) {
  if (!children) return null
  const isError = tone === 'error'
  return (
    <div className={`flex items-start gap-2 rounded-lg px-3 py-2.5 text-sm ${
      isError ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>
      {isError ? <AlertTriangle size={16} className="mt-0.5 shrink-0" />
               : <CheckCircle2 size={16} className="mt-0.5 shrink-0" />}
      <span className="flex-1">{children}</span>
      {onClose && <button onClick={onClose} className="shrink-0 opacity-60 hover:opacity-100"><X size={14} /></button>}
    </div>
  )
}

export function Modal({ title, children, onClose, wide = false }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink-900/50 p-4 sm:p-8">
      <div className={`card w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} shadow-xl`}>
        <div className="flex items-center justify-between border-b border-ink-200 px-5 py-4">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={onClose} className="text-ink-400 hover:text-ink-900"><X size={18} /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

export function EmptyState({ icon: Icon, title, body, action }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
      {Icon && <Icon size={32} className="text-ink-300" />}
      <h3 className="font-semibold">{title}</h3>
      {body && <p className="max-w-md text-sm text-ink-500">{body}</p>}
      {action}
    </div>
  )
}

export function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-ink-200 border-t-ink-900" />
    </div>
  )
}
