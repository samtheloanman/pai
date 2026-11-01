import { useEffect, useState } from 'react'
import { api } from './api.js'

function Row({ p, apply }) {
  const [key, setKey] = useState('')
  const [model, setModel] = useState(p.model || '')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const put = async (body) => {
    setBusy(true); setErr('')
    try { apply(await api('/api/providers', { method: 'PUT', body: JSON.stringify({ name: p.name, ...body }) })); setKey('') }
    catch (e) { setErr(e.message) }
    setBusy(false)
  }
  const save = () => put({ ...(key ? { key } : {}), ...(model !== (p.model || '') ? { model } : {}) })
  return (
    <div className="mem prov">
      <strong>{p.name}{p.cloud ? '' : ' (this box)'}</strong>
      <div className="row">
        {p.cloud && (p.has_key
          ? <><span>Key saved</span><button className="btn" disabled={busy} onClick={() => put({ key: '' })} aria-label={`Remove key for ${p.name}`}>Remove</button></>
          : <input type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} placeholder="API key" aria-label={`API key for ${p.name}`} />)}
        <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model" aria-label={`Model for ${p.name}`} />
        <button className="btn primary" disabled={busy} onClick={save} aria-label={`Save ${p.name}`}>Save</button>
      </div>
      {err && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{err}</p>}
    </div>
  )
}

export function Providers() {
  const [s, setS] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api('/api/providers').then(setS).catch((e) => setErr(e.message)) }, [])
  if (!s) return <div className="panel">{err || 'Loading…'}</div>
  const wrap = async (fn) => { setErr(''); try { setS(await fn()) } catch (e) { setErr(e.message) } }
  return (
    <section className="panel">
      <h2>Providers</h2>
      <p className="warn">{s.warning}</p>
      <p className="muted">Long numbers (like card numbers or very long ids) are kept on this box, even if they are not cards.</p>
      {s.restart_required && (
        <div className="banner" role="status">
          <span>Restart PAI to apply these changes: run <code>docker compose restart litellm</code></span>
          <button className="btn" onClick={() => wrap(() => api('/api/providers/restarted', { method: 'POST' }))}>I've restarted PAI</button>
        </div>
      )}
      <label className="row">
        <input type="checkbox" role="switch" checked={s.cloud_enabled} onChange={(e) => wrap(() => api('/api/providers/cloud', { method: 'PUT', body: JSON.stringify({ enabled: e.target.checked }) }))} />
        <span>Allow cloud models</span>
      </label>
      {err && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{err}</p>}
      {s.providers.map((p) => <Row key={p.name} p={p} apply={setS} />)}
    </section>
  )
}
