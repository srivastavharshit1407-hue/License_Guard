import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import GoogleSignInButton from '../components/GoogleSignInButton'
import { Alert } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import { readError } from '../lib/api'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', company_name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value })

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      await signup(form)
      navigate('/dashboard')
    } catch (err) {
      setError(readError(err, 'Could not create your account.'))
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
          <h1 className="text-2xl font-bold">Create your account</h1>
          <p className="mt-1 text-sm text-ink-500">You will own the workspace for your company.</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <Alert onClose={() => setError('')}>{error}</Alert>
            <div>
              <label className="label" htmlFor="name">Your name</label>
              <input id="name" className="input" value={form.full_name} onChange={update('full_name')} />
            </div>
            <div>
              <label className="label" htmlFor="company">Company name</label>
              <input id="company" required className="input" value={form.company_name} onChange={update('company_name')} />
            </div>
            <div>
              <label className="label" htmlFor="email">Work email</label>
              <input id="email" type="email" required className="input" autoComplete="email"
                value={form.email} onChange={update('email')} />
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <input id="password" type="password" required minLength={10} className="input"
                autoComplete="new-password" value={form.password} onChange={update('password')} />
              <p className="mt-1 text-xs text-ink-500">At least 10 characters.</p>
            </div>
            <button type="submit" disabled={busy} className="btn-primary w-full">
              {busy ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-ink-400">
            <div className="h-px flex-1 bg-ink-200" /> OR <div className="h-px flex-1 bg-ink-200" />
          </div>
          <GoogleSignInButton onError={setError} />

          <p className="mt-6 text-center text-sm text-ink-500">
            Already have an account? <Link to="/login" className="font-semibold text-ink-900 hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
