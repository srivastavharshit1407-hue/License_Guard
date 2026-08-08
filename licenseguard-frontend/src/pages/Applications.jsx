import { useEffect, useState } from 'react'
import { AppWindow, Pencil, Plus, Trash2 } from 'lucide-react'
import api, { readError, rows } from '../lib/api'
import { Alert, Badge, EmptyState, Modal, Spinner } from '../components/ui'

const CATEGORIES = [
  ['productivity', 'Productivity'], ['communication', 'Communication'],
  ['development', 'Development'], ['security', 'Security'], ['design', 'Design'],
  ['sales_marketing', 'Sales & Marketing'], ['finance', 'Finance & HR'],
  ['infrastructure', 'Infrastructure'], ['other', 'Other'],
]

const BLANK = { name: '', vendor: '', category: 'other', website: '', owner_email: '', description: '' }

export default function Applications() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(BLANK)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    api.get('/applications/')
      .then(({ data }) => setItems(rows(data)))
      .catch((err) => setError(readError(err)))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const openNew = () => { setForm(BLANK); setEditing('new') }
  const openEdit = (app) => { setForm({ ...BLANK, ...app }); setEditing(app.id) }
  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const save = async (event) => {
    event.preventDefault()
    setSaving(true); setError('')
    try {
      const payload = {
        name: form.name, vendor: form.vendor, category: form.category,
        website: form.website, owner_email: form.owner_email, description: form.description,
      }
      if (editing === 'new') await api.post('/applications/', payload)
      else await api.patch(`/applications/${editing}/`, payload)
      setEditing(null); load()
    } catch (err) {
      setError(readError(err))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (app) => {
    if (!window.confirm(`Delete ${app.name} and all of its licence pools?`)) return
    try { await api.delete(`/applications/${app.id}/`); load() }
    catch (err) { setError(readError(err)) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Applications</h1>
          <p className="text-sm text-ink-500">Every product your company holds licences for.</p>
        </div>
        <button onClick={openNew} className="btn-primary"><Plus size={16} /> Add application</button>
      </div>

      <Alert onClose={() => setError('')}>{error}</Alert>

      {loading ? <Spinner /> : items.length === 0 ? (
        <EmptyState icon={AppWindow} title="No applications yet"
          body="Add one manually, or connect a vendor so LicenseGuard discovers them for you."
          action={<button onClick={openNew} className="btn-primary"><Plus size={16} /> Add application</button>} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr>
                <th className="th">Application</th><th className="th">Category</th>
                <th className="th">Pools</th><th className="th">Seats</th>
                <th className="th">Owner</th><th className="th" />
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {items.map((app) => (
                <tr key={app.id} className="hover:bg-ink-50/60">
                  <td className="td">
                    <div className="font-medium">{app.name}</div>
                    {app.vendor && <div className="text-xs text-ink-500">{app.vendor}</div>}
                  </td>
                  <td className="td"><Badge>{CATEGORIES.find(([k]) => k === app.category)?.[1] || app.category}</Badge></td>
                  <td className="td">{app.pool_count}</td>
                  <td className="td tabular-nums">
                    {app.total_seats ? `${app.used_seats} / ${app.total_seats}` : `${app.used_seats} used`}
                  </td>
                  <td className="td text-ink-600">{app.owner_email || '-'}</td>
                  <td className="td text-right">
                    <button onClick={() => openEdit(app)} className="mr-1 p-1.5 text-ink-400 hover:text-ink-900"><Pencil size={15} /></button>
                    <button onClick={() => remove(app)} className="p-1.5 text-ink-400 hover:text-red-600"><Trash2 size={15} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <Modal title={editing === 'new' ? 'Add application' : 'Edit application'} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className="label">Name</label>
              <input required className="input" value={form.name} onChange={update('name')} placeholder="Google Workspace" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Vendor</label>
                <input className="input" value={form.vendor} onChange={update('vendor')} placeholder="Google" />
              </div>
              <div>
                <label className="label">Category</label>
                <select className="input" value={form.category} onChange={update('category')}>
                  {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Website</label>
                <input type="url" className="input" value={form.website} onChange={update('website')} placeholder="https://workspace.google.com" />
              </div>
              <div>
                <label className="label">Internal owner</label>
                <input type="email" className="input" value={form.owner_email} onChange={update('owner_email')} placeholder="it@acme.com" />
              </div>
            </div>
            <div>
              <label className="label">Notes</label>
              <textarea rows={3} className="input" value={form.description} onChange={update('description')} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Saving...' : 'Save'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
