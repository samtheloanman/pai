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
  const save = (e) => {
    e?.preventDefault()
    put({ ...(key ? { key } : {}), ...(model !== (p.model || '') ? { model } : {}) })
  }
  return (
    <form className="mem prov" onSubmit={save}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <strong>{p.name}</strong>
        <span className="status-tag">{p.cloud ? 'Optional cloud' : 'Local host'}</span>
      </div>
      <div className="row">
        {p.cloud && (p.has_key
          ? <><span>Key saved</span><button type="button" className="btn btn-sm" disabled={busy} onClick={() => put({ key: '' })} aria-label={`Remove key for ${p.name}`}>Remove key</button></>
          : <input type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} placeholder="API key (optional)" aria-label={`API key for ${p.name}`} />)}
        <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model identifier" aria-label={`Model for ${p.name}`} />
        <button type="submit" className="btn primary" disabled={busy} aria-label={`Save ${p.name}`}>Save</button>
      </div>
      {err && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{err}</p>}
    </form>
  )
}

export function Providers() {
  const [s, setS] = useState(null)
  const [err, setErr] = useState('')
  const [scheme, setScheme] = useState(() => {
    try { return localStorage.getItem('color-scheme') || 'light' } catch { return 'light' }
  })

  useEffect(() => { api('/api/providers').then(setS).catch((e) => setErr(e.message)) }, [])

  const applyScheme = (next) => {
    setScheme(next)
    const meta = document.querySelector('meta[name="color-scheme"]')
    if (meta) meta.content = next
    try {
      if (next === 'light dark') localStorage.removeItem('color-scheme')
      else localStorage.setItem('color-scheme', next)
    } catch {}
  }

  if (!s) return <div className="panel">{err || 'Loading…'}</div>
  const wrap = async (fn) => { setErr(''); try { setS(await fn()) } catch (e) { setErr(e.message) } }
  return (
    <section className="panel">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Local Runtime &amp; Providers</h2>
          <p className="muted">Built-in local inference and speech engines run out of the box with zero external API keys.</p>
        </div>
        <div className="row" role="group" aria-label="Appearance theme">
          <span className="muted" style={{ fontSize: 12.5 }}>Appearance:</span>
          {[['light', 'Light'], ['dark', 'Dark'], ['light dark', 'System']].map(([val, label]) => (
            <button
              key={val}
              type="button"
              className="chip btn-chip"
              aria-pressed={scheme === val}
              onClick={() => applyScheme(val)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="ledger" role="table" aria-label="Built-in local engines">
        <div className="ledger-row" role="row">
          <div className="ledger-main" role="cell">
            <strong>llama.cpp Inference Server</strong>
            <span className="muted">Serving <code>pai-chat</code> and <code>pai-decide</code> (Qwen3-4B-Instruct GGUF Q4_K_M)</span>
          </div>
          <div className="ledger-meta" role="cell">
            <code>llm:8080</code>
            <span className="status-tag">Active · 0 keys</span>
          </div>
        </div>
        <div className="ledger-row" role="row">
          <div className="ledger-main" role="cell">
            <strong>Speaches Voice Server</strong>
            <span className="muted">Serving <code>pai-stt</code> (Faster-Whisper Small) and <code>pai-tts</code> (Kokoro-82M)</span>
          </div>
          <div className="ledger-meta" role="cell">
            <code>speaches:8000</code>
            <span className="status-tag">Active · 0 keys</span>
          </div>
        </div>
      </div>

      <p className="warn">{s.warning}</p>
      <p className="muted">Long numbers (such as payment card numbers or account IDs) are kept on this machine even when cloud routing is enabled.</p>
      {s.restart_required && (
        <div className="banner" role="status">
          <span>Restart LiteLLM to apply provider changes: <code>docker compose restart litellm</code></span>
          <button type="button" className="btn btn-sm" onClick={() => wrap(() => api('/api/providers/restarted', { method: 'POST' }))}>Mark restarted</button>
        </div>
      )}
      <label className="row" style={{ cursor: 'pointer' }}>
        <input type="checkbox" role="switch" checked={s.cloud_enabled} onChange={(e) => wrap(() => api('/api/providers/cloud', { method: 'PUT', body: JSON.stringify({ enabled: e.target.checked }) }))} />
        <span>Allow optional cloud models (leave unchecked for strict local-only operation)</span>
      </label>
      {err && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{err}</p>}
      <div className="ledger">
        {s.providers.map((p) => <Row key={p.name} p={p} apply={setS} />)}
      </div>
    </section>
  )
}
