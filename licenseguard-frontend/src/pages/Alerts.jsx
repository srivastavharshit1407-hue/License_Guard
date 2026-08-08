import { useEffect, useState } from 'react'
import { BellRing, Pencil, Play, Plus, Trash2 } from 'lucide-react'
import api, { readError, rows } from '../lib/api'
import { Alert, Badge, EmptyState, Modal, Spinner } from '../components/ui'

const CONDITIONS = [
  ['utilization_above', 'Utilisation % goes above', '%'],
  ['used_seats_above', 'Used seats go above', 'seats'],
  ['available_seats_below', 'Available seats drop below', 'seats'],
  ['renewal_within_days', 'Renewal is within', 'days'],
]

const BLANK = {
  name: '', scope: 'all_pools', application: '', license_pool: '',
  condition: 'utilization_above', threshold: 90, recipientsText: '',
  cooldown_hours: 24, is_active: true,
}

export default function Alerts() {
  const [rules, setRules] = useState([])
  const [events, setEvents] = useState([])
  const [apps, setApps] = useState([])
  const [pools, setPools] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(BLANK)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([
      api.get('/alert-rules/'), api.get('/alert-events/'),
      api.get('/applications/'), api.get('/license-pools/'),
    ])
      .then(([ruleRes, eventRes, appRes, poolRes]) => {
        setRules(rows(ruleRes.data)); setEvents(rows(eventRes.data))
        setApps(rows(appRes.data)); setPools(rows(poolRes.data))
      })
      .catch((err) => setError(readError(err)))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const openNew = () => { setForm(BLANK); setEditing('new') }
  const openEdit = (rule) => {
    setForm({
      ...BLANK, ...rule,
      application: rule.application || '', license_pool: rule.license_pool || '',
      recipientsText: (rule.recipients || []).join(', '),
    })
    setEditing(rule.id)
  }
  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const save = async (event) => {
    event.preventDefault()
    setSaving(true); setError('')
    try {
      const payload = {
        name: form.name,
        scope: form.scope,
        application: form.scope === 'application' ? form.application : null,
        license_pool: form.scope === 'pool' ? form.license_pool : null,
        condition: form.condition,
        threshold: Number(form.threshold),
        recipients: form.recipientsText.split(',').map((s) => s.trim()).filter(Boolean),
        cooldown_hours: Number(form.cooldown_hours),
        is_active: form.is_active,
      }
      if (editing === 'new') await api.post('/alert-rules/', payload)
      else await api.patch(`/alert-rules/${editing}/`, payload)
      setEditing(null); load()
    } catch (err) {
      setError(readError(err))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (rule) => {
    if (!window.confirm(`Delete the rule "${rule.name}"?`)) return
    try { await api.delete(`/alert-rules/${rule.id}/`); load() }
    catch (err) { setError(readError(err)) }
  }

  const runNow = async () => {
    setError(''); setNotice('')
    try {
      const { data } = await api.post('/alert-rules/evaluate/', {})
      setNotice(data.triggered === 0
        ? 'Checked every rule - nothing is over its threshold.'
        : `${data.triggered} alert(s) fired and emails were sent.`)
      load()
    } catch (err) { setError(readError(err)) }
  }

  const unit = CONDITIONS.find(([key]) => key === form.condition)?.[2] || ''

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Alerts</h1>
          <p className="text-sm text-ink-500">Email the right people before a licence pool runs out.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={runNow} className="btn-secondary"><Play size={16} /> Run checks now</button>
          <button onClick={openNew} className="btn-primary"><Plus size={16} /> New rule</button>
        </div>
      </div>

      <Alert onClose={() => setError('')}>{error}</Alert>
      <Alert tone="success" onClose={() => setNotice('')}>{notice}</Alert>

      {loading ? <Spinner /> : rules.length === 0 ? (
        <EmptyState icon={BellRing} title="No alert rules yet"
          body='Example: "email it@acme.com when any pool goes above 90% utilised".'
          action={<button onClick={openNew} className="btn-primary"><Plus size={16} /> New rule</button>} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[820px]">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr>
                <th className="th">Rule</th><th className="th">Watches</th>
                <th className="th">Condition</th><th className="th">Recipients</th>
                <th className="th">Status</th><th className="th" />
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-ink-50/60">
                  <td className="td font-medium">{rule.name}</td>
                  <td className="td text-ink-600">
                    {rule.scope === 'all_pools' ? 'All pools'
                      : rule.scope === 'application' ? rule.application_name : rule.pool_name}
                  </td>
                  <td className="td text-ink-600">
                    {CONDITIONS.find(([key]) => key === rule.condition)?.[1]} {rule.threshold}
                  </td>
                  <td className="td text-ink-600">{(rule.recipients || []).join(', ')}</td>
                  <td className="td">
                    <Badge tone={rule.is_active ? 'green' : 'gray'}>{rule.is_active ? 'Active' : 'Paused'}</Badge>
                  </td>
                  <td className="td text-right">
                    <button onClick={() => openEdit(rule)} className="mr-1 p-1.5 text-ink-400 hover:text-ink-900"><Pencil size={15} /></button>
                    <button onClick={() => remove(rule)} className="p-1.5 text-ink-400 hover:text-red-600"><Trash2 size={15} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="border-b border-ink-200 px-5 py-4">
          <h2 className="font-semibold">Recent alerts</h2>
        </div>
        {events.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-ink-500">No alerts have fired yet.</p>
        ) : (
          <ul className="divide-y divide-ink-100">
            {events.slice(0, 15).map((event) => (
              <li key={event.id} className="flex items-start justify-between gap-4 px-5 py-3">
                <div>
                  <p className="text-sm font-medium">{event.message}</p>
                  <p className="mt-0.5 text-xs text-ink-500">
                    {new Date(event.triggered_at).toLocaleString()} &middot; {(event.recipients || []).join(', ')}
                  </p>
                </div>
                <Badge tone={event.email_sent ? 'green' : 'red'}>
                  {event.email_sent ? 'Emailed' : 'Not sent'}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </div>

      {editing && (
        <Modal wide title={editing === 'new' ? 'New alert rule' : 'Edit alert rule'} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className="label">Rule name</label>
              <input required className="input" value={form.name} onChange={update('name')}
                placeholder="Google Workspace nearly full" />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Watch</label>
                <select className="input" value={form.scope} onChange={update('scope')}>
                  <option value="all_pools">Every licence pool</option>
                  <option value="application">One application</option>
                  <option value="pool">One licence pool</option>
                </select>
              </div>
              {form.scope === 'application' && (
                <div>
                  <label className="label">Application</label>
                  <select required className="input" value={form.application} onChange={update('application')}>
                    <option value="">Select...</option>
                    {apps.map((app) => <option key={app.id} value={app.id}>{app.name}</option>)}
                  </select>
                </div>
              )}
              {form.scope === 'pool' && (
                <div>
                  <label className="label">Licence pool</label>
                  <select required className="input" value={form.license_pool} onChange={update('license_pool')}>
                    <option value="">Select...</option>
                    {pools.map((pool) => (
                      <option key={pool.id} value={pool.id}>{pool.application_name} - {pool.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Trigger when</label>
                <select className="input" value={form.condition} onChange={update('condition')}>
                  {CONDITIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Threshold ({unit})</label>
                <input type="number" required min="0" step="any" className="input"
                  value={form.threshold} onChange={update('threshold')} />
              </div>
            </div>

            <div>
              <label className="label">Email these people</label>
              <input required className="input" value={form.recipientsText} onChange={update('recipientsText')}
                placeholder="it@acme.com, finance@acme.com" />
              <p className="mt-1 text-xs text-ink-500">Comma separated.</p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Cooldown (hours)</label>
                <input type="number" min="0" className="input" value={form.cooldown_hours} onChange={update('cooldown_hours')} />
                <p className="mt-1 text-xs text-ink-500">Stops the same alert repeating every hour.</p>
              </div>
              <div className="flex items-end pb-2">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="h-4 w-4 rounded border-ink-300"
                    checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
                  Rule is active
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Saving...' : 'Save rule'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
