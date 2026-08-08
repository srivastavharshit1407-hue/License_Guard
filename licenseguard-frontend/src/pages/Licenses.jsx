import { useEffect, useRef, useState } from 'react'
import { KeyRound, Pencil, Plus, Trash2, Upload } from 'lucide-react'
import api, { readError, rows } from '../lib/api'
import { Alert, Badge, EmptyState, Modal, Spinner, UsageBar } from '../components/ui'

const BLANK = {
  application: '', name: '', sku: '', total_seats: 0, used_seats: 0,
  unit_cost: 0, currency: 'USD', billing_cycle: 'annual', renewal_date: '', notes: '',
}

const money = (value, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value || 0)

// Read-only stand-in for an <input>, used for fields a connector owns.
const LockedValue = ({ children }) => (
  <div className="input flex items-center bg-ink-50 text-ink-500">{children}</div>
)

export default function Licenses() {
  const [pools, setPools] = useState([])
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(BLANK)
  const [saving, setSaving] = useState(false)
  const fileRef = useRef(null)

  const load = () => {
    setLoading(true)
    Promise.all([api.get('/license-pools/'), api.get('/applications/')])
      .then(([poolRes, appRes]) => { setPools(rows(poolRes.data)); setApps(rows(appRes.data)) })
      .catch((err) => setError(readError(err)))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const openNew = () => { setForm({ ...BLANK, application: apps[0]?.id || '' }); setEditing('new') }
  const openEdit = (pool) => {
    setForm({ ...BLANK, ...pool, renewal_date: pool.renewal_date || '' })
    setEditing(pool.id)
  }
  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  // A connector owns identity/usage for pools it syncs. Editing those here
  // would just get silently clobbered on the next sync (or reject with a
  // 400 from the serializer's lock-down) - so don't even send them.
  const isSynced = editing !== 'new' && form.source && form.source !== 'manual' && form.source !== 'csv'

  const save = async (event) => {
    event.preventDefault()
    setSaving(true); setError('')
    try {
      const payload = {
        unit_cost: Number(form.unit_cost) || 0,
        currency: form.currency, billing_cycle: form.billing_cycle,
        renewal_date: form.renewal_date || null, notes: form.notes,
      }
      if (!isSynced) {
        payload.application = form.application
        payload.name = form.name
        payload.sku = form.sku
        payload.used_seats = Number(form.used_seats) || 0
      }
      if (!isSynced || !form.total_seats_is_synced) {
        payload.total_seats = Number(form.total_seats) || 0
      }
      if (editing === 'new') await api.post('/license-pools/', payload)
      else await api.patch(`/license-pools/${editing}/`, payload)
      setEditing(null); load()
    } catch (err) {
      setError(readError(err))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (pool) => {
    if (!window.confirm(`Delete the "${pool.name}" pool?`)) return
    try { await api.delete(`/license-pools/${pool.id}/`); load() }
    catch (err) { setError(readError(err)) }
  }

  const uploadCsv = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    const body = new FormData()
    body.append('file', file)
    setError(''); setNotice('')
    try {
      const { data } = await api.post('/license-pools/import-csv/', body,
        { headers: { 'Content-Type': 'multipart/form-data' } })
      setNotice(`Imported ${data.created} new and updated ${data.updated} existing pools.`)
      load()
    } catch (err) {
      setError(readError(err))
    } finally {
      event.target.value = ''
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Licences</h1>
          <p className="text-sm text-ink-500">Seats purchased, seats used, and what the gap costs.</p>
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".csv" hidden onChange={uploadCsv} />
          <button onClick={() => fileRef.current?.click()} className="btn-secondary">
            <Upload size={16} /> Import CSV
          </button>
          <button onClick={openNew} disabled={apps.length === 0} className="btn-primary">
            <Plus size={16} /> Add licence pool
          </button>
        </div>
      </div>

      <Alert onClose={() => setError('')}>{error}</Alert>
      <Alert tone="success" onClose={() => setNotice('')}>{notice}</Alert>

      {loading ? <Spinner /> : pools.length === 0 ? (
        <EmptyState icon={KeyRound} title="No licence pools yet"
          body="Add an application first, then record how many seats you bought. Or import a CSV with columns: application, pool_name, total_seats." />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[900px]">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr>
                <th className="th">Application</th><th className="th">Pool</th>
                <th className="th">Usage</th><th className="th">Source</th>
                <th className="th">Wasted / yr</th><th className="th">Renews</th><th className="th" />
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {pools.map((pool) => (
                <tr key={pool.id} className="hover:bg-ink-50/60">
                  <td className="td font-medium">{pool.application_name}</td>
                  <td className="td">
                    <div>{pool.name}</div>
                    {pool.sku && <div className="font-mono text-xs text-ink-400">{pool.sku}</div>}
                  </td>
                  <td className="td"><UsageBar used={pool.used_seats} total={pool.total_seats} /></td>
                  <td className="td">
                    <Badge tone={pool.source === 'manual' || pool.source === 'csv' ? 'gray' : 'blue'}>
                      {pool.source.replace(/_/g, ' ')}
                    </Badge>
                  </td>
                  <td className="td tabular-nums text-ink-600">
                    {pool.wasted_annual_cost > 0 ? money(pool.wasted_annual_cost, pool.currency) : '-'}
                  </td>
                  <td className="td text-ink-600">{pool.renewal_date || '-'}</td>
                  <td className="td text-right">
                    <button onClick={() => openEdit(pool)} className="mr-1 p-1.5 text-ink-400 hover:text-ink-900"><Pencil size={15} /></button>
                    <button onClick={() => remove(pool)} className="p-1.5 text-ink-400 hover:text-red-600"><Trash2 size={15} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <Modal wide title={editing === 'new' ? 'Add licence pool' : 'Edit licence pool'} onClose={() => setEditing(null)}>
          {isSynced && (
            <p className="-mt-2 mb-4 text-xs text-ink-500">
              Synced from your {form.source.replace(/_/g, ' ')} connection - identity and usage fields
              below are locked; only cost and renewal details are yours to edit.
            </p>
          )}
          <form onSubmit={save} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Application</label>
                {isSynced ? (
                  <LockedValue>{form.application_name}</LockedValue>
                ) : (
                  <select required className="input" value={form.application} onChange={update('application')}>
                    <option value="">Select...</option>
                    {apps.map((app) => <option key={app.id} value={app.id}>{app.name}</option>)}
                  </select>
                )}
              </div>
              <div>
                <label className="label">Pool name</label>
                {isSynced ? <LockedValue>{form.name}</LockedValue> : (
                  <input required className="input" value={form.name} onChange={update('name')} placeholder="Business Standard" />
                )}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="label">Seats purchased</label>
                {isSynced && form.total_seats_is_synced ? <LockedValue>{form.total_seats}</LockedValue> : (
                  <input type="number" min="0" className="input" value={form.total_seats} onChange={update('total_seats')} />
                )}
                {isSynced && !form.total_seats_is_synced && (
                  <p className="mt-1 text-xs text-ink-500">
                    {form.source.replace(/_/g, ' ')} has no API for this - keep it up to date by hand.
                  </p>
                )}
              </div>
              <div>
                <label className="label">Seats used</label>
                {isSynced ? (
                  <>
                    <LockedValue>{form.used_seats}</LockedValue>
                    <p className="mt-1 text-xs text-ink-500">Synced automatically - updates on each sync.</p>
                  </>
                ) : (
                  <input type="number" min="0" className="input" value={form.used_seats} onChange={update('used_seats')} />
                )}
              </div>
              <div>
                <label className="label">SKU</label>
                {isSynced ? <LockedValue>{form.sku || '—'}</LockedValue> : (
                  <input className="input" value={form.sku} onChange={update('sku')} />
                )}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-4">
              <div>
                <label className="label">Cost per seat</label>
                <input type="number" step="0.01" min="0" className="input" value={form.unit_cost} onChange={update('unit_cost')} />
              </div>
              <div>
                <label className="label">Currency</label>
                <input maxLength={3} className="input uppercase" value={form.currency} onChange={update('currency')} />
              </div>
              <div>
                <label className="label">Billing</label>
                <select className="input" value={form.billing_cycle} onChange={update('billing_cycle')}>
                  <option value="annual">Annual</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="label">Renewal date</label>
                <input type="date" className="input" value={form.renewal_date} onChange={update('renewal_date')} />
              </div>
            </div>
            <div>
              <label className="label">Notes</label>
              <textarea rows={2} className="input" value={form.notes} onChange={update('notes')} />
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
