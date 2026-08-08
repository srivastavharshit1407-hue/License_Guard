import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { AppWindow, BellRing, KeyRound, LayoutDashboard, LogOut, Plug, ShieldCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { to: '/applications', label: 'Applications', icon: AppWindow },
  { to: '/licenses', label: 'Licences', icon: KeyRound },
  { to: '/alerts', label: 'Alerts', icon: BellRing },
  { to: '/connections', label: 'Connections', icon: Plug },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const signOut = () => { logout(); navigate('/') }

  return (
    <div className="min-h-screen bg-ink-50">
      <header className="sticky top-0 z-30 border-b border-ink-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 font-bold">
            <ShieldCheck size={20} className="text-ink-900" />
            LicenseGuard
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium leading-tight">{user?.full_name || user?.email}</p>
              <p className="text-xs text-ink-500">{user?.organization_name}</p>
            </div>
            <button onClick={signOut} className="btn-secondary !px-3 !py-2" title="Sign out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-6">
        {/* Tabs. On mobile they scroll horizontally rather than wrapping. */}
        <nav className="mb-6 flex gap-1 overflow-x-auto rounded-xl border border-ink-200 bg-white p-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
                  isActive ? 'bg-ink-900 text-white' : 'text-ink-600 hover:bg-ink-50'}`}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <Outlet />
      </div>
    </div>
  )
}
