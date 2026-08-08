import { useEffect, useState } from 'react'
import { Plug, Plus, RefreshCw, Trash2, Wifi } from 'lucide-react'
import api, { readError, rows } from '../lib/api'
import { Alert, Badge, EmptyState, Modal, Spinner } from '../components/ui'

const STATUS_TONE = { connected: 'green', pending: 'amber', error: 'red', disabled: 'gray' }

export default function Connections() {
  const [connections, setConnections] = useState([])
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [creating, setCreating] = useState(null) // holds the chosen provider spec
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([api.get('/connections/'), api.get('/connectors/providers/')])
      .then(([connRes, provRes]) => { setConnections(rows(connRes.data)); setProviders(rows(provRes.data)) })
      .catch((err) => setError(readError(err)))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const startCreate = (provider) => {
    const initial = { display_name: `${provider.label}` }
    provider.config_fields.forEach((field) => { initial[field.key] = field.default || '' })
    setForm(initial)
    setCreating(provider)
  }

  const save = async (event) => {
    event.preventDefault()
    setSaving(true); setError('')
    try {
      // Split the one flat form into public config and encrypted credentials.
      const config = {}
      const credentials = {}
      creating.config_fields.forEach((field) => {
        const value = form[field.key]
        if (!value) return
        if (field.secret) credentials[field.key] = value
        else config[field.key] = value
      })
      await api.post('/connections/', {
        provider: creating.provider,
        display_name: form.display_name,
        config,
        credentials,
      })
      setCreating(null); load()
      setNotice('Connection saved. Use "Test" to confirm the credentials, then "Sync".')
    } catch (err) {
      setError(readError(err))
    } finally {
      setSaving(false)
    }
  }

  const act = async (connection, verb) => {
    setBusyId(connection.id); setError(''); setNotice('')
    try {
      const { data } = await api.post(`/connections/${connection.id}/${verb}/`, {})
      setNotice(verb === 'test'
        ? (data.message || 'Credentials look good.')
        : `Sync ${data.status}: ${data.pools_created} pool(s) created, ${data.pools_updated} updated, ${data.assignments_synced} seats recorded.${data.error_message ? ` ${data.error_message}` : ''}`)
      load()
    } catch (err) {
      setError(readError(err))
    } finally {
      setBusyId(null)
    }
  }

  const remove = async (connection) => {
    if (!window.confirm(`Remove the ${connection.display_name} connection?`)) return
    try { await api.delete(`/connections/${connection.id}/`); load() }
    catch (err) { setError(readError(err)) }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Connections</h1>
        <p className="text-sm text-ink-500">Link a vendor once; LicenseGuard keeps the seat counts current.</p>
      </div>

      <Alert onClose={() => setError('')}>{error}</Alert>
      <Alert tone="success" onClose={() => setNotice('')}>{notice}</Alert>

      {loading ? <Spinner /> : (
        <>
          {connections.length === 0 ? (
            <EmptyState icon={Plug} title="Nothing connected yet"
              body="Pick a provider below to start syncing seat counts automatically." />
          ) : (
            <div className="card overflow-x-auto">
              <table className="w-full min-w-[760px]">
                <thead className="border-b border-ink-200 bg-ink-50">
                  <tr>
                    <th className="th">Connection</th><th className="th">Provider</th>
                    <th className="th">Status</th><th className="th">Last sync</th><th className="th" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-100">
                  {connections.map((connection) => (
                    <tr key={connection.id} className="hover:bg-ink-50/60">
                      <td className="td font-medium">{connection.display_name}</td>
                      <td className="td text-ink-600">{connection.provider_label}</td>
                      <td className="td">
                        <Badge tone={STATUS_TONE[connection.status] || 'gray'}>{connection.status}</Badge>
                        {connection.last_error && (
                          <p className="mt-1 max-w-xs text-xs text-red-600">{connection.last_error}</p>
                        )}
                      </td>
                      <td className="td text-ink-600">
                        {connection.last_sync_at ? new Date(connection.last_sync_at).toLocaleString() : 'Never'}
                      </td>
                      <td className="td">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => act(connection, 'test')} disabled={busyId === connection.id}
                            className="btn-secondary !px-2.5 !py-1.5 !text-xs"><Wifi size={13} /> Test</button>
                          <button onClick={() => act(connection, 'sync')} disabled={busyId === connection.id}
                            className="btn-secondary !px-2.5 !py-1.5 !text-xs">
                            <RefreshCw size={13} className={busyId === connection.id ? 'animate-spin' : ''} /> Sync
                          </button>
                          <button onClick={() => remove(connection)}
                            className="p-1.5 text-ink-400 hover:text-red-600"><Trash2 size={15} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div>
            <h2 className="mb-3 mt-8 font-semibold">Available providers</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {providers.map((provider) => (
                <div key={provider.provider} className="card flex flex-col p-5">
                  <h3 className="font-semibold">{provider.label}</h3>
                  <p className="mt-1 flex-1 text-sm leading-relaxed text-ink-600">{provider.description}</p>
                  <div className="mt-4 flex items-center justify-between">
                    <Badge tone={provider.supports_total_seats ? 'green' : 'amber'}>
                      {provider.supports_total_seats ? 'Syncs seat cap' : 'Cap entered manually'}
                    </Badge>
                    <button onClick={() => startCreate(provider)} className="btn-primary !px-3 !py-1.5 !text-xs">
                      <Plus size={13} /> Connect
                    </button>
                  </div>
                  {provider.docs_url && (
                    <a href={provider.docs_url} target="_blank" rel="noreferrer"
                      className="mt-3 text-xs text-ink-500 hover:underline">Vendor API docs</a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {creating && (
        <Modal wide title={`Connect ${creating.label}`} onClose={() => setCreating(null)}>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className="label">Connection name</label>
              <input required className="input" value={form.display_name || ''}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
            </div>
            {creating.config_fields.map((field) => (
              <div key={field.key}>
                <label className="label">
                  {field.label}
                  {field.secret && <span className="ml-2 text-xs font-normal text-ink-400">encrypted at rest</span>}
                </label>
                {field.type === 'textarea' ? (
                  <textarea rows={6} required={field.required} className="input font-mono text-xs"
                    placeholder={field.placeholder || ''} value={form[field.key] || ''}
                    onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} />
                ) : (
                  <input type={field.secret ? 'password' : field.type === 'email' ? 'email' : 'text'}
                    required={field.required} className="input" placeholder={field.placeholder || ''}
                    value={form[field.key] || ''}
                    onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} />
                )}
                {field.help && <p className="mt-1 text-xs text-ink-500">{field.help}</p>}
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setCreating(null)} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Saving...' : 'Save connection'}</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
