import { useState } from 'react'
import { api } from './api.js'
import { riskLabel } from './format.js'

const WORDS = { done: 'Done.', expired: 'That request expired.', already_done: 'Already handled.', rejected: 'Rejected.', failed: 'That did not work.', unknown: 'Unknown request.' }

export function Approvals({ actions, reload }) {
  const [busy, setBusy] = useState(null) // id in flight: blocks double clicks
  const [msg, setMsg] = useState('')
  const act = async (id, verb) => {
    if (busy) return
    setBusy(id); setMsg('')
    try {
      const r = await api(`/api/actions/${id}/${verb}`, { method: 'POST' })
      setMsg(verb === 'reject' ? 'Rejected.' : WORDS[r.status] || 'Unknown request.')
    } catch (e) { setMsg(e.message) }
    setBusy(null)
    reload()
  }
  return (
    <section className="panel">
      <h2>Approvals</h2>
      <p className="muted">PAI asks before it sends, deletes or spends anything.</p>
      <p role="status" aria-live="polite" className="muted">{msg}</p>
      {actions === null ? <p className="muted">Loading…</p> : actions.length === 0 ? <p className="muted">Nothing is waiting for you.</p> : actions.map((a) => (
        <div className="mem" key={a.id}>
          <div><span className="chip risk">{riskLabel(a.kind)}</span> <span>{a.summary}</span></div>
          <div className="row">
            <button className="btn primary" disabled={!!busy} onClick={() => act(a.id, 'confirm')} aria-label={`Approve: ${a.summary}`}>Approve</button>
            <button className="btn" disabled={!!busy} onClick={() => act(a.id, 'reject')} aria-label={`Reject: ${a.summary}`}>Reject</button>
          </div>
        </div>
      ))}
    </section>
  )
}
