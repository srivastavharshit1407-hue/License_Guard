import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import GoogleSignInButton from '../components/GoogleSignInButton'
import { Alert } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { readError } from '../lib/api'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      await login(form.email, form.password)
      navigate('/dashboard')
    } catch (err) {
      setError(readError(err, 'Incorrect email or password.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 px-4 py-12">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2 text-lg font-bold">
          <ShieldCheck size={22} /> LicenseGuard
        </Link>

        <div className="card p-8">
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="mt-1 text-sm text-ink-500">Sign in to your licence inventory.</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <Alert onClose={() => setError('')}>{error}</Alert>
            <div>
              <label className="label" htmlFor="email">Work email</label>
              <input id="email" type="email" required className="input" autoComplete="email"
                value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <input id="password" type="password" required className="input" autoComplete="current-password"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
            <button type="submit" disabled={busy} className="btn-primary w-full">
              {busy ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-ink-400">
            <div className="h-px flex-1 bg-ink-200" /> OR <div className="h-px flex-1 bg-ink-200" />
          </div>
          <GoogleSignInButton onError={setError} />

          <p className="mt-6 text-center text-sm text-ink-500">
            No account? <Link to="/signup" className="font-semibold text-ink-900 hover:underline">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
