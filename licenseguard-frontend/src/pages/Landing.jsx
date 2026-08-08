import { Link } from 'react-router-dom'
import { BellRing, KeyRound, RefreshCw, ShieldCheck } from 'lucide-react'

const FEATURES = [
  { icon: RefreshCw, title: 'Syncs itself',
    body: 'Connect Google Workspace, Microsoft 365, Slack, Zoom or Atlassian once. LicenseGuard pulls seat counts on a schedule so the inventory is never a stale spreadsheet.' },
  { icon: KeyRound, title: 'Caps and utilisation',
    body: 'See how many seats you bought, how many are actually in use, and what the unused ones are costing you every year.' },
  { icon: BellRing, title: 'Alerts before you run out',
    body: 'Set a threshold per application. Cross it and the people you nominated get an email - no one has to remember to check.' },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2 text-lg font-bold">
          <ShieldCheck size={22} />
          LicenseGuard
        </div>
        <div className="flex items-center gap-2">
          <Link to="/login" className="btn-secondary">Log in</Link>
          <Link to="/signup" className="btn-primary">Get started</Link>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 pb-16 pt-20 text-center">
        <span className="badge bg-ink-100 text-ink-700">Software licence management</span>
        <h1 className="mt-5 text-4xl font-extrabold leading-tight tracking-tight sm:text-6xl">
          Know every licence<br />you are paying for.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-ink-600">
          LicenseGuard keeps a live inventory of every application your company subscribes to,
          how many seats you bought, how many are in use, and emails you before you run out.
        </p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Link to="/signup" className="btn-primary !px-6 !py-3 !text-base">Create your account</Link>
          <Link to="/login" className="btn-secondary !px-6 !py-3 !text-base">Sign in</Link>
        </div>
      </section>

      <section className="border-t border-ink-200 bg-ink-50 py-20">
        <div className="mx-auto grid max-w-6xl gap-6 px-6 sm:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <div key={title} className="card p-6">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-ink-900 text-white">
                <Icon size={18} />
              </div>
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-ink-200 py-8 text-center text-sm text-ink-500">
        LicenseGuard
      </footer>
    </div>
  )
}
