import { useEffect, useState } from 'react'
import { api } from './api.js'
import { activityLine } from './format.js'

const FILTERS = [
  ['All', null],
  ['Model calls', ['model_call']],
  ['Routes', ['route']],
  ['Actions', ['action_proposed', 'action_confirmed', 'action_rejected']],
  ['Cloud', ['outbound']],
  ['Config', ['config_changed']],
]
const n = (v) => Number(v).toLocaleString('en-US')

// Known fields only; never the raw field blob.
function meta(f) {
  const out = []
  if (f['gen_ai.usage.input_tokens'] != null) out.push(`${n(f['gen_ai.usage.input_tokens'])} in`)
  if (f['gen_ai.usage.output_tokens'] != null) out.push(`${n(f['gen_ai.usage.output_tokens'])} out`)
  if (f.duration_ms != null) out.push(`${n(f.duration_ms)} ms`)
  if (f.status) out.push(String(f.status))
  return out.join(' · ')
}

export function Activity() {
  const [rows, setRows] = useState(null)
  const [filter, setFilter] = useState(0)
  const [err, setErr] = useState('')
  const [check, setCheck] = useState({ busy: false, text: '' })
  useEffect(() => { api('/api/activity?limit=200').then(setRows).catch((e) => setErr(e.message)) }, [])
  const verify = async () => {
    setCheck({ busy: true, text: '' })
    try {
      const r = await api('/api/activity/verify')
      setCheck({ busy: false, text: r.intact ? 'Log intact.' : `Log has been changed at entry ${r.first_broken}.` })
    } catch (e) { setCheck({ busy: false, text: `Could not check the log: ${e.message}` }) }
  }
  const kinds = FILTERS[filter][1]
  const shown = rows && (kinds ? rows.filter((r) => kinds.includes(r.kind)) : rows)
  return (
    <section className="panel">
      <h2>Activity</h2>
      <p className="muted">What PAI did, newest first. Only details, never your messages.</p>
      <div className="row" role="group" aria-label="Filter by kind">
        {FILTERS.map(([label], i) => (
          <button key={label} className={`chip btn-chip`} aria-pressed={filter === i} onClick={() => setFilter(i)}>{label}</button>
        ))}
      </div>
      <div className="row">
        <button className="btn" onClick={verify} disabled={check.busy}>{check.busy ? 'Checking…' : 'Check log integrity'}</button>
        <span role="status" aria-live="polite" className="muted">{check.text}</span>
      </div>
      {err && <p role="alert" style={{ color: 'var(--danger)' }}>{err}</p>}
      {!shown ? (!err && <p className="muted">Loading…</p>) : shown.length === 0 ? <p className="muted">Nothing here yet.</p> : shown.map((r) => (
        <div className="mem act" key={r.id}>
          <div><div>{activityLine(r)}</div>{meta(r.fields) && <div className="muted">{meta(r.fields)}</div>}</div>
          <time className="muted" dateTime={r.ts}>{new Date(r.ts).toLocaleString()}</time>
        </div>
      ))}
    </section>
  )
}
